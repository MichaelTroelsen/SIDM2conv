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
    # Per-tune tempo = reload (the driver plays tempo+1 frames/row, matching the
    # (reload+1)-frame tick): Delirious reload $03 -> tempo 3; Road $02 -> 2.
    d, _ = R.load_sid(DELIRIOUS)
    assert R.find_tempo(d) == 3


@pytest.mark.skipif(not os.path.exists(ROAD), reason="Road SID missing")
def test_road_tempo_differs():
    d, la = R.load_sid(ROAD)
    assert la == 0x2C00
    assert R.find_tempo(d) == 2
    assert R.calibrate_base(R.RMZ(d, la)) == 0


def test_silent_intro_sector_duration():
    # sector 00 ("8F FF") is a PSE of 15 -> 16 rows, the silent-intro unit
    # (regression for the old cur_dur=1 bug that made it a single row).
    rmz, _ = _rmz()
    ev = rmz._sector(rmz._u16(rmz.sect_ptrs + 0), 0, 0)
    assert len(ev) == 1 and ev[0][3] is True       # one rest event
    assert ev[0][1] == 16                           # 15 + 1 rows


def test_voices_equal_length():
    # corrected durations make the two accompaniment voices exactly equal-length
    # (synced tracks); the old decode left them ~124 rows apart.
    rmz, _ = _rmz()

    def total(v):
        return sum(sum(r[1] for r in rmz._sector(rmz._u16(rmz.sect_ptrs + s * 2),
                                                  nt, st))
                   for s, nt, st in rmz._orderlist(v))
    assert total(1) == total(2)


def test_drum_value_is_freq_hibyte():
    # a drum table value is the freq HIGH byte -> nearest PAL semitone, NOT a
    # semitone directly. B4=2 [$40,$08,$06,$04] -> B-5,~C-3,G-2,~C#2 (the osc3 trace).
    assert R._drum_semitone(0x40) == 71            # B-5
    assert R._drum_semitone(0x06) == 31            # G-2
    assert R._drum_semitone(0x40) != 0x40          # not the raw value


def test_arp_plays_root_first():
    # arp data 0C 07 03 00 ([12,7,3,0], root last) plays rotated right -> [0,12,7,3]
    rmz, _ = _rmz()
    assert rmz.sounds[7] == (0x0C, 0x07, 0x03, 0x00, 0x0C, 0x07, 0x03, 0x00)
    ir, wt, pt = R.build_instruments(rmz)
    wrow = ir[6].wave_idx                            # snd 06 = ARP (B7 $42)
    offs = [wt[wrow + k][1] & 0x7F for k in range(4)]
    assert offs == [0, 12, 7, 3]


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
# ---------------------------------------------------------------------------
# the two open B7 bits -- pinned as a CENSUS, because one of them is a claim
# about absence and absence is what goes stale silently
# ---------------------------------------------------------------------------

def _rmz_corpus():
    """Every SID/Fun_Fun file that decodes to a ROMUZAK sound bank."""
    import glob
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "SID", "Fun_Fun", "*.sid"))):
        try:
            d, la = R.load_sid(f)
            r = R.RMZ(d, la)
        except Exception:                              # noqa: BLE001
            continue
        real = [s for s in r.sounds if s != (0xFF,) * 8]
        if real:
            out.append((os.path.basename(f), r, real))
    return out


@pytest.mark.skipif(not os.path.isdir(os.path.join(ROOT, "SID", "Fun_Fun")),
                    reason="SID/Fun_Fun not available")
def test_B7_bit5_FILTER_is_UNEXERCISED_by_this_corpus():
    """THE CLAIM THIS PINS IS AN ABSENCE, which is why it needs a test.

    build_instruments' docstring says bit5 is left undecoded because NO file
    sets it -- 0 of 64 sounds. An absence is exactly the kind of statement that
    rots without anyone noticing: add one ROMUZAK rip that uses the filter and
    the docstring becomes wrong silently. If this test fails, the bit is now
    exercised and the docstring must be rewritten, not the assertion relaxed.
    """
    corpus = _rmz_corpus()
    assert len(corpus) == 2, [c[0] for c in corpus]
    total = sum(len(real) for _, _, real in corpus)
    assert total == 64, total
    set5 = [(name, i) for name, _, real in corpus
            for i, s in enumerate(real) if s[7] & 0x20]
    assert set5 == [], (
        "B7 bit5 (FILTER) is now SET somewhere -- it is no longer unexercised, "
        "so decode it instead of leaving the docstring's count standing: %s" % set5)


@pytest.mark.skipif(not os.path.isdir(os.path.join(ROOT, "SID", "Fun_Fun")),
                    reason="SID/Fun_Fun not available")
def test_B7_bit0_DRUM_IS_exercised_and_never_appears_without_bit3():
    """The other direction, and the reason bit0 must NOT be modelled blind.

    Four sounds set bit0, and every one of them also sets bit3 ($09), so this
    corpus cannot attribute behaviour to either bit alone. Anyone decoding the
    drum path has to decode both or state which one the evidence isolates.
    """
    corpus = _rmz_corpus()
    drums = [(name, s[7]) for name, _, real in corpus
             for s in real if s[7] & 0x01]
    assert len(drums) == 4, drums
    assert all(b7 & 0x08 for _, b7 in drums), (
        "bit0 now appears WITHOUT bit3 -- the two are separable after all: %s"
        % drums)
