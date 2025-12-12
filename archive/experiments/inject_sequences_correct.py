#!/usr/bin/env python3
"""
Inject correctly extracted sequences into Driver 11 SF2 format.

Based on corrected extraction:
- Track 1 (Voice 0): 43 bytes from $1A70-$1A9B
- Track 2 (Voice 1): 24 bytes from $1A9B-$1AB3
- Track 3 (Voice 2): 59 bytes from $1AB3-$1AEE
- Total: 126 bytes (stacked contiguously)

The sequences are injected by finding the pattern marker (0x7E 0x80) in the
SF2 template and replacing it with the extracted sequence data.
"""

def load_extracted_tracks():
    """Load the three extracted track files."""
    print("Loading extracted tracks...")

    with open('output/track1_sequences.bin', 'rb') as f:
        track1 = f.read()

    with open('output/track2_sequences.bin', 'rb') as f:
        track2 = f.read()

    with open('output/track3_sequences.bin', 'rb') as f:
        track3 = f.read()

    print(f"  Track 1: {len(track1)} bytes")
    print(f"  Track 2: {len(track2)} bytes")
    print(f"  Track 3: {len(track3)} bytes")

    # Combine into contiguous block
    all_sequences = track1 + track2 + track3

    print(f"  Total: {len(all_sequences)} bytes\n")

    return all_sequences

def inject_sequences_into_sf2(sf2_template, sequences, output_file):
    """Inject sequences into SF2 file."""
    print(f"Reading template: {sf2_template}")

    with open(sf2_template, 'rb') as f:
        sf2_data = bytearray(f.read())

    load_addr = sf2_data[0] | (sf2_data[1] << 8)
    print(f"SF2 load address: ${load_addr:04X}")
    print(f"Template size: {len(sf2_data)} bytes\n")

    # Find the sequence pattern marker (7E 80 repeating)
    pattern = bytes([0x7E, 0x80])
    pattern_pos = sf2_data.find(pattern)

    if pattern_pos >= 0:
        print(f"Found sequence pattern at file offset 0x{pattern_pos:04X}")

        # Replace template sequences with extracted sequences
        if pattern_pos + len(sequences) <= len(sf2_data):
            sf2_data[pattern_pos:pattern_pos+len(sequences)] = sequences
            print(f"Injected {len(sequences)} bytes at 0x{pattern_pos:04X}")

            # Show first few entries of injected data
            print(f"\nFirst 10 injected entries:")
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
                elif note == 0xFF:
                    note_str = "FF (LOOP)"

                print(f"  +0x{offset:04X}: [{inst:02X}] [{cmd:02X}] [{note_str}]")
        else:
            print(f"ERROR: Sequences too large ({len(sequences)} bytes)")
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
    template_file = 'output/Stinsens_Last_Night_of_89_WITH_ORDERLISTS_EXPANDED.sf2'
    output_file = 'output/Stinsens_Last_Night_of_89_WITH_SEQUENCES_CORRECT.sf2'

    print("=" * 70)
    print("INJECT CORRECTED SEQUENCES")
    print("=" * 70 + "\n")

    # Load the three extracted tracks
    sequences = load_extracted_tracks()

    # Save combined sequences for inspection
    seq_bin_file = 'output/sequences_combined_correct.bin'
    with open(seq_bin_file, 'wb') as f:
        f.write(sequences)
    print(f"[OK] Saved combined sequences: {seq_bin_file}\n")

    # Inject into SF2 template
    result = inject_sequences_into_sf2(template_file, sequences, output_file)

    if result:
        print("\n" + "=" * 70)
        print("[SUCCESS] Sequence injection complete!")
        print("=" * 70)
        print(f"\nTest the file in SID Factory II:")
        print(f"  {output_file}\n")
    else:
        print("\n[FAILED] Sequence injection failed")

if __name__ == '__main__':
    main()
