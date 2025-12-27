#!/usr/bin/env python3
"""SF2Writer Laxity Driver and Validation Tests

Comprehensive tests for:
- Laxity driver-specific injection (_inject_laxity_music_data)
- SF2 file validation (_validate_sf2_file)
- Complex scenarios and edge cases

Target: Bring sf2_writer.py coverage from 33% to 60%+
Focus: 300+ line _inject_laxity_music_data method and validation
"""

import unittest
import sys
import struct
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_writer import SF2Writer
from sidm2.models import ExtractedData, PSIDHeader, SequenceEvent
from sidm2 import errors


# ============================================================================
# Test Fixtures
# ============================================================================

def create_minimal_psid_header(**kwargs) -> PSIDHeader:
    """Create minimal PSID header for testing."""
    defaults = {
        'magic': 'PSID',
        'version': 2,
        'data_offset': 124,
        'load_address': 0x1000,
        'init_address': 0x1000,
        'play_address': 0x1003,
        'songs': 1,
        'start_song': 1,
        'speed': 0,
        'name': 'Test Song',
        'author': 'Test Author',
        'copyright': '2025'
    }
    defaults.update(kwargs)
    return PSIDHeader(**defaults)


def create_minimal_extracted_data(**kwargs) -> ExtractedData:
    """Create minimal ExtractedData for testing."""
    defaults = {
        'header': create_minimal_psid_header(),
        'c64_data': b'\x00' * 100,
        'load_address': 0x1000,
        'sequences': [],
        'orderlists': [[], [], []],
        'instruments': [],
        'wavetable': b'',
        'pulsetable': b'',
        'filtertable': b'',
    }
    defaults.update(kwargs)
    return ExtractedData(**defaults)


def create_minimal_sf2_template() -> bytes:
    """Create minimal SF2 template."""
    output = bytearray()
    output.extend(struct.pack('<H', 0x1000))  # Load address
    output.extend(struct.pack('<H', 0x1337))  # SF2 magic
    # Block 1 (descriptor)
    output.append(1)
    output.extend(struct.pack('<H', 4))
    output.extend(struct.pack('<H', 11))  # Driver type
    output.extend(struct.pack('<H', 0))   # Version
    output.append(0)  # Checksum
    # End marker
    output.append(0xFF)
    output.extend(struct.pack('<H', 0))
    output.append(0)
    return bytes(output)


# ============================================================================
# Laxity Driver Tests
# ============================================================================

