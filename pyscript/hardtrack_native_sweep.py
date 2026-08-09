#!/usr/bin/env python3
"""HardTrack Composer Stage B corpus sweep -- build every decodable file in
SID/Shogoon/ natively and aggregate the per-voice fidelity the builder reports.

Self-contained the way pyscript/soundmonitor_sweep.py and blackbird_sweep.py
are: it invokes bin/build_hardtrack_native_song.py itself and parses the
fidelity block out of THAT SAME subprocess call's stdout, so one command
reproduces the corpus numbers from nothing but a fresh checkout (SID/Shogoon/ is
tracked). No log file has to have been produced by some other, untracked script
first -- that is exactly the trap R21 found in the Sound Monitor sweep.

  py -3 pyscript/hardtrack_native_sweep.py               # 60s window, whole corpus
  py -3 pyscript/hardtrack_native_sweep.py -t auto       # full song length
  py -3 pyscript/hardtrack_native_sweep.py -f Zakplus Sling
  py -3 pyscript/hardtrack_native_sweep.py --json out/ht_native_sweep.json

THREE numbers per voice, and they are not interchangeable:

  raw       every frame where either side has a frequency, gate-off included.
  audible   only frames where the ORIGINAL's gate was on.
  net       audible misses MINUS the driver's own note-on frames, which cannot
            match by construction (the driver holds the note's base pitch on its
            trigger frame; HardTrack still has the previous note's frequency
            there) and which the builder separately shows to be silent -- the
            SID TEST bit is set on essentially all of them.

`net` is the one that says whether the CONVERSION lost anything; `audible` is
the one to quote if only one number is wanted, because it makes no exclusion at
all. Reporting only `net` would be laundering, so the sweep prints all three
with their sample sizes.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sidm2.hardtrack_parser import HardTrackModule, HardTrackError  # noqa: E402
from sidm2.fidelity_common import score_pct  # noqa: E402

BUILDER = os.path.join(ROOT, "bin", "build_hardtrack_native_song.py")
ROW = re.compile(r"^\s+([012])\s+\|\s+(\S+)%?\s+\(\s*(\d+)\)\s+\|\s+"
                 r"(\S+)%?\s+\(\s*(\d+)\)\s+\|\s+(\d+) of\s+(\d+)"
                 r"(?:\s+\((\d+) under)?")
PARTS = re.compile(r"packed into (\d+) adaptive part")


def corpus(names=None):
    """Every HardTrack file in SID/Shogoon/ the parser will decode.

    A file it REFUSES (a wrapped or multi-instance HardTrack rip) is reported as
    such rather than skipped silently -- 5 of the 38 are refusals by design and a
    sweep that quietly dropped them would understate its own denominator.

    `SID/Shogoon/` is MIXED-PLAYER: 112 of its 150 files are GoatTracker, DMC and
    others, and those raise the same exception type ("no HardTrack Composer init
    signature found"). Counting them as refusals reported "117 refused" against a
    corpus of 38 -- a number that looks like a catastrophe and is really just the
    wrong denominator. A file with no init signature is NOT a HardTrack file, and
    is not counted at all.
    """
    out, refused = [], []
    for p in sorted(glob.glob(os.path.join(ROOT, "SID", "Shogoon", "*.sid"))):
        name = os.path.splitext(os.path.basename(p))[0]
        if names and name not in names:
            continue
        try:
            HardTrackModule.from_sid(p)
        except HardTrackError as e:
            if 'init signature' not in str(e):    # a HardTrack file we refuse
                refused.append((name, str(e)))
            continue
        except Exception:
            continue                     # not a HardTrack file at all
        out.append((name, p))
    return out, refused


def build_one(path, window):
    r = subprocess.run([sys.executable, BUILDER, path, str(window)],
                       capture_output=True, text=True, cwd=ROOT)
    txt = (r.stdout or "") + (r.stderr or "")
    rec = {'ok': False, 'parts': None, 'voices': [], 'log': txt.strip()[-400:]}
    mp = PARTS.search(txt)
    if mp:
        rec['parts'] = int(mp.group(1))
    for line in txt.splitlines():
        m = ROW.match(line)
        if not m:
            continue
        v, raw, rn, aud, an, tm, ms, ts = m.groups()
        rec['voices'].append({
            'voice': int(v),
            'raw': None if raw.startswith('n') else float(raw.rstrip('%')),
            'raw_n': int(rn),
            'audible': None if aud.startswith('n') else float(aud.rstrip('%')),
            'audible_n': int(an),
            'trig_miss': int(tm), 'miss': int(ms),
            'trig_silent': int(ts) if ts else 0})
    rec['ok'] = len(rec['voices']) == 3
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('-t', '--window', default='60',
                    help="seconds per song, or 'auto' for the full song")
    ap.add_argument('-f', '--files', nargs='*', help='song names to limit to')
    ap.add_argument('--json', help='write the full record here')
    a = ap.parse_args(argv)

    songs, refused = corpus(a.files)
    print(f"HardTrack Stage B sweep: {len(songs)} decodable, "
          f"{len(refused)} refused, window={a.window}s")
    results = {}
    for i, (name, path) in enumerate(songs, 1):
        rec = build_one(path, a.window)
        results[name] = rec
        if not rec['ok']:
            print(f"  [{i:2d}/{len(songs)}] {name:<28} BUILD FAILED")
            continue
        cells = []
        for vd in rec['voices']:
            net_miss = vd['miss'] - vd['trig_miss']
            cells.append(f"{vd['audible'] if vd['audible'] is not None else -1:5.1f}"
                         f"/{net_miss:<4d}")
        print(f"  [{i:2d}/{len(songs)}] {name:<28} parts={rec['parts'] or '?':>2} "
              f"aud/netmiss  " + "  ".join(cells))

    # Corpus aggregate. Weighted by FRAMES, not by file: a 20-frame voice and a
    # 5,000-frame voice are not the same evidence, and averaging percentages
    # would treat them as such.
    tot = {'raw_ok': 0, 'raw_n': 0, 'aud_ok': 0, 'aud_n': 0,
           'trig': 0, 'miss': 0, 'silent': 0}
    for rec in results.values():
        for vd in rec['voices']:
            if vd['raw'] is not None:
                tot['raw_ok'] += round(vd['raw'] / 100.0 * vd['raw_n'])
                tot['raw_n'] += vd['raw_n']
            if vd['audible'] is not None:
                tot['aud_ok'] += round(vd['audible'] / 100.0 * vd['audible_n'])
                tot['aud_n'] += vd['audible_n']
            tot['trig'] += vd['trig_miss']
            tot['miss'] += vd['miss']
            tot['silent'] += vd['trig_silent']
    raw = score_pct(tot['raw_ok'], tot['raw_n'])
    aud = score_pct(tot['aud_ok'], tot['aud_n'])
    net = tot['miss'] - tot['trig']
    print()
    print(f"  CORPUS raw     {raw if raw is not None else float('nan'):.2f}% "
          f"(n={tot['raw_n']})")
    print(f"  CORPUS audible {aud if aud is not None else float('nan'):.2f}% "
          f"(n={tot['aud_n']})")
    print(f"  misses {tot['miss']}, of which {tot['trig']} are the driver's "
          f"note-on frame ({tot['silent']} of those under the SID TEST bit, "
          f"i.e. silent)")
    print(f"  NET misses (everything else): {net} of {tot['raw_n']} frames")
    if a.json:
        with open(a.json, 'w') as f:
            json.dump({'window': a.window, 'results': results,
                       'refused': refused, 'totals': tot}, f, indent=1)
        print(f"  wrote {a.json}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
