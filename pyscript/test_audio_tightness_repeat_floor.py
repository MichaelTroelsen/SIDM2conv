#!/usr/bin/env python3
"""Repeatability-floor tests for audio_tightness_tool.

The defect these pin: `diagnose()` had no inconclusive outcome, so any voice
whose registers agreed and whose audio did not was called SYNTHESIS. On
Cybernoid_II that produced a confident wrong answer -- the registers really
are identical (6 differing siddump lines in 350 frames, all frames 0-2), and
the audio gap was not a synthesis defect.

Two things account for it, measured rather than assumed:

  * METRIC NOISE. Three renders of the SAME file with the SAME arguments
    (--delay=0 pinned) are the same signal to within r = 1.0000 and
    rms(diff)/rms ~ 0.001. On the full mix the detector is unmoved: 38/38
    onsets, 100% across all six pairings. On a VOICE-ISOLATED render that
    inaudible dither moves the onset count 101/88/98 and the pairwise match
    rate across 84.2-96.9%, because muting two voices leaves a large
    population of onsets sitting on the detector threshold.
  * PHASE. Perturbing the power-on delay moves it further, and phase is what
    actually differs between an original and a driver build, whose init code
    reaches the first play call differently.

Both bands cover the 71-85% the cross-tab was calling SYNTHESIS.

PATTERNS.md F5 says a comparison tool owes you f(x, x) = perfect. Comparing a
WAV against the same WAV satisfies that trivially and proves nothing. The
floor is the missing half: re-render, then compare.

diagnose(), floor_of() and repeat_floor_delays() are pure, so these run
without a renderer.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from pyscript.audio_tightness_tool import (
    PAL_CYCLES_PER_FRAME,
    REPEAT_FLOOR_SAMPLES,
    diagnose,
    effective_floor,
    floor_of,
    repeat_floor_delays,
)

REG_OK = {'freq': 100.0, 'wf': 100.0, 'pul': 100.0}
REG_BAD = {'freq': 40.0, 'wf': 100.0, 'pul': 100.0}


def stats(match_rate, jitter_p50_ms=1.0):
    return {'match_rate': match_rate, 'jitter_p50_ms': jitter_p50_ms}


def call(reg, st, floor=None, n=9, worst='phase'):
    # A floor is the minimum over N self-comparisons; the tests state the floor
    # they mean and this pads it out to N values at or above it, putting the
    # worst one in whichever bucket the test is about.
    if floor is None:
        samples = None
    elif worst == 'phase':
        samples = {'replicate': [1.0],
                   'phase': [floor] + [floor + 0.01] * (n - 2)}
    else:
        samples = {'replicate': [floor],
                   'phase': [floor + 0.01] * (n - 1)}
    return diagnose(reg, st, reg_match_pct=95.0, audio_match_rate=0.9,
                    loose_threshold_ms=40, floor_samples=samples)


class TestRepeatFloorDelays(unittest.TestCase):
    def test_first_delay_is_a_plain_replicate(self):
        # Without a delay-0 sample the floor cannot see the metric's own
        # instability, which on isolated voices is the larger of the two terms.
        for n in (1, 2, 3, 9):
            self.assertEqual(repeat_floor_delays(n)[0], 0)

    def test_delays_are_inside_one_frame(self):
        for n in (1, 2, 3, 5, 10):
            delays = repeat_floor_delays(n)
            self.assertEqual(len(delays), n)
            self.assertTrue(all(0 <= d < PAL_CYCLES_PER_FRAME for d in delays), delays)

    def test_zero_samples_is_empty_not_a_bare_replicate(self):
        self.assertEqual(repeat_floor_delays(0), [])

    def test_delays_are_distinct_and_ordered(self):
        delays = repeat_floor_delays(REPEAT_FLOOR_SAMPLES)
        self.assertEqual(delays, sorted(delays))
        self.assertEqual(len(set(delays)), len(delays))

    def test_delays_are_deterministic(self):
        # Two runs of the tool must calibrate against the same perturbations,
        # or one run's floor cannot be compared with another's.
        self.assertEqual(repeat_floor_delays(4), repeat_floor_delays(4))

    def test_default_keeps_the_rank_test_false_positive_rate_at_or_under_10pct(self):
        # "worse than all N samples" is a rank test over N+1 exchangeable
        # values: p = 1/(N+1). At the old default of 3 that was 25%, which is
        # not a rate at which to print a confident SYNTHESIS.
        self.assertLessEqual(1 / (REPEAT_FLOOR_SAMPLES + 1), 0.10)


class TestDiagnoseWithdrawsSynthesisInsideTheFloor(unittest.TestCase):
    """The Cybernoid_II case: registers exact, audio 76%, self-floor 78%."""

    def test_inside_the_floor_is_inconclusive_not_synthesis(self):
        verdict, why = call(REG_OK, stats(0.78), floor=0.78)
        self.assertEqual(verdict, 'INCONCLUSIVE')
        self.assertIn('phase', why)

    def test_above_the_floor_is_inconclusive(self):
        verdict, _ = call(REG_OK, stats(0.85), floor=0.78)
        self.assertEqual(verdict, 'INCONCLUSIVE')

    def test_below_the_floor_still_reports_synthesis(self):
        # Worse than phase alone ever manages on this file -- the diagnosis
        # survives calibration, and that is the whole point of measuring it.
        verdict, why = call(REG_OK, stats(0.40), floor=0.78)
        self.assertEqual(verdict, 'SYNTHESIS')
        self.assertIn('below all 9 self-comparisons', why)
        self.assertIn('p=0.10', why)

    def test_the_pre_fix_behaviour_is_what_the_floor_overturns(self):
        # Same inputs, floor withheld: this is exactly the verdict the tool
        # used to print unconditionally.
        self.assertEqual(call(REG_OK, stats(0.78), floor=None)[0], 'SYNTHESIS')
        self.assertEqual(call(REG_OK, stats(0.78), floor=0.78)[0], 'INCONCLUSIVE')

    def test_uncalibrated_synthesis_says_so(self):
        _, why = call(REG_OK, stats(0.78), floor=None)
        self.assertIn('NOT measured', why)

    def test_an_empty_sample_set_is_uncalibrated_not_a_zero_floor(self):
        # min([]) would raise; treating it as floor 0.0 would call every voice
        # INCONCLUSIVE. Neither -- it means the calibration did not happen.
        for empty in ({}, {'replicate': [], 'phase': []}):
            self.assertIsNone(floor_of(empty))
            verdict, why = diagnose(REG_OK, stats(0.78), 95.0, 0.9, 40,
                                    floor_samples=empty)
            self.assertEqual(verdict, 'SYNTHESIS')
            self.assertIn('NOT measured', why)

    def test_the_floor_is_the_minimum_not_the_mean(self):
        # A driver at 0.50 is inside a band whose worst sample is 0.45, even
        # though the mean sample is 0.80. Averaging would call this SYNTHESIS.
        verdict, _ = diagnose(REG_OK, stats(0.50), 95.0, 0.9, 40,
                              floor_samples={'replicate': [0.95],
                                             'phase': [0.45, 0.95, 0.85]})
        self.assertEqual(verdict, 'INCONCLUSIVE')

    def test_the_floor_spans_both_replicate_and_phase_samples(self):
        # The measured case: on an isolated voice a PLAIN re-render already
        # scores 84%, so a 71% driver must not be called SYNTHESIS just because
        # every phase sample happened to land higher.
        self.assertEqual(floor_of({'replicate': [0.84], 'phase': [0.95, 0.90]}), 0.84)
        verdict, why = diagnose(REG_OK, stats(0.86), 95.0, 0.9, 40,
                                floor_samples={'replicate': [0.84],
                                               'phase': [0.95, 0.90]})
        self.assertEqual(verdict, 'INCONCLUSIVE')
        self.assertIn('plain re-render', why)

    def test_the_explanation_names_which_half_set_the_floor(self):
        _, why = call(REG_OK, stats(0.80), floor=0.78, worst='replicate')
        self.assertIn('plain re-render', why)
        _, why = call(REG_OK, stats(0.80), floor=0.78, worst='phase')
        self.assertIn('phase-shifted re-render', why)

    def test_a_clean_voice_is_unaffected_by_the_floor(self):
        for floor in (None, 0.78, 0.99):
            self.assertEqual(call(REG_OK, stats(0.98), floor=floor)[0], 'ok')


class TestFloorDoesNotLeakIntoOtherQuadrants(unittest.TestCase):
    def test_sequencer_verdict_ignores_the_floor(self):
        # Registers disagree, so phase is not the question -- the note data is.
        self.assertEqual(call(REG_BAD, stats(0.40), floor=0.78)[0], 'SEQUENCER')

    def test_metric_verdict_ignores_the_floor(self):
        self.assertEqual(call(REG_BAD, stats(0.98), floor=0.78)[0], 'METRIC')

    def test_unexercised_registers_stay_na(self):
        self.assertEqual(call({}, stats(0.40), floor=0.78)[0], 'n/a')

    def test_no_onsets_stays_na(self):
        # None, not 0.0: a voice with nothing to match is not a failed match.
        self.assertEqual(call(REG_OK, stats(None), floor=0.78)[0], 'n/a')

    def test_jitter_alone_can_still_fail_a_high_match_rate(self):
        # match_rate above the floor but the matched onsets are far apart:
        # audio_ok is False, and the floor withholds SYNTHESIS all the same,
        # because the floor was measured on match_rate.
        verdict, _ = call(REG_OK, stats(0.99, jitter_p50_ms=200.0), floor=0.78)
        self.assertEqual(verdict, 'INCONCLUSIVE')


if __name__ == '__main__':
    unittest.main()


class TestTheFloorIsWidenedByMeasuredNoise(unittest.TestCase):
    """Cybernoid_II voice 3 read 85% vs a 77% floor, then 70% vs 71% -- the
    verdict flipped between two runs of the identical command. A raw floor is a
    minimum over point estimates that are themselves noisy; the replicate term
    is how much that noise is worth on this voice."""

    def test_margin_is_the_replicate_shortfall(self):
        eff, margin = effective_floor({'replicate': [0.93], 'phase': [0.71]})
        self.assertAlmostEqual(margin, 0.07)
        self.assertAlmostEqual(eff, 0.64)

    def test_a_perfect_replicate_leaves_the_floor_alone(self):
        eff, margin = effective_floor({'replicate': [1.0], 'phase': [0.71]})
        self.assertEqual(margin, 0.0)
        self.assertAlmostEqual(eff, 0.71)

    def test_the_flip_case_is_now_inconclusive_on_both_runs(self):
        # run A: audio 85%, floor 77%, replicate 93%
        a = diagnose(REG_OK, stats(0.85), 95.0, 0.9, 40,
                     floor_samples={'replicate': [0.93], 'phase': [0.77]})
        # run B: audio 70%, floor 71%, replicate 93% -- one point under, which
        # the un-widened floor called SYNTHESIS.
        b = diagnose(REG_OK, stats(0.70), 95.0, 0.9, 40,
                     floor_samples={'replicate': [0.93], 'phase': [0.71]})
        self.assertEqual(a[0], 'INCONCLUSIVE')
        self.assertEqual(b[0], 'INCONCLUSIVE')

    def test_a_real_defect_still_clears_the_widened_floor(self):
        verdict, why = diagnose(REG_OK, stats(0.30), 95.0, 0.9, 40,
                                floor_samples={'replicate': [0.93], 'phase': [0.71]})
        self.assertEqual(verdict, 'SYNTHESIS')
        self.assertIn('noise margin', why)

    def test_the_margin_can_never_push_the_floor_below_zero(self):
        eff, _ = effective_floor({'replicate': [0.0], 'phase': [0.10]})
        self.assertEqual(eff, 0.0)

    def test_widening_only_ever_declines_to_claim_a_defect(self):
        # The direction matters: this can miss a real defect, it can never
        # invent one. Anything the widened floor calls SYNTHESIS, the raw floor
        # called SYNTHESIS too.
        samples = {'replicate': [0.90], 'phase': [0.70, 0.80]}
        eff, _ = effective_floor(samples)
        self.assertLessEqual(eff, floor_of(samples))
