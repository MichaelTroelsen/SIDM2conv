#!/usr/bin/env python3
"""Unit Tests for sidm2.audio_tightness

Tests the pure numpy onset-detection / alignment / attack-shape functions
against synthetic click-track fixtures -- no VICE/SID2WAV needed, runs in
the normal pytest suite.

Usage:
    python -m pytest pyscript/test_audio_tightness.py -v
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.audio_tightness import (
    align_onsets,
    analyze_tightness,
    attack_rise_time_ms,
    detect_onsets,
    logmel_distance,
    median_ioi_ms,
    offset_and_jitter,
    safe_tolerance_ms,
)

SR = 44100


def _make_click_track(sr, duration_s, click_times_s, kind='exp', amp=1.0, decay=0.02, seed=0):
    """Synthetic click track: decaying noise bursts (percussive) at each
    given time. kind='exp' = sharp exponential-decay onset (step-like
    attack); kind='ramp' = a linear fade-in before the same decay."""
    n = int(round(duration_s * sr))
    x = np.zeros(n)
    rng = np.random.RandomState(seed)
    burst_len = int(decay * sr)
    noise = rng.uniform(-1, 1, burst_len)
    decay_env = np.exp(-np.arange(burst_len) / (decay * sr / 5))

    for t in click_times_s:
        start = int(round(t * sr))
        env = decay_env.copy()
        if kind == 'ramp':
            ramp_len = max(1, burst_len // 4)
            env = env.copy()
            env[:ramp_len] *= np.linspace(0, 1, ramp_len)
        end = min(n, start + burst_len)
        x[start:end] += amp * env[:end - start] * noise[:end - start]
    return x


class TestOnsetDetection(unittest.TestCase):
    def test_single_click_onset_time_accuracy(self):
        x = _make_click_track(SR, 1.0, [0.3])
        onsets = detect_onsets(x, SR)
        self.assertEqual(len(onsets), 1)
        self.assertAlmostEqual(onsets[0], 0.3, delta=0.02)

    def test_steady_tone_produces_no_false_onsets(self):
        n = int(SR * 1.0)
        tone = 0.3 * np.sin(2 * np.pi * 440 * np.arange(n) / SR)
        onsets = detect_onsets(tone, SR)
        self.assertEqual(onsets, [])

    def test_multiple_clicks_all_detected(self):
        click_times = [0.2, 0.6, 1.0, 1.4]
        x = _make_click_track(SR, 2.0, click_times)
        onsets = detect_onsets(x, SR)
        self.assertEqual(len(onsets), len(click_times))
        for expected, actual in zip(click_times, onsets):
            self.assertAlmostEqual(expected, actual, delta=0.025)


class TestAlignment(unittest.TestCase):
    def test_identical_tracks_align_fully(self):
        onsets = [0.1, 0.5, 0.9]
        pairs, missing, extra = align_onsets(onsets, list(onsets), tolerance_s=0.15)
        self.assertEqual(len(pairs), 3)
        self.assertEqual(missing, [])
        self.assertEqual(extra, [])

    def test_missing_and_extra_land_in_right_bucket(self):
        orig = [0.1, 0.5, 0.9]
        driver = [0.1, 0.9, 1.3]
        pairs, missing, extra = align_onsets(orig, driver, tolerance_s=0.05)
        self.assertEqual([p[0] for p in pairs], [0.1, 0.9])
        self.assertEqual(missing, [0.5])
        self.assertEqual(extra, [1.3])

    def test_missing_not_misaligned_to_a_neighbor(self):
        # A dropped onset must NOT silently steal a distant, unrelated
        # driver onset just because it's the closest one outside tolerance.
        orig = [0.1, 0.5, 0.9]
        driver = [0.1, 0.9]
        pairs, missing, extra = align_onsets(orig, driver, tolerance_s=0.05)
        self.assertEqual(missing, [0.5])
        self.assertEqual([p[1] for p in pairs], [0.1, 0.9])


class TestToleranceBoundary(unittest.TestCase):
    def test_shifted_click_flagged_loose_or_not_at_threshold(self):
        click_times = [0.5]
        x = _make_click_track(SR, 1.5, click_times)

        # Just inside the loose threshold.
        y_tight = _make_click_track(SR, 1.5, [click_times[0] + 0.03])
        report_tight = analyze_tightness(x, y_tight, SR, onset_tolerance_ms=150,
                                          loose_threshold_ms=40)
        self.assertEqual(len(report_tight.matched), 1)
        self.assertFalse(report_tight.matched[0].loose)

        # Clearly past the loose threshold.
        y_loose = _make_click_track(SR, 1.5, [click_times[0] + 0.08])
        report_loose = analyze_tightness(x, y_loose, SR, onset_tolerance_ms=150,
                                          loose_threshold_ms=40)
        self.assertEqual(len(report_loose.matched), 1)
        self.assertTrue(report_loose.matched[0].loose)

    def test_onset_outside_tolerance_window_is_missing_not_matched(self):
        x = _make_click_track(SR, 1.5, [0.5])
        y = _make_click_track(SR, 1.5, [0.5 + 0.2])
        report = analyze_tightness(x, y, SR, onset_tolerance_ms=150, loose_threshold_ms=40)
        self.assertEqual(report.matched, [])
        self.assertEqual(len(report.missing), 1)
        self.assertEqual(len(report.extra), 1)


class TestAttackRiseTime(unittest.TestCase):
    def test_ramp_onset_has_longer_rise_than_step_onset(self):
        n = int(SR * 0.5)
        onset_sample = 100
        onset_t = onset_sample / SR

        x_step = np.zeros(n)
        x_step[onset_sample:] = np.sin(2 * np.pi * 440 * np.arange(n - onset_sample) / SR)

        ramp_len = int(0.03 * SR)
        x_ramp = np.zeros(n)
        env = np.linspace(0, 1, ramp_len)
        x_ramp[onset_sample:onset_sample + ramp_len] = (
            env * np.sin(2 * np.pi * 440 * np.arange(ramp_len) / SR)
        )
        x_ramp[onset_sample + ramp_len:] = np.sin(
            2 * np.pi * 440 * np.arange(n - onset_sample - ramp_len) / SR
        )

        rise_step = attack_rise_time_ms(x_step, SR, onset_t)
        rise_ramp = attack_rise_time_ms(x_ramp, SR, onset_t)
        self.assertGreater(rise_ramp, rise_step)

    def test_silence_returns_zero_rise_time(self):
        x = np.zeros(int(SR * 0.2))
        self.assertEqual(attack_rise_time_ms(x, SR, 0.05), 0.0)


class TestLogmelDistance(unittest.TestCase):
    def test_identical_segments_have_zero_distance(self):
        n = 2000
        seg = np.sin(2 * np.pi * 440 * np.arange(n) / SR)
        self.assertAlmostEqual(logmel_distance(seg, seg, SR), 0.0, places=9)

    def test_different_timbres_have_nonzero_distance(self):
        n = 2000
        seg_a = np.sin(2 * np.pi * 440 * np.arange(n) / SR)
        seg_b = np.sin(2 * np.pi * 2000 * np.arange(n) / SR)
        self.assertGreater(logmel_distance(seg_a, seg_b, SR), 0.0)


class TestSummaryStats(unittest.TestCase):
    def test_hand_computed_summary_matches(self):
        orig_times = [0.2, 0.6, 1.0]
        x = _make_click_track(SR, 1.5, orig_times)
        driver_times = [0.2, 0.61, 1.3]  # 0.6->0.61 (10ms, tight), 1.0 missing, 1.3 extra
        y = _make_click_track(SR, 1.5, driver_times)

        report = analyze_tightness(x, y, SR, onset_tolerance_ms=150, loose_threshold_ms=40)

        self.assertEqual(len(report.orig_onsets), 3)
        self.assertEqual(len(report.driver_onsets), 3)
        self.assertEqual(len(report.matched), 2)
        self.assertEqual(len(report.missing), 1)
        self.assertEqual(len(report.extra), 1)

        deltas = sorted(abs(m.delta_ms) for m in report.matched)
        self.assertAlmostEqual(deltas[0], 0.0, delta=5.0)
        self.assertAlmostEqual(deltas[1], 10.0, delta=5.0)
        self.assertTrue(all(not m.loose for m in report.matched))


class TestOffsetJitterSeparation(unittest.TestCase):
    """A uniform shift and genuine looseness are different defects; the
    analysis must not report the former as the latter."""

    def test_uniform_shift_is_offset_not_jitter(self):
        times = [0.2, 0.6, 1.0, 1.4]
        shift = 0.05  # every onset 50ms late, but perfectly regular
        x = _make_click_track(SR, 2.0, times)
        y = _make_click_track(SR, 2.0, [t + shift for t in times])

        report = analyze_tightness(x, y, SR, onset_tolerance_ms=150,
                                    loose_threshold_ms=40)

        self.assertEqual(len(report.matched), len(times))
        # Raw deltas all ~+50ms -> every onset would read as "loose"...
        self.assertTrue(all(m.loose for m in report.matched))
        # ...but that is entirely the offset; nothing is actually loose.
        self.assertAlmostEqual(report.median_offset_ms, 50.0, delta=12.0)
        self.assertFalse(any(m.loose_jitter for m in report.matched))
        for m in report.matched:
            self.assertLess(abs(m.jitter_ms), 40.0)

    def test_genuine_looseness_shows_as_jitter(self):
        times = [0.2, 0.6, 1.0, 1.4]
        # No systematic shift, but one onset is badly late.
        driver = [0.2, 0.6, 1.0, 1.49]
        x = _make_click_track(SR, 2.0, times)
        y = _make_click_track(SR, 2.0, driver)

        report = analyze_tightness(x, y, SR, onset_tolerance_ms=150,
                                    loose_threshold_ms=40)

        self.assertAlmostEqual(report.median_offset_ms, 0.0, delta=12.0)
        self.assertEqual(sum(1 for m in report.matched if m.loose_jitter), 1)

    def test_offset_and_jitter_helper_matches_report_fields(self):
        times = [0.2, 0.6, 1.0]
        x = _make_click_track(SR, 1.5, times)
        y = _make_click_track(SR, 1.5, [t + 0.03 for t in times])
        report = analyze_tightness(x, y, SR)

        offset, jitters = offset_and_jitter(report.matched)
        self.assertAlmostEqual(offset, report.median_offset_ms, places=6)
        for m, j in zip(report.matched, jitters):
            self.assertAlmostEqual(m.jitter_ms, j, places=6)

    def test_offset_and_jitter_empty(self):
        self.assertEqual(offset_and_jitter([]), (0.0, []))


class TestToleranceMustNotExceedNoteSpacing(unittest.TestCase):
    """Regression guard for the E3 finding.

    Glyptodont (median IOI ~90ms) compared against its Blackbird native
    build reported a "+50ms (+2.5 PAL frame) systematic offset" under the
    old fixed 150ms tolerance. Sweeping the tolerance down collapsed that
    offset monotonically to exactly 0.0 at <=70ms: the offset was never
    real, it was greedy matching pairing each onset with its NEIGHBOUR
    because the window was wider than the gap between notes. Such a
    mispairing preserves time order, so count_alignment_crossings() cannot
    detect it -- only keeping the window below the IOI prevents it.
    """

    def test_median_ioi(self):
        self.assertAlmostEqual(median_ioi_ms([0.0, 0.1, 0.2, 0.3]), 100.0, delta=1e-6)
        self.assertEqual(median_ioi_ms([0.5]), 0.0)
        self.assertEqual(median_ioi_ms([]), 0.0)

    def test_safe_tolerance_is_half_the_ioi(self):
        self.assertAlmostEqual(safe_tolerance_ms([0.0, 0.1, 0.2, 0.3]), 50.0, delta=1e-6)

    def test_safe_tolerance_clamped(self):
        # Very dense material must not go below the detector's resolution...
        self.assertGreaterEqual(safe_tolerance_ms([i * 0.005 for i in range(10)]), 20.0)
        # ...and very sparse material must not get an unbounded window.
        self.assertLessEqual(safe_tolerance_ms([0.0, 5.0, 10.0]), 150.0)

    def test_wide_tolerance_fabricates_an_offset(self):
        """The bug itself: identical timing, but a tolerance wider than the
        note spacing pairs each driver onset with the WRONG neighbour."""
        ioi = 0.09                       # 90ms spacing, as in Glyptodont
        times = [0.2 + i * ioi for i in range(12)]
        x = _make_click_track(SR, 2.0, times)
        y = _make_click_track(SR, 2.0, times)   # identical -> truth is 0 offset

        tight = analyze_tightness(x, y, SR, onset_tolerance_ms=40)
        self.assertAlmostEqual(tight.median_offset_ms, 0.0, delta=12.0)

        # The auto default must land below the IOI and stay correct.
        auto = analyze_tightness(x, y, SR)
        self.assertLess(auto.params['onset_tolerance_ms'], ioi * 1000)
        self.assertAlmostEqual(auto.median_offset_ms, 0.0, delta=12.0)
        self.assertEqual(auto.params['tolerance_source'], 'auto (from median IOI)')

    def test_auto_tolerance_recorded_in_params(self):
        times = [0.2 + i * 0.09 for i in range(10)]
        x = _make_click_track(SR, 1.6, times)
        rep = analyze_tightness(x, x, SR)
        self.assertGreater(rep.median_ioi_ms, 0.0)
        self.assertLess(rep.params['onset_tolerance_ms'], rep.median_ioi_ms)

    def test_explicit_tolerance_is_respected_and_labelled(self):
        times = [0.2, 0.6, 1.0]
        x = _make_click_track(SR, 1.5, times)
        rep = analyze_tightness(x, x, SR, onset_tolerance_ms=77)
        self.assertEqual(rep.params['onset_tolerance_ms'], 77)
        self.assertEqual(rep.params['tolerance_source'], 'explicit')


if __name__ == '__main__':
    unittest.main()
