#!/usr/bin/env python3
"""Check filter data in SF2 file."""

import sys

sf2_file = sys.argv[1] if len(sys.argv) > 1 else 'test_output/Aids_Trouble_filtered.sf2'

# Read SF2 file
with open(sf2_file, 'rb') as f:
    data = f.read()

# Filter table is at address $1A1E in the SF2 driver
# SF2 file starts at $0D7E, so file offset is:
filter_offset = 0x1A1E - 0x0D7E + 2  # +2 for header bytes

filter_data = data[filter_offset:filter_offset+128]

print(f'Filter table at file offset 0x{filter_offset:04X} (address $1A1E):')
print(f'First 64 bytes: {filter_data[:64].hex(" ")}')
print(f'Last 64 bytes:  {filter_data[64:].hex(" ")}')

non_zero = sum(1 for b in filter_data if b != 0)
print(f'\nNon-zero bytes: {non_zero}/128 ({non_zero*100//128}%)')

# Show first few non-zero entries
print('\nFirst 10 non-zero bytes and their positions:')
count = 0
for i, b in enumerate(filter_data):
    if b != 0:
        print(f'  Offset {i:3d} (${filter_offset+i:04X}): ${b:02X}')
        count += 1
        if count >= 10:
            break
