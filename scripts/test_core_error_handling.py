"""
Test suite for core module error handling (v2.5.2).

Tests error handling in:
- sidm2/sid_parser.py
- sidm2/sf2_writer.py
- sidm2/sf2_packer.py

Version: 1.0.0
"""

import unittest
import os
import sys
import tempfile
import struct
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sidm2.sid_parser import SIDParser
from sidm2.sf2_writer import SF2Writer
from sidm2.sf2_packer import SF2Packer
from sidm2 import errors


class TestSIDParserErrorHandling(unittest.TestCase):
    """Test error handling in SIDParser"""

    def setUp(self):
        """Create temporary directory for test files"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_file_not_found_error(self):
        """Test FileNotFoundError for missing SID file"""
        nonexistent_path = os.path.join(self.temp_dir, "nonexistent.sid")

        with self.assertRaises(errors.FileNotFoundError) as context:
            SIDParser(nonexistent_path)

        error = context.exception
        self.assertIn("file", error.message.lower())
        # Check for either "not found" or "could not find"
        error_text = error.what_happened.lower()
        self.assertTrue("not found" in error_text or "could not find" in error_text)
        self.assertTrue(len(error.how_to_fix) > 0)
        self.assertIsNotNone(error.docs_link)

    def test_permission_error_read(self):
        """Test PermissionError when file is not readable"""
        # Create a file
        test_file = os.path.join(self.temp_dir, "test.sid")
        with open(test_file, 'wb') as f:
            f.write(b'PSID' + b'\x00' * 120)

        # On Windows, we can't easily make a file unreadable,
        # so we'll test the error type is correct by checking the class
        # This is more of a smoke test
        try:
            # Try to simulate permission error (platform-dependent)
            if sys.platform != 'win32':
                os.chmod(test_file, 0o000)
                with self.assertRaises(errors.PermissionError):
                    SIDParser(test_file)
        finally:
            # Restore permissions for cleanup
            if sys.platform != 'win32' and os.path.exists(test_file):
                os.chmod(test_file, 0o644)

    def test_invalid_input_file_too_small(self):
        """Test InvalidInputError for file too small"""
        test_file = os.path.join(self.temp_dir, "tiny.sid")
        with open(test_file, 'wb') as f:
            f.write(b'TINY')  # Only 4 bytes, need 124

        with self.assertRaises(errors.InvalidInputError) as context:
            SIDParser(test_file)

        error = context.exception
        self.assertIn("SID file", error.message)
        self.assertIn("4 bytes", str(error))
        self.assertIn("124 bytes", str(error))

    def test_invalid_input_bad_magic_bytes(self):
        """Test InvalidInputError for non-ASCII magic bytes"""
        test_file = os.path.join(self.temp_dir, "bad_magic.sid")
        with open(test_file, 'wb') as f:
            f.write(b'\xFF\xFF\xFF\xFF' + b'\x00' * 120)  # Non-ASCII magic

        with self.assertRaises(errors.InvalidInputError) as context:
            parser = SIDParser(test_file)
            parser.parse_header()

        error = context.exception
        # Should mention either "magic", "header", or "corrupted"
        error_text = (error.message + " " + (error.what_happened or "")).lower()
        self.assertTrue("magic" in error_text or "header" in error_text or "corrupted" in error_text)

    def test_invalid_input_wrong_magic(self):
        """Test InvalidInputError for wrong magic (not PSID/RSID)"""
        test_file = os.path.join(self.temp_dir, "wrong_magic.sid")
        with open(test_file, 'wb') as f:
            f.write(b'FAKE' + b'\x00' * 120)

        with self.assertRaises(errors.InvalidInputError) as context:
            parser = SIDParser(test_file)
            parser.parse_header()

        error = context.exception
        self.assertIn("FAKE", str(error))
        self.assertIn("PSID", str(error) or "RSID" in str(error))

    def test_invalid_input_data_offset_beyond_file(self):
        """Test InvalidInputError for data offset beyond file size"""
        test_file = os.path.join(self.temp_dir, "bad_offset.sid")

        # Create minimal valid PSID header
        with open(test_file, 'wb') as f:
            f.write(b'PSID')  # Magic
            f.write(struct.pack('>H', 2))  # Version 2
            f.write(struct.pack('>H', 9999))  # Data offset way beyond file size
            f.write(b'\x00' * 114)  # Rest of header

        with self.assertRaises(errors.InvalidInputError) as context:
            parser = SIDParser(test_file)
            header = parser.parse_header()
            parser.get_c64_data(header)

        error = context.exception
        # Should mention either "offset" or "invalid" or "beyond"
        error_text = (error.message + " " + (error.what_happened or "")).lower()
        self.assertTrue("offset" in error_text or "invalid" in error_text or "beyond" in error_text)

    def test_valid_psid_file(self):
        """Test that valid PSID file parses without error"""
        test_file = os.path.join(self.temp_dir, "valid.sid")

        # Create minimal valid PSID file
        with open(test_file, 'wb') as f:
            f.write(b'PSID')  # Magic
            f.write(struct.pack('>H', 2))  # Version 2
            f.write(struct.pack('>H', 124))  # Data offset (standard)
            f.write(struct.pack('>H', 0x1000))  # Load address
            f.write(struct.pack('>H', 0x1000))  # Init address
            f.write(struct.pack('>H', 0x1003))  # Play address
            f.write(struct.pack('>H', 1))  # Songs
            f.write(struct.pack('>H', 1))  # Start song
            f.write(struct.pack('>I', 0))  # Speed
            f.write(b'Test Song\x00' + b' ' * 22)  # Name (32 bytes)
            f.write(b'Test Author\x00' + b' ' * 20)  # Author (32 bytes)
            f.write(b'2025\x00' + b' ' * 27)  # Copyright (32 bytes)
            f.write(b'\x00' * 6)  # V2 fields
            # Add some data
            f.write(b'\xA9\x00\x60')  # LDA #$00, RTS

        # Should parse without error
        parser = SIDParser(test_file)
        header = parser.parse_header()
        c64_data, load_addr = parser.get_c64_data(header)

        self.assertEqual(header.magic, 'PSID')
        self.assertEqual(header.version, 2)
        self.assertEqual(load_addr, 0x1000)


class TestSF2PackerErrorHandling(unittest.TestCase):
    """Test error handling in SF2Packer"""

    def setUp(self):
        """Create temporary directory for test files"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up temporary files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_invalid_input_file_too_small(self):
        """Test InvalidInputError for SF2 file too small"""
        test_file = os.path.join(self.temp_dir, "tiny.sf2")
        with open(test_file, 'wb') as f:
            f.write(b'X')  # Only 1 byte, need at least 2 for load address

        with self.assertRaises(errors.InvalidInputError) as context:
            SF2Packer(Path(test_file))

        error = context.exception
        self.assertIn("SF2 file", error.message)
        self.assertIn("1 byte", str(error))
        self.assertIn("2 bytes", str(error))

    def test_invalid_input_data_beyond_64kb(self):
        """Test InvalidInputError for data extending beyond 64KB"""
        test_file = os.path.join(self.temp_dir, "too_large.sf2")

        # Create file with load address that would extend beyond 64KB
        with open(test_file, 'wb') as f:
            # Load address = $FF00, data = 300 bytes
            # End address = $FF00 + 300 = $1012C (beyond $FFFF)
            f.write(struct.pack('<H', 0xFF00))  # Load address
            f.write(b'\x00' * 300)  # Data that extends beyond 64KB

        with self.assertRaises(errors.InvalidInputError) as context:
            SF2Packer(Path(test_file))

        error = context.exception
        self.assertIn("64KB", str(error) or "64K" in str(error))
        self.assertIn("$", str(error))  # Should have hex address

    def test_valid_sf2_file(self):
        """Test that valid SF2 file loads without error"""
        test_file = os.path.join(self.temp_dir, "valid.sf2")

        # Create minimal valid SF2/PRG file
        with open(test_file, 'wb') as f:
            f.write(struct.pack('<H', 0x1000))  # Load address
            f.write(b'\x00' * 100)  # Some data

        # Should load without error
        packer = SF2Packer(Path(test_file))
        self.assertEqual(packer.load_address, 0x1000)


