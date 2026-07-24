#!/usr/bin/env python3
"""Unit Tests for pyscript.audio_tightness_report

Checks the text report's fixed structure and that expected values appear,
using hand-built TightnessReport fixtures (no rendering/analysis needed).
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.audio_tightness_report import format_text_report
from sidm2.audio_tightness import Onset, OnsetMatch, TightnessReport


def _make_report():
    matched = [
        OnsetMatch(orig_t=0.18, driver_t=0.18, delta_ms=0.0, rise_delta_ms=0.5,
                   spectral_dist=0.01, loose=False),
        OnsetMatch(orig_t=0.58, driver_t=0.63, delta_ms=50.0, rise_delta_ms=1.2,
                   spectral_dist=0.2, loose=True),
    ]
    return TightnessReport(
        orig_onsets=[Onset(t=0.18), Onset(t=0.58), Onset(t=0.98)],
        driver_onsets=[Onset(t=0.18), Onset(t=0.63), Onset(t=1.4)],
        matched=matched,
        missing=[0.98],
        extra=[1.4],
        params={'onset_tolerance_ms': 150, 'loose_threshold_ms': 40},
    )


class TestFormatTextReport(unittest.TestCase):
    def setUp(self):
        self.report = _make_report()

    def test_has_expected_section_headers(self):
        text = format_text_report(self.report, {'orig_path': 'a.sid', 'driver_path': 'b.sf2'})
        for header in ("AUDIO TIGHTNESS REPORT", "SUMMARY", "WORST OFFENDERS",
                       "MISSING ONSETS", "EXTRA ONSETS"):
            self.assertIn(header, text)

    def test_file_paths_present(self):
        text = format_text_report(self.report, {'orig_path': 'orig.sid', 'driver_path': 'drv.sf2'})
        self.assertIn('orig.sid', text)
        self.assertIn('drv.sf2', text)

    def test_counts_present(self):
        text = format_text_report(self.report, {})
        self.assertIn("Orig onsets:    3", text)
        self.assertIn("Driver onsets:  3", text)
        self.assertIn("Matched:        2", text)
        self.assertIn("Missing:        1", text)
        self.assertIn("Extra:          1", text)

    def test_loose_count_present(self):
        text = format_text_report(self.report, {})
        self.assertIn("Loose onsets:   1 / 2", text)

    def test_worst_offender_delta_present(self):
        text = format_text_report(self.report, {})
        self.assertIn("+50.0", text)

    def test_missing_and_extra_times_listed(self):
        text = format_text_report(self.report, {})
        self.assertIn("0.980", text)
        self.assertIn("1.400", text)

    def test_no_matches_handled_gracefully(self):
        empty = TightnessReport(
            orig_onsets=[Onset(t=0.1)], driver_onsets=[], matched=[],
            missing=[0.1], extra=[], params={},
        )
        text = format_text_report(empty, {})
        self.assertIn("No matched onsets", text)
        self.assertIn("(none)", text)  # worst-offenders table empty

    def test_voice_and_duration_meta_shown(self):
        text = format_text_report(self.report, {'voice': 2, 'mute_voices': '13', 'duration': 30})
        self.assertIn("voice 2", text)
        self.assertIn("30s", text)


if __name__ == '__main__':
    unittest.main()
