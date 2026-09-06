"""PostToolUse(Write|Edit): run pyflakes on the .py file that was just edited.

WHY THIS EXISTS. requirements-dev.txt states the cost of this bug class in as
many words: v3.5.63 shipped `extract_all_laxity_tables` used without being
imported, and a bare `except Exception` swallowed the resulting NameError FOR
NINE RELEASES. pyflakes is already a project-level expectation for exactly that
reason.

WHAT THIS ADDS OVER pyscript/test_pyflakes_undefined.py, which already exists.
That gate is narrower in three ways, and each gap is where the nine releases
went:
  * it checks `sidm2/` ONLY -- not bin/, pyscript/ or scripts/, which is where
    every builder and sweep lives;
  * it runs when someone runs the suite, not when the file is written;
  * it SKIPS CLEANLY when pyflakes is not importable, so an environment without
    it reports green rather than unchecked.
This hook checks the one file just edited, wherever it lives, at the moment it
is written. It does not replace the test -- the test is what CI enforces.

WARNS, never blocks. A PostToolUse hook cannot undo the write, and a half-typed
file mid-refactor is a normal intermediate state, not a reason to refuse an
edit. Same reasoning as check_line_endings.py alongside it.

TWO SEVERITY CLASSES, because reporting all of pyflakes at equal volume trains
the reader to skim it. HARD findings are the ones that mean the code is WRONG at
runtime -- an undefined name, a use before assignment, a redefinition that
silently discards the first binding (that last one is the v3.5.63 shape). Those
are named individually with their line numbers. Everything else -- unused
imports, f-strings without placeholders -- is COUNTED and not listed, so a
tidy-up suggestion never buries a NameError.

IF pyflakes IS NOT INSTALLED this hook stays SILENT rather than nagging on every
edit. The test gate already carries the "install requirements-dev.txt" message,
and a hook that fires on every single write is the wrong place to repeat it.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

# Substrings that mean the code is wrong at runtime, not merely untidy.
HARD = (
    "undefined name",
    "local variable",            # ... referenced before assignment
    "redefinition of unused",    # the shape that hid the v3.5.63 NameError
    "syntax error",
)
# pyflakes cannot trace symbols through `from X import *`; sidm2/__init__.py
# uses two star imports deliberately. Same suppression the test gate applies.
STAR_IMPORT = "may be undefined, or defined from star imports"

TIMEOUT_S = 20


def classify(lines):
    hard, soft = [], 0
    for line in lines:
        low = line.lower()
        if not line.strip() or STAR_IMPORT in line:
            continue
        if any(h in low for h in HARD):
            hard.append(line.strip())
        else:
            soft += 1
    return hard, soft


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0                                   # never fail on a parse error

    fp = (data.get("tool_input") or {}).get("file_path")
    if not fp or not fp.lower().endswith(".py"):
        return 0

    target = Path(fp)
    try:
        if not target.is_file():
            return 0
    except Exception:
        return 0

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pyflakes", str(target)],
            capture_output=True, text=True, timeout=TIMEOUT_S,
        )
    except Exception:
        return 0                    # not installed, or too slow -- stay silent

    # `python -m pyflakes` on a missing module exits 1 with an ImportError on
    # stderr and nothing on stdout. Distinguish that from real findings.
    if "No module named" in (proc.stderr or ""):
        return 0
    if proc.returncode == 0 and not proc.stdout.strip():
        return 0

    hard, soft = classify((proc.stdout or "").splitlines())
    if not hard:
        return 0                    # soft findings alone are not worth a nag

    # Strip the absolute path prefix so the message stays readable.
    shown = [re.sub(r"^.*[\\/]([^\\/]+:\d+)", r"\1", h) for h in hard[:8]]
    more = "" if len(hard) <= 8 else "  (+%d more)" % (len(hard) - 8)
    tail = "" if not soft else (
        " %d further pyflakes finding(s) (unused imports and similar) are not "
        "listed -- they do not change runtime behaviour." % soft
    )
    msg = (
        "PYFLAKES: %d runtime-affecting finding(s) in %s --\n  %s%s\n"
        "These are the class that shipped in v3.5.63 and survived NINE "
        "releases, because a bare `except Exception` swallowed the NameError. "
        "Fix before relying on this file; a wrapping try/except will hide it "
        "rather than surface it.%s"
        % (len(hard), fp, "\n  ".join(shown), more, tail)
    )
    print(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": msg,
        },
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
