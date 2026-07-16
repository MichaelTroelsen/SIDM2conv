"""Tests for sidm2.deenen_parser.DeenenGrammar.

Locks the 2026-07-16 finding: the Deenen replay is NOT one orderlist grammar.
Each rip carries its class boundaries as immediates in its own fetch routine,
and they differ. Every constant asserted here was read off the real
disassembly, not inferred from decoded output.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.deenen_parser import load_sid, DeenenGrammar

CORPUS = Path(__file__).parent.parent / "SID" / "deenen"


class TestDeenenGrammar(unittest.TestCase):

    def _g(self, name):
        p = CORPUS / f"{name}.sid"
        if not p.exists():
            self.skipTest(f"missing {p}")
        d, la, h = load_sid(str(p))
        return DeenenGrammar(d, la)

    def test_ding_is_the_seg_advance_class(self):
        """Ding_van_Charles $12A6: CMP #$5F / BCC -> pattern; $FF -> LDA $106c,X
        / CMP #$1a / ADC #$1b (segment advance). These are the constants
        decode_voice currently hardcodes, so the reader must agree with them."""
        g = self._g("Ding_van_Charles")
        self.assertTrue(g.read_ok)
        self.assertEqual(g.fetch, 0x12A6)
        self.assertEqual(g.pat_thr, 0x5F)
        self.assertEqual(g.ff_mode, "seg")

    def test_constant_runner_is_a_different_grammar(self):
        """Constant_Runner $13F3: CMP #$40 / BCC -> pattern, and $FF is
        LDA #$00 / STA $d7,X = RESTART TO INDEX 0, not segment-advance.

        This is why the Ding-class decoder ran away to 500 notes on a voice
        that really has 44: it read $43/$4E as pattern indices (their pointers
        land at $D1B9/$40C9, outside the file) and had no model for $FF.
        """
        g = self._g("Constant_Runner")
        self.assertTrue(g.read_ok)
        self.assertEqual(g.fetch, 0x13F3)
        self.assertEqual(g.pat_thr, 0x40, "pattern threshold is $40, not $5F")
        self.assertEqual(g.ff_mode, "restart")

    def test_the_grammar_really_varies_across_the_corpus(self):
        """The headline. If these ever collapse to one value, the reader broke."""
        seen = {}
        for n in ("Ding_van_Charles", "Constant_Runner", "After_the_War",
                  "Soldier_of_Light"):
            g = self._g(n)
            seen[n] = (g.pat_thr, g.ff_mode)
        self.assertEqual(seen["Ding_van_Charles"][0], 0x5F)
        self.assertEqual(seen["Constant_Runner"][0], 0x40)
        self.assertEqual(seen["After_the_War"][0], 0x6F)
        self.assertEqual(seen["Soldier_of_Light"][0], 0x50)
        self.assertGreater(len({v[0] for v in seen.values()}), 1,
                           "pattern threshold must NOT be one global constant")
        self.assertGreater(len({v[1] for v in seen.values()}), 1,
                           "$FF semantics must NOT be one global constant")

    def test_43_and_4e_are_not_pattern_indices(self):
        """Constant_Runner's orderlist contains $43/$4E. Under the Ding
        threshold ($5F) they are patterns; their pointers are out of file.
        Under the real threshold ($40) they are loop counts. Proves the bug
        rather than restating the grammar."""
        p = CORPUS / "Constant_Runner.sid"
        if not p.exists():
            self.skipTest("missing corpus file")
        d, la, h = load_sid(str(p))
        g = DeenenGrammar(d, la)
        end = la + len(d)
        pat_tbl = 0x136D
        for b in (0x43, 0x4E):
            self.assertLess(b, 0x5F, "would be a pattern under Ding's grammar")
            self.assertGreaterEqual(b, g.pat_thr,
                                    "is NOT a pattern under the real grammar")
            o = pat_tbl - la + b * 2
            ptr = d[o] | (d[o + 1] << 8)
            self.assertFalse(la <= ptr < end,
                             f"pat[${b:02X}]=${ptr:04X} should be out of file")

    def test_unreadable_file_reports_not_ok_rather_than_guessing(self):
        """A file whose fetch site isn't found must say so, not return a
        plausible default (the burden-of-proof rule)."""
        g = DeenenGrammar(bytearray(64), 0x1000)
        self.assertFalse(g.read_ok)
        self.assertIsNone(g.pat_thr)
        self.assertIsNone(g.fetch)


if __name__ == "__main__":
    unittest.main(verbosity=2)
