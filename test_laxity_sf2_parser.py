#!/usr/bin/env python3
"""Test script for Laxity SF2 parser implementation"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from sf2_viewer_core import SF2Parser

def test_laxity_sf2_parser():
    """Test the new Laxity SF2 parser"""

    # Load Laxity test file
    laxity_file = Path(__file__).parent / "learnings" / "Laxity - Stinsen - Last Night Of 89.sf2"

    if not laxity_file.exists():
        print(f"ERROR: Test file not found: {laxity_file}")
        return False

    print(f"Testing Laxity SF2 Parser")
    print("=" * 80)
    print(f"File: {laxity_file.name}")
    print()

    try:
        # Parse the file
        parser = SF2Parser(str(laxity_file))

        print(f"Laxity driver detected: {parser.is_laxity_driver}")
        print(f"Load address: 0x{parser.load_address:04X}")
        print()

        # Check sequence parsing
        print(f"Sequences found: {len(parser.sequences)}")
        print()

        if parser.sequences:
            for seq_idx, entries in parser.sequences.items():
                print(f"Sequence {seq_idx}: {len(entries)} entries")
                print("-" * 80)

                # Show first 20 entries
                for i, entry in enumerate(entries[:20]):
                    note_name = entry.note_name()
                    inst_val = f"0x{entry.instrument:02X}"
                    print(f"  [{i:3d}] Note: {note_name:5s}  Inst: {inst_val:10s}  "
                          f"Cmd: 0x{entry.command:02X}  Dur: {entry.duration}")

                if len(entries) > 20:
                    print(f"  ... ({len(entries) - 20} more entries)")
                print()

        # Verify data correctness
        print("Verification:")
        print("-" * 80)

        has_valid_data = False
        has_invalid_data = False

        for seq_idx, entries in parser.sequences.items():
            for entry in entries:
                # Check for invalid 0xE1 bytes appearing as notes
                if entry.note == 0xE1:
                    has_invalid_data = True
                    print(f"WARNING: Found 0xE1 byte in sequence {seq_idx} (should be skipped as padding)")

                # Check for valid note values
                if 0x01 <= entry.note <= 0x6F:
                    has_valid_data = True

        if has_valid_data and not has_invalid_data:
            print("[OK] Data is CORRECT - No 0xE1 padding bytes found in sequence notes")
            return True
        elif has_invalid_data:
            print("[ERROR] Data is INCORRECT - Found 0xE1 bytes in sequences (still reading from wrong offset)")
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
    success = test_laxity_sf2_parser()
    sys.exit(0 if success else 1)
