#!/usr/bin/env python3
"""
Tests for the SID to SF2 converter
"""

import unittest
import os
import tempfile
import struct
from sid_to_sf2 import (
    SIDParser, PSIDHeader, LaxityPlayerAnalyzer, SF2Writer,
    ExtractedData, SequenceEvent
)


class TestSIDParser(unittest.TestCase):
    """Tests for SID file parsing"""

    def setUp(self):
        """Create a test SID file"""
        self.test_dir = tempfile.mkdtemp()
        self.test_sid_path = os.path.join(self.test_dir, "test.sid")

        # Create a minimal valid PSID file
        self._create_test_sid()

    def _create_test_sid(self):
        """Create a minimal test SID file"""
        # PSID v2 header
        header = bytearray(0x7C)

        # Magic
        header[0:4] = b'PSID'

        # Version (big-endian)
        struct.pack_into('>H', header, 4, 2)

        # Data offset
        struct.pack_into('>H', header, 6, 0x7C)

        # Load address (0 = embedded in data)
        struct.pack_into('>H', header, 8, 0)

        # Init address
        struct.pack_into('>H', header, 10, 0x1000)

        # Play address
        struct.pack_into('>H', header, 12, 0x1003)

        # Number of songs
        struct.pack_into('>H', header, 14, 1)

        # Start song
        struct.pack_into('>H', header, 16, 1)

        # Speed
        struct.pack_into('>I', header, 18, 0)

        # Name (32 bytes)
        name = b'Test Song'
        header[22:22 + len(name)] = name

        # Author (32 bytes)
        author = b'Test Author'
        header[54:54 + len(author)] = author

        # Copyright (32 bytes)
        copyright = b'2024 Test'
        header[86:86 + len(copyright)] = copyright

        # C64 data with embedded load address
        c64_data = bytearray()
        c64_data.extend(struct.pack('<H', 0x1000))  # Load at $1000

        # Add some test code
        # JMP $1040 (init)
        c64_data.extend([0x4C, 0x40, 0x10])
        # JMP $10C6 (play)
        c64_data.extend([0x4C, 0xC6, 0x10])

        # Pad to make room for init and play
        while len(c64_data) < 0x42:
            c64_data.append(0xEA)  # NOP

        # Init routine at $1040
        c64_data.extend([0xA9, 0x00, 0x60])  # LDA #$00, RTS

        # Pad to play
        while len(c64_data) < 0xC8:
            c64_data.append(0xEA)

        # Play routine at $10C6
        c64_data.extend([0x60])  # RTS

        # Write file
        with open(self.test_sid_path, 'wb') as f:
            f.write(header)
            f.write(c64_data)

    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.test_sid_path):
            os.remove(self.test_sid_path)
        os.rmdir(self.test_dir)

    def test_parse_header_magic(self):
        """Test parsing PSID magic number"""
        parser = SIDParser(self.test_sid_path)
        header = parser.parse_header()
        self.assertEqual(header.magic, 'PSID')

    def test_parse_header_version(self):
        """Test parsing PSID version"""
        parser = SIDParser(self.test_sid_path)
        header = parser.parse_header()
        self.assertEqual(header.version, 2)

    def test_parse_header_addresses(self):
        """Test parsing init/play addresses"""
        parser = SIDParser(self.test_sid_path)
        header = parser.parse_header()
        self.assertEqual(header.init_address, 0x1000)
        self.assertEqual(header.play_address, 0x1003)

    def test_parse_header_metadata(self):
        """Test parsing song metadata"""
        parser = SIDParser(self.test_sid_path)
        header = parser.parse_header()
        self.assertEqual(header.name, 'Test Song')
        self.assertEqual(header.author, 'Test Author')
        self.assertEqual(header.copyright, '2024 Test')

    def test_parse_header_songs(self):
        """Test parsing song count"""
        parser = SIDParser(self.test_sid_path)
        header = parser.parse_header()
        self.assertEqual(header.songs, 1)
        self.assertEqual(header.start_song, 1)

    def test_get_c64_data_with_embedded_address(self):
        """Test extracting C64 data with embedded load address"""
        parser = SIDParser(self.test_sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        self.assertEqual(load_address, 0x1000)
        # First bytes should be JMP $1040
        self.assertEqual(c64_data[0], 0x4C)
        self.assertEqual(c64_data[1], 0x40)
        self.assertEqual(c64_data[2], 0x10)


class TestLaxityPlayerAnalyzer(unittest.TestCase):
    """Tests for Laxity player analysis"""

    def test_get_byte(self):
        """Test byte access from virtual memory"""
        data = bytes([0x4C, 0x40, 0x10, 0x4C, 0xC6, 0x10])
        header = PSIDHeader(
            magic='PSID', version=2, data_offset=0x7C,
            load_address=0x1000, init_address=0x1000, play_address=0x1003,
            songs=1, start_song=1, speed=0, name='', author='', copyright=''
        )
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        self.assertEqual(analyzer.get_byte(0x1000), 0x4C)
        self.assertEqual(analyzer.get_byte(0x1001), 0x40)
        self.assertEqual(analyzer.get_byte(0x1002), 0x10)

    def test_get_word(self):
        """Test word access from virtual memory"""
        data = bytes([0x4C, 0x40, 0x10])
        header = PSIDHeader(
            magic='PSID', version=2, data_offset=0x7C,
            load_address=0x1000, init_address=0x1000, play_address=0x1003,
            songs=1, start_song=1, speed=0, name='', author='', copyright=''
        )
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        # Little-endian word at $1001 should be $1040
        self.assertEqual(analyzer.get_word(0x1001), 0x1040)


class TestSequenceEvent(unittest.TestCase):
    """Tests for sequence event data structure"""

    def test_sequence_event_creation(self):
        """Test creating a sequence event"""
        event = SequenceEvent(instrument=0, command=0, note=0x30)
        self.assertEqual(event.instrument, 0)
        self.assertEqual(event.command, 0)
        self.assertEqual(event.note, 0x30)


class TestExtractedData(unittest.TestCase):
    """Tests for extracted data structure"""

    def test_extracted_data_creation(self):
        """Test creating extracted data structure"""
        header = PSIDHeader(
            magic='PSID', version=2, data_offset=0x7C,
            load_address=0x1000, init_address=0x1000, play_address=0x1003,
            songs=1, start_song=1, speed=0, name='Test', author='Author',
            copyright='2024'
        )

        extracted = ExtractedData(
            header=header,
            c64_data=b'\x00' * 100,
            load_address=0x1000,
            sequences=[],
            orderlists=[],
            instruments=[],
            wavetable=b'',
            pulsetable=b'',
            filtertable=b''
        )

        self.assertEqual(extracted.load_address, 0x1000)
        self.assertEqual(len(extracted.sequences), 0)


class TestSF2Writer(unittest.TestCase):
    """Tests for SF2 file writing"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.test_dir)

    def test_write_creates_file(self):
        """Test that write creates an output file"""
        header = PSIDHeader(
            magic='PSID', version=2, data_offset=0x7C,
            load_address=0x1000, init_address=0x1000, play_address=0x1003,
            songs=1, start_song=1, speed=0, name='Test', author='Author',
            copyright='2024'
        )

        extracted = ExtractedData(
            header=header,
            c64_data=b'\x00' * 100,
            load_address=0x1000,
            sequences=[[SequenceEvent(0, 0, 0x30)]],
            orderlists=[[(0, 0)]],
            instruments=[b'\x09\x00\x41\x00\x08\x00\x00\x00'],
            wavetable=b'',
            pulsetable=b'',
            filtertable=b''
        )

        output_path = os.path.join(self.test_dir, "test.sf2")
        writer = SF2Writer(extracted)
        writer.write(output_path)

        self.assertTrue(os.path.exists(output_path))

    def test_write_file_has_load_address(self):
        """Test that output file starts with valid load address"""
        header = PSIDHeader(
            magic='PSID', version=2, data_offset=0x7C,
            load_address=0x1000, init_address=0x1000, play_address=0x1003,
            songs=1, start_song=1, speed=0, name='Test', author='Author',
            copyright='2024'
        )

        extracted = ExtractedData(
            header=header,
            c64_data=b'\x00' * 100,
            load_address=0x1000,
            sequences=[],
            orderlists=[],
            instruments=[],
            wavetable=b'',
            pulsetable=b'',
            filtertable=b''
        )

        output_path = os.path.join(self.test_dir, "test.sf2")
        writer = SF2Writer(extracted)
        writer.write(output_path)

        with open(output_path, 'rb') as f:
            load_addr = struct.unpack('<H', f.read(2))[0]
            # Load address should be in valid C64 memory range
            self.assertGreaterEqual(load_addr, 0x0800)
            self.assertLess(load_addr, 0xFFFF)


class TestIntegration(unittest.TestCase):
    """Integration tests with real SID file"""

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_parse_real_sid_file(self):
        """Test parsing the actual Unboxed_Ending_8580.sid file"""
        sid_path = r"C:\Users\mit\claude\c64server\SIDM2\Unboxed_Ending_8580.sid"
        parser = SIDParser(sid_path)
        header = parser.parse_header()

        self.assertEqual(header.magic, 'PSID')
        self.assertEqual(header.version, 2)
        self.assertEqual(header.name, 'Unboxed Ending (8580)')
        self.assertEqual(header.author, 'Thomas Mogensen (DRAX)')
        self.assertEqual(header.copyright, '2018 Bonzai')

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_extract_c64_data(self):
        """Test extracting C64 data from real file"""
        sid_path = r"C:\Users\mit\claude\c64server\SIDM2\Unboxed_Ending_8580.sid"
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        self.assertEqual(load_address, 0x1000)
        self.assertEqual(len(c64_data), 4512)

        # Check for JMP instructions at start
        self.assertEqual(c64_data[0], 0x4C)  # JMP
        self.assertEqual(c64_data[3], 0x4C)  # JMP

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_analyze_real_file(self):
        """Test analyzing the real SID file"""
        sid_path = r"C:\Users\mit\claude\c64server\SIDM2\Unboxed_Ending_8580.sid"
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()

        # Should have created some basic structures
        self.assertIsNotNone(extracted)
        self.assertEqual(len(extracted.orderlists), 3)  # 3 voices


class TestNoteValues(unittest.TestCase):
    """Tests for note value handling"""

    def test_note_range(self):
        """Test that note values are in valid range"""
        # C64 SID notes typically range from 0 to ~95
        valid_notes = list(range(96))

        for note in valid_notes:
            event = SequenceEvent(instrument=0, command=0, note=note)
            self.assertGreaterEqual(event.note, 0)
            self.assertLess(event.note, 128)


class TestInstrumentEncoding(unittest.TestCase):
    """Tests for instrument data encoding"""

    def test_instrument_byte_order(self):
        """Test instrument data byte order"""
        # Standard instrument format: AD, SR, Wave, PulseLo, PulseHi, ...
        instrument = bytes([
            0x09,  # Attack/Decay
            0x00,  # Sustain/Release
            0x41,  # Waveform
            0x00, 0x08,  # Pulse width
            0x00, 0x00, 0x00
        ])

        self.assertEqual(len(instrument), 8)
        self.assertEqual(instrument[0], 0x09)  # AD
        self.assertEqual(instrument[2], 0x41)  # Wave


if __name__ == '__main__':
    # Run tests with verbosity
    unittest.main(verbosity=2)
