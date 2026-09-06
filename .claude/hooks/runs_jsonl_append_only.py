"""PreToolUse(Write|Edit): refuse any whole-file write to runs.jsonl.

WHY THIS EXISTS. /runtask states this rule harder than any other it carries:

    "Append ONE line of JSON to `.claude/tasks/runs.jsonl` with a single `>>`
     redirect. NEVER by reading the file and writing it back: that discards
     anything appended meanwhile, and on a file whose whole value is that
     earlier lines are immutable it puts every historical record at risk of
     being rewritten by accident. A tool that 'appends' by rewriting the file
     is not appending."

Until now NOTHING enforced it. Worse, the one hook that could have --
enforce_touches.py -- deliberately ALLOW-LISTS this path, because every cycle
appends to it by design. So the single file the pipeline most needs protected
was the one file explicitly waved through the gate. This hook closes exactly
that hole and nothing else: enforce_touches decides WHICH paths a task may
write, this decides HOW this one path may be written.

The file currently holds 418 records, and roughly a dozen commit messages cite
them as their evidence. A single Write that reads-then-writes loses every record
appended by a concurrent runner in between, and the victim gets no error.

WHAT IS STILL ALLOWED, because the ban is on the TOOL, not on writing:
  * `printf '%s\\n' "$LINE" >> .claude/tasks/runs.jsonl` via Bash -- the
    sanctioned append, and the reason this hook cannot simply ban all writes;
  * every other file, including whattask.json and serial.lock, which have their
    own rules enforced elsewhere.

WHY IT BLOCKS Edit AS WELL AS Write. Edit is a read-modify-write on the whole
file too. It is also how a well-meant "fix the malformed line" would arrive --
and rewriting a historical record is precisely the outcome the append-only
invariant exists to prevent. If a line genuinely must be repaired, that is a
deliberate human act with a backup, not a tool call that slipped through.

DENIES rather than warns. A PostToolUse warning would arrive after the records
were already gone; this is the one invariant where the whole point is that the
damage is silent and unrecoverable.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PROTECTED = (REPO_ROOT / ".claude" / "tasks" / "runs.jsonl").resolve()


def resolves_to_protected(fp: str) -> bool:
    """True when `fp` names the run log, however it was spelled."""
    try:
        cand = Path(fp)
        if not cand.is_absolute():
            cand = REPO_ROOT / cand
        # resolve() so ./ , ../ and mixed separators all normalise. strict=False
        # because the file need not exist for the comparison to be meaningful.
        return cand.resolve() == PROTECTED
    except Exception:
        # A path we cannot even parse is not one we can prove is the run log.
        return False


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0                                   # never fail on a parse error

    tool = data.get("tool_name")
    if tool not in ("Write", "Edit"):
        return 0

    fp = (data.get("tool_input") or {}).get("file_path")
    if not fp or not resolves_to_protected(fp):
        return 0

    reason = (
        "REFUSED: %s is APPEND-ONLY and %s rewrites the whole file.\n\n"
        "It holds 418 records that a dozen commit messages cite as their "
        "evidence, and its entire value is that earlier lines never change. A "
        "read-then-write silently discards anything a concurrent runner "
        "appended in between -- and the run that loses its record gets no "
        "error, so the loss is invisible.\n\n"
        "Append with a single redirect from Bash instead:\n"
        "    printf '%%s\\\\n' \"$LINE\" >> .claude/tasks/runs.jsonl\n"
        "Build $LINE as ONE line of JSON (no embedded newline), so two writers "
        "interleave between records rather than inside one -- a torn JSONL line "
        "poisons every later read.\n\n"
        "If you are genuinely repairing a historical line, that is a deliberate "
        "act: back the file up first and do it outside this tool."
        % (fp, tool)
    )
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        },
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
