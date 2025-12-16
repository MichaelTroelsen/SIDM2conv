#!/usr/bin/env python3
"""
Automated test of SF2 Viewer with Laxity file - loads and displays sequences
"""

import sys
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add SIDM2 to path
sys.path.insert(0, str(Path(__file__).parent))

from sf2_viewer_gui import SF2ViewerWindow

def test_laxity_file_display():
    """Test loading and displaying Laxity SF2 file"""

    app = QApplication(sys.argv)

    # Create viewer
    viewer = SF2ViewerWindow()
    viewer.setWindowTitle("SF2 Viewer - Laxity File Test")
    viewer.show()

    logger.info("SF2 Viewer GUI created and displayed")

    # Get Laxity file path
    laxity_file = Path(__file__).parent / "learnings" / "Laxity - Stinsen - Last Night Of 89.sf2"

    if not laxity_file.exists():
        logger.error(f"Test file not found: {laxity_file}")
        return False

    logger.info(f"Loading Laxity file: {laxity_file}")

    # Schedule file load after GUI is visible
    def load_file():
        try:
            viewer.load_file(str(laxity_file))
            logger.info("✅ File loaded successfully")

            # Navigate to Sequences tab
            viewer.tabs.setCurrentIndex(5)  # Sequences tab is index 5
            logger.info("✅ Switched to Sequences tab")

            # Select first sequence if available
            if viewer.sequence_combo.count() > 0:
                viewer.sequence_combo.setCurrentIndex(0)
                logger.info("✅ Selected first sequence")

                # Display information
                seq_info = viewer.sequence_info.text()
                logger.info(f"\n📊 Sequence Information:\n{seq_info}")

                # Get first few lines of display
                seq_text = viewer.sequence_text.toPlainText()
                lines = seq_text.split('\n')[:20]
                display_preview = '\n'.join(lines)
                logger.info(f"\n📋 Sequence Display Preview:\n{display_preview}")

                # Verify detection
                if hasattr(viewer.parser, 'is_laxity_driver'):
                    logger.info(f"\n✅ Laxity Driver Detected: {viewer.parser.is_laxity_driver}")

                if viewer.parser.sequences:
                    logger.info(f"✅ Sequences Parsed: {len(viewer.parser.sequences)}")
                    for seq_idx, seq_data in viewer.parser.sequences.items():
                        logger.info(f"   - Sequence {seq_idx}: {len(seq_data)} entries")

        except Exception as e:
            logger.error(f"❌ Error loading file: {e}")
            import traceback
            traceback.print_exc()

    # Use QTimer to load file after GUI is ready
    QTimer.singleShot(1000, load_file)

    # Keep window open for inspection
    logger.info("\n" + "="*80)
    logger.info("SF2 Viewer is now open with the Laxity file loaded")
    logger.info("Check the Sequences tab to view the sequences display")
    logger.info("The window will close after 30 seconds")
    logger.info("="*80 + "\n")

    # Auto-close after 30 seconds
    QTimer.singleShot(30000, app.quit)

    return app.exec()

if __name__ == "__main__":
    sys.exit(test_laxity_file_display())
