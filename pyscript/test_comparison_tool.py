"""
Unit tests for enhanced Comparison Tool (sidm2/comparison_tool.py)

Tests Phase 1b enhancement - JSON output and register-level diff reporting
"""

import unittest
import tempfile
import json
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sidm2.comparison_tool import (
    RegisterDiff,
    VoiceDiff,
    ComparisonDetailExtractor,
    ComparisonJSONExporter,
    ComparisonDiffReporter
)


class TestRegisterDiff(unittest.TestCase):
    """Test RegisterDiff class"""

    def test_register_diff_creation(self):
        """Test creating a register difference"""
        diff = RegisterDiff(
            frame=10,
            register=0x04,
            register_name="Voice1_Control",
            original_value=0x80,
            exported_value=0x81
        )

        self.assertEqual(diff.frame, 10)
        self.assertEqual(diff.register, 0x04)
        self.assertEqual(diff.register_name, "Voice1_Control")
        self.assertEqual(diff.original_value, 0x80)
        self.assertEqual(diff.exported_value, 0x81)

    def test_register_diff_to_dict(self):
        """Test RegisterDiff serialization to dictionary"""
        diff = RegisterDiff(
            frame=5,
            register=0x15,
            register_name="FilterCutoffLo",
            original_value=0xFF,
            exported_value=0xFE
        )

        d = diff.to_dict()

        self.assertEqual(d['frame'], 5)
        self.assertEqual(d['register'], "$15")
        self.assertEqual(d['register_name'], "FilterCutoffLo")
        self.assertEqual(d['original_value'], "$FF")
        self.assertEqual(d['exported_value'], "$FE")
        self.assertEqual(d['original_decimal'], 0xFF)
        self.assertEqual(d['exported_decimal'], 0xFE)
        self.assertEqual(d['difference'], -1)

    def test_register_diff_hex_formatting(self):
        """Test proper hex formatting in register diff"""
        diff = RegisterDiff(
            frame=0,
            register=0x00,
            register_name="Voice1_FreqLo",
            original_value=0x0F,
            exported_value=0xF0
        )

        d = diff.to_dict()
        self.assertEqual(d['original_value'], "$0F")
        self.assertEqual(d['exported_value'], "$F0")


class TestVoiceDiff(unittest.TestCase):
    """Test VoiceDiff class"""

    def test_voice_diff_creation(self):
        """Test creating a voice difference tracker"""
        voice_diff = VoiceDiff(voice=1)
        self.assertEqual(voice_diff.voice, 1)
        self.assertEqual(len(voice_diff.frequency_diffs), 0)
        self.assertEqual(len(voice_diff.waveform_diffs), 0)

    def test_voice_diff_frequency_tracking(self):
        """Test frequency difference tracking"""
        voice_diff = VoiceDiff(voice=2)

        voice_diff.add_frequency_diff(frame=10, original=0x1234, exported=0x1235)
        voice_diff.add_frequency_diff(frame=20, original=0x5678, exported=0x5678)  # No diff

        self.assertEqual(len(voice_diff.frequency_diffs), 1)
        self.assertEqual(voice_diff.frequency_diffs[0], (10, 0x1234, 0x1235))

    def test_voice_diff_to_dict(self):
        """Test VoiceDiff serialization"""
        voice_diff = VoiceDiff(voice=1)

        voice_diff.add_frequency_diff(frame=5, original=0xABCD, exported=0xABCE)
        voice_diff.add_waveform_diff(frame=5, original=0x40, exported=0x41)
        voice_diff.add_pulse_width_diff(frame=10, original=0x1FF, exported=0x200)

        d = voice_diff.to_dict()

        self.assertEqual(d['voice'], 1)
        self.assertEqual(d['frequency']['differences'], 1)
        self.assertEqual(d['waveform']['differences'], 1)
        self.assertEqual(d['pulse_width']['differences'], 1)
        self.assertEqual(d['adsr']['differences'], 0)
        self.assertIsNotNone(d['frequency']['first_diff'])
        # ADSR has no diffs, so first_diff will not be in the dict
        self.assertIsNone(d['adsr'].get('first_diff'))

    def test_voice_diff_samples_limit(self):
        """Test that sample limiting works"""
        voice_diff = VoiceDiff(voice=3)

        # Add 20 frequency differences
        for i in range(20):
            voice_diff.add_frequency_diff(frame=i, original=0x1000 + i, exported=0x2000 + i)

        d = voice_diff.to_dict()

        # Should only keep first 10 in samples
        self.assertEqual(len(d['frequency']['samples']), 10)
        self.assertEqual(d['frequency']['differences'], 20)


