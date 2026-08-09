"""Attribute HardTrack Stage A losses to a cause, exactly.

Answers one question: of the notes the PARSER resolves, which ones does Stage A
lose, and what do they have in common? That framing matters -- a note the parser
never resolved cannot be held against the transpile, and pooling the two makes
the number move for reasons unrelated to Stage A.

Every note is tagged from fields carried out of the sequencer walk itself
(`Onset.raw`, `Onset.pattern`, `Onset.pat_index`), never re-derived afterwards.
An earlier version of this analysis mapped onsets onto pattern events with a
cursor heuristic; it mis-aligned on one file and reversed a real result, which
is why the parser now carries these fields.

The tags:

  $6F legato        the instrument byte is $6F -- keep the instrument and do NOT
                    restart its programs. Driver 11 always restarts, so Stage A
                    gives such notes a duplicate instrument starting at the wave
                    program's settled step.
  next is $62       the following event freezes the wave stepper ($62 sets
                    $16D4). Driver 11 has no equivalent, so the program keeps
                    running and can leave the base pitch behind.
  plain             everything else.

Usage:
    py -3 pyscript/hardtrack_attribute.py "SID/Shogoon/*.sid" [-t 20] [--lag 1]
    py -3 pyscript/hardtrack_attribute.py "SID/Shogoon/*.sid" --detail
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import score_pct  # noqa: E402
from sidm2.hardtrack_parser import (  # noqa: E402
    HardTrackError, HardTrackModule, INSTR_LEGATO, next_pattern_event, simulate,
)
from pyscript.hardtrack_validate import SETTLE_FRAMES, freq_tracks  # noqa: E402
from pyscript.hardtrack_stagea_validate import build_and_wrap  # noqa: E402


def tag_of(module, onset):
    if onset.raw == INSTR_LEGATO:
        return '$6F legato'
    if onset.pattern is not None and onset.pat_index is not None:
        if next_pattern_event(module, onset.pattern, onset.pat_index) == 'cmd62':
            return 'next is $62'
    return 'plain'


def attribute(sid, seconds=20, subtune=0, lag=1):
    """-> (Counter{tag: [lost, total]}, [lost onset detail])."""
    module = HardTrackModule.from_sid(sid)
    frames = simulate(module, subtune, seconds * 50)
    with tempfile.TemporaryDirectory() as td:
        a_tracks = freq_tracks(build_and_wrap(sid, subtune, td), [f'-t{seconds}'])
    o_tracks = freq_tracks(sid, [f'-t{seconds}']
                           + ([f'-a{subtune}'] if subtune else []))
    last = max(max(t) for t in o_tracks.values() if t)

    tab = collections.defaultdict(lambda: [0, 0])
    detail = []
    for vi in range(3):
        at, ot = a_tracks[vi], o_tracks[vi]
        for f, onset in ((f, r[vi]) for f, r in enumerate(frames) if r[vi]):
            if module.instrument_drives_freq(onset.instrument):
                continue
            if f + max(lag, 1) + SETTLE_FRAMES > last:
                continue
            want = module.freq(onset.note)
            if not any(ot.get(f + d) == want for d in range(SETTLE_FRAMES + 1)):
                continue                      # the parser did not resolve it
            kept = any(at.get(f + lag + d) == want
                       for d in range(SETTLE_FRAMES + 1))
            tag = tag_of(module, onset)
            tab[tag][1] += 1
            if not kept:
                tab[tag][0] += 1
                detail.append((os.path.basename(sid)[:-4], vi, f, onset.note,
                               onset.instrument, tag))
    return tab, detail


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('sid', nargs='+')
    ap.add_argument('-t', '--seconds', type=int, default=20)
    ap.add_argument('-s', '--subtune', type=int, default=0)
    ap.add_argument('--lag', type=int, default=1,
                    help="Driver 11's known one-frame startup phase (default 1)")
    ap.add_argument('--detail', action='store_true', help='list every lost note')
    a = ap.parse_args(argv)

    paths = []
    for p in a.sid:
        paths.extend(sorted(glob.glob(p)) if any(c in p for c in '*?') else [p])

    total = collections.defaultdict(lambda: [0, 0])
    detail = []
    for sid in paths:
        try:
            tab, det = attribute(sid, a.seconds, a.subtune, a.lag)
        except (HardTrackError, RuntimeError):
            continue
        for k, (lost, n) in tab.items():
            total[k][0] += lost
            total[k][1] += n
        detail.extend(det)

    lost = sum(v[0] for v in total.values())
    n = sum(v[1] for v in total.values())
    if not n:
        print('no scoreable notes')
        return 1
    print(f'Of the {n} notes the PARSER resolves, Stage A loses {lost} '
          f'-- retention {100.0 * (n - lost) / n:.2f}%  (--lag {a.lag})\n')
    print(f'{"tag":16} {"lost":>6} {"of":>7}   rate')
    for k, (l, t) in sorted(total.items(), key=lambda kv: -kv[1][0]):
        print(f'{k:16} {l:6} {t:7}   {score_pct(l, t):6.2f}%')
    if lost:
        share = {k: v[0] for k, v in total.items() if v[0]}
        top = max(share, key=share.get)
        print(f'\nlargest single cause: {top} '
              f'({share[top]}/{lost} = {100.0 * share[top] / lost:.1f}% of losses)')
    if a.detail:
        print('\nlost notes:')
        for d in detail:
            print(f'   {d[0]:24} v{d[1]} frame {d[2]:5} note {d[3]:3} '
                  f'instr {d[4]:3}  {d[5]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
