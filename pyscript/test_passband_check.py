"""The passband check's own logic, on synthetic frames -- no siddump, no builds.

The defect this guards was invisible for as long as it existed because the
document quoted the BUILDER and nothing measured the ARTIFACT: 21 of 33 shipped
HardTrack builds rendered low-pass where their originals select low+band,
band+high, or modulate between modes up to 87 times, while `HARDTRACK.md` said
`$D418` was 100.00% byte-exact -- which was true of `build_hardtrack_native_song.py`
and false of every file it had not been re-run over.

Two failure shapes have to stay distinguishable, because a plain equality test
against a static side scores them the same:

  A. both sides constant, different constants  (LP vs LP+BP -- a permanent
     timbre offset on every frame)
  B. original modulates, ours is constant      (agreement can still look high
     if the original spends most frames on the mode we happen to hold)

`Hopscotch` was shape B at 87.2% agreement. A 99%-threshold catches it; a
"do the sets of modes used overlap?" test would not.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import passband_check as pb  # noqa: E402


def frames(vals):
    """siddump_frames_full-shaped: (voices, filter) per frame. Index 0 is the
    force-displayed row the module must drop."""
    return [({}, {"volmode": v}) for v in vals]


def test_frame_zero_is_dropped():
    """siddump force-displays every register on frame 0 whether the playroutine
    wrote it or not -- counting it would invent a mode change at the start."""
    assert pb.mode_sequence(frames([0x6F, 0x1F, 0x1F])) == [0x10, 0x10]


def test_only_the_passband_bits_are_compared():
    """Low nibble is master VOLUME. A volume difference is audible as level, not
    timbre; pooling them lets one mask the other."""
    assert pb.mode_sequence(frames([0x00, 0x1F, 0x10, 0x1A])) == [0x10] * 3


def test_absent_register_is_not_agreement():
    """`score_pct`'s rule: an unmeasured comparison is None, never 100.0."""
    assert pb.mode_sequence(frames([0x1F, None, None])) == []
    pct, n, _oc, _dc, _off = pb.compare([], [0x10])
    assert pct is None and n == 0
    pct, _n, _oc, _dc, _off = pb.compare([0x10], [])
    assert pct is None


def test_shape_A_constant_but_different():
    """Altered_States_Tune_1 as shipped: original LP+BP, ours LP, every frame."""
    pct, n, oc, dc, _off = pb.compare([0x30] * 100, [0x10] * 100)
    assert pct == 0.0 and n == 100
    assert oc == 0 and dc == 0, "neither side modulates -- the tell is the value"


def test_shape_B_original_modulates_ours_is_static():
    """Hopscotch as shipped: the original leaves LP for BP+HP on some frames and
    ours never does. Agreement stays HIGH because the original spends most of
    its time on the mode we hold -- the change counts are what expose it."""
    orig = [0x10] * 80 + [0x60] * 13 + [0x10] * 7   # leaves LP and comes back
    pct, _n, oc, dc, _off = pb.compare(orig, [0x10] * 100)
    assert pct == 87.0, "87 of 100 frames still match -- high, and still broken"
    assert oc == 2 and dc == 0, "one departure and one return = 2 changes"


def test_a_correct_build_agrees():
    orig = [0x10] * 50 + [0x60] * 50
    pct, n, oc, dc, off = pb.compare(orig, list(orig))
    assert pct == 100.0 and n == 100 and oc == dc == 1 and off == 0


def test_describe_names_every_mode_present():
    names, changes = pb.describe([0x10, 0x30, 0x60, 0x10])
    assert names == ["LP", "LP+BP", "BP+HP"]
    assert changes == 3


def test_overlap_is_the_shorter_side():
    """Parts differ in length between the two sides; scoring past the end of one
    would compare against nothing."""
    pct, n, _oc, _dc, _off = pb.compare([0x10] * 10, [0x10] * 4)
    assert n == 4 and pct == 100.0


def test_a_boot_offset_is_fitted_not_assumed():
    """The native driver boots a few frames late. Comparing frame i to frame i
    made a KNOWN constant delay read as a passband defect on every tune that
    MODULATES -- and only on those, since a static mode is immune to shifting,
    which is why the flaw survived the check's first run against real builds."""
    orig = [0x10] * 40 + [0x60] * 20 + [0x10] * 40
    late = [0x10] * 3 + orig[:-3]           # same programme, 3 frames late
    pct, _n, oc, dc, off = pb.compare(orig, late)
    assert pct == 100.0, "a pure delay is not a wrong passband"
    assert off == 3 and oc == dc == 2


def test_the_fitted_offset_is_reported():
    """A large offset is itself a finding -- right band, arriving late -- and a
    different defect from selecting the wrong band. It must not be absorbed."""
    orig = [0x10] * 50 + [0x60] * 50
    _pct, _n, _oc, _dc, off = pb.compare(orig, [0x10] * 6 + orig[:-6])
    assert off == 6


def test_a_tie_keeps_the_unshifted_reading():
    """Two constants that agree nowhere agree nowhere at every offset. Picking
    a shifted one would quietly shrink n."""
    pct, n, _oc, _dc, off = pb.compare([0x30] * 100, [0x10] * 100)
    assert pct == 0.0 and n == 100 and off == 0


def test_the_fit_cannot_manufacture_agreement():
    """Guard against the obvious abuse: a wide enough search will align almost
    anything. Two unrelated programmes must not reach agreement by shifting."""
    orig = [0x10] * 25 + [0x60] * 25 + [0x10] * 25 + [0x60] * 25
    ours = [0x40] * 100
    pct, _n, _oc, _dc, _off = pb.compare(orig, ours)
    assert pct == 0.0
