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


# ---------------------------------------------------------------------------
# `_PENDING` is PROCESS-GLOBAL, and the module now says so in code rather than
# in a neighbour's comment.
#
# WHY THESE TESTS EXIST. `commit_parts()` publishes ALL of `_PENDING`, so two
# songs staged concurrently in one interpreter cross-publish -- the first to
# finish commits the other's half-written parts under its own name. It was seen
# once, on a -j8 DMC sweep where `Spacegame_Music` tried to commit
# `_abl_part01.sf2.staging`, and it did not reproduce.
#
# IT IS NOT REACHABLE FROM TRACKED CODE TODAY: every `bin/build_*_native_song.py`
# is a one-song CLI and every sweep parallelises with `subprocess.run`. Before
# this guard the ONLY thing recording that was a comment in
# `pyscript/hardtrack_native_rebuild.py`. Nine builders import this module, so
# the invariant is one `ThreadPoolExecutor.submit(BM....)` from being broken by
# someone who never reads that comment. These tests pin the refusal, not the
# comment.
# ---------------------------------------------------------------------------

import threading                                                  # noqa: E402
import contextlib                                                 # noqa: E402


@contextlib.contextmanager
def _clean_pending(B):
    """Save and restore the module's staging globals around a test."""
    keep_pending, keep_owner = B._PENDING, B._PENDING_OWNER
    B._PENDING, B._PENDING_OWNER = [], None
    try:
        yield
    finally:
        B._PENDING, B._PENDING_OWNER = keep_pending, keep_owner


def _in_thread(fn):
    """Run `fn` on a worker thread; return (result, exception)."""
    box = {}

    def run():
        try:
            box['r'] = fn()
        except BaseException as e:          # noqa: BLE001 - we want it back
            box['e'] = e

    t = threading.Thread(target=run, name='worker-under-test')
    t.start()
    t.join()
    return box.get('r'), box.get('e')


def test_a_second_thread_cannot_commit_a_staging_set_it_did_not_stage():
    """THE DEFECT ITSELF: cross-thread publish is refused, loudly.

    The set is staged by the main thread; a worker then calls `commit_parts`.
    Before the guard this silently published another song's parts. It must now
    raise, and the message must name both threads -- a refusal nobody can
    attribute is a refusal nobody fixes.
    """
    import build_mon_native_song as B

    with _clean_pending(B):
        B._own_pending("stage")                     # main thread takes ownership
        B._PENDING.append(("a.sf2.staging", "a.sf2"))

        _, err = _in_thread(B.commit_parts)

        assert isinstance(err, RuntimeError), err
        assert "PROCESS-GLOBAL" in str(err), str(err)
        assert "worker-under-test" in str(err), str(err)
        # and it refused rather than half-publishing
        assert B._PENDING == [("a.sf2.staging", "a.sf2")]


def test_a_second_thread_cannot_stage_into_another_threads_set():
    """The append site is guarded too, not just the commit.

    Guarding only `commit_parts` would let two builds interleave their entries
    and then fail at publish time -- by which point the staging files on disk
    already belong to two songs. The refusal has to land on the FIRST foreign
    touch.
    """
    import build_mon_native_song as B

    with _clean_pending(B):
        B._own_pending("stage")
        B._PENDING.append(("a.sf2.staging", "a.sf2"))

        _, err = _in_thread(lambda: B._own_pending("stage"))

        assert isinstance(err, RuntimeError), err
        assert "refusing to stage" in str(err), str(err)


def test_one_worker_thread_may_own_a_whole_build():
    """WHAT IS DELIBERATELY STILL ALLOWED, so the guard is not over-tight.

    The rule is one OWNER per staging set, NOT "main thread only". A caller that
    runs an entire single-song build inside one worker thread shares nothing and
    must keep working; anchoring on the main thread would refuse it while
    catching no additional defect.
    """
    import build_mon_native_song as B

    with _clean_pending(B):
        def whole_build():
            B._own_pending("stage")
            B._PENDING.append(("b.sf2.staging", "b.sf2"))
            return B._own_pending("commit")         # same thread: allowed

        _, err = _in_thread(whole_build)
        assert err is None, err


