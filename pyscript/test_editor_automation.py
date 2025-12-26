#!/usr/bin/env python3
"""
Test SF2 Editor Automation with Real SIDFactoryII.exe

Tests the editor automation module with actual SID Factory II editor.
"""

import sys
import time
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_editor_automation import (
    SF2EditorAutomation,
    SF2EditorNotFoundError,
    SF2EditorTimeoutError,
    launch_editor_and_load,
    validate_sf2_with_editor
)

# Test file
TEST_SF2_FILE = "output/keep_Stinsens_Last_Night_of_89/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2"


@pytest.fixture
def automation():
    """Pytest fixture providing SF2EditorAutomation instance for tests"""
    try:
        return SF2EditorAutomation()
    except SF2EditorNotFoundError:
        pytest.skip("SIDFactoryII.exe not found")


def test_editor_detection():
    """Test 1: Detect SIDFactoryII.exe"""
    print("=" * 70)
    print("Test 1: Editor Detection")
    print("=" * 70)
    print()

    try:
        automation = SF2EditorAutomation()
        print(f"[PASS] Editor found: {automation.editor_path}")
        print()
        return True
    except SF2EditorNotFoundError as e:
        print(f"[FAIL] Editor not found: {e}")
        print()
        print("Please ensure SIDFactoryII.exe is in one of these locations:")
        print("  - Current directory")
        print("  - bin/SIDFactoryII.exe")
        print("  - tools/SIDFactoryII.exe")
        print("  - C:/Program Files/SIDFactoryII/SIDFactoryII.exe")
        print()
        return False

def test_editor_launch(automation):
    """Test 2: Launch Editor Without File"""
    print("=" * 70)
    print("Test 2: Launch Editor (No File)")
    print("=" * 70)
    print()

    try:
        success = automation.launch_editor(timeout=30)
        if success:
            print(f"[PASS] Editor launched successfully")
            print(f"  PID: {automation.pid}")
            print(f"  Window Handle: {automation.window_handle}")
            print(f"  Window Title: {automation.get_window_title()}")
            print()

            # Wait a bit
            time.sleep(2)

            # Close editor
            automation.close_editor()
            time.sleep(1)
            return True
        else:
            print("[FAIL] Editor launch returned False")
            return False
    except Exception as e:
        print(f"[FAIL] Editor launch failed: {e}")
        return False

