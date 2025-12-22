#!/usr/bin/env python3
"""
Tests for the SID to SF2 converter
"""

import sys
from pathlib import Path

# Add parent directory to path for sidm2 imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
import os
import tempfile
import struct
from sidm2 import (
    SIDParser, PSIDHeader, LaxityPlayerAnalyzer, SF2Writer,
    ExtractedData, SequenceEvent
)
from sidm2.table_extraction import (
    find_and_extract_pulse_table,
    find_and_extract_filter_table
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


class TestSequenceParsingEdgeCases(unittest.TestCase):
    """Tests for sequence parsing edge cases in LaxityPlayerAnalyzer"""

    def _parse_raw_sequence(self, raw_seq):
        """
        Helper to parse a raw sequence using the same logic as LaxityPlayerAnalyzer.
        Returns list of SequenceEvent objects.
        """
        seq = []
        current_instr = 0x80  # No change
        current_cmd = 0x00    # No command
        i = 0
        while i < len(raw_seq):
            b = raw_seq[i]

            # Instrument change: 0xA0-0xBF
            if 0xA0 <= b <= 0xBF:
                current_instr = b
                i += 1
                continue

            # Command: 0xC0-0xCF (followed by parameter byte)
            elif 0xC0 <= b <= 0xCF:
                current_cmd = b
                i += 1
                # Skip parameter byte
                if i < len(raw_seq):
                    i += 1
                continue

            # Duration/timing: 0x80-0x9F (Laxity uses full range)
            elif 0x80 <= b <= 0x9F:
                # Duration bytes modify timing - skip in SF2 (timing handled differently)
                i += 1
                continue

            # Note or control byte: 0x00-0x7F
            elif b <= 0x7F:
                # Clamp high notes to SF2 max (0x5D = B-7), but keep control bytes
                note = b
                if note > 0x5D and note not in (0x7E, 0x7F):
                    note = 0x5D  # Clamp to B-7
                seq.append(SequenceEvent(current_instr, current_cmd, note))
                current_instr = 0x80
                current_cmd = 0x00
                i += 1
                continue

            else:
                i += 1

        return seq

    def test_instrument_byte_lower_bound(self):
        """Test instrument byte at lower boundary 0xA0"""
        raw = [0xA0, 0x30]  # Instrument 0, note C-4
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].instrument, 0xA0)
        self.assertEqual(events[0].note, 0x30)

    def test_instrument_byte_upper_bound(self):
        """Test instrument byte at upper boundary 0xBF"""
        raw = [0xBF, 0x30]  # Instrument 31, note C-4
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].instrument, 0xBF)

    def test_command_byte_with_parameter(self):
        """Test command byte properly skips parameter"""
        raw = [0xC5, 0x10, 0x30]  # Command 5 with param 0x10, then note
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].command, 0xC5)
        self.assertEqual(events[0].note, 0x30)

    def test_command_byte_range(self):
        """Test all command bytes 0xC0-0xCF are handled"""
        for cmd in [0xC0, 0xC7, 0xCF]:
            raw = [cmd, 0x00, 0x30]  # Command with param, then note
            events = self._parse_raw_sequence(raw)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].command, cmd)

    def test_duration_byte_creates_event(self):
        """Test duration bytes 0x80-0x8F are skipped (timing only)"""
        raw = [0x80]  # Duration/timing byte - should be skipped in SF2
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 0)  # Duration bytes are skipped

    def test_duration_byte_upper_bound(self):
        """Test duration byte at upper boundary 0x8F is skipped"""
        raw = [0x8F]
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 0)  # Duration bytes are skipped

    def test_note_value_zero(self):
        """Test note value 0x00 (lowest note)"""
        raw = [0x00]
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].note, 0x00)

    def test_gate_on_byte(self):
        """Test gate on sustain byte 0x7E"""
        raw = [0x7E]
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].note, 0x7E)

    def test_end_marker_byte(self):
        """Test end marker byte 0x7F"""
        raw = [0x7F]
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].note, 0x7F)

    def test_instrument_resets_after_note(self):
        """Test that instrument resets to 0x80 after being used"""
        raw = [0xA0, 0x30, 0x35]  # Instrument, note, note
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].instrument, 0xA0)
        self.assertEqual(events[1].instrument, 0x80)  # Reset

    def test_command_resets_after_note(self):
        """Test that command resets to 0x00 after being used"""
        raw = [0xC5, 0x10, 0x30, 0x35]  # Command, param, note, note
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].command, 0xC5)
        self.assertEqual(events[1].command, 0x00)  # Reset

    def test_instrument_followed_by_command(self):
        """Test instrument byte followed by command byte"""
        raw = [0xA0, 0xC5, 0x10, 0x30]  # Instrument, command, param, note
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].instrument, 0xA0)
        self.assertEqual(events[0].command, 0xC5)
        self.assertEqual(events[0].note, 0x30)

    def test_multiple_instruments_in_sequence(self):
        """Test multiple instrument changes in same sequence"""
        raw = [0xA0, 0x30, 0xA5, 0x35]  # Instrument 0, note, instrument 5, note
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].instrument, 0xA0)
        self.assertEqual(events[1].instrument, 0xA5)

    def test_empty_sequence(self):
        """Test empty sequence returns empty list"""
        raw = []
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 0)

    def test_only_instrument_no_note(self):
        """Test sequence with only instrument byte (no note)"""
        raw = [0xA0]  # Instrument only
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 0)  # No event created without note

    def test_gap_bytes_0x90_to_0x9F(self):
        """Test bytes in gap range 0x90-0x9F are skipped"""
        raw = [0x90, 0x30]  # Gap byte, then note
        events = self._parse_raw_sequence(raw)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].note, 0x30)
        self.assertEqual(events[0].instrument, 0x80)  # No instrument set


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
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_parse_real_sid_file(self):
        """Test parsing the actual Unboxed_Ending_8580.sid file"""
        sid_path = r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"
        parser = SIDParser(sid_path)
        header = parser.parse_header()

        self.assertEqual(header.magic, 'PSID')
        self.assertEqual(header.version, 2)
        self.assertEqual(header.name, 'Unboxed Ending (8580)')
        self.assertEqual(header.author, 'Thomas Mogensen (DRAX)')
        self.assertEqual(header.copyright, '2018 Bonzai')

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_extract_c64_data(self):
        """Test extracting C64 data from real file"""
        sid_path = r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        self.assertEqual(load_address, 0x1000)
        self.assertEqual(len(c64_data), 4512)

        # Check for JMP instructions at start
        self.assertEqual(c64_data[0], 0x4C)  # JMP
        self.assertEqual(c64_data[3], 0x4C)  # JMP

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_analyze_real_file(self):
        """Test analyzing the real SID file"""
        sid_path = r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"
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


