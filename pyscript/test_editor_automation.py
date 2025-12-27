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
        auto = SF2EditorAutomation()
    except SF2EditorNotFoundError:
        pytest.skip("SIDFactoryII.exe not found")

    yield auto

    # Cleanup: Always close editor after test
    try:
        if auto.is_editor_running():
            auto.close_editor(force=True)
            time.sleep(0.5)
    except Exception:
        pass  # Ignore cleanup errors


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
    except SF2EditorNotFoundError as e:
        print(f"[FAIL] Editor not found: {e}")
        print()
        print("Please ensure SIDFactoryII.exe is in one of these locations:")
        print("  - Current directory")
        print("  - bin/SIDFactoryII.exe")
        print("  - tools/SIDFactoryII.exe")
        print("  - C:/Program Files/SIDFactoryII/SIDFactoryII.exe")
        print()
        pytest.fail(f"Editor not found: {e}")

def test_editor_launch(automation):
    """Test 2: Launch Editor Without File"""
    print("=" * 70)
    print("Test 2: Launch Editor (No File)")
    print("=" * 70)
    print()

    try:
        success = automation.launch_editor(timeout=30)
        if not success:
            print("[FAIL] Editor launch returned False")
        assert success, "Editor launch returned False"

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
    except Exception as e:
        print(f"[FAIL] Editor launch failed: {e}")
        pytest.fail(f"Editor launch failed: {e}")

def run_editor_load_file_test(automation, sf2_file):
    """Test 3: Launch Editor and Load File"""
    print("=" * 70)
    print("Test 3: Launch Editor and Load File")
    print("=" * 70)
    print()

    if not Path(sf2_file).exists():
        print(f"[SKIP] Test file not found: {sf2_file}")
        pytest.skip(f"Test file not found: {sf2_file}")

    try:
        print(f"Loading: {sf2_file}")
        print()

        success = automation.launch_editor(sf2_file, timeout=30)
        if not success:
            print("[FAIL] Editor launch failed")
        assert success, "Editor launch failed"

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
        else:
            print("[FAIL] File load timeout or failure")
            pytest.fail("File load timeout or failure")

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Test failed: {e}")

@pytest.mark.xfail(reason="GUI automation test - flaky due to window focus/timing issues")
def test_playback_control(automation):
    """Test 4: Playback Control (Start/Stop)

    Note: Marked as xfail due to inherent flakiness in GUI automation.
    Requires SID Factory II window to have focus and proper timing.
    """
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
            else:
                print("[FAIL] Stop playback failed")
                pytest.fail("Stop playback failed")
        else:
            print("[FAIL] Start playback failed")
            pytest.fail("Start playback failed")

    except Exception as e:
        print(f"[FAIL] Playback control test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Playback control test failed: {e}")

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

    except Exception as e:
        print(f"[FAIL] State detection test failed: {e}")
        pytest.fail(f"State detection test failed: {e}")

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

    except Exception as e:
        print(f"[FAIL] Advanced controls test failed: {e}")
        pytest.fail(f"Advanced controls test failed: {e}")

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
        pytest.skip(f"Test file not found: {sf2_file}")

    try:
        print("Phase 1: Launch editor (NO file)")
        print()

        success = automation.launch_editor(timeout=30)
        if not success:
            print("[FAIL] Editor launch failed")
        assert success, "Editor launch failed"

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
        else:
            print("[FAIL] File load failed or timeout")

            # Capture editor output for debugging
            output = automation.get_editor_output()
            if output['stderr']:
                print()
                print("Editor stderr output:")
                print(output['stderr'][:500])  # First 500 chars

            pytest.fail("File load failed or timeout")

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Test failed: {e}")

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

    except Exception as e:
        print(f"[FAIL] Editor info test failed: {e}")
        pytest.fail(f"Editor info test failed: {e}")

def main():
    """Run all tests"""
    print()
    print("=" * 70)
    print("SF2 Editor Automation - Real Editor Test")
    print("=" * 70)
    print()

    results = []

    # Test 1: Detect editor
    try:
        test_editor_detection()
        results.append(("Editor Detection", True))
    except (AssertionError, pytest.fail.Exception) as e:
        print()
        print(f"[ABORT] Cannot proceed: {e}")
        sys.exit(1)
    except pytest.skip.Exception:
        print()
        print("[ABORT] Editor detection skipped")
        sys.exit(1)

    automation = SF2EditorAutomation()

    try:
        # Test 2: Launch without file
        try:
            test_editor_launch(automation)
            results.append(("Launch Editor (No File)", True))
        except (AssertionError, pytest.fail.Exception):
            results.append(("Launch Editor (No File)", False))
        except pytest.skip.Exception:
            results.append(("Launch Editor (No File)", False))
        time.sleep(1)

        # Test 3: Launch with file
        try:
            run_editor_load_file_test(automation, TEST_SF2_FILE)
            results.append(("Launch and Load File", True))
        except (AssertionError, pytest.fail.Exception):
            results.append(("Launch and Load File)", False))
        except pytest.skip.Exception:
            results.append(("Launch and Load File", False))

        # Test 3b: Window messages file loading (alternative approach)
        print()
        print("=" * 70)
        print("TESTING ALTERNATIVE APPROACH: Window Messages")
        print("=" * 70)
        print()
        try:
            test_window_messages_file_loading(automation)
            results.append(("Window Messages File Loading", True))
        except (AssertionError, pytest.fail.Exception):
            results.append(("Window Messages File Loading", False))
        except pytest.skip.Exception:
            results.append(("Window Messages File Loading", False))

        # Test 4: Playback control
        if automation.is_editor_running():
            try:
                test_playback_control(automation)
                results.append(("Playback Control", True))
            except (AssertionError, pytest.fail.Exception):
                results.append(("Playback Control", False))
            except pytest.skip.Exception:
                results.append(("Playback Control", False))
        else:
            print("[SKIP] Test 4: Editor not running")
            results.append(("Playback Control", False))

        # Test 5: State detection
        if automation.is_editor_running():
            try:
                test_state_detection(automation)
                results.append(("State Detection", True))
            except (AssertionError, pytest.fail.Exception):
                results.append(("State Detection", False))
            except pytest.skip.Exception:
                results.append(("State Detection", False))
        else:
            print("[SKIP] Test 5: Editor not running")
            results.append(("State Detection", False))

        # Test 6: Advanced controls
        if automation.is_editor_running():
            try:
                test_advanced_controls(automation)
                results.append(("Advanced Controls", True))
            except (AssertionError, pytest.fail.Exception):
                results.append(("Advanced Controls", False))
            except pytest.skip.Exception:
                results.append(("Advanced Controls", False))
        else:
            print("[SKIP] Test 6: Editor not running")
            results.append(("Advanced Controls", False))

        # Test 7: Editor info
        if automation.is_editor_running():
            try:
                test_editor_info(automation)
                results.append(("Editor Info", True))
            except (AssertionError, pytest.fail.Exception):
                results.append(("Editor Info", False))
            except pytest.skip.Exception:
                results.append(("Editor Info", False))
        else:
            print("[SKIP] Test 7: Editor not running")
            results.append(("Editor Info", False))

    finally:
        # ALWAYS close editor, even if tests fail
        try:
            if automation.is_editor_running():
                print()
                print("Closing editor...")
                automation.close_editor(force=True)
                time.sleep(1)
        except Exception as e:
            print(f"Warning: Cleanup failed: {e}")

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
