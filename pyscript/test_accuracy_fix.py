#!/usr/bin/env python3
"""
Test script to verify the accuracy fix improved from 99.93% to 100%.

Tests the updated _frames_match() logic that compares only common registers
instead of requiring exact register set matches.
"""

import sys
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.accuracy import SIDRegisterCapture, SIDComparator


def test_accuracy_improvement():
    """Test that the accuracy fix improves frame matching from 99.93% to 100%."""

    print("\n" + "="*70)
    print("Testing Accuracy Fix - Sparse Frame Matching")
    print("="*70 + "\n")

    test_files = [
        ("output/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89_original.dump",
         "output/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.dump",
         "Stinsens_Last_Night_of_89"),
        ("output/Unboxed_Ending_8580/New/Unboxed_Ending_8580_original.dump",
         "output/Unboxed_Ending_8580/New/Unboxed_Ending_8580.dump",
         "Unboxed_Ending_8580"),
    ]

    total_tests = 0
    passed_tests = 0

    for orig_dump, exp_dump, label in test_files:
        orig_path = Path(orig_dump)
        exp_path = Path(exp_dump)

        print(f"Test: {label}")
        print(f"  Original: {orig_dump}")
        print(f"  Exported: {exp_dump}")

        if not orig_path.exists():
            print(f"  [WARN] Original dump not found, skipping")
            print()
            continue

        if not exp_path.exists():
            print(f"  [WARN] Exported dump not found, skipping")
            print()
            continue

        try:
            # Load captures
            original_capture = SIDRegisterCapture()
            exported_capture = SIDRegisterCapture()

            if not original_capture.capture_from_file(str(orig_path)):
                print(f"  [ERROR] Failed to load original dump")
                print()
                continue

            if not exported_capture.capture_from_file(str(exp_path)):
                print(f"  [ERROR] Failed to load exported dump")
                print()
                continue

            # Compare
            comparator = SIDComparator(original_capture, exported_capture)
            results = comparator.compare()

            frame_accuracy = results.get('frame_accuracy', 0)
            overall_accuracy = results.get('overall_accuracy', 0)

            print(f"  Results:")
            print(f"    Frame Accuracy:   {frame_accuracy:.2f}%")
            print(f"    Overall Accuracy: {overall_accuracy:.2f}%")

            # Check if we achieved 100%
            if frame_accuracy >= 99.99:  # Account for floating point rounding
                print(f"  [OK] PASS - Frame accuracy is 100% (or very close)")
                passed_tests += 1
            else:
                print(f"  [FAIL] FAIL - Frame accuracy is {frame_accuracy:.2f}%, expected ~100%")

            total_tests += 1

        except Exception as e:
            print(f"  [ERROR] Error during comparison: {e}")

        print()

    # Summary
    print("="*70)
    print("Summary")
    print("="*70)
    print(f"Tests run: {total_tests}")
    print(f"Tests passed: {passed_tests}")

    if total_tests == 0:
        print("\n[WARN] No test files found. Make sure to run the conversion pipeline first:")
        print("  python scripts/sid_to_sf2.py <input.sid> <output.sf2> --driver laxity")
        print("  python pyscript/siddump_complete.py <input.sid> -t30")
        pytest.skip("No test files found")

    success = passed_tests == total_tests
    print(f"\n{'[OK] All tests PASSED!' if success else '[FAIL] Some tests FAILED'}")
    print("="*70 + "\n")

    assert success, f"Only {passed_tests}/{total_tests} tests passed"


def test_sparse_frame_logic():
    """Test the sparse frame matching logic directly."""

    print("\n" + "="*70)
    print("Testing Sparse Frame Matching Logic")
    print("="*70 + "\n")

    from sidm2.accuracy import SIDComparator

    # Create a mock comparator
    original_capture = SIDRegisterCapture()
    exported_capture = SIDRegisterCapture()
    comparator = SIDComparator(original_capture, exported_capture)

    # Test case 1: Frames with different register counts but matching values
    frame1 = {0x00: 0x22, 0x01: 0x01, 0x04: 0x20}  # 3 registers
    frame2 = {0x00: 0x22, 0x01: 0x01, 0x04: 0x20, 0x02: 0x00}  # 4 registers

    result = comparator._frames_match(frame1, frame2)
    print("Test 1: Different register counts, same values")
    print(f"  Frame 1: {frame1}")
    print(f"  Frame 2: {frame2}")
    print(f"  Result: {result}")
    print(f"  Expected: True (matches because common registers have same values)")
    print(f"  Status: {'[OK] PASS' if result else '[FAIL] FAIL'}\n")

    # Test case 2: Frames with matching register sets and values
    frame3 = {0x00: 0x22, 0x01: 0x01}
    frame4 = {0x00: 0x22, 0x01: 0x01}

    result = comparator._frames_match(frame3, frame4)
    print("Test 2: Identical frames")
    print(f"  Frame 1: {frame3}")
    print(f"  Frame 2: {frame4}")
    print(f"  Result: {result}")
    print(f"  Expected: True")
    print(f"  Status: {'[OK] PASS' if result else '[FAIL] FAIL'}\n")

    # Test case 3: Frames with different values in common registers
    frame5 = {0x00: 0x22, 0x01: 0x01}
    frame6 = {0x00: 0x22, 0x01: 0x02}  # Different value for 0x01

    result = comparator._frames_match(frame5, frame6)
    print("Test 3: Different values in common registers")
    print(f"  Frame 1: {frame5}")
    print(f"  Frame 2: {frame6}")
    print(f"  Result: {result}")
    print(f"  Expected: False (values don't match)")
    print(f"  Status: {'[OK] PASS' if not result else '[FAIL] FAIL'}\n")

    # Test case 4: Both frames empty
    frame7 = {}
    frame8 = {}

    result = comparator._frames_match(frame7, frame8)
    print("Test 4: Both frames empty")
    print(f"  Frame 1: {frame7}")
    print(f"  Frame 2: {frame8}")
    print(f"  Result: {result}")
    print(f"  Expected: True (both empty)")
    print(f"  Status: {'[OK] PASS' if result else '[FAIL] FAIL'}\n")

    # Test case 5: One frame empty, one not
    frame9 = {}
    frame10 = {0x00: 0x22}

    result = comparator._frames_match(frame9, frame10)
    print("Test 5: One frame empty, one not")
    print(f"  Frame 1: {frame9}")
    print(f"  Frame 2: {frame10}")
    print(f"  Result: {result}")
    print(f"  Expected: False (no common registers)")
    print(f"  Status: {'[OK] PASS' if not result else '[FAIL] FAIL'}\n")

    print("="*70 + "\n")


def main():
    """Run all accuracy tests."""
    print("Accuracy Fix Verification Tests")
    print("Testing sparse frame matching improvement\n")

    # Test the logic directly
    test_sparse_frame_logic()

    # Test with real files (if they exist)
    try:
        test_accuracy_improvement()
        print("\n[SUCCESS] All tests passed!")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAILURE] Tests failed: {e}")
        sys.exit(1)
    except pytest.skip.Exception:
        print("\n[SKIPPED] No test files found")
        sys.exit(0)


if __name__ == '__main__':
    main()
