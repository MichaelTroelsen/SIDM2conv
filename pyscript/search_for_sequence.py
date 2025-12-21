#!/usr/bin/env python3
"""Search for the actual sequence matching the reference"""

# The reference starts with: 0b -- F-3
# This means we're looking for a sequence with:
#   - Instrument byte 0xAB (packed format for instrument 0x0B)
#   - Note byte 0x29 (F-3)
# Pattern: AB ?? 29 where ?? could be duration or command

with open('learnings/Laxity - Stinsen - Last Night Of 89.sf2', 'rb') as f:
    data = f.read()

print('Searching for pattern: AB ?? 29 (instrument 0B, any byte, note F-3)...')
print()

matches = []
for i in range(len(data) - 10):
    if data[i] == 0xAB and data[i+2] == 0x29:
        matches.append(i)

print(f'Found {len(matches)} potential matches:')
print()

for match_offset in matches[:20]:  # Show first 20 matches
    # Show context around the match
    context_start = max(0, match_offset - 5)
    context_end = min(len(data), match_offset + 30)

    context_bytes = data[context_start:context_end]
    hex_str = ' '.join(f'{b:02X}' for b in context_bytes)

    # Mark the match position
    match_pos = (match_offset - context_start) * 3  # *3 for "XX " spacing
    marker = ' ' * match_pos + '^^^'

    print(f'Offset 0x{match_offset:04X}:')
    print(f'  {hex_str}')
    print(f'  {marker}')

    # Try to extract a sequence starting from this offset
    seq_bytes = []
    offset = match_offset
    for j in range(100):
        if offset + j >= len(data):
            break
        byte = data[offset + j]
        seq_bytes.append(byte)
        if byte == 0x7F:  # End marker
            break

    if len(seq_bytes) > 10 and seq_bytes[-1] == 0x7F:
        print(f'  → Sequence found: {len(seq_bytes)} bytes ending with 0x7F')
        # Show first 20 bytes
        seq_hex = ' '.join(f'{b:02X}' for b in seq_bytes[:20])
        print(f'    First 20 bytes: {seq_hex}')
    else:
        print(f'  → No valid sequence (no 0x7F terminator within 100 bytes)')

    print()

print()
print('=' * 100)
print('REFERENCE PATTERN ANALYSIS')
print('=' * 100)
print()

# Parse the reference to understand what we're looking for
with open('track_3.txt', 'r') as f:
    lines = f.readlines()

print('Reference file shows:')
for i, line in enumerate(lines[:10]):
    print(f'  {i}: {line.strip()}')

print()
print('Expected packed byte sequence for first few steps:')
print('  Step 0: 0b -- F-3  → AB ?? 29 (AB=instrument 0B, 29=F-3)')
print('  Step 1: -- -- +++  → 7E (just gate on)')
print('  Step 2: -- 02 +++  → C2 7E (C2=command 02, 7E=gate on)')
print('  Step 3: -- -- +++  → 7E')
print('  Step 4: -- -- F-3  → 29 (just note F-3)')
print()
print('So the pattern should start like: AB ?? 29 7E C2 7E 7E 29 ...')
print('  where ?? is likely a duration/command byte')
