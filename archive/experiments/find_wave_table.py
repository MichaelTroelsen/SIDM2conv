#!/usr/bin/env python3
"""Find wave table in SF2-packed SID file"""

# Read SF2-packed SID
with open("SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid", 'rb') as f:
    data = f.read()

print("Searching for wave table in SF2-packed SID...")
print()

# Wave table format in SF2-packed: 2 columns (waveform, note_offset)
# Looking for patterns at various offsets

# Try reading from file offset $09F1 (right after pulse at $09BC + 75 bytes)
pulse_end = 0x09BC + 75  # 3 columns * 25 bytes
wave_offset = pulse_end

print(f"Checking offset ${wave_offset:04X} (after pulse table):")
for i in range(20):
    offset = wave_offset + i
    b1 = data[offset] if offset < len(data) else 0
    b2 = data[offset + 1] if offset + 1 < len(data) else 0
    print(f"  ${offset:04X}: {b1:02X} {b2:02X}")

print()

# Also check common SF2-packed wave table location (often around $0A00-$0B00)
print("Checking offset $0A00 area:")
for i in range(20):
    offset = 0x0A00 + i
    b1 = data[offset] if offset < len(data) else 0
    b2 = data[offset + 1] if offset + 1 < len(data) else 0
    print(f"  ${offset:04X}: {b1:02X} {b2:02X}")

print()

# Check what the working SF2 file has for wave table
print("Wave table from working FIXED.sf2 file:")
with open("output/Stinsens_Last_Night_of_89_FIXED.sf2", 'rb') as f:
    sf2_data = f.read()

import struct
load_addr = struct.unpack('<H', sf2_data[0:2])[0]
wave_addr = 0x1924  # Driver 11 wave table address
file_offset = wave_addr - load_addr + 2

print(f"Load address: ${load_addr:04X}")
print(f"Wave table at ${wave_addr:04X}, file offset ${file_offset:04X}")
print()

# Read first 20 entries (2 bytes each, column-major: 256 bytes per column)
print("Column 0 (waveform) - first 20 bytes:")
col0 = sf2_data[file_offset:file_offset + 20]
print(' '.join(f'{b:02X}' for b in col0))

print()
print("Column 1 (note offset) - first 20 bytes:")
col1 = sf2_data[file_offset + 256:file_offset + 256 + 20]
print(' '.join(f'{b:02X}' for b in col1))
