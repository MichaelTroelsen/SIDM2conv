"""The Laxity accuracy sweep must not be able to invent a number.

This pins the three refusals the sweep's docstring promises, because each one is
a shape this repo has actually shipped:

  * a file that failed to convert scored 0% (unmeasured read as measured-zero);
  * a percentage printed without its n (a 46-frame voice and a 6000-frame voice
    both printing "100.0");
  * a validation that compared nothing scored 100% (vacuous agreement).

The tests drive `measure_one` with `_run` monkeypatched, so no conversion, no
emulation and no corpus access happens here -- what is under test is the
BOOKKEEPING, which is where all three failures live.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, _ROOT)

import laxity_accuracy_sweep as S                            # noqa: E402


class _FakeRun:
    """Stands in for the three subprocess steps, in order."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def __call__(self, cmd, timeout):
        self.calls.append(cmd)
        return self.results.pop(0) if self.results else (0, "")


def test_a_failed_conversion_is_an_ERROR_not_a_zero(tmp_path, monkeypatch):
    """The first refusal. A build that never produced an artifact has no score;
    recording 0.0 would drag a corpus mean down with a number nothing measured."""
    monkeypatch.setattr(S, "WORK", tmp_path)
    monkeypatch.setattr(S, "_run", _FakeRun([(1, "boom")]))
    row = S.measure_one(tmp_path / "Nope.sid", 30, 60)
    assert row["status"] == "error"
    assert row["frame_accuracy"] is None, "an error row must carry NO score, not 0.0"


def test_a_validation_that_compared_nothing_is_NO_FRAMES_not_100(tmp_path, monkeypatch):
    """The vacuous-agreement refusal, and the reason `exercised()` exists in
    fidelity_common: two empty captures agree perfectly."""
    monkeypatch.setattr(S, "WORK", tmp_path)
    (tmp_path / "Empty.sf2").write_bytes(b"x")
    (tmp_path / "Empty_rt.sid").write_bytes(b"x")
    (tmp_path / "Empty.json").write_text(
        json.dumps({"summary": {"frame_accuracy": 100.0}}), encoding="utf-8")
    # stdout carries no "Captured N frames" line -> nothing was compared
    monkeypatch.setattr(S, "_run", _FakeRun([(0, ""), (0, ""), (0, "no frames here")]))
    row = S.measure_one(tmp_path / "Empty.sid", 30, 60)
    assert row["status"] == "no-frames"
    assert row["frame_accuracy"] is None, (
        "a comparison with no frames reported 100% -- that is vacuous agreement")


def test_a_real_row_carries_its_n(tmp_path, monkeypatch):
    """The n is parsed from the validator's stdout because the comparison JSON
    has none. If that line ever changes shape this fails rather than silently
    reporting a percentage with frames=None."""
    monkeypatch.setattr(S, "WORK", tmp_path)
    (tmp_path / "Real.sf2").write_bytes(b"x")
    (tmp_path / "Real_rt.sid").write_bytes(b"x")
    (tmp_path / "Real.json").write_text(
        json.dumps({"summary": {"frame_accuracy": 99.5}}), encoding="utf-8")
    out = "  Captured 1500 frames\n  Exact Frame Matches:   1490/1500 (99.33%)\n"
    monkeypatch.setattr(S, "_run", _FakeRun([(0, ""), (0, ""), (0, out)]))
    row = S.measure_one(tmp_path / "Real.sid", 30, 60)
    assert row["status"] == "ok"
    assert row["frames"] == 1500, "the frame count was not parsed from stdout"
    assert row["frame_accuracy"] == 99.5
    assert row["exact_match_pct"] == pytest.approx(99.33)


def test_the_validator_is_always_given_an_explicit_output_path(tmp_path, monkeypatch):
    """WITHOUT --output the validator writes validation_<stem>_<ts>.html into the
    CURRENT DIRECTORY -- the repo root. It is gitignored, so git status never
    shows it and the write is invisible; this run produced two such files before
    the flag was added. Pinned because the failure leaves no trace."""
    monkeypatch.setattr(S, "WORK", tmp_path)
    (tmp_path / "P.sf2").write_bytes(b"x")
    (tmp_path / "P_rt.sid").write_bytes(b"x")
    (tmp_path / "P.json").write_text(
        json.dumps({"summary": {"frame_accuracy": 100.0}}), encoding="utf-8")
    fake = _FakeRun([(0, ""), (0, ""), (0, "  Captured 10 frames\n")])
    monkeypatch.setattr(S, "_run", fake)
    S.measure_one(tmp_path / "P.sid", 30, 60)
    validate_cmd = fake.calls[-1]
    assert "--output" in validate_cmd, (
        "validate_sid_accuracy.py is being invoked without --output; it will "
        "write its HTML report into the repo root")
    assert "--comparison-json" in validate_cmd, (
        "--json writes the raw captures, not the comparison -- the first version "
        "of this script asked for the wrong file and every row read as an error")


def test_the_summary_reports_a_distribution_not_just_a_mean():
    """A lone mean over files of wildly different lengths is the shape CLAUDE.md
    warns about (a 1-second stinger averaged against a 2-minute song)."""
    rows = [{"status": "ok", "frame_accuracy": 100.0, "frames": 1500},
            {"status": "ok", "frame_accuracy": 90.0, "frames": 300},
            {"status": "error", "frame_accuracy": None, "frames": None},
            {"status": "no-frames", "frame_accuracy": None, "frames": None}]
    s = S.summarise(rows)
    assert s["measured"] == 2 and s["errors"] == 1 and s["no_frames"] == 1
    assert s["min"] == 90.0 and s["max"] == 100.0
    assert "mean" not in s, "a bare mean is exactly what this summary must not offer"
    assert s["n_frames_min"] == 300 and s["n_frames_max"] == 1500


def test_the_corpus_comes_from_the_selector_not_a_hand_list():
    """The previous measurement's population became unrecoverable because it was
    a hand-picked list held outside the tree. Read the source rather than calling
    it, so the check costs nothing and cannot be defeated by a stubbed selector."""
    src = open(os.path.join(_HERE, "laxity_accuracy_sweep.py"), encoding="utf-8").read()
    body = src[src.index("def laxity_corpus("):]
    body = body[:body.find("\ndef ", 1)] if body.find("\ndef ", 1) > 0 else body
    assert "DriverSelector" in body, "the corpus is no longer derived from the selector"
