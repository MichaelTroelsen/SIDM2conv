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

It also prints a per-voice fidelity MEDIAN summary, the way
`pyscript/dmc_native_sweep.py` does, by parsing the FIDELITY table the builder
(`bin/build_hardtrack_native_song.py`) already prints per file rather than
re-scoring anything. That builder only measures ONE metric -- per-frame freq
semitone agreement -- not DMC's freq/wf/pulse triple, so this prints one
metric's raw+audible medians, not three, and says so rather than inventing
waveform/pulse numbers HardTrack's own fidelity report does not produce. The
$D418 passband is scored by neither this nor the builder; that is a separate
check (`pyscript/passband_check.py`), not run here.

  py -3 pyscript/hardtrack_native_rebuild.py [--first N] [--last N] [--keep]

Chunk it with --first/--last (a single parent died at ~275 builds elsewhere);
--keep skips the clear so chunks after the first do not wipe their predecessors.
The median summary is over whatever this invocation built -- a chunked run
only reports its own chunk's voices, same as the build/refused counts already
did.
"""
import argparse
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from sidm2.fidelity_common import MIN_INFORMATIVE_FRAMES, underpowered  # noqa: E402

SID_DIR = os.path.join("SID", "Shogoon")
OUT_DIR = os.path.join("out", "hardtrack_native")
PARTS = re.compile(r"part (\d+)/(\d+) \((\d+)-(\d+)s")

# Matches the builder's own FIDELITY table row, e.g.:
#   "      0   |  94.9% ( 1234) |  96.0% ( 1000)     |    5 of   10 (2 ...)"
# Same shape as hardtrack_native_sweep.py's ROW -- one format, parsed twice
# rather than diverging.
FID_ROW = re.compile(r"^\s+([012])\s+\|\s+(\S+)%?\s+\(\s*(\d+)\)\s+\|\s+"
                     r"(\S+)%?\s+\(\s*(\d+)\)\s+\|\s+(\d+) of\s+(\d+)")


def _median(vals):
    vals = sorted(vals)
    if not vals:
        return None
    mid = len(vals) // 2
    return vals[mid] if len(vals) % 2 else (vals[mid - 1] + vals[mid]) / 2


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
    voices = []            # [(stem, voice_idx, raw_pct|None, raw_n, aud_pct|None, aud_n), ...]
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
        for line in (r.stdout or "").splitlines():
            m = FID_ROW.match(line)
            if not m:
                continue
            vi, raw, rn, aud, an = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
            voices.append((
                stem, int(vi),
                None if raw.startswith("n") else float(raw.rstrip("%")), int(rn),
                None if aud.startswith("n") else float(aud.rstrip("%")), int(an)))
        print("  %-26s %2d parts%s" % (stem, len(got),
                                       ", song %ss" % last[3] if last else ""))
        sys.stdout.flush()
    print("built %d, refused %d, of %d files" % (built, refused, len(sids)))

    # Per-voice fidelity MEDIAN, matching dmc_native_sweep's summary block so
    # the two corpora are comparable at a glance. Only ONE metric here (freq
    # semitone) where DMC has three (freq/wf/pulse) -- the builder's own
    # FIDELITY table does not measure waveform or pulse per voice, so this
    # prints one line, not three, rather than inventing the other two.
    raws = [r for (_, _, r, rn, _, _) in voices if r is not None]
    print()
    if not raws:
        print("no per-voice fidelity parsed (0 files built, or the builder's "
              "FIDELITY table format changed)")
    else:
        line = (f"  freq (raw):     median {_median(raws):6.1f}  over {len(raws)} "
                f"voices, {sum(1 for x in raws if x >= 99.95)} at 100, "
                f"{sum(1 for x in raws if x < 90)} below 90")
        auds = [au for (_, _, _, _, au, an) in voices if au is not None]
        if auds:
            line += (f"   | audible median {_median(auds):6.1f} over {len(auds)} "
                     f"voices, {sum(1 for x in auds if x < 90)} below 90")
        print(line)
        thin = sorted({stem for (stem, _, r, rn, _, _) in voices
                       if r is not None and underpowered(rn)})
        if thin:
            print(f"!! {len(thin)} file(s) with a voice scored over a thin window "
                  f"(< {MIN_INFORMATIVE_FRAMES} frames): {', '.join(thin[:8])}"
                  f"{' ...' if len(thin) > 8 else ''}")
        print("  (freq only -- HardTrack's builder does not report per-voice "
              "waveform/pulse the way DMC's does.")
        print("   NOT a $D418 figure -- passband is not scored by this or by "
              "the builder; see pyscript/passband_check.py.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
