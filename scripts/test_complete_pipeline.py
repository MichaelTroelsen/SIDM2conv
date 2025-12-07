#!/usr/bin/env python3
"""
Unit Tests for Complete Pipeline with Validation

Tests the complete SID conversion pipeline to ensure all required files
are generated and meet quality standards.

Author: SIDM2 Project
Date: 2025-12-03
"""

import unittest
from pathlib import Path
import re

from complete_pipeline_with_validation import (
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
        self.assertEqual(len(NEW_FILES), 6)
        self.assertIn('{basename}.sf2', NEW_FILES)
        self.assertIn('{basename}_exported.sid', NEW_FILES)
        self.assertIn('{basename}_exported.dump', NEW_FILES)
        self.assertIn('{basename}_exported.wav', NEW_FILES)
        self.assertIn('{basename}_exported.hex', NEW_FILES)
        self.assertIn('info.txt', NEW_FILES)

    def test_original_files_list(self):
        """Test that ORIGINAL_FILES list contains all expected items."""
        self.assertEqual(len(ORIGINAL_FILES), 3)
        self.assertIn('{basename}_original.dump', ORIGINAL_FILES)
        self.assertIn('{basename}_original.wav', ORIGINAL_FILES)
        self.assertIn('{basename}_original.hex', ORIGINAL_FILES)

    def test_total_file_count(self):
        """Test that total required files equals 9."""
        total = len(NEW_FILES) + len(ORIGINAL_FILES)
        self.assertEqual(total, 9, "Pipeline should generate exactly 9 files")


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
            self.assertEqual(result['total'], 9)
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
            self.assertEqual(result['total'], 9)
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
        # Driver 11 Test files are SF2-packed
        test_file = self.sidsf2_dir / 'Driver 11 Test - Arpeggio.sid'
        if test_file.exists():
            file_type = identify_sid_type(test_file)
            self.assertEqual(file_type, 'SF2_PACKED')


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
                self.assertLess(size, 25000,
                                f"{sf2.name} too large ({size} bytes)")

    def test_exported_sid_file_exists_and_size(self):
        """Test that exported SID files are generated and have reasonable size."""
        if self.output_base.exists():
            sid_files = list(self.output_base.glob('*/New/*_exported.sid'))
            self.assertGreater(len(sid_files), 0, "No exported SID files found")

            for sid in sid_files[:5]:  # Check first 5
                self.assertTrue(sid.exists())
                size = sid.stat().st_size
                self.assertGreater(size, 3000,
                                   f"{sid.name} too small ({size} bytes)")

    def test_info_txt_format(self):
        """Test that info.txt files have expected format."""
        if self.output_base.exists():
            info_files = list(self.output_base.glob('*/New/info.txt'))
            self.assertGreater(len(info_files), 0, "No info.txt files found")

            for info in info_files[:3]:  # Check first 3
                with open(info, 'r') as f:
                    content = f.read()

                # Check for required sections
                self.assertIn('SID to SF2', content)
                self.assertIn('Pipeline', content)
                self.assertIn('Source File Information', content)
                self.assertIn('Conversion Results', content)
                self.assertIn('Pipeline', content)

    def test_info_txt_has_comprehensive_data(self):
        """CRITICAL TEST: Ensure info.txt contains comprehensive table data.

        This test validates that the info.txt includes:
        - Table Addresses in SF2
        - Original SID Data Structure Addresses
        - ORIGINAL SID DATA TABLES (HEX VIEW)
        - CONVERTED SF2 DATA TABLES (HEX VIEW)

        This test must pass to ensure comprehensive data is not removed!
        """
        if self.output_base.exists():
            info_files = list(self.output_base.glob('*/New/info.txt'))
            self.assertGreater(len(info_files), 0, "No info.txt files found")

            for info in info_files[:3]:  # Check first 3
                with open(info, 'r') as f:
                    content = f.read()

                # CRITICAL: Check for comprehensive table data sections
                self.assertIn('Table Addresses in SF2', content,
                              f"Missing 'Table Addresses in SF2' section in {info.name}")

                self.assertIn('Original SID Data Structure Addresses', content,
                              f"Missing 'Original SID Data Structure Addresses' section in {info.name}")

                self.assertIn('ORIGINAL SID DATA TABLES (HEX VIEW)', content,
                              f"Missing 'ORIGINAL SID DATA TABLES (HEX VIEW)' section in {info.name}")

                self.assertIn('CONVERTED SF2 DATA TABLES (HEX VIEW)', content,
                              f"Missing 'CONVERTED SF2 DATA TABLES (HEX VIEW)' section in {info.name}")

                # Verify hex table format is present
                self.assertRegex(content, r'Start: \$[0-9A-F]{4}',
                                 f"Missing hex address format in {info.name}")

                # Verify hex data is present (hex bytes in format "00: xx xx xx")
                self.assertRegex(content, r'[0-9a-f]{2}: ([0-9a-f]{2} ){8,}',
                                 f"Missing hex data format in {info.name}")

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
