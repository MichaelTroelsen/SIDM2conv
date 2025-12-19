#!/usr/bin/env python3
"""Test the sequence at offset 0x2465"""

from sf2_viewer_core import unpack_sequence

# Read the sequence at offset 0x2465
with open('learnings/Laxity - Stinsen - Last Night Of 89.sf2', 'rb') as f:
    data = f.read()

offset = 0x2465
seq_bytes = bytearray()
i = 0
while offset + i < len(data) and i < 200:
    byte = data[offset + i]
    seq_bytes.append(byte)
    i += 1
    if byte == 0x7F:
        break

print(f'Sequence at offset 0x2465: {len(seq_bytes)} bytes')
print()
print('Raw bytes:')
hex_str = ' '.join(f'{b:02X}' for b in seq_bytes)
print(hex_str)
print()

# Unpack the sequence
events = unpack_sequence(bytes(seq_bytes))

print(f'Unpacked to {len(events)} events')
print()

# Show first 45 events
print('First 45 events (ALL tracks combined):')
print('Event | Inst | Cmd  | Note')
print('------|------|------|------')
for i in range(min(45, len(events))):
    event = events[i]
    inst = event['instrument']
    cmd = event['command']
    note = event['note']

    # Format for display
    if inst == 0x80:
        inst_str = '--'
    elif inst >= 0xA0:
        inst_str = f'{inst & 0x1F:02X}'
    else:
        inst_str = f'{inst:02X}'

    if cmd == 0x80:
        cmd_str = '--'
    elif cmd >= 0xC0:
        cmd_str = f'{cmd & 0x3F:02X}'
    else:
        cmd_str = f'{cmd:02X}'

    # Format note
    if note == 0x7E:
        note_str = '+++'
    elif note == 0x00:
        note_str = '---'
    else:
        # Convert to note name
        from sf2_viewer_core import SequenceEntry
        entry = SequenceEntry(note=note, instrument=0, command=0, param1=0, param2=0, duration=0)
        note_str = entry.note_name().strip()

    print(f'{i:5d} | {inst_str:4s} | {cmd_str:4s} | {note_str:6s}')

print()
print('=' * 100)
print('EXTRACTING TRACK 3 (every 3rd entry starting at index 2)')
print('=' * 100)
print()

track3_events = events[2::3]

print(f'Track 3 has {len(track3_events)} steps')
print()

print('TRACK 3:')
print('Step | Inst | Cmd  | Note')
print('-----|------|------|------')
for i in range(min(45, len(track3_events))):
    event = track3_events[i]
    inst = event['instrument']
    cmd = event['command']
    note = event['note']

    # Format for display
    if inst == 0x80:
        inst_str = '--'
    elif inst >= 0xA0:
        inst_str = f'{inst & 0x1F:02X}'
    else:
        inst_str = f'{inst:02X}'

    if cmd == 0x80:
        cmd_str = '--'
    elif cmd >= 0xC0:
        cmd_str = f'{cmd & 0x3F:02X}'
    else:
        cmd_str = f'{cmd:02X}'

    # Format note
    if note == 0x7E:
        note_str = '+++'
    elif note == 0x00:
        note_str = '---'
    else:
        from sf2_viewer_core import SequenceEntry
        entry = SequenceEntry(note=note, instrument=0, command=0, param1=0, param2=0, duration=0)
        note_str = entry.note_name().strip()

    print(f'{i:4d} | {inst_str:4s} | {cmd_str:4s} | {note_str:6s}')

print()
print('REFERENCE (first 45 steps):')
print('Step | Data')
print('-----|------')
with open('track_3.txt', 'r') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[1:46]):  # Skip "Track 3" header
        print(f'{i:4d} | {line.strip()}')

print()
print('=' * 100)
print('COMPARISON')
print('=' * 100)

# Parse reference
ref_entries = []
with open('track_3.txt', 'r') as f:
    lines = f.readlines()
    for line in lines[1:]:  # Skip header
        parts = line.strip().split()
        if len(parts) >= 3:
            # Handle "a00a 0b -- F-3" format
            if len(parts) == 4:
                inst = parts[1]
                cmd = parts[2]
                note = parts[3]
            else:
                inst = parts[0]
                cmd = parts[1]
                note = parts[2]
            ref_entries.append({'inst': inst.lower(), 'cmd': cmd.lower(), 'note': note.lower()})

matches = 0
total = min(len(track3_events), len(ref_entries))

for i in range(total):
    track3 = track3_events[i]
    ref = ref_entries[i]

    # Format track3 for comparison
    if track3['instrument'] == 0x80:
        t3_inst = '--'
    elif track3['instrument'] >= 0xA0:
        t3_inst = f'{track3["instrument"] & 0x1F:02x}'
    else:
        t3_inst = f'{track3["instrument"]:02x}'

    if track3['command'] == 0x80:
        t3_cmd = '--'
    elif track3['command'] >= 0xC0:
        t3_cmd = f'{track3["command"] & 0x3F:02x}'
    else:
        t3_cmd = f'{track3["command"]:02x}'

    if track3['note'] == 0x7E:
        t3_note = '+++'
    elif track3['note'] == 0x00:
        t3_note = '---'
    else:
        from sf2_viewer_core import SequenceEntry
        entry = SequenceEntry(note=track3['note'], instrument=0, command=0, param1=0, param2=0, duration=0)
        t3_note = entry.note_name().strip().lower()

    # Compare
    if t3_inst == ref['inst'] and t3_cmd == ref['cmd'] and t3_note == ref['note']:
        matches += 1

match_rate = 100 * matches / total if total > 0 else 0
print(f'Match rate: {matches}/{total} = {match_rate:.1f}%')
