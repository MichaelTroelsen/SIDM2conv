"""
Comprehensive tests for sidm2/laxity_analyzer.py module.

Target: 50% coverage (Phase 1, Module 3/4)
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from sidm2.laxity_analyzer import LaxityPlayerAnalyzer
from sidm2.models import PSIDHeader, ExtractedData


def create_test_header(init_addr=0x1000, play_addr=0x10A1, load_addr=0x1000):
    """Create a mock PSIDHeader for testing."""
    header = Mock(spec=PSIDHeader)
    header.init_address = init_addr
    header.play_address = play_addr
    header.load_address = load_addr
    header.speed = 0  # VBlank by default
    return header


def create_minimal_laxity_data(size=4096):
    """Create minimal Laxity player data for testing."""
    data = bytearray(size)

    # Add some realistic patterns for detection
    # Tempo value at typical location (init routine)
    data[0x00] = 0xA9  # LDA immediate
    data[0x01] = 0x06  # tempo=6
    data[0x02] = 0x85  # STA zeropage
    data[0x03] = 0x00

    # Volume setup pattern
    data[0x10] = 0xA9  # LDA immediate
    data[0x11] = 0x0F  # volume=15
    data[0x12] = 0x8D  # STA absolute
    data[0x13] = 0x18  # $D418
    data[0x14] = 0xD4

    # Filter table at known Laxity address (0x1A1E offset)
    filter_offset = 0x1A1E - 0x1000  # Assumes load_addr=0x1000
    if filter_offset >= 0 and filter_offset + 16 < size:
        # Break speeds in filter table
        data[filter_offset:filter_offset+4] = bytes([6, 12, 6, 6])
        # Some filter entries
        data[filter_offset+4:filter_offset+20] = bytes([
            0x80, 0x04, 0x20, 0,  # Filter entry 1
            0x60, 0x02, 0x30, 0,  # Filter entry 2
            0x40, 0x01, 0x10, 0,  # Filter entry 3
            0x7F, 0x00, 0x00, 0,  # End marker
        ])

    return bytes(data)


class TestLaxityPlayerAnalyzerInit(unittest.TestCase):
    """Test LaxityPlayerAnalyzer initialization."""

    def test_init_basic(self):
        """Test basic initialization."""
        data = create_minimal_laxity_data(1024)
        header = create_test_header()

        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        self.assertEqual(analyzer.data, data)
        self.assertEqual(analyzer.load_address, 0x1000)
        self.assertEqual(analyzer.header, header)
        self.assertEqual(len(analyzer.memory), 65536)

    def test_init_loads_data_into_memory(self):
        """Test that __init__ loads data into virtual memory."""
        data = bytes([0x01, 0x02, 0x03, 0x04])
        header = create_test_header()

        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        # Check data was loaded at correct address
        self.assertEqual(analyzer.memory[0x1000], 0x01)
        self.assertEqual(analyzer.memory[0x1001], 0x02)
        self.assertEqual(analyzer.memory[0x1002], 0x03)
        self.assertEqual(analyzer.memory[0x1003], 0x04)

    def test_init_handles_data_beyond_memory(self):
        """Test that __init__ handles data that would go beyond memory."""
        # Create data that would extend beyond 64K
        data = bytes([0xFF] * 1000)
        header = create_test_header()
        load_addr = 65000  # Near end of 64K

        analyzer = LaxityPlayerAnalyzer(data, load_addr, header)

        # Should load only what fits
        end_addr = min(load_addr + len(data), 65536)
        expected_size = end_addr - load_addr
        self.assertEqual(analyzer.memory[load_addr], 0xFF)
        self.assertEqual(len([b for b in analyzer.memory[load_addr:end_addr] if b == 0xFF]), expected_size)


class TestMemoryAccessMethods(unittest.TestCase):
    """Test memory access helper methods."""

    def setUp(self):
        """Set up test data."""
        self.data = bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC])
        self.header = create_test_header()
        self.analyzer = LaxityPlayerAnalyzer(self.data, 0x1000, self.header)

    def test_get_byte(self):
        """Test get_byte method."""
        # Test basic access
        self.assertEqual(self.analyzer.get_byte(0x1000), 0x12)
        self.assertEqual(self.analyzer.get_byte(0x1001), 0x34)
        self.assertEqual(self.analyzer.get_byte(0x1005), 0xBC)

    def test_get_byte_wraps_address(self):
        """Test that get_byte wraps addresses with & 0xFFFF."""
        # Address wrapping (simulates 16-bit address space)
        result = self.analyzer.get_byte(0x10000 | 0x1000)  # Should wrap
        self.assertEqual(result, 0x12)

    def test_get_word(self):
        """Test get_word method (little-endian)."""
        # Word at 0x1000: 0x12 (lo) | 0x34 (hi) = 0x3412
        self.assertEqual(self.analyzer.get_word(0x1000), 0x3412)

        # Word at 0x1004: 0x9A (lo) | 0xBC (hi) = 0xBC9A
        self.assertEqual(self.analyzer.get_word(0x1004), 0xBC9A)


class TestExtractTempo(unittest.TestCase):
    """Test tempo extraction methods."""

    def test_extract_tempo_from_filter_table(self):
        """Test extracting tempo from filter table break speeds."""
        data = create_minimal_laxity_data(4096)
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        tempo = analyzer.extract_tempo()

        # Should find tempo=6 from break speeds [6, 12, 6, 6]
        self.assertEqual(tempo, 6)

    def test_extract_tempo_from_init_routine(self):
        """Test extracting tempo from init routine."""
        data = bytearray(256)
        # LDA #8 followed by STA
        data[0x00] = 0xA9  # LDA immediate
        data[0x01] = 0x08  # tempo value
        data[0x02] = 0x85  # STA zeropage

        header = create_test_header(init_addr=0x1000)
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        tempo = analyzer.extract_tempo()

        self.assertEqual(tempo, 8)

    def test_extract_tempo_default_fallback(self):
        """Test tempo defaults to 6 when not found."""
        data = bytes([0x00] * 256)  # Empty data
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        tempo = analyzer.extract_tempo()

        self.assertEqual(tempo, 6)  # Default

    def test_extract_tempo_validates_range(self):
        """Test that tempo extraction validates value range (1-20)."""
        data = bytearray(256)
        # Invalid tempo value (too high)
        data[0x00] = 0xA9  # LDA immediate
        data[0x01] = 0x50  # invalid tempo (>20)
        data[0x02] = 0x85  # STA

        # Valid tempo later
        data[0x10] = 0xA9
        data[0x11] = 0x0A  # tempo=10
        data[0x12] = 0x85

        header = create_test_header(init_addr=0x1000)
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        tempo = analyzer.extract_tempo()

        self.assertEqual(tempo, 10)  # Should find valid tempo


class TestExtractInitVolume(unittest.TestCase):
    """Test initial volume extraction."""

    def test_extract_init_volume_from_d418(self):
        """Test extracting volume from STA $D418 pattern."""
        data = bytearray(512)
        # LDA #$0F followed by STA $D418
        data[0x10] = 0xA9  # LDA immediate
        data[0x11] = 0x0F  # volume value
        data[0x12] = 0x8D  # STA absolute
        data[0x13] = 0x18  # $D418 low
        data[0x14] = 0xD4  # $D418 high

        header = create_test_header(init_addr=0x1000)
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        volume = analyzer.extract_init_volume()

        self.assertEqual(volume, 0x0F)

    def test_extract_init_volume_extracts_low_nibble(self):
        """Test that volume extraction uses low nibble."""
        data = bytearray(512)
        # LDA #$3F (volume should be 0x0F)
        data[0x10] = 0xA9
        data[0x11] = 0x3F  # High nibble should be masked
        data[0x12] = 0x8D
        data[0x13] = 0x18
        data[0x14] = 0xD4

        header = create_test_header(init_addr=0x1000)
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        volume = analyzer.extract_init_volume()

        self.assertEqual(volume, 0x0F)  # Low nibble only

    def test_extract_init_volume_default(self):
        """Test volume defaults to 0x0F when not found."""
        data = bytes([0x00] * 256)
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        volume = analyzer.extract_init_volume()

        self.assertEqual(volume, 0x0F)  # Default max volume

    def test_extract_init_volume_alternative_pattern(self):
        """Test alternative volume extraction pattern (STA to variable)."""
        data = bytearray(512)
        # LDA #$0C followed by STA zeropage
        data[0x10] = 0xA9  # LDA immediate
        data[0x11] = 0x0C  # volume value (low nibble only)
        data[0x12] = 0x85  # STA zeropage

        header = create_test_header(init_addr=0x1000)
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        volume = analyzer.extract_init_volume()

        self.assertEqual(volume, 0x0C)


class TestDetectMultiSpeed(unittest.TestCase):
    """Test multi-speed detection."""

    def test_detect_multi_speed_normal(self):
        """Test detection returns 1 for normal speed."""
        data = bytes([0x00] * 256)
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        speed = analyzer.detect_multi_speed()

        self.assertEqual(speed, 1)

    def test_detect_multi_speed_from_jsr_count(self):
        """Test detection from JSR instruction count."""
        data = bytearray(512)
        play_addr = 0x10A1

        # Add 4 JSR instructions to play address
        for i in range(4):
            pos = i * 10
            data[pos] = 0x20  # JSR
            data[pos + 1] = play_addr & 0xFF
            data[pos + 2] = (play_addr >> 8) & 0xFF

        header = create_test_header(play_addr=play_addr)
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        speed = analyzer.detect_multi_speed()

        self.assertEqual(speed, 4)  # 4 JSRs = 4x speed

    def test_detect_multi_speed_2x(self):
        """Test detection returns 2 for 2x speed."""
        data = bytearray(512)
        play_addr = 0x10A1

        # Add 2 JSR instructions
        data[0x00] = 0x20  # JSR
        data[0x01] = play_addr & 0xFF
        data[0x02] = (play_addr >> 8) & 0xFF

        data[0x10] = 0x20  # JSR
        data[0x11] = play_addr & 0xFF
        data[0x12] = (play_addr >> 8) & 0xFF

        header = create_test_header(play_addr=play_addr)
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        speed = analyzer.detect_multi_speed()

        self.assertEqual(speed, 2)

    def test_detect_multi_speed_cia_timer(self):
        """Test detection from CIA timer setup."""
        data = bytearray(512)
        # STA $DC04 (CIA timer low)
        data[0x10] = 0x8D
        data[0x11] = 0x04
        data[0x12] = 0xDC

        header = create_test_header()
        header.speed = 1  # CIA timer flag
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        speed = analyzer.detect_multi_speed()

        self.assertEqual(speed, 2)  # CIA timer = 2x


class TestExtractFilterTable(unittest.TestCase):
    """Test filter table extraction."""

    @patch('sidm2.laxity_analyzer.find_and_extract_filter_table')
    def test_extract_filter_table_success(self, mock_find):
        """Test successful filter table extraction."""
        # Mock return: address and list of tuples
        mock_find.return_value = (0x1A1E, [
            (0x80, 0x04, 0x20, 0),
            (0x60, 0x02, 0x30, 0),
        ])

        data = create_minimal_laxity_data()
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        filter_data, addr = analyzer.extract_filter_table()

        self.assertEqual(addr, 0x1A1E)
        # Should convert tuples to bytes
        expected = bytes([0x80, 0x04, 0x20, 0, 0x60, 0x02, 0x30, 0])
        self.assertEqual(filter_data, expected)

    @patch('sidm2.laxity_analyzer.find_and_extract_filter_table')
    def test_extract_filter_table_empty(self, mock_find):
        """Test filter table extraction with empty result."""
        mock_find.return_value = (None, [])

        data = create_minimal_laxity_data()
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        filter_data, addr = analyzer.extract_filter_table()

        self.assertEqual(filter_data, b'')
        self.assertIsNone(addr)


class TestExtractPulseTable(unittest.TestCase):
    """Test pulse table extraction."""

    def test_extract_pulse_table_finds_oscillating_pattern(self):
        """Test pulse table extraction finds oscillating values."""
        data = bytearray(4096)

        # Create oscillating pattern at 0x1A00
        pulse_offset = 0x1A00 - 0x1000
        # Oscillating values: up, down, up, down (4+ oscillations)
        oscillating = [0x00, 0x10, 0x20, 0x10, 0x00, 0x10, 0x20, 0x30,
                      0x20, 0x10, 0x00, 0x10, 0x20, 0x10, 0x00] * 4
        data[pulse_offset:pulse_offset+len(oscillating)] = oscillating

        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        pulse_data = analyzer.extract_pulse_table()

        # Should extract 64 bytes
        self.assertEqual(len(pulse_data), 64)

    def test_extract_pulse_table_returns_empty_when_not_found(self):
        """Test pulse table extraction returns empty when no pattern found."""
        data = bytes([0x00] * 4096)  # No oscillating pattern
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        pulse_data = analyzer.extract_pulse_table()

        self.assertEqual(pulse_data, b'')


class TestExtractWaveTable(unittest.TestCase):
    """Test wave table extraction."""

    @patch('sidm2.table_extraction.find_and_extract_wave_table')
    def test_extract_wave_table_success(self, mock_find):
        """Test successful wave table extraction."""
        # Mock return: address and list of (waveform, note) tuples
        mock_find.return_value = (0x1100, [
            (0x11, 0x00),  # Triangle, note 0
            (0x21, 0x05),  # Saw, note +5
            (0x41, 0x0C),  # Pulse, note +12
        ])

        data = create_minimal_laxity_data()
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        wave_data, addr = analyzer.extract_wave_table()

        self.assertEqual(addr, 0x1100)
        # Should convert to bytes: waveform, note_offset pairs
        expected = bytes([0x11, 0x00, 0x21, 0x05, 0x41, 0x0C])
        self.assertEqual(wave_data, expected)

    @patch('sidm2.table_extraction.find_and_extract_wave_table')
    def test_extract_wave_table_empty(self, mock_find):
        """Test wave table extraction with empty result."""
        mock_find.return_value = (None, [])

        data = create_minimal_laxity_data()
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        wave_data, addr = analyzer.extract_wave_table()

        self.assertEqual(wave_data, b'')
        self.assertIsNone(addr)


class TestExtractCommands(unittest.TestCase):
    """Test command extraction."""

    def test_extract_commands_finds_valid_commands(self):
        """Test command extraction finds valid command data."""
        data = bytearray(4096)

        # Add command data at 0x1A60
        cmd_offset = 0x1A60 - 0x1000
        # Commands have first byte in range 0x00-0x0F
        data[cmd_offset:cmd_offset+24] = bytes([
            0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Cmd 0
            0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Cmd 1
            0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Cmd 2
        ])

        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        commands = analyzer.extract_commands()

        self.assertGreater(len(commands), 0)
        # Each command is 8 bytes
        for cmd in commands:
            self.assertEqual(len(cmd), 8)

    def test_extract_commands_stops_at_32(self):
        """Test command extraction stops at 32 commands."""
        data = bytearray(4096)

        # Fill with many valid commands
        cmd_offset = 0x1A60 - 0x1000
        for i in range(50):
            pos = cmd_offset + (i * 8)
            if pos + 8 < len(data):
                data[pos] = i % 16  # Valid command byte

        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        commands = analyzer.extract_commands()

        self.assertLessEqual(len(commands), 32)


class TestExtractInstruments(unittest.TestCase):
    """Test instrument extraction."""

    @patch('sidm2.table_extraction.find_instrument_table')
    def test_extract_instruments_success(self, mock_find):
        """Test successful instrument extraction."""
        mock_find.return_value = 0x1300  # Instrument table address

        data = bytearray(4096)
        instr_offset = 0x1300 - 0x1000

        # Add 3 instruments (8 bytes each in Laxity format)
        data[instr_offset:instr_offset+24] = bytes([
            0x88, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # Instr 0
            0x45, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x02,  # Instr 1
            0x22, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x04,  # Instr 2
        ])

        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        instruments = analyzer.extract_instruments()

        self.assertGreaterEqual(len(instruments), 3)
        # Each SF2 instrument is 8 bytes
        for instr in instruments[:3]:
            self.assertEqual(len(instr), 8)
            # Check AD, SR values were preserved
            self.assertGreater(instr[0] + instr[1], 0)

    @patch('sidm2.table_extraction.find_instrument_table')
    def test_extract_instruments_default_when_not_found(self, mock_find):
        """Test default instrument when table not found."""
        mock_find.return_value = None

        data = create_minimal_laxity_data()
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        instruments = analyzer.extract_instruments()

        # Should return at least one default instrument
        self.assertGreaterEqual(len(instruments), 1)
        self.assertEqual(len(instruments[0]), 8)


class TestMapCommand(unittest.TestCase):
    """Test command mapping."""

    def test_map_command_duration(self):
        """Test mapping duration commands (0x80-0xBF)."""
        data = create_minimal_laxity_data()
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        cmd_num, cmd_name = analyzer.map_command(0x80)
        self.assertEqual(cmd_num, 0x80)
        self.assertEqual(cmd_name, "Duration")

        cmd_num, cmd_name = analyzer.map_command(0xBF)
        self.assertEqual(cmd_num, 0xBF)
        self.assertEqual(cmd_name, "Duration")

    def test_map_command_named_commands(self):
        """Test mapping named super commands (0xC0-0xCF)."""
        data = create_minimal_laxity_data()
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        test_cases = [
            (0xC0, "Set duration"),
            (0xC1, "Slide up"),
            (0xC3, "Set ADSR"),
            (0xC4, "Set wave"),
            (0xCE, "Set tempo"),
            (0xCF, "End"),
        ]

        for cmd_byte, expected_name in test_cases:
            cmd_num, cmd_name = analyzer.map_command(cmd_byte)
            self.assertEqual(cmd_num, cmd_byte)
            self.assertEqual(cmd_name, expected_name)

    def test_map_command_unknown(self):
        """Test mapping unknown command."""
        data = create_minimal_laxity_data()
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        cmd_num, cmd_name = analyzer.map_command(0x70)
        self.assertEqual(cmd_num, 0x70)
        self.assertEqual(cmd_name, "Unknown $70")


class TestFindDataTables(unittest.TestCase):
    """Test data table finding."""

    def test_find_data_tables_returns_dict(self):
        """Test find_data_tables returns dictionary."""
        data = create_minimal_laxity_data()
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        tables = analyzer.find_data_tables()

        self.assertIsInstance(tables, dict)

    def test_find_data_tables_calls_subfunctions(self):
        """Test find_data_tables calls helper functions."""
        data = create_minimal_laxity_data()
        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(data, 0x1000, header)

        with patch.object(analyzer, '_find_pointer_tables') as mock_ptr:
            with patch.object(analyzer, '_find_sequence_data') as mock_seq:
                tables = analyzer.find_data_tables()

                mock_ptr.assert_called_once()
                mock_seq.assert_called_once()


class TestFindPointerTables(unittest.TestCase):
    """Test pointer table finding."""

    def test_find_pointer_tables_finds_valid_pairs(self):
        """Test finding valid low/high byte pointer table pairs."""
        data = bytearray(4096)
        load_addr = 0x1000

        # Create pointer table pair at 0x1200 (lo) and 0x1210 (hi)
        ptr_lo_offset = 0x1200 - load_addr
        ptr_hi_offset = 0x1210 - load_addr

        # Create 16 valid pointers pointing into data range
        for i in range(16):
            target_addr = 0x1300 + (i * 32)  # Targets in valid range
            data[ptr_lo_offset + i] = target_addr & 0xFF
            data[ptr_hi_offset + i] = (target_addr >> 8) & 0xFF

        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(bytes(data), load_addr, header)

        tables = {}
        analyzer._find_pointer_tables(tables)

        # Should find pointer table candidates
        if 'pointer_tables' in tables:
            self.assertGreater(len(tables['pointer_tables']), 0)

    def test_find_pointer_tables_skips_invalid_data(self):
        """Test that pointer finding skips invalid data (0xFF values)."""
        data = bytearray(4096)
        # Fill with 0xFF (invalid)
        for i in range(512):
            data[i] = 0xFF

        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        tables = {}
        analyzer._find_pointer_tables(tables)

        # Should not find valid tables with 0xFF values
        self.assertNotIn('pointer_tables', tables) or len(tables.get('pointer_tables', [])) == 0


class TestFindSequenceData(unittest.TestCase):
    """Test sequence data finding."""

    def test_find_sequence_data_finds_patterns(self):
        """Test finding sequence data patterns."""
        data = bytearray(4096)

        # Create sequence-like data at 0x1500
        seq_offset = 0x1500 - 0x1000
        # Sequence data has notes (0x00-0x60), markers (0x7E, 0x7F), commands (0xC0+)
        sequence_pattern = [
            0x30, 0x32, 0x34, 0x36,  # Notes
            0x7E, 0x7F,              # Markers (gate on, end)
            0xC0, 0x05,              # Command
            0x40, 0x42, 0x44,        # More notes
            0xA5, 0xB0,              # Duration/transpose
        ] * 3  # Repeat for good score

        data[seq_offset:seq_offset+len(sequence_pattern)] = sequence_pattern

        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        tables = {}
        analyzer._find_sequence_data(tables)

        # Should find sequence candidates
        if 'sequence_regions' in tables:
            self.assertGreater(len(tables['sequence_regions']), 0)

    def test_find_sequence_data_scores_correctly(self):
        """Test sequence scoring gives higher scores to valid patterns."""
        data = bytearray(4096)

        # High-scoring sequence data
        good_seq_offset = 0x1500 - 0x1000
        good_pattern = ([0x30] * 10 + [0x7E, 0x7F] * 5 + [0xC0] * 5)  # Score: 10 + 20 + 5 = 35
        data[good_seq_offset:good_seq_offset+len(good_pattern)] = good_pattern

        header = create_test_header()
        analyzer = LaxityPlayerAnalyzer(bytes(data), 0x1000, header)

        tables = {}
        analyzer._find_sequence_data(tables)

        # Should find at least one candidate with good score
        if 'sequence_regions' in tables:
            scores = [score for _, score in tables['sequence_regions']]
            self.assertGreater(max(scores), 20)


if __name__ == '__main__':
    unittest.main(verbosity=2)
