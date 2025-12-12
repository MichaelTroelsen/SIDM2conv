#!/usr/bin/env python3
"""
SF2 File Validator

Validates SF2 file structure to ensure it's not corrupted.
"""

import struct
import sys
from pathlib import Path


def validate_sf2_structure(sf2_path):
    """
    Validate SF2 file structure.

    Returns:
        (is_valid, errors, info)
    """
    errors = []
    info = {}

    try:
        with open(sf2_path, 'rb') as f:
            data = f.read()

        # Check file size
        if len(data) < 100:
            errors.append(f"File too small: {len(data)} bytes")
            return False, errors, info

        info['file_size'] = len(data)

        # Check load address (offset 0x00-0x01)
        load_addr = struct.unpack('<H', data[0:2])[0]
        info['load_addr'] = f"${load_addr:04X}"

        if load_addr < 0x0400 or load_addr > 0xFFFF:
            errors.append(f"Invalid load address: ${load_addr:04X}")

        # Check file ID (offset 0x02-0x03) - should be $1337
        file_id = struct.unpack('<H', data[2:4])[0]
        info['file_id'] = f"${file_id:04X}"

        if file_id != 0x1337:
            errors.append(f"Invalid file ID: ${file_id:04X} (expected $1337)")

        # Parse blocks
        offset = 4
        blocks_found = []
        end_marker_offset = None

        while offset < min(0x300, len(data)):
            block_id = data[offset]

            if block_id == 0xFF:
                end_marker_offset = offset
                info['end_marker_offset'] = f"${offset:04X}"
                break

            if offset + 1 >= len(data):
                errors.append(f"Unexpected EOF at block offset ${offset:04X}")
                break

            block_size = data[offset + 1]
            blocks_found.append({
                'id': block_id,
                'offset': offset,
                'size': block_size
            })

            offset += 2 + block_size

        info['blocks'] = len(blocks_found)
        info['block_list'] = ', '.join([f"ID{b['id']}" for b in blocks_found])

        if end_marker_offset is None:
            errors.append("END marker (0xFF) not found in header")

        # Find C64 memory start (first non-zero byte after END marker)
        if end_marker_offset:
            c64_start = end_marker_offset + 1
            while c64_start < len(data) and data[c64_start] == 0:
                c64_start += 1

            if c64_start < len(data):
                info['c64_memory_start'] = f"${c64_start:04X}"
                info['c64_memory_size'] = len(data) - c64_start
            else:
                errors.append("No C64 memory section found after END marker")

        # Check for Block 5 (Music Data)
        block5 = None
        for block in blocks_found:
            if block['id'] == 5:
                block5 = block
                break

        if block5:
            info['music_data_block'] = f"offset=${block5['offset']:04X}, size={block5['size']}"

            # Parse Music Data block
            block_offset = block5['offset'] + 2
            block_data = data[block_offset:block_offset + block5['size']]

            if len(block_data) >= 18:
                track_count = block_data[0]
                sequence_count = block_data[5]

                info['track_count'] = track_count
                info['sequence_count'] = sequence_count

                if track_count != 3:
                    errors.append(f"Invalid track count: {track_count} (expected 3)")
        else:
            errors.append("Music Data block (ID=5) not found")

        # Summary
        is_valid = len(errors) == 0

        return is_valid, errors, info

    except Exception as e:
        errors.append(f"Exception during validation: {e}")
        return False, errors, info


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_sf2.py <sf2_file>")
        sys.exit(1)

    sf2_file = sys.argv[1]

    if not Path(sf2_file).exists():
        print(f"Error: File not found: {sf2_file}")
        sys.exit(1)

    print(f"Validating: {sf2_file}")
    print("=" * 60)

    is_valid, errors, info = validate_sf2_structure(sf2_file)

    print("\nFile Information:")
    for key, value in info.items():
        print(f"  {key:20s}: {value}")

    if errors:
        print("\nValidation Errors:")
        for error in errors:
            print(f"  ✗ {error}")

    print("\n" + "=" * 60)
    if is_valid:
        print("✓ File is VALID")
        sys.exit(0)
    else:
        print(f"✗ File has {len(errors)} error(s)")
        sys.exit(1)


if __name__ == '__main__':
    main()
