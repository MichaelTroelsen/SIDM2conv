"""Drive SIDFactoryII via pyautogui to F10-load each candidate file
and report PASS / CRASH per file.

Workflow per file:
  1. Launch SIDFactoryII.exe (no file argv).
  2. Wait for window titled "SID Factory II".
  3. F10 → opens file picker.
  4. Type absolute path; Enter.
  5. Confirm "load file" dialog with Y.
  6. Poll: process alive + window title contains filename → PASS.
     Process exits early → CRASH (capture exit code, stderr tail).
  7. Close editor (Alt+X or kill).

Usage: python pyscript/sf2_load_test.py <file.sf2> [<file2.sf2> ...]
"""
import os
import sys
import time
import subprocess
import tempfile
from pathlib import Path

import win32gui
import win32api
import win32con
import win32process
import psutil
import pyautogui

EDITOR = str(Path('bin/SIDFactoryII.exe').absolute())


def find_window_for_pid(pid, timeout=10):
    """Return the top-level visible HWND for `pid`, or None."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        hits = []
        def cb(hwnd, _):
            if not win32gui.IsWindowVisible(hwnd):
                return
            try:
                _, wpid = win32process.GetWindowThreadProcessId(hwnd)
            except Exception:
                return
            if wpid == pid and win32gui.GetWindowText(hwnd):
                hits.append(hwnd)
        win32gui.EnumWindows(cb, None)
        if hits:
            return hits[0]
        time.sleep(0.2)
    return None


def title_of(hwnd):
    try:
        return win32gui.GetWindowText(hwnd)
    except Exception:
        return None


import ctypes
from ctypes import wintypes

# SendInput-based key injection. SDL apps often miss keybd_event-style events
# because they use raw input or DirectInput; SendInput simulates a hardware
# keystroke and is the most compatible.
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', wintypes.WORD), ('wScan', wintypes.WORD),
                ('dwFlags', wintypes.DWORD), ('time', wintypes.DWORD),
                ('dwExtraInfo', ctypes.POINTER(wintypes.ULONG))]

class _INPUTunion(ctypes.Union):
    _fields_ = [('ki', KEYBDINPUT),
                ('padding', ctypes.c_ubyte * 32)]

class INPUT(ctypes.Structure):
    _fields_ = [('type', wintypes.DWORD), ('u', _INPUTunion)]

def _make_input(vk, key_up=False, use_scan=False):
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki.wVk = 0 if use_scan else vk
    if use_scan:
        inp.u.ki.wScan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)  # MAPVK_VK_TO_VSC
        inp.u.ki.dwFlags = KEYEVENTF_SCANCODE | (KEYEVENTF_KEYUP if key_up else 0)
    else:
        inp.u.ki.wScan = 0
        inp.u.ki.dwFlags = KEYEVENTF_KEYUP if key_up else 0
    inp.u.ki.time = 0
    inp.u.ki.dwExtraInfo = ctypes.pointer(wintypes.ULONG(0))
    return inp

def send_vk(vk_code, hold_ms=20, use_scan=True):
    """Send a keystroke via SendInput. Scancode mode (use_scan=True) bypasses
    most input filters and is what SDL2 reliably sees as a real key press."""
    down = _make_input(vk_code, key_up=False, use_scan=use_scan)
    up   = _make_input(vk_code, key_up=True,  use_scan=use_scan)
    n_down = ctypes.windll.user32.SendInput(1, ctypes.byref(down), ctypes.sizeof(INPUT))
    time.sleep(hold_ms / 1000.0)
    ctypes.windll.user32.SendInput(1, ctypes.byref(up), ctypes.sizeof(INPUT))
    return n_down == 1


KEYEVENTF_UNICODE = 0x0004

def _make_unicode_input(ch, key_up=False):
    """SendInput with KEYEVENTF_UNICODE bypasses keyboard layout — the OS
    maps the Unicode char directly to a synthetic keystroke. Required for
    backslash on the Danish layout (where vk 0xE2 produces a different
    char than '\\\\' depending on AltGr state)."""
    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki.wVk = 0
    inp.u.ki.wScan = ord(ch)
    inp.u.ki.dwFlags = KEYEVENTF_UNICODE | (KEYEVENTF_KEYUP if key_up else 0)
    inp.u.ki.time = 0
    inp.u.ki.dwExtraInfo = ctypes.pointer(wintypes.ULONG(0))
    return inp


def type_string(s, interval=0.025):
    """Type via SendInput in SCANCODE mode. SDL2 ignores KEYEVENTF_UNICODE
    events; only real scancode keystrokes reach the SDL keyboard handler.
    For each char: VkKeyScan -> VK -> scancode + shift state, then SendInput."""
    for ch in s:
        vk = win32api.VkKeyScan(ch)
        if vk == -1:
            continue
        key = vk & 0xFF
        shift = bool((vk >> 8) & 1)
        # Build sequence: optional shift down, key down, key up, optional shift up
        events = []
        if shift:
            events.append(_make_input(win32con.VK_SHIFT, key_up=False, use_scan=True))
        events.append(_make_input(key, key_up=False, use_scan=True))
        events.append(_make_input(key, key_up=True,  use_scan=True))
        if shift:
            events.append(_make_input(win32con.VK_SHIFT, key_up=True, use_scan=True))
        for ev in events:
            ctypes.windll.user32.SendInput(1, ctypes.byref(ev), ctypes.sizeof(INPUT))
            time.sleep(0.008)
        time.sleep(interval)


def screenshot(label, outdir='/tmp/sf2_screens'):
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f'{int(time.time()*1000)}_{label}.png')
    pyautogui.screenshot(path)
    return path


def test_one(sf2_path: str, total_timeout: float = 12.0, capture_screens=False) -> dict:
    """Drive a fresh SIDFactoryII instance to F10-load `sf2_path`.

    Strategy:
      1. Copy the file under a short test-only name into bin/, so SF2II's
         file picker shows it directly when opened (cwd=bin/).
      2. Use F10 → type the test name → Enter → Y/Enter to confirm.
      3. Watch the process + window title to classify outcome.
    """
    abs_path = str(Path(sf2_path).absolute())
    result = {
        'file': sf2_path, 'verdict': 'UNKNOWN',
        'elapsed_s': 0.0, 'exit_code': None, 'title': None,
        'stderr_tail': '', 'phase': 'launch',
    }

    # Stage the file into bin/ under a short ASCII name (so the picker sees it
    # in its default folder and the filename has no chars that confuse typing).
    bin_dir = Path(EDITOR).parent
    test_name = f'__sf2load_test__{int(time.time()*1000)%100000}.sf2'
    staged = bin_dir / test_name
    import shutil
    shutil.copyfile(sf2_path, staged)

    stderr_f = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='_sf2.err')
    stdout_f = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='_sf2.out')

    file_name = test_name  # what we'll type into the picker
    t0 = time.time()
    proc = subprocess.Popen(
        [EDITOR, '--skip-intro'],
        stdout=stdout_f, stderr=stderr_f,
        cwd=str(bin_dir),
    )
    try:
        # 1. Wait for window
        result['phase'] = 'wait_for_window'
        hwnd = find_window_for_pid(proc.pid, timeout=8)
        if hwnd is None:
            result['verdict'] = 'NO_WINDOW'
            return result
        result['title'] = title_of(hwnd)

        # 2. Foreground + click to FORCE focus + F10. SetForegroundWindow alone
        # is unreliable due to Windows' focus-stealing prevention; a real mouse
        # click on the window guarantees focus transfer.
        result['phase'] = 'F10'
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        time.sleep(0.4)
        # Force focus with an actual click in the window's client area
        try:
            rect = win32gui.GetWindowRect(hwnd)  # (left, top, right, bottom)
            cx = (rect[0] + rect[2]) // 2
            cy = rect[1] + 20  # near the title bar to avoid hitting active controls
            pyautogui.click(cx, cy)
        except Exception as e:
            print(f'  click failed: {e}')
        time.sleep(0.4)
        if capture_screens: screenshot('01_before_f10')
        if proc.poll() is not None:
            result['verdict'] = 'CRASH'
            result['exit_code'] = proc.returncode
            return result
        send_vk(win32con.VK_F10)
        time.sleep(1.0)
        if capture_screens: screenshot('02_after_f10')
        if proc.poll() is not None:
            result['verdict'] = 'CRASH'
            result['exit_code'] = proc.returncode
            result['phase'] = 'after_F10'
            return result

        # 3. Tab into the Filename: input field (typing in the file list
        # would only do single-char incremental jumps). Filename takes
        # printable chars one at a time. Our staged name has no backslash
        # (file is in cwd=bin/), so scancode-mode typing works cleanly.
        result['phase'] = 'tab_to_filename'
        send_vk(win32con.VK_TAB)
        time.sleep(0.3)
        if capture_screens: screenshot('02b_after_tab')
        type_string(file_name, interval=0.025)
        time.sleep(0.4)
        if capture_screens: screenshot('03_after_type')
        send_vk(win32con.VK_RETURN)
        time.sleep(0.8)
        if capture_screens: screenshot('04_after_enter')
        if proc.poll() is not None:
            result['verdict'] = 'CRASH'
            result['exit_code'] = proc.returncode
            result['phase'] = 'after_enter_in_picker'
            return result

        # 4. Confirmation dialog: "Do you want to load the file?" → Y / Enter
        send_vk(ord('Y'))
        time.sleep(0.2)
        send_vk(win32con.VK_RETURN)
        time.sleep(0.4)
        if capture_screens: screenshot('05_after_confirm')

        # 5. Poll for load completion / crash
        result['phase'] = 'wait_load'
        deadline = t0 + total_timeout
        loaded = False
        while time.time() < deadline:
            if proc.poll() is not None:
                result['verdict'] = 'CRASH'
                result['exit_code'] = proc.returncode
                result['elapsed_s'] = round(time.time() - t0, 2)
                return result
            t = title_of(hwnd) or ''
            result['title'] = t
            # Filename presence is a strong signal; Driver/song name in title also acceptable
            stem = Path(sf2_path).stem.lower()
            if stem in t.lower() or '.sf2' in t.lower():
                loaded = True
                break
            time.sleep(0.3)

        result['elapsed_s'] = round(time.time() - t0, 2)
        if loaded:
            result['verdict'] = 'PASS'
        else:
            result['verdict'] = 'NO_TITLE_CHANGE'
        return result
    finally:
        # Clean up staged test file
        try:
            if staged.exists():
                staged.unlink()
        except Exception:
            pass
        # Always tear down
        try:
            if proc.poll() is None:
                # Try graceful close (Alt+X / Esc), then kill
                try:
                    pyautogui.hotkey('alt', 'f4')
                except Exception:
                    pass
                time.sleep(0.4)
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=3)
        except Exception:
            pass
        # Capture stderr tail AND save full stderr for post-mortem
        try:
            stderr_f.flush(); stderr_f.seek(0)
            full = stderr_f.read()
            # Save full stderr alongside the file for inspection
            log_path = f'/tmp/sf2_load_{Path(sf2_path).stem}.log'
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(full)
            result['stderr_log'] = log_path
            result['stderr_tail'] = '\n'.join(full.splitlines()[-15:])
        except Exception:
            pass
        try:
            stderr_f.close(); stdout_f.close()
            os.unlink(stderr_f.name); os.unlink(stdout_f.name)
        except Exception:
            pass


def main(argv):
    if not argv:
        print(__doc__); sys.exit(1)
    rows = []
    for path in argv:
        if not os.path.exists(path):
            print(f'MISSING: {path}'); continue
        print(f'\n>>> {path}', flush=True)
        r = test_one(path)
        rows.append(r)
        print(f'  verdict={r["verdict"]:<14s} '
              f'phase={r["phase"]:<22s} '
              f'elapsed={r["elapsed_s"]:>5.1f}s '
              f'exit={r["exit_code"]} '
              f'title={r["title"]!r}')
        if r['stderr_tail']:
            for ln in r['stderr_tail'].splitlines()[:6]:
                print(f'  | {ln}')

    print('\n=== Summary ===')
    print(f'{"verdict":<16s} {"elapsed":>8s} {"file":<60s}')
    for r in rows:
        print(f'{r["verdict"]:<16s} {r["elapsed_s"]:>6.1f}s   {r["file"]:<60s}')


if __name__ == '__main__':
    main(sys.argv[1:])
