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
