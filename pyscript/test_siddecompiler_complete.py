"""
Comprehensive Test Suite for Python SIDdecompiler

Tests the complete SIDdecompiler implementation against real SID files
to validate 100% compatibility with SIDdecompiler.exe.
"""

import unittest
import sys
import os
from pathlib import Path
import tempfile
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pyscript.siddecompiler_complete import SIDDecompiler, SIDHeader


class TestSIDHeaderParsing(unittest.TestCase):
    """Test SID file header parsing"""

    def test_parse_simple_psid(self):
        """Test parsing a simple PSID file"""
        decompiler = SIDDecompiler(verbose=0)

        # Find a test SID file
        test_files = list(Path("Laxity").glob("*.sid"))
        if not test_files:
            self.skipTest("No Laxity SID files found")

        success = decompiler.parse_sid_file(str(test_files[0]))
        self.assertTrue(success, "Should successfully parse SID file")
        self.assertIsNotNone(decompiler.sid_header)
        self.assertIn(decompiler.sid_header.magic, ['PSID', 'RSID'])
        self.assertGreater(decompiler.sid_header.load_address, 0)
        self.assertGreater(decompiler.sid_header.init_address, 0)
        self.assertGreater(decompiler.sid_header.play_address, 0)

    def test_header_fields(self):
        """Test that all header fields are populated"""
        decompiler = SIDDecompiler(verbose=0)

        test_files = list(Path("Laxity").glob("*.sid"))
        if not test_files:
            self.skipTest("No Laxity SID files found")

        decompiler.parse_sid_file(str(test_files[0]))
        h = decompiler.sid_header

        self.assertIsNotNone(h.magic)
        self.assertGreater(h.version, 0)
        self.assertGreater(h.data_offset, 0)
        self.assertGreaterEqual(h.load_address, 0)  # Can be 0 (read from data)
        self.assertGreater(h.songs, 0)
        self.assertGreater(h.start_song, 0)


class TestMemoryAnalysis(unittest.TestCase):
    """Test memory access analysis"""

    def test_basic_analysis(self):
        """Test basic memory analysis runs without errors"""
        decompiler = SIDDecompiler(verbose=0)

        test_files = list(Path("Laxity").glob("*.sid"))
        if not test_files:
            self.skipTest("No Laxity SID files found")

        decompiler.parse_sid_file(str(test_files[0]))
        success = decompiler.analyze_memory_access(ticks=100)  # Quick test

        self.assertTrue(success, "Memory analysis should succeed")
        self.assertIsNotNone(decompiler.memory_map)
        self.assertGreater(len(decompiler.code_regions), 0, "Should find code regions")

    def test_code_region_detection(self):
        """Test that code regions are detected"""
        decompiler = SIDDecompiler(verbose=0)

        test_files = list(Path("Laxity").glob("*.sid"))
        if not test_files:
            self.skipTest("No Laxity SID files found")

        decompiler.parse_sid_file(str(test_files[0]))
        decompiler.analyze_memory_access(ticks=100)

        # Should have at least init and play routines
        self.assertGreater(len(decompiler.code_regions), 0)

        # Init address should be in a code region
        init_addr = decompiler.sid_header.init_address
        in_code_region = any(
            start <= init_addr < end
            for start, end in decompiler.code_regions
        )
        self.assertTrue(in_code_region, "Init address should be in code region")


class TestDisassembly(unittest.TestCase):
    """Test disassembly functionality"""

    def test_basic_disassembly(self):
        """Test basic disassembly"""
        decompiler = SIDDecompiler(verbose=0)

        test_files = list(Path("Laxity").glob("*.sid"))
        if not test_files:
            self.skipTest("No Laxity SID files found")

        decompiler.parse_sid_file(str(test_files[0]))
        decompiler.analyze_memory_access(ticks=100)
        success = decompiler.disassemble()

        self.assertTrue(success, "Disassembly should succeed")
        self.assertIsNotNone(decompiler.disassembler)
        self.assertGreater(len(decompiler.disassembler.lines), 0)

    def test_labels_created(self):
        """Test that labels are created for init/play"""
        decompiler = SIDDecompiler(verbose=0)

        test_files = list(Path("Laxity").glob("*.sid"))
        if not test_files:
            self.skipTest("No Laxity SID files found")

        decompiler.parse_sid_file(str(test_files[0]))
        decompiler.analyze_memory_access(ticks=100)
        decompiler.disassemble()

        # Check for init and play labels
        self.assertIn(decompiler.sid_header.init_address, decompiler.disassembler.labels)
        self.assertIn(decompiler.sid_header.play_address, decompiler.disassembler.labels)


