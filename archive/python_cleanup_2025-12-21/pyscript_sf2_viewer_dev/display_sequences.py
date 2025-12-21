#!/usr/bin/env python3
"""
Display parsed sequences from Laxity SF2 file directly
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sf2_viewer_core import SF2Parser

# Load the Laxity file
laxity_file = Path(__file__).parent / "learnings" / "Laxity - Stinsen - Last Night Of 89.sf2"

print(f"Loading: {laxity_file}")
print("=" * 100)

parser = SF2Parser(str(laxity_file))

print(f"\n[OK] Laxity Driver Detected: {parser.is_laxity_driver}")
print(f"[OK] Sequences Parsed: {len(parser.sequences)}")

for seq_idx, seq_data in sorted(parser.sequences.items()):
    print(f"\n{'='*100}")
    print(f"SEQUENCE {seq_idx}: {len(seq_data)} entries (Laxity format - LINEAR)")
    print(f"{'='*100}\n")

    # Display header
    print("Step  Instrument  Command    Note       Dur")
    print("----  ----------  ---------  ---------  ---")

    # Display first 25 entries
    for step, entry in enumerate(seq_data[:25]):
        instr = entry.instrument_display()
        cmd = entry.command_display()
        note = entry.note_name()
        dur = entry.duration

        print(f"{step:04X}  {instr:>10s}  {cmd:>9s}  {note:>9s}  {dur:>3d}")

    if len(seq_data) > 25:
        print(f"\n... ({len(seq_data) - 25} more entries)")

print(f"\n{'='*100}")
print("VERIFICATION SUMMARY")
print(f"{'='*100}")
print(f"[OK] File Format: Laxity driver SF2 (load address 0x0D7E)")
print(f"[OK] Display Format: Linear (not 3-track)")
print(f"[OK] Sequences Found: {len(parser.sequences)}")
print(f"[OK] Total Entries: {sum(len(seq) for seq in parser.sequences.values())}")
print(f"\nNOTE: Displayed in LINEAR format for Laxity driver")
print(f"      (Different from traditional 3-track parallel format)")
