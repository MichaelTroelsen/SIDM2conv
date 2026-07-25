#!/usr/bin/env python3
"""Tests for the Blackbird corpus sweep harness (pyscript/blackbird_sweep.py).

These do NOT build anything -- a real sweep is ~25 minutes. They cover the
parts that can silently corrupt a fidelity claim: the output parser, the
regression/part-move comparison, and the integrity of the corpus list itself.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "pyscript"))

import blackbird_sweep as sweep   # noqa: E402

# A real build tail, captured verbatim from To_Die_For_II after E4.
SAMPLE_OK = """
  packed into 1 adaptive part(s) (span 643 tick-rows, 150-row probe step)
    part 1/1 rows[0:643) (643 rows): wrote out/blackbird/To_Die_For_II_native_part01.sf2 (13986 bytes)
    full-part window (2572f span) [0:2572) n=2572: overall=98.2%  freq=99.9%, waveform=100.0%, pulse=100.0%, adsr=100.0%, filter=88.9%

  WEIGHTED AVERAGE over 1 part(s), 2572 frames (CAP_B=96): overall=98.2%  freq=99.9%, waveform=100.0%, pulse=100.0%, adsr=100.0%, filter=88.9%
"""

SAMPLE_MULTIPART = """
  packed into 3 adaptive part(s) (span 1200 tick-rows)
  WEIGHTED AVERAGE over 3 part(s), 4000 frames (CAP_B=96): overall=98.1%  freq=99.0%, waveform=100.0%, pulse=97.5%, adsr=100.0%, filter=94.0%
"""

SAMPLE_FAILED = """
Traceback (most recent call last):
SystemExit: not a located Blackbird v1.2-exact rip
"""


class TestParseBuildOutput(unittest.TestCase):
    def test_parses_all_registers_and_parts(self):
        rec = sweep.parse_build_output(SAMPLE_OK)
        self.assertIsNotNone(rec)
        self.assertAlmostEqual(rec["overall"], 98.2)
        self.assertAlmostEqual(rec["freq"], 99.9)
        self.assertAlmostEqual(rec["waveform"], 100.0)
        self.assertAlmostEqual(rec["pulse"], 100.0)
        self.assertAlmostEqual(rec["adsr"], 100.0)
        self.assertAlmostEqual(rec["filter"], 88.9)
        self.assertEqual(rec["parts"], 1)

    def test_multipart_count(self):
        self.assertEqual(sweep.parse_build_output(SAMPLE_MULTIPART)["parts"], 3)

    def test_failed_build_returns_none_not_zero(self):
        """A refused build must not read as 0% or as 'unchanged'."""
        self.assertIsNone(sweep.parse_build_output(SAMPLE_FAILED))
        self.assertIsNone(sweep.parse_build_output(""))


class TestCorpusIntegrity(unittest.TestCase):
    def test_corpus_is_sixteen_unique_files(self):
        self.assertEqual(len(sweep.CORPUS), 16)
        self.assertEqual(len(set(sweep.CORPUS)), 16)

    def test_every_corpus_sid_exists(self):
        """Catches a renamed/removed rip before it silently shrinks the sweep."""
        missing = [n for n in sweep.CORPUS
                   if not (ROOT / "SID" / "LFT" / f"{n}.sid").exists()]
        self.assertEqual(missing, [], f"corpus SIDs missing from SID/LFT: {missing}")

    def test_expected_parts_covers_corpus_exactly(self):
        self.assertEqual(set(sweep.EXPECTED_PARTS), set(sweep.CORPUS))

    def test_known_multipart_files(self):
        """The B10 trap: these three are the only files that split."""
        multi = {k: v for k, v in sweep.EXPECTED_PARTS.items() if v != 1}
        self.assertEqual(multi, {"Fargo": 2, "Dithered_Island": 2,
                                 "Into_the_Unknown": 3})


def _rec(overall, parts=1, byts=100):
    return {"overall": overall, "parts": parts, "bytes": byts,
            **{r: overall for r in sweep.REGISTERS}}


class TestCompare(unittest.TestCase):
    def test_detects_regression_and_improvement(self):
        before = {"a": _rec(99.0), "b": _rec(90.0), "c": _rec(100.0)}
        after = {"a": _rec(98.0), "b": _rec(95.0), "c": _rec(100.0)}
        rep = sweep.compare(before, after)
        self.assertEqual(rep["regressed"], ["a"])
        self.assertEqual(rep["improved"], ["b"])

    def test_part_move_reported_separately_from_regression(self):
        """A moved part count changes the measurement window, so it is not a
        regression -- it means the two numbers are not comparable at all."""
        before = {"a": _rec(99.0, parts=1)}
        after = {"a": _rec(99.0, parts=2)}
        rep = sweep.compare(before, after)
        self.assertEqual(rep["part_moves"], ["a"])
        self.assertEqual(rep["regressed"], [])

    def test_byte_identical_is_visible(self):
        """A mechanism fix leaves untouched files byte-identical; a re-tuning
        perturbs many. That distinction is worth surfacing."""
        before = {"a": _rec(99.0, byts=100), "b": _rec(99.0, byts=200)}
        after = {"a": _rec(99.0, byts=100), "b": _rec(99.5, byts=222)}
        rep = sweep.compare(before, after)
        self.assertEqual(rep["byte_changes"], ["b"])

    def test_error_record_does_not_count_as_unchanged(self):
        before = {"a": _rec(99.0)}
        after = {"a": {"error": "no WEIGHTED AVERAGE line", "rc": 1}}
        rep = sweep.compare(before, after)
        self.assertEqual(rep["errors"], ["a"])
        self.assertEqual(rep["regressed"], [])

    def test_mean_matches_recorded_e4_figure(self):
        """Guards the exact number quoted in CLAUDE.md / ACCURACY_MATRIX.md."""
        recorded = {
            "Fargo": 99.9, "Glyptodont": 99.8, "Dishwasher_Groove": 100.0,
            "Dithered_Island": 99.9, "Elvendance": 100.0, "Euclid_Was_Here": 99.9,
            "Into_the_Unknown": 98.1, "Maple_Leaf_Rag": 100.0,
            "Revolutions_Delivered": 99.0, "Thus_Spoke_the_PC_Speaker": 100.0,
            "Toy_Rocket": 100.0, "Crank_Crank_Airwolf": 100.0, "Trinket": 100.0,
            "To_Die_For_II": 98.2, "Fugue_on_a_Theme_by_D_M_Hanlon": 99.9,
            "Quintessence": 100.0,
        }
        self.assertEqual(set(recorded), set(sweep.CORPUS))
        got = sweep.mean_overall({k: _rec(v) for k, v in recorded.items()})
        self.assertAlmostEqual(got, 99.669, places=3)


class TestRoundTrip(unittest.TestCase):
    def test_json_round_trip_preserves_comparison(self):
        before = {"a": _rec(94.2)}
        after = {"a": _rec(98.2)}
        rep = sweep.compare(json.loads(json.dumps(before)),
                            json.loads(json.dumps(after)))
        self.assertEqual(rep["improved"], ["a"])
        self.assertAlmostEqual(rep["mean_after"] - rep["mean_before"], 4.0, places=6)


if __name__ == "__main__":
    unittest.main()
