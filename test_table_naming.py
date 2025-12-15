#!/usr/bin/env python3
"""
Test the improved table naming based on dimensions.
"""

import sys
from sf2_viewer_core import SF2Parser
from pathlib import Path

# Test with the Laxity file
sf2_file = r"C:\Users\mit\claude\c64server\SIDM2\G5\examples\Driver 11 Test - Arpeggio.sf2"

print("Testing Table Naming with Dimension-Based Inference\n" + "="*60)

try:
    parser = SF2Parser(sf2_file)

    if not parser.table_descriptors:
        print("ERROR: No table descriptors parsed!")
        sys.exit(1)

    print(f"File: {Path(sf2_file).name}\n")
    print(f"Found {len(parser.table_descriptors)} tables:\n")

    for i, desc in enumerate(parser.table_descriptors):
        # Show table info
        print(f"{i+1}. {desc.name:20} (Type: 0x{desc.type:02X}, ID: {desc.id})")
        print(f"   @ ${desc.address:04X}  Dims: {desc.row_count:3}x{desc.column_count}  Layout: {'CM' if desc.data_layout.value == 1 else 'RM'}")
        print()

    print("="*60)
    print("Table name identification:")
    print("- Tables with proper names (Wave, Pulse, Filter, etc.): GOOD")
    print("- Generic 'Table[0x00]' names should be reduced")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
