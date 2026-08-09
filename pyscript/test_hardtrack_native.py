"""Tests for the HardTrack Composer Stage B path.

Two layers, both cheap enough to run in the normal suite:

  * `voice_events` -- the sequencer event walk the native shim is built on. It
    must stay tied to `simulate()` (one state machine, not two) and it must
    produce a CONTIGUOUS tick timeline per voice, because every native builder
    walks that list accumulating durations and a gap slides the rest of the
    voice earlier for the whole song.
  * `HardTrackShim` -- the MON-compatible view. Constructing it needs no
    siddump, no assembler and no SF2II, so the protocol it must satisfy is
    pinned here rather than only inside a ten-minute corpus build.

The fidelity numbers themselves are NOT asserted here; they need a trace and a
build. `pyscript/hardtrack_native_sweep.py` reproduces those from a fresh clone.
"""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sidm2.hardtrack_parser import (  # noqa: E402
    HardTrackError, HardTrackModule, INSTR_LEGATO, simulate, voice_events)

CORP = os.path.join(ROOT, 'SID', 'Shogoon')
FILES = ['Love_tune_2', 'Zakplus', 'Sling', 'Jazzloor', 'Domagareflexow']


def sid(name):
    return os.path.join(CORP, name + '.sid')


def mod(name):
    return HardTrackModule.from_sid(sid(name))


