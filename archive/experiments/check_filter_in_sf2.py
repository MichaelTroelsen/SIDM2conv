#!/usr/bin/env python3
"""
Check the filter table in the correct SF2 file to verify the pattern.
"""
import struct

# Read the correct SF2 file
filepath = "output/Stinsens_CORRECT.sf2"
print(f"Reading filter table from: {filepath}")
print()

with open(filepath, 'rb') as f:
    sf2_data = f.read()

# Get load address
load_addr = struct.unpack('<H', sf2_data[0:2])[0]
print(f"Load Address: ${load_addr:04X}")
print()

# Filter table in Driver 11 is at $1E24
# 4 columns × 256 rows, column-major
filter_addr = 0x1E24
filter_offset = filter_addr - load_addr + 2

print(f"Filter table at ${filter_addr:04X}, file offset ${filter_offset:04X}")
print()

# Read first 25 bytes of each column
for col in range(4):
    col_offset = filter_offset + (col * 256)
    col_data = sf2_data[col_offset:col_offset + 25]
    print(f"Column {col} (first 25 bytes):")
    print(f"  {' '.join(f'{b:02X}' for b in col_data)}")
    print()
