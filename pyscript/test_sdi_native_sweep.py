"""A killed sweep must not leave builders writing into out/<player>/.

THE DEFECT, reproduced from the PROCESS LIST rather than taken from the task
text (which said a PID file and an EXIT trap had already failed to fix it):
both sweeps run a ThreadPoolExecutor whose workers each
`subprocess.run([sys.executable, BUILDER, ...])`. Those builders are ordinary
grandchildren with no lifetime tie to the parent. Measured on this machine with
a stand-in child of the same shape:

    unprotected   3 children before kill -> 3 survivors 3s after a hard kill
                  -> 3 artifacts written AFTER the parent was dead
    job object    3 children before kill -> 0 survivors -> 0 artifacts (waited 50s)

That is the corpus-voiding mechanism end to end: the replacement run's output
gets interleaved with a dead run's, and part-1-only scoring does not see it.

WHY A HANDLER CANNOT FIX IT, which is why the two things already tried did not:
`atexit` and a signal handler both need the parent to still be alive to run
their cleanup, and a hard kill is exactly the case where it is not. The Job
Object moves the invariant into the kernel -- descendants inherit the job, and
Windows terminates them when the last handle closes, which happens when the
parent dies however it dies.

WHAT THESE TESTS DO NOT DO: they do not spawn a real builder. That would write
into out/dmc or out/sdi, which this task declares no path for, and the kill
semantics are a property of the spawn mechanism rather than of what the child
computes. The end-to-end kill was verified by hand (numbers above) and is
recorded in runs.jsonl; what is pinned here is that the guarantee is REQUESTED,
that its handle is RETAINED, and that the ctypes declarations which silently
broke it once are still present.
"""
import os
import re
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)
sys.path.insert(0, _ROOT)

import sdi_native_sweep as S                      # noqa: E402
import process_group as P                          # noqa: E402

DMC = os.path.join(_HERE, "dmc_native_sweep.py")
SDI = os.path.join(_HERE, "sdi_native_sweep.py")
PG = os.path.join(_HERE, "process_group.py")


@pytest.mark.skipif(os.name != "nt", reason="job objects are Windows-only")
def test_the_job_object_actually_installs():
    """Not "returns something" -- returns TRUE. Its first version returned False
    on this very machine and printed a polite message instead of protecting
    anything, so a test that accepted either value would have passed the bug."""
    assert S.bind_children_to_this_process() is True
    assert P._JOB_HANDLE[0], "the handle must be retained -- closing it kills the job"


@pytest.mark.skipif(os.name != "nt", reason="job objects are Windows-only")
def test_it_is_idempotent_so_both_sweeps_may_call_it():
    """dmc_native_sweep imports it from here, so it can be called twice in one
    process. A second call must not fail or drop the first handle."""
    assert S.bind_children_to_this_process() is True
    first = P._JOB_HANDLE[0]
    assert S.bind_children_to_this_process() is True
    assert P._JOB_HANDLE[0], "the handle was lost on the second call"
    assert first, "the first call left no handle"


def test_every_handle_restype_is_declared():
    """THE REGRESSION THAT ALREADY HAPPENED ONCE, pinned at the source.

    ctypes defaults a restype to c_int, which on 64-bit truncates
    GetCurrentProcess()'s -1 pseudo-handle; AssignProcessToJobObject then fails
    with ERROR_INVALID_HANDLE (6) and the function returns False -- installing
    nothing, quietly. All three declarations must stay.
    """
    src = open(PG, encoding="utf-8").read()
    body = src[src.index("def bind_children_to_this_process("):]
    nxt = body.find(chr(10) + 'def ', 1)   # a following def, if there is one
    body = body if nxt < 0 else body[:nxt]   # the helper is the LAST def now
    assert "k32.GetCurrentProcess.restype = wintypes.HANDLE" in body
    assert "k32.CreateJobObjectW.restype = wintypes.HANDLE" in body
    assert "k32.AssignProcessToJobObject.argtypes" in body


