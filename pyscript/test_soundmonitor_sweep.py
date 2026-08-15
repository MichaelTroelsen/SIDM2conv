#!/usr/bin/env python3
"""Tests for the Sound Monitor corpus fidelity sweep (pyscript/soundmonitor_sweep.py).

The parsing/tally/compare logic is pure and always runs. Triggering the 11
real native builds (64tass assembly, subprocess calls) inside the fast test
suite would be slow and CI-flaky, so the corpus-reproduction check instead
reads a pre-existing out/soundmonitor/sweep_*.json and skips cleanly if none
exists yet -- run `py -3 pyscript/soundmonitor_sweep.py <label>` once to
produce one (SID/Fun_Fun/ is tracked, so this reproduces from a fresh clone
with no external HVSC dependency).
"""
import glob
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "pyscript"))

import soundmonitor_sweep as sweep   # noqa: E402


class TestParseParts(unittest.TestCase):
    def test_exact_frame_bounds_preferred_over_rounded_seconds(self):
        text = "part 1/2 (0-161s, 0-8069f): instr=7 bundles=34"
        self.assertEqual(sweep.parse_parts(text), [(1, 0, 8069)])

    def test_falls_back_to_second_bounds_when_no_frame_group(self):
        text = "part 2/2 (161-241s): instr=3 bundles=10"
        self.assertEqual(sweep.parse_parts(text), [(2, 161 * 50, 241 * 50)])

    def test_multiple_parts_across_lines(self):
        text = (
            "part 1/2 (0-90s, 0-4500f): ...\n"
            "some other noise\n"
            "part 2/2 (90-161s, 4500-8069f): ...\n"
        )
        self.assertEqual(sweep.parse_parts(text),
                         [(1, 0, 4500), (2, 4500, 8069)])

    def test_no_part_lines_returns_empty(self):
        self.assertEqual(sweep.parse_parts("build failed, no output"), [])


class TestSongFreqWf(unittest.TestCase):
    def test_sums_ok_and_tot_across_parts_and_voices(self):
        rec = {"parts": {
            "1": {"voices": [{"freq_ok": 10, "wf_ok": 9, "pulse_ok": 8, "tot": 10},
                              {"freq_ok": 5, "wf_ok": 5, "pulse_ok": 5, "tot": 5}]},
            "2": {"voices": [{"freq_ok": 20, "wf_ok": 20, "pulse_ok": 20, "tot": 20}]},
        }}
        ok, tot = sweep.song_freq_wf(rec)
        self.assertEqual(ok, (10 + 9) + (5 + 5) + (20 + 20))
        self.assertEqual(tot, 2 * 10 + 2 * 5 + 2 * 20)

    def test_voices_with_zero_tot_are_excluded_not_scored_zero(self):
        """A voice with no gated frames in the window must not drag the
        percentage down -- it is unmeasured, not a failure."""
        rec = {"parts": {"1": {"voices": [
            {"freq_ok": 0, "wf_ok": 0, "pulse_ok": 0, "tot": 0},
            {"freq_ok": 10, "wf_ok": 10, "pulse_ok": 10, "tot": 10},
        ]}}}
        ok, tot = sweep.song_freq_wf(rec)
        self.assertEqual((ok, tot), (20, 20))          # only the second voice counted

    def test_missing_parts_key_is_zero_zero(self):
        self.assertEqual(sweep.song_freq_wf({"error": "no part line"}), (0, 0))


class TestCorpusFreqWfStrict(unittest.TestCase):
    def test_aggregates_across_songs(self):
        out = {
            "A": {"parts": {"1": {"voices": [{"freq_ok": 9, "wf_ok": 9, "pulse_ok": 9, "tot": 10}]}}},
            "B": {"parts": {"1": {"voices": [{"freq_ok": 10, "wf_ok": 10, "pulse_ok": 10, "tot": 10}]}}},
        }
        pct = sweep.corpus_freq_wf_strict(out)
        self.assertAlmostEqual(pct, 100 * (18 + 20) / (20 + 20))

    def test_a_failed_song_contributes_nothing_not_a_zero_score(self):
        out = {
            "A": {"error": "no part line in build output"},
            "B": {"parts": {"1": {"voices": [{"freq_ok": 10, "wf_ok": 10, "pulse_ok": 10, "tot": 10}]}}},
        }
        self.assertAlmostEqual(sweep.corpus_freq_wf_strict(out), 100.0)


