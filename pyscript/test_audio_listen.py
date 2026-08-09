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
    CHROMA_WIN_S,
    PITCH_CLASS_NAMES,
    chroma_shift_description,
    chroma_vector,
    dominant_pitch_classes,
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


def _peak_class(chroma):
    return PITCH_CLASS_NAMES[int(np.argmax(chroma))]


class TestChromaVector(unittest.TestCase):
    def test_a4_peaks_on_a(self):
        self.assertEqual(_peak_class(chroma_vector(_tone(SR, 2.0, 440.0), SR)), 'A')

    def test_adjacent_semitone_lands_in_a_different_bin(self):
        # A4 vs A#4 -- one semitone apart. If these collapsed into one bin the
        # whole feature would be useless for detecting a transposition error.
        a4 = _peak_class(chroma_vector(_tone(SR, 2.0, 440.0), SR))
        as4 = _peak_class(chroma_vector(_tone(SR, 2.0, 466.16), SR))
        self.assertEqual(a4, 'A')
        self.assertEqual(as4, 'A#')

    def test_octaves_fold_to_the_same_pitch_class(self):
        for f in (110.0, 220.0, 440.0, 880.0):
            self.assertEqual(_peak_class(chroma_vector(_tone(SR, 2.0, f), SR)), 'A',
                             f"{f} Hz should fold to A")

    def test_c4_and_e4(self):
        self.assertEqual(_peak_class(chroma_vector(_tone(SR, 2.0, 261.63), SR)), 'C')
        self.assertEqual(_peak_class(chroma_vector(_tone(SR, 2.0, 329.63), SR)), 'E')

    def test_normalized_to_sum_one(self):
        c = chroma_vector(_tone(SR, 2.0, 440.0), SR)
        self.assertAlmostEqual(c.sum(), 1.0, places=9)
        self.assertEqual(c.shape, (12,))

    def test_silence_returns_all_zeros_not_a_flat_distribution(self):
        # "No pitched energy" must be distinguishable from "every class equally
        # present" -- same no-evidence-is-not-a-zero rule as score_pct.
        c = chroma_vector(_silence(SR, 2.0), SR)
        self.assertEqual(c.shape, (12,))
        self.assertEqual(c.sum(), 0.0)

    def test_signal_shorter_than_window_returns_zeros(self):
        c = chroma_vector(_tone(SR, 0.05, 440.0), SR)
        self.assertEqual(c.sum(), 0.0)


class TestChromaResolvesSidBassRegister(unittest.TestCase):
    """The window-length constraint, pinned with the measurement behind it.

    Chroma needs a LONGER window than the 40 ms used for onset timing elsewhere
    in this module. Measured on a 55 Hz (A1) tone, the register SID bass
    actually occupies:

        40 ms  -> 'G'  (0.693, margin +0.385)   CONFIDENTLY WRONG
        100 ms -> 'B'  (0.481, margin  0.000)   wrong, and a tie
        200 ms -> 'A'  (0.667, margin +0.500)   correct
        400 ms -> 'A'  (0.667, margin +0.500)   correct, no further gain

    The 40 ms failure is the dangerous one: it is not noisy, it is wrong with a
    large margin, which is exactly the shape of result that gets believed. This
    test exists so a future "why is the chroma window different from every other
    window in this file" cleanup fails loudly instead of silently reintroducing
    it.
    """

    def test_bass_a1_resolves_at_the_default_window(self):
        self.assertEqual(_peak_class(chroma_vector(_tone(SR, 2.0, 55.0), SR)), 'A')

    def test_bass_a1_is_misidentified_at_the_onset_timing_window(self):
        wrong = _peak_class(chroma_vector(_tone(SR, 2.0, 55.0), SR, win_s=0.04, hop_s=0.02))
        self.assertNotEqual(wrong, 'A')

    def test_default_window_is_long_enough(self):
        self.assertGreaterEqual(CHROMA_WIN_S, 0.2)

    def test_low_c1_edge_of_band_is_included(self):
        # 32.7 Hz is the band floor; it must not be silently discarded.
        self.assertGreater(chroma_vector(_tone(SR, 2.0, 32.703), SR).sum(), 0.0)


class TestChromaShiftDescription(unittest.TestCase):
    def test_names_the_gaining_and_losing_classes(self):
        a = chroma_vector(_tone(SR, 2.0, 440.0), SR)      # A
        b = chroma_vector(_tone(SR, 2.0, 466.16), SR)     # A#
        desc = chroma_shift_description(a, b)
        self.assertIn('A#', desc)
        self.assertIn('toward', desc)
        self.assertIn('away from', desc)

    def test_identical_chroma_reports_unchanged(self):
        a = chroma_vector(_tone(SR, 2.0, 440.0), SR)
        self.assertIn('unchanged', chroma_shift_description(a, a))

    def test_empty_original_is_refused_not_described(self):
        a = np.zeros(12)
        b = chroma_vector(_tone(SR, 2.0, 440.0), SR)
        self.assertIn('no pitched energy in the original',
                      chroma_shift_description(a, b))

    def test_empty_driver_is_refused_not_described(self):
        a = chroma_vector(_tone(SR, 2.0, 440.0), SR)
        self.assertIn('no pitched energy in the driver',
                      chroma_shift_description(a, np.zeros(12)))

    def test_both_empty(self):
        self.assertIn('either side', chroma_shift_description(np.zeros(12), np.zeros(12)))

    def test_wrong_shape_is_reported(self):
        self.assertIn('unavailable', chroma_shift_description(np.zeros(5), np.zeros(12)))


class TestDominantPitchClasses(unittest.TestCase):
    def test_names_the_strongest_class_first(self):
        out = dominant_pitch_classes(chroma_vector(_tone(SR, 2.0, 440.0), SR))
        self.assertTrue(out.startswith('A '), out)

    def test_empty_chroma_is_na(self):
        self.assertEqual(dominant_pitch_classes(np.zeros(12)), 'n/a')


class TestChromaIsWiredIntoTheReport(unittest.TestCase):
    def test_extract_features_populates_chroma(self):
        feats = extract_features(_tone(SR, 2.0, 440.0), SR)
        self.assertEqual(feats.chroma.shape, (12,))
        self.assertAlmostEqual(feats.chroma.sum(), 1.0, places=9)
        self.assertEqual(_peak_class(feats.chroma), 'A')

    def test_short_signal_leaves_chroma_empty_without_crashing(self):
        feats = extract_features(_tone(SR, 0.01, 440.0), SR)
        self.assertEqual(feats.chroma.shape, (12,))
        self.assertEqual(feats.chroma.sum(), 0.0)

    def test_report_includes_pitch_rows(self):
        a = extract_features(_tone(SR, 2.0, 440.0), SR)
        b = extract_features(_tone(SR, 2.0, 466.16), SR)
        report = format_feature_report(a, b)
        self.assertIn('dominant pitch', report)
        self.assertIn('pitch content:', report)

    def test_report_flags_a_transposition_the_centroid_barely_moves_on(self):
        # One semitone up: centroid shifts ~26 Hz (easy to dismiss as noise),
        # but the pitch class changes outright. This is the case chroma exists
        # for, so assert the report actually names it.
        a = extract_features(_tone(SR, 2.0, 440.0), SR)
        b = extract_features(_tone(SR, 2.0, 466.16), SR)
        self.assertIn('A#', format_feature_report(a, b))


if __name__ == '__main__':
    unittest.main()
