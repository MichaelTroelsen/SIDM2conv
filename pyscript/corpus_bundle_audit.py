#!/usr/bin/env python3
"""Screen every built artifact for a BUNDLE COLLAPSE, and say what it found.

WHAT THIS SCREENS FOR. `sidm2.fidelity_common.bundle_collapse` flags an artifact
whose program tables carry almost no distinct rows -- the shape a build has when
its trace was empty or dead, so the music decoded and the per-note timbre data
did not. The floor is MEASURED, not chosen: `BUNDLE_FLOOR = 5` sits below the
lowest real build in the corpus.

WHAT IT DOES NOT SCREEN FOR, stated up front because a clean run reads like a
guarantee and is not one:

  * a count ABOVE the floor means "not the collapse this looks for", never
    "correct";
  * it is BLIND to a one-voice-dead trace. Measured: a control built with voice
    1 frozen for the whole song scores 24 bundles -- identical to the certified
    Balloon_part01. Losing one voice removes rows the other two still produce,
    so the distinct SET does not move;
  * `_PROGRAM_TABLES` names a "Pulse" table that does not exist in the SF2
    descriptor set at all (PATTERNS.md F15), so in practice this is a wave +
    filter measure;
  * Blackbird is excluded: its builds carry no .span and siddump cannot drive an
    LFT rip, so the comparison that would justify a number is unavailable.

WHY THIS SCRIPT EXISTS RATHER THAN A THROWAWAY. The 2026-09-04 audit that
produced the reference numbers was a scratch file with two defects worth not
repeating:

  * it called `bundle_diversity(f)` AND `bundle_collapse(f)`, and the latter
    calls the former again -- every file parsed TWICE, 13,580 parses for 6,790
    files, ~48 minutes for ~24 minutes of work. Here the measurement is taken
    ONCE and the floor applied to it locally;
  * it was launched without `-u` and printed only six lines, so the 8 KB stdout
    buffer never flushed and its output file sat at 0 bytes for the entire run
    -- indistinguishable from a hang. There was no way to tell a working sweep
    from a wedged one except by watching CPU time. This prints a HEARTBEAT
    every 15 seconds inside a corpus as well as a summary per corpus, and
    flushes every line -- a per-corpus summary alone still leaves minutes of
    silence on sdi (5,039 artifacts in one directory), which is the same defect
    wearing a smaller number. Same class as the closed
    passband-sweep-has-no-incremental-output.

USAGE
    py -3 pyscript/corpus_bundle_audit.py                 # all six corpora
    py -3 pyscript/corpus_bundle_audit.py --corpus sdi    # one
    py -3 pyscript/corpus_bundle_audit.py --limit 50      # sample, for a smoke test
    py -3 pyscript/corpus_bundle_audit.py --json out.json # machine-readable

EXIT CODE is 1 when anything is flagged, so this can gate a build. A deliberate
control artifact (out/dmc/EMPTYTRACE_CONTROL_part01.sf2) IS expected to flag --
`--exclude-controls` drops the known controls when you want the exit code to
mean "a real artifact collapsed".
"""
from __future__ import annotations

import argparse
import contextlib
import glob
import io
import json
import os
import sys
import time
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if os.path.join(ROOT, "pyscript") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "pyscript"))

from sidm2.fidelity_common import bundle_diversity, BUNDLE_FLOOR    # noqa: E402

# The six corpora this screen covers. Blackbird is absent on purpose -- see the
# module docstring; adding it would produce numbers nothing can justify.
CORPORA = ("dmc", "mon", "sdi", "hardtrack_native", "fc", "soundmonitor")

# Artifacts built deliberately degenerate, to prove the screen fires at all.
# Named rather than pattern-matched: a rule like "*CONTROL*" would silently
# excuse a real song someone names badly.
CONTROL_ARTIFACTS = (
    "EMPTYTRACE_CONTROL_part01.sf2",        # whole trace stubbed -- MUST flag
    "EMPTYTRACE_V1_CONTROL_part01.sf2",     # voice 1 dead -- must NOT flag
)


def measure(path):
    """One artifact -> (bundles|None, notes|None). ONE parse.

    Returns None for bundles when nothing could be read. That is UNMEASURABLE,
    not a collapse, and the difference is the whole point of this screen: an
    artifact that will not parse is UNSCREENED, and conflating it with a clean
    result is the defect this thread started from.

    The parser narrates to stdout/stderr; captured so progress stays readable.
    """
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            m = bundle_diversity(path)
    except Exception:                                          # noqa: BLE001
        return None, None
    if m is None:
        return None, None
    return m["bundles"], m["notes"]


