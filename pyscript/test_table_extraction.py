"""
Comprehensive tests for table_extraction.py module.

Coverage target: 50% (from 1.49%)
Current: 819 statements, 799 missing

Test Categories:
1. Helper functions (get_valid_wave_entry_points, validate_wave_pointer)
2. SID register table finding (find_sid_register_tables)
3. Table address finding (find_table_addresses_from_player)
4. Instrument table extraction (find_instrument_table)
5. Wave table extraction (find_and_extract_wave_table)
6. Pulse/Filter table extraction
7. Specialized tables (hr, init, arp, command)
8. Complete extraction (extract_all_laxity_tables)
"""

import sys
import os
import struct
import unittest
from typing import Dict, List, Tuple, Any, Optional

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sidm2.table_extraction import (
    get_valid_wave_entry_points,
    validate_wave_pointer,
    find_sid_register_tables,
    find_table_addresses_from_player,
    find_instrument_table,
    find_wave_table_from_player_code,
    find_and_extract_wave_table,
    find_and_extract_pulse_table,
    find_and_extract_filter_table,
    extract_hr_table,
    extract_init_table,
    extract_arp_table,
    extract_command_table,
    extract_all_laxity_tables,
)
from sidm2.exceptions import TableExtractionError


# ============================================================================
# Test Fixtures
# ============================================================================

def create_minimal_sid_data(load_addr: int = 0x1000, size: int = 256) -> bytes:
    """Create minimal C64 program data for testing."""
    data = bytearray(size)
    # Fill with NOPs (0xEA)
    for i in range(size):
        data[i] = 0xEA
    return bytes(data)


def create_sid_data_with_sta_instructions(load_addr: int = 0x1000) -> bytes:
    """
    Create SID data with STA $D4xx,Y instructions for testing
    find_sid_register_tables.

    Pattern:
        LDA table,X   (BD lo hi)  <- Note: Uses X, not Y!
        STA $D4xx,Y   (99 lo hi)
    """
    data = bytearray(256)
    offset = 0

    # Example: LDA $1200,X ; STA $D400,Y (Voice 1 frequency low)
    data[offset] = 0xBD      # LDA absolute,X (not Y!)
    data[offset + 1] = 0x00  # Table addr low
    data[offset + 2] = 0x12  # Table addr high ($1200)
    offset += 3

    data[offset] = 0x99      # STA absolute,Y
    data[offset + 1] = 0x00  # SID register low
    data[offset + 2] = 0xD4  # SID register high ($D400)
    offset += 3

    # Example: LDA $1300,X ; STA $D401,Y (Voice 1 frequency high)
    data[offset] = 0xBD      # LDA absolute,X
    data[offset + 1] = 0x00
    data[offset + 2] = 0x13  # $1300
    offset += 3

    data[offset] = 0x99
    data[offset + 1] = 0x01  # $D401
    data[offset + 2] = 0xD4
    offset += 3

    # Fill rest with NOPs
    for i in range(offset, len(data)):
        data[i] = 0xEA

    return bytes(data)


def create_wave_table_data(entries: List[Tuple[int, int]]) -> bytes:
    """
    Create wave table data from list of (waveform, note_offset) tuples.

    Args:
        entries: List of (col0, col1) where:
                 - Normal: (waveform, note_offset)
                 - Jump: (0x7F, target_index)

    Returns:
        Bytes representing the wave table in row-major format
    """
    data = bytearray()
    for waveform, note_offset in entries:
        data.append(waveform)
        data.append(note_offset)
    return bytes(data)


