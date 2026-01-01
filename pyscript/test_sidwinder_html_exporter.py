"""
Unit Tests for SIDwinder HTML Trace Exporter

Tests for sidwinder_html_exporter.py - interactive HTML trace
visualization with timeline navigation and register state display.

Tests cover:
- HTML trace export
- Register info mapping (29 SID registers)
- Frame serialization to JavaScript
- TraceData handling
- HTML output validity
- Different frame counts
- Empty trace data
- Register group classification

Usage:
    python pyscript/test_sidwinder_html_exporter.py
    python pyscript/test_sidwinder_html_exporter.py -v
"""

import unittest
import sys
import os
from pathlib import Path
import tempfile
from dataclasses import dataclass
from typing import List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pyscript.sidwinder_html_exporter import SIDwinderHTMLExporter, export_trace_to_html
from pyscript.sidtracer import TraceData, SIDHeader
from sidm2.cpu6502_emulator import SIDRegisterWrite


class TestSIDwinderHTMLExporter(unittest.TestCase):
    """Test SIDwinder HTML trace exporter."""

    def setUp(self):
        """Set up test fixtures."""
        # Create sample SID header
        self.header = SIDHeader(
            version=2,
            data_offset=0x7C,
            load_address=0x1000,
            init_address=0x1000,
            play_address=0x1003,
            songs=1,
            start_song=1,
            speed=0,
            name="Test SID",
            author="Tester",
            released="2026",
            flags=0
        )

        # Create sample trace data with register writes
        self.trace_data = TraceData(
            init_writes=[
                SIDRegisterWrite(0, 100, 0xD400, 0x10, "Voice 1: Frequency Lo"),
                SIDRegisterWrite(0, 110, 0xD401, 0x20, "Voice 1: Frequency Hi"),
            ],
            frame_writes=[
                [  # Frame 0
                    SIDRegisterWrite(1, 200, 0xD404, 0x21, "Voice 1: Control"),
                    SIDRegisterWrite(1, 210, 0xD40B, 0x41, "Voice 2: Control"),
                ],
                [  # Frame 1
                    SIDRegisterWrite(2, 300, 0xD400, 0x15, "Voice 1: Frequency Lo"),
                    SIDRegisterWrite(2, 310, 0xD412, 0x61, "Voice 3: Control"),
                ]
            ],
            frames=2,
            cycles=500,
            header=self.header
        )

    def test_exporter_initialization(self):
        """Test SIDwinderHTMLExporter initialization."""
        exporter = SIDwinderHTMLExporter(self.trace_data, "Test SID")

        self.assertEqual(exporter.sid_name, "Test SID")
        self.assertEqual(exporter.trace_data, self.trace_data)
        self.assertIsNotNone(exporter.timestamp)

    def test_register_info_complete(self):
        """Test that all 29 SID registers are defined."""
        self.assertEqual(len(SIDwinderHTMLExporter.REGISTER_INFO), 29)

        # Check key registers
        self.assertIn(0x00, SIDwinderHTMLExporter.REGISTER_INFO)  # Voice 1 Freq Lo
        self.assertIn(0x07, SIDwinderHTMLExporter.REGISTER_INFO)  # Voice 2 Freq Lo
        self.assertIn(0x0E, SIDwinderHTMLExporter.REGISTER_INFO)  # Voice 3 Freq Lo
        self.assertIn(0x15, SIDwinderHTMLExporter.REGISTER_INFO)  # Filter Cutoff Lo
        self.assertIn(0x18, SIDwinderHTMLExporter.REGISTER_INFO)  # Mode/Volume

    def test_register_groups(self):
        """Test register group classification."""
        # Voice 1 (0x00-0x06)
        self.assertEqual(SIDwinderHTMLExporter.REGISTER_INFO[0x00][1], "voice1")
        self.assertEqual(SIDwinderHTMLExporter.REGISTER_INFO[0x06][1], "voice1")

        # Voice 2 (0x07-0x0D)
        self.assertEqual(SIDwinderHTMLExporter.REGISTER_INFO[0x07][1], "voice2")
        self.assertEqual(SIDwinderHTMLExporter.REGISTER_INFO[0x0D][1], "voice2")

        # Voice 3 (0x0E-0x14)
        self.assertEqual(SIDwinderHTMLExporter.REGISTER_INFO[0x0E][1], "voice3")
        self.assertEqual(SIDwinderHTMLExporter.REGISTER_INFO[0x14][1], "voice3")

        # Filter (0x15-0x18)
        self.assertEqual(SIDwinderHTMLExporter.REGISTER_INFO[0x15][1], "filter")
        self.assertEqual(SIDwinderHTMLExporter.REGISTER_INFO[0x18][1], "filter")

    def test_serialize_frames_to_js(self):
        """Test frame data serialization to JavaScript."""
        exporter = SIDwinderHTMLExporter(self.trace_data)
        js_data = exporter._serialize_frames_to_js()

        self.assertIsInstance(js_data, str)
        self.assertIn('[', js_data)
        self.assertIn(']', js_data)
        # Check for register offset (0xD400 -> 0x00 = 0)
        self.assertIn('"reg":0', js_data)
        # Check for register offset (0xD404 -> 0x04 = 4)
        self.assertIn('"reg":4', js_data)
        # Check for values
        self.assertIn('"value":33', js_data)  # 0x21
        self.assertIn('"value":65', js_data)  # 0x41

    def test_generate_html_structure(self):
        """Test HTML generation structure."""
        exporter = SIDwinderHTMLExporter(self.trace_data, "Test SID")
        html = exporter._generate_html()

        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 5000)
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('</html>', html)
        self.assertIn('Test SID', html)

    def test_html_contains_required_sections(self):
        """Test that HTML contains all required sections."""
        exporter = SIDwinderHTMLExporter(self.trace_data)
        html = exporter._generate_html()

        # Check for main sections
        self.assertIn('Overview', html)
        self.assertIn('Statistics', html)
        self.assertIn('Timeline', html)
        self.assertIn('Frame Viewer', html)
        self.assertIn('Register States', html)

    def test_html_contains_interactive_elements(self):
        """Test that HTML contains interactive elements."""
        exporter = SIDwinderHTMLExporter(self.trace_data)
        html = exporter._generate_html()

        # Timeline slider
        self.assertIn('frameSlider', html)
        self.assertIn('type="range"', html)

        # JavaScript for interactivity
        self.assertIn('<script>', html)
        self.assertIn('addEventListener', html)
        self.assertIn('loadFrame', html)

    def test_html_contains_register_table(self):
        """Test that HTML contains register state table."""
        exporter = SIDwinderHTMLExporter(self.trace_data)
        html = exporter._generate_html()

        # Check for register groups
        self.assertIn('Voice 1', html)
        self.assertIn('Voice 2', html)
        self.assertIn('Voice 3', html)
        self.assertIn('Filter', html)

        # Check for register addresses
        self.assertIn('$D400', html)
        self.assertIn('$D404', html)

    def test_export_to_file(self):
        """Test exporting trace to HTML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name

        try:
            exporter = SIDwinderHTMLExporter(self.trace_data, "Test SID")
            result = exporter.export(output_path)

            self.assertTrue(result)
            self.assertTrue(os.path.exists(output_path))

            # Read and verify content
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.assertIn('<!DOCTYPE html>', content)
            self.assertIn('Test SID', content)
            self.assertGreater(len(content), 5000)

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_export_with_many_frames(self):
        """Test export with larger frame count."""
        # Create trace with 100 frames
        frame_writes = []
        for i in range(100):
            frame_writes.append([
                SIDRegisterWrite(i+1, (i+1)*100, 0xD400, i % 256, "Voice 1: Frequency Lo")
            ])

        large_trace = TraceData(
            init_writes=[],
            frame_writes=frame_writes,
            frames=100,
            cycles=10000,
            header=self.header
        )

        exporter = SIDwinderHTMLExporter(large_trace)
        html = exporter._generate_html()

        self.assertIn('100', html)  # Should mention 100 frames
        self.assertGreater(len(html), 10000)

    def test_export_with_no_frames(self):
        """Test export with zero frames (init only)."""
        zero_trace = TraceData(
            init_writes=[
                SIDRegisterWrite(0, 100, 0xD400, 0x10, "Voice 1: Frequency Lo"),
            ],
            frame_writes=[],
            frames=0,
            cycles=100,
            header=self.header
        )

        exporter = SIDwinderHTMLExporter(zero_trace)
        html = exporter._generate_html()

        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('0', html)  # Zero frames

    def test_export_with_all_register_types(self):
        """Test export with writes to all register types."""
        all_writes = [
            SIDRegisterWrite(1, 100, 0xD400, 0x10, "Voice 1: Frequency Lo"),
            SIDRegisterWrite(1, 110, 0xD407, 0x20, "Voice 2: Frequency Lo"),
            SIDRegisterWrite(1, 120, 0xD40E, 0x30, "Voice 3: Frequency Lo"),
            SIDRegisterWrite(1, 130, 0xD415, 0x40, "Filter: Cutoff Lo"),
        ]

        trace = TraceData(
            init_writes=[],
            frame_writes=[all_writes],
            frames=1,
            cycles=200,
            header=self.header
        )

        exporter = SIDwinderHTMLExporter(trace)
        html = exporter._generate_html()

        # Check all groups are present
        self.assertIn('voice1', html)
        self.assertIn('voice2', html)
        self.assertIn('voice3', html)
        self.assertIn('filter', html)

    def test_statistics_section(self):
        """Test statistics section generation."""
        exporter = SIDwinderHTMLExporter(self.trace_data)
        html = exporter._generate_html()

        # Should contain statistics
        self.assertIn('Total Writes', html)
        self.assertIn('Init Writes', html)
        self.assertIn('Avg/Frame', html)
        self.assertIn('Total Cycles', html)


class TestExportTraceToHTMLFunction(unittest.TestCase):
    """Test convenience function for trace export."""

    def setUp(self):
        """Set up test fixtures."""
        self.header = SIDHeader(
            version=2, data_offset=0x7C, load_address=0x1000,
            init_address=0x1000, play_address=0x1003,
            songs=1, start_song=1, speed=0,
            name="Test", author="Tester", released="2026", flags=0
        )

        self.trace_data = TraceData(
            init_writes=[],
            frame_writes=[[]],
            frames=1,
            cycles=100,
            header=self.header
        )

    def test_export_trace_to_html_function(self):
        """Test export_trace_to_html convenience function."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name

        try:
            result = export_trace_to_html(
                self.trace_data,
                output_path,
                "Test SID"
            )

            self.assertTrue(result)
            self.assertTrue(os.path.exists(output_path))

            # Verify content
            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.assertIn('<!DOCTYPE html>', content)
            self.assertIn('Test SID', content)

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_export_with_default_name(self):
        """Test export with default SID name."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            output_path = f.name

        try:
            result = export_trace_to_html(self.trace_data, output_path)

            self.assertTrue(result)

            with open(output_path, 'r', encoding='utf-8') as f:
                content = f.read()

            self.assertIn('SID Trace', content)  # Default name

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)


class TestRegisterAddressCalculation(unittest.TestCase):
    """Test register address offset calculation."""

    def test_register_offset_calculation(self):
        """Test that register addresses are correctly converted to offsets."""
        header = SIDHeader(
            version=2, data_offset=0x7C, load_address=0x1000,
            init_address=0x1000, play_address=0x1003,
            songs=1, start_song=1, speed=0,
            name="Test", author="Tester", released="2026", flags=0
        )

        # Test different register addresses
        test_cases = [
            (0xD400, 0),    # Voice 1 Freq Lo -> offset 0
            (0xD404, 4),    # Voice 1 Control -> offset 4
            (0xD407, 7),    # Voice 2 Freq Lo -> offset 7
            (0xD40E, 14),   # Voice 3 Freq Lo -> offset 14
            (0xD418, 24),   # Mode/Volume -> offset 24
        ]

        for address, expected_offset in test_cases:
            write = SIDRegisterWrite(1, 100, address, 0x10, "Test")
            offset = write.address - 0xD400

            self.assertEqual(offset, expected_offset,
                           f"Address ${address:04X} should have offset {expected_offset}")


if __name__ == '__main__':
    unittest.main()
