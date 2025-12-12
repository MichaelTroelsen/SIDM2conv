#!/usr/bin/env python3
"""
Read the 3 sequence pointers and extract sequence data for each voice.

Based on disassembly:
- $199F-$19A0: Voice 1 sequence pointer
- $19A1-$19A2: Voice 2 sequence pointer
- $19A3-$19A4: Voice 3 sequence pointer
"""

def read_pointers(data):
    """Read the 3 sequence pointers."""
    # PSID header is 0x7E bytes
    # Memory address $199F = file offset 0x7E + ($199F - $1000)
    ptr_offset = 0x7E + (0x199F - 0x1000)  # = 0x7E + 0x99F = 0xA1D

    print(f"Reading sequence pointers at file offset 0x{ptr_offset:04X} (memory $199F):\n")

    pointers = []
    for i in range(3):
        offset = ptr_offset + (i * 2)
        lo = data[offset]
        hi = data[offset + 1]
        ptr = lo | (hi << 8)

        pointers.append(ptr)
        print(f"Voice {i+1} pointer: ${ptr:04X} (file offset 0x{ptr - 0x1000 + 2:04X})")

    return pointers

def extract_voice_sequences(data, voice_num, start_ptr, end_boundary):
    """Extract all sequences for one voice."""
    print(f"\n=== VOICE {voice_num} SEQUENCES ===\n")

    # Convert memory address to file offset
    # PSID header is 0x7E bytes, then data loads at $1000
    start_offset = 0x7E + (start_ptr - 0x1000)

    print(f"Start pointer: ${start_ptr:04X} (file offset 0x{start_offset:04X})")
    print(f"End boundary: 0x{end_boundary:04X}")
    print(f"Maximum size: {end_boundary - start_offset} bytes\n")

    # Extract until end boundary
    seq_data = data[start_offset:end_boundary]

    # Show first 100 bytes
    print("First 100 bytes (as 3-byte entries):\n")
    for i in range(min(33, len(seq_data) // 3)):
        offset = i * 3
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

        print(f"  +0x{offset:04X}: [{inst:02X}] [{cmd:02X}] [{note_str}]")

    return seq_data

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("SEQUENCE POINTER EXTRACTION")
    print("=" * 70 + "\n")

    with open(sid_file, 'rb') as f:
        data = f.read()

    load_addr = data[0x7C] | (data[0x7D] << 8)
    print(f"File: {sid_file}")
    print(f"Load address: ${load_addr:04X}")
    print(f"File size: {len(data)} bytes\n")

    # Read the 3 pointers
    pointers = read_pointers(data)

    # Known boundaries
    # From earlier analysis: tempo table ends at 0x0A9A
    # Orderlists start at 0x0AEE
    tempo_end = 0x0A9A
    orderlist_start = 0x0AEE

    print(f"\nKnown boundaries:")
    print(f"  Tempo table ends: 0x{tempo_end:04X}")
    print(f"  Orderlists start: 0x{orderlist_start:04X}\n")

    # Extract sequences for each voice
    # End each voice's sequences when we hit the next voice's pointer or a known boundary

    voice_sequences = []

    for i in range(3):
        voice_num = i + 1
        start_ptr = pointers[i]

        # Determine end boundary (as file offset)
        if i < 2:
            # End at next voice's pointer
            end_ptr = pointers[i+1]
            end_offset = 0x7E + (end_ptr - 0x1000)
        else:
            # Last voice - end at tempo table
            end_offset = tempo_end

        seq_data = extract_voice_sequences(data, voice_num, start_ptr, end_offset)
        voice_sequences.append(seq_data)

        # Save to file
        output_file = f'output/voice{voice_num}_sequences.bin'
        with open(output_file, 'wb') as f:
            f.write(seq_data)

        print(f"\n[OK] Saved: {output_file} ({len(seq_data)} bytes)")

    print(f"\n\n=== SUMMARY ===\n")
    print(f"Voice 1 sequences: {len(voice_sequences[0])} bytes")
    print(f"Voice 2 sequences: {len(voice_sequences[1])} bytes")
    print(f"Voice 3 sequences: {len(voice_sequences[2])} bytes")
    print(f"Total: {sum(len(v) for v in voice_sequences)} bytes")

if __name__ == '__main__':
    main()
