"""The rung-3 comparison: SF2II against our own wrapper render.

Capturing needs the editor GUI, so these tests exercise the scoring and the
offset search on synthetic data -- which is where both retracted rung-3
conclusions actually went wrong.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sf2ii_vs_wrapper as W  # noqa: E402


def _cap(frames, freq=0x1234, ctl=0x41, pw=0x800):
    """SF2II capture: 25 registers per frame, voice regs at 7*v."""
    out = {}
    for f in frames:
        b = [0] * 25
        for v in range(3):
            b[7 * v] = freq & 0xFF
            b[7 * v + 1] = freq >> 8
            b[7 * v + 2] = pw & 0xFF
            b[7 * v + 3] = (pw >> 8) & 0xF
            b[7 * v + 4] = ctl
        out[f] = b
    return out


def _wrap(frames, freq=0x1234, ctl=0x41, pw=0x800):
    return {f: [(freq, ctl, pw)] * 3 for f in frames}


def test_identical_streams_score_100_at_offset_zero():
    cap, wrap = _cap(range(100)), _wrap(range(100))
    fh, wh, ph, tot = W.score(cap, wrap, 0, 0)
    assert tot == 100
    assert (fh, wh, ph) == (100, 100, 100)


def test_a_gated_off_frame_is_not_counted():
    """The gate gates the comparison -- a silent voice must not be scored."""
    cap, wrap = _cap(range(50)), _wrap(range(50), ctl=0x40)   # gate bit clear
    assert W.score(cap, wrap, 0, 0)[3] == 0


def test_the_search_can_express_a_NEGATIVE_offset():
    """A render that LEADS must be findable.

    sf2ii_vs_real.py searched range(0, 400) and so could not say "-3"; it
    reported the offset-0 value instead, which is how a build scoring 91/93/64%
    was published as 66/21/61% and called a failure.
    """
    assert min(range(-W.MAX_LEAD, W.MAX_LAG)) < 0
    # wrapper frame f corresponds to capture frame f-4 => offset -4
    cap = _cap(range(100))
    wrap = {f + 4: [(0x1234, 0x41, 0x800)] * 3 for f in range(100)}
    best = max(range(-W.MAX_LEAD, 8),
               key=lambda o: W.score(cap, wrap, 0, o)[0])
    assert best == -4, best


def test_offsets_are_ranked_by_RATE_not_by_raw_hit_count():
    """The trap that produced a wrong global offset.

    Offset A compares many frames badly; offset B compares few frames
    perfectly. Raw hits pick A, and A is wrong.
    """
    cap = _cap(range(200))
    wrap = {}
    for f in range(30):                        # a short band that matches exactly
        wrap[f] = [(0x1234, 0x41, 0x800)] * 3
    for f in range(30, 200):                   # a long band that mostly does not
        wrap[f] = [(0x1234 if f % 4 == 0 else 0x9999, 0x41, 0x800)] * 3

    # offset 0 compares all 200 frames and is mostly wrong; offset 170 lines the
    # capture's tail up with the short exact band -- 30 frames, all correct.
    hits0, _, _, tot0 = W.score(cap, wrap, 0, 0)
    hitsB, _, _, totB = W.score(cap, wrap, 0, 170)
    assert (tot0, totB) == (200, 30)
    assert hits0 > hitsB                        # raw hits prefer the wrong one
    assert hitsB / totB > hits0 / tot0          # the rate prefers the right one


def test_the_tracked_editor_binary_is_never_written_to():
    """Running the capture must not dirty the working tree.

    bin/sf2ii_vs_real.py used to copy a freshly built editor OVER the tracked
    bin/SIDFactoryII_dbg.exe on every run, so every rung-3 run left a 1 MB
    binary modified and "should this be committed?" became a standing question
    the tool had effectively decided by itself.
    """
    import sf2ii_vs_real as V
    src = open(os.path.join(os.path.dirname(os.path.abspath(V.__file__)),
                            "sf2ii_vs_real.py"), encoding="utf-8").read()
    assert "shutil.copyfile(DBG_SRC, DBG_LOCAL)" in src
    assert "shutil.copyfile(DBG_SRC, DBG)" not in src
    assert V.DBG != V.DBG_LOCAL
    # the local copy stays beside the tracked one (SF2II runs with cwd=bin/)
    assert os.path.dirname(V.DBG) == os.path.dirname(V.DBG_LOCAL)
