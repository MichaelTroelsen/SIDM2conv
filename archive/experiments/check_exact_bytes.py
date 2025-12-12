#!/usr/bin/env python3
# Check exact byte positions

with open("SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid", 'rb') as f:
    data = f.read()

offset = 0x09BC

print("Checking byte positions:")
print("-" * 60)
print(f"Byte 24 (last of col0): ${offset+24:04X} = {data[offset+24]:02X}")
print(f"Byte 25 (first of col1): ${offset+25:04X} = {data[offset+25]:02X}")
print()
print(f"Byte 49 (last of col1): ${offset+49:04X} = {data[offset+49]:02X}")
print(f"Byte 50 (first of col2): ${offset+50:04X} = {data[offset+50]:02X}")
print()

# Show columns
col0 = data[offset:offset + 25]
col1 = data[offset + 25:offset + 50]
col2 = data[offset + 50:offset + 75]

print("Column 0 (bytes 0-24):")
print(f"  First 6: {' '.join(f'{b:02X}' for b in col0[:6])}")
print()

print("Column 1 (bytes 25-49):")
print(f"  First 6: {' '.join(f'{b:02X}' for b in col1[:6])}")
print(f"  Expected: 00 00 70 40 10 F0")
print()

print("Column 2 (bytes 50-74):")
print(f"  First 6: {' '.join(f'{b:02X}' for b in col2[:6])}")
print(f"  User said: 01 00 04 20 20 04  (but originally said 'column 2 should start with 00 01 00 04 20 20')")
print()

# Check what the user actually said
print("Wait - let me check the actual start:")
print(f"  Byte 50: {data[offset+50]:02X}")
print(f"  Byte 51: {data[offset+51]:02X}")
print(f"  Byte 52: {data[offset+52]:02X}")
print(f"  Byte 53: {data[offset+53]:02X}")
print(f"  Byte 54: {data[offset+54]:02X}")
print(f"  Byte 55: {data[offset+55]:02X}")