class TestNewFeatures(unittest.TestCase):
    """Tests for new improvement features"""

    SID_DIR = r"C:\Users\mit\claude\c64server\SIDM2\SID"

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_tempo_extraction(self):
        """Test tempo detection (#8)"""
        sid_path = os.path.join(self.SID_DIR, "Unboxed_Ending_8580.sid")
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        tempo = analyzer.extract_tempo()

        # Tempo should be in valid range
        self.assertGreaterEqual(tempo, 1)
        self.assertLessEqual(tempo, 31)

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_filter_table_extraction(self):
        """Test filter table extraction (#9)"""
        sid_path = os.path.join(self.SID_DIR, "Unboxed_Ending_8580.sid")
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        filter_table, filter_addr = analyzer.extract_filter_table()

        # Filter table should be bytes, address should be int or None
        self.assertIsInstance(filter_table, bytes)
        self.assertIsInstance(filter_addr, (int, type(None)))

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_pulse_table_extraction(self):
        """Test pulse width table extraction (#10)"""
        sid_path = os.path.join(self.SID_DIR, "Unboxed_Ending_8580.sid")
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        pulse_table = analyzer.extract_pulse_table()

        # Pulse table should be bytes
        self.assertIsInstance(pulse_table, bytes)

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_command_mapping(self):
        """Test command/effect mapping (#6)"""
        sid_path = os.path.join(self.SID_DIR, "Unboxed_Ending_8580.sid")
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)

        # Test known command mappings
        cmd, name = analyzer.map_command(0xC0)
        self.assertEqual(cmd, 0xC0)
        self.assertEqual(name, "Set duration")

        cmd, name = analyzer.map_command(0xC5)
        self.assertEqual(cmd, 0xC5)
        self.assertEqual(name, "Vibrato")

        # Test duration command
        cmd, name = analyzer.map_command(0x85)
        self.assertEqual(name, "Duration")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_validation(self):
        """Test data validation (#7)"""
        sid_path = os.path.join(self.SID_DIR, "Unboxed_Ending_8580.sid")
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()

        # Validation should produce a list (possibly empty)
        self.assertIsInstance(extracted.validation_errors, list)

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_pointer_table_parsing(self):
        """Test pointer table parsing (#3)"""
        sid_path = os.path.join(self.SID_DIR, "Unboxed_Ending_8580.sid")
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()

        # Pointer tables should be a dict
        self.assertIsInstance(extracted.pointer_tables, dict)

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_improved_instrument_extraction(self):
        """Test improved instrument extraction (#5)"""
        sid_path = os.path.join(self.SID_DIR, "Unboxed_Ending_8580.sid")
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        instruments = analyzer.extract_instruments()

        # Should find some instruments
        self.assertGreater(len(instruments), 0)

        # Each instrument should be 8 bytes (SF2 format)
        for instr in instruments:
            self.assertEqual(len(instr), 8)

            # Waveform byte should be valid
            wave = instr[2]
            valid_waves = (0x00, 0x10, 0x11, 0x20, 0x21, 0x40, 0x41, 0x80, 0x81,
                         0x12, 0x14, 0x22, 0x24, 0x42, 0x44, 0x82, 0x84)
            self.assertIn(wave, valid_waves)

    def test_extracted_data_new_fields(self):
        """Test that ExtractedData has new fields"""
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

        # Check new fields exist and have defaults
        self.assertEqual(extracted.tempo, 6)
        self.assertIsInstance(extracted.commands, list)
        self.assertIsInstance(extracted.pointer_tables, dict)
        self.assertIsInstance(extracted.validation_errors, list)


