"""
Test suite for Laxity driver components (v2.5.3).

Tests the Laxity driver system including:
- LaxityParser (sequence/instrument/command extraction)
- LaxityPlayerAnalyzer (table extraction, tempo/volume detection)
- LaxityConverter (table injection, driver integration)

Version: 1.0.0
"""

import unittest
import os
import sys
import struct
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sidm2.laxity_parser import LaxityParser, LaxityData
from sidm2.laxity_analyzer import LaxityPlayerAnalyzer
from sidm2.laxity_converter import LaxityConverter
from sidm2.models import PSIDHeader


class TestLaxityParser(unittest.TestCase):
    """Test LaxityParser for sequence/instrument/command extraction"""

    def setUp(self):
        """Create test data"""
        self.load_address = 0x1000
        # Create minimal valid Laxity data with sequence pointers
        self.data = bytearray(0x2000)

        # Set up sequence pointer table at $199F (offset $099F from $1000)
        # Voice 0: sequence at $1B00
        self.data[0x099F] = 0x00
        self.data[0x09A0] = 0x1B
        # Voice 1: sequence at $1B20
        self.data[0x09A1] = 0x20
        self.data[0x09A2] = 0x1B
        # Voice 2: sequence at $1B40
        self.data[0x09A3] = 0x40
        self.data[0x09A4] = 0x1B

        # Add simple sequences (note $24, end marker $7F)
        self.data[0x0B00] = 0x24  # Note
        self.data[0x0B01] = 0x7F  # End
        self.data[0x0B20] = 0x30  # Note
        self.data[0x0B21] = 0x7F  # End
        self.data[0x0B40] = 0x3C  # Note
        self.data[0x0B41] = 0x7F  # End

        # Add instrument table at $1A6B (offset $0A6B from $1000)
        # Column-major format: 8 instruments × 8 bytes
        for i in range(8):
            # AD values (column 0)
            self.data[0x0A6B + i] = 0x09
            # SR values (column 1)
            self.data[0x0A6B + 8 + i] = 0x00
            # Pulse pointers (column 2)
            self.data[0x0A6B + 16 + i] = 0x00
            # Filter bytes (column 3)
            self.data[0x0A6B + 24 + i] = 0x00
            # Unused (columns 4-6)
            # Wave table pointers (column 7)
            self.data[0x0A6B + 56 + i] = 0x00

        # Add command table at $1ADB (offset $0ADB from $1000)
        self.data[0x0ADB] = 0xC0  # Command 1
        self.data[0x0ADC] = 0x10
        self.data[0x0ADD] = 0x20
        self.data[0x0ADE] = 0xC1  # Command 2
        self.data[0x0ADF] = 0x30
        self.data[0x0AE0] = 0x40
        self.data[0x0AE1] = 0x00  # End marker
        self.data[0x0AE2] = 0x00
        self.data[0x0AE3] = 0x00

    def test_parse_sequences(self):
        """Test sequence extraction"""
        parser = LaxityParser(bytes(self.data), self.load_address)
        result = parser.parse()

        self.assertIsInstance(result, LaxityData)
        self.assertEqual(len(result.sequences), 3)
        self.assertEqual(result.sequences[0], b'\x24\x7F')
        self.assertEqual(result.sequences[1], b'\x30\x7F')
        self.assertEqual(result.sequences[2], b'\x3C\x7F')

    def test_parse_orderlists(self):
        """Test orderlist extraction"""
        parser = LaxityParser(bytes(self.data), self.load_address)
        result = parser.parse()

        self.assertEqual(len(result.orderlists), 3)
        self.assertEqual(result.orderlists[0], [0])
        self.assertEqual(result.orderlists[1], [1])
        self.assertEqual(result.orderlists[2], [2])

    def test_parse_instruments(self):
        """Test instrument extraction (column-major to row-major conversion)"""
        parser = LaxityParser(bytes(self.data), self.load_address)
        result = parser.parse()

        self.assertEqual(len(result.instruments), 8)
        # Check first instrument (converted from column-major)
        instr = result.instruments[0]
        self.assertEqual(instr[0], 0x09)  # AD
        self.assertEqual(instr[1], 0x00)  # SR

    def test_parse_commands(self):
        """Test command table extraction"""
        parser = LaxityParser(bytes(self.data), self.load_address)
        result = parser.parse()

        self.assertEqual(len(result.command_table), 2)
        self.assertEqual(result.command_table[0], b'\xC0\x10\x20')
        self.assertEqual(result.command_table[1], b'\xC1\x30\x40')

    def test_sequence_extraction_strategies(self):
        """Test multiple sequence address resolution strategies"""
        # Test with address outside loaded data range
        data = bytearray(0x2000)
        data[0x099F] = 0x00  # Sequence at $2000 (outside range)
        data[0x09A0] = 0x20

        parser = LaxityParser(bytes(data), 0x1000)
        result = parser.parse()

        # Should still work with alternative strategies
        self.assertIsInstance(result, LaxityData)

    def test_empty_sequence_handling(self):
        """Test handling of empty/invalid sequences"""
        data = bytearray(0x2000)
        # Point to area with no end marker
        data[0x099F] = 0xFF
        data[0x09A0] = 0x1F

        parser = LaxityParser(bytes(data), 0x1000)
        result = parser.parse()

        # Should not crash, may have empty sequences
        self.assertIsInstance(result, LaxityData)


