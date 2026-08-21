"""`build_native_song` must refuse an input it cannot turn into music.

Both guards exist because a build that PROCEEDS on bad input does not fail --
it ships. `Flimbos_Quest_main` emitted 34 parts of silence and was then scored,
reading freq 0.2/0.2/0.2 as a fidelity defect rather than a decode that failed.
A refusal puts the file in the sweep's `not_built` class, where a build gap
stops masquerading as a fidelity gap.

The two guards catch the same failure at different layers, and the ORDER
matters: a decode with no notes is caught before the trace is even consulted,
so its message is the one the user sees.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "bin"))
sys.path.insert(0, ROOT)

BM = pytest.importorskip("build_mon_native_song")

EMPTY_TRACE = ([], [], [])


class _Ev:
    def __init__(self, note):
        self.note = note
        self.dur = 8


class _Song:
    """The minimum `build_native_song` reads before it reaches either guard."""

    def __init__(self, note):
        self.voices = [[_Ev(note)], [_Ev(note)], [_Ev(note)]]

    def tick_to_frame(self, t):
        return t


def _build(song, traces):
    return BM.build_native_song(song, "Some_Song.sid", 0, {}, [], traces=traces)


def test_an_empty_trace_is_refused_by_name():
    """dd67bee closed the LOUD half of this -- a siddump that fails now raises
    rather than returning ''. This is the quiet half: a siddump that exits 0
    having printed no rows. Without the guard the notes decode fine, so the
    build proceeds and derives every per-note (FM, pulse) bundle from an empty
    series, shipping held degenerate programs.
    """
    with pytest.raises(ValueError) as e:
        _build(_Song(note=60), EMPTY_TRACE)

    msg = str(e.value)
    assert "trace has no frames" in msg
    assert "Some_Song.sid" in msg, "the refusal must name the file it refused"
    assert "not the fidelity" in msg, (
        "the message has to say this is a CAPTURE failure -- the whole point is "
        "that it stops being read as a fidelity number")


def test_a_decode_with_no_notes_is_refused_before_the_trace_is_consulted():
    """Order, not just coverage: a silent decode with an empty trace has BOTH
    faults, and the no-notes message must win. Reporting the trace would send
    the reader to siddump for what is a decode bug."""
    with pytest.raises(ValueError) as e:
        _build(_Song(note=0), EMPTY_TRACE)

    assert "decoded no notes on any voice" in str(e.value)


def test_a_silent_voice_is_ordinary_and_only_a_silent_SONG_refuses():
    """Many songs rest one voice. Refusing on that would reject real music --
    the guard is deliberately `not any(...)` across all three."""
    song = _Song(note=60)
    song.voices[1] = [_Ev(0)]                 # one voice silent

    with pytest.raises(ValueError) as e:      # reaches the TRACE guard, not the
        _build(song, EMPTY_TRACE)             # no-notes one

    assert "trace has no frames" in str(e.value)


@pytest.mark.parametrize("frames", [[], ()], ids=["empty-list", "empty-tuple"])
def test_emptiness_is_tested_by_truth_not_by_type(frames):
    """`per_frame` returns a list today; the guard must not care."""
    with pytest.raises(ValueError, match="trace has no frames"):
        _build(_Song(note=60), (frames, [], []))
