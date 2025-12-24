"""
Unit tests for SIDwinder integration wrapper (sidm2/sidwinder_wrapper.py)

Tests the Phase 1 enhancement - SIDwinder Tracer integration into Step 7.5
"""

import unittest
import tempfile
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sidm2.sidwinder_wrapper import SIDwinderIntegration, trace_sid


class TestSIDwinderIntegration(unittest.TestCase):
    """Test SIDwinder integration wrapper."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(__file__).parent
        # Use Stinsens test file
        self.test_sid = self.test_dir.parent / 'Laxity' / 'Stinsens_Last_Night_of_89.sid'
        
    def test_sidwinder_integration_available(self):
        """Test that SIDwinder integration is available."""
        from sidm2.sidwinder_wrapper import SIDwinderIntegration
        self.assertIsNotNone(SIDwinderIntegration)

    def test_trace_sid_with_valid_file(self):
        """Test tracing a valid SID file."""
        if not self.test_sid.exists():
            self.skipTest(f"Test SID file not found: {self.test_sid}")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            result = SIDwinderIntegration.trace_sid(
                sid_file=self.test_sid,
                output_dir=output_dir,
                frames=50,
                verbose=0
            )

            self.assertIsNotNone(result)
            self.assertTrue(result['success'])
            self.assertTrue(result['trace_file'].exists())
            self.assertEqual(result['frames'], 50)
            self.assertGreater(result['writes'], 0)
            self.assertGreater(result['file_size'], 0)

    def test_trace_sid_with_nonexistent_file(self):
        """Test tracing a nonexistent SID file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            result = SIDwinderIntegration.trace_sid(
                sid_file=Path('nonexistent.sid'),
                output_dir=output_dir,
                frames=100,
                verbose=0
            )

            self.assertIsNone(result)

    def test_convenience_function(self):
        """Test the convenience function trace_sid()."""
        if not self.test_sid.exists():
            self.skipTest(f"Test SID file not found: {self.test_sid}")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            result = trace_sid(
                sid_file=self.test_sid,
                output_dir=output_dir,
                frames=25,
                verbose=0
            )

            self.assertIsNotNone(result)
            self.assertTrue(result['success'])

    def test_trace_returns_correct_data_types(self):
        """Test that trace result contains correct data types."""
        if not self.test_sid.exists():
            self.skipTest(f"Test SID file not found: {self.test_sid}")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            result = SIDwinderIntegration.trace_sid(
                sid_file=self.test_sid,
                output_dir=output_dir,
                frames=25,
                verbose=0
            )

            self.assertIsInstance(result['success'], bool)
            self.assertIsInstance(result['trace_file'], Path)
            self.assertIsInstance(result['frames'], int)
            self.assertIsInstance(result['cycles'], int)
            self.assertIsInstance(result['writes'], int)
            self.assertIsInstance(result['file_size'], int)

    def test_trace_file_format(self):
        """Test that generated trace file has correct SIDwinder format."""
        if not self.test_sid.exists():
            self.skipTest(f"Test SID file not found: {self.test_sid}")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            result = SIDwinderIntegration.trace_sid(
                sid_file=self.test_sid,
                output_dir=output_dir,
                frames=25,
                verbose=0
            )

            trace_content = result['trace_file'].read_text()
            lines = trace_content.strip().split('\n')
            
            for i, line in enumerate(lines[1:], 1):
                self.assertTrue(
                    line.startswith('FRAME:'),
                    f"Line {i} doesn't start with FRAME: prefix"
                )


if __name__ == '__main__':
    unittest.main()
