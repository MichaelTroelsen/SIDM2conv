"""Myth (Jeroen Tel / MoN relocating compilation) -> native SF2, via EMULATION extraction.

Myth's sub-player uses relative pointers + a relocation base ($900A:B) and play=$0000
(self-IRQ), so a static parser is impractical. Instead we drive the sub-player in py65
(relocate $2000->$9000, init, call play $9006 per frame) and extract EVERYTHING by
emulation: the per-voice note/duration/instrument events (from the freq-lookup $93EE),
the per-frame full SID state ($D400-$D418 -> freq/wf/pulse/AD-SR/filter), and the freq +
instrument tables from the relocated image. A MON-compatible shim feeds the shared
trace-driven native build (bin/build_mon_native_song.build_native_song), the same
pipeline that produced Hawkeye/Cybernoid/Supremacy.

  py -3 bin/build_myth_native_song.py [sub] [seconds|auto]
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
from sidm2.mon_parser import load_sid, MONEvent
from py65.devices.mpu6502 import MPU
import build_mon_native_song as BM

SUB = int(sys.argv[1]) if len(sys.argv) > 1 else 0
warg = sys.argv[2] if len(sys.argv) > 2 else "30"

SID = os.path.join("SID", "Tel_Jeroen", "Myth.sid")
os.chdir(ROOT)
d, la, h = load_sid(SID)
SRC, DST = (0x2000, 0x9000) if SUB == 0 else (0x3E00, 0xA400)
INITB, PLAYB = DST, DST + 6
FREQLOOK = DST + (0x93EE - 0x9000)
FREQLO, FREQHI = DST + (0x90F4 - 0x9000), DST + (0x9153 - 0x9000)
DURREL, INSTRX, NOTEIDX = 0x90E8, 0x90E5, 0x90F1

mpu = MPU()
for i, b in enumerate(d):
    mpu.memory[(la + i) & 0xFFFF] = b
for i in range(0x1000):
    mpu.memory[DST + i] = mpu.memory[SRC + i]


def _run(pc, a=0):
    mpu.a, mpu.x, mpu.y = a & 0xFF, 0, 0
    mpu.pc = pc
    mpu.memory[0x01FF] = mpu.memory[0x01FE] = 0xFF
    mpu.sp = 0xFD
    for _ in range(500000):
        if mpu.pc == 0x0000:
            return
        mpu.step()


_run(INITB, SUB)

# capture the relocated freq tables (note-indexed)
FREQ_LO = [mpu.memory[FREQLO + i] for i in range(0x70)]
FREQ_HI = [mpu.memory[FREQHI + i] for i in range(0x70)]


def _state_hash():
    """A hash of the sub-player's per-voice sequencer state, to detect the song loop."""
    return bytes(mpu.memory[0x90CA:0x90F4]) + bytes(mpu.memory[0x0F:0x11])


def capture(nframes, detect_loop=False):
    """Run play per frame; return (events per voice, frames trace, ftr, instr_map).
    events[v] = list of (onset_frame, note_idx, instr_idx). frames[i] = (voicedict, fcut).
    ftr[i] = (cutoff11, ctrl). instr_map[idx] = {'ad','sr','waveform'} from first use.
    If detect_loop, stop when the sequencer state repeats (the song's loop length)."""
    events = [[], [], []]
    frames, ftr = [], []
    instr_map = {}
    seen = {}
    for fr in range(nframes):
        if detect_loop and fr > 8:
            hsh = _state_hash()
            if hsh in seen:
                print(f"  loop detected at frame {fr} (period {fr - seen[hsh]})")
                break
            seen[hsh] = fr
        mpu.a, mpu.x, mpu.y = 0, 0, 0
        mpu.pc = PLAYB
        mpu.memory[0x01FF] = mpu.memory[0x01FE] = 0xFF
        mpu.sp = 0xFD
        trig = []
        for _ in range(200000):
            if mpu.pc == 0x0000:
                break
            if mpu.pc == FREQLOOK and 0 <= mpu.x <= 2:
                trig.append((mpu.x, mpu.y, mpu.memory[INSTRX + mpu.x]))
            mpu.step()
        # end-of-frame SID state
        vd = {}
        for v in range(3):
            o = v * 7
            vd[v] = {
                'freq': mpu.memory[0xD400 + o] | (mpu.memory[0xD401 + o] << 8),
                'wf': mpu.memory[0xD404 + o],
                'pul': mpu.memory[0xD402 + o] | ((mpu.memory[0xD403 + o] & 0x0F) << 8),
            }
        cut = (mpu.memory[0xD415] & 0x07) | (mpu.memory[0xD416] << 3)
        frames.append((vd, cut))
        ftr.append((cut, mpu.memory[0xD417]))
        for v, noteidx, instr in trig:
            events[v].append((fr, noteidx, instr))
            if instr not in instr_map:
                o = v * 7
                instr_map[instr] = {'ad': mpu.memory[0xD405 + o],
                                    'sr': mpu.memory[0xD406 + o],
                                    'waveform': mpu.memory[0xD404 + o] or 0x41}
    return events, frames, ftr, instr_map


