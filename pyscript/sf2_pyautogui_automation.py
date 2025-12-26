"""
SID Factory II PyAutoGUI Automation Module

Alternative to AutoIt using pure Python GUI automation.
Combines CLI --skip-intro flag with PyAutoGUI for window control.

Author: SIDM2 Project
Version: 1.0.0
Date: 2025-12-26
"""

import pyautogui
import pygetwindow as gw
import subprocess
import time
import os
from pathlib import Path
from typing import Optional, Tuple


class SF2PyAutoGUIAutomation:
    """PyAutoGUI-based automation for SID Factory II editor"""

    def __init__(self, editor_path: Optional[str] = None):
        """
        Initialize PyAutoGUI automation

        Args:
            editor_path: Path to SIDFactoryII.exe (default: bin/SIDFactoryII.exe)
        """
        if editor_path is None:
            # Default to bin/SIDFactoryII.exe
            project_root = Path(__file__).parent.parent
            editor_path = project_root / "bin" / "SIDFactoryII.exe"

        self.editor_path = Path(editor_path)
        if not self.editor_path.exists():
            raise FileNotFoundError(f"Editor not found: {self.editor_path}")

        self.process = None
        self.window = None

        # PyAutoGUI configuration
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        pyautogui.PAUSE = 0.1  # Short pause between actions

    def launch_with_file(self, sf2_path: str, skip_intro: bool = True,
                        timeout: int = 10) -> bool:
        """
        Launch editor with SF2 file using CLI + PyAutoGUI

        Args:
            sf2_path: Path to SF2 file to load
            skip_intro: Use --skip-intro flag (recommended: True)
            timeout: Seconds to wait for window (default: 10)

        Returns:
            True if launched successfully, False otherwise
        """
        sf2_path = Path(sf2_path)
        if not sf2_path.exists():
            print(f"[FAIL] SF2 file not found: {sf2_path}")
            return False

        # Build command
        cmd = [str(self.editor_path)]
        if skip_intro:
            cmd.append("--skip-intro")
        cmd.append(str(sf2_path.absolute()))

        print(f"[INFO] Launching editor...")
        print(f"  Command: {' '.join(cmd)}")

        # Launch process
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.editor_path.parent
            )
        except Exception as e:
            print(f"[FAIL] Failed to launch: {e}")
            return False

        print(f"[INFO] Process started (PID: {self.process.pid})")

        # Wait for window
        print(f"[INFO] Waiting for window (timeout: {timeout}s)...")
        window = self.wait_for_window("SID Factory II", timeout)

        if window is None:
            print(f"[FAIL] Window not found within {timeout} seconds")
            if self.process.poll() is not None:
                print(f"[FAIL] Process already exited (code: {self.process.returncode})")
            return False

        self.window = window
        print(f"[OK] Window found: {window.title}")

        # Verify file loaded
        time.sleep(0.5)
        if ".sf2" in window.title.lower() or sf2_path.stem in window.title:
            print(f"[OK] File appears to be loaded: {window.title}")
            return True
        else:
            print(f"[WARN] File may not be loaded. Title: {window.title}")
            return True  # Return True anyway - window is open

    def wait_for_window(self, title_contains: str, timeout: int = 10) -> Optional[object]:
        """
        Wait for window with title containing specific text

        Args:
            title_contains: String that should be in window title
            timeout: Maximum seconds to wait

        Returns:
            Window object if found, None otherwise
        """
        start_time = time.time()
        last_check = 0

        while (time.time() - start_time) < timeout:
            # Get all windows
            windows = gw.getWindowsWithTitle(title_contains)

            if windows:
                # Return first match
                return windows[0]

            # Progress indicator every second
            elapsed = time.time() - start_time
            if elapsed - last_check >= 1.0:
                print(f"  Waiting... ({int(elapsed)}s/{timeout}s)")
                last_check = elapsed

            time.sleep(0.1)

        return None

    def is_window_open(self) -> bool:
        """Check if editor window is still open"""
        if self.window is None:
            return False

        try:
            # Check if window still exists
            return self.window.isActive or self.window.visible
        except:
            return False

    def activate_window(self) -> bool:
        """Bring editor window to foreground"""
        if self.window is None:
            print("[FAIL] No window to activate")
            return False

        try:
            self.window.activate()
            time.sleep(0.2)
            print("[OK] Window activated")
            return True
        except Exception as e:
            print(f"[FAIL] Could not activate window: {e}")
            return False

    def get_window_position(self) -> Optional[Tuple[int, int, int, int]]:
        """Get window position and size (x, y, width, height)"""
        if self.window is None:
            return None

        try:
            return (self.window.left, self.window.top,
                   self.window.width, self.window.height)
        except:
            return None

    def send_key(self, key: str, repeat: int = 1) -> bool:
        """
        Send keyboard input to editor

        Args:
            key: Key name (e.g., 'f5', 'f6', 'enter')
            repeat: Number of times to press (default: 1)

        Returns:
            True if sent successfully
        """
        if not self.activate_window():
            return False

        try:
            for _ in range(repeat):
                pyautogui.press(key)
                time.sleep(0.1)

            print(f"[OK] Sent key: {key} (x{repeat})")
            return True
        except Exception as e:
            print(f"[FAIL] Could not send key '{key}': {e}")
            return False

    def start_playback(self) -> bool:
        """Start playback (F5)"""
        print("[INFO] Starting playback (F5)...")
        return self.send_key('f5')

    def stop_playback(self) -> bool:
        """Stop playback (F6)"""
        print("[INFO] Stopping playback (F6)...")
        return self.send_key('f6')

    def close_editor(self) -> bool:
        """Close editor gracefully"""
        if self.window is None:
            print("[WARN] No window to close")
            return True

        try:
            self.window.close()
            time.sleep(0.5)
            print("[OK] Editor closed")
            return True
        except Exception as e:
            print(f"[WARN] Could not close window: {e}")

            # Try killing process
            if self.process and self.process.poll() is None:
                self.process.terminate()
                time.sleep(0.5)
                if self.process.poll() is None:
                    self.process.kill()
                print("[OK] Process terminated")

            return True

    def __del__(self):
        """Cleanup on deletion"""
        if self.process and self.process.poll() is None:
            self.process.terminate()