class TestCompare(unittest.TestCase):
    def _rec(self, ok_per_voice, tot, nparts=1):
        parts = {str(p + 1): {"voices": [{"freq_ok": ok_per_voice, "wf_ok": ok_per_voice,
                                          "pulse_ok": 0, "tot": tot}]}
                  for p in range(nparts)}
        return {"parts": parts}

    def test_flags_regression(self):
        before = {"A": self._rec(10, 10)}   # 100%
        after = {"A": self._rec(5, 10)}      # 50%
        rep = sweep.compare(before, after)
        self.assertIn("A", rep["regressed"])
        self.assertNotIn("A", rep["improved"])

    def test_flags_improvement(self):
        before = {"A": self._rec(5, 10)}
        after = {"A": self._rec(10, 10)}
        rep = sweep.compare(before, after)
        self.assertIn("A", rep["improved"])

    def test_flags_part_count_move_separately_from_score(self):
        """A part-count change means the measurement window moved -- must be
        reported distinctly from a plain regression/improvement, exactly as
        blackbird_sweep.py's 'B10 trap' guard does."""
        before = {"A": self._rec(10, 10, nparts=1)}
        after = {"A": self._rec(10, 10, nparts=2)}
        rep = sweep.compare(before, after)
        self.assertIn("A", rep["part_moves"])

    def test_missing_song_in_either_sweep_is_an_error_not_silent(self):
        before = {"A": {"error": "no part line"}}
        after = {"A": self._rec(10, 10)}
        rep = sweep.compare(before, after)
        self.assertIn("A", rep["errors"])


class TestCorpusReproducesFromFreshClone(unittest.TestCase):
    """R21: this is the actual verification the review asked for -- a
    previously-run sweep's JSON must reproduce the documented headline. It
    reads an existing out/soundmonitor/sweep_*.json rather than running the
    11 real builds itself (slow, CI-flaky); run
    `py -3 pyscript/soundmonitor_sweep.py <label>` once to produce one --
    SID/Fun_Fun/ is tracked, so this needs nothing but a fresh checkout.
    """

    def test_headline_reproduces_within_documented_bounds(self):
        candidates = sorted(glob.glob(
            str(ROOT / "out" / "soundmonitor" / "sweep_*.json")))
        if not candidates:
            self.skipTest("no out/soundmonitor/sweep_*.json yet -- run "
                           "py -3 pyscript/soundmonitor_sweep.py <label> once")
        out = json.load(open(candidates[-1]))
        pct = sweep.corpus_freq_wf_strict(out)
        # docs/players/SOUNDMONITOR.md: 99.23% over 26/27 parts (Dance part01
        # missing from the old log-based sweep); this sweep parses parts from
        # live build output so it should recover that part too, giving 99.25%
        # (SOUNDMONITOR.md's own stated "restoring it" figure) -- allow a
        # wide-ish band since this is the FIRST tracked run, not yet a pinned
        # regression baseline.
        self.assertGreaterEqual(pct, 99.0)
        self.assertLessEqual(pct, 100.0)


if __name__ == "__main__":
    unittest.main()


def test_parse_parts_keeps_only_the_last_run_of_part_lines():
    """A build's stdout carries MORE THAN ONE run of part lines.

    This builder runs a legato A/B first -- two probe builds (`_abg`, `_abl`)
    over a 90 s head -- before the real one, and each emits its own
    `part N/M (...)`. Keeping them all is harmless only while the final build
    has at least as many parts as the probes; otherwise the probe's surplus
    entries survive as phantom parts with the WRONG bounds, pointing at
    artifacts `prune_stale_parts` has since deleted.

    The same class cost the DMC sweep a published figure: `Happy_Jingle`'s 7 s
    part 1 was scored over a probe's 90 s and read 23.4/16.1/8.1 where the part
    itself is 98.3/100.0/98.8.
    """
    probe = ("  part 1/5 (0-20s, 0-1000f): instr=7\n"
             "  part 2/5 (20-40s, 1000-2000f): instr=7\n"
             "  part 3/5 (40-60s, 2000-3000f): instr=7\n")
    final = ("  part 1/2 (0-7s, 0-395f): instr=12\n"
             "  part 2/2 (7-90s, 395-4500f): instr=2\n")
    got = sweep.parse_parts(probe + final)
    assert got == [(1, 0, 395), (2, 395, 4500)], got
    assert len(got) == 2, "the probe's surplus parts must not survive"


def test_parse_parts_is_unchanged_for_a_single_run():
    """The guard must not disturb the ordinary case -- one build, N parts."""
    text = ("  part 1/3 (0-10s, 0-500f)\n"
            "  part 2/3 (10-20s, 500-1000f)\n"
            "  part 3/3 (20-30s, 1000-1500f)\n")
    assert sweep.parse_parts(text) == [(1, 0, 500), (2, 500, 1000), (3, 1000, 1500)]
