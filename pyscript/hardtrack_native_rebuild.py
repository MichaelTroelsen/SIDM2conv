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
import datetime
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from sidm2.fidelity_common import MIN_INFORMATIVE_FRAMES, underpowered  # noqa: E402

# Kill-safety: a hard kill of this sweep must not leave its spawned builder
# running. Lives in pyscript/process_group.py; see that module for the
# measurement. THIS SWEEP IS SERIAL and needs it anyway -- measured
# 2026-09-03, a lone blocking subprocess.run orphans its child exactly like
# a pooled one (unguarded: child survived the parent's hard kill and wrote
# its artifact; guarded: 0 survivors). The pool multiplies the count, it is
# not the mechanism.
from process_group import bind_children_to_this_process  # noqa: E402

SID_DIR = os.path.join("SID", "Shogoon")
OUT_DIR = os.path.join("out", "hardtrack_native")
PARTS = re.compile(r"part (\d+)/(\d+) \((\d+)-(\d+)s")

# The RUN marker. Per-artifact `.prov` sidecars (a1e6f9a) say which commit built
# each file that EXISTS; they are structurally silent about the rest of the run.
# 117 of 150 HardTrack rips are refused, and a refusal writes no artifact, so it
# leaves no stamp -- "this song was never in the corpus" and "this song failed
# the last rebuild" look identical from the artifacts alone. That negative space
# is what this file records, and it is the reason a staleness check previously
# had to reconstruct coverage from part-count bursts and commit mtimes instead
# of reading it.
#
# NOT a `.sf2`, deliberately: `_provenance()` omits a timestamp so same-commit
# rebuilds stay byte-identical across every sidecar, and three no-regression
# checks rest on that. A run marker is not an artifact and SHOULD carry a time,
# so it is kept out of the `*.sf2` glob every byte-comparison sweep uses.
MARKER = os.path.join(OUT_DIR, "_rebuild.json")


def _run_stamp():
    """commit/tree/flags for the RUN, same fields as the artifact sidecars."""
    def git(*a):
        try:
            out = subprocess.run(("git", "-C", ROOT) + a, capture_output=True,
                                 text=True, timeout=10)
            return out.stdout.strip() if out.returncode == 0 else None
        except Exception:                                        # noqa: BLE001
            return None
    st = git("status", "--porcelain")
    return {
        "commit": git("rev-parse", "--short", "HEAD") or "unknown",
        "tree": "unknown" if st is None else ("dirty" if st else "clean"),
        "flags": " ".join("%s=%s" % (k, v) for k, v in sorted(os.environ.items())
                          if k.startswith(("FILT_", "INIT_", "SR_", "SM_", "BB_"))),
    }


def _write_marker(record, keep):
    """Append this run to the marker; a chunked rebuild is several runs.

    APPEND, never overwrite, because `--keep` exists so a rebuild can be split
    into chunks. A marker that recorded only the last chunk would claim the
    corpus was covered when files 0..N never ran -- the same false completeness
    the artifacts already suffer from, reintroduced one level up.
    """
    runs = []
    if keep:
        try:
            with open(MARKER, encoding="utf-8") as f:
                runs = json.load(f).get("runs", [])
        except (OSError, ValueError):
            runs = []                    # a marker we cannot read is not fatal
    runs.append(record)
    try:
        with open(MARKER, "w", encoding="utf-8") as f:
            json.dump({"runs": runs}, f, indent=1, sort_keys=True)
        return True
    except OSError:
        return False                     # provenance we cannot write is not fatal

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
    print("  kill-safety: %s" % ("builders die with this process (job object)"
                                 if bind_children_to_this_process() else
                                 "NOT ESTABLISHED -- a hard kill will leave "
                                 "builders running; kill the TREE (taskkill /T)"),
          flush=True)
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
    built_songs, refused_songs = [], []
    started = datetime.datetime.now(datetime.timezone.utc)
    voices = []            # [(stem, voice_idx, raw_pct|None, raw_n, aud_pct|None, aud_n), ...]
    for sid in sids:
        stem = os.path.basename(sid)[:-4]
        r = subprocess.run(["py", "-3", "bin/build_hardtrack_native_song.py", sid],
                           capture_output=True, text=True, cwd=ROOT)
        got = sorted(glob.glob(os.path.join(OUT_DIR, stem + "_part*.sf2")))
        if not got:
            refused += 1
            refused_songs.append(stem)
            continue                     # a refused rip is expected, not a fault
        built += 1
        built_songs.append({"song": stem, "parts": len(got)})
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

    stamp = _run_stamp()
    ok = _write_marker({
        "at": started.isoformat(timespec="seconds"),
        "finished": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "commit": stamp["commit"],
        "tree": stamp["tree"],
        "flags": stamp["flags"],
        "first": a.first,
        "last": None if a.last == 1 << 30 else a.last,
        "cleared": not a.keep,
        "considered": len(sids),
        "built": built_songs,
        "refused": refused_songs,
    }, keep=a.keep)
    print("  marker: %s (%s)" % (MARKER, "written" if ok else "NOT WRITTEN"))

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
