#!/usr/bin/env python3
"""Tests for mel-scale band spacing (improvement #1).

Covers sidm2.audio_tightness's band geometry (band_edges / band_centers /
band_energies / undersampled_bands) and its opt-in use from
sidm2.audio_listen.extract_features(band_scale='mel').

Two things these lock down, in order of importance:

1. THE LINEAR DEFAULT IS UNCHANGED. detect_onsets() feeds band_energies()
   straight into the onset comparison that most of this project's published
   fidelity numbers rest on. Mel spacing is opt-in per call site and any change
   to that must fail here first.
2. Mel actually buys what it claims. Linear spacing cannot resolve a full
   octave in SID's bass register -- see TestLinearCannotSeeAnOctave.

Usage:
    python -m pytest pyscript/test_audio_mel_scale.py -v
"""
import logging
import sys
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.audio_tightness import (BAND_SCALES, band_centers, band_edges,
                                    band_energies, detect_onsets, hz_to_mel,
                                    logmel_distance, mel_to_hz,
                                    undersampled_bands)
from sidm2.audio_listen import (AudioFeatures, extract_features,
                                 extract_features_windowed, format_feature_report)

SR = 44100


def _tone(freq_hz, duration_s=1.0, sr=SR, amp=0.5):
    t = np.arange(int(round(duration_s * sr))) / sr
    return amp * np.sin(2 * np.pi * freq_hz * t)


class TestMelConversion(unittest.TestCase):
    def test_round_trip(self):
        for f in (30.0, 100.0, 440.0, 2000.0, 8000.0):
            self.assertAlmostEqual(float(mel_to_hz(hz_to_mel(f))), f, places=6)

    def test_zero_hz_is_zero_mel(self):
        self.assertAlmostEqual(float(hz_to_mel(0.0)), 0.0, places=9)

    def test_monotonic(self):
        f = np.array([0.0, 50.0, 500.0, 5000.0])
        self.assertTrue(np.all(np.diff(hz_to_mel(f)) > 0))

    def test_array_input_supported(self):
        out = hz_to_mel(np.array([100.0, 200.0]))
        self.assertEqual(out.shape, (2,))


class TestBandEdges(unittest.TestCase):
    def test_linear_is_exactly_linspace(self):
        # Regression guard: the previous implementation was an inline
        # np.linspace, and every existing number in this project came from it.
        np.testing.assert_allclose(band_edges(40, 30, 8000, 'linear'),
                                    np.linspace(30, 8000, 41))

    def test_default_scale_is_linear(self):
        np.testing.assert_allclose(band_edges(40, 30, 8000),
                                    band_edges(40, 30, 8000, 'linear'))

    def test_edge_count(self):
        for scale in BAND_SCALES:
            self.assertEqual(len(band_edges(40, 30, 8000, scale)), 41)

    def test_endpoints_preserved_under_mel(self):
        e = band_edges(40, 30, 8000, 'mel')
        self.assertAlmostEqual(e[0], 30.0, places=6)
        self.assertAlmostEqual(e[-1], 8000.0, places=6)

    def test_mel_edges_monotonic(self):
        self.assertTrue(np.all(np.diff(band_edges(40, 30, 8000, 'mel')) > 0))

    def test_mel_band_width_increases_with_frequency(self):
        # The whole point of mel spacing: narrow bands low, wide bands high.
        widths = np.diff(band_edges(40, 30, 8000, 'mel'))
        self.assertTrue(np.all(np.diff(widths) > 0))

    def test_linear_band_width_is_constant(self):
        widths = np.diff(band_edges(40, 30, 8000, 'linear'))
        np.testing.assert_allclose(widths, widths[0])

    def test_mel_puts_more_bands_where_sid_material_lives(self):
        # The assessment doc's complaint: under linear, half the bins sit above
        # 4 kHz where SID material rarely is.
        lin = band_edges(40, 30, 8000, 'linear')[:-1]
        mel = band_edges(40, 30, 8000, 'mel')[:-1]
        self.assertEqual(int((lin < 4000).sum()), 20)
        self.assertEqual(int((mel < 4000).sum()), 31)

    def test_unknown_scale_raises(self):
        with self.assertRaises(ValueError) as cm:
            band_edges(40, 30, 8000, 'bark')
        self.assertIn('bark', str(cm.exception))


