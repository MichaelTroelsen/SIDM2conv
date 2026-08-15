"""The tracked DMC sweep's logic, on synthetic frames -- no siddump, no builds.

`bin/_dmc_fidelity.py` produced every DMC figure in `DMC.md` and
`ACCURACY_MATRIX.md`, including "the best-evidenced number in the project", and
it is gitignored (`bin/_*.py`) and scores one part named on argv. Third instance
of the defect `soundmonitor_sweep.py` and `sdi_native_sweep.py` were promoted to
fix.

The behaviours pinned here are the ones that would let the sweep report a
comfortable number it has not earned.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dmc_native_sweep as sw  # noqa: E402
from sidm2.fidelity_common import MIN_INFORMATIVE_FRAMES  # noqa: E402


def frames(rows):
    """siddump_per_frame-shaped: ({voice: {freq,wf,pul}}, cutoff) per frame."""
    return [({vi: dict(freq=f, wf=w, pul=p) for vi, (f, w, p) in enumerate(r)}, None)
            for r in rows]


def _flat(freq, wf=0x41, pul=0x800, n=600):
    return frames([[(freq, wf, pul)] * 3] * n)


def test_it_reproduces_a_perfect_match():
    a = _flat(0x1000)
    per, n, dly = sw.score_pair(a, _flat(0x1000), 20)
    assert dly == 0 and n > 0
    for vi in per:
        assert {k: per[vi][k] for k in ("freq", "wf", "pul")} == {
            "freq": 100.0, "wf": 100.0, "pul": 100.0}


def test_the_audible_column_ignores_frames_where_both_sides_are_gated_off():
    """A voice that has not entered yet is silent on BOTH sides, but the two
    idle register states still differ -- the original holds whatever init left,
    ours holds the leading rest's. Scoring those answers a question nobody asked,
    and on a late-entering voice it DOMINATES: `Billie_Jean` v2 has 962 of 1,896
    frames before it enters, so raw wf reads 49.3% while all 190 frames it
    sounds are exact."""
    lead = [[(0x1000, 0x20, 0x800)] * 3] * 100     # gated off, both sides idle
    ours = [[(0x1000, 0xF0, 0x800)] * 3] * 100     # ...our idle waveform differs
    tail = [[(0x1000, 0x41, 0x800)] * 3] * 100     # gated on, both sides agree
    per, n, dly = sw.score_pair(frames(lead + tail), frames(ours + tail), 20)
    for vi in per:
        assert dly == 0 and per[vi]["wf"] < 55        # raw: ~half the window
        assert per[vi]["audible"]["wf"] == 100.0      # ...none of which sounded
        assert per[vi]["audible"]["freq"] == 100.0
        assert per[vi]["audible_n"] == 96   # n-4: the window's own tail trim


def test_the_audible_column_is_None_when_nothing_ever_gated_on():
    """Same discipline as `score_pct`: no audible frame is NO EVIDENCE, not a
    perfect score. A build that is silent end to end must not read 100."""
    a = frames([[(0x1000, 0x20, 0x800)] * 3] * 200)
    per, n, dly = sw.score_pair(a, a, 20)
    for vi in per:
        assert per[vi]["wf"] == 100.0
        assert per[vi]["audible"]["wf"] is None
        assert per[vi]["audible_n"] == 0


def test_a_defect_that_plays_is_NOT_hidden_by_the_audible_column():
    """The column exists to separate inaudible idle state from real loss -- not
    to launder a defect. A voice that is gated on and wrong must score wrong in
    BOTH columns."""
    a = frames([[(0x1000, 0x41, 0x800)] * 3] * 200)
    b = frames([[(0x1000, 0x11, 0x800)] * 3] * 200)
    per, n, dly = sw.score_pair(a, b, 20)
    for vi in per:
        assert per[vi]["wf"] == 0.0
        assert per[vi]["audible"]["wf"] == 0.0
        assert per[vi]["audible_n"] > 0


def test_a_register_neither_side_ever_wrote_is_None_not_100():
    """`score_pct`'s rule, and the one this repo has had to re-fix at every
    layer: 0/0 is 'no test ran'. A tune that never touches pulse must not bank
    a free 100% for it."""
    rows = [[(0x1000, 0x41, None)] * 3] * 600
    per, _n, _dly = sw.score_pair(frames(rows), frames(rows), 20)
    for vi in per:
        assert per[vi]["pul"] is None
        assert per[vi]["freq"] == 100.0


def test_freq_is_compared_as_a_SEMITONE():
    """Vibrato landing on the same note is not a note error -- the same rule
    every other scorer here uses."""
    per, _n, _dly = sw.score_pair(_flat(0x1000), _flat(0x1001), 20)
    assert per[0]["freq"] == 100.0, "one period unit apart is the same semitone"
    assert per[0]["wf"] == 100.0


def test_the_boot_offset_is_fitted():
    a = _flat(0x1000, n=600)
    late = frames([[(0, 0, 0)] * 3] * 4 + [[(0x1000, 0x41, 0x800)] * 3] * 596)
    _per, _n, dly = sw.score_pair(a, late, 20)
    assert dly != 0, "a delayed build must be aligned, not scored as wrong"


def test_an_empty_window_refuses_rather_than_scoring():
    per, n, _dly = sw.score_pair(_flat(0x1000, n=2), _flat(0x1000, n=2), 20)
    assert per is None and n == 0


def test_a_missing_build_is_not_a_zero():
    """32 of the 88 corpus files are NO-TABLES or FALLBACK and were never built.
    Scoring them 0 would make a BUILD gap look like a FIDELITY gap -- the exact
    conflation `DMC.md`'s own 'ELIGIBLE IS NOT AN ACCURACY FIGURE' box warns
    about."""
    rec = sw.measure("__definitely_not_a_corpus_file__", 20)
    assert rec.get("error"), "a missing source is an error, not a score"
    assert "voices" not in rec


def test_the_corpus_is_derived_not_named():
    """A named list is what let the headline rest on one file."""
    all_files = sw.corpus_files()
    assert len(all_files) > 50, "should be the whole tracked SID dir"
    assert "Balloon" in all_files
    assert sw.corpus_files(limit=3) == all_files[:3]
    assert sw.corpus_files(names=["Zoom"]) == ["Zoom"]


def test_a_thin_window_is_markable():
    """A DMC part can be a couple of seconds. Without `n` it prints the same
    confident 100.0 as Balloon's 19,996 frames."""
    from sidm2.fidelity_common import underpowered
    assert underpowered(MIN_INFORMATIVE_FRAMES - 1)
    assert not underpowered(19996)


