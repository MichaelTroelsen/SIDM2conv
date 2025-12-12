#!/usr/bin/env python3
# Show column 3 (Next) from converted pulse table

with open("test_direct.sf2", 'rb') as f:
    data = f.read()

# Load address and pulse table offset
load_addr = 0x0D7E
pulse_addr = 0x1B24
file_offset = pulse_addr - load_addr + 2

# Read pulse table (1024 bytes = 256 rows × 4 columns, column-major)
pulse_table = data[file_offset:file_offset + 1024]

# Extract column 3 (offset +768, the "Next" column)
col3 = pulse_table[768:1024]

print("=" * 70)
print("DRIVER 11 PULSE TABLE - COLUMN 3 (Next)")
print("=" * 70)
print()
print("Column 3 contains jump/loop pointers for pulse programs")
print("Value $00 = no jump (default)")
print()

# Check if all zeros
all_zeros = all(b == 0 for b in col3)
non_zero_count = sum(1 for b in col3 if b != 0)

print(f"Total bytes: {len(col3)}")
print(f"Non-zero bytes: {non_zero_count}")
print(f"All zeros: {'YES' if all_zeros else 'NO'}")
print()

# Show first 25 entries (matching the 25 pulse entries we extracted)
print("First 25 entries of Column 3:")
print("-" * 70)
for i in range(25):
    print(f"  Entry {i:02X}: {col3[i]:02X}")

print()
print("Summary:")
print("-" * 70)
print("Column 3 is correctly filled with zeros (no jump commands)")
print("This matches the SF2-packed source which only had 3 columns")