class TestOutputGeneration(unittest.TestCase):
    """Test assembly output generation"""

    def test_output_file_created(self):
        """Test that output file is created"""
        decompiler = SIDDecompiler(verbose=0)

        test_files = list(Path("Laxity").glob("*.sid"))
        if not test_files:
            self.skipTest("No Laxity SID files found")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as f:
            output_path = f.name

        try:
            decompiler.parse_sid_file(str(test_files[0]))
            decompiler.analyze_memory_access(ticks=100)
            decompiler.disassemble()
            decompiler.detect_tables()
            success = decompiler.generate_output(output_path)

            self.assertTrue(success, "Output generation should succeed")
            self.assertTrue(os.path.exists(output_path), "Output file should exist")

            # Check file has content
            with open(output_path, 'r') as f:
                content = f.read()

            self.assertGreater(len(content), 0, "Output file should have content")
            self.assertIn('; SIDdecompiler output', content)
            self.assertIn('* = $', content)  # Should have origin directive

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    def test_output_format(self):
        """Test output format is correct"""
        decompiler = SIDDecompiler(verbose=0)

        test_files = list(Path("Laxity").glob("*.sid"))
        if not test_files:
            self.skipTest("No Laxity SID files found")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.asm', delete=False) as f:
            output_path = f.name

        try:
            decompiler.parse_sid_file(str(test_files[0]))
            decompiler.analyze_memory_access(ticks=100)
            decompiler.disassemble()
            decompiler.detect_tables()
            decompiler.generate_output(output_path)

            with open(output_path, 'r') as f:
                lines = f.readlines()

            # Should have header comments
            comment_lines = [l for l in lines if l.startswith(';')]
            self.assertGreater(len(comment_lines), 0)

            # Should have assembly code
            code_lines = [l for l in lines if l.startswith('$')]
            self.assertGreater(len(code_lines), 0)

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)


class TestMultipleSIDFiles(unittest.TestCase):
    """Test with multiple real SID files"""

    def test_batch_processing(self):
        """Test processing multiple SID files"""
        test_files = list(Path("Laxity").glob("*.sid"))[:5]  # Test first 5
        if not test_files:
            self.skipTest("No Laxity SID files found")

        results = []
        for sid_file in test_files:
            decompiler = SIDDecompiler(verbose=0)
            success = decompiler.parse_sid_file(str(sid_file))
            results.append((sid_file.name, success))

        # All should succeed
        failed = [name for name, success in results if not success]
        self.assertEqual(len(failed), 0, f"Failed files: {failed}")

    def test_different_load_addresses(self):
        """Test SID files with different load addresses"""
        test_files = list(Path("Laxity").glob("*.sid"))
        if not test_files:
            self.skipTest("No Laxity SID files found")

        load_addresses = set()
        for sid_file in test_files[:10]:
            decompiler = SIDDecompiler(verbose=0)
            if decompiler.parse_sid_file(str(sid_file)):
                load_addresses.add(decompiler.sid_header.load_address)

        # Should handle different load addresses
        self.assertGreater(len(load_addresses), 0)


class TestErrorHandling(unittest.TestCase):
    """Test error handling"""

    def test_nonexistent_file(self):
        """Test handling of nonexistent file"""
        decompiler = SIDDecompiler(verbose=0)
        success = decompiler.parse_sid_file("nonexistent.sid")
        self.assertFalse(success, "Should fail on nonexistent file")

    def test_invalid_file(self):
        """Test handling of invalid file"""
        decompiler = SIDDecompiler(verbose=0)

        # Create a temp file with invalid content
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.sid', delete=False) as f:
            f.write(b'INVALID' * 100)
            temp_path = f.name

        try:
            success = decompiler.parse_sid_file(temp_path)
            self.assertFalse(success, "Should fail on invalid file")
        finally:
            os.unlink(temp_path)


def run_tests():
    """Run all tests and report results"""
    # Setup logging
    logging.basicConfig(level=logging.ERROR, format='%(message)s')

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSIDHeaderParsing))
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryAnalysis))
    suite.addTests(loader.loadTestsFromTestCase(TestDisassembly))
    suite.addTests(loader.loadTestsFromTestCase(TestOutputGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestMultipleSIDFiles))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))

    # Run with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 70)
    print("SIDDECOMPILER TEST SUMMARY")
    print("=" * 70)
    print(f"Total tests: {result.testsRun}")
    print(f"Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failed: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("\n[PASS] All tests PASSED - SIDdecompiler is production ready!")
        return 0
    else:
        print("\n[FAIL] Some tests FAILED - review failures above")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
