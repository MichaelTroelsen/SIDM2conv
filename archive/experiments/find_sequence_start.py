#!/usr/bin/env python3
"""
Find the actual start of the sequence table.

Key insight from user: Row numbers should be:
  0000, 0020, 0040, 0060, 0080, 00a0, 00c0, 00e0, 0140, 0160, 01c0, 0240

In decimal: 0, 32, 64, 96, 128, 160, 192, 224, 320, 352, 448, 576

These might be:
1. Byte offsets (if each entry = 1 byte) - unlikely, entries are 3 bytes
2. Row offsets where row = 32 bytes - but that would be huge
3. Entry offsets where entry = 3 bytes - 0x0020 * 3 = 0x0060 (96 bytes)
4. Something else entirely

Let me test: if row 0x0020 means byte offset 0x0060 (0x0020 * 3 bytes/entry):
  0000 * 3 = 0x0000 (0)
  0020 * 3 = 0x0060 (96)
  0040 * 3 = 0x00C0 (192)
  0060 * 3 = 0x0120 (288)
  0080 * 3 = 0x0180 (384)
  ...

Actually, let me just search for a pattern that looks like valid sequence data.
"""

def score_sequence_validity(data, start, length=256):
    """Score how likely a region is to be sequence data."""
    if start + length > len(data):
        length = len(data) - start

    valid_count = 0
    total_count = 0

    for i in range(start, start + length, 3):
        if i + 2 >= len(data):
            break

        inst = data[i]
        cmd = data[i+1]
        note = data[i+2]

        # Valid instrument: 0-31 or 0x80+ (no change marker)
        inst_valid = (inst <= 0x1F) or (inst >= 0x80)

        # Valid note: 0-95 or gate markers
        note_valid = (note <= 0x5F) or note in [0x7E, 0x80, 0xFF, 0xFE]

        if inst_valid and note_valid:
            valid_count += 1

        total_count += 1

    if total_count == 0:
        return 0.0

    return (valid_count / total_count) * 100

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print(f"Reading: {sid_file}")
    with open(sid_file, 'rb') as f:
        data = f.read()

    # Known: tempo table ends at 0x0A9A
    tempo_end = 0x0A9A

    # Scan backwards from tempo to find high-scoring regions
    print(f"\nScanning for sequence data (backwards from tempo at 0x{tempo_end:04X}):\n")

    best_score = 0
    best_start = 0

    # Try various starting points
    for start in range(0x0700, tempo_end, 4):  # Step by 4 to stay aligned
        score = score_sequence_validity(data, start, length=512)

        if score > 75:  # High confidence threshold
            print(f"  0x{start:04X}: {score:.1f}% valid")

            if score > best_score:
                best_score = score
                best_start = start

    print(f"\nBest candidate: 0x{best_start:04X} ({best_score:.1f}% valid)")

    # Now try to determine if row numbers are entry indices
    # Test theory: row number = entry index (0x0020 = entry 32)
    print(f"\n=== Testing Theory: Row Number = Entry Index ===\n")

    # If entries are numbered sequentially, then:
    # Row 0x0020 (32 decimal) = byte offset 32 * 3 = 96 = 0x60
    # Row 0x0040 (64 decimal) = byte offset 64 * 3 = 192 = 0xC0

    expected_rows = [0x0000, 0x0020, 0x0040, 0x0060, 0x0080, 0x00A0, 0x00C0, 0x00E0,
                     0x0140, 0x0160, 0x01C0, 0x0240]

    print("If row number = entry index, byte offsets would be:")
    byte_offsets = [(row, row * 3) for row in expected_rows]

    for row, byte_off in byte_offsets:
        print(f"  Row 0x{row:04X} ({row:4d} dec) -> Byte 0x{byte_off:04X} ({byte_off:4d} dec)")

    # Now test this theory with the best start offset
    print(f"\n=== Validating at offset 0x{best_start:04X} ===\n")

    for row, byte_off in byte_offsets[:8]:  # Test first 8
        file_offset = best_start + byte_off

        if file_offset + 8 >= len(data):
            print(f"  Row 0x{row:04X} (byte +0x{byte_off:04X}): BEYOND FILE")
            continue

        # Show first 3 entries
        print(f"  Row 0x{row:04X} (byte +0x{byte_off:04X}, file 0x{file_offset:04X}):")

        for i in range(3):
            off = file_offset + (i * 3)
            if off + 2 >= len(data):
                break

            inst = data[off]
            cmd = data[off+1]
            note = data[off+2]

            note_str = note
            if note == 0x7E:
                note_str = "7E"
            elif note == 0x80:
                note_str = "80"
            elif note >= 0x80:
                note_str = f"{note:02X}"
            else:
                note_str = f"{note:02X}"

            print(f"    [{inst:02X}] [{cmd:02X}] [{note_str}]")

if __name__ == '__main__':
    main()
