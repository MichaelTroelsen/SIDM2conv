"""
Unit tests for Laxity → SF2 instrument transposition.

Tests the instrument_transposition module which handles conversion of
Laxity row-major 8×8 to SF2 column-major 32×6 instrument format.

Run: python pyscript/test_instrument_transposition.py -v
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.instrument_transposition import (
    transpose_instruments,
    transpose_instruments_from_dict,
    get_instrument_from_sf2_table,
    InstrumentTransposer
)


class TestInstrumentTransposerClass(unittest.TestCase):
    """Test InstrumentTransposer class"""

    def test_transposer_initialization(self):
        """Test transposer initializes correctly"""
        transposer = InstrumentTransposer()
        self.assertEqual(transposer.SF2_NUM_INSTRUMENTS, 32)
        self.assertEqual(transposer.SF2_TABLE_SIZE, 256)
        self.assertEqual(transposer.SF2_BYTES_PER_INSTRUMENT, 6)

    def test_laxity_byte_offsets(self):
        """Test Laxity byte offset constants"""
        transposer = InstrumentTransposer()
        self.assertEqual(transposer.LAXITY_AD, 0)
        self.assertEqual(transposer.LAXITY_SR, 1)
        self.assertEqual(transposer.LAXITY_WAVEFORM, 2)
        self.assertEqual(transposer.LAXITY_PULSE, 3)
        self.assertEqual(transposer.LAXITY_FILTER, 4)
        self.assertEqual(transposer.LAXITY_FILTER_WAVEFORM, 5)
        self.assertEqual(transposer.LAXITY_ARPEGGIO, 6)
        self.assertEqual(transposer.LAXITY_FLAGS, 7)

    def test_sf2_column_offsets(self):
        """Test SF2 column offset constants"""
        transposer = InstrumentTransposer()
        self.assertEqual(transposer.SF2_COL_AD, 0)
        self.assertEqual(transposer.SF2_COL_SR, 1)
        self.assertEqual(transposer.SF2_COL_FLAGS, 2)
        self.assertEqual(transposer.SF2_COL_FILTER, 3)
        self.assertEqual(transposer.SF2_COL_PULSE, 4)
        self.assertEqual(transposer.SF2_COL_WAVE, 5)


class TestBasicTransposition(unittest.TestCase):
    """Test basic instrument transposition"""

    def test_single_instrument_transposition(self):
        """Test transposing a single Laxity instrument"""
        # Laxity instrument 0: AD=0x49, SR=0x80, Wave=0x05, Pulse=0x03, Filter=0x07, Flags=0x40
        laxity_inst = bytes([0x49, 0x80, 0x05, 0x03, 0x07, 0x01, 0x00, 0x40])

        sf2_table = transpose_instruments([laxity_inst])

        # Verify table size
        self.assertEqual(len(sf2_table), 256)

        # Extract instrument 0 from SF2 table
        inst = get_instrument_from_sf2_table(sf2_table, 0)

        # Verify parameters
        self.assertEqual(inst['ad'], 0x49)
        self.assertEqual(inst['sr'], 0x80)
        self.assertEqual(inst['wave'], 0x05)
        self.assertEqual(inst['pulse'], 0x03)
        self.assertEqual(inst['filter'], 0x07)
        self.assertEqual(inst['flags'], 0x40)

    def test_eight_instruments_transposition(self):
        """Test transposing 8 Laxity instruments"""
        # Create 8 test instruments with unique values
        laxity_instruments = []
        for i in range(8):
            # Create instrument with predictable values
            inst = bytes([
                i * 10,      # AD
                i * 11,      # SR
                i,           # Waveform
                i + 1,       # Pulse
                i + 2,       # Filter
                0x00,        # Filter waveform (not used)
                0x00,        # Arpeggio (not used)
                i * 5        # Flags
            ])
            laxity_instruments.append(inst)

        sf2_table = transpose_instruments(laxity_instruments)

        # Verify all 8 instruments
        for i in range(8):
            inst = get_instrument_from_sf2_table(sf2_table, i)
            self.assertEqual(inst['ad'], i * 10, f"Instrument {i} AD mismatch")
            self.assertEqual(inst['sr'], i * 11, f"Instrument {i} SR mismatch")
            self.assertEqual(inst['wave'], i, f"Instrument {i} Wave mismatch")
            self.assertEqual(inst['pulse'], i + 1, f"Instrument {i} Pulse mismatch")
            self.assertEqual(inst['filter'], i + 2, f"Instrument {i} Filter mismatch")
            self.assertEqual(inst['flags'], i * 5, f"Instrument {i} Flags mismatch")

    def test_empty_instruments_list(self):
        """Test transposing empty instruments list (all defaults)"""
        sf2_table = transpose_instruments([])

        # Should create table with all defaults
        self.assertEqual(len(sf2_table), 256)

        # First 4 instruments should have waveform defaults (tri, saw, pulse, noise)
        inst0 = get_instrument_from_sf2_table(sf2_table, 0)
        inst1 = get_instrument_from_sf2_table(sf2_table, 1)
        inst2 = get_instrument_from_sf2_table(sf2_table, 2)
        inst3 = get_instrument_from_sf2_table(sf2_table, 3)

        self.assertEqual(inst0['wave'], 0x01)  # Triangle
        self.assertEqual(inst1['wave'], 0x02)  # Sawtooth
        self.assertEqual(inst2['wave'], 0x00)  # Pulse
        self.assertEqual(inst3['wave'], 0x03)  # Noise


class TestColumnMajorStorage(unittest.TestCase):
    """Test column-major storage format"""

    def test_column_major_layout(self):
        """Test that SF2 table uses column-major storage"""
        # Create 2 test instruments
        inst0 = bytes([0x10, 0x20, 0x30, 0x40, 0x50, 0x00, 0x00, 0x60])
        inst1 = bytes([0x11, 0x21, 0x31, 0x41, 0x51, 0x00, 0x00, 0x61])

        sf2_table = transpose_instruments([inst0, inst1])

        # Column 0 (AD): bytes 0-31
        self.assertEqual(sf2_table[0], 0x10)  # Instrument 0 AD
        self.assertEqual(sf2_table[1], 0x11)  # Instrument 1 AD

        # Column 1 (SR): bytes 32-63
        self.assertEqual(sf2_table[32], 0x20)  # Instrument 0 SR
        self.assertEqual(sf2_table[33], 0x21)  # Instrument 1 SR

        # Column 2 (Flags): bytes 64-95
        self.assertEqual(sf2_table[64], 0x60)  # Instrument 0 Flags
        self.assertEqual(sf2_table[65], 0x61)  # Instrument 1 Flags

        # Column 3 (Filter): bytes 96-127
        self.assertEqual(sf2_table[96], 0x50)  # Instrument 0 Filter
        self.assertEqual(sf2_table[97], 0x51)  # Instrument 1 Filter

        # Column 4 (Pulse): bytes 128-159
        self.assertEqual(sf2_table[128], 0x40)  # Instrument 0 Pulse
        self.assertEqual(sf2_table[129], 0x41)  # Instrument 1 Pulse

        # Column 5 (Wave): bytes 160-191
        self.assertEqual(sf2_table[160], 0x30)  # Instrument 0 Wave
        self.assertEqual(sf2_table[161], 0x31)  # Instrument 1 Wave

    def test_column_calculation_formula(self):
        """Test column-major offset calculation: offset = col * 32 + row"""
        transposer = InstrumentTransposer()

        # Create test instrument
        inst = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x00, 0x00, 0xFF])
        sf2_table = transpose_instruments([inst])

        # Verify formula: offset = col * 32 + row
        for inst_idx in range(1):  # Just check instrument 0
            # Column 0 (AD)
            offset = transposer.SF2_COL_AD * 32 + inst_idx
            self.assertEqual(sf2_table[offset], 0xAA)

            # Column 1 (SR)
            offset = transposer.SF2_COL_SR * 32 + inst_idx
            self.assertEqual(sf2_table[offset], 0xBB)

            # Column 2 (Flags)
            offset = transposer.SF2_COL_FLAGS * 32 + inst_idx
            self.assertEqual(sf2_table[offset], 0xFF)

            # Column 3 (Filter)
            offset = transposer.SF2_COL_FILTER * 32 + inst_idx
            self.assertEqual(sf2_table[offset], 0xEE)

            # Column 4 (Pulse)
            offset = transposer.SF2_COL_PULSE * 32 + inst_idx
            self.assertEqual(sf2_table[offset], 0xDD)

            # Column 5 (Wave)
            offset = transposer.SF2_COL_WAVE * 32 + inst_idx
            self.assertEqual(sf2_table[offset], 0xCC)


class TestPaddingDefaults(unittest.TestCase):
    """Test padding with default instruments"""

    def test_padding_to_32_instruments(self):
        """Test that table is padded to 32 instruments"""
        # Create 1 instrument, should pad to 32
        inst = bytes([0x49, 0x80, 0x05, 0x03, 0x07, 0x00, 0x00, 0x40])
        sf2_table = transpose_instruments([inst])

        # Check that instruments 1-31 have defaults
        inst1 = get_instrument_from_sf2_table(sf2_table, 1)
        self.assertEqual(inst1['sr'], 0xF0)  # Default sustain/release

        inst31 = get_instrument_from_sf2_table(sf2_table, 31)
        self.assertEqual(inst31['sr'], 0xF0)  # Default sustain/release

    def test_default_instrument_pattern(self):
        """Test that default instruments cycle through 4 waveforms"""
        sf2_table = transpose_instruments([])

        # Should cycle: Triangle, Sawtooth, Pulse, Noise, Triangle, ...
        expected_waves = [0x01, 0x02, 0x00, 0x03] * 8  # Cycle 8 times = 32 instruments

        for i in range(32):
            inst = get_instrument_from_sf2_table(sf2_table, i)
            self.assertEqual(
                inst['wave'],
                expected_waves[i],
                f"Instrument {i} should have waveform {expected_waves[i]}, got {inst['wave']}"
            )

    def test_default_adsr_values(self):
        """Test default ADSR values"""
        sf2_table = transpose_instruments([])

        # All defaults should have AD=0x00, SR=0xF0
        for i in range(32):
            inst = get_instrument_from_sf2_table(sf2_table, i)
            self.assertEqual(inst['ad'], 0x00)
            self.assertEqual(inst['sr'], 0xF0)


class TestRoundTrip(unittest.TestCase):
    """Test round-trip transposition and extraction"""

    def test_single_instrument_roundtrip(self):
        """Test transpose → extract → verify"""
        original = bytes([0x49, 0x80, 0x05, 0x03, 0x07, 0x01, 0x00, 0x40])

        # Transpose
        sf2_table = transpose_instruments([original])

        # Extract
        extracted = get_instrument_from_sf2_table(sf2_table, 0)

        # Verify (only 6 parameters used in SF2)
        self.assertEqual(extracted['ad'], original[0])
        self.assertEqual(extracted['sr'], original[1])
        self.assertEqual(extracted['wave'], original[2])
        self.assertEqual(extracted['pulse'], original[3])
        self.assertEqual(extracted['filter'], original[4])
        self.assertEqual(extracted['flags'], original[7])

    def test_multiple_instruments_roundtrip(self):
        """Test round-trip for multiple instruments"""
        originals = [
            bytes([i * 10, i * 11, i, i + 1, i + 2, 0, 0, i * 5])
            for i in range(8)
        ]

        sf2_table = transpose_instruments(originals)

        for i, original in enumerate(originals):
            extracted = get_instrument_from_sf2_table(sf2_table, i)

            self.assertEqual(extracted['ad'], original[0])
            self.assertEqual(extracted['sr'], original[1])
            self.assertEqual(extracted['wave'], original[2])
            self.assertEqual(extracted['pulse'], original[3])
            self.assertEqual(extracted['filter'], original[4])
            self.assertEqual(extracted['flags'], original[7])


class TestDictFormatConversion(unittest.TestCase):
    """Test conversion from dict format"""

    def test_transpose_from_dict_single(self):
        """Test transposing single instrument from dict"""
        inst_dict = {
            'ad': 0x49,
            'sr': 0x80,
            'wave_ptr': 0x05,
            'pulse_ptr': 0x03,
            'filter_ptr': 0x07,
            'restart': 0x40  # Maps to flags
        }

        sf2_table = transpose_instruments_from_dict([inst_dict])

        extracted = get_instrument_from_sf2_table(sf2_table, 0)
        self.assertEqual(extracted['ad'], 0x49)
        self.assertEqual(extracted['sr'], 0x80)
        self.assertEqual(extracted['wave'], 0x05)
        self.assertEqual(extracted['pulse'], 0x03)
        self.assertEqual(extracted['filter'], 0x07)
        self.assertEqual(extracted['flags'], 0x40)

    def test_transpose_from_dict_multiple(self):
        """Test transposing multiple instruments from dict"""
        inst_dicts = [
            {'ad': i * 10, 'sr': i * 11, 'wave_ptr': i, 'pulse_ptr': i + 1,
             'filter_ptr': i + 2, 'restart': i * 5}
            for i in range(4)
        ]

        sf2_table = transpose_instruments_from_dict(inst_dicts)

        for i in range(4):
            extracted = get_instrument_from_sf2_table(sf2_table, i)
            self.assertEqual(extracted['ad'], i * 10)
            self.assertEqual(extracted['sr'], i * 11)
            self.assertEqual(extracted['wave'], i)
            self.assertEqual(extracted['pulse'], i + 1)
            self.assertEqual(extracted['filter'], i + 2)
            self.assertEqual(extracted['flags'], i * 5)

    def test_dict_with_missing_fields(self):
        """Test dict with missing fields uses defaults"""
        inst_dict = {'ad': 0x49}  # Only AD specified

        sf2_table = transpose_instruments_from_dict([inst_dict])

        extracted = get_instrument_from_sf2_table(sf2_table, 0)
        self.assertEqual(extracted['ad'], 0x49)
        self.assertEqual(extracted['sr'], 0xF0)  # Default
        self.assertEqual(extracted['wave'], 0x01)  # Default triangle
        self.assertEqual(extracted['pulse'], 0x00)  # Default
        self.assertEqual(extracted['filter'], 0x00)  # Default
        self.assertEqual(extracted['flags'], 0x00)  # Default


class TestParameterMapping(unittest.TestCase):
    """Test correct parameter mapping"""

    def test_laxity_to_sf2_mapping(self):
        """Test Laxity bytes map to correct SF2 columns"""
        # Laxity: AD SR WF PW FL FW AR SP
        # Indices: 0  1  2  3  4  5  6  7
        laxity = bytes([0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0x11, 0x22, 0xFF])

        sf2_table = transpose_instruments([laxity])
        inst = get_instrument_from_sf2_table(sf2_table, 0)

        # Verify mapping
        self.assertEqual(inst['ad'], 0xAA)      # Laxity[0] → SF2 Column 0
        self.assertEqual(inst['sr'], 0xBB)      # Laxity[1] → SF2 Column 1
        self.assertEqual(inst['wave'], 0xCC)    # Laxity[2] → SF2 Column 5
        self.assertEqual(inst['pulse'], 0xDD)   # Laxity[3] → SF2 Column 4
        self.assertEqual(inst['filter'], 0xEE)  # Laxity[4] → SF2 Column 3
        self.assertEqual(inst['flags'], 0xFF)   # Laxity[7] → SF2 Column 2

        # Laxity[5] and Laxity[6] are NOT used in SF2

    def test_unused_laxity_parameters(self):
        """Test that Laxity bytes 5 and 6 are not used"""
        # Set bytes 5 and 6 to non-zero (should be ignored)
        laxity = bytes([0x49, 0x80, 0x05, 0x03, 0x07, 0xFF, 0xFF, 0x40])

        sf2_table = transpose_instruments([laxity])
        inst = get_instrument_from_sf2_table(sf2_table, 0)

        # Verify other parameters are correct (bytes 5 and 6 don't affect output)
        self.assertEqual(inst['ad'], 0x49)
        self.assertEqual(inst['sr'], 0x80)
        self.assertEqual(inst['wave'], 0x05)
        self.assertEqual(inst['flags'], 0x40)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling"""

    def test_invalid_instrument_size(self):
        """Test error when instrument is not 8 bytes"""
        # 7 bytes (too short)
        short_inst = bytes([0x49, 0x80, 0x05, 0x03, 0x07, 0x01, 0x00])

        with self.assertRaises(ValueError) as ctx:
            transpose_instruments([short_inst])

        self.assertIn("8 bytes", str(ctx.exception))

    def test_too_many_instruments_truncation(self):
        """Test truncation when more than 32 instruments"""
        # Create 40 instruments
        instruments = [
            bytes([i, 0, 0, 0, 0, 0, 0, 0])
            for i in range(40)
        ]

        sf2_table = transpose_instruments(instruments)

        # Should be truncated to 32
        inst31 = get_instrument_from_sf2_table(sf2_table, 31)
        self.assertEqual(inst31['ad'], 31)  # Last instrument should be index 31

    def test_instrument_index_out_of_range(self):
        """Test error when extracting invalid instrument index"""
        sf2_table = transpose_instruments([bytes([0] * 8)])

        # Valid range: 0-31
        with self.assertRaises(ValueError) as ctx:
            get_instrument_from_sf2_table(sf2_table, 32)

        self.assertIn("out of range", str(ctx.exception))

        # Negative index
        with self.assertRaises(ValueError):
            get_instrument_from_sf2_table(sf2_table, -1)

    def test_sf2_table_too_small(self):
        """Test error when SF2 table is too small"""
        small_table = bytes([0] * 100)  # Only 100 bytes, need 256

        with self.assertRaises(ValueError) as ctx:
            get_instrument_from_sf2_table(small_table, 0)

        self.assertIn("too small", str(ctx.exception))

    def test_zero_values_instrument(self):
        """Test instrument with all zeros"""
        zero_inst = bytes([0] * 8)
        sf2_table = transpose_instruments([zero_inst])

        inst = get_instrument_from_sf2_table(sf2_table, 0)
        self.assertEqual(inst['ad'], 0)
        self.assertEqual(inst['sr'], 0)
        self.assertEqual(inst['wave'], 0)
        self.assertEqual(inst['pulse'], 0)
        self.assertEqual(inst['filter'], 0)
        self.assertEqual(inst['flags'], 0)

    def test_max_values_instrument(self):
        """Test instrument with maximum values"""
        max_inst = bytes([0xFF] * 8)
        sf2_table = transpose_instruments([max_inst])

        inst = get_instrument_from_sf2_table(sf2_table, 0)
        self.assertEqual(inst['ad'], 0xFF)
        self.assertEqual(inst['sr'], 0xFF)
        self.assertEqual(inst['wave'], 0xFF)
        self.assertEqual(inst['pulse'], 0xFF)
        self.assertEqual(inst['filter'], 0xFF)
        self.assertEqual(inst['flags'], 0xFF)


