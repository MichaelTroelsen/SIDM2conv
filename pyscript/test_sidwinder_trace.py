"""
Unit Tests for SIDwinder Trace Components

Tests for SIDTracer, TraceFormatter, and sidwinder_trace CLI.
Part of Python SIDwinder replacement (v2.8.0).
"""

import unittest
import sys
import os
from pathlib import Path
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pyscript.sidtracer import SIDTracer, SIDHeader, TraceData
from pyscript.trace_formatter import TraceFormatter
from sidm2.cpu6502_emulator import SIDRegisterWrite


class TestSIDHeader(unittest.TestCase):
    """Test SID header parsing."""

    def test_header_properties(self):
        """Test SIDHeader property methods."""
        # PSID v1
        header_v1 = SIDHeader(
            version=1, data_offset=0x7C, load_address=0x1000,
            init_address=0x1000, play_address=0x1003,
            songs=1, start_song=1, speed=0,
            name="Test", author="Tester", released="2025",
            flags=0
        )
        self.assertFalse(header_v1.is_rsid)
        self.assertFalse(header_v1.is_basic)

        # RSID v2 with BASIC flag
        header_v2 = SIDHeader(
            version=2, data_offset=0x7C, load_address=0x1000,
            init_address=0x1000, play_address=0x1003,
            songs=1, start_song=1, speed=0,
            name="Test", author="Tester", released="2025",
            flags=0x02
        )
        self.assertTrue(header_v2.is_rsid)
        self.assertTrue(header_v2.is_basic)


