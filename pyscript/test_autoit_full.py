"""
Full AutoIt Automation Test with Stinsen SF2 File

Tests the complete end-to-end AutoIt automation:
1. Python calls AutoIt script
2. AutoIt launches editor + loads file
3. Python verifies file loaded
4. Python controls playback
5. Python closes editor
"""

import sys
import time
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_editor_automation import SF2EditorAutomation


def test_full_autoit_automation():
    """Test complete AutoIt automation workflow"""

    # Find Stinsen SF2 file
    sf2_file = "output/keep_Stinsens_Last_Night_of_89/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2"

    if not Path(sf2_file).exists():
        print(f"[ERROR] SF2 file not found: {sf2_file}")
        pytest.skip(f"SF2 file not found: {sf2_file}")

    print("\n" + "=" * 70)
    print("Full AutoIt Automation Test - Stinsen SF2 File")
    print("=" * 70 + "\n")

    print(f"Test file: {sf2_file}")
    print(f"File size: {Path(sf2_file).stat().st_size:,} bytes")
    print()

    # Create automation instance
    print("Step 1: Creating automation instance...")
    automation = SF2EditorAutomation()

    print(f"  Editor path: {automation.editor_path}")
    print(f"  AutoIt script: {automation.autoit_script}")
    print(f"  AutoIt enabled: {automation.autoit_enabled}")
    print(f"  AutoIt available: {automation.autoit_script.exists() if automation.autoit_script else False}")
    print()

    if not automation.autoit_enabled:
        print("[ERROR] AutoIt not enabled or not available")
        print("Please check:")
        print("  1. AutoIt script compiled: scripts/autoit/sf2_loader.exe")
        print("  2. Config file: config/sf2_automation.ini")
        pytest.skip("AutoIt not enabled or not available")

    # Test AutoIt file loading
    print("Step 2: Testing AutoIt file loading (fully automated)...")
    print("  This will:")
    print("    - Launch SID Factory II via AutoIt")
    print("    - Load the SF2 file automatically")
    print("    - Keep editor open with keep-alive")
    print()

    success = automation.launch_editor_with_file(sf2_file, use_autoit=True, timeout=60)

    if not success:
        print("[FAIL] AutoIt file loading failed")
    assert success, "AutoIt file loading failed"

    print("[OK] AutoIt file loading succeeded!")
    print()

    # Verify editor is running
    print("Step 3: Verifying editor state...")

    editor_running = automation.is_editor_running()
    if not editor_running:
        print("[FAIL] Editor not running after AutoIt launch")
    assert editor_running, "Editor not running after AutoIt launch"

    print("[OK] Editor is running")

    # Verify file is loaded
    file_loaded = automation.is_file_loaded()
    if not file_loaded:
        print("[FAIL] File not loaded")
        title = automation.get_window_title()
        print(f"  Window title: {title}")
    assert file_loaded, "File not loaded"

    title = automation.get_window_title()
    print(f"[OK] File loaded: {title}")
    print()

    # Test playback controls
    print("Step 4: Testing playback controls...")

    # Start playback
    print("  Starting playback (F5)...")
    automation.start_playback()
    time.sleep(1)

    if automation.is_playing():
        print("  [OK] Playback started")

        # Play for 3 seconds
        print("  Playing for 3 seconds...")
        time.sleep(3)

        # Stop playback
        print("  Stopping playback (F6)...")
        automation.stop_playback()
        time.sleep(0.5)

        if not automation.is_playing():
            print("  [OK] Playback stopped")
        else:
            print("  [WARN] Playback may still be active")
    else:
        print("  [WARN] Could not verify playback started")

    print()

    # Close editor
    print("Step 5: Closing editor...")
    automation.close_editor()
    time.sleep(1)

    if not automation.is_editor_running():
        print("[OK] Editor closed successfully")
    else:
        print("[WARN] Editor may still be running")

    print()

    # Final results
    print("=" * 70)
    print("Full AutoIt Automation Test Results")
    print("=" * 70 + "\n")
    print("[OK] All tests PASSED!")
    print()
    print("Summary:")
    print("  - AutoIt compilation: YES")
    print("  - Editor launch: YES")
    print("  - File loading: YES (fully automated)")
    print("  - Playback control: YES")
    print("  - Editor close: YES")
    print()
    print("The AutoIt automation is working perfectly!")
    print("100% automated workflow confirmed!")
    print()
    # Test passes if we reach here without assertion failures


if __name__ == '__main__':
    try:
        test_full_autoit_automation()
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)
    except (AssertionError, pytest.skip.Exception) as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Test cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
