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
    ram_layout_base, simulate_registers,
)

# token index within a siddump voice cell: Freq Note Abs WF ADSR Pul
T_FREQ, T_WF, T_PULSE = 0, 3, 5


def register_tracks(sid, sd_args):
    """One siddump run -> {voice: {frame: (freq, wf, pulse)}}, filled forward."""
    txt = run_siddump(sid, sd_args)
    out = {0: {}, 1: {}, 2: {}}
    last = [[0, 0, 0] for _ in range(3)]
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
    return out


def validate(sid, seconds=20, subtune=0, offset=0):
    """-> {register: (ok, tot)} plus per-instrument-class frequency counts."""
    module = HardTrackModule.from_sid(sid)
    model = simulate_registers(module, subtune, seconds * 50)
    tracks = register_tracks(sid, [f'-t{seconds}'] + ([f'-a{subtune}'] if subtune else []))

    acc = {k: [0, 0] for k in ('freq', 'wf', 'pulse', 'freq_seq', 'freq_drv')}
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

    keys = ('freq', 'wf', 'pulse', 'freq_seq', 'freq_drv')
    tot = {True: {k: [0, 0] for k in keys}, False: {k: [0, 0] for k in keys}}
    refused, dead = [], []
    print(f'{"file":30} {"seed":>5} {"freq":>13} {"  seq-pitch":>13} '
          f'{"  prog-driven":>14} {"wf":>8} {"pulse":>8}')
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
              f'{pc("wf"):>8} {pc("pulse"):>8}')

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
                         ('pulse', 'pulse width $D402/3')):
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
