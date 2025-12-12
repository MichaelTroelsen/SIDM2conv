#!/usr/bin/env python3
# Final verification against user's specifications

with open("SIDSF2player/SF2packed_Stinsens_Last_Night_of_89.sid", 'rb') as f:
    data = f.read()

offset = 0x09BC
col0 = data[offset:offset + 25]
col1 = data[offset + 25:offset + 50]
col2 = data[offset + 50:offset + 75]

print("=" * 70)
print("PULSE TABLE EXTRACTION VERIFICATION")
print("=" * 70)
print()
print("User's specifications:")
print("-" * 70)
print("  Column 1 should start with: 00 00 70 40 10 f0")
print("  Column 2 should start with: 00 01 00 04 20 20")
print()

print("Actual extracted data:")
print("-" * 70)
col1_start = ' '.join(f'{b:02X}' for b in col1[:6])
col2_start = ' '.join(f'{b:02X}' for b in col2[:6])

print(f"  Column 1 starts with: {col1_start}")
print(f"  Column 2 starts with: {col2_start}")
print()

# Check matches (case insensitive comparison)
match1 = col1_start.upper() == "00 00 70 40 10 F0"
match2 = col2_start.upper() == "00 01 00 04 20 20"

print("Results:")
print("-" * 70)
print(f"  Column 1: {'MATCH' if match1 else 'MISMATCH'}")
print(f"  Column 2: {'MATCH' if match2 else 'MISMATCH'}")
print()

if match1 and match2:
    print("SUCCESS: Pulse table extraction is CORRECT!")
else:
    print("ERROR: Extraction mismatch!")

print()
print("All 3 columns in full:")
print("-" * 70)
print(f"Column 0 (Value):    {' '.join(f'{b:02X}' for b in col0)}")
print(f"Column 1 (Delta):    {' '.join(f'{b:02X}' for b in col1)}")
print(f"Column 2 (Duration): {' '.join(f'{b:02X}' for b in col2)}")