def test_part1_span_is_read_from_the_builders_own_output():
    """The span is not in the SF2. It IS printed at build time, and reading it
    there is the only way a multi-part song gets an honest window."""
    out = ("  part 1/114 (0-8s, 0-400f): instr=29 bundles=44 filter=3\n"
           "  part 2/114 (8-16s, 400-800f): instr=29 bundles=44 filter=3\n")
    assert sw.part1_span(out) == 400
    assert sw.part1_span("no part line here") is None, \
        "absent must be None -- a caller treating it as 0 would score nothing"


def test_a_song_without_a_recorded_span_still_refuses(tmp_path, monkeypatch):
    """The guard, restated. It used to be "a multi-part song must refuse"; the
    span is no longer GUESSED but RECORDED (`.span`, written by the emitter), so
    refusing a recorded window would be refusing a measurement. What must still
    refuse is an artifact with no span at all.

    The mutation this guards is the first draft of this sweep: it scored part 1
    of `Cant_Stop` (114 parts, ~8 s) against the original's first 20 s and
    reported 34.8/86.0/91.5. That number measured the window, not the build.
    """
    import glob
    built = [n for n in sw.corpus_files()
             if glob.glob(os.path.join(sw.BUILD_DIR, f"{n}_part*.sf2"))]
    if not built:                      # nothing built in this checkout
        return
    # hide every sidecar from part_span without touching the tree
    monkeypatch.setattr(sw, "part_span", lambda _p: None)
    rec = sw.measure(built[0], None, build=False)
    assert rec.get("needs_bounds") is True, \
        "with no recorded span and no --seconds, refuse rather than guess"
    assert "voices" not in rec


