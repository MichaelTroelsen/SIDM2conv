"""Frame-timing validation of the Maniacs of Noise (Hawkeye) parser.

Compares, per voice, the parser's predicted note ONSETS (frame number + note)
against the ground truth from siddump_complete.py. The parser computes each
onset frame as cumulative_ticks * (speed+1); siddump gives the real player's
output. Only retriggered notes are compared (legato/slide notes appear bracketed
in siddump, not as fresh onsets).

  py -3 bin/mon_validate.py                       # Hawkeye subtune 3
  py -3 bin/mon_validate.py path.sid SUBTUNE      # any tune/subtune
"""
import itertools
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
    """-> ({0,1,2: [(frame, mon_note), ...]}, m, pass_frames): predicted retrig
    onsets per voice (exact tick grid via MON.tick_to_frame — handles swing
    tempos) plus the ONE-PASS length in frames (the parser decodes one orderlist
    pass; the real player LOOPS — e.g. Supremacy sub1 wraps at ~38s — so the
    comparison must clip to one pass)."""
    d, la, _ = load_sid(path)
    m = MON(d, la, subtune)
    V, vpass = {}, {}
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
        else:
            vpass[v] = m.tick_to_frame(ticks)   # this voice's full one-pass length
        V[v] = out
    return V, m, vpass


def _artifact_variant(sd_v, pa_v):
    """-> the drop-leading-onset variant of one voice's siddump list, or None
    if the count precondition doesn't even apply. Candidate fix for an
    `is_first_frame` display artifact (Monitor_Madness_1/2, Trying_Out_2: the
    INIT routine primes a voice's waveform register before the real first
    note; `format_voice_column`'s `is_first_frame` branch unconditionally
    shows a note for ANY wave>=0x10 on the very first displayed row, so that
    priming write reads as a spurious extra onset at frame 0) -- but a count
    mismatch of exactly one can ALSO be a genuine trailing wraparound onset
    unrelated to frame 0 (Cybernoid sub1 V2: found the hard way, dropping
    unconditionally silently broke an already-exact voice). NEVER apply this
    blind: `main()` tries both the original and this variant per voice and
    keeps whichever combination actually scores best, so a wrong guess here
    can only lose a tie-break, not regress a working voice."""
    if len(sd_v) == len(pa_v) + 1 and sd_v and sd_v[0][0] == 0:
        return sd_v[1:]
    return None


def _score(sd, pa_off, vpass):
    """Total (matched, out-of) onset frames for one candidate offset already
    applied to pa_off, using the SAME clip-to-overlap + per-index compare the
    final report uses."""
    total_ok = total = 0
    for v in range(3):
        limit = min(sd[v][-1][0] if sd[v] else 0, pa_off[v][-1][0] if pa_off[v] else 0)
        if v in vpass:
            limit = min(limit, vpass[v] - 1)
        so = [x for x in sd[v] if x[0] <= limit]
        po = [x for x in pa_off[v] if x[0] <= limit]
        n = min(len(so), len(po))
        total_ok += sum(1 for i in range(n) if so[i][0] == po[i][0])
        total += max(len(so), len(po))
    return total_ok, total


def main():
    os.chdir(ROOT)
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join('SID', 'Tel_Jeroen', 'Hawkeye.sid')
    subtune = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    seconds = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    max_frame = seconds * 50

    sd_raw = siddump_onsets(path, subtune, seconds)
    pa, m, vpass = parser_onsets(path, subtune, max_frame)

    # constant engine output offset: sequencer state reaches the SID a fixed
    # 1-2 frames after the tick (engine-variant dependent). Calibrated by
    # BRUTE-FORCE SEARCH over a small offset range (and, per voice, whether to
    # apply the `_artifact_variant` drop), picking whichever combination
    # maximizes total matched onset frames (using the exact same clip+compare
    # the final report uses) rather than trusting index-0 deltas alone. A
    # direct score search sidesteps guessing which index/voice is trustworthy:
    # whichever combination actually lines up the MOST onsets wins. Ties
    # prefer (in order) the smallest |offset|, then fewer artifact drops --
    # both bias toward the simplest explanation of the data, and the fewer-
    # drops tiebreak is what keeps this from ever REGRESSING a voice that was
    # already fine (dropping only wins a tie-break when it demonstrably helps).
    candidates = [[sd_raw[v]] for v in range(3)]
    for v in range(3):
        alt = _artifact_variant(sd_raw[v], pa[v])
        if alt is not None:
            candidates[v].append(alt)
    best_key, best_sd, best_off = None, sd_raw, 0
    for combo in itertools.product(*candidates):
        sd_try = {v: combo[v] for v in range(3)}
        ndrops = sum(1 for v in range(3) if combo[v] is not sd_raw[v])
        for off in range(-20, 21):
            pa_try = {v: [(f + off, n) for f, n in pa[v]] for v in range(3)}
            ok, _ = _score(sd_try, pa_try, vpass)
            key = (ok, -abs(off), -ndrops)
            if best_key is None or key > best_key:
                best_key, best_sd, best_off = key, sd_try, off
    sd, off = best_sd, best_off
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
        # LOOP-AWARE: the parser decodes ONE orderlist pass; the real player wraps
        # (per voice — e.g. Supremacy sub1 V1 at ~38s). Clip both streams to this
        # voice's one-pass length so pass-2 onsets don't count as mismatches.
        if v in vpass:
            limit = min(limit, vpass[v] - 1)
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
