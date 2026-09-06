"""PreToolUse(Write|Edit): refuse a write outside the running task's `touches`.

WHY THIS EXISTS. /runtask's central rule is "AN UNDECLARED PATH IS A STOP, NEVER
A GRANT" -- the task's `touches` is the complete list of paths it may write, and
the lock was claimed on that basis, so a path taken afterwards means the
contention arithmetic was guarding the wrong set. Over a long session that rule
was enforced entirely by reading, and it is the single most common stop: seven
tasks in one day (2026-09-06) refused because the fix site was undeclared.

Reading is not writing: this hook only ever looks at Write/Edit targets.

WHEN IT IS SILENT, which is most of the time:
  * `.claude/tasks/serial.lock` is missing, empty, or unparseable -- no task is
    in flight, so there is nothing to enforce and a config problem must not
    become an edit block;
  * the target is outside the repo (scratchpad probes, temp files);
  * the target is the runner's own append-only log or lock files, which every
    cycle writes by design.

WHY AN EMPTY REGISTRY ALLOWS EVERYTHING. A hook that blocked whenever no record
was held would break every ordinary session that is not running /runtask at all.
The registry being non-empty IS the signal that a gated task is in flight.

WHY IT UNIONS ALL HOLDERS RATHER THAN MATCHING THIS PROCESS. The runner shells
out, so the pid writing a file is not the pid in the record -- a lesson already
recorded once when a sweep's registry pid (21732) and its journal pid (39620)
turned out to be different processes. Matching on pid would make the hook fire
on every legitimate write. The union is the safe over-approximation: it can miss
a cross-task violation while two tasks are held, and it never blocks a write the
plan actually allows.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOCK = REPO_ROOT / ".claude" / "tasks" / "serial.lock"

# Paths every /runtask cycle writes by design, independent of `touches`.
ALWAYS_ALLOWED = {
    ".claude/tasks/runs.jsonl",
    ".claude/tasks/serial.lock",
    ".claude/tasks/serial.lock.tmp",
}


def declared_writable(records):
    """Union of the rw: paths across every held record, repo-relative, /-joined."""
    out = set()
    for rec in records:
        for entry in rec.get("touches") or []:
            if entry.startswith("r:"):             # read-only: not a grant
                continue
            path = entry[3:] if entry.startswith("rw:") else entry
            if path.startswith("desktop-singleton:"):
                continue                           # a resource, not a file path
            out.add(path.replace("\\", "/").strip("/"))
    return out


def covered(rel: str, writable) -> bool:
    """A path is allowed if it equals a declared path or sits under one."""
    return any(rel == d or rel.startswith(d + "/") for d in writable)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    fp = (data.get("tool_input") or {}).get("file_path")
    if not fp:
        return 0

    try:
        records = json.loads(LOCK.read_text(encoding="utf-8"))
    except Exception:
        return 0                                   # no lock, or unreadable
    if isinstance(records, dict):
        records = [records]
    if not records:
        return 0                                   # no task in flight

    try:
        rel = Path(fp).resolve().relative_to(REPO_ROOT).as_posix()
    except Exception:
        return 0                                   # outside the repo

    if rel in ALWAYS_ALLOWED:
        return 0

    writable = declared_writable(records)
    if covered(rel, writable):
        return 0

    holders = ", ".join(r.get("task", "?") for r in records)
    listed = ", ".join(sorted(writable)) or "(none)"
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                "UNDECLARED PATH: %s is not in the running task's touches. "
                "Held: %s. Writable: %s. /runtask's rule is that an undeclared "
                "path is a STOP, never a grant -- the lock was claimed on the "
                "declared set, so writing outside it means the contention "
                "arithmetic guarded the wrong paths and nothing downstream can "
                "detect that. Record the task `blocked`, name this path, and "
                "get a corrected touches from /whattask."
                % (rel, holders, listed)
            ),
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
