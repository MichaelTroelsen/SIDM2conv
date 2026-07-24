#!/usr/bin/env python3
"""Unit Tests for pyscript.audio_tightness_html_exporter

No browser needed -- asserts well-formed HTML and presence of expected
content strings, mirroring test_sidwinder_html_exporter.py's pattern.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.audio_tightness_html_exporter import AudioTightnessHTMLExporter
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


class TestAudioTightnessHTMLExporter(unittest.TestCase):
    def setUp(self):
        self.report = _make_report()
        self.meta = {'orig_path': 'orig.sid', 'driver_path': 'driver.sf2'}

    def test_well_formed_html(self):
        html = AudioTightnessHTMLExporter(self.report, self.meta).build_html()
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('<html', html)
        self.assertIn('</html>', html)
        self.assertIn('<script>', html)

    def test_file_names_present(self):
        html = AudioTightnessHTMLExporter(self.report, self.meta).build_html()
        self.assertIn('orig.sid', html)
        self.assertIn('driver.sf2', html)

    def test_stat_labels_present(self):
        html = AudioTightnessHTMLExporter(self.report, self.meta).build_html()
        # "Offset" and "Loose % (jitter)" replaced the old single "Mean Delta"
        # card: a whole-render shift and per-note looseness are different
        # defects and one averaged number hid that.
        for label in ("Matched", "Missing", "Extra", "Offset", "Loose", "Crossed"):
            self.assertIn(label, html)

    def test_timeline_section_present(self):
        html = AudioTightnessHTMLExporter(self.report, self.meta).build_html()
        self.assertIn('tightness-timeline-canvas', html)
        self.assertIn('Alignment Timeline', html)
        self.assertIn('timeline-offset-toggle', html)

    def test_timeline_reports_no_crossings_for_monotonic_alignment(self):
        html = AudioTightnessHTMLExporter(self.report, self.meta).build_html()
        self.assertIn('No crossed pairs', html)

    def test_timeline_flags_crossed_pairs(self):
        """A driver onset that runs backwards relative to its predecessor is
        a mispairing, and the timeline must say so rather than presenting it
        as ordinary jitter."""
        from sidm2.audio_tightness import OnsetMatch
        crossed = _make_report()
        crossed.matched = [
            OnsetMatch(orig_t=0.10, driver_t=0.90, delta_ms=800.0,
                       rise_delta_ms=0.0, spectral_dist=0.1, loose=True),
            OnsetMatch(orig_t=0.50, driver_t=0.20, delta_ms=-300.0,
                       rise_delta_ms=0.0, spectral_dist=0.1, loose=True),
        ]
        html = AudioTightnessHTMLExporter(crossed, self.meta).build_html()
        self.assertIn('crossed pair(s)', html)
        self.assertNotIn('No crossed pairs', html)

    def test_stat_values_present(self):
        html = AudioTightnessHTMLExporter(self.report, self.meta).build_html()
        # 2 matched, 1 missing, 1 extra (see _make_report)
        self.assertIn('>2<', html)
        self.assertIn('>1<', html)

    def test_onset_table_rows_present(self):
        html = AudioTightnessHTMLExporter(self.report, self.meta).build_html()
        self.assertIn('0.180', html)
        self.assertIn('0.630', html)
        self.assertIn('sortOnsetTable', html)

    def test_waveform_section_present_without_env_data(self):
        html = AudioTightnessHTMLExporter(self.report, self.meta).build_html()
        self.assertIn('tightness-waveform-canvas', html)
        self.assertIn('No waveform envelope data', html)

    def test_waveform_section_uses_env_data_when_provided(self):
        html = AudioTightnessHTMLExporter(
            self.report, self.meta, orig_env=[0.1, 0.5, 0.2], driver_env=[0.1, 0.4, 0.3]
        ).build_html()
        self.assertNotIn('No waveform envelope data', html)
        self.assertIn('origEnv', html)
        self.assertIn('driverEnv', html)

    def test_empty_report_does_not_crash(self):
        empty = TightnessReport(orig_onsets=[], driver_onsets=[], matched=[], missing=[], extra=[], params={})
        html = AudioTightnessHTMLExporter(empty, {}).build_html()
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('</html>', html)

    def test_export_writes_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.html"
            exporter = AudioTightnessHTMLExporter(self.report, self.meta)
            self.assertTrue(exporter.export(out))
            self.assertTrue(out.exists())
            content = out.read_text(encoding='utf-8')
            self.assertIn('<!DOCTYPE html>', content)


if __name__ == '__main__':
    unittest.main()
