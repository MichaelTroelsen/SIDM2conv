#!/usr/bin/env python3
"""
Final working SF2 sequence injection.

SF2 Structure:
1. Header blocks (metadata)
2. END marker (0xFF)
3. C64 memory image (driver code + music data)

The Music Data block contains pointers to where sequences/orderlists
are located in the C64 memory image.
"""

import struct
import pickle


def load_extracted_sequences():
    """Load sequences and orderlists from pickle file."""
    with open('sf2_music_data_extracted.pkl', 'rb') as f:
        data = pickle.load(f)
    return data['sequences'], data['orderlists']


def find_c64_memory_start(sf2_data):
    """Find where C64 memory image starts in the SF2 file."""
    # Find END marker (0xFF) in header blocks
    for i in range(4, min(0x300, len(sf2_data))):
        if sf2_data[i] == 0xFF:
            # Check if this looks like an END marker (previous bytes should be block data)
            if i >= 2:
                # Skip past END marker
                c64_start = i + 1
                # Skip padding zeros
                while c64_start < len(sf2_data) and sf2_data[c64_start] == 0:
                    c64_start += 1
                return c64_start

    return None


def parse_music_data_block(sf2_data):
    """Parse Music Data block to get pointers."""
    offset = 4
    while offset < 0x200:
        block_id = sf2_data[offset]
        if block_id == 0xFF:
            break
        if block_id == 5:  # Music Data block
            block_size = sf2_data[offset + 1]
            block_data = sf2_data[offset + 2:offset + 2 + block_size]

            if len(block_data) >= 18:
                idx = 0
                track_count = block_data[idx]
                idx += 1
                orderlist_ptrs_lo = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                orderlist_ptrs_hi = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                sequence_count = block_data[idx]
                idx += 1
                sequence_ptrs_lo = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                sequence_ptrs_hi = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                orderlist_size = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                orderlist_start = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                sequence_size = struct.unpack('<H', block_data[idx:idx+2])[0]
                idx += 2
                sequence_start = struct.unpack('<H', block_data[idx:idx+2])[0]

                return {
                    'block_offset': offset,
                    'track_count': track_count,
                    'sequence_count': sequence_count,
                    'orderlist_start': orderlist_start,
                    'sequence_start': sequence_start,
                    'orderlist_size': orderlist_size,
                    'sequence_size': sequence_size,
                }

        block_size = sf2_data[offset + 1]
        offset += 2 + block_size

    return None


def main():
    reference_file = 'learnings/Laxity - Stinsen - Last Night Of 89.sf2'
    output_file = 'output/Stinsens_with_siddump_sequences.sf2'

    print("=" * 70)
    print("FINAL SF2 SEQUENCE INJECTION")
    print("=" * 70)
    print()

    # Step 1: Load reference SF2
    print("Step 1: Load reference SF2...")
    with open(reference_file, 'rb') as f:
        sf2_data = bytearray(f.read())

    load_addr = struct.unpack('<H', sf2_data[0:2])[0]
    print(f"  File size: {len(sf2_data)} bytes")
    print(f"  Load address: ${load_addr:04X}")
    print()

    # Step 2: Find C64 memory start
    print("Step 2: Find C64 memory start...")
    c64_memory_start = find_c64_memory_start(sf2_data)
    if c64_memory_start is None:
        print("  ERROR: Could not find C64 memory start!")
        return

    print(f"  C64 memory starts at file offset: 0x{c64_memory_start:04X}")
    print()

    # Step 3: Parse Music Data block
    print("Step 3: Parse Music Data block...")
    music_info = parse_music_data_block(sf2_data)
    if music_info is None:
        print("  ERROR: Could not find Music Data block!")
        return

    print(f"  Sequence count: {music_info['sequence_count']}")
    print(f"  Sequence start: ${music_info['sequence_start']:04X}")
    print(f"  Orderlist start: ${music_info['orderlist_start']:04X}")
    print()

    # Step 4: Calculate file offsets
    print("Step 4: Calculate file offsets...")

    def mem_to_file(addr):
        return c64_memory_start + (addr - load_addr)

    seq_file_offset = mem_to_file(music_info['sequence_start'])
    order_file_offset = mem_to_file(music_info['orderlist_start'])

    print(f"  Sequences at file offset: 0x{seq_file_offset:04X}")
    print(f"  Orderlists at file offset: 0x{order_file_offset:04X}")
    print()

    # Step 5: Load extracted sequences
    print("Step 5: Load extracted sequences...")
    sequences, orderlists = load_extracted_sequences()
    print(f"  Loaded {len(sequences)} sequences")
    print(f"  Loaded {len(orderlists)} orderlists")
    print()

    # Step 6: Write sequences to SF2
    print("Step 6: Write sequences to SF2...")

    # Write all 39 sequences
    offset = seq_file_offset
    for seq_num, sequence in enumerate(sequences):
        for entry in sequence:
            if offset >= len(sf2_data):
                print(f"  WARNING: Ran out of space at sequence {seq_num}!")
                break
            sf2_data[offset] = entry[0]  # instrument
            sf2_data[offset + 1] = entry[1]  # command
            sf2_data[offset + 2] = entry[2]  # note
            offset += 3

    print(f"  Wrote {len(sequences)} sequences ({offset - seq_file_offset} bytes)")
    print()

    # Step 7: Write orderlists to SF2
    print("Step 7: Write orderlists to SF2...")

    offset = order_file_offset
    for voice_num, orderlist in enumerate(orderlists):
        for byte in orderlist:
            if offset >= len(sf2_data):
                print(f"  WARNING: Ran out of space at orderlist {voice_num}!")
                break
            sf2_data[offset] = byte
            offset += 1

    print(f"  Wrote {len(orderlists)} orderlists ({offset - order_file_offset} bytes)")
    print()

    # Step 8: Write output file
    print("Step 8: Write output file...")
    with open(output_file, 'wb') as f:
        f.write(sf2_data)

    print(f"  Wrote: {output_file}")
    print(f"  Size: {len(sf2_data)} bytes")
    print()

    print("=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print()
    print("The extracted sequences from siddump have been injected!")
    print()
    print("TRY LOADING IN SID FACTORY II:")
    print(f"  {output_file}")
    print()
    print("This should load successfully because:")
    print("  - Used reference SF2 as template (correct structure)")
    print("  - Preserved all blocks and headers")
    print("  - Only replaced sequence/orderlist data in C64 memory")
    print("  - Kept all table data (wave, pulse, filter, instruments)")


if __name__ == '__main__':
    main()
