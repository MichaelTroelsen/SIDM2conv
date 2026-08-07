#!/usr/bin/env python3
"""Tests for the SF2II crash oracle (pyscript/blackbird_crash_probe.py).

These NEVER launch SF2II. They cover the analysis half: the port of SF2II's own
Unpack, the combo-command schedule, and above all `assert_window_covers` -- the
guard that makes a too-short play window raise instead of returning a
reassuring all-survived result.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "pyscript"))

import blackbird_crash_probe as probe   # noqa: E402

TERM = probe.SEQ_TERMINATOR


def seq(*vals):
    """A 256-byte sequence block, terminated and zero-padded like the real thing."""
    body = bytes(vals) + bytes([TERM])
    return body + bytes(0x100 - len(body))


class TestUnpackSequence(unittest.TestCase):
    """Ported from SF2II's DataSourceSequence::Unpack (datasource_sequence.cpp)."""

    def test_bare_notes_are_one_event_each(self):
        n, cmds, packed = probe.unpack_sequence(seq(0x10, 0x11, 0x12))
        self.assertEqual(n, 3)
        self.assertEqual(cmds, [])
        self.assertEqual(packed, 4)          # 3 notes + terminator

    def test_command_byte_is_recorded_with_its_event_index(self):
        # command $C0|5, then a note
        n, cmds, _ = probe.unpack_sequence(seq(0xC0 | 5, 0x10, 0x11))
        self.assertEqual(cmds, [(0, 5)])
        self.assertEqual(n, 2)

    def test_command_index_is_masked_to_six_bits(self):
        _, cmds, _ = probe.unpack_sequence(seq(0xFF, 0x10))
        self.assertEqual(cmds, [(0, 63)])    # $FF & 0x3F == 63 == RESTART_ARM_FX

    def test_instrument_byte_is_consumed_between_command_and_note(self):
        n, cmds, _ = probe.unpack_sequence(seq(0xC0 | 7, 0xA0 | 3, 0x10))
        self.assertEqual(cmds, [(0, 7)])
        self.assertEqual(n, 1)

    def test_duration_byte_expands_into_extra_events(self):
        # $80|4 -> duration 4, then the note; 1 note event + 4 held events
        n, _, _ = probe.unpack_sequence(seq(0x80 | 4, 0x10))
        self.assertEqual(n, 5)

    def test_duration_persists_across_following_notes(self):
        """`duration` is NOT reset per event in the C++ -- it is sticky."""
        n, _, _ = probe.unpack_sequence(seq(0x80 | 2, 0x10, 0x11))
        self.assertEqual(n, 6)               # (1+2) + (1+2)

    def test_missing_terminator_reports_none(self):
        block = bytes([0x10] * 0x100)        # no 0x7F anywhere
        n, _, packed = probe.unpack_sequence(block)
        self.assertIsNone(packed)
        self.assertEqual(n, 0x100)

    def test_overflow_detection_matches_1024_cap(self):
        """The duration-expansion loop is unbounded in the C++, so a sequence
        can genuinely unpack past the fixed 1024-entry m_Events array."""
        self.assertFalse(probe.events_overflow(seq(0x10, 0x11)))
        # 100 notes each holding 15 extra events = 1600 > 1024
        big = bytes([0x80 | 15, 0x10] * 100) + bytes([TERM])
        self.assertTrue(probe.events_overflow(big + bytes(0x100 - len(big))))

    def test_real_corpus_sequences_stay_under_the_cap(self):
        """Regression guard for the overrun hypothesis: the shipped corpus must
        never approach SF2II's 1024-event array."""
        built = sorted((ROOT / "out" / "blackbird").glob("*_native_part01.sf2"))
        if not built:
            self.skipTest("no built Blackbird SF2s in out/blackbird (gitignored)")
        worst = 0
        for path in built[:4]:
            _, seqs, _ = probe.load_sf2_sequences(str(path))
            for s in seqs:
                worst = max(worst, probe.unpack_sequence(s)[0])
        self.assertLessEqual(worst, probe.MAX_EVENT_COUNT,
                             f"a shipped sequence unpacks to {worst} events")