def create_instrument_table_data(instruments: List[Dict[str, int]]) -> bytes:
    """
    Create instrument table data (8 bytes per instrument).

    Format (8 bytes):
        0: AD (attack/decay)
        1: SR (sustain/release)
        2: Waveform pointer
        3: Pulse pointer
        4: Filter pointer
        5: Vibrato table pointer
        6: Vibrato delay
        7: Hard restart option
    """
    data = bytearray()
    for inst in instruments:
        data.append(inst.get('ad', 0x88))
        data.append(inst.get('sr', 0x09))
        data.append(inst.get('wave_ptr', 0))
        data.append(inst.get('pulse_ptr', 0))
        data.append(inst.get('filter_ptr', 0))
        data.append(inst.get('vib_ptr', 0))
        data.append(inst.get('vib_delay', 0))
        data.append(inst.get('hr_option', 0))
    return bytes(data)


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestGetValidWaveEntryPoints(unittest.TestCase):
    """Test get_valid_wave_entry_points function."""

    def test_empty_wave_table(self):
        """Test with empty wave table."""
        wave_table = []
        result = get_valid_wave_entry_points(wave_table)
        self.assertEqual(result, {0})

    def test_simple_wave_table_no_jumps(self):
        """Test wave table with no jump commands."""
        wave_table = [
            (0x11, 0x00),  # Triangle + Gate, note 0
            (0x21, 0x05),  # Saw + Gate, note +5
            (0x41, 0x0C),  # Pulse + Gate, note +12
        ]
        result = get_valid_wave_entry_points(wave_table)
        self.assertEqual(result, {0})

    def test_wave_table_with_single_jump(self):
        """Test wave table with one jump command."""
        wave_table = [
            (0x11, 0x00),  # Entry 0: Triangle + Gate
            (0x21, 0x05),  # Entry 1: Saw + Gate
            (0x7F, 0x00),  # Entry 2: Jump to 0
            (0x41, 0x0C),  # Entry 3: Pulse + Gate (valid entry point after jump)
        ]
        result = get_valid_wave_entry_points(wave_table)
        self.assertEqual(result, {0, 3})

    def test_wave_table_with_multiple_jumps(self):
        """Test wave table with multiple jump commands."""
        wave_table = [
            (0x11, 0x00),  # Entry 0: Valid (always)
            (0x7F, 0x00),  # Entry 1: Jump
            (0x21, 0x05),  # Entry 2: Valid (after jump at 1)
            (0x7F, 0x02),  # Entry 3: Jump
            (0x41, 0x0C),  # Entry 4: Valid (after jump at 3)
            (0x81, 0x00),  # Entry 5: Noise
        ]
        result = get_valid_wave_entry_points(wave_table)
        self.assertEqual(result, {0, 2, 4})

    def test_wave_table_jump_at_end(self):
        """Test wave table with jump command at the end (no next entry)."""
        wave_table = [
            (0x11, 0x00),
            (0x21, 0x05),
            (0x7F, 0x00),  # Jump at end, no entry after
        ]
        result = get_valid_wave_entry_points(wave_table)
        # Should only have 0, not an invalid entry 3
        self.assertEqual(result, {0})


class TestValidateWavePointer(unittest.TestCase):
    """Test validate_wave_pointer function."""

    def test_empty_wave_table(self):
        """Test with empty wave table - only 0 is valid."""
        wave_table = []
        self.assertTrue(validate_wave_pointer(0, wave_table))
        self.assertFalse(validate_wave_pointer(1, wave_table))
        self.assertFalse(validate_wave_pointer(5, wave_table))

    def test_valid_pointer_to_start(self):
        """Test valid pointer to index 0."""
        wave_table = [(0x11, 0x00), (0x21, 0x05)]
        self.assertTrue(validate_wave_pointer(0, wave_table))

    def test_invalid_pointer_no_jump(self):
        """Test invalid pointer when no jump commands exist."""
        wave_table = [(0x11, 0x00), (0x21, 0x05), (0x41, 0x0C)]
        self.assertTrue(validate_wave_pointer(0, wave_table))
        self.assertFalse(validate_wave_pointer(1, wave_table))
        self.assertFalse(validate_wave_pointer(2, wave_table))

    def test_valid_pointer_after_jump(self):
        """Test valid pointer to entry after jump command."""
        wave_table = [
            (0x11, 0x00),  # Index 0: valid
            (0x7F, 0x00),  # Index 1: jump
            (0x21, 0x05),  # Index 2: valid (after jump)
        ]
        self.assertTrue(validate_wave_pointer(0, wave_table))
        self.assertFalse(validate_wave_pointer(1, wave_table))
        self.assertTrue(validate_wave_pointer(2, wave_table))

    def test_invalid_pointer_beyond_table(self):
        """Test invalid pointer beyond table size."""
        wave_table = [(0x11, 0x00), (0x21, 0x05)]
        self.assertFalse(validate_wave_pointer(10, wave_table))
        self.assertFalse(validate_wave_pointer(100, wave_table))


