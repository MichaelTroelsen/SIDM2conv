#!/usr/bin/env python3
import struct

# Read SF2-packed SID
with open("SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid", 'rb') as f:
    packed_raw = f.read()

packed_load = struct.unpack('>H', packed_raw[8:10])[0]
if packed_load == 0:
    packed_load = struct.unpack('<H', packed_raw[0x7C:0x7C+2])[0]
    packed_music = packed_raw[0x7E:]
else:
    packed_music = packed_raw[0x7C:]

print(f"Packed load: ${packed_load:04X}")
print(f"Packed music size: {len(packed_music)} bytes")
print()

# Extract pulse using our method
pulse_addr = 0x09BC
offset = pulse_addr - packed_load
col_size = 25

print(f"Pulse address: ${pulse_addr:04X}")
print(f"Offset in packed_music: ${offset:04X} ({offset} bytes)")
print()

col0 = packed_music[offset:offset + col_size]
col1 = packed_music[offset + col_size:offset + 2*col_size]
col2 = packed_music[offset + 2*col_size:offset + 3*col_size]

print(f"Column 0 (first 10): {' '.join(f'{b:02X}' for b in col0[:10])}")
print(f"Column 1 (first 10): {' '.join(f'{b:02X}' for b in col1[:10])}")
print(f"Column 2 (first 10): {' '.join(f'{b:02X}' for b in col2[:10])}")
print()

# Now create 4-column format
pulse_4col = bytearray(256 * 4)
for i in range(col_size):
    pulse_4col[i] = col0[i]
    pulse_4col[256 + i] = col1[i]
    pulse_4col[512 + i] = col2[i]

print(f"4-column format column 0 (first 10): {' '.join(f'{pulse_4col[i]:02X}' for i in range(10))}")
print(f"4-column format column 1 (first 10): {' '.join(f'{pulse_4col[256+i]:02X}' for i in range(10))}")
print(f"4-column format column 2 (first 10): {' '.join(f'{pulse_4col[512+i]:02X}' for i in range(10))}")

