#!/usr/bin/env python3
"""
Compare two SF2 files byte-by-byte to find differences.
"""

import sys
from pathlib import Path

def compare_sf2_files(file1, file2):
    """Compare two SF2 files and report differences."""

    with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
        data1 = f1.read()
        data2 = f2.read()

    print("=" * 80)
    print("SF2 FILE COMPARISON")
    print("=" * 80)
    print(f"File 1: {file1} ({len(data1)} bytes)")
    print(f"File 2: {file2} ({len(data2)} bytes)")
    print()

    # Compare sizes
    if len(data1) != len(data2):
        print(f"SIZE DIFFERENCE: {len(data1)} vs {len(data2)} ({len(data1) - len(data2):+d} bytes)")
        print()

    # Compare headers (first 32 bytes)
    print("HEADER COMPARISON (first 32 bytes):")
    print("-" * 80)
    print(f"{'Offset':<8} {'File 1':<24} {'File 2':<24} {'Match':<8}")
    print("-" * 80)

    for i in range(min(32, len(data1), len(data2))):
        b1 = data1[i]
        b2 = data2[i] if i < len(data2) else 0
        match = "OK" if b1 == b2 else "DIFF"
        print(f"${i:04X}    {b1:02X} ({b1:3d})              {b2:02X} ({b2:3d})              {match}")

    print()

    # Load addresses
    load1 = data1[0] | (data1[1] << 8)
    load2 = data2[0] | (data2[1] << 8) if len(data2) >= 2 else 0
    print(f"Load Address: ${load1:04X} vs ${load2:04X} {'[MATCH]' if load1 == load2 else '[DIFF]'}")
    print()

    # Find all differences
    print("ALL DIFFERENCES:")
    print("-" * 80)

    differences = []
    max_len = max(len(data1), len(data2))

    for i in range(max_len):
        b1 = data1[i] if i < len(data1) else None
        b2 = data2[i] if i < len(data2) else None

        if b1 != b2:
            differences.append((i, b1, b2))

    if not differences:
        print("FILES ARE IDENTICAL!")
    else:
        print(f"Found {len(differences)} differences")
        print()
        print(f"{'Offset':<8} {'File 1':<12} {'File 2':<12}")
        print("-" * 40)

        # Show first 50 differences
        for offset, b1, b2 in differences[:50]:
            b1_str = f"${b1:02X}" if b1 is not None else "EOF"
            b2_str = f"${b2:02X}" if b2 is not None else "EOF"
            print(f"${offset:04X}    {b1_str:<12} {b2_str:<12}")

        if len(differences) > 50:
            print(f"... and {len(differences) - 50} more differences")

    print()
    print("=" * 80)

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python compare_sf2_binary.py <file1> <file2>")
        print()
        print("Example:")
        print('  python compare_sf2_binary.py "G5/examples/Driver 11 Test - Arpeggio.sf2" "output/test.sf2"')
        sys.exit(1)

    file1 = Path(sys.argv[1])
    file2 = Path(sys.argv[2])

    if not file1.exists():
        print(f"ERROR: File not found: {file1}")
        sys.exit(1)

    if not file2.exists():
        print(f"ERROR: File not found: {file2}")
        sys.exit(1)

    compare_sf2_files(file1, file2)
