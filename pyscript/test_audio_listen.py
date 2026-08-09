#!/usr/bin/env python3
"""Unit Tests for sidm2.audio_listen

Tests the pure numpy/Pillow feature-extraction and spectrogram-rendering
functions against synthetic tone/noise fixtures -- no VICE/SID2WAV needed,
runs in the normal pytest suite.

Usage:
    python -m pytest pyscript/test_audio_listen.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.audio_listen import (
    AudioFeatures,
    extract_features,
    format_feature_report,
    render_comparison_spectrogram,
)

SR = 44100


def _tone(sr, duration_s, freq_hz, amp=0.5):
    n = int(round(duration_s * sr))
    t = np.arange(n) / sr
    return (amp * np.sin(2 * np.pi * freq_hz * t)).astype(np.float64)


def _white_noise(sr, duration_s, amp=0.5, seed=0):
    n = int(round(duration_s * sr))
    rng = np.random.RandomState(seed)
    return (amp * rng.uniform(-1, 1, n)).astype(np.float64)


def _silence(sr, duration_s):
    return np.zeros(int(round(duration_s * sr)))


class TestExtractFeaturesSilence(unittest.TestCase):
    def test_silence_reports_full_silence_fraction(self):
        feats = extract_features(_silence(SR, 1.0), SR)
        self.assertEqual(feats.silence_frac, 1.0)
        self.assertEqual(feats.centroid_hz_mean, 0.0)

    def test_empty_array_does_not_crash(self):
        feats = extract_features(np.zeros(0), SR)
        self.assertIsInstance(feats, AudioFeatures)
        self.assertEqual(feats.silence_frac, 1.0)


class TestExtractFeaturesTone(unittest.TestCase):
    def test_low_tone_has_lower_centroid_than_high_tone(self):
        low = extract_features(_tone(SR, 1.0, 200), SR)
        high = extract_features(_tone(SR, 1.0, 3000), SR)
        self.assertLess(low.centroid_hz_mean, high.centroid_hz_mean)

    def test_pure_tone_is_not_silent(self):
        feats = extract_features(_tone(SR, 1.0, 440), SR)
        self.assertLess(feats.silence_frac, 0.5)
        self.assertGreater(feats.rms_db_mean, -50.0)

    def test_pure_tone_is_more_tonal_than_white_noise(self):
        tone = extract_features(_tone(SR, 1.0, 440), SR)
        noise = extract_features(_white_noise(SR, 1.0), SR)
        # flatness: geometric/arithmetic mean of band energy, closer to 1.0 = noisier
        self.assertLess(tone.flatness_mean, noise.flatness_mean)

    def test_louder_signal_has_higher_rms(self):
        quiet = extract_features(_tone(SR, 1.0, 440, amp=0.05), SR)
        loud = extract_features(_tone(SR, 1.0, 440, amp=0.9), SR)
        self.assertLess(quiet.rms_db_mean, loud.rms_db_mean)

    def test_duration_matches_input_length(self):
        feats = extract_features(_tone(SR, 2.5, 440), SR)
        self.assertAlmostEqual(feats.duration_s, 2.5, places=1)


class TestFormatFeatureReport(unittest.TestCase):
    def test_report_is_readable_text_with_both_labels(self):
        a = extract_features(_tone(SR, 1.0, 440), SR)
        b = extract_features(_tone(SR, 1.0, 880), SR)
        report = format_feature_report(a, b, orig_label='orig.sid', driver_label='driver.sf2')
        self.assertIsInstance(report, str)
        self.assertIn('orig.sid', report)
        self.assertIn('driver.sf2', report)
        self.assertIn('spectral centroid', report)

    def test_report_shows_signed_delta(self):
        a = extract_features(_tone(SR, 1.0, 200), SR)
        b = extract_features(_tone(SR, 1.0, 4000), SR)
        report = format_feature_report(a, b)
        # driver (b) is brighter than orig (a), so the centroid delta must be positive
        centroid_line = [l for l in report.splitlines() if 'spectral centroid' in l][0]
        delta_field = " ".join(centroid_line.split()[-2:])
        self.assertIn('+', delta_field)


class TestRenderComparisonSpectrogram(unittest.TestCase):
    def test_writes_a_valid_png(self):
        from PIL import Image
        orig = _tone(SR, 1.0, 440)
        driver = _tone(SR, 1.0, 880)
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "spec.png"
            result = render_comparison_spectrogram(orig, SR, driver, SR, out_path)
            self.assertTrue(result.exists())
            with Image.open(result) as img:
                img.load()
                self.assertEqual(img.format, 'PNG')
                self.assertGreater(img.width, 0)
                self.assertGreater(img.height, 0)

    def test_creates_parent_directories(self):
        orig = _tone(SR, 0.5, 440)
        driver = _tone(SR, 0.5, 440)
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "nested" / "dir" / "spec.png"
            result = render_comparison_spectrogram(orig, SR, driver, SR, out_path)
            self.assertTrue(result.exists())

    def test_different_sample_rates_do_not_crash(self):
        orig = _tone(44100, 0.5, 440)
        driver = _tone(22050, 0.5, 440)
        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "spec.png"
            result = render_comparison_spectrogram(orig, 44100, driver, 22050, out_path)
            self.assertTrue(result.exists())


if __name__ == '__main__':
    unittest.main()
