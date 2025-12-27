#!/usr/bin/env python3
"""SF2 Packer Comprehensive Tests

Tests for SF2 to SID packing functionality.
Focuses on critical packing operations, pointer relocation, and validation.

Test Coverage:
- File loading and validation
- Word read/write operations
- Driver address extraction
- Code/data section management
- Address computation and compaction
- Pointer relocation (3-tier scanning)
- PSID header generation
- Integration tests

Target: 40-60% coverage of sf2_packer.py (currently 0%, 389 statements)
"""

import unittest
import sys
import struct
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_packer import (
    SF2Packer, DataSection, create_psid_header, validate_sid_file
)
from sidm2 import errors


class TestDataSection(unittest.TestCase):
    """Test DataSection dataclass."""

    def test_data_section_creation(self):
        """Test DataSection initialization."""
        section = DataSection(
            source_address=0x1000,
            data=b'\x4C\x00\x10',
            dest_address=0x2000,
            is_code=True
        )

        self.assertEqual(section.source_address, 0x1000)
        self.assertEqual(section.data, b'\x4C\x00\x10')
        self.assertEqual(section.dest_address, 0x2000)
        self.assertEqual(section.is_code, True)

    def test_data_section_size_property(self):
        """Test size property calculation."""
        section = DataSection(
            source_address=0x1000,
            data=b'\x00' * 256
        )

        self.assertEqual(section.size, 256)

    def test_data_section_default_values(self):
        """Test default values for optional fields."""
        section = DataSection(
            source_address=0x1000,
            data=b'\x4C'
        )

        # Default dest_address should be 0
        self.assertEqual(section.dest_address, 0)
        # Default is_code should be True
        self.assertEqual(section.is_code, True)


class TestSF2PackerFileLoading(unittest.TestCase):
    """Test SF2 file loading and validation."""

    def test_load_minimal_sf2_file(self):
        """Test loading minimal valid SF2 file."""
        # Create minimal SF2 file (PRG format)
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            # PRG header: load address 0x1000
            f.write(struct.pack('<H', 0x1000))
            # Minimal data (100 bytes)
            f.write(b'\x00' * 100)
            temp_path = Path(f.name)

        try:
            packer = SF2Packer(temp_path)

            # Verify load address
            self.assertEqual(packer.load_address, 0x1000)
            # Verify driver top (always at $1000)
            self.assertEqual(packer.driver_top, 0x1000)
            # Verify memory loaded
            self.assertEqual(packer.memory[0x1000], 0x00)
        finally:
            temp_path.unlink()

    def test_load_file_too_small(self):
        """Test error handling for files smaller than 2 bytes."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            # Only 1 byte (invalid PRG header)
            f.write(b'\x00')
            temp_path = Path(f.name)

        try:
            with self.assertRaises(errors.InvalidInputError) as cm:
                SF2Packer(temp_path)

            # Verify error message contains useful info
            self.assertIn("at least 2 bytes", str(cm.exception))
        finally:
            temp_path.unlink()

    def test_load_file_exceeds_64kb(self):
        """Test error handling for files that exceed 64KB address space."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            # Load address near end of memory
            f.write(struct.pack('<H', 0xFF00))
            # Too much data (would exceed $10000)
            f.write(b'\x00' * 300)
            temp_path = Path(f.name)

        try:
            with self.assertRaises(errors.InvalidInputError) as cm:
                SF2Packer(temp_path)

            # Verify error mentions 64KB limit
            self.assertIn("64KB", str(cm.exception))
        finally:
            temp_path.unlink()

    def test_sf2_format_detection(self):
        """Test SF2 format magic ID detection."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            # PRG header: load address 0x1000
            f.write(struct.pack('<H', 0x1000))
            # SF2 magic ID: 0x1337
            f.write(struct.pack('<H', 0x1337))
            # Additional data
            f.write(b'\x00' * 100)
            temp_path = Path(f.name)

        try:
            packer = SF2Packer(temp_path)

            # Should detect SF2 format
            self.assertTrue(packer._is_sf2_format())
            self.assertTrue(packer.is_sf2_format)
        finally:
            temp_path.unlink()

    def test_non_sf2_format_detection(self):
        """Test non-SF2 format (raw PRG) detection."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            # PRG header: load address 0x1000
            f.write(struct.pack('<H', 0x1000))
            # Non-SF2 magic (arbitrary data)
            f.write(b'\x4C\x00\x10')
            # Additional data
            f.write(b'\x00' * 100)
            temp_path = Path(f.name)

        try:
            packer = SF2Packer(temp_path)

            # Should NOT detect SF2 format
            self.assertFalse(packer._is_sf2_format())
            self.assertFalse(packer.is_sf2_format)
        finally:
            temp_path.unlink()


