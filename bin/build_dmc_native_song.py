"""DMC (Bjerregaard / Demo Music Creator) SID -> native SF2 (Stage B).

The DMC parser (sidm2/dmc_parser.py, onset-validated) provides tick-timed note
events; a MON-compatible shim feeds bin/build_mon_native_song's build_native_song
— the same trace-driven engine that produced Hawkeye/Hubbard/etc. Every note's
per-frame freq / waveform / pulse / filter is captured from the siddump trace, so
the native driver reproduces DMC's PWM / vibrato / wavetable / filter engines
without modelling them.

  py -3 bin/build_dmc_native_song.py SID/JohannesBjerregaard/Rockbuster.sid [secs|auto]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)

from sidm2.mon_parser import MONEvent
from sidm2.dmc_parser import load_sid, DMCModule, decode_song
import build_mon_native_song as BM

SID = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    "SID", "JohannesBjerregaard", "Rockbuster.sid")
warg = sys.argv[2] if len(sys.argv) > 2 else "auto"


class DMCShim:
    """MON-compatible view of a decoded DMC song for the native build."""

    tempo_toggle = False
    hard_restart = 0          # DMC gates per note; no Hubbard-style $7D kill
    snap_gate = True          # snap capture onsets to the trace's gate-rise frame
    hp_engine = 0             # DMC pulse comes from captured programs (its own PWM)

    def __init__(self, m, phase, budget_ticks):
        self.m = m
        self._fpt = m.lay.tempo_reload + 1
        self.onset_delay = phase
        voices = decode_song(m, tick_budget=budget_ticks)
        self.voices = [[] for _ in range(3)]
        for v in range(3):
            cur = 0
            out = self.voices[v]
            for tk, n in voices[v]:
                if n.pitch < 0:               # REST
                    out.append(MONEvent(note=0, dur=n.ticks, instr=cur,
                                        wprog=0, retrig=False, rest=True))
                    continue
                if n.sound >= 0:
                    cur = n.sound
                out.append(MONEvent(note=n.pitch, dur=n.ticks, instr=cur,
                                    wprog=0, retrig=True))

    @property
    def frames_per_tick(self):
        return self._fpt

    def tick_to_frame(self, ticks):
        return ticks * self._fpt

    def frame_to_tick(self, frame):
        return max(0, (frame + self._fpt - 1) // self._fpt)

    def _voice_blocks(self, v):
        return [(0, self.voices[v])] if self.voices[v] else []

    def note_freq(self, note):
        return self.m.note_freq(note & 0x7F)

    def instrument(self, idx):
        s = self.m.sound(idx)             # [AD,SR,PWinit,PWrails,PWspeed,vib,f6,f7]
        return {'ad': s[0], 'sr': s[1],
                'waveform': 0x41,          # hint; real waveform captured per-frame
                'pw': s[2] | ((s[3] & 0x0F) << 8),
                'pulseval': s[4], 'fx': 0,
                'wave_prog': 0, 'flags': 0, 'raw': list(s)}


def find_phase(path, m, voices):
    from sidm2.fidelity_common import siddump_note_onsets
    real = siddump_note_onsets(path, ['-a0', '-t20'])
    fpt = m.lay.tempo_reload + 1
    pf = [set(tk * fpt for tk, n in voices[v] if n.pitch >= 0) for v in range(3)]

    def score(ph):
        s = 0
        for v in range(3):
            rl = real[v] if isinstance(real, (list, tuple)) else real.get(v, [])
            s += len(set(f for f, _ in rl) & set(f + ph for f in pf[v]))
        return s
    return max(range(0, 8), key=score)


def main():
    d, la, h = load_sid(SID)
    m = DMCModule(d, la)
    if not (m.lay.sector_lo and m.lay.sound and m.lay.freq and m.lay.trk_lo):
        sys.exit("DMC tables not located (variant?) — cannot build")
    fpt = m.lay.tempo_reload + 1
    voices0 = decode_song(m, tick_budget=4000)
    phase = find_phase(SID, m, voices0)
    span_ticks = max((sum(n.ticks for _, n in voices0[v]) for v in range(3)),
                     default=0)
    span = span_ticks * fpt + phase
    base = os.path.splitext(os.path.basename(SID))[0]
    print(f"{base}: fpt={fpt} phase={phase} span={span // 50}s "
          f"events={[len(v) for v in voices0]}")

    shim = DMCShim(m, phase, budget_ticks=span_ticks + 8)

    import mon_fidelity as F
    secs = span // 50 + 4
    print(f"  tracing full song ({secs}s)...")
    traces = (F.per_frame(SID, [f'-a0', f'-t{secs}']),
              BM.filter_trace(SID, 0, secs))

    adaptive = warg.lower() in ("auto", "a")
    if not adaptive:
        t1 = min(span, int(warg) * 50)
        br = BM.build_native_song(shim, SID, 0, {}, [], win=(0, t1), traces=traces)
        out = os.path.join(ROOT, "out", "dmc", f"{base}_part01.sf2")
        BM.emit_one(shim, br, out, f"{base} 0-{t1 // 50}s")
        return

    CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP = 63, 32, 256, 120, 100

    def fits(t0, t1):
        nb, ni, nw, nf, ns = BM.build_native_song(
            shim, SID, 0, {}, [], win=(t0, t1), traces=traces, count_only=True)
        return (nb <= CAP_B and ni <= CAP_I and nw <= CAP_TBL
                and nf <= CAP_TBL and ns <= CAP_SEG)

    bounds, t0 = [], 0
    maxp = int(os.environ.get('DMC_MAX_PARTS', '0')) or 10**9
    while t0 < span and len(bounds) < maxp:
        t1 = min(t0 + STEP, span)
        while t1 < span and fits(t0, min(t1 + STEP, span)):
            t1 = min(t1 + STEP, span)
        bounds.append((t0, t1))
        t0 = t1
    print(f"  packed into {len(bounds)} adaptive parts")
    for part, (t0, t1) in enumerate(bounds, 1):
        br = BM.build_native_song(shim, SID, 0, {}, [], win=(t0, t1), traces=traces)
        out = os.path.join(ROOT, "out", "dmc", f"{base}_part{part:02d}.sf2")
        BM.emit_one(shim, br, out, f"part {part}/{len(bounds)} "
                    f"({t0 // 50}-{t1 // 50}s)")


if __name__ == "__main__":
    main()
