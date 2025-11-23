#!/usr/bin/env python3
"""
Automated SF2 Editor Validation Test

Tests converted SF2 files by:
1. Launching SID Factory II editor
2. Sending space key to start playback
3. Capturing screenshot
4. Killing process
5. Generating validation report

Usage:
    python test_sf2_editor.py                    # Test all SF2 files
    python test_sf2_editor.py SF2/Angular.sf2    # Test specific file
    python test_sf2_editor.py --convert-first    # Convert SID files first

Requirements:
    pip install -r requirements-test.txt
"""

import os
import sys
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional

# Check for required modules
try:
    import pyautogui
    import pygetwindow as gw
    from PIL import Image
    import win32gui
    import win32con
    import win32api
    import ctypes
    from ctypes import wintypes
except ImportError as e:
    print(f"Missing required module: {e}")
    print("Install with: pip install -r requirements-test.txt")
    sys.exit(1)

# SendInput structures for low-level keyboard input
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_SPACE = 0x20

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
    ]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type", wintypes.DWORD),
        ("_input", _INPUT)
    ]

def send_key(vk_code):
    """Send a key press using SendInput."""
    # Key down
    x = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk_code))
    ctypes.windll.user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))
    time.sleep(0.05)
    # Key up
    x = INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=vk_code, dwFlags=KEYEVENTF_KEYUP))
    ctypes.windll.user32.SendInput(1, ctypes.byref(x), ctypes.sizeof(x))

# Configuration
EDITOR_PATH = r"C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\artifacts"
EDITOR_EXE = "SIDFactoryII.exe"
SCREENSHOT_DIR = Path("SF2/screenshots")
SF2_DIR = Path("SF2")
SID_DIR = Path("SID")

# Timing configuration
EDITOR_LOAD_DELAY = 3.0  # Seconds to wait for editor to load
SPLASH_DISMISS_DELAY = 1.0  # Seconds to wait after dismissing splash screen (if enabled)
PLAY_DELAY = 0.5  # Seconds to wait after pressing space to play
SCREENSHOT_DELAY = 0.3  # Seconds to wait before screenshot
SKIP_INTRO = True  # Set to True if Editor.Skip.Intro = 1 in config.ini


