#!/usr/bin/env python3
"""Test if reference matches Track 1 or Track 2 instead of Track 3"""

from sf2_viewer_core import SF2Parser

parser = SF2Parser('learnings/Laxity - Stinsen - Last Night Of 89.sf2')

# Test sequence 6 (best match)
seq = parser.sequences[6]

print('=' * 100)
print('SEQUENCE 6 - ALL THREE TRACKS')
print('=' * 100)
print()

# Extract all 3 tracks
track1 = seq[0::3]  # Every 3rd entry starting at index 0
track2 = seq[1::3]  # Every 3rd entry starting at index 1
track3 = seq[2::3]  # Every 3rd entry starting at index 2

print(f'Track 1: {len(track1)} steps')
print(f'Track 2: {len(track2)} steps')
print(f'Track 3: {len(track3)} steps')
print()

# Show first 15 steps of each track
print('TRACK 1 (first 15 steps):')
print('Step | Inst | Cmd  | Note')
print('-----|------|------|------')
for i in range(min(15, len(track1))):
    entry = track1[i]
    inst = f'{entry.instrument & 0x1F:02X}' if entry.instrument >= 0xA0 else ('--' if entry.instrument == 0x80 else f'{entry.instrument:02X}')
    cmd = f'{entry.command & 0x3F:02X}' if entry.command >= 0xC0 else ('--' if entry.command == 0x80 else f'{entry.command:02X}')
    note = entry.note_name().strip()
    print(f'{i:4d} | {inst:4s} | {cmd:4s} | {note:6s}')

print()
print('TRACK 2 (first 15 steps):')
print('Step | Inst | Cmd  | Note')
print('-----|------|------|------')
for i in range(min(15, len(track2))):
    entry = track2[i]
    inst = f'{entry.instrument & 0x1F:02X}' if entry.instrument >= 0xA0 else ('--' if entry.instrument == 0x80 else f'{entry.instrument:02X}')
    cmd = f'{entry.command & 0x3F:02X}' if entry.command >= 0xC0 else ('--' if entry.command == 0x80 else f'{entry.command:02X}')
    note = entry.note_name().strip()
    print(f'{i:4d} | {inst:4s} | {cmd:4s} | {note:6s}')

print()
print('TRACK 3 (first 15 steps):')
print('Step | Inst | Cmd  | Note')
print('-----|------|------|------')
for i in range(min(15, len(track3))):
    entry = track3[i]
    inst = f'{entry.instrument & 0x1F:02X}' if entry.instrument >= 0xA0 else ('--' if entry.instrument == 0x80 else f'{entry.instrument:02X}')
    cmd = f'{entry.command & 0x3F:02X}' if entry.command >= 0xC0 else ('--' if entry.command == 0x80 else f'{entry.command:02X}')
    note = entry.note_name().strip()
    print(f'{i:4d} | {inst:4s} | {cmd:4s} | {note:6s}')

print()
print('REFERENCE (first 15 steps):')
print('Step | Data')
print('-----|------')
with open('track_3.txt', 'r') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[1:16]):  # Skip "Track 3" header
        print(f'{i:4d} | {line.strip()}')

print()
print('=' * 100)
print('COMPARING PATTERNS:')
print('=' * 100)
print()

# Check if any track shows instrument 0b at step 0
print('Looking for instrument 0B at step 0:')
for track_num, track in [(1, track1), (2, track2), (3, track3)]:
    if len(track) > 0:
        entry = track[0]
        if entry.instrument >= 0xA0:
            inst_val = entry.instrument & 0x1F
        else:
            inst_val = entry.instrument if entry.instrument != 0x80 else None

        if inst_val == 0x0B:
            print(f'  Track {track_num}: ✓ Has instrument 0B at step 0')
        elif inst_val is not None:
            print(f'  Track {track_num}: Has instrument {inst_val:02X} at step 0')
        else:
            print(f'  Track {track_num}: No instrument at step 0')

print()
print('Looking for F-3 note at step 0:')
for track_num, track in [(1, track1), (2, track2), (3, track3)]:
    if len(track) > 0:
        entry = track[0]
        note_name = entry.note_name().strip()
        if note_name == 'F-3':
            print(f'  Track {track_num}: ✓ Has F-3 at step 0')
        else:
            print(f'  Track {track_num}: Has {note_name} at step 0')
