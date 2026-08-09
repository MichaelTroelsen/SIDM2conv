#!/usr/bin/env python3
"""Tests for A-weighted loudness in sidm2.audio_listen (improvement #2).

Synthetic tones only -- no VICE/sidplayfp needed, runs in the normal suite.

These test BEHAVIOUR, not field existence: the curve is checked against the
published IEC 61672 third-octave table, and the end-to-end dBA offset is
checked against that same curve. A test that only asserted "rms_dba_mean is a
float" would pass on an implementation that returned the unweighted level.

Usage:
    python -m pytest pyscript/test_audio_listen_aweighting.py -v
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.audio_listen import (a_weight_db, a_weighting_correction_db,
                                 extract_features, format_feature_report)

SR = 44100

# IEC 61672 A-weighting, published third-octave values. This is the external
# ground truth -- the formula is checked against it rather than against itself.
IEC_61672_TABLE = {
    31.5: -39.4, 63: -26.2, 125: -16.1, 250: -8.6, 500: -3.2,
    1000: 0.0, 2000: 1.2, 4000: 1.0, 8000: -1.1,
}


def _tone(freq_hz, duration_s=1.0, amp=0.5, sr=SR):
    t = np.arange(int(round(duration_s * sr))) / sr
    return amp * np.sin(2 * np.pi * freq_hz * t)


class TestAWeightCurve(unittest.TestCase):
    def test_matches_published_iec_61672_table(self):
        for f, expected in IEC_61672_TABLE.items():
            self.assertAlmostEqual(float(a_weight_db(f)), expected, delta=0.15,
                                    msg=f"A({f} Hz) disagrees with IEC 61672")

    def test_1khz_is_the_zero_reference(self):
        # The +2.0 dB term in the formula exists solely to make this true.
        self.assertAlmostEqual(float(a_weight_db(1000)), 0.0, places=2)

    def test_dc_is_negative_infinity(self):
        # A real zero of the response, not missing data.
        self.assertEqual(float(a_weight_db(0)), -np.inf)

    def test_accepts_arrays(self):
        out = a_weight_db(np.array([100.0, 1000.0, 4000.0]))
        self.assertEqual(out.shape, (3,))
        self.assertLess(out[0], out[1])

    def test_midrange_is_boosted_not_just_attenuated(self):
        # A-weighting is not monotonic: 2-4 kHz sits ABOVE 0 dB. An
        # implementation that only ever attenuates has the curve wrong.
        self.assertGreater(float(a_weight_db(2000)), 0.0)
        self.assertGreater(float(a_weight_db(4000)), 0.0)


class TestCorrectionArray(unittest.TestCase):
    def test_zero_correction_for_silence(self):
        # No spectrum to weight => no correction invented (score_pct's rule).
        corr = a_weighting_correction_db(np.zeros(SR), SR)
        self.assertTrue(np.all(corr == 0.0))

    def test_empty_input_gives_empty_array(self):
        self.assertEqual(a_weighting_correction_db(np.zeros(0), SR).size, 0)

    def test_frame_count_matches_frame_rms_grid(self):
        # dBA is produced by ADDING this to the per-frame dBFS, so the grids
        # must agree or the two would be misaligned.
        x = _tone(440, duration_s=1.0)
        hop = max(1, int(round(0.01 * SR)))
        win = max(2, int(round(0.04 * SR)))
        expected = (len(x) - win) // hop + 1
        self.assertEqual(len(a_weighting_correction_db(x, SR)), expected)

    def test_correction_equals_the_curve_for_a_pure_tone(self):
        for f in (440, 1000, 2000):
            corr = a_weighting_correction_db(_tone(f), SR)
            self.assertAlmostEqual(float(np.mean(corr)), float(a_weight_db(f)),
                                    delta=0.1, msg=f"{f} Hz")


class TestEndToEndLevels(unittest.TestCase):
    """The plan's stated acceptance criteria, plus the sign behaviour."""

    def test_1khz_dba_matches_dbfs(self):
        ft = extract_features(_tone(1000), SR)
        self.assertAlmostEqual(ft.rms_dba_mean, ft.rms_db_mean, delta=0.5)

    def test_60hz_is_discounted_by_roughly_the_curve(self):
        ft = extract_features(_tone(60), SR)
        offset = ft.rms_dba_mean - ft.rms_db_mean
        self.assertLess(offset, -20.0, "60 Hz must be heavily discounted")
        # Within the documented low-frequency residual (FFT bin width).
        self.assertAlmostEqual(offset, float(a_weight_db(60)), delta=1.5)

    def test_bass_discounted_more_than_midrange(self):
        off = {}
        for f in (55, 220, 1000):
            ft = extract_features(_tone(f), SR)
            off[f] = ft.rms_dba_mean - ft.rms_db_mean
        self.assertLess(off[55], off[220])
        self.assertLess(off[220], off[1000])

    def test_2khz_is_boosted_above_dbfs(self):
        # Sign check: dBA > dBFS here. Catches a dropped minus sign that the
        # bass-attenuation tests alone would not.
        ft = extract_features(_tone(2000), SR)
        self.assertGreater(ft.rms_dba_mean, ft.rms_db_mean)

    def test_raw_dbfs_fields_are_untouched(self):
        # #2 is additive by design -- raw dBFS stays authoritative for exact
        # level checks, so adding A-weighting must not perturb it.
        x = _tone(440)
        ft = extract_features(x, SR)
        hop = max(1, int(round(0.01 * SR)))
        win = max(2, int(round(0.04 * SR)))
        n = (len(x) - win) // hop + 1
        rms = np.array([np.sqrt(np.mean(x[i * hop:i * hop + win] ** 2)) for i in range(n)])
        self.assertAlmostEqual(ft.rms_db_mean, float(np.mean(20 * np.log10(rms))), places=6)

    def test_dba_is_a_correction_on_dbfs_not_a_separate_scale(self):
        x = _tone(220)
        ft = extract_features(x, SR)
        corr = a_weighting_correction_db(x, SR)
        self.assertAlmostEqual(ft.rms_dba_mean - ft.rms_db_mean,
                                float(np.mean(corr)), places=6)


