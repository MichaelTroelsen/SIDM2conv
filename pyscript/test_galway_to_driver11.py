"""Tests for sidm2.galway_to_driver11 (Stage A1 — Galway -> Driver 11 mapping).

Deterministic unit tests for the pure-data mapping, plus corpus-guarded
end-to-end checks on real Galway SIDs (skipped if the corpus isn't present).

Spec: docs/analysis/GALWAY_TO_DRIVER11_MAPPING.md
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.sid_player import FREQ_TABLE_LO, FREQ_TABLE_HI, NOTE_NAMES
from sidm2.galway_1stgen_extractor import GalwayEvent, GalwayInstrument
from sidm2.galway_to_driver11 import (
    calibrate_pitch_base, derive_tick, _dur_to_rows, _norm_waveform,
    build_instruments, build_track, galway_to_driver11,
    D11Instrument, D11Row, SF2_NOTE_MIN, SF2_NOTE_MAX, SF2_GATE_ON, SF2_GATE_OFF,
)
from sidm2.galway_driver11_emitter import (
    segment_track, unpack_sequence, emit_driver11_sf2)

CORPUS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "SID", "Galway_Martin")


def _ram_with_freq_table(lo_addr, hi_addr, base_offset=0, n=90):
    """Build a 64K RAM image whose LoFrq/HiFrq tables hold PAL note freqs such
    that Galway index i corresponds to PAL note (i + base_offset)."""
    ram = bytearray(0x10000)
    for i in range(n):
        ni = i + base_offset
        if 0 <= ni < 96:
            ram[(lo_addr + i) & 0xFFFF] = FREQ_TABLE_LO[ni]
            ram[(hi_addr + i) & 0xFFFF] = FREQ_TABLE_HI[ni]
    return ram


def _note(pitch, dur=4, tie=False):
    return GalwayEvent('note', pitch, dur, tie, 0, 0)


def _ev(kind, value=0, dur=0):
    return GalwayEvent(kind, 0, dur, False, value, 0)


class TestPitchCalibration(unittest.TestCase):
    def test_base_zero(self):
        ram = _ram_with_freq_table(0x4000, 0x4100, base_offset=0)
        self.assertEqual(calibrate_pitch_base(ram, 0x4000, 0x4100), 0)

    def test_base_offset(self):
        ram = _ram_with_freq_table(0x4000, 0x4100, base_offset=12)
        self.assertEqual(calibrate_pitch_base(ram, 0x4000, 0x4100), 12)

    def test_no_match_falls_back_to_zero(self):
        ram = bytearray(0x10000)            # all zero freqs → no PAL match
        self.assertEqual(calibrate_pitch_base(ram, 0x4000, 0x4100), 0)


class TestDeriveTick(unittest.TestCase):
    def test_wizball_like_ignores_rare_outliers(self):
        # Hundreds of even durations + a few odd outliers -> GCD of the common
        # ones (2), not 1.
        durs = [6] * 700 + [4] * 157 + [12] * 353 + [32] * 484 + [3, 5, 5, 9, 9]
        self.assertEqual(derive_tick(durs), 2)

    def test_commando_like_fast_tune(self):
        durs = [1] * 224 + [2] * 375 + [4] * 93 + [8] * 22 + [16] * 61
        self.assertEqual(derive_tick(durs), 1)

    def test_clamped_to_max(self):
        durs = [16] * 100 + [32] * 100        # gcd 16 -> clamped to 8
        self.assertEqual(derive_tick(durs), 8)

    def test_empty(self):
        self.assertEqual(derive_tick([]), 4)


class TestDurToRows(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_dur_to_rows(8, 2), 4)
        self.assertEqual(_dur_to_rows(6, 2), 3)

    def test_zero_is_one_row(self):
        self.assertEqual(_dur_to_rows(0, 2), 1)

    def test_min_one_row(self):
        self.assertEqual(_dur_to_rows(1, 4), 1)   # round(0.25)=0 -> clamped to 1

    def test_capped(self):
        self.assertLessEqual(_dur_to_rows(0xFF, 1), 64)


class TestWaveformNorm(unittest.TestCase):
    def test_pulse(self):
        self.assertEqual(_norm_waveform(0x41), 0x41)

    def test_sawtooth(self):
        self.assertEqual(_norm_waveform(0x21), 0x21)

    def test_pulse_priority_over_triangle(self):
        self.assertEqual(_norm_waveform(0x51), 0x41)   # pulse+tri -> pulse

    def test_default_when_no_waveform_bit(self):
        self.assertEqual(_norm_waveform(0x01), 0x41)


class TestBuildInstruments(unittest.TestCase):
    def _gi(self, ptr, ctrl, ad, sr):
        return GalwayInstrument(ptr=ptr, ctrl=ctrl,
                                attack=ad >> 4, decay=ad & 0xF,
                                sustain=sr >> 4, release=sr & 0xF,
                                vadsd=0, vrd=0,
                                waveforms=('pulse',))

    def test_maps_fields_and_ptr_index(self):
        gis = [self._gi(0x1000, 0x41, 0x06, 0xFA),
               self._gi(0x1010, 0x21, 0x09, 0x5D)]
        rows, wave, pulse, ptr_to_idx = build_instruments(gis)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0].ad, 0x06)
        self.assertEqual(rows[0].sr, 0xFA)
        self.assertEqual(ptr_to_idx, {0x1000: 0, 0x1010: 1})
        # each instrument gets a [wf,0] + [7F,loop] wave program
        self.assertEqual(wave[rows[0].wave_idx], (0x41, 0x00))
        self.assertEqual(wave[rows[1].wave_idx], (0x21, 0x00))

    def test_empty_yields_default_instrument(self):
        rows, wave, pulse, ptr_to_idx = build_instruments([])
        self.assertEqual(len(rows), 1)
        self.assertEqual(ptr_to_idx, {})
        self.assertTrue(wave)

    def test_pulse_instruments_get_a_pulse_program(self):
        # Regression: pulse ($41) voices are SILENT without a pulse-width
        # program. The song must carry a default pulse program and pulse
        # instruments must point at it (pulse_idx 0 = row 0).
        from sidm2.galway_to_driver11 import DEFAULT_PULSE_PROGRAM
        self.assertTrue(DEFAULT_PULSE_PROGRAM)
        self.assertEqual(DEFAULT_PULSE_PROGRAM[0][0] & 0xF0, 0x80)  # 'set pulse' cmd
        gis = [GalwayInstrument(ptr=0x1000, ctrl=0x41, attack=0, decay=6,
                                sustain=0xF, release=0xA, vadsd=0, vrd=0,
                                waveforms=('pulse',))]
        rows, _, _, _ = build_instruments(gis)
        self.assertEqual(rows[0].pulse_idx, 0)

    def test_caps_at_32(self):
        gis = [self._gi(0x1000 + i, 0x41, 0, 0) for i in range(40)]
        rows, _, _, _ = build_instruments(gis)
        self.assertEqual(len(rows), 32)


class TestBuildTrack(unittest.TestCase):
    def test_note_with_sustain_rows(self):
        # dur 8 at tick 2 -> 4 rows: 1 note + 3 '+++'. note byte = pitch+1.
        rows = build_track([_note(58, 8), _ev('end')], {}, base=0, tick=2)
        self.assertEqual(rows[0].note, 59)
        self.assertEqual([r.note for r in rows[1:]], [SF2_GATE_ON] * 3)

    def test_rest_emits_gate_off(self):
        rows = build_track([_ev('rest', dur=4), _ev('end')], {}, base=0, tick=2)
        self.assertEqual([r.note for r in rows], [SF2_GATE_OFF] * 2)

    def test_instrument_set_on_next_note_only_when_changed(self):
        evs = [_ev('instr', value=0x1000), _note(58), _note(60),
               _ev('instr', value=0x1010), _note(62), _ev('end')]
        rows = build_track(evs, {0x1000: 0, 0x1010: 1}, base=0, tick=4)
        note_rows = [r for r in rows if r.note <= SF2_NOTE_MAX]
        self.assertEqual(note_rows[0].instrument, 0)     # first note sets instr 0
        self.assertIsNone(note_rows[1].instrument)       # unchanged -> None
        self.assertEqual(note_rows[2].instrument, 1)     # changed -> instr 1

    def test_code_is_skipped_not_terminal(self):
        evs = [_note(58, 4), _ev('code', value=0x2000), _note(60, 4), _ev('end')]
        rows = build_track(evs, {}, base=0, tick=4)
        notes = [r.note for r in rows if SF2_NOTE_MIN <= r.note <= SF2_NOTE_MAX]
        self.assertEqual(notes, [59, 61])                # both notes survive (pitch+1)

    def test_desync_terminates(self):
        evs = [_note(58, 4), _ev('desync'), _note(60, 4)]
        rows = build_track(evs, {}, base=0, tick=4)
        notes = [r.note for r in rows if SF2_NOTE_MIN <= r.note <= SF2_NOTE_MAX]
        self.assertEqual(notes, [59])                    # stops at desync

    def test_pitch_base_applied_and_clamped(self):
        rows = build_track([_note(50, 4, tie=True)], {}, base=12, tick=4)
        self.assertEqual(rows[0].note, 63)               # 50 + 12 + 1
        self.assertTrue(rows[0].tie)
        # clamp high (110 + 12 + 1 = 123 > 0x6F)
        rows = build_track([_note(110, 4)], {}, base=12, tick=4)
        self.assertEqual(rows[0].note, SF2_NOTE_MAX)


@unittest.skipUnless(os.path.exists(os.path.join(CORPUS, "Wizball.sid")),
                     "Galway corpus not present")
class TestEndToEndCorpus(unittest.TestCase):
    def _song(self, name):
        from sidm2.sid_parser import SIDParser
        from sidm2.galway_1stgen_extractor import recover_channels
        p = os.path.join(CORPUS, name)
        h = SIDParser(p).parse_header()
        d = open(p, 'rb').read()[h.data_offset:]
        la = h.load_address
        if la == 0 and len(d) >= 2:
            la = d[0] | (d[1] << 8); d = d[2:]
        st = recover_channels(d, la, h.init_address,
                              songs=getattr(h, 'songs', 1) or 1,
                              start_song=getattr(h, 'start_song', 1) or 1)
        self.assertIsNotNone(st, f"recover_channels failed for {name}")
        return galway_to_driver11(st)

    def test_wizball(self):
        s = self._song("Wizball.sid")
        self.assertEqual(s.pitch_base, 0)
        self.assertEqual(s.tempo, 2)            # gcd of common durations
        self.assertEqual(s.subtune, 3)          # title tune
        self.assertEqual(len(s.instruments), 5)
        self.assertGreater(s.note_count, 1000)
        # V0 opens on A#4 (galway index 58 -> note byte 59 = index+1)
        first = next(r for r in s.tracks[0]
                     if SF2_NOTE_MIN <= r.note <= SF2_NOTE_MAX)
        self.assertEqual(NOTE_NAMES[first.note - 1], "A#4")

    def test_terra_cresta(self):
        s = self._song("Terra_Cresta.sid")
        self.assertEqual(s.pitch_base, 0)
        self.assertEqual(len(s.instruments), 9)
        self.assertGreater(s.note_count, 2000)

    def test_commando_fast_tune_tick_one(self):
        s = self._song("Commando_High-Score.sid")
        self.assertEqual(s.tempo, 1)            # genuinely fast (1/2-frame base)
        self.assertGreater(s.note_count, 500)


class TestPackerRoundTrip(unittest.TestCase):
    """pack (segment_track) -> unpack must reproduce the per-tick note stream
    (mirrors SF2II datasource_sequence.cpp Pack/Unpack)."""

    def _roundtrip(self, rows):
        flat = []
        for s in segment_track(rows):
            flat.extend(unpack_sequence(s))
        return flat

    def test_notes_sustains_and_offs(self):
        rows = [D11Row(note=0x18, instrument=1), D11Row(note=SF2_GATE_ON),
                D11Row(note=SF2_GATE_ON), D11Row(note=0x1A),
                D11Row(note=SF2_GATE_OFF), D11Row(note=SF2_GATE_OFF),
                D11Row(note=0x20, command=3), D11Row(note=SF2_GATE_ON)]
        self.assertEqual(self._roundtrip(rows), [r.note for r in rows])

    def test_long_hold_exceeds_duration_cap(self):
        # 40 sustain rows must round-trip even though one duration byte caps at 15
        rows = [D11Row(note=0x20)] + [D11Row(note=SF2_GATE_ON)] * 40
        self.assertEqual(self._roundtrip(rows), [r.note for r in rows])

    def test_long_track_segments_under_size_cap(self):
        rows = [D11Row(note=(0x01 + (i % 0x6E)), instrument=(i % 32))
                for i in range(2000)]
        seqs = segment_track(rows)
        self.assertGreater(len(seqs), 1)               # had to split
        self.assertTrue(all(len(s) < 0xFF for s in seqs))
        self.assertEqual(self._roundtrip(rows), [r.note for r in rows])

    def test_empty_track(self):
        self.assertEqual(segment_track([]), [bytes([0x7F])])


@unittest.skipUnless(os.path.exists(os.path.join(CORPUS, "Wizball.sid")),
                     "Galway corpus not present")
class TestEmitterCorpus(unittest.TestCase):
    def _song(self, name):
        from sidm2.sid_parser import SIDParser
        from sidm2.galway_1stgen_extractor import recover_channels
        p = os.path.join(CORPUS, name)
        h = SIDParser(p).parse_header()
        d = open(p, 'rb').read()[h.data_offset:]
        la = h.load_address
        if la == 0 and len(d) >= 2:
            la = d[0] | (d[1] << 8); d = d[2:]
        st = recover_channels(d, la, h.init_address,
                              songs=getattr(h, 'songs', 1) or 1,
                              start_song=getattr(h, 'start_song', 1) or 1)
        return galway_to_driver11(st)

    def test_wizball_emits_valid_driver11_sf2(self):
        from sidm2.models import SF2DriverInfo
        from sidm2 import sf2_parser
        song = self._song("Wizball.sid")
        sf2 = emit_driver11_sf2(song)
        # re-parses as a Driver 11 file
        di = SF2DriverInfo()
        la = sf2_parser.parse_sf2_blocks(bytearray(sf2), di)
        self.assertEqual(la, 0x0D7E)
        self.assertEqual(di.track_count, 3)
        # seq0 pointer resolves and its notes match the song's V0 melody
        off = lambda a: a - la + 2
        s0 = sf2[off(di.sequence_ptrs_lo)] | (sf2[off(di.sequence_ptrs_hi)] << 8)
        seq0 = sf2[off(s0):off(s0) + 0x100]
        emitted = [n for n in unpack_sequence(bytes(seq0))
                   if SF2_NOTE_MIN <= n <= SF2_NOTE_MAX][:12]
        song_v0 = [r.note for r in song.tracks[0]
                   if SF2_NOTE_MIN <= r.note <= SF2_NOTE_MAX][:12]
        self.assertEqual(emitted, song_v0)
        # pulse program present in the file (so pulse voices aren't silent)
        pa = di.table_addresses['Pulse']['addr']
        self.assertEqual(sf2[off(pa)] & 0xF0, 0x80)    # row 0 col 0 = 'set pulse'


if __name__ == "__main__":
    unittest.main()
