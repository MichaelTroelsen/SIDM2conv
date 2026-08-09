#!/usr/bin/env python3
"""Tests for sidm2.audio_listen's windowed (section-aware) features.

Improvement #4 from docs/AUDIO_LISTENING_IMPROVEMENT_PLANS.md: a defect confined
to one passage is diluted by every correct second around it when features are
reported only as a whole-file mean. These pin that a localized problem is
actually found -- and, just as importantly, that a UNIFORM difference is NOT
reported as a localized one.

Usage:
    python -m pytest pyscript/test_audio_listen_windowed.py -v
"""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.audio_listen import (MIN_WINDOWS_FOR_OUTLIER, WINDOW_OUTLIER_SIGMA, WINDOW_S,
                                 _robust_spread, extract_features_windowed,
                                 format_windowed_diff_report, worst_window)

SR = 22050  # half rate: these fixtures are seconds long, and nothing here is rate-sensitive


def _tone(duration_s, freq_hz=440.0, amp=0.5, sr=SR):
    t = np.arange(int(round(duration_s * sr))) / sr
    return (amp * np.sin(2 * np.pi * freq_hz * t)).astype(np.float64)


def _noise(duration_s, amp=0.5, sr=SR, seed=0):
    rng = np.random.RandomState(seed)
    return (amp * rng.uniform(-1, 1, int(round(duration_s * sr)))).astype(np.float64)


class TestExtractFeaturesWindowed(unittest.TestCase):
    def test_splits_into_expected_window_count(self):
        w = extract_features_windowed(_tone(10.0), SR, window_s=2.0)
        self.assertEqual(len(w), 5)

    def test_start_times_are_window_aligned(self):
        w = extract_features_windowed(_tone(10.0), SR, window_s=2.0)
        self.assertEqual([round(t, 3) for t, _ in w], [0.0, 2.0, 4.0, 6.0, 8.0])

    def test_each_window_reports_its_own_duration(self):
        w = extract_features_windowed(_tone(6.0), SR, window_s=2.0)
        for _, feats in w:
            self.assertAlmostEqual(feats.duration_s, 2.0, places=2)

    def test_signal_shorter_than_one_window_yields_one_window(self):
        # Not [] -- a short render must still report something.
        w = extract_features_windowed(_tone(1.0), SR, window_s=5.0)
        self.assertEqual(len(w), 1)
        self.assertEqual(w[0][0], 0.0)

    def test_empty_signal_yields_no_windows(self):
        self.assertEqual(extract_features_windowed(np.zeros(0), SR), [])

    def test_short_trailing_remainder_is_dropped(self):
        # 5.2s at 2s windows: the 1.2s tail is >= half a window so it stays;
        # 5.0s exactly gives 2 full windows plus a 1.0s tail (exactly half).
        self.assertEqual(len(extract_features_windowed(_tone(5.2), SR, window_s=2.0)), 3)
        # 4.2s -> windows at 0,2 and a 0.2s stub, which is under half and dropped.
        self.assertEqual(len(extract_features_windowed(_tone(4.2), SR, window_s=2.0)), 2)

    def test_hop_shorter_than_window_overlaps(self):
        w = extract_features_windowed(_tone(10.0), SR, window_s=4.0, hop_s=2.0)
        # 8.0 is kept: it spans 8-10s = exactly half a window, the MIN_WINDOW_FRACTION floor.
        self.assertEqual([round(t, 3) for t, _ in w], [0.0, 2.0, 4.0, 6.0, 8.0])

    def test_default_window_is_the_module_constant(self):
        w = extract_features_windowed(_tone(WINDOW_S * 2), SR)
        self.assertEqual(len(w), 2)


