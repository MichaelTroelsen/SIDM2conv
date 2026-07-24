#!/usr/bin/env python3
"""Renderer-selection tests for audio_tightness_tool.

choose_renderer() is pure (availability is injected, not probed), so these
run without VICE or SID2WAV installed.

The rule these lock in: ONE renderer serves BOTH sides of a comparison, and
--voice forces SID2WAV because it is the only renderer with a voice-mute
flag. Everything else prefers VSID -- SID2WAV is a 1997 build that hangs
outright on some newer tunes (lft's Glyptodont renders zero samples under it
while VSID handles it fine), which is what made the auto-selection necessary.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.audio_tightness_tool import RenderError, choose_renderer


BOTH = dict(vsid_available=True, sid2wav_available=True)


class TestChooseRendererAuto(unittest.TestCase):
    def test_auto_prefers_vsid_when_available(self):
        renderer, _ = choose_renderer('auto', None, **BOTH)
        self.assertEqual(renderer, 'vsid')

    def test_auto_falls_back_to_sid2wav_without_vsid(self):
        renderer, reason = choose_renderer('auto', None, vsid_available=False,
                                            sid2wav_available=True)
        self.assertEqual(renderer, 'sid2wav')
        self.assertIn('falling back', reason)

    def test_auto_with_voice_forces_sid2wav_even_though_vsid_available(self):
        renderer, reason = choose_renderer('auto', 1, **BOTH)
        self.assertEqual(renderer, 'sid2wav')
        self.assertIn('--voice', reason)

    def test_auto_with_voice_errors_without_sid2wav(self):
        with self.assertRaises(RenderError) as cm:
            choose_renderer('auto', 2, vsid_available=True, sid2wav_available=False)
        self.assertIn('--voice', str(cm.exception))

    def test_auto_errors_when_nothing_available(self):
        with self.assertRaises(RenderError) as cm:
            choose_renderer('auto', None, vsid_available=False, sid2wav_available=False)
        self.assertIn('No renderer available', str(cm.exception))


class TestChooseRendererExplicit(unittest.TestCase):
    def test_explicit_vsid(self):
        renderer, reason = choose_renderer('vsid', None, **BOTH)
        self.assertEqual(renderer, 'vsid')
        self.assertIn('explicitly', reason)

    def test_explicit_sid2wav_wins_over_vsid_preference(self):
        renderer, _ = choose_renderer('sid2wav', None, **BOTH)
        self.assertEqual(renderer, 'sid2wav')

    def test_explicit_vsid_with_voice_is_rejected(self):
        # Silently ignoring --voice would produce an unmuted render presented
        # as if it were voice-isolated -- the failure mode worth erroring on.
        with self.assertRaises(RenderError) as cm:
            choose_renderer('vsid', 3, **BOTH)
        self.assertIn('voice-mute', str(cm.exception))

    def test_explicit_vsid_unavailable_errors(self):
        with self.assertRaises(RenderError) as cm:
            choose_renderer('vsid', None, vsid_available=False, sid2wav_available=True)
        self.assertIn('vsid.exe', str(cm.exception))

    def test_explicit_sid2wav_unavailable_errors(self):
        with self.assertRaises(RenderError) as cm:
            choose_renderer('sid2wav', None, vsid_available=True, sid2wav_available=False)
        self.assertIn('SID2WAV.EXE', str(cm.exception))


class TestRendererIsSharedByBothSides(unittest.TestCase):
    def test_same_inputs_give_same_renderer(self):
        """Both sides resolve through one choose_renderer() call in main(),
        but assert determinism anyway -- a renderer that varied per call
        would silently compare two different SID emulations."""
        for voice in (None, 1, 2, 3):
            first = choose_renderer('auto', voice, **BOTH)
            second = choose_renderer('auto', voice, **BOTH)
            self.assertEqual(first, second)


if __name__ == '__main__':
    unittest.main()
