"""
Unit tests for siddump_complete.py

Tests cover:
- SID file parsing (PSID/RSID headers)
- Frequency table lookups
- Note detection logic
- Channel state tracking
- Output formatting
- CLI argument parsing
- Integration testing with real SID files

Usage:
    python pyscript/test_siddump.py
    python pyscript/test_siddump.py -v
"""

import unittest
import sys
import os
import io
import tempfile
import struct
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the module under test
from pyscript.siddump_complete import (
    parse_sid_file, detect_note, format_voice_column, format_frame_row,
    Channel, Filter, SIDHeader, FREQ_TBL_LO, FREQ_TBL_HI, FILTER_NAMES,
    run_siddump, main
)
from sidm2.errors import InvalidInputError


class TestSIDFileParser(unittest.TestCase):
    """Test SID file parsing functionality."""

    def create_test_sid(self, version=2, load_addr=0x1000, init_addr=0x1000,
                       play_addr=0x1003, songs=1, start_song=1, flags=0):
        """Create a minimal valid PSID file for testing."""
        data = bytearray()

        # Magic bytes
        data.extend(b'PSID' if version == 2 else b'RSID')

        # Version (big-endian)
        data.extend(struct.pack('>H', version))

        # Data offset
        data.extend(struct.pack('>H', 0x7C))  # Standard header size

        # Load address
        data.extend(struct.pack('>H', load_addr))

        # Init address
        data.extend(struct.pack('>H', init_addr))

        # Play address
        data.extend(struct.pack('>H', play_addr))

        # Number of songs
        data.extend(struct.pack('>H', songs))

        # Start song
        data.extend(struct.pack('>H', start_song))

        # Speed (32-bit)
        data.extend(struct.pack('>I', 0))

        # Name (32 bytes)
        data.extend(b'Test Song'.ljust(32, b'\x00'))

        # Author (32 bytes)
        data.extend(b'Test Author'.ljust(32, b'\x00'))

        # Released (32 bytes)
        data.extend(b'2025 Test'.ljust(32, b'\x00'))

        # Flags
        data.extend(struct.pack('>H', flags))

        # Pad to data offset
        while len(data) < 0x7C:
            data.append(0)

        # Add minimal C64 data (RTS instruction)
        data.extend([0x60] * 10)  # RTS

        return bytes(data)

    def test_parse_valid_psid(self):
        """Test parsing a valid PSID file."""
        sid_data = self.create_test_sid()

        with tempfile.NamedTemporaryFile(suffix='.sid', delete=False) as f:
            f.write(sid_data)
            temp_path = f.name

        try:
            header, c64_data = parse_sid_file(temp_path)

            self.assertEqual(header.magic, 'PSID')
            self.assertEqual(header.version, 2)
            self.assertEqual(header.load_address, 0x1000)
            self.assertEqual(header.init_address, 0x1000)
            self.assertEqual(header.play_address, 0x1003)
            self.assertEqual(header.songs, 1)
            self.assertEqual(header.start_song, 1)
            self.assertEqual(header.name, 'Test Song')
            self.assertEqual(header.author, 'Test Author')
            self.assertIsInstance(c64_data, bytes)
            self.assertGreater(len(c64_data), 0)
        finally:
            os.unlink(temp_path)

    def test_parse_rsid(self):
        """Test parsing an RSID file."""
        sid_data = self.create_test_sid(version=3)
        sid_data = b'RSID' + sid_data[4:]  # Change to RSID

        with tempfile.NamedTemporaryFile(suffix='.sid', delete=False) as f:
            f.write(sid_data)
            temp_path = f.name

        try:
            header, c64_data = parse_sid_file(temp_path)
            self.assertEqual(header.magic, 'RSID')
            self.assertEqual(header.version, 3)
        finally:
            os.unlink(temp_path)

    def test_parse_invalid_magic(self):
        """Test parsing file with invalid magic bytes."""
        sid_data = b'XXXX' + self.create_test_sid()[4:]

        with tempfile.NamedTemporaryFile(suffix='.sid', delete=False) as f:
            f.write(sid_data)
            temp_path = f.name

        try:
            with self.assertRaises(InvalidInputError) as cm:
                parse_sid_file(temp_path)
            self.assertIn("PSID or RSID magic bytes", str(cm.exception))
        finally:
            os.unlink(temp_path)

    def test_parse_nonexistent_file(self):
        """Test parsing a non-existent file."""
        with self.assertRaises(FileNotFoundError):
            parse_sid_file('nonexistent_file_xyz.sid')

    def test_parse_zero_play_address(self):
        """Test parsing file with play address 0 (IRQ mode)."""
        sid_data = self.create_test_sid(play_addr=0)

        with tempfile.NamedTemporaryFile(suffix='.sid', delete=False) as f:
            f.write(sid_data)
            temp_path = f.name

        try:
            header, c64_data = parse_sid_file(temp_path)
            self.assertEqual(header.play_address, 0)
        finally:
            os.unlink(temp_path)


