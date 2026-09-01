"""Make a sweep's spawned builders die when the sweep itself dies.

EXTRACTED FROM pyscript/sdi_native_sweep.py, where it landed only because that
task's `touches` covered that file and not a new one. dmc_native_sweep then had
to `from sdi_native_sweep import bind_children_to_this_process`, importing a
whole corpus sweep to reach one function. This module is that function's real
home; both sweeps import it from here.

THE DEFECT IT EXISTS FOR, measured rather than assumed
(runs.jsonl:corpus-job-survives-kill): a sweep runs a ThreadPoolExecutor whose
workers each `subprocess.run([sys.executable, BUILDER, ...])`. Those builders are
ordinary grandchildren with no lifetime tie to the parent, so a hard kill of the
sweep leaves every in-flight builder running to completion, writing into
out/<player>/ and voiding the run that replaces it.

    unprotected  3 children -> parent hard-killed -> 3 survivors -> 3 artifacts
                 written AFTER the parent was gone
    job object   3 children -> parent hard-killed -> 0 survivors -> 0 artifacts

A PID FILE AND AN EXIT TRAP CANNOT FIX THIS, and both were tried before this
was: each needs the parent alive to run its cleanup, and a hard kill is exactly
the case where it is not. The Job Object puts the invariant in the kernel.
"""
import os

# Held for the life of the process: closing this handle is what kills the builders.
_JOB_HANDLE = [None]


def bind_children_to_this_process():
    """Make every builder this sweep spawns die when the sweep dies.

    THE DEFECT, reproduced from the process list rather than taken on trust: this
    sweep runs a ThreadPoolExecutor whose workers each `subprocess.run([sys.executable,
    BUILDER, ...])`. Those builders are ordinary grandchildren with NO lifetime tie to
    the parent, so killing the sweep -- `Stop-Process`, taskkill without /T, a closed
    terminal -- leaves every in-flight builder running to completion. Measured: parent
    killed, 3 of 3 children survived with ParentProcessId still pointing at the dead
    parent, and each went on to write its artifact. That is how a "killed" corpus run
    keeps writing into out/<player>/ and voids the run that replaces it.

    A PID FILE AND AN EXIT TRAP DO NOT FIX THIS, which is why the task says both were
    already tried: both need the parent to still be alive to run their cleanup, and a
    hard kill is precisely the case where it is not.

    THE FIX IS THE OS, not a handler. A Windows Job Object with
    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE holds the invariant in the kernel: descendants
    inherit the job, and when the last handle to it closes -- which happens when this
    process dies, however it dies -- Windows terminates every process still in it.

    Returns True if the guarantee is in force, False if it could not be established.
    NEVER RAISES: a sweep that refuses to start because it could not install a safety
    net is worse than one that runs without it, so the failure is reported to the
    caller and printed, not thrown. On non-Windows this returns False -- the POSIX
    equivalent (a process group plus killpg, or prctl PDEATHSIG) is a separate job and
    this repo's sweeps run on Windows.
    """
    if os.name != "nt":
        return False
    if _JOB_HANDLE[0]:
        # ALREADY INSTALLED, and this is not merely an optimisation: creating a
        # second job would overwrite the retained handle, leaking the first one
        # and leaving two jobs where the contract promises one. Both sweeps may
        # call this, and a test that imports one sweep may already have.
        return True

    try:
        import ctypes
        from ctypes import wintypes

        class _BASIC(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                        ("PerJobUserTimeLimit", ctypes.c_int64),
                        ("LimitFlags", wintypes.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t),
                        ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", wintypes.DWORD),
                        ("Affinity", ctypes.POINTER(ctypes.c_ulong)),
                        ("PriorityClass", wintypes.DWORD),
                        ("SchedulingClass", wintypes.DWORD)]

        class _IO(ctypes.Structure):
            _fields_ = [("ReadOperationCount", ctypes.c_uint64),
                        ("WriteOperationCount", ctypes.c_uint64),
                        ("OtherOperationCount", ctypes.c_uint64),
                        ("ReadTransferCount", ctypes.c_uint64),
                        ("WriteTransferCount", ctypes.c_uint64),
                        ("OtherTransferCount", ctypes.c_uint64)]

        class _EXT(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", _BASIC),
                        ("IoInfo", _IO),
                        ("ProcessMemoryLimit", ctypes.c_size_t),
                        ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t),
                        ("PeakJobMemoryUsed", ctypes.c_size_t)]

        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
        JobObjectExtendedLimitInformation = 9

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        # EVERY handle restype MUST be declared. ctypes defaults to c_int, which on
        # 64-bit TRUNCATES GetCurrentProcess()'s -1 pseudo-handle and makes
        # AssignProcessToJobObject fail with ERROR_INVALID_HANDLE (6). Measured: that
        # is exactly what this function did on its first version, and it failed
        # SILENTLY -- returning False, printing "NOT ESTABLISHED", installing nothing.
        # A safety net whose failure mode is a polite message is the shape worth
        # naming here.
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        job = k32.CreateJobObjectW(None, None)
        if not job:
            return False
        info = _EXT()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not k32.SetInformationJobObject(job, JobObjectExtendedLimitInformation,
                                           ctypes.byref(info), ctypes.sizeof(info)):
            return False
        if not k32.AssignProcessToJobObject(job, k32.GetCurrentProcess()):
            # Already in a job that forbids nesting (pre-Win8, or some CI runners).
            return False
        _JOB_HANDLE[0] = job        # keep it open; closing it is the kill trigger
        return True
    except Exception:                                          # noqa: BLE001
        return False
