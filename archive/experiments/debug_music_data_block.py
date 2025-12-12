#!/usr/bin/env python3
"""
Debug script to inspect Music Data block in SF2 file
"""

import struct
from pathlib import Path

sf2_path = Path('output/SIDSF2player_Complete_Pipeline/SF2packed_Stinsens_Last_Night_of_89/New/SF2packed_Stinsens_Last_Night_of_89.sf2')

if not sf2_path.exists():
    print(f"File not found: {sf2_path}")
    exit(1)

with open(sf2_path, 'rb') as f:
    sf2_data = f.read()

print(f"SF2 file size: {len(sf2_data)} bytes")
print()

load_addr = struct.unpack('<H', sf2_data[0:2])[0]
print(f"Load address: ${load_addr:04X}")
print()

# Find C64 memory start
c64_memory_start = None
for i in range(4, min(0x300, len(sf2_data))):
    if sf2_data[i] == 0xFF:
        c64_start = i + 1
        while c64_start < len(sf2_data) and sf2_data[c64_start] == 0:
            c64_start += 1
        c64_memory_start = c64_start
        break

print(f"C64 memory start (file offset): {c64_memory_start} (0x{c64_memory_start:04X})")
print()

# Parse blocks
offset = 4
block_num = 0
while offset < 0x200:
    block_id = sf2_data[offset]
    if block_id == 0xFF:
        print(f"Block {block_num}: END marker at offset {offset}")
        break

    block_size = sf2_data[offset + 1]
    print(f"Block {block_num}: ID={block_id}, size={block_size}, offset={offset}")

    if block_id == 5:  # Music Data block
        print("  *** MUSIC DATA BLOCK ***")
        block_data = sf2_data[offset + 2:offset + 2 + block_size]

        if len(block_data) >= 18:
            idx = 0
            track_count = block_data[idx]
            print(f"  TrackCount: {track_count}")
            idx += 1

            orderlist_ptrs_lo = struct.unpack('<H', block_data[idx:idx+2])[0]
            print(f"  OrderListPointersLowAddress: ${orderlist_ptrs_lo:04X}")
            idx += 2

            orderlist_ptrs_hi = struct.unpack('<H', block_data[idx:idx+2])[0]
            print(f"  OrderListPointersHighAddress: ${orderlist_ptrs_hi:04X}")
            idx += 2

            sequence_count = block_data[idx]
            print(f"  SequenceCount: {sequence_count}")
            idx += 1

            sequence_ptrs_lo = struct.unpack('<H', block_data[idx:idx+2])[0]
            print(f"  SequencePointersLowAddress: ${sequence_ptrs_lo:04X}")
            idx += 2

            sequence_ptrs_hi = struct.unpack('<H', block_data[idx:idx+2])[0]
            print(f"  SequencePointersHighAddress: ${sequence_ptrs_hi:04X}")
            idx += 2

            orderlist_size = struct.unpack('<H', block_data[idx:idx+2])[0]
            print(f"  OrderListSize: {orderlist_size} (0x{orderlist_size:04X})")
            idx += 2

            orderlist_track1 = struct.unpack('<H', block_data[idx:idx+2])[0]
            print(f"  OrderListTrack1Address: ${orderlist_track1:04X}")
            idx += 2

            sequence_size = struct.unpack('<H', block_data[idx:idx+2])[0]
            print(f"  SequenceSize: {sequence_size} (0x{sequence_size:04X})")
            idx += 2

            sequence_00 = struct.unpack('<H', block_data[idx:idx+2])[0]
            print(f"  Sequence00Address: ${sequence_00:04X}")
            print()

            # Calculate file offsets
            def mem_to_file(addr):
                return c64_memory_start + (addr - load_addr)

            print("  File offset calculations:")
            print(f"    Sequence 0: mem=${sequence_00:04X}, file=0x{mem_to_file(sequence_00):04X} ({mem_to_file(sequence_00)})")
            print(f"    Sequence 1: mem=${sequence_00 + sequence_size:04X}, file=0x{mem_to_file(sequence_00 + sequence_size):04X} ({mem_to_file(sequence_00 + sequence_size)})")
            print(f"    Sequence 3: mem=${sequence_00 + 3*sequence_size:04X}, file=0x{mem_to_file(sequence_00 + 3*sequence_size):04X} ({mem_to_file(sequence_00 + 3*sequence_size)})")
            print()

            # Check bounds
            seq_3_offset = mem_to_file(sequence_00 + 3 * sequence_size)
            if seq_3_offset + sequence_size > len(sf2_data):
                print(f"  ⚠️ PROBLEM: Sequence 3 would overflow file!")
                print(f"     Sequence 3 needs bytes [{seq_3_offset}, {seq_3_offset + sequence_size})")
                print(f"     But file is only {len(sf2_data)} bytes")
                print(f"     Overflow by: {(seq_3_offset + sequence_size) - len(sf2_data)} bytes")
            else:
                print(f"  ✓ Sequence 3 fits within file")

    block_num += 1
    offset += 2 + block_size

print()
print("Total file size:", len(sf2_data), "bytes")