class TestWordOperations(unittest.TestCase):
    """Test word read/write operations."""

    def setUp(self):
        """Create test SF2 file for each test."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            # PRG header + minimal data
            f.write(struct.pack('<H', 0x1000))
            f.write(b'\x00' * 100)
            self.temp_path = Path(f.name)
        self.packer = SF2Packer(self.temp_path)

    def tearDown(self):
        """Clean up test file."""
        self.temp_path.unlink()

    def test_read_word_little_endian(self):
        """Test little-endian word reading."""
        # Write test data
        self.packer.memory[0x1000] = 0x34  # Low byte
        self.packer.memory[0x1001] = 0x12  # High byte

        # Read word
        value = self.packer._read_word(0x1000)

        # Should be 0x1234 (little-endian)
        self.assertEqual(value, 0x1234)

    def test_write_word_little_endian(self):
        """Test little-endian word writing."""
        # Write word
        self.packer._write_word(0x1000, 0x5678)

        # Verify bytes
        self.assertEqual(self.packer.memory[0x1000], 0x78)  # Low byte
        self.assertEqual(self.packer.memory[0x1001], 0x56)  # High byte

    def test_read_word_big_endian(self):
        """Test big-endian word reading."""
        # Write test data
        self.packer.memory[0x1000] = 0x12  # High byte
        self.packer.memory[0x1001] = 0x34  # Low byte

        # Read word (big-endian)
        value = self.packer._read_word_be(0x1000)

        # Should be 0x1234 (big-endian)
        self.assertEqual(value, 0x1234)

    def test_word_roundtrip(self):
        """Test write then read produces same value."""
        test_values = [0x0000, 0x1234, 0xABCD, 0xFFFF]

        for value in test_values:
            self.packer._write_word(0x2000, value)
            read_value = self.packer._read_word(0x2000)
            self.assertEqual(read_value, value,
                           f"Roundtrip failed for 0x{value:04X}")


class TestDriverAddressExtraction(unittest.TestCase):
    """Test driver address extraction."""

    def test_read_driver_addresses(self):
        """Test reading init and play addresses from DriverCommon."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            # PRG header: load address 0x1000
            f.write(struct.pack('<H', 0x1000))

            # Write file data (file offset 0x02+ loads at memory[0x1000+])
            # memory[load_address + 0x2F] = file offset 0x31 = init address low byte
            # memory[load_address + 0x30] = file offset 0x32 = init address high byte
            # memory[load_address + 0x31] = file offset 0x33 = play address low byte
            # memory[load_address + 0x32] = file offset 0x34 = play address high byte
            file_data = bytearray(0x40)

            # Offset 0x2F-0x30 in loaded data (file offset 0x31-0x32): init = 0x1100
            file_data[0x2F] = 0x00  # Init low byte
            file_data[0x30] = 0x11  # Init high byte

            # Offset 0x31-0x32 in loaded data (file offset 0x33-0x34): play = 0x1200
            file_data[0x31] = 0x00  # Play low byte
            file_data[0x32] = 0x12  # Play high byte

            f.write(bytes(file_data))
            temp_path = Path(f.name)

        try:
            packer = SF2Packer(temp_path)
            init_addr, play_addr = packer.read_driver_addresses()

            self.assertEqual(init_addr, 0x1100)
            self.assertEqual(play_addr, 0x1200)
        finally:
            temp_path.unlink()


