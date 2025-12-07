#!/usr/bin/env python3
"""
Verify Wave table packing format in SF2 files
Checks that Wave table uses column-major storage: notes first, then waveforms
"""

import struct

def verify_wave_table_packing(sf2_file_path):
    """
    Verify Wave table is packed correctly as:
    - Bytes 0-31: Note offsets (Column 0)
    - Bytes 32-63: Waveforms (Column 1)
    """
    with open(sf2_file_path, 'rb') as f:
        data = f.read()

    # Parse SF2 header
    if len(data) < 4:
        print(f"ERROR: File too small")
        return False

    load_addr = struct.unpack('<H', data[0:2])[0]
    file_id = struct.unpack('<H', data[2:4])[0]

    if file_id != 0x1337:
        print(f"ERROR: Not a valid SF2 file (ID={file_id:04X})")
        return False

    print(f"SF2 file: {sf2_file_path}")
    print(f"Load address: ${load_addr:04X}")
    print(f"File ID: ${file_id:04X}")

    # Find Wave table definition
    wave_addr = None
    offset = 4

    while offset < len(data) - 2:
        block_id = data[offset]
        if block_id == 0xFF:  # End marker
            break

        block_size = data[offset + 1]
        block_data = data[offset + 2:offset + 2 + block_size]

        # Block 3 = Driver Tables
        if block_id == 3:
            # Parse table definitions
            idx = 0
            while idx < len(block_data):
                table_type = block_data[idx]
                if table_type == 0xFF:
                    break

                if idx + 3 > len(block_data):
                    break

                table_id = block_data[idx + 1]

                # Find name
                name_start = idx + 3
                name_end = name_start
                while name_end < len(block_data) and block_data[name_end] != 0:
                    name_end += 1

                name = block_data[name_start:name_end].decode('latin-1', errors='replace')

                pos = name_end + 1
                if pos + 12 <= len(block_data):
                    addr = struct.unpack('<H', block_data[pos+5:pos+7])[0]
                    columns = struct.unpack('<H', block_data[pos+7:pos+9])[0]
                    rows = struct.unpack('<H', block_data[pos+9:pos+11])[0]

                    if name == 'Wave' or (table_type == 0x00 and table_id == 2):
                        wave_addr = addr
                        wave_columns = columns
                        wave_rows = rows
                        print(f"\nWave table found at ${wave_addr:04X} ({columns}x{rows})")
                        break

                    idx = pos + 12
                else:
                    break

        offset += 2 + block_size

    if not wave_addr:
        print("ERROR: Wave table not found in SF2 file")
        return False

    # Extract Wave table data
    wave_offset = wave_addr - load_addr + 2
    if wave_offset + 64 > len(data):
        print(f"ERROR: Wave table offset ${wave_offset:04X} out of bounds")
        return False

    wave_data = data[wave_offset:wave_offset + 64]

    # Column-major format: Bytes 0-31 = notes, Bytes 32-63 = waveforms
    notes = wave_data[0:32]
    waveforms = wave_data[32:64]

    print("\nWave table packing format verification:")
    print("-" * 60)
    print("Column 0 (Bytes 0-31): Should be NOTE OFFSETS")
    print(f"  {notes[0:16].hex(' ').upper()}")
    print(f"  {notes[16:32].hex(' ').upper()}")

    print("\nColumn 1 (Bytes 32-63): Should be WAVEFORMS")
    print(f"  {waveforms[0:16].hex(' ').upper()}")
    print(f"  {waveforms[16:32].hex(' ').upper()}")

    # Heuristic check: waveforms should have values like 0x11, 0x21, 0x41, 0x81, 0x7F
    # Notes should mostly be 0x00 or small values (or 0x80-0xFF for special offsets)
    waveform_valid_count = sum(1 for w in waveforms if w in [0x11, 0x21, 0x41, 0x81, 0x7F, 0x7E, 0x80, 0x01, 0x02, 0x04, 0x08])
    note_valid_count = sum(1 for n in notes if n <= 0x5F or n >= 0x80)

    print(f"\nValidation:")
    print(f"  Waveforms look valid: {waveform_valid_count}/32 ({waveform_valid_count*100//32}%)")
    print(f"  Notes look valid: {note_valid_count}/32 ({note_valid_count*100//32}%)")

    # Show first 5 entries as (waveform, note) pairs
    print(f"\nFirst 5 entries (waveform, note):")
    for i in range(min(5, 32)):
        wave = waveforms[i]
        note = notes[i]
        wave_str = {
            0x11: "tri", 0x21: "saw", 0x41: "pulse", 0x81: "noise",
            0x7F: "JUMP", 0x7E: "HOLD", 0x80: "GATE-OFF"
        }.get(wave, f"${wave:02X}")
        note_str = f"${note:02X}" if note != 0x00 else "0"
        print(f"  {i:02d}: {wave_str:10} note={note_str}")

    if waveform_valid_count >= 16 and note_valid_count >= 16:
        print("\n[SUCCESS] Wave table appears to be correctly packed!")
        print("  Format: [32 notes][32 waveforms] (column-major)")
        return True
    else:
        print("\n[WARNING] Wave table packing may be incorrect")
        print("  Expected: [32 notes][32 waveforms]")
        return False


if __name__ == '__main__':
    import sys
    import glob

    if len(sys.argv) > 1:
        sf2_file = sys.argv[1]
        verify_wave_table_packing(sf2_file)
    else:
        # Find a recent SF2 file to test
        files = glob.glob('output/SIDSF2player_Complete_Pipeline/*/New/*.sf2')
        if files:
            print(f"Testing most recent SF2 file...\n")
            verify_wave_table_packing(files[0])
        else:
            print("No SF2 files found. Please specify a file path.")