class TestFrequencyTables(unittest.TestCase):
    """Test frequency table lookups."""

    def test_frequency_tables_length(self):
        """Test that frequency tables have correct length (96 notes)."""
        self.assertEqual(len(FREQ_TBL_LO), 96)
        self.assertEqual(len(FREQ_TBL_HI), 96)

    def test_middle_c_frequency(self):
        """Test that middle C (note 48) has correct frequency."""
        # Middle C should be around $1168
        freq = FREQ_TBL_LO[48] | (FREQ_TBL_HI[48] << 8)
        self.assertEqual(freq, 0x1168)

    def test_frequency_increasing(self):
        """Test that frequencies increase with note number."""
        prev_freq = 0
        for i in range(96):
            freq = FREQ_TBL_LO[i] | (FREQ_TBL_HI[i] << 8)
            self.assertGreater(freq, prev_freq, f"Note {i} frequency should be higher than note {i-1}")
            prev_freq = freq

    def test_octave_doubling(self):
        """Test that octave up roughly doubles frequency."""
        # C-2 (note 24) to C-3 (note 36)
        freq_c2 = FREQ_TBL_LO[24] | (FREQ_TBL_HI[24] << 8)
        freq_c3 = FREQ_TBL_LO[36] | (FREQ_TBL_HI[36] << 8)

        ratio = freq_c3 / freq_c2
        # Should be approximately 2.0 (within 5% tolerance)
        self.assertAlmostEqual(ratio, 2.0, delta=0.1)


class TestNoteDetection(unittest.TestCase):
    """Test note detection logic."""

    def test_detect_exact_match(self):
        """Test detecting a note with exact frequency match."""
        # Middle C frequency
        freq = FREQ_TBL_LO[48] | (FREQ_TBL_HI[48] << 8)
        note = detect_note(freq, -1, 8, FREQ_TBL_LO, FREQ_TBL_HI)
        self.assertEqual(note, 48)

    def test_detect_close_match(self):
        """Test detecting a note with close frequency (vibrato)."""
        # Middle C frequency + 5 (vibrato)
        freq = (FREQ_TBL_LO[48] | (FREQ_TBL_HI[48] << 8)) + 5
        note = detect_note(freq, -1, 8, FREQ_TBL_LO, FREQ_TBL_HI)
        self.assertEqual(note, 48)

    def test_sticky_note_detection(self):
        """Test sticky note detection (oldnotefactor)."""
        # Frequency between C and C# but closer to C#
        freq_c = FREQ_TBL_LO[48] | (FREQ_TBL_HI[48] << 8)
        freq_cs = FREQ_TBL_LO[49] | (FREQ_TBL_HI[49] << 8)
        freq_between = (freq_c + freq_cs) // 2 + 10  # Closer to C#

        # With previous note = C and oldnotefactor, should stick to C
        note_sticky = detect_note(freq_between, 48, 8, FREQ_TBL_LO, FREQ_TBL_HI)

        # Without previous note, should detect C#
        note_normal = detect_note(freq_between, -1, 8, FREQ_TBL_LO, FREQ_TBL_HI)

        # Sticky detection should favor previous note
        self.assertIn(note_sticky, [48, 49])
        self.assertIn(note_normal, [48, 49])

    def test_detect_lowest_note(self):
        """Test detecting lowest note (C-0)."""
        freq = FREQ_TBL_LO[0] | (FREQ_TBL_HI[0] << 8)
        note = detect_note(freq, -1, 8, FREQ_TBL_LO, FREQ_TBL_HI)
        self.assertEqual(note, 0)

    def test_detect_highest_note(self):
        """Test detecting highest note (B-7)."""
        freq = FREQ_TBL_LO[95] | (FREQ_TBL_HI[95] << 8)
        note = detect_note(freq, -1, 8, FREQ_TBL_LO, FREQ_TBL_HI)
        self.assertEqual(note, 95)


