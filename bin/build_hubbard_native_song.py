"""Rob Hubbard v1 SID -> native SF2 (Stage B), via the shared trace-driven pipeline.

The Hubbard parser (sidm2/hubbard_parser.py, onset-validated ~100%) provides exact
tick-timed events; a MON-compatible shim feeds bin/build_mon_native_song's
build_native_song — the same engine that produced Hawkeye/Cybernoid/Supremacy/Myth.
Every note's per-frame freq (vibrato/portamento/drums/skydive/octarp) and pulse
(the $08xx-$0Exx timbre oscillation) is captured from the siddump trace into FM /
pulse / wave programs, so the native driver reproduces the effects engine without
modeling it analytically.

APPEND (tie) notes are MERGED into their predecessor (the engine does not re-gate
them; the merged capture reproduces the actual gate/waveform stream).

  py -3 bin/build_hubbard_native_song.py SID/Hubbard_Rob/Monty_on_the_Run.sid [song] [seconds|auto]
"""
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)

from sidm2.mon_parser import MONEvent
from sidm2.hubbard_parser import HubbardModule, decode_song, load_sid
import build_mon_native_song as BM

SID = sys.argv[1] if len(sys.argv) > 1 else os.path.join("SID", "Hubbard_Rob",
                                                         "Monty_on_the_Run.sid")
SONG = int(sys.argv[2]) if len(sys.argv) > 2 else 0
warg = sys.argv[3] if len(sys.argv) > 3 else "auto"


class HubbardShim:
    """MON-compatible view of a decoded Hubbard song for the native build."""

    tempo_toggle = False
    hard_restart = 1          # Hubbard's release "kill adsr" + per-note ADSR re-arm
    snap_gate = True          # snap capture onsets to the trace's gate-rise frame
                              # (drums gate for ONE frame; a late phase loses it)

    def __init__(self, m, song, phase):
        self.m = m
        self.speed = m.resetspd
        self._fpt = m.frames_per_tick
        self.onset_delay = phase
        voices, _ = decode_song(m, song)
        self.voices = [[] for _ in range(3)]
        for v in range(3):
            cur_instr = 0
            out = self.voices[v]
            for tk, n in voices[v]:
                if n.instr >= 0:
                    cur_instr = n.instr
                if n.append and out:
                    # tie: the engine does not re-gate — extend the note
                    out[-1] = MONEvent(note=out[-1].note,
                                       dur=out[-1].dur + n.ticks,
                                       instr=out[-1].instr, wprog=0, retrig=True)
                    continue
                pitch = n.pitch if n.pitch >= 0 else 0
                out.append(MONEvent(note=pitch, dur=n.ticks, instr=cur_instr,
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
        ins = self.m.instrument(idx)
        return {'ad': ins['ad'], 'sr': ins['sr'],
                'waveform': ins['ctrl'] or 0x41,
                'pw': (ins['pwlo'] | (ins['pwhi'] << 8)) & 0x0FFF,
                'wave_prog': 0, 'flags': 0, 'raw': [0] * 8}


def find_phase(path, song, m, voices):
    """The per-file onset phase (0-2 frames): the initial speed-counter value
    shifts the first note-tick. Measured against a 30s siddump."""
    from sidm2.fidelity_common import siddump_note_onsets
    real = siddump_note_onsets(path, [f'-a{song}', '-t30'])
    fpt = m.frames_per_tick
    pf = [set(tk * fpt for tk, n in voices[v] if not n.append and n.pitch >= 0)
          for v in range(3)]

    def score(ph):
        s = 0
        for v in range(3):
            rl = real[v] if isinstance(real, (list, tuple)) else real.get(v, [])
            s += len(set(f for f, _ in rl) & set(f + ph for f in pf[v]))
        return s
    return max(range(0, 4), key=score)


def main():
    d, la, h = load_sid(SID)
    m = HubbardModule(d, la)
    voices, totals = decode_song(m, SONG)
    phase = find_phase(SID, SONG, m, voices)
    shim = HubbardShim(m, SONG, phase)
    span = shim.tick_to_frame(max(sum(ev.dur for ev in shim.voices[v])
                                  for v in range(3))) + phase
    base = os.path.splitext(os.path.basename(SID))[0]
    print(f"{base} song{SONG}: fpt={m.frames_per_tick} phase={phase} "
          f"span={span // 50}s events={[len(v) for v in shim.voices]}")

    import mon_fidelity as F
    secs = span // 50 + 4
    print(f"  tracing full song ({secs}s) once...")
    traces = (F.per_frame(SID, [f'-a{SONG}', f'-t{secs}']),
              BM.filter_trace(SID, SONG, secs))

    adaptive = warg.lower() in ("auto", "a")
    if not adaptive:
        t1 = min(span, int(warg) * 50)
        br = BM.build_native_song(shim, SID, SONG, {}, [], win=(0, t1),
                                  traces=traces)
        out = os.path.join(ROOT, "out", "hubbard",
                           f"{base}_song{SONG}_part01.sf2")
        BM.emit_one(shim, br, out, f"{base} 0-{t1 // 50}s")
        return

    CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP = 63, 32, 256, 120, 100

    def fits(t0, t1):
        nb, ni, nw, nf, ns = BM.build_native_song(
            shim, SID, SONG, {}, [], win=(t0, t1), traces=traces,
            count_only=True)
        return (nb <= CAP_B and ni <= CAP_I and nw <= CAP_TBL
                and nf <= CAP_TBL and ns <= CAP_SEG)

    bounds, t0 = [], 0
    while t0 < span:
        t1 = min(t0 + STEP, span)
        while t1 < span and fits(t0, min(t1 + STEP, span)):
            t1 = min(t1 + STEP, span)
        bounds.append((t0, t1))
        t0 = t1
    print(f"  packed into {len(bounds)} adaptive parts")
    for part, (t0, t1) in enumerate(bounds, 1):
        br = BM.build_native_song(shim, SID, SONG, {}, [], win=(t0, t1),
                                  traces=traces)
        out = os.path.join(ROOT, "out", "hubbard",
                           f"{base}_song{SONG}_part{part:02d}.sf2")
        BM.emit_one(shim, br, out,
                    f"part {part}/{len(bounds)} ({t0 // 50}-{t1 // 50}s)")


if __name__ == "__main__":
    main()
