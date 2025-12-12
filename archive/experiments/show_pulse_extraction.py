#!/usr/bin/env python3
"""
Show pulse table extraction in detail
"""

# Read SF2-packed SID
with open("SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid", 'rb') as f:
    data = f.read()

# Extract at offset $09BC
offset = 0x09BC
pulse_data = data[offset:offset + 75]

print("=" * 80)
print("RAW PULSE DATA FROM SF2-PACKED SID")
print("=" * 80)
print(f"\nStarting at offset: ${offset:04X}")
print(f"Total bytes: {len(pulse_data)} (3 columns × 25 bytes each)\n")

# Show as 3 consecutive columns
col0 = pulse_data[0:25]
col1 = pulse_data[25:50]
col2 = pulse_data[50:75]

print("COLUMN 0 (Value) - Bytes 0-24:")
print("  " + " ".join(f"{b:02X}" for b in col0))
print()

print("COLUMN 1 (Delta) - Bytes 25-49:")
print("  " + " ".join(f"{b:02X}" for b in col1))
print()

print("COLUMN 2 (Duration) - Bytes 50-74:")
print("  " + " ".join(f"{b:02X}" for b in col2))
print()

print("=" * 80)
print("EXTRACTED ENTRIES (reading across columns)")
print("=" * 80)
print("\nEntry | Value | Delta | Duration | Interpretation")
print("-" * 70)

for i in range(25):
    value = col0[i]
    delta = col1[i]
    duration = col2[i]
    
    # Interpret common values
    interp = ""
    if value == 0x7F:
        interp = "End/Jump marker"
    elif value == 0x88:
        interp = "Pulse value $088"
    elif value == 0x81:
        interp = "Pulse value $081"
    
    print(f"  {i:02X}  |  {value:02X}   |  {delta:02X}   |   {duration:02X}     | {interp}")

print()
print("=" * 80)
print("VERIFICATION")
print("=" * 80)
print(f"\nColumn 1 starts with: {' '.join(f'{b:02X}' for b in col1[:6])}")
print(f"  Expected: 00 00 70 40 10 F0")
print(f"  Match: {'✓' if col1[:6] == bytes([0x00, 0x00, 0x70, 0x40, 0x10, 0xF0]) else '✗'}")
print()
print(f"Column 2 starts with: {' '.join(f'{b:02X}' for b in col2[:6])}")
print(f"  Expected: 01 00 04 20 20 04")
print(f"  Match: {'✓' if col2[:6] == bytes([0x01, 0x00, 0x04, 0x20, 0x20, 0x04]) else '✗'}")

