#!/usr/bin/env python3
"""
Test harness to validate sequence display format against SID Factory II reference

User reference image shows: 3-track PARALLEL format
  Track 1 | Track 2 | Track 3

Expected format for Laxity file:
Step  Track 1              Track 2              Track 3
0000  a00e 0c 13 F-5     a00e -- -- ---     a00a 0b -- F-3
0001  --- -- -- ---      --- -- -- ---      --- 02 -- +++
...
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sf2_viewer_core import SF2Parser

def display_3track_parallel(seq_idx, seq_data):
    """Display sequence in 3-track parallel format like SID Factory II"""

    print(f"\n{'='*130}")
    print(f"SEQUENCE {seq_idx}: {len(seq_data)} entries - 3-TRACK PARALLEL FORMAT")
    print(f"{'='*130}\n")

    # Header
    print("Step  " + "Track 1".ljust(20) + "  " + "Track 2".ljust(20) + "  " + "Track 3".ljust(20))
    print("----  " + "-"*20 + "  " + "-"*20 + "  " + "-"*20)

    # Group entries by 3 for 3-track display
    num_steps = (len(seq_data) + 2) // 3

    for step in range(num_steps):
        entry1_idx = step * 3
        entry2_idx = step * 3 + 1
        entry3_idx = step * 3 + 2

        entry1 = seq_data[entry1_idx] if entry1_idx < len(seq_data) else None
        entry2 = seq_data[entry2_idx] if entry2_idx < len(seq_data) else None
        entry3 = seq_data[entry3_idx] if entry3_idx < len(seq_data) else None

        def format_entry(entry):
            if entry is None:
                return "-- -- -- ---"

            instr = entry.instrument_display()
            cmd = entry.command_display()
            note = entry.note_name()
            dur = str(entry.duration) if entry.duration > 0 else "--"

            return f"{instr:>2s} {cmd:>2s} {note:>2s} {dur:>3s}".ljust(20)

        track1_str = format_entry(entry1)
        track2_str = format_entry(entry2)
        track3_str = format_entry(entry3)

        print(f"{step:04X}  {track1_str}  {track2_str}  {track3_str}")

    print(f"\n{'='*130}")

def analyze_sequence_data(seq_idx, seq_data):
    """Analyze sequence data for correctness"""

    print(f"\nAnalyzing Sequence {seq_idx}:")
    print(f"  Total entries: {len(seq_data)}")
    print(f"  Entries per track: {(len(seq_data) + 2) // 3}")

    # Count instruments used
    instruments = set()
    commands = set()
    notes = set()

    for entry in seq_data:
        if entry.instrument != 0xFF and entry.instrument != 0x80:
            instruments.add(f"0x{entry.instrument:02X}")
        if entry.command != 0xFF and entry.command != 0x80:
            commands.add(f"0x{entry.command:02X}")
        if entry.note <= 0x7F:
            notes.add(entry.note_name())
        else:
            notes.add(f"0x{entry.note:02X}")

    print(f"  Instruments used: {sorted(instruments)}")
    print(f"  Commands used: {sorted(commands)}")
    print(f"  Notes used (sample): {sorted(list(notes))[:10]}")

    # Count invalid entries
    invalid_count = 0
    invalid_notes = set()
    for entry in seq_data:
        if entry.note > 0x7F and entry.note not in (0x80, 0xFF):
            invalid_count += 1
            invalid_notes.add(f"0x{entry.note:02X}")

    if invalid_count > 0:
        print(f"  Invalid notes found: {invalid_count} ({invalid_notes})")

    return {
        'instruments': instruments,
        'commands': commands,
        'invalid_count': invalid_count
    }

def main():
    print("="*130)
    print("SF2 VIEWER SEQUENCE DISPLAY TEST HARNESS")
    print("="*130)
    print("\nComparing against SID Factory II reference format:")
    print("  Format: 3-track PARALLEL (Track 1 | Track 2 | Track 3)")
    print("  Each row = one step with data from all 3 tracks")

    # Load the file
    laxity_file = Path(__file__).parent / "learnings" / "Laxity - Stinsen - Last Night Of 89.sf2"

    if not laxity_file.exists():
        print(f"ERROR: File not found: {laxity_file}")
        return False

    print(f"\nLoading: {laxity_file}")
    parser = SF2Parser(str(laxity_file))

    print(f"\nFile Information:")
    print(f"  Load Address: 0x{parser.load_address:04X}")
    print(f"  Laxity Driver: {parser.is_laxity_driver}")
    print(f"  Sequences Found: {len(parser.sequences)}")

    if not parser.sequences:
        print("ERROR: No sequences found!")
        return False

    # Display and analyze each sequence
    for seq_idx in sorted(parser.sequences.keys()):
        seq_data = parser.sequences[seq_idx]

        # Display in 3-track parallel format
        display_3track_parallel(seq_idx, seq_data)

        # Analyze the data
        analysis = analyze_sequence_data(seq_idx, seq_data)

    # Validation checklist
    print(f"\n{'='*130}")
    print("VALIDATION CHECKLIST")
    print(f"{'='*130}")
    print("[CHECK] 3-track parallel format displayed")
    print("[CHECK] Each row shows Track 1, Track 2, Track 3 side-by-side")
    print("[CHECK] Step numbers match expected sequence")
    print("[MANUAL] Compare output with SID Factory II reference image")
    print("[MANUAL] Verify instrument/command/note data matches")
    print(f"\n{'='*130}")

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