class SF2EditorValidator:
    """Validates SF2 files by loading them in SID Factory II editor."""

    def __init__(self, editor_path: str = EDITOR_PATH, load_delay: float = EDITOR_LOAD_DELAY,
                 splash_delay: float = SPLASH_DISMISS_DELAY, skip_intro: bool = SKIP_INTRO):
        self.editor_path = Path(editor_path)
        self.editor_exe = self.editor_path / EDITOR_EXE
        self.screenshot_dir = SCREENSHOT_DIR
        self.results: List[Tuple[str, bool, str, Optional[str]]] = []
        self.load_delay = load_delay
        self.splash_delay = splash_delay
        self.skip_intro = skip_intro

        # Create screenshot directory
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Verify editor exists
        if not self.editor_exe.exists():
            raise FileNotFoundError(f"Editor not found: {self.editor_exe}")

    def validate_sf2(self, sf2_path: Path) -> Tuple[bool, str, Optional[str]]:
        """
        Validate a single SF2 file by loading it in the editor.

        Returns:
            Tuple of (success, message, screenshot_path)
        """
        sf2_path = Path(sf2_path).resolve()

        if not sf2_path.exists():
            return False, f"File not found: {sf2_path}", None

        print(f"  Validating: {sf2_path.name}")

        process = None
        screenshot_path = None

        try:
            # Launch editor from its directory
            process = subprocess.Popen(
                [str(self.editor_exe), str(sf2_path)],
                cwd=str(self.editor_path),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Wait for editor to load
            print(f"    Waiting for editor to load...")
            time.sleep(self.load_delay)

            # Check if process is still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                return False, f"Editor exited immediately: {stderr.decode()}", None

            # Try to find the editor window and force it to foreground
            hwnd = self._find_editor_hwnd()
            if hwnd:
                try:
                    # Get window rect and click on it to give it focus
                    rect = win32gui.GetWindowRect(hwnd)
                    center_x = (rect[0] + rect[2]) // 2
                    center_y = (rect[1] + rect[3]) // 2

                    # Use Alt key trick to allow SetForegroundWindow
                    pyautogui.press('alt')
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    time.sleep(0.3)

                    # Click twice on the window to ensure focus
                    pyautogui.click(center_x, center_y)
                    time.sleep(0.2)
                    pyautogui.click(center_x, center_y)
                    time.sleep(0.3)

                    print(f"    Window focused (hwnd={hwnd})")
                except Exception as e:
                    print(f"    Window activation failed: {e}")
            else:
                print(f"    Warning: Could not find editor window")

            # Re-click and send keys - need to ensure focus is maintained
            if hwnd:
                rect = win32gui.GetWindowRect(hwnd)
                center_x = (rect[0] + rect[2]) // 2
                center_y = (rect[1] + rect[3]) // 2
                pyautogui.click(center_x, center_y)
                time.sleep(0.1)

            # Dismiss splash screen if not skipped in config
            if not self.skip_intro:
                print(f"    Dismissing splash screen...")
                pyautogui.press('space')
                time.sleep(self.splash_delay)

                # Re-click to maintain focus
                if hwnd:
                    pyautogui.click(center_x, center_y)
                    time.sleep(0.1)

            # Send space key to start playback
            print(f"    Starting playback...")
            pyautogui.press('space')
            time.sleep(PLAY_DELAY)

            # Capture screenshot
            print(f"    Capturing screenshot...")
            time.sleep(SCREENSHOT_DELAY)
            screenshot_path = self._capture_screenshot(sf2_path.stem)

            if screenshot_path:
                print(f"    Screenshot saved: {screenshot_path}")
                return True, "Successfully loaded and captured", str(screenshot_path)
            else:
                return True, "Loaded but screenshot failed", None

        except Exception as e:
            return False, f"Error: {str(e)}", None

        finally:
            # Kill the editor process
            if process and process.poll() is None:
                print(f"    Terminating editor...")
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()

    def _find_editor_window(self):
        """Find the SID Factory II window."""
        try:
            windows = gw.getWindowsWithTitle('SID Factory II')
            if windows:
                return windows[0]
            # Also try partial match
            for win in gw.getAllWindows():
                if 'SIDFactory' in win.title or 'SF2' in win.title:
                    return win
        except Exception:
            pass
        return None

    def _find_editor_hwnd(self):
        """Find the SID Factory II window handle using win32."""
        result = []

        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if 'SID Factory II' in title or 'SIDFactory' in title:
                    result.append(hwnd)
            return True

        win32gui.EnumWindows(enum_callback, None)
        return result[0] if result else None

    def _capture_screenshot(self, name: str) -> Optional[str]:
        """Capture screenshot and save to file."""
        try:
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{timestamp}.png"
            filepath = self.screenshot_dir / filename

            # Try to capture just the editor window
            window = self._find_editor_window()
            if window:
                try:
                    # Get window region
                    left, top, width, height = window.left, window.top, window.width, window.height
                    screenshot = pyautogui.screenshot(region=(left, top, width, height))
                except Exception:
                    # Fall back to full screen
                    screenshot = pyautogui.screenshot()
            else:
                # Full screen capture
                screenshot = pyautogui.screenshot()

            screenshot.save(str(filepath))
            return str(filepath)

        except Exception as e:
            print(f"    Screenshot error: {e}")
            return None

    def validate_all(self, sf2_files: List[Path]) -> List[Tuple[str, bool, str, Optional[str]]]:
        """Validate multiple SF2 files."""
        self.results = []

        for sf2_path in sf2_files:
            success, message, screenshot = self.validate_sf2(sf2_path)
            self.results.append((str(sf2_path), success, message, screenshot))

        return self.results

    def generate_report(self, output_path: str = "SF2/validation_report.html") -> str:
        """Generate HTML validation report with screenshots."""

        passed = sum(1 for _, success, _, _ in self.results if success)
        total = len(self.results)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>SF2 Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #e0e0e0; }}
        h1 {{ color: #4fc3f7; }}
        .summary {{ background: #2a2a2a; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .result {{ background: #2a2a2a; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid; }}
        .pass {{ border-color: #4caf50; }}
        .fail {{ border-color: #f44336; }}
        .filename {{ font-weight: bold; color: #4fc3f7; }}
        .message {{ color: #bbb; margin: 5px 0; }}
        .screenshot {{ max-width: 100%; margin-top: 10px; border: 1px solid #444; }}
        .timestamp {{ color: #888; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>SF2 Editor Validation Report</h1>
    <div class="summary">
        <strong>Summary:</strong> {passed}/{total} files passed<br>
        <span class="timestamp">Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>
    </div>
"""

        for filepath, success, message, screenshot in self.results:
            status_class = "pass" if success else "fail"
            status_text = "✓ PASS" if success else "✗ FAIL"
            filename = Path(filepath).name

            html += f"""
    <div class="result {status_class}">
        <div class="filename">{filename} - {status_text}</div>
        <div class="message">{message}</div>
"""

            if screenshot and Path(screenshot).exists():
                # Use relative path for HTML
                rel_path = Path(screenshot).name
                html += f'        <img class="screenshot" src="screenshots/{rel_path}" alt="{filename}">\n'

            html += "    </div>\n"

        html += """
</body>
</html>
"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        return output_path


def convert_sid_files():
    """Convert all SID files to SF2."""
    from sid_to_sf2 import convert_sid_to_sf2

    sid_files = list(SID_DIR.glob("*.sid"))
    print(f"Converting {len(sid_files)} SID files...")

    for sid_file in sid_files:
        sf2_file = SF2_DIR / f"{sid_file.stem}.sf2"
        print(f"  {sid_file.name} -> {sf2_file.name}")
        try:
            convert_sid_to_sf2(str(sid_file), str(sf2_file))
        except Exception as e:
            print(f"    Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Validate SF2 files in SID Factory II editor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_sf2_editor.py                    # Test all SF2 files
  python test_sf2_editor.py SF2/Angular.sf2    # Test specific file
  python test_sf2_editor.py --convert-first    # Convert SID files first
  python test_sf2_editor.py --editor-path "C:\\path\\to\\artifacts"
  python test_sf2_editor.py --load-delay 5.0   # Slower systems
        """
    )
    parser.add_argument('files', nargs='*', help='SF2 files to validate (default: all in SF2/)')
    parser.add_argument('--convert-first', action='store_true', help='Convert SID files before validation')
    parser.add_argument('--no-report', action='store_true', help='Skip HTML report generation')
    parser.add_argument('--editor-path', type=str, default=EDITOR_PATH,
                       help=f'Path to SID Factory II artifacts folder (default: {EDITOR_PATH})')
    parser.add_argument('--load-delay', type=float, default=EDITOR_LOAD_DELAY,
                       help=f'Seconds to wait for editor to load (default: {EDITOR_LOAD_DELAY})')
    parser.add_argument('--splash-delay', type=float, default=SPLASH_DISMISS_DELAY,
                       help=f'Seconds to wait after dismissing splash (default: {SPLASH_DISMISS_DELAY})')
    parser.add_argument('--skip-intro', action='store_true', default=SKIP_INTRO,
                       help='Skip intro screen (set Editor.Skip.Intro=1 in config.ini)')
    parser.add_argument('--no-skip-intro', action='store_true',
                       help='Do not skip intro screen (dismiss with space key)')
    args = parser.parse_args()

    # Handle skip-intro flags
    skip_intro = args.skip_intro and not args.no_skip_intro

    print("=" * 60)
    print("SF2 Editor Validation Test")
    print("=" * 60)

    # Convert SID files if requested
    if args.convert_first:
        convert_sid_files()
        print()

    # Get list of SF2 files to validate
    if args.files:
        sf2_files = [Path(f) for f in args.files]
    else:
        sf2_files = sorted(SF2_DIR.glob("*.sf2"))

    if not sf2_files:
        print("No SF2 files found to validate")
        return 1

    print(f"\nValidating {len(sf2_files)} SF2 files:\n")

    try:
        validator = SF2EditorValidator(
            editor_path=args.editor_path,
            load_delay=args.load_delay,
            splash_delay=args.splash_delay,
            skip_intro=skip_intro
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    # Validate all files
    results = validator.validate_all(sf2_files)

    # Print summary
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)

    passed = 0
    for filepath, success, message, screenshot in results:
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {Path(filepath).name}: {message}")
        if success:
            passed += 1

    print(f"\nTotal: {passed}/{len(results)} passed")

    # Generate report
    if not args.no_report and results:
        report_path = validator.generate_report()
        print(f"\nReport generated: {report_path}")

    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
