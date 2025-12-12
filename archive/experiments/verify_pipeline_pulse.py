#!/usr/bin/env python3
"""Verify pulse table in pipeline-generated SF2 file"""
import struct

# Read the pipeline-generated file
with open("output/SIDSF2player_Complete_Pipeline/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2", 'rb') as f:
    sf2_data = f.read()

# Get load address
load_addr = struct.unpack('<H', sf2_data[0:2])[0]
print(f"SF2 Load Address: ${load_addr:04X}")

# Pulse table at $1B24 in Driver 11 format
pulse_addr = 0x1B24
file_offset = pulse_addr - load_addr + 2

print(f"Pulse table at memory ${pulse_addr:04X}")
print(f"File offset: ${file_offset:04X}")
print()

# Extract first 10 bytes from each column (column-major: 256 bytes per column)
col0 = sf2_data[file_offset:file_offset + 10]
col1 = sf2_data[file_offset + 256:file_offset + 256 + 10]
col2 = sf2_data[file_offset + 512:file_offset + 512 + 10]
col3 = sf2_data[file_offset + 768:file_offset + 768 + 10]

print("Pulse Table - First 10 entries:")
print(f"Column 0 (Value):    {' '.join(f'{b:02X}' for b in col0)}")
print(f"Column 1 (Delta):    {' '.join(f'{b:02X}' for b in col1)}")
print(f"Column 2 (Duration): {' '.join(f'{b:02X}' for b in col2)}")
print(f"Column 3 (Next):     {' '.join(f'{b:02X}' for b in col3)}")
print()

print("Expected (from SF2-packed extraction):")
print("Column 0: 88 00 81 00 00 0F 7F 88 7F 88")
print("Column 1: 00 00 70 40 10 F0 00 00 00 00")
print("Column 2: 00 01 00 04 20 20 04 00 07 00")
print()

# Verify
expected_col0 = bytes([0x88, 0x00, 0x81, 0x00, 0x00, 0x0F, 0x7F, 0x88, 0x7F, 0x88])
expected_col1 = bytes([0x00, 0x00, 0x70, 0x40, 0x10, 0xF0, 0x00, 0x00, 0x00, 0x00])
expected_col2 = bytes([0x00, 0x01, 0x00, 0x04, 0x20, 0x20, 0x04, 0x00, 0x07, 0x00])

if col0 == expected_col0:
    print("✓ Column 0 CORRECT")
else:
    print("✗ Column 0 WRONG")

if col1 == expected_col1:
    print("✓ Column 1 CORRECT")
else:
    print("✗ Column 1 WRONG")

if col2 == expected_col2:
    print("✓ Column 2 CORRECT")
else:
    print("✗ Column 2 WRONG")
