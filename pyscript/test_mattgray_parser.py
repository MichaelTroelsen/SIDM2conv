"""Tests for the Matt Gray parser and its Stage A Driver 11 transpile.

The reference file is the HVSC Driller rip, whose player is the one Matt Gray
build with an independently corroborated memory map (the Codebase64 rough
disassembly agrees with the PSID header's init/play exactly).  Tests that need
it are skipped when HVSC is not present, so the suite still runs on a bare
checkout; the pure-logic tests below run everywhere.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.mattgray_parser import (  # noqa: E402
    INSTR_SIZE, NUM_NOTES, MattGrayError, MattGrayInstrument, MattGrayParser,
    MattGraySong, parse_sid, simulate,
)

HVSC = os.environ.get(
    "HVSC_ROOT",
    r"C:\Users\mit\Downloads\HVSC_85-all-of-them\C64Music")
DRILLER = os.path.join(HVSC, "MUSICIANS", "G", "Gray_Matt", "Driller.sid")

needs_driller = pytest.mark.skipif(
    not os.path.exists(DRILLER), reason="HVSC Driller.sid not available")


# --------------------------------------------------------------------------
# Pure-logic tests (no HVSC needed)
# --------------------------------------------------------------------------

def test_instrument_pulse_width_nibble_order():
    """A0[0] packs the pulse as hi-nibble -> $d402 lo, lo-nibble -> $d403 hi.

    Instrument 1 of Driller has A0[0] = $90, and the real player programs
    pulse $090 (confirmed against siddump frame 1).
    """
    ins = MattGrayInstrument(index=0, a0=[0x90, 0, 0, 0, 0, 0, 0, 0],
                             a1=[0] * 8)
    assert ins.pulse_width == 0x090


def test_instrument_flag_accessors():
    a0 = [0x00, 0x41, 0xFE, 0x0D, 0x25, 0x37, 0x40, 0x07]
    a1 = [0x50, 0x02, 0x81, 0x11, 0x01, 0x03, 0x00, 0x00]
    ins = MattGrayInstrument(index=3, a0=a0, a1=a1)
    assert ins.waveform == 0x41
    assert ins.ad == 0xFE and ins.sr == 0x0D
    assert ins.pulse_sweep == 0x25
    assert ins.arp_ctrl == 0x37
    assert ins.attack_waveform == 0x40
    assert ins.flags == 0x07
    assert ins.slide_rate == 0x50
    assert ins.slide_period == 0x02
    assert ins.auto_effect == 0x01
    assert ins.drum_len == 0x03
    assert len(ins.raw) == 2 * INSTR_SIZE


def test_frames_per_tick_is_tempo_plus_one():
    """Measured, not assumed: Driller's tempo 3 gives onsets 4 frames apart."""
    song = MattGraySong(load_addr=0, init_addr=0, play_addr=0, play_voice=0,
                        subtune=1, tempo=3)
    assert song.frames_per_tick == 4
    song.tempo = 0
    assert song.frames_per_tick == 1


def test_freq_out_of_range_is_zero():
    song = MattGraySong(load_addr=0, init_addr=0, play_addr=0, play_voice=0,
                        subtune=1, tempo=3,
                        freq_lo=[0x0C], freq_hi=[0x01])
    assert song.freq(0) == 0x010C
    assert song.freq(5) == 0
    assert song.freq(-1) == 0


def test_rejects_non_matt_gray_play_shim():
    """music_play must be the 3x 'ldx #X / jsr play_voice' shim."""
    data = bytes([0xEA] * 64)          # all NOPs
    with pytest.raises(MattGrayError):
        MattGrayParser(data, 0x1000, 0x1000, 0x1000)


# --------------------------------------------------------------------------
# Driller reference file
# --------------------------------------------------------------------------

@needs_driller
def test_driller_tables_resolve_to_known_addresses():
    """Backward dataflow from the code operands must find the documented map."""
    song = parse_sid(DRILLER, subtune=1)
    assert song.play_voice == 0x0900
    assert song.table_addrs["frq_lo"] == 0x0D53
    assert song.table_addrs["frq_hi"] == 0x0DB3
    assert song.table_addrs["instr_a0"] == 0x0EA5
    assert song.table_addrs["instr_a1"] == 0x0F55
    assert song.table_addrs["pattern_lobytes"] == 0x157F
    assert song.table_addrs["tune_tempo"] == 0x1054


@needs_driller
def test_driller_shape():
    song = parse_sid(DRILLER, subtune=1)
    assert len(song.patterns) == 42
    assert len(song.instruments) == 22
    assert song.tempo == 3
    assert len(song.freq_lo) == NUM_NOTES
    assert len(song.freq_hi) == NUM_NOTES
    # every track ends with a $ff loop or $fe stop terminator
    for trk in song.tracks:
        assert trk[-1] in (0xFF, 0xFE)


@needs_driller
def test_driller_first_notes_match_the_real_player():
    """Frame 1 values cross-checked against a siddump of the real rip.

    voice 1 plays note $23 on instrument 1 -> $07e9; voice 2 note $17 -> $03f4.
    """
    song = parse_sid(DRILLER, subtune=1)
    assert song.freq(0x23) == 0x07E9
    assert song.freq(0x17) == 0x03F4
    assert song.instruments[1].a0 == [0x90, 0x41, 0xFE, 0x0D, 0x25, 0x00, 0x40, 0x02]

    ev = simulate(song, frames=600)
    assert ev[0][0].frame == 1 and ev[0][0].note == 0x23 and ev[0][0].instrument == 1
    assert ev[1][0].frame == 1 and ev[1][0].note == 0x17 and ev[1][0].instrument == 1


