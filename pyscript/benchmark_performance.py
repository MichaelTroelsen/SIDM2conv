#!/usr/bin/env python3
"""Conversion performance benchmark — a fixed SID set, timed with its SPREAD.

    py -3 pyscript/benchmark_performance.py                 # 5 files x 3 repeats
    py -3 pyscript/benchmark_performance.py --repeats 5
    py -3 pyscript/benchmark_performance.py --json out.json # machine-readable
    py -3 pyscript/benchmark_performance.py --list          # print the set, run nothing

WHY THIS NEVER PRINTS ONE NUMBER. A benchmark whose figure is not reproducible
across two runs on the same machine is not a benchmark, it is a sample. Every
row here reports min / median / max and the SPREAD between them, and `--repeats`
is refused below 2 because one run cannot show a spread at all. A row whose
spread exceeds SPREAD_WARN is flagged `!` — that is the benchmark telling you
its own number is not yet trustworthy, not a failure of the code under test.

THE FIRST REPEAT IS REPORTED SEPARATELY rather than discarded. It carries
interpreter start-up, bytecode compilation and OS file-cache misses, which are
real costs a caller pays once; hiding them in a mean makes cold and warm runs
indistinguishable, and silently dropping them is how a benchmark starts
flattering itself. `cold` is repeat 1; min/median/max cover repeats 2..N.

THE FIXED SET IS TRACKED IN GIT, deliberately. A benchmark that measures files
which exist only on the machine that wrote it cannot be compared against anyone
else's run — the same weakness that made an untracked corpus sweep in this repo
unauditable. Every entry below was confirmed `git ls-files`-tracked and
converting with rc=0 on 2026-09-05. A member that goes missing is REPORTED, not
skipped quietly, because a shorter set with the same headline is the failure
this note exists to prevent.

NOTHING IS WRITTEN INSIDE THE REPO. Each conversion emits into a temporary
directory created by this script and removed afterwards, so running the
benchmark never touches out/, SF2/ or the working tree.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONVERTER = os.path.join(ROOT, "scripts", "sid_to_sf2.py")

# A row whose (max-min)/median exceeds this is flagged as not-yet-reproducible.
SPREAD_WARN = 0.20

# The fixed set: one file per driver path the converter can take, so a timing
# change can be attributed to a family rather than to "conversion" in general.
FIXED_SET = [
    ("laxity-np21", "SID/Stinsens_Last_Night_of_89.sid"),
    ("laxity-variant", "SID/Angular.sid"),
    ("mon", "SID/Tel_Jeroen/Cybernoid_II.sid"),
    ("dmc", "SID/JohannesBjerregaard/Dreaming_2.sid"),
    ("hardtrack", "SID/Shogoon/Shogoon-Rave.sid"),
]


def _tracked(rel):
    """Is this path tracked in git? Unknown (no git) is reported as None."""
    try:
        r = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                           cwd=ROOT, capture_output=True, timeout=30)
        return r.returncode == 0
    except Exception:                                        # noqa: BLE001
        return None


def _convert_once(rel, outdir, i):
    """One end-to-end conversion. Returns (seconds, returncode, diagnostic).

    Each repeat gets its OWN destination filename. Writing every repeat to the
    same path made later repeats behave differently from the first -- which is
    a benchmark measuring its own leftovers rather than the conversion, and it
    is why this returns the tail of stderr on a failure instead of a bare code.
    """
    dst = os.path.join(outdir, "%s_r%d.sf2" % (os.path.basename(rel)[:-4], i))
    t0 = time.perf_counter()
    r = subprocess.run([sys.executable, CONVERTER, os.path.join(ROOT, rel), dst],
                       cwd=ROOT, capture_output=True)
    dt = time.perf_counter() - t0
    if r.returncode == 0:
        return dt, 0, ""
    err = (r.stderr or r.stdout or b"").decode("utf-8", "replace").strip()
    return dt, r.returncode, err[-400:]


def measure(rel, repeats, outdir):
    """Time `repeats` conversions. Returns a dict, or None if the file is gone."""
    if not os.path.exists(os.path.join(ROOT, rel)):
        return None
    times, rcs, errs = [], [], []
    for i in range(repeats):
        dt, rc, err = _convert_once(rel, outdir, i)
        times.append(dt)
        rcs.append(rc)
        if err:
            errs.append(err)
    warm = times[1:]                       # repeat 1 is reported separately
    return {
        "cold": times[0],
        "min": min(warm), "median": statistics.median(warm), "max": max(warm),
        "runs": times, "returncodes": rcs, "errors": errs,
        "ok": all(rc == 0 for rc in rcs),
    }


def _spread(m):
    return (m["max"] - m["min"]) / m["median"] if m["median"] else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repeats", type=int, default=3,
                    help="conversions per file; must be >= 2 (default 3)")
    ap.add_argument("--json", metavar="PATH", help="also write results as JSON")
    ap.add_argument("--list", action="store_true",
                    help="print the fixed set and its tracked status, run nothing")
    a = ap.parse_args()

    if a.list:
        print("%-16s %-9s %s" % ("family", "tracked", "path"))
        for fam, rel in FIXED_SET:
            t = _tracked(rel)
            print("%-16s %-9s %s%s" % (fam, {True: "yes", False: "NO", None: "?"}[t],
                                       rel, "" if os.path.exists(os.path.join(ROOT, rel))
                                       else "   <== MISSING ON DISK"))
        return 0

    if a.repeats < 2:
        print("--repeats must be at least 2: one run cannot show a spread, and a "
              "benchmark that reports a single figure is a sample, not a benchmark.")
        return 2
    if not os.path.exists(CONVERTER):
        print("converter not found: %s" % os.path.relpath(CONVERTER, ROOT))
        return 2

    outdir = tempfile.mkdtemp(prefix="sidm2_bench_")
    results, missing = {}, []
    try:
        print("conversion benchmark | %d files x %d repeats | output -> %s"
              % (len(FIXED_SET), a.repeats, outdir), flush=True)
        print()
        for fam, rel in FIXED_SET:
            m = measure(rel, a.repeats, outdir)
            if m is None:
                missing.append(rel)
                print("  %-16s MISSING: %s" % (fam, rel), flush=True)
                continue
            results[rel] = dict(m, family=fam)
            print("  %-16s cold %6.2fs | warm min %6.2f med %6.2f max %6.2f%s"
                  % (fam, m["cold"], m["min"], m["median"], m["max"],
                     "" if m["ok"] else "   <== NON-ZERO EXIT"), flush=True)
    finally:
        shutil.rmtree(outdir, ignore_errors=True)

    print()
    print("%-16s %8s %8s %8s %8s  %8s" %
          ("family", "cold", "min", "median", "max", "spread"))
    flagged = []
    for rel, m in results.items():
        sp = _spread(m)
        mark = "!" if sp > SPREAD_WARN else " "
        if sp > SPREAD_WARN:
            flagged.append(rel)
        print("%-16s %7.2fs %7.2fs %7.2fs %7.2fs  %6.1f%% %s"
              % (m["family"], m["cold"], m["min"], m["median"], m["max"], 100 * sp, mark))

    if results:
        meds = [m["median"] for m in results.values()]
        print()
        print("TOTAL of the per-file medians: %.2fs over %d files "
              "(this is a SUM OF MEDIANS, not a measured total run)"
              % (sum(meds), len(results)))
    if flagged:
        print()
        print("!  %d row(s) exceed a %.0f%% spread and are NOT yet reproducible: %s"
              % (len(flagged), 100 * SPREAD_WARN, ", ".join(os.path.basename(f) for f in flagged)))
        print("   Re-run with more --repeats, or on a quieter machine, before "
              "quoting these numbers.")
    if missing:
        print()
        print("!  %d fixed-set member(s) MISSING -- the set below is not the one "
              "these numbers describe: %s" % (len(missing), ", ".join(missing)))

    bad = [r for r, m in results.items() if not m["ok"]]
    if bad:
        print()
        print("!  %d file(s) returned a non-zero exit; their timings measure a "
              "FAILING path, not a conversion:" % len(bad))
        for r in bad:
            m = results[r]
            print("     %-22s rc=%s" % (os.path.basename(r), m["returncodes"]))
            if m["errors"]:
                for ln in m["errors"][0].splitlines()[-4:]:
                    print("       | %s" % ln)

    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump({"repeats": a.repeats, "spread_warn": SPREAD_WARN,
                       "results": results, "missing": missing,
                       "flagged_spread": flagged, "nonzero_exit": bad}, f, indent=1)
        print()
        print("wrote %s" % a.json)

    # exit 1 when the run cannot be trusted: a missing member, a failing
    # conversion, or a spread too wide to quote.
    return 1 if (missing or bad or flagged) else 0


if __name__ == "__main__":
    sys.exit(main())
