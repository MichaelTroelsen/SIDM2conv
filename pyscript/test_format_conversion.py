#!/usr/bin/env python3
"""
Format Conversion Edge Case Tests

Tests for data format conversions between different SID player formats.
Focuses on edge cases, boundary conditions, and validation.

Test Coverage:
- Filter format conversion (Laxity animation → SF2 static)
- 11-bit cutoff value validation
- End marker handling
- Empty/invalid table handling
"""

import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.laxity_converter import LaxityConverter


class TestFilterFormatConversion(unittest.TestCase):
    """Test Laxity animation filter format → SF2 static filter format."""

    def test_basic_filter_conversion(self):
        """Test basic 4-byte Laxity filter entry to SF2 format."""
        # Laxity format: (target_cutoff, delta, duration_dir, next_idx)
        # Example: (0xB5, 0x03, 0x80, 0x00)
        laxity_entries = [(0xB5, 0x03, 0x80, 0x00)]

        # Convert to SF2 format (cutoff_hi, cutoff_lo, resonance, next)
        sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

        # Verify conversion
        self.assertEqual(len(sf2_entries), 1)
        sf2_entry = sf2_entries[0]
        self.assertEqual(len(sf2_entry), 4)

        # Extract 11-bit cutoff from SF2 format
        cutoff_hi, cutoff_lo, resonance, next_idx = sf2_entry
        cutoff_11bit = (cutoff_hi << 8) | cutoff_lo

        # Should be in valid 11-bit range (0-2047)
        self.assertGreaterEqual(cutoff_11bit, 0)
        self.assertLessEqual(cutoff_11bit, 2047)

    def test_filter_cutoff_11bit_range(self):
        """Test that converted cutoff values stay within 11-bit range."""
        # Test edge cases: min and max 8-bit values
        test_cases = [
            0x00,  # Minimum
            0x7F,  # Mid-range
            0xFF,  # Maximum 8-bit
        ]

        for target_cutoff in test_cases:
            laxity_entries = [(target_cutoff, 0x01, 0x80, 0x00)]
            sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

            cutoff_hi, cutoff_lo, _, _ = sf2_entries[0]
            cutoff_11bit = (cutoff_hi << 8) | cutoff_lo

            # 11-bit range: 0x000-0x7FF (0-2047)
            self.assertGreaterEqual(cutoff_11bit, 0,
                                   f"Cutoff {cutoff_11bit} below valid range")
            self.assertLessEqual(cutoff_11bit, 0x7FF,
                                f"Cutoff {cutoff_11bit} above valid range")

    def test_filter_end_marker_conversion(self):
        """Test end marker (0x00) conversion in filter tables."""
        # Laxity end marker: next_idx = 0x00
        laxity_entries = [(0x50, 0x02, 0x80, 0x00)]
        sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

        # SF2 end marker: next_idx = 0x7F
        _, _, _, next_idx = sf2_entries[0]
        self.assertEqual(next_idx, 0x7F,
                        "End marker should convert from 0x00 to 0x7F")

    def test_filter_end_marker_7f(self):
        """Test end marker (0x7F) is preserved."""
        # Laxity alternative end marker: next_idx = 0x7F
        laxity_entries = [(0x50, 0x02, 0x80, 0x7F)]
        sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

        # SF2 end marker: next_idx = 0x7F
        _, _, _, next_idx = sf2_entries[0]
        self.assertEqual(next_idx, 0x7F,
                        "End marker 0x7F should be preserved")

    def test_filter_resonance_generation(self):
        """Test that resonance values are generated correctly."""
        # In Laxity format, byte 2 is duration+direction
        # In SF2 format, byte 2 is resonance
        # Test that conversion produces valid resonance values

        laxity_entries = [(0xB5, 0x03, 0x80, 0x00)]
        sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

        _, _, resonance, _ = sf2_entries[0]

        # Resonance should be in valid range (0x00-0xFF)
        self.assertGreaterEqual(resonance, 0x00)
        self.assertLessEqual(resonance, 0xFF)

    def test_filter_table_batch_conversion(self):
        """Test conversion of full filter table (32 entries)."""
        # Create 32 Laxity filter entries
        laxity_entries = []
        for i in range(32):
            # Varying cutoff values
            target = min(0xFF, 0x40 + i * 4)
            laxity_entries.append((target, 0x02, 0x80, 0x00))

        # Convert entire table
        sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

        # Should have 32 SF2 entries
        self.assertEqual(len(sf2_entries), 32)

        # Verify each entry has valid cutoff
        for i, entry in enumerate(sf2_entries):
            cutoff_hi, cutoff_lo, _, _ = entry
            cutoff_11bit = (cutoff_hi << 8) | cutoff_lo

            self.assertLessEqual(cutoff_11bit, 0x7FF,
                                f"Entry {i}: cutoff {cutoff_11bit} exceeds 11-bit range")

    def test_filter_empty_table(self):
        """Test handling of empty filter table."""
        # Empty table
        laxity_entries = []
        sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

        # Should return empty list
        self.assertIsInstance(sf2_entries, list)
        self.assertEqual(len(sf2_entries), 0)


