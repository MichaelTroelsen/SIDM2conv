"""The PostToolUse hook that warns about untested sources must not cry wolf.

The hook's first version compared filenames only -- it warned whenever
`pyscript/test_<name>.py` was absent -- and that was wrong on 29 of the 91 files
it fired on, because a module can be thoroughly exercised by a test under
another name. These tests pin the distinction, because a warning that is wrong a
third of the time is one people stop reading, and then the hook is worse than
nothing.

The anchors below name real modules on purpose. If one of them gains or loses a
test the assertion should be UPDATED with the new fact, not deleted -- that is
the point of pinning it.
"""
import importlib.util
import io
import json
import os
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO, ".claude", "hooks", "warn_missing_test.py")

needs_hook = pytest.mark.skipif(not os.path.exists(HOOK),
                                reason=".claude/hooks/warn_missing_test.py absent")


def _load():
    spec = importlib.util.spec_from_file_location("warn_missing_test", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(rel_path):
    """Feed the hook a PostToolUse payload for `rel_path`; return its stdout."""
    mod = _load()
    payload = json.dumps({"tool_input":
                          {"file_path": os.path.join(REPO, rel_path)}})
    old_in, old_out = sys.stdin, sys.stdout
    sys.stdin, sys.stdout = io.StringIO(payload), io.StringIO()
    try:
        rc = mod.main()
        return rc, sys.stdout.getvalue()
    finally:
        sys.stdin, sys.stdout = old_in, old_out


@needs_hook
def test_it_never_blocks():
    """Every path returns 0. A PostToolUse hook cannot undo the write anyway,
    and a non-zero exit here would turn a debt notice into a broken edit."""
    for p in ("sidm2/models.py", "sidm2/sf2_caps.py", "bin/build_dmc_native_song.py",
              "pyscript/abpage.py", "README.md"):
        rc, _ = _run(p)
        assert rc == 0, p


@needs_hook
def test_a_module_tested_under_another_name_is_SILENT():
    """THE REGRESSION THIS FILE EXISTS FOR.

    sidm2/models.py has no pyscript/test_models.py and never has -- but 12 test
    files import it, so it is not untested, it is unconventionally named. The
    name-only rule warned here; warning here is the false positive that trains
    people to ignore the hook.
    """
    mod = _load()
    assert not os.path.exists(os.path.join(REPO, "pyscript", "test_models.py"))
    assert mod._a_test_imports("models"), "no test imports sidm2/models.py?"
    rc, out = _run("sidm2/models.py")
    assert out == "", "hook warned about a module that tests do import"


@needs_hook
@pytest.mark.parametrize("rel,stem", [("sidm2/sf2_caps.py", "sf2_caps"),
                                      ("bin/build_dmc_native_song.py",
                                       "build_dmc_native_song")])
def test_a_genuinely_untested_module_DOES_warn(rel, stem):
    """The other direction, so the test above cannot be satisfied by a hook that
    simply never speaks. Both of these have no same-named test AND no test that
    imports them; sf2_caps is 43 lines of table caps that five builders compare
    against, so a silent gap there truncates builds."""
    mod = _load()
    if os.path.exists(os.path.join(REPO, "pyscript", "test_%s.py" % stem)):
        pytest.skip("%s gained a test -- update the triage in the hook" % stem)
    if mod._a_test_imports(stem):
        pytest.skip("%s is now imported by a test -- update the triage" % stem)
    rc, out = _run(rel)
    assert out, "hook stayed silent on a module nothing tests"
    assert "No test exercises" in json.loads(out)["systemMessage"]


@needs_hook
@pytest.mark.parametrize("rel", ["pyscript/abpage.py",       # not watched
                                 "bin/native_dispatch.py",   # bin/, not build_*
                                 "sidm2/test_helper.py",     # a test needs no test
                                 "docs/players/MON.md"])     # not python
def test_out_of_scope_paths_are_silent(rel):
    rc, out = _run(rel)
    assert out == "", rel


@needs_hook
def test_the_scope_decision_is_recorded_not_just_made():
    """The task that set WATCHED required the choice be written down so it is not
    re-litigated. If someone narrows it later they must move the note too."""
    src = io.open(HOOK, encoding="utf-8").read()
    assert 'WATCHED = ("sidm2", "bin", "scripts")' in src
    assert "THE SCOPE DECISION" in src
    assert "THE TRIAGE" in src
