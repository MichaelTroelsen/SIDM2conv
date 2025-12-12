#!/usr/bin/env python3
"""
Simple approach: Compare note patterns from siddump with data in SID file.

Strategy:
1. Run siddump to get the actual note sequence played
2. Convert those notes to frequency values
3. Search for those frequency values (or patterns leading to them) in the SID file
4. This will help identify where sequence data is stored
"""

import subprocess
import re

def get_siddump_notes(sid_file, frames=50):
    """Get note sequence from siddump output."""
    print(f"Running siddump on {sid_file}...")

    cmd = ['tools\\siddump.exe', sid_file, f'-t{frames//50 + 1}']
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error running siddump: {result.stderr}")
        return []

    # Parse siddump output to extract notes
    notes = []
    lines = result.stdout.split('\n')

    for line in lines:
        # Look for lines with note information
        # Format: | frame | freq note WF ADSR ...
        if line.startswith('|') and not line.startswith('| Frame'):
            parts = line.split('|')
            if len(parts) >= 4:
                try:
                    frame = int(parts[1].strip())
                    if frame >= frames:
                        break

                    # Parse each voice (columns 2, 3, 4)
                    for voice in range(3):
                        voice_data = parts[2 + voice].strip()
                        if voice_data and not voice_data.startswith('...'):
                            # Extract frequency (first 4 hex digits)
                            freq_match = re.match(r'([0-9A-F]{4})', voice_data)
                            if freq_match:
                                freq = int(freq_match.group(1), 16)
                                if freq > 0:
                                    notes.append({
                                        'frame': frame,
                                        'voice': voice,
                                        'freq': freq
                                    })
                except:
                    continue

    return notes

def search_freq_in_file(sid_file, target_freq):
    """Search for frequency value in SID file."""
    with open(sid_file, 'rb') as f:
        data = f.read()

    freq_lo = target_freq & 0xFF
    freq_hi = (target_freq >> 8) & 0xFF

    matches = []

    # Search for the 2-byte frequency value
    for offset in range(len(data) - 1):
        if data[offset] == freq_lo and data[offset + 1] == freq_hi:
            mem_addr = 0x1000 + (offset - 0x7E)
            matches.append((offset, mem_addr))

    return matches

def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'

    print("=" * 70)
    print("SIMPLE SEQUENCE FINDER")
    print("=" * 70 + "\n")

    # Get notes from siddump
    notes = get_siddump_notes(sid_file, frames=20)

    if not notes:
        print("No notes found in siddump output!")
        return

    print(f"Found {len(notes)} note events in first 20 frames\n")

    # Show first 10 notes
    print("First 10 note events:")
    for i, note in enumerate(notes[:10]):
        print(f"  Frame {note['frame']:3d}, Voice {note['voice']}, Freq ${note['freq']:04X}")

    print("\n" + "=" * 70)
    print("SEARCHING FOR FREQUENCY VALUES IN SID FILE")
    print("=" * 70 + "\n")

    # Search for a few unique frequencies
    unique_freqs = list(set(n['freq'] for n in notes[:20]))[:5]

    for freq in unique_freqs:
        print(f"\nSearching for frequency ${freq:04X}:")
        matches = search_freq_in_file(sid_file, freq)

        if matches:
            print(f"  Found {len(matches)} matches:")
            for offset, mem_addr in matches[:5]:
                print(f"    File offset 0x{offset:04X} (Memory ${mem_addr:04X})")
        else:
            print(f"  No matches found")

    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70 + "\n")

    print("Note: Frequency values are calculated from note data, not stored directly.")
    print("The player uses a frequency table to convert notes to SID frequencies.")
    print("\nTo find sequence data, we need to:")
    print("1. Find the frequency table (usually 96 notes × 2 bytes)")
    print("2. Find where note values are stored (sequence data)")
    print("3. Trace how the player reads from sequences to frequency table\n")

    # Look for frequency table
    print("Searching for frequency table patterns...")
    with open(sid_file, 'rb') as f:
        data = f.read()

    # A frequency table typically starts with low C (0x0117)
    freq_table_start = data.find(bytes([0x17, 0x01]))

    if freq_table_start >= 0:
        mem_addr = 0x1000 + (freq_table_start - 0x7E)
        print(f"Potential frequency table at:")
        print(f"  File offset: 0x{freq_table_start:04X}")
        print(f"  Memory addr: ${mem_addr:04X}\n")

        print("First 20 bytes of frequency table:")
        for i in range(10):
            offset = freq_table_start + i * 2
            lo = data[offset]
            hi = data[offset + 1]
            freq = lo | (hi << 8)
            print(f"  Note {i:2d}: ${freq:04X}")

if __name__ == '__main__':
    main()
