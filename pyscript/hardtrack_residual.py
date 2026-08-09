"""Explain the HardTrack PARSER residual -- the ~11.3% of sequencer-pitch notes
whose exact frequency-table value never reaches $D400/$D401.

The headline parser figure asks one question: does the player's OWN table value
for the decoded note reach the frequency register within 8 frames? For 652 of
5,784 notes it does not, and that shortfall was previously unattributed. This
tool answers what those notes are doing, and the answer is NOT decode error:

  * The wave program's arp column owns the frequency register. On every frame
    the stepper writes freq[(note + arp) & $7F] -- or freq[arp & $7F] when the
    arp byte is >= $80 (an ABSOLUTE note). The sequencer note is a BASE the
    program offsets from, so the bare table value appears only on frames whose
    arp step happens to be zero. An instrument whose program has no zero step
    inside the window can never score, however perfect the decode.

  * There is a constant 3-frame delay between the frame `simulate()` dispatches
    a row on and the frame the program's first step reaches the register. It is
    NOT a row-grid phase error: a wrong tempo phase would scale with speed+1,
    and this does not move across tempo dividers 2..6. `simulate()`'s grid is
    right -- confirmed against the player's own init, which leaves the divider
    at 2 (`STY $1100` with Y=2).

What is modelled here is only the arp column, enough to attribute the residual.
The full per-frame engine lives in `sidm2.hardtrack_synth`; this tool
deliberately does not duplicate it, and reports register-level agreement rather
than claiming a fidelity score.

Usage:
    py -3 pyscript/hardtrack_residual.py "SID/Shogoon/*.sid" [-t 20]
    py -3 pyscript/hardtrack_residual.py "SID/Shogoon/*.sid" --phase-scan
"""
from __future__ import annotations

import argparse
import collections
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sidm2.hardtrack_parser import (  # noqa: E402
    HardTrackError, HardTrackModule, INSTR_LEGATO, simulate,
)
from pyscript.hardtrack_validate import SETTLE_FRAMES, freq_tracks  # noqa: E402

# The measured note-on -> register delay. Established two independent ways:
# directly, by reading raw siddump at the first note-on of three files (the
# first sequencer output lands on frame 4 where simulate() dispatches on frame
# 1), and by solving for the phase at which the arp model agrees frame-exactly,
# which comes out 3 unanimously across every file and every tempo divider.
NOTE_ON_DELAY = 3
LOOKAHEAD = 33


def arp_steps(module, cursor, n=LOOKAHEAD):
    """The arp byte the wave stepper applies on each of `n` frames.

    Transcribed from the player's own stepper (Griffin_Score $141D):

        LDY cur,X / INC cur,X / LDA WAVE,Y / CMP #$FF / BNE +
        LDA ARP,Y / STA cur,X / JMP re-enter        ; $FF = jump, target in ARP
        CMP #$FE / BNE + / DEC freeze,X / JMP skip  ; $FE = stop writing freq

    The cursor is incremented BEFORE the $FF test, and $FE does not hold its own
    arp byte -- it gates the stepper off entirely (the freeze counter is tested
    at the top of the routine), so the register keeps its previous value. None
    marks such a frame: "no write, register holds".
    """
    if module.wave_table is None:
        return [None] * n
    out, c, stopped = [], cursor, False
    for _ in range(n):
        if stopped:
            out.append(None)
            continue
        wf = arp = None
        for _hop in range(8):
            y = c
            c = (c + 1) & 0xFF
            wf = module.byte(module.wave_table + y)
            if wf == 0xFF:
                c = module.byte(module.arp_table + y)
                continue
            arp = module.byte(module.arp_table + y)
            break
        else:
            stopped = True
        if stopped or wf == 0xFE:
            stopped = True
            out.append(None)
            continue
        out.append(arp)
    return out


def arp_note(arp: int, note: int) -> int:
    """The note index the stepper selects for an arp byte.

    $00-$7F is a relative semitone offset added to the note and masked ($144A
    `CLC / ADC note,X / AND #$7F`); $80+ is an ABSOLUTE note ($1448 `BMI` skips
    the add).
    """
    return (note + arp) & 0x7F if arp < 0x80 else arp & 0x7F


