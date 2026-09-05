"""Tests for pyscript/graphify_root_fixup.py.

Every test here works on a TEMPORARY root file, never on the real
graphify-out/.graphify_root -- the real one is a live cache this repo's own
tooling reads, and a test that repairs it would pass by changing the thing it
is measuring.

The controls matter more than usual in this file. The failure being guarded is
SILENT: a stale root makes graphify answer queries against a directory that
does not exist, and it reports that as an empty result rather than an error. A
test that cannot tell "correctly detected broken" from "detected nothing" would
reproduce exactly the defect it is supposed to catch.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyscript.graphify_root_fixup import (  # noqa: E402
    inspect,
    repair,
    resolves_to_repo_root,
)


def _root_file(tmp_path: Path, value: str) -> Path:
    """A .graphify_root holding `value`, written the way graphify writes it:
    no trailing newline."""
    d = tmp_path / "graphify-out"
    d.mkdir(exist_ok=True)
    f = d / ".graphify_root"
    f.write_text(value, encoding="utf-8", newline="")
    return f


def test_the_git_bash_path_is_detected_as_broken(tmp_path):
    """The actual defect: /c/Users/... is not a Windows path.

    POSITIVE CONTROL FIRST -- the same helper must call the real repo root OK.
    Without it, a resolves_to_repo_root() that returned False for everything
    would pass this test while being useless.
    """
    assert resolves_to_repo_root(str(tmp_path), tmp_path) is True, (
        "the checker calls a REAL directory broken -- it would report every "
        "root as broken and the 'broken' assertion below would be vacuous")
    assert resolves_to_repo_root("/c/Users/mit/claude/c64server/sidm2", tmp_path) is False


def test_repair_writes_the_native_path_with_no_trailing_newline(tmp_path):
    f = _root_file(tmp_path, "/c/Users/mit/claude/c64server/sidm2")
    assert repair(f, tmp_path) is True
    raw = f.read_bytes()
    assert raw.decode("utf-8") == str(tmp_path)
    assert not raw.endswith(b"\n"), (
        "a trailing newline was added; graphify writes the bare path and an "
        "upstream string comparison could break on the difference")


def test_repair_is_idempotent_and_does_not_churn_a_working_value(tmp_path):
    """Second run must be a NO-OP, and a differently-CASED but working path
    must be left alone -- graphify itself wrote 'SIDM2' for a directory named
    'sidm2', and rewriting that would be churn in a file nobody reads."""
    f = _root_file(tmp_path, "/c/nope/does/not/exist")
    assert repair(f, tmp_path) is True
    before = f.read_bytes()
    assert repair(f, tmp_path) is False, "repaired a file that was already correct"
    assert f.read_bytes() == before

    upper = _root_file(tmp_path, str(tmp_path).upper())
    status, _ = inspect(upper, tmp_path)
    if Path(str(tmp_path).upper()).exists():      # case-insensitive filesystem
        assert status == "ok"
        assert repair(upper, tmp_path) is False
    else:
        pytest.skip("case-sensitive filesystem: the SIDM2/sidm2 case is moot")


def test_a_fresh_clone_with_no_graphify_out_is_absent_not_broken(tmp_path):
    """A clone that has never run /graphify has nothing to repair. Reporting
    that as 'broken' would send someone hunting a defect that is just an
    un-built cache."""
    status, recorded = inspect(tmp_path / "graphify-out" / ".graphify_root", tmp_path)
    assert status == "absent"
    assert recorded is None


def test_an_empty_or_whitespace_root_file_is_broken(monkeypatch, tmp_path):
    """An empty file resolves to Path('') -- which is '.', the CURRENT
    DIRECTORY. So this has to be tested with the CWD set to the repo root,
    because that is the only arrangement in which an empty value would
    otherwise read as correct.

    THE FIRST VERSION OF THIS TEST WAS VACUOUS and a mutation caught it: it
    passed tmp_path as the repo root while the CWD was elsewhere, so ''
    resolved to a DIFFERENT directory and was rejected by the samefile()
    check -- the empty-string guard was never reached, and deleting that guard
    left this test green. Pinned now: remove `if not text: return False` from
    resolves_to_repo_root() and this test must fail.
    """
    monkeypatch.chdir(tmp_path)
    for junk in ("", "   ", "\n"):
        f = _root_file(tmp_path, junk)
        status, _ = inspect(f, tmp_path)
        assert status == "broken", (
            "empty root %r read as %s -- with the CWD at the repo root an "
            "empty value resolves to it and looks correct" % (junk, status))


def test_a_valid_but_WRONG_directory_is_broken(tmp_path):
    """The check must be 'is it THIS repo', not 'does it exist'. A root
    pointing at some other real directory is the case that would otherwise
    produce a confidently empty graph."""
    other = tmp_path / "some_other_checkout"
    other.mkdir()
    f = _root_file(tmp_path, str(other))
    status, _ = inspect(f, tmp_path)
    assert status == "broken"