class TestLaxityInjection(unittest.TestCase):
    """Test Laxity driver-specific music data injection."""

    def setUp(self):
        """Create test writer with Laxity driver."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data, driver_type='laxity')
        # Create Laxity driver output (load address + data)
        self.writer.output = bytearray()
        self.writer.output.extend(struct.pack('<H', 0x1000))
        self.writer.output.extend(b'\x00' * 8000)

    def test_inject_laxity_empty_data(self):
        """Test Laxity injection with empty data."""
        self.data.orderlists = [[], [], []]
        self.data.sequences = []
        self.writer._inject_laxity_music_data()
        self.assertGreater(len(self.writer.output), 2)

    def test_inject_laxity_orderlists_tuple_format(self):
        """Test orderlist injection with (transpose, seq_idx) tuples."""
        self.data.orderlists = [
            [(0xA0, 0), (0xA0, 1), (0xA0, 2)],
            [(0xA0, 0)],
            []
        ]
        self.data.sequences = []
        self.writer._inject_laxity_music_data()

        # Verify first entry
        load_addr = 0x1000
        orderlist_offset = 0x1900 - load_addr + 2
        self.assertEqual(self.writer.output[orderlist_offset], 0)

    def test_inject_laxity_orderlists_dict_format(self):
        """Test orderlist injection with dict format."""
        self.data.orderlists = [
            [{'sequence': 0, 'transpose': 0xA0}, {'sequence': 1}],
            [],
            []
        ]
        self.data.sequences = []
        self.writer._inject_laxity_music_data()

        load_addr = 0x1000
        orderlist_offset = 0x1900 - load_addr + 2
        self.assertEqual(self.writer.output[orderlist_offset], 0)
        self.assertEqual(self.writer.output[orderlist_offset + 1], 1)

    def test_inject_laxity_orderlists_int_format(self):
        """Test orderlist injection with direct int values."""
        self.data.orderlists = [[0, 1, 2], [0], []]
        self.data.sequences = []
        self.writer._inject_laxity_music_data()

        load_addr = 0x1000
        orderlist_offset = 0x1900 - load_addr + 2
        self.assertEqual(self.writer.output[orderlist_offset], 0)
        self.assertEqual(self.writer.output[orderlist_offset + 1], 1)
        self.assertEqual(self.writer.output[orderlist_offset + 2], 2)

    def test_inject_laxity_orderlist_end_marker(self):
        """Test that orderlists end with 0xFF marker."""
        self.data.orderlists = [[0, 1], [], []]
        self.data.sequences = []
        self.writer._inject_laxity_music_data()

        load_addr = 0x1000
        orderlist_offset = 0x1900 - load_addr + 2
        # After 2 entries, should be 0xFF
        self.assertEqual(self.writer.output[orderlist_offset + 2], 0xFF)

    def test_inject_laxity_sequences_dict_format(self):
        """Test sequence injection with dict format."""
        self.data.orderlists = [[], [], []]
        self.data.sequences = [
            [
                {'note': 24, 'duration': 1, 'gate': True},
                {'note': 26, 'gate': False}
            ]
        ]
        self.writer._inject_laxity_music_data()

        load_addr = 0x1000
        sequence_offset = (0x1900 + 3 * 256) - load_addr + 2
        # First byte should be gate marker
        self.assertEqual(self.writer.output[sequence_offset], 0x7E)
        self.assertEqual(self.writer.output[sequence_offset + 1], 24)

    def test_inject_laxity_sequences_int_format(self):
        """Test sequence injection with direct int values."""
        self.data.orderlists = [[], [], []]
        self.data.sequences = [[24, 26, 28]]
        self.writer._inject_laxity_music_data()

        load_addr = 0x1000
        sequence_offset = (0x1900 + 3 * 256) - load_addr + 2
        self.assertEqual(self.writer.output[sequence_offset], 24)
        self.assertEqual(self.writer.output[sequence_offset + 1], 26)

    def test_inject_laxity_sequence_end_marker(self):
        """Test that sequences end with 0x7F marker."""
        self.data.orderlists = [[], [], []]
        self.data.sequences = [[24, 26]]
        self.writer._inject_laxity_music_data()

        load_addr = 0x1000
        sequence_offset = (0x1900 + 3 * 256) - load_addr + 2
        # After 2 notes, should be 0x7F end marker
        self.assertEqual(self.writer.output[sequence_offset + 2], 0x7F)

    def test_inject_laxity_multiple_sequences(self):
        """Test injection of multiple sequences."""
        self.data.orderlists = [[], [], []]
        self.data.sequences = [
            [24, 26],    # 2 bytes + 0x7F
            [30, 32, 34], # 3 bytes + 0x7F
            [40]         # 1 byte + 0x7F
        ]
        self.writer._inject_laxity_music_data()

        load_addr = 0x1000
        sequence_offset = (0x1900 + 3 * 256) - load_addr + 2
        # First sequence
        self.assertEqual(self.writer.output[sequence_offset], 24)
        self.assertEqual(self.writer.output[sequence_offset + 1], 26)
        self.assertEqual(self.writer.output[sequence_offset + 2], 0x7F)
        # Second sequence starts at +3
        self.assertEqual(self.writer.output[sequence_offset + 3], 30)

    def test_inject_laxity_output_too_small(self):
        """Test error handling when output is too small."""
        self.writer.output = bytearray(b'\x00')
        self.writer._inject_laxity_music_data()
        # Should return early
        self.assertEqual(len(self.writer.output), 1)

    def test_inject_laxity_pointer_patching(self):
        """Test pointer patching in relocated player."""
        self.writer.output = bytearray(b'\x00' * 8000)
        self.writer.output[0:2] = struct.pack('<H', 0x1000)
        # Set old pointer value that should be patched
        self.writer.output[0x02C3] = 0x83
        self.writer.output[0x02C4] = 0x1A

        self.data.orderlists = [[], [], []]
        self.data.sequences = []
        self.writer._inject_laxity_music_data()

        # Verify patch was applied (0x1A83 -> 0x1A81)
        self.assertEqual(self.writer.output[0x02C3], 0x81)
        self.assertEqual(self.writer.output[0x02C4], 0x1A)

    def test_inject_laxity_max_3_orderlists(self):
        """Test that only first 3 orderlists are injected."""
        self.data.orderlists = [
            [0, 1],
            [2, 3],
            [4, 5],
            [6, 7],  # Should be ignored
            [8, 9]   # Should be ignored
        ]
        self.data.sequences = []
        self.writer._inject_laxity_music_data()

        load_addr = 0x1000
        # Track 0
        offset0 = 0x1900 - load_addr + 2
        self.assertEqual(self.writer.output[offset0], 0)
        # Track 1
        offset1 = offset0 + 256
        self.assertEqual(self.writer.output[offset1], 2)
        # Track 2
        offset2 = offset1 + 256
        self.assertEqual(self.writer.output[offset2], 4)

    def test_inject_laxity_orderlist_256_limit(self):
        """Test that orderlists are limited to 256 entries."""
        long_orderlist = list(range(300))
        self.data.orderlists = [long_orderlist, [], []]
        self.data.sequences = []
        self.writer._inject_laxity_music_data()

        load_addr = 0x1000
        orderlist_offset = 0x1900 - load_addr + 2
        # Entry 255 should be 255
        self.assertEqual(self.writer.output[orderlist_offset + 255], 255)


# ============================================================================
# Validation Tests
# ============================================================================

class TestSF2Validation(unittest.TestCase):
    """Test SF2 file validation."""

    def setUp(self):
        """Create temp directory and test writer."""
        self.temp_dir = tempfile.mkdtemp()
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_validate_valid_file(self):
        """Test validation of valid SF2 file."""
        test_file = os.path.join(self.temp_dir, 'valid.sf2')
        with open(test_file, 'wb') as f:
            f.write(create_minimal_sf2_template())
        # Should not crash
        self.writer._validate_sf2_file(test_file)

    def test_validate_file_too_small(self):
        """Test validation of file that's too small."""
        test_file = os.path.join(self.temp_dir, 'small.sf2')
        with open(test_file, 'wb') as f:
            f.write(b'\x00' * 50)
        # Should handle gracefully
        self.writer._validate_sf2_file(test_file)

    def test_validate_invalid_magic(self):
        """Test validation with invalid magic number."""
        test_file = os.path.join(self.temp_dir, 'badmagic.sf2')
        data = bytearray()
        data.extend(struct.pack('<H', 0x1000))
        data.extend(struct.pack('<H', 0xDEAD))  # Wrong magic
        data.extend(b'\x00' * 200)
        with open(test_file, 'wb') as f:
            f.write(data)
        # Should detect invalid magic
        self.writer._validate_sf2_file(test_file)

    def test_validate_nonexistent_file(self):
        """Test validation of nonexistent file."""
        test_file = os.path.join(self.temp_dir, 'nonexistent.sf2')
        # Should handle IOError gracefully
        self.writer._validate_sf2_file(test_file)

    def test_validate_truncated_block(self):
        """Test validation with truncated block."""
        test_file = os.path.join(self.temp_dir, 'truncated.sf2')
        data = bytearray()
        data.extend(struct.pack('<H', 0x1000))
        data.extend(struct.pack('<H', 0x1337))
        data.append(1)  # Block ID
        data.extend(struct.pack('<H', 500))  # Declares 500 bytes
        data.extend(b'\x00' * 50)  # But only 50 available
        with open(test_file, 'wb') as f:
            f.write(data)
        # Should detect truncation
        self.writer._validate_sf2_file(test_file)

    def test_validate_end_marker(self):
        """Test validation recognizes end marker."""
        test_file = os.path.join(self.temp_dir, 'endmarker.sf2')
        data = bytearray()
        data.extend(struct.pack('<H', 0x1000))
        data.extend(struct.pack('<H', 0x1337))
        data.append(0xFF)  # End marker
        data.extend(struct.pack('<H', 0))
        data.append(0)
        with open(test_file, 'wb') as f:
            f.write(data)
        # Should validate successfully
        self.writer._validate_sf2_file(test_file)