class TestRobustSpread(unittest.TestCase):
    def test_identical_values_have_no_spread(self):
        self.assertEqual(_robust_spread(np.array([3.0, 3.0, 3.0, 3.0])), 0.0)

    def test_empty_has_no_spread(self):
        self.assertEqual(_robust_spread(np.array([])), 0.0)

    def test_degenerate_mad_returns_zero_rather_than_falling_back_to_std(self):
        # The classic MAD breakdown: a majority of identical values makes MAD
        # exactly 0 even though one value is plainly an outlier. _robust_spread
        # reports that honestly (0.0) and the caller switches to the flat-baseline
        # branch. It must NOT fall back to std -- see the next test for why.
        v = np.array([0.0, 0.0, 0.0, 0.0, 10.0])
        self.assertEqual(_robust_spread(v), 0.0)

    def test_std_fallback_would_have_capped_a_lone_outlier_below_threshold(self):
        """Why the std fallback is gone, pinned as arithmetic.

        For one outlier among n identical values, std-based z has a hard ceiling
        of n/sqrt(n-1) -- 2.5 at n=5, BELOW WINDOW_OUTLIER_SIGMA=3. The clearest
        possible defect would have been reported as 'nothing stands out'.
        """
        v = np.array([0.0, 0.0, 0.0, 0.0, 10.0])
        z_if_std_used = float(np.max(np.abs(v - np.median(v))) / np.std(v))
        self.assertLess(z_if_std_used, WINDOW_OUTLIER_SIGMA)
        self.assertAlmostEqual(z_if_std_used, 5 / np.sqrt(4), places=6)

    def test_outlier_does_not_inflate_its_own_yardstick(self):
        # MAD is used precisely so the bad window can't widen the scale it is
        # judged against; std would be dragged upward by the outlier.
        v = np.array([1.0, 1.1, 0.9, 1.0, 50.0])
        self.assertLess(_robust_spread(v), float(np.std(v)))


class TestWorstWindowFindsLocalizedDefect(unittest.TestCase):
    """The plan's specified case: clean tone, then tone + noise."""

    def _pair(self):
        clean = np.concatenate([_tone(4.0) for _ in range(5)])
        # driver matches for 16s, then one 4s section goes noisy
        broken = np.concatenate([_tone(4.0), _tone(4.0), _tone(4.0), _tone(4.0),
                                  _tone(4.0) + _noise(4.0, amp=0.4)])
        o = extract_features_windowed(clean, SR, window_s=4.0)
        d = extract_features_windowed(broken, SR, window_s=4.0)
        return o, d

    def test_noisy_section_has_higher_flatness(self):
        o, d = self._pair()
        self.assertGreater(d[4][1].flatness_mean, d[0][1].flatness_mean)

    def test_worst_window_points_at_the_noisy_section(self):
        o, d = self._pair()
        out = worst_window(o, d)
        self.assertIsNotNone(out)
        self.assertEqual(out.index, 4)
        self.assertAlmostEqual(out.start_s, 16.0, places=1)

    def test_worst_window_clears_the_outlier_threshold(self):
        o, d = self._pair()
        self.assertTrue(worst_window(o, d).is_outlier)

    def test_lone_obvious_defect_is_judged_on_the_flat_baseline_branch(self):
        # Four identical windows plus one broken one is the MAD-degenerate case;
        # this is the regression guard for the 2.5-sigma false negative.
        out = worst_window(*self._pair())
        self.assertEqual(out.basis, 'flat-baseline')
        self.assertGreater(out.score, 1.0)

    def test_report_calls_out_the_right_window(self):
        o, d = self._pair()
        report = format_windowed_diff_report(o, d)
        self.assertIn('WORST WINDOW', report)
        self.assertIn('16.0s', report)

    def test_whole_file_mean_dilutes_what_windowing_finds(self):
        """The motivating claim, asserted rather than assumed."""
        from sidm2.audio_listen import extract_features
        clean = np.concatenate([_tone(4.0) for _ in range(5)])
        broken = np.concatenate([_tone(4.0)] * 4 + [_tone(4.0) + _noise(4.0, amp=0.4)])
        whole_delta = abs(extract_features(broken, SR).flatness_mean
                          - extract_features(clean, SR).flatness_mean)
        o = extract_features_windowed(clean, SR, window_s=4.0)
        d = extract_features_windowed(broken, SR, window_s=4.0)
        local_delta = abs(d[4][1].flatness_mean - o[4][1].flatness_mean)
        self.assertGreater(local_delta, whole_delta * 2)


