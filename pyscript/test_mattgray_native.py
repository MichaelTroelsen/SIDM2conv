"""Matt Gray Stage B: the native trace-driven build.

These pin the shim contract and the two decisions that were made by measuring
rather than by taste. They do not build SF2s -- that needs siddump and takes
minutes per subtune; the corpus sweep in docs/players/MATTGRAY.md is the
fidelity evidence.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

LN2 = os.path.join(ROOT, "SID", "Gray_Matt", "Last_Ninja_2.sid")
needs_sid = pytest.mark.skipif(not os.path.exists(LN2), reason="HVSC file absent")


def _shim(sub=0):
    import build_mattgray_native_song as MG
    from sidm2.mattgray_parser import parse_sid
    return MG, MG.MattGrayShim(parse_sid(LN2, subtune=sub))


@needs_sid
def test_shim_exposes_the_mon_tick_protocol():
    MG, sh = _shim(0)
    assert sh.frames_per_tick == 6            # subtune 0 is tempo 5
    assert sh.tick_to_frame(10) == 60
    assert sh.frame_to_tick(60) == 10
    assert len(sh.voices) == 3
    assert any(sh.voices)


@needs_sid
def test_durations_come_from_the_walk_not_the_duration_byte():
    """A sticky duration byte is re-used by the sequencer, so the gap to the
    next event is the truth. Events must tile without overlap."""
    MG, sh = _shim(0)
    for v in range(3):
        evs = sh.events[v]
        for i in range(len(evs) - 1):
            gap = evs[i + 1].tick - evs[i].tick
            assert sh.voices[v][i].dur == max(1, gap), (v, i)


@needs_sid
def test_note_freq_uses_the_players_own_table_and_extrapolates_past_it():
    """Never the generic PAL table, and never a read off the end of it."""
    MG, sh = _shim(0)
    n = len(sh.song.freq_lo)
    for k in range(0, n, 7):
        assert sh.note_freq(k) == sh.song.freq(k)
    # past the table: doubling, clamped, and strictly beyond the last real entry
    assert sh.note_freq(n) >= sh.song.freq(n - 12)
    assert sh.note_freq(200) <= 0xFFFF
    assert sh.note_freq(-1) == 0


@needs_sid
def test_a_truncated_decode_is_refused_not_built():
    """Subtune 7 is the only one of the 13 whose pattern the relocating copy
    cuts short, and the only one that renders catastrophically (voice 0 at
    1.9% audible against 92-100% elsewhere). Emitting it silently is the
    failure mode this refusal exists to prevent."""
    from sidm2.mattgray_parser import parse_sid
    trunc = [s for s in range(13) if parse_sid(LN2, subtune=s).truncated_patterns]
    assert trunc == [7], f"expected only subtune 7 truncated, got {trunc}"

    import subprocess
    r = subprocess.run([sys.executable, os.path.join(ROOT, "bin",
                                                     "build_mattgray_native_song.py"),
                        LN2, "auto", "7"],
                       capture_output=True, text=True, cwd=ROOT, timeout=600)
    assert "REFUSED" in r.stdout, r.stdout[-400:]
    assert r.returncode != 0


@needs_sid
def test_snap_gate_is_off_and_that_was_measured():
    """HardTrack wants gate-snapping; Matt Gray does not.

    Chosen on the whole corpus, not one file: over 12 subtunes (n=172,745
    audible frames) snap_gate=False scores 98.16% against True's 97.87%, is
    better on 5 voices and worse on NONE, and takes voices at exactly 100.0%
    from 15/36 to 16/36. A strictly dominant result, so the default is off --
    and MG_SNAP=1 restores the other setting for anyone re-checking.
    """
    import build_mattgray_native_song as MG
    assert MG.MattGrayShim.snap_gate is False
    assert "MG_SNAP" in open(
        os.path.join(ROOT, "bin", "build_mattgray_native_song.py"),
        encoding="utf-8").read()


@needs_sid
def test_the_shim_does_not_model_the_synth_engine():
    """Stage B's whole point: the slide/arp/PWM/drum engines are CAPTURED.

    docs/players/MATTGRAY.md listed all four as Stage B work to reverse
    engineer. If a future change starts modelling them in the shim, this
    fails and the docstring explains why that is the wrong direction.
    """
    import build_mattgray_native_song as MG
    src = open(MG.__file__, encoding="utf-8").read()
    for banned in ("arp_table", "slide_rate", "pulse_sweep", "drum_len"):
        assert banned not in src, (
            f"{banned} appears in the Stage B shim -- the synth side is "
            f"captured per frame, not modelled")


# -- the rest merge (the rung-4 gate-off defect) ---------------------------

class _FakeShim:
    """The three things merge_sounding_rests touches, and nothing else."""
    onset_delay = 0

    def __init__(self, voices, fpt=6):
        self.voices = voices
        self._fpt = fpt

    def tick_to_frame(self, t):
        return t * self._fpt


def _ev(dur, rest, note=48):
    from sidm2.mon_parser import MONEvent
    return MONEvent(note=(0 if rest else note), dur=dur, instr=1,
                    retrig=not rest, rest=rest)


def _frames(n, wf, freq):
    """n frames of one fill-forwarded state on every voice."""
    return [({v: {'freq': freq, 'wf': wf, 'pul': 0} for v in range(3)}, None)
            for _ in range(n)]


def test_a_rest_the_original_sounds_through_is_merged():
    """A rest emits bare gate-off rows with no wave/pulse/FM program, so the
    pitch FREEZES; Matt Gray's arpeggio keeps stepping through the release.
    Measured on Last_Ninja_2 sub 0: all 313 sounding gate-off runs inside a
    NOTE were byte-exact and all 276 inside a REST were wrong."""
    import build_mattgray_native_song as MG
    sh = _FakeShim([[_ev(4, False), _ev(2, False)] for _ in range(3)])
    sh.voices[0] = [_ev(4, False), _ev(2, True)]
    # gate off ($10 = triangle, bit0 clear) and advancing -> audible release
    n, s = MG.merge_sounding_rests(sh, _frames(64, 0x10, 0x2000))
    assert n == 1 and s == 2
    assert len(sh.voices[0]) == 1
    assert sh.voices[0][0].dur == 6            # 4 + the rest's 2
    assert sh.voices[0][0].rest is False


def test_a_rest_the_player_silences_is_left_alone():
    """$00 = no waveform bits at all, so the oscillator is silent: nothing is
    heard through the rest and a capture would only cost program space."""
    import build_mattgray_native_song as MG
    sh = _FakeShim([[_ev(4, False), _ev(2, True)] for _ in range(3)])
    n, _ = MG.merge_sounding_rests(sh, _frames(64, 0x00, 0x2000))
    assert n == 0
    assert [e.rest for e in sh.voices[0]] == [False, True]


def test_a_sounding_but_frequency_zero_rest_is_left_alone():
    """Waveform bits set but freq 0 = the oscillator is not advancing."""
    import build_mattgray_native_song as MG
    sh = _FakeShim([[_ev(4, False), _ev(2, True)] for _ in range(3)])
    n, _ = MG.merge_sounding_rests(sh, _frames(64, 0x10, 0x0000))
    assert n == 0


def test_the_merge_stops_at_the_fm_capture_cap():
    """Past FM_CAP frames `fm_program_for` freezes anyway, so the merge would
    buy nothing and still cost the program space."""
    import build_mattgray_native_song as MG
    import build_mon_native_song as BM
    long_rest = (BM.FM_CAP // 6) + 4           # pushes the note past the cap
    sh = _FakeShim([[_ev(4, False), _ev(long_rest, True)] for _ in range(3)])
    n, _ = MG.merge_sounding_rests(sh, _frames(BM.FM_CAP * 2, 0x10, 0x2000))
    assert n == 0


def test_a_leading_rest_has_no_note_to_merge_into():
    import build_mattgray_native_song as MG
    sh = _FakeShim([[_ev(2, True), _ev(4, False)] for _ in range(3)])
    n, _ = MG.merge_sounding_rests(sh, _frames(64, 0x10, 0x2000))
    assert n == 0
    assert sh.voices[0][0].rest is True


# -- the signature locator, cross-validated against the fast path ----------

DRILLER = os.path.join(ROOT, "SID", "Gray_Matt", "Driller.sid")
needs_driller = pytest.mark.skipif(not os.path.exists(DRILLER),
                                   reason="HVSC file absent")


@needs_driller
def test_signature_locator_agrees_with_the_validated_fast_path():
    """parse() tries the driller fast path first and only falls back, so the
    two paths never meet in normal use. Forcing verify() to raise sends a
    driller-layout file down the signature path -- and on Driller sub 1 the two
    decodes agree in EVERY field. That is the whole evidence that the 16 Stage
    B tunes, all of which decode by signature, are not being mis-parsed."""
    from sidm2 import mattgray_parser as MP
    from sidm2.mattgray_parser import parse_sid, MattGrayError

    fast = parse_sid(DRILLER, subtune=1)
    assert fast.layout == "driller", "test premise: this file uses the fast path"

    real = MP.MattGrayParser.verify
    try:
        MP.MattGrayParser.verify = lambda self: (_ for _ in ()).throw(
            MattGrayError("forced onto the signature path"))
        sig = parse_sid(DRILLER, subtune=1)
    finally:
        MP.MattGrayParser.verify = real

    assert sig.layout == "signature"
    assert sig.table_addrs == fast.table_addrs
    for f in ("tracks", "patterns", "pattern_addrs", "freq_lo", "freq_hi",
              "tempo", "arp_table_addr", "duration_base", "truncated_patterns"):
        assert getattr(sig, f) == getattr(fast, f), f"{f} differs between paths"
    key = lambda s: [(i.ad, i.sr, i.waveform, i.pulse_width, i.flags,
                      bytes(i.raw)) for i in s.instruments]
    assert key(sig) == key(fast)


@needs_sid
def test_the_located_instrument_table_explains_every_sounded_adsr():
    """$D405/$D406 at a note-on is a verbatim copy of the instrument record in
    this player family, so a correctly located table explains every sounded
    pair -- 100.0% on all 8 signature subtunes measured. Ground truth is the
    ORIGINAL's own trace, which owes nothing to our build.

    The NULL is asserted alongside, because a hit rate with nothing to compare
    it against proves nothing: the same records read 16 bytes off the located
    base must NOT explain the onsets.

    What this does NOT catch, stated because it was mutation-tested and found
    wanting: shifting the base by a whole record (+8) still passes, since set
    membership survives losing one never-sounded record. The cross-validation
    test above is what catches that. Sub 0 only here; the sweep is in the doc.
    """
    from sidm2.fidelity_common import siddump_frames_full
    from sidm2.mattgray_parser import parse_sid

    song = parse_sid(LN2, subtune=0)
    assert song.layout == "signature", "test premise: this file locates by signature"
    good = {(i.ad, i.sr) for i in song.instruments}

    # the null: the same span of bytes, 16 off the located base
    raw = open(LN2, "rb").read()
    body = raw[raw[7] | (raw[6] << 8):]
    load, data = body[0] | (body[1] << 8), body[2:]
    base = song.table_addrs["instr_a0"] + 16 - load
    STRIDE = 8
    null = {(data[base + k * STRIDE + 1], data[base + k * STRIDE + 2])
            for k in range(len(song.instruments))
            if 0 <= base + k * STRIDE + 2 < len(data)}

    prev, n, hit = [0, 0, 0], 0, 0
    for fr in siddump_frames_full(LN2, ['-a0', '-t20']):
        for v in range(3):
            st = fr[0][v]
            if st['wf'] is None:
                continue
            on = (st['wf'] & 1) and not (prev[v] & 1)
            prev[v] = st['wf']
            if on and st['adsr'] is not None:
                n += 1
                hit += ((st['adsr'] >> 8) & 0xFF, st['adsr'] & 0xFF) in good
    prev, nn, nhit = [0, 0, 0], 0, 0
    for fr in siddump_frames_full(LN2, ['-a0', '-t20']):
        for v in range(3):
            st = fr[0][v]
            if st['wf'] is None:
                continue
            on = (st['wf'] & 1) and not (prev[v] & 1)
            prev[v] = st['wf']
            if on and st['adsr'] is not None:
                nn += 1
                nhit += ((st['adsr'] >> 8) & 0xFF, st['adsr'] & 0xFF) in null

    assert n >= 20, f"too few onsets ({n}) to conclude anything"
    assert hit == n, f"located instrument table explains only {hit}/{n} onsets"
    assert nhit <= 0.05 * n, (
        f"the NULL table explains {nhit}/{nn} onsets -- this test has no "
        f"discriminating power, so its 100% means nothing")
