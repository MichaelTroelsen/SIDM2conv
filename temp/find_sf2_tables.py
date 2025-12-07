#!/usr/bin/env python3
"""
Find SF2 Table Locations in Packed SID

Scans an SF2-packed SID file to find the actual locations of music tables
by comparing with a known original SF2 file.
"""

import struct
from pathlib import Path


def load_psid(path):
    """Load PSID file and return load address and music data."""
    with open(path, 'rb') as f:
        data = f.read()

    magic = data[0:4]
    if magic not in [b'PSID', b'RSID']:
        # Try as raw PRG
        load_addr = struct.unpack('<H', data[0:2])[0]
        return load_addr, data[2:]

    version = struct.unpack('>H', data[4:6])[0]
    load_addr = struct.unpack('>H', data[8:10])[0]
    header_size = 0x7C if version == 2 else 0x76

    if load_addr == 0:
        load_addr = struct.unpack('<H', data[header_size:header_size+2])[0]
        music_data = data[header_size+2:]
    else:
        music_data = data[header_size:]

    return load_addr, music_data


def extract_table_from_file(music_data, load_addr, table_start, table_end):
    """Extract table from file."""
    offset_start = table_start - load_addr
    offset_end = table_end - load_addr

    if offset_start < 0 or offset_end > len(music_data):
        return None

    return music_data[offset_start:offset_end]


def find_pattern_in_data(haystack, needle, min_match=32):
    """Find where needle pattern appears in haystack."""
    if len(needle) < min_match:
        min_match = len(needle)

    best_offset = -1
    best_matches = 0

    # Search for pattern
    for offset in range(len(haystack) - len(needle) + 1):
        matches = sum(1 for i in range(len(needle))
                     if haystack[offset + i] == needle[i])

        if matches > best_matches:
            best_matches = matches
            best_offset = offset

    match_pct = (best_matches / len(needle) * 100) if len(needle) > 0 else 0

    return best_offset, best_matches, match_pct


def find_sf2_tables(original_sf2, packed_sid):
    """Find table locations in packed SID by comparing with original SF2."""

    print("="*80)
    print("FINDING SF2 TABLE LOCATIONS IN PACKED SID")
    print("="*80)
    print()

    # Load files
    orig_load, orig_data = load_psid(original_sf2)
    packed_load, packed_data = load_psid(packed_sid)

    print(f"Original SF2:  {original_sf2}")
    print(f"  Load address: ${orig_load:04X}")
    print(f"  Data size:    {len(orig_data):,} bytes")
    print()

    print(f"Packed SID:    {packed_sid}")
    print(f"  Load address: ${packed_load:04X}")
    print(f"  Data size:    {len(packed_data):,} bytes")
    print()

    # Driver 11 table definitions (relative to original load address)
    tables = {
        'Init': (0x0F20, 0x0F40),
        'HR': (0x0F40, 0x1040),
        'Instruments': (0x1040, 0x1100),
        'Commands': (0x1100, 0x11E0),
        'Wave': (0x11E0, 0x13E0),
        'Pulse': (0x13E0, 0x16E0),
        'Filter': (0x16E0, 0x19E0),
        'Arpeggio': (0x19E0, 0x1AE0),
        'Tempo': (0x1AE0, 0x1BE0),
    }

    print("="*80)
    print("SEARCHING FOR TABLES")
    print("="*80)
    print()

    found_tables = {}

    for name, (start, end) in tables.items():
        size = end - start

        # Extract from original
        orig_table = extract_table_from_file(orig_data, orig_load, start, end)

        if not orig_table:
            print(f"{name:<15} SKIP (not in original)")
            continue

        # Search for this pattern in packed SID
        offset, matches, match_pct = find_pattern_in_data(packed_data, orig_table)

        if offset >= 0:
            found_addr = packed_load + offset
            status = "PERFECT" if match_pct == 100 else \
                     "GOOD" if match_pct >= 80 else \
                     "FAIR" if match_pct >= 50 else \
                     "POOR"

            print(f"{name:<15} Found at ${found_addr:04X} "
                  f"(offset ${offset:04X}) - {match_pct:5.1f}% match ({status})")

            found_tables[name] = {
                'address': found_addr,
                'offset': offset,
                'size': size,
                'match_pct': match_pct,
                'orig_start': start,
                'orig_end': end
            }
        else:
            print(f"{name:<15} NOT FOUND")

    # Calculate address mapping
    print()
    print("="*80)
    print("ADDRESS MAPPING ANALYSIS")
    print("="*80)
    print()

    print(f"{'Table':<15} {'Original':<12} {'Packed':<12} {'Offset Diff'}")
    print("-"*60)

    for name, info in found_tables.items():
        orig_addr = info['orig_start']
        packed_addr = info['address']
        diff = packed_addr - orig_addr

        print(f"{name:<15} ${orig_addr:04X}       ${packed_addr:04X}       "
              f"{diff:+5d} (${diff:+04X})")

    # Find common offset
    offsets = [info['address'] - info['orig_start'] for info in found_tables.values()]
    if offsets:
        avg_offset = sum(offsets) / len(offsets)
        print()
        print(f"Average address offset: {avg_offset:+.0f} bytes (${int(avg_offset):+04X})")
        print(f"This suggests packed load address should be: ${orig_load + int(avg_offset):04X}")

    return found_tables


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) != 3:
        print("Usage: python find_sf2_tables.py <original_sf2> <packed_sid>")
        sys.exit(1)

    original_sf2 = sys.argv[1]
    packed_sid = sys.argv[2]

    found_tables = find_sf2_tables(original_sf2, packed_sid)

    print()
    print("="*80)
    print(f"FOUND {len(found_tables)} TABLES")
    print("="*80)


if __name__ == '__main__':
    main()
