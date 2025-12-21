"""
Unit tests for SF2 Packer module.

Tests SF2 to SID conversion, memory management, pointer relocation,
and PRG format generation.

Run: python scripts/test_sf2_packer.py
"""

import unittest
import struct
import tempfile
import os
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_packer import SF2Packer, DataSection
from sidm2 import errors


class TestDataSection(unittest.TestCase):
    """Test DataSection dataclass."""

    def test_create_data_section(self):
        """Test DataSection creation."""
        data = b'\x01\x02\x03\x04'
        section = DataSection(
            source_address=0x1000,
            data=data
        )

        self.assertEqual(section.source_address, 0x1000)
        self.assertEqual(section.data, data)
        self.assertEqual(section.dest_address, 0)
        self.assertTrue(section.is_code)

    def test_data_section_size(self):
        """Test DataSection size property."""
        data = b'\x01\x02\x03\x04\x05'
        section = DataSection(
            source_address=0x1000,
            data=data
        )

        self.assertEqual(section.size, 5)

    def test_data_section_with_dest(self):
        """Test DataSection with destination address."""
        section = DataSection(
            source_address=0x1000,
            data=b'\x01\x02',
            dest_address=0x2000,
            is_code=False
        )

        self.assertEqual(section.dest_address, 0x2000)
        self.assertFalse(section.is_code)


class TestSF2PackerInitialization(unittest.TestCase):
    """Test SF2Packer initialization and file loading."""

    def setUp(self):
        """Create temporary test files."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_test_sf2(self, load_addr=0x0D7E, data_size=100, magic_id=None):
        """Create a minimal test SF2 file."""
        # PRG format: 2-byte load address + data
        prg_data = struct.pack('<H', load_addr)

        # Add magic ID if specified (SF2 format marker)
        if magic_id is not None:
            prg_data += struct.pack('<H', magic_id)
            data_size -= 2  # Account for magic ID

        # Pad with zeros
        prg_data += bytes(data_size)

        # Create temporary file
        temp_file = os.path.join(self.temp_dir, 'test.sf2')
        with open(temp_file, 'wb') as f:
            f.write(prg_data)

        return Path(temp_file)

    def test_load_valid_sf2(self):
        """Test loading valid SF2 file."""
        sf2_file = self._create_test_sf2()
        packer = SF2Packer(sf2_file)

        self.assertEqual(packer.load_address, 0x0D7E)
        self.assertEqual(packer.driver_top, 0x1000)
        self.assertIsInstance(packer.memory, bytearray)
        self.assertEqual(len(packer.memory), 65536)

    def test_detect_sf2_format_with_magic(self):
        """Test SF2 format detection with magic ID 0x1337."""
        sf2_file = self._create_test_sf2(magic_id=0x1337)
        packer = SF2Packer(sf2_file)

        self.assertTrue(packer.is_sf2_format)

    def test_detect_non_sf2_format(self):
        """Test non-SF2 format detection (no magic ID)."""
        sf2_file = self._create_test_sf2(magic_id=None)
        packer = SF2Packer(sf2_file)

        self.assertFalse(packer.is_sf2_format)

    def test_load_sf2_too_small(self):
        """Test error when SF2 file is too small."""
        temp_file = os.path.join(self.temp_dir, 'tiny.sf2')
        with open(temp_file, 'wb') as f:
            f.write(b'\x00')  # Only 1 byte

        with self.assertRaises(errors.InvalidInputError) as ctx:
            SF2Packer(Path(temp_file))

        self.assertIn("at least 2 bytes", str(ctx.exception))

    def test_load_sf2_exceeds_64kb(self):
        """Test error when SF2 data exceeds 64KB boundary."""
        # Create file that would load beyond 64KB
        temp_file = os.path.join(self.temp_dir, 'overflow.sf2')
        load_addr = 0xFFFF
        data = bytes(100)  # Will overflow beyond $10000

        with open(temp_file, 'wb') as f:
            f.write(struct.pack('<H', load_addr))
            f.write(data)

        with self.assertRaises(errors.InvalidInputError) as ctx:
            SF2Packer(Path(temp_file))

        self.assertIn("64KB", str(ctx.exception))


class TestSF2PackerMemoryOperations(unittest.TestCase):
    """Test memory read/write operations."""

    def setUp(self):
        """Create packer with test data."""
        self.temp_dir = tempfile.mkdtemp()

        # Create minimal SF2 file
        temp_file = os.path.join(self.temp_dir, 'test.sf2')
        with open(temp_file, 'wb') as f:
            f.write(struct.pack('<H', 0x1000))  # Load address
            f.write(bytes(200))  # Padding

        self.packer = SF2Packer(Path(temp_file))

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_read_word_little_endian(self):
        """Test reading little-endian 16-bit word."""
        # Set up test data: 0x1234 in little-endian = 0x34 0x12
        self.packer.memory[0x1000] = 0x34
        self.packer.memory[0x1001] = 0x12

        result = self.packer._read_word(0x1000)
        self.assertEqual(result, 0x1234)

    def test_write_word_little_endian(self):
        """Test writing little-endian 16-bit word."""
        self.packer._write_word(0x1000, 0x5678)

        self.assertEqual(self.packer.memory[0x1000], 0x78)
        self.assertEqual(self.packer.memory[0x1001], 0x56)

    def test_read_word_big_endian(self):
        """Test reading big-endian 16-bit word."""
        # Set up test data: 0xABCD in big-endian = 0xAB 0xCD
        self.packer.memory[0x1000] = 0xAB
        self.packer.memory[0x1001] = 0xCD

        result = self.packer._read_word_be(0x1000)
        self.assertEqual(result, 0xABCD)

    def test_read_write_roundtrip(self):
        """Test write then read gives same value."""
        test_value = 0x9ABC
        test_addr = 0x2000

        self.packer._write_word(test_addr, test_value)
        result = self.packer._read_word(test_addr)

        self.assertEqual(result, test_value)


class TestSF2PackerDriverAddresses(unittest.TestCase):
    """Test reading driver init and play addresses."""

    def setUp(self):
        """Create packer with driver addresses."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_read_driver_addresses(self):
        """Test reading init and play addresses from SF2."""
        # Create SF2 file with driver addresses
        load_addr = 0x0D7E
        init_addr = 0x1000
        play_addr = 0x1003

        temp_file = os.path.join(self.temp_dir, 'test.sf2')
        with open(temp_file, 'wb') as f:
            # Write PRG load address
            f.write(struct.pack('<H', load_addr))

            # Write padding up to init address offset
            # Init at file offset 0x31 = memory offset 0x2F from load_addr
            f.write(bytes(0x2F))

            # Write init address (little-endian)
            f.write(struct.pack('<H', init_addr))

            # Write play address (little-endian)
            f.write(struct.pack('<H', play_addr))

            # Pad rest
            f.write(bytes(100))

        packer = SF2Packer(Path(temp_file))
        init, play = packer.read_driver_addresses()

        self.assertEqual(init, init_addr)
        self.assertEqual(play, play_addr)