class TestSectionManagement(unittest.TestCase):
    """Test data section extraction and management."""

    def setUp(self):
        """Create test packer."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            f.write(struct.pack('<H', 0x1000))
            f.write(b'\x00' * 0x1000)
            self.temp_path = Path(f.name)
        self.packer = SF2Packer(self.temp_path)

    def tearDown(self):
        """Clean up."""
        self.temp_path.unlink()

    def test_scan_until_marker(self):
        """Test scanning memory until marker byte found."""
        # Write test data with marker
        test_data = b'\x01\x02\x03\x7F\x05\x06'
        self.packer.memory[0x1000:0x1006] = test_data

        # Scan until 0x7F marker
        result = self.packer._scan_until_marker(0x1000, [0x7F])

        # Should include data up to and including marker
        self.assertEqual(result, b'\x01\x02\x03\x7F')

    def test_scan_until_marker_not_found(self):
        """Test scanning when marker not found (max_size limit)."""
        # Write test data without marker
        self.packer.memory[0x1000:0x1010] = b'\x01' * 16

        # Scan with small max_size
        result = self.packer._scan_until_marker(0x1000, [0x7F], max_size=8)

        # Should stop at max_size
        self.assertEqual(len(result), 8)

    def test_scan_multiple_markers(self):
        """Test scanning with multiple valid marker bytes."""
        # Write test data with different markers
        test_data = b'\x01\x02\xFE\x05\x06'
        self.packer.memory[0x1000:0x1005] = test_data

        # Scan for either 0x7F or 0xFE
        result = self.packer._scan_until_marker(0x1000, [0x7F, 0xFE])

        # Should stop at first marker found (0xFE)
        self.assertEqual(result, b'\x01\x02\xFE')


class TestAddressComputation(unittest.TestCase):
    """Test destination address computation."""

    def setUp(self):
        """Create test packer with sections."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            f.write(struct.pack('<H', 0x1000))
            f.write(b'\x00' * 100)
            self.temp_path = Path(f.name)
        self.packer = SF2Packer(self.temp_path)

    def tearDown(self):
        """Clean up."""
        self.temp_path.unlink()

    def test_compute_destination_addresses_sequential(self):
        """Test sequential address assignment."""
        # Create test sections with gaps
        self.packer.data_sections = [
            DataSection(0x1000, b'\x00' * 50),
            DataSection(0x1100, b'\x00' * 100),  # Gap of 206 bytes
            DataSection(0x1200, b'\x00' * 30),   # Gap of 206 bytes
        ]

        # Compute destinations starting at 0x2000
        end_addr = self.packer.compute_destination_addresses(0x2000)

        # Should eliminate gaps
        self.assertEqual(self.packer.data_sections[0].dest_address, 0x2000)
        self.assertEqual(self.packer.data_sections[1].dest_address, 0x2032)  # 0x2000 + 50
        self.assertEqual(self.packer.data_sections[2].dest_address, 0x2096)  # 0x2032 + 100

        # End address should be last section end
        self.assertEqual(end_addr, 0x2096 + 30)  # 0x20B4

    def test_compute_destination_addresses_sorting(self):
        """Test sections are sorted by source address."""
        # Create sections in random order
        self.packer.data_sections = [
            DataSection(0x1200, b'\x00' * 30),
            DataSection(0x1000, b'\x00' * 50),
            DataSection(0x1100, b'\x00' * 100),
        ]

        # Compute destinations
        self.packer.compute_destination_addresses(0x2000)

        # Should be sorted by source address
        self.assertEqual(self.packer.data_sections[0].source_address, 0x1000)
        self.assertEqual(self.packer.data_sections[1].source_address, 0x1100)
        self.assertEqual(self.packer.data_sections[2].source_address, 0x1200)

    def test_compute_destination_addresses_compaction(self):
        """Test gap elimination."""
        # Create sections with large gaps
        self.packer.data_sections = [
            DataSection(0x1000, b'\x00' * 10),
            DataSection(0x2000, b'\x00' * 10),  # 4KB gap
        ]

        # Compute destinations
        end_addr = self.packer.compute_destination_addresses(0x3000)

        # Should eliminate 4KB gap
        self.assertEqual(self.packer.data_sections[0].dest_address, 0x3000)
        self.assertEqual(self.packer.data_sections[1].dest_address, 0x300A)  # No gap

        # Total size should be 20 bytes, not 4KB+
        self.assertEqual(end_addr, 0x3014)


