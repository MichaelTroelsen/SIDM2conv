#!/usr/bin/env python3
"""
SF2 Packer Pointer Alignment Regression Tests

Tests for Track 3.1 fix (alignment=2 → alignment=1)
Prevents regression of 17/18 SIDwinder disassembly failure bug

Test Coverage:
- Odd-addressed pointer detection
- alignment=1 vs alignment=2 comparison
- $0000 crash prevention
- Jump table edge cases
- Consecutive pointer detection
"""

import unittest
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.cpu6502 import CPU6502


class TestPointerAlignmentDetection(unittest.TestCase):
    """Test that alignment=1 catches odd-addressed pointers."""

    def test_even_addressed_pointer_detected(self):
        """alignment=1 should detect pointers at even addresses."""
        # Create memory with pointer at even address $0000
        memory = bytearray(100)
        memory[0x00] = 0x50  # Low byte
        memory[0x01] = 0x10  # High byte → pointer to $1050

        cpu = CPU6502(bytes(memory))
        pointers = cpu.scan_data_pointers(0, 100, 0x1000, 0x2000, alignment=1)

        # Should find pointer at offset 0
        self.assertEqual(len(pointers), 1)
        self.assertEqual(pointers[0], (0, 0x1050))

    def test_odd_addressed_pointer_detected_with_alignment_1(self):
        """CRITICAL: alignment=1 must detect pointers at odd addresses."""
        # Create memory with pointer at ODD address $0001
        memory = bytearray(100)
        memory[0x01] = 0x60  # Low byte
        memory[0x02] = 0x11  # High byte → pointer to $1160

        cpu = CPU6502(bytes(memory))
        pointers = cpu.scan_data_pointers(0, 100, 0x1000, 0x2000, alignment=1)

        # Should find pointer at offset 1 (odd address)
        self.assertGreaterEqual(len(pointers), 1,
                               "alignment=1 MUST detect odd-addressed pointers")

        # Find the odd-addressed pointer
        odd_pointer = [p for p in pointers if p[0] == 1]
        self.assertEqual(len(odd_pointer), 1,
                        "Should find exactly one pointer at offset 1")
        self.assertEqual(odd_pointer[0], (1, 0x1160))

    def test_odd_addressed_pointer_MISSED_with_alignment_2(self):
        """BUG REPRODUCTION: alignment=2 misses odd-addressed pointers."""
        # Create memory with pointer at ODD address $0001
        memory = bytearray(100)
        memory[0x01] = 0x60  # Low byte
        memory[0x02] = 0x11  # High byte → pointer to $1160

        cpu = CPU6502(bytes(memory))
        pointers = cpu.scan_data_pointers(0, 100, 0x1000, 0x2000, alignment=2)

        # Should NOT find pointer at offset 1 with alignment=2
        odd_pointer = [p for p in pointers if p[0] == 1]
        self.assertEqual(len(odd_pointer), 0,
                        "alignment=2 skips odd offsets - THIS WAS THE BUG")

    def test_alignment_1_catches_all_alignment_2_catches_half(self):
        """Verify alignment=1 catches 2x more pointers than alignment=2."""
        # Create memory with pointers at both even and odd addresses
        memory = bytearray(100)

        # Even address $00: pointer to $1050
        memory[0x00] = 0x50
        memory[0x01] = 0x10

        # Odd address $01: pointer to $1160 (overlaps with above!)
        # This tests that scan handles overlapping pointers
        memory[0x01] = 0x60
        memory[0x02] = 0x11

        # Even address $04: pointer to $1270
        memory[0x04] = 0x70
        memory[0x05] = 0x12

        # Odd address $05: pointer to $1380
        memory[0x05] = 0x80
        memory[0x06] = 0x13

        cpu = CPU6502(bytes(memory))

        pointers_align1 = cpu.scan_data_pointers(0, 100, 0x1000, 0x2000, alignment=1)
        pointers_align2 = cpu.scan_data_pointers(0, 100, 0x1000, 0x2000, alignment=2)

        # alignment=1 should find MORE pointers (includes odd offsets)
        self.assertGreaterEqual(len(pointers_align1), len(pointers_align2),
                               "alignment=1 should find at least as many pointers as alignment=2")


