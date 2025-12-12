#!/usr/bin/env python3
import struct

# Read template
with open("G5/examples/Driver 11 Test - Arpeggio.sf2", 'rb') as f:
    sf2_data = bytearray(f.read())

orig_load = struct.unpack('<H', sf2_data[0:2])[0]

# Extract pulse from SF2-packed SID
with open("SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid", 'rb') as f:
    packed_raw = f.read()

# Extract
offset = 0x09BC
col_size = 25
col0 = packed_raw[offset:offset + col_size]
col1 = packed_raw[offset + col_size:offset + 2*col_size]
col2 = packed_raw[offset + 2*col_size:offset + 3*col_size]

# Convert to 4-column
pulse_4col = bytearray(256 * 4)
for i in range(col_size):
    pulse_4col[i] = col0[i]
    pulse_4col[256 + i] = col1[i]
    pulse_4col[512 + i] = col2[i]

print(f"Extracted pulse column 0 (first 10): {' '.join(f'{pulse_4col[i]:02X}' for i in range(10))}")

# Write to SF2
pulse_addr = 0x13E0  # From the script
sf2_offset = pulse_addr - orig_load + 2

print(f"Writing to SF2 at offset ${sf2_offset:04X}")
print(f"Length: {len(pulse_4col)} bytes")

sf2_data[sf2_offset:sf2_offset + len(pulse_4col)] = pulse_4col

# Write output
with open("test_manual_write.sf2", 'wb') as f:
    f.write(sf2_data)

# Read back
print()
print("Reading back from output file:")
pulse_readback = sf2_data[sf2_offset:sf2_offset + 10]
print(f"Pulse column 0 (first 10): {' '.join(f'{b:02X}' for b in pulse_readback)}")

