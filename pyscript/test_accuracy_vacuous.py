#!/usr/bin/env python3
"""Regression tests for the three scoring defects fixed in sidm2/accuracy.py.

Each test pins one defect that produced a *wrong number* on the user-facing
validator, so none of them can silently come back:

1. Sparse-register desync -- voice comparison paired the two sides by list
   position, where the lists only contained frames on which freq_lo and freq_hi
   were co-written. A lo-only write contributed nothing and one extra dual-write
   shifted every later comparison.
2. Fabricated zeros -- held filter registers defaulted to 0, inventing a cutoff
   the hardware never held.
3. Vacuous zero -- a player that never touches the filter left filter_accuracy
   at its 0.0 initialiser, which was then weighted 10% into overall_accuracy.
   A faithful file was docked ten points for not using a filter.

These are all instances of the rule score_pct() exists to enforce: an empty
comparison is "no test ran", never a score.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.accuracy import SIDComparator, SIDRegisterCapture


def capture(frames):
    """A SIDRegisterCapture over hand-written sparse {reg: value} frames."""
    c = SIDRegisterCapture()
    c.frames = list(frames)
    return c


def compare(a, b):
    return SIDComparator(capture(a), capture(b)).compare()


class TestNoFilterIsNotAPenalty(unittest.TestCase):
    """Defect 3: the ten-point tax on correctly not using a filter."""

    # Two identical captures that touch voice 1 only and never the filter --
    # the shape of every Rob Hubbard tune (docs/players/HUBBARD.md: "Hubbard
    # never writes cutoff").
    FRAMES = [{0x00: 0x10, 0x01: 0x20, 0x04: 0x41}] * 8

    def test_filter_is_n_a_not_zero(self):
        r = compare(self.FRAMES, self.FRAMES)
        self.assertIsNone(r['filter_accuracy'],
                          "a file that never filters must report no evidence, not 0%")

    def test_identical_captures_score_100_not_90(self):
        r = compare(self.FRAMES, self.FRAMES)
        self.assertAlmostEqual(r['overall_accuracy'], 100.0, places=6,
                               msg="unmeasured filter must be dropped from the "
                                   "weighted mean, not folded in as a zero")

    def test_filter_still_scored_when_present(self):
        """The fix must not make the filter unscoreable -- only unpenalised."""
        a = [{0x15: 0x10, 0x16: 0x02}] * 4
        b = [{0x15: 0x99, 0x16: 0x02}] * 4
        self.assertIsNotNone(compare(a, b)['filter_accuracy'])
        self.assertLess(compare(a, b)['filter_accuracy'], 100.0)


class TestHeldRegistersCarryForward(unittest.TestCase):
    """Defects 1 and 2: absence means held, not zero."""

    def test_lo_only_write_is_not_dropped(self):
        """A voice writing freq_lo alone (fine vibrato/slide) must be compared.

        The old extractor required BOTH bytes on the same frame, so these two
        captures -- which differ audibly on frames 1..3 -- compared as equal.
        """
        a = [{0x00: 0x10, 0x01: 0x20}, {0x00: 0x11}, {0x00: 0x12}, {0x00: 0x13}]
        b = [{0x00: 0x10, 0x01: 0x20}, {0x00: 0x99}, {0x00: 0x98}, {0x00: 0x97}]
        freq = compare(a, b)['voice_accuracy']['voice1']['frequency']
        self.assertIsNotNone(freq)
        self.assertLess(freq, 100.0, "lo-only writes were dropped from the comparison")

    def test_held_filter_register_is_not_zeroed(self):
        """Writing only $D416 must not fabricate a cutoff-lo of 0.

        Both sides hold $D415 = 0x7F from frame 0 and then write $D416 alone.
        Under the old `frame.get(0x15, 0)` the later frames read cutoff-lo 0 on
        both sides -- equal, but equal to a value neither side ever held.
        """
        frames = [{0x15: 0x7F, 0x16: 0x01}, {0x16: 0x02}, {0x16: 0x03}]
        tl = SIDComparator._timeline(capture(frames), (0x15, 0x16), 3)
        self.assertEqual([t[0] for t in tl], [0x7F, 0x7F, 0x7F],
                         "held $D415 must carry forward, not reset to 0")

    def test_an_extra_early_write_does_not_shift_everything_after(self):
        """A redundant re-write must not desynchronise the comparison.

        NOTE: unlike its siblings this is a forward guard, not a defect pin --
        the pre-fix code also returns 100% on this input, because a 4-frame
        fixture is too short for the position-pairing drift to bite. It is kept
        so the frame-aligned implementation cannot regress INTO a desync; the
        old desync itself is pinned by test_lo_only_write_is_not_dropped.
        """
        a = [{0x00: 0x10, 0x01: 0x20}, {0x00: 0x30}, {0x00: 0x40}, {0x00: 0x50}]
        b = [{0x00: 0x10, 0x01: 0x20}, {0x00: 0x30, 0x01: 0x20}, {0x00: 0x40},
             {0x00: 0x50}]
        freq = compare(a, b)['voice_accuracy']['voice1']['frequency']
        self.assertEqual(freq, 100.0,
                         "a redundant re-write must not desynchronise the comparison")


class TestConstantSeriesIsNotEvidence(unittest.TestCase):
    """The vacuous-100 that survived the first fix.

    Dropping frames where BOTH sides are None is not enough on its own: siddump
    force-displays every register on its FIRST row whether or not the
    playroutine wrote it, so a tune that never touches the filter still yields a
    full-length, entirely non-None series of zeroes on both sides. Those frames
    are not None, so they pass the None check and score a confident 100%.

    Measured before `exercised()` was wired in: validating Commando (Hubbard,
    who never writes a cutoff) against itself printed
    `Filter Accuracy: 100.00%`.
    """

    def test_both_sides_constant_at_the_same_value_is_n_a(self):
        frames = [{0x15: 0, 0x16: 0, 0x17: 0, 0x18: 0}] + [{0x00: 0x10}] * 6
        self.assertIsNone(compare(frames, frames)['filter_accuracy'])

    def test_both_sides_constant_at_DIFFERENT_values_still_scores(self):
        """A permanently wrong register is a real total disagreement, not n/a."""
        a = [{0x18: 0x3F}] + [{0x00: 0x10}] * 6
        b = [{0x18: 0x1F}] + [{0x00: 0x10}] * 6
        score = compare(a, b)['filter_accuracy']
        self.assertIsNotNone(score, "a constant WRONG value must not vanish into n/a")
        self.assertEqual(score, 0.0)

    def test_a_moving_register_is_still_scored(self):
        a = [{0x15: 0x10}, {0x15: 0x20}, {0x15: 0x30}]
        b = [{0x15: 0x10}, {0x15: 0x20}, {0x15: 0x99}]
        score = compare(a, b)['filter_accuracy']
        self.assertIsNotNone(score)
        self.assertLess(score, 100.0)


class TestRegisterAccuracyComparesHeldValues(unittest.TestCase):
    """register_accuracy used to pair the i-th WRITE against the i-th write.

    Two bugs in one: a positional desync (one extra write shifts every later
    pair) and the wrong question -- what the SID plays is the value a register
    HOLDS each frame, and how many times that value was written is inaudible.
    """

    def test_redundant_rewrites_score_100(self):
        """Identical held timelines; `b` merely restates each value. Audibly equal.

        Both sides hold 41, 41, 11, 11. `a` writes twice, `b` four times. Under
        write-pairing that compared a[1]=0x11 against b[1]=0x41 and scored
        1 match over a denominator of 4 -- 25% for two identical-sounding
        drivers. The honest answer is 100%.

        (The value has to MOVE for this to be a test at all: a register both
        sides hold at one constant is reported n/a by `exercised`, which is a
        separate and deliberate behaviour covered above.)
        """
        a = [{0x04: 0x41}, {}, {0x04: 0x11}, {}]
        b = [{0x04: 0x41}, {0x04: 0x41}, {0x04: 0x11}, {0x04: 0x11}]
        acc = compare(a, b)['register_accuracy']['Voice1_Control']
        self.assertEqual(acc, 100.0)

    def test_a_genuinely_different_held_value_is_still_caught(self):
        """The fix must not make disagreement invisible."""
        a = [{0x04: 0x41}, {}, {}, {}]
        b = [{0x04: 0x41}, {0x04: 0x11}, {}, {}]
        acc = compare(a, b)['register_accuracy']['Voice1_Control']
        self.assertIsNotNone(acc)
        self.assertLess(acc, 100.0)

    def test_a_register_neither_side_uses_is_absent(self):
        """Not 0%, not 100% -- absent, so it cannot drag the average either way."""
        frames = [{0x04: 0x41}] * 4
        self.assertNotIn('Voice3_Control', compare(frames, frames)['register_accuracy'])


class TestEmptyComparison(unittest.TestCase):
    def test_zero_frames_reports_no_evidence(self):
        r = compare([], [])
        self.assertIsNone(r['overall_accuracy'])
        self.assertIsNone(r['frame_accuracy'])

    def test_a_dimension_neither_side_wrote_is_dropped(self):
        """Voice 3 is silent on both sides: n/a, not 0% and not 100%."""
        frames = [{0x00: 0x10, 0x01: 0x20}] * 4
        r = compare(frames, frames)
        self.assertIsNone(r['voice_accuracy']['voice3']['frequency'])


if __name__ == '__main__':
    unittest.main()
