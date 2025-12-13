#!/usr/bin/env python3
"""Test musical content comparison for all MIDI files."""

import sys
from pathlib import Path
import subprocess

# List of all test files
TEST_FILES = [
    "Angular",
    "Balance",
    "Beast",
    "Blue",
    "Cascade",
    "Chaser",
    "Clarencio_extended",
    "Colorama",
    "Cycles",
    "Delicate",
    "Dreams",
    "Dreamy",
    "Ocean_Reloaded",
    "Omniphunk",
    "Phoenix_Code_End_Tune",
    "Stinsens_Last_Night_of_89",
    "Unboxed_Ending_8580"
]

def test_file(filename):
    """Test a single file's musical content."""
    output_dir = Path("output/midi_comparison")
    python_file = output_dir / f"{filename}_python.mid"
    sidtool_file = output_dir / f"{filename}_sidtool.mid"

    if not python_file.exists() or not sidtool_file.exists():
        return filename, "MISSING", 0, 0

    # Run comparison
    result = subprocess.run(
        [sys.executable, "scripts/compare_musical_content.py",
         str(python_file), str(sidtool_file)],
        capture_output=True,
        text=True
    )

    # Parse output
    lines = result.stdout.strip().split('\n')
    status = "UNKNOWN"
    python_notes = 0
    sidtool_notes = 0

    for line in lines:
        if "PERFECT" in line:
            status = "PERFECT"
        elif "DIFF" in line:
            status = "DIFF"
        elif "_python.mid:" in line:
            python_notes = int(line.split(":")[1].split()[0])
        elif "_sidtool.mid:" in line:
            sidtool_notes = int(line.split(":")[1].split()[0])

    return filename, status, python_notes, sidtool_notes

def main():
    print("=" * 80)
    print("MUSICAL CONTENT COMPARISON - ALL 17 FILES")
    print("=" * 80)
    print(f"{'File':<30} {'Python':<10} {'SIDtool':<10} {'Status'}")
    print("-" * 80)

    perfect_count = 0
    diff_count = 0
    missing_count = 0

    for filename in TEST_FILES:
        name, status, python_notes, sidtool_notes = test_file(filename)

        if status == "PERFECT":
            perfect_count += 1
            marker = "[PERFECT]"
        elif status == "DIFF":
            diff_count += 1
            marker = "[DIFF]"
        else:
            missing_count += 1
            marker = "[MISSING]"

        print(f"{name:<30} {python_notes:<10} {sidtool_notes:<10} {marker}")

    print("-" * 80)
    print(f"\nRESULTS:")
    print(f"  Perfect matches: {perfect_count}/{len(TEST_FILES)} ({100*perfect_count/len(TEST_FILES):.1f}%)")
    print(f"  Differences:     {diff_count}/{len(TEST_FILES)}")
    print(f"  Missing:         {missing_count}/{len(TEST_FILES)}")
    print("=" * 80)

if __name__ == '__main__':
    main()
