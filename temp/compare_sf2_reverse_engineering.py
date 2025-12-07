#!/usr/bin/env python3
"""Compare original SF2 with reverse-engineered SF2 from SF2-packed SID."""

import struct
from pathlib import Path


def parse_sf2_header(data):
    """Parse SF2 header to extract basic info."""
    magic = data[0:4].decode('ascii', errors='ignore')
    version = struct.unpack('>H', data[4:6])[0]
    load_addr = struct.unpack('>H', data[8:10])[0]
    init_addr = struct.unpack('>H', data[10:12])[0]
    play_addr = struct.unpack('>H', data[12:14])[0]
    songs = struct.unpack('>H', data[14:16])[0]
    start_song = struct.unpack('>H', data[16:18])[0]

    name = data[0x16:0x36].decode('ascii', errors='ignore').rstrip('\x00')
    author = data[0x36:0x56].decode('ascii', errors='ignore').rstrip('\x00')
    copyright = data[0x56:0x76].decode('ascii', errors='ignore').rstrip('\x00')

    header_size = 0x7C if version == 2 else 0x76
    if load_addr == 0:
        load_addr = struct.unpack('<H', data[header_size:header_size+2])[0]

    data_size = len(data) - header_size

    return {
        'magic': magic,
        'version': version,
        'load_addr': load_addr,
        'init_addr': init_addr,
        'play_addr': play_addr,
        'songs': songs,
        'start_song': start_song,
        'header_size': header_size,
        'name': name,
        'author': author,
        'copyright': copyright,
        'data_size': data_size,
        'total_size': len(data)
    }


def find_table_offsets(data, load_addr):
    """Find table offsets in SF2 data."""
    # Driver 11 standard offsets from load address
    tables = {
        'Commands': 0x1844 - load_addr,
        'Instruments': 0x1784 - load_addr,
        'Wave': 0x1924 - load_addr,
        'Pulse': 0x1B24 - load_addr,
        'Filter': 0x1E24 - load_addr,
        'Arpeggio': 0x2124 - load_addr,
        'Tempo': 0x2224 - load_addr,
        'HR': 0x1684 - load_addr,
        'Init': 0x1664 - load_addr,
    }

    found = {}
    for name, offset in tables.items():
        if 0 <= offset < len(data):
            found[name] = offset

    return found