class TestIndependentOfBandSettings(unittest.TestCase):
    """The whole reason for a dedicated STFT: nb/band_scale must not matter.

    Reading the curve off band_energies()' bands instead would put a 12.8 dB
    error on a 55 Hz tone -- documented in audio_listen.py's A-weighting block.
    """

    def test_offset_is_invariant(self):
        x = _tone(220)
        offsets = []
        for kw in (dict(), dict(nb=96), dict(nb=12),
                   dict(band_scale='mel'), dict(nb=96, band_scale='mel')):
            ft = extract_features(x, SR, **kw)
            offsets.append(ft.rms_dba_mean - ft.rms_db_mean)
        for o in offsets[1:]:
            self.assertAlmostEqual(o, offsets[0], places=9)

    def test_a_banded_lookup_would_have_been_badly_wrong(self):
        """Pins WHY the dedicated STFT exists, so it cannot be 'simplified'.

        If someone replaces the per-bin weighting with a band-centre lookup,
        the 55 Hz error jumps from ~1.4 dB to ~12.8 dB. This records that gap
        as arithmetic rather than as a comment nobody rechecks.
        """
        nb, fmin, fmax = 40, 30, 8000
        edges = np.linspace(fmin, fmax, nb + 1)
        centers = (edges[:-1] + edges[1:]) / 2
        i = min(int(np.searchsorted(edges, 55)) - 1, nb - 1)
        banded_error = abs(float(a_weight_db(centers[i])) - float(a_weight_db(55)))
        self.assertGreater(banded_error, 10.0)

        ft = extract_features(_tone(55), SR)
        actual_error = abs((ft.rms_dba_mean - ft.rms_db_mean) - float(a_weight_db(55)))
        self.assertLess(actual_error, 2.0)
        self.assertLess(actual_error, banded_error / 5)


class TestDegenerateInputs(unittest.TestCase):
    def test_silence_leaves_dba_equal_to_dbfs(self):
        ft = extract_features(np.zeros(SR), SR)
        self.assertEqual(ft.rms_dba_mean, ft.rms_db_mean)

    def test_empty_input_uses_the_no_evidence_default(self):
        ft = extract_features(np.zeros(0), SR)
        self.assertEqual(ft.rms_dba_mean, -120.0)
        self.assertEqual(ft.rms_dba_max, -120.0)

    def test_signal_shorter_than_one_window_does_not_crash(self):
        ft = extract_features(_tone(440, duration_s=0.01), SR)
        self.assertIsInstance(ft.rms_dba_mean, float)


class TestReport(unittest.TestCase):
    def test_report_includes_the_dba_row(self):
        a = extract_features(_tone(60), SR)
        b = extract_features(_tone(1000), SR)
        report = format_feature_report(a, b)
        self.assertIn('A-wtd', report)
        self.assertIn('dBA', report)

    def test_report_shows_the_perceptual_gap_dbfs_misses(self):
        # Same amplitude, wildly different loudness: the dBFS rows agree while
        # the dBA row does not. This is the case that motivates the feature.
        a = extract_features(_tone(60), SR)
        b = extract_features(_tone(1000), SR)
        self.assertAlmostEqual(a.rms_db_mean, b.rms_db_mean, delta=0.5)
        self.assertGreater(abs(a.rms_dba_mean - b.rms_dba_mean), 20.0)


if __name__ == '__main__':
    unittest.main()