def run_editor_load_file_test(automation, sf2_file):
    """Test 3: Launch Editor and Load File"""
    print("=" * 70)
    print("Test 3: Launch Editor and Load File")
    print("=" * 70)
    print()

    if not Path(sf2_file).exists():
        print(f"[SKIP] Test file not found: {sf2_file}")
        return False

    try:
        print(f"Loading: {sf2_file}")
        print()

        success = automation.launch_editor(sf2_file, timeout=30)
        if not success:
            print("[FAIL] Editor launch failed")
            return False

        print(f"[OK] Editor launched")
        print(f"  PID: {automation.pid}")
        print(f"  Window Handle: {automation.window_handle}")
        print()

        # Wait for file load
        print("Waiting for file to load...")
        if automation.wait_for_load(timeout=10):
            print(f"[PASS] File loaded successfully")
            print(f"  Window Title: {automation.get_window_title()}")
            print(f"  File Loaded: {automation.is_file_loaded()}")
            print()
            return True
        else:
            print("[FAIL] File load timeout or failure")
            return False

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_playback_control(automation):
    """Test 4: Playback Control (Start/Stop)"""
    print("=" * 70)
    print("Test 4: Playback Control")
    print("=" * 70)
    print()

    try:
        # Get initial state
        state = automation.get_playback_state()
        print("Initial State:")
        print(f"  Running: {state['running']}")
        print(f"  File Loaded: {state['file_loaded']}")
        print(f"  Playing: {state['playing']}")
        print(f"  Window Title: {state['window_title']}")
        print()

        # Start playback
        print("Starting playback (F5)...")
        if automation.start_playback():
            print("[OK] Playback start command sent")
            time.sleep(1)

            # Check if playing
            state = automation.get_playback_state()
            print(f"  Playing: {state['playing']}")
            print(f"  Window Title: {state['window_title']}")
            print()

            # Play for 5 seconds
            print("Playing for 5 seconds...")
            time.sleep(5)

            # Stop playback
            print("Stopping playback (F8)...")
            if automation.stop_playback():
                print("[OK] Playback stop command sent")
                time.sleep(1)

                # Check if stopped
                state = automation.get_playback_state()
                print(f"  Playing: {state['playing']}")
                print(f"  Window Title: {state['window_title']}")
                print()

                print("[PASS] Playback control test completed")
                return True
            else:
                print("[FAIL] Stop playback failed")
                return False
        else:
            print("[FAIL] Start playback failed")
            return False

    except Exception as e:
        print(f"[FAIL] Playback control test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_state_detection(automation):
    """Test 5: State Detection (Phase 3)"""
    print("=" * 70)
    print("Test 5: State Detection (Phase 3)")
    print("=" * 70)
    print()

    try:
        # Test window title retrieval
        title = automation.get_window_title()
        print(f"Window Title: {title}")
        print()

        # Test file loaded detection
        file_loaded = automation.is_file_loaded()
        print(f"File Loaded: {file_loaded}")
        print()

        # Test playback detection
        playing = automation.is_playing()
        print(f"Playing: {playing}")
        print()

        # Test complete state
        state = automation.get_playback_state()
        print("Complete State:")
        for key, value in state.items():
            print(f"  {key}: {value}")
        print()

        print("[PASS] State detection working")
        return True

    except Exception as e:
        print(f"[FAIL] State detection test failed: {e}")
        return False

def test_advanced_controls(automation):
    """Test 6: Advanced Controls (Phase 4)"""
    print("=" * 70)
    print("Test 6: Advanced Controls (Phase 4)")
    print("=" * 70)
    print()

    try:
        # Test position seeking (not yet implemented)
        print("Testing position seeking...")
        result = automation.set_position(5)
        print(f"  Result: {result} (expected: False - not implemented yet)")
        print()

        # Test volume control (not yet implemented)
        print("Testing volume control...")
        result = automation.set_volume(75)
        print(f"  Result: {result} (expected: False - not implemented yet)")
        print()

        # Test loop toggle (not yet implemented)
        print("Testing loop toggle...")
        result = automation.toggle_loop(True)
        print(f"  Result: {result} (expected: False - not implemented yet)")
        print()

        print("[PASS] Advanced control methods exist (implementation pending)")
        return True

    except Exception as e:
        print(f"[FAIL] Advanced controls test failed: {e}")
        return False

def test_window_messages_file_loading(automation):
    """Test 3b: Window Messages File Loading (Alternative Approach)"""
    print("=" * 70)
    print("Test 3b: Window Messages File Loading")
    print("=" * 70)
    print()

    print("NOTE: This test uses SendMessage API instead of keyboard events")
    print("      which may be faster and work even if window is closing.")
    print()

    # Close editor if running
    if automation.is_editor_running():
        print("Closing previous editor instance...")
        automation.close_editor(force=True)
        time.sleep(1)

    sf2_file = TEST_SF2_FILE

    if not Path(sf2_file).exists():
        print(f"[SKIP] Test file not found: {sf2_file}")
        return False

    try:
        print("Phase 1: Launch editor (NO file)")
        print()

        success = automation.launch_editor(timeout=30)
        if not success:
            print("[FAIL] Editor launch failed")
            return False

        print(f"[OK] Editor launched")
        print(f"  PID: {automation.pid}")
        print(f"  Window Handle: {automation.window_handle}")
        print()

        print("Phase 2: Load file via window messages (IMMEDIATELY after launch)")
        print(f"File: {sf2_file}")
        print()

        # Call load_file_via_window_messages IMMEDIATELY with skip_running_check
        success = automation.load_file_via_window_messages(
            sf2_file,
            timeout=15,
            skip_running_check=True  # CRITICAL: don't delay with checks
        )

        if success:
            print(f"[PASS] File loaded successfully via window messages!")
            print(f"  Window Title: {automation.get_window_title()}")
            print(f"  File Loaded: {automation.is_file_loaded()}")
            print()
            return True
        else:
            print("[FAIL] File load failed or timeout")

            # Capture editor output for debugging
            output = automation.get_editor_output()
            if output['stderr']:
                print()
                print("Editor stderr output:")
                print(output['stderr'][:500])  # First 500 chars

            return False

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_editor_info(automation):
    """Test 7: Get Editor Info"""
    print("=" * 70)
    print("Test 7: Editor Info")
    print("=" * 70)
    print()

    try:
        info = automation.get_editor_info()
        print("Editor Info:")
        for key, value in info.items():
            print(f"  {key}: {value}")
        print()

        print("[PASS] Editor info retrieved")
        return True

    except Exception as e:
        print(f"[FAIL] Editor info test failed: {e}")
        return False

def main():
    """Run all tests"""
    print()
    print("=" * 70)
    print("SF2 Editor Automation - Real Editor Test")
    print("=" * 70)
    print()

    results = []

    # Test 1: Detect editor
    if not test_editor_detection():
        print()
        print("[ABORT] Cannot proceed without SIDFactoryII.exe")
        sys.exit(1)

    automation = SF2EditorAutomation()

    # Test 2: Launch without file
    results.append(("Launch Editor (No File)", test_editor_launch(automation)))
    time.sleep(1)

    # Test 3: Launch with file
    results.append(("Launch and Load File", run_editor_load_file_test(automation, TEST_SF2_FILE)))

    # Test 3b: Window messages file loading (alternative approach)
    print()
    print("=" * 70)
    print("TESTING ALTERNATIVE APPROACH: Window Messages")
    print("=" * 70)
    print()
    results.append(("Window Messages File Loading", test_window_messages_file_loading(automation)))

    # Test 4: Playback control
    if automation.is_editor_running():
        results.append(("Playback Control", test_playback_control(automation)))
    else:
        print("[SKIP] Test 4: Editor not running")
        results.append(("Playback Control", False))

    # Test 5: State detection
    if automation.is_editor_running():
        results.append(("State Detection", test_state_detection(automation)))
    else:
        print("[SKIP] Test 5: Editor not running")
        results.append(("State Detection", False))

    # Test 6: Advanced controls
    if automation.is_editor_running():
        results.append(("Advanced Controls", test_advanced_controls(automation)))
    else:
        print("[SKIP] Test 6: Editor not running")
        results.append(("Advanced Controls", False))

    # Test 7: Editor info
    if automation.is_editor_running():
        results.append(("Editor Info", test_editor_info(automation)))
    else:
        print("[SKIP] Test 7: Editor not running")
        results.append(("Editor Info", False))

    # Close editor if still running
    if automation.is_editor_running():
        print()
        print("Closing editor...")
        automation.close_editor(force=True)
        time.sleep(1)

    # Summary
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print()

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")

    print()
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print()

    if passed == total:
        print("[SUCCESS] All tests passed!")
        sys.exit(0)
    else:
        print("[PARTIAL] Some tests failed")
        sys.exit(1)

if __name__ == '__main__':
    main()