def test_a_recorded_span_is_used_and_is_not_a_guess():
    """A `.span` beside the artifact is the window the emitter built, so it is
    scored -- and it is scored over THAT window, not the global default.

    This is the fix for a real published error: `Happy_Jingle`'s 7-second part 1
    was scored over 90 seconds because `part1_span` re-parsed the builder's log
    and `re.search` took a DISCARDED single-part trial split. It read
    23.4/16.1/8.1 where the part itself is 98.3/100.0/98.8.
    """
    import glob
    named = None
    for n in sw.corpus_files():
        parts = sorted(glob.glob(os.path.join(sw.BUILD_DIR, f"{n}_part*.sf2")))
        if parts and sw.part_span(parts[0]):
            named = (n, sw.part_span(parts[0]))
            break
    if not named:                      # no sidecars in this checkout
        return
    name, span = named
    rec = sw.measure(name, None, build=False)
    assert rec.get("voices"), "a recorded span must actually score"
    assert rec["n"] <= span * 50 + 4, \
        "scored past the part the span records -- the over-run this guards"


def test_part1_span_takes_the_last_trial_not_the_first():
    """The DMC builder prints a discarded `part 1/1` before its adaptive split
    settles, so the FIRST match is a window that was thrown away."""
    text = ("  part 1/1 (0-90s, 0-4500f): instr=13\n"
            "  part 1/2 (0-7s, 0-395f): instr=12\n"
            "  part 2/2 (7-90s, 395-4500f): instr=2\n")
    assert sw.part1_span(text) == 395, "must read the part actually emitted"


def test_an_asserted_window_is_honoured():
    rec = sw.measure("Balloon", 400, build=False)
    if rec.get("not_built"):
        return
    assert rec.get("voices"), "an asserted window must actually score"
    assert rec["n"] > 19000, "400s at 50fps"


def test_a_builder_refusal_is_not_an_error():
    """14 of 88 corpus files are NO-TABLES and 18 are FALLBACK. The builder
    declining a variant it cannot locate is designed behaviour; counting it as a
    fault reports 32 working refusals as 32 things going wrong. DMC.md carries
    an 'ELIGIBLE IS NOT AN ACCURACY FIGURE' box because this distinction has
    been lost here before."""
    rec = sw._classify_build_failure(
        "locating tables...\nDMC tables not located (variant?) - cannot build\n")
    assert "refused" in rec and "error" not in rec
    assert "not located" in rec["refused"]


def test_an_unknown_failure_stays_an_error():
    """A refusal list that swallows everything would hide a real break."""
    rec = sw._classify_build_failure("Traceback...\nZeroDivisionError: division by zero\n")
    assert "error" in rec and "refused" not in rec


def test_a_silent_build_failure_is_still_an_error():
    rec = sw._classify_build_failure("")
    assert rec["error"] == "build failed with no output"


def test_wave_overflow_is_a_builder_cap_not_a_crash():
    """`WAVE overflow: 288 rows > 256` is the same cap the SDI sweep hits on 16
    files. It is neither a designed refusal (the builder wanted to build this
    one) nor a crash, so it must stay visible as its own class rather than
    vanish into a bare `errored` count."""
    rec = sw._classify_build_failure("ValueError: WAVE overflow: 288 rows > 256")
    assert "error" in rec
    assert "WAVE overflow" in rec["error"], "the cause must survive to the report"
