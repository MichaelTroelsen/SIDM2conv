"""Manual test to verify F10 opens file dialog in SID Factory II

This script launches the editor and KEEPS IT OPEN so you can manually
verify what F10 does.
"""

import sys
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_editor_automation import SF2EditorAutomation
import win32gui
import win32con

def main():
    print("=" * 70)
    print("SID Factory II - Manual F10 Test")
    print("=" * 70)
    print()
    print("This test will:")
    print("1. Launch SID Factory II")
    print("2. Wait 2 seconds")
    print("3. Send F10 key via window message")
    print("4. KEEP THE EDITOR OPEN for you to verify")
    print()
    print("PLEASE WATCH: Does F10 open a file dialog?")
    print()
    input("Press Enter to start...")
    print()

    automation = SF2EditorAutomation()

    print("Launching editor...")
    if not automation.launch_editor(timeout=30):
        print("[FAIL] Could not launch editor")
        return

    print(f"[OK] Editor launched")
    print(f"  PID: {automation.pid}")
    print(f"  Window Handle: {automation.window_handle}")
    print(f"  Window Title: {automation.get_window_title()}")
    print()

    print("Waiting 2 seconds...")
    time.sleep(2)

    print("Checking if editor still running...")
    if not automation.is_editor_running():
        print("[ERROR] Editor already closed!")
        print()
        print("This confirms the editor closes immediately when launched")
        print("programmatically without user interaction.")
        return

    print(f"[OK] Editor still running")
    print()

    print("Sending F10 via window message...")
    try:
        win32gui.SendMessage(automation.window_handle, win32con.WM_KEYDOWN, win32con.VK_F10, 0)
        time.sleep(0.05)
        win32gui.SendMessage(automation.window_handle, win32con.WM_KEYUP, win32con.VK_F10, 0)
        print("[OK] F10 sent")
    except Exception as e:
        print(f"[ERROR] Failed to send F10: {e}")

    print()
    print("Waiting 2 seconds for dialog to appear...")
    time.sleep(2)

    print()
    print("Looking for dialog windows...")
    dialogs_found = []

    def find_dialogs(hwnd, param):
        try:
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                if title and len(title) > 0:  # Only windows with titles
                    owner = win32gui.GetWindow(hwnd, win32con.GW_OWNER)
                    dialogs_found.append({
                        'handle': hwnd,
                        'title': title,
                        'class': class_name,
                        'owner': owner,
                        'is_owned_by_editor': owner == automation.window_handle
                    })
        except:
            pass
        return True

    win32gui.EnumWindows(find_dialogs, None)

    print(f"Found {len(dialogs_found)} visible windows with titles:")
    print()
    for i, dialog in enumerate(dialogs_found[:20], 1):  # Show first 20
        print(f"  {i}. Title: {dialog['title']}")
        print(f"     Class: {dialog['class']}")
        print(f"     Handle: {dialog['handle']}")
        print(f"     Owned by editor: {dialog['is_owned_by_editor']}")
        print()

    print()
    print("=" * 70)
    print("MANUAL VERIFICATION")
    print("=" * 70)
    print()
    print("Please check:")
    print("1. Is the SID Factory II window still open?")
    print("2. Did a file dialog appear after F10 was sent?")
    print("3. If yes, what does the dialog title say?")
    print()
    input("Press Enter when done verifying...")

    print()
    print("Closing editor...")
    automation.close_editor(force=True)

    print()
    print("[DONE] Test complete")

if __name__ == '__main__':
    main()
