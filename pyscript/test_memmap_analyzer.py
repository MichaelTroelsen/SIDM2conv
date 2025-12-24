"""
Unit tests for Memory Map Analyzer (Step 12.5)

Tests the MemoryMapAnalyzer class and its methods.
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.memmap_analyzer import MemoryMapAnalyzer, MemoryRegion, analyze_memory_map


class TestMemoryRegion(unittest.TestCase):
    """Test cases for MemoryRegion class"""

    def test_region_creation(self):
        """Test creating a memory region"""
        region = MemoryRegion(0x1000, 0x1FFF, "CODE", "Test region")

        self.assertEqual(region.start, 0x1000)
        self.assertEqual(region.end, 0x1FFF)
        self.assertEqual(region.region_type, "CODE")
        self.assertEqual(region.description, "Test region")

    def test_region_size(self):
        """Test calculating region size"""
        region = MemoryRegion(0x1000, 0x1FFF, "CODE")
        self.assertEqual(region.size, 0x1000)  # 4096 bytes

        region2 = MemoryRegion(0x1000, 0x1000, "CODE")
        self.assertEqual(region2.size, 1)  # Single byte

    def test_region_overlaps(self):
        """Test detecting overlapping regions"""
        region1 = MemoryRegion(0x1000, 0x1FFF, "CODE")
        region2 = MemoryRegion(0x1500, 0x2500, "DATA")
        region3 = MemoryRegion(0x2000, 0x3000, "DATA")

        # region1 and region2 overlap
        self.assertTrue(region1.overlaps(region2))
        self.assertTrue(region2.overlaps(region1))

        # region1 and region3 don't overlap
        self.assertFalse(region1.overlaps(region3))
        self.assertFalse(region3.overlaps(region1))

        # region2 and region3 overlap
        self.assertTrue(region2.overlaps(region3))


class TestMemoryMapAnalyzer(unittest.TestCase):
    """Test cases for MemoryMapAnalyzer class"""

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
        cls.output_dir = Path("output/test_memmap")
        cls.output_dir.mkdir(parents=True, exist_ok=True)

    def test_analyzer_creation(self):
        """Test creating a memory map analyzer"""
        analyzer = MemoryMapAnalyzer(self.test_sid)
        self.assertEqual(analyzer.sid_file, self.test_sid)
        self.assertEqual(len(analyzer.regions), 0)

    def test_read_header(self):
        """Test reading SID file header"""
        analyzer = MemoryMapAnalyzer(self.test_sid)
        header = analyzer._read_sid_header()

        self.assertIn('magic', header)
        self.assertIn(header['magic'], ['PSID', 'RSID'])
        self.assertIn('load_addr', header)
        self.assertIn('init_addr', header)
        self.assertIn('play_addr', header)
        self.assertIn('name', header)
        self.assertIn('author', header)

    def test_read_data(self):
        """Test reading SID file data"""
        analyzer = MemoryMapAnalyzer(self.test_sid)
        analyzer.header = analyzer._read_sid_header()
        data, load_addr = analyzer._read_sid_data()

        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)
        self.assertGreater(load_addr, 0)

    def test_analyze_success(self):
        """Test successful memory map analysis"""
        analyzer = MemoryMapAnalyzer(self.test_sid)
        result = analyzer.analyze(verbose=0)

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertIn('load_addr', result)
        self.assertIn('end_addr', result)
        self.assertIn('total_size', result)
        self.assertIn('code_size', result)
        self.assertIn('data_size', result)
        self.assertIn('regions', result)

        # Verify regions
        self.assertGreater(len(result['regions']), 0)
        self.assertIsInstance(result['regions'][0], MemoryRegion)

    def test_analyze_with_invalid_file(self):
        """Test analysis with non-existent file"""
        analyzer = MemoryMapAnalyzer(Path("nonexistent.sid"))
        result = analyzer.analyze(verbose=0)

        self.assertIsNotNone(result)
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_generate_report(self):
        """Test generating memory map report"""
        analyzer = MemoryMapAnalyzer(self.test_sid)
        result = analyzer.analyze(verbose=0)

        self.assertTrue(result['success'])

        # Generate report
        report_file = self.output_dir / f"{self.test_sid.stem}_memmap.txt"
        success = analyzer.generate_report(result, report_file)

        self.assertTrue(success)
        self.assertTrue(report_file.exists())

        # Verify report contents
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn("SID MEMORY MAP ANALYSIS", content)
        self.assertIn("FILE INFORMATION", content)
        self.assertIn("MEMORY LAYOUT", content)
        self.assertIn("MEMORY REGIONS", content)
        self.assertIn("STATISTICS", content)
        self.assertIn("VISUAL MEMORY MAP", content)

        # Clean up
        report_file.unlink()

    def test_memory_statistics(self):
        """Test memory statistics calculation"""
        analyzer = MemoryMapAnalyzer(self.test_sid)
        result = analyzer.analyze(verbose=0)

        self.assertTrue(result['success'])

        # Code + data should equal total (approximately)
        total = result['total_size']
        code = result['code_size']
        data = result['data_size']

        self.assertGreaterEqual(total, code)
        self.assertGreaterEqual(total, data)
        self.assertEqual(code + data, total)

    def test_region_identification(self):
        """Test identification of memory regions"""
        analyzer = MemoryMapAnalyzer(self.test_sid)
        result = analyzer.analyze(verbose=0)

        self.assertTrue(result['success'])

        # Should have at least main data region
        self.assertGreater(len(result['regions']), 0)

        # Check for expected region types
        region_types = [r.region_type for r in result['regions']]
        self.assertIn("DATA", region_types)

        # If init/play addresses exist, should have CODE regions
        if result['header']['init_addr'] > 0:
            self.assertIn("CODE", region_types)

    def test_convenience_function(self):
        """Test convenience analyze_memory_map function"""
        report_file = self.output_dir / f"{self.test_sid.stem}_convenience.txt"

        result = analyze_memory_map(
            sid_file=self.test_sid,
            output_file=report_file,
            verbose=0
        )

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertTrue(report_file.exists())

        # Clean up
        report_file.unlink()


class TestMemoryMapConstants(unittest.TestCase):
    """Test memory map constants"""

    def test_c64_memory_constants(self):
        """Test C64 memory range constants"""
        self.assertEqual(MemoryMapAnalyzer.C64_RAM_START, 0x0000)
        self.assertEqual(MemoryMapAnalyzer.C64_RAM_END, 0xFFFF)
        self.assertEqual(MemoryMapAnalyzer.SID_CHIP_START, 0xD400)
        self.assertEqual(MemoryMapAnalyzer.SID_CHIP_END, 0xD7FF)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryRegion))
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryMapAnalyzer))
    suite.addTests(loader.loadTestsFromTestCase(TestMemoryMapConstants))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