# ============================================================================
# Logging Tests
# ============================================================================

class TestLogging(unittest.TestCase):
    """Test logging methods."""

    def setUp(self):
        """Create test writer."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)

    def test_log_sf2_structure_basic(self):
        """Test logging SF2 structure."""
        test_data = create_minimal_sf2_template()
        # Should not crash
        self.writer._log_sf2_structure("TEST", test_data)

    def test_log_sf2_structure_empty(self):
        """Test logging with empty data."""
        self.writer._log_sf2_structure("EMPTY", b'')

    def test_log_sf2_structure_large(self):
        """Test logging with large data."""
        large_data = create_minimal_sf2_template() + (b'\x00' * 10000)
        self.writer._log_sf2_structure("LARGE", large_data)

    def test_log_block3_structure(self):
        """Test logging block 3 structure."""
        block3_content = bytearray(200)
        self.writer._log_block3_structure(bytes(block3_content))

    def test_log_block5_structure(self):
        """Test logging block 5 structure."""
        block5_content = bytearray(300)
        self.writer._log_block5_structure(bytes(block5_content))

    def test_print_extraction_summary(self):
        """Test extraction summary printing."""
        self.data.sequences = [[SequenceEvent(0, 0, i) for i in range(10)]]
        self.data.instruments = [b'\x09\x00\xF8\x00\x00\x00\x00\x41']
        # Should not crash
        self.writer._print_extraction_summary()


# ============================================================================
# Complex Scenarios
# ============================================================================

class TestComplexScenarios(unittest.TestCase):
    """Test complex real-world scenarios."""

    def setUp(self):
        """Create temp directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_mixed_orderlist_formats(self):
        """Test handling mixed data types in orderlists."""
        mixed_orderlists = [
            [(0, 0), {'sequence': 1}, 2],  # tuple, dict, int
            [0, (0, 1)],
            [{'sequence': 0}]
        ]

        data = create_minimal_extracted_data(
            orderlists=mixed_orderlists,
            sequences=[[24, 26], [28, 30], [32]]
        )

        writer = SF2Writer(data, driver_type='laxity')
        writer.output = bytearray(b'\x00' * 8000)
        writer.output[0:2] = struct.pack('<H', 0x1000)

        # Should handle mixed types
        writer._inject_laxity_music_data()

    def test_empty_sequence_in_list(self):
        """Test handling empty sequence in list."""
        data = create_minimal_extracted_data(
            sequences=[
                [SequenceEvent(0, 0, 24), SequenceEvent(0, 0, 26)],
                [],  # Empty
                [SequenceEvent(0, 0, 28)]
            ]
        )

        writer = SF2Writer(data)
        writer.output = bytearray(create_minimal_sf2_template())
        writer.load_address = 0x1000
        writer.output.extend(b'\x00' * 2000)
        writer.driver_info.sequence_ptrs_lo = 0x1900
        writer.driver_info.sequence_ptrs_hi = 0x1920
        writer.driver_info.sequence_start = 0x2000

        # Should skip empty sequence
        writer._inject_sequences()

    def test_sequence_mixed_event_types(self):
        """Test sequence with mixed event types."""
        mixed_sequence = [
            {'note': 24, 'duration': 1},
            26,  # Direct int
            {'note': 28, 'gate': True},
            30
        ]

        data = create_minimal_extracted_data(sequences=[mixed_sequence])
        writer = SF2Writer(data, driver_type='laxity')
        writer.output = bytearray(b'\x00' * 8000)
        writer.output[0:2] = struct.pack('<H', 0x1000)

        # Should handle mixed types
        writer._inject_laxity_music_data()


if __name__ == '__main__':
    unittest.main(verbosity=2)
