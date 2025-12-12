#!/usr/bin/env python3
"""
Simple approach: Take the reference SF2 and inject our extracted sequences.

This preserves the working structure and just replaces the sequence data.
"""

import pickle
import struct


def load_extracted_sequences():
    """Load sequences and orderlists from pickle file."""
    with open('sf2_music_data_extracted.pkl', 'rb') as f:
        data = pickle.load(f)
    return data['sequences'], data['orderlists']


def find_music_data_block(sf2_data):
    """Find Block 5 (Music Data) in SF2 file."""
    # SF2 format: blocks are [block_id] [size_lo] [size_hi] [data...]
    offset = 0

    while offset < len(sf2_data):
        if offset + 3 > len(sf2_data):
            break

        block_id = sf2_data[offset]

        if block_id == 0xFF:  # End block
            break

        if block_id == 0:  # Skip padding
            offset += 1
            continue

        size = sf2_data[offset + 1] | (sf2_data[offset + 2] << 8)

        if block_id == 5:  # Music Data block
            print(f"  Found Block 5 at offset 0x{offset:04X}")
            print(f"  Block size: {size} bytes")
            return offset, size

        offset += 3 + size

    return None, None


def write_sequences_to_block(sequences, orderlists):
    """
    Write sequences and orderlists to a block of data.

    Returns the music data block content (without block header).
    """
    data = bytearray()

    # Write 39 sequences
    print("  Writing 39 sequences...")
    for seq_num, sequence in enumerate(sequences):
        for entry in sequence:
            data.append(entry[0])  # instrument
            data.append(entry[1])  # command
            data.append(entry[2])  # note

    print(f"  Sequences total: {len(data)} bytes")

    # Write 3 orderlists
    print("  Writing 3 orderlists...")
    orderlist_start = len(data)

    for voice_num, orderlist in enumerate(orderlists):
        for byte in orderlist:
            data.append(byte)

    print(f"  Orderlists total: {len(data) - orderlist_start} bytes")
    print(f"  Music data total: {len(data)} bytes")

    return data


def main():
    reference_file = 'learnings/Laxity - Stinsen - Last Night Of 89.sf2'
    output_file = 'output/Stinsens_with_extracted_sequences.sf2'

    print("=" * 70)
    print("INJECTING EXTRACTED SEQUENCES INTO REFERENCE SF2")
    print("=" * 70)
    print()

    # Step 1: Load reference SF2
    print("Step 1: Load reference SF2...")
    with open(reference_file, 'rb') as f:
        sf2_data = bytearray(f.read())

    print(f"  Reference size: {len(sf2_data)} bytes")
    print()

    # Step 2: Find music data block
    print("Step 2: Find music data block...")
    block_offset, block_size = find_music_data_block(sf2_data)

    if block_offset is None:
        print("  ERROR: Could not find music data block!")
        return

    print()

    # Step 3: Load extracted sequences
    print("Step 3: Load extracted sequences...")
    sequences, orderlists = load_extracted_sequences()
    print(f"  Loaded {len(sequences)} sequences")
    print(f"  Loaded {len(orderlists)} orderlists")
    print()

    # Step 4: Create new music data
    print("Step 4: Create new music data...")
    new_music_data = write_sequences_to_block(sequences, orderlists)
    print()

    # Step 5: Replace music data block
    print("Step 5: Replace music data in SF2...")

    # Calculate new block size
    new_block_size = len(new_music_data)
    old_block_end = block_offset + 3 + block_size

    print(f"  Old block size: {block_size} bytes")
    print(f"  New block size: {new_block_size} bytes")
    print(f"  Size difference: {new_block_size - block_size:+d} bytes")

    # Build new SF2 data
    new_sf2 = bytearray()

    # Copy everything before the block
    new_sf2.extend(sf2_data[:block_offset])

    # Write new block header
    new_sf2.append(5)  # Block ID
    new_sf2.append(new_block_size & 0xFF)  # Size low
    new_sf2.append((new_block_size >> 8) & 0xFF)  # Size high

    # Write new music data
    new_sf2.extend(new_music_data)

    # Copy everything after the old block
    new_sf2.extend(sf2_data[old_block_end:])

    print(f"  New SF2 size: {len(new_sf2)} bytes")
    print()

    # Step 6: Write output file
    print("Step 6: Write output file...")
    with open(output_file, 'wb') as f:
        f.write(new_sf2)

    print(f"  Wrote: {output_file}")
    print()

    print("=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print()
    print("The sequences from siddump have been injected into the reference SF2.")
    print("This preserves all the working table data (wave, pulse, filter, etc.)")
    print("and only replaces the sequences/orderlists with our extracted ones.")
    print()
    print("TRY LOADING IN SID FACTORY II:")
    print(f"  {output_file}")


if __name__ == '__main__':
    main()