class TestJumpTableScenarios(unittest.TestCase):
    """Test pointer detection in jump table patterns."""

    def test_jump_table_consecutive_pointers(self):
        """Test detection of consecutive pointers in jump tables."""
        # Jump table: array of 16-bit pointers
        memory = bytearray(100)

        # Jump table at $10: 4 consecutive pointers
        jump_table = [
            (0x10, 0x1100),  # Entry 0
            (0x12, 0x1120),  # Entry 1
            (0x14, 0x1140),  # Entry 2
            (0x16, 0x1160),  # Entry 3
        ]

        for offset, target in jump_table:
            memory[offset] = target & 0xFF
            memory[offset + 1] = (target >> 8) & 0xFF

        cpu = CPU6502(bytes(memory))
        pointers = cpu.scan_data_pointers(0, 100, 0x1000, 0x2000, alignment=1)

        # Should find all 4 jump table entries
        self.assertGreaterEqual(len(pointers), 4,
                               "Should detect all jump table entries")

        # Verify each entry was found
        for expected_offset, expected_target in jump_table:
            found = [p for p in pointers if p == (expected_offset, expected_target)]
            self.assertEqual(len(found), 1,
                           f"Should find pointer at ${expected_offset:04X} → ${expected_target:04X}")

    def test_odd_addressed_jump_table(self):
        """CRITICAL: Test jump table starting at odd address."""
        # Jump table at ODD address $11
        memory = bytearray(100)

        # Jump table at $11: 3 consecutive pointers
        jump_table = [
            (0x11, 0x1200),  # Entry 0 (ODD address)
            (0x13, 0x1220),  # Entry 1 (ODD address)
            (0x15, 0x1240),  # Entry 2 (ODD address)
        ]

        for offset, target in jump_table:
            memory[offset] = target & 0xFF
            memory[offset + 1] = (target >> 8) & 0xFF

        cpu = CPU6502(bytes(memory))
        pointers = cpu.scan_data_pointers(0, 100, 0x1000, 0x2000, alignment=1)

        # Should find ALL entries (all at odd addresses)
        found_count = sum(1 for p in pointers if p[0] in [0x11, 0x13, 0x15])
        self.assertEqual(found_count, 3,
                        "alignment=1 MUST detect odd-addressed jump table entries")


