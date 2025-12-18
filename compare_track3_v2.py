#!/usr/bin/env python3
"""
Compare track_3.txt reference with SF2 file Track 3 data
3-column format: Instrument (2 chars), Command (2 chars), Note (3-4 chars)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sf2_viewer_core import SF2Parser


def load_reference(ref_file):
    """Load reference file - Format: [XXYY] AA BB CCC
    XXYY = OrderList entry (optional, 4 hex chars like a00a)
    AA = Instrument (2 chars)
    BB = Command (2 chars)
    CCC = Note (3-4 chars)
    """
    reference = []

    with open(ref_file, 'r') as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        line = line.strip()

        # Skip header and empty lines
        if not line or line.startswith("Track"):
            continue

        # Parse line - format: "[a00a] 0b -- F-3" or "-- -- +++" or "-- 02 +++"
        parts = line.split()

        if len(parts) == 0:
            continue
        elif len(parts) == 3:
            # Format: "AA BB CCC" (Inst Cmd Note)
            instr, cmd, note = parts
        elif len(parts) == 4:
            # Format: "XXYY AA BB CCC" (OrderList Inst Cmd Note)
            # Skip the orderlist entry (XXYY), take the sequence data (AA BB CCC)
            _, instr, cmd, note = parts
        else:
            # Fallback: take last 3 parts
            instr = parts[-3] if len(parts) >= 3 else "--"
            cmd = parts[-2] if len(parts) >= 2 else "--"
            note = parts[-1] if len(parts) >= 1 else "---"

        reference.append({
            'line': i + 1,
            'instr': instr,
            'cmd': cmd,
            'note': note
        })

    return reference


def extract_track3(sf2_file, seq_idx=0):
    """Extract Track 3 from specified sequence"""
    parser = SF2Parser(sf2_file)

    if not parser.sequences:
        return []

    if seq_idx not in parser.sequences:
        print(f"[WARNING] Sequence {seq_idx} not found, using first available")
        seq_idx = sorted(parser.sequences.keys())[0]

    seq_data = parser.sequences[seq_idx]

    # Extract Track 3 (every 3rd entry starting from index 2)
    track3 = []
    for i in range(2, len(seq_data), 3):
        entry = seq_data[i]

        instr_str = entry.instrument_display()  # 2 chars: "--" or "0A"
        cmd_str = entry.command_display()       # 2 chars: "--" or "02"
        note_str = entry.note_name()            # 3+ chars: "F-3", "+++", etc

        track3.append({
            'idx': len(track3),
            'instr': instr_str,
            'cmd': cmd_str,
            'note': note_str,
            'raw': f"note={entry.note:02X} inst={entry.instrument:02X} cmd={entry.command:02X}"
        })

    return track3


def create_comparison(ref_file, sf2_file, output_file, seq_idx=0):
    """Create side-by-side comparison file"""

    print("=" * 100)
    print("CREATING TRACK 3 COMPARISON")
    print("=" * 100)
    print()

    # Load reference
    print(f"[*] Loading reference: {ref_file}")
    reference = load_reference(ref_file)
    print(f"[OK] Loaded {len(reference)} reference entries")

    # Extract SF2 Track 3
    print(f"[*] Loading SF2: {sf2_file}")
    track3 = extract_track3(sf2_file, seq_idx)
    print(f"[OK] Extracted {len(track3)} Track 3 entries from Sequence {seq_idx}")
    print()

    # Create comparison
    print(f"[*] Creating comparison: {output_file}")

    matched = 0
    mismatched = 0

    with open(output_file, 'w') as f:
        # Header
        f.write("=" * 120 + "\n")
        f.write("TRACK 3 SIDE-BY-SIDE COMPARISON\n")
        f.write("=" * 120 + "\n\n")
        f.write(f"Reference File: {ref_file}\n")
        f.write(f"SF2 File: {sf2_file}\n")
        f.write(f"Sequence: {seq_idx}\n")
        f.write(f"Track: 3\n")
        f.write(f"Format: Instrument (2 chars), Command (2 chars), Note (3-4 chars)\n\n")
        f.write("=" * 120 + "\n\n")

        # Column headers
        f.write(f"{'Entry':<6} {'Reference':<20} {'SF2 Actual':<20} {'Match':<10} {'Notes':<40}\n")
        f.write("-" * 120 + "\n")

        # Compare entries
        max_entries = max(len(reference), len(track3))

        for i in range(max_entries):
            ref_entry = reference[i] if i < len(reference) else None
            sf2_entry = track3[i] if i < len(track3) else None

            if ref_entry and sf2_entry:
                # Format both for comparison
                ref_str = f"{ref_entry['instr']:2s} {ref_entry['cmd']:2s} {ref_entry['note']:4s}"
                sf2_str = f"{sf2_entry['instr']:2s} {sf2_entry['cmd']:2s} {sf2_entry['note']:4s}"

                # Normalize for comparison (lowercase, strip)
                ref_norm = f"{ref_entry['instr'].lower():2s} {ref_entry['cmd'].lower():2s} {ref_entry['note'].lower():4s}".strip()
                sf2_norm = f"{sf2_entry['instr'].lower():2s} {sf2_entry['cmd'].lower():2s} {sf2_entry['note'].lower():4s}".strip()

                if ref_norm == sf2_norm:
                    match_status = "[MATCH]"
                    matched += 1
                    notes_str = ""
                else:
                    match_status = "[DIFF]"
                    mismatched += 1

                    # Notes about differences
                    notes = []
                    if ref_entry['instr'].lower() != sf2_entry['instr'].lower():
                        notes.append(f"Instr: {ref_entry['instr']} vs {sf2_entry['instr']}")
                    if ref_entry['cmd'].lower() != sf2_entry['cmd'].lower():
                        notes.append(f"Cmd: {ref_entry['cmd']} vs {sf2_entry['cmd']}")
                    if ref_entry['note'].lower() != sf2_entry['note'].lower():
                        notes.append(f"Note: {ref_entry['note']} vs {sf2_entry['note']}")

                    notes_str = ", ".join(notes)

                f.write(f"{i:<6} {ref_str:<20} {sf2_str:<20} {match_status:<10} {notes_str:<40}\n")

            elif ref_entry:
                ref_str = f"{ref_entry['instr']:2s} {ref_entry['cmd']:2s} {ref_entry['note']:4s}"
                f.write(f"{i:<6} {ref_str:<20} {'(no data)':<20} [MISSING]  {'SF2 has no entry':<40}\n")
                mismatched += 1

            elif sf2_entry:
                sf2_str = f"{sf2_entry['instr']:2s} {sf2_entry['cmd']:2s} {sf2_entry['note']:4s}"
                f.write(f"{i:<6} {'(no data)':<20} {sf2_str:<20} [EXTRA]    {'Reference has no entry':<40}\n")
                mismatched += 1

        # Summary
        f.write("\n" + "=" * 120 + "\n")
        f.write("COMPARISON SUMMARY\n")
        f.write("=" * 120 + "\n\n")
        f.write(f"Total Reference Entries: {len(reference)}\n")
        f.write(f"Total SF2 Entries: {len(track3)}\n")
        f.write(f"Matched Entries: {matched}\n")
        f.write(f"Mismatched Entries: {mismatched}\n\n")

        total = len(reference)
        if total > 0:
            accuracy = (matched / total) * 100
            f.write(f"Accuracy: {accuracy:.1f}% ({matched}/{total})\n\n")

            if matched == total:
                f.write("RESULT: 100% MATCH - All entries verified!\n")
            elif accuracy >= 50:
                f.write(f"RESULT: PARTIAL MATCH ({accuracy:.1f}%) - Some similarities found\n")
            else:
                f.write(f"RESULT: LOW MATCH ({accuracy:.1f}%) - Significant differences\n")

        f.write("\n" + "=" * 120 + "\n")

    print(f"[OK] Comparison file created")
    print()
    print(f"[*] Results:")
    print(f"    Matched: {matched}/{total}")
    if total > 0:
        print(f"    Accuracy: {accuracy:.1f}%")
    print()

    return matched, total


def main():
    ref_file = r"C:\Users\mit\claude\c64server\SIDM2\track_3.txt"
    sf2_file = r"C:\Users\mit\claude\c64server\SIDM2\learnings\Laxity - Stinsen - Last Night Of 89.sf2"
    output_file = r"C:\Users\mit\claude\c64server\SIDM2\TRACK3_COMPARISON.txt"

    seq_idx = 0  # Default to Sequence 0

    if len(sys.argv) > 1:
        sf2_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    if len(sys.argv) > 3:
        seq_idx = int(sys.argv[3])

    if not Path(ref_file).exists():
        print(f"[ERROR] Reference file not found: {ref_file}")
        sys.exit(1)

    if not Path(sf2_file).exists():
        print(f"[ERROR] SF2 file not found: {sf2_file}")
        sys.exit(1)

    matched, total = create_comparison(ref_file, sf2_file, output_file, seq_idx)

    print("=" * 100)
    if total > 0:
        accuracy = (matched / total) * 100
        if accuracy == 100:
            print("SUCCESS: 100% MATCH!")
        else:
            print(f"COMPLETE: {accuracy:.1f}% match - See comparison file for details")
    else:
        print("COMPLETE: See comparison file for details")
    print("=" * 100)
    print()
    print(f"Output file: {output_file}")

    sys.exit(0)


if __name__ == "__main__":
    main()
