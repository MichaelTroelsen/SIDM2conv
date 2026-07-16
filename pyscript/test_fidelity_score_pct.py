"""Tests for sidm2.fidelity_common.score_pct / fmt_pct.

Regression for the vacuous-100 bug class: every fidelity scorer in the project
carried a private `100.0 * ok / tot if tot else 100.0`, so a comparison with NO
DATA reported PERFECT AGREEMENT. Found by the 2026-07-16 fidelity audit in 10
files — and in two builders the fabricated 100.0 fed a real A/B decision, where
100.0 vs 100.0 compares equal and an unmeasured voice silently voted.

Same family as the v3.21.0 zig64 gate bug: an empty comparison is "no test ran",
never a pass.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.fidelity_common import score_pct, fmt_pct


class TestScorePct(unittest.TestCase):

    def test_empty_comparison_is_none_not_100(self):
        """THE regression. 0/0 must never be a perfect score."""
        self.assertIsNone(score_pct(0, 0),
                          "0/0 must be None ('no test ran'), never 100.0")

    def test_empty_comparison_is_not_zero_either(self):
        """No data is not a failure either — the inverted form of the bug
        (`max(1, tot)`) booked unmeasured voices as 0-correct-of-N."""
        self.assertIsNot(score_pct(0, 0), 0.0)
        self.assertNotEqual(score_pct(0, 0), 0.0)

    def test_real_percentages(self):
        self.assertEqual(score_pct(1, 1), 100.0)
        self.assertEqual(score_pct(0, 1), 0.0)
        self.assertEqual(score_pct(1, 2), 50.0)
        self.assertAlmostEqual(score_pct(996, 996), 100.0)

    def test_perfect_score_requires_evidence(self):
        """100.0 must be reachable ONLY from a non-empty comparison."""
        self.assertEqual(score_pct(5, 5), 100.0)   # real
        self.assertIsNone(score_pct(0, 0))         # vacuous

    def test_none_cannot_be_silently_compared(self):
        """The builders' A/B did `fl[v] > fg[v] + 1.0`. With the old 100.0 that
        silently compared equal; with None it must raise rather than decide."""
        a, b = score_pct(0, 0), score_pct(0, 0)
        with self.assertRaises(TypeError):
            _ = a > b + 1.0

    def test_fmt_pct_renders_none_as_na(self):
        self.assertIn("n/a", fmt_pct(None))
        self.assertNotIn("100", fmt_pct(None))
        self.assertIn("100.0", fmt_pct(100.0))

    def test_fmt_pct_width(self):
        self.assertEqual(len(fmt_pct(None, 6)), 6)
        self.assertEqual(len(fmt_pct(99.2, 6)), 6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
