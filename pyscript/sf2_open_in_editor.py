"""Launch SIDFactoryII with a given SF2 file F10-loaded, and LEAVE it running
for interactive use. Retries if the load crashes (heap-state-dependent).

Usage: py -3 pyscript/sf2_open_in_editor.py <file.sf2> [max_attempts]

This is the user-facing variant of sf2_load_test/sf2_load_retry: those
return after testing whether load works (and kill SF2II at the end);
this one leaves the editor open so you can actually edit/play.

Strategy: spawn a DETACHED SF2II via Start-Process (so it survives this
Python process exiting), drive F10-load via SendInput, then verify the
process is alive a few seconds later. If crashed, kill remnants and retry.
Each detached spawn is an independent draw against the ~73% per-attempt
success rate, so retries are required even after the harness confirms
the file is loadable in principle.
"""
import sys
import time
import subprocess
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sf2_load_test as harness

EDITOR = harness.EDITOR  # bin/SIDFactoryII.exe (x64 stock build)
ALIVE_CHECK_SECONDS = 4.0


def _spawn_detached(exe: str, cwd: str) -> int:
    """subprocess.Popen with DETACHED_PROCESS so the child outlives this
    Python process AND inherits foreground rights (which Start-Process via
    PowerShell loses, breaking SetForegroundWindow on every attempt)."""
    DETACH = 0x00000008  # DETACHED_PROCESS
    NEW_PG = 0x00000200  # CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(
        [exe, "--skip-intro"],
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=DETACH | NEW_PG,
        close_fds=True,
    )
    return proc.pid


def _is_alive(pid: int) -> bool:
    rc = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) "
         f"{{ Write-Output 'ALIVE' }} else {{ Write-Output 'DEAD' }}"],
        capture_output=True, text=True,
    )
    return rc.stdout.strip() == "ALIVE"


def _kill_pid(pid: int):
    subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"Stop-Process -Id {pid} -Force -ErrorAction SilentlyContinue"],
        capture_output=True,
    )


def _find_window_for_pid(pid: int, timeout: float = 8.0):
    import win32gui
    import win32process
    deadline = time.time() + timeout
    while time.time() < deadline:
        hits = []
        def cb(h, _):
            try:
                _, wpid = win32process.GetWindowThreadProcessId(h)
                if wpid == pid and win32gui.IsWindowVisible(h) \
                        and win32gui.GetWindowText(h):
                    hits.append(h)
            except Exception:
                pass
        win32gui.EnumWindows(cb, None)
        if hits:
            return hits[0]
        time.sleep(0.2)
    return None


def _drive_f10_load(hwnd, filename: str):
    import win32gui
    import win32con
    import pyautogui
    try:
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass  # focus-stealing prevention; the click below forces it
    time.sleep(0.4)
    rect = win32gui.GetWindowRect(hwnd)
    pyautogui.click((rect[0] + rect[2]) // 2, rect[1] + 20)
    time.sleep(0.4)
    harness.send_vk(win32con.VK_F10)
    time.sleep(1.0)
    harness.send_vk(win32con.VK_TAB)
    time.sleep(0.3)
    harness.type_string(filename)
    time.sleep(0.4)
    harness.send_vk(win32con.VK_RETURN)
    time.sleep(0.8)
    harness.send_vk(ord("Y"))
    time.sleep(0.2)
    harness.send_vk(win32con.VK_RETURN)


def _get_window_title(pid: int) -> str:
    import win32gui
    import win32process
    titles = []
    def cb(h, _):
        try:
            _, wpid = win32process.GetWindowThreadProcessId(h)
            if wpid == pid and win32gui.IsWindowVisible(h):
                t = win32gui.GetWindowText(h)
                if t:
                    titles.append(t)
        except Exception:
            pass
    win32gui.EnumWindows(cb, None)
    return titles[0] if titles else ""


def _try_one_detached_load(staged_name: str, bin_dir: Path) -> tuple[bool, int | None]:
    """Spawn detached, drive F10-load, return (loaded_alive, pid).

    A successful load requires both: (a) process alive after the wait window,
    and (b) window title contains the staged filename — otherwise the F10
    keystroke was suppressed (e.g. focus-stealing) and we'd hand the user
    an editor with the default file loaded."""
    pid = _spawn_detached(EDITOR, str(bin_dir))
    time.sleep(2.5)
    if not _is_alive(pid):
        return False, None
    hwnd = _find_window_for_pid(pid, timeout=6.0)
    if hwnd is None:
        _kill_pid(pid)
        return False, None
    try:
        _drive_f10_load(hwnd, staged_name)
    except Exception as e:
        print(f"    F10-load drive error: {e}", file=sys.stderr)
        _kill_pid(pid)
        return False, None
    time.sleep(ALIVE_CHECK_SECONDS)
    if not _is_alive(pid):
        return False, None
    title = _get_window_title(pid)
    if staged_name not in title:
        # Editor is alive but didn't load our file — treat as failure
        print(f"    F10-load did not take effect (title={title!r})",
              file=sys.stderr)
        _kill_pid(pid)
        return False, None
    return True, pid


def open_in_editor(sf2_path: str, max_attempts: int = 15) -> bool:
    abs_path = str(Path(sf2_path).absolute())
    if not Path(abs_path).exists():
        print(f"ERROR: file not found: {sf2_path}", file=sys.stderr)
        return False

    bin_dir = Path(EDITOR).parent
    staged_name = f"_load_{Path(sf2_path).stem[:24]}.sf2"
    staged = bin_dir / staged_name
    shutil.copyfile(abs_path, staged)

    for attempt in range(1, max_attempts + 1):
        print(f"Attempt {attempt}/{max_attempts}: spawning detached SF2II + F10-loading...",
              flush=True)
        ok, pid = _try_one_detached_load(staged_name, bin_dir)
        if ok:
            print(f"\n  SUCCESS: SIDFactoryII PID {pid} is running with "
                  f"{Path(sf2_path).name} loaded.", flush=True)
            print(f"  Close the editor manually when done.", flush=True)
            return True
        print(f"  attempt {attempt}: crashed - retrying", flush=True)
        time.sleep(0.5)

    print(f"FAIL: all {max_attempts} attempts crashed", file=sys.stderr)
    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    max_attempts = int(sys.argv[2]) if len(sys.argv) >= 3 else 15
    ok = open_in_editor(sys.argv[1], max_attempts=max_attempts)
    sys.exit(0 if ok else 1)