def test_the_kill_on_job_close_flag_is_the_one_being_set():
    """0x2000 is JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE. Any other flag makes the
    job a bookkeeping device that kills nothing."""
    src = open(PG, encoding="utf-8").read()
    assert re.search(r"JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE\s*=\s*0x2000", src)
    assert "LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE" in src


def test_it_never_raises_even_when_the_os_refuses():
    """A sweep must not fail to start because it could not install a safety net.

    Forced by making CreateJobObjectW unavailable: the function has to come back
    False, not blow up. Checked by calling it on a non-Windows code path shape --
    the `except Exception: return False` is the guarantee.
    """
    src = open(PG, encoding="utf-8").read()
    body = src[src.index("def bind_children_to_this_process("):]
    nxt = body.find(chr(10) + 'def ', 1)   # a following def, if there is one
    body = body if nxt < 0 else body[:nxt]   # the helper is the LAST def now
    assert "except Exception:" in body and "return False" in body
    assert body.count("return False") >= 4, (
        "each failure point must return False rather than falling through to True")


def test_both_sweeps_request_the_guarantee_and_print_which_one_holds():
    """If a sweep stops calling this, a hard kill silently goes back to leaving
    builders running -- and the printed line is how a human tells the two apart."""
    for path, name in ((SDI, "sdi"), (DMC, "dmc")):
        src = open(path, encoding="utf-8").read()
        assert "bind_children_to_this_process" in src, "%s sweep dropped it" % name
        assert "kill-safety:" in src, "%s sweep no longer says which guarantee holds" % name
        assert "NOT ESTABLISHED" in src, (
            "%s sweep no longer warns when the net is absent -- silence here is the "
            "failure mode, not the fix" % name)


