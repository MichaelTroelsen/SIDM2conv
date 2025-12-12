#!/usr/bin/env python3
"""
Extract sequences from SF2-packed SID and inject into Driver 11 SF2 format.

Based on findings:
1. SF2 sequences start at memory $0903 (Sequence Pointers section)
2. Sequences use contiguous stacking (variable length, like Tetris)
3. Format: 3 bytes per entry [Instrument] [Command] [Note]
4. Row numbers in orderlist display are byte offsets / 32 (?)

From analysis:
- In Stinsens SID: sequences found at 0x07FC-0x0A9A (670 bytes)
- In reference SF2: sequences start at file offset +0x007B after 123 zero bytes

Strategy:
1. Extract complete sequence region from SID file
2. Inject into SF2 file at correct location (memory $0903 + some offset)
"""

def extract_sequences_from_sid(sid_file):
    """Extract sequence table from SF2-packed SID file."""
    print(f"Reading: {sid_file}")

    with open(sid_file, 'rb') as f:
        data = f.read()

    # Based on analysis: sequences at 0x07FC-0x0A9A
    seq_start = 0x07FC
    seq_end = 0x0A9A

    sequences = data[seq_start:seq_end]

    print(f"Extracted {len(sequences)} bytes of sequence data")
    print(f"  Start: 0x{seq_start:04X}")
    print(f"  End: 0x{seq_end:04X}")

    # Show first few entries
    print(f"\nFirst 10 entries:")
    for i in range(min(10, len(sequences) // 3)):
        offset = i * 3
        inst = sequences[offset]
        cmd = sequences[offset+1]
        note = sequences[offset+2]

        note_str = f"{note:02X}"
        if note == 0x7E:
            note_str = "7E (+++)"
        elif note == 0x7F:
            note_str = "7F (END)"
        elif note == 0x80:
            note_str = "80 (---)"

        print(f"  +0x{offset:04X}: [{inst:02X}] [{cmd:02X}] [{note_str}]")

    return sequences

def inject_sequences_into_sf2(sf2_template, sequences, output_file):
    """Inject sequences into SF2 file."""
    print(f"\nReading template: {sf2_template}")

    with open(sf2_template, 'rb') as f:
        sf2_data = bytearray(f.read())

    load_addr = sf2_data[0] | (sf2_data[1] << 8)
    print(f"SF2 load address: ${load_addr:04X}")

    # Sequence section is at memory $0903
    # For load address $0D7E, this is BEFORE the file data
    # So we need to figure out where sequences actually go in the file

    # From reference file analysis: sequences start at +0x007B
    # Let's use the same offset
    seq_section_start = 0x0903

    # Calculate file offset
    # The sequence section starts at a fixed memory location
    # For files loaded at $0D7E, we need to find where $0903 maps to in the file

    # Actually, looking at the reference file, sequences appear to start
    # around file offset that corresponds to memory address in the loaded song

    # For now, let's try to find the existing sequence pattern (7E 80 repeating)
    # and replace it

    pattern = bytes([0x7E, 0x80])
    pattern_pos = sf2_data.find(pattern)

    if pattern_pos >= 0:
        print(f"Found template sequence pattern at file offset 0x{pattern_pos:04X}")

        # Replace template sequences with extracted sequences
        # Make sure we don't overflow
        if pattern_pos + len(sequences) <= len(sf2_data):
            sf2_data[pattern_pos:pattern_pos+len(sequences)] = sequences
            print(f"Injected {len(sequences)} bytes of sequences at 0x{pattern_pos:04X}")
        else:
            print(f"ERROR: Sequences too large ({len(sequences)} bytes) for available space")
            return None
    else:
        print("ERROR: Could not find sequence pattern in template")
        return None

    # Write output
    with open(output_file, 'wb') as f:
        f.write(sf2_data)

    print(f"\n[OK] Saved: {output_file}")
    print(f"     Size: {len(sf2_data)} bytes")

    return output_file

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'
    template_file = 'output/Stinsens_Last_Night_of_89_WITH_ORDERLISTS_EXPANDED.sf2'
    output_file = 'output/Stinsens_Last_Night_of_89_WITH_SEQUENCES.sf2'

    print("=" * 70)
    print("EXTRACT AND INJECT SEQUENCES")
    print("=" * 70 + "\n")

    # Extract sequences from SID file
    sequences = extract_sequences_from_sid(sid_file)

    # Save extracted sequences for inspection
    seq_bin_file = 'output/sequences_extracted.bin'
    with open(seq_bin_file, 'wb') as f:
        f.write(sequences)
    print(f"\n[OK] Saved extracted sequences: {seq_bin_file}")

    # Inject into SF2 template
    result = inject_sequences_into_sf2(template_file, sequences, output_file)

    if result:
        print("\n[SUCCESS] Sequence injection complete!")
        print(f"\nTest the file in SID Factory II:")
        print(f"  {output_file}")
    else:
        print("\n[FAILED] Sequence injection failed")

if __name__ == '__main__':
    main()
