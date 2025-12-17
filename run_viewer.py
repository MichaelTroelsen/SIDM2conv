#!/usr/bin/env python3
"""Launch SF2 Viewer with Laxity test file"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sf2_viewer_gui import SF2ViewerWindow
from PyQt6.QtWidgets import QApplication

def main():
    app = QApplication(sys.argv)

    # Create window
    window = SF2ViewerWindow()
    window.show()

    print("=" * 80)
    print("SF2 VIEWER - LAXITY FILE TEST")
    print("=" * 80)
    print()

    # Load Laxity file
    laxity_file = Path(__file__).parent / "learnings" / "Laxity - Stinsen - Last Night Of 89.sf2"

    if laxity_file.exists():
        print(f"Loading: {laxity_file.name}")
        window.load_file(str(laxity_file))
        print("File loaded successfully!")
        print()

        # Show some info
        if window.parser:
            print(f"Laxity driver detected: {window.parser.is_laxity_driver}")
            print(f"Load address: 0x{window.parser.load_address:04X}")
            print(f"Sequences found: {len(window.parser.sequences)}")
            print()

            # Go to Sequences tab
            window.tabs.setCurrentIndex(5)
            print("Switched to Sequences tab")

            # Show first sequence
            if len(window.parser.sequences) > 0:
                window.sequence_combo.setCurrentIndex(0)
                print("Selected Sequence 0")
                print()
                print("SEQUENCE 0 PREVIEW:")
                print("-" * 80)
                entries = window.parser.sequences[0]
                for i, entry in enumerate(entries[:15]):
                    note_name = entry.note_name()
                    print(f"  [{i:2d}] {note_name:6s} (Inst: 0x{entry.instrument:02X}, Cmd: 0x{entry.command:02X})")
                if len(entries) > 15:
                    print(f"  ... ({len(entries) - 15} more entries)")
    else:
        print(f"ERROR: File not found: {laxity_file}")
        return

    print()
    print("=" * 80)
    print("SF2 VIEWER IS NOW RUNNING!")
    print("Window is open and displaying Laxity sequence data")
    print("=" * 80)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
