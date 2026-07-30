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

# player -> (builder script, corpus glob)
CORPORA = {
    "sdi":          ("bin/sdi_to_sf2.py",          "SID/Gallefoss_Glenn/*.sid"),
    "soundmonitor": ("bin/soundmonitor_to_sf2.py", "SID/Fun_Fun/*.sid"),
    "fc":           ("bin/fc_to_sf2.py",           "SID/Fun_Fun/*.sid"),
    "mon":          ("bin/mon_to_sf2.py",          "SID/Tel_Jeroen/*.sid"),
    "romuzak":      ("bin/romuzak_to_sf2.py",      "SID/Fun_Fun/*.sid"),
    "deenen":       ("bin/deenen_to_sf2.py",       "SID/deenen/*.sid"),
    "kimmel":       ("bin/kimmel_to_sf2.py",       "SID/Kimmel_Jeroen/*.sid"),
}

# "43 DROPPED" (caller-supplied branch) or "N sequence(s) exceed" (segmenting).
DROP_RE = re.compile(r"(\d+) DROPPED|(\d+) sequence\(s\) exceed")


def sweep(player, limit=None):
    script, pattern = CORPORA[player]
    files = sorted(glob.glob(os.path.join(ROOT, pattern)))[:limit]
    if not files:
        print(f"{player}: no corpus files matched {pattern} -- skipping")
        return None

    affected, built, refused, worst = [], 0, 0, 0
    for f in files:
        try:
            p = subprocess.run(
                [sys.executable, os.path.join(ROOT, script), f],
                cwd=ROOT, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            continue
        blob = (p.stdout or "") + (p.stderr or "")
        if "not the supported" in blob or "ERROR" in blob or p.returncode != 0:
            refused += 1
            if "DROPPED" not in blob and "exceed" not in blob:
                continue
        else:
            built += 1
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