class TestComparisonDetailExtractor(unittest.TestCase):
    """Test ComparisonDetailExtractor class"""

    def test_extract_register_diffs_identical_frames(self):
        """Test extracting diffs from identical frames"""
        frames1 = [
            {0x00: 0x34, 0x01: 0x12, 0x04: 0x00},
            {0x00: 0x35, 0x01: 0x12, 0x04: 0x00},
        ]

        frames2 = [
            {0x00: 0x34, 0x01: 0x12, 0x04: 0x00},
            {0x00: 0x35, 0x01: 0x12, 0x04: 0x00},
        ]

        diffs = ComparisonDetailExtractor.extract_register_diffs(frames1, frames2)
        self.assertEqual(len(diffs), 0)

    def test_extract_register_diffs_with_differences(self):
        """Test extracting diffs from different frames"""
        frames1 = [
            {0x00: 0x34, 0x01: 0x12, 0x04: 0x00},
            {0x00: 0x35, 0x01: 0x12, 0x04: 0x80},
        ]

        frames2 = [
            {0x00: 0x34, 0x01: 0x12, 0x04: 0x00},
            {0x00: 0x35, 0x01: 0x12, 0x04: 0x81},  # Different control register
        ]

        diffs = ComparisonDetailExtractor.extract_register_diffs(frames1, frames2)

        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].frame, 1)
        self.assertEqual(diffs[0].register, 0x04)
        self.assertEqual(diffs[0].original_value, 0x80)
        self.assertEqual(diffs[0].exported_value, 0x81)

    def test_extract_voice_diffs(self):
        """Test extracting voice-level differences"""
        frames1 = [
            {0x00: 0x34, 0x01: 0x12},  # Voice 1 frequency
            {0x00: 0x35, 0x01: 0x12},
        ]

        frames2 = [
            {0x00: 0x34, 0x01: 0x12},
            {0x00: 0x36, 0x01: 0x12},  # Different frequency
        ]

        voice_diffs = ComparisonDetailExtractor.extract_voice_diffs(frames1, frames2)

        self.assertIn(1, voice_diffs)
        self.assertEqual(len(voice_diffs[1].frequency_diffs), 1)
        self.assertEqual(voice_diffs[1].frequency_diffs[0][0], 1)  # Frame 1
        self.assertEqual(voice_diffs[1].frequency_diffs[0][1], 0x1235)  # Original
        self.assertEqual(voice_diffs[1].frequency_diffs[0][2], 0x1236)  # Exported

    def test_extract_voice_diffs_all_voices(self):
        """Test extracting diffs for all 3 voices"""
        frames1 = [
            {
                0x00: 0x11, 0x01: 0x11,  # Voice 1 freq
                0x07: 0x22, 0x08: 0x22,  # Voice 2 freq
                0x0E: 0x33, 0x0F: 0x33,  # Voice 3 freq
            }
        ]

        frames2 = [
            {
                0x00: 0x11, 0x01: 0x11,
                0x07: 0x23, 0x08: 0x22,  # Voice 2 different
                0x0E: 0x33, 0x0F: 0x33,
            }
        ]

        voice_diffs = ComparisonDetailExtractor.extract_voice_diffs(frames1, frames2)

        # Voice 1 should have no diffs
        self.assertEqual(len(voice_diffs[1].frequency_diffs), 0)

        # Voice 2 should have 1 diff
        self.assertEqual(len(voice_diffs[2].frequency_diffs), 1)

        # Voice 3 should have no diffs
        self.assertEqual(len(voice_diffs[3].frequency_diffs), 0)


