#!/usr/bin/env python3

# Read raw SID file
with open("SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid", 'rb') as f:
    data = f.read()

# Extract from file offset $09BC
offset = 0x09BC
col_size = 25

col0 = data[offset:offset + col_size]
col1 = data[offset + col_size:offset + 2*col_size]
col2 = data[offset + 2*col_size:offset + 3*col_size]

print(f"Direct extraction from file offset ${offset:04X}:")
print(f"Column 0 (first 10): {' '.join(f'{b:02X}' for b in col0[:10])}")
print(f"Column 1 (first 10): {' '.join(f'{b:02X}' for b in col1[:10])}")
print(f"Column 2 (first 10): {' '.join(f'{b:02X}' for b in col2[:10])}")
print()

# Check what we expect
print("Expected:")
print("Column 0: 88 00 81 00 00 0F 7F 88 7F 88")
print("Column 1: 00 00 70 40 10 F0 00 00 00 00")
print("Column 2: 00 01 00 04 20 20 04 00 07 00")

