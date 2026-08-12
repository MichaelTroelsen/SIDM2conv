"""A sweep that cannot launch a process must not report that as a file's result.

The first full-corpus run of `sdi_native_sweep.py` returned rc=3221225794
(`STATUS_DLL_INIT_FAILED`) for every file from #275 of 441 onward: ~5 h in, the
long-lived parent could no longer spawn a child. The run did not stop. It
recorded all 167 in the same `errored` column as `not an SDI play+3 rip`,
printed `built 161 refused 38 errored 242 of 441`, and published per-variant
medians that were in fact an alphabetical A-O sample. Three of those files build
cleanly on a fresh invocation, so 167 "results" were fabrications.

The distinction these tests pin is not cosmetic: `errored` means *we asked and
the builder could not*, `unmeasured` means *we never asked*. Pooling the second
into the first turns an infrastructure collapse into a claim about the corpus.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sdi_native_sweep as sw  # noqa: E402


class _Done:
    def __init__(self, rc, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def _fake_run(monkeypatch, responses):
    """Feed build_one() canned child results, one per call."""
    calls = iter(responses)
    monkeypatch.setattr(sw.os.path, "exists", lambda _p: True)
    monkeypatch.setattr(sw.subprocess, "run", lambda *a, **k: next(calls))


_BUILT = _Done(0, "x.sid: la=$1000 variant=E\n"
                  "  voice 0:  99.9%\n  voice 1: 100.0%\n  voice 2:  98.0%\n"
                  "packed into 3 adaptive parts\n")
_REAL_ERR = _Done(1, "", "ValueError: not an SDI play+3 rip (signatures missing)")
_LAUNCH = _Done(3221225794)


def test_a_silent_launch_failure_is_not_a_result(monkeypatch):
    _fake_run(monkeypatch, [_LAUNCH])
    rec = sw.build_one("Anything")
    assert rec["infra"] == "STATUS_DLL_INIT_FAILED (0xC0000142)"
    assert rec["voices"] is None and rec["refused"] is None


def test_the_same_rc_WITH_output_is_a_real_result(monkeypatch):
    """The code only quarantines a child that never spoke. A builder that ran,
    said something and happened to exit with that code has an opinion about the
    file, and suppressing it would hide a genuine failure."""
    _fake_run(monkeypatch, [_Done(3221225794, "", "ValueError: WAVE overflow: 305 rows > 256")])
    rec = sw.build_one("Pervers")
    assert "infra" not in rec
    assert "WAVE overflow" in rec["error"]


def test_summarize_keeps_unmeasured_out_of_errored(monkeypatch):
    results = {
        "ok": {"voices": [99.9, 100.0, 98.0], "variant": "E"},
        "real": {"voices": None, "refused": None, "error": "not an SDI play+3 rip"},
        "never_asked": {"voices": None, "refused": None, "infra": "STATUS_NO_MEMORY (0xC0000017)"},
    }
    s = sw.summarize(results)
    assert s["built"] == 1
    assert s["errored"] == 1, "the launch failure must not inflate the error class"
    assert s["unmeasured"] == 1
    assert s["unmeasured_files"] == ["never_asked"]


def test_the_run_aborts_instead_of_fabricating_the_rest(monkeypatch, capsys):
    """The mutation this guards: with --infra-abort 0 the sweep marches on and
    every remaining file lands in the record as a failure it never had."""
    names = [f"f{i}" for i in range(10)]
    _fake_run(monkeypatch, [_BUILT] + [_LAUNCH] * 9)
    sw.main(["--files", *names, "--infra-abort", "3"])
    guarded = capsys.readouterr().out
    # 9 unmeasured: the 3 that launch-failed plus the 6 never attempted. The
    # abort does not make those 6 measured -- it makes them *named*.
    assert "ABORTING" in guarded
    assert "9 file(s) UNMEASURED" in guarded, guarded
    assert "--files f1 f2 f3 f4 f5 f6 ..." in guarded, "must print a resume command"
    assert guarded.count("LAUNCH FAILURE") == 3, "must stop spawning, not just warn"

    _fake_run(monkeypatch, [_BUILT] + [_LAUNCH] * 9)
    sw.main(["--files", *names, "--infra-abort", "0"])
    unguarded = capsys.readouterr().out
    assert "ABORTING" not in unguarded
    assert unguarded.count("LAUNCH FAILURE") == 9, "unguarded, it burns the whole corpus"
    # Even unguarded, the count that would have been published stays honest.
    assert "built 1  refused 0  errored 0" in unguarded
    assert "9 file(s) UNMEASURED" in unguarded


def test_an_isolated_launch_failure_does_not_abort_the_sweep(monkeypatch, capsys):
    """One transient hiccup between successes is not host exhaustion; aborting on
    it would make a 441-file sweep unfinishable."""
    _fake_run(monkeypatch, [_BUILT, _LAUNCH, _BUILT, _LAUNCH, _BUILT, _REAL_ERR])
    sw.main(["--files", "a", "b", "c", "d", "e", "f", "--infra-abort", "3"])
    out = capsys.readouterr().out
    assert "ABORTING" not in out
    assert "built 3" in out
    assert "2 file(s) UNMEASURED" in out


def test_the_headline_states_the_real_denominator(monkeypatch, capsys):
    """`built 161 refused 38 errored 242 of 441` read as a 441-file corpus
    result. It was a 274-file one."""
    _fake_run(monkeypatch, [_BUILT, _BUILT, _LAUNCH, _LAUNCH, _LAUNCH])
    sw.main(["--files", "a", "b", "c", "d", "e", "--infra-abort", "3"])
    out = capsys.readouterr().out
    assert "cover 2 files, NOT 5" in out, out


# --------------------------------------------------------------------------
# The classifier is shared plumbing, not an SDI detail.
#
# CLAUDE.md: fidelity_common is "the shared measurement plumbing every scorer
# should route through -- do not write a new one", written after five
# independent copies of one weighted-accuracy scheme were each found broken.
# `soundmonitor_sweep` and `blackbird_sweep` have this sweep's exact shape --
# run the builder, look for the line carrying the numbers, record an error when
# it is absent -- so a silent child lands in their BUILD FAILED column too.

def test_the_classifier_lives_in_the_shared_harness():
    from sidm2.fidelity_common import LAUNCH_FAILURE_RCS, launch_failure
    assert launch_failure(3221225794) == "STATUS_DLL_INIT_FAILED (0xC0000142)"
    assert launch_failure(0) is None
    assert launch_failure(1) is None, "an ordinary non-zero exit is a result"
    assert 3221225495 in LAUNCH_FAILURE_RCS


def test_a_child_that_spoke_is_always_a_result():
    """However it exited. It ran, it had an opinion about the file, and
    suppressing that would hide a genuine failure."""
    from sidm2.fidelity_common import launch_failure
    assert launch_failure(3221225794, "ValueError: WAVE overflow") is None
    assert launch_failure(3221225794, "   \n  ") is not None, "whitespace is silence"


def test_every_sweep_routes_through_it():
    """Mutation this pins: a sweep reintroducing its own rc table, or dropping
    the check, goes back to reporting a host collapse as failed builds."""
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("sdi_native_sweep.py", "soundmonitor_sweep.py", "blackbird_sweep.py"):
        src = open(os.path.join(root, "pyscript", name), encoding="utf-8").read()
        assert "launch_failure" in src, f"{name} does not classify launch failures"
        assert "LAUNCH_FAILURE_RCS = {" not in src, \
            f"{name} declares its own copy of the rc table"
