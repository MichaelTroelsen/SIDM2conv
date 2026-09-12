"""Guards for pyscript/hardtrack_duration_law_sweep.py.

THE ONE THAT MATTERS IS THE SPAN UNIT. `.span` records SECONDS -- written by
`build_mon_native_song._write_span` ("Record the seconds this part covers") and
read back by `fidelity_common.part_span` ("Seconds part 1 of this build actually
covers"). Reading it as FRAMES produced TWO false refutations of a true law
before anyone noticed: Shogoon-Rave got a 4-second window instead of 24, too few
onsets to measure, and the law read as disproved.

So the sweep must multiply by 50, and that is asserted here both structurally
and BEHAVIOURALLY -- the behavioural half is the one that would survive someone
rewriting the expression.

The other guards are the ones the sweep's own docstring promises: a row with too
few gaps is reported `few` rather than scored, and a flat gap series is flagged
rather than credited with a meaningless 100%.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pyscript"))

import hardtrack_duration_law_sweep as S  # noqa: E402

pytestmark = pytest.mark.skipif(
    not os.path.isdir(S.BUILD_DIR),
    reason="out/hardtrack_native not present in this checkout")


# ---------------------------------------------------------------------------
# THE SPAN UNIT
# ---------------------------------------------------------------------------

def test_the_sweep_reads_part_span_and_scales_it_to_FRAMES():
    """STRUCTURAL half: the seconds -> frames conversion is present.

    `part_span` returns SECONDS; every frame index the sweep computes must be
    50x that. If this ever fails, check the behavioural test below before
    'fixing' it -- the expression may have moved rather than gone."""
    src = open(os.path.join(ROOT, "pyscript",
                            "hardtrack_duration_law_sweep.py"),
               encoding="utf-8").read()
    assert "part_span" in src, "the sweep no longer reads the .span sidecar"
    assert "* 50" in src, (
        "the seconds -> frames conversion is gone; a span read as FRAMES gives "
        "a window ~50x too small, which is the error that produced two false "
        "refutations of this law")


def test_a_span_read_as_FRAMES_would_collapse_the_measurement():
    """BEHAVIOURAL half, and the point of the whole file.

    Take a real part, measure it correctly, then measure it again with the span
    treated as frames. The second must find drastically fewer gaps -- if the two
    agree, the guard above is protecting nothing and this sweep cannot tell the
    two readings apart."""
    songs = S.songs()
    if not songs:
        pytest.skip("no built HardTrack part01 artifacts")
    stem, orig, part = next((s for s in songs if s[0] == "Hopscotch"), songs[0])
    secs = S.part_span(part)
    assert secs, "%s has no .span sidecar" % stem
    assert 1 <= secs <= 600, (
        "%s span=%r -- that is not a plausible SECONDS value; if it looks like "
        "a frame count the sidecar contract has changed" % (stem, secs))

    import tempfile
    from sidm2.fidelity_common import siddump_frames_full
    frames = siddump_frames_full(orig, ["-a0", "-t%d" % (int(secs) + 2)])
    correct = S.gate_onsets(frames, 1, 0, int(secs) * 50)   # SECONDS -> frames
    wrong = S.gate_onsets(frames, 1, 0, int(secs))          # span read as FRAMES
    assert len(correct) > len(wrong), (
        "the two span readings produced the same onset count (%d), so this "
        "sweep cannot distinguish them" % len(correct))
    # Tie the bar to the sweep's OWN refusal threshold rather than to a number
    # I picked: the frames reading must leave too little to score at all, so a
    # run made that way is REFUSED as `few` instead of quietly reporting a
    # percentage. (Hopscotch: 96 gaps read correctly, 2 read as frames.)
    assert len(wrong) < S.MIN_N, (
        "a span read as frames still yields %d onsets, which is enough for the "
        "sweep to score -- so the misread would produce a NUMBER rather than a "
        "refusal, which is exactly how it went unnoticed twice" % len(wrong))
    assert len(correct) >= 10 * max(1, len(wrong)), (
        "correct=%d wrong=%d -- not the order-of-magnitude collapse a 50x "
        "window difference must produce" % (len(correct), len(wrong)))


# ---------------------------------------------------------------------------
# THE LAW, on named files rather than a whole-corpus run
# ---------------------------------------------------------------------------

#: Measured twice at head 57f1c7b, --onsets note --voice 1: these hold the law
#: at EXACTLY 100.0%. The full corpus figure is 20 of 29 scored (3 `few`,
#: 1 silent) -- NOT the 21 the task text quotes, because Ritual_II_tune_2 scores
#: 100.0% over n=2 and this sweep refuses it as underpowered.
LAW_EXACT = ["Hopscotch", "Jazzloor", "Zakplus"]

#: The inverse signature: high identity, low shift. These are the control that
#: makes the law a discrimination rather than something every file shows.
CLEAN = ["Sling", "Griffin_Score"]


def _row(stem):
    import tempfile
    songs = {s[0]: s for s in S.songs()}
    if stem not in songs:
        pytest.skip("%s not built" % stem)
    _stem, orig, part = songs[stem]
    with tempfile.TemporaryDirectory(prefix="ht_law_test_") as tmp:
        return S.measure(stem, orig, part, 1, tmp, "note")


@pytest.mark.parametrize("stem", LAW_EXACT)
def test_the_law_holds_exactly_on_these(stem):
    r = _row(stem)
    assert r["status"] == "ok", r
    assert r["shift"] == 100.0, r
    assert r["n"] >= S.MIN_N, r


@pytest.mark.parametrize("stem", CLEAN)
def test_the_clean_controls_show_the_INVERSE(stem):
    """Without these the law would be unfalsifiable: a measure that returned
    100% on every file would 'confirm' it everywhere."""
    r = _row(stem)
    assert r["status"] == "ok", r
    assert r["identity"] >= 90.0, r
    assert r["shift"] < 90.0, r


def test_gate_onsets_and_note_onsets_are_different_questions():
    """The law is TRUE of note rows and FALSE of gate rises, on the same songs
    and windows. Measuring it over gate rises reads as a refutation -- that
    happened once. Both entry points must stay reachable."""
    assert callable(S.gate_onsets) and callable(S.note_onsets)
    r_note = _row("Hopscotch")
    songs = {s[0]: s for s in S.songs()}
    if "Hopscotch" not in songs:
        pytest.skip("Hopscotch not built")
    import tempfile
    _s, orig, part = songs["Hopscotch"]
    with tempfile.TemporaryDirectory(prefix="ht_law_test_") as tmp:
        r_gate = S.measure("Hopscotch", orig, part, 1, tmp, "gate")
    assert r_note["shift"] == 100.0, r_note
    assert r_gate["shift"] != 100.0, (
        "gate rises show the same shift as note rows -- then the two readings "
        "are not the different questions this sweep says they are: %r" % r_gate)


def test_underpowered_and_flat_rows_are_refused_not_scored():
    """A 100.0% over two gaps is arithmetic, not evidence."""
    assert S.MIN_N >= 8, S.MIN_N
    assert S.MIN_DISTINCT >= 3, S.MIN_DISTINCT
    og = [8] * 20
    gg = [8] * 19
    m, n = S.agreement(gg, og[1:])
    assert m == n == 19, "a constant gap series satisfies every shift"
    assert len(set(og)) < S.MIN_DISTINCT, "...which is why it is flagged flat"


def test_the_gate_READING_is_degenerate_and_the_note_reading_is_not():
    """THE FLAG THAT COST THREE CYCLES, pinned so it is not re-derived a fourth
    time as "the law does not reproduce".

    `--onsets` defaults to "gate". Under gate rises the build reproduces the
    original's gaps exactly (identity 100.0 on 26 of 27 scored songs), and when
    gg == og the rate of gg[i] == og[i+1] is ALGEBRAICALLY the rate of
    og[i] == og[i+1] -- the ORIGINAL's own self-shift. The build has dropped out
    of the number, so a bare run prints LAW: 0 of 33 and reads exactly like a
    refutation.

    Under `--onsets note` the same corpus, the same artifacts and the same
    script give LAW: 20 of 33 with 6 clean controls -- reproducing the recorded
    figure to the song. Measured on the eight songs that run named:

        song                shift%   og[i]==og[i+1]
        Teekkno              100.0        99.0
        Muminki_Rooooolz     100.0        70.7
        Ritual_II_tune_1     100.0        50.0
        Timsoft_Intro        100.0        42.1
        What_Can_I_Say_Crap  100.0        95.7
        Tribute_to_Laxity    100.0        12.9     <-- 100 against 12.9
        Zakplus              100.0        41.5
        Walk_to_Soul         100.0        36.4

    Tribute_to_Laxity is the one that settles it: shift 100.0 while the original
    is only 12.9% self-shifted. That is a real discrimination, not a collapse.

    So this test pins BOTH halves -- the algebra that makes the gate reading
    degenerate, and the fact that the note reading is not.
    """
    import hardtrack_duration_law_sweep as S

    # HALF ONE: when gg == og, shift IS the original's self-shift. Six distinct
    # values, so MIN_DISTINCT would wave this straight through -- PERIODICITY,
    # not flatness, is what destroys the discrimination.
    og = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6] * 4
    gg = list(og)
    im, inn = S.agreement(gg, og)
    sm, sn = S.agreement(gg, og[1:])
    self_shift = sum(1 for i in range(len(og) - 1) if og[i] == og[i + 1])
    assert im == inn, "control: identity must be 100% when gg == og"
    assert len(set(og)) >= S.MIN_DISTINCT, (
        "the point is that MIN_DISTINCT does NOT exclude this series")
    assert sm == self_shift, (
        "shift counted %d agreements; the original's self-shift is %d. If these "
        "differ the collapse no longer holds and HARDTRACK.md must be re-read."
        % (sm, self_shift))
    assert 0 < sm < sn, "the fixture must be PARTIALLY periodic or this is vacuous"

    # HALF TWO: a genuinely shifted build is NOT degenerate -- shift 100% while
    # the original is barely self-shifted at all, the Tribute_to_Laxity shape.
    # built so NO two adjacent values are equal, including across the seam --
    # otherwise the fixture is partly self-shifted and proves less than it looks
    og2 = [(i * 7) % 11 + 1 for i in range(36)]
    gg2 = og2[1:] + [og2[0]]           # every note held for its SUCCESSOR's gap
    sm2, sn2 = S.agreement(gg2, og2[1:])
    im2, inn2 = S.agreement(gg2, og2)
    self2 = sum(1 for i in range(len(og2) - 1) if og2[i] == og2[i + 1])
    assert sm2 == sn2, "a truly shifted build must score shift 100%"
    assert im2 < inn2 * 0.5, "and identity must be LOW, or the two are not separable"
    assert self2 <= 1, (
        "the fixture's own self-shift must be near zero, or shift 100%% proves "
        "nothing about the build (self_shift=%d)" % self2)


def test_the_default_onset_reading_is_note_not_gate():
    """A bare `py -3 pyscript/hardtrack_duration_law_sweep.py` must print the
    reading that DISCRIMINATES.

    With the old `gate` default it printed LAW: 0 of 33, which was recorded as a
    refutation of the law in three separate cycles before the flag was noticed.
    The degeneracy is pinned algebraically above; this pins the ergonomic half,
    which is what actually cost the time.
    """
    import re
    src = open(os.path.join(os.path.dirname(__file__),
                            "hardtrack_duration_law_sweep.py"), encoding="utf-8").read()
    m = re.search(r'add_argument\(\s*"--onsets".*?default=("?)(\w+)\1', src, re.S)
    assert m, "the --onsets argument or its default moved; re-read it before trusting this"
    assert m.group(2) == "note", (
        "--onsets defaults to %r. Under 'gate' the measure is degenerate "
        "whenever identity is high, and a bare run reads as a refutation of a "
        "law that holds on 20 of 33 songs under 'note'." % m.group(2))


def test_the_run_states_which_onset_reading_produced_its_numbers():
    """QUOTE THE READING WITH THE NUMBER, the same rule CLAUDE.md already
    applies to the measurement WINDOW. Two readings of this corpus give 20 and 0;
    a figure that does not say which one it came from is not quotable."""
    src = open(os.path.join(os.path.dirname(__file__),
                            "hardtrack_duration_law_sweep.py"), encoding="utf-8").read()
    assert "onset definition:" in src, (
        "the run no longer prints which onset reading it used, so its LAW line "
        "can be quoted without the condition that makes it true")


def test_a_row_answering_YES_to_both_questions_is_reported_as_ambiguous():
    """`shift` and `identity` ask OPPOSITE questions. A row scoring high on both
    is answering neither, because a sufficiently PERIODIC original satisfies the
    shift trivially. The module docstring has said so since it was written and
    nothing enforced it, so three such rows were counted toward the headline
    LAW figure -- including Shogoon-Rave, the file the law was first attributed
    on (shift 100.0, identity 93.5).

    MIN_DISTINCT cannot screen them: they carry 3 to 6 distinct values. The
    corpus figure moves 20 -> 17 discriminating rows.
    """
    import hardtrack_duration_law_sweep as S
    assert S.AMBIG_BOTH == 90.0, S.AMBIG_BOTH

    src = open(os.path.join(os.path.dirname(__file__),
                            "hardtrack_duration_law_sweep.py"), encoding="utf-8").read()
    assert 'row["status"] = "ambiguous"' in src, (
        "the both-high guard is gone; a periodic original will be counted as law again")
    assert "AMBIGUOUS" in src, (
        "the run no longer REPORTS the ambiguous rows, so they vanish silently "
        "instead of being visible as unanswered")

    # the guard must not swallow a DISCRIMINATING row: Tribute_to_Laxity's shape
    # is shift 100.0 against identity 12.5, and that must stay `ok`.
    assert S.AMBIG_BOTH > 12.5, "the threshold must leave a genuine law row alone"


def test_the_ambiguous_rows_are_excluded_from_the_law_count_not_just_labelled():
    """Labelling them and still counting them would be worse than not labelling
    them at all -- the number would keep its inflation while looking audited."""
    src = open(os.path.join(os.path.dirname(__file__),
                            "hardtrack_duration_law_sweep.py"), encoding="utf-8").read()
    assert 'ok = [r for r in rows if r["status"] == "ok"]' in src, (
        "the scored set is built some other way now; re-check that ambiguous "
        "rows are still outside it")
    assert 'law = [r for r in ok if r["shift"] == 100.0]' in src, (
        "the LAW count no longer derives from the `ok` set, so an ambiguous row "
        "may be counted again")


# ---------------------------------------------------------------------------
# THE SECOND RELATION, AND WHY IT IS HERE AT ALL
# ---------------------------------------------------------------------------

def test_the_two_relations_are_equivalent_on_a_CONSTRUCTED_law_series():
    """BEHAVIOURAL, and the point of recovering the 2026-09-04 relation.

    The corpus table dated 2026-09-04 measured `offset[k] == og[k] + C` with C
    swept per file; the 2026-09-10 sweep measured `gg[i] == og[i+1]`. They are
    equivalent by telescoping -- C cancels -- so they CANNOT split on one series
    in one window. Build a series that satisfies the law exactly and assert both
    relations see it, because the equivalence is what makes a future split
    diagnostic of the INPUTS rather than of the law.
    """
    import hardtrack_duration_law_sweep as S

    # an original with a deliberately NON-periodic gap sequence, so `identity`
    # cannot pass by accident the way a uniform grid lets it
    og = [5, 10, 5, 20, 10, 5, 15, 5, 10, 20, 5, 10]
    orig = [100]
    for g in og:
        orig.append(orig[-1] + g)
    # ours holds each note for its SUCCESSOR's length, at the documented -3 lead
    ours = [orig[k] + og[k] + S.LEAD_C for k in range(len(og))]

    gg = S.gaps(ours)
    sm, sn = S.agreement(gg, S.gaps(orig)[1:])
    assert sn >= S.MIN_N, sn
    assert 100.0 * sm / sn == 100.0, (sm, sn)

    C, hits, n = S.best_offset_c(ours, orig, S.gaps(orig))
    assert C == S.LEAD_C, C
    assert hits == n, (hits, n)

    # and the control: identity must NOT also be high, or the series could not
    # have discriminated the law from its negation in the first place
    im, inn = S.agreement(gg, S.gaps(orig))
    assert 100.0 * im / inn < S.AMBIG_BOTH, 100.0 * im / inn


def test_the_relation_crosscheck_is_NOT_asked_of_an_underpowered_row():
    """The first version of this cross-check flagged exactly two rows --
    Ritual_II_tune_2 (n=2) and Trance (n=5) -- and neither was a disagreement
    about the law. Below MIN_N `best_offset_c` DECLINES (C is None) while
    `shift` still divides by its 2 gaps and prints a confident 100.0, so the
    comparison reports a split whose only content is that one side refused.
    `None` means not asked and must stay distinguishable from False."""
    import hardtrack_duration_law_sweep as S

    short = [0, 5, 10]                      # 2 gaps, well under MIN_N
    C, hits, n = S.best_offset_c(short, short, S.gaps(short))
    assert C is None, (
        "best_offset_c fitted a constant to %d notes; below MIN_N it must "
        "decline, or the cross-check reads its refusal as a disagreement" % n)

    src = open(os.path.join(os.path.dirname(__file__),
                            "hardtrack_duration_law_sweep.py"), encoding="utf-8").read()
    assert "None if sn < MIN_N else" in src, (
        "the cross-check is no longer gated on MIN_N, so every underpowered row "
        "will be reported as a relation disagreement again")
    assert 'r.get("relations_agree") is not None' in src, (
        "the denominator counts rows that were never asked, which makes the "
        "headline '0 of 32' instead of '0 of 29' and overstates the coverage")


def test_the_crosscheck_result_is_REPORTED_even_when_it_is_zero():
    """A check that only speaks up when it fires is indistinguishable from a
    check that is not running -- which is how the 2026-09-04 table stood
    unchallenged for six days."""
    src = open(os.path.join(os.path.dirname(__file__),
                            "hardtrack_duration_law_sweep.py"), encoding="utf-8").read()
    assert "RELATIONS" in src, "the cross-check no longer prints a headline"
    assert "DISAGREE" in src
    i = src.index("RELATIONS")
    assert "if split:" in src[i:], (
        "the explanatory text must be conditional, but the COUNT must not be")


# ---------------------------------------------------------------------------
# THE DURATION LAW IS AN ALIGNMENT ARTIFACT. siddump force-displays every
# register on its first row, so the ORIGINAL always carries a frame-0 "onset"
# that is not a note-on. OUR render carries one only when its own first note
# does not fire at frame ~1 -- a voice whose first note sits at tick 0 fires
# there and MERGES with the force-display, costing our list one leading entry.
# Compared index-by-index, that reads the whole voice one note late, which is
# exactly what `shift` reported. Measured over the settled set: 17 of 17 LAW
# files have their voice's first note at tick 0 and 0 of 6 CLEAN files do.

def test_a_voice_starting_at_tick_0_is_not_late_it_is_MISSING_THE_PHANTOM():
    """The LAW shape: our first note merges with the force-display."""
    import hardtrack_duration_law_sweep as M
    # original: phantom at 0, then real notes every 25 frames
    oo = [0, 4, 29, 54, 79, 104, 129, 154, 179, 204]
    # ours: the SAME real notes at -3, with no separate phantom
    po = [f - 3 for f in oo[1:]]
    pct, C, n, which = M.aligned_fit(oo, po)
    assert which == "ours-real", which
    assert C == -3, C
    assert pct == 100.0, pct
    # and the NAIVE comparison is what manufactures the law
    gg, og = M.gaps(po), M.gaps(oo)
    m, k = M.agreement(gg, og[1:])
    assert k and m == k, "the naive shift must read 100%% on this shape"


def test_a_voice_starting_later_shows_its_own_phantom_and_reads_CLEAN():
    import hardtrack_duration_law_sweep as M
    oo = [0, 40, 65, 90, 115, 140, 165, 190, 215, 240]
    po = [1] + [f - 3 for f in oo[1:]]      # our own phantom, then the real notes
    pct, C, n, which = M.aligned_fit(oo, po)
    assert which == "ours-phantom", which
    assert C == -3 and pct == 100.0, (C, pct)


def test_aligned_fit_declines_rather_than_scoring_too_few_notes():
    """Below MIN_N it must return no hypothesis, not a confident 100% on 3 gaps."""
    import hardtrack_duration_law_sweep as M
    oo = [0, 4, 29, 54]
    pct, C, n, which = M.aligned_fit(oo, [f - 3 for f in oo[1:]])
    assert which is None, which