class MythShim:
    """MON-compatible view of the emulated Myth song for the native build."""

    def __init__(self, events, instr_map, fpt):
        self.speed = fpt - 1
        self._fpt = fpt
        self._instr_map = instr_map
        self.voices = [[] for _ in range(3)]
        for v in range(3):
            ev = events[v]
            for k, (onset, note, instr) in enumerate(ev):
                nxt = ev[k + 1][0] if k + 1 < len(ev) else onset + fpt
                dur_ticks = max(1, (nxt - onset) // fpt)
                self.voices[v].append(MONEvent(note=note, dur=dur_ticks, instr=instr,
                                               wprog=0, retrig=True))

    @property
    def frames_per_tick(self):
        return self._fpt

    def _voice_blocks(self, v):
        return [(0, self.voices[v])] if self.voices[v] else []

    def note_freq(self, note):
        note &= 0x7F
        if note >= 0x70:
            return 0
        return FREQ_LO[note] | (FREQ_HI[note] << 8)

    def instrument(self, idx):
        m = self._instr_map.get(idx, {'ad': 0x00, 'sr': 0xF0, 'waveform': 0x41})
        return {'ad': m['ad'], 'sr': m['sr'], 'waveform': m['waveform'],
                'pw': 0x800, 'wave_prog': 0, 'flags': 0, 'raw': [0] * 8}


def main():
    adaptive = warg.lower() in ("auto", "a")
    if adaptive:
        print(f"Myth sub{SUB}: relocate $%04X->$%04X, extracting full song (loop-detect)..."
              % (SRC, DST))
        events, frames, ftr, instr_map = capture(60000, detect_loop=True)
    else:
        span_s = int(warg)
        print(f"Myth sub{SUB}: relocate $%04X->$%04X, extracting {span_s}s..." % (SRC, DST))
        events, frames, ftr, instr_map = capture(span_s * 50 + 50)
    counts = [len(events[v]) for v in range(3)]
    gaps = []
    for v in range(3):
        ev = events[v]
        gaps += [ev[k + 1][0] - ev[k][0] for k in range(len(ev) - 1) if ev[k + 1][0] > ev[k][0]]
    fpt = 0
    for g in gaps:
        fpt = math.gcd(fpt, g)
    fpt = fpt or 1
    span = len(frames)
    print(f"  {span} frames  triggers/voice={counts}  instruments={sorted(instr_map)}  fpt={fpt}")

    m = MythShim(events, instr_map, fpt)
    BM.write_mon_freqtable = lambda mm: _write_freqtable()   # use the emulated freq table
    traces = (frames, ftr)
    base = f"Myth_sub{SUB}"

    if not adaptive:
        br = BM.build_native_song(m, SID, SUB, {}, [], win=(0, span), traces=traces)
        out = os.path.join(ROOT, "out", "mon", f"{base}_part01.sf2")
        BM.emit_one(m, br, out, f"{base} 0-{span // 50}s")
        return

    # adaptive windowing (mirror build_mon_native_song.main): grow each window until a
    # driver cap trips, using the cheap count_only probe.
    CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP = 63, 32, 256, 120, 100

    def fits(t0, t1):
        nb, ni, nw, nf, ns = BM.build_native_song(
            m, SID, SUB, {}, [], win=(t0, t1), traces=traces, count_only=True)
        return nb <= CAP_B and ni <= CAP_I and nw <= CAP_TBL and nf <= CAP_TBL and ns <= CAP_SEG

    bounds, t0 = [], 0
    while t0 < span:
        t1 = min(t0 + STEP, span)
        while t1 < span and fits(t0, min(t1 + STEP, span)):
            t1 = min(t1 + STEP, span)
        bounds.append((t0, t1))
        t0 = t1
    print(f"  packed into {len(bounds)} adaptive parts")
    for part, (t0, t1) in enumerate(bounds, 1):
        br = BM.build_native_song(m, SID, SUB, {}, [], win=(t0, t1), traces=traces)
        out = os.path.join(ROOT, "out", "mon", f"{base}_part{part:02d}.sf2")
        BM.emit_one(m, br, out, f"part {part}/{len(bounds)} ({t0 // 50}-{t1 // 50}s)")


def _write_freqtable():
    words = [(FREQ_LO[i] | (FREQ_HI[i] << 8)) & 0xFFFF for i in range(0x70)]
    with open(os.path.join(ROOT, "drivers_src", "mon", "freqtable.inc"), "w") as f:
        f.write("; Myth emulated note->freq table\n")
        for k in range(0, len(words), 8):
            f.write("        .word " + ", ".join(f"${w:04x}" for w in words[k:k + 8]) + "\n")


if __name__ == "__main__":
    main()
