#!/usr/bin/env python3
"""Search for any filter-related bytes in SID file"""

# Read SID file
with open('Laxity/Stinsens_Last_Night_of_89.sid', 'rb') as f:
    sid_full = f.read()

print('Searching for Filter-Related Bytes in SID File:')
print('=' * 60)

# Search for distinctive filter bytes from reference
filter_bytes = [
    ([0x9F, 0x00, 0xF2], 'Filter entry 0'),
    ([0x90, 0x2C, 0xF2], 'Filter entry 1'),
    ([0x90, 0x24, 0xF2], 'Filter entry 2'),
    ([0x90, 0x3A, 0xF2], 'Filter entry 3'),
    ([0x0F, 0xFF, 0x10], 'Filter entry 4'),
    ([0xA4, 0x30, 0xF2], 'Filter entry 6'),
    ([0xC1, 0x70, 0xF2], 'Filter entry 8'),
]

found_any = False
for pattern_bytes, description in filter_bytes:
    pattern = bytes(pattern_bytes)
    offset = sid_full.find(pattern)
    if offset != -1:
        mem_addr = offset - 0x7C + 0x1000
        print(f'\nFound: {description}')
        print(f'  Pattern: {" ".join(f"0x{b:02X}" for b in pattern)}')
        print(f'  File offset: 0x{offset:04X}')
        print(f'  Memory addr: 0x{mem_addr:04X}')
        found_any = True

if not found_any:
    print('\nNo filter patterns found in SID file')
    print('\nConclusion:')
    print('  - Filter data exists in SF2 reference (Filter.txt)')
    print('  - Filter data does NOT exist in Laxity NP21 SID file')
    print('  - Laxity player does not use SF2-style filter tables')
    print('  - This explains 0% filter conversion accuracy')
    print('\nPossible reasons:')
    print('  1. Laxity uses different filter format (not table-based)')
    print('  2. Laxity encodes filters in sequence data (inline)')
    print('  3. Laxity does not use filters in this tune')
