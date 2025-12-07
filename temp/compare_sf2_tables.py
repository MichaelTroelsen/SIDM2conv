#!/usr/bin/env python3
"""Compare SF2 tables byte-by-byte between original and reverse-engineered."""

import struct
from pathlib import Path


def parse_psid_header(data):
    """Parse PSID header."""
    magic = data[0:4].decode('ascii', errors='ignore')
    version = struct.unpack('>H', data[4:6])[0]
    load_addr = struct.unpack('>H', data[8:10])[0]
    header_size = 0x7C if version == 2 else 0x76

    if load_addr == 0:
        load_addr = struct.unpack('<H', data[header_size:header_size+2])[0]

    return {
        'header_size': header_size,
        'load_addr': load_addr,
        'music_data': data[header_size:]
    }


def extract_table(music_data, load_addr, start_addr, end_addr):
    """Extract table data from SF2 file."""
    offset_start = start_addr - load_addr
    offset_end = end_addr - load_addr

    if offset_start < 0 or offset_end > len(music_data):
        return b''

    return music_data[offset_start:offset_end]


def compare_tables(orig_path, rev_path):
    """Compare tables between original and reverse-engineered SF2."""

    # Read files
    with open(orig_path, 'rb') as f:
        orig_data = f.read()
    with open(rev_path, 'rb') as f:
        rev_data = f.read()

    # Parse headers
    orig_header = parse_psid_header(orig_data)
    rev_header = parse_psid_header(rev_data)

    orig_music = orig_header['music_data']
    rev_music = rev_header['music_data']
    orig_load = orig_header['load_addr']
    rev_load = rev_header['load_addr']

    print("="*80)
    print("SF2 TABLE-BY-TABLE COMPARISON")
    print("="*80)
    print(f"\nOriginal: {orig_path}")
    print(f"  Load addr: ${orig_load:04X}")
    print(f"  Data size: {len(orig_music):,} bytes")

    print(f"\nReverse-eng: {rev_path}")
    print(f"  Load addr: ${rev_load:04X}")
    print(f"  Data size: {len(rev_music):,} bytes")

    # Driver 11 table definitions (from both files)
    tables = [
        ("Init", 0x0F20, 0x0F40),
        ("HR", 0x0F40, 0x1040),
        ("Instruments", 0x1040, 0x1100),
        ("Commands", 0x1100, 0x11E0),
        ("Wave", 0x11E0, 0x13E0),
        ("Pulse", 0x13E0, 0x16E0),
        ("Filter", 0x16E0, 0x19E0),
        ("Arpeggio", 0x19E0, 0x1AE0),
        ("Tempo", 0x1AE0, 0x1BE0),
    ]

    print(f"\n{'='*80}")
    print("TABLE COMPARISON")
    print(f"{'='*80}\n")

    print(f"{'Table':<15} {'Size':<8} {'Match %':<10} {'Status':<15} {'Details'}")
    print("-"*80)

    total_matches = 0
    total_bytes = 0

    for name, start, end in tables:
        size = end - start

        # Extract from both files
        orig_table = extract_table(orig_music, orig_load, start, end)
        rev_table = extract_table(rev_music, rev_load, start, end)

        if len(orig_table) == 0 or len(rev_table) == 0:
            print(f"{name:<15} {size:<8} {'N/A':<10} {'Missing':<15} Table not found")
            continue

        # Compare byte-by-byte
        matches = sum(1 for i in range(min(len(orig_table), len(rev_table)))
                     if orig_table[i] == rev_table[i])
        total = min(len(orig_table), len(rev_table))
        match_pct = (matches / total * 100) if total > 0 else 0

        total_matches += matches
        total_bytes += total

        status = "PERFECT" if match_pct == 100 else \
                 "GOOD" if match_pct >= 80 else \
                 "FAIR" if match_pct >= 50 else \
                 "POOR"

        # Show first difference
        first_diff = -1
        for i in range(total):
            if orig_table[i] != rev_table[i]:
                first_diff = i
                break

        details = f"1st diff @{first_diff}" if first_diff >= 0 else "Perfect match"

        print(f"{name:<15} {size:<8} {match_pct:>6.1f}%   {status:<15} {details}")

        # Show detailed hex comparison for poor matches
        if match_pct < 50 and size <= 64:
            print(f"\n  Detailed comparison (first {min(32, total)} bytes):")
            print(f"  Original:  ", end="")
            for i in range(min(32, len(orig_table))):
                print(f"{orig_table[i]:02x} ", end="")
            print()
            print(f"  Reverse:   ", end="")
            for i in range(min(32, len(rev_table))):
                marker = "^^" if i < len(orig_table) and orig_table[i] != rev_table[i] else "  "
                print(f"{rev_table[i]:02x} ", end="")
            print()
            print()

    print("-"*80)
    overall = (total_matches / total_bytes * 100) if total_bytes > 0 else 0
    print(f"{'OVERALL':<15} {total_bytes:<8} {overall:>6.1f}%   "
          f"{'GOOD' if overall >= 80 else 'FAIR' if overall >= 50 else 'POOR':<15} "
          f"{total_matches}/{total_bytes} bytes")

    print(f"\n{'='*80}")
    print("ANALYSIS")
    print(f"{'='*80}\n")

    if overall >= 90:
        print("Excellent! Reverse engineering is highly accurate.")
    elif overall >= 70:
        print("Good! Most data recovered correctly.")
        print("Differences may be due to template vs original driver variations.")
    elif overall >= 50:
        print("Fair. Significant differences detected.")
        print("Issue: Using wrong extraction method or template mismatch.")
    else:
        print("Poor. Major differences detected.")
        print("Issue: Incorrect table extraction or data corruption.")

    print(f"\nRecommendations:")
    if overall < 80:
        print("- Verify we're using the correct SF2 template")
        print("- Check if source SID has correct table data")
        print("- Compare with siddump output for validation")
        print("- Consider extracting directly from SF2-packed SID instead of converting")


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 3:
        print("Usage: python compare_sf2_tables.py <original.sf2> <reverse_eng.sf2>")
        sys.exit(1)

    compare_tables(sys.argv[1], sys.argv[2])