class TestBandCenters(unittest.TestCase):
    def test_centers_lie_between_edges(self):
        for scale in BAND_SCALES:
            e = band_edges(40, 30, 8000, scale)
            c = band_centers(40, 30, 8000, scale)
            self.assertEqual(len(c), 40)
            self.assertTrue(np.all(c > e[:-1]))
            self.assertTrue(np.all(c < e[1:]))

    def test_centers_track_the_scale_they_were_asked_for(self):
        # The bug this exists to prevent: energies binned with mel edges but
        # centres computed from a linear linspace.
        self.assertFalse(np.allclose(band_centers(40, 30, 8000, 'mel'),
                                      band_centers(40, 30, 8000, 'linear')))


class TestUndersampling(unittest.TestCase):
    """A mel band narrower than the FFT resolution contains no bin and reads as
    exactly zero -- indistinguishable from silence, and fatal to flatness."""

    def test_default_config_is_safe(self):
        self.assertEqual(undersampled_bands(SR, 0.04, 40, 30, 8000, 'mel'), 0)

    def test_linear_never_undersamples_at_these_settings(self):
        for nb in (40, 96, 128):
            self.assertEqual(undersampled_bands(SR, 0.04, nb, 30, 8000, 'linear'), 0)

    def test_high_band_count_undersamples_under_mel(self):
        # nb=96 is what the spectrogram path uses; measured 11 bands narrower
        # than the 25 Hz FFT bin at a 40 ms window.
        self.assertGreater(undersampled_bands(SR, 0.04, 96, 30, 8000, 'mel'), 0)

    def test_longer_window_fixes_it(self):
        self.assertEqual(undersampled_bands(SR, 0.2, 96, 30, 8000, 'mel'), 0)

    def test_band_energies_warns_when_undersampled(self):
        with self.assertLogs('sidm2.audio_tightness', level=logging.WARNING) as cm:
            band_energies(_tone(440, 0.3), SR, nb=96, scale='mel')
        self.assertIn('narrower', ' '.join(cm.output))

    def test_band_energies_is_quiet_in_the_safe_default(self):
        logger = logging.getLogger('sidm2.audio_tightness')
        with mock.patch.object(logger, 'warning') as warn:
            band_energies(_tone(440, 0.3), SR, nb=40, scale='mel')
        warn.assert_not_called()


class TestBandEnergiesBackwardCompatible(unittest.TestCase):
    """The linear default must be untouched -- fidelity numbers depend on it."""

    def test_default_equals_explicit_linear(self):
        x = _tone(440, 0.3)
        np.testing.assert_allclose(band_energies(x, SR),
                                    band_energies(x, SR, scale='linear'))

    def test_mel_actually_changes_the_output(self):
        x = _tone(440, 0.3)
        self.assertFalse(np.allclose(band_energies(x, SR, scale='linear'),
                                      band_energies(x, SR, scale='mel')))

    def test_shape_is_unchanged_by_scale(self):
        x = _tone(440, 0.3)
        self.assertEqual(band_energies(x, SR, scale='linear').shape,
                          band_energies(x, SR, scale='mel').shape)

    def test_empty_input_still_returns_empty(self):
        self.assertEqual(band_energies(np.zeros(4), SR, scale='mel').shape, (0, 40))

    def test_detect_onsets_default_path_unaffected(self):
        # detect_onsets does not expose scale; it must keep using linear.
        x = np.zeros(SR)
        for t in (0.1, 0.3, 0.5, 0.7):
            i = int(t * SR)
            x[i:i + 400] += np.hanning(400) * 0.8
        self.assertGreaterEqual(len(detect_onsets(x, SR)), 3)


class TestLogmelDistance(unittest.TestCase):
    def test_default_is_linear_and_unchanged(self):
        a, b = _tone(440, 0.1), _tone(880, 0.1)
        self.assertAlmostEqual(logmel_distance(a, b, SR),
                               logmel_distance(a, b, SR, scale='linear'), places=12)

    def test_identical_segments_score_zero_under_both_scales(self):
        a = _tone(440, 0.1)
        for scale in BAND_SCALES:
            self.assertAlmostEqual(logmel_distance(a, a, SR, scale=scale), 0.0, places=9)


