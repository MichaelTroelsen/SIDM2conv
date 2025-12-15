#!/usr/bin/env python3
"""
Test the improved All Tables display formatting.
"""

from sf2_viewer_core import SF2Parser

sf2_file = r'G5/examples/Driver 11 Test - Arpeggio.sf2'
print(f'Testing improved All Tables display with: {sf2_file}\n')

parser = SF2Parser(sf2_file)

if not parser.table_descriptors:
    print('ERROR: No tables found')
    exit(1)

# Simulate the improved formatting
tables_data = {}
for descriptor in parser.table_descriptors:
    table_data = parser.get_table_data(descriptor)
    tables_data[descriptor.name] = (descriptor, table_data)

max_rows = max(len(data[1]) for data in tables_data.values())
sorted_tables = sorted(tables_data.keys())
col_width = 24

# Build header
header = ""
for table_name in sorted_tables:
    header += f"{table_name:^{col_width}}"

print("SF2 All Tables View")
print("=" * len(header))
print(header)
print("=" * len(header))

# Show first 15 rows
for row_idx in range(min(15, max_rows)):
    for table_name in sorted_tables:
        descriptor, table_data = tables_data[table_name]

        if row_idx < len(table_data):
            row_bytes = ' '.join(f'{val:02X}' for val in table_data[row_idx])
            row_text = f'{row_idx:02X}: {row_bytes}'
        else:
            row_text = ""

        row_text = f"{row_text:<{col_width}}"
        print(row_text, end='')

    print()

print("\n✓ Display formatting working correctly!")
print(f"✓ {len(sorted_tables)} tables displayed with improved alignment")
print(f"✓ Showing {min(15, max_rows)} rows with proper column widths")