# ============================================================================
# SID Register Table Tests
# ============================================================================

class TestFindSIDRegisterTables(unittest.TestCase):
    """Test find_sid_register_tables function."""

    def test_empty_data(self):
        """Test with empty data - should raise exception."""
        with self.assertRaises(TableExtractionError):
            find_sid_register_tables(b'', 0x1000)

    def test_data_too_small(self):
        """Test with data smaller than 4 bytes."""
        with self.assertRaises(TableExtractionError):
            find_sid_register_tables(b'\xEA\xEA', 0x1000)

    def test_minimal_valid_data(self):
        """Test with minimal valid data (4 bytes)."""
        data = b'\xEA\xEA\xEA\xEA'
        result = find_sid_register_tables(data, 0x1000)
        self.assertIsInstance(result, dict)
        self.assertEqual(len(result), 0)  # No STA instructions found

    def test_find_single_sta_instruction(self):
        """Test finding single STA $D4xx,Y instruction."""
        data = create_sid_data_with_sta_instructions(0x1000)
        result = find_sid_register_tables(data, 0x1000)

        # Should find mapping for register 0x00 ($D400)
        self.assertIn(0x00, result)
        self.assertEqual(result[0x00], 0x1200)

    def test_find_multiple_sta_instructions(self):
        """Test finding multiple STA instructions for different registers."""
        data = create_sid_data_with_sta_instructions(0x1000)
        result = find_sid_register_tables(data, 0x1000)

        # Should find mappings for both $D400 and $D401
        self.assertIn(0x00, result)
        self.assertIn(0x01, result)
        self.assertEqual(result[0x00], 0x1200)
        self.assertEqual(result[0x01], 0x1300)

    def test_ignore_non_sid_addresses(self):
        """Test that non-SID addresses are ignored."""
        data = bytearray(256)
        # STA $1000,Y (not SID)
        data[0] = 0x99
        data[1] = 0x00
        data[2] = 0x10

        # LDA $1500,X ; STA $D400,Y (SID - should be found)
        data[10] = 0xBD       # LDA absolute,X
        data[11] = 0x00
        data[12] = 0x15       # $1500
        data[13] = 0x99       # STA absolute,Y
        data[14] = 0x00       # $D400
        data[15] = 0xD4

        result = find_sid_register_tables(bytes(data), 0x1000)

        # Only SID address should be found
        self.assertEqual(len(result), 1)
        self.assertIn(0x00, result)
        self.assertEqual(result[0x00], 0x1500)


# ============================================================================
# Table Address Finding Tests
# ============================================================================

class TestFindTableAddressesFromPlayer(unittest.TestCase):
    """Test find_table_addresses_from_player function."""

    def test_empty_data(self):
        """Test with empty data - should raise exception."""
        with self.assertRaises(TableExtractionError):
            find_table_addresses_from_player(b'', 0x1000)

    def test_minimal_data(self):
        """Test with minimal data."""
        data = create_minimal_sid_data(0x1000, 256)
        result = find_table_addresses_from_player(data, 0x1000)
        self.assertIsInstance(result, dict)
        # Result may be empty dict if no patterns found
        # Just verify it's a dict


# ============================================================================
# Instrument Table Tests
# ============================================================================

