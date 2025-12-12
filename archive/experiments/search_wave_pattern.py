#!/usr/bin/env python3
"""Search for wave table pattern in SF2-packed SID"""

# Read SF2-packed SID
with open("SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid", 'rb') as f:
    data = f.read()

# Expected wave table data from working SF2
wave_col0 = bytes([0x21, 0x21, 0x41, 0x7F, 0x81, 0x41, 0x41, 0x41, 0x7F, 0x81])
wave_col1 = bytes([0x80, 0x80, 0x00, 0x02, 0xC0, 0xA1, 0x9A, 0x00, 0x07, 0xC4])

print("Searching for wave table Column 0 pattern:")
print(f"  Looking for: {' '.join(f'{b:02X}' for b in wave_col0)}")

# Search for column 0
for i in range(len(data) - len(wave_col0)):
    if data[i:i+len(wave_col0)] == wave_col0:
        print(f"  Found at offset ${i:04X}")

print()
print("Searching for wave table Column 1 pattern:")
print(f"  Looking for: {' '.join(f'{b:02X}' for b in wave_col1)}")

# Search for column 1
for i in range(len(data) - len(wave_col1)):
    if data[i:i+len(wave_col1)] == wave_col1:
        print(f"  Found at offset ${i:04X}")

print()
print("Trying interleaved format (alternating bytes):")
# Maybe it's stored as: waveform, note_offset, waveform, note_offset...
interleaved = bytearray()
for i in range(10):
    interleaved.append(wave_col0[i])
    interleaved.append(wave_col1[i])

print(f"  Looking for: {' '.join(f'{interleaved[i]:02X}' for i in range(20))}")

for i in range(len(data) - len(interleaved)):
    if data[i:i+len(interleaved)] == bytes(interleaved):
        print(f"  Found at offset ${i:04X}")

print()
print("Just checking what's at common wave locations:")
print()

# Check around $0A00 area more carefully
for offset in [0x09F1, 0x0A00, 0x0A10, 0x0A20, 0x0A30, 0x0A40, 0x0A50]:
    print(f"Offset ${offset:04X}:")
    # Read as if it's 2-column format (waveform, note_offset pairs)
    for i in range(5):
        idx = offset + i * 2
        if idx + 1 < len(data):
            wave = data[idx]
            note = data[idx + 1]
            print(f"  Entry {i:2d}: {wave:02X} {note:02X}")
    print()
