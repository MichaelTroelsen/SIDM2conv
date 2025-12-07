#!/usr/bin/env python3
"""
Proper SF2 extraction - preserves original structure, only replaces tables we can extract.
"""

import struct
from pathlib import Path


def extract_sf2_properly(packed_sid_path, original_sf2_path, output_path):
    """Extract SF2 by using original structure and injecting extracted tables."""

    # Read packed SID
    with open(packed_sid_path, 'rb') as f:
        packed_raw = f.read()

    # Read original SF2 (for structure reference only)
    with open(original_sf2_path, 'rb') as f:
        original_data = bytearray(f.read())

    # Parse packed SID
    packed_load = struct.unpack('>H', packed_raw[8:10])[0]
    packed_init = struct.unpack('>H', packed_raw[10:12])[0]
    packed_play = struct.unpack('>H', packed_raw[12:14])[0]

    if packed_load == 0:
        packed_load = struct.unpack('<H', packed_raw[0x7C:0x7C+2])[0]
        packed_music = packed_raw[0x7E:]
    else:
        packed_music = packed_raw[0x7C:]

    # Parse original SF2
    orig_load = struct.unpack('<H', original_data[0:2])[0]

    print(f'Packed SID: load=${packed_load:04X}, init=${packed_init:04X}, play=${packed_play:04X}')
    print(f'Original SF2: load=${orig_load:04X}, size={len(original_data):,}')
    print()

    # Tables at absolute addresses
    tables = [
        ('Instruments', 0x1040, 192),
        ('Commands', 0x1100, 224),
        ('Wave', 0x11E0, 512),
        ('Pulse', 0x13E0, 768),
        ('Filter', 0x16E0, 768),
        ('Arpeggio', 0x19E0, 256),
        ('Tempo', 0x1AE0, 256),
    ]

    print('Extracting tables from packed SID and injecting into original structure:')
    print()

    # For each table, extract from packed SID and inject into original structure
    for name, addr, size in tables:
        # Extract from packed SID
        packed_offset = addr - packed_load
        table_data = packed_music[packed_offset:packed_offset+size]

        # Inject into original SF2 structure
        orig_offset = addr - orig_load + 2  # +2 for load address

        if orig_offset >= 0 and orig_offset + size <= len(original_data):
            # Verify it's the same data
            original_table = original_data[orig_offset:orig_offset+size]
            matches = sum(1 for i in range(size) if table_data[i] == original_table[i])
            match_pct = matches / size * 100

            # Inject
            original_data[orig_offset:orig_offset+size] = table_data

            print(f'{name:<15} ${addr:04X}: {matches}/{size} ({match_pct:5.1f}%) - injected')
        else:
            print(f'{name:<15} ${addr:04X}: SKIP (out of bounds)')

    # Update DriverCommon structure with correct init/play addresses
    # DriverCommon is at fixed file offsets: 0x31-0x32 (init), 0x33-0x34 (play)
    # File offset = memory offset + 2 (for load address header)
    # Memory offset = address - load_address
    print()
    print('Updating DriverCommon with correct addresses:')

    # Calculate the actual init/play routines from the packed SID
    # The PSID header init/play are entry points, but DriverCommon needs the actual routine addresses
    # For SF2 Driver 11: entry stubs are at $1000 and $1003, pointing to actual routines

    # Read the JMP targets from the packed SID to get the actual routine addresses
    if len(packed_music) >= 6:
        # Check if there are JMP instructions at $1000 and $1003
        if packed_music[0] == 0x4C:  # JMP opcode at offset 0 ($1000)
            actual_init = struct.unpack('<H', packed_music[1:3])[0]
        else:
            actual_init = packed_init

        if packed_music[3] == 0x4C:  # JMP opcode at offset 3 ($1003)
            actual_play = struct.unpack('<H', packed_music[4:6])[0]
        else:
            actual_play = packed_play
    else:
        actual_init = packed_init
        actual_play = packed_play

    # Read old values before updating
    old_init = struct.unpack('<H', original_data[0x31:0x33])[0]
    old_play = struct.unpack('<H', original_data[0x33:0x35])[0]

    # Write to DriverCommon structure (file offset 0x31 and 0x33)
    # Init address at file offset 0x31 (little-endian)
    struct.pack_into('<H', original_data, 0x31, actual_init)
    # Play address at file offset 0x33 (little-endian)
    struct.pack_into('<H', original_data, 0x33, actual_play)

    print(f'  Init: ${actual_init:04X} (was ${old_init:04X})')
    print(f'  Play: ${actual_play:04X} (was ${old_play:04X})')

    # Write output
    with open(output_path, 'wb') as f:
        f.write(original_data)

    print()
    print(f'Created: {output_path}')
    print(f'Size: {len(original_data):,} bytes')

    return True


if __name__ == '__main__':
    import sys

    if len(sys.argv) != 4:
        print('Usage: python extract_sf2_properly.py <packed_sid> <original_sf2> <output_sf2>')
        sys.exit(1)

    extract_sf2_properly(sys.argv[1], sys.argv[2], sys.argv[3])
