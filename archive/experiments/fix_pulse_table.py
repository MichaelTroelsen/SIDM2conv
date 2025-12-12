#!/usr/bin/env python3
"""
Extract pulse table from SF2-packed SID and write to Driver 11 SF2 file.
"""

import struct

def read_file(filepath):
    """Read file and return bytes."""
    with open(filepath, 'rb') as f:
        return f.read()

def write_file(filepath, data):
    """Write data to file."""
    with open(filepath, 'wb') as f:
        f.write(data)

def extract_sf2_packed_pulse(sf2_packed_data, offset, length):
    """
    Extract pulse data from SF2-packed SID at given offset.
    Returns raw bytes.
    """
    return sf2_packed_data[offset:offset + length]

def convert_3col_to_4col_pulse(data_3col):
    """
    Convert 3-column SF2-packed pulse data to 4-column Driver 11 format.

    SF2-packed: 3 columns (assumed: Value Lo, Value Hi, Param)
    Driver 11: 4 columns (Value, Delta, Duration, Next) - column-major

    For now, we'll parse the 3-column data as row-major (3 bytes per entry)
    and convert to 4-column column-major format.
    """
    num_entries = len(data_3col) // 3

    # Parse 3-column data (row-major)
    entries = []
    for i in range(num_entries):
        offset = i * 3
        if offset + 2 < len(data_3col):
            col0 = data_3col[offset]
            col1 = data_3col[offset + 1]
            col2 = data_3col[offset + 2]
            entries.append((col0, col1, col2))

    # Convert to 4-column format
    # Map: 3-col (val_lo, val_hi, param) -> 4-col (value, delta, duration, next)
    # We'll use the 3 columns as: value=col0, delta=col1, duration=col2, next=0

    # Create 4-column data in column-major format (256 rows × 4 columns)
    pulse_4col = bytearray(256 * 4)  # 1024 bytes

    for i, (col0, col1, col2) in enumerate(entries):
        if i < 256:
            pulse_4col[i] = col0              # Column 0: Value
            pulse_4col[256 + i] = col1        # Column 1: Delta
            pulse_4col[512 + i] = col2        # Column 2: Duration
            pulse_4col[768 + i] = 0           # Column 3: Next (default 0)

    return bytes(pulse_4col)

def write_pulse_to_sf2(sf2_data, pulse_table_addr, pulse_data, load_addr):
    """
    Write pulse table data to SF2 file at the correct offset.
    """
    sf2_data = bytearray(sf2_data)

    # Calculate file offset (memory address - load address + 2 for PRG header)
    file_offset = pulse_table_addr - load_addr + 2

    print(f"Writing pulse table:")
    print(f"  Memory address: ${pulse_table_addr:04X}")
    print(f"  Load address: ${load_addr:04X}")
    print(f"  File offset: ${file_offset:04X} ({file_offset} bytes)")
    print(f"  Pulse data length: {len(pulse_data)} bytes")

    # Write the pulse data
    sf2_data[file_offset:file_offset + len(pulse_data)] = pulse_data

    return bytes(sf2_data)

def main():
    # Input files
    sf2_packed_sid = "SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid"
    sf2_output = "output/Pipeline_Single/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2"

    # Pulse table info from user
    pulse_offset_sid = 0x09BC  # Where pulse data is in SF2-packed SID
    pulse_length = 0x19        # 25 bytes

    # SF2 file info
    sf2_load_addr = 0x0D7E
    sf2_pulse_addr = 0x1B24    # Where to write pulse data in SF2

    print("=" * 70)
    print("PULSE TABLE EXTRACTION AND CONVERSION")
    print("=" * 70)

    # Step 1: Read SF2-packed SID
    print(f"\n1. Reading SF2-packed SID: {sf2_packed_sid}")
    sf2_packed_data = read_file(sf2_packed_sid)
    print(f"   File size: {len(sf2_packed_data)} bytes")

    # Step 2: Extract pulse data
    print(f"\n2. Extracting pulse data from offset ${pulse_offset_sid:04X}")
    pulse_3col = extract_sf2_packed_pulse(sf2_packed_data, pulse_offset_sid, pulse_length)
    print(f"   Extracted {len(pulse_3col)} bytes")
    print(f"   Data: {' '.join(f'{b:02X}' for b in pulse_3col[:16])}...")

    # Step 3: Convert to 4-column format
    print(f"\n3. Converting to 4-column Driver 11 format")
    pulse_4col = convert_3col_to_4col_pulse(pulse_3col)
    num_entries = len(pulse_3col) // 3
    print(f"   Converted {num_entries} entries to 4-column format")
    print(f"   Total pulse table size: {len(pulse_4col)} bytes (256 rows × 4 columns)")

    # Step 4: Read SF2 file
    print(f"\n4. Reading SF2 file: {sf2_output}")
    sf2_data = read_file(sf2_output)
    print(f"   File size: {len(sf2_data)} bytes")

    # Step 5: Write pulse data to SF2
    print(f"\n5. Writing pulse table to SF2")
    sf2_modified = write_pulse_to_sf2(sf2_data, sf2_pulse_addr, pulse_4col, sf2_load_addr)

    # Step 6: Save modified SF2
    output_file = "test_direct.sf2"
    print(f"\n6. Saving modified SF2 to: {output_file}")
    write_file(output_file, sf2_modified)
    print(f"   Saved {len(sf2_modified)} bytes")

    print("\n" + "=" * 70)
    print("PULSE TABLE UPDATE COMPLETE")
    print("=" * 70)
    print(f"\nOutput file: {output_file}")
    print("\nNext steps:")
    print("  1. Verify with: python verify_all_tables.py test_direct.sf2")
    print("  2. Compare with reference: python analyze_pulse_table.py")

if __name__ == '__main__':
    main()
