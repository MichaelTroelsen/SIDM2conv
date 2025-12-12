#!/usr/bin/env python3
"""
ULTRATHINK: Reverse engineering based on packer code understanding.

KEY INSIGHT from packer_simple.cpp:
- Packer PRESERVES data structure
- Only RELOCATES code and data to new address
- Sequences remain in SF2 format, just moved!

Strategy:
1. Read reference SF2 to find original sequence locations
2. Calculate relocation delta
3. Find sequences at relocated address in SID
"""

import struct

def read_word_le(data, offset):
    """Read 16-bit little-endian word."""
    return data[offset] | (data[offset + 1] << 8)

def mem_to_file_offset(mem_addr, load_addr=0x1000):
    """Convert memory address to SID file offset."""
    return 0x7E + (mem_addr - load_addr)

def main():
    sf2_file = 'learnings/Laxity - Stinsen - Last Night Of 89.sf2'
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("FINDING RELOCATED SEQUENCES USING PACKER LOGIC")
    print("=" * 70)
    print()

    # Step 1: Read SF2 file to find original locations
    with open(sf2_file, 'rb') as f:
        sf2_data = f.read()

    # SF2 is a PRG file - first 2 bytes are load address
    sf2_load_addr = read_word_le(sf2_data, 0)
    print(f"SF2 original load address: ${sf2_load_addr:04X}")

    # SF2 actual data starts at offset 2 (after load address)
    sf2_music_data = sf2_data[2:]
    print(f"SF2 data size: {len(sf2_music_data)} bytes")
    print()

    # Step 2: Read SID file
    with open(sid_file, 'rb') as f:
        sid_data = f.read()

    # PSID header
    sid_load_addr = read_word_le(sid_data, 0x08)
    if sid_load_addr == 0:
        # Load address in data
        sid_load_addr = read_word_le(sid_data, 0x7C)

    print(f"SID load address: ${sid_load_addr:04X}")

    # SID music data starts after PSID header (0x7E)
    sid_music_data = sid_data[0x7E:]
    print(f"SID data size: {len(sid_music_data)} bytes")
    print()

    # Step 3: Calculate relocation
    relocation_delta = sid_load_addr - sf2_load_addr
    print(f"Relocation delta: ${relocation_delta:04X} ({relocation_delta:+d})")
    print()

    # Step 4: Parse SF2 header blocks to find sequence table location
    print("=" * 70)
    print("PARSING SF2 HEADER BLOCKS")
    print("=" * 70)
    print()

    offset = 0
    blocks_found = {}

    # Parse SF2 header blocks
    # Format: [block_id] [size_low] [size_high] [data...]
    while offset < len(sf2_music_data):
        if offset + 3 > len(sf2_music_data):
            break

        block_id = sf2_music_data[offset]

        if block_id == 0xFF:  # End block
            print("Found end block at offset", hex(offset))
            break

        if block_id == 0:
            offset += 1
            continue

        size = read_word_le(sf2_music_data, offset + 1)

        blocks_found[block_id] = {
            'offset': offset,
            'size': size,
            'data_offset': offset + 3
        }

        print(f"Block {block_id}: offset 0x{offset:04X}, size {size} bytes")

        offset += 3 + size

    print()

    # Step 5: Find Block 5 (Music Data - contains sequences + orderlists)
    if 5 in blocks_found:
        music_block = blocks_found[5]
        print("Found Block 5 (Music Data)!")
        print(f"  Offset in SF2: 0x{music_block['data_offset']:04X}")
        print(f"  Size: {music_block['size']} bytes")

        # This block contains sequences and orderlists
        # Extract it
        music_data = sf2_music_data[music_block['data_offset']:music_block['data_offset'] + music_block['size']]

        print()
        print("First 100 bytes of music data:")
        for i in range(0, min(100, len(music_data)), 16):
            print(f"  +{i:04X}: ", end='')
            for j in range(16):
                if i + j < len(music_data):
                    print(f"{music_data[i+j]:02X} ", end='')
            print()

        print()

        # Now find where this data is in the SID
        # The music data block starts at some offset in SF2
        # It should be at (sf2_load_addr + music_block['data_offset']) in memory
        # Relocated to (sid_load_addr + same_offset) in SID

        sf2_memory_addr = sf2_load_addr + music_block['data_offset']
        sid_memory_addr = sf2_memory_addr + relocation_delta
        sid_file_offset = mem_to_file_offset(sid_memory_addr, sid_load_addr)

        print(f"Music data in SF2 memory: ${sf2_memory_addr:04X}")
        print(f"Music data relocated to:  ${sid_memory_addr:04X}")
        print(f"SID file offset:          0x{sid_file_offset:04X}")
        print()

        # Verify by checking if the data matches
        if sid_file_offset + 20 < len(sid_data):
            print("Checking if data matches...")
            print("SF2 music data: ", end='')
            for i in range(20):
                print(f"{music_data[i]:02X} ", end='')
            print()

            print("SID at offset:  ", end='')
            for i in range(20):
                if sid_file_offset + i < len(sid_data):
                    print(f"{sid_data[sid_file_offset + i]:02X} ", end='')
            print()
            print()

    else:
        print("Block 5 (Music Data) not found in SF2!")
        print("Available blocks:", list(blocks_found.keys()))

if __name__ == '__main__':
    main()
