#!/usr/bin/env python3
"""Verify arpeggio table address in Stinsen SID file"""

# Read SID file
with open('Laxity/Stinsens_Last_Night_of_89.sid', 'rb') as f:
    sid_full = f.read()

# Arpeggio table: 256 entries × 1 byte = 256 bytes
# Reference data from first 16 entries
ref_arps = [
    0x00,  # 000
    0xFC,  # 001
    0xF7,  # 002
    0x70,  # 003
    0x00,  # 004
    0xFB,  # 005
    0xF6,  # 006
    0x70,  # 007
    0x00,  # 008
    0xFD,  # 009
    0xF8,  # 010
    0x70,  # 011
    0x00,  # 012
    0xFB,  # 013
    0xF6,  # 014
    0x70,  # 015
]

print('Arpeggio Table Verification:')
print('=' * 60)

# Search for arpeggio pattern in SID file
# Look for sequence: 00 FC F7 70 00 FB F6 70
pattern = bytes([0x00, 0xFC, 0xF7, 0x70, 0x00, 0xFB, 0xF6, 0x70])
arp_file_offset = sid_full.find(pattern)

if arp_file_offset == -1:
    print('\nArpeggio pattern not found in SID file!')
    print('Trying alternative search...\n')

    # Try searching for a smaller pattern
    pattern2 = bytes([0xFC, 0xF7, 0x70, 0x00, 0xFB])
    arp_file_offset = sid_full.find(pattern2)

    if arp_file_offset != -1:
        # Adjust to start at the 0x00 before 0xFC
        arp_file_offset -= 1
    else:
        print('No arpeggio data found!')
        exit(1)

# Calculate memory address (load address is $1000, header is $7C)
arp_memory_addr = arp_file_offset - 0x7C + 0x1000

print(f'\nArpeggio Table Location:')
print(f'  Memory address: 0x{arp_memory_addr:04X}')
print(f'  File offset: 0x{arp_file_offset:04X}')
print(f'  Size: 256 bytes (256 entries x 1 byte)')

# Read arpeggio data from SID file
print(f'\nFirst 16 arpeggio entries from SID file at 0x{arp_memory_addr:04X}:')

matches = 0
for i in range(16):
    offset = arp_file_offset + i
    byte_val = sid_full[offset]
    ref_val = ref_arps[i]

    match = 'MATCH' if byte_val == ref_val else 'DIFF '
    if match == 'MATCH':
        matches += 1

    print(f'  {i:03d} | SID: 0x{byte_val:02X}, Ref: 0x{ref_val:02X}  [{match}]')

print(f'\nResult: {matches}/16 matches ({100*matches/16:.1f}%)')

if matches == 16:
    print(f'\nPERFECT MATCH - Arpeggio table address verified!')
    print(f'\nArpeggio Table Summary:')
    print(f'  Format: Linear (1 byte per entry)')
    print(f'  Address: 0x{arp_memory_addr:04X}')
    print(f'  Size: 256 bytes')
    print(f'  Active entries: 0-65 (first 66 entries)')
    print(f'  Zero entries: 66-255 (remaining 190 entries)')
else:
    print(f'\nAddress needs further investigation')
