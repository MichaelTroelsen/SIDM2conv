"""
Pytest Configuration and Global Fixtures

Provides session-level cleanup to ensure SF2 editor processes are always closed.

SCOPE OF THE CLEANUP (2026-07-30). Both cleanup paths below used to kill EVERY
SIDFactoryII process on the machine, not just the ones the tests started. That
silently sabotaged any long SF2II play-test running alongside the suite:
`psutil.Process.kill()` is a TerminateProcess, and its non-zero exit code is
exactly what `blackbird_crash_probe.classify_termination` reads as CRASHED. It
produced a phantom "the one-part Driller crashes in SF2II" result -- six trials,
both arms, 100% CRASHED at scattered times, all with the same exit code -- that
was entirely this file reaching outside its own session. `pytest_sessionfinish`
was the worse of the two: it swallowed all exceptions, so it never even said
what it had killed.

An editor older than this pytest session cannot have been started by it, so the
cleanup now leaves those alone.
"""

import time

import pytest

# Bound at import (collection time), before any test can spawn an editor.
_SESSION_START = time.time()


def _kill_editors_started_this_session(verbose):
    """Kill only SIDFactoryII processes newer than this pytest session.

    Returns (killed, skipped). Never raises -- cleanup must not fail a run.
    """
    killed = skipped = 0
    try:
        import psutil
        for proc in psutil.process_iter(['name', 'pid']):
            if 'SIDFactoryII' not in (proc.info.get('name') or ''):
                continue
            try:
                if proc.create_time() < _SESSION_START:
                    if verbose:
                        print(f"  Leaving PID {proc.info['pid']} alone (started "
                              f"before this test session -- not ours)")
                    skipped += 1
                    continue
                if verbose:
                    print(f"  Killing SIDFactoryII.exe (PID: {proc.info['pid']})")
                proc.kill()
                killed += 1
            except Exception as e:
                if verbose:
                    print(f"  Warning: Could not handle PID "
                          f"{proc.info['pid']}: {e}")
    except Exception as e:
        if verbose:
            print(f"  Warning: Global cleanup failed: {e}")
    return killed, skipped


@pytest.fixture(scope="session", autouse=True)
def cleanup_editor_processes():
    """
    Session-level fixture that ensures all editor processes are cleaned up.

    Runs automatically after all tests complete (autouse=True).
    Scope='session' means it runs once at the end of the entire test session.
    """
    yield

    # Teardown (after all tests)
    print("\n" + "=" * 70)
    print("Global Cleanup: Ensuring all editor processes are closed")
    print("=" * 70)

    killed, skipped = _kill_editors_started_this_session(verbose=True)
    if killed:
        print(f"  Killed {killed} editor process(es)")
    else:
        print("  No editor processes started by this session")
    if skipped:
        print(f"  Left {skipped} pre-existing editor process(es) running")

    print("=" * 70)


def pytest_sessionfinish(session, exitstatus):
    """
    Additional cleanup hook that runs after pytest session finishes.

    This is a backup cleanup mechanism that runs even if fixtures fail. It is
    scoped to this session's own editors for the reason in the module docstring;
    it also no longer kills silently -- an unexplained kill of someone else's
    process is what made the phantom crash result so hard to attribute.
    """
    print("\n[Pytest Session Finish Hook]")
    killed, skipped = _kill_editors_started_this_session(verbose=False)
    if killed or skipped:
        print(f"  editors: killed {killed} from this session, "
              f"left {skipped} pre-existing")
