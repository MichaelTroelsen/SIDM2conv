"""PostToolUse(Edit): warn when doc text adds a PERCENTAGE with no condition.

WHY THIS EXISTS. This is the repo's single most-recorded defect class, and
CLAUDE.md is largely a monument to it:

    "the older 17/19 and 18/20 are RETRACTED ... both were measured over
     `*_sub0_part01` only"
    "Read older 'filter 100%' figures as cutoff only"
    "99.93% is a TARGET, not a measurement"
    "HARDTRACK.md ... has retracted 2 published claims"
    "a voice compared over 46 frames printed a 100.0 identical to one
     compared over 6,000"

Every one is the same shape: a percentage published without the denominator,
window, or file count that makes it true. fidelity_common.py already carries
three guards for this in the MEASUREMENT path -- score_pct returns None on a
zero denominator, exercised() catches vacuous agreement, underpowered() flags a
too-small n and fmt_pct suffixes it with "!". This hook is the same discipline
one step later, on the DOCUMENT, where the number outlives the run that made it.

WARNS, never blocks, and never rewrites. Whether a figure needs its window
stated is a judgement about what is being claimed; a hook can only notice that
none is nearby.

SCOPE: Edit ONLY, and only the `new_string`. A PostToolUse hook has no
before-image (check_line_endings.py alongside it records the same limitation),
so on a Write there is no way to tell an added percentage from one that has sat
in the file for six months -- and re-flagging the whole of CLAUDE.md on every
touch would be noise that teaches the reader to ignore it. Restricting to the
text an Edit actually introduced is the only scoping with a real before/after.
The cost is honest and worth stating: a percentage added by a full-file Write is
NOT checked.

WHAT COUNTS AS A CONDITION is deliberately generous -- an n, a denominator, a
unit being counted, a window, a named span, or an explicit retraction/target
marker all satisfy it. The aim is to catch the bare "97.4%" with nothing around
it, not to grade how well-qualified a well-qualified figure is.
"""
import json
import re
import sys

WATCHED_SUFFIXES = (".md",)

PCT = re.compile(r"\b\d{1,3}(?:\.\d+)?\s?%")

# Anything that tells the reader what the number was measured over.
CONDITION = re.compile(
    r"""
      \bn\s*[=:]\s*\d          # n=346
    | \bn\s+\d{2,}             # "n 346-2253"
    | \d+\s*(?:of|/)\s*\d+     # 22 of 27, 12/24
    | \b(?:frames?|files?|voices?|parts?|songs?|subtunes?|notes?|note-ons?
        |rows?|entries|tunes?|sequences?|instruments?|onsets?)\b
    | \b(?:window|span|median|mean|over|across|within|per\b)
    | \bRETRACTED\b | \bTARGET\b | \bnot\s+a\s+measurement\b
    | \bunverified\b | \bdoc-carried\b | \bpessimistic\b
    """,
    re.I | re.X,
)

MAX_REPORTED = 4


def unconditioned(text: str):
    """Lines in `text` carrying a % with no condition on or beside them."""
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if not PCT.search(line):
            continue
        window = " ".join(lines[max(0, i - 1):i + 2])
        if CONDITION.search(window):
            continue
        out.append((i + 1, line.strip()))
    return out


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0

    if data.get("tool_name") != "Edit":
        return 0                      # Write has no before-image -- see module docstring

    ti = data.get("tool_input") or {}
    fp = ti.get("file_path") or ""
    if not fp.lower().endswith(WATCHED_SUFFIXES):
        return 0

    new = ti.get("new_string")
    if not isinstance(new, str) or not new.strip():
        return 0

    # Only flag what this edit INTRODUCED: a percentage already present in the
    # old text is not this edit's doing.
    old = ti.get("old_string") or ""
    hits = [h for h in unconditioned(new) if h[1] not in old]
    if not hits:
        return 0

    shown = "\n  ".join("L%d: %s" % (n, t[:110]) for n, t in hits[:MAX_REPORTED])
    more = "" if len(hits) <= MAX_REPORTED else (
        "\n  (+%d more)" % (len(hits) - MAX_REPORTED))
    msg = (
        "UNCONDITIONED FIGURE in %s -- %d percentage(s) added with no n, "
        "denominator, unit, or window nearby:\n  %s%s\n"
        "This repo's most-retracted defect class. CLAUDE.md already carries "
        "\"the older 17/19 and 18/20 are RETRACTED\" (measured over "
        "*_sub0_part01 only), \"read older 'filter 100%%' figures as cutoff "
        "only\", and \"99.93%% is a TARGET, not a measurement\". A figure "
        "outlives the run that produced it, so state what it was measured "
        "over -- n, the file or frame count, the window, and which column "
        "(raw vs audible) -- or say plainly that it is doc-carried and "
        "unverified."
        % (fp, len(hits), shown, more)
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
