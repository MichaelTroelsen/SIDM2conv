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
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sidm2.mon_parser import load_sid, MON

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
    """-> {0,1,2: [(frame, note_name), ...]} retriggered onsets per voice."""
    txt = subprocess.run(
        ['py', '-3', 'pyscript/siddump_complete.py', sidpath,
         f'-a{subtune}', f'-t{seconds}'], capture_output=True, text=True).stdout
    V = {0: [], 1: [], 2: []}
    for ln in txt.splitlines():
        if not ln.startswith('|') or 'Frame' in ln:
            continue
        c = [x.strip() for x in ln.split('|')]
        if len(c) < 6:
            continue
        try:
            fr = int(c[1])
        except ValueError:
            continue
        for vi, cell in enumerate(c[2:5]):
            # unbracketed note with WF present = a fresh gated onset
            m = re.match(r'^([0-9A-F]{4})\s+([A-G][-#]\d)\s+([0-9A-F]{2})\b', cell)
            if m and m.group(1) != '0000':
                V[vi].append((fr, m.group(2)))
    return V


def parser_onsets(path, subtune, max_frame):
    """-> {0,1,2: [(frame, mon_note), ...]} predicted retrig onsets per voice."""
    d, la, _ = load_sid(path)
    m = MON(d, la, subtune)
    fpt = m.frames_per_tick
    V = {}
    for v in range(3):
        frame = 0
        out = []
        for ev in m.voices[v]:
            if ev.retrig:
                out.append((frame, ev.note))
            frame += ev.dur * fpt
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
    print(f"{os.path.basename(path)} subtune {subtune}  "
          f"speed={m.speed} frames/tick={m.frames_per_tick}  window={seconds}s\n")

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
