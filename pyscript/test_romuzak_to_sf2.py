"""Tests for the ROMUZAK V6.3 -> SF2 converter (bin/romuzak_to_sf2.py).

Fast (no siddump): validates the relocation-safe table finder, the track/sector
decode against known Delirious data, and that the converter emits a parseable SF2.
The full note-for-note check vs siddump is documented in docs/players/ROMUZAK.md.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'bin'))

DELIRIOUS = os.path.join(ROOT, 'SID', 'Fun_Fun', 'Delirious_9_tune_1.sid')
ROAD = os.path.join(ROOT, 'SID', 'Fun_Fun', 'Road_of_Excess_end.sid')
pytestmark = pytest.mark.skipif(not os.path.exists(DELIRIOUS), reason="corpus SID missing")

import romuzak_to_sf2 as R  # noqa: E402


def _rmz():
    d, la = R.load_sid(DELIRIOUS)
    return R.RMZ(d, la), la


def test_find_tables_delirious():
    rmz, la = _rmz()
    assert la == 0x2BFE
    assert rmz.track_ptrs == 0x3640
    assert rmz.sect_ptrs == 0x3676
    assert rmz.sound_tbl == 0x36F6          # sector_ptrs + 0x80
    assert rmz.drum_tbl == 0x2D60


def test_orderlist_structure():
    rmz, _ = _rmz()
    # track0 (lead): SEC15, then sector 00 (pause) repeated 12x — the silent intro
    ol0 = rmz._orderlist(0)
    assert ol0[0][0] == 0x15
    assert [e[0] for e in ol0[1:13]] == [0x00] * 12


def test_sector_decode_notes():
    rmz, _ = _rmz()
    # sector 13 is "a1 63 18 0c ..." = SND.01, DUR.03, note $18, note $0c, ...
    ev = rmz._sector(rmz._u16(rmz.sect_ptrs + 0x13 * 2), 0, 0)
    notes = [n for n, dur, ins, rest in ev if not rest]
    assert notes[:4] == [0x18, 0x0C, 0x1A, 0x1B]   # 24, 12, 26, 27 (matches siddump)
    assert ev[0][2] == 1                            # instrument = SND.01


def test_base_is_fixed_zero():
    # ROMUZAK note values are SF2 chromatic semitones -> base 0 for every tune
    # (the old median-centering left Delirious at 0 by luck but Road at +2).
    rmz, _ = _rmz()
    assert R.calibrate_base(rmz) == 0


def test_tempo_from_tick_divider():
    # Per-tune tempo derived from the player's tick-divider reload constant:
    # Delirious reload $03 (4-frame tick) -> 5; Road reload $02 (3-frame tick) -> 4.
    d, _ = R.load_sid(DELIRIOUS)
    assert R.find_tempo(d) == 5


@pytest.mark.skipif(not os.path.exists(ROAD), reason="Road SID missing")
def test_road_tempo_differs():
    d, la = R.load_sid(ROAD)
    assert la == 0x2C00
    assert R.find_tempo(d) == 4
    assert R.calibrate_base(R.RMZ(d, la)) == 0


def test_emit_parseable_sf2():
    from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo
    rmz, la = _rmz()
    base = R.calibrate_base(rmz)
    ir, wt, pt = R.build_instruments(rmz)
    sil = R._append_silent_instrument(ir, wt, pt)
    seqs, ols = R.build_structured(rmz, base, sil)
    assert len(seqs) > 0 and all(len(o) > 0 for o in ols)
    from sidm2.galway_to_driver11 import GalwayDriver11Song
    from sidm2.galway_driver11_emitter import emit_driver11_sf2
    song = GalwayDriver11Song(instruments=ir, wave_table=wt, pulse_table=pt,
                              tracks=[], tempo=5, pitch_base=base, subtune=0)
    sf2 = emit_driver11_sf2(song, sequences=seqs, orderlists=ols)
    info = SF2DriverInfo()
    assert parse_sf2_blocks(sf2, info) is not None    # valid SF2
