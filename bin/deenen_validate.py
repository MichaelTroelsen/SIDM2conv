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
from sidm2.fidelity_common import freq_to_semi, siddump_note_onsets, siddump_freq_track

FRAME_TOL = 4
# The onset row's own frequency can be a 1-frame attack transient (e.g. a noise-
# flavored click before the tone locks in) rather than the settled target -- seen
# on Constant_Runner (engine-note-exact per bin/deenen_engine_check.py, yet the
# strict same-frame pitch check read 35.6%). A 0..2-frame settle window recovers
# it (15.9->99.1 / 93.2->97.7 on its two affected voices) and plateaus at 2 (no
# further gain at 3-4), verified corpus-wide with zero regression on the 4
# existing clean wins. Voice(s) that DON'T recover under this window (e.g.
# Constant_Runner voice1, flat ~35-40% at every window size 0-4) are a different,
# real issue -- an apparent unmodelled arpeggio/sweep effect instrument, not a
# metric artifact -- and should NOT be waved through by widening this further.
PITCH_SETTLE_WINDOW = 2

REPLAY = ['After_the_War', 'Astro_Marine_Corps', 'B_A_T', 'Back_to_the_Future_III',
          'Constant_Runner', 'Cool_Tune', 'Ding_van_Charles', 'Eye_to_Eye_intro',
          'F1_Simulator', 'Hotline_Intro', 'Hotline_Intro_Tune', 'Koekoek',
          'Lord_of_the_Rings', 'Mantalos', 'Mr_Heli', 'Satan', 'Shitty_Disco_Dump',
          'Smooth_Criminal', 'Zamzara']


def validate(path, subtune, secs):
    d, la, h = load_sid(path)
    m = DeenenModule(d, la, subtune, h)
    if not m.loc.ok():
        return None
    win = secs * 50
    parser = [[(f, freq_to_semi(m._freq(n))) for f, n in m.voice_onsets(v) if f < win]
              for v in range(3)]
    realm = siddump_note_onsets(path, [f'-a{subtune}', f'-t{secs}'], require_wf=True)
    real_frames = [[f for f, _ in realm[v] if f < win] for v in range(3)]
    freq_track = [siddump_freq_track(path, [f'-a{subtune}', f'-t{secs}'], v)
                  for v in range(3)]
    max_frame = [max(freq_track[v]) if freq_track[v] else 0 for v in range(3)]

    # Monotonic 1-1 alignment (each real onset + each parser onset consumed once)
    # so coverage is honest (<=100%, no flood over-count). Search a global frame
    # phase + semitone offset maximizing total frame-aligned onset hits.
    def align(myl, rf, ph, so, v):
        """-> (omatch, pmatch): frame-aligned pairs, and of those, pitch-class
        agreeing pairs, under a monotonic 1-1 walk of both sorted streams. Pitch
        is checked over rf2..rf2+PITCH_SETTLE_WINDOW (see module docstring) using
        the continuous raw frequency track, not just the onset row's own value."""
        i = j = om = pm = 0
        myl = sorted((pf + ph, ps) for pf, ps in myl)
        rf = sorted(rf)
        track = freq_track[v]
        while i < len(myl) and j < len(rf):
            pf, ps = myl[i]
            rf2 = rf[j]
            if abs(pf - rf2) <= FRAME_TOL:
                om += 1
                target = (ps + so) % 12
                for lag in range(0, PITCH_SETTLE_WINDOW + 1):
                    f2 = rf2 + lag
                    if f2 > max_frame[v]:
                        continue
                    rs = freq_to_semi(track.get(f2, 0))
                    if rs >= 0 and rs % 12 == target:
                        pm += 1
                        break
                i += 1
                j += 1
            elif pf < rf2 - FRAME_TOL:
                i += 1
            else:
                j += 1
        return om, pm

    # `so` (semitone offset) does not affect frame alignment -> pick `ph` by onset
    # match, then pick `so` by pitch match at that phase.
    best = (-1, 0)
    for ph in range(-6, 7):
        tot = sum(align(parser[v], real_frames[v], ph, 0, v)[0] for v in range(3))
        if tot > best[0]:
            best = (tot, ph)
    ph = best[1]
    bso = (-1, 0)
    for so in range(-12, 13):
        pm = sum(align(parser[v], real_frames[v], ph, so, v)[1] for v in range(3))
        if pm > bso[0]:
            bso = (pm, so)
    so = bso[1]

    onset_cov, pitch_rate = [], []
    for v in range(3):
        rf = real_frames[v]
        if not rf:
            continue
        om, pm = align(parser[v], rf, ph, so, v)
        onset_cov.append(100.0 * om / len(rf))
        pitch_rate.append(100.0 * pm / om if om else 0.0)
    if not onset_cov:
        return None
    return (statistics.median(onset_cov), statistics.median(pitch_rate),
            ph, so, [len(r) for r in real_frames], [len(p) for p in parser])


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
    print(f"{'tune':26} {'locate':>6} {'plaus':>5} {'onset%':>7} {'pitch%':>7} "
          f"{'ph':>4} {'so':>4} {'real':>12} {'parse':>12}")
    oks = wins = 0
    for nm in REPLAY:
        p = f'SID/deenen/{nm}.sid'
        d, la, h = load_sid(p)
        m = DeenenModule(d, la, 0, h)
        loc = 'Y' if m.loc.ok() else ('sig' if m.loc.dispatch else 'N')
        plaus = 'Y' if (m.loc.ok() and m.plausible()) else '-'
        r = validate(p, 0, secs)
        if r is None:
            print(f"{nm:26} {loc:>6} {plaus:>5} {'--':>7} {'--':>7}")
            continue
        oks += 1
        oc, pr, ph, so, rl, pl = r
        # a "win" = plausible decode with strong onset+pitch agreement
        if plaus == 'Y' and oc >= 75 and pr >= 75:
            wins += 1
        print(f"{nm:26} {loc:>6} {plaus:>5} {oc:7.1f} {pr:7.1f} {ph:4d} {so:4d} "
              f"{str(rl):>12} {str(pl):>12}")
    print(f"\nlocated+decoded: {oks}/{len(REPLAY)}   clean wins (plaus,"
          f" onset>=75, pitch>=75): {wins}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