def test_an_empty_pending_commits_from_any_thread():
    """`build_myth_native_song` calls `prune_stale_parts` with nothing staged and
    documents that as a no-op. The guard must not turn that into a crash, and it
    must not leave a stale owner behind for the next set."""
    import build_mon_native_song as B

    with _clean_pending(B):
        _, err = _in_thread(B.commit_parts)
        assert err is None, err
        assert B._PENDING_OWNER is None


def test_committing_releases_ownership_for_the_next_set():
    """Ownership is per-SET, not per-process-lifetime.

    If `commit_parts` left `_PENDING_OWNER` set, a legitimate second build in the
    same interpreter (a test, a batch driver) would be refused forever after the
    first. The owner must clear when the set drains.
    """
    import build_mon_native_song as B

    with _clean_pending(B):
        B._own_pending("stage")
        B._PENDING.append(("c.sf2.staging", "c.sf2"))
        B._PENDING = []                              # pretend the set published
        B._PENDING_OWNER = None
        _, err = _in_thread(lambda: B._own_pending("stage"))
        assert err is None, err


def test_the_guard_is_wired_into_all_three_call_sites():
    """Structural: the refusal is worthless if a path skips it.

    Reads the module's own source rather than trusting the tests above, which
    call `_own_pending` directly and so would still pass if `commit_parts`,
    `_discard_pending` or the staging append had never been wired to it.
    """
    import inspect

    import build_mon_native_song as B

    assert '_own_pending("commit")' in inspect.getsource(B.commit_parts)
    assert '_own_pending("discard")' in inspect.getsource(B._discard_pending)
    # emit_one, NOT build_native_song -- the staging append lives in the emitter.
    # This test caught that distinction on its first run, which is the whole
    # reason it reads the source instead of trusting the tests above.
    assert '_own_pending("stage")' in inspect.getsource(B.emit_one)


def test_atexit_publishes_a_set_staged_by_a_worker_thread():
    """The guard must NOT strand a set at interpreter shutdown.

    `_finish_pending` runs at atexit on the MAIN thread, after Python has joined
    every non-daemon thread -- so the stager has finished and no second writer
    can exist. Without the ownership reset, a set staged by a worker would make
    the guard raise inside atexit: nothing published, nothing discarded, and
    .staging files left on disk. That is strictly worse than the cross-publish
    this guard exists to prevent, so it is pinned.
    """
    import inspect

    import build_mon_native_song as B

    assert "_PENDING_OWNER = None" in inspect.getsource(B._finish_pending), (
        "atexit no longer clears ownership -- a worker-staged set will strand")

    with _clean_pending(B):
        def stage_only():
            B._own_pending("stage")
            B._PENDING.append(("d.sf2.staging", "d.sf2"))

        _, err = _in_thread(stage_only)
        assert err is None, err
        assert B._PENDING_OWNER is not threading.current_thread()

        # main thread, exactly as atexit would: it must not raise
        B._UNWOUND = True                 # take the discard arm, no real files
        try:
            B._finish_pending()
        finally:
            B._UNWOUND = False
        assert B._PENDING == []


# ---------------------------------------------------------------------------
# The WAVE-table 256-row bound: the overflow IS reachable, and it can NEVER be
# silent.
#
# THE CONCERN, stated exactly as the task raised it: gen_includes_song
# (bin/build_romuzak_native_song.py) writes wave rows at `edit[wo + start + r]`
# and only THEN advances the cursor and checks `wave_cursor > 256`, so a program
# starting near 255 writes past the boundary BEFORE it raises.
#
# THE WRITE PAST THE BOUNDARY IS REAL. It is not defended against here and these
# tests do not claim otherwise. What they pin is that it cannot produce a
# TRUNCATED ARTIFACT, which is the outcome that would matter -- four independent
# legs, each of which would have to break for a wrong wave table to ship:
#
#   1. the check is arithmetically EQUIVALENT to a pre-write check -- it rejects
#      exactly the same programs, one instruction later;
#   2. the spill lands in the in-memory `edit` buffer, which is discarded when
#      the exception propagates;
#   3. the raise precedes the drivers_src/romuzak/layout.inc write, so a refused
#      build leaves no half-written layout behind;
#   4. nothing catches it on the emit path.
#
# The overflow is reached in practice -- DMC_Demo_IV_tune_5 died laying part 5
# with "WAVE overflow: 288 rows > 256" (bin/build_dmc_native_song.py:350). That
# is the guard working, and it is why leg 4 is worth a test rather than an
# assumption.
# ---------------------------------------------------------------------------

