"""The shared kill-safety helper, pinned where it now lives.

pyscript/test_sdi_native_sweep.py already pins the GUARANTEE -- that the flag is
KILL_ON_JOB_CLOSE, that every handle restype is declared, that the function never
raises, and that both sweeps ask for it. Those assertions moved with the code and
are not repeated here.

What this file pins is what only a SHARED module can get wrong: that it is
importable on its own, that it drags neither sweep in behind it, and that two
callers in one process are safe. The whole reason for the extraction was that
dmc_native_sweep had to import a 900-line corpus sweep to reach one function; a
test that imports both sweeps to check the helper would re-create exactly that.
"""
import os
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import process_group as P                            # noqa: E402

PG = os.path.join(_HERE, "process_group.py")


def test_it_imports_with_only_pyscript_on_the_path():
    """THE POINT OF THE EXTRACTION, checked the only way that can see it.

    In-process this is vacuous -- pytest has already put rootdir and this
    directory on sys.path, so any arrangement of imports passes. So shell out
    with a bare interpreter, `-I` (isolated: no cwd, no user site), and only
    this directory on the path. If the helper ever grows a dependency on a
    sweep, on sidm2/, or on a third-party package, this is what notices.
    """
    src = ("import sys; sys.path.insert(0, %r); import process_group as P; "
           "print(P.bind_children_to_this_process.__name__)" % _HERE)
    # -I implies -E, so PYTHONPATH is ignored -- the path has to go in the source.
    r = subprocess.run([sys.executable, "-I", "-c", src], capture_output=True,
                       text=True, cwd=_HERE)
    assert r.returncode == 0, r.stderr
    assert "bind_children_to_this_process" in r.stdout


def test_it_imports_neither_sweep():
    """The dependency runs sweep -> helper and must never run back.

    Checked over the parsed IMPORT NODES rather than by module identity or by
    grepping the text. Module identity would miss an `import` inside a function
    body, which is exactly where a cycle would hide; a text search hits the
    docstring, which names both sweeps on purpose to say where the code came
    from. ast sees the function-body case and ignores the prose.
    """
    import ast
    tree = ast.parse(open(PG, encoding="utf-8").read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    for name in ("sdi_native_sweep", "dmc_native_sweep"):
        assert name not in imported, (
            "process_group imports %s -- that is the cycle the extraction "
            "removed, coming back" % name)
    assert imported <= {"os", "ctypes"}, (
        "the shared helper grew a dependency (%s); it is imported by every "
        "sweep and must stay stdlib-only" % sorted(imported - {"os", "ctypes"}))


def test_importing_it_costs_nothing_on_a_machine_without_job_objects():
    """ctypes/wintypes are resolved INSIDE the function, not at module scope.

    A top-level `from ctypes import wintypes` raises on Linux, which would make
    a Windows-only safety net into an import-time failure for every reader of
    either sweep on any other platform.
    """
    src = open(PG, encoding="utf-8").read()
    head = src[:src.index("def bind_children_to_this_process(")]
    assert "wintypes" not in head, "wintypes is imported at module scope"
    assert "import ctypes" not in head, "ctypes is imported at module scope"


@pytest.mark.skipif(os.name != "nt", reason="job objects are Windows-only")
def test_two_callers_in_one_process_share_one_job():
    """Both sweeps may call it, and a sweep may be imported by a test that
    already called it. The second call must return True and must not replace the
    retained handle -- replacing it drops the last reference to the first job,
    which is the kill trigger, so the children of call one would die at once."""
    assert P.bind_children_to_this_process() is True
    first = P._JOB_HANDLE[0]
    assert first, "the first call retained no handle"
    assert P.bind_children_to_this_process() is True
    assert P._JOB_HANDLE[0] == first, (
        "the second call installed a NEW job -- the first job's handle was "
        "dropped, which terminates the children it was protecting")


@pytest.mark.skipif(os.name != "nt", reason="job objects are Windows-only")
def test_it_returns_true_rather_than_something_truthy():
    """Its first version returned False on this machine and printed a polite
    message instead of protecting anything. A caller that treats any non-None
    return as success would have shipped that."""
    assert P.bind_children_to_this_process() is True


def test_the_module_records_the_measurement_not_just_the_mechanism():
    """The docstring carries the 3-survivors/0-survivors numbers and the reason a
    PID file and an exit trap cannot work. Both were tried before this, and
    without that written down the next reader tries them again."""
    doc = P.__doc__ or ""
    assert "3 survivors" in doc and "0 survivors" in doc
    assert "PID FILE AND AN EXIT TRAP CANNOT FIX THIS" in doc
