#!/usr/bin/env python3
"""Rebuild a corpus and count files whose module silently loses music.

The static scan (`sf2_truncation_scan.py`) can only say "the 128-slot sequence
table is full, so a drop was POSSIBLE". Only a rebuild knows how many sequences
were actually requested, so only a rebuild can say a drop HAPPENED. This runs a
builder over a corpus and tallies the emitter's truncation warning.

    py -3 pyscript/sf2_truncation_sweep.py sdi
    py -3 pyscript/sf2_truncation_sweep.py sdi soundmonitor mon
    py -3 pyscript/sf2_truncation_sweep.py --list

Exit 1 if any file loses music.
"""
import glob
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# player -> (builder script, corpus glob). Every Stage A builder that shares
# `galway_driver11_emitter` belongs here -- that emitter is what truncates, so
# any builder reaching it can lose music.
CORPORA = {
    "sdi":          ("bin/sdi_to_sf2.py",          "SID/Gallefoss_Glenn/*.sid"),
    "soundmonitor": ("bin/soundmonitor_to_sf2.py", "SID/Fun_Fun/*.sid"),
    "fc":           ("bin/fc_to_sf2.py",           "SID/Fun_Fun/*.sid"),
    "mon":          ("bin/mon_to_sf2.py",          "SID/Tel_Jeroen/*.sid"),
    "romuzak":      ("bin/romuzak_to_sf2.py",      "SID/Fun_Fun/*.sid"),
    "deenen":       ("bin/deenen_to_sf2.py",       "SID/deenen/*.sid"),
    "kimmel":       ("bin/kimmel_to_sf2.py",       "SID/Red_kommel_jeroen/*.sid"),
    "hubbard":      ("bin/hubbard_to_sf2.py",      "SID/Hubbard_Rob/*.sid"),
    "mattgray":     ("bin/mattgray_to_sf2.py",     "SID/Gray_Matt/*.sid"),
    # The DEFAULT shipped converter (sid-to-sf2.bat -> conversion_pipeline),
    # not a bin/ side tool -- the one path an end user actually runs. Its ONLY
    # call to emit_driver11_sf2 is the Galway path (conversion_pipeline.py:688),
    # so Galway rips are what exercise the cap here. Laxity -> the Laxity driver
    # uses a different packer entirely and cannot hit this table.
    "pipeline":     ("scripts/sid_to_sf2.py",      "SID/Galway_Martin/*.sid"),
}

# "43 DROPPED" (caller-supplied branch) or "N sequence(s) exceed" (segmenting).
DROP_RE = re.compile(r"(\d+) DROPPED|(\d+) sequence\(s\) exceed")


def sweep(player, limit=None):
    script, pattern = CORPORA[player]
    files = sorted(glob.glob(os.path.join(ROOT, pattern)))[:limit]
    if not files:
        print(f"{player}: no corpus files matched {pattern} -- skipping")
        return None

    # Always pass an explicit output path in a scratch dir. Several builders --
    # scripts/sid_to_sf2.py among them -- default their output NEXT TO THE INPUT
    # when none is given, which spraying over a read-only corpus directory
    # (SID/Laxity picked up 286 stray .sf2/.txt pairs before this was fixed).
    scratch = os.path.join(ROOT, "out", "_truncation_sweep", player)
    os.makedirs(scratch, exist_ok=True)

    affected, built, refused, worst = [], 0, 0, 0
    for f in files:
        dest = os.path.join(
            scratch, os.path.splitext(os.path.basename(f))[0] + ".sf2")
        try:
            p = subprocess.run(
                [sys.executable, os.path.join(ROOT, script), f, dest],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            continue
        blob = (p.stdout or "") + (p.stderr or "")
        # Classify on the EXIT CODE plus explicit refusal phrases. A bare
        # "ERROR" substring is not a refusal: the default pipeline logs its own
        # diagnostic ERROR lines on a successful run, which misfiled all 286
        # Laxity conversions as "refused" and made the tally unreadable.
        refused_markers = ("not the supported", "not a located",
                           "no subtune-select support", "not a Sound Monitor",
                           "skipping", "Traceback")
        if p.returncode != 0 or any(k in blob for k in refused_markers):
            refused += 1
        else:
            built += 1
        # Scan for a drop either way -- a builder can emit AND lose music.
        m = DROP_RE.search(blob)
        if m:
            n = int(m.group(1) or m.group(2))
            worst = max(worst, n)
            affected.append((os.path.basename(f), n))
            print(f"  !! {os.path.basename(f)}: {n} sequence(s) dropped",
                  flush=True)

    print(f"{player}: {len(files)} corpus file(s), {built} built, "
          f"{refused} refused/errored, **{len(affected)} lose music** "
          f"(worst {worst} sequences dropped)")
    return affected


def main(argv):
    if not argv or argv[0] == "--list":
        print("players:", ", ".join(sorted(CORPORA)))
        return 0
    limit = None
    if argv[0].startswith("--limit="):
        limit = int(argv[0].split("=", 1)[1])
        argv = argv[1:]
    bad = 0
    for player in argv:
        if player not in CORPORA:
            print(f"unknown player {player!r}; try --list")
            return 2
        r = sweep(player, limit)
        bad += len(r or [])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