class TestComboSchedule(unittest.TestCase):
    def _build(self, cmd_index):
        seqs = [seq(0xC0 | cmd_index, 0x10, 0x11)]
        orderlists = [bytes([0x00, 0xFF] + [0xFF] * 254)]
        return seqs, orderlists

    def test_finds_combo_command_and_converts_to_seconds(self):
        seqs, ols = self._build(48)
        sched = probe.combo_schedule(seqs, ols, frames_per_row=4.52, combo_lo=48)
        self.assertEqual(len(sched), 1)
        secs, row, voice, cmd = sched[0]
        self.assertEqual((row, voice, cmd), (0, 0, 48))
        self.assertAlmostEqual(secs, 0.0)

    def test_sentinel_63_is_not_a_combo_command(self):
        """RESTART_ARM_FX shipped in B25 and is in the same command channel --
        it must not be counted as a combo code."""
        seqs, ols = self._build(probe.RESTART_ARM_FX)
        self.assertEqual(probe.combo_schedule(seqs, ols, 4.52, combo_lo=48), [])

    def test_below_combo_base_is_a_plain_fx_command(self):
        seqs, ols = self._build(7)
        self.assertEqual(probe.combo_schedule(seqs, ols, 4.52, combo_lo=48), [])

    def test_schedule_is_in_PLAYBACK_order_not_sequence_order(self):
        """Ordering follows the orderlist, not the sequence table.

        seq0 = two notes then command 48 (event 2); seq1 = command 49 at event
        0. The orderlist plays seq1 FIRST, so 49 lands on row 0 and 48 on row 3
        -- command 49 legitimately precedes 48 in time. (An earlier version of
        this test asserted the command INDICES ascend, which is meaningless:
        the schedule exists to say when things execute.)
        """
        seqs = [seq(0x10, 0x11, 0xC0 | 48, 0x12), seq(0xC0 | 49, 0x10)]
        ols = [bytes([0x01, 0x00, 0xFF] + [0xFF] * 253)]
        sched = probe.combo_schedule(seqs, ols, 4.52, combo_lo=48)
        self.assertEqual(sched, sorted(sched), "schedule must be time-ordered")
        self.assertEqual([(row, cmd) for _, row, _, cmd in sched],
                         [(0, 49), (3, 48)])


class TestWindowValidity(unittest.TestCase):
    """The guard for the failure that produced a false all-clear.

    A 6-second window over a build whose first combo command fires at 8.2s
    executed ZERO of the construct under test and returned 16/16 SURVIVED.
    """

    def _sched_at(self, seconds):
        return [(seconds, 91, 1, 48)]

    def test_rejects_window_shorter_than_first_event(self):
        with self.assertRaises(ValueError) as cm:
            probe.assert_window_covers(self._sched_at(8.2), window_seconds=6.0)
        self.assertIn("ZERO", str(cm.exception))

    def test_rejects_window_without_enough_margin(self):
        """Barely reaching the event is not enough -- tempo and startup vary."""
        with self.assertRaises(ValueError):
            probe.assert_window_covers(self._sched_at(8.2), window_seconds=8.5)

    def test_accepts_the_shipped_default_window(self):
        probe.assert_window_covers(self._sched_at(8.2),
                                   window_seconds=probe.PLAY_WAIT_SECONDS)

    def test_empty_schedule_is_an_error_not_a_pass(self):
        """Playing a build with no combo commands says nothing about them."""
        with self.assertRaises(ValueError):
            probe.assert_window_covers([], window_seconds=65.0)

    def test_default_window_covers_glyptodont_first_event(self):
        """Glyptodont's earliest combo command is row 91 at 4.52 frames/row."""
        first = 91 * 4.52 / 50.0
        self.assertAlmostEqual(first, 8.22, places=1)
        probe.assert_window_covers([(first, 91, 1, 48)],
                                   window_seconds=probe.PLAY_WAIT_SECONDS)


class TestClassifyTermination(unittest.TestCase):
    """R23: a user closing the SF2II window mid-trial must not be reported as
    CRASHED. The original oracle checked only `_is_alive(pid)` after the play
    wait, so "not alive" (crashed OR cleanly closed by a human) collapsed to
    one bucket -- a 492s Driller trial the user closed manually came back
    CRASHED, indistinguishable from the real thing (whats-next.md).
    """

    def test_still_running_is_survived(self):
        self.assertEqual(probe.classify_termination(None), "SURVIVED")

    def test_clean_exit_code_zero_is_closed_not_crashed(self):
        """The core R23 fix: exit code 0 must never read as CRASHED."""
        self.assertEqual(probe.classify_termination(0), "CLOSED")

    def test_positive_nonzero_exit_code_is_crashed(self):
        self.assertEqual(probe.classify_termination(1), "CRASHED")

    def test_windows_access_violation_style_code_is_crashed(self):
        """STATUS_ACCESS_VIOLATION (0xC0000005) as Windows reports it: some
        toolchains surface this as a large positive DWORD, others as the
        signed-int32 equivalent (-1073741819) -- classify_termination must
        treat both as CRASHED, since neither is ever the clean-exit value 0."""
        self.assertEqual(probe.classify_termination(3221225477), "CRASHED")
        self.assertEqual(probe.classify_termination(-1073741819), "CRASHED")