class TestSIDTracer(unittest.TestCase):
    """Test SID tracer functionality."""

    @classmethod
    def setUpClass(cls):
        """Find a test SID file."""
        laxity_dir = Path("Laxity")
        if not laxity_dir.exists():
            raise unittest.SkipTest("Laxity directory not found")

        cls.test_files = list(laxity_dir.glob("*.sid"))
        if not cls.test_files:
            raise unittest.SkipTest("No SID files found in Laxity directory")

        cls.test_sid = cls.test_files[0]

    def test_parse_sid_file(self):
        """Test SID file parsing."""
        tracer = SIDTracer(self.test_sid, verbose=0)

        self.assertIsNotNone(tracer.header)
        self.assertIsNotNone(tracer.sid_data)
        self.assertGreater(tracer.header.load_address, 0)
        self.assertGreater(tracer.header.init_address, 0)
        self.assertGreater(tracer.header.play_address, 0)

    def test_trace_execution(self):
        """Test trace execution with small frame count."""
        tracer = SIDTracer(self.test_sid, verbose=0)
        trace_data = tracer.trace(frames=5)

        self.assertIsNotNone(trace_data)
        self.assertEqual(trace_data.frames, 5)
        self.assertEqual(len(trace_data.frame_writes), 5)
        self.assertGreater(trace_data.cycles, 0)

    def test_trace_zero_frames(self):
        """Test trace with zero frames (init only)."""
        tracer = SIDTracer(self.test_sid, verbose=0)
        trace_data = tracer.trace(frames=0)

        self.assertEqual(trace_data.frames, 0)
        self.assertEqual(len(trace_data.frame_writes), 0)

    def test_trace_many_frames(self):
        """Test trace with many frames."""
        tracer = SIDTracer(self.test_sid, verbose=0)
        trace_data = tracer.trace(frames=100)

        self.assertEqual(trace_data.frames, 100)
        self.assertEqual(len(trace_data.frame_writes), 100)

    def test_invalid_sid_file(self):
        """Test handling of invalid SID file."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".sid") as f:
            f.write(b"INVALID" + b"\x00" * 100)
            temp_path = Path(f.name)

        try:
            with self.assertRaises(ValueError):
                SIDTracer(temp_path, verbose=0)
        finally:
            temp_path.unlink()

    def test_nonexistent_file(self):
        """Test handling of nonexistent file."""
        with self.assertRaises(ValueError):
            SIDTracer(Path("nonexistent.sid"), verbose=0)


class TestTraceFormatter(unittest.TestCase):
    """Test trace formatter."""

    def test_format_register(self):
        """Test register write formatting."""
        write = SIDRegisterWrite(frame=0, cycle=0, address=0xD400, value=0x0F)
        formatted = TraceFormatter._format_register(write)
        self.assertEqual(formatted, "D400:$0F")

        write2 = SIDRegisterWrite(frame=1, cycle=100, address=0xD418, value=0xFF)
        formatted2 = TraceFormatter._format_register(write2)
        self.assertEqual(formatted2, "D418:$FF")

    def test_format_init_line(self):
        """Test init line formatting."""
        writes = [
            SIDRegisterWrite(frame=0, cycle=0, address=0xD400, value=0x00),
            SIDRegisterWrite(frame=0, cycle=1, address=0xD418, value=0x0F),
        ]
        line = TraceFormatter._format_init_line(writes)
        self.assertEqual(line, "D400:$00,D418:$0F,\n")

    def test_format_init_line_empty(self):
        """Test empty init line formatting."""
        line = TraceFormatter._format_init_line([])
        self.assertEqual(line, "\n")

    def test_format_frame_line(self):
        """Test frame line formatting."""
        writes = [
            SIDRegisterWrite(frame=1, cycle=0, address=0xD400, value=0x0F),
            SIDRegisterWrite(frame=1, cycle=1, address=0xD401, value=0x90),
        ]
        line = TraceFormatter._format_frame_line(writes)
        self.assertEqual(line, "FRAME: D400:$0F,D401:$90,\n")

    def test_format_frame_line_empty(self):
        """Test empty frame line formatting."""
        line = TraceFormatter._format_frame_line([])
        self.assertEqual(line, "FRAME:\n")

    def test_format_trace(self):
        """Test complete trace formatting."""
        trace_data = TraceData(
            init_writes=[
                SIDRegisterWrite(frame=0, cycle=0, address=0xD418, value=0x00),
            ],
            frame_writes=[
                [SIDRegisterWrite(frame=1, cycle=0, address=0xD400, value=0x10)],
                [SIDRegisterWrite(frame=2, cycle=0, address=0xD401, value=0x20)],
            ],
            frames=2,
            cycles=1000
        )

        formatted = TraceFormatter.format_trace(trace_data)
        lines = formatted.split('\n')

        # Check structure
        self.assertEqual(lines[0], "D418:$00,")  # Init line
        self.assertEqual(lines[1], "FRAME: D400:$10,")  # Frame 1
        self.assertEqual(lines[2], "FRAME: D401:$20,")  # Frame 2

    def test_write_trace_file(self):
        """Test writing trace to file."""
        trace_data = TraceData(
            init_writes=[],
            frame_writes=[[SIDRegisterWrite(frame=1, cycle=0, address=0xD400, value=0x00)]],
            frames=1,
            cycles=100
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.txt"
            TraceFormatter.write_trace_file(trace_data, output_path)

            self.assertTrue(output_path.exists())
            content = output_path.read_text()
            self.assertIn("FRAME:", content)

    def test_register_usage_analysis(self):
        """Test register usage analysis."""
        trace_data = TraceData(
            init_writes=[
                SIDRegisterWrite(frame=0, cycle=0, address=0xD400, value=0x00),
                SIDRegisterWrite(frame=0, cycle=1, address=0xD400, value=0x10),
            ],
            frame_writes=[
                [SIDRegisterWrite(frame=1, cycle=0, address=0xD400, value=0x20)],
                [SIDRegisterWrite(frame=2, cycle=0, address=0xD401, value=0x30)],
            ],
            frames=2,
            cycles=100
        )

        usage = TraceFormatter._analyze_register_usage(trace_data)

        self.assertEqual(usage[0xD400], 3)  # 2 init + 1 frame
        self.assertEqual(usage[0xD401], 1)  # 1 frame


class TestIntegration(unittest.TestCase):
    """Integration tests for complete trace workflow."""

    @classmethod
    def setUpClass(cls):
        """Find a test SID file."""
        laxity_dir = Path("Laxity")
        if not laxity_dir.exists():
            raise unittest.SkipTest("Laxity directory not found")

        cls.test_files = list(laxity_dir.glob("*.sid"))
        if not cls.test_files:
            raise unittest.SkipTest("No SID files found in Laxity directory")

        cls.test_sid = cls.test_files[0]

    def test_full_workflow(self):
        """Test complete trace workflow."""
        # Create tracer
        tracer = SIDTracer(self.test_sid, verbose=0)

        # Generate trace
        trace_data = tracer.trace(frames=10)

        # Write to file
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "trace.txt"
            TraceFormatter.write_trace_file(trace_data, output_path)

            # Verify output
            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)

            # Check content
            content = output_path.read_text()
            lines = content.split('\n')

            # Should have init line + 10 frame lines + trailing newline = 12 lines
            self.assertGreaterEqual(len(lines), 11)

            # Check format
            for i, line in enumerate(lines[1:11]):  # Skip init line, check frames
                if line:  # Skip empty lines
                    self.assertTrue(line.startswith("FRAME:"), f"Line {i+1} should start with FRAME:")

    def test_multiple_files(self):
        """Test tracing multiple SID files."""
        test_count = min(3, len(self.test_files))

        for sid_file in self.test_files[:test_count]:
            with self.subTest(sid=sid_file.name):
                tracer = SIDTracer(sid_file, verbose=0)
                trace_data = tracer.trace(frames=5)

                self.assertEqual(trace_data.frames, 5)
                self.assertIsNotNone(trace_data.header)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
