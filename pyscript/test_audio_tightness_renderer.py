#!/usr/bin/env python3
"""Renderer-selection tests for audio_tightness_tool.

choose_renderer() is pure (availability is injected, not probed), so these
run without VICE or sidplayfp installed.

The rule these lock in: ONE renderer serves BOTH sides of a comparison, and
--voice forces sidplayfp because it is the only renderer with a voice-mute
flag. Everything else prefers VSID as the default renderer.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.audio_tightness_tool import RenderError, choose_renderer


BOTH = dict(vsid_available=True, sidplayfp_available=True)


class TestChooseRendererAuto(unittest.TestCase):
    def test_auto_prefers_vsid_when_available(self):
        renderer, _ = choose_renderer('auto', None, **BOTH)
        self.assertEqual(renderer, 'vsid')

    def test_auto_falls_back_to_sidplayfp_without_vsid(self):
        renderer, reason = choose_renderer('auto', None, vsid_available=False,
                                            sidplayfp_available=True)
        self.assertEqual(renderer, 'sidplayfp')
        self.assertIn('falling back', reason)

    def test_auto_with_voice_forces_sidplayfp_even_though_vsid_available(self):
        renderer, reason = choose_renderer('auto', 1, **BOTH)
        self.assertEqual(renderer, 'sidplayfp')
        self.assertIn('--voice', reason)

    def test_auto_with_voice_errors_without_sidplayfp(self):
        with self.assertRaises(RenderError) as cm:
            choose_renderer('auto', 2, vsid_available=True, sidplayfp_available=False)
        self.assertIn('--voice', str(cm.exception))

    def test_auto_errors_when_nothing_available(self):
        with self.assertRaises(RenderError) as cm:
            choose_renderer('auto', None, vsid_available=False, sidplayfp_available=False)
        self.assertIn('No renderer available', str(cm.exception))


class TestChooseRendererExplicit(unittest.TestCase):
    def test_explicit_vsid(self):
        renderer, reason = choose_renderer('vsid', None, **BOTH)
        self.assertEqual(renderer, 'vsid')
        self.assertIn('explicitly', reason)

    def test_explicit_sidplayfp_wins_over_vsid_preference(self):
        renderer, _ = choose_renderer('sidplayfp', None, **BOTH)
        self.assertEqual(renderer, 'sidplayfp')

    def test_explicit_vsid_with_voice_is_rejected(self):
        # Silently ignoring --voice would produce an unmuted render presented
        # as if it were voice-isolated -- the failure mode worth erroring on.
        with self.assertRaises(RenderError) as cm:
            choose_renderer('vsid', 3, **BOTH)
        self.assertIn('voice-mute', str(cm.exception))

    def test_explicit_vsid_unavailable_errors(self):
        with self.assertRaises(RenderError) as cm:
            choose_renderer('vsid', None, vsid_available=False, sidplayfp_available=True)
        self.assertIn('vsid.exe', str(cm.exception))

    def test_explicit_sidplayfp_unavailable_errors(self):
        with self.assertRaises(RenderError) as cm:
            choose_renderer('sidplayfp', None, vsid_available=True, sidplayfp_available=False)
        self.assertIn('sidplayfp.exe', str(cm.exception))


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


class TestVoiceAllForcesSidplayfp(unittest.TestCase):
    """--voice all is a voice request like any other: it needs -u, so it needs
    sidplayfp. The value is the string 'all' rather than an int, so this pins
    that choose_renderer tests truthiness and not `isinstance(voice, int)`.
    """

    def test_voice_all_forces_sidplayfp_over_vsid_preference(self):
        renderer, reason = choose_renderer('auto', 'all', **BOTH)
        self.assertEqual(renderer, 'sidplayfp')
        self.assertIn('voice', reason)

    def test_voice_all_with_explicit_vsid_is_rejected(self):
        with self.assertRaises(RenderError):
            choose_renderer('vsid', 'all', **BOTH)


class TestPowerOnDelayIsPinned(unittest.TestCase):
    """sidplayfp's --delay defaults to RANDOM (`--help-debug`), which shifts the
    whole render by up to ~8 ms per run. Measured 2026-08-08 on Commando over
    20 s: three renders with identical arguments gave onset counts 152/159/156
    and rms(difference)/rms of ~1.2 -- the difference between two runs of the
    SAME file was as large as the signal. With --delay=0 the same three renders
    give 156/156/156 and ~0.0003. A tool whose whole output is onset timing in
    milliseconds cannot leave that flag at its default.
    """

    def _args(self, **kw):
        import subprocess
        import tempfile
        from unittest import mock
        from sidm2.sidplayfp_wrapper import SidplayfpIntegration
        seen = {}

        def fake_run(args, **_):
            seen['args'] = args
            raise RuntimeError('stop before rendering')

        # export_to_wav returns early on a missing input file, so the fixture
        # has to be a real (empty) file -- sidplayfp is never actually run.
        with tempfile.TemporaryDirectory() as td:
            sid = Path(td) / 'x.sid'
            sid.write_bytes(b'')
            with mock.patch.object(SidplayfpIntegration, '_find_sidplayfp',
                                    return_value=Path('sidplayfp.exe')), \
                 mock.patch.object(subprocess, 'run', side_effect=fake_run):
                SidplayfpIntegration.export_to_wav(
                    sid_file=sid, output_file=Path(td) / 'x.wav', **kw)
        return seen.get('args', [])

    def test_delay_zero_by_default(self):
        self.assertIn('--delay=0', self._args())

    def test_explicit_delay_is_passed_through(self):
        self.assertIn('--delay=1500', self._args(power_on_delay=1500))

    def test_none_restores_sidplayfps_random_default(self):
        self.assertFalse([a for a in self._args(power_on_delay=None)
                          if a.startswith('--delay')])