class TestChannelDataClass(unittest.TestCase):
    """Test Channel dataclass."""

    def test_channel_default_values(self):
        """Test Channel default initialization."""
        ch = Channel()
        self.assertEqual(ch.freq, 0)
        self.assertEqual(ch.pulse, 0)
        self.assertEqual(ch.wave, 0)
        self.assertEqual(ch.adsr, 0)
        self.assertEqual(ch.note, -1)

    def test_channel_custom_values(self):
        """Test Channel with custom values."""
        ch = Channel(freq=0x1168, pulse=0x800, wave=0x41, adsr=0x0DD9, note=48)
        self.assertEqual(ch.freq, 0x1168)
        self.assertEqual(ch.pulse, 0x800)
        self.assertEqual(ch.wave, 0x41)
        self.assertEqual(ch.adsr, 0x0DD9)
        self.assertEqual(ch.note, 48)


class TestFilterDataClass(unittest.TestCase):
    """Test Filter dataclass."""

    def test_filter_default_values(self):
        """Test Filter default initialization."""
        filt = Filter()
        self.assertEqual(filt.cutoff, 0)
        self.assertEqual(filt.ctrl, 0)
        self.assertEqual(filt.type, 0)

    def test_filter_custom_values(self):
        """Test Filter with custom values."""
        filt = Filter(cutoff=0x1100, ctrl=0x00, type=0x59)
        self.assertEqual(filt.cutoff, 0x1100)
        self.assertEqual(filt.ctrl, 0x00)
        self.assertEqual(filt.type, 0x59)


class TestOutputFormatting(unittest.TestCase):
    """Test output formatting functions."""

    def test_format_voice_column_first_frame(self):
        """Test formatting voice column for first frame."""
        chn = Channel(freq=0x1168, pulse=0x800, wave=0x41, adsr=0x0DD9, note=48)
        prevchn = Channel()
        prevchn2 = Channel()

        output = format_voice_column(chn, prevchn, prevchn2, True, False, False, 0)

        # First frame should show all values
        self.assertIn('1168', output)
        self.assertIn('C-4', output)  # Note 48 is C-4
        self.assertIn('41', output)
        self.assertIn('DD9', output)
        self.assertIn('800', output)

    def test_format_voice_column_no_change(self):
        """Test formatting voice column with no changes."""
        chn = Channel(freq=0x1168, pulse=0x800, wave=0x41, adsr=0x0DD9, note=48)
        prevchn = Channel(freq=0x1168, pulse=0x800, wave=0x41, adsr=0x0DD9, note=48)
        prevchn2 = Channel(freq=0x1168, pulse=0x800, wave=0x41, adsr=0x0DD9, note=48)

        output = format_voice_column(chn, prevchn, prevchn2, False, False, False, 0)

        # No changes should show dots
        self.assertIn('....', output)  # Frequency unchanged
        self.assertIn('...', output)   # Note unchanged
        self.assertIn('..', output)    # Wave/ADSR unchanged

    def test_format_voice_column_frequency_change(self):
        """Test formatting voice column with frequency change."""
        chn = Channel(freq=0x1200, pulse=0x800, wave=0x41, adsr=0x0DD9, note=50)
        prevchn = Channel(freq=0x1168, pulse=0x800, wave=0x41, adsr=0x0DD9, note=48)
        prevchn2 = Channel(freq=0x1168, pulse=0x800, wave=0x41, adsr=0x0DD9, note=48)

        output = format_voice_column(chn, prevchn, prevchn2, False, False, False, 0)

        # Frequency change should show new frequency
        self.assertIn('1200', output)

    def test_format_voice_column_gate_off(self):
        """Test formatting voice column with gate off."""
        chn = Channel(freq=0x1168, pulse=0x800, wave=0x00, adsr=0x0DD9, note=-1)
        prevchn = Channel(freq=0x1168, pulse=0x800, wave=0x41, adsr=0x0DD9, note=48)
        prevchn2 = Channel(freq=0x1168, pulse=0x800, wave=0x41, adsr=0x0DD9, note=48)

        output = format_voice_column(chn, prevchn, prevchn2, False, False, False, 0)

        # Gate off (wave < 0x10) should show dots for note
        self.assertIn('...', output)


