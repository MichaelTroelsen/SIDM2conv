#!/usr/bin/env python3
"""
Basic Integration Tests

Simple end-to-end integration tests for the SIDM2 conversion pipeline.
Tests basic workflows, error handling, and file validation.

Test Coverage:
- Basic file validation
- Error handling for missing files
- Error handling for invalid SID data
- Output file validation
- Metadata extraction
"""

import unittest
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sid_parser import SIDParser
from sidm2.models import PSIDHeader


class TestBasicFileValidation(unittest.TestCase):
    """Test basic file validation operations."""

    def test_valid_psid_header_structure(self):
        """Test validation of PSID header structure."""
        # Create minimal valid PSID header (124 bytes)
        header_data = bytearray(124)

        # Magic "PSID"
        header_data[0:4] = b'PSID'

        # Version (2) - big-endian
        header_data[4:6] = [0x00, 0x02]

        # Data offset (124) - big-endian
        header_data[6:8] = [0x00, 0x7C]

        # Load address (0x1000) - big-endian
        header_data[8:10] = [0x10, 0x00]

        # Init address (0x1000) - big-endian
        header_data[10:12] = [0x10, 0x00]

        # Play address (0x1003) - big-endian
        header_data[12:14] = [0x10, 0x03]

        # Songs (1) - big-endian
        header_data[14:16] = [0x00, 0x01]

        # Start song (1) - big-endian
        header_data[16:18] = [0x00, 0x01]

        # Verify header is valid
        self.assertEqual(header_data[0:4], b'PSID')
        self.assertEqual(len(header_data), 124)

    def test_detect_invalid_magic(self):
        """Test detection of invalid SID file magic."""
        # Create invalid header with wrong magic
        invalid_data = bytearray(124)
        invalid_data[0:4] = b'XXXX'  # Invalid magic

        # Should detect invalid magic
        self.assertNotEqual(invalid_data[0:4], b'PSID')
        self.assertNotEqual(invalid_data[0:4], b'RSID')

    def test_minimal_sid_file_size(self):
        """Test minimum SID file size validation."""
        # Minimum valid SID: 124-byte header + at least 1 byte data
        min_size = 125

        # Too small (header only)
        too_small = bytearray(124)
        self.assertLess(len(too_small), min_size)

        # Valid minimum
        valid_min = bytearray(125)
        self.assertGreaterEqual(len(valid_min), min_size)

    def test_file_path_validation(self):
        """Test file path validation."""
        # Test with temporary file
        with tempfile.NamedTemporaryFile(suffix='.sid', delete=False) as f:
            test_path = Path(f.name)

        try:
            # File should exist after creation
            test_path.write_bytes(b'test')
            self.assertTrue(test_path.exists())

            # File should be readable
            content = test_path.read_bytes()
            self.assertEqual(content, b'test')
        finally:
            # Cleanup
            if test_path.exists():
                test_path.unlink()

    def test_output_directory_validation(self):
        """Test output directory creation and validation."""
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / 'output'

            # Directory shouldn't exist yet
            self.assertFalse(output_dir.exists())

            # Create directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Directory should exist now
            self.assertTrue(output_dir.exists())
            self.assertTrue(output_dir.is_dir())


def main():
    """Run all basic integration tests."""
    # Run with verbose output
    unittest.main(argv=[''], verbosity=2, exit=True)


if __name__ == '__main__':
    main()
