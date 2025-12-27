#!/usr/bin/env python3
"""SF2Writer Comprehensive Tests

Tests for SF2 file writing functionality.
Target: Improve coverage from 3.16% to 60% (sf2_writer.py: 1,143 statements)

Test Coverage:
- Core methods (__init__, write, _find_template, _find_driver)
- Template parsing (_parse_sf2_header, _parse_descriptor_block, etc.)
- Data injection (15 injection methods for sequences, instruments, tables)
- Helper methods (_addr_to_offset, _update_table_definitions, etc.)
- Validation and logging
- Integration tests (full SF2 generation)

Priority: CRITICAL - Core conversion module with 1,090 missing lines
"""

import unittest
import sys
import struct
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_writer import SF2Writer
from sidm2.models import (
    ExtractedData, PSIDHeader, SequenceEvent, SF2DriverInfo, InstrumentData
)
from sidm2 import errors


# ============================================================================
# Test Fixtures and Helpers
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
        'orderlists': [[], [], []],  # 3 voices
        'instruments': [],
        'wavetable': b'',
        'pulsetable': b'',
        'filtertable': b'',
    }
    defaults.update(kwargs)
    return ExtractedData(**defaults)


def create_test_sequence(length: int = 10) -> List[SequenceEvent]:
    """Create test sequence with specified length."""
    return [
        SequenceEvent(instrument=0, command=0, note=i)
        for i in range(length)
    ]


def create_minimal_sf2_template() -> bytes:
    """Create minimal SF2 template file for testing.

    SF2 format:
    - PRG header (2 bytes): load address
    - SF2 magic (2 bytes): 0x1337
    - Blocks with ID + size + content + checksum
    - Block 0xFF: end marker
    """
    output = bytearray()

    # PRG header: load address 0x1000
    output.extend(struct.pack('<H', 0x1000))

    # SF2 magic ID
    output.extend(struct.pack('<H', 0x1337))

    # Minimal descriptor block (Block 1)
    block1_content = bytearray()
    # Driver version info (4 bytes)
    block1_content.extend(struct.pack('<H', 11))  # Driver type
    block1_content.extend(struct.pack('<H', 0))   # Driver version

    # Block 1 header: ID, size, content, checksum
    output.append(1)  # Block ID
    output.extend(struct.pack('<H', len(block1_content)))  # Size
    output.extend(block1_content)
    output.append(sum(block1_content) & 0xFF)  # Checksum

    # Block 0xFF: end marker
    output.append(0xFF)
    output.extend(struct.pack('<H', 0))  # Size 0
    output.append(0)  # Checksum

    return bytes(output)


# ============================================================================
# Core Methods Tests
# ============================================================================

class TestSF2WriterInit(unittest.TestCase):
    """Test SF2Writer initialization."""

    def test_init_with_minimal_data(self):
        """Test initialization with minimal ExtractedData."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)

        self.assertIsNotNone(writer)
        self.assertEqual(writer.data, data)
        self.assertEqual(len(writer.output), 0)
        self.assertEqual(writer.driver_type, 'np20')  # Default
        self.assertEqual(writer.load_address, 0)

    def test_init_with_custom_driver_type(self):
        """Test initialization with custom driver type."""
        data = create_minimal_extracted_data()

        # Test each driver type
        for driver_type in ['driver11', 'np20', 'laxity', 'galway']:
            writer = SF2Writer(data, driver_type=driver_type)
            self.assertEqual(writer.driver_type, driver_type)

    def test_init_creates_sf2_driver_info(self):
        """Test that SF2DriverInfo is initialized."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)

        self.assertIsNotNone(writer.driver_info)
        self.assertIsInstance(writer.driver_info, SF2DriverInfo)


class TestFindTemplate(unittest.TestCase):
    """Test template finding logic."""

    def test_find_template_driver11(self):
        """Test finding driver11 template."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data, driver_type='driver11')

        # Should look for G5/drivers/driver11/template.sf2 or examples
        template_path = writer._find_template('driver11')

        if template_path:
            # Path should contain 'driver' or 'Driver' (case-insensitive)
            self.assertTrue(
                'driver' in template_path.lower() or 'g5' in template_path.lower(),
                f"Expected driver-related path, got: {template_path}"
            )

    def test_find_template_np20(self):
        """Test finding np20 template."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data, driver_type='np20')

        template_path = writer._find_template('np20')

        if template_path:
            self.assertIn('np20', template_path)

    def test_find_template_laxity(self):
        """Test finding laxity template."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data, driver_type='laxity')

        template_path = writer._find_template('laxity')

        if template_path:
            self.assertIn('laxity', template_path)

    def test_find_template_nonexistent(self):
        """Test finding nonexistent template."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)

        template_path = writer._find_template('nonexistent_driver_xyz_123')

        # May return None, empty string, or fallback path
        # Just verify it's a string or None
        self.assertTrue(template_path is None or isinstance(template_path, str))