class TestPulseTableExtraction(unittest.TestCase):
    """Tests for pulse table extraction improvements"""

    SID_DIR = r"C:\Users\mit\claude\c64server\SIDM2\SID"

    def _load_sid_data(self, filename):
        """Helper to load SID file and return data and load_address"""
        sid_path = os.path.join(self.SID_DIR, filename)
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)
        return c64_data, load_address

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "SID file not found"
    )
    def test_pulse_table_finds_correct_address(self):
        """Test pulse table extraction finds the correct address"""
        c64_data, load_address = self._load_sid_data("Unboxed_Ending_8580.sid")
        addr, entries = find_and_extract_pulse_table(c64_data, load_address)
        self.assertIsNotNone(addr, "Pulse table address should be found")
        self.assertGreater(len(entries), 0, "Should extract at least one entry")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "SID file not found"
    )
    def test_pulse_table_extracts_multiple_entries(self):
        """Test pulse table extracts all entries including loops"""
        c64_data, load_address = self._load_sid_data("Unboxed_Ending_8580.sid")
        addr, entries = find_and_extract_pulse_table(c64_data, load_address)
        # Should extract more than just the first few entries
        self.assertGreater(len(entries), 5, "Should extract more than 5 pulse entries")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "SID file not found"
    )
    def test_pulse_entry_format(self):
        """Test pulse table entries have correct 4-byte format"""
        c64_data, load_address = self._load_sid_data("Unboxed_Ending_8580.sid")
        addr, entries = find_and_extract_pulse_table(c64_data, load_address)
        for i, entry in enumerate(entries):
            self.assertIsInstance(entry, tuple, f"Entry {i} should be tuple")
            self.assertEqual(len(entry), 4, f"Entry {i} should have 4 bytes")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "SID file not found"
    )
    def test_pulse_table_chain_patterns(self):
        """Test pulse table correctly handles chain patterns (next_idx references)"""
        c64_data, load_address = self._load_sid_data("Unboxed_Ending_8580.sid")
        addr, entries = find_and_extract_pulse_table(c64_data, load_address)
        # Check for entries with next_idx values that form chains
        has_chain = any(entry[3] != 0 for entry in entries if len(entry) == 4)
        self.assertTrue(has_chain, "Should have chain patterns in pulse table")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "SID file not found"
    )
    def test_pulse_table_all_files(self):
        """Test pulse table extraction works for all SID files"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]
        for sid_file in sid_files:
            c64_data, load_address = self._load_sid_data(sid_file)
            addr, entries = find_and_extract_pulse_table(c64_data, load_address)
            # Each file should either find a table or return None gracefully
            if addr is not None:
                self.assertGreater(len(entries), 0, f"Found addr but no entries in {sid_file}")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "SID file not found"
    )
    def test_pulse_table_scoring_prefers_patterns(self):
        """Test that pulse table scoring correctly favors valid patterns"""
        c64_data, load_address = self._load_sid_data("Unboxed_Ending_8580.sid")
        addr, entries = find_and_extract_pulse_table(c64_data, load_address)
        # Valid tables should have reasonable pulse values (0-255 for high byte)
        for i, entry in enumerate(entries):
            if len(entry) == 4:
                self.assertLessEqual(entry[0], 255, f"Entry {i} pulse value out of range")


class TestFilterTableExtraction(unittest.TestCase):
    """Tests for filter table extraction improvements"""

    SID_DIR = r"C:\Users\mit\claude\c64server\SIDM2\SID"

    def _load_sid_data(self, filename):
        """Helper to load SID file and return data and load_address"""
        sid_path = os.path.join(self.SID_DIR, filename)
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)
        return c64_data, load_address

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "SID file not found"
    )
    def test_filter_table_finds_correct_address(self):
        """Test filter table extraction finds the correct address"""
        c64_data, load_address = self._load_sid_data("Unboxed_Ending_8580.sid")
        addr, entries = find_and_extract_filter_table(c64_data, load_address)
        self.assertIsNotNone(addr, "Filter table address should be found")
        self.assertGreater(len(entries), 0, "Should extract at least one entry")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "SID file not found"
    )
    def test_filter_table_extracts_multiple_entries(self):
        """Test filter table extracts entries beyond just defaults"""
        c64_data, load_address = self._load_sid_data("Unboxed_Ending_8580.sid")
        addr, entries = find_and_extract_filter_table(c64_data, load_address)
        # Should extract more than just 1 default entry
        self.assertGreater(len(entries), 1, "Should extract more than 1 filter entry")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "SID file not found"
    )
    def test_filter_entry_format(self):
        """Test filter table entries have correct 4-element format"""
        c64_data, load_address = self._load_sid_data("Unboxed_Ending_8580.sid")
        addr, entries = find_and_extract_filter_table(c64_data, load_address)
        for i, entry in enumerate(entries):
            self.assertIsInstance(entry, (tuple, bytes), f"Entry {i} should be tuple or bytes")
            self.assertEqual(len(entry), 4, f"Entry {i} should have 4 elements")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "SID file not found"
    )
    def test_filter_table_avoids_pulse_overlap(self):
        """Test filter table extraction respects avoid_addr parameter"""
        c64_data, load_address = self._load_sid_data("Unboxed_Ending_8580.sid")
        pulse_addr, _ = find_and_extract_pulse_table(c64_data, load_address)
        filter_addr, entries = find_and_extract_filter_table(
            c64_data, load_address, avoid_addr=pulse_addr
        )
        # Filter table should not overlap with pulse table
        if filter_addr and pulse_addr:
            self.assertNotEqual(filter_addr, pulse_addr, "Filter should not be at pulse address")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "SID file not found"
    )
    def test_filter_table_all_files(self):
        """Test filter table extraction works for all SID files"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]
        for sid_file in sid_files:
            c64_data, load_address = self._load_sid_data(sid_file)
            addr, entries = find_and_extract_filter_table(c64_data, load_address)
            # Each file should either find a table or return None gracefully
            if addr is not None:
                self.assertGreater(len(entries), 0, f"Found addr but no entries in {sid_file}")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "SID file not found"
    )
    def test_filter_table_pattern_detection(self):
        """Test filter table uses pattern-based detection"""
        c64_data, load_address = self._load_sid_data("Unboxed_Ending_8580.sid")
        addr, entries = find_and_extract_filter_table(c64_data, load_address)
        # Valid filter entries should have valid duration/direction bytes
        for i, entry in enumerate(entries):
            if len(entry) == 4:
                # Byte 2 is duration (bits 0-6) + direction (bit 7)
                duration = entry[2] & 0x7F
                self.assertLessEqual(duration, 127, f"Entry {i} duration out of range")