class TestPointerRelocation(unittest.TestCase):
    """Test pointer relocation logic."""

    def setUp(self):
        """Create test packer."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            f.write(struct.pack('<H', 0x1000))
            f.write(b'\x00' * 0x1000)
            self.temp_path = Path(f.name)
        self.packer = SF2Packer(self.temp_path)

    def tearDown(self):
        """Clean up."""
        self.temp_path.unlink()

    def test_adjust_sequence_pointers(self):
        """Test sequence pointer table adjustment."""
        # Set up sequence pointer at 0x1903
        ptr_addr = 0x1903
        old_ptr = 0x1500
        self.packer._write_word(ptr_addr, old_ptr)

        # Add to sequence pointer list
        self.packer.sequence_pointers = [ptr_addr]

        # Create sections with address mapping
        self.packer.data_sections = [
            DataSection(0x1500, b'\x00' * 10, dest_address=0x2000)
        ]

        # Adjust pointers
        self.packer.adjust_pointers()

        # Pointer should now point to new address
        new_ptr = self.packer._read_word(ptr_addr)
        self.assertEqual(new_ptr, 0x2000)

    def test_adjust_orderlist_pointers(self):
        """Test orderlist pointer adjustment."""
        # Set up orderlist pointer
        ptr_addr = 0x1900
        old_ptr = 0x1600
        self.packer._write_word(ptr_addr, old_ptr)

        # Add to orderlist pointer list
        self.packer.orderlist_pointers = [ptr_addr]

        # Create sections with address mapping
        self.packer.data_sections = [
            DataSection(0x1600, b'\x00' * 20, dest_address=0x2100)
        ]

        # Adjust pointers
        self.packer.adjust_pointers()

        # Pointer should be updated
        new_ptr = self.packer._read_word(ptr_addr)
        self.assertEqual(new_ptr, 0x2100)

    def test_pointer_not_in_address_map(self):
        """Test pointer that doesn't match any section is unchanged."""
        # Set up pointer to address not in any section
        ptr_addr = 0x1903
        old_ptr = 0xD400  # SID register (not in sections)
        self.packer._write_word(ptr_addr, old_ptr)

        # Add to sequence pointer list
        self.packer.sequence_pointers = [ptr_addr]

        # Create sections (doesn't include 0xD400)
        self.packer.data_sections = [
            DataSection(0x1500, b'\x00' * 10, dest_address=0x2000)
        ]

        # Adjust pointers
        self.packer.adjust_pointers()

        # Pointer should be unchanged
        new_ptr = self.packer._read_word(ptr_addr)
        self.assertEqual(new_ptr, old_ptr)


