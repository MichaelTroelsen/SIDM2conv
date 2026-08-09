"""Validate the HardTrack Composer sequencer decode against siddump.

Scores a modelled note-on as correct when the player's OWN frequency-table
value for that note actually reaches $D400/$D401 within a few frames. That is a
byte-exact register comparison, not a note-name match, so it is immune to the
one-frame attack transient siddump reports as the "onset" row.

Notes played by an instrument whose bit-7 flag is set are reported SEPARATELY:
those instruments drive the frequency register from their own wave program, so
the sequencer pitch never appears there. Pooling them into one number would
describe the unimplemented synth engine as a parser error -- and would move
whenever the instrument mix changed, for reasons having nothing to do with the
decode. Quote the two columns, never their average.

Usage:
    py -3 pyscript/hardtrack_validate.py SID/Shogoon/*.sid [-t 20]
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import iter_siddump_rows, run_siddump, score_pct  # noqa: E402
from sidm2.hardtrack_parser import (  # noqa: E402
    HardTrackError, HardTrackModule, simulate,
)

_FREQ_RE = re.compile(r'^([0-9A-F.]{4})')
SETTLE_FRAMES = 8


def freq_tracks(sid, sd_args):
    """One siddump run -> {voice: {frame: raw 16-bit freq}}, filled forward."""
    txt = run_siddump(sid, sd_args)
    out = {0: {}, 1: {}, 2: {}}
    last = [0, 0, 0]
    for fr, cells in iter_siddump_rows(txt):
        if fr is None:
            continue
        for vi in range(3):
            m = _FREQ_RE.match(cells[2 + vi])
            if m and '.' not in m.group(1):
                last[vi] = int(m.group(1), 16)
            out[vi][fr] = last[vi]
    return out


def validate(sid, seconds=20, subtune=0):
    """-> (seq_ok, seq_tot, drv_ok, drv_tot) for one file."""
    module = HardTrackModule.from_sid(sid)
    frames = simulate(module, subtune, seconds * 50)
    args = [f'-t{seconds}'] + ([f'-a{subtune}'] if subtune else [])
    tracks = freq_tracks(sid, args)

    seq_ok = seq_tot = drv_ok = drv_tot = 0
    for vi in range(3):
        track = tracks[vi]
        for f, cell in ((f, r[vi]) for f, r in enumerate(frames) if r[vi]):
            note, instr = cell
            want = module.freq(note)
            hit = any(track.get(f + d) == want for d in range(SETTLE_FRAMES + 1))
            if module.instrument_drives_freq(instr):
                drv_ok += hit
                drv_tot += 1
            else:
                seq_ok += hit
                seq_tot += 1
    return seq_ok, seq_tot, drv_ok, drv_tot


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('sid', nargs='+')
    ap.add_argument('-t', '--seconds', type=int, default=20)
    ap.add_argument('-s', '--subtune', type=int, default=0)
    a = ap.parse_args(argv)

    paths = []
    for p in a.sid:
        paths.extend(sorted(glob.glob(p)) if any(c in p for c in '*?') else [p])

    tso = tst = tdo = tdt = 0
    refused = []
    print(f'{"file":28} {"sequencer-pitch":>17}  {"program-driven":>15}')
    for sid in paths:
        try:
            so, st, do, dt = validate(sid, a.seconds, a.subtune)
        except HardTrackError as e:
            refused.append((os.path.basename(sid), str(e).split(':')[0]))
            continue
        tso += so; tst += st; tdo += do; tdt += dt
        sp = score_pct(so, st)
        dp = score_pct(do, dt)
        print(f'{os.path.basename(sid):28} '
              f'{so:5}/{st:<5} {"n/a" if sp is None else f"{sp:5.1f}%":>7}  '
              f'{do:4}/{dt:<5} {"n/a" if dp is None else f"{dp:5.1f}%":>7}')

    gs, gd = score_pct(tso, tst), score_pct(tdo, tdt)
    print(f'\n{"CORPUS":28} {tso}/{tst} = '
          f'{"n/a" if gs is None else f"{gs:.2f}%"} sequencer-pitch   |   '
          f'{tdo}/{tdt} = {"n/a" if gd is None else f"{gd:.2f}%"} program-driven')
    if refused:
        print(f'\nREFUSED ({len(refused)}) -- not single-instance HardTrack modules:')
        for name, why in refused:
            print(f'  {name:28} {why}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
