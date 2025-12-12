#!/usr/bin/env python3
"""
Parse the Music Data block (Block 5) to understand the pointer structure.

Based on SF2Writer code (_parse_music_data_block):
- track_count (1 byte)
- orderlist_ptrs_lo (2 bytes)
- orderlist_ptrs_hi (2 bytes)
- sequence_count (1 byte)
- sequence_ptrs_lo (2 bytes)
- sequence_ptrs_hi (2 bytes)
- orderlist_size (2 bytes)
- orderlist_start (2 bytes)
- sequence_size (2 bytes)
- sequence_start (2 bytes)
"""

import struct


def parse_music_data_block(data):
    """Parse Music Data block."""
    if len(data) < 18:
        print("ERROR: Music Data block too small!")
        return

    idx = 0

    track_count = data[idx]
    print(f"Track count: {track_count}")
    idx += 1

    orderlist_ptrs_lo = struct.unpack('<H', data[idx:idx+2])[0]
    idx += 2
    print(f"Orderlist pointers (low bytes):  ${orderlist_ptrs_lo:04X}")

    orderlist_ptrs_hi = struct.unpack('<H', data[idx:idx+2])[0]
    idx += 2
    print(f"Orderlist pointers (high bytes): ${orderlist_ptrs_hi:04X}")

    sequence_count = data[idx]
    print(f"Sequence count: {sequence_count}")
    idx += 1

    sequence_ptrs_lo = struct.unpack('<H', data[idx:idx+2])[0]
    idx += 2
    print(f"Sequence pointers (low bytes):  ${sequence_ptrs_lo:04X}")

    sequence_ptrs_hi = struct.unpack('<H', data[idx:idx+2])[0]
    idx += 2
    print(f"Sequence pointers (high bytes): ${sequence_ptrs_hi:04X}")

    orderlist_size = struct.unpack('<H', data[idx:idx+2])[0]
    idx += 2
    print(f"Orderlist size: {orderlist_size} bytes")

    orderlist_start = struct.unpack('<H', data[idx:idx+2])[0]
    idx += 2
    print(f"Orderlist start: ${orderlist_start:04X}")

    if idx + 4 <= len(data):
        sequence_size = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        print(f"Sequence size: {sequence_size} bytes")

        sequence_start = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        print(f"Sequence start: ${sequence_start:04X}")

    return {
        'track_count': track_count,
        'orderlist_ptrs_lo': orderlist_ptrs_lo,
        'orderlist_ptrs_hi': orderlist_ptrs_hi,
        'sequence_count': sequence_count,
        'sequence_ptrs_lo': sequence_ptrs_lo,
        'sequence_ptrs_hi': sequence_ptrs_hi,
        'orderlist_size': orderlist_size,
        'orderlist_start': orderlist_start,
        'sequence_size': sequence_size if idx >= 16 else 0,
        'sequence_start': sequence_start if idx >= 18 else 0,
    }


def find_music_data_in_memory(sf2_data, load_addr, sequence_start, orderlist_start):
    """Find where sequences and orderlists are in the file."""
    # After the END marker (0xFF), the C64 memory image starts
    # Find the END marker
    end_marker_offset = None
    for i in range(len(sf2_data)):
        if sf2_data[i] == 0xFF:
            # Check if this is really the END block marker
            if i >= 4 and i < 0x200:  # Should be in header area
                # Check if previous data looks like a block
                if i >= 2:
                    block_id = sf2_data[i-2]
                    block_size = sf2_data[i-1]
                    if block_id in [1,2,3,4,5,6,7,8,9] and block_size < 255:
                        end_marker_offset = i
                        break

    if end_marker_offset is None:
        print("Could not find END marker!")
        return

    print()
    print(f"END marker at offset: 0x{end_marker_offset:04X}")

    # The C64 memory starts after padding
    # Find first non-zero byte after END marker
    c64_memory_start = end_marker_offset + 1
    while c64_memory_start < len(sf2_data) and sf2_data[c64_memory_start] == 0:
        c64_memory_start += 1

    print(f"C64 memory starts at offset: 0x{c64_memory_start:04X}")
    print(f"C64 load address: ${load_addr:04X}")
    print()

    # Calculate file offsets for sequences and orderlists
    def mem_to_file(addr):
        return c64_memory_start + (addr - load_addr)

    seq_file_offset = mem_to_file(sequence_start)
    order_file_offset = mem_to_file(orderlist_start)

    print(f"Sequences at memory ${sequence_start:04X} -> file offset 0x{seq_file_offset:04X}")
    print(f"Orderlists at memory ${orderlist_start:04X} -> file offset 0x{order_file_offset:04X}")
    print()

    # Show what's at those offsets
    if seq_file_offset < len(sf2_data):
        print("Sequence data preview:")
        for i in range(0, min(96, len(sf2_data) - seq_file_offset), 3):
            if seq_file_offset + i + 2 < len(sf2_data):
                inst = sf2_data[seq_file_offset + i]
                cmd = sf2_data[seq_file_offset + i + 1]
                note = sf2_data[seq_file_offset + i + 2]
                print(f"  [{inst:02X}] [{cmd:02X}] [{note:02X}]", end='')
                if note == 0x7F:
                    print("  <- END")
                    break
                else:
                    print()

    return c64_memory_start, mem_to_file


def main():
    reference_file = 'learnings/Laxity - Stinsen - Last Night Of 89.sf2'

    print("=" * 70)
    print("MUSIC DATA BLOCK ANALYSIS")
    print("=" * 70)
    print()

    with open(reference_file, 'rb') as f:
        sf2_data = f.read()

    # Find and parse Music Data block
    load_addr = struct.unpack('<H', sf2_data[0:2])[0]
    print(f"Load address: ${load_addr:04X}")
    print()

    # Find Block 5 (Music Data)
    offset = 4
    while offset < 0x200:
        block_id = sf2_data[offset]
        if block_id == 0xFF:
            break
        if block_id == 5:  # Music Data
            block_size = sf2_data[offset + 1]
            block_data = sf2_data[offset + 2:offset + 2 + block_size]

            print("Music Data Block:")
            print()
            info = parse_music_data_block(block_data)
            find_music_data_in_memory(sf2_data, load_addr, info['sequence_start'], info['orderlist_start'])
            break

        block_size = sf2_data[offset + 1]
        offset += 2 + block_size


if __name__ == '__main__':
    main()
