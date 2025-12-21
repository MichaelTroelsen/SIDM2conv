#!/usr/bin/env python3
"""Analyze the complete structure of Broware.sf2 to understand what's where"""

from pathlib import Path
import struct

sf2_path = Path("output/SIDSF2player_Complete_Pipeline/Broware/New/Broware.sf2")

with open(sf2_path, 'rb') as f:
    sf2_data = f.read()

load_addr = struct.unpack('<H', sf2_data[0:2])[0]
file_data = sf2_data[2:]

print("="*80)
print("BROWARE.SF2 COMPLETE MEMORY MAP")
print("="*80)

print(f"\nFile details:")
print(f"  Total file size: {len(sf2_data):,} bytes")
print(f"  Load address: ${load_addr:04X}")
print(f"  File data size: {len(file_data):,} bytes")
print(f"  Maps to memory: ${load_addr:04X}-${load_addr + len(file_data):04X}")

# Check different regions of the file
regions = [
    ("Load Address", 0, 2, "PRG header"),
    ("Region 1", 2, 20, "Start of data at $0D7E"),
    ("Region 2", 20, 50, "Hex: likely SF2 metadata"),
    ("Region 3", 100, 120, "Middle data"),
    ("Region 4", 200, 220, "More data"),
    ("Region 5", 300, 320, "More data"),
    ("Offset 642 (->$0FFF)", 642, 644, "Last 2 bytes before $1000"),
    ("Offset 644 (->$1000)", 644, 664, "First 20 bytes at $1000 (WEIRD OPCODES)"),
    ("Offset 700", 700, 720, "Data after $1000 region"),
]

for region_name, start, end, description in regions:
    bytes_data = sf2_data[start:end]
    hex_str = ' '.join(f'{b:02x}' for b in bytes_data)

    # Try to interpret as ASCII
    ascii_str = ''
    for b in bytes_data:
        if 32 <= b < 127:
            ascii_str += chr(b)
        else:
            ascii_str += '.'

    print(f"\n{region_name} (offset {start}-{end-1}):")
    print(f"  {hex_str}")
    print(f"  ASCII: {ascii_str}")
    print(f"  Note: {description}")

# Check if the weird opcodes pattern repeats or has structure
print(f"\n" + "="*80)
print("ANALYZING THE 'WEIRD OPCODES' REGION")
print("="*80)

weird_start = 644
weird_bytes = sf2_data[weird_start:weird_start + 200]

print(f"\nBytes at offset {weird_start} (address $1000):")
print(f"{' '.join(f'{b:02x}' for b in weird_bytes[:64])}")

# Look for patterns
print(f"\nAnalyzing patterns:")
print(f"  0xA7 appears at offsets: ", [i for i, b in enumerate(weird_bytes[:100]) if b == 0xA7])
print(f"  0x7F (END marker) appears at offsets: ", [i for i, b in enumerate(weird_bytes[:100]) if b == 0x7F])
print(f"  0x00 (zero) appears at offsets: ", [i for i, b in enumerate(weird_bytes[:100]) if b == 0x00])

# Check if these look like SF2 sequence/music data instead of code
print(f"\n" + "="*80)
print("HYPOTHESIS: Is the data at $1000 actually SF2 sequences/music?")
print("="*80)

# In SF2 files, 0x7F is an end marker for sequences
markers_7f = [i for i in range(len(weird_bytes)-1) if weird_bytes[i] == 0x7F]
print(f"\n0x7F (sequence end marker) found at offsets in region: {markers_7f[:10]}")

# Look for sequences starting with command bytes
print(f"\nFirst 20 bytes: {' '.join(f'{b:02x}' for b in weird_bytes[:20])}")
print(f"  0xA7: Could be a sequence command or table data")
print(f"  0x41: Another byte")
print(f"  0xA2: Another byte")
print(f"  Pattern repeats: A7 41 / A7 48 / etc.")

# Check what's in the first 642 bytes (the part at load address)
print(f"\n" + "="*80)
print("WHAT'S IN THE FIRST 642 BYTES?")
print("="*80)

first_region = sf2_data[2:644]
print(f"\nSize: {len(first_region):,} bytes (maps to ${load_addr:04X}-${load_addr + len(first_region) - 1:04X})")

# Find ASCII strings
ascii_regions = []
current_start = None
for i, b in enumerate(first_region):
    if 32 <= b < 127:
        if current_start is None:
            current_start = i
    else:
        if current_start is not None:
            ascii_regions.append((current_start, i))
            current_start = None

print(f"\nFound {len(ascii_regions)} ASCII regions in first 642 bytes:")
for start, end in ascii_regions[:10]:
    ascii_bytes = first_region[start:end]
    ascii_str = bytes(ascii_bytes).decode('ascii', errors='ignore')
    print(f"  Offset {start:3d}-{end:3d}: {ascii_str}")

print(f"\n" + "="*80)
