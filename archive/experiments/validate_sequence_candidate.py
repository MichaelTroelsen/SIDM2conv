#!/usr/bin/env python3
"""
Validate the sequence candidate at file offset 0x0800.

This script:
1. Extracts sequences starting from 0x0800
2. Splits them by end markers (0x7F, 0xFF in note column)
3. Maps them to sequence numbers (0-38)
4. Cross-references with orderlist usage
"""

def mem_to_file_offset(mem_addr):
    """Convert memory address to file offset."""
    return 0x7E + (mem_addr - 0x1000)

def file_to_mem_addr(file_offset):
    """Convert file offset to memory address."""
    return 0x1000 + (file_offset - 0x7E)

def read_orderlist(data, start_offset):
    """Read and decode orderlist."""
    entries = []
    i = start_offset
    current_transpose = 0xA0

    while i < len(data):
        byte = data[i]

        if byte == 0xFF or byte == 0xFE:
            break

        # Transpose marker
        if byte >= 0xA0:
            current_transpose = byte
            if i + 1 < len(data):
                seq_num = data[i+1]
                entries.append({'transpose': byte, 'sequence': seq_num, 'offset': i - start_offset})
                i += 2
            else:
                break
        else:
            # Sequence number
            entries.append({'transpose': current_transpose, 'sequence': byte, 'offset': i - start_offset})
            i += 1

    return entries

def extract_sequences_from_candidate(data, start_offset, max_sequences=39):
    """
    Extract sequences from candidate location.

    Sequences are 3-byte entries: [Instrument] [Command] [Note]
    They end with markers in the note column:
    - 0x7F = END
    - 0xFF = LOOP
    - 0x80 = GATE OFF (continues)
    """
    sequences = []
    current_seq = []
    offset = start_offset
    seq_num = 0

    while offset + 2 < len(data) and seq_num < max_sequences:
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
        else:
            offset += 3

        # Safety check - if we've gone too far, stop
        if offset - start_offset > 4000:  # Increased limit
            break

    return sequences

def format_note(note):
    """Format note byte for display."""
    if note == 0x7E:
        return "7E (+++)"
    elif note == 0x7F:
        return "7F (END)"
    elif note == 0x80:
        return "80 (---)"
    elif note == 0xFF:
        return "FF (LOOP)"
    elif note >= 0xA0:
        return f"{note:02X} (TRAN)"
    else:
        return f"{note:02X}"

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("SEQUENCE CANDIDATE VALIDATION")
    print("=" * 70)
    print()

    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"File: {sid_file}")
    print(f"Size: {len(data)} bytes")
    print()

    # Read orderlists to know which sequences are used
    print("=" * 70)
    print("STEP 1: READ ORDERLISTS TO KNOW WHAT WE'RE LOOKING FOR")
    print("=" * 70)
    print()

    orderlist_offsets = {
        'Voice 0': 0x0AEE,
        'Voice 1': 0x0B1A,
        'Voice 2': 0x0B31
    }

    all_sequences_used = set()
    orderlist_details = {}

    for voice, offset in orderlist_offsets.items():
        entries = read_orderlist(data, offset)
        sequences = [e['sequence'] for e in entries]
        all_sequences_used.update(sequences)
        orderlist_details[voice] = {
            'sequences': sequences,
            'unique': set(sequences)
        }

        print(f"{voice}:")
        print(f"  Uses sequences: {sorted(set(sequences))}")
        print(f"  First 10 entries: {sequences[:10]}")
        print()

    print(f"TOTAL: Need to find {len(all_sequences_used)} unique sequences (0-38)")
    print()

    # Extract sequences from candidate location
    print("=" * 70)
    print("STEP 2: EXTRACT SEQUENCES FROM CANDIDATE (0x0800)")
    print("=" * 70)
    print()

    candidate_offset = 0x0800
    sequences = extract_sequences_from_candidate(data, candidate_offset)

    print(f"Extracted {len(sequences)} sequences from file offset 0x{candidate_offset:04X}")
    print(f"Memory address: ${file_to_mem_addr(candidate_offset):04X}")
    print()

    # Show summary
    print("=" * 70)
    print("SEQUENCE SUMMARY")
    print("=" * 70)
    print()

    for seq in sequences[:15]:  # Show first 15
        print(f"Sequence {seq['number']:02d}:")
        print(f"  File offset: 0x{seq['start_offset']:04X} - 0x{seq['end_offset']:04X}")
        print(f"  Length: {seq['length']} bytes ({len(seq['entries'])} entries)")
        print(f"  End marker: {seq['end_marker']}")
        print(f"  First 3 entries:")
        for i, entry in enumerate(seq['entries'][:3]):
            print(f"    [{entry['inst']:02X}] [{entry['cmd']:02X}] [{format_note(entry['note'])}]")
        print()

    if len(sequences) > 15:
        print(f"... and {len(sequences) - 15} more sequences")
        print()

    # Cross-reference with orderlist usage
    print("=" * 70)
    print("STEP 3: CROSS-REFERENCE WITH ORDERLIST USAGE")
    print("=" * 70)
    print()

    if len(sequences) >= 39:
        print(f"[OK] Found {len(sequences)} sequences (need 39)")
        print()

        # Check if all needed sequences are present
        missing = []
        for seq_num in all_sequences_used:
            if seq_num >= len(sequences):
                missing.append(seq_num)

        if missing:
            print(f"[MISSING] Sequences not found: {missing}")
        else:
            print(f"[OK] All 39 needed sequences are present (0-38)")
        print()

        # Show which sequences are used by which voice
        print("Sequence usage by voice:")
        for voice, details in orderlist_details.items():
            print(f"\n{voice}:")
            for seq_num in sorted(details['unique'])[:10]:  # First 10
                if seq_num < len(sequences):
                    seq = sequences[seq_num]
                    print(f"  Seq {seq_num:02d}: {len(seq['entries'])} entries, ends with {seq['end_marker']}")

    else:
        print(f"[INCOMPLETE] Only found {len(sequences)} sequences (need 39)")
        print(f"  This location may not be correct, or sequences are stored differently")

    print()
    print("=" * 70)
    print("DETAILED SEQUENCE 0 (First sequence)")
    print("=" * 70)
    print()

    if sequences:
        seq0 = sequences[0]
        print(f"Sequence 0 is used by: Voice 1")
        print(f"Location: 0x{seq0['start_offset']:04X} - 0x{seq0['end_offset']:04X}")
        print(f"Length: {len(seq0['entries'])} entries")
        print()
        print("All entries:")
        for i, entry in enumerate(seq0['entries']):
            print(f"  +{i*3:03d}: [{entry['inst']:02X}] [{entry['cmd']:02X}] [{format_note(entry['note'])}]")

    print()
    print("=" * 70)
    print("CONCLUSION")
    print("=" * 70)
    print()

    if len(sequences) >= 39:
        print("SUCCESS! This appears to be the correct sequence location!")
        print()
        print("Next steps:")
        print("1. Extract all 39 sequences from this location")
        print("2. Inject into Driver 11 SF2 format")
        print("3. Test the conversion")
    else:
        print("UNCERTAIN - Need more investigation:")
        print(f"- Only found {len(sequences)} sequences")
        print("- Sequences may not be stored contiguously")
        print("- May need to search for sequence pointer table")
        print("- Or try RetroDebugger to trace runtime behavior")
    print()

if __name__ == '__main__':
    main()
