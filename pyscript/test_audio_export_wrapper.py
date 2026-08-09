#!/usr/bin/env python3
"""Tests for sidm2.audio_export_wrapper.AudioExportIntegration.export_voice_stems.

Mocks SidplayfpIntegration.export_to_wav (no real sidplayfp.exe needed) and
AudioExportIntegration._check_tool_available -- same pattern as
test_audio_tightness_renderer.py's TestPowerOnDelayIsPinned, so this runs
without VICE or sidplayfp installed.
"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.audio_export_wrapper import AudioExportIntegration


def _ok_result(output_file):
    return {'success': True, 'output_file': output_file, 'file_size': 1234}


class TestExportVoiceStemsUnavailable(unittest.TestCase):
    def test_returns_none_when_sidplayfp_unavailable(self):
        with mock.patch.object(AudioExportIntegration, '_check_tool_available',
                                return_value=False):
            result = AudioExportIntegration.export_voice_stems(
                sid_file=Path('song.sid'), output_wav=Path('out/song.wav'))
        self.assertIsNone(result)


class TestExportVoiceStemsCallsSidplayfp(unittest.TestCase):
    def _run(self, side_effect=None):
        calls = []

        def fake_export_to_wav(**kw):
            calls.append(kw)
            if side_effect:
                return side_effect(kw)
            return _ok_result(kw['output_file'])

        with mock.patch.object(AudioExportIntegration, '_check_tool_available',
                                return_value=True), \
             mock.patch('sidm2.audio_export_wrapper.SidplayfpIntegration.export_to_wav',
                         side_effect=fake_export_to_wav):
            result = AudioExportIntegration.export_voice_stems(
                sid_file=Path('song.sid'), output_wav=Path('out/song.wav'), duration=30)
        return result, calls

    def test_calls_sidplayfp_three_times(self):
        _, calls = self._run()
        self.assertEqual(len(calls), 3)

    def test_mute_digits_match_voice_mute_map(self):
        _, calls = self._run()
        mutes = {c['mute_voices'] for c in calls}
        self.assertEqual(mutes, {'23', '13', '12'})

    def test_power_on_delay_pinned_to_zero(self):
        _, calls = self._run()
        for c in calls:
            self.assertEqual(c['power_on_delay'], 0)

    def test_output_filenames_are_named_per_voice(self):
        _, calls = self._run()
        names = sorted(str(c['output_file'].name) for c in calls)
        self.assertEqual(names, ['song_voice1.wav', 'song_voice2.wav', 'song_voice3.wav'])

    def test_stems_written_next_to_output_wav(self):
        _, calls = self._run()
        for c in calls:
            self.assertEqual(c['output_file'].parent, Path('out'))

    def test_duration_and_subtune_forwarded(self):
        with mock.patch.object(AudioExportIntegration, '_check_tool_available',
                                return_value=True), \
             mock.patch('sidm2.audio_export_wrapper.SidplayfpIntegration.export_to_wav',
                         return_value=_ok_result(Path('x'))) as mocked:
            AudioExportIntegration.export_voice_stems(
                sid_file=Path('song.sid'), output_wav=Path('out/song.wav'),
                duration=45, subtune=2)
        for _, kw in mocked.call_args_list:
            self.assertEqual(kw['duration'], 45)
            self.assertEqual(kw['subtune'], 2)

    def test_result_keyed_by_voice_number(self):
        result, _ = self._run()
        self.assertEqual(set(result.keys()), {1, 2, 3})

    def test_successful_result_tagged_with_tool(self):
        result, _ = self._run()
        for r in result.values():
            self.assertEqual(r['tool'], 'sidplayfp')


class TestExportVoiceStemsPartialFailure(unittest.TestCase):
    def test_one_voice_failing_does_not_abort_the_others(self):
        def side_effect(kw):
            if kw['mute_voices'] == '13':  # voice 2
                return {'success': False, 'error': 'boom'}
            return _ok_result(kw['output_file'])

        with mock.patch.object(AudioExportIntegration, '_check_tool_available',
                                return_value=True), \
             mock.patch('sidm2.audio_export_wrapper.SidplayfpIntegration.export_to_wav',
                         side_effect=lambda **kw: side_effect(kw)):
            result = AudioExportIntegration.export_voice_stems(
                sid_file=Path('song.sid'), output_wav=Path('out/song.wav'))

        self.assertFalse(result[2]['success'])
        self.assertEqual(result[2]['error'], 'boom')
        self.assertTrue(result[1]['success'])
        self.assertTrue(result[3]['success'])

    def test_export_to_wav_returning_none_is_reported_as_failure(self):
        with mock.patch.object(AudioExportIntegration, '_check_tool_available',
                                return_value=True), \
             mock.patch('sidm2.audio_export_wrapper.SidplayfpIntegration.export_to_wav',
                         return_value=None):
            result = AudioExportIntegration.export_voice_stems(
                sid_file=Path('song.sid'), output_wav=Path('out/song.wav'))
        for r in result.values():
            self.assertFalse(r['success'])
            self.assertIn('error', r)


if __name__ == '__main__':
    unittest.main()
