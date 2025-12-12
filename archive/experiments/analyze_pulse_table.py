#!/usr/bin/env python3
"""
Analyze pulse table from SF2-packed SID and compare with converted Driver 11 SF2.
"""

import struct
import sys

def read_file(filepath):
    """Read file and return bytes."""
    with open(filepath, 'rb') as f:
        return f.read()

def parse_sf2_packed_pulse_table(data, offset, length):
    """
    Parse 3-column pulse table from SF2-packed SID file.
    Assumes row-major storage: each entry is 3 consecutive bytes.

    Note: User's image shows 16 entries, so we'll parse without stopping at 0x7F.
    """
    entries = []
    pos = offset
    entry_num = 0

    # Parse all bytes as 3-byte entries
    while pos + 2 < offset + length and entry_num < 256:
        col0 = data[pos]
        col1 = data[pos + 1]
        col2 = data[pos + 2]

        note = ""
        if col0 == 0x7F:
            note = "END?"  # Question mark since we're not stopping

        entries.append((entry_num, col0, col1, col2, note))
        pos += 3
        entry_num += 1

    return entries

def parse_driver11_pulse_table(data, load_addr, table_addr, num_entries=32, skip_empty=False):
    """
    Parse 4-column pulse table from Driver 11 SF2 file.
    Column-major storage: all column 0, then all column 1, etc.
    """
    offset = table_addr - load_addr + 2  # +2 for PRG load address

    if offset < 0 or offset >= len(data):
        return None

    entries = []

    # Read column-major data
    col0_data = data[offset:offset + num_entries]
    col1_data = data[offset + num_entries:offset + 2*num_entries]
    col2_data = data[offset + 2*num_entries:offset + 3*num_entries]
    col3_data = data[offset + 3*num_entries:offset + 4*num_entries]

    for i in range(num_entries):
        if i >= len(col0_data):
            break

        col0 = col0_data[i]
        col1 = col1_data[i] if i < len(col1_data) else 0
        col2 = col2_data[i] if i < len(col2_data) else 0
        col3 = col3_data[i] if i < len(col3_data) else 0

        # Optionally skip empty entries
        if skip_empty and col0 == 0 and col1 == 0 and col2 == 0 and col3 == 0:
            continue

        entries.append((i, col0, col1, col2, col3))

    return entries

def display_sf2_packed_pulse_table(entries):
    """Display 3-column pulse table."""
    print("\n" + "=" * 60)
    print("SF2-PACKED SID PULSE TABLE (3-column, row-major)")
    print("=" * 60)
    print("Entry | Col0 | Col1 | Col2 | Note")
    print("-" * 60)

    for entry in entries:
        num, col0, col1, col2, note = entry
        print(f"  {num:02X}  |  {col0:02X}  |  {col1:02X}  |  {col2:02X}  | {note}")

def display_driver11_pulse_table(entries):
    """Display 4-column pulse table."""
    print("\n" + "=" * 70)
    print("DRIVER 11 SF2 PULSE TABLE (4-column, column-major)")
    print("=" * 70)
    print("Entry | Col0 | Col1 | Col2 | Col3 | 12-bit Value | Delta")
    print("-" * 70)

    for entry in entries:
        num, col0, col1, col2, col3 = entry
        # Reconstruct 12-bit pulse value from lo/hi bytes
        pulse_value = ((col1 & 0x0F) << 8) | col0
        print(f"  {num:02X}  |  {col0:02X}  |  {col1:02X}  |  {col2:02X}  |  {col3:02X}  |   ${pulse_value:03X}     |  {col2:02X}")

def main():
    # Original SF2-packed SID file
    sf2_packed_file = "SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid"
    pulse_offset = 0x09BC  # User-provided address
    pulse_length = 0x19    # User-provided length (25 bytes)

    # Reference SF2 file (manually created/correct version)
    reference_file = "learnings/Stinsen - Last Night Of 89.sf2"
    reference_load = 0x0D7E
    reference_pulse_addr = 0x1B24

    # Converted Driver 11 SF2 file
    driver11_file = "output/Pipeline_Single/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2"
    driver11_load = 0x0D7E
    driver11_pulse_addr = 0x1B24  # From verify_all_tables.py

    print("PULSE TABLE ANALYSIS")
    print("=" * 70)

    # Parse SF2-packed pulse table
    print(f"\nReading SF2-packed SID: {sf2_packed_file}")
    print(f"Pulse table at offset: ${pulse_offset:04X}")
    print(f"Pulse table length: {pulse_length} bytes ({pulse_length // 3} entries)")

    sf2_packed_data = read_file(sf2_packed_file)
    sf2_packed_entries = parse_sf2_packed_pulse_table(sf2_packed_data, pulse_offset, pulse_length)
    display_sf2_packed_pulse_table(sf2_packed_entries)

    # Parse Reference SF2 pulse table
    print(f"\n\nReading Reference SF2: {reference_file}")
    print(f"Load address: ${reference_load:04X}")
    print(f"Pulse table at memory address: ${reference_pulse_addr:04X}")

    reference_data = read_file(reference_file)
    reference_entries = parse_driver11_pulse_table(reference_data, reference_load, reference_pulse_addr, num_entries=16, skip_empty=False)

    if reference_entries:
        print(f"(Showing first 16 entries)")
        display_driver11_pulse_table(reference_entries[:16])  # Show first 16 like user's image
    else:
        print("ERROR: Could not parse reference pulse table")

    # Parse Converted Driver 11 pulse table
    print(f"\n\nReading Converted Driver 11 SF2: {driver11_file}")
    print(f"Load address: ${driver11_load:04X}")
    print(f"Pulse table at memory address: ${driver11_pulse_addr:04X}")

    driver11_data = read_file(driver11_file)
    driver11_entries = parse_driver11_pulse_table(driver11_data, driver11_load, driver11_pulse_addr, num_entries=16, skip_empty=False)

    if driver11_entries:
        display_driver11_pulse_table(driver11_entries)
    else:
        print("ERROR: Could not parse Driver 11 pulse table")

    # Compare entry counts
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print(f"SF2-packed SID entries:     {len(sf2_packed_entries)}")
    print(f"Reference SF2 entries:      {len(reference_entries) if reference_entries else 0}")
    print(f"Converted SF2 entries:      {len(driver11_entries) if driver11_entries else 0}")

    # Check if converted matches reference
    if reference_entries and driver11_entries:
        matches = all(
            ref == conv
            for ref, conv in zip(reference_entries, driver11_entries)
        )
        print(f"\nConverted matches reference: {'YES' if matches else 'NO'}")

    # Show raw hex data from SF2-packed file
    print("\n" + "=" * 70)
    print("RAW HEX DATA (SF2-packed SID)")
    print("=" * 70)
    raw_data = sf2_packed_data[pulse_offset:pulse_offset + pulse_length]
    for i in range(0, len(raw_data), 16):
        chunk = raw_data[i:i+16]
        hex_str = ' '.join(f'{b:02X}' for b in chunk)
        print(f"${pulse_offset + i:04X}: {hex_str}")

if __name__ == '__main__':
    main()
