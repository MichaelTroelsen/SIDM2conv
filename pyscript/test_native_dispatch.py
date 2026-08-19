"""Tests for sidm2/native_dispatch.py.

These pin the dispatcher's MECHANISM, deliberately not its current verdicts.
The measured fact that `dmc` and `mon` accept every file is a DEFECT the module
exists to document, and a test asserting it would fail the day someone fixes it
-- which is the wrong way round. So nothing here asserts "dmc accepts
everything"; the ROADMAP carries that measurement instead.

What is pinned is the behaviour that makes the module safe to build on:

  * a probe BUG must not read as a refusal (this actually happened -- see
    `test_probe_bug_raises_rather_than_reading_as_a_refusal`)
  * a collision must be visible, not resolved silently by probe order
  * the player-id prefilter may REORDER but must never EXCLUDE

The probes parse; they never build, render or siddump, so this file is cheap
enough to run beside a corpus job.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sidm2 import native_dispatch as ND  # noqa: E402


def a_real_sid():
    """Any one corpus file; the mechanism tests do not care which."""
    d = os.path.join(ROOT, "SID", "JohannesBjerregaard")
    fs = sorted(f for f in os.listdir(d) if f.endswith(".sid"))
    if not fs:
        pytest.skip("no corpus SIDs on this machine")
    return os.path.join(d, fs[0])


def test_probe_bug_raises_rather_than_reading_as_a_refusal(monkeypatch):
    """The regression test for a bug this module shipped with.

    `is_soundmonitor(data, la, h)` was called with two arguments; the TypeError
    was caught by a broad `except Exception` and recorded as "not a Sound
    Monitor rip", so the family silently rejected its OWN corpus while the run
    still looked clean. A caller error must never become a verdict about a file.
    """
    def broken(path):
        raise TypeError("takes 3 positional arguments but 2 were given")

    monkeypatch.setattr(ND, "PROBE_ORDER", (("dmc", broken),))
    with pytest.raises(ND.ProbeBug):
        ND.probe("dmc", a_real_sid())


@pytest.mark.parametrize("exc", [TypeError, AttributeError, NameError, ImportError])
def test_every_bug_exception_raises(monkeypatch, exc):
    def broken(path):
        raise exc("boom")

    monkeypatch.setattr(ND, "PROBE_ORDER", (("dmc", broken),))
    with pytest.raises(ND.ProbeBug):
        ND.probe("dmc", a_real_sid())


def test_parser_refusal_is_a_verdict_not_a_bug(monkeypatch):
    """ValueError is how every parser here says 'not mine'. It must be caught."""
    def refuses(path):
        raise ValueError("decoded no notes on any voice")

    monkeypatch.setattr(ND, "PROBE_ORDER", (("dmc", refuses),))
    ok, reason = ND.probe("dmc", a_real_sid())
    assert ok is False
    assert "decoded no notes" in reason


def test_unimplemented_probe_reports_itself(monkeypatch):
    monkeypatch.setattr(ND, "PROBE_ORDER", (("hardtrack", None),))
    ok, reason = ND.probe("hardtrack", a_real_sid())
    assert ok is False
    assert reason == "no probe implemented"


def test_collision_is_reported_not_resolved(monkeypatch):
    """Two families accepting one file must BOTH appear.

    Silently taking the first is the failure mode that makes a dispatcher worse
    than no dispatcher, because the misroute looks like a fidelity problem.
    """
    monkeypatch.setattr(ND, "PROBE_ORDER",
                        (("dmc", lambda p: {"x": 1}), ("mon", lambda p: {"x": 2})))
    r = ND.dispatch(a_real_sid())
    assert r["accepted"] == ["dmc", "mon"], "a collision must stay visible"


def test_first_match_is_opt_in_and_stops_early(monkeypatch):
    monkeypatch.setattr(ND, "PROBE_ORDER",
                        (("dmc", lambda p: {"x": 1}), ("mon", lambda p: {"x": 2})))
    r = ND.dispatch(a_real_sid(), first_match=True)
    assert r["accepted"] == ["dmc"]


def test_prefilter_reorders_but_never_excludes(monkeypatch):
    """player-id verdicts are not exhaustive, so a prefilter may only reorder.

    Excluding on them would drop the 1-in-12 Blackbird file player-id cannot
    identify at all.
    """
    seen = []

    def rec(name):
        def f(path):
            seen.append(name)
            raise ValueError("nope")
        return f

    monkeypatch.setattr(ND, "PROBE_ORDER",
                        (("dmc", rec("dmc")), ("hubbard", rec("hubbard"))))
    r = ND.dispatch(a_real_sid(), player_id="Rob_Hubbard")
    assert r["prefilter"] == "hubbard"
    assert seen[0] == "hubbard", "the reliable verdict should be tried first"
    assert set(seen) == {"dmc", "hubbard"}, "every probe still runs"
    assert set(r["rejected"]) == {"dmc", "hubbard"}


def test_unreliable_player_id_sets_no_prefilter():
    """Soundmonitor is the verdict 10 of 12 Matt Gray files report. It must not
    steer anything."""
    r = ND.dispatch(a_real_sid(), player_id="Soundmonitor")
    assert r["prefilter"] is None


def test_reliable_ids_are_the_measured_three_families():
    assert set(ND.RELIABLE_PLAYER_IDS.values()) == {"galway", "hubbard", "blackbird"}


def test_dispatch_on_a_real_file_returns_the_documented_shape():
    r = ND.dispatch(a_real_sid())
    assert set(r) == {"accepted", "rejected", "prefilter"}
    assert isinstance(r["accepted"], list)
    assert isinstance(r["rejected"], dict)
    known = {p for p, _ in ND.PROBE_ORDER}
    assert set(r["accepted"]) | set(r["rejected"]) <= known


# --- rank(): evidence strength, not boolean accept -----------------------------
#
# Same discipline as above -- these pin the RANKING MECHANISM, never the current
# verdicts. That `blackbird` accepts 1 of 48 and `dmc` 48 of 48 is a measured
# property of today's parsers and belongs in ROADMAP A4, not in an assertion
# that would fail the day a parser improves.


def test_every_family_is_classified_as_signature_or_construct_only():
    """A family that is in neither set would silently never be rankable."""
    named = {p for p, _fn in ND.PROBE_ORDER}
    classified = ND.SIGNATURE | ND.CONSTRUCT_ONLY | ND.UNPROBED
    assert named - classified == set(), "unclassified families: %s" % (
        named - classified)
    assert not (ND.SIGNATURE & ND.CONSTRUCT_ONLY)
    assert not (ND.SIGNATURE & ND.UNPROBED)
    assert not (ND.CONSTRUCT_ONLY & ND.UNPROBED)
    # every UNPROBED family really has no probe -- otherwise the label lies
    for name, fn in ND.PROBE_ORDER:
        if name in ND.UNPROBED:
            assert fn is None, "%s is labelled UNPROBED but has a probe" % name


def test_a_unique_signature_match_is_confident(monkeypatch):
    monkeypatch.setattr(ND, "PROBE_ORDER",
                        (("sdi", lambda p: {"ok": 1}),
                         ("dmc", lambda p: {"ok": 1}),
                         ("mon", lambda p: {"ok": 1})))
    r = ND.rank("x.sid")
    assert r["best"] == "sdi" and r["confident"] is True
    assert r["weak"] == ["dmc", "mon"]


def test_two_signature_families_colliding_abstains(monkeypatch):
    """A collision must never be resolved by probe order -- same rule dispatch()
    follows, carried into the ranking."""
    monkeypatch.setattr(ND, "PROBE_ORDER",
                        (("sdi", lambda p: {"ok": 1}),
                         ("soundmonitor", lambda p: {"ok": 1})))
    r = ND.rank("x.sid")
    assert r["best"] is None and r["confident"] is False
    assert "collision" in r["why"]


def test_construct_only_families_alone_never_produce_an_answer(monkeypatch):
    """THE GUARD ON THE REFUTED DESIGN. Promoting a construct-only family when
    no signature family accepts was implemented, measured and removed: it
    answered 6 more files and got 2 wrong, dropping precision 75.0 -> 71.4.
    This fails if that path comes back."""
    def acc(p):
        return {"ok": 1}
    monkeypatch.setattr(ND, "PROBE_ORDER",
                        (("dmc", acc), ("mon", acc), ("hubbard", acc)))
    r = ND.rank("x.sid", player_id="Rob_Hubbard")   # a RELIABLE verdict
    assert r["best"] is None, "a construct-only family was promoted"
    assert r["confident"] is False
    assert set(r["weak"]) == {"dmc", "mon", "hubbard"}


def test_rank_abstains_when_nothing_accepts(monkeypatch):
    def refuses(p):
        raise ValueError("not mine")
    monkeypatch.setattr(ND, "PROBE_ORDER", (("sdi", refuses), ("dmc", refuses)))
    r = ND.rank("x.sid")
    assert r["best"] is None and r["confident"] is False


def test_rank_exposes_the_underlying_dispatch_result(monkeypatch):
    """The ranking must not hide the collision evidence dispatch() reports."""
    monkeypatch.setattr(ND, "PROBE_ORDER",
                        (("sdi", lambda p: {"ok": 1}), ("dmc", lambda p: {"ok": 1})))
    r = ND.rank("x.sid")
    assert r["dispatch"]["accepted"] == ["sdi", "dmc"]
