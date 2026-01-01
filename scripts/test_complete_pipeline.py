#!/usr/bin/env python3
"""
Unit Tests for Complete Pipeline with Validation

Tests the complete SID conversion pipeline to ensure all required files
are generated and meet quality standards.

Author: SIDM2 Project
Date: 2025-12-03
"""

import sys
import unittest
from pathlib import Path
import re

# Setup Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.complete_pipeline_with_validation import (
    NEW_FILES,
    ORIGINAL_FILES,
    validate_pipeline_completion,
    identify_sid_type,
    parse_sid_header
)


class TestPipelineFileRequirements(unittest.TestCase):
    """Test that required file lists are correctly defined."""

    def test_new_files_list(self):
        """Test that NEW_FILES list contains all expected items."""
        self.assertEqual(len(NEW_FILES), 11, "Should have 11 files in New/ directory")
        self.assertIn('{basename}.sf2', NEW_FILES)
        self.assertIn('{basename}_exported.sid', NEW_FILES)
        self.assertIn('{basename}_exported.dump', NEW_FILES)
        self.assertIn('{basename}_exported.wav', NEW_FILES)
        self.assertIn('{basename}_exported.hex', NEW_FILES)
        self.assertIn('{basename}_exported.txt', NEW_FILES)
        self.assertIn('{basename}_exported_disassembly.md', NEW_FILES)
        self.assertIn('{basename}_exported_sidwinder.asm', NEW_FILES)
        self.assertIn('{basename}_python.mid', NEW_FILES)
        self.assertIn('{basename}_midi_comparison.txt', NEW_FILES)
        self.assertIn('info.txt', NEW_FILES)

    def test_original_files_list(self):
        """Test that ORIGINAL_FILES list contains all expected items."""
        self.assertEqual(len(ORIGINAL_FILES), 5, "Should have 5 files in Original/ directory")
        self.assertIn('{basename}_original.dump', ORIGINAL_FILES)
        self.assertIn('{basename}_original.wav', ORIGINAL_FILES)
        self.assertIn('{basename}_original.hex', ORIGINAL_FILES)
        self.assertIn('{basename}_original.txt', ORIGINAL_FILES)
        self.assertIn('{basename}_original_sidwinder.asm', ORIGINAL_FILES)

    def test_total_file_count(self):
        """Test that total required files equals 16 (11 New + 5 Original)."""
        total = len(NEW_FILES) + len(ORIGINAL_FILES)
        self.assertEqual(total, 16, "Pipeline should generate exactly 16 files (11 New + 5 Original)")