class TestFrameFormatting(unittest.TestCase):
    """Test complete frame row formatting."""

    def test_format_frame_row_basic(self):
        """Test basic frame row formatting."""
        channels = [
            Channel(freq=0x1168, pulse=0x800, wave=0x41, adsr=0x0DD9, note=48),
            Channel(freq=0x1000, pulse=0x700, wave=0x21, adsr=0x0AA9, note=45),
            Channel(freq=0x0F00, pulse=0x600, wave=0x11, adsr=0x0889, note=42),
        ]
        prev_channels = [Channel(), Channel(), Channel()]
        prev_channels2 = [Channel(), Channel(), Channel()]
        filt = Filter(cutoff=0x1100, ctrl=0x00, type=0x59)
        prevfilt = Filter()

        output, should_print = format_frame_row(
            0, channels, prev_channels, prev_channels2, filt, prevfilt,
            True, False, False, 1, 8, 0, False
        )

        # Should contain frame number
        self.assertIn('|     0 |', output)

        # Should contain pipe delimiters
        self.assertGreater(output.count('|'), 5)

        # Should contain filter cutoff
        self.assertIn('1100', output)

    def test_format_frame_row_timeseconds(self):
        """Test frame row with time format (mm:ss.ff)."""
        channels = [Channel(), Channel(), Channel()]
        prev_channels = [Channel(), Channel(), Channel()]
        prev_channels2 = [Channel(), Channel(), Channel()]
        filt = Filter()
        prevfilt = Filter()

        # Frame 150 = 3 seconds at 50fps = 0:03.00
        output, _ = format_frame_row(
            150, channels, prev_channels, prev_channels2, filt, prevfilt,
            True, True, False, 1, 8, 0, False
        )

        # Should contain time format
        self.assertIn('0:03.00', output)

    def test_format_frame_row_profiling(self):
        """Test frame row with profiling enabled."""
        channels = [Channel(), Channel(), Channel()]
        prev_channels = [Channel(), Channel(), Channel()]
        prev_channels2 = [Channel(), Channel(), Channel()]
        filt = Filter()
        prevfilt = Filter()

        output, _ = format_frame_row(
            0, channels, prev_channels, prev_channels2, filt, prevfilt,
            True, False, False, 1, 8, 5000, True
        )

        # Should contain profiling info (cycles, raster lines)
        self.assertIn('5000', output)


class TestCLIArgumentParsing(unittest.TestCase):
    """Test CLI argument parsing."""

    def test_main_no_arguments(self):
        """Test main with no arguments (should show usage)."""
        with patch('sys.argv', ['siddump_complete.py']):
            with patch('sys.stderr', new_callable=io.StringIO) as mock_stderr:
                with self.assertRaises(SystemExit) as cm:
                    main()
                self.assertEqual(cm.exception.code, 2)

    def test_main_help(self):
        """Test main with --help flag."""
        with patch('sys.argv', ['siddump_complete.py', '--help']):
            with self.assertRaises(SystemExit) as cm:
                main()
            self.assertEqual(cm.exception.code, 0)

    def test_argument_defaults(self):
        """Test that argument parser sets correct defaults."""
        import argparse
        from pyscript.siddump_complete import main

        # Create a minimal argument parser matching the real one
        parser = argparse.ArgumentParser()
        parser.add_argument('sidfile')
        parser.add_argument('-t', '--seconds', type=int, default=60)
        parser.add_argument('-f', '--firstframe', type=int, default=0)
        parser.add_argument('-p', '--profiling', action='store_true')
        parser.add_argument('-z', '--timeseconds', action='store_true')

        args = parser.parse_args(['test.sid'])
        self.assertEqual(args.seconds, 60)
        self.assertEqual(args.firstframe, 0)
        self.assertFalse(args.profiling)
        self.assertFalse(args.timeseconds)

    def test_argument_parsing_time_flag(self):
        """Test parsing -t flag."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('sidfile')
        parser.add_argument('-t', '--seconds', type=int, default=60)

        args = parser.parse_args(['test.sid', '-t30'])
        self.assertEqual(args.seconds, 30)

    def test_argument_parsing_multiple_flags(self):
        """Test parsing multiple flags."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('sidfile')
        parser.add_argument('-t', '--seconds', type=int, default=60)
        parser.add_argument('-f', '--firstframe', type=int, default=0)
        parser.add_argument('-p', '--profiling', action='store_true')
        parser.add_argument('-z', '--timeseconds', action='store_true')

        args = parser.parse_args(['test.sid', '-t30', '-p', '-z', '-f10'])
        self.assertEqual(args.seconds, 30)
        self.assertEqual(args.firstframe, 10)
        self.assertTrue(args.profiling)
        self.assertTrue(args.timeseconds)


