#!/usr/bin/env python3
"""
Extract pulse table from SF2-packed SID (3 columns at different offsets)
and write to Driver 11 SF2 file (4 columns, column-major).
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

def extract_sf2_packed_pulse_3col(sf2_packed_data):
    """
    Extract 3-column pulse data from SF2-packed SID.
    Columns are stored consecutively: col0, col1, col2.

    Returns: (col0, col1, col2) - each 25 bytes
    """
    offset = 0x09BC
    col_size = 25

    # All 3 columns are consecutive
    col0 = sf2_packed_data[offset:offset + col_size]
    col1 = sf2_packed_data[offset + col_size:offset + 2*col_size]
    col2 = sf2_packed_data[offset + 2*col_size:offset + 3*col_size]

    return col0, col1, col2

def convert_3col_to_4col_pulse(col0, col1, col2):
    """
    Convert 3-column SF2-packed pulse data to 4-column Driver 11 format.

    SF2-packed: 3 columns of 25 bytes each (column-major at different offsets)
    Driver 11: 4 columns of 256 bytes each (column-major, consecutive)

    Mapping: col0 -> Value, col1 -> Delta, col2 -> Duration, 0 -> Next
    """
    num_entries = 25

    # Create 4-column data in column-major format (256 rows × 4 columns)
    pulse_4col = bytearray(256 * 4)  # 1024 bytes, initialized to 0

    # Copy the 3 columns to the first 3 columns of Driver 11 format
    for i in range(num_entries):
        pulse_4col[i] = col0[i]              # Column 0: Value
        pulse_4col[256 + i] = col1[i]        # Column 1: Delta
        pulse_4col[512 + i] = col2[i]        # Column 2: Duration
        # Column 3 (Next) remains 0

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

    # SF2 file info
    sf2_load_addr = 0x0D7E
    sf2_pulse_addr = 0x1B24

    print("=" * 70)
    print("PULSE TABLE EXTRACTION (3 Columns) AND CONVERSION")
    print("=" * 70)

    # Step 1: Read SF2-packed SID
    print(f"\n1. Reading SF2-packed SID: {sf2_packed_sid}")
    sf2_packed_data = read_file(sf2_packed_sid)
    print(f"   File size: {len(sf2_packed_data)} bytes")

    # Step 2: Extract 3-column pulse data
    print(f"\n2. Extracting 3-column pulse data (consecutive)")
    print(f"   Column 0 at: $09BC (bytes 0-24)")
    print(f"   Column 1 at: $09D5 (bytes 25-49)")
    print(f"   Column 2 at: $09EE (bytes 50-74)")
    col0, col1, col2 = extract_sf2_packed_pulse_3col(sf2_packed_data)
    print(f"   Extracted: {len(col0)} + {len(col1)} + {len(col2)} = {len(col0)+len(col1)+len(col2)} bytes")

    # Show first few entries
    print(f"\n   First 15 entries:")
    print(f"   Entry | Col0 | Col1 | Col2 | Display")
    print(f"   " + "-" * 50)
    for i in range(15):
        print(f"     {i:02X}  |  {col0[i]:02X}  |  {col1[i]:02X}  |  {col2[i]:02X}  | {col0[i]:02X} {col1[i]:02X} {col2[i]:02X}")

    # Step 3: Convert to 4-column format
    print(f"\n3. Converting to 4-column Driver 11 format")
    pulse_4col = convert_3col_to_4col_pulse(col0, col1, col2)
    print(f"   Converted 25 entries to 4-column format")
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
    print("\nNext step: python verify_all_tables.py test_direct.sf2")

if __name__ == '__main__':
    main()
