"""Tests for the variant-D track loop guard in sidm2.sdi_parser.

Locks the 2026-08-20 finding: a D track ends in $ff (loop), not $fe -- all
18 D-variant files in SID/Gallefoss_Glenn end that way on all three voices
and $fe appears nowhere -- so nothing bounded the walk and every one of them
reported its `max_ticks` ceiling back as the song length. Four of them read
an identical 2401s window, which is what exposed it: three identical round
numbers are a cap, not three song lengths.

These pin the MECHANISM, not the spans the defect happened to produce. The
two failure modes the guard has to sit between are both asserted here: no
bound at all (the defect), and stopping each voice at its own first wrap
(which would truncate a short track that is MEANT to repeat under a long
one -- Space_Suit v1 is a single pair that loops 38 times per song).
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sdi_parser import load_sid, SDIModule

CORPUS = Path(__file__).parent.parent / "SID" / "Gallefoss_Glenn"
MT = 40000


def d_modules():
    """Every variant-D module in the corpus, as (name, SDIModule)."""
    out = []
    for p in sorted(CORPUS.glob("*.sid")):
        try:
            d, la, h = load_sid(str(p))
            m = SDIModule(d, la)
        except Exception:
            continue                      # not an SDI rip; locate() failed
        if m.lay.variant == 'D':
            out.append((p.stem, m))
    return out


class TestDVariantLoopGuard(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not CORPUS.is_dir():
            raise unittest.SkipTest(f"missing {CORPUS}")
        cls.mods = d_modules()
        if not cls.mods:
            raise unittest.SkipTest("no variant-D files in the corpus")

    def test_the_walk_is_bounded_by_the_song_not_by_the_tick_cap(self):
        """The defect: span == max_ticks, so the cap WAS the song length."""
        for name, m in self.mods:
            with self.subTest(name):
                span = max((e.frame for v in range(3)
                            for e in m.decode_voice(v, MT)), default=0)
                self.assertLess(
                    span, MT * m.fpt,
                    f"{name} still decodes to the {MT}-tick ceiling -- the "
                    "cap is being read back as the song length")

    def test_raising_the_cap_does_not_move_the_song_length(self):
        """A cap you can move is not a length. A length is not a cap."""
        for name, m in self.mods:
            with self.subTest(name):
                a = SDIModule(m.d, m.la)._song_ticks_d(MT)
                b = SDIModule(m.d, m.la)._song_ticks_d(MT * 10)
                self.assertEqual(a, b, f"{name} song length tracks the cap")

    def test_the_guard_only_truncates_and_never_alters_an_event(self):
        """Bounding the walk must not change the music inside the bound.

        Each side gets a FRESH module on purpose. Comparing two walks of one
        module hides the bug this test exists for: _play_seq_d carries the
        running instrument on the module and mutates it in place, so a
        second walk starts from the first walk's leftovers and the two agree
        for the wrong reason. Measured against the pre-guard parser, that
        confound hid a real change to 21 of 54 corpus voices.
        """
        for name, m in self.mods:
            for v in range(3):
                with self.subTest(name=name, voice=v):
                    fresh = SDIModule(m.d, m.la)
                    new = SDIModule(m.d, m.la).decode_voice(v, MT)
                    old = fresh._walk_d(v, MT, wrap=True)[0]   # unbounded
                    self.assertEqual(
                        new, old[:len(new)],
                        f"{name} v{v}: bounded decode is not a prefix of the "
                        "unbounded one -- the guard changed the decode")

    def test_measuring_the_song_leaves_no_trace_on_the_decoder(self):
        """The bound is computed by walking every voice first. That pass
        must restore the running instrument it mutates, or it hands the real
        decode someone else's instrument."""
        for name, m in self.mods:
            with self.subTest(name):
                probe = SDIModule(m.d, m.la)
                probe._cur_instr = [7, 7, 7]
                probe._song_ticks_d(MT)
                self.assertEqual(
                    probe._cur_instr, [7, 7, 7],
                    f"{name}: measuring the song length clobbered _cur_instr")
                virgin = SDIModule(m.d, m.la)
                virgin._song_ticks_d(MT)
                self.assertNotIn(
                    '_cur_instr', vars(virgin),
                    f"{name}: measuring invented decoder state from nothing")

    def test_a_short_track_still_loops_under_a_long_one(self):
        """The other failure mode: stopping at the first $ff would leave a
        short-track voice silent for the rest of the song. Space_Suit v1 is
        one pair; it has to repeat, not stop."""
        mods = dict(self.mods)
        if 'Space_Suit' not in mods:
            self.skipTest("Space_Suit not in corpus")
        m = mods['Space_Suit']
        one_pass = len(m._walk_d(1, MT, wrap=False)[0])
        looped = len(m.decode_voice(1, MT))
        self.assertGreater(
            looped, 5 * one_pass,
            "the wrap stopped firing -- a 1-pair track no longer repeats")

    def test_song_length_is_the_longest_voice_not_the_first_wrap(self):
        """The rule itself: the bound comes from the longest single pass."""
        for name, m in self.mods:
            with self.subTest(name):
                passes = [m._walk_d(v, MT, wrap=False)[1] for v in range(3)]
                self.assertEqual(m._song_ticks_d(MT), max(passes),
                                 f"{name}: bound is not the longest pass")

    def test_every_voice_still_sounds_for_the_whole_song(self):
        """A bound that silences a voice for the tail is worse than no bound.
        Loose on purpose: this catches a truncated voice, not a few frames."""
        for name, m in self.mods:
            end = m._song_ticks_d(MT) * m.fpt
            for v in range(3):
                with self.subTest(name=name, voice=v):
                    ev = m.decode_voice(v, MT)
                    if not ev:
                        continue                  # genuinely empty track
                    last = max(e.frame for e in ev)
                    self.assertGreater(
                        last, 0.9 * end,
                        f"{name} v{v} stops at {last} of {end} -- truncated")


if __name__ == "__main__":
    unittest.main()
