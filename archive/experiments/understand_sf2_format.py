#!/usr/bin/env python3
"""
Understand SF2 format by parsing the reference file.

Based on SF2Writer code:
- Offset 0-1: Load address (little-endian)
- Offset 2-3: File ID (0x1337, little-endian)
- Offset 4+: Blocks [block_id][block_size][data...]
- Block IDs: 1=Descriptor, 2=Driver Common, 3=Driver Tables, 4=Instrument Desc, 5=Music Data, FF=End
"""

import struct


def parse_sf2_file(filename):
    """Parse SF2 file and show structure."""
    with open(filename, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes")
    print()

    # Parse header
    load_addr = struct.unpack('<H', data[0:2])[0]
    file_id = struct.unpack('<H', data[2:4])[0]

    print(f"Load address: ${load_addr:04X}")
    print(f"File ID: ${file_id:04X} (expected $1337)")
    print()

    if file_id != 0x1337:
        print("WARNING: File ID doesn't match expected value!")
        print("This might not be an SF2 file, or uses different format.")
        print()

    # Parse blocks
    print("Blocks:")
    print()

    offset = 4
    block_num = 0

    while offset < len(data) - 2:
        block_id = data[offset]

        if block_id == 0xFF:
            print(f"Block {block_num}: END (0xFF) at offset 0x{offset:04X}")
            break

        block_size = data[offset + 1]
        block_data_start = offset + 2
        block_data_end = block_data_start + block_size

        block_names = {
            1: "Descriptor",
            2: "Driver Common",
            3: "Driver Tables",
            4: "Instrument Desc",
            5: "Music Data"
        }

        block_name = block_names.get(block_id, f"Unknown({block_id})")

        print(f"Block {block_num}: {block_name} (ID={block_id})")
        print(f"  Offset: 0x{offset:04X}")
        print(f"  Size: {block_size} bytes")
        print(f"  Data: 0x{block_data_start:04X} - 0x{block_data_end:04X}")

        # Show first 32 bytes of block data
        preview_len = min(32, block_size)
        preview = ' '.join(f'{b:02X}' for b in data[block_data_start:block_data_start + preview_len])
        print(f"  Preview: {preview}...")
        print()

        offset += 2 + block_size
        block_num += 1

        if block_num > 20:
            print("... (limiting output)")
            break


def main():
    reference_file = 'learnings/Laxity - Stinsen - Last Night Of 89.sf2'

    print("=" * 70)
    print("SF2 FORMAT ANALYSIS")
    print("=" * 70)
    print()

    parse_sf2_file(reference_file)

    print()
    print("=" * 70)
    print("NEXT: Use this structure to inject sequences")
    print("=" * 70)


if __name__ == '__main__':
    main()