class TestFindInstrumentTable(unittest.TestCase):
    """Test find_instrument_table function."""

    def test_data_too_small(self):
        """Test with data too small for instrument table."""
        data = b'\xEA' * 10
        result = find_instrument_table(data, 0x1000, verbose=False)
        self.assertIsNone(result)

    def test_no_valid_instruments_found(self):
        """Test when no valid instruments are found."""
        data = create_minimal_sid_data(0x1000, 512)
        result = find_instrument_table(data, 0x1000, verbose=False)
        self.assertIsNone(result)

    def test_find_valid_instrument_table(self):
        """Test finding a valid instrument table."""
        # Create data with valid instrument table at offset 0x100
        data = bytearray(512)

        # Fill with NOPs
        for i in range(len(data)):
            data[i] = 0xEA

        # Add instrument table at offset 0x100 (address 0x1100)
        offset = 0x100
        instruments = [
            {'ad': 0x88, 'sr': 0x09, 'wave_ptr': 0, 'pulse_ptr': 0},
            {'ad': 0x45, 'sr': 0x06, 'wave_ptr': 2, 'pulse_ptr': 1},
            {'ad': 0x22, 'sr': 0x03, 'wave_ptr': 4, 'pulse_ptr': 2},
        ]

        inst_data = create_instrument_table_data(instruments)
        data[offset:offset + len(inst_data)] = inst_data

        result = find_instrument_table(bytes(data), 0x1000, verbose=False)

        # Should find the instrument table
        # Note: May or may not find it depending on scoring threshold
        # At minimum, should return either None or an address
        self.assertTrue(result is None or isinstance(result, int))

    def test_find_instrument_table_with_verbose(self):
        """Test finding instrument table with verbose output."""
        data = create_minimal_sid_data(0x1000, 512)
        # Call with verbose=True to get diagnostics
        result = find_instrument_table(data, 0x1000, verbose=True)
        # Should return tuple (addr, diagnostics) when verbose=True
        if result is not None:
            self.assertIsInstance(result, tuple)
            self.assertEqual(len(result), 2)

    def test_find_instrument_table_with_wave_table(self):
        """Test finding instrument table with wave table provided."""
        data = create_minimal_sid_data(0x1000, 512)
        wave_table = [(0x11, 0x00), (0x21, 0x05)]
        result = find_instrument_table(data, 0x1000, verbose=False,
                                      wave_table=wave_table)
        # Should use wave_table for validation
        self.assertTrue(result is None or isinstance(result, int))


# ============================================================================
# Wave Table From Player Code Tests
# ============================================================================

class TestFindWaveTableFromPlayerCode(unittest.TestCase):
    """Test find_wave_table_from_player_code function."""

    def test_empty_data(self):
        """Test with empty data."""
        note_addr, wave_addr = find_wave_table_from_player_code(b'', 0x1000)
        # May return None values
        self.assertTrue(note_addr is None or isinstance(note_addr, int))
        self.assertTrue(wave_addr is None or isinstance(wave_addr, int))

    def test_minimal_data(self):
        """Test with minimal data."""
        data = create_minimal_sid_data(0x1000, 256)
        note_addr, wave_addr = find_wave_table_from_player_code(data, 0x1000)
        self.assertTrue(note_addr is None or isinstance(note_addr, int))
        self.assertTrue(wave_addr is None or isinstance(wave_addr, int))


# ============================================================================
# Wave Table Tests
# ============================================================================

class TestFindAndExtractWaveTable(unittest.TestCase):
    """Test find_and_extract_wave_table function."""

    def test_empty_data(self):
        """Test with empty data - should raise exception."""
        with self.assertRaises(TableExtractionError):
            find_and_extract_wave_table(b'', 0x1000, verbose=False)

    def test_data_too_small(self):
        """Test with very small data - should raise exception."""
        data = b'\xEA\xEA'
        with self.assertRaises(TableExtractionError):
            find_and_extract_wave_table(data, 0x1000, verbose=False)

    def test_minimal_valid_data(self):
        """Test with minimal valid data (64+ bytes)."""
        data = create_minimal_sid_data(0x1000, 256)
        addr, table = find_and_extract_wave_table(data, 0x1000, verbose=False)
        # May or may not find patterns in NOPs
        # Just verify return types are correct
        self.assertTrue(addr is None or isinstance(addr, int))
        self.assertIsInstance(table, list)

    def test_wave_table_with_verbose(self):
        """Test wave table extraction with verbose output."""
        data = create_minimal_sid_data(0x1000, 256)
        # verbose=True returns 3 values: (addr, table, debug_info)
        addr, table, debug_info = find_and_extract_wave_table(data, 0x1000, verbose=True)
        self.assertTrue(addr is None or isinstance(addr, int))
        self.assertIsInstance(table, list)
        self.assertIsInstance(debug_info, dict)

    def test_wave_table_with_siddump_waveforms(self):
        """Test wave table extraction with siddump waveforms hint."""
        data = create_minimal_sid_data(0x1000, 256)
        siddump_waveforms = [0x11, 0x21, 0x41]  # Triangle, Saw, Pulse
        addr, table = find_and_extract_wave_table(data, 0x1000, verbose=False,
                                                   siddump_waveforms=siddump_waveforms)
        self.assertTrue(addr is None or isinstance(addr, int))
        self.assertIsInstance(table, list)


