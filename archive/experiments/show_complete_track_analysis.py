#!/usr/bin/env python3
"""
Complete analysis showing:
1. Where orderlists are located
2. What they reference
3. Where tracks/sequences should start (Track 1, 2, 3)
"""

def decode_orderlist(data, start_offset, name):
    """Decode orderlist from SID file."""
    print(f"\n=== {name} ===")
    print(f"Location: 0x{start_offset:04X}\n")

    entries = []
    i = start_offset
    current_transpose = 0xA0  # Default transpose

    print("Raw bytes: ", end='')
    # Read until we hit an end marker or reasonable limit
    for j in range(50):
        if i >= len(data):
            break

        byte = data[i]
        print(f"{byte:02X} ", end='')

        if byte == 0xFF:
            print("(FF=loop)")
            if i + 1 < len(data):
                loop_target = data[i+1]
                print(f"Loop target: {loop_target:02X}")
            break
        elif byte == 0xFE:
            print("(FE=end)")
            break

        i += 1

        if j % 16 == 15:
            print()
            print("           ", end='')

    print(f"\n\nDecoded entries:")

    # Re-parse to decode
    i = start_offset
    entry_num = 0

    while i < len(data):
        byte = data[i]

        if byte == 0xFF or byte == 0xFE:
            break

        # Check if transpose marker
        if byte >= 0xA0:
            current_transpose = byte
            if i + 1 < len(data):
                seq_num = data[i+1]
                entries.append({'transpose': byte, 'sequence': seq_num})
                print(f"  Entry {entry_num:02d}: Transpose={byte:02X} Sequence={seq_num:02X}")
                i += 2
                entry_num += 1
            else:
                break
        else:
            # Sequence number with previous transpose
            entries.append({'transpose': current_transpose, 'sequence': byte})
            print(f"  Entry {entry_num:02d}: (Transpose={current_transpose:02X}) Sequence={byte:02X}")
            i += 1
            entry_num += 1

    # Get unique sequences
    sequences = sorted(set(e['sequence'] for e in entries))
    print(f"\nUnique sequences referenced: {len(sequences)}")
    print(f"  Sequence numbers: {' '.join(f'{s:02X}' for s in sequences)}")

    return entries, sequences

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("COMPLETE TRACK ANALYSIS")
    print("=" * 70)

    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"\nFile: {sid_file}")
    print(f"Size: {len(data)} bytes")
    print(f"Load address: ${data[0x7C] | (data[0x7D] << 8):04X}")

    # Known orderlist locations from STINSEN_CONVERSION_STATUS.md
    voice0_offset = 0x0AEE
    voice1_offset = 0x0B1A
    voice2_offset = 0x0B31

    # Decode each orderlist
    v0_entries, v0_seqs = decode_orderlist(data, voice0_offset, "VOICE 0 ORDERLIST")
    v1_entries, v1_seqs = decode_orderlist(data, voice1_offset, "VOICE 1 ORDERLIST")
    v2_entries, v2_seqs = decode_orderlist(data, voice2_offset, "VOICE 2 ORDERLIST")

    # Analyze all unique sequences
    all_seqs = sorted(set(v0_seqs + v1_seqs + v2_seqs))

    print(f"\n\n=== OVERALL SEQUENCE USAGE ===\n")
    print(f"Total unique sequences: {len(all_seqs)}")
    print(f"Sequence numbers: {' '.join(f'{s:02X}' for s in all_seqs)}\n")

    print("Distribution:")
    print(f"  Voice 0 uses: {len(v0_seqs)} sequences ({' '.join(f'{s:02X}' for s in v0_seqs)})")
    print(f"  Voice 1 uses: {len(v1_seqs)} sequences ({' '.join(f'{s:02X}' for s in v1_seqs)})")
    print(f"  Voice 2 uses: {len(v2_seqs)} sequences ({' '.join(f'{s:02X}' for s in v2_seqs)})")

    # Now the key question: are these sequence NUMBERS or BYTE OFFSETS?
    print(f"\n\n=== CRITICAL QUESTION ===\n")
    print("Are orderlist values SEQUENCE NUMBERS or BYTE OFFSETS?")
    print()
    print("Evidence for SEQUENCE NUMBERS:")
    print(f"  - Values range 0x00-0x{max(all_seqs):02X} (max = {max(all_seqs)})")
    print(f"  - This suggests {max(all_seqs)+1} separate sequences")
    print("  - Would need a sequence pointer table to map numbers->addresses")
    print()
    print("Evidence for BYTE OFFSETS:")
    print("  - But sequences are ~670 bytes total")
    print(f"  - Max sequence number {max(all_seqs):02X} = {max(all_seqs)} decimal")
    print("  - This is much smaller than 670!")
    print()
    print("CONCLUSION:")
    print("  These appear to be SEQUENCE NUMBERS, not byte offsets!")
    print("  We need to find the SEQUENCE POINTER TABLE that maps numbers to addresses!")
    print()
    print("In Driver 11 SF2 format:")
    print("  - Sequence Pointers section at $0903 contains:")
    print("    1. Pointer table (maps sequence numbers to addresses)")
    print("    2. Actual sequence data")
    print()
    print("We need to find:")
    print("  - Where is the pointer table in the SF2-packed SID file?")
    print("  - Where do the actual sequences start?")
    print(f"  - How to extract sequences {' '.join(f'{s:02X}' for s in all_seqs[:10])} etc.?")

if __name__ == '__main__':
    main()
