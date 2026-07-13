"""Onset + pitch validation of sidm2.deenen_parser against siddump.

For each voice: match the decoder's predicted note onsets (frame, semitone)
against siddump's real gated onsets. A per-file frame PHASE and a global
semitone OFFSET are searched (like every other SIDM2 fidelity tool); reported
numbers are the median-over-voices onset-frame coverage and, among frame-matched
onsets, the pitch-match rate.

  py -3 bin/deenen_validate.py                       # whole SID/deenen replay set
  py -3 bin/deenen_validate.py SID/deenen/Ding_van_Charles.sid [SUBTUNE] [SECS]
"""
import os
import sys
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from sidm2.deenen_parser import DeenenModule, load_sid, DISPATCH_SIG
from sidm2.fidelity_common import freq_to_semi, siddump_note_onsets

NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
FRAME_TOL = 4

REPLAY = ['After_the_War', 'Astro_Marine_Corps', 'B_A_T', 'Back_to_the_Future_III',
          'Constant_Runner', 'Cool_Tune', 'Ding_van_Charles', 'Eye_to_Eye_intro',
          'F1_Simulator', 'Hotline_Intro', 'Hotline_Intro_Tune', 'Koekoek',
          'Lord_of_the_Rings', 'Mantalos', 'Mr_Heli', 'Satan', 'Shitty_Disco_Dump',
          'Smooth_Criminal', 'Zamzara']


def name_to_semi(nm):
    return NAMES.index(nm[:2]) + 12 * int(nm[2])


def validate(path, subtune, secs):
    d, la, h = load_sid(path)
    m = DeenenModule(d, la, subtune)
    if not m.loc.ok():
        return None
    win = secs * 50
    parser = [[(f, freq_to_semi(m._freq(n))) for f, n in m.voice_onsets(v) if f < win]
              for v in range(3)]
    realm = siddump_note_onsets(path, [f'-a{subtune}', f'-t{secs}'], require_wf=True)
    real = [[(f, name_to_semi(nm)) for f, nm in realm[v] if f < win] for v in range(3)]

    # search a global frame phase + semitone offset maximizing total onset hits
    def hits(ph, so):
        tot = 0
        for v in range(3):
            rf = real[v]
            for pf, ps in parser[v]:
                cand = [rs for rf2, rs in rf if abs(rf2 - (pf + ph)) <= FRAME_TOL]
                if cand and any((ps + so) % 12 == rs % 12 for rs in cand):
                    tot += 1
        return tot
    best = (-1, 0, 0)
    for ph in range(-6, 7):
        for so in range(-12, 13):
            hh = hits(ph, so)
            if hh > best[0]:
                best = (hh, ph, so)
    _, ph, so = best

    onset_cov, pitch_rate = [], []
    for v in range(3):
        rf = real[v]
        if not rf:
            continue
        omatch = pmatch = 0
        for pf, ps in parser[v]:
            cand = [rs for rf2, rs in rf if abs(rf2 - (pf + ph)) <= FRAME_TOL]
            if cand:
                omatch += 1
                if any((ps + so) % 12 == rs % 12 for rs in cand):
                    pmatch += 1
        onset_cov.append(100.0 * omatch / len(rf))
        pitch_rate.append(100.0 * pmatch / omatch if omatch else 0.0)
    if not onset_cov:
        return None
    return (statistics.median(onset_cov), statistics.median(pitch_rate),
            ph, so, [len(r) for r in real], [len(p) for p in parser])


def main():
    args = sys.argv[1:]
    secs = 30
    if args and args[0].endswith('.sid'):
        path = args[0]
        st = int(args[1]) if len(args) > 1 else 0
        if len(args) > 2:
            secs = int(args[2])
        r = validate(path, st, secs)
        print(path, '->', r)
        return 0
    print(f"{'tune':26} {'locate':>6} {'onset%':>7} {'pitch%':>7} {'ph':>4} {'so':>4} "
          f"{'real':>12} {'parse':>12}")
    oks = 0
    for nm in REPLAY:
        p = f'SID/deenen/{nm}.sid'
        d, la, h = load_sid(p)
        m = DeenenModule(d, la, 0)
        loc = 'Y' if m.loc.ok() else ('sig' if m.loc.dispatch else 'N')
        r = validate(p, 0, secs)
        if r is None:
            print(f"{nm:26} {loc:>6} {'--':>7} {'--':>7}")
            continue
        oks += 1
        oc, pr, ph, so, rl, pl = r
        print(f"{nm:26} {loc:>6} {oc:7.1f} {pr:7.1f} {ph:4d} {so:4d} "
              f"{str(rl):>12} {str(pl):>12}")
    print(f"\nlocated+decoded: {oks}/{len(REPLAY)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