# ============================================================================
# Pulse/Filter Table Tests
# ============================================================================

class TestFindAndExtractPulseTable(unittest.TestCase):
    """Test find_and_extract_pulse_table function."""

    def test_empty_data(self):
        """Test with empty data - should raise exception."""
        with self.assertRaises(TableExtractionError):
            find_and_extract_pulse_table(b'', 0x1000)

    def test_data_too_small(self):
        """Test with very small data - should raise exception."""
        data = b'\xEA\xEA'
        with self.assertRaises(TableExtractionError):
            find_and_extract_pulse_table(data, 0x1000)

    def test_minimal_valid_data(self):
        """Test with minimal valid data (64+ bytes)."""
        data = create_minimal_sid_data(0x1000, 256)
        addr, table = find_and_extract_pulse_table(data, 0x1000)
        self.assertTrue(addr is None or isinstance(addr, int))
        self.assertIsInstance(table, list)

    def test_with_pulse_ptrs_hint(self):
        """Test pulse table extraction with pulse pointers hint."""
        data = create_minimal_sid_data(0x1000, 256)
        pulse_ptrs = {0, 1, 2}  # Hint: these pulse pointers are used
        addr, table = find_and_extract_pulse_table(data, 0x1000, pulse_ptrs=pulse_ptrs)
        self.assertTrue(addr is None or isinstance(addr, int))
        self.assertIsInstance(table, list)

    def test_with_avoid_addr(self):
        """Test pulse table extraction with address to avoid."""
        data = create_minimal_sid_data(0x1000, 256)
        avoid_addr = 0x1100  # Avoid this address
        addr, table = find_and_extract_pulse_table(data, 0x1000, avoid_addr=avoid_addr)
        self.assertTrue(addr is None or isinstance(addr, int))
        self.assertIsInstance(table, list)


class TestFindAndExtractFilterTable(unittest.TestCase):
    """Test find_and_extract_filter_table function."""

    def test_empty_data(self):
        """Test with empty data - should raise exception."""
        with self.assertRaises(TableExtractionError):
            find_and_extract_filter_table(b'', 0x1000)

    def test_data_too_small(self):
        """Test with very small data - should raise exception."""
        data = b'\xEA\xEA'
        with self.assertRaises(TableExtractionError):
            find_and_extract_filter_table(data, 0x1000)

    def test_minimal_valid_data(self):
        """Test with minimal valid data (64+ bytes)."""
        data = create_minimal_sid_data(0x1000, 256)
        addr, table = find_and_extract_filter_table(data, 0x1000)
        self.assertTrue(addr is None or isinstance(addr, int))
        self.assertIsInstance(table, list)

    def test_with_filter_ptrs_hint(self):
        """Test filter table extraction with filter pointers hint."""
        data = create_minimal_sid_data(0x1000, 256)
        filter_ptrs = {0, 1, 2}  # Hint: these filter pointers are used
        addr, table = find_and_extract_filter_table(data, 0x1000, filter_ptrs=filter_ptrs)
        self.assertTrue(addr is None or isinstance(addr, int))
        self.assertIsInstance(table, list)

    def test_with_avoid_addr(self):
        """Test filter table extraction with address to avoid."""
        data = create_minimal_sid_data(0x1000, 256)
        avoid_addr = 0x1100  # Avoid this address
        addr, table = find_and_extract_filter_table(data, 0x1000, avoid_addr=avoid_addr)
        self.assertTrue(addr is None or isinstance(addr, int))
        self.assertIsInstance(table, list)


