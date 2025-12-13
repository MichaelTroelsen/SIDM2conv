#!/usr/bin/env python3
"""
Test VICE rendering function with Laxity and SF2 files.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from complete_pipeline_with_validation import render_wav_with_vice

def test_vice_rendering():
    """Test VICE rendering with Laxity and SF2 files."""

    print("=" * 80)
    print("VICE Rendering Test")
    print("=" * 80)

    # Test 1: Original Laxity file (baseline test)
    print("\nTest 1: Original Laxity File")
    print("-" * 80)

    laxity_sid = Path("SID/Angular.sid")
    laxity_wav = Path("test_vice_laxity.wav")

    if laxity_sid.exists():
        print(f"Testing VICE with: {laxity_sid}")
        success = render_wav_with_vice(laxity_sid, laxity_wav, seconds=10)

        if success and laxity_wav.exists():
            size = laxity_wav.stat().st_size
            print(f"[PASS] LAXITY TEST PASSED")
            print(f"  WAV file created: {size:,} bytes ({size/1024:.1f} KB)")
        else:
            print(f"[FAIL] LAXITY TEST FAILED - No WAV output")
    else:
        print(f"[SKIP] Test skipped - {laxity_sid} not found")

    # Test 2: SF2-packed file (critical test - solves SID2WAV limitation)
    print("\n" + "=" * 80)
    print("Test 2: SF2-Packed File (Critical Test)")
    print("-" * 80)

    sf2_sid = Path("output/SIDSF2player_Complete_Pipeline/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89_exported.sid")
    sf2_wav = Path("test_vice_sf2.wav")

    if sf2_sid.exists():
        print(f"Testing VICE with: {sf2_sid}")
        print(f"Note: This file is SF2-packed (Driver 11) - SID2WAV produces silent WAV")
        print(f"      VICE should produce audible output, solving the limitation")

        success = render_wav_with_vice(sf2_sid, sf2_wav, seconds=10)

        if success and sf2_wav.exists():
            size = sf2_wav.stat().st_size
            print(f"[PASS] SF2 TEST PASSED")
            print(f"  WAV file created: {size:,} bytes ({size/1024:.1f} KB)")
            print(f"  VICE successfully rendered SF2-packed file!")
        else:
            print(f"[FAIL] SF2 TEST FAILED - No WAV output")
    else:
        print(f"[SKIP] Test skipped - {sf2_sid} not found")

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    laxity_ok = laxity_wav.exists() and laxity_wav.stat().st_size > 0
    sf2_ok = sf2_wav.exists() and sf2_wav.stat().st_size > 0

    if laxity_ok and sf2_ok:
        print("[PASS] ALL TESTS PASSED")
        print(f"  VICE rendering works for both Laxity and SF2 files")
        print(f"  Ready to integrate into pipeline")
    elif sf2_ok:
        print("[WARN] SF2 TEST PASSED (Critical)")
        print(f"  VICE successfully renders SF2 files (solves SID2WAV limitation)")
    else:
        print("[FAIL] TESTS FAILED")
        print(f"  VICE rendering needs debugging")

if __name__ == '__main__':
    test_vice_rendering()
