#!/usr/bin/env python3
"""Unit tests for the voice-isolation (digi-bleed) guard and the register half
of pyscript/audio_tightness_tool.py's registers x audio cross-tab.

Synthetic arrays only -- no renderer, no siddump. See
sidm2/audio_tightness.py's module comment for the real measurements the
thresholds come from.

Usage:
    python -m pytest pyscript/test_voice_bleed_guard.py -v
"""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.audio_tightness import (
    BLEED_REFUSE_FRAC,
    BLEED_WARN_FRAC,
    analyze_voice_bleed,
    normalized_correlation,
    rms,
)


def _tone(freq, n=4410, sr=44100, amp=1.0, phase=0.0):
    t = np.arange(n) / sr
    return (amp * np.sin(2 * np.pi * freq * t + phase)).astype(np.float32)


class TestRms(unittest.TestCase):
    def test_empty_is_zero_not_nan(self):
        # np.mean of an empty array is nan with a RuntimeWarning; a bleed
        # verdict computed from nan silently compares False against every
        # threshold and would read as 'clean'.
        self.assertEqual(rms(np.array([], dtype=np.float32)), 0.0)

    def test_known_value(self):
        self.assertAlmostEqual(rms(np.array([3.0, 4.0])), np.sqrt(12.5), places=6)


class TestNormalizedCorrelation(unittest.TestCase):
    def test_identical_is_one(self):
        x = _tone(440)
        self.assertAlmostEqual(normalized_correlation(x, x), 1.0, places=6)

    def test_constant_side_is_nan_not_zero(self):
        # A constant signal has no defined correlation. Returning 0.0 would
        # claim "these are unrelated", which is a different (and unearned)
        # statement from "this cannot be computed".
        r = normalized_correlation(np.zeros(100, dtype=np.float32), _tone(440, 100))
        self.assertTrue(np.isnan(r))

    def test_dc_offset_does_not_create_correlation(self):
        # Both means are removed first: two unrelated signals sharing only a DC
        # offset must not read as correlated.
        a = _tone(440) + 5.0
        b = _tone(997) + 5.0
        self.assertLess(abs(normalized_correlation(a, b)), 0.2)


class TestVoiceBleedGuard(unittest.TestCase):
    def test_silence_when_muted_is_clean(self):
        iso = {1: _tone(440), 2: _tone(554), 3: _tone(659)}
        rep = analyze_voice_bleed(mix=_tone(440) + _tone(554) + _tone(659),
                                   muted=np.zeros(4410, dtype=np.float32),
                                   isolated=iso)
        self.assertEqual(rep.verdict, 'clean')
        self.assertFalse(rep.blocking)
        self.assertEqual([v.shared_frac for v in rep.voices], [0.0, 0.0, 0.0])

    def test_dominating_residual_refuses(self):
        # Residual amplitude equal to each slice -> 100% shared energy.
        resid = _tone(70, amp=1.0)
        iso = {v: resid.copy() for v in (1, 2, 3)}
        rep = analyze_voice_bleed(mix=resid * 3, muted=resid, isolated=iso)
        self.assertEqual(rep.verdict, 'refuse')
        self.assertTrue(rep.blocking)
        self.assertAlmostEqual(rep.max_shared_frac, 1.0, places=6)

    def test_warn_band_is_reported_but_not_blocking(self):
        # Both sides are sines, so the RMS ratio IS the amplitude ratio:
        # (0.2/1.0)**2 = 4% -> clean, (0.3/1.0)**2 = 9% -> warn. (First draft of
        # this test scaled the residual by sqrt(2) "to convert amplitude to
        # RMS" and put the clean case at 8%, inside the warn band -- the test
        # was wrong, not the code.) The band has to be non-blocking or the
        # guard would refuse every filtered tune.
        iso = {v: _tone(440 + 100 * v, amp=1.0) for v in (1, 2, 3)}
        clean = analyze_voice_bleed(_tone(440), _tone(70, amp=0.2), iso)
        warn = analyze_voice_bleed(_tone(440), _tone(70, amp=0.3), iso)
        self.assertEqual(clean.verdict, 'clean')
        self.assertEqual(warn.verdict, 'warn')
        self.assertFalse(warn.blocking)

    def test_thresholds_are_ordered(self):
        self.assertLess(BLEED_WARN_FRAC, BLEED_REFUSE_FRAC)

    def test_shared_frac_is_capped_at_one(self):
        # A residual louder than the slice would otherwise report >100% shared,
        # which is not a fraction of anything.
        iso = {1: _tone(440, amp=0.1)}
        rep = analyze_voice_bleed(_tone(440), _tone(70, amp=5.0), iso)
        self.assertEqual(rep.voices[0].shared_frac, 1.0)

    def test_total_silence_is_no_signal_not_clean(self):
        # THE POINT OF THIS TEST: a render where nothing happened must not
        # certify voice isolation as clean. 0/0 is "no evidence", the same rule
        # sidm2.fidelity_common.score_pct enforces for register scores. A
        # `verdict == 'clean'` here would let a silent build sail through the
        # guard and then be scored per-voice against another silent build.
        z = np.zeros(4410, dtype=np.float32)
        rep = analyze_voice_bleed(z, z, {1: z, 2: z, 3: z})
        self.assertEqual(rep.verdict, 'no-signal')
        self.assertTrue(rep.blocking)
        self.assertIsNone(rep.max_shared_frac)
        self.assertTrue(all(v.shared_frac is None for v in rep.voices))

    def test_silent_voice_with_live_residual_is_total_contamination(self):
        # A slice that is ONLY residual is 100% contaminated, not 'no evidence'
        # -- the residual itself is the evidence.
        z = np.zeros(4410, dtype=np.float32)
        resid = _tone(70)
        rep = analyze_voice_bleed(_tone(440), resid, {1: z, 2: _tone(440), 3: _tone(554)})
        self.assertEqual(rep.voices[0].shared_frac, 1.0)
        self.assertTrue(rep.blocking)

    def test_pair_correlation_separates_shared_from_independent(self):
        indep = analyze_voice_bleed(
            _tone(440), np.zeros(4410, dtype=np.float32),
            {1: _tone(440), 2: _tone(619), 3: _tone(877)})
        shared = _tone(70, amp=4.0)
        common = analyze_voice_bleed(
            _tone(440), shared,
            {1: shared + _tone(440), 2: shared + _tone(619), 3: shared + _tone(877)})
        self.assertLess(max(abs(v) for v in indep.pair_corr.values()), 0.3)
        self.assertGreater(min(common.pair_corr.values()), 0.8)


class TestPerVoiceRegisterAgreement(unittest.TestCase):
    """The register half of the cross-tab. Exercised through its guards only --
    the siddump-driven path needs real files and is covered by running the tool.
    """

    def test_empty_window_raises_rather_than_scoring(self):
        from sidm2.fidelity_common import per_voice_register_agreement
        # secs=0 -> n <= 0. The old shape of this bug across five scorers was
        # to return 100.0 for an empty window; this must refuse instead.
        with self.assertRaises(ValueError) as cm:
            per_voice_register_agreement(
                'SID/Hubbard_Rob/Commando.sid', 'SID/Hubbard_Rob/Commando.sid', 0)
        self.assertIn('empty register comparison window', str(cm.exception))


if __name__ == '__main__':
    unittest.main()
