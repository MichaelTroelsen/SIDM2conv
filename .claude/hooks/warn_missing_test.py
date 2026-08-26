"""PostToolUse(Write|Edit): warn when a source file has no matching test file.

The repo convention is `pyscript/test_<name>.py` for every source `<name>.py`.
The /whattask plan's own notes record this rule being broken five times, and a
cross-check on 2026-08-26 found THIRTEEN more builders and tools with no test
file at all -- build_mon_native_song.py, build_sdi_native_song.py,
hardtrack_native_rebuild.py, sf2_editor_automation.py among them.

WARNS, never blocks. A missing test is a debt to record, not a reason to refuse
an edit -- and a PostToolUse hook cannot block the write anyway.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WATCHED = ("sidm2", "bin", "scripts")


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    ti = data.get("tool_input") or {}
    tr = data.get("tool_response") or {}
    fp = tr.get("filePath") or ti.get("file_path")
    if not fp:
        return 0

    try:
        target = Path(fp).resolve()
        rel = target.relative_to(REPO_ROOT)
    except Exception:
        return 0                                   # outside the repo: not ours

    if target.suffix.lower() != ".py":
        return 0
    if target.name.startswith("test_"):
        return 0                                   # a test needs no test
    parts = rel.parts
    if not parts or parts[0] not in WATCHED:
        return 0
    if parts[0] == "bin" and not target.name.startswith("build_"):
        return 0                                   # bin/ is full of one-off probes

    expected = REPO_ROOT / "pyscript" / ("test_%s.py" % target.stem)
    if expected.exists():
        return 0

    msg = ("No test file for %s -- this repo's convention is pyscript/test_%s.py, "
           "and it does not exist. That rule has already been broken 5+ times; a "
           "2026-08-26 cross-check found 13 source files with no test at all. If "
           "this edit changes behaviour, create the test rather than leaving the "
           "gap." % (rel.as_posix(), target.stem))
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
