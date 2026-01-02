#!/usr/bin/env python3
"""
Parse SF2 file block structure to understand format.
"""

import struct
import sys
from pathlib import Path

def parse_sf2_blocks(filename):
    """Parse and display SF2 file block structure."""

    with open(filename, 'rb') as f:
        data = f.read()

    print("=" * 80)
    print(f"SF2 FILE STRUCTURE: {filename}")
    print("=" * 80)
    print(f"File size: {len(data)} bytes")
    print()

    # Load address
    load_addr = struct.unpack('<H', data[0:2])[0]
    print(f"Load Address: ${load_addr:04X}")
    print()

    # Parse blocks starting at offset 2
    offset = 2
    block_num = 0

    print("BLOCKS:")
    print("-" * 80)

    while offset < min(len(data), 512):  # Only parse first 512 bytes
        if offset + 2 > len(data):
            break

        block_id = data[offset]
        block_size = data[offset + 1]

        # Stop if we hit zeros (end of blocks)
        if block_id == 0 and block_size == 0:
            print(f"\nEnd of blocks at offset ${offset:04X}")
            break

        print(f"\nBlock {block_num} at offset ${offset:04X}:")
        print(f"  ID: ${block_id:02X}")
        print(f"  Size: {block_size} bytes")

        if offset + 2 + block_size > len(data):
            print(f"  ERROR: Block extends past end of file!")
            break

        block_data = data[offset + 2:offset + 2 + block_size]

        # Parse based on block ID
        if block_id == 0x01:  # Descriptor block
            parse_descriptor_block(block_data)
        elif block_id == 0x02:  # Driver common
            print(f"  Type: Driver Common (addresses)")
        elif block_id == 0x03:  # Music data
            print(f"  Type: Music Data")
        else:
            print(f"  Type: Unknown")

        # Show first 32 bytes of block data
        print(f"  Data (first 32 bytes):")
        for i in range(0, min(32, len(block_data)), 16):
            hex_str = ' '.join(f'{b:02X}' for b in block_data[i:i+16])
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in block_data[i:i+16])
            print(f"    ${offset + 2 + i:04X}: {hex_str:<48} {ascii_str}")

        offset += 2 + block_size
        block_num += 1

    print()
    print("=" * 80)

def parse_descriptor_block(data):
    """Parse descriptor block details."""
    print(f"  Type: Descriptor Block")

    if len(data) < 3:
        print(f"  ERROR: Block too small")
        return

    driver_type = data[0]
    driver_size = struct.unpack('<H', data[1:3])[0]

    print(f"  Driver Type: ${driver_type:02X}")
    print(f"  Driver Size: {driver_size} bytes")

    # Driver name (null-terminated)
    if len(data) > 3:
        name_bytes = data[3:]
        # Find null terminator
        null_pos = name_bytes.find(0)
        if null_pos >= 0:
            name = name_bytes[:null_pos].decode('ascii', errors='replace')
            print(f"  Driver Name: '{name}'")
        else:
            # No null terminator, show what's there
            name = name_bytes.decode('ascii', errors='replace')
            print(f"  Driver Name: '{name}' (NO NULL TERMINATOR!)")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python parse_sf2_blocks.py <sf2_file>")
        sys.exit(1)

    filename = sys.argv[1]
    if not Path(filename).exists():
        print(f"ERROR: File not found: {filename}")
        sys.exit(1)

    parse_sf2_blocks(filename)