def shim_module():
    """Import the builder without running it (it has no import guard on argv,
    but it does chdir + read sys.argv, so give it a benign one)."""
    path = os.path.join(ROOT, 'bin', 'build_hardtrack_native_song.py')
    old = sys.argv
    sys.argv = ['build_hardtrack_native_song.py', sid('Love_tune_2')]
    try:
        spec = importlib.util.spec_from_file_location('_ht_native', path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m
    finally:
        sys.argv = old


@pytest.mark.parametrize('name', FILES)
def test_event_walk_agrees_with_simulate(name):
    """The event log must be the SAME walk as simulate(), not a second copy.

    A duplicated sequencer state machine is what mis-attributed the Stage A
    losses once already, so the note-on count is pinned against simulate()'s
    own output for every file.
    """
    m = mod(name)
    ev, _ = voice_events(m, 0, 1000)
    sim = simulate(m, 0, 1000)
    for v in range(3):
        walked = sum(1 for e in ev[v] if e.kind == 'note')
        simulated = sum(1 for row in sim if row[v] is not None)
        assert walked == simulated, f"{name} voice {v}"


@pytest.mark.parametrize('name', FILES)
def test_event_timeline_is_contiguous_from_tick_zero(name):
    """Durations must tile the timeline with no gap and no overlap.

    build_native_song places event k at tick sum(dur[:k]); a voice whose first
    note is at tick 4 but whose list starts there would be played 4 ticks early
    for the entire song (measured: Love_tune_2 voices 1 and 2, 10 and 20 frames
    early, and the fidelity metric shows it as a whole-voice failure rather
    than as a phase).
    """
    m = mod(name)
    ev, _ = voice_events(m, 0, 1000)
    for v in range(3):
        if not ev[v]:
            continue
        tk = 0
        for e in ev[v]:
            assert e.tick == tk, f"{name} v{v}: event at {e.tick}, expected {tk}"
            assert e.dur >= 1
            tk += e.dur


@pytest.mark.parametrize('name', FILES)
def test_event_frames_sit_on_the_tempo_grid(name):
    """frame == 1 + tick*(speed+1) -- the player's divider starts at 2, so the
    first row lands on frame 1. The shim derives its onset phase from this, and
    a builder that assumed frame 0 would capture every note one frame early."""
    m = mod(name)
    fpt = m.speed(0) + 1
    ev, _ = voice_events(m, 0, 1000)
    for v in range(3):
        for e in ev[v]:
            if e.tick == 0 and e.kind == 'gate_off':
                continue                      # synthesised lead-in rest
            assert e.frame == 1 + e.tick * fpt, f"{name} v{v} tick {e.tick}"


def test_legato_events_are_flagged():
    """$6F carries a quarter of all note events; the walk must expose it. Stage
    B does not need a separate mechanism for it (the capture handles it), but
    losing the flag would make the difference from $00 invisible to any later
    analysis."""
    m = mod('Love_tune_2')
    ev, _ = voice_events(m, 0, 6000)
    flagged = [e for v in range(3) for e in ev[v] if e.legato]
    assert flagged, 'Love_tune_2 has $6F notes'
    assert all(e.raw == INSTR_LEGATO for e in flagged)


def test_shim_protocol():
    """The MON shim contract build_native_song actually calls."""
    M = shim_module()
    s = M.HardTrackShim(mod('Love_tune_2'), 0, frames=1000)
    assert s.frames_per_tick == s.speed + 1
    assert s.tick_to_frame(0) == 0 and s.tick_to_frame(3) == 3 * s.frames_per_tick
    assert s.frame_to_tick(s.tick_to_frame(7)) == 7
    for v in range(3):
        blocks = s._voice_blocks(v)
        assert len(blocks) <= 1
        for _pat, evs in blocks:
            assert evs is s.voices[v]
    ins = s.instrument(0)
    assert set(ins) >= {'ad', 'sr', 'waveform', 'pw'}
    assert ins['waveform'] != 0          # 0 would silence the driver's idle row


def test_shim_freq_table_covers_the_drivers_112_entries():
    """write_mon_freqtable asks for notes 0..$6F but HardTrack's table holds 96.

    Reading 16 entries off the end of the player's table would emit whatever
    data follows it as if it were a frequency; the shim extrapolates by octave
    doubling instead, and the result must stay monotonic and in range.
    """
    M = shim_module()
    s = M.HardTrackShim(mod('Love_tune_2'), 0, frames=200)
    vals = [s.note_freq(i) for i in range(0x70)]
    assert all(0 < f <= 0xFFFF for f in vals)
    assert vals[:96] == [s.mod.freq(i) for i in range(96)]
    assert all(b >= a for a, b in zip(vals, vals[1:])), 'freq table not monotonic'


def test_shim_disables_scaled_fm_entries():
    """HardTrack percussion emits real Hz deltas in the $40-$43 hi-byte range,
    which is the driver's SCALED-vibrato marker. With the marker on, one
    Love_tune_2 drum note froze at the wrong absolute frequency for its whole
    tail while its waveform stayed byte-exact -- invisible to a waveform
    metric. Pin the opt-out, and pin that the shared helper honours it."""
    import build_mon_native_song as BM
    M = shim_module()
    s = M.HardTrackShim(mod('Love_tune_2'), 0, frames=200)
    assert s.no_fm_scale
    assert not BM._fm_scale_ok(s)

    class Other:                      # every other shim is unaffected
        pass
    assert BM._fm_scale_ok(Other())


def test_gate_off_is_folded_into_the_previous_note():
    """$61 gates off but HardTrack keeps stepping the wave program, so the
    voice arpeggiates through its release. Emitting a rest there idles the
    voice and throws the tail away; the tail must stay inside the preceding
    note's capture window instead."""
    M = shim_module()
    m = mod('Love_tune_2')
    s = M.HardTrackShim(m, 0, frames=6000)
    ev, _ = voice_events(m, 0, 6000)
    for v in range(3):
        interior = [e for e in ev[v][1:] if e.kind == 'gate_off']
        if not interior:
            continue
        assert not any(x.rest for x in s.voices[v][1:]), \
            f"voice {v}: an interior gate-off became a rest"


def test_refusals_are_still_refusals():
    """The Stage B entry point must not decode a wrapped rip that the parser
    refuses -- the simulator runs away on those (2,997 phantom onsets against
    the wrong song)."""
    for name in ('Eternal', 'Zone_of_Darkness', 'Commercial_Fake'):
        p = sid(name)
        if not os.path.exists(p):
            continue
        with pytest.raises(HardTrackError):
            HardTrackModule.from_sid(p)


def test_song_span_stops_at_the_orderlist_loop():
    """A HardTrack song never ends ($FF restart / $FD jump), so the span is one
    pass. A builder that used the scan length instead would emit the same music
    twice."""
    M = shim_module()
    s = M.HardTrackShim(mod('Love_tune_2'), 0, frames=M.SCAN_FRAMES)
    span = M.song_span_frames(s)
    assert 0 < span <= M.SCAN_FRAMES
