"""
Pytest Configuration and Global Fixtures

Provides session-level cleanup to ensure SF2 editor processes are always closed.
"""

import pytest


@pytest.fixture(scope="session", autouse=True)
def cleanup_editor_processes():
    """
    Session-level fixture that ensures all editor processes are cleaned up.

    Runs automatically after all tests complete (autouse=True).
    Scope='session' means it runs once at the end of the entire test session.
    """
    # Setup (before tests)
    yield

    # Teardown (after all tests)
    print("\n" + "=" * 70)
    print("Global Cleanup: Ensuring all editor processes are closed")
    print("=" * 70)

    try:
        import psutil
        killed = 0
        for proc in psutil.process_iter(['name', 'pid']):
            if 'SIDFactoryII' in proc.info['name']:
                try:
                    print(f"  Killing SIDFactoryII.exe (PID: {proc.info['pid']})")
                    proc.kill()
                    killed += 1
                except Exception as e:
                    print(f"  Warning: Could not kill PID {proc.info['pid']}: {e}")

        if killed > 0:
            print(f"  Killed {killed} editor process(es)")
        else:
            print("  No editor processes found")

    except Exception as e:
        print(f"  Warning: Global cleanup failed: {e}")

    print("=" * 70)


def pytest_sessionfinish(session, exitstatus):
    """
    Additional cleanup hook that runs after pytest session finishes.

    This is a backup cleanup mechanism that runs even if fixtures fail.
    """
    print("\n[Pytest Session Finish Hook]")

    try:
        import psutil
        for proc in psutil.process_iter(['name']):
            if 'SIDFactoryII' in proc.info['name']:
                proc.kill()
    except Exception:
        pass  # Silent cleanup
