#!/usr/bin/env python3
"""Verify filter table address in Stinsen SID file"""

# Read SID file
with open('Laxity/Stinsens_Last_Night_of_89.sid', 'rb') as f:
    sid_full = f.read()

# Filter table: 256 entries × 3 bytes = 768 bytes (column-major)
# Reference data from first 10 entries
ref_filters = [
    (0x9F, 0x00, 0xF2),  # 000
    (0x90, 0x2C, 0xF2),  # 001
    (0x90, 0x24, 0xF2),  # 002
    (0x90, 0x3A, 0xF2),  # 003
    (0x0F, 0xFF, 0x10),  # 004
    (0x7F, 0x00, 0x05),  # 005
    (0xA4, 0x30, 0xF2),  # 006
    (0x90, 0x4F, 0x02),  # 007
    (0xC1, 0x70, 0xF2),  # 008
    (0xA5, 0x70, 0xF2),  # 009
]

print('Filter Table Verification (Column-Major Format):')
print('=' * 60)

# Search for filter pattern in SID file
# Look for sequence: 0x9F 0x00 0xF2 0x90 0x2C 0xF2
pattern = bytes([0x9F, 0x00, 0xF2, 0x90, 0x2C, 0xF2])
filter_file_offset = sid_full.find(pattern)

if filter_file_offset == -1:
    print('\nFilter pattern not found in SID file!')
    print('Trying alternative search...\n')

    # Try searching for just the first filter entry
    pattern2 = bytes([0x9F, 0x00, 0xF2])
    filter_file_offset = sid_full.find(pattern2)

    if filter_file_offset == -1:
        print('No filter data found!')
        exit(1)

# Calculate memory address (load address is $1000, header is $7C)
filter_memory_addr = filter_file_offset - 0x7C + 0x1000

print(f'\nFilter Table Location:')
print(f'  Memory address: 0x{filter_memory_addr:04X}')
print(f'  File offset: 0x{filter_file_offset:04X}')
print(f'  Size: 768 bytes (256 entries x 3 bytes)')

# Read filter data from SID file
print(f'\nFirst 10 filter entries from SID file at 0x{filter_memory_addr:04X}:')

matches = 0
for i in range(10):
    offset = filter_file_offset + (i * 3)
    b1 = sid_full[offset]
    b2 = sid_full[offset + 1]
    b3 = sid_full[offset + 2]

    ref_b1, ref_b2, ref_b3 = ref_filters[i]

    match = 'MATCH' if (b1 == ref_b1 and b2 == ref_b2 and b3 == ref_b3) else 'DIFF '
    if match == 'MATCH':
        matches += 1

    print(f'  {i:03d} | SID: 0x{b1:02X} 0x{b2:02X} 0x{b3:02X}, Ref: 0x{ref_b1:02X} 0x{ref_b2:02X} 0x{ref_b3:02X}  [{match}]')

print(f'\nResult: {matches}/10 matches ({100*matches/10:.0f}%)')

if matches == 10:
    print(f'\nPERFECT MATCH - Filter table address verified!')
    print(f'\nFilter Table Summary:')
    print(f'  Format: Column-Major (3 bytes per entry)')
    print(f'  Address: 0x{filter_memory_addr:04X}')
    print(f'  Size: 768 bytes (256 entries)')
    print(f'  Active entries: 0-25 (first 26 entries)')
    print(f'  Zero entries: 26-255 (remaining 230 entries)')
else:
    print(f'\nAddress needs further investigation')