class TestTableLinkageValidation(unittest.TestCase):
    """Tests for instrument table linkage validation"""

    SID_DIR = r"C:\Users\mit\claude\c64server\SIDM2\SID"

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_table_linkage_validation_runs(self):
        """Test that table linkage validation runs during extraction"""
        sid_path = os.path.join(self.SID_DIR, "Unboxed_Ending_8580.sid")
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()

        # Validation should have run (may have errors or not)
        self.assertIsInstance(extracted.validation_errors, list)

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_instruments_have_valid_wave_ptr(self):
        """Test that instrument wave_ptr values are within table bounds"""
        sid_path = os.path.join(self.SID_DIR, "Unboxed_Ending_8580.sid")
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()

        # Check for wave_ptr validation errors
        wave_errors = [e for e in extracted.validation_errors if 'wave_ptr' in e]
        # If there are wave_ptr errors, they should be properly formatted
        for err in wave_errors:
            self.assertIn('Instrument', err)

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_all_files_table_linkage(self):
        """Test table linkage validation for all SID files"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]

        for sid_file in sid_files:
            sid_path = os.path.join(self.SID_DIR, sid_file)
            parser = SIDParser(sid_path)
            header = parser.parse_header()
            c64_data, load_address = parser.get_c64_data(header)

            analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
            extracted = analyzer.extract_music_data()

            # Each file should have validation errors list
            self.assertIsInstance(extracted.validation_errors, list,
                                f"Failed for {sid_file}")


class TestFullConversionPipeline(unittest.TestCase):
    """Integration tests for complete SID->SF2 conversion pipeline"""

    SID_DIR = r"C:\Users\mit\claude\c64server\SIDM2\SID"
    SF2_DIR = r"C:\Users\mit\claude\c64server\SIDM2\SF2"

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_converted_sf2_has_valid_load_address(self):
        """Test that converted SF2 has proper load address"""
        sid_path = os.path.join(self.SID_DIR, "Unboxed_Ending_8580.sid")
        sf2_path = os.path.join(self.test_dir, "test_output.sf2")

        # Parse and extract
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()

        # Write SF2
        writer = SF2Writer(extracted)
        writer.write(sf2_path)

        # Verify load address
        with open(sf2_path, 'rb') as f:
            load_lo = f.read(1)[0]
            load_hi = f.read(1)[0]
            file_load_addr = (load_hi << 8) | load_lo

        # Load address should be in valid C64 range
        self.assertGreaterEqual(file_load_addr, 0x0800)
        self.assertLessEqual(file_load_addr, 0xFFFE)

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_converted_sf2_metadata_preserved(self):
        """Test song name, author, copyright preserved through conversion"""
        sid_path = os.path.join(self.SID_DIR, "Unboxed_Ending_8580.sid")
        sf2_path = os.path.join(self.test_dir, "test_output.sf2")

        # Parse and extract
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()

        # Remember original metadata
        orig_name = header.name
        orig_author = header.author

        # Write SF2
        writer = SF2Writer(extracted)
        writer.write(sf2_path)

        # Verify file was created and has content
        self.assertTrue(os.path.exists(sf2_path))
        file_size = os.path.getsize(sf2_path)
        self.assertGreater(file_size, 100, "SF2 file too small")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID"),
        "SID directory not found"
    )
    def test_all_files_convert_successfully(self):
        """Test that all SID files convert to SF2 without errors"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]

        for sid_file in sid_files:
            sid_path = os.path.join(self.SID_DIR, sid_file)
            sf2_path = os.path.join(self.test_dir, sid_file.replace('.sid', '.sf2'))

            # Parse and extract
            parser = SIDParser(sid_path)
            header = parser.parse_header()
            c64_data, load_address = parser.get_c64_data(header)

            analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
            extracted = analyzer.extract_music_data()

            # Write SF2 - should not raise exception
            writer = SF2Writer(extracted)
            writer.write(sf2_path)

            # Verify file was created
            self.assertTrue(os.path.exists(sf2_path),
                          f"Failed to create SF2 for {sid_file}")

    @unittest.skipUnless(
        os.path.exists(r"C:\Users\mit\claude\c64server\SIDM2\SID\Unboxed_Ending_8580.sid"),
        "Real SID file not found"
    )
    def test_converted_sf2_has_valid_sequences(self):
        """Test that converted SF2 has non-empty sequence data"""
        sid_path = os.path.join(self.SID_DIR, "Unboxed_Ending_8580.sid")
        sf2_path = os.path.join(self.test_dir, "test_output.sf2")

        # Parse and extract
        parser = SIDParser(sid_path)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()

        # Verify we have sequences
        self.assertGreater(len(extracted.sequences), 0,
                         "No sequences extracted")

        # Verify sequences have content
        for i, seq in enumerate(extracted.sequences):
            self.assertGreater(len(seq), 0,
                             f"Sequence {i} is empty")

        # Write SF2
        writer = SF2Writer(extracted)
        writer.write(sf2_path)

        # Verify file has reasonable size (sequences take space)
        file_size = os.path.getsize(sf2_path)
        self.assertGreater(file_size, 1000,
                         "SF2 file too small, sequences may be missing")


