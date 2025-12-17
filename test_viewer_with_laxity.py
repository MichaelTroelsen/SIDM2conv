#!/usr/bin/env python3
"""Test SF2 Viewer with Laxity file - no unicode characters"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from sf2_viewer_core import SF2Parser

def main():
    # Load Laxity test file
    laxity_file = Path(__file__).parent / "learnings" / "Laxity - Stinsen - Last Night Of 89.sf2"

    if not laxity_file.exists():
        print(f"ERROR: Test file not found: {laxity_file}")
        return False

    print("=" * 80)
    print("SF2 VIEWER - LAXITY FILE TEST")
    print("=" * 80)
    print(f"File: {laxity_file.name}")
    print()

    try:
        # Parse the file
        parser = SF2Parser(str(laxity_file))

        print(f"Laxity driver detected: {parser.is_laxity_driver}")
        print(f"Load address: 0x{parser.load_address:04X}")
        print()

        # Display sequence information
        print(f"Sequences found: {len(parser.sequences)}")
        print()

        if parser.sequences:
            for seq_idx, entries in parser.sequences.items():
                print(f"Sequence {seq_idx}: {len(entries)} entries")
                print("-" * 80)

                # Show first 15 entries
                for i, entry in enumerate(entries[:15]):
                    note_name = entry.note_name()
                    inst_val = f"0x{entry.instrument:02X}"
                    print(f"  [{i:3d}] Note: {note_name:5s}  Inst: {inst_val:10s}  "
                          f"Cmd: 0x{entry.command:02X}  Dur: {entry.duration}")

                if len(entries) > 15:
                    print(f"  ... ({len(entries) - 15} more entries)")
                print()

        # Verify data correctness
        print("=" * 80)
        print("VERIFICATION RESULTS:")
        print("=" * 80)

        has_valid_data = False
        has_invalid_data = False
        e1_count = 0

        for seq_idx, entries in parser.sequences.items():
            for entry in entries:
                # Check for invalid 0xE1 bytes
                if entry.note == 0xE1:
                    has_invalid_data = True
                    e1_count += 1

                # Check for valid note values
                if 0x01 <= entry.note <= 0x6F:
                    has_valid_data = True

        if has_valid_data and not has_invalid_data:
            print("[OK] Data is CORRECT")
            print("  - No 0xE1 padding bytes found in sequence notes")
            print("  - Valid note values present")
            print("  - Parser reading from correct offset")
            return True
        elif has_invalid_data:
            print("[ERROR] Data is INCORRECT")
            print(f"  - Found {e1_count} invalid 0xE1 bytes (padding still in data)")
            return False
        else:
            print("[WARNING] No valid note data found")
            return False

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    print()
    print("=" * 80)
    if success:
        print("TEST PASSED - Laxity parser is working correctly!")
    else:
        print("TEST FAILED - Issues detected")
    print("=" * 80)
    sys.exit(0 if success else 1)
