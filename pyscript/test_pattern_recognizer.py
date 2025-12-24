"""
Unit tests for Pattern Recognizer (Step 17)

Tests the PatternRecognizer class and its methods.
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.pattern_recognizer import PatternRecognizer, Pattern, analyze_patterns


class TestPattern(unittest.TestCase):
    """Test cases for Pattern class"""

    def test_pattern_creation(self):
        """Test creating a pattern"""
        data = b'\x01\x02\x03\x04'
        occurrences = [0, 10, 20]
        pattern = Pattern(data, occurrences)

        self.assertEqual(pattern.data, data)
        self.assertEqual(pattern.length, 4)
        self.assertEqual(pattern.count, 3)
        self.assertEqual(pattern.occurrences, occurrences)

    def test_bytes_saved_calculation(self):
        """Test calculating potential bytes saved"""
        # Pattern that appears 3 times, 8 bytes long
        # Savings: 2 * (8 - 2) = 12 bytes
        data = b'\x01\x02\x03\x04\x05\x06\x07\x08'
        occurrences = [0, 10, 20]
        pattern = Pattern(data, occurrences)

        expected_savings = 2 * (8 - 2)  # (count-1) * (length-2)
        self.assertEqual(pattern.bytes_saved(), expected_savings)

    def test_single_occurrence_no_savings(self):
        """Test that single occurrence has no savings"""
        pattern = Pattern(b'\x01\x02\x03\x04', [0])
        self.assertEqual(pattern.bytes_saved(), 0)


class TestPatternRecognizer(unittest.TestCase):
    """Test cases for PatternRecognizer class"""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        # Find test SID files
        test_dirs = [
            Path("Fun_Fun"),
            Path("laxity_music"),
            Path("test_files"),
            Path(".")
        ]

        cls.test_sid = None
        for test_dir in test_dirs:
            if test_dir.exists():
                sid_files = list(test_dir.glob("*.sid"))
                if sid_files:
                    cls.test_sid = sid_files[0]
                    break

        if not cls.test_sid:
            raise unittest.SkipTest("No test SID files found")

        # Create output directory
        cls.output_dir = Path("output/test_patterns")
        cls.output_dir.mkdir(parents=True, exist_ok=True)

    def test_recognizer_creation(self):
        """Test creating a pattern recognizer"""
        recognizer = PatternRecognizer(self.test_sid)
        self.assertEqual(recognizer.sid_file, self.test_sid)
        self.assertEqual(len(recognizer.patterns), 0)

    def test_read_header(self):
        """Test reading SID file header"""
        recognizer = PatternRecognizer(self.test_sid)
        header = recognizer._read_sid_header()

        self.assertIn('magic', header)
        self.assertIn(header['magic'], ['PSID', 'RSID'])
        self.assertIn('load_addr', header)
        self.assertIn('name', header)
        self.assertIn('author', header)

    def test_read_data(self):
        """Test reading SID file data"""
        recognizer = PatternRecognizer(self.test_sid)
        recognizer.header = recognizer._read_sid_header()
        data, load_addr = recognizer._read_sid_data()

        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)
        self.assertGreater(load_addr, 0)

    def test_analyze_success(self):
        """Test successful pattern analysis"""
        recognizer = PatternRecognizer(self.test_sid)
        result = recognizer.analyze(verbose=0)

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertIn('total_patterns', result)
        self.assertIn('total_occurrences', result)
        self.assertIn('potential_savings', result)
        self.assertIn('compression_ratio', result)
        self.assertIn('top_patterns', result)
        self.assertIn('command_frequencies', result)

    def test_analyze_with_invalid_file(self):
        """Test analysis with non-existent file"""
        recognizer = PatternRecognizer(Path("nonexistent.sid"))
        result = recognizer.analyze(verbose=0)

        self.assertIsNotNone(result)
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_find_patterns(self):
        """Test pattern finding algorithm"""
        recognizer = PatternRecognizer(self.test_sid)
        recognizer.header = recognizer._read_sid_header()
        recognizer.data, recognizer.load_addr = recognizer._read_sid_data()

        # Find patterns
        patterns = recognizer._find_patterns(4, 8)

        # Should find at least some patterns in real SID file
        self.assertIsInstance(patterns, list)
        if len(patterns) > 0:
            self.assertIsInstance(patterns[0], Pattern)

    def test_command_pattern_analysis(self):
        """Test command pattern analysis"""
        recognizer = PatternRecognizer(self.test_sid)
        recognizer.header = recognizer._read_sid_header()
        recognizer.data, recognizer.load_addr = recognizer._read_sid_data()

        command_freq = recognizer._analyze_command_patterns()

        self.assertIsInstance(command_freq, dict)
        # Command frequencies should be non-negative
        for count in command_freq.values():
            self.assertGreaterEqual(count, 0)

    def test_generate_report(self):
        """Test generating pattern analysis report"""
        recognizer = PatternRecognizer(self.test_sid)
        result = recognizer.analyze(verbose=0)

        self.assertTrue(result['success'])

        # Generate report
        report_file = self.output_dir / f"{self.test_sid.stem}_patterns.txt"
        success = recognizer.generate_report(result, report_file)

        self.assertTrue(success)
        self.assertTrue(report_file.exists())

        # Verify report contents
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn("SID PATTERN ANALYSIS", content)
        self.assertIn("FILE INFORMATION", content)
        self.assertIn("PATTERN STATISTICS", content)
        self.assertIn("TOP REPEATING PATTERNS", content)

        # Clean up
        report_file.unlink()

    def test_pattern_statistics(self):
        """Test pattern statistics calculation"""
        recognizer = PatternRecognizer(self.test_sid)
        result = recognizer.analyze(verbose=0)

        self.assertTrue(result['success'])

        # All statistics should be non-negative
        self.assertGreaterEqual(result['total_patterns'], 0)
        self.assertGreaterEqual(result['total_occurrences'], 0)
        self.assertGreaterEqual(result['potential_savings'], 0)
        self.assertGreaterEqual(result['compression_ratio'], 0)

    def test_top_patterns_sorted(self):
        """Test that top patterns are sorted by savings"""
        recognizer = PatternRecognizer(self.test_sid)
        result = recognizer.analyze(verbose=0)

        self.assertTrue(result['success'])

        if len(result['top_patterns']) > 1:
            # Check that patterns are sorted by bytes_saved (descending)
            for i in range(len(result['top_patterns']) - 1):
                self.assertGreaterEqual(
                    result['top_patterns'][i].bytes_saved(),
                    result['top_patterns'][i+1].bytes_saved()
                )

    def test_convenience_function(self):
        """Test convenience analyze_patterns function"""
        report_file = self.output_dir / f"{self.test_sid.stem}_convenience.txt"

        result = analyze_patterns(
            sid_file=self.test_sid,
            output_file=report_file,
            verbose=0
        )

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertTrue(report_file.exists())

        # Clean up
        report_file.unlink()


class TestPatternConstants(unittest.TestCase):
    """Test pattern recognizer constants"""

    def test_pattern_constants(self):
        """Test that pattern search constants are reasonable"""
        self.assertEqual(PatternRecognizer.MIN_PATTERN_LENGTH, 4)
        self.assertEqual(PatternRecognizer.MAX_PATTERN_LENGTH, 32)
        self.assertEqual(PatternRecognizer.MIN_OCCURRENCES, 2)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestPattern))
    suite.addTests(loader.loadTestsFromTestCase(TestPatternRecognizer))
    suite.addTests(loader.loadTestsFromTestCase(TestPatternConstants))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