@needs_driller
def test_driller_onset_spacing_is_256_frames_for_duration_3f():
    """Duration $3f = 64 ticks x 4 frames; measured onsets are 1, 257, 513..."""
    song = parse_sid(DRILLER, subtune=1)
    ev = simulate(song, frames=2000)
    frames = [e.frame for e in ev[0][:5]]
    assert frames == [1, 257, 513, 769, 1025]
    assert all(e.duration == 0x3F for e in ev[0][:5])


@needs_driller
def test_pattern_slide_command_is_attached_to_the_following_note():
    """Pattern 5 is 'fa 0e fd 3f 2f 2b 2e fc 20 2a ff': the $fc 20 applies to
    the $2a that follows it, and to nothing else."""
    song = parse_sid(DRILLER, subtune=1)
    pat5 = song.patterns[5]
    assert pat5[:11] == [0xFA, 0x0E, 0xFD, 0x3F, 0x2F, 0x2B, 0x2E,
                         0xFC, 0x20, 0x2A, 0xFF]
    ev = simulate(song, frames=400000, stop_on_loop=True)
    slid = [e for v in ev for e in v if e.pattern == 5 and e.slide is not None]
    assert slid, "expected the $fc 20 slide to be recorded on a note"
    for e in slid:
        assert e.note == 0x2A
        assert e.slide == (2, 0x20)
    # the notes before it in the same pattern carry no slide
    unslid = [e for v in ev for e in v
              if e.pattern == 5 and e.note in (0x2F, 0x2B, 0x2E)]
    assert unslid and all(e.slide is None for e in unslid)


@needs_driller
def test_all_three_voices_loop_together():
    """Driller's three tracks have different entry counts (117/82/109) but are
    written to wrap at the same tick -- a good internal consistency check."""
    song = parse_sid(DRILLER, subtune=1)
    ev = simulate(song, frames=400000, stop_on_loop=True)
    ends = [max(e.tick + e.duration + 1 for e in ev[v]) for v in range(3)]
    assert ends[0] == ends[1] == ends[2] == 8320


@needs_driller
def test_note_zero_is_a_rest():
    song = parse_sid(DRILLER, subtune=1)
    ev = simulate(song, frames=400000, stop_on_loop=True)
    rests = [e for v in ev for e in v if e.note == 0]
    assert rests, "Driller does contain rests"
    assert all(e.is_rest for e in rests)


@needs_driller
def test_subtune_out_of_range_is_rejected():
    with pytest.raises(MattGrayError):
        parse_sid(DRILLER, subtune=99)


# --------------------------------------------------------------------------
# Stage A transpile
# --------------------------------------------------------------------------

@needs_driller
def test_stage_a_sequences_round_trip_exactly():
    """Packed Driver 11 sequences must unpack back to the row grid byte-exactly
    and stay under SF2II's Unpack buffer cap."""
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bin"))
    from mattgray_to_sf2 import build_instruments, build_tracks, calibrate_base
    from sidm2.galway_driver11_emitter import (
        _SEQ_EVENT_LIMIT, segment_track, unpack_sequence)

    song = parse_sid(DRILLER, subtune=1)
    ev = simulate(song, frames=400000, stop_on_loop=True)
    base = calibrate_base(song)
    instr_rows, _wt, _pt, _ft = build_instruments(song, base)
    tracks, _clipped = build_tracks(song, ev, base, len(instr_rows), 0, 4000)

    total_seqs = 0
    for rows in tracks:
        seqs = segment_track(rows)
        total_seqs += len(seqs)
        flat = []
        for sq in seqs:
            span = unpack_sequence(sq)
            assert len(span) <= _SEQ_EVENT_LIMIT
            flat.extend(span)
        assert flat == [r.note for r in rows]
    assert total_seqs <= 120           # SF2II sequence-slot cap


# --- R20: part capacity is MEASURED per song, not a hardcoded frame count ----
# The old code split on a flat MAX_PART_FRAMES=24_000 "SF2II memory wall" whose
# derivation was never found and does not follow from the format: nothing in a
# Driver 11 file grows with TIME (every table is fixed-size; the sequence region
# is a fixed 128 x 256-byte slots), so capacity is a function of event DENSITY.
# Measured: Driller's whole 8320-row / 665.6s song is ONE valid module at 57/128
# sequence slots, top $61CF against the $D000 wall.

def test_default_ceiling_no_longer_forces_drillers_split():
    """Driller is 33280 frames; the old 24_000 default split it into two."""
    import importlib
    M = importlib.import_module("mattgray_to_sf2")
    assert M.MAX_PART_FRAMES > 33280,         "default window ceiling must not re-split Driller"


def test_convert_probes_both_binding_limits():
    """Guards against someone reinstating a duration-based split: the
    sequence-slot count and the $D000 top are the only two things that actually
    bound one module."""
    import importlib, inspect
    M = importlib.import_module("mattgray_to_sf2")
    src = inspect.getsource(M.convert)
    assert "SEQ_SLOTS" in src
    assert "0xD000" in src
    assert "_part_fits" in src
