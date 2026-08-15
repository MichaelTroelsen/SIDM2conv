"""`_snap_onset` -- the per-note capture alignment shared by six native builders.

The window it searches (fr-2 .. fr+3) is right; the SELECTION rule inside it was
not. It returned the FIRST gate rise scanning left-to-right, so whenever the
previous note was <=2 frames long that note's own rise sat at fr-2 and won. The
capture then began two frames early, replayed two frames of the wrong
instrument, and the driver hard-restarted on top of it -- emitting a gate rise
the original does not have, two frames into the note.

Measured on `Roadblaster` v0 (DMC, n=15,996): 352 of 352 real gate rises matched
at delta 0 with NOTHING missing, and 93 spurious extra rises -- exactly the file's
93 two-frame notes, 1:1. A purely additive defect, which is why every strict
freq/wf/pulse column read it as wrong content (58.6/84.4/62.5) while +-2 frames
of slack recovered 96.9/100.0/100.0 and +-10 recovered nothing further.

`snap_gate` is opt-in per shim: DMC, Future Composer, HardTrack, Hubbard, SDI and
Sound Monitor set it; Matt Gray measured it OFF (see test_mattgray_native.py).
So this function is on six corpora's critical path and the tie-break below is
load-bearing: the window exists for Hubbard, whose grid frame lands one frame
LATE, putting the true rise at fr-1.
"""
import importlib.util
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = importlib.util.spec_from_file_location(
    "build_mon_native_song", os.path.join(ROOT, "bin", "build_mon_native_song.py"))


@pytest.fixture(scope="module")
def BM():
    sys.path.insert(0, ROOT)
    sys.path.insert(0, os.path.join(ROOT, "bin"))
    mod = importlib.util.module_from_spec(_SPEC)
    _SPEC.loader.exec_module(mod)
    return mod


class Shim:
    """Minimal stand-in for the shim object `_snap_onset` reads `snap_gate` off."""

    def __init__(self, snap_gate=True):
        self.snap_gate = snap_gate


def frames(gates, v=0):
    """siddump_per_frame-shaped frames whose voice `v` gate bit follows `gates`.

    Only $D404 bit 0 matters here, so the waveform is $41 (gate on) / $40 (off) --
    the same pair the real captures see on a plain triangle note.
    """
    return [({vi: dict(freq=0x1000, wf=(0x41 if (g and vi == v) else 0x40),
                       pul=0x800) for vi in range(3)}, None)
            for g in gates]


def gates(*runs):
    """`gates((0, 5), (1, 2))` -> [0]*5 + [1]*2. Reads like the trace does."""
    out = []
    for value, count in runs:
        out += [value] * count
    return out


def test_a_rise_at_fr_itself_wins_over_an_earlier_one_in_the_window(BM):
    """THE DEFECT. Frame 33 starts a 2-frame note, frame 35 starts the next one.

    Both are genuine gate rises and both are inside the window for fr=35. The
    note's own rise is the right answer; the old first-match scan returned 33.
    """
    f = frames(gates((0, 33), (1, 1), (0, 1), (1, 8)))
    #                          ^33      ^34    ^35 = the note under capture
    assert BM._snap_onset(Shim(), f, 0, 35) == 35


def test_the_old_first_match_order_is_what_returned_the_wrong_frame(BM):
    """Same input, old rule, via the A/B switch -- so the regression is pinned
    from both sides rather than asserted only in a comment."""
    f = frames(gates((0, 33), (1, 1), (0, 1), (1, 8)))
    os.environ["SNAP_FIRST"] = "1"
    try:
        assert BM._snap_onset(Shim(), f, 0, 35) == 33
    finally:
        del os.environ["SNAP_FIRST"]


def test_a_rise_one_frame_early_is_still_found(BM):
    """Hubbard's case -- the reason the window exists. The grid frame lands one
    frame late, the true rise is at fr-1, and nothing sits at fr."""
    f = frames(gates((0, 20), (1, 6)))          # rise at 20, capture asked at 21
    assert BM._snap_onset(Shim(), f, 0, 21) == 20


def test_the_full_backward_reach_still_works_when_nothing_is_nearer(BM):
    f = frames(gates((0, 20), (1, 6)))          # rise at 20, capture asked at 22
    assert BM._snap_onset(Shim(), f, 0, 22) == 20


def test_the_forward_reach_still_works(BM):
    f = frames(gates((0, 25), (1, 6)))          # rise at 25, capture asked at 22
    assert BM._snap_onset(Shim(), f, 0, 22) == 25


def test_ties_break_backward(BM):
    """fr-1 and fr+1 are both rises and equidistant. Backward wins: that is the
    direction the window was added for, so a tie must not silently flip six
    corpora forward."""
    f = frames(gates((0, 21), (1, 1), (0, 1), (1, 4)))
    #                          ^21      ^22     ^23   -- rises at 21 and 23, none at 22
    assert BM._snap_onset(Shim(), f, 0, 22) == 21


def test_no_rise_anywhere_in_the_window_leaves_the_frame_alone(BM):
    f = frames(gates((1, 40)))                  # gate held: no rise to snap to
    assert BM._snap_onset(Shim(), f, 0, 22) == 22


def test_a_shim_that_did_not_opt_in_is_never_touched(BM):
    """Matt Gray measured snap_gate OFF. A change to the selection rule must not
    reach a shim that never asked for snapping at all."""
    f = frames(gates((0, 33), (1, 1), (0, 1), (1, 8)))
    assert BM._snap_onset(Shim(snap_gate=False), f, 0, 35) == 35
    assert BM._snap_onset(Shim(snap_gate=False), f, 0, 34) == 34


def test_the_window_is_not_widened_by_the_reordering(BM):
    """A rise 3 frames BEFORE fr stays out of reach -- reordering must not turn
    into a wider search, which would start capturing across note boundaries in
    the other direction."""
    f = frames(gates((0, 19), (1, 1), (0, 20)))  # lone rise at 19
    assert BM._snap_onset(Shim(), f, 0, 22) == 22
