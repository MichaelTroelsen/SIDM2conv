#!/usr/bin/env python3
"""Compare musical content of two MIDI files (notes only, ignoring timing details)."""

import sys
from pathlib import Path
import mido

def extract_note_sequence(midi_path):
    """Extract sequence of note ON events (pitch only) from MIDI file."""
    notes = []

    try:
        mid = mido.MidiFile(midi_path)

        for track_idx, track in enumerate(mid.tracks):
            for msg in track:
                if msg.type == 'note_on' and msg.velocity > 0:
                    notes.append((track_idx, msg.note))
    except Exception as e:
        print(f"Error reading {midi_path}: {e}")
        return None

    return notes

def compare_sequences(seq1, seq2, name1="File 1", name2="File 2"):
    """Compare two note sequences and report differences."""

    if seq1 is None or seq2 is None:
        print("Cannot compare - one or both files failed to load")
        return False

    print(f"\n{name1}: {len(seq1)} notes")
    print(f"{name2}: {len(seq2)} notes")

    if len(seq1) == len(seq2):
        # Check if sequences are identical
        identical = True
        first_diff = None

        for i in range(len(seq1)):
            if seq1[i] != seq2[i]:
                identical = False
                if first_diff is None:
                    first_diff = i

        if identical:
            print("\n[PERFECT] Identical note sequences!")
            return True
        else:
            print(f"\n[DIFF] Same length but different notes (first difference at position {first_diff})")
            print(f"  Position {first_diff}: {seq1[first_diff]} vs {seq2[first_diff]}")
            return False
    else:
        print(f"\n[DIFF] Different lengths")

        # Find where they diverge
        min_len = min(len(seq1), len(seq2))
        first_diff = None

        for i in range(min_len):
            if seq1[i] != seq2[i]:
                first_diff = i
                break

        if first_diff is not None:
            print(f"  First difference at position {first_diff}")
            print(f"  {name1}[{first_diff}]: {seq1[first_diff]}")
            print(f"  {name2}[{first_diff}]: {seq2[first_diff]}")
        else:
            print(f"  Sequences match up to position {min_len-1}")
            print(f"  Then {name1 if len(seq1) > len(seq2) else name2} has extra notes")

        return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python compare_musical_content.py <midi1> <midi2>")
        sys.exit(1)

    file1 = Path(sys.argv[1])
    file2 = Path(sys.argv[2])

    if not file1.exists():
        print(f"Error: {file1} not found")
        sys.exit(1)

    if not file2.exists():
        print(f"Error: {file2} not found")
        sys.exit(1)

    print(f"Comparing musical content:")
    print(f"  {file1.name}")
    print(f"  {file2.name}")

    seq1 = extract_note_sequence(file1)
    seq2 = extract_note_sequence(file2)

    is_match = compare_sequences(seq1, seq2, file1.name, file2.name)

    sys.exit(0 if is_match else 1)

if __name__ == '__main__':
    main()
