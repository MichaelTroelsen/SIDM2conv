#!/usr/bin/env python3
"""
Extract complete sequence table from Stinsens file.

Key insight: Sequences are NOT separated by markers.
The sequence table is one continuous block of 3-byte entries.
Orderlists reference specific byte offsets into this table.

Expected row numbers from orderlist display:
  0000, 0020, 0040, 0060, 0080, 00a0, 00c0, 00e0, 0140, 0160, 01c0, 0240
These are BYTE OFFSETS into the sequence table!
"""

def show_entries_at_offset(data, table_start, byte_offset, count=8):
    """Show sequence entries at a specific byte offset."""
    file_offset = table_start + byte_offset
    entries = []

    for i in range(count):
        offset = file_offset + (i * 3)
        if offset + 2 >= len(data):
            break

        inst = data[offset]
        cmd = data[offset+1]
        note = data[offset+2]

        # Format note with special markers
        note_str = note
        if note == 0x7E:
            note_str = "7E (GATE)"
        elif note == 0x80:
            note_str = "80 (---)"
        elif note == 0xFF:
            note_str = "FF (END)"
        elif note == 0xFE:
            note_str = "FE (LOOP)"
        else:
            note_str = f"{note:02X}"

        entries.append({
            'byte_offset': byte_offset + (i * 3),
            'file_offset': offset,
            'instrument': inst,
            'command': cmd,
            'note': note,
            'note_str': note_str
        })

    return entries

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print(f"Reading: {sid_file}")
    with open(sid_file, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data)} bytes\n")

    # Based on analysis: sequence table found at 0x0800-0x0A9A region
    # But let's be more precise - find the actual start

    # Try different start points
    possible_starts = [0x07FC, 0x0800, 0x0804]

    for seq_start in possible_starts:
        seq_end = 0x0A9A  # Tempo table starts here
        seq_len = seq_end - seq_start

        print(f"=== Testing sequence table at 0x{seq_start:04X} - 0x{seq_end:04X} ({seq_len} bytes) ===\n")

        # Expected byte offsets from orderlist "row numbers"
        expected_offsets = [
            0x0000, 0x0020, 0x0040, 0x0060, 0x0080, 0x00A0, 0x00C0, 0x00E0,
            0x0140, 0x0160, 0x01C0, 0x0240
        ]

        print("Checking expected byte offsets:\n")

        all_valid = True
        for byte_off in expected_offsets:
            if byte_off >= seq_len:
                print(f"  Offset 0x{byte_off:04X}: BEYOND TABLE END ({seq_len} bytes)")
                all_valid = False
                continue

            print(f"  Offset 0x{byte_off:04X} (file 0x{seq_start + byte_off:04X}):")
            entries = show_entries_at_offset(data, seq_start, byte_off, count=4)

            for entry in entries:
                print(f"    +0x{entry['byte_offset']:04X}: [{entry['instrument']:02X}] [{entry['command']:02X}] [{entry['note_str']}]")

            # Check if this looks valid
            # Valid = instrument 0-31 or 0x80+, reasonable note values
            valid_count = 0
            for entry in entries:
                inst_valid = (entry['instrument'] <= 0x1F) or (entry['instrument'] >= 0x80)
                note_valid = (entry['note'] <= 0x5F) or entry['note'] in [0x7E, 0x80, 0xFF, 0xFE]

                if inst_valid and note_valid:
                    valid_count += 1

            if valid_count >= 3:
                print(f"    [OK] {valid_count}/4 entries look valid")
            else:
                print(f"    [WARN] Only {valid_count}/4 entries look valid")
                all_valid = False

            print()

        if all_valid:
            print(f"[SUCCESS] Sequence table start: 0x{seq_start:04X}\n")

            # Extract and save
            seq_data = data[seq_start:seq_end]
            output_file = 'output/sequence_table_stinsens.bin'
            with open(output_file, 'wb') as f:
                f.write(seq_data)

            print(f"[OK] Saved sequence table: {output_file}")
            print(f"     Size: {len(seq_data)} bytes ({len(seq_data)//3} entries)\n")

            # Create hex dump for inspection
            hex_file = 'output/sequence_table_stinsens.hex'
            with open(hex_file, 'w') as f:
                for i in range(0, len(seq_data), 16):
                    hex_vals = ' '.join(f'{seq_data[j]:02X}' for j in range(i, min(i+16, len(seq_data))))
                    f.write(f"0x{i:04X}: {hex_vals}\n")

            print(f"[OK] Saved hex dump: {hex_file}\n")

            # Create formatted sequence listing
            list_file = 'output/sequence_table_stinsens.txt'
            with open(list_file, 'w') as f:
                f.write("Stinsen Sequence Table\n")
                f.write("=" * 70 + "\n\n")

                for byte_off in expected_offsets:
                    if byte_off >= len(seq_data):
                        break

                    f.write(f"Sequence at byte offset 0x{byte_off:04X}:\n")
                    f.write("-" * 50 + "\n")

                    entries = show_entries_at_offset(data, seq_start, byte_off, count=16)
                    for entry in entries:
                        f.write(f"  +0x{entry['byte_offset']:04X}: [{entry['instrument']:02X}] [{entry['command']:02X}] [{entry['note_str']}]\n")

                    f.write("\n")

            print(f"[OK] Saved sequence listing: {list_file}\n")
            break
        else:
            print(f"[FAIL] This start offset doesn't match expected patterns\n")
            print("=" * 70 + "\n")

if __name__ == '__main__':
    main()