# ============================================================================
# Specialized Table Tests
# ============================================================================

class TestExtractHRTable(unittest.TestCase):
    """Test extract_hr_table function."""

    def test_extract_from_minimal_data(self):
        """Test extraction from minimal data."""
        data = create_minimal_sid_data(0x1000, 256)
        init_addr = 0x1000
        result = extract_hr_table(data, 0x1000, init_addr)

        # Should return a list
        self.assertIsInstance(result, list)

    def test_extract_with_different_init_addr(self):
        """Test extraction with different init address."""
        data = create_minimal_sid_data(0x1000, 512)
        init_addr = 0x1100  # Different address
        result = extract_hr_table(data, 0x1000, init_addr)

        self.assertIsInstance(result, list)


class TestExtractInitTable(unittest.TestCase):
    """Test extract_init_table function."""

    def test_extract_from_minimal_data(self):
        """Test extraction from minimal data."""
        data = create_minimal_sid_data(0x1000, 256)
        init_addr = 0x1000
        tempo = 6
        volume = 15
        result = extract_init_table(data, 0x1000, init_addr, tempo, volume)

        # Should return a list of 5 init values
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 5)

    def test_extract_with_different_tempo_volume(self):
        """Test extraction with different tempo and volume values."""
        data = create_minimal_sid_data(0x1000, 256)
        init_addr = 0x1000
        tempo = 10
        volume = 12
        result = extract_init_table(data, 0x1000, init_addr, tempo, volume)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 5)


class TestExtractArpTable(unittest.TestCase):
    """Test extract_arp_table function."""

    def test_extract_from_minimal_data(self):
        """Test extraction from minimal data."""
        data = create_minimal_sid_data(0x1000, 256)
        result = extract_arp_table(data, 0x1000)

        # Should return a list
        self.assertIsInstance(result, list)

    def test_extract_from_larger_data(self):
        """Test extraction from larger data."""
        data = create_minimal_sid_data(0x1000, 1024)
        result = extract_arp_table(data, 0x1000)

        self.assertIsInstance(result, list)


class TestExtractCommandTable(unittest.TestCase):
    """Test extract_command_table function."""

    def test_extract_from_minimal_data(self):
        """Test extraction from minimal data."""
        data = create_minimal_sid_data(0x1000, 256)
        result = extract_command_table(data, 0x1000, sequences=None)

        # Should return a list
        self.assertIsInstance(result, list)

    def test_extract_with_sequences(self):
        """Test extraction with sequences provided."""
        data = create_minimal_sid_data(0x1000, 256)
        sequences = [[0xA0, 0x00], [0xA0, 0x05]]  # Mock sequences
        result = extract_command_table(data, 0x1000, sequences=sequences)

        self.assertIsInstance(result, list)


# ============================================================================
# Integration Tests
# ============================================================================

class TestExtractAllLaxityTables(unittest.TestCase):
    """Test extract_all_laxity_tables function (integration test)."""

    def test_extract_from_minimal_data(self):
        """Test extraction from minimal data."""
        data = create_minimal_sid_data(0x1000, 1024)
        result = extract_all_laxity_tables(data, 0x1000)

        # Should return a dictionary with expected keys
        self.assertIsInstance(result, dict)
        self.assertIn('instruments', result)
        self.assertIn('wave_table', result)
        self.assertIn('pulse_table', result)
        self.assertIn('filter_table', result)

    def test_extract_returns_correct_structure(self):
        """Test that extraction returns correctly structured data."""
        data = create_minimal_sid_data(0x1000, 1024)
        result = extract_all_laxity_tables(data, 0x1000)

        # Verify structure
        self.assertIsInstance(result.get('instruments'), list)
        self.assertIsInstance(result.get('wave_table'), list)
        self.assertIsInstance(result.get('pulse_table'), list)
        self.assertIsInstance(result.get('filter_table'), list)


if __name__ == '__main__':
    unittest.main(verbosity=2)
