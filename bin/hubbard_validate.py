"""Onset validation for the Rob Hubbard v1 parser vs siddump.

Compares the parser's predicted note onsets (non-append notes; onset frame =
tick * (resetspd+1) + PHASE) against siddump gate-on onsets. PHASE is a small
per-file constant (the initial `speed` counter value shifts the first note-tick
by 0-2 frames — Monty/Commando are 0, Crazy Comets/Zoids are +1, Chimera +2);
it is searched in [-4, 8] like every other fidelity tool's alignment.

  py -3 bin/hubbard_validate.py                      # Monty, song 0, 60s
  py -3 bin/hubbard_validate.py path.sid [SONG] [SECS]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from sidm2.hubbard_parser import HubbardModule, decode_song, load_sid
from sidm2.fidelity_common import siddump_note_onsets


def validate(path, song=0, secs=60):
    """Returns (per-voice coverage %, phase, counts). Coverage = % of siddump
    onset frames the parser predicts exactly (after the constant phase)."""
    d, la, h = load_sid(path)
    m = HubbardModule(d, la)
    voices, _ = decode_song(m, song)
    real = siddump_note_onsets(path, [f'-a{song}', f'-t{secs}'])
    fpt = m.frames_per_tick
    win = (secs - 1) * 50
    rf = []
    for v in range(3):
        rl = real[v] if isinstance(real, (list, tuple)) else real.get(v, [])
        rf.append(set(f for f, _ in rl if f < win))
    pf = [set(tk * fpt for tk, n in voices[v]
              if not n.append and n.pitch >= 0) for v in range(3)]

    def score(ph):
        return sum(len(rf[v] & set(f + ph for f in pf[v])) for v in range(3))
    phase = max(range(-4, 9), key=score)
    cov = []
    for v in range(3):
        hit = len(rf[v] & set(f + phase for f in pf[v]))
        cov.append(100.0 * hit / len(rf[v]) if rf[v] else -1.0)
    counts = [len(rf[v]) for v in range(3)]
    return cov, phase, counts, m


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'SID/Hubbard_Rob/Monty_on_the_Run.sid'
    song = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    secs = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    cov, phase, counts, m = validate(path, song, secs)
    print(f'{os.path.basename(path)} song{song}  fpt={m.frames_per_tick} phase={phase}')
    for v in range(3):
        print(f'  V{v}: {cov[v]:6.1f}% of {counts[v]} onsets')


if __name__ == '__main__':
    main()
