#!/usr/bin/env python3
"""
Search for all 3 filter table columns independently.
"""

# Search patterns (first 7 bytes of each column)
col0_pattern = bytes([0x9f, 0x90, 0x90, 0x90, 0x0f, 0x7f, 0xa4])
col1_pattern = bytes([0x00, 0x2c, 0x24, 0x3a, 0xff, 0x00, 0x30])
col2_pattern = bytes([0xf2, 0xf2, 0xf2, 0xf2, 0x00, 0x05, 0xf2])

# Read the SF2-packed SID file
filepath = "SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid"
print(f"Searching for filter table columns in: {filepath}")
print()

with open(filepath, 'rb') as f:
    data = f.read()

print(f"File size: {len(data)} bytes (${len(data):04X})")
print()

# Search for all three patterns independently
patterns = [
    ("Column 0", col0_pattern, "9f 90 90 90 0f 7f a4"),
    ("Column 1", col1_pattern, "00 2c 24 3a ff 00 30"),
    ("Column 2", col2_pattern, "f2 f2 f2 f2 00 05 f2"),
]

results = {}

for name, pattern, hex_str in patterns:
    matches = []
    for i in range(len(data) - len(pattern)):
        if data[i:i+len(pattern)] == pattern:
            matches.append(i)
    results[name] = matches

    print(f"{name} pattern ({hex_str}) found at {len(matches)} location(s):")
    for offset in matches:
        print(f"  Offset ${offset:04X}")
        # Show full 25 bytes
        end = min(len(data), offset + 25)
        print(f"  Data:   {' '.join(f'{data[j]:02X}' for j in range(offset, end))}")
    print()

# Analyze spacing between columns
print("=" * 70)
print("ANALYZING COLUMN SPACING")
print("=" * 70)

if results["Column 0"] and results["Column 1"] and results["Column 2"]:
    col0_off = results["Column 0"][0]
    col1_off = results["Column 1"][0]
    col2_off = results["Column 2"][0]

    print(f"\nColumn 0 offset: ${col0_off:04X}")
    print(f"Column 1 offset: ${col1_off:04X}")
    print(f"Column 2 offset: ${col2_off:04X}")
    print()
    print(f"Column 1 - Column 0 = ${col1_off - col0_off:04X} ({col1_off - col0_off} bytes)")
    print(f"Column 2 - Column 1 = ${col2_off - col1_off:04X} ({col2_off - col1_off} bytes)")
    print(f"Column 2 - Column 0 = ${col2_off - col0_off:04X} ({col2_off - col0_off} bytes)")
    print()

    # Check if columns are evenly spaced
    if col1_off - col0_off == col2_off - col1_off:
        col_size = col1_off - col0_off
        print(f"Columns are EVENLY SPACED with {col_size} bytes (${col_size:02X}) between them")
    else:
        print("Columns are NOT evenly spaced")
