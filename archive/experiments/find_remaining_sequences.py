#!/usr/bin/env python3
"""
Find the remaining 5 sequences (34-38) that weren't found in the first pass.
"""

def mem_to_file_offset(mem_addr):
    """Convert memory address to file offset."""
    return 0x7E + (mem_addr - 0x1000)

def file_to_mem_addr(file_offset):
    """Convert file offset to memory address."""
    return 0x1000 + (file_offset - 0x7E)

def extract_sequences_no_limit(data, start_offset):
    """Extract sequences without arbitrary limits."""
    sequences = []
    current_seq = []
    offset = start_offset
    seq_num = 0

    while offset + 2 < len(data):
        inst = data[offset]
        cmd = data[offset + 1]
        note = data[offset + 2]

        # Add entry to current sequence
        current_seq.append({
            'inst': inst,
            'cmd': cmd,
            'note': note,
            'offset': offset
        })

        # Check for end markers
        if note == 0x7F or note == 0xFF:
            # Sequence complete
            sequences.append({
                'number': seq_num,
                'start_offset': current_seq[0]['offset'],
                'end_offset': offset + 2,
                'length': len(current_seq) * 3,
                'entries': current_seq,
                'end_marker': 'END' if note == 0x7F else 'LOOP'
            })
            current_seq = []
            seq_num += 1
            offset += 3

            # Stop after finding 39 sequences
            if seq_num >= 39:
                break
        else:
            offset += 3

    return sequences

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("FINDING REMAINING SEQUENCES (34-38)")
    print("=" * 70)
    print()

    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"File: {sid_file}")
    print(f"Size: {len(data)} bytes")
    print()

    # Extract all sequences starting from 0x0800
    candidate_offset = 0x0800
    sequences = extract_sequences_no_limit(data, candidate_offset)

    print(f"Extracted {len(sequences)} sequences from file offset 0x{candidate_offset:04X}")
    print()

    if len(sequences) >= 39:
        print("[SUCCESS] Found all 39 sequences!")
        print()

        # Show the last 10 sequences (29-38)
        print("Last 10 sequences (29-38):")
        for seq in sequences[-10:]:
            print(f"\nSequence {seq['number']:02d}:")
            print(f"  File offset: 0x{seq['start_offset']:04X} - 0x{seq['end_offset']:04X}")
            print(f"  Memory addr: ${file_to_mem_addr(seq['start_offset']):04X} - ${file_to_mem_addr(seq['end_offset']):04X}")
            print(f"  Length: {seq['length']} bytes ({len(seq['entries'])} entries)")
            print(f"  End marker: {seq['end_marker']}")
            print(f"  First entry: [{seq['entries'][0]['inst']:02X}] [{seq['entries'][0]['cmd']:02X}] [{seq['entries'][0]['note']:02X}]")

        print()
        print("=" * 70)
        print(f"TOTAL RANGE: 0x{sequences[0]['start_offset']:04X} - 0x{sequences[-1]['end_offset']:04X}")
        print(f"Memory range: ${file_to_mem_addr(sequences[0]['start_offset']):04X} - ${file_to_mem_addr(sequences[-1]['end_offset']):04X}")
        total_size = sequences[-1]['end_offset'] - sequences[0]['start_offset'] + 1
        print(f"Total size: {total_size} bytes")
        print("=" * 70)
    else:
        print(f"[INCOMPLETE] Only found {len(sequences)} sequences")
        print()

        # Show where we stopped
        if sequences:
            last_seq = sequences[-1]
            print(f"Last sequence found: {last_seq['number']}")
            print(f"Ended at file offset: 0x{last_seq['end_offset']:04X}")
            print(f"Memory address: ${file_to_mem_addr(last_seq['end_offset']):04X}")
            print()
            print("Next bytes after last sequence:")
            offset = last_seq['end_offset'] + 1
            for i in range(min(60, len(data) - offset)):
                if i % 12 == 0:
                    print(f"\n  0x{offset+i:04X}: ", end='')
                print(f"{data[offset+i]:02X} ", end='')
            print()

if __name__ == '__main__':
    main()