class TestLaxityPlayerAnalyzer(unittest.TestCase):
    """Test LaxityPlayerAnalyzer for table extraction and analysis"""

    def setUp(self):
        """Create test data with valid PSID header"""
        self.load_address = 0x1000
        self.data = bytearray(0x2000)

        # Create minimal valid PSID header
        self.header = PSIDHeader(
            magic='PSID',
            version=2,
            data_offset=124,
            load_address=self.load_address,
            init_address=self.load_address,
            play_address=self.load_address + 0xA1,
            songs=1,
            start_song=1,
            speed=0,
            name='Test Song',
            author='Test Author',
            copyright='2025'
        )

        # Add init routine with tempo and volume
        # LDA #$06, STA $xxxx (tempo = 6)
        self.data[0x0000] = 0xA9
        self.data[0x0001] = 0x06
        self.data[0x0002] = 0x8D
        # LDA #$0F, STA $D418 (volume = 15)
        self.data[0x0010] = 0xA9
        self.data[0x0011] = 0x0F
        self.data[0x0012] = 0x8D
        self.data[0x0013] = 0x18
        self.data[0x0014] = 0xD4

        # Add filter table at $1A1E (offset $0A1E)
        # 4-byte entries: (cutoff, step, duration, next)
        # Note: First 4 bytes are break speed table in Laxity format
        # Set to 0x06 to match expected tempo
        self.data[0x0A1E] = 0x06  # Break speed 0
        self.data[0x0A1F] = 0x06  # Break speed 1
        self.data[0x0A20] = 0x06  # Break speed 2
        self.data[0x0A21] = 0x06  # Break speed 3

        # Add wave table at some location
        # (waveform, note_offset) pairs
        self.data[0x0B00] = 0x41  # Pulse waveform
        self.data[0x0B01] = 0x00  # No transpose
        self.data[0x0B02] = 0x7F  # End marker

    def test_extract_tempo(self):
        """Test tempo extraction from init routine"""
        analyzer = LaxityPlayerAnalyzer(bytes(self.data), self.load_address, self.header)
        tempo = analyzer.extract_tempo()

        self.assertEqual(tempo, 6)

    def test_extract_init_volume(self):
        """Test volume extraction from init routine"""
        analyzer = LaxityPlayerAnalyzer(bytes(self.data), self.load_address, self.header)
        volume = analyzer.extract_init_volume()

        self.assertEqual(volume, 0x0F)

    def test_detect_multi_speed(self):
        """Test multi-speed detection"""
        analyzer = LaxityPlayerAnalyzer(bytes(self.data), self.load_address, self.header)
        multi_speed = analyzer.detect_multi_speed()

        # Should default to 1 for normal speed
        self.assertEqual(multi_speed, 1)

    def test_extract_filter_table(self):
        """Test filter table extraction"""
        analyzer = LaxityPlayerAnalyzer(bytes(self.data), self.load_address, self.header)
        filter_data, filter_addr = analyzer.extract_filter_table()

        # Should extract filter data
        self.assertIsInstance(filter_data, bytes)

    def test_extract_wave_table(self):
        """Test wave table extraction"""
        analyzer = LaxityPlayerAnalyzer(bytes(self.data), self.load_address, self.header)
        wave_data, wave_addr = analyzer.extract_wave_table()

        # Should return wave data or empty
        self.assertIsInstance(wave_data, bytes)

    def test_get_byte_word_methods(self):
        """Test memory access methods"""
        analyzer = LaxityPlayerAnalyzer(bytes(self.data), self.load_address, self.header)

        # Test get_byte
        byte_val = analyzer.get_byte(self.load_address)
        self.assertEqual(byte_val, self.data[0])

        # Test get_word (little-endian)
        self.data[0x0100] = 0x34
        self.data[0x0101] = 0x12
        analyzer = LaxityPlayerAnalyzer(bytes(self.data), self.load_address, self.header)
        word_val = analyzer.get_word(self.load_address + 0x0100)
        self.assertEqual(word_val, 0x1234)

    def test_find_data_tables(self):
        """Test data table discovery"""
        analyzer = LaxityPlayerAnalyzer(bytes(self.data), self.load_address, self.header)
        tables = analyzer.find_data_tables()

        self.assertIsInstance(tables, dict)

    def test_extract_music_data_integration(self):
        """Test complete music data extraction"""
        # Create more complete test data
        data = bytearray(0x2000)

        # Add sequence pointers at $199F
        data[0x099F] = 0x00
        data[0x09A0] = 0x1B
        data[0x0B00] = 0x24  # Simple sequence
        data[0x0B01] = 0x7F

        # Add instrument table
        for i in range(8):
            data[0x0A6B + i] = 0x09
            data[0x0A6B + 8 + i] = 0x00

        analyzer = LaxityPlayerAnalyzer(bytes(data), self.load_address, self.header)
        extracted = analyzer.extract_music_data()

        # Should have extracted data structure
        self.assertIsNotNone(extracted)
        self.assertEqual(extracted.tempo, 6)  # Default tempo


