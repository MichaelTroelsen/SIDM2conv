"""Myth builder: it must prune stale parts, like every other native builder.

WHY THIS FILE EXISTS. bin/build_myth_native_song.py emitted its parts and
returned. Nine sibling builders (blackbird, dmc, fc, hardtrack, hubbard,
mattgray, mon, sdi, soundmonitor) call prune_stale_parts after their part loop;
this one did not, so a rebuild that packed into FEWER parts than a previous era
left the old higher-numbered parts on disk. The inventory then reports phantom
files and a listener plays a stale tail -- the defect prune_stale_parts' own
docstring records (Supremacy_sub2 showed 70 files for a real 10-part build).

The source-level assertions are deliberate. A behavioural test alone would need
a full Myth build, which is minutes of py65 emulation; asserting the CALL SITES
exist catches the regression that actually happened -- somebody adding an emit
path and forgetting the prune -- at no cost.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bin"))

MYTH = ROOT / "bin" / "build_myth_native_song.py"


def _src() -> str:
    return MYTH.read_text(encoding="utf-8")


def _prune_calls() -> list[str]:
    """Every BM.prune_stale_parts(...) call, with balanced parens.

    A naive regex of the form prune_stale_parts\\([^)]*\\) does NOT work here and
    silently matches half a call: the argument is os.path.join(...), so the
    negated-paren class stops at that inner close-paren. It cost this file two
    red tests before the pattern was replaced by a scan for the MATCHING paren.
    """
    src = _src()
    out: list[str] = []
    needle = "BM.prune_stale_parts("
    i = src.find(needle)
    while i != -1:
        j = i + len(needle) - 1
        depth = 0
        while j < len(src):
            if src[j] == "(":
                depth += 1
            elif src[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append(src[i:j + 1])
        i = src.find(needle, j)
    return out


def test_the_adaptive_part_loop_is_followed_by_a_prune():
    """The multi-part path must prune to len(bounds)."""
    calls = _prune_calls()
    assert calls, "the Myth builder does not prune at all"
    assert any(c.rstrip().endswith("len(bounds))") for c in calls), (
        "the adaptive path must prune to len(bounds); found: %r" % calls)


def test_the_single_part_path_prunes_too():
    """The non-adaptive path emits ONE part and must drop 02..NN left by a
    previous adaptive era. This is the half that is easy to forget, because it
    returns early."""
    calls = _prune_calls()
    assert any(c.rstrip().endswith(", 1)") for c in calls), (
        "the single-part early-return path must prune to 1; found: %r" % calls)


def test_every_emit_path_has_a_prune():
    """Count-based backstop: as many prune calls as emit_one calls, so a third
    emit path fails here instead of silently leaving stale parts behind."""
    emits = _src().count("BM.emit_one(")
    prunes = len(_prune_calls())
    assert emits == prunes, (
        "%d emit_one call(s) but %d prune_stale_parts call(s) -- every emit path "
        "needs one" % (emits, prunes))


def test_the_prune_target_is_the_mon_output_dir():
    """Myth is a MoN-family builder and writes into out/mon/, so the prune prefix
    must point there -- pruning the wrong directory is a silent no-op."""
    for call in _prune_calls():
        assert '"out", "mon"' in call or "'out', 'mon'" in call, call


def test_pruning_a_myth_named_part_set_leaves_exactly_the_new_count(tmp_path):
    """The behaviour itself, on Myth's real naming, without a full build.

    A rebuild going 8 parts -> 3 must leave exactly 3, and must take each part's
    .span sidecar with it -- spans were once orphaned because nothing globs them,
    so the only symptom was the phantom-file inventory.
    """
    BM = pytest.importorskip("build_mon_native_song")
    prefix = str(tmp_path / "Myth_sub0")
    for n in range(1, 9):
        Path(f"{prefix}_part{n:02d}.sf2").write_bytes(b"x")
        Path(f"{prefix}_part{n:02d}.sf2.span").write_text("s")

    BM.prune_stale_parts(prefix, 3)

    sf2 = sorted(p.name for p in tmp_path.glob("*.sf2"))
    spans = sorted(p.name for p in tmp_path.glob("*.sf2.span"))
    assert sf2 == [f"Myth_sub0_part{n:02d}.sf2" for n in (1, 2, 3)], sf2
    assert spans == [f"Myth_sub0_part{n:02d}.sf2.span" for n in (1, 2, 3)], spans
