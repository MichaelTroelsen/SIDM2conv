#!/usr/bin/env python3
"""Verify wave table address in Stinsen SID file"""

# Read SID file
with open('Laxity/Stinsens_Last_Night_of_89.sid', 'rb') as f:
    sid_full = f.read()

# Wave table location found earlier
waveform_file_offset = 0x0958  # Memory 0x18DC
waveform_memory_addr = 0x18DC

# Notes should be 256 bytes after waveforms
notes_file_offset = waveform_file_offset + 256
notes_memory_addr = waveform_memory_addr + 256

print(f'Wave Table Verification (Row-Major Format):')
print(f'=' * 60)
print(f'\nWaveforms:')
print(f'  Memory address: 0x{waveform_memory_addr:04X}')
print(f'  File offset: 0x{waveform_file_offset:04X}')
print(f'  Size: 256 bytes')

print(f'\nNotes:')
print(f'  Memory address: 0x{notes_memory_addr:04X}')
print(f'  File offset: 0x{notes_file_offset:04X}')
print(f'  Size: 256 bytes')

# Read notes from SID file
notes_sid = sid_full[notes_file_offset:notes_file_offset+256]

# Reference notes (first 10)
ref_notes = [0x80, 0x80, 0x00, 0x02, 0xC0, 0xA1, 0x9A, 0x00, 0x07, 0xC4]

print(f'\nFirst 10 notes from SID file at 0x{notes_memory_addr:04X}:')
for i in range(10):
    note_sid = notes_sid[i]
    note_ref = ref_notes[i]
    match = 'MATCH' if note_sid == note_ref else 'DIFF '
    print(f'  {i:03d} | SID: 0x{note_sid:02X}, Ref: 0x{note_ref:02X}  [{match}]')

# Count total matches
matches = sum(1 for i in range(10) if notes_sid[i] == ref_notes[i])
print(f'\nResult: {matches}/10 matches ({100*matches/10:.0f}%)')

if matches == 10:
    print(f'\n✅ PERFECT MATCH - Wave table address verified!')
    print(f'\nWave Table Summary:')
    print(f'  Format: Row-Major (256 waveforms, then 256 notes)')
    print(f'  Waveforms: 0x{waveform_memory_addr:04X} - 0x{waveform_memory_addr + 255:04X} (256 bytes)')
    print(f'  Notes: 0x{notes_memory_addr:04X} - 0x{notes_memory_addr + 255:04X} (256 bytes)')
    print(f'  Total size: 512 bytes')
    print(f'  Original expected address: 0x190C')
    print(f'  Actual waveform address: 0x{waveform_memory_addr:04X}')
    print(f'  Offset: {0x190C - waveform_memory_addr:+d} bytes')
else:
    print(f'\n⚠️  Addresses need further investigation')
