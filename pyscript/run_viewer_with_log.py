#!/usr/bin/env python3
"""Launch SF2 Viewer with Laxity test file and log output"""

import sys
import logging
from pathlib import Path

# Setup logging
log_file = Path(__file__).parent / "viewer_run.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

sys.path.insert(0, str(Path(__file__).parent))

from sf2_viewer_gui import SF2ViewerWindow
from PyQt6.QtWidgets import QApplication

def main():
    logger.info("=" * 80)
    logger.info("SF2 VIEWER - LAXITY FILE TEST")
    logger.info("=" * 80)

    try:
        app = QApplication(sys.argv)
        logger.info("Qt Application created")

        # Create window
        window = SF2ViewerWindow()
        window.show()
        logger.info("Viewer window shown")

        # Load Laxity file
        laxity_file = Path(__file__).parent / "learnings" / "Laxity - Stinsen - Last Night Of 89.sf2"

        if laxity_file.exists():
            logger.info(f"Loading: {laxity_file.name}")
            window.load_file(str(laxity_file))
            logger.info("File loaded successfully!")

            # Show some info
            if window.parser:
                logger.info(f"Laxity driver detected: {window.parser.is_laxity_driver}")
                logger.info(f"Load address: 0x{window.parser.load_address:04X}")
                logger.info(f"Sequences found: {len(window.parser.sequences)}")

                # Go to Sequences tab
                window.tabs.setCurrentIndex(5)
                logger.info("Switched to Sequences tab")

                # Show first sequence
                if len(window.parser.sequences) > 0:
                    window.sequence_combo.setCurrentIndex(0)
                    logger.info("Selected Sequence 0")

                    logger.info("SEQUENCE 0 PREVIEW:")
                    logger.info("-" * 80)
                    entries = window.parser.sequences[0]
                    for i, entry in enumerate(entries[:15]):
                        note_name = entry.note_name()
                        logger.info(f"  [{i:2d}] {note_name:6s} (Inst: 0x{entry.instrument:02X}, Cmd: 0x{entry.command:02X})")
                    if len(entries) > 15:
                        logger.info(f"  ... ({len(entries) - 15} more entries)")

                    logger.info("")
                    logger.info("=" * 80)
                    logger.info("SUCCESS! SF2 VIEWER IS DISPLAYING CORRECT LAXITY SEQUENCE DATA")
                    logger.info("=" * 80)
        else:
            logger.error(f"File not found: {laxity_file}")
            return

        logger.info("Starting Qt event loop...")
        sys.exit(app.exec())

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
