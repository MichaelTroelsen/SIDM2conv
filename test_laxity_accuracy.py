#!/usr/bin/env python3
"""Quick accuracy test for Laxity driver wave table fix"""

import subprocess
import sys
from pathlib import Path

def test_file(sid_file):
    """Test a single Laxity SID file"""
    print(f"\n{'='*80}")
    print(f"Testing: {sid_file.name}")
    print('='*80)

    basename = sid_file.stem
    output_sf2 = Path(f"output/test_{basename}.sf2")
    output_sid = Path(f"output/test_{basename}_exported.sid")
    orig_dump = Path(f"output/test_{basename}_original.dump")
    exp_dump = Path(f"output/test_{basename}_exported.dump")

    # Convert SID to SF2
    print("  [1/5] Converting SID -> SF2 with Laxity driver...")
    result = subprocess.run(
        ['python', 'scripts/sid_to_sf2.py', str(sid_file), str(output_sf2), '--driver', 'laxity', '--overwrite'],
        capture_output=True,
        text=True,
        timeout=30
    )
    if result.returncode != 0:
        print(f"    [ERROR] Conversion failed")
        return None
    print(f"    [OK] Created {output_sf2}")

    # Export SF2 to SID
    print("  [2/5] Exporting SF2 -> SID...")
    result = subprocess.run(
        ['python', 'scripts/sf2_to_sid.py', str(output_sf2), str(output_sid)],
        capture_output=True,
        text=True,
        timeout=30
    )
    if result.returncode != 0:
        print(f"    [ERROR] Export failed")
        return None
    print(f"    [OK] Created {output_sid}")

    # Generate dumps
    print("  [3/5] Generating siddumps...")
    subprocess.run(['tools\\siddump.exe', str(sid_file), '-t10'],
                   stdout=open(orig_dump, 'w'), timeout=30)
    subprocess.run(['tools\\siddump.exe', str(output_sid), '-t10'],
                   stdout=open(exp_dump, 'w'), timeout=30)
    print(f"    [OK] Created dumps")

    # Count register writes
    orig_count = len(open(orig_dump).readlines())
    exp_count = len(open(exp_dump).readlines())
    print(f"  [4/5] Register writes: {orig_count} original -> {exp_count} exported")

    # Validate accuracy
    print("  [5/5] Calculating accuracy...")
    result = subprocess.run(
        ['python', 'scripts/validate_sid_accuracy.py', str(orig_dump), str(exp_dump)],
        capture_output=True,
        text=True,
        timeout=30
    )

    # Extract accuracy from output
    for line in result.stdout.split('\n'):
        if 'Frame Accuracy:' in line:
            accuracy = line.split(':')[1].strip()
            print(f"    Frame Accuracy: {accuracy}")
            return accuracy
        if 'Overall Accuracy:' in line:
            overall = line.split(':')[1].strip()
            print(f"    Overall Accuracy: {overall}")

    return None

if __name__ == '__main__':
    # Test known Laxity files
    test_files = [
        Path('learnings/Stinsens_Last_Night_of_89.sid'),
        Path('SIDSF2player/Broware.sid'),
    ]

    results = {}
    for sid_file in test_files:
        if sid_file.exists():
            accuracy = test_file(sid_file)
            results[sid_file.name] = accuracy
        else:
            print(f"\n[SKIP] {sid_file} not found")

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print('='*80)
    for filename, accuracy in results.items():
        status = "[OK]" if accuracy and "99" in accuracy else "[FAIL]"
        print(f"  {status} {filename}: {accuracy or 'N/A'}")
