"""Validate a HardTrack Stage A build: does the emitted SF2 play the notes?

Pipeline: .sid -> bin/hardtrack_to_sf2.py -> .sf2 -> scripts/sf2_to_sid.py ->
siddump. A modelled note-on scores when the ORIGINAL player's frequency-table
value for that note reaches $D400/$D401 in the Driver 11 render.

That is deliberately the same metric `pyscript/hardtrack_validate.py` applies to
the original SID, so the two numbers are directly comparable: the parser's own
score is the ceiling Stage A can reach, and the gap between them is what the
transpile lost. Reporting Stage A alone would hide whether a low score came from
the conversion or from a note the parser never decoded.

Notes played by an instrument whose wave program drives the frequency register
(field 5 bit 7) are excluded, exactly as in the parser validator -- their pitch
is not the sequencer's to place.

Usage:
    py -3 pyscript/hardtrack_stagea_validate.py SID/Shogoon/Love_tune_2.sid
    py -3 pyscript/hardtrack_stagea_validate.py "SID/Shogoon/*.sid" -t 20
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.fidelity_common import score_pct  # noqa: E402
from sidm2.hardtrack_parser import (  # noqa: E402
    HardTrackError, HardTrackModule, simulate,
)
from pyscript.hardtrack_validate import freq_tracks  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def build_and_wrap(sid, subtune, tmpdir):
    """.sid -> Stage A .sf2 -> playable .sid. Returns the wrapped path."""
    stem = os.path.splitext(os.path.basename(sid))[0]
    sf2 = os.path.join(tmpdir, stem + '.sf2')
    out = os.path.join(tmpdir, stem + '_d11.sid')
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, 'bin', 'hardtrack_to_sf2.py'),
         sid, sf2, '--subtune', str(subtune), '-q'],
        capture_output=True, text=True, cwd=ROOT)
    if r.returncode or not os.path.exists(sf2):
        raise RuntimeError(f'Stage A build failed: {r.stderr.strip()[:200]}')
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, 'scripts', 'sf2_to_sid.py'), sf2, out],
        capture_output=True, text=True, cwd=ROOT)
    if r.returncode or not os.path.exists(out):
        raise RuntimeError(f'sf2_to_sid failed: {r.stderr.strip()[:200]}')
    return out


def validate(sid, seconds=20, subtune=0):
    """-> (stage_a_ok, total, parser_ok) over sequencer-pitch notes."""
    module = HardTrackModule.from_sid(sid)
    frames = simulate(module, subtune, seconds * 50)
    with tempfile.TemporaryDirectory() as td:
        wrapped = build_and_wrap(sid, subtune, td)
        a_tracks = freq_tracks(wrapped, [f'-t{seconds}'])
    o_tracks = freq_tracks(sid, [f'-t{seconds}'] + ([f'-a{subtune}'] if subtune else []))

    a_ok = o_ok = tot = 0
    for vi in range(3):
        at, ot = a_tracks[vi], o_tracks[vi]
        for f, cell in ((f, r[vi]) for f, r in enumerate(frames) if r[vi]):
            note, instr = cell
            if module.instrument_drives_freq(instr):
                continue
            want = module.freq(note)
            tot += 1
            a_ok += any(at.get(f + d) == want for d in range(9))
            o_ok += any(ot.get(f + d) == want for d in range(9))
    return a_ok, tot, o_ok


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('sid', nargs='+')
    ap.add_argument('-t', '--seconds', type=int, default=20)
    ap.add_argument('-s', '--subtune', type=int, default=0)
    a = ap.parse_args(argv)

    paths = []
    for p in a.sid:
        paths.extend(sorted(glob.glob(p)) if any(c in p for c in '*?') else [p])

    ta = to = tt = 0
    print(f'{"file":28} {"Stage A":>15} {"parser ceiling":>16}')
    for sid in paths:
        try:
            ao, tot, oo = validate(sid, a.seconds, a.subtune)
        except (HardTrackError, RuntimeError):
            continue
        if not tot:
            continue
        ta += ao; to += oo; tt += tot
        print(f'{os.path.basename(sid):28} {ao:5}/{tot:<5} {score_pct(ao,tot):5.1f}%'
              f'   {oo:5}/{tot:<5} {score_pct(oo,tot):5.1f}%')
    if tt:
        print(f'\n{"CORPUS":28} Stage A {ta}/{tt} = {score_pct(ta,tt):.2f}%'
              f'   |   parser ceiling {to}/{tt} = {score_pct(to,tt):.2f}%')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
