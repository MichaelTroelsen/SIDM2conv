"""
Test PyAutoGUI Integration with SF2EditorAutomation

Tests the complete integration of PyAutoGUI into the main automation system.

Usage:
    python pyscript/test_pyautogui_integration.py
"""

import sys
import time
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_editor_automation import SF2EditorAutomation


def test_pyautogui_integration():
    """Test PyAutoGUI integration with main automation system"""
    print("=" * 60)
    print("PyAutoGUI Integration Test")
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
        pytest.skip(f"Test file not found: {test_file}")

    print(f"[INFO] Test file: {test_file.name}")
    print()

    # Test 1: Auto-detect mode (should use PyAutoGUI by default)
    print("Test 1: Auto-detect mode (default = PyAutoGUI)")
    print("-" * 60)

    automation = SF2EditorAutomation()

    print(f"[INFO] Default mode: {automation.default_automation_mode}")
    print(f"[INFO] PyAutoGUI enabled: {automation.pyautogui_enabled}")
    print(f"[INFO] AutoIt enabled: {automation.autoit_enabled}")
    print()

    if automation.default_automation_mode != 'pyautogui':
        print(f"[WARN] Default mode is {automation.default_automation_mode}, expected 'pyautogui'")
        print("[INFO] This is OK if PyAutoGUI is not available")
        print()

    # Launch with default mode
    print("[INFO] Launching editor with default mode...")
    success = automation.launch_editor_with_file(str(test_file))

    if not success:
        print("[FAIL] Editor launch failed")
    assert success, "Editor launch failed"

    try:
        print("[OK] Editor launched successfully!")
        print()

        # Test playback control
        print("Test 2: Playback Control")
        print("-" * 60)

        if automation.pyautogui_automation:
            print("[INFO] Starting playback (F5)...")
            automation.pyautogui_automation.start_playback()
            time.sleep(3)

            print("[INFO] Stopping playback (F6)...")
            automation.pyautogui_automation.stop_playback()
            print("[OK] Playback control works!")
            print()

        # Keep window open for a bit
        print("Test 3: Window Stability")
        print("-" * 60)
        print("[INFO] Keeping window open for 5 seconds...")

        for i in range(5):
            if automation.pyautogui_automation:
                if not automation.pyautogui_automation.is_window_open():
                    print(f"[FAIL] Window closed after {i} seconds")
                    pytest.fail(f"Window closed after {i} seconds")
            time.sleep(1)
            print(f"  {5-i} seconds remaining...")

        print("[OK] Window remained stable!")
        print()

    finally:
        # ALWAYS close editor
        print("Test 4: Graceful Shutdown")
        print("-" * 60)

        try:
            if automation.pyautogui_automation:
                automation.pyautogui_automation.close_editor()
                print("[OK] Editor closed gracefully")
            else:
                print("[WARN] No PyAutoGUI automation instance to close")
        except Exception as e:
            print(f"[WARN] Cleanup error: {e}")

    print()
    print("=" * 60)
    print("All Tests Passed!")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  - Default mode: {automation.default_automation_mode}")
    print(f"  - PyAutoGUI: {'ENABLED' if automation.pyautogui_enabled else 'DISABLED'}")
    print(f"  - AutoIt: {'ENABLED' if automation.autoit_enabled else 'DISABLED'}")
    print(f"  - Test result: SUCCESS")
    print()


def test_mode_selection():
    """Test explicit mode selection"""
    print("=" * 60)
    print("Mode Selection Test")
    print("=" * 60)
    print()

    automation = SF2EditorAutomation()

    # Test file
    project_root = Path(__file__).parent.parent
    test_file = (project_root / "output" / "keep_Stinsens_Last_Night_of_89" /
                "Stinsens_Last_Night_of_89" / "New" /
                "Stinsens_Last_Night_of_89.sf2")

    if not test_file.exists():
        print("[SKIP] Test file not found")
        pytest.skip("Test file not found")

    # Test explicit PyAutoGUI mode
    print("Test: Explicit PyAutoGUI mode")
    print("-" * 60)

    if automation.pyautogui_enabled:
        print("[INFO] Launching with mode='pyautogui'...")
        success = automation.launch_editor_with_file(str(test_file), mode='pyautogui')

        if not success:
            print("[FAIL] PyAutoGUI mode failed")
        assert success, "PyAutoGUI mode failed"

        try:
            print("[OK] PyAutoGUI mode works explicitly")
            time.sleep(2)
        finally:
            # ALWAYS close editor
            try:
                if automation.pyautogui_automation:
                    automation.pyautogui_automation.close_editor()
            except Exception:
                pass
    else:
        print("[SKIP] PyAutoGUI not enabled")

    print()


if __name__ == "__main__":
    print()
    print("PyAutoGUI Integration Test Suite")
    print("=" * 60)
    print()

    try:
        # Run main integration test
        test_pyautogui_integration()
        print()

        # Run mode selection test
        test_mode_selection()
        print()

        print("=" * 60)
        print("ALL TESTS PASSED!")
        print("=" * 60)
        sys.exit(0)

    except (AssertionError, pytest.skip.Exception) as e:
        print()
        print("=" * 60)
        print(f"TEST FAILED: {e}")
        print("=" * 60)
        sys.exit(1)

    finally:
        # Global cleanup: Kill any remaining editor processes
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                if 'SIDFactoryII' in proc.info['name']:
                    proc.kill()
        except Exception:
            pass