class TestTally(unittest.TestCase):
    def test_crash_rate_is_over_trials_that_actually_played(self):
        """A NOLOAD is a flaky loader, not evidence about play."""
        t = probe.tally(["SURVIVED", "CRASHED", "NOLOAD", "SURVIVED"])
        self.assertEqual(t["played"], 3)
        self.assertAlmostEqual(t["crash_rate"], 1 / 3)

    def test_no_played_trials_gives_no_rate_rather_than_zero(self):
        t = probe.tally(["NOLOAD", "NOLOAD"])
        self.assertIsNone(t["crash_rate"])

    def test_all_survived_recorded_e3f_result(self):
        t = probe.tally(["SURVIVED"] * 5)
        self.assertEqual(t["crash_rate"], 0.0)
        self.assertEqual(t["played"], 5)

    def test_closed_trials_are_excluded_from_crash_rate(self):
        """R23: a CLOSED trial (clean exit, most likely a human closing the
        window) must not count for OR against the crash rate -- it is not
        evidence either way, exactly like NOLOAD. Without this, a run of
        3 real crashes + 1 closed-by-user trial would UNDERSTATE the crash
        rate (4 trials, 3/4) instead of reporting the true 3/3 = 100%."""
        t = probe.tally(["CRASHED", "CRASHED", "CRASHED", "CLOSED"])
        self.assertEqual(t["CLOSED"], 1)
        self.assertEqual(t["played"], 3)
        self.assertAlmostEqual(t["crash_rate"], 1.0)

    def test_noplay_trials_are_excluded_from_crash_rate(self):
        """A trial whose Play keystroke was lost never entered the window under
        test, so like NOLOAD and CLOSED it is 'no test ran' -- it must not be
        counted as a pass. This is the whole point of the NOPLAY verdict: the
        old oracle reported such a trial as SURVIVED."""
        t = probe.tally(["SURVIVED", "NOPLAY", "NOPLAY"])
        self.assertEqual(t["NOPLAY"], 2)
        self.assertEqual(t["played"], 1)
        self.assertEqual(t["crash_rate"], 0.0)

    def test_all_noplay_gives_no_rate_rather_than_a_clean_pass(self):
        t = probe.tally(["NOPLAY", "NOPLAY"])
        self.assertIsNone(t["crash_rate"])
        self.assertEqual(t["played"], 0)
        self.assertEqual(t["SURVIVED"], 0)


class TestPlayingClockOracle(unittest.TestCase):
    """The 'is it actually playing' oracle -- pure image logic, no editor."""

    def _img(self, size=(184, 22), color=(0, 0, 0)):
        Image = self._pil()
        return Image.new("RGB", size, color)

    def _pil(self):
        try:
            from PIL import Image
            return Image
        except ImportError:
            self.skipTest("Pillow not installed")

    def test_identical_captures_read_as_not_playing(self):
        """A stopped editor repaints the same clock -- must not read as playing,
        or the NOPLAY verdict could never fire."""
        a = self._img()
        self.assertFalse(probe.clock_advanced(a, a.copy()))

    def test_a_changed_digit_reads_as_playing(self):
        a = self._img()
        b = a.copy()
        for x in range(6):          # a few pixels of one bitmap-font digit
            for y in range(4):
                b.putpixel((170 + x, 8 + y), (255, 255, 255))
        self.assertTrue(probe.clock_advanced(a, b))

    def test_a_single_stray_pixel_does_not_read_as_playing(self):
        """Threshold exists so compression/AA noise cannot fake a tick."""
        a = self._img()
        b = a.copy()
        b.putpixel((100, 10), (255, 255, 255))
        self.assertFalse(probe.clock_advanced(a, b))

    def test_box_scales_with_window_size(self):
        """The box is in reference-window pixels; a differently sized window
        must still crop the clock rather than an arbitrary region."""
        ref = probe.scale_box(probe.PLAYING_TIME_BOX, probe.REF_WINDOW_SIZE)
        self.assertEqual(ref, probe.PLAYING_TIME_BOX)
        w, h = probe.REF_WINDOW_SIZE
        doubled = probe.scale_box(probe.PLAYING_TIME_BOX, (w * 2, h * 2))
        self.assertEqual(doubled,
                         tuple(v * 2 for v in probe.PLAYING_TIME_BOX))

    def test_clock_box_lies_inside_the_reference_window(self):
        l, t, r, b = probe.PLAYING_TIME_BOX
        w, h = probe.REF_WINDOW_SIZE
        self.assertTrue(0 <= l < r <= w and 0 <= t < b <= h)


if __name__ == "__main__":
    unittest.main()