class TestRealWorldExample(unittest.TestCase):
    """Test with real-world Laxity instrument data"""

    def test_example_from_rosetta_stone(self):
        """Test example from docs/guides/LAXITY_TO_SF2_GUIDE.md"""
        # Example from Rosetta Stone (Instrument 0):
        # $1A6B:  $49 $80 $05 $03 $07 $01 $00 $40
        laxity_inst = bytes([0x49, 0x80, 0x05, 0x03, 0x07, 0x01, 0x00, 0x40])

        sf2_table = transpose_instruments([laxity_inst])

        # Expected SF2 layout (column-major):
        # Column 0 (AD):     $0A03: $49
        # Column 1 (SR):     $0A23: $80
        # Column 2 (Flags):  $0A43: $40
        # Column 3 (Filter): $0A63: $07
        # Column 4 (Pulse):  $0A83: $03
        # Column 5 (Wave):   $0AA3: $05

        # Check column 0 (AD) at offset 0
        self.assertEqual(sf2_table[0], 0x49)

        # Check column 1 (SR) at offset 32
        self.assertEqual(sf2_table[32], 0x80)

        # Check column 2 (Flags) at offset 64
        self.assertEqual(sf2_table[64], 0x40)

        # Check column 3 (Filter) at offset 96
        self.assertEqual(sf2_table[96], 0x07)

        # Check column 4 (Pulse) at offset 128
        self.assertEqual(sf2_table[128], 0x03)

        # Check column 5 (Wave) at offset 160
        self.assertEqual(sf2_table[160], 0x05)


def run_tests():
    """Run all tests with verbose output"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestInstrumentTransposerClass,
        TestBasicTransposition,
        TestColumnMajorStorage,
        TestPaddingDefaults,
        TestRoundTrip,
        TestDictFormatConversion,
        TestParameterMapping,
        TestEdgeCases,
        TestRealWorldExample,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())
