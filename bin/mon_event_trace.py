"""Supremacy (MoN flat variant) EVENT-BOUNDARY ground-truth tracer.

Drives the real player in py65 and logs the sequencer state at the three
decode-critical PCs (the same method as the freq-lookup tracer that cracked the
note formula):

  $1203  ORDERLIST pattern select (end of the $11DF fall-through prefix chain):
         A = pattern index, with the per-voice transpose ($1007), instrument
         base ($100D) and repeat ($1016) the chain just left behind — settles
         the orderlist-chain question against any static model.
  $12C1  EVENT FINALIZE (note-trigger path — plain notes, $FD slides, and the
         prefix-chain retrigger all funnel here).
  $1343  the REST/alternate finalize (the $124A handler's exit).

Per event: frame, voice, pattern read position (Y / $E6), orderlist position
($E9), note ($F0), duration state ($F3/$F6), instrument ($1026 = idx*7), wprog
($1064), slide ($102F speed / $1032 target), transpose/base/repeat, $10DB.

  py -3 bin/mon_event_trace.py [SID] [subtune] [seconds] [--voice N] [--from SEC]
        [--csv out.csv]

This is the decode answer sheet for the portamento/30-60s section (see
whats-next.md item 5): retrigger conditions, rest timing, additive durations
and the orderlist chain all become mechanical lookups against this trace.
"""
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sidm2.mon_parser import load_sid                    # noqa: E402
from py65.devices.mpu6502 import MPU                     # noqa: E402

# decode-critical PCs (Supremacy loads at $1000; these are absolute in the binary)
PC_OLSEL = 0x1203        # orderlist pattern select (STA $E3,X)
PC_FINAL = 0x12C1        # event finalize (note trigger)
PC_REST = 0x1343         # rest/alternate finalize

FIELDS = ['frame', 'kind', 'voice', 'a', 'y', 'pat_e3', 'pos_e6', 'ol_e9',
          'note_f0', 'dur_f3', 'dur_f6', 'instr26', 'wprog64', 'slide2f',
          'target32', 'transp07', 'base0d', 'rep16', 'loop_db']


def trace(path, subtune, seconds):
    d, la, h = load_sid(path)
    mpu = MPU()
    for i, b in enumerate(d):
        mpu.memory[(la + i) & 0xFFFF] = b

    def call(addr, a=0, max_steps=100_000, hook=None):
        mpu.a, mpu.x, mpu.y = a, 0, 0
        mpu.pc = addr
        mpu.memory[0x01FF] = 0xFF                        # JSR-style return to $FFFF
        mpu.memory[0x01FE] = 0xFE
        mpu.sp = 0xFD
        for _ in range(max_steps):
            if mpu.pc == 0xFFFF:
                return True
            if hook is not None:
                hook()
            mpu.step()
        return False

    if not call(h.init_address, a=subtune):
        raise RuntimeError("init did not return")

    events = []
    frame = [0]

    def snap(kind):
        x = mpu.x & 0x03
        mem = mpu.memory
        events.append({
            'frame': frame[0], 'kind': kind, 'voice': x,
            'a': mpu.a, 'y': mpu.y,
            'pat_e3': mem[0xE3 + x], 'pos_e6': mem[0xE6 + x],
            'ol_e9': mem[0xE9 + x], 'note_f0': mem[0xF0 + x],
            'dur_f3': mem[0xF3 + x], 'dur_f6': mem[0xF6 + x],
            'instr26': mem[0x1026 + x], 'wprog64': mem[0x1064 + x],
            'slide2f': mem[0x102F + x], 'target32': mem[0x1032 + x],
            'transp07': mem[0x1007 + x], 'base0d': mem[0x100D + x],
            'rep16': mem[0x1016 + x], 'loop_db': mem[0x10DB],
        })

    def hook():
        pc = mpu.pc
        if pc == PC_OLSEL:
            snap('olsel')
        elif pc == PC_FINAL:
            snap('note')
        elif pc == PC_REST:
            snap('rest')

    for f in range(seconds * 50):
        frame[0] = f
        if not call(h.play_address, a=0, hook=hook):
            raise RuntimeError(f"play did not return at frame {f}")
    return events


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    path = args[0] if args else os.path.join('SID', 'Tel_Jeroen', 'Supremacy.sid')
    sub = int(args[1]) if len(args) > 1 else 2
    secs = int(args[2]) if len(args) > 2 else 40

    def opt(name, default=None):
        for i, a in enumerate(sys.argv):
            if a == name and i + 1 < len(sys.argv):
                return sys.argv[i + 1]
        return default
    want_voice = opt('--voice')
    from_sec = int(opt('--from', '0'))
    csv_out = opt('--csv')

    os.chdir(ROOT)
    events = trace(path, sub, secs)
    print(f"{os.path.basename(path)} sub{sub}: {len(events)} events over {secs}s")

    if csv_out:
        with open(csv_out, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(events)
        print(f"wrote {csv_out}")

    hdr = (f"{'frame':>6} {'kind':5} v {'A':>2} {'Y':>3} {'e3':>2} {'e6':>3} "
           f"{'e9':>2} {'F0':>2} {'F3':>3} {'F6':>3} {'i26':>3} {'wp':>2} "
           f"{'sl':>2} {'tg':>2} {'tr':>2} {'0d':>2} {'rp':>2} {'db':>2}")
    print(hdr)
    for e in events:
        if want_voice is not None and e['voice'] != int(want_voice):
            continue
        if e['frame'] < from_sec * 50:
            continue
        print(f"{e['frame']:6} {e['kind']:5} {e['voice']} {e['a']:02X} {e['y']:3}"
              f" {e['pat_e3']:02X} {e['pos_e6']:3} {e['ol_e9']:02X} {e['note_f0']:02X}"
              f" {e['dur_f3']:3} {e['dur_f6']:3} {e['instr26']:3} {e['wprog64']:2X}"
              f" {e['slide2f']:2X} {e['target32']:2X} {e['transp07']:2X}"
              f" {e['base0d']:2X} {e['rep16']:2X} {e['loop_db']:2X}")


if __name__ == '__main__':
    main()
