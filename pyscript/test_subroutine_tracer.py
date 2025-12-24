"""
Unit tests for Subroutine Tracer (Step 18)

Tests the SubroutineTracer class and its methods.
"""

import unittest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.subroutine_tracer import SubroutineTracer, Subroutine, trace_subroutines


class TestSubroutine(unittest.TestCase):
    """Test cases for Subroutine class"""

    def test_subroutine_creation(self):
        """Test creating a subroutine"""
        sub = Subroutine(0x1000)

        self.assertEqual(sub.address, 0x1000)
        self.assertEqual(len(sub.callers), 0)
        self.assertEqual(len(sub.calls), 0)
        self.assertEqual(sub.size, 0)

    def test_add_caller(self):
        """Test adding callers to a subroutine"""
        sub = Subroutine(0x1000)
        sub.add_caller(0x2000)
        sub.add_caller(0x3000)

        self.assertEqual(len(sub.callers), 2)
        self.assertIn(0x2000, sub.callers)
        self.assertIn(0x3000, sub.callers)

    def test_add_duplicate_caller(self):
        """Test that duplicate callers are not added"""
        sub = Subroutine(0x1000)
        sub.add_caller(0x2000)
        sub.add_caller(0x2000)

        self.assertEqual(len(sub.callers), 1)

    def test_add_call(self):
        """Test adding calls from a subroutine"""
        sub = Subroutine(0x1000)
        sub.add_call(0x2000)
        sub.add_call(0x3000)

        self.assertEqual(len(sub.calls), 2)
        self.assertIn(0x2000, sub.calls)
        self.assertIn(0x3000, sub.calls)

    def test_add_duplicate_call(self):
        """Test that duplicate calls are not added"""
        sub = Subroutine(0x1000)
        sub.add_call(0x2000)
        sub.add_call(0x2000)

        self.assertEqual(len(sub.calls), 1)


class TestSubroutineTracer(unittest.TestCase):
    """Test cases for SubroutineTracer class"""

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
        cls.output_dir = Path("output/test_subroutines")
        cls.output_dir.mkdir(parents=True, exist_ok=True)

    def test_tracer_creation(self):
        """Test creating a subroutine tracer"""
        tracer = SubroutineTracer(self.test_sid)
        self.assertEqual(tracer.sid_file, self.test_sid)
        self.assertEqual(len(tracer.subroutines), 0)

    def test_read_header(self):
        """Test reading SID file header"""
        tracer = SubroutineTracer(self.test_sid)
        header = tracer._read_sid_header()

        self.assertIn('magic', header)
        self.assertIn(header['magic'], ['PSID', 'RSID'])
        self.assertIn('init_addr', header)
        self.assertIn('play_addr', header)

    def test_read_data(self):
        """Test reading SID file data"""
        tracer = SubroutineTracer(self.test_sid)
        tracer.header = tracer._read_sid_header()
        data, load_addr = tracer._read_sid_data()

        self.assertIsInstance(data, bytes)
        self.assertGreater(len(data), 0)
        self.assertGreater(load_addr, 0)

    def test_analyze_success(self):
        """Test successful subroutine analysis"""
        tracer = SubroutineTracer(self.test_sid)
        result = tracer.analyze(verbose=0)

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertIn('total_subroutines', result)
        self.assertIn('init_subroutines', result)
        self.assertIn('play_subroutines', result)
        self.assertIn('shared_subroutines', result)
        self.assertIn('max_call_depth', result)

    def test_analyze_with_invalid_file(self):
        """Test analysis with non-existent file"""
        tracer = SubroutineTracer(Path("nonexistent.sid"))
        result = tracer.analyze(verbose=0)

        self.assertIsNotNone(result)
        self.assertFalse(result['success'])
        self.assertIn('error', result)

    def test_subroutine_statistics(self):
        """Test subroutine statistics calculation"""
        tracer = SubroutineTracer(self.test_sid)
        result = tracer.analyze(verbose=0)

        self.assertTrue(result['success'])

        # All statistics should be non-negative
        self.assertGreaterEqual(result['total_subroutines'], 0)
        self.assertGreaterEqual(result['init_subroutines'], 0)
        self.assertGreaterEqual(result['play_subroutines'], 0)
        self.assertGreaterEqual(result['shared_subroutines'], 0)
        self.assertGreaterEqual(result['max_call_depth'], 0)

        # Shared should be <= min(init, play)
        self.assertLessEqual(
            result['shared_subroutines'],
            min(result['init_subroutines'], result['play_subroutines'])
        )

    def test_trace_subroutines(self):
        """Test subroutine tracing"""
        tracer = SubroutineTracer(self.test_sid)
        tracer.header = tracer._read_sid_header()
        tracer.data, tracer.load_addr = tracer._read_sid_data()

        if tracer.header['init_addr'] > 0:
            subs = tracer._trace_subroutines(tracer.header['init_addr'])
            self.assertIsInstance(subs, set)

    def test_calculate_call_depth(self):
        """Test call depth calculation"""
        tracer = SubroutineTracer(self.test_sid)
        result = tracer.analyze(verbose=0)

        self.assertTrue(result['success'])

        # Test call depth calculation for first subroutine
        if tracer.subroutines:
            first_addr = list(tracer.subroutines.keys())[0]
            depth = tracer._calculate_call_depth(first_addr, set())
            self.assertGreaterEqual(depth, 0)

    def test_generate_report(self):
        """Test generating subroutine trace report"""
        tracer = SubroutineTracer(self.test_sid)
        result = tracer.analyze(verbose=0)

        self.assertTrue(result['success'])

        # Generate report
        report_file = self.output_dir / f"{self.test_sid.stem}_subroutines.txt"
        success = tracer.generate_report(result, report_file)

        self.assertTrue(success)
        self.assertTrue(report_file.exists())

        # Verify report contents
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn("SID SUBROUTINE CALL TRACE", content)
        self.assertIn("FILE INFORMATION", content)
        self.assertIn("SUBROUTINE STATISTICS", content)
        self.assertIn("CALL GRAPH", content)

        # Clean up
        report_file.unlink()

    def test_subroutine_relationships(self):
        """Test that subroutine relationships are correctly recorded"""
        tracer = SubroutineTracer(self.test_sid)
        result = tracer.analyze(verbose=0)

        self.assertTrue(result['success'])

        # Check that callers and calls are consistent
        for sub in tracer.subroutines.values():
            # Each call should have a corresponding caller relationship
            for call_addr in sub.calls:
                if call_addr in tracer.subroutines:
                    self.assertIn(sub.address, tracer.subroutines[call_addr].callers)

    def test_convenience_function(self):
        """Test convenience trace_subroutines function"""
        report_file = self.output_dir / f"{self.test_sid.stem}_convenience.txt"

        result = trace_subroutines(
            sid_file=self.test_sid,
            output_file=report_file,
            verbose=0
        )

        self.assertIsNotNone(result)
        self.assertTrue(result['success'])
        self.assertTrue(report_file.exists())

        # Clean up
        report_file.unlink()


class TestSubroutineConstants(unittest.TestCase):
    """Test subroutine tracer constants"""

    def test_opcode_constants(self):
        """Test 6502 opcode constants"""
        self.assertEqual(SubroutineTracer.JSR_OPCODE, 0x20)
        self.assertEqual(SubroutineTracer.RTS_OPCODE, 0x60)
        self.assertEqual(SubroutineTracer.JMP_OPCODE, 0x4C)


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestSubroutine))
    suite.addTests(loader.loadTestsFromTestCase(TestSubroutineTracer))
    suite.addTests(loader.loadTestsFromTestCase(TestSubroutineConstants))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
