#!/usr/bin/env python3
"""Calibration cases: check the listening metrics against a HUMAN's verdict.

Improvement #3 from docs/AUDIO_LISTENING_IMPROVEMENT_PLANS.md. Every threshold
in sidm2/audio_listen.py and sidm2/audio_tightness.py was chosen by reasoning,
not derived from a listening test. `pyscript/calibration_cases.json` records the
pairs where someone actually listened and said something, so the metrics can be
checked against evidence outside themselves.

WHAT RUNS BY DEFAULT
    The manifest checks -- structure, internal consistency, and the recorded
    findings. These are fast, need no audio, and are the part that guards
    against the manifest silently rotting.

WHAT IS OPT-IN
    Re-measuring a case means building two SF2s (one at a historical commit, via
    a git worktree) and rendering minutes of audio -- far too heavy for a suite
    that runs on every commit. Those tests skip unless SIDM2_CALIBRATION_AUDIO
    is set AND the artifacts named in the manifest exist.

Usage:
    python -m pytest pyscript/test_audio_listen_calibration.py -v
"""
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

MANIFEST = Path(__file__).parent / 'calibration_cases.json'
AUDIO_ENV = 'SIDM2_CALIBRATION_AUDIO'


def load_manifest():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


class TestManifestIsWellFormed(unittest.TestCase):
    def setUp(self):
        self.data = load_manifest()

    def test_manifest_exists_and_parses(self):
        self.assertIn('cases', self.data)
        self.assertGreater(len(self.data['cases']), 0)

    def test_every_case_has_a_human_verdict(self):
        # The entire point of a calibration case: without a recorded human
        # judgement it is just another number checked against itself.
        for case in self.data['cases']:
            self.assertTrue(case.get('human_verdict'),
                            f"{case.get('id')}: no human_verdict")
            self.assertTrue(case.get('verdict_source'),
                            f"{case.get('id')}: verdict not attributed to a source")

    def test_every_case_is_regenerable(self):
        for case in self.data['cases']:
            for name, build in case['builds'].items():
                self.assertTrue(build.get('commit'), f"{case['id']}/{name}: no commit")
                self.assertTrue(build.get('build_cmd'), f"{case['id']}/{name}: no build_cmd")

    def test_referenced_tunes_exist(self):
        root = Path(__file__).parent.parent
        for case in self.data['cases']:
            self.assertTrue((root / case['tune']).exists(),
                            f"{case['id']}: tune missing: {case['tune']}")

    def test_case_ids_are_unique(self):
        ids = [c['id'] for c in self.data['cases']]
        self.assertEqual(len(ids), len(set(ids)))


class TestRecordedFindingsAreInternallyConsistent(unittest.TestCase):
    """The manifest's prose findings must agree with its own numbers.

    Guards the failure mode where someone re-measures, updates the numbers, and
    leaves a conclusion behind that the new numbers no longer support.
    """

    def setUp(self):
        self.data = load_manifest()

    def test_orders_correctly_matches_the_numbers(self):
        for case in self.data['cases']:
            m = case['measurements']['onset_match_pct']
            claimed = case['findings']['orders_correctly']
            actual = m['bad'] < m['good']
            self.assertEqual(claimed, actual,
                             f"{case['id']}: findings.orders_correctly={claimed} but "
                             f"bad={m['bad']} good={m['good']}")

    def test_absolute_gate_claim_matches_the_floor(self):
        # "Usable as an absolute gate" requires the known-GOOD build to sit
        # inside its own repeatability floor. If a correct build scores below
        # the floor, no threshold can separate good from bad.
        for case in self.data['cases']:
            m = case['measurements']
            good = m['onset_match_pct']['good']
            floor_min = m['repeatability_floor_pct']['min']
            claimed = case['findings']['absolute_gate_usable']
            self.assertEqual(claimed, good >= floor_min,
                             f"{case['id']}: absolute_gate_usable={claimed} but "
                             f"good={good} vs floor_min={floor_min}")

    def test_floor_min_max_bracket_the_samples(self):
        for case in self.data['cases']:
            fl = case['measurements']['repeatability_floor_pct']
            self.assertAlmostEqual(fl['min'], min(fl['samples']), places=6)
            self.assertAlmostEqual(fl['max'], max(fl['samples']), places=6)

    def test_both_builds_are_below_the_floor(self):
        # The finding this case exists to pin: BOTH driver builds -- including
        # the one with no outstanding complaint -- score below what the original
        # scores against itself. That systematic deficit, not the bad/good gap,
        # is why this metric cannot gate a native-driver build.
        for case in self.data['cases']:
            m = case['measurements']
            floor_min = m['repeatability_floor_pct']['min']
            for which in ('bad', 'good'):
                self.assertLess(m['onset_match_pct'][which], floor_min,
                                f"{case['id']}/{which} is at or above the floor -- "
                                f"the recorded finding no longer holds, re-check the doc")


@unittest.skipUnless(os.environ.get(AUDIO_ENV),
                     f"set {AUDIO_ENV}=1 (and build the artifacts) to re-measure")
class TestReMeasureFromAudio(unittest.TestCase):
    """Re-derive a case's numbers from real audio and confirm the ordering holds.

    Deliberately asserts only the ORDINAL claim (bad scores below good), never
    the exact percentages: those move with renderer version, window length and
    onset-detector tuning, and a test pinned to them would fail for reasons that
    say nothing about fidelity.
    """

    def test_ordering_holds_when_remeasured(self):
        from sidm2.audio_tightness import analyze_tightness_files

        root = Path(__file__).parent.parent
        data = load_manifest()
        checked = 0
        for case in data['cases']:
            wavs = {w: root / 'out' / 'calibration' / f"{case['id']}_{w}.wav"
                    for w in ('orig', 'bad', 'good')}
            if not all(p.exists() for p in wavs.values()):
                continue
            rates = {}
            for which in ('bad', 'good'):
                rep = analyze_tightness_files(wavs['orig'], wavs[which])
                rates[which] = (len(rep.matched) / len(rep.orig_onsets)
                                if rep.orig_onsets else None)
            self.assertIsNotNone(rates['bad'])
            self.assertIsNotNone(rates['good'])
            self.assertLess(rates['bad'], rates['good'],
                            f"{case['id']}: the known-bad build no longer scores below "
                            f"the known-good one ({rates['bad']:.3f} vs {rates['good']:.3f})")
            checked += 1
        if checked == 0:
            self.skipTest("no calibration WAVs found under out/calibration/")


if __name__ == '__main__':
    unittest.main()