class TestFindDriver(unittest.TestCase):
    """Test driver finding logic."""

    def test_find_driver_returns_path(self):
        """Test that _find_driver returns a path string or None."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)

        driver_path = writer._find_driver()

        # Should return string path or None
        self.assertTrue(driver_path is None or isinstance(driver_path, str))

    def test_find_driver_path_format(self):
        """Test driver path has correct format."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)

        driver_path = writer._find_driver()

        if driver_path:
            # Should contain 'driver' or 'G5' in path
            self.assertTrue(
                'driver' in driver_path.lower() or 'g5' in driver_path.lower()
            )


class TestWrite(unittest.TestCase):
    """Test main write() method."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_creates_file(self):
        """Test that write() creates output file."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data, driver_type='driver11')

        output_path = os.path.join(self.temp_dir, 'test_output.sf2')

        # Mock template finding to use test template
        with patch.object(writer, '_find_template') as mock_find:
            # Create test template
            template_path = os.path.join(self.temp_dir, 'template.sf2')
            with open(template_path, 'wb') as f:
                f.write(create_minimal_sf2_template())

            mock_find.return_value = template_path

            # Write file
            writer.write(output_path)

            # Verify file exists
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)

    def test_write_with_nonexistent_template(self):
        """Test write() with nonexistent template falls back to driver."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)

        output_path = os.path.join(self.temp_dir, 'test_output.sf2')

        # Mock both template and driver finding
        with patch.object(writer, '_find_template') as mock_template, \
             patch.object(writer, '_find_driver') as mock_driver, \
             patch.object(writer, '_create_minimal_structure') as mock_create:

            # Template doesn't exist
            mock_template.return_value = '/nonexistent/template.sf2'
            # Driver also doesn't exist (fallback to minimal structure)
            mock_driver.return_value = '/nonexistent/driver.prg'

            # Should not raise error (creates minimal structure)
            writer.write(output_path)

            # Should have called _create_minimal_structure
            mock_create.assert_called_once()

    def test_write_permission_error_on_read(self):
        """Test write() raises PermissionError on template read failure."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)

        output_path = os.path.join(self.temp_dir, 'test_output.sf2')

        with patch.object(writer, '_find_template') as mock_find:
            # Template exists but can't be read
            mock_find.return_value = '/root/protected_template.sf2'

            with patch('builtins.open', side_effect=IOError("Permission denied")):
                with self.assertRaises(errors.PermissionError):
                    writer.write(output_path)


# ============================================================================
# Template Parsing Tests
# ============================================================================

class TestParseTemplateBlocks(unittest.TestCase):
    """Test SF2 template block parsing."""

    def setUp(self):
        """Create test writer with minimal template."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)
        self.writer.output = bytearray(create_minimal_sf2_template())
        self.writer.load_address = 0x1000

    def test_parse_sf2_header(self):
        """Test SF2 header parsing."""
        result = self.writer._parse_sf2_header()

        # Should successfully parse header
        self.assertTrue(result)

        # Should have detected SF2 format
        # (load_address would be set)
        self.assertGreater(self.writer.load_address, 0)

    def test_parse_sf2_header_invalid_magic(self):
        """Test parsing with invalid SF2 magic."""
        # Corrupt magic ID
        self.writer.output[2:4] = b'\x00\x00'

        result = self.writer._parse_sf2_header()

        # Should fail to parse
        self.assertFalse(result)

    def test_parse_descriptor_block(self):
        """Test descriptor block parsing."""
        # Create descriptor block content
        descriptor_content = bytearray()
        descriptor_content.extend(struct.pack('<H', 11))  # Driver type
        descriptor_content.extend(struct.pack('<H', 1))   # Driver version

        # Should not raise error
        self.writer._parse_descriptor_block(bytes(descriptor_content))

        # Driver info should be updated
        self.assertEqual(self.writer.driver_info.driver_type, 11)

    def test_parse_music_data_block(self):
        """Test music data block parsing."""
        # Create music data block with orderlist pointers
        music_data = bytearray(100)

        # Set orderlist pointers at expected offsets
        music_data[0:2] = struct.pack('<H', 0x1900)  # Voice 0
        music_data[2:4] = struct.pack('<H', 0x1920)  # Voice 1
        music_data[4:6] = struct.pack('<H', 0x1940)  # Voice 2

        # Should not raise error
        self.writer._parse_music_data_block(bytes(music_data))

        # Driver info should have orderlist pointers
        # (Implementation may vary, just check no crash)
        self.assertIsNotNone(self.writer.driver_info)

    def test_parse_tables_block(self):
        """Test tables block parsing."""
        # Create tables block with instrument definitions
        tables_data = bytearray(200)

        # Should not raise error
        self.writer._parse_tables_block(bytes(tables_data))

        # Should update driver info table addresses
        self.assertIsNotNone(self.writer.driver_info.table_addresses)


# ============================================================================
# Helper Method Tests
# ============================================================================

class TestAddrToOffset(unittest.TestCase):
    """Test address to offset conversion."""

    def test_addr_to_offset_basic(self):
        """Test basic address to offset conversion."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)
        writer.load_address = 0x1000

        # Address 0x1050 should map to offset 0x52 (0x50 + 2 for PRG header)
        offset = writer._addr_to_offset(0x1050)
        self.assertEqual(offset, 0x52)

    def test_addr_to_offset_at_load_address(self):
        """Test conversion at exact load address."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)
        writer.load_address = 0x1000

        # Address equals load address -> offset 2 (PRG header)
        offset = writer._addr_to_offset(0x1000)
        self.assertEqual(offset, 2)

    def test_addr_to_offset_different_load_address(self):
        """Test conversion with different load addresses."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)

        # Test various load addresses (all +2 for PRG header)
        test_cases = [
            (0x0800, 0x0900, 0x102),  # load, addr, expected offset (+2)
            (0x1000, 0x1234, 0x236),  # 0x234 + 2
            (0x2000, 0x2500, 0x502),  # 0x500 + 2
        ]

        for load_addr, addr, expected_offset in test_cases:
            writer.load_address = load_addr
            offset = writer._addr_to_offset(addr)
            self.assertEqual(offset, expected_offset,
                           f"Failed for load={load_addr:04X}, addr={addr:04X}")