def audit(corpora=CORPORA, limit=None, floor=BUNDLE_FLOOR, exclude_controls=False,
          progress=None):
    """Screen `corpora`, returning a result dict. Pure enough to test."""
    rows, flagged, unread = [], [], []
    dist = Counter()
    per_corpus = {}

    for c in corpora:
        d = os.path.join(ROOT, "out", c)
        files = sorted(glob.glob(os.path.join(d, "**", "*.sf2"), recursive=True))
        if limit:
            files = files[:limit]
        n_f = n_u = 0
        lo = None
        t0 = time.time()
        last_beat = t0
        for i, f in enumerate(files):
            # A HEARTBEAT, not just a per-corpus line. The corpus this screen
            # exists for has 5,039 artifacts in one directory, so a summary
            # printed only when a corpus FINISHES leaves minutes of silence --
            # which is a milder version of the exact defect this script was
            # written to fix. Throttled by TIME rather than by a file count so
            # it stays quiet on the 19-file corpora and talkative on the big one.
            if progress and time.time() - last_beat >= 15.0:
                last_beat = time.time()
                progress("  %-16s %5d/%-5d  %.0f%%  (%d flagged so far)"
                         % (c, i, len(files), 100.0 * i / max(1, len(files)), n_f))
            base = os.path.basename(f)
            if exclude_controls and base in CONTROL_ARTIFACTS:
                continue
            bundles, notes = measure(f)
            rel = os.path.relpath(f, ROOT).replace("\\", "/")
            if bundles is None:
                unread.append(rel)
                n_u += 1
                continue
            dist[bundles] += 1
            lo = bundles if lo is None else min(lo, bundles)
            rows.append({"corpus": c, "path": rel, "bundles": bundles, "notes": notes})
            if bundles <= floor:
                flagged.append({"corpus": c, "path": rel, "bundles": bundles,
                                "notes": notes, "control": base in CONTROL_ARTIFACTS})
                n_f += 1
        per_corpus[c] = {"scanned": len(files), "flagged": n_f, "unread": n_u,
                         "min_bundles": lo, "seconds": round(time.time() - t0, 1)}
        if progress:
            progress("%-18s scanned=%-5d flagged=%-4d unread=%-4d min=%-5s %5.1fs"
                     % (c, len(files), n_f, n_u, lo, per_corpus[c]["seconds"]))

    return {
        "floor": floor,
        "scanned": sum(v["scanned"] for v in per_corpus.values()),
        "flagged": flagged,
        "unread": unread,
        "per_corpus": per_corpus,
        "distribution": dict(sorted(dist.items())),
        "rows": rows,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--corpus", action="append", choices=list(CORPORA),
                    help="limit to one corpus (repeatable); default is all six")
    ap.add_argument("--limit", type=int, help="first N artifacts per corpus (smoke test)")
    ap.add_argument("--floor", type=int, default=BUNDLE_FLOOR,
                    help="override BUNDLE_FLOOR (default %d -- it is MEASURED, "
                         "so raising it is a claim, not a tweak)" % BUNDLE_FLOOR)
    ap.add_argument("--exclude-controls", action="store_true",
                    help="drop the deliberate control artifacts, so a nonzero exit "
                         "means a REAL artifact collapsed")
    ap.add_argument("--json", help="write the full result here")
    a = ap.parse_args(argv)

    def say(line):
        print(line, flush=True)          # flush: a buffered sweep looks wedged

    t0 = time.time()
    res = audit(corpora=tuple(a.corpus) if a.corpus else CORPORA,
                limit=a.limit, floor=a.floor,
                exclude_controls=a.exclude_controls, progress=say)

    say("")
    say("BUNDLE_FLOOR = %d" % res["floor"])
    say("scanned %d | flagged %d | unread %d | %.1fs"
        % (res["scanned"], len(res["flagged"]), len(res["unread"]), time.time() - t0))

    low = [(k, v) for k, v in res["distribution"].items() if k <= 20]
    if low:
        say("")
        say("low tail: " + ", ".join("%d:%d" % kv for kv in low))

    if res["flagged"]:
        say("")
        say("FLAGGED:")
        for r in sorted(res["flagged"], key=lambda x: (x["bundles"], x["path"])):
            say("  %-52s %2d bundles / %5s notes%s"
                % (r["path"], r["bundles"], r["notes"],
                   "   <- deliberate control" if r["control"] else ""))

    if res["unread"]:
        say("")
        say("UNREAD (unmeasurable -- NOT a pass and NOT a collapse):")
        for p in res["unread"][:20]:
            say("  " + p)
        if len(res["unread"]) > 20:
            say("  ... and %d more" % (len(res["unread"]) - 20))

    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1)
        say("")
        say("wrote %s" % a.json)

    return 1 if res["flagged"] else 0


if __name__ == "__main__":
    sys.exit(main())
