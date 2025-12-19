#!/usr/bin/env python3
"""Test sequence format - check if track interleaving is correct"""

from sf2_viewer_core import SF2Parser

parser = SF2Parser('learnings/Laxity - Stinsen - Last Night Of 89.sf2')

# Try sequence 10 (the one user said is 0x0A)
seq = parser.sequences[10]

print(f'Sequence 10 has {len(seq)} total entries')
print()

# Show first 15 entries WITHOUT track splitting
print('All entries (no track splitting):')
print('Entry | Inst | Cmd  | Note')
print('------|------|------|------')
for i in range(min(15, len(seq))):
    entry = seq[i]
    inst = f'{entry.instrument:02X}' if entry.instrument != 0x80 else '--'
    cmd = f'{entry.command:02X}' if entry.command != 0x80 else '--'
    note = entry.note_name().strip()
    print(f'{i:5d} | {inst:4s} | {cmd:4s} | {note:6s}')

print()
print('Compare with reference (first 10 steps):')
with open('track_3.txt', 'r') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[:10]):
        print(f'Ref {i:2d}: {line.strip()}')