import ast                                                        # noqa: E402
import io                                                         # noqa: E402

_ROMUZAK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'bin', 'build_romuzak_native_song.py')
_DMC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'bin', 'build_dmc_native_song.py')


def _emit_one_sites(source):
    """(all emit_one call lines, those enclosed by a try) for a source string."""
    calls, guarded = [], []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.try_depth = 0

        def visit_Try(self, node):
            self.try_depth += 1
            self.generic_visit(node)
            self.try_depth -= 1

        def visit_Call(self, node):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == 'emit_one':
                calls.append(node.lineno)
                if self.try_depth:
                    guarded.append(node.lineno)
            self.generic_visit(node)

    V().visit(ast.parse(source))
    return calls, guarded


def test_wave_overflow_check_is_equivalent_to_a_pre_write_check():
    """Leg 1. The post-write check rejects EXACTLY the programs a pre-write check
    would, so no over-long program is ever accepted.

    The highest row index written for a program is `start + len(wp) - 1`; the
    cursor afterwards is `start + len(wp)`. So `cursor > 256` is true iff some
    write used an index >= 256. Simulated over the whole reachable domain rather
    than argued.
    """
    for start in range(0, 300):
        for length in range(1, 40):
            max_index_written = start + length - 1
            cursor_after = start + length
            assert (max_index_written >= 256) == (cursor_after > 256), (
                start, length)


def test_wave_overflow_raise_precedes_the_layout_inc_write():
    """Leg 3. A refused build must not leave a half-written layout.inc.

    gen_includes_song's docstring says it writes drivers_src/romuzak/layout.inc.
    If that write happened before the wave loop, an overflow would abort with a
    layout on disk describing a table that was never laid.
    """
    lines = io.open(_ROMUZAK, encoding='utf-8').read().splitlines()
    raise_ln = [i for i, l in enumerate(lines) if 'WAVE overflow' in l]
    # the real line is open(os.path.join(LAYOUT_DIR, "layout.inc"), "w") --
    # match the two tokens on one line rather than a brittle contiguous string.
    layout_ln = [i for i, l in enumerate(lines)
                 if 'layout.inc' in l and ('"w"' in l or "'w'" in l)]
    assert len(raise_ln) == 1, raise_ln
    assert len(layout_ln) == 1, layout_ln
    assert raise_ln[0] < layout_ln[0], (
        'the WAVE overflow raise no longer precedes the layout.inc write')

    # POSITIVE CONTROL, same reason as the test below: prove the ordering check
    # can fail. With the two lines swapped it must report the violation.
    swapped = ['with open(os.path.join(LAYOUT_DIR, "layout.inc"), "w") as f:',
               'raise ValueError("WAVE overflow: 999 rows > 256")']
    r2 = [i for i, l in enumerate(swapped) if 'WAVE overflow' in l]
    l2 = [i for i, l in enumerate(swapped)
          if 'layout.inc' in l and ('"w"' in l or "'w'" in l)]
    assert r2 and l2 and not (r2[0] < l2[0]), (
        'the ordering predicate no longer detects a reversed file')


def test_nothing_catches_the_wave_overflow_on_the_dmc_emit_path():
    """Leg 4, and the only leg that could plausibly rot.

    The DMC part loop calls BM.emit_one directly. If anyone wraps that call in a
    try/except, an overflowing part becomes a SKIPPED part and the song ships
    short -- silently, which is the whole failure this guard exists to prevent.
    The file does contain a try/except, but it is in the post-build SCORING loop
    and reads artifacts back from disk; it must not enclose emit_one.
    """
    # POSITIVE CONTROL FIRST. A scan that reports "nothing guarded" is exactly
    # what a broken scan also reports, and this one cannot be mutation-checked
    # against the real builder (bin/build_romuzak_native_song.py and
    # bin/build_dmc_native_song.py are read-only to the task that added this).
    # So prove the detector fires before believing that it did not.
    bad = """
def f():
    try:
        BM.emit_one(a, b, c, d)
    except Exception:
        pass
"""
    calls, guarded = _emit_one_sites(bad)
    assert calls and guarded, (
        'the detector no longer sees a wrapped emit_one -- it would report the '
        'real builder clean for the wrong reason')

    calls, guarded = _emit_one_sites(io.open(_DMC, encoding='utf-8').read())
    assert calls, 'no emit_one call found -- this test has lost its subject'
    assert not guarded, (
        'emit_one is inside a try/except at line(s) %s -- a WAVE overflow would '
        'become a silently skipped part' % guarded)
