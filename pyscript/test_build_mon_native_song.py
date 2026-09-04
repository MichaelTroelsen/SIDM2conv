"""What `detect_filter_drives` is blind to -- and what is NOT evidence of it.

THE DETECTOR'S BLINDNESS IS REAL AND STRUCTURAL. `detect_filter_drives`
(bin/build_mon_native_song.py) keys entirely on the CUTOFF: its trigger is
`abs(ftr[f][0] - ftr[f-1][0]) >= FILT_FAST`, and the second element of each
`ftr` tuple is `$D417`, consulted only for routing bits. `$D418` is not an input
to it at all, so a passband change that moves no cutoff cannot be seen. That much
is a property of the code and is pinned below by reading the code's own inputs.

BUT THE ONE FILE OFFERED AS PROOF OF IT IS NOT PROOF, and that is the substance
of this module. A prior cycle sampled 32 of 728 files and reported exactly one
"genuine hit" -- `SID/Fun_Fun/Byte_Bite.sid`, described as toggling `$D418`
every 6 frames "with routing already on". Measured here, the routing claim is
false and the rest follows from it:

    $D417 over 3000 frames (60 s) : only $00 and $08  -> low 3 bits ALWAYS zero
    raw $D418 distinct values     : $09 (835), $19 (133), $1A (32) over 20 s
    low nibble  = master VOLUME   : 9, occasionally 10
    mode bits 4-6                 : 0 for $09, 1 (low-pass) for $19/$1A

No voice is ever routed through the filter, so the filter has no input and the
low-pass bit is acoustically inert. What the tune is actually doing is pulsing
the master VOLUME for one frame every ~6 -- a gate/percussion blip -- and the
mode bit rides along because it is the same register write. Reading bits 4-6 out
of that byte and calling the result "filter activity" is the measurement error,
not a finding about the detector.

TWO CONSEQUENCES, both deliberate:

  * The old task id `passband-blindness-is-unexercised-by-this-corpus` wanted a
    test asserting the corpus never exercises the blindness. That is NOT what is
    asserted here -- a 32-file sample cannot establish it, and this module makes
    no claim either way about the other 727 files.
  * `thread-passband-through-detect-filter-drives` justifies a change to a
    detector FIVE builders share (MoN, DMC, SDI, FC, Myth) on the strength of
    this one hit. That justification is gone until a file survives
    `passband_change_is_audible` below.

The guard fix the task named is here too: a prior scan excluded events at
`f <= 2` to skip init writes, which is too narrow -- `Filthy_Hit`'s init lands at
frame 25. The right exclusion is "changes once and never again", which is what
an init write looks like regardless of when it happens.
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "bin"))

BYTE_BITE = os.path.join(_ROOT, "SID", "Fun_Fun", "Byte_Bite.sid")


def passband_change_is_audible(filtctl, passband):
    """Does this trace show a $D418 passband change that could be HEARD?

    Two conditions, and the prior cycle's criterion checked neither:

      * ROUTING ON at the changing frame. `$D417`'s low three bits select which
        voices feed the filter. With all three clear the filter has no input and
        its mode bits change nothing audible -- which is exactly Byte_Bite.
      * MORE THAN ONE CHANGE. A value that changes once and never again is an
        init write, whenever it lands. The superseded guard excluded `f <= 2`
        instead, which misses `Filthy_Hit` (init at frame 25) while wrongly
        keeping genuine early activity.
    """
    n = min(len(filtctl), len(passband))
    changes = [f for f in range(1, n) if passband[f] != passband[f - 1]]
    if len(changes) <= 1:                      # init write, not activity
        return []
    return [f for f in changes if (filtctl[f] or 0) & 0x07]


def test_detect_filter_drives_cannot_see_d418_at_all():
    """Structural, and it needs no trace: $D418 is not among the detector's inputs.

    `filter_trace` returns 2-tuples of (cutoff11, $D417) and its docstring says
    so outright -- "The passband lives in $D418 and is fetched separately by
    `passband_trace` rather than widening a shared [tuple]". So whatever
    `detect_filter_drives` does with its `ftr` argument, it cannot consult the
    passband: the value is not in the structure it is handed.
    """
    import inspect

    import build_mon_native_song as B

    # THE SHAPE, not the prose: every ftr element carries two fields, so there is
    # no third slot a passband could arrive in.
    ftr = B.filter_trace(BYTE_BITE, 0, 2) if os.path.isfile(BYTE_BITE) else None
    if ftr:
        assert {len(t) for t in ftr} == {2}, {len(t) for t in ftr}

    # and the detector reads only [0] (cutoff) and [1] (routing) of them.
    # COMMENTS AND THE DOCSTRING ARE STRIPPED FIRST: detect_filter_drives
    # discusses $D418 in a comment (the Juba-Jazz note) while never reading it,
    # and a naive substring test fails on the prose -- which is exactly the
    # difference between what the code says and what it does.
    lines = inspect.getsource(B.detect_filter_drives).splitlines()
    body = "\n".join(ln.split("#", 1)[0] for ln in lines
                     if not ln.strip().startswith("#"))
    body = body.replace(B.detect_filter_drives.__doc__ or "", "")
    assert "ftr[f][1] & 0x07" in body
    assert "ftr[f][2]" not in body
    assert "d418" not in body.lower(), [ln for ln in body.splitlines() if "418" in ln.lower()]


def test_the_guard_rejects_a_single_change_whenever_it_lands():
    """'Changes once and never again' is an init write at frame 2 or frame 25.

    The superseded `f <= 2` guard is what this replaces; Filthy_Hit's init at
    frame 25 is the case that broke it. Routing is ON throughout both fixtures,
    so the ONLY thing separating them is the change count.
    """
    routed = [0x0F] * 40                            # all three voices routed
    late_init = [0] * 25 + [1] * 15                 # ONE change, at frame 25
    assert passband_change_is_audible(routed, late_init) == []

    # identical routing, identical shape, only the change COUNT differs
    repeated = [0] * 10 + [1] * 5 + [0] * 5 + [1] * 20      # three changes
    assert passband_change_is_audible(routed, repeated) == [10, 15, 20]


def test_the_guard_rejects_a_passband_change_with_nothing_routed():
    """A mode change with $D417's low 3 bits clear is inaudible, not a blind spot."""
    unrouted = [0x08] * 40                           # bit 3 set, no VOICE routed
    toggling = [(f // 6) % 2 for f in range(40)]     # plenty of changes
    assert passband_change_is_audible(unrouted, toggling) == []
    # ...and the identical passband WITH a voice routed does count
    assert passband_change_is_audible([0x09] * 40, toggling) != []


@pytest.mark.skipif(not os.path.isfile(BYTE_BITE), reason="Byte_Bite.sid absent")
def test_byte_bite_is_not_evidence_of_the_blindness():
    """The one reported 'genuine hit', measured: it is a VOLUME blip, not a filter.

    Slow -- it shells out to siddump -- but the whole point is that the claim was
    made from a trace and can only be withdrawn from one.
    """
    import build_mon_native_song as B

    ftr = B.filter_trace(BYTE_BITE, 0, 20)
    pb = B.passband_trace(BYTE_BITE, 0, 20)
    filtctl = [c for _, c in ftr]

    # the passband really does move, a lot -- so "nothing happens" is not the reason
    n = min(len(ftr), len(pb))
    changes = [f for f in range(1, n) if pb[f] != pb[f - 1]]
    assert len(changes) > 100, len(changes)

    # ...but not one of them routes a voice, so not one is audible
    assert passband_change_is_audible(filtctl, pb) == []
    assert all((c or 0) & 0x07 == 0 for c in filtctl), sorted({c & 0x07 for c in filtctl})


@pytest.mark.skipif(not os.path.isfile(BYTE_BITE), reason="Byte_Bite.sid absent")
def test_byte_bite_writes_d418_for_its_volume_nibble():
    """$09/$19/$1A -- the mode bit rides along with a one-frame volume pulse.

    This is the positive account of the previous test: the register is being
    written for its LOW nibble (master volume 9, pulsing to 10), and bits 4-6
    change as a side effect of writing the whole byte.
    """
    from sidm2.fidelity_common import siddump_frames_full

    vals = [g["volmode"] for _, g in siddump_frames_full(BYTE_BITE, ["-a0", "-t20"])
            if g.get("volmode") is not None]
    assert vals, "no $D418 captured"
    assert set(vals) <= {0x09, 0x19, 0x1A}, sorted(set(vals))
    assert {v & 0x0F for v in vals} == {9, 10}          # the volume nibble moves
    assert {(v >> 4) & 0x07 for v in vals} == {0, 1}    # so the mode bits follow
    # the pulse is brief: the resting value dominates
    assert vals.count(0x09) > len(vals) // 2, vals.count(0x09)


CYBERNOID_II = os.path.join(_ROOT, "SID", "Tel_Jeroen", "Cybernoid_II.sid")


def test_init_passband_seeds_from_the_opening_run_not_frame_zero():
    """INIT_PASSBAND must not seed from a ONE-FRAME transient.

    THE DEFECT THIS PINS, measured on Cybernoid_II sub0 (2026-09-04).
    `passband_trace` returns `$01` (LP) at frame 0 and `$03` (LP+BP) from frame 1
    onward -- 1440 of 1500 frames are LP+BP. Seeding `_init_fmode` from
    `pbtr[win[0]]` alone therefore opened the driver on LP, a value the tune holds
    for exactly one frame, instead of the LP+BP it actually plays.

    WHY THE OLD SEED LOOKED LIKE IT WORKED: it does remove the leading `off`, and
    a report saying "ours goes off/LP+BP -> LP/LP+BP" is literally true. But the
    passband score did not move AT ALL -- 84.6% before and 84.6% after, the same
    215 audible mismatched frames -- because a wrong `LP` is no better than a
    wrong `off`. An improvement in the printed mode string is not an improvement.
    With the modal seed the same file scores 100.0 with dChg 0.

    THE FIX IS NOT A NO-OP ELSEWHERE, and that is the point of the census in
    docs/players/MON.md: 12 of 24 MoN songs seed differently under the two rules
    (Hawkeye sub2/sub3 read LP+BP+HP at frame 0 where the song holds LP). It IS a
    no-op on every file the DMC/HardTrack A/B validated -- 13 of 13 identical --
    so those results carry over unchanged.

    This asserts the RULE against the real trace rather than the constant, so it
    fails if the seed reverts to frame 0.
    """
    if not os.path.isfile(CYBERNOID_II):
        pytest.skip("Cybernoid_II.sid absent")
    import inspect

    import build_mon_native_song as B

    pbtr = B.passband_trace(CYBERNOID_II, 0, 30)
    assert pbtr, "no passband trace"

    # the trap itself: frame 0 disagrees with the run that follows it
    assert (pbtr[0] & 0x07) == 0x01, hex(pbtr[0])
    assert (pbtr[1] & 0x07) == 0x03, hex(pbtr[1])

    seg = pbtr[0:50]
    modal = max(set(seg), key=seg.count)
    assert (modal & 0x07) == 0x03, hex(modal)
    assert (modal & 0x07) != (pbtr[0] & 0x07), (
        "frame 0 and the opening run agree here, so this file no longer "
        "exercises the transient -- find another before deleting this test")

    src = inspect.getsource(B.build_native_song)
    assert "_seg" in src and "count" in src, (
        "the seed no longer looks like a modal-over-a-run rule")
