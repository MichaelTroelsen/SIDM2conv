#!/usr/bin/env python3
"""
Detailed MIDI Difference Analyzer

Compares two MIDI files note-by-note to find exact differences.
"""

import sys
try:
    from mido import MidiFile
except ImportError:
    print("ERROR: mido not installed. Run: pip install mido")
    sys.exit(1)


def analyze_track(track, track_name):
    """Analyze a single MIDI track in detail"""
    notes = []
    current_time = 0

    for msg in track:
        current_time += msg.time

        if msg.type == 'note_on' and msg.velocity > 0:
            notes.append({
                'time': current_time,
                'note': msg.note,
                'velocity': msg.velocity,
                'type': 'on'
            })
        elif msg.type in ('note_off', 'note_on') and (msg.type == 'note_off' or msg.velocity == 0):
            notes.append({
                'time': current_time,
                'note': msg.note,
                'velocity': 0,
                'type': 'off'
            })

    return notes


def compare_files(file1, file2):
    """Compare two MIDI files in detail"""
    print(f"\nComparing:")
    print(f"  File 1: {file1}")
    print(f"  File 2: {file2}\n")

    mid1 = MidiFile(file1)
    mid2 = MidiFile(file2)

    print(f"Basic Info:")
    print(f"  File 1: {len(mid1.tracks)} tracks, {mid1.ticks_per_beat} ticks/beat")
    print(f"  File 2: {len(mid2.tracks)} tracks, {mid2.ticks_per_beat} ticks/beat\n")

    # Compare each track
    for track_idx in range(min(len(mid1.tracks), len(mid2.tracks))):
        print(f"="*60)
        print(f"Track {track_idx + 1}")
        print(f"="*60)

        track1_name = f"File1-Track{track_idx}"
        track2_name = f"File2-Track{track_idx}"

        notes1 = analyze_track(mid1.tracks[track_idx], track1_name)
        notes2 = analyze_track(mid2.tracks[track_idx], track2_name)

        print(f"\nNote counts:")
        print(f"  File 1: {len([n for n in notes1 if n['type'] == 'on'])} note_on events")
        print(f"  File 2: {len([n for n in notes2 if n['type'] == 'on'])} note_on events")

        # Show first 20 events from each
        print(f"\nFirst 20 note events:")
        print(f"{'Time':<10} {'File1 Note':<12} {'File2 Note':<12} {'Match':<10}")
        print(f"-"*60)

        for i in range(min(20, max(len(notes1), len(notes2)))):
            n1_str = f"{notes1[i]['note']:3d} ({notes1[i]['type']:3s})" if i < len(notes1) else "---"
            n2_str = f"{notes2[i]['note']:3d} ({notes2[i]['type']:3s})" if i < len(notes2) else "---"
            t1 = notes1[i]['time'] if i < len(notes1) else 0
            t2 = notes2[i]['time'] if i < len(notes2) else 0
            time_str = f"{t1}/{t2}"

            match = "OK" if (i < len(notes1) and i < len(notes2) and
                           notes1[i]['note'] == notes2[i]['note'] and
                           notes1[i]['type'] == notes2[i]['type']) else "DIFF"

            print(f"{time_str:<10} {n1_str:<12} {n2_str:<12} {match:<10}")

        # Find where they diverge
        print(f"\nFinding first divergence point...")
        for i in range(min(len(notes1), len(notes2))):
            if notes1[i]['note'] != notes2[i]['note'] or notes1[i]['type'] != notes2[i]['type']:
                print(f"  First difference at event {i}:")
                print(f"    File 1: Note {notes1[i]['note']} ({notes1[i]['type']}) at time {notes1[i]['time']}")
                print(f"    File 2: Note {notes2[i]['note']} ({notes2[i]['type']}) at time {notes2[i]['time']}")

                # Show context
                print(f"\n  Context (5 events before and after):")
                for j in range(max(0, i-5), min(len(notes1), i+6)):
                    marker = " >>> " if j == i else "     "
                    n1 = notes1[j] if j < len(notes1) else None
                    n2 = notes2[j] if j < len(notes2) else None

                    n1_str = f"Note {n1['note']:3d} ({n1['type']:3s}) @ {n1['time']}" if n1 else "---"
                    n2_str = f"Note {n2['note']:3d} ({n2['type']:3s}) @ {n2['time']}" if n2 else "---"

                    print(f"{marker}[{j}] File1: {n1_str:<30} File2: {n2_str}")
                break
        else:
            if len(notes1) != len(notes2):
                print(f"  Files match up to event {min(len(notes1), len(notes2))}")
                print(f"  File 1 has {len(notes1) - min(len(notes1), len(notes2))} extra events")
                print(f"  File 2 has {len(notes2) - min(len(notes1), len(notes2))} extra events")
            else:
                print(f"  All {len(notes1)} events match!")

        print()


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python analyze_midi_diff.py file1.mid file2.mid")
        sys.exit(1)

    compare_files(sys.argv[1], sys.argv[2])
