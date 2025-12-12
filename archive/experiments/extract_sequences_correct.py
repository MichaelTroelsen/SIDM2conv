#!/usr/bin/env python3
"""
Extract sequences correctly using the actual pointer locations.

Based on disassembly analysis:
- Sequence pointers at $1A1C-$1A21 (split format: low bytes, then high bytes)
- Voice 0: $1A70
- Voice 1: $1A9B
- Voice 2: $1AB3
"""

def mem_to_file_offset(mem_addr):
    """Convert memory address to file offset (PSID header is 0x7E bytes)."""
    return 0x7E + (mem_addr - 0x1000)

def extract_sequences(sid_file):
    """Extract sequences for all 3 voices."""
    print("=" * 70)
    print("SEQUENCE EXTRACTION (CORRECT METHOD)")
    print("=" * 70 + "\n")

    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"File: {sid_file}")
    print(f"Size: {len(data)} bytes\n")

    # Read the actual pointers from $1A1C-$1A21
    ptr_offset = mem_to_file_offset(0x1A1C)
    print(f"Reading pointers from memory $1A1C (file offset 0x{ptr_offset:04X}):\n")

    # Read split format: 3 low bytes, 3 high bytes
    low_bytes = []
    high_bytes = []

    for i in range(3):
        low_bytes.append(data[ptr_offset + i])
        high_bytes.append(data[ptr_offset + 3 + i])

    # Combine into pointers
    pointers = []
    for i in range(3):
        ptr = low_bytes[i] | (high_bytes[i] << 8)
        pointers.append(ptr)
        print(f"Voice {i} pointer: ${ptr:04X} (low=${low_bytes[i]:02X}, high=${high_bytes[i]:02X})")

    # Known boundaries
    # Orderlists start at $1AEE (this is where Voice 2 sequences end)
    orderlist_start = 0x1AEE

    print(f"\nKnown boundaries:")
    print(f"  Orderlists: ${orderlist_start:04X}\n")

    # Extract each voice's sequences
    voice_sequences = []

    for i in range(3):
        voice_num = i
        start_mem = pointers[i]
        start_offset = mem_to_file_offset(start_mem)

        # Determine end boundary
        if i < 2:
            # End at next voice's pointer
            end_mem = pointers[i+1]
            end_offset = mem_to_file_offset(end_mem)
        else:
            # Last voice - end at orderlist start
            end_mem = orderlist_start
            end_offset = mem_to_file_offset(end_mem)

        seq_size = end_offset - start_offset

        print(f"=== VOICE {voice_num} SEQUENCES ===")
        print(f"Memory: ${start_mem:04X} - ${end_mem:04X}")
        print(f"File offset: 0x{start_offset:04X} - 0x{end_offset:04X}")
        print(f"Size: {seq_size} bytes ({seq_size // 3} entries)\n")

        # Extract
        seq_data = data[start_offset:end_offset]

        # Show first 20 entries
        print("First 20 entries:")
        for j in range(min(20, len(seq_data) // 3)):
            offset = j * 3
            inst = seq_data[offset]
            cmd = seq_data[offset+1]
            note = seq_data[offset+2]

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

        voice_sequences.append(seq_data)

        # Save to file
        output_file = f'output/track{voice_num+1}_sequences.bin'
        with open(output_file, 'wb') as f:
            f.write(seq_data)

        print(f"\n[OK] Saved: {output_file}\n")

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\nTrack 1 (Voice 0): {len(voice_sequences[0])} bytes")
    print(f"Track 2 (Voice 1): {len(voice_sequences[1])} bytes")
    print(f"Track 3 (Voice 2): {len(voice_sequences[2])} bytes")
    print(f"Total: {sum(len(v) for v in voice_sequences)} bytes\n")

    return voice_sequences

if __name__ == '__main__':
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'
    sequences = extract_sequences(sid_file)
