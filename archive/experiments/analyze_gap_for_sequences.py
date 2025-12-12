#!/usr/bin/env python3
"""
Analyze the 202-byte gap at $1954-$1A1D to see if it contains sequences.

The orderlists reference 39 sequences (0-38).
The gap has 202 bytes, which could fit 39 short sequences.
"""

def mem_to_file_offset(mem_addr):
    """Convert memory address to file offset."""
    return 0x7E + (mem_addr - 0x1000)

def file_to_mem_addr(file_offset):
    """Convert file offset to memory address."""
    return 0x1000 + (file_offset - 0x7E)

def try_extract_sequences(data, start_offset, num_sequences=39):
    """
    Try to extract sequences from the gap.

    Assume sequences are stored back-to-back, separated by end markers.
    """
    sequences = []
    offset = start_offset
    seq_num = 0

    while offset < len(data) and seq_num < num_sequences:
        seq_bytes = []
        max_seq_length = 100  # Safety limit

        # Extract until end marker
        for i in range(max_seq_length):
            if offset + 2 >= len(data):
                break

            b1 = data[offset]
            b2 = data[offset + 1]
            b3 = data[offset + 2]

            seq_bytes.extend([b1, b2, b3])
            offset += 3

            # Check for end markers in third byte position
            if b3 == 0x7F or b3 == 0xFF:
                # Found end marker
                sequences.append({
                    'number': seq_num,
                    'bytes': bytes(seq_bytes),
                    'length': len(seq_bytes)
                })
                seq_num += 1
                break

        # If we didn't find an end marker, the sequence might use a different format
        if len(seq_bytes) % 3 != 0 or len(seq_bytes) == max_seq_length * 3:
            # Didn't find proper end, skip this approach
            break

    return sequences

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("ANALYZING GAP FOR SEQUENCE DATA")
    print("=" * 70)
    print()

    with open(sid_file, 'rb') as f:
        data = f.read()

    # Gap between wave and filter tables
    gap_start_mem = 0x1954
    gap_end_mem = 0x1A1D
    gap_start_file = mem_to_file_offset(gap_start_mem)
    gap_end_file = mem_to_file_offset(gap_end_mem)

    print(f"Gap location:")
    print(f"  Memory: ${gap_start_mem:04X} - ${gap_end_mem:04X}")
    print(f"  File:   0x{gap_start_file:04X} - 0x{gap_end_file:04X}")
    print(f"  Size:   {gap_end_file - gap_start_file + 1} bytes")
    print()

    # Try to extract 39 sequences
    print("Attempting to extract 39 sequences...")
    sequences = try_extract_sequences(data, gap_start_file, 39)

    print(f"Found {len(sequences)} sequences with end markers")
    print()

    if sequences:
        print("First 10 sequences:")
        for seq in sequences[:10]:
            print(f"  Seq {seq['number']:02d}: {seq['length']} bytes")

            # Show first 12 bytes
            print(f"    ", end='')
            for i in range(min(12, len(seq['bytes']))):
                print(f"{seq['bytes'][i]:02X} ", end='')
            if len(seq['bytes']) > 12:
                print("...")
            else:
                print()

        if len(sequences) > 10:
            print(f"  ... and {len(sequences) - 10} more")

        print()
        print(f"Total bytes used: {sum(s['length'] for s in sequences)} / 202")
    else:
        print("No sequences found with this method.")
        print()
        print("The gap may not contain sequences, or they use a different format.")
        print()
        print("Alternative: Sequences might be stored elsewhere, or embedded in code.")

    # Check if gap data looks like sequence-style 3-byte entries
    print()
    print("=" * 70)
    print("RAW GAP DATA ANALYSIS")
    print("=" * 70)
    print()
    print("First 60 bytes as 3-byte groups:")

    for i in range(20):
        offset = gap_start_file + i * 3
        if offset + 2 < len(data):
            b1 = data[offset]
            b2 = data[offset + 1]
            b3 = data[offset + 2]
            print(f"  +{i*3:03d}: [{b1:02X}] [{b2:02X}] [{b3:02X}]")

    print()

if __name__ == '__main__':
    main()
