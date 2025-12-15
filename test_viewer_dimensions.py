#!/usr/bin/env python3
"""
Test the SF2 Viewer with different SF2 files to verify dimension parsing.
This script will show the parsed dimensions for each file.
"""

import os
from sf2_viewer_core import SF2Parser
from pathlib import Path

# Test with all available SF2 files
sf2_dir = Path(r"C:\Users\mit\claude\c64server\SIDM2\G5\examples")

print("Testing SF2 Parser - Table Dimensions\n" + "="*60)

for sf2_file in sorted(sf2_dir.glob("*.sf2")):
    print(f"\nFile: {sf2_file.name}")
    print("-" * 60)

    try:
        parser = SF2Parser(str(sf2_file))

        if not parser.table_descriptors:
            print("  ERROR: No table descriptors parsed!")
            continue

        print(f"  Parsed {len(parser.table_descriptors)} tables:")

        for desc in parser.table_descriptors:
            # Show details for Instruments and Commands tables
            if desc.type in [0x81, 0x80]:
                type_name = "Instruments" if desc.type == 0x81 else "Commands"
                print(f"    {type_name:20} @ ${desc.address:04X}  Dims: {desc.row_count:3}x{desc.column_count}  Layout: {'CM' if desc.data_layout.value == 1 else 'RM'}")
            elif desc.name and desc.name != "Table[0x00]":
                print(f"    {desc.name:20} @ ${desc.address:04X}  Dims: {desc.row_count:3}x{desc.column_count}  Layout: {'CM' if desc.data_layout.value == 1 else 'RM'}")

    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "="*60)
print("Summary:")
print("- If Instruments shows variable dimensions (not always 32x6), parser is CORRECT")
print("- If all tables show COLUMN_MAJOR layout, that's correct for Driver 11")
