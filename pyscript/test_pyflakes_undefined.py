"""Static check: no undefined-name regressions in sidm2/.

This test generalizes the v3.5.64 defensive guard. v3.5.63 was an
undefined-name regression — `extract_all_laxity_tables` used inside
`laxity_raw_np21_builder` without being imported. v3.5.64 added a
target test that catches the specific Stage 7 emission impact. This
test catches the *class*: any undefined-name regression that ships
to the sidm2/ package.

# How it works

Runs `pyflakes sidm2/` via subprocess, filters output to
"undefined name" findings, asserts the count is zero.

# Suppressed false positives

pyflakes can't trace symbols through `from X import *` star imports.
`sidm2/__init__.py` uses two star imports for `.constants` and
`.exceptions` (this is the project's intentional re-export pattern).
The corresponding `may be undefined, or defined from star imports`
warnings are filtered out.

# Why pyflakes (not ruff, not pylint)

* Smaller surface area, focused checker, no config file required.
* Installed via `pip install pyflakes` (pure-Python, no deps).
* Same checker pyflakes/flake8/ruff all use under the hood for F821.

If pyflakes isn't installed in the test environment, the test SKIPS
with a clear message that points at `requirements-dev.txt`. CI workflows
should install dev deps via `pip install -r requirements-dev.txt` so
this gate runs on every commit.

# Recommended invocation

```
pip install -r requirements-dev.txt
pytest pyscript/test_pyflakes_undefined.py -v
```
"""
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).parent.parent
SIDM2_DIR = ROOT / "sidm2"


def _run_pyflakes() -> tuple[int, str]:
    """Returns (returncode, stdout+stderr) from `pyflakes sidm2/`.

    Returns (-1, "") if pyflakes isn't installed.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pyflakes", str(SIDM2_DIR)],
            capture_output=True, text=True, cwd=str(ROOT),
        )
    except FileNotFoundError:
        return -1, ""
    if "No module named pyflakes" in (result.stderr or ""):
        return -1, ""
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def _undefined_name_findings(pyflakes_output: str) -> list[str]:
    """Return only "undefined name" lines from pyflakes output.

    Filters out the harmless `may be undefined, or defined from star
    imports` and `unable to detect undefined names` lines — those are
    pyflakes flagging its own inability to trace star imports, not
    actual undefined-name bugs.
    """
    out: list[str] = []
    for line in pyflakes_output.splitlines():
        if "undefined name" not in line:
            continue
        if "may be undefined, or defined from star imports" in line:
            continue
        if "unable to detect undefined names" in line:
            continue
        out.append(line.strip())
    return out


class TestNoUndefinedNamesInSidm2(unittest.TestCase):
    """Guards against the v3.5.63 bug class: a symbol used at the
    module level (function call, class reference, etc.) without being
    imported. Bare `except Exception` can hide the resulting NameError
    at runtime."""

    def test_pyflakes_finds_no_undefined_names(self):
        rc, out = _run_pyflakes()
        if rc < 0:
            self.skipTest(
                "pyflakes not installed in this environment; "
                "install dev deps with `pip install -r requirements-dev.txt` "
                "to run this gate (v3.5.66 lists pyflakes in dev deps so "
                "CI runs the check on every commit)")
        findings = _undefined_name_findings(out)
        self.assertEqual(
            findings, [],
            f"pyflakes found {len(findings)} undefined-name issue(s) "
            f"in sidm2/ — fix each, or add `# noqa: F821` if it's a "
            f"deliberate forward reference / pyflakes false-positive. "
            f"This guard catches the v3.5.63-class regression (a "
            f"symbol used in code but not in module-level imports, "
            f"hidden by a bare except Exception). Findings:\n  "
            + "\n  ".join(findings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
