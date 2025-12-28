#!/usr/bin/env python3
"""Check for filter data in converted SF2 file"""

# Read SF2 file
with open('test_stinsen_driver11.sf2', 'rb') as f:
    sf2_data = f.read()

# Search for filter pattern
pattern = bytes([0x9F, 0x00, 0xF2, 0x90, 0x2C, 0xF2])
filter_offset = sf2_data.find(pattern)

print('Filter Data Search in SF2 File:')
print('=' * 60)

if filter_offset != -1:
    print(f'\nFilter pattern found at offset: 0x{filter_offset:04X}')
    print(f'\nFirst 10 filter entries from SF2:')
    for i in range(10):
        offset = filter_offset + (i * 3)
        b1, b2, b3 = sf2_data[offset:offset+3]
        print(f'  {i:03d} | 0x{b1:02X} 0x{b2:02X} 0x{b3:02X}')
else:
    print('\nFilter pattern NOT found in SF2 file')
    print('Searching for partial pattern...')

    # Search for just first filter entry
    pattern2 = bytes([0x9F, 0x00, 0xF2])
    filter_offset = sf2_data.find(pattern2)

    if filter_offset != -1:
        print(f'\nPartial filter pattern found at: 0x{filter_offset:04X}')
        print(f'First 10 entries:')
        for i in range(10):
            offset = filter_offset + (i * 3)
            if offset + 3 <= len(sf2_data):
                b1, b2, b3 = sf2_data[offset:offset+3]
                print(f'  {i:03d} | 0x{b1:02X} 0x{b2:02X} 0x{b3:02X}')
    else:
        print('\nNo filter data found in SF2 file')
        print('\nThis confirms 0% filter accuracy - filters not converted')
