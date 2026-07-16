"""Engine-note agreement: compare the decoder to the PLAYER'S OWN note stream.

Why this exists
---------------
`bin/deenen_validate.py` scores pitch by comparing decoded note indices against
`freq_to_semi()` of the real SID frequency at each gate-on frame. That is an
INFERENCE about what the player meant, and it can disagree with a decoder that is
in fact exact — Constant_Runner scores 35.6% pitch there while reproducing the
player's notes perfectly.

This tool removes the inference. The Deenen note handler computes its final note
index and stores it (`$152A: STA $f2,X` on Constant_Runner — `LDA $d0 / CLC /
ADC $da,X` then index FREQ_LO/FREQ_HI). Watching that store gives the note the
player ACTUALLY played, from its own state, with no metric in between. Comparing
the decoder against it answers "is the decode right?" directly, instead of
"does the decode agree with my model of the SID output?".

This is the strongest ground truth available for this engine, and it is how
Constant_Runner's decode was proven exact (92/92, 80/80, 34/34 on 2026-07-16)
while deenen_validate still reported 35.6%.

CAVEAT: it validates NOTES, not timing, timbre or effects. A file can pass here
and still not sound right (slides/vibrato/instruments are not checked). Use it to
separate "the decoder is wrong" from "the metric is wrong" — not as a fidelity
claim on its own.

Usage: py -3 bin/deenen_engine_check.py [name ...]     (default: the known set)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from py65.devices.mpu6502 import MPU
from sidm2.deenen_parser import load_sid, DeenenModule

# The note handler's `STA $f2,X` — the player's own computed note index.
NOTE_ZP = 0xF2


class Mem:
    """RAM that records the note-store site only."""

    def __init__(self, store_pc):
        self.m = bytearray(0x10000)
        self.notes = [[], [], []]
        self.store_pc = store_pc
        self.pc = 0

    def __len__(self):
        return len(self.m)

    def __getitem__(self, a):
        return self.m[a]

    def __setitem__(self, a, v):
        if isinstance(a, slice):
            self.m[a] = v
            return
        if NOTE_ZP <= a <= NOTE_ZP + 2 and self.pc == self.store_pc:
            self.notes[a - NOTE_ZP].append(v & 0xFF)
        self.m[a] = v & 0xFF


def find_note_store(d, la):
    """Locate `CLC / ADC $da,X / STA $f2,X` — the note-formation site.

    ANCHORED, not scanned. A bare scan for `18 75 xx 95 xx` finds the first such
    sequence anywhere in the file, which is usually NOT the note handler (that
    mistake made every file read 0% here). The row dispatch
    `CMP #$60 / BCS +3 / JMP note` (the DISPATCH_SIG) carries the note handler's
    address in its JMP operand — start there.
    """
    i = d.find(bytes([0xC9, 0x60, 0xB0, 0x03, 0x4C]))
    if i < 0:
        return None, None
    handler = d[i + 5] | (d[i + 6] << 8)                    # the JMP target
    o = handler - la
    if not (0 <= o < len(d) - 8):
        return None, None
    for k in range(o, min(o + 0x40, len(d) - 5)):           # within the handler
        if (d[k] == 0x18 and d[k + 1] == 0x75 and           # CLC ; ADC zp,X
                d[k + 3] == 0x95):                          # STA zp,X
            return la + k + 3, d[k + 4]                     # pc of STA, its zp
    return None, None


def check(name, frames=1200):
    path = os.path.join(ROOT, 'SID', 'deenen', name + '.sid')
    d, la, h = load_sid(path)
    pc, zp = find_note_store(d, la)
    if pc is None:
        print(f'{name:24} note-store site NOT FOUND — cannot check')
        return None
    global NOTE_ZP
    NOTE_ZP = zp
    mem = Mem(pc)
    mem.m[la:la + len(d)] = d
    mpu = MPU(memory=mem)
    mem.m[0x01] = 0x37

    def run(addr):
        mpu.a = 0
        mpu.pc = addr
        mpu.sp = 0xFF
        for _ in range(300000):
            mem.pc = mpu.pc
            if mem.m[mpu.pc] == 0x60 and mpu.sp >= 0xFF:
                break
            mpu.step()

    run(h['init'])
    mem.notes = [[], [], []]
    for _ in range(frames):
        run(h['play'])

    m = DeenenModule(d, la, 0, h)
    out = []
    for v in range(3):
        real = mem.notes[v]
        dec = [e['note'] for e in m.decode_voice(v, max_rows=400)
               if e['kind'] == 'note']
        n = min(len(real), len(dec))
        same = sum(1 for i in range(n) if real[i] == dec[i])
        pct = 100.0 * same / n if n else None      # None = no evidence, not 100
        out.append((pct, n, len(real), len(dec)))
    s = '  '.join(
        f'v{v} ' + (f'{p:5.1f}% n={n}' if p is not None else '  n/a  ')
        for v, (p, n, _, _) in enumerate(out))
    # `all()` over an empty sequence is True — an all-n/a file would claim a
    # perfect match on no evidence. That is the vacuous-100 bug this project
    # keeps finding (see sidm2.fidelity_common.score_pct); require evidence.
    scored = [p for p, n, _, _ in out if n]
    flag = ''
    if scored and all(p == 100.0 for p in scored):
        flag = '   <-- decoder reproduces the player EXACTLY'
    print(f'{name:24} {s}{flag}')
    return out


if __name__ == '__main__':
    names = sys.argv[1:] or ['Ding_van_Charles', 'B_A_T', 'Lord_of_the_Rings',
                             'After_the_War', 'Constant_Runner', 'Mantalos',
                             'Zamzara', 'Mr_Heli', 'Astro_Marine_Corps']
    print('engine-note agreement: decoder vs the PLAYER\'S OWN computed note '
          '(notes only — not timing/timbre/effects)\n')
    for n in names:
        try:
            check(n)
        except Exception as e:
            print(f'{n:24} EXC {type(e).__name__}: {e}')