class TestErrorMessageFormat(unittest.TestCase):
    """Test error message formatting and structure"""

    def test_error_message_has_all_sections(self):
        """Test that error messages have all required sections"""
        try:
            # Trigger a FileNotFoundError
            from sidm2.errors import FileNotFoundError
            raise FileNotFoundError(
                path="test.sid",
                context="test file"
            )
        except errors.FileNotFoundError as e:
            error_str = str(e)

            # Check for required sections
            self.assertIn("ERROR:", error_str)
            self.assertIn("What happened:", error_str)
            self.assertIn("Why this happened:", error_str)
            self.assertIn("How to fix:", error_str)
            self.assertIn("Need help?", error_str)
            self.assertIn("Technical details:", error_str)

    def test_error_message_has_documentation_links(self):
        """Test that errors include documentation links"""
        try:
            from sidm2.errors import InvalidInputError
            raise InvalidInputError(
                input_type="test",
                value="bad",
                docs_link="guides/TROUBLESHOOTING.md"
            )
        except errors.InvalidInputError as e:
            error_str = str(e)

            # Check for GitHub documentation URL
            self.assertIn("github.com", error_str.lower())
            self.assertIn("SIDM2", error_str or "sidm2" in error_str.lower())

    def test_error_to_dict_serialization(self):
        """Test error serialization to dictionary"""
        from sidm2.errors import ConversionError

        error = ConversionError(
            stage="test",
            reason="test reason",
            input_file="test.sid"
        )

        error_dict = error.to_dict()

        self.assertIn('type', error_dict)
        self.assertIn('message', error_dict)
        self.assertIn('what_happened', error_dict)
        self.assertEqual(error_dict['type'], 'ConversionError')


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSIDParserErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestSF2PackerErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorMessageFormat))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