class TestPSIDHeaderGeneration(unittest.TestCase):
    """Test PSID header generation."""

    def test_create_psid_header_basic(self):
        """Test basic PSID header creation."""
        header = create_psid_header(
            name="Test Song",
            author="Test Author",
            copyright_str="2025 Test",
            load_address=0x1000,
            init_address=0x1000,
            play_address=0x1003
        )

        # Should be exactly 124 bytes
        self.assertEqual(len(header), 124)

        # Check magic
        self.assertEqual(header[0:4], b'PSID')

        # Check version (big-endian 0x0002)
        version = struct.unpack('>H', header[4:6])[0]
        self.assertEqual(version, 0x0002)

        # Check data offset (124 bytes)
        data_offset = struct.unpack('>H', header[6:8])[0]
        self.assertEqual(data_offset, 0x007C)

        # Check addresses (big-endian)
        load_addr = struct.unpack('>H', header[8:10])[0]
        init_addr = struct.unpack('>H', header[10:12])[0]
        play_addr = struct.unpack('>H', header[12:14])[0]

        self.assertEqual(load_addr, 0x1000)
        self.assertEqual(init_addr, 0x1000)
        self.assertEqual(play_addr, 0x1003)

    def test_psid_header_string_fields(self):
        """Test string field encoding in PSID header."""
        name = "My Song"
        author = "Composer"
        copyright_str = "2025"

        header = create_psid_header(
            name=name,
            author=author,
            copyright_str=copyright_str,
            load_address=0x1000,
            init_address=0x1000,
            play_address=0x1003
        )

        # Extract and verify name (offset 22, 32 bytes)
        name_bytes = header[22:54]
        self.assertTrue(name_bytes.startswith(name.encode('ascii')))

        # Extract and verify author (offset 54, 32 bytes)
        author_bytes = header[54:86]
        self.assertTrue(author_bytes.startswith(author.encode('ascii')))

        # Extract and verify copyright (offset 86, 32 bytes)
        copyright_bytes = header[86:118]
        self.assertTrue(copyright_bytes.startswith(copyright_str.encode('ascii')))

    def test_psid_header_long_strings_truncated(self):
        """Test that strings longer than 31 chars are truncated."""
        long_name = "A" * 50  # 50 characters

        header = create_psid_header(
            name=long_name,
            author="Author",
            copyright_str="2025",
            load_address=0x1000,
            init_address=0x1000,
            play_address=0x1003
        )

        # Name field should contain at most 31 'A's
        name_bytes = header[22:54]
        # Count non-null bytes
        name_str = name_bytes.rstrip(b'\x00').decode('ascii')
        self.assertLessEqual(len(name_str), 31)

    def test_psid_header_song_count(self):
        """Test song count and start song fields."""
        header = create_psid_header(
            name="Test",
            author="Test",
            copyright_str="Test",
            load_address=0x1000,
            init_address=0x1000,
            play_address=0x1003
        )

        # Number of songs (offset 14, big-endian)
        num_songs = struct.unpack('>H', header[14:16])[0]
        self.assertEqual(num_songs, 0x0001)

        # Start song (offset 16, big-endian)
        start_song = struct.unpack('>H', header[16:18])[0]
        self.assertEqual(start_song, 0x0001)