class TestLinearCannotSeeAnOctave(unittest.TestCase):
    """The measured justification for this whole change.

    100 Hz and 200 Hz are one octave apart -- the most basic musical interval.
    Under linear spacing with the defaults, both land in band 0 (width 199 Hz)
    and the reported centroid moves by 0.1 Hz. That is not a noisy answer; it
    is a confident near-zero, the shape of result that gets believed.
    """

    def test_linear_reports_almost_no_change_across_an_octave(self):
        lo = extract_features(_tone(100), SR).centroid_hz_mean
        hi = extract_features(_tone(200), SR).centroid_hz_mean
        self.assertLess(abs(hi - lo), 1.0)

    def test_mel_resolves_the_same_octave(self):
        lo = extract_features(_tone(100), SR, band_scale='mel').centroid_hz_mean
        hi = extract_features(_tone(200), SR, band_scale='mel').centroid_hz_mean
        self.assertGreater(hi - lo, 50.0)

    def test_peak_band_separates_under_mel_but_not_linear(self):
        def peak(freq, scale):
            return int(np.argmax(band_energies(_tone(freq), SR, scale=scale).mean(axis=0)))
        self.assertEqual(peak(100, 'linear'), peak(200, 'linear'))
        self.assertNotEqual(peak(100, 'mel'), peak(200, 'mel'))


class TestExtractFeaturesBandScale(unittest.TestCase):
    def test_default_is_linear(self):
        self.assertEqual(extract_features(_tone(440), SR).band_scale, 'linear')

    def test_scale_is_recorded(self):
        self.assertEqual(extract_features(_tone(440), SR, band_scale='mel').band_scale, 'mel')

    def test_recorded_on_the_silent_early_return_too(self):
        feats = extract_features(np.zeros(4), SR, band_scale='mel')
        self.assertEqual(feats.band_scale, 'mel')

    def test_centroid_ordering_still_holds_under_mel(self):
        lo = extract_features(_tone(200), SR, band_scale='mel')
        hi = extract_features(_tone(3000), SR, band_scale='mel')
        self.assertLess(lo.centroid_hz_mean, hi.centroid_hz_mean)

    def test_invalid_scale_propagates(self):
        with self.assertRaises(ValueError):
            extract_features(_tone(440), SR, band_scale='bark')

    def test_windowed_threads_the_scale_through(self):
        windows = extract_features_windowed(_tone(440, 12.0), SR, window_s=5.0,
                                             band_scale='mel')
        self.assertGreaterEqual(len(windows), 2)
        self.assertTrue(all(f.band_scale == 'mel' for _, f in windows))


class TestReportRefusesMixedScales(unittest.TestCase):
    """Differencing a linear against a mel AudioFeatures would report the
    measurement settings as if they were a property of the driver."""

    def test_mismatch_is_refused(self):
        a = extract_features(_tone(440), SR)
        b = extract_features(_tone(440), SR, band_scale='mel')
        report = format_feature_report(a, b)
        self.assertIn('REFUSED', report)
        self.assertIn('band scale', report)

    def test_matching_scales_report_normally(self):
        a = extract_features(_tone(440), SR, band_scale='mel')
        b = extract_features(_tone(880), SR, band_scale='mel')
        report = format_feature_report(a, b)
        self.assertNotIn('REFUSED', report)
        self.assertIn('spectral centroid', report)

    def test_mel_report_says_which_geometry_it_used(self):
        a = extract_features(_tone(440), SR, band_scale='mel')
        b = extract_features(_tone(880), SR, band_scale='mel')
        self.assertIn('mel', format_feature_report(a, b).splitlines()[0])

    def test_linear_report_header_is_unchanged(self):
        a = extract_features(_tone(440), SR)
        b = extract_features(_tone(880), SR)
        self.assertNotIn('mel', format_feature_report(a, b).splitlines()[0])

    def test_default_constructed_features_are_linear(self):
        # A hand-built AudioFeatures (tests, JSON round-trip) must not
        # accidentally look like a mel one and trip the guard.
        f = AudioFeatures(duration_s=1.0, rms_db_mean=-10, rms_db_max=-9,
                          silence_frac=0.0, centroid_hz_mean=100,
                          centroid_hz_std=0.0, rolloff85_hz_mean=200,
                          zcr_mean=0.1, flatness_mean=0.2)
        self.assertEqual(f.band_scale, 'linear')


if __name__ == '__main__':
    unittest.main()
