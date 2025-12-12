#!/usr/bin/env python3
"""
Convert SF2-packed SID to Driver 11 SF2 file

Extracts all tables from SF2-packed SID format and writes to proper Driver 11 SF2 format.
Includes the corrected 3-column pulse table extraction.
"""

import struct
import sys
from pathlib import Path


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

    # Write the pulse data
    sf2_data[file_offset:file_offset + len(pulse_data)] = pulse_data

    return bytes(sf2_data)


def main():
    """
    Main conversion process.

    Usage:
        python convert_sf2packed_to_sf2.py <sf2_packed_sid> <template_sf2> <output_sf2>

    Example:
        python convert_sf2packed_to_sf2.py \\
            SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid \\
            output/Pipeline_Single/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2 \\
            output/Stinsens_Last_Night_of_89_fixed.sf2
    """

    if len(sys.argv) < 4:
        print("Usage: python convert_sf2packed_to_sf2.py <sf2_packed_sid> <template_sf2> <output_sf2>")
        print()
        print("  sf2_packed_sid: Input SF2-packed SID file")
        print("  template_sf2:   SF2 template file (will be used as base)")
        print("  output_sf2:     Output SF2 file with corrected pulse table")
        sys.exit(1)

    sf2_packed_sid = sys.argv[1]
    template_sf2 = sys.argv[2]
    output_sf2 = sys.argv[3]

    # SF2 file info (Driver 11 standard)
    sf2_load_addr = 0x0D7E
    sf2_pulse_addr = 0x1B24

    print("=" * 70)
    print("SF2-PACKED SID TO DRIVER 11 SF2 CONVERSION")
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
    print(f"\n   First 10 entries:")
    print(f"   Entry | Col0 | Col1 | Col2")
    print(f"   " + "-" * 35)
    for i in range(10):
        print(f"     {i:02X}  |  {col0[i]:02X}  |  {col1[i]:02X}  |  {col2[i]:02X}")

    # Step 3: Convert to 4-column format
    print(f"\n3. Converting to 4-column Driver 11 format")
    pulse_4col = convert_3col_to_4col_pulse(col0, col1, col2)
    print(f"   Converted 25 entries to 4-column format")
    print(f"   Total pulse table size: {len(pulse_4col)} bytes (256 rows × 4 columns)")

    # Step 4: Read SF2 template file
    print(f"\n4. Reading SF2 template: {template_sf2}")
    sf2_data = read_file(template_sf2)
    print(f"   File size: {len(sf2_data)} bytes")

    # Verify load address
    template_load = struct.unpack('<H', sf2_data[0:2])[0]
    print(f"   Load address: ${template_load:04X}")

    if template_load != sf2_load_addr:
        print(f"\n   WARNING: Template load address ${template_load:04X} != expected ${sf2_load_addr:04X}")
        sf2_load_addr = template_load

    # Step 5: Write pulse data to SF2
    print(f"\n5. Writing pulse table to SF2")
    print(f"   Memory address: ${sf2_pulse_addr:04X}")
    print(f"   Load address: ${sf2_load_addr:04X}")
    file_offset = sf2_pulse_addr - sf2_load_addr + 2
    print(f"   File offset: ${file_offset:04X} ({file_offset} bytes)")
    sf2_modified = write_pulse_to_sf2(sf2_data, sf2_pulse_addr, pulse_4col, sf2_load_addr)

    # Step 6: Save modified SF2
    print(f"\n6. Saving modified SF2 to: {output_sf2}")

    # Create output directory if needed
    output_path = Path(output_sf2)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    write_file(output_sf2, sf2_modified)
    print(f"   Saved {len(sf2_modified)} bytes")

    print("\n" + "=" * 70)
    print("CONVERSION COMPLETE")
    print("=" * 70)
    print(f"\nOutput file: {output_sf2}")
    print("\nNext steps:")
    print(f"  1. Verify: python verify_all_tables.py {output_sf2}")
    print(f"  2. Test in SID Factory II editor")
    print(f"  3. Export to SID and test playback")


if __name__ == '__main__':
    main()
