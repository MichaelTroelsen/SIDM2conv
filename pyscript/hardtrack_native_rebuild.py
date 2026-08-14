#!/usr/bin/env python3
"""Rebuild the whole HardTrack Stage B corpus with the CURRENT builder.

A fix in the builder is not a fix in the corpus (PATTERNS.md F7). Four players
shipped artifacts that contradicted their own documentation because a builder
change was never carried into `out/`, and every fidelity scorer here was blind to
the register that had changed. So a change to the driver or the shim ends with
this, not with one file rebuilt by hand.

It clears `out/hardtrack_native/` first -- a stale artifact that no longer builds
is exactly what the audit above kept finding -- then rebuilds every SID in
SID/Shogoon/ the builder accepts, at the DEFAULT window ('auto', the full song),
which is what a shipped artifact is. A measurement window like the sweep's -t 60
is not.

  py -3 pyscript/hardtrack_native_rebuild.py [--first N] [--last N] [--keep]

Chunk it with --first/--last (a single parent died at ~275 builds elsewhere);
--keep skips the clear so chunks after the first do not wipe their predecessors.
"""
import argparse
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

SID_DIR = os.path.join("SID", "Shogoon")
OUT_DIR = os.path.join("out", "hardtrack_native")
PARTS = re.compile(r"part (\d+)/(\d+) \((\d+)-(\d+)s")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, default=0)
    ap.add_argument("--last", type=int, default=1 << 30)
    ap.add_argument("--keep", action="store_true",
                    help="do not clear out/hardtrack_native first")
    a = ap.parse_args(argv)

    os.makedirs(OUT_DIR, exist_ok=True)
    if not a.keep:
        n = 0
        for p in glob.glob(os.path.join(OUT_DIR, "*")):
            os.remove(p)
            n += 1
        print("cleared %d stale artifacts from %s" % (n, OUT_DIR))

    sids = sorted(glob.glob(os.path.join(SID_DIR, "*.sid")))[a.first:a.last]
    built = refused = 0
    for sid in sids:
        stem = os.path.basename(sid)[:-4]
        r = subprocess.run(["py", "-3", "bin/build_hardtrack_native_song.py", sid],
                           capture_output=True, text=True, cwd=ROOT)
        got = sorted(glob.glob(os.path.join(OUT_DIR, stem + "_part*.sf2")))
        if not got:
            refused += 1
            continue                     # a refused rip is expected, not a fault
        built += 1
        spans = PARTS.findall(r.stdout or "")
        last = spans[-1] if spans else None
        print("  %-26s %2d parts%s" % (stem, len(got),
                                       ", song %ss" % last[3] if last else ""))
        sys.stdout.flush()
    print("built %d, refused %d, of %d files" % (built, refused, len(sids)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