class TestComparisonJSONExporter(unittest.TestCase):
    """Test ComparisonJSONExporter class"""

    def test_format_register_accuracy(self):
        """Test formatting register accuracy data"""
        input_data = {
            'Voice1_FreqLo': {
                'accuracy': 95.5,
                'orig_writes': 100,
                'exp_writes': 100,
                'matches': 95
            }
        }

        formatted = ComparisonJSONExporter._format_register_accuracy(input_data)

        self.assertIn('Voice1_FreqLo', formatted)
        self.assertEqual(formatted['Voice1_FreqLo']['accuracy_percent'], 95.5)
        self.assertEqual(formatted['Voice1_FreqLo']['original_writes'], 100)
        self.assertEqual(formatted['Voice1_FreqLo']['matching_writes'], 95)

    def test_generate_recommendations_excellent(self):
        """Test generating recommendations for excellent accuracy"""
        comparison = {'overall_accuracy': 99.5}
        recs = ComparisonJSONExporter._generate_recommendations(comparison)

        self.assertTrue(any('EXCELLENT' in r for r in recs))

    def test_generate_recommendations_good(self):
        """Test generating recommendations for good accuracy"""
        comparison = {
            'overall_accuracy': 85.0,
            'frame_accuracy': 80.0,
            'filter_accuracy': 70.0,
            'voice_accuracy': {}
        }

        recs = ComparisonJSONExporter._generate_recommendations(comparison)

        self.assertTrue(any('GOOD' in r for r in recs))
        self.assertTrue(any('timing' in r.lower() or 'filter' in r.lower() for r in recs))

    def test_export_comparison_results(self):
        """Test exporting comparison results to JSON"""
        # Create mock objects
        class MockCapture:
            def __init__(self):
                self.sid_path = Path("test.sid")
                self.duration = 30
                self.frames = [
                    {0x00: 0x34, 0x01: 0x12},
                    {0x00: 0x35, 0x01: 0x12},
                ]

        original = MockCapture()
        exported = MockCapture()

        comparison_results = {
            'overall_accuracy': 95.5,
            'frame_accuracy': 95.0,
            'filter_accuracy': 90.0,
            'frame_count_match': True,
            'voice_accuracy': {
                'Voice1': {
                    'frequency_accuracy': 95.0,
                    'waveform_accuracy': 95.0
                }
            },
            'register_accuracy': {
                'Voice1_FreqLo': {
                    'accuracy': 95.0,
                    'orig_writes': 100,
                    'exp_writes': 100,
                    'matches': 95
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            output_path = f.name

        try:
            result = ComparisonJSONExporter.export_comparison_results(
                original,
                exported,
                comparison_results,
                output_path
            )

            self.assertTrue(result)
            self.assertTrue(Path(output_path).exists())

            # Verify JSON structure
            with open(output_path, 'r') as f:
                data = json.load(f)

            self.assertIn('metadata', data)
            self.assertIn('summary', data)
            self.assertIn('voice_accuracy', data)
            self.assertEqual(data['summary']['overall_accuracy'], 95.5)

        finally:
            Path(output_path).unlink(missing_ok=True)


class TestComparisonDiffReporter(unittest.TestCase):
    """Test ComparisonDiffReporter class"""

    def test_generate_text_report(self):
        """Test generating text diff report"""
        class MockCapture:
            def __init__(self):
                self.sid_path = Path("test.sid")
                self.duration = 30
                self.frames = [
                    {0x00: 0x34, 0x01: 0x12, 0x04: 0x00},
                    {0x00: 0x35, 0x01: 0x12, 0x04: 0x80},
                ]

        original = MockCapture()
        exported = MockCapture()

        comparison_results = {
            'overall_accuracy': 95.5,
            'frame_accuracy': 95.0,
            'filter_accuracy': 90.0,
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_path = f.name

        try:
            result = ComparisonDiffReporter.generate_text_report(
                original,
                exported,
                comparison_results,
                output_path
            )

            self.assertTrue(result)
            self.assertTrue(Path(output_path).exists())

            # Verify report content
            with open(output_path, 'r') as f:
                content = f.read()

            self.assertIn('SID ACCURACY COMPARISON', content)
            self.assertIn('95.50', content)  # Overall accuracy
            self.assertIn('VOICE 1', content)

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_text_report_formatting(self):
        """Test that text report is properly formatted"""
        class MockCapture:
            def __init__(self):
                self.sid_path = Path("original.sid")
                self.duration = 30
                self.frames = [
                    {0x00: 0x10, 0x01: 0x20},
                    {0x00: 0x11, 0x01: 0x20},
                ]

        original = MockCapture()
        exported = MockCapture()

        comparison_results = {
            'overall_accuracy': 100.0,
            'frame_accuracy': 100.0,
            'filter_accuracy': 100.0,
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_path = f.name

        try:
            ComparisonDiffReporter.generate_text_report(
                original,
                exported,
                comparison_results,
                output_path
            )

            with open(output_path, 'r') as f:
                lines = f.readlines()

            # Verify structure
            self.assertTrue(any('=' * 80 in line for line in lines))
            self.assertTrue(any('original.sid' in line for line in lines))

        finally:
            Path(output_path).unlink(missing_ok=True)


if __name__ == '__main__':
    unittest.main()
