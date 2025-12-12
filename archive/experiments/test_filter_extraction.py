#!/usr/bin/env python3
"""Test filter table extraction from SF2-packed SID."""

import struct
from scripts.extract_sf2_properly import extract_sf2_packed_filter_3col

# Read the SF2-packed SID
with open('SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid', 'rb') as f:
    packed_raw = f.read()

# Extract filter table
packed_load = 0x1000  # SF2-packed format
filter_data = extract_sf2_packed_filter_3col(packed_raw, packed_load)

print("Filter table extraction test")
print("=" * 70)
print()

print(f"Extracted {len(filter_data)} bytes (expected: 1024)")
print()

# Show first 25 bytes of each column
print("Column 0 (first 25 bytes):")
col0 = filter_data[0:25]
print(f"  {' '.join(f'{b:02X}' for b in col0)}")
print()

print("Column 1 (first 25 bytes):")
col1 = filter_data[256:256+25]
print(f"  {' '.join(f'{b:02X}' for b in col1)}")
print()

print("Column 2 (first 25 bytes):")
col2 = filter_data[512:512+25]
print(f"  {' '.join(f'{b:02X}' for b in col2)}")
print()

print("Column 3 (first 25 bytes) - should be all zeros:")
col3 = filter_data[768:768+25]
print(f"  {' '.join(f'{b:02X}' for b in col3)}")
print()

# Verify against expected patterns
expected_col0_start = bytes([0x9f, 0x90, 0x90, 0x90, 0x0f, 0x7f, 0xa4])
expected_col1_start = bytes([0x00, 0x2c, 0x24, 0x3a, 0xff, 0x00, 0x30])
expected_col2_start = bytes([0xf2, 0xf2, 0xf2, 0xf2, 0x10, 0x05, 0xf2])

print("=" * 70)
print("VALIDATION")
print("=" * 70)

col0_match = col0[:7] == expected_col0_start
col1_match = col1[:7] == expected_col1_start
col2_match = col2[:7] == expected_col2_start
col3_zeros = all(b == 0 for b in col3)

print(f"Column 0 matches expected: {col0_match}")
print(f"Column 1 matches expected: {col1_match}")
print(f"Column 2 matches expected: {col2_match}")
print(f"Column 3 all zeros: {col3_zeros}")
print()

if col0_match and col1_match and col2_match and col3_zeros:
    print("SUCCESS: All filter columns extracted correctly!")
else:
    print("FAILED: Filter extraction has errors")