class TestUniformDifferenceIsNotLocalized(unittest.TestCase):
    """A whole-render offset must NOT be reported as a localized defect.

    format_feature_report() already shows a uniform shift; the entire value
    windowing adds is variation BETWEEN sections, which is why worst_window()
    subtracts the median delta before ranking.
    """

    def _uniform_pair(self):
        clean = np.concatenate([_tone(4.0) for _ in range(5)])
        quieter = clean * 0.5          # uniformly ~6 dB down, everywhere
        o = extract_features_windowed(clean, SR, window_s=4.0)
        d = extract_features_windowed(quieter, SR, window_s=4.0)
        return o, d

    def test_uniform_level_change_yields_no_outlier_at_all(self):
        o, d = self._uniform_pair()
        out = worst_window(o, d)
        if out is not None:
            self.assertFalse(out.is_outlier)

    def test_report_says_the_difference_is_not_localized(self):
        o, d = self._uniform_pair()
        report = format_windowed_diff_report(o, d)
        self.assertNotIn('WORST WINDOW', report)
        # A uniform offset leaves zero between-window deviation, so this lands in
        # the "uniform across windows" branch -- and the message says explicitly
        # that a whole-render offset is not a localized defect.
        self.assertIn('uniform across windows', report)
        self.assertIn('not a localized defect', report)

    def test_the_uniform_delta_is_nonetheless_real_and_visible_in_the_table(self):
        # It must not be hidden either -- the table still shows every window
        # about 6 dB down; only the OUTLIER CLAIM is withheld.
        o, d = self._uniform_pair()
        deltas = [d[i][1].rms_db_mean - o[i][1].rms_db_mean for i in range(len(o))]
        for dv in deltas:
            self.assertLess(dv, -5.0)


class TestDegenerateInputs(unittest.TestCase):
    def test_identical_renders_produce_no_outlier(self):
        x = np.concatenate([_tone(4.0) for _ in range(5)])
        w = extract_features_windowed(x, SR, window_s=4.0)
        self.assertIsNone(worst_window(w, w))

    def test_identical_renders_report_flat(self):
        x = np.concatenate([_tone(4.0) for _ in range(5)])
        w = extract_features_windowed(x, SR, window_s=4.0)
        self.assertIn('no section deviates', format_windowed_diff_report(w, w))

    def test_no_windows_on_either_side_is_reported_not_crashed(self):
        self.assertIn('No comparable windows', format_windowed_diff_report([], []))

    def test_mismatched_window_counts_are_flagged_and_truncated(self):
        short = extract_features_windowed(_tone(8.0), SR, window_s=4.0)
        long_ = extract_features_windowed(_tone(20.0), SR, window_s=4.0)
        report = format_windowed_diff_report(short, long_)
        self.assertIn('window counts differ', report)
        self.assertIn('Comparing the first 2', report)

    def test_worst_window_uses_only_the_overlap(self):
        short = extract_features_windowed(_tone(8.0), SR, window_s=4.0)
        long_ = extract_features_windowed(_tone(20.0), SR, window_s=4.0)
        out = worst_window(short, long_)
        if out is not None:
            self.assertLess(out.index, 2)

    def test_too_few_windows_withholds_the_outlier_verdict(self):
        # A spread estimated from 2 points cannot support an outlier claim.
        clean = np.concatenate([_tone(4.0), _tone(4.0)])
        broken = np.concatenate([_tone(4.0), _tone(4.0) + _noise(4.0, amp=0.4)])
        o = extract_features_windowed(clean, SR, window_s=4.0)
        d = extract_features_windowed(broken, SR, window_s=4.0)
        self.assertLess(len(o), MIN_WINDOWS_FOR_OUTLIER)
        report = format_windowed_diff_report(o, d)
        self.assertNotIn('>> WORST WINDOW', report)
        self.assertIn('NOT called an outlier', report)


class TestReportShape(unittest.TestCase):
    def test_report_contains_every_tracked_metric_column(self):
        x = np.concatenate([_tone(4.0) for _ in range(5)])
        w = extract_features_windowed(x, SR, window_s=4.0)
        report = format_windowed_diff_report(w, w)
        for label in ('RMS level', 'centroid', 'rolloff', 'flatness', 'silence'):
            self.assertIn(label, report)

    def test_report_has_one_row_per_window(self):
        x = np.concatenate([_tone(4.0) for _ in range(5)])
        w = extract_features_windowed(x, SR, window_s=4.0)
        report = format_windowed_diff_report(w, w)
        rows = [ln for ln in report.splitlines() if ln.rstrip().endswith('s')
                and 's' in ln[:10] and ln[:2] in ('  ', '> ')]
        self.assertGreaterEqual(len([ln for ln in report.splitlines()
                                     if ln[2:9].strip().endswith('s')
                                     and ln[2:9].strip()[0].isdigit()]), 5)

    def test_labels_appear_in_the_report(self):
        x = np.concatenate([_tone(4.0) for _ in range(5)])
        w = extract_features_windowed(x, SR, window_s=4.0)
        report = format_windowed_diff_report(w, w, orig_label='a.sid', driver_label='b.sf2')
        self.assertIn('driver MINUS original', report)


if __name__ == '__main__':
    unittest.main()
