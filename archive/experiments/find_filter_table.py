#!/usr/bin/env python3
"""
Search for filter table pattern in SF2-packed SID file.

Expected filter table (3 columns × $19/25 bytes):
- Column 0: 9f 90 90 90 0f 7f a4 ...
- Column 1: 00 2c 24 3a ff 00 30 ...
- Column 2: f2 f2 f2 f2 00 05 f2 ...
"""

# Search patterns (first 7 bytes of each column)
col0_pattern = bytes([0x9f, 0x90, 0x90, 0x90, 0x0f, 0x7f, 0xa4])
col1_pattern = bytes([0x00, 0x2c, 0x24, 0x3a, 0xff, 0x00, 0x30])
col2_pattern = bytes([0xf2, 0xf2, 0xf2, 0xf2, 0x00, 0x05, 0xf2])

# Read the SF2-packed SID file
filepath = "SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid"
print(f"Searching for filter table in: {filepath}")
print()

with open(filepath, 'rb') as f:
    data = f.read()

print(f"File size: {len(data)} bytes (${len(data):04X})")
print()

# Search for column 0 pattern
print("=" * 70)
print("SEARCHING FOR FILTER TABLE COLUMNS")
print("=" * 70)

col0_matches = []
for i in range(len(data) - len(col0_pattern)):
    if data[i:i+len(col0_pattern)] == col0_pattern:
        col0_matches.append(i)

print(f"\nColumn 0 pattern (9f 90 90 90 0f 7f a4) found at {len(col0_matches)} location(s):")
for offset in col0_matches:
    print(f"  Offset ${offset:04X}")
    # Show surrounding context
    start = max(0, offset - 8)
    end = min(len(data), offset + 32)
    print(f"  Context: {' '.join(f'{data[j]:02X}' for j in range(start, end))}")
    print()

# For each col0 match, check if col1 and col2 follow at +25 and +50 byte offsets
print("\n" + "=" * 70)
print("CHECKING FOR CONSECUTIVE 3-COLUMN LAYOUT")
print("=" * 70)

col_size = 0x19  # 25 bytes per column

for col0_offset in col0_matches:
    col1_offset = col0_offset + col_size
    col2_offset = col0_offset + 2 * col_size

    # Check if we have enough data
    if col2_offset + len(col2_pattern) > len(data):
        print(f"\nOffset ${col0_offset:04X}: Not enough data for 3 columns")
        continue

    # Check if col1 and col2 patterns match
    col1_match = data[col1_offset:col1_offset+len(col1_pattern)] == col1_pattern
    col2_match = data[col2_offset:col2_offset+len(col2_pattern)] == col2_pattern

    print(f"\nOffset ${col0_offset:04X}:")
    print(f"  Column 0 at ${col0_offset:04X}: {'MATCH' if True else 'NO MATCH'}")
    print(f"  Column 1 at ${col1_offset:04X}: {'MATCH' if col1_match else 'NO MATCH'}")
    print(f"  Column 2 at ${col2_offset:04X}: {'MATCH' if col2_match else 'NO MATCH'}")

    if col1_match and col2_match:
        print(f"\n  *** FOUND COMPLETE 3-COLUMN FILTER TABLE AT ${col0_offset:04X} ***")

        # Display full columns
        print(f"\n  Column 0 (${col0_offset:04X}):")
        col0_data = data[col0_offset:col0_offset + col_size]
        print(f"    {' '.join(f'{b:02X}' for b in col0_data)}")

        print(f"\n  Column 1 (${col1_offset:04X}):")
        col1_data = data[col1_offset:col1_offset + col_size]
        print(f"    {' '.join(f'{b:02X}' for b in col1_data)}")

        print(f"\n  Column 2 (${col2_offset:04X}):")
        col2_data = data[col2_offset:col2_offset + col_size]
        print(f"    {' '.join(f'{b:02X}' for b in col2_data)}")

print("\n" + "=" * 70)
print("SEARCH COMPLETE")
print("=" * 70)