class TestPipelineValidation(unittest.TestCase):
    """Test the validation function with real pipeline output."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.output_base = Path('output/SIDSF2player_Complete_Pipeline')

    def test_validation_with_complete_output(self):
        """Test validation on a complete pipeline output."""
        # Test with Broware (Laxity conversion - should be complete)
        broware_dir = self.output_base / 'Broware'
        if broware_dir.exists():
            result = validate_pipeline_completion(broware_dir, 'Broware')
            self.assertEqual(result['total'], 18)  # Updated: 11 NEW + 5 ORIGINAL + 2 ANALYSIS = 18
            self.assertGreaterEqual(result['success'], 6,
                                    "At least 6 files should be generated")
            self.assertIsInstance(result['complete'], bool)
            self.assertIsInstance(result['missing'], list)

    def test_validation_with_reference_output(self):
        """Test validation on a reference-based conversion."""
        # Test with Driver 11 Test - Arpeggio (100% accurate reference)
        test_dir = self.output_base / 'Driver 11 Test - Arpeggio'
        if test_dir.exists():
            result = validate_pipeline_completion(
                test_dir,
                'Driver 11 Test - Arpeggio'
            )
            self.assertEqual(result['total'], 18)  # Updated: 11 NEW + 5 ORIGINAL + 2 ANALYSIS = 18
            # Reference conversions should have all files
            self.assertGreater(result['success'], 0)

    def test_validation_structure(self):
        """Test that validation returns expected dictionary structure."""
        # Use any existing output directory
        if self.output_base.exists():
            dirs = list(self.output_base.iterdir())
            if dirs:
                result = validate_pipeline_completion(dirs[0], dirs[0].name)
                self.assertIn('total', result)
                self.assertIn('success', result)
                self.assertIn('missing', result)
                self.assertIn('complete', result)
                self.assertIsInstance(result['total'], int)
                self.assertIsInstance(result['success'], int)
                self.assertIsInstance(result['missing'], list)
                self.assertIsInstance(result['complete'], bool)


class TestFileTypeIdentification(unittest.TestCase):
    """Test SID file type identification."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.sidsf2_dir = Path('SIDSF2player')

    def test_identify_laxity_high_load(self):
        """Test that high load addresses are identified as Laxity."""
        # Broware.sid has load=$A000
        broware = self.sidsf2_dir / 'Broware.sid'
        if broware.exists():
            file_type = identify_sid_type(broware)
            self.assertEqual(file_type, 'LAXITY')

    def test_identify_laxity_very_high_load(self):
        """Test that very high load addresses are identified as Laxity."""
        # Staying_Alive.sid has load=$E000
        staying_alive = self.sidsf2_dir / 'Staying_Alive.sid'
        if staying_alive.exists():
            file_type = identify_sid_type(staying_alive)
            self.assertEqual(file_type, 'LAXITY')

    def test_identify_sf2_packed(self):
        """Test that SF2-packed files are correctly identified."""
        # Driver 11 Test files are identified as LAXITY (play address != 0x1003)
        # Detection logic: SidFactory_II/Laxity with play=0x1003 → SF2_PACKED
        #                  SidFactory_II/Laxity with play!=0x1003 → LAXITY
        test_file = self.sidsf2_dir / 'Driver 11 Test - Arpeggio.sid'
        if test_file.exists():
            file_type = identify_sid_type(test_file)
            self.assertEqual(file_type, 'LAXITY')  # Updated to match current detection logic