class TestOutputCreation(unittest.TestCase):
    """Test output data creation."""

    def setUp(self):
        """Create test packer."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            f.write(struct.pack('<H', 0x1000))
            f.write(b'\x00' * 100)
            self.temp_path = Path(f.name)
        self.packer = SF2Packer(self.temp_path)

    def tearDown(self):
        """Clean up."""
        self.temp_path.unlink()

    def test_create_output_data_concatenation(self):
        """Test output data concatenates all sections."""
        # Create test sections
        self.packer.data_sections = [
            DataSection(0x1000, b'\x01\x02\x03'),
            DataSection(0x1100, b'\x04\x05'),
            DataSection(0x1200, b'\x06\x07\x08\x09'),
        ]

        # Create output
        output = self.packer.create_output_data(0x2000)

        # Should concatenate all section data
        expected = b'\x01\x02\x03\x04\x05\x06\x07\x08\x09'
        self.assertEqual(output, expected)

    def test_create_output_data_preserves_order(self):
        """Test output preserves section order."""
        # Sections in specific order
        self.packer.data_sections = [
            DataSection(0x1000, b'AAA'),
            DataSection(0x1100, b'BBB'),
            DataSection(0x1200, b'CCC'),
        ]

        output = self.packer.create_output_data(0x2000)

        # Should preserve order
        self.assertEqual(output, b'AAABBBCCC')


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def test_empty_sections_list(self):
        """Test handling of empty sections list."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            f.write(struct.pack('<H', 0x1000))
            f.write(b'\x00' * 100)
            temp_path = Path(f.name)

        try:
            packer = SF2Packer(temp_path)
            # No sections added
            packer.data_sections = []

            # Should handle empty list
            end_addr = packer.compute_destination_addresses(0x2000)
            self.assertEqual(end_addr, 0x2000)

            output = packer.create_output_data(0x2000)
            self.assertEqual(output, b'')
        finally:
            temp_path.unlink()

    def test_single_byte_section(self):
        """Test handling of single-byte sections."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            f.write(struct.pack('<H', 0x1000))
            f.write(b'\x00' * 100)
            temp_path = Path(f.name)

        try:
            packer = SF2Packer(temp_path)
            packer.data_sections = [
                DataSection(0x1000, b'\xFF')
            ]

            # Should handle 1-byte section
            packer.compute_destination_addresses(0x2000)
            output = packer.create_output_data(0x2000)

            self.assertEqual(len(output), 1)
            self.assertEqual(output, b'\xFF')
        finally:
            temp_path.unlink()

    def test_large_section(self):
        """Test handling of large sections (>4KB)."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            f.write(struct.pack('<H', 0x1000))
            f.write(b'\x00' * 8000)
            temp_path = Path(f.name)

        try:
            packer = SF2Packer(temp_path)
            large_data = b'\xAB' * 5000  # 5KB section
            packer.data_sections = [
                DataSection(0x1000, large_data)
            ]

            # Should handle large section
            packer.compute_destination_addresses(0x2000)
            output = packer.create_output_data(0x2000)

            self.assertEqual(len(output), 5000)
            self.assertEqual(output[0], 0xAB)
            self.assertEqual(output[-1], 0xAB)
        finally:
            temp_path.unlink()


class TestIntegration(unittest.TestCase):
    """Integration tests for complete packing workflow."""

    def test_full_pack_workflow_minimal(self):
        """Test complete pack workflow with minimal SF2."""
        with tempfile.NamedTemporaryFile(suffix='.sf2', delete=False) as f:
            # Create minimal valid SF2-like file
            f.write(struct.pack('<H', 0x1000))  # Load address

            # Write driver code with entry stubs
            # Init stub: JMP $1100
            f.write(b'\x4C\x00\x11')
            # Play stub: JMP $1200
            f.write(b'\x4C\x00\x12')

            # Padding to ensure we have driver addresses
            f.write(b'\x00' * 0x2F)

            # Driver addresses (at file offset 0x31 and 0x33)
            f.write(struct.pack('<H', 0x1100))  # Init address
            f.write(struct.pack('<H', 0x1200))  # Play address

            # More padding
            f.write(b'\x00' * 200)

            temp_path = Path(f.name)

        try:
            packer = SF2Packer(temp_path)

            # Add minimal sections
            packer.data_sections = [
                DataSection(0x1000, b'\x4C\x00\x11\x4C\x00\x12' + b'\x00' * 50,
                          is_code=True)
            ]

            # Compute addresses
            packer.compute_destination_addresses(0x1000)

            # Create output
            output = packer.create_output_data(0x1000)

            # Should produce valid output
            self.assertGreater(len(output), 0)
            self.assertIsInstance(output, bytes)
        finally:
            temp_path.unlink()


def main():
    """Run all SF2 packer tests."""
    # Run with verbose output
    unittest.main(argv=[''], verbosity=2, exit=True)


if __name__ == '__main__':
    main()
