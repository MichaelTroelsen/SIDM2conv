"""PreToolUse(Write|Edit): refuse to create a .py file in the repo root.

CLAUDE.md Critical Rule #1 is "ALL .py files in pyscript/ only. No .py in root."
Until now that was enforced only by `cleanup.bat --scan`, a manual step nobody
runs mid-task, so the rule was discovered after the fact rather than prevented.

Deliberately NARROW: only the repo root itself. Subdirectories (sidm2/, bin/,
scripts/, .claude/hooks/) are all legitimate homes for .py files, and blocking
those would make the hook something people switch off.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0                                   # never block on a parse failure

    fp = (data.get("tool_input") or {}).get("file_path")
    if not fp:
        return 0

    try:
        target = Path(fp).resolve()
    except Exception:
        return 0

    if target.suffix.lower() != ".py":
        return 0
    if target.parent != REPO_ROOT:
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "CLAUDE.md Critical Rule #1: no .py files in the repo root -- "
                "ALL Python lives in pyscript/. Write it to pyscript/%s instead "
                "(or sidm2/ for package code, bin/ for a builder). Enforcement "
                "reference: cleanup.bat --scan, docs/guides/ROOT_FOLDER_RULES.md."
                % target.name
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
