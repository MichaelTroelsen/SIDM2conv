"""PostToolUse(Write|Edit): warn when a file is left with MIXED line endings.

WHY THIS EXISTS. This repo has no .gitattributes and `core.autocrlf` is true, so
line endings are a PER-FILE property rather than a repo-wide one. Measured:
sidm2/conversion_pipeline.py, sidm2/sequence_translator.py, sidm2/dmc_parser.py
and bin/build_mon_native_song.py are uniform CRLF; bin/build_sdi_native_song.py,
pyscript/test_mon_filter.py and most pyscript/test_*.py are pure LF. A patch
script that emits "\n" into a CRLF file leaves the file mixed, git then reports
a whole-file diff, and the change becomes unreviewable.

That happened THREE times in one session (2026-09-06) -- each caught only by a
manual byte count afterwards, and each costing a normalise-and-recheck round.

WARNS, never blocks. A PostToolUse hook cannot undo the write, and mixed endings
are a thing to fix rather than a reason to refuse an edit.

WHY IT COUNTS BYTES AND NOT `grep -c '\\r'`. The obvious check is wrong: grep
counts LINES CONTAINING a carriage return, so on a 549-line pure-LF file whose
content happens to include \\r it answers 549 and reads as "uniformly CRLF".
The only reliable test is `data.count(b"\\r\\n")` against
`data.count(b"\\n") - data.count(b"\\r\\n")`, which is what this does.

WHY IT DOES NOT FLAG A FILE THAT WAS ALREADY MIXED BEFORE THE EDIT. It cannot
know: PostToolUse runs after the write and there is no before-image. Flagging the
current state is still right -- a mixed file is worth fixing whoever made it --
but the message says "now mixed", not "you made it mixed", because the hook has
no evidence for the stronger claim.
"""
import json
import sys
from pathlib import Path

# Binary and generated files where a mixed count means nothing.
SKIP_SUFFIXES = {
    ".sid", ".sf2", ".prg", ".png", ".wav", ".exe", ".bin", ".d64",
    ".zip", ".pyc", ".jpg", ".gif", ".pdf",
}
MAX_BYTES = 8 * 1024 * 1024


def endings(data: bytes):
    """(crlf_count, bare_lf_count) -- byte counts, never a line-based grep."""
    crlf = data.count(b"\r\n")
    return crlf, data.count(b"\n") - crlf


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0                                   # never fail on a parse error

    fp = (data.get("tool_input") or {}).get("file_path")
    if not fp:
        return 0

    try:
        target = Path(fp)
        if target.suffix.lower() in SKIP_SUFFIXES:
            return 0
        if not target.is_file() or target.stat().st_size > MAX_BYTES:
            return 0
        raw = target.read_bytes()
    except Exception:
        return 0

    if b"\x00" in raw[:4096]:                      # git treats it as binary
        return 0

    crlf, lf = endings(raw)
    if crlf == 0 or lf == 0:                       # uniform either way -- fine
        return 0

    dominant = "CRLF" if crlf >= lf else "LF"
    stray = lf if crlf >= lf else crlf
    msg = (
        "LINE ENDINGS ARE NOW MIXED in %s: %d CRLF and %d bare LF. This repo "
        "has no .gitattributes and core.autocrlf is true, so a mixed file "
        "produces a whole-file diff and the real change becomes unreviewable. "
        "The file is predominantly %s with %d stray line(s). Normalise before "
        "moving on, e.g. read the file as bytes and "
        "`b.replace(b'\\r\\n', b'\\n').replace(b'\\n', b'\\r\\n')` for CRLF (drop "
        "the second replace for LF), then re-check by COUNTING BYTES -- "
        "`grep -c '\\r'` counts lines and will tell you a pure-LF file is CRLF."
        % (fp, crlf, lf, dominant, stray)
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