class TestSF2PackerScanning(unittest.TestCase):
    """Test memory scanning operations."""

    def setUp(self):
        """Create packer for scanning tests."""
        self.temp_dir = tempfile.mkdtemp()

        # Create minimal SF2 file
        temp_file = os.path.join(self.temp_dir, 'test.sf2')
        with open(temp_file, 'wb') as f:
            f.write(struct.pack('<H', 0x1000))
            f.write(bytes(2000))

        self.packer = SF2Packer(Path(temp_file))

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_scan_until_marker(self):
        """Test scanning memory until marker byte."""
        # Set up test data: sequence ending with 0x7F
        test_addr = 0x1500
        test_data = bytes([0x01, 0x02, 0x03, 0x04, 0x7F])

        for i, byte in enumerate(test_data):
            self.packer.memory[test_addr + i] = byte

        result = self.packer._scan_until_marker(test_addr, [0x7F])

        self.assertEqual(result, test_data)

    def test_scan_until_marker_max_size(self):
        """Test scanning respects max_size limit."""
        test_addr = 0x1500
        # Fill with non-marker bytes
        for i in range(100):
            self.packer.memory[test_addr + i] = 0x01

        result = self.packer._scan_until_marker(test_addr, [0x7F], max_size=10)

        self.assertEqual(len(result), 10)

    def test_scan_multiple_markers(self):
        """Test scanning for multiple marker types."""
        test_addr = 0x1500
        # Data ending with 0xFE (loop marker)
        test_data = bytes([0xA0, 0x00, 0xA2, 0x01, 0xFE])

        for i, byte in enumerate(test_data):
            self.packer.memory[test_addr + i] = byte

        result = self.packer._scan_until_marker(test_addr, [0x7F, 0xFE, 0xFF])

        self.assertEqual(result, test_data)


class TestSF2PackerConstants(unittest.TestCase):
    """Test SF2Packer constants and offsets."""

    def test_driver_offsets(self):
        """Test driver structure offsets."""
        self.assertEqual(SF2Packer.DRIVER_CODE_TOP, 0x1000)
        self.assertEqual(SF2Packer.SEQUENCE_TABLE_OFFSET, 0x0903)
        self.assertEqual(SF2Packer.INSTRUMENT_TABLE_OFFSET, 0x0A03)
        self.assertEqual(SF2Packer.PULSE_TABLE_OFFSET, 0x0D03)
        self.assertEqual(SF2Packer.FILTER_TABLE_OFFSET, 0x0F03)

    def test_control_bytes(self):
        """Test control byte constants."""
        self.assertEqual(SF2Packer.END_MARKER, 0x7F)
        self.assertEqual(SF2Packer.LOOP_MARKER, 0x7E)
        self.assertEqual(SF2Packer.ORDERLIST_END, 0xFF)
        self.assertEqual(SF2Packer.ORDERLIST_LOOP, 0xFE)


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