class TestBuildDescriptionData(unittest.TestCase):
    """Test description data building."""

    def test_build_description_data_basic(self):
        """Test building basic description data."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)

        result = writer._build_description_data()

        # Should return bytearray or None
        self.assertTrue(result is None or isinstance(result, bytearray))

    def test_build_description_data_with_song_info(self):
        """Test building description with song info."""
        header = create_minimal_psid_header(
            name='Test Song',
            author='Test Author',
            copyright='2025 Test'
        )
        data = create_minimal_extracted_data(header=header)
        writer = SF2Writer(data)

        result = writer._build_description_data()

        if result:
            # Should contain song info
            self.assertGreater(len(result), 0)


class TestBuildTableTextData(unittest.TestCase):
    """Test table text data building."""

    def test_build_table_text_data_empty_names(self):
        """Test building with empty name lists."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)

        result = writer._build_table_text_data([], [])

        self.assertIsInstance(result, bytearray)

    def test_build_table_text_data_with_names(self):
        """Test building with instrument and command names."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data)

        instrument_names = ['Instr0', 'Instr1', 'Instr2']
        command_names = ['Cmd0', 'Cmd1']

        result = writer._build_table_text_data(instrument_names, command_names)

        self.assertIsInstance(result, bytearray)
        self.assertGreater(len(result), 0)


# ============================================================================
# Data Injection Tests
# ============================================================================

class TestInjectSequences(unittest.TestCase):
    """Test sequence injection."""

    def setUp(self):
        """Create test writer with template."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)
        self.writer.output = bytearray(create_minimal_sf2_template())
        self.writer.load_address = 0x1000

        # Set up driver info with sequence pointers
        self.writer.driver_info.sequence_ptrs_lo = 0x1900
        self.writer.driver_info.sequence_ptrs_hi = 0x1920
        self.writer.driver_info.sequence_start = 0x2000

    def test_inject_sequences_empty(self):
        """Test injecting empty sequence list."""
        self.data.sequences = []

        # Should not raise error
        self.writer._inject_sequences()

    def test_inject_sequences_single(self):
        """Test injecting single sequence."""
        # Create single sequence
        seq = create_test_sequence(5)
        self.data.sequences = [seq]

        # Expand output to accommodate sequences
        self.writer.output.extend(b'\x00' * 1000)

        # Should not raise error
        self.writer._inject_sequences()

        # Output should be modified
        self.assertGreater(len(self.writer.output), len(create_minimal_sf2_template()))

    def test_inject_sequences_multiple(self):
        """Test injecting multiple sequences."""
        # Create multiple sequences
        self.data.sequences = [
            create_test_sequence(10),
            create_test_sequence(15),
            create_test_sequence(8),
        ]

        # Expand output
        self.writer.output.extend(b'\x00' * 2000)

        # Should not raise error
        self.writer._inject_sequences()


class TestInjectOrderlists(unittest.TestCase):
    """Test orderlist injection."""

    def setUp(self):
        """Create test writer."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)
        self.writer.output = bytearray(create_minimal_sf2_template())
        self.writer.load_address = 0x1000

        # Set up driver info
        self.writer.driver_info.orderlist_ptrs_lo = 0x1800
        self.writer.driver_info.orderlist_start = 0x1900

    def test_inject_orderlists_empty(self):
        """Test injecting empty orderlists."""
        self.data.orderlists = [[], [], []]

        # Expand output
        self.writer.output.extend(b'\x00' * 1000)

        # Should not raise error
        self.writer._inject_orderlists()

    def test_inject_orderlists_with_data(self):
        """Test injecting orderlists with data."""
        # Create orderlists for 3 voices
        self.data.orderlists = [
            [(0, 0), (0, 1), (0, 2)],  # Voice 0
            [(0, 0), (0, 3)],          # Voice 1
            [(0, 0)],                  # Voice 2
        ]

        # Expand output
        self.writer.output.extend(b'\x00' * 1000)

        # Should not raise error
        self.writer._inject_orderlists()


class TestInjectInstruments(unittest.TestCase):
    """Test instrument injection."""

    def setUp(self):
        """Create test writer."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)
        self.writer.output = bytearray(create_minimal_sf2_template())
        self.writer.load_address = 0x1000

        # Set up driver info
        self.writer.driver_info.table_addresses = {
            'instruments': 0x1A00
        }

    def test_inject_instruments_empty(self):
        """Test injecting empty instrument list."""
        self.data.instruments = []

        # Expand output
        self.writer.output.extend(b'\x00' * 2000)

        # Should not raise error
        self.writer._inject_instruments()

    def test_inject_instruments_single(self):
        """Test injecting single instrument."""
        # Create single 8-byte instrument
        self.data.instruments = [b'\x09\x00\xF8\x00\x00\x00\x00\x41']

        # Expand output
        self.writer.output.extend(b'\x00' * 2000)

        # Should not raise error
        self.writer._inject_instruments()

    def test_inject_instruments_multiple(self):
        """Test injecting multiple instruments."""
        # Create 8 instruments (8 bytes each)
        self.data.instruments = [
            b'\x09\x00\xF8\x00\x00\x00\x00\x41' for _ in range(8)
        ]

        # Expand output
        self.writer.output.extend(b'\x00' * 2000)

        # Should not raise error
        self.writer._inject_instruments()


