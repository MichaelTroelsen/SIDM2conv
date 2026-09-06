"""SessionStart: print the task pipeline's state once, instead of 25 times.

WHY THIS EXISTS. Every /runtask cycle re-derives the same three facts by hand
before it can choose anything: is the plan still keyed to HEAD, does the lock
registry hold records whose process is gone, and how many tasks actually pass
their gates. In one session (2026-09-06) that computation ran about twenty-five
times and produced the same answer each time -- while the fact that MATTERED,
that seven of the eight gate-passing tasks had already recorded an
undeclared-path stop AT THIS SAME HEAD, took eight cycles to become visible.

Front-loading it makes a spent plan visible BEFORE a cycle is spent on it.

WHAT IT DOES NOT DO. It does not pick a task, claim a lock, reap anything, or
write. Reaping in particular is deliberately left to /runtask: that must happen
INSIDE the mutex, against a registry re-read from disk, and a SessionStart hook
holds no mutex. So orphans are REPORTED here and reaped there -- naming a
suspect is safe, acting on it outside the lock is the race the mutex exists to
prevent.

READINESS COMES FROM THE RUN LOG, NEVER FROM THE PLAN. A task absent from
whattask.json may be absent because it is DONE; /whattask drops closed tasks. An
earlier cycle misread exactly that and nearly argued against a correct close. So
`done` is computed from the LAST record per id across the whole log, and the
plan is used only for the task list.

IT FAILS SILENT. A missing plan, an unparseable registry or a git that will not
run all mean "print less", never "break the session". A status line is a
convenience; nothing downstream may depend on it.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TASKS = REPO_ROOT / ".claude" / "tasks"
PLAN = TASKS / "whattask.json"
RUNS = TASKS / "runs.jsonl"
LOCK = TASKS / "serial.lock"
MUTEX = TASKS / "serial.lock.d"

GIT_TIMEOUT_S = 10


def head_sha():
    try:
        r = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                           cwd=str(REPO_ROOT), capture_output=True, text=True,
                           timeout=GIT_TIMEOUT_S)
        return r.stdout.strip() or None
    except Exception:
        return None


def pid_alive(pid) -> bool:
    """True when the pid is running. Unknown -> True, so we never call a live
    holder an orphan on a probe failure."""
    try:
        pid = int(pid)
    except Exception:
        return True
    try:
        if os.name == "nt":
            r = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"],
                               capture_output=True, text=True, timeout=GIT_TIMEOUT_S)
            return str(pid) in (r.stdout or "")
        os.kill(pid, 0)
        return True
    except Exception:
        return True


def read_runs():
    """(last record per id, record count, blank-line numbers)."""
    last, n, blanks = {}, 0, []
    try:
        raw = RUNS.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return last, 0, blanks
    for i, line in enumerate(raw.split("\n"), 1):
        if not line.strip():
            if i <= raw.count("\n"):        # ignore the trailing newline itself
                blanks.append(i)
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        n += 1
        last[r.get("id")] = r
    return last, n, blanks


def main() -> int:
    if not PLAN.is_file():
        return 0                                   # no pipeline here -- silent

    try:
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        tasks = plan.get("tasks") or []
    except Exception:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "TASK PIPELINE: .claude/tasks/whattask.json "
                                 "does not parse. /runtask will stop on it; "
                                 "re-run /whattask.",
        }}))
        return 0

    last, n_records, blanks = read_runs()
    done = {i for i, r in last.items() if r.get("outcome") == "done"}

    lines = []

    # --- plan freshness -----------------------------------------------------
    plan_head = (plan.get("generated_from") or {}).get("head")
    head = head_sha()
    if plan_head and head and not (plan_head.startswith(head)
                                   or head.startswith(plan_head)):
        lines.append("PLAN IS STALE: keyed to %s, HEAD is %s. It may list tasks "
                     "that are already closed -- re-run /whattask."
                     % (plan_head, head))
    elif plan_head:
        lines.append("Plan fresh at %s." % plan_head)

    # --- gate arithmetic ----------------------------------------------------
    ready, requires_user, dep_blocked = [], 0, 0
    for t in tasks:
        if t.get("id") in done:
            continue
        if t.get("mode") == "requires-user":
            requires_user += 1
            continue
        if any(d not in done for d in (t.get("depends_on") or [])):
            dep_blocked += 1
            continue
        ready.append(t)

    lines.append("%d tasks, %d done, %d pass their gates (%d requires-user, "
                 "%d dependency-blocked). %d run records."
                 % (len(tasks), len(done), len(ready), requires_user,
                    dep_blocked, n_records))

    # --- the fact that took eight cycles to surface -------------------------
    # A task that already stopped at THIS head will stop the same way again;
    # only a corrected `touches` from /whattask changes that.
    repeats = [t["id"] for t in ready
               if last.get(t.get("id"), {}).get("outcome") == "blocked"
               and head and last[t["id"]].get("head", "").startswith(head[:7])]
    if repeats and len(repeats) >= max(1, len(ready) - 1):
        lines.append("WARNING: %d of the %d gate-passing tasks already recorded "
                     "`blocked` at THIS head (%s). They will block again -- the "
                     "fix is a corrected `touches` from /whattask, not another "
                     "cycle. First: %s"
                     % (len(repeats), len(ready), head, ", ".join(repeats[:3])))
    elif repeats:
        lines.append("%d gate-passing task(s) already blocked at this head: %s"
                     % (len(repeats), ", ".join(repeats[:3])))

    # --- registry: report suspects, never reap ------------------------------
    if MUTEX.is_dir():
        lines.append("MUTEX HELD: .claude/tasks/serial.lock.d exists. Another "
                     "runner may be mid-update, or it was left behind.")
    if LOCK.is_file():
        try:
            recs = json.loads(LOCK.read_text(encoding="utf-8"))
            if isinstance(recs, dict):
                recs = [recs]
        except Exception:
            recs = None
            lines.append("REGISTRY DOES NOT PARSE: .claude/tasks/serial.lock. "
                         "Stop and say so -- never overwrite it.")
        if recs:
            orphans = [r for r in recs if not pid_alive(r.get("pid"))]
            lines.append("Registry holds %d record(s): %s."
                         % (len(recs), ", ".join(str(r.get("task"))
                                                 for r in recs[:4])))
            if orphans:
                lines.append("  %d look orphaned (pid not running): %s. /runtask "
                             "reaps these INSIDE its mutex -- do not remove them "
                             "here." % (len(orphans),
                                        ", ".join(str(o.get("task"))
                                                  for o in orphans[:4])))

    if blanks:
        lines.append("runs.jsonl has %d blank line(s) at %s -- harmless to an "
                     "append, but a naive json.loads over every line will crash "
                     "on them." % (len(blanks),
                                   ", ".join(str(b) for b in blanks[:5])))

    msg = "TASK PIPELINE\n  " + "\n  ".join(lines)
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": msg,
    }}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)                     # a status line never breaks a session
