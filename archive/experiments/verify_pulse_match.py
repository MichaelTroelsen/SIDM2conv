#!/usr/bin/env python3
# Verify pulse extraction matches expected values

with open("SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid", 'rb') as f:
    data = f.read()

offset = 0x09BC
pulse_data = data[offset:offset + 75]

col0 = pulse_data[0:25]
col1 = pulse_data[25:50]
col2 = pulse_data[50:75]

print("\nVERIFICATION:")
print("-" * 60)
print(f"Column 1 starts with: {' '.join(f'{b:02X}' for b in col1[:6])}")
print(f"  Expected: 00 00 70 40 10 F0")
match1 = col1[:6] == bytes([0x00, 0x00, 0x70, 0x40, 0x10, 0xF0])
print(f"  Match: {'YES' if match1 else 'NO'}")

print()
print(f"Column 2 starts with: {' '.join(f'{b:02X}' for b in col2[:6])}")
print(f"  Expected: 01 00 04 20 20 04")
match2 = col2[:6] == bytes([0x01, 0x00, 0x04, 0x20, 0x20, 0x04])
print(f"  Match: {'YES' if match2 else 'NO'}")

print()
if match1 and match2:
    print("SUCCESS: All columns extracted correctly!")
else:
    print("ERROR: Extraction mismatch!")
