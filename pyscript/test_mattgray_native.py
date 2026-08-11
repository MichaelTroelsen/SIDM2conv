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
