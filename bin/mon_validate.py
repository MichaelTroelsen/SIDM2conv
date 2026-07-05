"""Frame-timing validation of the Maniacs of Noise (Hawkeye) parser.

Compares, per voice, the parser's predicted note ONSETS (frame number + note)
against the ground truth from siddump_complete.py. The parser computes each
onset frame as cumulative_ticks * (speed+1); siddump gives the real player's
output. Only retriggered notes are compared (legato/slide notes appear bracketed
in siddump, not as fresh onsets).

  py -3 bin/mon_validate.py                       # Hawkeye subtune 3
  py -3 bin/mon_validate.py path.sid SUBTUNE      # any tune/subtune
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sidm2.mon_parser import load_sid, MON
from sidm2.fidelity_common import siddump_note_onsets

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']


def note_name(n):
    """MoN note byte -> siddump-style name. The MoN note == siddump abs-note
    value; siddump prints octave = (abs>>4)-? Empirically abs $11 -> F-1, so
    name = NAMES[n%12] + str(n//12) does NOT line up; calibrate to siddump by
    matching the chromatic table instead (handled by the caller comparing the
    siddump-reported names directly)."""
    return NAMES[n % 12] + str(n // 12)


def siddump_onsets(sidpath, subtune, seconds):
    """-> {0,1,2: [(frame, note_name), ...]} retriggered onsets per voice
    (unbracketed note with WF present = a fresh gated onset)."""
    return siddump_note_onsets(sidpath, [f'-a{subtune}', f'-t{seconds}'],
                               require_wf=True)


def parser_onsets(path, subtune, max_frame):
    """-> {0,1,2: [(frame, mon_note), ...]} predicted retrig onsets per voice
    (exact tick grid via MON.tick_to_frame — handles swing tempos)."""
    d, la, _ = load_sid(path)
    m = MON(d, la, subtune)
    V = {}
    for v in range(3):
        ticks = 0
        out = []
        for ev in m.voices[v]:
            frame = m.tick_to_frame(ticks)
            if ev.retrig:
                out.append((frame, ev.note))
            ticks += ev.dur
            if frame > max_frame:
                break
        V[v] = out
    return V, m


def main():
    os.chdir(ROOT)
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join('SID', 'Tel_Jeroen', 'Hawkeye.sid')
    subtune = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    seconds = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    max_frame = seconds * 50

    sd = siddump_onsets(path, subtune, seconds)
    pa, m = parser_onsets(path, subtune, max_frame)

    # constant engine output offset: sequencer state reaches the SID a fixed
    # 1-2 frames after the tick (engine-variant dependent) — calibrate it out
    # as the median first-onset delta, like mon_sf2_validate.
    deltas = [sd[v][0][0] - pa[v][0][0] for v in range(3) if sd[v] and pa[v]]
    off = sorted(deltas)[len(deltas) // 2] if deltas else 0
    pa = {v: [(f + off, n) for f, n in pa[v]] for v in range(3)}

    swing = f" swing({m.speed},{m.speed + 1})" if m.tempo_toggle else ""
    print(f"{os.path.basename(path)} subtune {subtune}  "
          f"speed={m.speed} frames/tick={m.frames_per_tick}{swing}  "
          f"onset offset={off}  window={seconds}s\n")

    total_ok = total = 0
    for v in range(3):
        # Compare only within the OVERLAPPING frame range: the parser emits ONE
        # orderlist pass while siddump keeps playing (looping short orderlists)
        # and stops at the window edge — so clip both to min(last-onset frame) so
        # neither the loop nor the window edge creates phantom mismatches.
        limit = min(sd[v][-1][0] if sd[v] else 0, pa[v][-1][0] if pa[v] else 0)
        so = [x for x in sd[v] if x[0] <= limit]
        po = [x for x in pa[v] if x[0] <= limit]
        n = min(len(so), len(po))
        frame_ok = sum(1 for i in range(n) if so[i][0] == po[i][0])
        total_ok += frame_ok
        total += max(len(so), len(po))
        status = 'EXACT' if (frame_ok == len(so) == len(po)) else f'{frame_ok}/{max(len(so), len(po))}'
        print(f"  V{v}: siddump={len(so):3} parser={len(po):3} frame-match={status}")
        for i in range(n):
            if so[i][0] != po[i][0]:
                print(f"       first diff @idx {i}: siddump frame {so[i][0]} ({so[i][1]}) "
                      f"vs parser frame {po[i][0]} (note ${po[i][1]:02X})")
                break
    print(f"\nonset frames matched: {total_ok}/{total}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
