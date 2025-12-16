#!/usr/bin/env python3
"""
Test script to verify Laxity parser integration in SF2 Viewer
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add SIDM2 to path
sys.path.insert(0, str(Path(__file__).parent))

from sf2_viewer_core import SF2Parser

def test_laxity_viewer():
    """Test Laxity parser integration with SF2 Viewer"""

    # Test file
    test_file = Path(__file__).parent / "learnings" / "Laxity - Stinsen - Last Night Of 89.sf2"

    if not test_file.exists():
        logger.error(f"Test file not found: {test_file}")
        return False

    logger.info(f"Testing with: {test_file}")
    logger.info("=" * 80)

    # Parse the file
    try:
        parser = SF2Parser(str(test_file))

        # Check if Laxity driver was detected
        logger.info(f"Is Laxity Driver: {parser.is_laxity_driver}")
        logger.info(f"Load Address: 0x{parser.load_address:04X}")
        logger.info(f"Magic ID: 0x{parser.magic_id:04X}")
        logger.info(f"Number of Sequences: {len(parser.sequences)}")

        if parser.is_laxity_driver:
            logger.info("✓ Laxity driver detected correctly!")
        else:
            logger.warning("✗ Laxity driver NOT detected - check load address")

        # Display sequence information
        logger.info("=" * 80)
        logger.info("SEQUENCE DATA:")
        logger.info("=" * 80)

        for seq_idx in sorted(parser.sequences.keys())[:3]:  # Show first 3 sequences
            seq_data = parser.sequences[seq_idx]
            logger.info(f"\nSequence {seq_idx}:")
            logger.info(f"  Total entries: {len(seq_data)}")

            if len(seq_data) > 0:
                logger.info(f"  First 10 entries:")
                for i, entry in enumerate(seq_data[:10]):
                    note_name = entry.note_name() if hasattr(entry, 'note_name') else f"0x{entry.note:02X}"
                    instr = entry.instrument_display() if hasattr(entry, 'instrument_display') else f"0x{entry.instrument:02X}"
                    cmd = entry.command_display() if hasattr(entry, 'command_display') else f"0x{entry.command:02X}"
                    logger.info(f"    {i}: Note={note_name:>8s} Instr={instr:>2s} Cmd={cmd:>2s}")

                # Check for invalid data
                invalid_entries = [
                    entry for entry in seq_data
                    if entry.note > 0x7F and entry.note not in (0x7E, 0x7F, 0x80)
                ]
                if invalid_entries:
                    logger.warning(f"  ⚠️ Found {len(invalid_entries)} entries with invalid note values!")
                else:
                    logger.info(f"  ✓ All entries have valid note values")

        logger.info("=" * 80)
        logger.info("Test completed successfully!")
        return True

    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_laxity_viewer()
    sys.exit(0 if success else 1)