class TestLaxityConverter(unittest.TestCase):
    """Test LaxityConverter for table injection and driver integration"""

    def setUp(self):
        """Create temporary directory and mock driver"""
        self.temp_dir = tempfile.mkdtemp()
        self.driver_path = Path(self.temp_dir) / 'sf2driver_laxity_00.prg'

        # Create mock driver file
        # PRG format: 2-byte load address + driver code
        driver_data = bytearray()
        driver_data.extend(struct.pack('<H', 0x0D7E))  # Load address
        driver_data.extend([0xA9, 0x00, 0x60] * 100)  # Some code

        with open(self.driver_path, 'wb') as f:
            f.write(driver_data)

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_load_driver(self):
        """Test driver loading"""
        # Temporarily override DRIVER_PATH
        converter = LaxityConverter()
        original_path = converter.DRIVER_PATH
        converter.DRIVER_PATH = self.driver_path

        try:
            converter.load_driver()
            self.assertIsNotNone(converter.driver)
            self.assertGreater(len(converter.driver), 0)
        finally:
            converter.DRIVER_PATH = original_path

    def test_load_driver_missing_file(self):
        """Test error handling for missing driver"""
        converter = LaxityConverter()
        converter.DRIVER_PATH = Path(self.temp_dir) / 'nonexistent.prg'

        with self.assertRaises(FileNotFoundError):
            converter.load_driver()

    def test_inject_tables(self):
        """Test table injection into driver"""
        converter = LaxityConverter()
        converter.driver = bytearray(0x2000)

        # Create some Laxity music data
        laxity_data = bytearray()
        laxity_data.extend([0x24, 0x7F])  # Simple sequence
        laxity_data.extend([0x09, 0x00] * 8)  # Instruments

        result = converter.inject_tables(converter.driver, laxity_data)

        self.assertIsInstance(result, bytes)
        self.assertGreaterEqual(len(result), 0x1900)

        # Verify data was injected at $1900
        self.assertEqual(result[0x1900], 0x24)
        self.assertEqual(result[0x1901], 0x7F)

    def test_inject_tables_extend_driver(self):
        """Test driver extension when data is too large"""
        converter = LaxityConverter()
        converter.driver = bytearray(0x1000)  # Small driver

        # Large music data that requires extension
        laxity_data = bytearray(0x1000)
        laxity_data[0] = 0xFF

        result = converter.inject_tables(converter.driver, laxity_data)

        # Should have extended driver
        self.assertGreaterEqual(len(result), 0x1900 + len(laxity_data))

    def test_memory_layout_validation(self):
        """Test memory layout constants"""
        converter = LaxityConverter()

        # Verify memory layout addresses
        self.assertEqual(converter.SEQUENCE_ADDR, 0x1900)
        self.assertEqual(converter.INSTRUMENTS_ADDR, 0x1A6B)
        self.assertEqual(converter.WAVE_ADDR, 0x1ACB)
        self.assertEqual(converter.PULSE_ADDR, 0x1A3B)
        self.assertEqual(converter.FILTER_ADDR, 0x1A1E)


class TestLaxityEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""

    def test_parser_max_sequence_length(self):
        """Test sequence length limit enforcement"""
        data = bytearray(0x2000)
        # Create sequence without end marker (should truncate at 10000 bytes)
        data[0x099F] = 0x00
        data[0x09A0] = 0x1B
        for i in range(0x0B00, min(0x0B00 + 11000, len(data))):
            data[i] = 0x24  # Fill with notes (no end marker)

        parser = LaxityParser(bytes(data), 0x1000)
        result = parser.parse()

        # Should handle gracefully (may have empty sequences or truncated)
        self.assertIsInstance(result, LaxityData)

    def test_analyzer_boundary_addresses(self):
        """Test handling of boundary memory addresses"""
        data = bytearray(0x2000)
        header = PSIDHeader(
            magic='PSID', version=2, data_offset=124,
            load_address=0xFE00,  # High load address
            init_address=0xFE00, play_address=0xFEA1,
            songs=1, start_song=1, speed=0,
            name='Test', author='Test', copyright='2025'
        )

        analyzer = LaxityPlayerAnalyzer(bytes(data), 0xFE00, header)

        # Should handle gracefully
        tempo = analyzer.extract_tempo()
        self.assertIsInstance(tempo, int)

    def test_converter_empty_music_data(self):
        """Test table injection with empty music data"""
        converter = LaxityConverter()
        converter.driver = bytearray(0x2000)

        result = converter.inject_tables(converter.driver, bytearray())

        # Should handle empty data gracefully
        self.assertIsInstance(result, bytes)

    def test_parser_column_major_conversion(self):
        """Test column-major to row-major instrument conversion"""
        data = bytearray(0x2000)

        # Set up column-major instrument table
        # 8 instruments, 8 bytes each, stored column-major
        instr_offset = 0x0A6B

        # Column 0 (AD values): 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10
        for i in range(8):
            data[instr_offset + i] = 0x09 + i

        # Column 1 (SR values): 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27
        for i in range(8):
            data[instr_offset + 8 + i] = 0x20 + i

        parser = LaxityParser(bytes(data), 0x1000)
        result = parser.parse()

        # Verify conversion to row-major
        self.assertEqual(len(result.instruments), 8)
        # First instrument should be [0x09, 0x20, ...]
        self.assertEqual(result.instruments[0][0], 0x09)
        self.assertEqual(result.instruments[0][1], 0x20)
        # Second instrument should be [0x0A, 0x21, ...]
        self.assertEqual(result.instruments[1][0], 0x0A)
        self.assertEqual(result.instruments[1][1], 0x21)


def run_tests():
    """Run all Laxity driver tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLaxityParser))
    suite.addTests(loader.loadTestsFromTestCase(TestLaxityPlayerAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestLaxityConverter))
    suite.addTests(loader.loadTestsFromTestCase(TestLaxityEdgeCases))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
