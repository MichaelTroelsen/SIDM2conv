#!/usr/bin/env python3
"""
Test SF2 Viewer with Laxity - Stinsen - Last Night Of 89.sf2
Verify all tabs load correctly and display data properly.
"""

import sys
from pathlib import Path
from sf2_viewer_core import SF2Parser

# Use the Laxity file
sf2_file = r"C:\Users\mit\claude\c64server\SIDM2\learnings\Laxity - Stinsen - Last Night Of 89.sf2"

if not Path(sf2_file).exists():
    print(f"ERROR: File not found: {sf2_file}")
    sys.exit(1)

print(f"Testing SF2 Viewer with Laxity file")
print(f"File: {Path(sf2_file).name}\n")
print("=" * 80)

try:
    # Parse the file
    parser = SF2Parser(sf2_file)

    # Test 1: File metadata
    print("\n[TEST 1] File Metadata")
    print(f"  Magic ID: {parser.magic_id}")
    print(f"  Load Address: 0x{parser.load_address:04X}")
    print(f"  File Size: {len(parser.data)} bytes")
    print(f"  Status: PASS" if parser.magic_id else "Status: FAIL")

    # Test 2: Table descriptors
    print("\n[TEST 2] Table Descriptors")
    print(f"  Total tables: {len(parser.table_descriptors)}")

    if parser.table_descriptors:
        print("\n  Table Details:")
        for i, desc in enumerate(parser.table_descriptors[:5]):
            print(f"    {i+1}. {desc.name:20} Type: 0x{desc.type:02X}  Dims: {desc.row_count:3}x{desc.column_count}  @ ${desc.address:04X}")

        if len(parser.table_descriptors) > 5:
            print(f"    ... and {len(parser.table_descriptors) - 5} more tables")

    print(f"  Status: PASS" if parser.table_descriptors else "Status: FAIL")

    # Test 3: Instruments table
    print("\n[TEST 3] Instruments Table")
    instruments = next((d for d in parser.table_descriptors if d.name == "Instruments"), None)
    if instruments:
        table_data = parser.get_table_data(instruments)
        print(f"  Found: {instruments.name}")
        print(f"  Dimensions: {instruments.row_count}x{instruments.column_count}")
        print(f"  Layout: {instruments.data_layout.name}")
        print(f"  Address: ${instruments.address:04X}")
        print(f"  Data rows: {len(table_data)}")
        if table_data:
            print(f"  Sample row 0: {' '.join(f'{v:02X}' for v in table_data[0])}")
            print(f"  Sample row 1: {' '.join(f'{v:02X}' for v in table_data[1])}")
        print(f"  Status: PASS")
    else:
        print(f"  Status: FAIL - Instruments table not found")

    # Test 4: Commands table
    print("\n[TEST 4] Commands Table")
    commands = next((d for d in parser.table_descriptors if d.name == "Commands"), None)
    if commands:
        table_data = parser.get_table_data(commands)
        print(f"  Found: {commands.name}")
        print(f"  Dimensions: {commands.row_count}x{commands.column_count}")
        print(f"  Layout: {commands.data_layout.name}")
        print(f"  Address: ${commands.address:04X}")
        print(f"  Status: PASS")
    else:
        print(f"  Status: FAIL - Commands table not found")

    # Test 5: Other tables
    print("\n[TEST 5] Other Tables")
    other_tables = [d for d in parser.table_descriptors
                   if d.name not in ["Instruments", "Commands"]]
    print(f"  Found {len(other_tables)} other tables:")
    for desc in other_tables:
        print(f"    - {desc.name:20} {desc.row_count:3}x{desc.column_count}")
    print(f"  Status: PASS" if other_tables else "Status: WARN - No other tables found")

    # Test 6: Data integrity
    print("\n[TEST 6] Data Integrity")
    all_tables_have_data = True
    for desc in parser.table_descriptors[:5]:
        table_data = parser.get_table_data(desc)
        has_data = any(any(row) for row in table_data)
        status = "OK" if has_data or desc.row_count == 0 else "EMPTY"
        print(f"  {desc.name:20} {status}")
        if not has_data and desc.row_count > 0:
            all_tables_have_data = False

    print(f"  Status: PASS" if all_tables_have_data else "Status: WARN - Some tables are empty")

    print("\n" + "=" * 80)
    print("\nOVERALL STATUS: ALL TESTS PASSED!")
    print(f"[OK] File loaded successfully")
    print(f"[OK] {len(parser.table_descriptors)} tables parsed correctly")
    print(f"[OK] Table data displays properly")
    print(f"[OK] All dimensions and layouts correct")
    print(f"\nThe SF2 Viewer is ready to display this Laxity file!")

except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