def compare_sf2_files(original_path, reverse_eng_path):
    """Compare original SF2 with reverse-engineered version."""

    # Read files
    with open(original_path, 'rb') as f:
        original_data = f.read()

    with open(reverse_eng_path, 'rb') as f:
        reverse_data = f.read()

    # Parse headers
    orig_header = parse_sf2_header(original_data)
    rev_header = parse_sf2_header(reverse_data)

    print("=" * 80)
    print("SF2 REVERSE ENGINEERING COMPARISON")
    print("=" * 80)
    print()

    print(f"Original SF2:        {original_path}")
    print(f"Reverse-engineered:  {reverse_eng_path}")
    print()

    # Compare headers
    print("=" * 80)
    print("HEADER COMPARISON")
    print("=" * 80)
    print(f"{'Field':<20} {'Original':<30} {'Reverse-Eng':<30} {'Match'}")
    print("-" * 80)

    fields = ['name', 'author', 'copyright', 'load_addr', 'init_addr', 'play_addr',
              'songs', 'start_song', 'data_size', 'total_size']

    for field in fields:
        orig_val = orig_header[field]
        rev_val = rev_header[field]
        match = "YES" if orig_val == rev_val else "NO"

        if isinstance(orig_val, int):
            if field in ['load_addr', 'init_addr', 'play_addr']:
                print(f"{field:<20} ${orig_val:04X} ({orig_val:<20}) "
                      f"${rev_val:04X} ({rev_val:<20}) {match}")
            else:
                print(f"{field:<20} {orig_val:<30} {rev_val:<30} {match}")
        else:
            print(f"{field:<20} {orig_val:<30} {rev_val:<30} {match}")

    print()

    # Size analysis
    print("=" * 80)
    print("SIZE ANALYSIS")
    print("=" * 80)
    size_diff = orig_header['total_size'] - rev_header['total_size']
    size_pct = (size_diff / orig_header['total_size']) * 100
    print(f"Original size:       {orig_header['total_size']:,} bytes")
    print(f"Reverse-eng size:    {rev_header['total_size']:,} bytes")
    print(f"Size difference:     {size_diff:,} bytes ({size_pct:.1f}% smaller)")
    print()

    # Extract music data
    orig_music_data = original_data[orig_header['header_size']:]
    rev_music_data = reverse_data[rev_header['header_size']:]

    print(f"Original music data: {len(orig_music_data):,} bytes")
    print(f"Reverse music data:  {len(rev_music_data):,} bytes")
    print()

    # Table analysis
    print("=" * 80)
    print("TABLE STRUCTURE ANALYSIS")
    print("=" * 80)

    orig_tables = find_table_offsets(orig_music_data, orig_header['load_addr'])
    rev_tables = find_table_offsets(rev_music_data, rev_header['load_addr'])

    print(f"{'Table':<20} {'Original Offset':<20} {'Reverse Offset':<20} {'Match'}")
    print("-" * 80)

    all_tables = set(orig_tables.keys()) | set(rev_tables.keys())
    for table in sorted(all_tables):
        orig_off = orig_tables.get(table, -1)
        rev_off = rev_tables.get(table, -1)
        match = "YES" if orig_off == rev_off else "NO"

        orig_str = f"${orig_off:04X}" if orig_off >= 0 else "Missing"
        rev_str = f"${rev_off:04X}" if rev_off >= 0 else "Missing"

        print(f"{table:<20} {orig_str:<20} {rev_str:<20} {match}")

    print()

    # Byte-by-byte comparison of first 256 bytes
    print("=" * 80)
    print("FIRST 256 BYTES COMPARISON")
    print("=" * 80)

    matches = 0
    total = min(256, len(orig_music_data), len(rev_music_data))

    for i in range(total):
        if orig_music_data[i] == rev_music_data[i]:
            matches += 1

    match_pct = (matches / total * 100) if total > 0 else 0
    print(f"Matching bytes: {matches}/{total} ({match_pct:.1f}%)")
    print()

    # Detailed byte diff for first 64 bytes
    print("First 64 bytes (hexdump):")
    print()
    print("Offset   Original                                         Reverse-Eng")
    print("-" * 80)

    for offset in range(0, min(64, len(orig_music_data), len(rev_music_data)), 16):
        orig_bytes = orig_music_data[offset:offset+16]
        rev_bytes = rev_music_data[offset:offset+16]

        orig_hex = ' '.join(f"{b:02x}" for b in orig_bytes)
        rev_hex = ' '.join(f"{b:02x}" for b in rev_bytes)

        match_marker = "=" if orig_bytes == rev_bytes else "!"
        print(f"{offset:04x}:    {orig_hex:<48} {match_marker}")
        print(f"         {rev_hex:<48}")
        print()

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    header_matches = sum(1 for f in fields if orig_header[f] == rev_header[f])
    header_total = len(fields)

    print(f"Header fields matching: {header_matches}/{header_total} ({header_matches/header_total*100:.1f}%)")
    print(f"File size ratio:        {rev_header['total_size']/orig_header['total_size']*100:.1f}%")
    print(f"First 256 bytes match:  {match_pct:.1f}%")
    print()

    if size_diff > 0:
        print("MISSING DATA:")
        print(f"  - {size_diff:,} bytes ({size_pct:.1f}%) not recovered in reverse engineering")
        print()
        print("POSSIBLE REASONS:")
        print("  - Auxiliary data (names, comments) not extracted from SID")
        print("  - Extended tables not detected")
        print("  - Sequence/orderlist data compressed differently")
        print("  - Template file has different driver size")

    print()
    print("=" * 80)


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 3:
        print("Usage: python compare_sf2_reverse_engineering.py <original.sf2> <reverse_engineered.sf2>")
        sys.exit(1)

    original = sys.argv[1]
    reverse_eng = sys.argv[2]

    compare_sf2_files(original, reverse_eng)
