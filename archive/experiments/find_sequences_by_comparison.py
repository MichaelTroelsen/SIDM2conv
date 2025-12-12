#!/usr/bin/env python3
"""
Find sequence data in SF2-packed SID by comparing with reference SF2 file.

Strategy:
1. Extract sequence data from reference SF2 file (Driver 11 format)
2. Search for this data in the SF2-packed SID file
3. Report exact locations where matches are found
"""

def extract_sequences_from_reference_sf2(sf2_file):
    """Extract sequence data from reference SF2 file."""
    print(f"Reading reference SF2: {sf2_file}")

    with open(sf2_file, 'rb') as f:
        data = f.read()

    # In Driver 11 SF2 format, sequences start at memory $0903
    # For a file loaded at $0D7E:
    #   File offset = $0903 - $0D7E = negative, so sequences are in AUX section

    # Let's search for sequence pattern markers in the file
    # Look for the pattern of 3-byte entries with typical sequence markers

    # First, find load address
    load_addr = data[0] | (data[1] << 8)
    print(f"SF2 load address: ${load_addr:04X}")
    print(f"SF2 file size: {len(data)} bytes\n")

    # Search for sequence-like data (7E/80 markers, note values)
    print("Searching for sequence patterns in reference SF2...")

    candidates = []

    # Look for multiple consecutive 3-byte entries that look like sequences
    for offset in range(len(data) - 300):  # Need at least 300 bytes
        # Check if this looks like sequence data
        valid_count = 0

        for i in range(30):  # Check 30 entries (90 bytes)
            if offset + i*3 + 2 >= len(data):
                break

            inst = data[offset + i*3]
            cmd = data[offset + i*3 + 1]
            note = data[offset + i*3 + 2]

            # Validate entry
            inst_ok = inst <= 0x1F or inst >= 0x80 or inst == 0x7E
            note_ok = note <= 0x60 or note in [0x7E, 0x7F, 0x80, 0xFF]

            if inst_ok and note_ok:
                valid_count += 1

        if valid_count >= 25:  # At least 25/30 entries valid
            candidates.append((offset, valid_count))

    if candidates:
        print(f"Found {len(candidates)} sequence pattern candidates:\n")

        for i, (offset, score) in enumerate(candidates[:5]):
            print(f"Candidate {i+1}: Offset 0x{offset:04X} (score: {score}/30)")

            # Show first 10 entries
            print("  First 10 entries:")
            for j in range(10):
                if offset + j*3 + 2 >= len(data):
                    break

                inst = data[offset + j*3]
                cmd = data[offset + j*3 + 1]
                note = data[offset + j*3 + 2]

                note_str = f"{note:02X}"
                if note == 0x7E:
                    note_str = "7E (+++)"
                elif note == 0x7F:
                    note_str = "7F (END)"
                elif note == 0x80:
                    note_str = "80 (---)"
                elif note == 0xFF:
                    note_str = "FF (LOOP)"

                print(f"    +{j*3:02d}: [{inst:02X}] [{cmd:02X}] [{note_str}]")
            print()

        # Return the best candidate
        best = max(candidates, key=lambda x: x[1])
        seq_offset = best[0]

        # Extract a reasonable chunk (500 bytes for now)
        seq_data = data[seq_offset:seq_offset+500]

        return seq_data, seq_offset
    else:
        print("No sequence patterns found!")
        return None, None

def search_for_sequences_in_sid(sid_file, reference_seq):
    """Search for reference sequence data in SID file."""
    print(f"\nReading SID file: {sid_file}")

    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"SID file size: {len(data)} bytes")

    # Try to find the first 30 bytes of reference sequences
    search_len = min(30, len(reference_seq))
    pattern = reference_seq[:search_len]

    print(f"\nSearching for {search_len}-byte pattern from reference...")

    # Search for exact match
    pos = data.find(pattern)

    if pos >= 0:
        print(f"[MATCH FOUND] at file offset 0x{pos:04X}")

        # Calculate memory address (PSID header is 0x7E bytes, data loads at $1000)
        mem_addr = 0x1000 + (pos - 0x7E)
        print(f"              Memory address: ${mem_addr:04X}")

        return pos, mem_addr
    else:
        print("[NO EXACT MATCH] Searching for partial matches...")

        # Try shorter patterns
        for length in [20, 15, 12, 9]:
            pattern = reference_seq[:length]
            pos = data.find(pattern)

            if pos >= 0:
                mem_addr = 0x1000 + (pos - 0x7E)
                print(f"[PARTIAL MATCH] {length} bytes at offset 0x{pos:04X} (${mem_addr:04X})")
                return pos, mem_addr

        print("[FAILED] No matches found")
        return None, None

def main():
    reference_sf2 = 'learnings/Laxity - Stinsen - Last Night Of 89.sf2'
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("FIND SEQUENCES BY COMPARISON")
    print("=" * 70 + "\n")

    # Extract sequences from reference SF2
    ref_seq, ref_offset = extract_sequences_from_reference_sf2(reference_sf2)

    if ref_seq is None:
        print("Failed to extract reference sequences!")
        return

    print(f"[OK] Extracted reference sequences: {len(ref_seq)} bytes from offset 0x{ref_offset:04X}\n")

    # Search for this data in the SID file
    sid_offset, mem_addr = search_for_sequences_in_sid(sid_file, ref_seq)

    if sid_offset is not None:
        print(f"\n{'=' * 70}")
        print("SUCCESS - SEQUENCE LOCATION FOUND")
        print("=" * 70)
        print(f"\nSequences start at:")
        print(f"  File offset: 0x{sid_offset:04X}")
        print(f"  Memory addr: ${mem_addr:04X}")
        print(f"\nUse this address to extract sequences from the SID file.")
    else:
        print("\n[FAILED] Could not locate sequences in SID file")
        print("The data structure may be different between SF2 and SF2-packed formats")

if __name__ == '__main__':
    main()