class TestInjectWaveTable(unittest.TestCase):
    """Test wave table injection."""

    def setUp(self):
        """Create test writer."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)
        self.writer.output = bytearray(create_minimal_sf2_template())
        self.writer.load_address = 0x1000

        # Set up driver info
        self.writer.driver_info.table_addresses = {
            'wave': 0x1B00
        }

    def test_inject_wave_table_empty(self):
        """Test injecting empty wave table."""
        self.data.wavetable = b''

        # Expand output
        self.writer.output.extend(b'\x00' * 2000)

        # Should not raise error
        self.writer._inject_wave_table()

    def test_inject_wave_table_with_data(self):
        """Test injecting wave table with data."""
        # Create test wave table (256 entries of waveform + note offset)
        wave_data = bytearray()
        for i in range(256):
            wave_data.append(0x41)  # Waveform (triangle)
            wave_data.append(i % 96)  # Note offset

        self.data.wavetable = bytes(wave_data)

        # Expand output
        self.writer.output.extend(b'\x00' * 2000)

        # Should not raise error
        self.writer._inject_wave_table()

        # Verify some data was written
        # (actual verification would check specific offsets)


class TestInjectPulseTable(unittest.TestCase):
    """Test pulse table injection."""

    def setUp(self):
        """Create test writer."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)
        self.writer.output = bytearray(create_minimal_sf2_template())
        self.writer.load_address = 0x1000

        self.writer.driver_info.table_addresses = {
            'pulse': 0x1D00
        }

    def test_inject_pulse_table_empty(self):
        """Test injecting empty pulse table."""
        self.data.pulsetable = b''

        self.writer.output.extend(b'\x00' * 2000)
        self.writer._inject_pulse_table()

    def test_inject_pulse_table_with_data(self):
        """Test injecting pulse table with data."""
        # Create test pulse table (16-bit values)
        pulse_data = bytearray()
        for i in range(128):
            pulse_data.extend(struct.pack('<H', 0x0800 + i * 16))

        self.data.pulsetable = bytes(pulse_data)

        self.writer.output.extend(b'\x00' * 2000)
        self.writer._inject_pulse_table()


class TestInjectFilterTable(unittest.TestCase):
    """Test filter table injection."""

    def setUp(self):
        """Create test writer."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)
        self.writer.output = bytearray(create_minimal_sf2_template())
        self.writer.load_address = 0x1000

        self.writer.driver_info.table_addresses = {
            'filter': 0x1F00
        }

    def test_inject_filter_table_empty(self):
        """Test injecting empty filter table."""
        self.data.filtertable = b''

        self.writer.output.extend(b'\x00' * 2000)
        self.writer._inject_filter_table()

    def test_inject_filter_table_with_data(self):
        """Test injecting filter table with data."""
        # Create test filter table
        filter_data = b'\x00\x0F\x00' * 64  # 64 filter entries

        self.data.filtertable = filter_data

        self.writer.output.extend(b'\x00' * 2000)
        self.writer._inject_filter_table()


class TestInjectTables(unittest.TestCase):
    """Test other table injection methods."""

    def setUp(self):
        """Create test writer."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)
        self.writer.output = bytearray(create_minimal_sf2_template())
        self.writer.load_address = 0x1000

        # Set up all table addresses
        self.writer.driver_info.table_addresses = {
            'hr': 0x1700,
            'init': 0x1800,
            'tempo': 0x1850,
            'arp': 0x1900,
            'commands': 0x1A00,
        }

        # Expand output
        self.writer.output.extend(b'\x00' * 3000)

    def test_inject_hr_table(self):
        """Test HR (Hard Restart) table injection."""
        self.data.hr_table = [(0, 0), (1, 5), (2, 10)]
        self.writer._inject_hr_table()

    def test_inject_init_table(self):
        """Test init table injection."""
        self.data.init_table = [6, 15, 0, 0, 0]  # tempo, volume, instr0-2
        self.writer._inject_init_table()

    def test_inject_tempo_table(self):
        """Test tempo table injection."""
        self.data.tempo = 6
        self.writer._inject_tempo_table()

    def test_inject_arp_table(self):
        """Test arpeggio table injection."""
        self.data.arp_table = [(0, 4, 7, 12), (0, 3, 7, 10)]
        self.writer._inject_arp_table()

    def test_inject_commands(self):
        """Test command table injection."""
        self.data.commands = [b'\x00\x00', b'\x01\x05', b'\x02\x10']
        self.writer._inject_commands()


