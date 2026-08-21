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


# --- hardtrack: the family that was UNPROBED ----------------------------------
#
# Same discipline as the rest of this file: these pin the MECHANISM -- that the
# probe reaches its parser across the (load, data) argument inversion, that its
# refusals read as verdicts rather than bugs, and that it discriminates at all.
# They deliberately do NOT assert "33 of 150", because that count is a property
# of today's signature and would fail the day it learns a new variant. The
# measured breakdown lives in native_dispatch's own UNPROBED comment.

HT_ACCEPTED = "SID/Shogoon/Altered_States_Tune_1.sid"     # in the Stage B corpus
HT_NO_SIGNATURE = "SID/Shogoon/286AT_Heist.sid"           # no init pattern at all
HT_WRAPPED = "SID/Shogoon/Commercial_Fake.sid"            # PSID init != module entry
HT_MULTI_INSTANCE = "SID/Shogoon/Eternal.sid"             # 2 player instances


def test_hardtrack_is_a_signature_family_not_construct_only():
    """The whole point of the probe. A construct-only hardtrack would accept
    everything and add no evidence to the ranking; it is in SIGNATURE because
    four 6502 patterns must each match exactly once."""
    assert "hardtrack" in ND.SIGNATURE
    assert "hardtrack" not in ND.CONSTRUCT_ONLY
    assert "hardtrack" not in ND.UNPROBED
    assert dict(ND.PROBE_ORDER)["hardtrack"] is not None


def test_hardtrack_probe_crosses_the_argument_inversion():
    """HardTrackModule takes (load, data) where every other parser takes
    (data, la), and reads the PSID header itself. Getting that wrong raises
    TypeError -> ProbeBug, so an ACCEPT here is what proves the wiring."""
    ok, evidence = ND.probe("hardtrack", HT_ACCEPTED)
    assert ok, evidence
    assert set(evidence) == {"load", "init_off", "instrument_base", "tables"}
    assert isinstance(evidence["load"], int)


def test_hardtrack_refusals_are_verdicts_not_probe_bugs():
    """Every refusal path is a HardTrackError, which subclasses ValueError, so
    it must come back through probe()'s reject path -- never as ProbeBug."""
    for path in (HT_NO_SIGNATURE, HT_WRAPPED, HT_MULTI_INSTANCE):
        ok, reason = ND.probe("hardtrack", path)
        assert not ok, path
        assert "HardTrackError" in reason, (path, reason)


def test_hardtrack_refuses_a_wrapped_rip_rather_than_decoding_instance_zero():
    """A DESIGN DECISION, pinned so it is not 'fixed' into a false accept: a rip
    whose PSID vector is not the module's own entry, or which carries several
    player instances, is refused. Those files are HardTrack-ish and still must
    not be claimed -- decoding instance 0 would report the wrong song."""
    _, wrapped = ND.probe("hardtrack", HT_WRAPPED)
    assert "not the module entry" in wrapped
    _, multi = ND.probe("hardtrack", HT_MULTI_INSTANCE)
    assert "player instances" in multi


def test_hardtrack_discriminates_over_a_real_mixed_player_directory():
    """SID/Shogoon is tracked (150 files) and mixed-player, so this runs from a
    fresh clone in well under a second. Bounds, not a count: a signature family
    must accept SOME files and reject SOME, which is exactly what separates it
    from the construct-only families that accept everything."""
    import glob
    files = sorted(glob.glob("SID/Shogoon/*.sid"))
    assert len(files) > 100, "corpus missing -- this test needs SID/Shogoon"
    accepted = [f for f in files if ND.probe("hardtrack", f)[0]]
    assert 0 < len(accepted) < len(files)


def test_hardtrack_wins_over_the_construct_only_families_that_also_accept():
    """The ranking claim. dmc and mon accept this file too, but they accept
    almost everything, so they are `weak` and carry no evidence -- hardtrack is
    the unique signature match and rank() is therefore confident."""
    r = ND.rank(HT_ACCEPTED)
    assert r["signature"] == ["hardtrack"]
    assert r["best"] == "hardtrack" and r["confident"] is True


# --- mattgray: the probe that accepted nothing, and why it hid ----------------

MG_ACCEPTED = "SID/Gray_Matt/Driller.sid"          # the corroborated Matt Gray map
MG_REFUSED = "SID/Shogoon/286AT_Heist.sid"         # not Matt Gray at all


def test_mattgray_probe_reaches_its_parser():
    """It used to unpack a 6-value load_sid into 3 names and pass 2 args to a
    4-arg constructor. Either mistake makes this ACCEPT impossible."""
    ok, evidence = ND.probe("mattgray", MG_ACCEPTED)
    assert ok, evidence
    assert set(evidence) == {"load", "init", "play", "tables"}
    assert evidence["tables"], "locate() returned no tables"


def test_mattgray_still_refuses_a_file_from_another_family():
    ok, reason = ND.probe("mattgray", MG_REFUSED)
    assert not ok
    assert "MattGrayError" in reason


def test_mattgray_is_a_signature_family():
    """`locate()` raises when any table is unidentifiable, so an accept is
    evidence. While it sat in CONSTRUCT_ONLY the fixed probe still produced
    best=None -- the fix was not finished until the classification moved."""
    assert "mattgray" in ND.SIGNATURE
    assert "mattgray" not in ND.CONSTRUCT_ONLY
    r = ND.rank(MG_ACCEPTED)
    assert r["signature"] == ["mattgray"]
    assert r["best"] == "mattgray" and r["confident"] is True


def test_a_wrong_arity_unpack_is_a_bug_not_a_refusal(monkeypatch):
    """THE DEFECT THAT HID THE DEFECT, pinned. CPython raises ValueError for a
    bad unpack, and ValueError is this module's REFUSAL type, so the broad
    handler recorded a caller error as the file's verdict -- mattgray reported
    'accepts nothing, including its own corpus' for as long as the probe
    existed. BUG_EXCEPTIONS alone cannot catch this: ValueError must stay a
    refusal in every other case."""
    def bad(_path):
        a, b, c = (1, 2, 3, 4, 5, 6)                # the original mistake
        return {"a": a, "b": b, "c": c}
    monkeypatch.setitem(dict(ND.PROBE_ORDER), "mattgray", bad)
    monkeypatch.setattr(ND, "PROBE_ORDER", tuple(
        (p, bad if p == "mattgray" else f) for p, f in ND.PROBE_ORDER))
    with pytest.raises(ND.ProbeBug) as e:
        ND.probe("mattgray", MG_ACCEPTED)
    assert "unpacked its loader wrongly" in str(e.value)


def test_an_ordinary_valueerror_is_still_a_refusal(monkeypatch):
    """The other half: the unpack check must not swallow real refusals. Every
    parser says 'not mine' with a ValueError."""
    def refuses(_path):
        raise ValueError("not a Matt Gray music_play shim")
    monkeypatch.setattr(ND, "PROBE_ORDER", tuple(
        (p, refuses if p == "mattgray" else f) for p, f in ND.PROBE_ORDER))
    ok, reason = ND.probe("mattgray", MG_ACCEPTED)
    assert not ok
    assert "music_play shim" in reason
