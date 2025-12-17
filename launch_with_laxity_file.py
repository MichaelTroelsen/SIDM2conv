#!/usr/bin/env python3
"""
Launch SF2 Viewer and automatically load the Laxity test file with Sequences tab active
"""

import sys
from pathlib import Path
from PyQt6.QtCore import QTimer

sys.path.insert(0, str(Path(__file__).parent))

from sf2_viewer_gui import SF2ViewerWindow

def main():
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Create and show window
    window = SF2ViewerWindow()
    window.show()

    print("SF2 Viewer launched")
    print("=" * 80)

    # Path to Laxity test file
    laxity_file = Path(__file__).parent / "learnings" / "Laxity - Stinsen - Last Night Of 89.sf2"

    # Schedule file load after GUI is ready
    def load_file():
        try:
            print(f"Loading: {laxity_file}")
            window.load_file(str(laxity_file))
            print("✓ File loaded successfully")

            # Switch to Sequences tab (index 5)
            window.tabs.setCurrentIndex(5)
            print("✓ Switched to Sequences tab")

            # Select first sequence
            if window.sequence_combo.count() > 0:
                window.sequence_combo.setCurrentIndex(0)
                print("✓ Selected first sequence")

                # Get info
                info = window.sequence_info.text()
                print(f"\nSequence Info: {info}")
                print("\nSequences are now displayed in 3-track PARALLEL format")
                print("=" * 80)
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

    # Load file after 1 second (gives GUI time to render)
    QTimer.singleShot(1000, load_file)

    # Run application
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
