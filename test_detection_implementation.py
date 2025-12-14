#!/usr/bin/env python3
"""
Test the new player detection implementation.
Validates code size heuristic and detection logic.
"""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sidm2.siddecompiler import SIDdecompilerAnalyzer

def test_detection_implementation():
    """Test the new player detection on known files."""

    print("=" * 80)
    print("TESTING ENHANCED PLAYER DETECTION IMPLEMENTATION")
    print("=" * 80)
    print()

    analyzer = SIDdecompilerAnalyzer()

    # Test files with known player types
    test_cases = [
        # (file_path, expected_type, description)
        ("output/SIDSF2player_Complete_Pipeline/Broware/analysis/Broware_siddecompiler.asm",
         "NewPlayer v21 (Laxity)", "Broware (Laxity, 1323 lines)"),

        ("output/SIDSF2player_Complete_Pipeline/Stinsens_Last_Night_of_89/analysis/Stinsens_Last_Night_of_89_siddecompiler.asm",
         "NewPlayer v21 (Laxity)", "Stinsens (Laxity, 1232 lines)"),

        ("output/SIDSF2player_Complete_Pipeline/Driver 11 Test - Arpeggio/analysis/Driver 11 Test - Arpeggio_siddecompiler.asm",
         "Driver 11 or SF2 variant", "Driver 11 Test (232 lines)"),

        ("output/SIDSF2player_Complete_Pipeline/Driver 11 Test - Filter/analysis/Driver 11 Test - Filter_siddecompiler.asm",
         "Driver 11 or SF2 variant", "Driver 11 Test (232 lines)"),

        ("output/SIDSF2player_Complete_Pipeline/Staying_Alive/analysis/Staying_Alive_siddecompiler.asm",
         "NewPlayer v21 (Laxity)", "Staying_Alive (1138 lines)"),
    ]

    results = []
    print("Testing code size detection on known files:")
    print("-" * 80)

    for asm_file, expected, description in test_cases:
        asm_path = Path(asm_file)

        if not asm_path.exists():
            print(f"SKIP: {description}")
            print(f"      File not found: {asm_file}")
            print()
            continue

        # Count lines
        code_lines = analyzer._count_disassembly_lines(asm_path)
        detected_type, confidence = analyzer._detect_by_code_size(code_lines)

        # Check if detection matches expected
        matches = expected.lower() in detected_type.lower() or detected_type.lower() in expected.lower()

        status = "PASS" if matches else "FAIL"
        results.append((description, status, code_lines, detected_type, confidence))

        print(f"{status}: {description}")
        print(f"      Lines: {code_lines}")
        print(f"      Detected: {detected_type}")
        print(f"      Confidence: {confidence:.0%}")
        print(f"      Expected: {expected}")
        print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, status, _, _, _ in results if status == "PASS")
    total = len(results)

    print(f"\nPassed: {passed}/{total}")
    print()

    print("Results by file:")
    print("-" * 80)
    for desc, status, lines, detected, conf in results:
        status_str = "[OK]" if status == "PASS" else "[FAIL]"
        print(f"{status_str} {desc:<50} ({lines:>4} lines) -> {detected}")

    print()
    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()

    # Analyze results
    laxity_files = [r for r in results if "Laxity" in r[0] or "Staying" in r[0]]
    driver_files = [r for r in results if "Driver 11" in r[0]]

    laxity_correct = sum(1 for r in laxity_files if r[1] == "PASS")
    driver_correct = sum(1 for r in driver_files if r[1] == "PASS")

    print(f"Laxity Detection: {laxity_correct}/{len(laxity_files)} correct")
    print(f"Driver 11 Detection: {driver_correct}/{len(driver_files)} correct")
    print()

    if passed == total:
        print("SUCCESS: All detection tests passed!")
    else:
        print(f"PARTIAL SUCCESS: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    print()
    print("=" * 80)

if __name__ == "__main__":
    test_detection_implementation()
