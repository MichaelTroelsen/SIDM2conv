"""Tests for pyscript/corpus_bundle_audit.py.

THE FIRST TEST IS THE REASON THIS SCRIPT EXISTS. The throwaway that produced
the 2026-09-04 reference numbers called `bundle_diversity(f)` and then
`bundle_collapse(f)` -- and the latter calls the former again. Every file was
parsed TWICE: 13,580 parses for 6,790 files, ~48 minutes for ~24 minutes of
work. Nothing detected it, because the result was correct; only the cost was
wrong. `test_measure_parses_each_file_exactly_ONCE` is what makes that
regression loud instead of invisible.

The classification tests drive `audit()` against a fake corpus tree, so they
need no built artifacts and run in milliseconds. The two control-artifact tests
use the real ones and SKIP when out/ is absent, which it is on a fresh clone
(out/ is gitignored).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pyscript"))

import corpus_bundle_audit as A          # noqa: E402


# ---------------------------------------------------------------------------
# The cost property -- one parse per file
# ---------------------------------------------------------------------------

def test_measure_parses_each_file_exactly_ONCE(monkeypatch):
    """The defect this script was written to avoid, pinned.

    Deliberately counts CALLS rather than timing anything: a wall-clock
    assertion would be flaky and would not say WHY it got slower. Calling
    bundle_collapse() alongside bundle_diversity() is the specific mistake, and
    it doubles this number.
    """
    calls = []

    def counting(path):
        calls.append(path)
        return {"bundles": 9, "notes": 100, "per_table": {}}

    monkeypatch.setattr(A, "bundle_diversity", counting)
    A.measure("anything.sf2")
    assert calls == ["anything.sf2"], (
        "measure() made %d parse(s); it must make exactly one -- calling "
        "bundle_collapse as well re-parses the file" % len(calls))


def test_measure_reports_unmeasurable_as_None_not_as_zero(monkeypatch):
    """None is NOT a collapse. Conflating 'could not read' with 'read and found
    nothing' is the defect this whole screen exists to keep apart."""
    monkeypatch.setattr(A, "bundle_diversity", lambda p: None)
    assert A.measure("x.sf2") == (None, None)

    def boom(p):
        raise ValueError("corrupt")

    monkeypatch.setattr(A, "bundle_diversity", boom)
    assert A.measure("x.sf2") == (None, None)


# ---------------------------------------------------------------------------
# Classification, against a fake corpus
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_corpus(tmp_path, monkeypatch):
    """A tiny out/ tree plus a canned measurement per filename."""
    (tmp_path / "out" / "dmc").mkdir(parents=True)
    names = {
        "clean.sf2": (24, 6000),
        "collapsed.sf2": (2, 400),
        "at_the_floor.sf2": (5, 300),      # <= floor, so flagged
        "just_above.sf2": (6, 300),        # the 1,569-artifact population
        "unreadable.sf2": (None, None),
        "EMPTYTRACE_CONTROL_part01.sf2": (2, 424),
    }
    for n in names:
        (tmp_path / "out" / "dmc" / n).write_bytes(b"x")
    monkeypatch.setattr(A, "ROOT", str(tmp_path))
    monkeypatch.setattr(A, "measure", lambda p: names[Path(p).name])
    return names


def test_audit_flags_at_and_below_the_floor_only(fake_corpus):
    res = A.audit(corpora=("dmc",))
    flagged = {Path(r["path"]).name for r in res["flagged"]}
    assert flagged == {"collapsed.sf2", "at_the_floor.sf2",
                       "EMPTYTRACE_CONTROL_part01.sf2"}
    assert "just_above.sf2" not in flagged, "6 is above BUNDLE_FLOOR = 5"


def test_audit_keeps_unread_separate_from_flagged(fake_corpus):
    res = A.audit(corpora=("dmc",))
    assert [Path(p).name for p in res["unread"]] == ["unreadable.sf2"]
    assert all(Path(r["path"]).name != "unreadable.sf2" for r in res["flagged"]), (
        "an unreadable artifact is UNSCREENED, not collapsed")


def test_audit_labels_the_deliberate_controls(fake_corpus):
    res = A.audit(corpora=("dmc",))
    ctrl = [r for r in res["flagged"] if r["control"]]
    assert len(ctrl) == 1
    assert Path(ctrl[0]["path"]).name == "EMPTYTRACE_CONTROL_part01.sf2"


def test_exclude_controls_drops_them_so_the_exit_code_means_something(fake_corpus):
    res = A.audit(corpora=("dmc",), exclude_controls=True)
    names = {Path(r["path"]).name for r in res["flagged"]}
    assert "EMPTYTRACE_CONTROL_part01.sf2" not in names
    assert names == {"collapsed.sf2", "at_the_floor.sf2"}


def test_progress_is_called_so_a_long_sweep_is_not_silent(fake_corpus):
    lines = []
    A.audit(corpora=("dmc",), progress=lines.append)
    assert lines, "audit() emitted no progress at all"
    assert any("dmc" in ln for ln in lines)


# ---------------------------------------------------------------------------
# Scope decisions worth pinning
# ---------------------------------------------------------------------------

def test_blackbird_is_deliberately_not_in_the_corpus_list():
    """Excluded on purpose: its builds carry no .span and siddump cannot drive
    an LFT rip, so any number would be unjustifiable. Pinned so it is not added
    for looking like an omission."""
    assert "blackbird" not in A.CORPORA
    assert set(A.CORPORA) == {"dmc", "mon", "sdi", "hardtrack_native",
                              "fc", "soundmonitor"}


def test_exit_code_is_nonzero_only_when_something_is_flagged(fake_corpus, tmp_path):
    assert A.main(["--corpus", "dmc"]) == 1
    # nothing at or below the floor -> clean
    import corpus_bundle_audit as M
    A.audit  # noqa: B018 - keep the import meaningful
    M_measure = M.measure
    try:
        M.measure = lambda p: (24, 6000)
        assert A.main(["--corpus", "dmc"]) == 0
    finally:
        M.measure = M_measure


def test_json_output_round_trips(fake_corpus, tmp_path):
    out = tmp_path / "res.json"
    A.main(["--corpus", "dmc", "--json", str(out)])
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["floor"] == A.BUNDLE_FLOOR
    assert doc["scanned"] == 6
    assert len(doc["flagged"]) == 3
    assert doc["unread"] == ["out/dmc/unreadable.sf2"]


# ---------------------------------------------------------------------------
# The real controls -- skipped without a built corpus
# ---------------------------------------------------------------------------

def test_the_real_whole_trace_control_flags_and_the_voice1_one_does_not():
    """The screen is worthless if its positive control stops firing, and
    over-read if its documented blind spot silently starts firing."""
    whole = ROOT / "out" / "dmc" / "EMPTYTRACE_CONTROL_part01.sf2"
    v1 = ROOT / "out" / "dmc" / "EMPTYTRACE_V1_CONTROL_part01.sf2"
    if not (whole.exists() and v1.exists()):
        pytest.skip("built DMC corpus not present (out/ is gitignored)")

    wb, _ = A.measure(str(whole))
    vb, _ = A.measure(str(v1))
    assert wb is not None and vb is not None
    assert wb <= A.BUNDLE_FLOOR, (
        "the whole-trace control no longer flags -- the screen has stopped working")
    assert vb > A.BUNDLE_FLOOR, (
        "the voice-1-dead control now flags; that is the DOCUMENTED blind spot, "
        "so either the measure changed or the control did")
