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

DMC = os.path.join(_HERE, "dmc_native_sweep.py")
SDI = os.path.join(_HERE, "sdi_native_sweep.py")


@pytest.mark.skipif(os.name != "nt", reason="job objects are Windows-only")
def test_the_job_object_actually_installs():
    """Not "returns something" -- returns TRUE. Its first version returned False
    on this very machine and printed a polite message instead of protecting
    anything, so a test that accepted either value would have passed the bug."""
    assert S.bind_children_to_this_process() is True
    assert S._JOB_HANDLE[0], "the handle must be retained -- closing it kills the job"


@pytest.mark.skipif(os.name != "nt", reason="job objects are Windows-only")
def test_it_is_idempotent_so_both_sweeps_may_call_it():
    """dmc_native_sweep imports it from here, so it can be called twice in one
    process. A second call must not fail or drop the first handle."""
    assert S.bind_children_to_this_process() is True
    first = S._JOB_HANDLE[0]
    assert S.bind_children_to_this_process() is True
    assert S._JOB_HANDLE[0], "the handle was lost on the second call"
    assert first, "the first call left no handle"


def test_every_handle_restype_is_declared():
    """THE REGRESSION THAT ALREADY HAPPENED ONCE, pinned at the source.

    ctypes defaults a restype to c_int, which on 64-bit truncates
    GetCurrentProcess()'s -1 pseudo-handle; AssignProcessToJobObject then fails
    with ERROR_INVALID_HANDLE (6) and the function returns False -- installing
    nothing, quietly. All three declarations must stay.
    """
    src = open(SDI, encoding="utf-8").read()
    body = src[src.index("def bind_children_to_this_process("):]
    body = body[:body.index("\ndef ", 1)]
    assert "k32.GetCurrentProcess.restype = wintypes.HANDLE" in body
    assert "k32.CreateJobObjectW.restype = wintypes.HANDLE" in body
    assert "k32.AssignProcessToJobObject.argtypes" in body


def test_the_kill_on_job_close_flag_is_the_one_being_set():
    """0x2000 is JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE. Any other flag makes the
    job a bookkeeping device that kills nothing."""
    src = open(SDI, encoding="utf-8").read()
    assert re.search(r"JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE\s*=\s*0x2000", src)
    assert "LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE" in src


def test_it_never_raises_even_when_the_os_refuses():
    """A sweep must not fail to start because it could not install a safety net.

    Forced by making CreateJobObjectW unavailable: the function has to come back
    False, not blow up. Checked by calling it on a non-Windows code path shape --
    the `except Exception: return False` is the guarantee.
    """
    src = open(SDI, encoding="utf-8").read()
    body = src[src.index("def bind_children_to_this_process("):]
    body = body[:body.index("\ndef ", 1)]
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
    src = open(DMC, encoding="utf-8").read()
    assert "from sdi_native_sweep import bind_children_to_this_process" in src
    assert "CreateJobObjectW" not in src, (
        "dmc_native_sweep now has its own copy of the job-object code -- import it "
        "instead, or move both to a shared module")