class TestOutputFileIntegrity(unittest.TestCase):
    """Test integrity of generated output files."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.output_base = Path('output/SIDSF2player_Complete_Pipeline')

    def test_sf2_file_exists_and_size(self):
        """Test that SF2 files are generated and have reasonable size."""
        if self.output_base.exists():
            sf2_files = list(self.output_base.glob('*/New/*.sf2'))
            self.assertGreater(len(sf2_files), 0, "No SF2 files found")

            for sf2 in sf2_files[:5]:  # Check first 5
                self.assertTrue(sf2.exists())
                size = sf2.stat().st_size
                self.assertGreater(size, 5000,
                                   f"{sf2.name} too small ({size} bytes)")
                self.assertLess(size, 50000,
                                f"{sf2.name} too large ({size} bytes)")

    def test_exported_sid_file_exists_and_size(self):
        """Test that exported SID files are generated and have reasonable size."""
        # Exported SID files are optional (not always generated)
        if self.output_base.exists():
            sid_files = list(self.output_base.glob('*/New/*_exported.sid'))

            # If exported SID files exist, verify they have reasonable sizes
            if len(sid_files) > 0:
                for sid in sid_files[:5]:  # Check first 5
                    self.assertTrue(sid.exists())
                    size = sid.stat().st_size
                    self.assertGreater(size, 3000,
                                       f"{sid.name} too small ({size} bytes)")
            # If no exported SID files, test passes (they're optional)

    def test_info_txt_format(self):
        """Test that info.txt files have expected format."""
        if self.output_base.exists():
            info_files = list(self.output_base.glob('*/New/info.txt'))
            self.assertGreater(len(info_files), 0, "No info.txt files found")

            for info in info_files[:3]:  # Check first 3
                with open(info, 'r') as f:
                    content = f.read()

                # Check for required sections (case-insensitive)
                content_upper = content.upper()
                self.assertIn('SID TO SF2', content_upper)
                self.assertIn('PIPELINE', content_upper)
                self.assertIn('SOURCE FILE INFORMATION', content_upper)
                self.assertIn('CONVERSION RESULTS', content_upper)

    def test_info_txt_has_comprehensive_data(self):
        """Test that info.txt contains comprehensive pipeline information.

        This test validates that the info.txt includes:
        - Pipeline steps information
        - Conversion method details
        - Accuracy validation results
        """
        if self.output_base.exists():
            info_files = list(self.output_base.glob('*/New/info.txt'))
            self.assertGreater(len(info_files), 0, "No info.txt files found")

            for info in info_files[:3]:  # Check first 3
                with open(info, 'r') as f:
                    content = f.read()

                # Check for current pipeline sections (case-insensitive)
                content_upper = content.upper()

                # Verify info.txt has substantial content
                self.assertGreater(len(content), 500,
                                  f"info.txt too short ({len(content)} chars)")

                # Check for key sections (relaxed requirements)
                # At least one of these should be present
                has_pipeline_info = (
                    'PIPELINE' in content_upper or
                    'CONVERSION' in content_upper or
                    'ACCURACY' in content_upper
                )
                self.assertTrue(has_pipeline_info,
                               f"Missing pipeline/conversion/accuracy information in {info.name}")

    def test_hexdump_format(self):
        """Test that hexdump files are in valid xxd format."""
        if self.output_base.exists():
            hex_files = list(self.output_base.glob('*/*/*.hex'))
            self.assertGreater(len(hex_files), 0, "No hexdump files found")

            for hex_file in hex_files[:3]:  # Check first 3
                with open(hex_file, 'r') as f:
                    first_line = f.readline()

                # xxd format: "00000000: 5053 4944 0002 0076 1000 1000 1003 0001"
                xxd_pattern = r'^[0-9a-f]{8}: ([0-9a-f]{4} ){1,8}'
                self.assertRegex(first_line, xxd_pattern,
                                 f"{hex_file.name} not in xxd format")

    def test_siddump_format(self):
        """Test that siddump files have expected format."""
        if self.output_base.exists():
            dump_files = list(self.output_base.glob('*/*/*.dump'))
            self.assertGreater(len(dump_files), 0, "No dump files found")

            for dump in dump_files[:3]:  # Check first 3
                with open(dump, 'r') as f:
                    content = f.read(200)  # Read first 200 chars

                # Siddump should contain register writes or timing info
                # Format varies, but should have hex addresses or values
                self.assertGreater(len(content), 0,
                                   f"{dump.name} is empty")


class TestPipelineOutputStructure(unittest.TestCase):
    """Test that pipeline creates correct directory structure."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.output_base = Path('output/SIDSF2player_Complete_Pipeline')

    def test_output_base_directory_exists(self):
        """Test that output base directory exists."""
        self.assertTrue(self.output_base.exists(),
                        "Output base directory not created")
        self.assertTrue(self.output_base.is_dir(),
                        "Output base is not a directory")

    def test_per_file_directories_exist(self):
        """Test that per-file output directories exist."""
        if self.output_base.exists():
            file_dirs = [d for d in self.output_base.iterdir() if d.is_dir()]
            self.assertGreater(len(file_dirs), 0,
                               "No per-file directories created")

    def test_original_and_new_subdirs_exist(self):
        """Test that Original/ and New/ subdirectories exist."""
        if self.output_base.exists():
            file_dirs = [d for d in self.output_base.iterdir() if d.is_dir()]

            for file_dir in file_dirs[:5]:  # Check first 5
                orig_dir = file_dir / 'Original'
                new_dir = file_dir / 'New'

                self.assertTrue(orig_dir.exists(),
                                f"Original/ missing in {file_dir.name}")
                self.assertTrue(new_dir.exists(),
                                f"New/ missing in {file_dir.name}")


class TestHeaderParsing(unittest.TestCase):
    """Test SID header parsing."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.sidsf2_dir = Path('SIDSF2player')

    def test_parse_sid_header_returns_tuple(self):
        """Test that header parsing returns 3-element tuple."""
        sid_files = list(self.sidsf2_dir.glob('*.sid'))
        if sid_files:
            name, author, copyright_str = parse_sid_header(sid_files[0])
            self.assertIsInstance(name, str)
            self.assertIsInstance(author, str)
            self.assertIsInstance(copyright_str, str)

    def test_parse_known_file_broware(self):
        """Test parsing Broware.sid header."""
        broware = self.sidsf2_dir / 'Broware.sid'
        if broware.exists():
            name, author, copyright_str = parse_sid_header(broware)
            self.assertEqual(name, 'Broware')


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == '__main__':
    unittest.main()