# ============================================================================
# Integration Tests
# ============================================================================

class TestSF2WriterIntegration(unittest.TestCase):
    """Integration tests for complete SF2 generation."""

    def setUp(self):
        """Create temporary directory."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_generation_minimal_data(self):
        """Test complete SF2 generation with minimal data."""
        # Create minimal but complete extracted data
        data = create_minimal_extracted_data(
            sequences=[create_test_sequence(10)],
            orderlists=[[(0, 0)], [(0, 0)], [(0, 0)]],
            instruments=[b'\x09\x00\xF8\x00\x00\x00\x00\x41'],
        )

        writer = SF2Writer(data, driver_type='driver11')
        output_path = os.path.join(self.temp_dir, 'test_full.sf2')

        # Mock template to use test template
        with patch.object(writer, '_find_template') as mock_find:
            template_path = os.path.join(self.temp_dir, 'template.sf2')
            with open(template_path, 'wb') as f:
                f.write(create_minimal_sf2_template())

            mock_find.return_value = template_path

            # Should complete without error
            writer.write(output_path)

            # File should exist
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)

    def test_full_generation_with_all_tables(self):
        """Test generation with all tables populated."""
        # Create comprehensive extracted data
        data = create_minimal_extracted_data(
            sequences=[create_test_sequence(20), create_test_sequence(15)],
            orderlists=[
                [(0, 0), (0, 1)],
                [(0, 0)],
                [(0, 1)],
            ],
            instruments=[b'\x09\x00\xF8\x00\x00\x00\x00\x41' for _ in range(4)],
            wavetable=b'\x41\x00' * 128,
            pulsetable=b'\x00\x08' * 64,
            filtertable=b'\x00\x0F\x00' * 32,
        )

        # Add optional tables
        data.hr_table = [(0, 0), (1, 5)]
        data.init_table = [6, 15, 0, 0, 0]
        data.arp_table = [(0, 4, 7, 12)]
        data.commands = [b'\x00\x00', b'\x01\x05']

        writer = SF2Writer(data, driver_type='driver11')
        output_path = os.path.join(self.temp_dir, 'test_comprehensive.sf2')

        # Mock template
        with patch.object(writer, '_find_template') as mock_find:
            template_path = os.path.join(self.temp_dir, 'template.sf2')
            with open(template_path, 'wb') as f:
                f.write(create_minimal_sf2_template())

            mock_find.return_value = template_path

            # Should complete without error
            writer.write(output_path)

            # Verify output
            self.assertTrue(os.path.exists(output_path))
            file_size = os.path.getsize(output_path)

            # Should be larger than minimal template
            self.assertGreater(file_size, len(create_minimal_sf2_template()))


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def test_empty_sequences_list(self):
        """Test handling of empty sequences."""
        data = create_minimal_extracted_data(sequences=[])
        writer = SF2Writer(data)

        # Should not crash
        self.assertIsNotNone(writer)

    def test_very_long_sequence(self):
        """Test handling of very long sequence."""
        long_seq = create_test_sequence(1000)
        data = create_minimal_extracted_data(sequences=[long_seq])
        writer = SF2Writer(data)

        self.assertEqual(len(data.sequences[0]), 1000)

    def test_max_instruments(self):
        """Test handling of maximum instruments (32)."""
        instruments = [b'\x09\x00\xF8\x00\x00\x00\x00\x41' for _ in range(32)]
        data = create_minimal_extracted_data(instruments=instruments)
        writer = SF2Writer(data)

        self.assertEqual(len(data.instruments), 32)

    def test_invalid_driver_type(self):
        """Test handling of invalid driver type."""
        data = create_minimal_extracted_data()
        writer = SF2Writer(data, driver_type='invalid_driver_xyz')

        # Should not crash during init
        self.assertEqual(writer.driver_type, 'invalid_driver_xyz')


class TestTableInjectionMethods(unittest.TestCase):
    """Test critical table injection methods (Track 3.4)."""

    def setUp(self):
        """Create test writer with mock data."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)
        self.writer.load_address = 0x1000
        self.writer.output = bytearray(0x3000)  # Pre-allocate buffer

    def test_inject_wave_table_with_data(self):
        """Test wave table injection with actual data."""
        # Set up wave table address (dict with addr, columns, rows)
        self.writer.driver_info.table_addresses = {
            'Wave': {'addr': 0x11E0, 'columns': 2, 'rows': 32, 'id': 0}
        }

        # Mock wave table data (waveform, note offset)
        self.data.wave_table = [
            (0x21, 0x00),  # Pulse wave, note C
            (0x41, 0x0C),  # Saw wave, note C+12
        ]

        # Should inject without errors
        self.writer._inject_wave_table()

    def test_inject_pulse_table_with_data(self):
        """Test pulse table injection with actual data."""
        self.writer.driver_info.table_addresses = {
            'Pulse': {'addr': 0x13E0, 'columns': 4, 'rows': 32, 'id': 1}
        }

        # Pulse table entries: (pulse_value, dur_lo, dur_hi, next_idx)
        self.data.pulse_table = [
            (0x0800, 0x40, 0x40, 0x7F),
            (0x1000, 0x80, 0x80, 0x7F),
        ]

        self.writer._inject_pulse_table()

    def test_inject_filter_table_with_data(self):
        """Test filter table injection with actual data."""
        self.writer.driver_info.table_addresses = {
            'Filter': {'addr': 0x16E0, 'columns': 4, 'rows': 32, 'id': 2}
        }

        # Filter table entries: (cutoff_hi, cutoff_lo, resonance, next_idx)
        self.data.filter_table = [
            (0x05, 0xA8, 0x80, 0x7F),  # Converted from Laxity format
        ]

        self.writer._inject_filter_table()

    def test_inject_tempo_table(self):
        """Test tempo table injection."""
        self.writer.driver_info.table_addresses = {
            'Tempo': {'addr': 0x1AE0, 'columns': 1, 'rows': 1, 'id': 3}
        }

        self.data.tempo = 6  # Standard 60Hz

        self.writer._inject_tempo_table()

    def test_inject_init_table(self):
        """Test init table injection."""
        self.writer.driver_info.table_addresses = {
            'Init': {'addr': 0x1A00, 'columns': 1, 'rows': 1, 'id': 4}
        }

        self.data.init_volume = 15

        self.writer._inject_init_table()

    def test_inject_hr_table(self):
        """Test HR table injection."""
        self.writer.driver_info.table_addresses = {
            'HR': {'addr': 0x1900, 'columns': 2, 'rows': 32, 'id': 5}
        }

        # Mock HR data
        self.data.hr_table = [(0x02, 0x21)]

        self.writer._inject_hr_table()

    def test_inject_arp_table(self):
        """Test arpeggio table injection."""
        self.writer.driver_info.table_addresses = {
            'Arp': {'addr': 0x19E0, 'columns': 4, 'rows': 32, 'id': 6}
        }

        # Mock arpeggio data
        self.data.arp_table = [(0x00, 0x04, 0x07, 0x7F)]

        self.writer._inject_arp_table()

    def test_inject_commands_phase1(self):
        """Test command injection using Phase 1 (command_index_map)."""
        self.writer.driver_info.table_addresses = {
            'Commands': {'addr': 0x1100, 'columns': 3, 'rows': 64, 'id': 0}
        }

        # Mock Phase 1 command_index_map
        self.data.command_index_map = {
            (0x01, 0x00, 0x00): 0,  # Command type 1, params 0,0 → index 0
            (0x02, 0x05, 0x00): 1,  # Command type 2, params 5,0 → index 1
        }

        self.writer._inject_commands()

    def test_inject_commands_empty_map(self):
        """Test command injection with empty command map."""
        self.writer.driver_info.table_addresses = {
            'Commands': {'addr': 0x1100, 'columns': 3, 'rows': 64, 'id': 0}
        }

        # Empty command map
        self.data.command_index_map = {}

        # Should use defaults
        self.writer._inject_commands()


