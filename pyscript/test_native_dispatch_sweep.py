"""Guards for pyscript/native_dispatch_sweep.py.

THE ONE THAT MATTERS IS THE RETURN-SHAPE CONTRACT. A4's figures were re-measured
by a throwaway probe that INVENTED `rank()`'s return shape -- it read a
"candidates" list of dicts that does not exist -- got nothing, and printed
"exactly-one-and-correct: 0 of 60" with an EMPTY accept table. That number looked
exactly like a measurement and was a measurement of the probe's own bug. The
sweep now reads `rank()["dispatch"]["accepted"]`, `["signature"]`, `["best"]` and
`["confident"]`, and the first test below pins those four against the real
function so the shape cannot move out from under it silently.

The second guard is the one the docstring promises: a total of ZERO accepts is a
harness failure, not a result, because dmc and mon accept nearly every file by
construction. The sweep REFUSES to report in that case rather than publishing a
confident zero.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "pyscript"))

import native_dispatch_sweep as S  # noqa: E402
import sidm2.native_dispatch as N  # noqa: E402


# ---------------------------------------------------------------------------
# THE RETURN-SHAPE CONTRACT
# ---------------------------------------------------------------------------

def _a_real_sid():
    import glob
    for fam, rel in sorted(S.CORPORA.items()):
        hits = sorted(glob.glob(os.path.join(ROOT, rel, "*.sid")))
        if hits:
            return hits[0]
    return None


def test_rank_returns_the_four_keys_the_sweep_actually_reads():
    """BEHAVIOURAL, against the real function -- not a restatement of the code.

    If `rank()` ever stops returning one of these, the sweep must fail loudly
    here rather than silently measuring nothing. This is the test that would
    have caught the invented-shape probe described in the module docstring."""
    p = _a_real_sid()
    if p is None:
        pytest.skip("no SID corpus on this machine")
    r = N.rank(p)
    assert isinstance(r, dict), type(r)
    assert "dispatch" in r, sorted(r)
    assert "accepted" in r["dispatch"], sorted(r["dispatch"])
    assert isinstance(r["dispatch"]["accepted"], (list, tuple)), r["dispatch"]["accepted"]
    for k in ("signature", "best", "confident"):
        assert k in r, "rank() no longer returns %r; the sweep reads it -- %s" % (k, sorted(r))
    # and the sweep's own reader must survive the same call
    row = S.measure_one("dmc", p)
    assert "error" not in row, row
    assert isinstance(row["accepted"], list)


def test_a_MISSING_file_yields_no_accepts_rather_than_raising():
    """MEASURED, and it is the reason the vacuity guard is not optional.

    `rank()` does NOT raise on a nonexistent path -- it returns an ordinary
    result with `accepted: []`. So a single typo in a CORPORA path does not
    crash the sweep: it produces a full run in which no probe accepts anything,
    which is indistinguishable from 'the dispatcher rejects everything' unless
    something refuses to report it. That something is `vacuous()`.

    This test pins the behaviour rather than the wish. The first version of it
    asserted an `error` key and FAILED, which is how the real behaviour was
    found -- worth keeping as a comment because the wrong expectation is the
    intuitive one."""
    row = S.measure_one("dmc", os.path.join(ROOT, "does_not_exist_xyz.sid"))
    assert row["accepted"] == [], row
    assert not row.get("error"), (
        "rank() now raises on a missing file -- if so the vacuity guard is no "
        "longer the only thing catching a typo'd CORPORA path, and this test "
        "should be rewritten rather than relaxed")
    # and the consequence: a whole sweep of missing files is REFUSED, not reported
    rows = [S.measure_one("dmc", os.path.join(ROOT, "nope_%d.sid" % i)) for i in range(5)]
    assert S.vacuous(rows, S.summarise(rows)), (
        "a sweep over paths that do not exist must refuse, because rank() is "
        "happy to report nothing at all")


# ---------------------------------------------------------------------------
# THE VACUITY GUARD
# ---------------------------------------------------------------------------

def test_zero_accepts_is_REFUSED_rather_than_reported():
    """The guard the module exists to carry.

    dmc and mon accept nearly every file, so a total of zero accepts can only be
    the harness failing. Reporting `0 of N` there publishes this script's bug as
    a finding about the repo -- which is precisely what happened once."""
    rows = [dict(family="dmc", file="a.sid", accepted=[], signature=[],
                 best=None, confident=False) for _ in range(10)]
    s = S.summarise(rows)
    assert s["accepts"] == {}
    msg = S.vacuous(rows, s)
    assert msg, "a sweep where NO probe accepted ANY file must refuse to report"
    assert "harness" in msg.lower()


def test_an_empty_sample_is_also_refused():
    """Zero files is the other way to print a meaningless zero."""
    assert S.vacuous([], S.summarise([]))


def test_a_healthy_run_is_NOT_refused():
    """The guard must discriminate, not just fire -- otherwise it would block
    every real run and get deleted."""
    rows = [dict(family="dmc", file="a.sid", accepted=["dmc", "mon"], signature=[],
                 best=None, confident=False)]
    assert S.vacuous(rows, S.summarise(rows)) is None


# ---------------------------------------------------------------------------
# CORRECTNESS IS EXCLUSIVE, AND THE SAMPLE IS STATED
# ---------------------------------------------------------------------------

def test_exactly_one_and_correct_requires_EXCLUSIVITY():
    """A file its own family accepts ALONGSIDE dmc and mon is not a win -- it is
    the collision that makes first_match unsafe, which is A4's finding. Counting
    it as correct would invert the conclusion."""
    rows = [
        dict(family="sdi", file="x", accepted=["sdi"], signature=[], best="sdi", confident=True),
        dict(family="sdi", file="y", accepted=["sdi", "dmc", "mon"], signature=[],
             best="sdi", confident=True),
    ]
    s = S.summarise(rows)
    assert s["exactly_one_and_correct"] == 1, s
    assert s["best_is_own_family"] == 2, s


def test_CORPORA_names_only_families_that_have_a_probe():
    """A family with no probe can never be correct for its own files, so listing
    one drags the headline toward zero. Measured: adding galway and deenen (no
    probes) turned a real 2-of-48 into a confident 0-of-60."""
    unprobed = set(S.CORPORA) - S.probed_families()
    assert not unprobed, (
        "CORPORA names %s, which PROBE_ORDER has no probe for" % sorted(unprobed))


def test_the_sweep_PRINTS_the_files_it_drew(capsys):
    """The half both prior runs omitted. Without the filenames, 'first 6
    alphabetically' and '6 spread across each corpus' cannot be compared, and
    three per-probe movements could not be told from sampling noise."""
    import glob
    if not glob.glob(os.path.join(ROOT, "SID", "*", "*.sid")):
        pytest.skip("no SID corpus on this machine")
    rc = S.main(["--per-corpus", "1", "--families", "dmc"])
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "sample rule:" in out, out
    assert ".sid" in out, "the sweep must name the files it used, not just count them"


def test_the_sample_rule_is_reproducible_for_a_given_seed():
    """--schedule random is only useful if the draw can be repeated, which is
    the property the 2026-08-17 run lacked."""
    import glob
    if not glob.glob(os.path.join(ROOT, "SID", "*", "*.sid")):
        pytest.skip("no SID corpus on this machine")
    a = S.sample(3, "random", 7)
    b = S.sample(3, "random", 7)
    c = S.sample(3, "random", 8)
    assert a == b, "same seed must draw the same files"
    if len(a) > 2:
        assert a != c, "a different seed should draw differently"