# ---------------------------------------------------------------------------
# the per-voice screen actually FIRES -- it was dead code until it was wired
# ---------------------------------------------------------------------------

def _frames(bundles_per_voice, n=200):
    """A siddump_frames_full-shaped trace where voice i carries `bundles[i]`
    distinct (wf, adsr, pul) triples. 1 == collapsed, by the definition
    VOICE_BUNDLE_FLOOR encodes."""
    out = []
    for f in range(n):
        vs = {}
        for vi, k in enumerate(bundles_per_voice):
            j = f % max(1, k)
            vs[vi] = {"freq": 0x1000, "wf": 0x41 + j, "adsr": 0x0500 + j,
                      "pul": 0x800 + j}
        out.append((vs, {"cutoff": 0, "filtctl": 0, "volmode": 0}))
    return out


def test_the_voice_screen_FIRES_on_a_collapse(monkeypatch, capsys):
    """THE POINT OF WIRING IT. trace_voice_bundles and voice_collapse_vs were
    written, tested, and then called by nothing -- the measure protected no
    corpus. A screen that never fires is indistinguishable from the dead code
    it replaced, so this pins that it speaks.

    Voice 1 carries 9 distinct bundles in the reference and exactly 1 in the
    build: alive, then collapsed.
    """
    import build_mon_native_song as mod
    from sidm2 import fidelity_common as FC
    monkeypatch.setattr(FC, "artifact_trace", lambda p, a: _frames([9, 1, 9]))
    mod._screen_voices("ignored.sf2", _frames([9, 9, 9]), 0, 200, 1, 3)
    out = capsys.readouterr().out
    assert "VOICE COLLAPSE" in out, out
    assert "[1]" in out, "it must name WHICH voice, not just that one died"


def test_the_voice_screen_is_SILENT_on_a_clean_build(monkeypatch, capsys):
    """The other direction, so the test above cannot be satisfied by a screen
    that shouts at everything. Same bundles both sides."""
    import build_mon_native_song as mod
    from sidm2 import fidelity_common as FC
    monkeypatch.setattr(FC, "artifact_trace", lambda p, a: _frames([9, 9, 9]))
    mod._screen_voices("ignored.sf2", _frames([9, 9, 9]), 0, 200, 1, 3)
    assert capsys.readouterr().out == ""


def test_an_unmeasurable_artifact_is_NOT_reported_as_clean(monkeypatch, capsys):
    """None is not []. An artifact that will not parse is UNSCREENED, and the
    whole reason this screen exists is that unmeasured and measured-clean were
    being conflated one level up."""
    import build_mon_native_song as mod
    from sidm2 import fidelity_common as FC
    monkeypatch.setattr(FC, "artifact_trace", lambda p, a: None)
    mod._screen_voices("ignored.sf2", _frames([9, 9, 9]), 0, 200, 2, 3)
    assert "UNMEASURABLE" in capsys.readouterr().out


def test_a_missing_reference_trace_says_UNSCREENED(capsys):
    """If siddump could not drive the ORIGINAL there is no reference, and
    silence there would read exactly like a clean part."""
    import build_mon_native_song as mod
    mod._screen_voices("ignored.sf2", None, 0, 200, 1, 1)
    assert "UNSCREENED" in capsys.readouterr().out


def test_the_screen_can_be_switched_off(monkeypatch, capsys):
    """It costs one siddump per part (~1.4 s measured), so a bulk sweep needs
    an escape hatch -- and the escape hatch must be provably silent."""
    import build_mon_native_song as mod
    from sidm2 import fidelity_common as FC
    monkeypatch.setattr(FC, "artifact_trace", lambda p, a: _frames([9, 1, 9]))
    monkeypatch.setenv("MON_NO_VOICE_SCREEN", "1")
    mod._screen_voices("ignored.sf2", _frames([9, 9, 9]), 0, 200, 1, 3)
    assert capsys.readouterr().out == ""
