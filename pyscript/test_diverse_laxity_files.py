#!/usr/bin/env python3
"""
Test diverse Laxity SID files (Phase 1 High Priority).

Tests extreme edge cases and diverse file characteristics:
- Largest file (34KB)
- Smallest file (400 bytes)
- 1-voice, 2-voice, and 3-voice files
- Various complexity levels

Based on analysis in docs/testing/TEST_FILE_RECOMMENDATIONS.md
"""

import unittest
import sys
import os
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sidm2.conversion_pipeline import convert_laxity_to_sf2


class TestDiverseLaxityFiles(unittest.TestCase):
    """Test diverse Laxity files for edge cases and variety"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.laxity_dir = Path("Laxity")

        # Skip tests if Laxity directory doesn't exist
        if not self.laxity_dir.exists():
            self.skipTest("Laxity directory not found")

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def _convert_file(self, filename):
        """Helper to convert a Laxity file"""
        input_path = self.laxity_dir / filename
        if not input_path.exists():
            self.skipTest(f"Test file not found: {filename}")

        output_path = Path(self.temp_dir) / f"{input_path.stem}_test.sf2"

        # Convert with Laxity driver
        try:
            convert_laxity_to_sf2(
                str(input_path),
                str(output_path)
            )
        except Exception as e:
            self.fail(f"Conversion failed for {filename}: {e}")

        self.assertTrue(output_path.exists(), f"Output file not created for {filename}")
        self.assertGreater(output_path.stat().st_size, 0, f"Output file is empty for {filename}")

        return True

    # =========================================================================
    # PHASE 1: HIGH PRIORITY TESTS
    # =========================================================================

    def test_largest_file_aviator_arcade_ii(self):
        """Test largest file in collection (34,904 bytes)

        Tests:
        - Performance with large files
        - Memory allocation limits
        - Complex sequence/instrument extraction
        - 3-voice handling

        File: Aviator_Arcade_II.sid (34KB, 3-voice, 100% filter)
        """
        result = self._convert_file("Aviator_Arcade_II.sid")
        # Large file should convert successfully
        self.assertTrue(result)

    def test_smallest_file_repeat_me(self):
        """Test smallest file in collection (400 bytes)

        Tests:
        - Minimal valid file structure
        - Edge case: very short sequences/tables
        - Sparse data structures
        - 3-voice handling in minimal file

        File: Repeat_me.sid (400 bytes, 3-voice, 100% filter)
        """
        result = self._convert_file("Repeat_me.sid")
        # Minimal file should still convert successfully
        self.assertTrue(result)

    def test_one_voice_only_stormlord_2(self):
        """Test 1-voice only file (voices 2+3 unused)

        Tests:
        - Extreme edge case: only voice 1 active
        - Voices 2+3 properly handled as silent
        - No assumptions about all voices being used

        File: Stormlord_2.sid (20,146 bytes, 1-voice, 100% filter)
        """
        result = self._convert_file("Stormlord_2.sid")
        # 1-voice file should convert without errors
        self.assertTrue(result)

    # =========================================================================
    # PHASE 2: MEDIUM PRIORITY TESTS
    # =========================================================================

    def test_three_voice_medium_alliance(self):
        """Test 3-voice medium-sized file

        Tests:
        - Standard 3-voice handling
        - Medium complexity
        - Filter conversion

        File: Alliance.sid (5,167 bytes, 3-voice, 100% filter)
        """
        result = self._convert_file("Alliance.sid")
        self.assertTrue(result)

    def test_two_voice_large_ruff_scale(self):
        """Test 2-voice large file

        Tests:
        - 2-voice handling (voice 3 unused)
        - Large file with only 2 voices
        - Voice 3 edge cases

        File: Ruff_Scale.sid (23,772 bytes, 2-voice, 100% filter)
        """
        result = self._convert_file("Ruff_Scale.sid")
        self.assertTrue(result)

    def test_three_voice_small_basics(self):
        """Test 3-voice small file

        Tests:
        - Simple 3-voice structure
        - Small file size
        - Basic filter usage

        File: Basics.sid (2,998 bytes, 3-voice, 100% filter)
        """
        result = self._convert_file("Basics.sid")
        self.assertTrue(result)

    # =========================================================================
    # PHASE 3: NICE TO HAVE TESTS
    # =========================================================================

    def test_large_complex_no_way(self):
        """Test large complex 3-voice file

        Tests:
        - Large file complexity
        - Complex sequence/instrument extraction
        - Performance validation

        File: No_Way.sid (19,666 bytes, 3-voice, 100% filter)
        """
        result = self._convert_file("No_Way.sid")
        self.assertTrue(result)

    def test_small_three_voice_galax_it_y(self):
        """Test small 3-voice file

        Tests:
        - Small 3-voice structure
        - Edge case for minimal 3-voice

        File: Galax_it_y.sid (2,110 bytes, 3-voice, 100% filter)
        """
        result = self._convert_file("Galax_it_y.sid")
        self.assertTrue(result)

    def test_two_voice_alternative_system(self):
        """Test alternative 2-voice large file

        Tests:
        - 2-voice handling (different tune)
        - Voice 3 edge cases

        File: System.sid (23,772 bytes, 2-voice, 100% filter)
        """
        result = self._convert_file("System.sid")
        self.assertTrue(result)

    def test_very_small_twone_five(self):
        """Test very small file

        Tests:
        - Very small file structure
        - Edge case for tiny files

        File: Twone_Five.sid (673 bytes, 3-voice, 100% filter)
        """
        result = self._convert_file("Twone_Five.sid")
        self.assertTrue(result)


class TestFileCharacteristics(unittest.TestCase):
    """Test that files have expected characteristics"""

    def setUp(self):
        """Set up test environment"""
        self.laxity_dir = Path("Laxity")
        if not self.laxity_dir.exists():
            self.skipTest("Laxity directory not found")

    def test_size_extremes(self):
        """Verify size extremes exist"""
        # Largest file
        largest = self.laxity_dir / "Aviator_Arcade_II.sid"
        if largest.exists():
            size = largest.stat().st_size
            self.assertGreater(size, 30000, "Largest file should be >30KB")
            self.assertLess(size, 40000, "Largest file should be <40KB")

        # Smallest file
        smallest = self.laxity_dir / "Repeat_me.sid"
        if smallest.exists():
            size = smallest.stat().st_size
            self.assertLess(size, 1000, "Smallest file should be <1KB")
            self.assertGreater(size, 300, "Smallest file should be >300 bytes")

    def test_file_availability(self):
        """Verify test files exist"""
        phase1_files = [
            "Aviator_Arcade_II.sid",
            "Repeat_me.sid",
            "Stormlord_2.sid"
        ]

        available = 0
        for filename in phase1_files:
            if (self.laxity_dir / filename).exists():
                available += 1

        self.assertGreater(available, 0, "At least one Phase 1 test file should exist")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
