"""Validate the HardTrack synth engine per FRAME, not per note-onset.

`hardtrack_validate.py` asks "did the sequencer's note reach $D400/$D401 within
a settle window". That question has two problems it cannot fix from inside: it
needs a window (which has no plateau, so every figure has to be quoted with
one), and it is unanswerable for an instrument whose wave program drives the
frequency itself -- those notes score 2.6% because the thing being predicted is
not the thing being written.

`sidm2.hardtrack_synth.simulate_registers()` predicts the register file
directly, so this scores the obvious thing instead: on what fraction of frames
is the predicted value byte-exact. No window, no settle heuristic, and the
program-driven instruments are scored on what they actually do.

Frames are excluded from the denominator only where scoring them would be
meaningless, and each exclusion is counted and printed:
  * frame 0 -- siddump force-displays every register on its first row whether
    the playroutine wrote it or not, so it is not evidence either way;
  * frames before a voice's first note-on -- the model has nothing to predict
    yet and the real player is emitting whatever init left behind.

Usage:
    py -3 pyscript/hardtrack_synth_validate.py "SID/Shogoon/*.sid" [-t 20]
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import (  # noqa: E402
    exercised, iter_siddump_rows, run_siddump, score_pct,
)
from sidm2.hardtrack_parser import HardTrackError, HardTrackModule  # noqa: E402
from sidm2.hardtrack_synth import (  # noqa: E402
    ram_layout_base, simulate_all,
)

# token index within a siddump voice cell: Freq Note Abs WF ADSR Pul
T_FREQ, T_WF, T_PULSE = 0, 3, 5
# siddump's trailing cell: FCut RC Typ V. FCut is (D415 & 7) | (D416 << 3) and
# this player never writes D415, so `>> 3` recovers D416 exactly. Typ is only
# (D418 >> 4) & 7, so bit 7 -- voice 3 off -- is invisible here and D418 is
# compared on bits 0-6 alone.
FILTER_NAMES = ['Off', 'Low', 'Bnd', 'L+B', 'Hi ', 'L+H', 'B+H', 'LBH']


def register_tracks(sid, sd_args):
    """One siddump run -> ({voice: {frame: (freq, wf, pulse)}}, {frame: filter})."""
    txt = run_siddump(sid, sd_args)
    out = {0: {}, 1: {}, 2: {}}
    filt = {}
    last = [[0, 0, 0] for _ in range(3)]
    flast = [0, 0, 0, 0]        # cutoff, res/route, mode, volume
    for fr, cells in iter_siddump_rows(txt):
        if fr is None:
            continue
        for vi in range(3):
            tok = cells[2 + vi].split()
            if len(tok) > T_PULSE:
                for slot, ti in ((0, T_FREQ), (1, T_WF), (2, T_PULSE)):
                    if '.' not in tok[ti]:
                        last[vi][slot] = int(tok[ti], 16)
            out[vi][fr] = tuple(last[vi])
        tok = cells[5].split()
        if len(tok) > 3:
            if '.' not in tok[0]:
                flast[0] = int(tok[0], 16) >> 3
            if '.' not in tok[1]:
                flast[1] = int(tok[1], 16)
            if '.' not in tok[2]:
                flast[2] = FILTER_NAMES.index(tok[2].ljust(3)) << 4
            if '.' not in tok[3]:
                flast[3] = int(tok[3], 16)
        filt[fr] = (flast[0], flast[1], flast[2] | flast[3])
    return out, filt


def validate(sid, seconds=20, subtune=0, offset=0):
    """-> {register: (ok, tot)} plus per-instrument-class frequency counts."""
    module = HardTrackModule.from_sid(sid)
    model, fmodel = simulate_all(module, subtune, seconds * 50)
    tracks, ftrack = register_tracks(
        sid, [f'-t{seconds}'] + ([f'-a{subtune}'] if subtune else []))

    acc = {k: [0, 0] for k in ('freq', 'wf', 'pulse', 'freq_seq', 'freq_drv',
                               'cutoff', 'res_route', 'mode_vol')}
    skipped = 0
    pred_freq, real_freq = [], []
    for vi in range(3):
        track = tracks[vi]
        for f, row in enumerate(model):
            vf = row[vi]
            real = track.get(f + offset)
            # frame 0 is siddump's forced full display, not a written value
            if real is None or f + offset < 1 or not vf.started:
                skipped += 1
                continue
            pred_freq.append(vf.freq)
            real_freq.append(real[0])
            for key, got, want in (('freq', vf.freq, real[0]),
                                   ('wf', vf.waveform, real[1]),
                                   ('pulse', vf.pulse, real[2])):
                acc[key][0] += got == want
                acc[key][1] += 1
            k = 'freq_drv' if vf.drives_freq else 'freq_seq'
            acc[k][0] += vf.freq == real[0]
            acc[k][1] += 1
    # A file whose predicted and actual series are both one constant carries no
    # information, however high the percentage looks.
    # The filter is global, not per-voice, so it is scored over frames rather
    # than voice-frames. Each register is guarded separately: $D418 is one
    # constant on most of this corpus and would otherwise report a vacuous
    # 100% on files that never move it.
    for si, key in enumerate(('cutoff', 'res_route', 'mode_vol')):
        mask = 0x7F if key == 'mode_vol' else 0xFF
        pv = [getattr(f, key) & mask for i, f in enumerate(fmodel)
              if i >= 1 and i in ftrack]
        rv = [ftrack[i][si] & mask for i in range(len(fmodel))
              if i >= 1 and i in ftrack]
        if exercised(pv, rv):
            acc[key][0] = sum(1 for a, b in zip(pv, rv) if a == b)
            acc[key][1] = len(pv)

    live = exercised(pred_freq, real_freq)
    seeded = ram_layout_base(module) is not None
    return {k: tuple(v) for k, v in acc.items()}, skipped, live, seeded


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('sid', nargs='+')
    ap.add_argument('-t', '--seconds', type=int, default=20)
    ap.add_argument('-s', '--subtune', type=int, default=0)
    ap.add_argument('-o', '--offset', type=int, default=0,
                    help='shift the siddump frame index; report it, never tune it')
    a = ap.parse_args(argv)

    paths = []
    for p in a.sid:
        paths.extend(sorted(glob.glob(p)) if any(c in p for c in '*?') else [p])

    keys = ('freq', 'wf', 'pulse', 'freq_seq', 'freq_drv',
            'cutoff', 'res_route', 'mode_vol')
    tot = {True: {k: [0, 0] for k in keys}, False: {k: [0, 0] for k in keys}}
    refused, dead = [], []
    print(f'{"file":30} {"seed":>5} {"freq":>13} {"  seq-pitch":>13} '
          f'{"  prog-driven":>14} {"wf":>8} {"pulse":>8} {"cutoff":>8} '
          f'{"$D417":>7} {"$D418":>7}')
    for sid in paths:
        try:
            acc, _, live, seeded = validate(sid, a.seconds, a.subtune, a.offset)
        except HardTrackError as e:
            refused.append((os.path.basename(sid), str(e).split(' -- ')[0].split(':')[0]))
            continue
        if not live:
            dead.append(os.path.basename(sid))
            continue
        for k, v in acc.items():
            tot[seeded][k][0] += v[0]
            tot[seeded][k][1] += v[1]

        def pc(k):
            p = score_pct(*acc[k])
            return 'n/a' if p is None else f'{p:.1f}%'
        print(f'{os.path.basename(sid):30} {"yes" if seeded else "no":>5} '
              f'{acc["freq"][0]:6}/{acc["freq"][1]:<6} '
              f'{pc("freq_seq"):>12} {pc("freq_drv"):>13} '
              f'{pc("wf"):>8} {pc("pulse"):>8} {pc("cutoff"):>8} '
              f'{pc("res_route"):>7} {pc("mode_vol"):>7}')

    # Seeded and unseeded files answer different questions -- the unseeded ones
    # carry a startup transient the seeded ones do not -- so they are never
    # pooled into one headline number.
    for seeded in (True, False):
        if not tot[seeded]['freq'][1]:
            continue
        print(f'\n-- power-on RAM {"seeded from the module image" if seeded else
              "UNSEEDED (second player build): expect a startup transient"} --')
        for k, label in (('freq', 'frequency  (all frames)'),
                         ('freq_seq', '  sequencer-pitch instruments'),
                         ('freq_drv', '  program-driven instruments'),
                         ('wf', 'waveform $D404'),
                         ('pulse', 'pulse width $D402/3'),
                         ('cutoff', 'filter cutoff $D416'),
                         ('res_route', 'filter res/routing $D417'),
                         ('mode_vol', 'filter mode+volume $D418 (bits 0-6)')):
            p = score_pct(*tot[seeded][k])
            print(f'{label:34} {tot[seeded][k][0]:7}/{tot[seeded][k][1]:<7} '
                  f'{"n/a" if p is None else f"{p:6.2f}%"}')
    if dead:
        print(f'\nNO SIGNAL ({len(dead)}) -- predicted and actual are one constant:')
        for n in dead:
            print(f'  {n}')
    if refused:
        print(f'\nREFUSED ({len(refused)}):')
        for name, why in refused:
            print(f'  {name:30} {why}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
