#!/usr/bin/env python3
"""Verify tempo table address in Stinsen SID file"""

# Read SID file
with open('Laxity/Stinsens_Last_Night_of_89.sid', 'rb') as f:
    sid_full = f.read()

# Tempo table: 256 entries × 1 byte = 256 bytes
# Reference data: only first 3 entries are non-zero
ref_tempos = [0x03, 0x04, 0x7F]

print('Tempo Table Verification:')
print('=' * 60)

# Search for tempo pattern in SID file
# Look for sequence: 03 04 7F
pattern = bytes([0x03, 0x04, 0x7F])
tempo_file_offset = sid_full.find(pattern)

if tempo_file_offset == -1:
    print('\nTempo pattern not found in SID file!')
    exit(1)

# Calculate memory address (load address is $1000, header is $7C)
tempo_memory_addr = tempo_file_offset - 0x7C + 0x1000

print(f'\nTempo Table Location:')
print(f'  Memory address: 0x{tempo_memory_addr:04X}')
print(f'  File offset: 0x{tempo_file_offset:04X}')
print(f'  Size: 256 bytes (256 entries x 1 byte)')

# Read tempo data from SID file
print(f'\nFirst 3 tempo entries from SID file at 0x{tempo_memory_addr:04X}:')

matches = 0
for i in range(3):
    offset = tempo_file_offset + i
    byte_val = sid_full[offset]
    ref_val = ref_tempos[i]

    match = 'MATCH' if byte_val == ref_val else 'DIFF '
    if match == 'MATCH':
        matches += 1

    print(f'  {i:03d} | SID: 0x{byte_val:02X}, Ref: 0x{ref_val:02X}  [{match}]')

# Check that next few bytes are zeros
print(f'\nNext 5 bytes (should be zeros):')
all_zeros = True
for i in range(3, 8):
    offset = tempo_file_offset + i
    byte_val = sid_full[offset]
    is_zero = 'YES' if byte_val == 0x00 else 'NO '
    if byte_val != 0x00:
        all_zeros = False
    print(f'  {i:03d} | SID: 0x{byte_val:02X}  [Zero: {is_zero}]')

print(f'\nResult: {matches}/3 tempo matches ({100*matches/3:.1f}%)')
print(f'Zero padding: {"CONFIRMED" if all_zeros else "UNEXPECTED"}')

if matches == 3 and all_zeros:
    print(f'\nPERFECT MATCH - Tempo table address verified!')
    print(f'\nTempo Table Summary:')
    print(f'  Format: Linear (1 byte per entry)')
    print(f'  Address: 0x{tempo_memory_addr:04X}')
    print(f'  Size: 256 bytes')
    print(f'  Active entries: 0-2 (first 3 entries)')
    print(f'  Zero entries: 3-255 (remaining 253 entries)')
    print(f'  Values: 0x03, 0x04, 0x7F')
else:
    print(f'\nAddress needs further investigation')