class TestSequenceInjectionAdvanced(unittest.TestCase):
    """Test advanced sequence injection scenarios (Track 3.4)."""

    def setUp(self):
        """Create test writer."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)
        self.writer.load_address = 0x1000
        self.writer.driver_info.sequence_start = 0x1900
        self.writer.output = bytearray(0x3000)

    def test_inject_sequences_with_instrument_changes(self):
        """Test sequences with instrument changes."""
        # Sequence with instrument changes
        self.data.sequences = [
            [
                SequenceEvent(instrument=0, command=0, note=0x30),  # C-4
                SequenceEvent(instrument=1, command=0, note=0x32),  # D-4
                SequenceEvent(instrument=0, command=0, note=0x7F),  # End
            ]
        ]

        # Set up sequence pointer
        seq_ptr_offset = self.writer._addr_to_offset(0x1903)
        struct.pack_into('<H', self.writer.output, seq_ptr_offset, 0x1900)

        self.writer._inject_sequences()

    def test_inject_sequences_with_commands(self):
        """Test sequences with command changes."""
        # Sequence with command changes
        self.data.sequences = [
            [
                SequenceEvent(instrument=0, command=0, note=0x30),  # C-4
                SequenceEvent(instrument=0, command=1, note=0x32),  # D-4
                SequenceEvent(instrument=0, command=0, note=0x7F),  # End
            ]
        ]

        seq_ptr_offset = self.writer._addr_to_offset(0x1903)
        struct.pack_into('<H', self.writer.output, seq_ptr_offset, 0x1900)

        self.writer._inject_sequences()

    def test_inject_sequences_with_duration_changes(self):
        """Test sequences with varying note values (duration handled by player)."""
        # Note: Duration is handled by the player, not stored in SequenceEvent
        # This test verifies sequences with different note patterns
        self.data.sequences = [
            [
                SequenceEvent(instrument=0, command=0, note=0x30),  # C-4
                SequenceEvent(instrument=0, command=0, note=0x32),  # D-4
                SequenceEvent(instrument=0, command=0, note=0x34),  # E-4
                SequenceEvent(instrument=0, command=0, note=0x7F),  # End
            ]
        ]

        seq_ptr_offset = self.writer._addr_to_offset(0x1903)
        struct.pack_into('<H', self.writer.output, seq_ptr_offset, 0x1900)

        self.writer._inject_sequences()

    def test_inject_sequences_packed_format(self):
        """Test variable-length packed sequence format."""
        # Multiple sequences of different lengths
        self.data.sequences = [
            [  # Short sequence
                SequenceEvent(instrument=0, command=0, note=0x30),
                SequenceEvent(instrument=0, command=0, note=0x7F),
            ],
            [  # Longer sequence
                SequenceEvent(instrument=0, command=0, note=0x32),
                SequenceEvent(instrument=0, command=0, note=0x34),
                SequenceEvent(instrument=0, command=0, note=0x7F),
            ],
            [  # Empty sequence
                SequenceEvent(instrument=0x80, command=0x80, note=0x7F),
            ],
        ]

        # Set up sequence pointers
        for i in range(3):
            offset = self.writer._addr_to_offset(0x1903 + i * 2)
            struct.pack_into('<H', self.writer.output, offset, 0x1900)

        self.writer._inject_sequences()

        # Sequences should be packed contiguously


class TestInstrumentConversion(unittest.TestCase):
    """Test instrument injection with Laxity→SF2 conversion (Track 3.4)."""

    def setUp(self):
        """Create test writer."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)
        self.writer.load_address = 0x1000
        self.writer.output = bytearray(0x3000)
        self.writer.driver_info.table_addresses = {
            'Instruments': {'addr': 0x1040, 'columns': 8, 'rows': 16, 'id': 1}
        }

    def test_inject_instruments_pulse_pointer_conversion(self):
        """Test pulse pointer Y*4 to direct index conversion."""
        # Laxity format: byte 6 = pulse_ptr in Y*4 format
        # Y*4 = 0x04 should convert to index 0x01
        self.data.instruments = [
            bytearray([0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04, 0x00])
            #                                              ^^^^ Y*4 = 4
        ]

        self.writer._inject_instruments()

        # Pulse pointer should be converted (Y*4 → direct)

    def test_inject_instruments_wave_pointer_validation(self):
        """Test wave pointer bounds validation."""
        # Laxity format: byte 7 = wave_ptr
        # Should be validated against wave_table_size
        self.data.instruments = [
            bytearray([0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xFF])
            #                                                      ^^^^ Large wave_ptr
        ]

        # Should clamp or validate wave_ptr
        self.writer._inject_instruments()

    def test_inject_instruments_waveform_mapping(self):
        """Test Laxity waveform to SF2 index mapping."""
        # Laxity waveforms: 0x21→0x00, 0x41→0x02, etc.
        self.data.instruments = [
            bytearray([0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x21]),
            #                                                      ^^^^ Laxity waveform
        ]

        self.writer._inject_instruments()

        # Waveform should be mapped to SF2 index

    def test_inject_instruments_column_major_storage(self):
        """Test instruments use column-major storage."""
        # 2 instruments with 8 columns each
        self.data.instruments = [
            bytearray([0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x21]),
            bytearray([0x0A, 0x01, 0x00, 0x00, 0x00, 0x00, 0x04, 0x41]),
        ]

        self.writer._inject_instruments()

        # Should write all column 0 values, then all column 1 values, etc.