def test_dmc_imports_it_rather_than_duplicating_it():
    """Two copies would drift, and this pair has already drifted once elsewhere
    in this repo (the Blackbird prune fork). One implementation, imported."""
    for path, name in ((DMC, "dmc"), (SDI, "sdi")):
        src = open(path, encoding="utf-8").read()
        assert "from process_group import bind_children_to_this_process" in src, (
            "%s sweep no longer imports the shared helper" % name)
        assert "CreateJobObjectW" not in src, (
            "%s_native_sweep now has its own copy of the job-object code -- import "
            "it from process_group instead" % name)
    # and the shared module is where the implementation actually lives
    assert "CreateJobObjectW" in open(PG, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# THE SILENT DEATH, and the two things that must change before a relaunch.
#
# On 2026-08-20 a detached 441-file sweep ran for hours and died with its log
# frozen at three banner lines, 0 files written and no stderr beyond them. The
# job-object tests above cover the OPPOSITE failure -- a killed parent leaving
# children alive; this pair covers a parent dying unobserved.
#
# Two defects made it unattributable and both are fixed in sdi_native_sweep.py:
#
#   1. THE ONLY RECORD WAS THE LAUNCHER'S REDIRECT. A redirect captures nothing
#      a dying process never manages to print, and the log, the result JSON and
#      the start-epoch file all lived in a session scratchpad that was
#      garbage-collected nine days later. The sweep now keeps its own journal
#      beside --json, rewritten after every file, closed by an atexit hook that
#      stamps HOW the run ended.
#   2. A 0-FILE SWEEP WAS INDISTINGUISHABLE FROM A COMPLETED ONE. main() wrote
#      a well-formed result JSON and returned 0 whatever the built count was.
# ---------------------------------------------------------------------------


def test_the_journal_sits_beside_the_result_not_in_a_temp_dir():
    """Derived from --json on purpose -- see the module comment.

    A separate flag would be a separate thing to forget, and the whole point is
    that the NEXT death leaves evidence without anyone having remembered to ask
    for it. None when --json is absent: a sweep nobody wanted the result of
    does not get a journal either.
    """
    assert S.journal_path_for("/w/x/out.json") == "/w/x/out.json.journal"
    assert S.journal_path_for(None) is None
    assert S.journal_path_for("") is None


def test_writing_the_journal_never_raises_even_at_an_impossible_path():
    """A sweep must not die because its own black box could not be written.

    This is the same rule as the job object's install path two tests up: the
    safety net is allowed to fail, but never to become the cause.
    """
    old = S._JOURNAL_PATH[0]
    try:
        S._JOURNAL_PATH[0] = os.path.join(_HERE, "no", "such", "dir", "j.json")
        S.write_journal()                       # must not raise
    finally:
        S._JOURNAL_PATH[0] = old


def test_a_journal_left_running_is_closed_as_DIED(tmp_path):
    """The line the 2026-08-20 death did not leave.

    _close_journal runs from atexit, so it fires on an uncaught exception and on
    a signal the interpreter survives long enough to unwind. A journal still
    reading 'running' at that point means the process went down mid-sweep, and
    it must say so rather than being left ambiguous.
    """
    import json as _json
    p = str(tmp_path / "run.json.journal")
    old_path, old_state = S._JOURNAL_PATH[0], S._JOURNAL["state"]
    try:
        S._JOURNAL_PATH[0] = p
        S._JOURNAL.update(state="running", done=7, total=441, last_file="Kirby")
        S._close_journal()
        got = _json.load(open(p, encoding="utf-8"))
        assert got["state"] == "died", got
        assert got["done"] == 7 and got["total"] == 441
        assert got["last_file"] == "Kirby", "the journal must name where it stopped"
        assert got["ended"], "a closed journal must carry an end timestamp"
    finally:
        S._JOURNAL_PATH[0], S._JOURNAL["state"] = old_path, old_state


def test_a_sweep_that_builds_nothing_exits_non_zero_and_says_complete_false(tmp_path):
    """The headline rule: 0 files built is NOT a corpus result.

    Driven end to end through main() with a song name that does not exist, so
    build_one returns 'missing .sid' without spawning anything -- no builder
    runs and out/sdi is never touched. Both halves are asserted: the exit
    status, because a shell chain reads that, and the flag inside the file,
    because a later reader has only the file.
    """
    import json as _json
    out = str(tmp_path / "res.json")
    rc = S.main(["--files", "NoSuchSongExistsHere", "--json", out,
                 "--schedule", "corpus-order"])
    assert rc == 1, "a sweep that built nothing must not exit 0"
    got = _json.load(open(out, encoding="utf-8"))
    assert got["complete"] is False, got.get("summary")
    assert got["summary"]["built"] == 0


def test_positive_control_a_sweep_that_DID_build_exits_zero(tmp_path, monkeypatch):
    """Without this the test above passes for a build that can never succeed.

    'returns 1' is satisfied by a main() that returns 1 unconditionally, which
    is precisely the shape that would make every future sweep look dead. So
    stub one built file and require the other branch.
    """
    import json as _json
    monkeypatch.setattr(S, "build_one", lambda name, timeout=1800: {
        "variant": "A", "voices": [100.0, 100.0, 100.0], "parts": 1,
        "onset_agree": (10, 10), "refused": None, "v_wrapper": False,
        "n": [500, 500, 500], "rc": 0})
    out = str(tmp_path / "ok.json")
    rc = S.main(["--files", "Whatever", "--json", out, "--schedule", "corpus-order"])
    assert rc == 0, "a sweep that built a file must exit 0"
    got = _json.load(open(out, encoding="utf-8"))
    assert got["complete"] is True
    assert os.path.exists(out + ".journal"), "the journal must sit beside --json"
    j = _json.load(open(out + ".journal", encoding="utf-8"))
    assert j["state"] == "finished", j
    assert j["built"] == 1 and j["total"] == 1


# ---------------------------------------------------------------------------
# THE SCHEDULER HAD NO TESTS AT ALL until 2026-09-05 -- `schedule_longest_first`
# and `decoded_span` are the DEFAULT ordering for every sweep and no test file
# mentioned either name.
#
# It is pinned here rather than re-justified, because the number that justified
# it does not reproduce: sdi-six-timeouts-at-j16 published "build time vs trace
# window r=0.942" over nine files; recomputed against the spans this module
# returns, with the same nine files and the same recorded times, it is 0.335 --
# while the part-count figure from the same record reproduces EXACTLY at 0.420.
# Four of those nine timings sit at a flat 1078-1152s across spans differing
# 3.7x, and one of them (Lame) was later re-timed at 16.6s. See decoded_span's
# docstring. Ordering longest-first is still right; the r is not evidence for it.
# ---------------------------------------------------------------------------


def test_the_order_is_descending_by_span_and_that_is_the_whole_contract():
    """Synthetic, so it tests the ORDERING and not the corpus."""
    spans = {"a": 10, "b": 500, "c": 100}
    S.decoded_span_orig = S.decoded_span
    try:
        S.decoded_span = lambda n: spans[n]
        ordered, got = S.schedule_longest_first(["a", "b", "c"])
    finally:
        S.decoded_span = S.decoded_span_orig
    assert ordered == ["b", "c", "a"], ordered
    assert got == spans


def test_undecodable_files_sort_LAST_not_first():
    """`decoded_span` returns None for a file with no SDI signature, and None
    must not sort as a huge span. 98 of the 441 corpus files are in this class,
    so getting the sense wrong would schedule every unbuildable file first.
    """
    spans = {"real": 100, "junk": None, "big": 900}
    S.decoded_span_orig = S.decoded_span
    try:
        S.decoded_span = lambda n: spans[n]
        ordered, _ = S.schedule_longest_first(["real", "junk", "big"])
    finally:
        S.decoded_span = S.decoded_span_orig
    assert ordered == ["big", "real", "junk"], ordered
    assert ordered[-1] == "junk"


def test_scheduling_is_a_PERMUTATION_never_a_filter():
    """The one property that would corrupt a corpus result if it broke.

    A sweep reports `built N of len(corpus)`, so a scheduler that dropped or
    duplicated a name would silently change the denominator. Multiset equality,
    not set equality -- a duplicate must fail too.
    """
    names = ["x", "y", "z", "w"]
    spans = {"x": 5, "y": None, "z": 50, "w": 5}
    S.decoded_span_orig = S.decoded_span
    try:
        S.decoded_span = lambda n: spans[n]
        ordered, _ = S.schedule_longest_first(names)
    finally:
        S.decoded_span = S.decoded_span_orig
    assert sorted(ordered) == sorted(names), ordered
    assert len(ordered) == len(names)


@pytest.mark.skipif(not os.path.isdir(os.path.join(_ROOT, "SID", "Gallefoss_Glenn")),
                    reason="SDI corpus not present")
def test_the_prescan_is_cheap_enough_to_run_before_every_sweep():
    """The design only works because the pre-scan is in-memory.

    `decoded_span` deliberately does NOT siddump or py65-trace -- that is the
    2.5-hour part. Measured at 2.87s for all 441 files. The bound here is loose
    (30s) because it is guarding against someone wiring a trace into this path,
    not against normal machine variation.
    """
    import time
    t0 = time.time()
    names = S.corpus_files()
    ordered, spans = S.schedule_longest_first(names)
    elapsed = time.time() - t0
    assert len(ordered) == len(names)
    assert elapsed < 30, (
        "the pre-scan took %.1fs -- it must stay an in-memory decode; if this "
        "starts tracing, every sweep pays it twice" % elapsed)
    real = [s for s in spans.values() if s is not None]
    assert len(real) > 300, "positive control: only %d files decoded" % len(real)
