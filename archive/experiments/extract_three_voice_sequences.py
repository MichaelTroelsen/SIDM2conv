#!/usr/bin/env python3
"""
Extract the three voice sequences from Stinsen SID file.

Based on corrected understanding:
- Voice 0: $1A70 (file 0x0AEE)
- Voice 1: $1A9B (file 0x0B19)
- Voice 2: $1AB3 (file 0x0B31)

Each contains a continuous sequence of 3-byte entries until end marker.
"""

def mem_to_file_offset(mem_addr):
    """Convert memory address to file offset."""
    return 0x7E + (mem_addr - 0x1000)

def file_to_mem_addr(file_offset):
    """Convert file offset to memory address."""
    return 0x1000 + (file_offset - 0x7E)

def extract_voice_sequence(data, start_offset, max_bytes=2000):
    """
    Extract one voice sequence.

    Returns raw bytes until we hit an end marker or run out of data.
    """
    sequence_bytes = []
    offset = start_offset
    entries = 0

    while offset < len(data) and offset < start_offset + max_bytes:
        byte = data[offset]
        sequence_bytes.append(byte)

        # Check for end markers at appropriate positions
        # In 3-byte entries, check every 3rd byte for potential end markers
        if (len(sequence_bytes) - 2) % 3 == 0:  # Third byte of an entry
            if byte == 0xFF or byte == 0xFE:
                # Might be end marker
                # Read next byte to confirm
                if offset + 1 < len(data):
                    next_byte = data[offset + 1]
                    # If next byte is also 0xFF or 0x00, likely end of sequence
                    if next_byte in [0xFF, 0xFE, 0x00]:
                        break
                entries += 1

        offset += 1

    return bytes(sequence_bytes)

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
    print("EXTRACTING THREE VOICE SEQUENCES")
    print("=" * 70)
    print()

    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"File: {sid_file}")
    print(f"Size: {len(data)} bytes")
    print()

    # Voice locations
    voices = {
        'Voice 0': {'mem': 0x1A70, 'file': 0x0AEE},
        'Voice 1': {'mem': 0x1A9B, 'file': 0x0B19},
        'Voice 2': {'mem': 0x1AB3, 'file': 0x0B31}
    }

    extracted_sequences = {}

    for voice_name, locs in voices.items():
        print(f"=" * 70)
        print(f"{voice_name}")
        print(f"=" * 70)
        print(f"Memory address: ${locs['mem']:04X}")
        print(f"File offset: 0x{locs['file']:04X}")
        print()

        # Extract sequence
        sequence = extract_voice_sequence(data, locs['file'])

        print(f"Extracted {len(sequence)} bytes ({len(sequence)//3} entries as 3-byte groups)")
        print()

        # Show first 20 entries
        print("First 20 entries (as 3-byte groups):")
        for i in range(min(20, len(sequence) // 3)):
            offset = i * 3
            if offset + 2 < len(sequence):
                b1 = sequence[offset]
                b2 = sequence[offset + 1]
                b3 = sequence[offset + 2]

                # Format based on common patterns
                if b1 >= 0xA0:
                    print(f"  +{offset:03d}: [{b1:02X} TRAN] [{b2:02X}] [{format_note(b3)}]")
                else:
                    print(f"  +{offset:03d}: [{b1:02X}] [{b2:02X}] [{format_note(b3)}]")

        if len(sequence) // 3 > 20:
            print(f"  ... and {len(sequence)//3 - 20} more entries")

        print()

        # Show last 5 entries to see end marker
        print("Last 5 entries:")
        start_entry = max(0, len(sequence) // 3 - 5)
        for i in range(start_entry, len(sequence) // 3):
            offset = i * 3
            if offset + 2 < len(sequence):
                b1 = sequence[offset]
                b2 = sequence[offset + 1]
                b3 = sequence[offset + 2]

                if b1 >= 0xA0:
                    print(f"  +{offset:03d}: [{b1:02X} TRAN] [{b2:02X}] [{format_note(b3)}]")
                else:
                    print(f"  +{offset:03d}: [{b1:02X}] [{b2:02X}] [{format_note(b3)}]")

        print()

        # Save to extracted sequences
        extracted_sequences[voice_name] = sequence

    # Summary
    print("=" * 70)
    print("EXTRACTION SUMMARY")
    print("=" * 70)
    print()

    total_bytes = sum(len(seq) for seq in extracted_sequences.values())
    print(f"Voice 0: {len(extracted_sequences['Voice 0'])} bytes")
    print(f"Voice 1: {len(extracted_sequences['Voice 1'])} bytes")
    print(f"Voice 2: {len(extracted_sequences['Voice 2'])} bytes")
    print(f"TOTAL: {total_bytes} bytes")
    print()

    # Write to binary files for inspection
    for voice_name, sequence in extracted_sequences.items():
        filename = f"sequence_{voice_name.replace(' ', '_').lower()}.bin"
        with open(filename, 'wb') as f:
            f.write(sequence)
        print(f"Wrote {voice_name} to: {filename}")

    print()
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print()
    print("1. Inspect the extracted sequences to verify they look correct")
    print("2. Inject these three sequences into Driver 11 SF2 format")
    print("3. Test the conversion")
    print()

if __name__ == '__main__':
    main()
