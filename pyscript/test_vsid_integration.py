#!/usr/bin/env python3
"""
Test VSID Integration in Conversion Pipeline

Verifies that VSID wrapper works correctly and integrates with the audio export system.
"""

import sys
from pathlib import Path
import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.vsid_wrapper import VSIDIntegration
from sidm2.audio_export_wrapper import AudioExportIntegration


def check_vsid_availability():
    """Test if VSID is available"""
    print("\n=== Test 1: VSID Availability ===")
    available = VSIDIntegration._check_tool_available()
    vsid_path = VSIDIntegration._find_vsid()

    if available:
        print(f"[OK] VSID is available at: {vsid_path}")
        return True
    else:
        print("[X] VSID is NOT available")
        print("\nTo install VSID:")
        print("  python pyscript/install_vice.py")
        print("  OR")
        print("  install-vice.bat")
        return False


def check_vsid_export(test_sid_file):
    """Check VSID export functionality"""
    print("\n=== Test 2: VSID Export ===")

    if not test_sid_file.exists():
        print(f"[X] Test SID file not found: {test_sid_file}")
        return False

    output_wav = Path("test_output/vsid_test.wav")
    output_wav.parent.mkdir(parents=True, exist_ok=True)

    print(f"Input: {test_sid_file}")
    print(f"Output: {output_wav}")

    result = VSIDIntegration.export_to_wav(
        sid_file=test_sid_file,
        output_file=output_wav,
        duration=10,  # 10 seconds for quick test
        verbose=1
    )

    if result and result.get('success'):
        print(f"[OK] VSID export successful")
        print(f"  File size: {result['file_size']:,} bytes")
        print(f"  Duration: {result['duration']}s")
        return True
    else:
        error = result.get('error', 'Unknown error') if result else 'No result'
        print(f"[X] VSID export failed: {error}")
        return False


def check_audio_export_wrapper(test_sid_file):
    """Check AudioExportIntegration with VSID preference"""
    print("\n=== Test 3: Audio Export Wrapper (VSID Preferred) ===")

    if not test_sid_file.exists():
        print(f"[X] Test SID file not found: {test_sid_file}")
        return False

    output_wav = Path("test_output/audio_wrapper_test.wav")
    output_wav.parent.mkdir(parents=True, exist_ok=True)

    print(f"Input: {test_sid_file}")
    print(f"Output: {output_wav}")

    result = AudioExportIntegration.export_to_wav(
        sid_file=test_sid_file,
        output_file=output_wav,
        duration=10,
        verbose=1
    )

    if result and result.get('success'):
        tool_used = result.get('tool', 'unknown')
        print(f"[OK] Audio export successful using: {tool_used}")
        print(f"  File size: {result['file_size']:,} bytes")
        print(f"  Duration: {result['duration']}s")
        return True
    else:
        error = result.get('error', 'No tool available') if result else 'No tool available'
        print(f"[X] Audio export failed: {error}")
        return False


def find_test_sid_file():
    """Find a suitable test SID file"""
    # Try common locations
    test_locations = [
        Path("Fun_Fun"),
        Path("experiments/detection_fix_test"),
        Path("test_collections/Laxity"),
        Path("G5/examples"),
        Path("output"),
    ]

    for location in test_locations:
        if location.exists():
            sid_files = list(location.glob("*.sid"))
            if sid_files:
                return sid_files[0]

    return None


def main():
    """Run all VSID integration tests"""
    print("=" * 60)
    print("VSID Integration Test Suite")
    print("=" * 60)

    # Test 1: Check VSID availability
    vsid_available = check_vsid_availability()

    if not vsid_available:
        print("\n" + "=" * 60)
        print("VSID not available - skipping export tests")
        print("=" * 60)
        return 1

    # Find test SID file
    test_sid = find_test_sid_file()
    if not test_sid:
        print("\n[X] No test SID file found")
        print("  Please ensure test SID files exist in:")
        print("    - test_collections/Laxity/")
        print("    - G5/examples/")
        print("    - output/")
        return 1

    print(f"\nUsing test file: {test_sid}")

    # Test 2: Direct VSID export
    vsid_export_ok = check_vsid_export(test_sid)

    # Test 3: Audio export wrapper
    wrapper_ok = check_audio_export_wrapper(test_sid)

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"VSID Availability:    {'[OK] PASS' if vsid_available else '[X] FAIL'}")
    print(f"VSID Export:          {'[OK] PASS' if vsid_export_ok else '[X] FAIL'}")
    print(f"Audio Export Wrapper: {'[OK] PASS' if wrapper_ok else '[X] FAIL'}")
    print("=" * 60)

    all_pass = vsid_available and vsid_export_ok and wrapper_ok
    if all_pass:
        print("\n[OK] ALL TESTS PASSED")
        return 0
    else:
        print("\n[X] SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