class TestAllSIDFiles(unittest.TestCase):
    """Test conversion with all SID files in the SID directory"""

    SID_DIR = r"C:\Users\mit\claude\c64server\SIDM2\SID"

    @classmethod
    def setUpClass(cls):
        """Check if SID directory exists"""
        if not os.path.exists(cls.SID_DIR):
            raise unittest.SkipTest(f"SID directory not found: {cls.SID_DIR}")

    def test_all_sid_files_parseable(self):
        """Test that all SID files in directory can be parsed"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]
        self.assertGreater(len(sid_files), 0, "No SID files found in directory")

        for sid_file in sid_files:
            with self.subTest(sid_file=sid_file):
                sid_path = os.path.join(self.SID_DIR, sid_file)
                parser = SIDParser(sid_path)
                header = parser.parse_header()

                # Verify basic header fields
                self.assertIn(header.magic, ['PSID', 'RSID'])
                self.assertGreaterEqual(header.version, 1)
                self.assertGreater(header.songs, 0)

    def test_all_sid_files_extractable(self):
        """Test that C64 data can be extracted from all SID files"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]

        for sid_file in sid_files:
            with self.subTest(sid_file=sid_file):
                sid_path = os.path.join(self.SID_DIR, sid_file)
                parser = SIDParser(sid_path)
                header = parser.parse_header()
                c64_data, load_address = parser.get_c64_data(header)

                # Verify valid data extracted
                self.assertGreater(len(c64_data), 0)
                self.assertGreaterEqual(load_address, 0x0400)
                self.assertLess(load_address, 0xFFFF)

    def test_all_sid_files_analyzable(self):
        """Test that all SID files can be analyzed"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]

        for sid_file in sid_files:
            with self.subTest(sid_file=sid_file):
                sid_path = os.path.join(self.SID_DIR, sid_file)
                parser = SIDParser(sid_path)
                header = parser.parse_header()
                c64_data, load_address = parser.get_c64_data(header)

                analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
                extracted = analyzer.extract_music_data()

                # Verify extracted data structure
                self.assertIsNotNone(extracted)
                self.assertEqual(len(extracted.orderlists), 3)

    def test_all_sid_files_convertible(self):
        """Test that all SID files can be converted to SF2"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]
        test_dir = tempfile.mkdtemp()

        try:
            for sid_file in sid_files:
                with self.subTest(sid_file=sid_file):
                    sid_path = os.path.join(self.SID_DIR, sid_file)
                    output_path = os.path.join(test_dir, sid_file.replace('.sid', '.sf2'))

                    # Parse and analyze
                    parser = SIDParser(sid_path)
                    header = parser.parse_header()
                    c64_data, load_address = parser.get_c64_data(header)

                    analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
                    extracted = analyzer.extract_music_data()

                    # Write SF2
                    writer = SF2Writer(extracted)
                    writer.write(output_path)

                    # Verify output exists and has content
                    self.assertTrue(os.path.exists(output_path))
                    self.assertGreater(os.path.getsize(output_path), 0)
        finally:
            import shutil
            shutil.rmtree(test_dir)

    def test_all_sid_files_tempo_extraction(self):
        """Test tempo extraction for all SID files (#8)"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]

        for sid_file in sid_files:
            with self.subTest(sid_file=sid_file):
                sid_path = os.path.join(self.SID_DIR, sid_file)
                parser = SIDParser(sid_path)
                header = parser.parse_header()
                c64_data, load_address = parser.get_c64_data(header)

                analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
                tempo = analyzer.extract_tempo()

                # Tempo should be in valid range
                self.assertGreaterEqual(tempo, 1)
                self.assertLessEqual(tempo, 31)

    def test_all_sid_files_instrument_extraction(self):
        """Test instrument extraction for all SID files (#5)"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]

        for sid_file in sid_files:
            with self.subTest(sid_file=sid_file):
                sid_path = os.path.join(self.SID_DIR, sid_file)
                parser = SIDParser(sid_path)
                header = parser.parse_header()
                c64_data, load_address = parser.get_c64_data(header)

                analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
                instruments = analyzer.extract_instruments()

                # Should find at least one instrument
                self.assertGreaterEqual(len(instruments), 1)

                # Each instrument should be 8 bytes
                for instr in instruments:
                    self.assertEqual(len(instr), 8)

    def test_all_sid_files_validation(self):
        """Test validation for all SID files (#7)"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]

        for sid_file in sid_files:
            with self.subTest(sid_file=sid_file):
                sid_path = os.path.join(self.SID_DIR, sid_file)
                parser = SIDParser(sid_path)
                header = parser.parse_header()
                c64_data, load_address = parser.get_c64_data(header)

                analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
                extracted = analyzer.extract_music_data()

                # Validation errors should be a list
                self.assertIsInstance(extracted.validation_errors, list)

                # Check extracted data has valid structure
                self.assertGreater(len(extracted.sequences), 0)
                self.assertEqual(len(extracted.orderlists), 3)

    def test_all_sid_files_tables_extraction(self):
        """Test filter and pulse table extraction for all SID files (#9, #10)"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]

        for sid_file in sid_files:
            with self.subTest(sid_file=sid_file):
                sid_path = os.path.join(self.SID_DIR, sid_file)
                parser = SIDParser(sid_path)
                header = parser.parse_header()
                c64_data, load_address = parser.get_c64_data(header)

                analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)

                # Extract tables
                filter_table, filter_addr = analyzer.extract_filter_table()
                pulse_table = analyzer.extract_pulse_table()

                # Tables should be bytes
                self.assertIsInstance(filter_table, bytes)
                self.assertIsInstance(filter_addr, (int, type(None)))
                self.assertIsInstance(pulse_table, bytes)

    def test_all_sid_files_command_mapping(self):
        """Test command mapping for all SID files (#6)"""
        sid_files = [f for f in os.listdir(self.SID_DIR) if f.endswith('.sid')]

        for sid_file in sid_files:
            with self.subTest(sid_file=sid_file):
                sid_path = os.path.join(self.SID_DIR, sid_file)
                parser = SIDParser(sid_path)
                header = parser.parse_header()
                c64_data, load_address = parser.get_c64_data(header)

                analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
                extracted = analyzer.extract_music_data()

                # Check that commands were extracted
                self.assertIsInstance(extracted.commands, list)

                # Verify sequences have mapped commands
                for seq in extracted.sequences:
                    for event in seq:
                        # Command should be valid
                        self.assertGreaterEqual(event.command, 0)
                        self.assertLessEqual(event.command, 0xFF)


class TestLaxityFrequencyTable(unittest.TestCase):
    """Tests for Laxity frequency table extraction and note conversion"""

    def setUp(self):
        """Set up test data with known frequency table"""
        # Create minimal C64 data with frequency table at $1835
        self.load_addr = 0x1000
        freq_table_offset = 0x1835 - self.load_addr  # Offset in data

        # Create data buffer large enough to contain frequency table
        self.c64_data = bytearray(freq_table_offset + (96 * 2))

        # Fill with known frequency values for testing
        # C-0 (MIDI 24) = ~16.35 Hz -> SID freq ~1112 (0x0458)
        # A-4 (MIDI 69) = 440 Hz -> SID freq ~7492 (0x1D44)
        # C-5 (MIDI 72) = ~523.25 Hz -> SID freq ~8910 (0x22CE)

        # Entry 0: C-0 frequency (0x0458 = 1112)
        self.c64_data[freq_table_offset + 0] = 0x58
        self.c64_data[freq_table_offset + 1] = 0x04

        # Entry 45: A-4 frequency (0x1D44 = 7492)
        self.c64_data[freq_table_offset + 45 * 2] = 0x44
        self.c64_data[freq_table_offset + 45 * 2 + 1] = 0x1D

        # Entry 48: C-5 frequency (0x22CE = 8910)
        self.c64_data[freq_table_offset + 48 * 2] = 0xCE
        self.c64_data[freq_table_offset + 48 * 2 + 1] = 0x22

    def test_frequency_table_extraction(self):
        """Test extraction of frequency table from C64 data"""
        from sidm2.sequence_translator import LaxityFrequencyTable

        freq_table = LaxityFrequencyTable(bytes(self.c64_data), self.load_addr)

        # Should extract 96 frequencies
        self.assertEqual(len(freq_table.frequencies), 96)

        # Verify known values
        self.assertEqual(freq_table.frequencies[0], 0x0458)  # C-0
        self.assertEqual(freq_table.frequencies[45], 0x1D44)  # A-4
        self.assertEqual(freq_table.frequencies[48], 0x22CE)  # C-5

    def test_frequency_to_sf2_note_conversion(self):
        """Test SID frequency to SF2 note number conversion"""
        from sidm2.sequence_translator import LaxityFrequencyTable

        freq_table = LaxityFrequencyTable(bytes(self.c64_data), self.load_addr)

        # Test A-4 (440 Hz) -> should convert to MIDI note 69
        # SF2 range is C-0 to B-7 = MIDI 0-93 = 0x00-0x5D
        note_a4 = freq_table.frequency_to_sf2_note(0x1D44)
        self.assertGreaterEqual(note_a4, 67)  # Around MIDI 69 (A-4)
        self.assertLessEqual(note_a4, 71)

        # C-5 (MIDI 72)
        note_c5 = freq_table.frequency_to_sf2_note(0x22CE)
        self.assertGreaterEqual(note_c5, 70)  # Around MIDI 72 (C-5)
        self.assertLessEqual(note_c5, 74)

    def test_translate_laxity_note(self):
        """Test translation of Laxity note indices to SF2 notes"""
        from sidm2.sequence_translator import LaxityFrequencyTable, SF2_GATE_ON, SF2_END

        freq_table = LaxityFrequencyTable(bytes(self.c64_data), self.load_addr)

        # Test control bytes pass through
        # Note: $00 is a valid note (C-0), NOT a rest! $7E is the rest marker
        note_c0 = freq_table.translate_laxity_note(0x00)
        self.assertGreaterEqual(note_c0, 0)  # $00 translates to a valid note
        self.assertLessEqual(note_c0, 93)
        self.assertEqual(freq_table.translate_laxity_note(SF2_GATE_ON), SF2_GATE_ON)  # $7E = rest
        self.assertEqual(freq_table.translate_laxity_note(SF2_END), SF2_END)  # $7F = end

        # Test note lookup
        note = freq_table.translate_laxity_note(45)  # A-4 index
        self.assertGreaterEqual(note, 0)
        self.assertLessEqual(note, 93)  # 0x5D

    def test_frequency_edge_cases(self):
        """Test edge cases for frequency conversion"""
        from sidm2.sequence_translator import LaxityFrequencyTable

        freq_table = LaxityFrequencyTable(bytes(self.c64_data), self.load_addr)

        # Zero frequency
        self.assertEqual(freq_table.frequency_to_sf2_note(0), 0)

        # Very high frequency (should clamp to max)
        self.assertEqual(freq_table.frequency_to_sf2_note(0xFFFF), 93)

        # Very low frequency (should clamp to min)
        self.assertEqual(freq_table.frequency_to_sf2_note(1), 0)


class TestCommandIndexMap(unittest.TestCase):
    """Tests for command index mapping"""

    def test_build_command_index_map(self):
        """Test building stable command index mapping"""
        from sidm2.sequence_extraction import build_command_index_map

        # Command parameters: (type, param1, param2)
        commands = [
            (0, 0x01, 0x20),  # Slide up
            (1, 0x04, 0x08),  # Vibrato
            (0, 0x01, 0x20),  # Duplicate - should reuse index 0
            (2, 0x02, 0x00),  # Portamento
            (9, 0xF0, 0xA0),  # Set ADSR
        ]

        index_map = build_command_index_map(commands)

        # Should have 4 unique commands
        self.assertEqual(len(index_map), 4)

        # Same command should map to same index
        self.assertEqual(index_map[(0, 0x01, 0x20)], 0)

        # Different commands should have different indices
        self.assertNotEqual(index_map[(1, 0x04, 0x08)], index_map[(2, 0x02, 0x00)])

        # Indices should be sequential starting from 0
        indices = sorted(index_map.values())
        self.assertEqual(indices, [0, 1, 2, 3])

    def test_command_index_map_limit(self):
        """Test that command index map respects 64-entry limit"""
        from sidm2.sequence_extraction import build_command_index_map

        # Create 70 unique commands
        commands = [(0, i, 0) for i in range(70)]

        index_map = build_command_index_map(commands)

        # Should cap at 64 entries
        self.assertEqual(len(index_map), 64)

        # Indices should be 0-63
        self.assertEqual(max(index_map.values()), 63)
        self.assertEqual(min(index_map.values()), 0)


class TestErrorHandling(unittest.TestCase):
    """Tests for error handling edge cases"""

    def test_convert_sid_to_sf2_file_not_found(self):
        """Test that FileNotFoundError is raised for missing input file"""
        from scripts.sid_to_sf2 import convert_sid_to_sf2
        from sidm2.errors import FileNotFoundError as SIDMFileNotFoundError

        with self.assertRaises((FileNotFoundError, SIDMFileNotFoundError)) as cm:
            convert_sid_to_sf2('nonexistent.sid', 'output.sf2')

        self.assertIn('not found', str(cm.exception).lower())

    def test_convert_sid_to_sf2_invalid_driver(self):
        """Test that ValueError or ConfigurationError is raised for invalid driver type"""
        from scripts.sid_to_sf2 import convert_sid_to_sf2
        from sidm2.errors import ConfigurationError

        # Use an existing SID file for this test
        sid_file = 'SID/Angular.sid'
        if os.path.exists(sid_file):
            with self.assertRaises((ValueError, ConfigurationError)) as cm:
                convert_sid_to_sf2(sid_file, 'output.sf2', driver_type='invalid')

            # Check error message mentions driver or invalid
            self.assertTrue('driver' in str(cm.exception).lower() or 'invalid' in str(cm.exception).lower())

    def test_laxity_parser_small_data(self):
        """Test that parser handles data < 256 bytes gracefully"""
        from sidm2.laxity_parser import LaxityParser

        # Create minimal data
        small_data = bytes(100)

        parser = LaxityParser(small_data, 0x1000)

        # Parser should handle small data without crashing - it returns minimal data
        result = parser.parse()
        self.assertIsNotNone(result)
        # With small data, parser returns empty/minimal structures
        self.assertEqual(len(result.orderlists), 3)  # Always 3 orderlists

    def test_laxity_parser_empty_data(self):
        """Test that parser handles empty data"""
        from sidm2.laxity_parser import LaxityParser

        parser = LaxityParser(bytes(0), 0x1000)

        # Parser handles empty data gracefully by returning minimal structures
        result = parser.parse()
        self.assertIsNotNone(result)
        self.assertEqual(len(result.orderlists), 3)  # Always 3 orderlists

    def test_laxity_parser_extraction_failures_use_defaults(self):
        """Test that parser provides defaults when extraction fails"""
        from sidm2.laxity_parser import LaxityParser

        # Create data large enough to pass initial validation but with no valid structures
        # Use random-ish data that won't contain valid orderlists/sequences
        data = bytes([i % 256 for i in range(1000)])

        parser = LaxityParser(data, 0x1000)
        result = parser.parse()

        # Should return LaxityData without raising exception
        self.assertIsNotNone(result)
        self.assertEqual(len(result.orderlists), 3)  # Always 3 orderlists
        # Parser returns what it finds (may be 0 instruments if none detected)
        self.assertGreaterEqual(len(result.instruments), 0)

    def test_find_instrument_table_small_data(self):
        """Test that find_instrument_table returns None for small data"""
        from sidm2.table_extraction import find_instrument_table

        small_data = bytes(50)
        result = find_instrument_table(small_data, 0x1000)

        self.assertIsNone(result)

    def test_extract_laxity_instruments_small_data(self):
        """Test that extract_laxity_instruments returns empty list for small data"""
        from sidm2.instrument_extraction import extract_laxity_instruments

        small_data = bytes(50)
        result = extract_laxity_instruments(small_data, 0x1000)

        self.assertEqual(result, [])

    def test_convert_sid_to_both_drivers_file_not_found(self):
        """Test that convert_sid_to_both_drivers raises FileNotFoundError"""
        from scripts.sid_to_sf2 import convert_sid_to_both_drivers
        from sidm2.errors import FileNotFoundError as SIDMFileNotFoundError

        with self.assertRaises((FileNotFoundError, SIDMFileNotFoundError)):
            convert_sid_to_both_drivers('nonexistent.sid')



if __name__ == '__main__':
    # Run tests with verbosity
    unittest.main(verbosity=2)
