#!/usr/bin/env python3
"""
Test memory overlap detection functionality.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.memory_overlap_detector import MemoryOverlapDetector, OverlapConflict


def test_no_overlaps():
    """Test detection when there are no overlaps"""

    print("=" * 100)
    print("TEST: NO OVERLAPS")
    print("=" * 100)
    print()

    detector = MemoryOverlapDetector()

    # Add non-overlapping blocks
    detector.add_block('code', 0x0800, 0x0FFF, 'code', 'Player code')
    detector.add_block('data1', 0x1000, 0x1FFF, 'data', 'Music data')
    detector.add_block('data2', 0x2000, 0x2FFF, 'data', 'Tables')
    detector.add_block('free', 0x3000, 0xCFFF, 'free', 'Free memory')

    overlaps = detector.detect_overlaps()

    print(detector.generate_overlap_report())
    print()

    if len(overlaps) == 0:
        print("[OK] No overlaps detected correctly!")
    else:
        print("[FAIL] Unexpected overlaps found")
    print()


def test_simple_overlap():
    """Test detection of simple overlaps"""

    print("=" * 100)
    print("TEST: SIMPLE OVERLAP")
    print("=" * 100)
    print()

    detector = MemoryOverlapDetector()

    # Add overlapping blocks
    detector.add_block('block1', 0x1000, 0x1100, 'data')
    detector.add_block('block2', 0x1080, 0x1180, 'data')

    overlaps = detector.detect_overlaps()

    print(detector.generate_overlap_report())
    print()

    if len(overlaps) > 0:
        print("[OK] Overlap detected correctly!")
        for overlap in overlaps:
            print(f"     {overlap}")
    else:
        print("[FAIL] Overlap not detected")
    print()


def test_critical_overlap():
    """Test detection of critical overlaps (code + data)"""

    print("=" * 100)
    print("TEST: CRITICAL OVERLAP (CODE)")
    print("=" * 100)
    print()

    detector = MemoryOverlapDetector()

    # Add code and overlapping data
    detector.add_block('player_code', 0x0800, 0x0FFF, 'code', 'Player code')
    detector.add_block('data_table', 0x0F00, 0x1100, 'data', 'Data table - overlaps with code!')

    overlaps = detector.detect_overlaps()

    print(detector.generate_overlap_report())
    print()

    if len(overlaps) > 0:
        overlap = overlaps[0]
        if overlap.severity == 'critical':
            print("[OK] Critical overlap detected correctly!")
            print(f"     {overlap}")
        else:
            print(f"[WARN] Overlap detected but severity is {overlap.severity}, expected critical")
    else:
        print("[FAIL] Critical overlap not detected")
    print()


def test_multiple_overlaps():
    """Test detection of multiple overlapping blocks"""

    print("=" * 100)
    print("TEST: MULTIPLE OVERLAPS")
    print("=" * 100)
    print()

    detector = MemoryOverlapDetector()

    # Add multiple overlapping blocks
    detector.add_block('block1', 0x1000, 0x1100, 'data')
    detector.add_block('block2', 0x1080, 0x1180, 'data')
    detector.add_block('block3', 0x1100, 0x1200, 'data')
    detector.add_block('block4', 0x1180, 0x1280, 'data')

    overlaps = detector.detect_overlaps()

    print(detector.generate_overlap_report())
    print()

    suggestions = detector.generate_suggestions()
    print("SUGGESTIONS:")
    print("-" * 100)
    for suggestion in suggestions:
        print(f"  {suggestion}")
    print()

    if len(overlaps) >= 3:  # Should detect multiple overlaps
        print("[OK] Multiple overlaps detected correctly!")
    else:
        print("[FAIL] Not enough overlaps detected")
    print()


def test_memory_fragmentation():
    """Test memory fragmentation analysis"""

    print("=" * 100)
    print("TEST: MEMORY FRAGMENTATION ANALYSIS")
    print("=" * 100)
    print()

    detector = MemoryOverlapDetector()

    # Add fragmented memory layout
    detector.add_block('code', 0x0800, 0x0FFF, 'code')
    detector.add_block('gap1', 0x1000, 0x1001, 'free')  # Small gap
    detector.add_block('data1', 0x1002, 0x2000, 'data')
    detector.add_block('gap2', 0x2001, 0x3000, 'free')  # Another gap
    detector.add_block('data2', 0x3001, 0x4000, 'data')

    overlaps = detector.detect_overlaps()
    suggestions = detector.generate_suggestions()

    print(detector.generate_overlap_report())
    print()

    print("FRAGMENTATION ANALYSIS:")
    print("-" * 100)
    for suggestion in suggestions:
        print(f"  {suggestion}")
    print()

    print("[OK] Fragmentation analysis complete")
    print()


def test_validation():
    """Test validation function"""

    print("=" * 100)
    print("TEST: VALIDATION")
    print("=" * 100)
    print()

    detector = MemoryOverlapDetector()
    detector.add_block('valid1', 0x1000, 0x1100, 'data')
    detector.add_block('valid2', 0x2000, 0x2100, 'data')

    valid, messages = detector.validate_no_overlaps()

    print(f"Validation Result: {'PASS' if valid else 'FAIL'}")
    print("Messages:")
    for msg in messages:
        print(f"  - {msg}")
    print()

    if valid:
        print("[OK] Clean memory layout validated successfully!")
    else:
        print("[FAIL] Validation failed")
    print()


if __name__ == "__main__":
    print()
    print("MEMORY OVERLAP DETECTION TEST SUITE")
    print("=" * 100)
    print()

    test_no_overlaps()
    test_simple_overlap()
    test_critical_overlap()
    test_multiple_overlaps()
    test_memory_fragmentation()
    test_validation()

    print("=" * 100)
    print("MEMORY OVERLAP TESTS COMPLETE")
    print("=" * 100)
