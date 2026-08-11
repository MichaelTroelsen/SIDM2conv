#!/usr/bin/env python3
"""Grade the ADSR instrument key across a spread of players.

    py -3 pyscript/instrument_map_sweep.py [-n 3] [-t 20] [dir ...]

One line per file: the verdict from `sidm2.instrument_map.key_reliability` and
the numbers behind it. The point is NOT to produce a score — it is the
calibration run for the key itself. A tool that grades every file `reliable`
has not been tested, it has been believed, so this sweep exists to show the
distribution and to name the files that fail.

Defaults to `-n 3` files per `SID/<player>/` directory plus the loose files in
`SID/`, which is a spread across player families rather than a corpus.
"""
import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import siddump_frames_full          # noqa: E402
from sidm2.instrument_map import (                             # noqa: E402
    key_reliability, onsets_with_registers)


def pick(dirs, per_dir):
    out = []
    for d in dirs:
        if os.path.isfile(d):
            out.append(d)
            continue
        loose = sorted(f for f in os.listdir(d) if f.lower().endswith('.sid'))
        out += [os.path.join(d, f) for f in loose[:per_dir]]
        for sub in sorted(os.listdir(d)):
            p = os.path.join(d, sub)
            if os.path.isdir(p):
                f = sorted(x for x in os.listdir(p) if x.lower().endswith('.sid'))
                out += [os.path.join(p, x) for x in f[:per_dir]]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='*', default=['SID'])
    ap.add_argument('-n', '--per-dir', type=int, default=3)
    ap.add_argument('-t', '--seconds', type=int, default=20)
    a = ap.parse_args(argv)

    files = pick(a.paths or ['SID'], a.per_dir)
    tally = Counter()
    print("%-46s %-18s %6s %6s %6s %6s" %
          ("file", "verdict", "onsets", "distct", "modul", "unsett"))
    for f in files:
        try:
            fr = siddump_frames_full(f, ['-t%d' % a.seconds])
            on = onsets_with_registers(fr)
            v = key_reliability(on, fr)
        except Exception as e:                                  # noqa: BLE001
            print("%-46s %-18s %s" % (os.path.basename(f)[:46], "ERROR", e))
            tally['ERROR'] += 1
            continue
        tally[v.verdict] += 1
        print("%-46s %-18s %6d %6d %6d %6d" %
              (os.path.relpath(f, 'SID')[:46], v.verdict, v.onsets, v.distinct,
               v.modulated, v.unsettled))
    print()
    print("%d files: %s" % (len(files),
                            ", ".join("%s %d" % kv for kv in tally.most_common())))
    return 0


if __name__ == '__main__':
    sys.exit(main())
