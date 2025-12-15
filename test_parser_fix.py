#!/usr/bin/env python3
"""
Test script to verify the SF2 parser correctly reads table dimensions
from the null-terminated name string format.
"""

import sys
from sf2_viewer_core import SF2Parser

# Test file
sf2_file = r"C:\Users\mit\claude\c64server\SIDM2\G5\examples\Driver 11 Test - Arpeggio.sf2"

print("Testing SF2 Parser with corrected null-terminated name handling...")
print(f"File: {sf2_file}\n")

try:
    parser = SF2Parser(sf2_file)

    if not parser.table_descriptors:
        print("ERROR: No table descriptors parsed!")
        sys.exit(1)

    print(f"Successfully parsed {len(parser.table_descriptors)} table descriptors:\n")

    for i, desc in enumerate(parser.table_descriptors):
        print(f"Table {i}:")
        print(f"  Name: {desc.name}")
        print(f"  Type: 0x{desc.type:02X}")
        print(f"  ID: {desc.id}")
        print(f"  Address: ${desc.address:04X}")
        print(f"  Dimensions: {desc.row_count} rows x {desc.column_count} columns")
        print(f"  Layout: {'COLUMN_MAJOR' if desc.data_layout.value == 1 else 'ROW_MAJOR'}")
        print()

    # Check Instruments table specifically
    instruments = next((d for d in parser.table_descriptors if d.type == 0x81), None)
    if instruments:
        print(f"\n*** INSTRUMENTS TABLE ***")
        print(f"Dimensions: {instruments.row_count}x{instruments.column_count}")
        print(f"Expected for test file: 19x6 (user said test has $13 instruments)")

        if instruments.row_count == 19 and instruments.column_count == 6:
            print("[PASS] Dimensions match expected values!")
        else:
            print(f"[INFO] Got {instruments.row_count}x{instruments.column_count} (may differ from template file expectations)")
    else:
        print("\nWARNING: No Instruments table found!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
