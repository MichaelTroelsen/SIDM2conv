"""
Unit tests for Report Generator (Step 19)

Tests the ReportGenerator class and its methods.
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.report_generator import ReportGenerator, generate_consolidated_report


class TestReportGenerator(unittest.TestCase):
    """Test cases for ReportGenerator class"""

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

        # Create test analysis directory with some dummy files
        cls.test_analysis_dir = Path("output/test_report_gen/analysis")
        cls.test_analysis_dir.mkdir(parents=True, exist_ok=True)

        # Create some dummy analysis files
        stem = cls.test_sid.stem

        # Create dummy memmap file
        memmap_file = cls.test_analysis_dir / f"{stem}_memmap.txt"
        with open(memmap_file, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("MEMORY MAP\n")
            f.write("Total size:     3262 bytes (100%)\n")
            f.write("Code regions:    700 bytes (21%)\n")
            f.write("Data regions:   2562 bytes (78%)\n")

        # Create dummy patterns file
        patterns_file = cls.test_analysis_dir / f"{stem}_patterns.txt"
        with open(patterns_file, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("PATTERN ANALYSIS\n")
            f.write("Total patterns:      100\n")
            f.write("Potential savings:   500 bytes\n")

        # Create dummy callgraph file
        callgraph_file = cls.test_analysis_dir / f"{stem}_callgraph.txt"
        with open(callgraph_file, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("CALL GRAPH\n")
            f.write("Total subroutines:   5\n")
            f.write("Max call depth:      2\n")

        cls.output_dir = Path("output/test_report_gen")
        cls.output_dir.mkdir(parents=True, exist_ok=True)

    def test_generator_creation(self):
        """Test creating a report generator"""
        generator = ReportGenerator(self.test_sid, self.test_analysis_dir)
        self.assertEqual(generator.sid_file, self.test_sid)
        self.assertEqual(generator.analysis_dir, self.test_analysis_dir)

    def test_scan_analysis_files(self):
        """Test scanning for analysis files"""
        generator = ReportGenerator(self.test_sid, self.test_analysis_dir)
        reports = generator._scan_analysis_files()

        self.assertIsInstance(reports, dict)
        # Should find at least the files we created
        self.assertIn('memmap', reports)
        self.assertIn('patterns', reports)
        self.assertIn('callgraph', reports)

    def test_scan_nonexistent_directory(self):
        """Test scanning a directory that doesn't exist"""
        generator = ReportGenerator(self.test_sid, Path("nonexistent"))
        reports = generator._scan_analysis_files()

        self.assertEqual(len(reports), 0)

    def test_extract_statistics(self):
        """Test extracting statistics from reports"""
        generator = ReportGenerator(self.test_sid, self.test_analysis_dir)
        generator.available_reports = generator._scan_analysis_files()
        stats = generator._extract_statistics()

        self.assertIsInstance(stats, dict)
        # Should extract some statistics from our dummy files
        if 'memmap' in generator.available_reports:
            self.assertIn('total_size', stats)
            self.assertIn('code_size', stats)

    def test_read_file_summary(self):
        """Test reading file summary"""
        generator = ReportGenerator(self.test_sid, self.test_analysis_dir)

        # Create a test file
        test_file = self.output_dir / "test_summary.txt"
        with open(test_file, 'w') as f:
            for i in range(30):
                f.write(f"Line {i}\n")

        # Read summary (max 20 lines)
        summary = generator._read_file_summary(test_file, max_lines=20)

        lines = summary.split('\n')
        # Should have 20 lines plus ellipsis line
        self.assertGreaterEqual(len(lines), 20)
        self.assertIn("...", summary)

        # Clean up
        test_file.unlink()

    def test_generate_report(self):
        """Test generating consolidated report"""
        generator = ReportGenerator(self.test_sid, self.test_analysis_dir)
        output_file = self.output_dir / f"{self.test_sid.stem}_consolidated.txt"

        result = generator.generate(output_file, verbose=0)

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertEqual(result['output_file'], output_file)
        self.assertGreater(result['report_count'], 0)
        self.assertTrue(output_file.exists())

        # Verify report content
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn("SID CONVERSION ANALYSIS REPORT", content)
        self.assertIn("EXECUTIVE SUMMARY", content)
        self.assertIn("AVAILABLE ANALYSES", content)
        self.assertIn("FILE INDEX", content)

        # Clean up
        output_file.unlink()

    def test_generate_with_no_reports(self):
        """Test generating report with no analysis files"""
        empty_dir = self.output_dir / "empty"
        empty_dir.mkdir(exist_ok=True)

        generator = ReportGenerator(self.test_sid, empty_dir)
        output_file = self.output_dir / "empty_report.txt"

        result = generator.generate(output_file, verbose=0)

        self.assertIsNotNone(result)
        self.assertFalse(result['success'])
        self.assertIn('error', result)

        # Clean up
        empty_dir.rmdir()

    def test_report_statistics_section(self):
        """Test that statistics section is included"""
        generator = ReportGenerator(self.test_sid, self.test_analysis_dir)
        output_file = self.output_dir / f"{self.test_sid.stem}_stats.txt"

        result = generator.generate(output_file, verbose=0)

        self.assertTrue(result['success'])

        # Check for statistics in output
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should have statistics section
        self.assertIn("EXECUTIVE SUMMARY", content)

        # Clean up
        output_file.unlink()

    def test_report_file_index(self):
        """Test that file index is included"""
        generator = ReportGenerator(self.test_sid, self.test_analysis_dir)
        output_file = self.output_dir / f"{self.test_sid.stem}_index.txt"

        result = generator.generate(output_file, verbose=0)

        self.assertTrue(result['success'])

        # Check for file index
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn("FILE INDEX", content)
        self.assertIn("analysis/", content)

        # Clean up
        output_file.unlink()

    def test_convenience_function(self):
        """Test convenience generate_consolidated_report function"""
        output_file = self.output_dir / f"{self.test_sid.stem}_convenience.txt"

        result = generate_consolidated_report(
            sid_file=self.test_sid,
            analysis_dir=self.test_analysis_dir,
            output_file=output_file,
            verbose=0
        )

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertTrue(output_file.exists())

        # Clean up
        output_file.unlink()


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestReportGenerator))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
