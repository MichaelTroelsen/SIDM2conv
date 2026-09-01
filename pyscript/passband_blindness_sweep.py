"""Price the $D418-only filter event: how often is `detect_filter_drives` blind?

THE QUESTION, and why a number is worth this much machinery. `detect_filter_drives`
(bin/build_mon_native_song.py) keys on cutoff jumps: `abs(ftr[f][0] - ftr[f-1][0])
>= FILT_FAST`. A filter event signalled by $D418's passband bits ALONE is
invisible to it by construction -- `filter_trace`'s own docstring says so. That
blindness is structurally real. What nobody has measured is how OFTEN it happens,
and a shared detector five builders import must not be changed on a guess.

TWO PRIOR READINGS ARE BOTH DEAD, which is the whole reason this exists:
  * "no file exercises the blindness" -- asserted from a 32-file seeded sample
    (8 per corpus, -t20), REFUTED by one hit;
  * that one hit -- SID/Fun_Fun/Byte_Bite.sid -- was itself REFUTED (66e3877,
    pyscript/test_build_mon_native_song.py). It pulses low-pass every 6 frames
    but ALSO sweeps cutoff normally, so the detector is not blind to its filter
    at all. Its cutoff moves in steps of exactly $40, i.e. AT the threshold.

So a count of unverified hits is precisely the output that already misled one
cycle. Every hit this script reports therefore carries the evidence needed to
kill it the same way: `distinct_cutoff` and `max_abs_dcutoff` over the whole
trace, so "does this file sweep cutoff independently?" is answerable FROM THE
OUTPUT rather than by re-running anything.

WHAT IS DELIBERATELY NOT IMPORTED. `bin/build_mon_native_song.py` defines
FILT_FAST, and importing it would be the obvious way to stay in step with it --
but it pulls in 11 modules at import (the graph names build_romuzak_driver_full,
build_romuzak_native_song, hardtrack_to_sf2, mon_to_sf2, the Galway emitters),
and the ROMUZAK path writes drivers_src/romuzak/layout.inc and
out/romuzak_driver.prg. Those are PATTERNS.md F12 shared-state paths: a
read-only measurement must not touch them. So FILT_FAST is a literal here, and
`test_passband_blindness_sweep.py` reads the constant out of that file AS TEXT
and fails if the two ever disagree. Drift breaks a test instead of shipping.

FRAME 0 IS NOT EVIDENCE and is skipped. siddump force-displays every register on
row 0 whatever the playroutine did, so frame 0 carries the pre-init bus state
(fidelity_common.siddump_frames_full says so; Hawkeye reads $D418 = $FF there
before its own init writes $1F). Counting the 0 -> real transition would score a
blind event in every file on disk.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# bin/build_mon_native_song.py:838 -- "11-bit cutoff jump that marks an attack".
# Pinned against that file by test_filt_fast_still_agrees_with_the_builder.
FILT_FAST = 0x40

# The four corpora the claim is about, with the counts the task states.
CORPORA = {
    "dmc": "SID/JohannesBjerregaard",
    "fc": "SID/Fun_Fun",
    "mon": "SID/Tel_Jeroen",
    "sdi": "SID/Gallefoss_Glenn",
}


def blind_events(cutoff: list[int], passband: list[int],
                 filt_fast: int = FILT_FAST, window: int = 8,
                 skip_first: int = 1) -> list[int]:
    """Frames where the passband changes and NO fast cutoff move is nearby.

    THE WINDOWED FORM, not the adjacent-delta one. The naive version asks only
    whether frame f itself carries a cutoff jump; a filter attack that lands one
    frame either side of the passband write then reads as blind when the
    detector would in fact have caught it. `window` frames on BOTH sides is the
    criterion the prior cycle settled on, and it is the one reused here.

    `skip_first` drops siddump's frame-0 pre-init artefact (see module
    docstring). The first frame that can be reported is therefore
    `skip_first + 1`, because a change needs a predecessor.
    """
    n = min(len(cutoff), len(passband))
    out = []
    for f in range(max(1, skip_first + 1), n):
        if passband[f] == passband[f - 1]:
            continue
        lo, hi = max(1, f - window), min(n - 1, f + window)
        if any(abs(cutoff[g] - cutoff[g - 1]) >= filt_fast
               for g in range(lo, hi + 1)):
            continue
        out.append(f)
    return out


def series(sid: str, secs: int, sub: int = 0) -> tuple[list[int], list[int]]:
    """(cutoff11, passband) per frame from ONE siddump call.

    `filter_trace` and `passband_trace` in the builder each run their own
    siddump; over 728 files that is 728 avoidable emulations. Both read the same
    `FCut RC Typ V` cell, so `siddump_frames_full` supplies both -- and its
    'cutoff' is byte-for-byte the value `siddump_filter_trace` calls cutoff11
    (same lenient match on the same column).
    """
    import logging
    from sidm2.fidelity_common import siddump_frames_full
    prev = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        frames = siddump_frames_full(sid, ['-a%d' % sub, '-t%d' % secs])
    finally:
        logging.disable(prev)
    cutoff = [(g['cutoff'] if g['cutoff'] is not None else 0) for _, g in frames]
    passband = [0 if g['volmode'] is None else (g['volmode'] >> 4) & 0x07
                for _, g in frames]
    return cutoff, passband


def sweep_file(args: tuple[str, str, int]) -> dict:
    """One file. Never raises: a file that cannot be dumped is reported as such.

    A sweep that dies on file 300 of 728 answers nothing, and an exception
    swallowed into a zero would answer it WRONGLY -- 'no blind events' and 'no
    trace' must not look the same. Hence the explicit `error` field.
    """
    corpus, path, secs = args
    rec = {"corpus": corpus, "file": os.path.relpath(path, ROOT).replace("\\", "/"),
           "frames": 0, "n_blind": 0, "blind_frames": [],
           "distinct_cutoff": 0, "distinct_passband": [], "max_abs_dcutoff": 0,
           "error": None}
    try:
        cutoff, passband = series(path, secs)
    except Exception as exc:                                     # noqa: BLE001
        rec["error"] = "%s: %s" % (type(exc).__name__, exc)
        return rec
    if not cutoff:
        rec["error"] = "no frames"
        return rec
    ev = blind_events(cutoff, passband)
    rec.update(
        frames=len(cutoff),
        n_blind=len(ev),
        blind_frames=ev[:20],
        distinct_cutoff=len(set(cutoff)),
        distinct_passband=sorted(set(passband)),
        # THE HAND-CHECK, precomputed: Byte_Bite was killed by exactly this --
        # a file whose cutoff moves by >= FILT_FAST anywhere is a file the
        # detector is not blind to, whatever its passband does.
        max_abs_dcutoff=max((abs(cutoff[i] - cutoff[i - 1])
                             for i in range(1, len(cutoff))), default=0),
    )
    return rec


def collect(dirs: dict[str, str]) -> list[tuple[str, str]]:
    found = []
    for corpus, rel in dirs.items():
        d = os.path.join(ROOT, rel)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if name.lower().endswith(".sid"):
                found.append((corpus, os.path.join(d, name)))
    return found


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--secs", type=int, default=60)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--json", default=None)
    ap.add_argument("--corpus", action="append", default=None,
                    help="restrict to one of %s" % ",".join(CORPORA))
    ap.add_argument("--limit", type=int, default=0, help="first N files (a smoke run)")
    a = ap.parse_args(argv)

    dirs = ({k: v for k, v in CORPORA.items() if k in a.corpus}
            if a.corpus else dict(CORPORA))
    files = collect(dirs)
    if a.limit:
        files = files[:a.limit]
    print("%d files over %d corpora at -t%d, jobs=%d"
          % (len(files), len(dirs), a.secs, a.jobs), flush=True)

    work = [(c, p, a.secs) for c, p in files]
    rows = []
    # Incremental sidecar: the PARENT (never the workers -- concurrent appends
    # from N processes would tear each other's lines) writes one JSON row per
    # line as each ex.map() result arrives, and flushes + fsyncs it immediately.
    # That is what lets a killed or hung sweep be told apart from a running one
    # by reading this file mid-run, instead of only from the final --json,
    # which (see below) is still written once at the end.
    jsonl_path = (a.json + ".jsonl") if a.json else None
    jsonl_fh = open(jsonl_path, "w", encoding="utf-8") if jsonl_path else None
    try:
        with ProcessPoolExecutor(max_workers=max(1, a.jobs)) as ex:
            for i, rec in enumerate(ex.map(sweep_file, work), 1):
                rows.append(rec)
                if jsonl_fh is not None:
                    jsonl_fh.write(json.dumps(rec) + "\n")
                    jsonl_fh.flush()
                    os.fsync(jsonl_fh.fileno())
                if rec["error"] or rec["n_blind"]:
                    print("  [%d/%d] %-8s %-52s blind=%-5d dcut_max=%-5d dist_cut=%-4d %s"
                          % (i, len(work), rec["corpus"], os.path.basename(rec["file"]),
                             rec["n_blind"], rec["max_abs_dcutoff"],
                             rec["distinct_cutoff"], rec["error"] or ""), flush=True)
                elif i % 25 == 0:
                    print("  [%d/%d] ..." % (i, len(work)), flush=True)
    finally:
        if jsonl_fh is not None:
            jsonl_fh.close()

    hits = [r for r in rows if r["n_blind"] and not r["error"]]
    errs = [r for r in rows if r["error"]]
    # A HIT WHOSE CUTOFF MOVES BY >= FILT_FAST IS NOT BLINDNESS. Reported apart
    # rather than pooled: pooling them is how the last count came out wrong.
    unswept = [r for r in hits if r["max_abs_dcutoff"] < FILT_FAST]
    print("\n%d files, %d errors" % (len(rows), len(errs)))
    print("candidate hits (passband change, no fast cutoff in +/-8): %d" % len(hits))
    print("of those, cutoff NEVER moves >= FILT_FAST anywhere: %d" % len(unswept))
    for r in sorted(unswept, key=lambda r: -r["n_blind"]):
        print("   %-8s %-52s blind=%-5d frames=%-5d dist_cut=%-4d pb=%s"
              % (r["corpus"], r["file"], r["n_blind"], r["frames"],
                 r["distinct_cutoff"], r["distinct_passband"]))
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump({"filt_fast": FILT_FAST, "secs": a.secs,
                       "corpora": dirs, "rows": rows}, fh, indent=1)
        print("wrote %s" % a.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