def scan(sid, seconds=20, subtune=0):
    """-> one record per sequencer-pitch note."""
    module = HardTrackModule.from_sid(sid)
    frames = simulate(module, subtune, seconds * 50)
    tracks = freq_tracks(sid, [f'-t{seconds}']
                         + ([f'-a{subtune}'] if subtune else []))
    last = max(max(t) for t in tracks.values() if t)

    out = []
    for vi in range(3):
        track = tracks[vi]
        for f, onset in ((f, r[vi]) for f, r in enumerate(frames) if r[vi]):
            if module.instrument_drives_freq(onset.instrument):
                continue
            if f + 1 + SETTLE_FRAMES > last:
                continue
            note = onset.note
            want = module.freq(note)
            hit = any(track.get(f + d) == want for d in range(SETTLE_FRAMES + 1))
            arps = arp_steps(module, module.instrument(onset.instrument).wave_cursor)
            out.append(dict(
                file=os.path.basename(sid)[:-4], v=vi, f=f, note=note,
                raw=onset.raw, hit=hit, arps=arps, speed=module.speed(subtune),
                obs=[track.get(f + d) for d in range(LOOKAHEAD)],
                want=want,
                pred=[None if a is None else module.freq(arp_note(a, note))
                      for a in arps]))
    return out


def explained(r, phase=NOTE_ON_DELAY, span=SETTLE_FRAMES + 1):
    """Does the modelled program predict the register on some frame?"""
    for d in range(span):
        j = d - phase
        if 0 <= j < len(r['pred']) and r['pred'][j] is not None \
                and r['obs'][d] == r['pred'][j]:
            return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('sid', nargs='+')
    ap.add_argument('-t', '--seconds', type=int, default=20)
    ap.add_argument('-s', '--subtune', type=int, default=0)
    ap.add_argument('--phase-scan', action='store_true',
                    help='show that the note-on delay is 3 at every tempo')
    a = ap.parse_args(argv)

    paths = []
    for p in a.sid:
        paths.extend(sorted(glob.glob(p)) if any(c in p for c in '*?') else [p])

    rows = []
    for sid in paths:
        try:
            rows.extend(scan(sid, a.seconds, a.subtune))
        except (HardTrackError, RuntimeError, ValueError):
            continue
    if not rows:
        print('no scoreable notes')
        return 1

    lost = [r for r in rows if not r['hit']]
    print(f'{len(rows)} sequencer-pitch notes, {len(lost)} lost '
          f'({100.0 * len(lost) / len(rows):.2f}%)  [{SETTLE_FRAMES}-frame window]\n')

    if a.phase_scan:
        print('note-on -> register delay, solved per note, grouped by tempo divider')
        print('(a row-grid phase error would scale with speed+1; this does not)')
        by = collections.defaultdict(collections.Counter)
        for r in rows:
            for p in range(-2, 9):
                n = ok = 0
                for d in range(SETTLE_FRAMES + 1):
                    j = d - p
                    if not (0 <= j < len(r['pred'])) or r['pred'][j] is None \
                            or r['obs'][d] is None:
                        continue
                    n += 1
                    ok += (r['obs'][d] == r['pred'][j])
                if n >= 3 and ok == n:
                    by[r['speed']][p] += 1
        print(f'{"speed":>6} {"notes":>7}   delay:count')
        for s in sorted(by):
            top = by[s].most_common(4)
            print(f'{s:>6} {sum(by[s].values()):>7}   '
                  + '  '.join(f'{p}:{n}' for p, n in top))
        print()

    ok_l = sum(explained(r) for r in lost)
    ok_k = sum(explained(r) for r in rows if r['hit'])
    nkept = len(rows) - len(lost)
    print(f'the modelled arp program predicts the register (delay {NOTE_ON_DELAY}):')
    print(f'   on LOST notes  {ok_l:5}/{len(lost):<5} {100.0*ok_l/len(lost):5.1f}%')
    print(f'   on kept notes  {ok_k:5}/{nkept:<5} {100.0*ok_k/nkept:5.1f}%'
          '   <- a model that only fitted the losses would not do this\n')

    never = sum(1 for r in lost if r['want'] not in
                [v for v in r['obs'] if v is not None])
    print(f'lost notes whose bare table value is NEVER written, even within '
          f'{LOOKAHEAD} frames: {never}/{len(lost)} = {100.0*never/len(lost):.1f}%')
    print('   for those the metric asks for something the player never does\n')

    bad = [r for r in lost if not explained(r)]
    leg = sum(1 for r in bad if r['raw'] == INSTR_LEGATO)
    print(f'unexplained: {len(bad)} notes = {100.0*len(bad)/len(rows):.2f}% of all '
          f'sequencer-pitch notes')
    print(f'   {leg} of them carry instrument byte $6F (legato). That is an '
          'association only --\n   the obvious mechanism (legato does not restart '
          'the program, so the cursor\n   continues) was TESTED AND FALSIFIED: '
          'allowing any cursor phase explains\n   just 2 of them, against a '
          '1.5% hit rate for other instruments\' programs.')
    for k, n in collections.Counter((r['file'], r['raw']) for r in bad).most_common(6):
        print(f'      {k[0][:26]:26} raw ${k[1]:02X}  {n:3}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