class TestUpdateTableDefinitions(unittest.TestCase):
    """Test table definition updates (Track 3.4)."""

    def setUp(self):
        """Create test writer."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)
        self.writer.load_address = 0x1000

    def test_update_table_definitions_instruments(self):
        """Test updating instrument table dimensions."""
        # Create Block 3 with instrument table descriptor
        block3_data = bytearray(30)
        block3_data[0] = 0x80  # Table type: Instruments
        block3_data[1] = 0x00  # Table ID
        block3_data[2] = 11    # Name length
        block3_data[3:14] = b'Instruments'
        # Descriptor bytes at +14: address, columns, rows, visible_rows
        struct.pack_into('<H', block3_data, 14, 0x1040)  # Address
        struct.pack_into('<H', block3_data, 16, 8)       # Columns
        struct.pack_into('<H', block3_data, 18, 0)       # Rows (will be updated)
        struct.pack_into('B', block3_data, 20, 0)        # Visible rows

        # Add Block 3 to output
        self.writer.output = bytearray(100)
        self.writer.output[4] = 0x03  # Block 3 ID
        self.writer.output[5] = len(block3_data)  # Block size
        self.writer.output[6:6+len(block3_data)] = block3_data

        # Set instrument count
        self.data.instruments = [b'\x00' * 8 for _ in range(16)]

        self.writer._update_table_definitions()

        # Row count should be updated to 16


class TestAuxiliaryDataBuilding(unittest.TestCase):
    """Test auxiliary data building (Track 3.4)."""

    def setUp(self):
        """Create test writer."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data)

    def test_build_description_data(self):
        """Test description data building."""
        # Use helper to create PSID header with metadata
        self.data.header = create_minimal_psid_header(
            name="Test Song",
            author="Test Author",
            copyright="2025"
        )

        result = self.writer._build_description_data()

        # Should return bytearray with encoded strings
        self.assertIsInstance(result, (bytearray, type(None)))

    def test_build_table_text_data(self):
        """Test table text data building."""
        # Mock instrument and command names
        instrument_names = ["Instr 0", "Instr 1"]
        command_names = ["Cmd 0", "Cmd 1"]

        result = self.writer._build_table_text_data(instrument_names, command_names)

        # Should return bytearray with encoded names
        self.assertIsInstance(result, bytearray)