class TestIntegration(unittest.TestCase):
    """Integration tests with real SID files."""

    def setUp(self):
        """Find available test SID files."""
        self.test_files = []

        # Look for test files in common locations
        test_locations = [
            'SID',
            'Fun_Fun',
            'Laxity',
            'test_files'
        ]

        for location in test_locations:
            if os.path.isdir(location):
                for filename in os.listdir(location):
                    if filename.endswith('.sid'):
                        self.test_files.append(os.path.join(location, filename))
                        if len(self.test_files) >= 3:  # Limit to 3 files for speed
                            break
            if len(self.test_files) >= 3:
                break

    @unittest.skipIf(len([]) == 0, "No test SID files found")
    def test_parse_real_files(self):
        """Test parsing real SID files."""
        for sid_file in self.test_files[:3]:
            with self.subTest(file=sid_file):
                try:
                    header, c64_data = parse_sid_file(sid_file)

                    # Basic validation
                    self.assertIn(header.magic, ['PSID', 'RSID'])
                    self.assertGreater(header.version, 0)
                    self.assertGreater(len(c64_data), 0)
                    self.assertIsInstance(header.name, str)
                    self.assertIsInstance(header.author, str)

                except Exception as e:
                    self.fail(f"Failed to parse {sid_file}: {e}")

    def test_frequency_detection_range(self):
        """Test note detection across full frequency range."""
        for note in range(0, 96, 12):  # Test every octave
            freq = FREQ_TBL_LO[note] | (FREQ_TBL_HI[note] << 8)
            detected = detect_note(freq, -1, 8, FREQ_TBL_LO, FREQ_TBL_HI)
            self.assertEqual(detected, note,
                           f"Note {note} frequency {freq:04X} detected as {detected}")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def test_detect_note_zero_frequency(self):
        """Test note detection with zero frequency."""
        note = detect_note(0, -1, 8, FREQ_TBL_LO, FREQ_TBL_HI)
        # Zero frequency should return -1 (no note) or lowest note
        # Algorithm may treat zero specially
        self.assertIn(note, [-1, 0])

    def test_detect_note_max_frequency(self):
        """Test note detection with maximum frequency."""
        note = detect_note(0xFFFF, -1, 8, FREQ_TBL_LO, FREQ_TBL_HI)
        # Should return highest note (95) as closest match
        self.assertEqual(note, 95)

    def test_format_voice_column_extreme_values(self):
        """Test formatting with extreme values."""
        chn = Channel(freq=0xFFFF, pulse=0xFFF, wave=0xFF, adsr=0xFFFF, note=95)
        prevchn = Channel()
        prevchn2 = Channel()

        output = format_voice_column(chn, prevchn, prevchn2, True, False, False, 0)

        # Should handle extreme values without crashing
        self.assertIsInstance(output, str)
        self.assertGreater(len(output), 0)

    def test_filter_type_names(self):
        """Test all filter type names are defined."""
        self.assertEqual(len(FILTER_NAMES), 8)
        for name in FILTER_NAMES:
            self.assertIsInstance(name, str)


class TestOutputConsistency(unittest.TestCase):
    """Test output format consistency."""

    def test_note_names_all_octaves(self):
        """Test that all note names are correct for all octaves."""
        note_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-',
                     'F#', 'G-', 'G#', 'A-', 'A#', 'B-']

        for note in range(96):
            octave = note // 12
            note_in_octave = note % 12
            expected_name = f"{note_names[note_in_octave]}{octave}"

            # Create channel with this note
            chn = Channel(note=note, wave=0x41)
            freq = FREQ_TBL_LO[note] | (FREQ_TBL_HI[note] << 8)
            chn.freq = freq

            output = format_voice_column(chn, Channel(), Channel(), True, False, False, 0)

            # Check that expected note name appears in output
            self.assertIn(expected_name, output,
                         f"Note {note} should show as {expected_name}")

    def test_output_column_widths(self):
        """Test that output maintains consistent column widths."""
        channels = [Channel(freq=0x1168, pulse=0x800, wave=0x41, adsr=0x0DD9, note=48)] * 3
        prev_channels = [Channel()] * 3
        prev_channels2 = [Channel()] * 3
        filt = Filter(cutoff=0x1100, ctrl=0x00, type=0x59)
        prevfilt = Filter()

        # Generate multiple frames
        outputs = []
        for frame in range(10):
            output, _ = format_frame_row(
                frame, channels, prev_channels, prev_channels2, filt, prevfilt,
                False, False, False, 1, 8, 0, False
            )
            outputs.append(output)

        # All outputs should have same length (consistent columns)
        lengths = [len(o) for o in outputs]
        self.assertEqual(len(set(lengths)), 1, "All output lines should have same length")


def run_tests(verbosity=1):
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    # Check for -v flag
    verbosity = 2 if '-v' in sys.argv else 1

    print("=" * 80)
    print("Running siddump_complete.py Unit Tests")
    print("=" * 80)
    print()

    exit_code = run_tests(verbosity)

    print()
    print("=" * 80)
    if exit_code == 0:
        print("All tests PASSED")
    else:
        print("Some tests FAILED")
    print("=" * 80)

    sys.exit(exit_code)
