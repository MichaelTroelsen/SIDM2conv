#!/usr/bin/env python3
"""Tests for the Future Composer Stage-B shim (bin/build_fc_native_song.py).

Pure/synthetic -- these never assemble a driver or run siddump (a real corpus
build is minutes). They pin the parts of the shim that silently corrupt a build
if wrong: the two independent `+1`s in FC's timing model, instrument-0
threading, and rest mapping.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bin"))

from sidm2.fc_parser import FCSong, FCNote, FCInstrument, NUM_NOTES  # noqa: E402


def _song(voices, speed=1, n_instr=4):
    """A minimal FCSong: freq table = index*0x10 so freq(i) is checkable."""
    return FCSong(
        load=0x1800, base=0x1800, speed=speed,
        freq_lo=[(i * 0x10) & 0xFF for i in range(NUM_NOTES)],
        freq_hi=[((i * 0x10) >> 8) & 0xFF for i in range(NUM_NOTES)],
        instruments=[FCInstrument(index=i, pulse=0, waveform=0x41,
                                  ad=0x0A + i, sr=0xF0 + i, unused=0,
                                  vibrato=0, arp=0, mctrl=0)
                     for i in range(n_instr)],
        voices=voices, voice_blocks=[[] for _ in voices])


def _shim(voices, speed=1, n_instr=4):
    import build_fc_native_song as B
    return B.FCShim(_song(voices, speed, n_instr))


class TestTimingModel(unittest.TestCase):
    """FC has TWO independent +1s and both are load-bearing (see
    docs/players/FUTURECOMPOSER.md "Timing")."""

    def test_frames_per_tick_is_speed_plus_one(self):
        self.assertEqual(_shim([[], [], []], speed=1).frames_per_tick, 2)
        self.assertEqual(_shim([[], [], []], speed=0).frames_per_tick, 1)
        self.assertEqual(_shim([[], [], []], speed=5).frames_per_tick, 6)

    def test_event_duration_is_dur_plus_one_ticks(self):
        """A duration byte D runs D..0..-1 = D+1 ticks. Dropping this makes
        dur5:dur2 read 5:2 instead of the true 6:3 -- relative timing wrong."""
        sh = _shim([[FCNote(note=10, dur=5, instr=1),
                     FCNote(note=12, dur=2, instr=1)], [], []])
        self.assertEqual([e.dur for e in sh.voices[0]], [6, 3])

    def test_tick_frame_conversions_round_trip(self):
        sh = _shim([[], [], []], speed=1)
        self.assertEqual(sh.tick_to_frame(10), 20)
        self.assertEqual(sh.frame_to_tick(20), 10)
        self.assertEqual(sh.frame_to_tick(21), 10)      # floor, not round
        self.assertEqual(sh.frame_to_tick(-5), 0)       # never negative

    def test_zero_duration_never_produces_a_zero_length_event(self):
        """dur=0 is legal FC (1 tick). A 0-tick event would make the sequencer
        emit nothing and desync every later note in the voice."""
        sh = _shim([[FCNote(note=10, dur=0, instr=1)], [], []])
        self.assertEqual(sh.voices[0][0].dur, 1)


class TestInstrumentThreading(unittest.TestCase):
    def test_instrument_zero_carries_the_previous_sound(self):
        """FC instrument 0 means "no change" -- the player carries the current
        sound. sf2_to_fc records that getting this wrong resets instruments to
        0 mid-song."""
        sh = _shim([[FCNote(note=10, dur=1, instr=3),
                     FCNote(note=11, dur=1, instr=0),
                     FCNote(note=12, dur=1, instr=0),
                     FCNote(note=13, dur=1, instr=2)], [], []])
        self.assertEqual([e.instr for e in sh.voices[0]], [3, 3, 3, 2])

    def test_threading_is_per_voice_not_global(self):
        sh = _shim([[FCNote(note=10, dur=1, instr=3)],
                    [FCNote(note=10, dur=1, instr=0)],
                    []])
        self.assertEqual(sh.voices[0][0].instr, 3)
        self.assertEqual(sh.voices[1][0].instr, 0)   # voice 1 never set one

    def test_leading_instrument_zero_stays_zero(self):
        sh = _shim([[FCNote(note=10, dur=1, instr=0)], [], []])
        self.assertEqual(sh.voices[0][0].instr, 0)


class TestRests(unittest.TestCase):
    def test_note_at_or_above_96_becomes_a_rest(self):
        """FC encodes a rest as a freq-table index past the 96-entry table."""
        sh = _shim([[FCNote(note=NUM_NOTES, dur=3, instr=1),
                     FCNote(note=108, dur=3, instr=1),
                     FCNote(note=40, dur=3, instr=1)], [], []])
        self.assertEqual([e.rest for e in sh.voices[0]], [True, True, False])

    def test_a_rest_keeps_its_duration(self):
        """The long silent intro IS the point of building FC natively -- a rest
        that loses its length shifts the whole voice early."""
        sh = _shim([[FCNote(note=108, dur=47, instr=0)], [], []])
        self.assertEqual(sh.voices[0][0].dur, 48)
        self.assertTrue(sh.voices[0][0].rest)


class TestFreqTable(unittest.TestCase):
    def test_note_freq_uses_the_songs_own_table(self):
        """PLAYBOOK: always emit the player's OWN freq table; the generic PAL
        table is a semitone off and detuned (Stage A hit exactly this)."""
        sh = _shim([[], [], []])
        self.assertEqual(sh.note_freq(3), 0x30)
        self.assertEqual(sh.note_freq(10), 0xA0)

    def test_out_of_range_note_freq_is_zero_not_an_exception(self):
        sh = _shim([[], [], []])
        self.assertEqual(sh.note_freq(NUM_NOTES), 0)
        self.assertEqual(sh.note_freq(255), 0)


class TestInstrumentRecord(unittest.TestCase):
    def test_ad_sr_come_from_the_fc_record(self):
        sh = _shim([[], [], []], n_instr=3)
        rec = sh.instrument(2)
        self.assertEqual((rec['ad'], rec['sr']), (0x0C, 0xF2))
        self.assertEqual(rec['waveform'], 0x41)

    def test_out_of_range_instrument_falls_back_without_raising(self):
        """A decode can reference an instrument index the table doesn't have;
        the build must not die mid-corpus."""
        sh = _shim([[], [], []], n_instr=2)
        rec = sh.instrument(31)
        self.assertIn('ad', rec)
        self.assertEqual(rec['waveform'], 0x41)

    def test_zero_waveform_falls_back_to_pulse(self):
        song = _song([[], [], []])
        song.instruments[1].waveform = 0
        import build_fc_native_song as B
        self.assertEqual(B.FCShim(song).instrument(1)['waveform'], 0x41)


class TestVoiceBlocks(unittest.TestCase):
    def test_returns_one_flat_block_per_nonempty_voice(self):
        sh = _shim([[FCNote(note=10, dur=1, instr=1)], [], []])
        self.assertEqual(len(sh._voice_blocks(0)), 1)
        self.assertEqual(sh._voice_blocks(0)[0][0], 0)
        self.assertEqual(sh._voice_blocks(1), [])        # empty voice -> no block


class TestSpan(unittest.TestCase):
    def test_span_is_ticks_times_frames_per_tick(self):
        import build_fc_native_song as B
        sh = _shim([[FCNote(note=10, dur=9, instr=1)] * 4, [], []], speed=1)
        # 4 events x 10 ticks = 40 ticks, fpt 2 -> 80 frames
        self.assertEqual(B.song_span_frames(sh), 80)

    def test_mismatched_voice_spans_use_the_longest(self):
        """All three FC voices normally span the same tick count (a good
        internal consistency check); a mismatch must not silently truncate."""
        import build_fc_native_song as B
        sh = _shim([[FCNote(note=10, dur=9, instr=1)],
                    [FCNote(note=10, dur=19, instr=1)], []], speed=1)
        self.assertEqual(B.song_span_frames(sh), 40)     # 20 ticks * 2


if __name__ == "__main__":
    unittest.main()
