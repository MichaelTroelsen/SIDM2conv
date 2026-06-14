"""Launch SF2II argv-loaded with our SF2, focus the window, press PLAY, let it
run a few seconds, then kill and dump the captured stderr so we can see what SID
register writes (if any) SF2II's emulation produces during PLAYBACK (not just
the one-shot init analysis the argv-load harness sees)."""
import sys
import time
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pyscript"))
import sf2_load_test as H
import win32con

ROOT = Path(__file__).resolve().parent.parent
EDITOR = ROOT / "bin" / "SIDFactoryII.exe"
SF2 = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "out" / "galway_trace_song.sf2"
PLAYKEY = sys.argv[2] if len(sys.argv) > 2 else "f1"   # SF2II play-from-start
ERR = ROOT / "out" / "sf2ii_play.err"

KEYMAP = {"f1": win32con.VK_F1, "f2": win32con.VK_F2, "space": win32con.VK_SPACE}


def main():
    errf = open(ERR, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen([str(EDITOR), str(SF2), "--skip-intro"],
                            cwd=str(EDITOR.parent), stdout=subprocess.DEVNULL,
                            stderr=errf)
    try:
        hwnd = H.find_window_for_pid(proc.pid, timeout=8)
        if not hwnd:
            print("NO WINDOW"); return
        print(f"window: {H.title_of(hwnd)!r}")
        time.sleep(2.0)            # let it finish loading
        import win32gui, pyautogui
        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        rect = win32gui.GetWindowRect(hwnd)
        pyautogui.click((rect[0] + rect[2]) // 2, rect[1] + 20)
        time.sleep(0.4)
        print(f"pressing {PLAYKEY} to play...")
        H.send_vk(KEYMAP[PLAYKEY])
        time.sleep(3.5)            # play
        print("alive during play:", proc.poll() is None)
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=3)
        errf.close()


if __name__ == "__main__":
    main()