def demo_pyautogui_automation():
    """Demonstration of PyAutoGUI automation"""
    print("=" * 60)
    print("PyAutoGUI Automation Demo")
    print("=" * 60)
    print()

    # Find test file
    project_root = Path(__file__).parent.parent
    test_file = (project_root / "output" / "keep_Stinsens_Last_Night_of_89" /
                "Stinsens_Last_Night_of_89" / "New" /
                "Stinsens_Last_Night_of_89.sf2")

    if not test_file.exists():
        print(f"[FAIL] Test file not found: {test_file}")
        print("[INFO] Please provide a valid SF2 file path")
        return

    print(f"[INFO] Test file: {test_file.name}")
    print()

    # Create automation instance
    automation = SF2PyAutoGUIAutomation()

    # Launch with file
    print("Step 1: Launching editor with file...")
    if not automation.launch_with_file(test_file):
        print("[FAIL] Launch failed")
        return

    print()
    print("Step 2: Verifying window state...")
    if automation.is_window_open():
        pos = automation.get_window_position()
        if pos:
            print(f"[OK] Window open at: ({pos[0]}, {pos[1]}) size: {pos[2]}x{pos[3]}")
    else:
        print("[FAIL] Window is not open")
        return

    print()
    print("Step 3: Testing playback control...")

    # Start playback
    automation.start_playback()
    print("[INFO] Playing for 3 seconds...")
    time.sleep(3)

    # Stop playback
    automation.stop_playback()

    print()
    print("Step 4: Keeping window open for 10 seconds...")
    print("[INFO] You can interact with the editor manually")
    print("[INFO] Move mouse to top-left corner to abort (FAILSAFE)")

    for i in range(10):
        if not automation.is_window_open():
            print(f"[WARN] Window closed after {i} seconds")
            break
        time.sleep(1)
        print(f"  {10-i} seconds remaining...")

    print()
    print("Step 5: Closing editor...")
    automation.close_editor()

    print()
    print("=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    demo_pyautogui_automation()