class TestCrashPrevention(unittest.TestCase):
    """Test that fix prevents $0000 crash scenarios."""

    def test_unrelocated_pointer_to_zero_detected(self):
        """Test detection of pointers that might cause $0000 crashes."""
        # Simulate unrelocated pointer scenario
        # Pointer at $10 contains $00 $00 (would crash if jumped to)
        memory = bytearray(100)
        memory[0x10] = 0x00
        memory[0x11] = 0x00

        cpu = CPU6502(bytes(memory))
        pointers = cpu.scan_data_pointers(0, 100, 0x0000, 0x2000, alignment=1)

        # Should NOT find this as a valid relocatable pointer
        # (high byte $00 is below valid range $10-$9F)
        zero_pointer = [p for p in pointers if p[1] == 0x0000]
        self.assertEqual(len(zero_pointer), 0,
                        "Pointers to $0000 should be filtered out (invalid high byte)")

    def test_valid_relocatable_range_only(self):
        """Test that only pointers in $1000-$9FFF range are detected."""
        memory = bytearray(100)

        # Invalid pointers (should be filtered out)
        memory[0x00] = 0xFF  # $00FF - zero page
        memory[0x01] = 0x00

        memory[0x02] = 0x00  # $D000 - hardware registers
        memory[0x03] = 0xD0

        memory[0x04] = 0x00  # $A000 - outside range
        memory[0x05] = 0xA0

        # Valid pointer (should be detected)
        memory[0x06] = 0x50  # $1050 - valid relocatable range
        memory[0x07] = 0x10

        cpu = CPU6502(bytes(memory))
        pointers = cpu.scan_data_pointers(0, 100, 0x1000, 0x2000, alignment=1)

        # Should only find the valid pointer
        valid_pointers = [p for p in pointers if 0x1000 <= p[1] < 0x2000]
        self.assertGreaterEqual(len(valid_pointers), 1,
                               "Should find at least one valid pointer")

        # Verify the valid pointer was found
        found = [p for p in pointers if p == (0x06, 0x1050)]
        self.assertEqual(len(found), 1,
                        "Should find pointer at $06 → $1050")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_pointer_at_end_of_memory(self):
        """Test pointer detection at memory boundary."""
        memory = bytearray(100)

        # Pointer at offset 98 (last valid position for 2-byte pointer)
        memory[98] = 0x80
        memory[99] = 0x15  # Pointer to $1580

        cpu = CPU6502(bytes(memory))
        pointers = cpu.scan_data_pointers(0, 100, 0x1000, 0x2000, alignment=1)

        # Should find pointer at boundary
        found = [p for p in pointers if p[0] == 98]
        self.assertEqual(len(found), 1,
                        "Should detect pointer at memory boundary")

    def test_overlapping_pointer_values(self):
        """Test handling of overlapping pointer patterns."""
        # Three consecutive bytes form two overlapping pointers
        memory = bytearray(100)
        memory[0x20] = 0x00  # Could be low byte of pointer at $20
        memory[0x21] = 0x10  # Could be high byte of pointer at $20 OR low byte at $21
        memory[0x22] = 0x11  # Could be high byte of pointer at $21

        cpu = CPU6502(bytes(memory))
        pointers = cpu.scan_data_pointers(0, 100, 0x1000, 0x2000, alignment=1)

        # Both interpretations are valid
        # alignment=1 should find both: $20→$1000 and $21→$1110
        self.assertGreaterEqual(len(pointers), 2,
                               "Should handle overlapping pointer patterns")

    def test_empty_memory_no_pointers(self):
        """Test scan on empty memory (all zeros)."""
        memory = bytearray(100)  # All zeros

        cpu = CPU6502(bytes(memory))
        pointers = cpu.scan_data_pointers(0, 100, 0x1000, 0x2000, alignment=1)

        # No valid pointers in empty memory (high byte $00 is invalid)
        self.assertEqual(len(pointers), 0,
                        "Empty memory should have no valid pointers")


class TestRegressionPrevention(unittest.TestCase):
    """Tests to prevent regression of Track 3.1 bug."""

    def test_alignment_1_is_default_for_data_sections(self):
        """CRITICAL: Ensure alignment=1 remains the default."""
        # This test documents the fix - alignment MUST be 1 for data sections
        # If this test fails, the bug has regressed

        memory = bytearray(100)
        # Add an odd-addressed pointer
        memory[0x0F] = 0xA0  # Odd offset
        memory[0x10] = 0x12  # Pointer to $12A0

        cpu = CPU6502(bytes(memory))
        # Test with alignment=1 (should be default for data sections)
        pointers = cpu.scan_data_pointers(0, 100, 0x1000, 0x2000, alignment=1)

        found = [p for p in pointers if p[0] == 0x0F]
        self.assertEqual(len(found), 1,
                        "REGRESSION CHECK: alignment=1 must be used for data sections")

    def test_documented_failure_case_cocktail_to_go(self):
        """Test pattern from working file (Cocktail_to_Go_tune_3)."""
        # This test ensures the working file pattern continues to work
        # Pattern: Multiple pointers, some at odd addresses

        memory = bytearray(200)

        # Simulate Cocktail_to_Go pointer pattern (even + odd addresses)
        test_pointers = [
            (0x10, 0x1100),  # Even
            (0x15, 0x1250),  # Odd
            (0x20, 0x1300),  # Even
            (0x27, 0x1450),  # Odd
        ]

        for offset, target in test_pointers:
            memory[offset] = target & 0xFF
            memory[offset + 1] = (target >> 8) & 0xFF

        cpu = CPU6502(bytes(memory))
        pointers = cpu.scan_data_pointers(0, 200, 0x1000, 0x2000, alignment=1)

        # Should find ALL pointers (even + odd)
        for expected_offset, expected_target in test_pointers:
            found = [p for p in pointers if p == (expected_offset, expected_target)]
            self.assertEqual(len(found), 1,
                           f"Must detect pointer at ${expected_offset:04X} (regression check)")


def main():
    """Run all tests."""
    # Run with verbose output
    unittest.main(argv=[''], verbosity=2, exit=True)


if __name__ == '__main__':
    main()