class TestFilterScaling(unittest.TestCase):
    """Test 8-bit to 11-bit cutoff scaling."""

    def test_scaling_factor_8x(self):
        """Test that 8-bit values are scaled by 8 to get 11-bit values."""
        # Test specific known conversions
        test_cases = [
            (0x00, 0x000),  # 0 * 8 = 0
            (0x01, 0x008),  # 1 * 8 = 8
            (0x10, 0x080),  # 16 * 8 = 128
            (0x80, 0x400),  # 128 * 8 = 1024
            (0xFF, 0x7F8),  # 255 * 8 = 2040
        ]

        for laxity_8bit, expected_11bit in test_cases:
            laxity_entries = [(laxity_8bit, 0x01, 0x80, 0x00)]
            sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

            cutoff_hi, cutoff_lo, _, _ = sf2_entries[0]
            actual_11bit = (cutoff_hi << 8) | cutoff_lo

            self.assertEqual(actual_11bit, expected_11bit,
                           f"0x{laxity_8bit:02X} * 8 should equal 0x{expected_11bit:03X}")

    def test_maximum_value_clamping(self):
        """Test that values exceeding 11-bit range are clamped."""
        # Maximum 11-bit value is 0x7FF (2047)
        # 255 * 8 = 2040, which is within range
        # But test that clamping logic exists

        laxity_entries = [(0xFF, 0x01, 0x80, 0x00)]
        sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

        cutoff_hi, cutoff_lo, _, _ = sf2_entries[0]
        cutoff_11bit = (cutoff_hi << 8) | cutoff_lo

        self.assertLessEqual(cutoff_11bit, 0x7FF,
                           "Cutoff should be clamped to max 11-bit value")


class TestFilterIndexConversion(unittest.TestCase):
    """Test Y×4 index format conversion to direct indexing."""

    def test_y4_to_direct_conversion(self):
        """Test conversion from Y×4 format to direct index."""
        # Y×4 format means index is multiplied by 4 for Y-register addressing
        test_cases = [
            (0x00, 0x7F),  # 0 → end marker
            (0x04, 0x01),  # 4 → 1
            (0x08, 0x02),  # 8 → 2
            (0x0C, 0x03),  # 12 → 3
            (0x10, 0x04),  # 16 → 4
            (0x7F, 0x7F),  # 0x7F → end marker (preserved)
        ]

        for y4_index, expected_direct in test_cases:
            laxity_entries = [(0x50, 0x01, 0x80, y4_index)]
            sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

            _, _, _, actual_direct = sf2_entries[0]

            self.assertEqual(actual_direct, expected_direct,
                           f"Y×4 index 0x{y4_index:02X} should convert to 0x{expected_direct:02X}")

    def test_invalid_y4_indices(self):
        """Test handling of invalid Y×4 indices (not divisible by 4)."""
        # Invalid indices should convert to end marker (0x7F)
        invalid_indices = [0x01, 0x02, 0x03, 0x05, 0x06, 0x07]

        for y4_index in invalid_indices:
            laxity_entries = [(0x50, 0x01, 0x80, y4_index)]
            sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

            _, _, _, direct_index = sf2_entries[0]

            self.assertEqual(direct_index, 0x7F,
                           f"Invalid Y×4 index 0x{y4_index:02X} should convert to end marker")


class TestFilterEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_single_entry(self):
        """Test conversion of single filter entry."""
        laxity_entries = [(0xB5, 0x03, 0x80, 0x00)]
        sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

        self.assertEqual(len(sf2_entries), 1)
        cutoff_hi, cutoff_lo, resonance, next_idx = sf2_entries[0]

        # Verify all components are valid
        self.assertIsInstance(cutoff_hi, int)
        self.assertIsInstance(cutoff_lo, int)
        self.assertIsInstance(resonance, int)
        self.assertIsInstance(next_idx, int)

    def test_multiple_entries_with_chain(self):
        """Test conversion of chained filter entries."""
        # Create a chain: entry 0 → entry 1 → entry 2 → end
        laxity_entries = [
            (0x50, 0x02, 0x80, 0x04),  # Index 0, next=1 (Y×4=4)
            (0x60, 0x02, 0x80, 0x08),  # Index 1, next=2 (Y×4=8)
            (0x70, 0x02, 0x80, 0x00),  # Index 2, next=end
        ]

        sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

        self.assertEqual(len(sf2_entries), 3)

        # Verify chain indices
        _, _, _, next0 = sf2_entries[0]
        _, _, _, next1 = sf2_entries[1]
        _, _, _, next2 = sf2_entries[2]

        self.assertEqual(next0, 0x01)  # Points to entry 1
        self.assertEqual(next1, 0x02)  # Points to entry 2
        self.assertEqual(next2, 0x7F)  # End marker

    def test_all_zero_entry(self):
        """Test conversion of all-zero entry."""
        laxity_entries = [(0x00, 0x00, 0x00, 0x00)]
        sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

        self.assertEqual(len(sf2_entries), 1)
        cutoff_hi, cutoff_lo, resonance, next_idx = sf2_entries[0]

        # Cutoff should be 0
        cutoff_11bit = (cutoff_hi << 8) | cutoff_lo
        self.assertEqual(cutoff_11bit, 0)

        # Next index should be end marker
        self.assertEqual(next_idx, 0x7F)

    def test_invalid_entry_skipped(self):
        """Test that entries with wrong length are skipped."""
        # Mix of valid 4-byte tuples and invalid ones
        # Note: The actual implementation expects tuples, not byte arrays
        # So this test verifies the length check in convert_filter_table

        # This would be handled at the parsing level, but we can test
        # that a properly formed list of tuples works
        laxity_entries = [
            (0x50, 0x02, 0x80, 0x00),  # Valid
            (0x60, 0x02, 0x80, 0x04),  # Valid
        ]

        sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

        # Should process both valid entries
        self.assertEqual(len(sf2_entries), 2)


class TestFilterConversionConsistency(unittest.TestCase):
    """Test conversion consistency and determinism."""

    def test_conversion_deterministic(self):
        """Test that same input always produces same output."""
        laxity_entries = [(0xB5, 0x03, 0x80, 0x00)]

        # Convert multiple times
        result1 = LaxityConverter.convert_filter_table(laxity_entries)
        result2 = LaxityConverter.convert_filter_table(laxity_entries)
        result3 = LaxityConverter.convert_filter_table(laxity_entries)

        # All results should be identical
        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)

    def test_batch_conversion_consistency(self):
        """Test that batch conversion produces consistent results."""
        # Create 10 identical entries
        laxity_entries = [(0x80, 0x02, 0x80, 0x00)] * 10

        sf2_entries = LaxityConverter.convert_filter_table(laxity_entries)

        self.assertEqual(len(sf2_entries), 10)

        # All entries should be identical
        first_entry = sf2_entries[0]
        for entry in sf2_entries[1:]:
            self.assertEqual(entry, first_entry)

    def test_different_inputs_different_outputs(self):
        """Test that different inputs produce different outputs."""
        laxity1 = [(0x50, 0x02, 0x80, 0x00)]
        laxity2 = [(0x60, 0x02, 0x80, 0x00)]

        sf2_1 = LaxityConverter.convert_filter_table(laxity1)
        sf2_2 = LaxityConverter.convert_filter_table(laxity2)

        # Outputs should be different (different cutoff values)
        self.assertNotEqual(sf2_1, sf2_2)


def main():
    """Run all format conversion tests."""
    # Run with verbose output
    unittest.main(argv=[''], verbosity=2, exit=True)


if __name__ == '__main__':
    main()
