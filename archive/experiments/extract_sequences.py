#!/usr/bin/env python3
"""
Extract sequence table from Stinsens file.

Based on findings:
- High confidence sequence data at 0x0800-0x0900+ region
- Format: 3 bytes per entry [Instrument] [Command] [Note]
- Gate markers: 7E (gate toggle), 80 (gate off)
- End markers: FF
"""

def extract_sequences(data, start_offset, end_offset):
    """
    Extract individual sequences from contiguous sequence table.

    Sequences are variable length and stacked together.
    They're referenced by byte offset from orderlists.
    """
    sequences = []
    current_seq = []
    seq_start = start_offset
    offset = start_offset

    print(f"\nExtracting sequences from 0x{start_offset:04X} to 0x{end_offset:04X}...")
    print(f"Total region: {end_offset - start_offset} bytes ({(end_offset - start_offset) // 3} potential entries)\n")

    while offset < end_offset:
        if offset + 2 >= len(data):
            break

        inst = data[offset]
        cmd = data[offset+1]
        note = data[offset+2]

        entry = {
            'offset': offset,
            'byte_offset': offset - start_offset,  # Offset within sequence table
            'instrument': inst,
            'command': cmd,
            'note': note
        }

        # Add special markers
        if note == 0x7E:
            entry['marker'] = 'GATE (+++/---)'
        elif note == 0x80:
            entry['marker'] = '--- (gate off)'
        elif note == 0xFF:
            entry['marker'] = 'END (7F jump)'
        elif note == 0xFE:
            entry['marker'] = 'LOOP (7E)'

        current_seq.append(entry)

        # Check if this looks like end of sequence
        # Heuristic: FF note is likely end marker
        if note == 0xFF:
            sequences.append({
                'start_offset': seq_start,
                'byte_offset': seq_start - start_offset,
                'length': len(current_seq),
                'bytes': len(current_seq) * 3,
                'entries': current_seq.copy()
            })

            # Start new sequence
            offset += 3
            current_seq = []
            seq_start = offset
        else:
            offset += 3

    # Add any remaining sequence
    if current_seq:
        sequences.append({
            'start_offset': seq_start,
            'byte_offset': seq_start - start_offset,
            'length': len(current_seq),
            'bytes': len(current_seq) * 3,
            'entries': current_seq.copy()
        })

    return sequences

def print_sequence_table(sequences):
    """Print formatted sequence table."""
    print(f"=== Extracted {len(sequences)} Sequences ===\n")

    total_bytes = sum(seq['bytes'] for seq in sequences)
    print(f"Total sequence data: {total_bytes} bytes\n")

    for idx, seq in enumerate(sequences):
        print(f"Sequence #{idx:02d} (byte offset 0x{seq['byte_offset']:04X}, file offset 0x{seq['start_offset']:04X}):")
        print(f"  Length: {seq['length']} entries ({seq['bytes']} bytes)")

        # Show all entries for short sequences, first/last for long ones
        if seq['length'] <= 16:
            print(f"  Entries:")
            for entry in seq['entries']:
                marker = f" [{entry['marker']}]" if 'marker' in entry else ""
                print(f"    +0x{entry['byte_offset']:04X}: [{entry['instrument']:02X}] [{entry['command']:02X}] [{entry['note']:02X}]{marker}")
        else:
            print(f"  First 8 entries:")
            for entry in seq['entries'][:8]:
                marker = f" [{entry['marker']}]" if 'marker' in entry else ""
                print(f"    +0x{entry['byte_offset']:04X}: [{entry['instrument']:02X}] [{entry['command']:02X}] [{entry['note']:02X}]{marker}")

            print(f"  ... ({seq['length'] - 16} middle entries)")

            print(f"  Last 8 entries:")
            for entry in seq['entries'][-8:]:
                marker = f" [{entry['marker']}]" if 'marker' in entry else ""
                print(f"    +0x{entry['byte_offset']:04X}: [{entry['instrument']:02X}] [{entry['command']:02X}] [{entry['note']:02X}]{marker}")

        print()

def verify_with_orderlists(sequences):
    """
    Verify extracted sequences match orderlist references.

    From STINSEN_CONVERSION_STATUS.md:
    - Voice 0: 0E 0F 0F 0F 0F 11 01...
    - Voice 1: 00 12 06 06 06 07...
    - Voice 2: 0A 0A 0B 0C 0A 10...

    Expected row numbers: 0000, 0020, 0040, 0060, 0080, 00a0, 00c0, 00e0, 0140, 0160, 01c0, 0240
    These are byte offsets into sequence table!
    """
    print("\n=== Verifying against Orderlist References ===\n")

    expected_offsets = [0x0000, 0x0020, 0x0040, 0x0060, 0x0080, 0x00a0, 0x00c0, 0x00e0,
                        0x0140, 0x0160, 0x01c0, 0x0240]

    print("Expected sequence byte offsets (from row numbers):")
    print("  " + ", ".join(f"0x{off:04X}" for off in expected_offsets))
    print()

    print("Extracted sequence byte offsets:")
    extracted_offsets = [seq['byte_offset'] for seq in sequences]
    print("  " + ", ".join(f"0x{off:04X}" for off in extracted_offsets[:20]))
    if len(extracted_offsets) > 20:
        print(f"  ... ({len(extracted_offsets) - 20} more)")
    print()

    # Check matches
    matches = 0
    for exp_off in expected_offsets:
        if exp_off in extracted_offsets:
            idx = extracted_offsets.index(exp_off)
            matches += 1
            print(f"  [OK] 0x{exp_off:04X} matches Sequence #{idx:02d}")
        else:
            print(f"  [MISS] 0x{exp_off:04X} NOT FOUND")

    print(f"\nMatch rate: {matches}/{len(expected_offsets)} ({matches*100//len(expected_offsets)}%)")

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print(f"Reading: {sid_file}")
    with open(sid_file, 'rb') as f:
        data = f.read()

    # Based on analysis: sequences likely start around 0x0800
    # End before tempo table at 0x0A9A

    # Let's find exact boundaries by looking for first high-confidence region
    # and last valid sequence before tempo

    seq_start = 0x07FC  # Start a bit before 0x0800 to catch all data
    seq_end = 0x0A9A    # Tempo table starts here

    sequences = extract_sequences(data, seq_start, seq_end)
    print_sequence_table(sequences)
    verify_with_orderlists(sequences)

    # Save sequences to binary files
    print("\n=== Saving Sequences ===\n")

    # Save complete sequence table
    seq_data = data[seq_start:seq_end]
    output_file = 'output/sequences_complete.bin'
    with open(output_file, 'wb') as f:
        f.write(seq_data)
    print(f"[OK] Saved complete sequence table: {output_file} ({len(seq_data)} bytes)")

    # Also save index of sequence offsets
    index_file = 'output/sequence_offsets.txt'
    with open(index_file, 'w') as f:
        f.write("Sequence Index\n")
        f.write("=" * 50 + "\n\n")
        for idx, seq in enumerate(sequences):
            f.write(f"Sequence #{idx:02d}:\n")
            f.write(f"  File offset: 0x{seq['start_offset']:04X}\n")
            f.write(f"  Byte offset: 0x{seq['byte_offset']:04X}\n")
            f.write(f"  Length: {seq['length']} entries ({seq['bytes']} bytes)\n")
            f.write("\n")

    print(f"[OK] Saved sequence index: {index_file}")

if __name__ == '__main__':
    main()