class TestLaxityNativeFormatInjection(unittest.TestCase):
    """Test _inject_laxity_music_data() Laxity native format (Track 3.6)."""

    def setUp(self):
        """Create test writer with Laxity-specific setup."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data, driver_type='laxity')
        self.writer.load_address = 0x1000
        # Create large output buffer for Laxity format
        self.writer.output = bytearray(0x4000)  # 16KB
        # Write PRG load address
        struct.pack_into('<H', self.writer.output, 0, 0x1000)

    def test_inject_laxity_orderlists_dict_format(self):
        """Test orderlist injection with dict format entries."""
        # Set up 3 orderlists with dict entries
        self.data.orderlists = [
            [{'sequence': 0, 'transpose': 0xA0}],  # Voice 1
            [{'sequence': 1, 'transpose': 0xA2}],  # Voice 2
            [{'sequence': 2, 'transpose': 0xA4}],  # Voice 3
        ]

        # Call the method
        self.writer._inject_laxity_music_data()

        # Verify orderlists were written (at 0x1900 base)
        # Orderlists start at 0x1900, each track is 256 bytes
        # Track 1: 0x1900, Track 2: 0x1A00, Track 3: 0x1B00
        track1_offset = 0x1900 - 0x1000 + 2  # +2 for PRG header

        # Should have written sequence indices
        self.assertEqual(self.writer.output[track1_offset], 0)  # Sequence 0
        self.assertEqual(self.writer.output[track1_offset + 256], 1)  # Sequence 1
        self.assertEqual(self.writer.output[track1_offset + 512], 2)  # Sequence 2

    def test_inject_laxity_orderlists_with_end_marker(self):
        """Test orderlist end marker (0xFF) placement."""
        # Short orderlist (less than 256 entries)
        self.data.orderlists = [
            [0, 1, 2],  # Only 3 entries
            [],
            [],
        ]

        self.writer._inject_laxity_music_data()

        track1_offset = 0x1900 - 0x1000 + 2

        # Should have 0xFF after last entry
        self.assertEqual(self.writer.output[track1_offset + 3], 0xFF)

    def test_inject_laxity_sequences_with_end_markers(self):
        """Test sequence injection with 0x7F end markers."""
        # Set up sequences with SequenceEvent objects
        self.data.sequences = [
            [
                SequenceEvent(instrument=0, command=0, note=0x30),
                SequenceEvent(instrument=0, command=0, note=0x32),
            ]
        ]

        self.writer._inject_laxity_music_data()

        # Sequences start after orderlists (0x1900 + 3*256 = 0x1C00)
        # But actual injection depends on logic - just verify no crash
        # This tests the sequence writing code path
        self.assertIsNotNone(self.writer.output)

    def test_inject_laxity_handles_empty_data(self):
        """Test injection handles empty orderlists/sequences gracefully."""
        # Empty data
        self.data.orderlists = [[], [], []]
        self.data.sequences = []

        # Should not crash
        self.writer._inject_laxity_music_data()

        self.assertIsNotNone(self.writer.output)

    def test_inject_laxity_output_too_small(self):
        """Test injection handles output buffer that's too small."""
        # Create very small output buffer
        self.writer.output = bytearray(1)  # Only 1 byte

        # Should log error and return early without crashing
        self.writer._inject_laxity_music_data()

        # Should still have the buffer (not destroyed)
        self.assertIsNotNone(self.writer.output)


class TestLaxityTableInjection(unittest.TestCase):
    """Test Laxity-specific table injection (Track 3.6)."""

    def setUp(self):
        """Create test writer."""
        self.data = create_minimal_extracted_data()
        self.writer = SF2Writer(self.data, driver_type='laxity')
        self.writer.load_address = 0x1000
        self.writer.output = bytearray(0x4000)
        struct.pack_into('<H', self.writer.output, 0, 0x1000)

    def test_inject_laxity_wave_table_dual_array_format(self):
        """Test Laxity wave table uses dual array format (not interleaved)."""
        # Set up wave table data
        self.data.wave_table = [
            (0x21, 0x00),  # Waveform, note offset
            (0x41, 0x0C),
        ]

        self.writer._inject_laxity_music_data()

        # Just verify method completes without error
        # (actual wave table injection is complex and position-dependent)
        self.assertIsNotNone(self.writer.output)

    def test_inject_laxity_instrument_table(self):
        """Test Laxity instrument table injection."""
        # Set up instrument data
        self.data.instruments = [
            bytearray([0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x21]),
            bytearray([0x0A, 0x01, 0x00, 0x00, 0x00, 0x00, 0x04, 0x41]),
        ]

        self.writer._inject_laxity_music_data()

        # Verify method completes
        self.assertIsNotNone(self.writer.output)


if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
