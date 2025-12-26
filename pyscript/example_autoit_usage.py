"""
Example: Using AutoIt Hybrid Automation

This script demonstrates how to use the AutoIt hybrid approach
for fully automated SF2 file validation.

Prerequisites:
1. AutoIt3 installed (https://www.autoitscript.com)
2. sf2_loader.exe compiled (run scripts/autoit/compile.bat)
3. SID Factory II installed
4. Test SF2 file available

Usage:
    python pyscript/example_autoit_usage.py
"""

import sys
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_editor_automation import SF2EditorAutomation


def example_auto_detect():
    """Example 1: Auto-detect mode (uses AutoIt if available)"""

    print("=" * 70)
    print("Example 1: Auto-Detect Mode")
    print("=" * 70)
    print()

    automation = SF2EditorAutomation()

    # Check if AutoIt is available
    if automation.autoit_enabled:
        print(f"✅ AutoIt mode available")
        print(f"   Script: {automation.autoit_script}")
    else:
        print(f"⚠️  AutoIt mode NOT available")
        print(f"   Expected: {automation.autoit_script}")
        print(f"   Will use manual workflow instead")

    print()

    # This will use AutoIt if available, manual workflow if not
    test_file = "output/test.sf2"  # Replace with your test file

    if not Path(test_file).exists():
        print(f"❌ Test file not found: {test_file}")
        print(f"   Please specify a valid SF2 file")
        return False

    print(f"Loading file: {test_file}")
    print()

    success = automation.launch_editor_with_file(test_file)

    if success:
        print()
        print("✅ File loaded successfully!")
        print()

        # Test playback
        print("Testing playback...")
        automation.start_playback()
        time.sleep(5)
        automation.stop_playback()
        print("✅ Playback test complete")
        print()

        # Cleanup
        automation.close_editor()
        print("✅ Editor closed")

        return True
    else:
        print()
        print("❌ File load failed")
        return False


def example_force_autoit():
    """Example 2: Force AutoIt mode"""

    print("=" * 70)
    print("Example 2: Force AutoIt Mode")
    print("=" * 70)
    print()

    automation = SF2EditorAutomation()

    if not automation.autoit_enabled:
        print("❌ AutoIt not available - cannot run this example")
        print()
        print("To enable AutoIt:")
        print("1. Install AutoIt3: https://www.autoitscript.com")
        print("2. Run: scripts/autoit/compile.bat")
        print("3. Verify: scripts/autoit/sf2_loader.exe exists")
        return False

    print("✅ Forcing AutoIt mode")
    print()

    test_file = "output/test.sf2"  # Replace with your test file

    if not Path(test_file).exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    print(f"Loading file: {test_file}")
    print()

    # Force AutoIt mode (even if disabled in config)
    success = automation.launch_editor_with_file(test_file, use_autoit=True)

    if success:
        print()
        print("✅ File loaded successfully via AutoIt!")

        # Get state
        state = automation.get_playback_state()
        print()
        print("Editor State:")
        for key, value in state.items():
            print(f"  {key}: {value}")

        # Cleanup
        automation.close_editor()

        return True
    else:
        print()
        print("❌ AutoIt file load failed")
        return False


def example_manual_mode():
    """Example 3: Force Manual mode"""

    print("=" * 70)
    print("Example 3: Force Manual Mode")
    print("=" * 70)
    print()

    automation = SF2EditorAutomation()

    print("ℹ️  Forcing manual mode (AutoIt will NOT be used)")
    print()

    test_file = "output/test.sf2"  # Replace with your test file

    if not Path(test_file).exists():
        print(f"❌ Test file not found: {test_file}")
        return False

    # Force manual mode
    success = automation.launch_editor_with_file(test_file, use_autoit=False)

    if success:
        print()
        print("✅ File loaded successfully via manual workflow!")

        # Cleanup
        automation.close_editor()

        return True
    else:
        print()
        print("❌ Manual file load failed")
        return False


def example_batch_validation():
    """Example 4: Batch validation with AutoIt"""

    print("=" * 70)
    print("Example 4: Batch Validation with AutoIt")
    print("=" * 70)
    print()

    automation = SF2EditorAutomation()

    if not automation.autoit_enabled:
        print("❌ AutoIt not available - batch validation requires AutoIt")
        print("   Install AutoIt and compile sf2_loader.exe")
        return False

    # List of files to validate
    files = [
        "output/file1.sf2",
        "output/file2.sf2",
        "output/file3.sf2",
    ]

    print(f"Validating {len(files)} files with AutoIt...")
    print()

    results = []

    for i, sf2_file in enumerate(files, 1):
        print(f"[{i}/{len(files)}] {Path(sf2_file).name}")

        if not Path(sf2_file).exists():
            print(f"  ⚠️  SKIP - File not found")
            results.append((sf2_file, False, "File not found"))
            continue

        # Load file with AutoIt
        success = automation.launch_editor_with_file(sf2_file, use_autoit=True)

        if success:
            # Test playback
            automation.start_playback()
            time.sleep(2)

            is_playing = automation.is_playing()
            automation.stop_playback()

            result = "PASS" if is_playing else "FAIL"
            results.append((sf2_file, is_playing, result))
            print(f"  ✅ {result}")

            # Close editor for next file
            automation.close_editor()
            time.sleep(1)
        else:
            results.append((sf2_file, False, "Load failed"))
            print(f"  ❌ FAIL - Load failed")

    # Summary
    print()
    print("=" * 70)
    print("Batch Validation Results")
    print("=" * 70)

    passed = sum(1 for _, success, _ in results if success)
    for sf2_file, success, message in results:
        status = "✅" if success else "❌"
        print(f"{status} {Path(sf2_file).name} - {message}")

    print()
    print(f"Results: {passed}/{len(results)} passed ({passed/len(results)*100:.0f}%)")

    return passed == len(results)


def main():
    """Run examples"""

    print()
    print("=" * 70)
    print("AutoIt Hybrid Automation - Usage Examples")
    print("=" * 70)
    print()

    print("Available examples:")
    print("1. Auto-detect mode (uses AutoIt if available)")
    print("2. Force AutoIt mode")
    print("3. Force manual mode")
    print("4. Batch validation with AutoIt")
    print()

    choice = input("Select example (1-4) or Enter to run all: ").strip()

    print()

    if choice == "1":
        example_auto_detect()
    elif choice == "2":
        example_force_autoit()
    elif choice == "3":
        example_manual_mode()
    elif choice == "4":
        example_batch_validation()
    else:
        # Run all examples
        example_auto_detect()
        print("\n" * 2)
        example_force_autoit()
        print("\n" * 2)
        # Skip manual mode (requires user input)
        # example_manual_mode()


if __name__ == '__main__':
    main()
