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
from sidm2.hubbard_parser import (HubbardModule, decode_song, load_sid,
                                  detect_module_map, swallow_state,
                                  ticks_to_frames)
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
    hp_engine = 0 if os.environ.get('HUBBARD_PULSE_ENGINE') == '0' else 1
                              # the per-instrument ROM pulse engine (DEFAULT —
                              # Monty/Commando/Zoids pulse 100% vs <=98.6 with
                              # captured programs; =0 to fall back)

    def __init__(self, m, song, phase):
        self.m = m
        self.speed = m.resetspd
        self._fpt = m.frames_per_tick
        self.onset_delay = phase
        voices, _ = decode_song(m, song)
        self.voices = [[] for _ in range(3)]
        for v in range(3):
            cur_instr = 0
            prev_norel = False
            out = self.voices[v]
            for tk, n in voices[v]:
                if n.instr >= 0:
                    cur_instr = n.instr
                if n.append and out:
                    # TIE: the engine does not re-gate but the effects keep
                    # running — emit a per-segment tie event (own <=FM_CAP
                    # capture; merging built 512-frame chains whose FM
                    # truncated flat = the Monty-intro ornament defect)
                    out.append(MONEvent(note=out[-1].note, dur=n.ticks,
                                        instr=cur_instr, wprog=0,
                                        retrig=False, tie=True))
                    prev_norel = n.no_release
                    continue
                pitch = n.pitch if n.pitch >= 0 else 0
                if (prev_norel or getattr(n, 'no_fetch', False)) and out:
                    # No gate edge, no re-attack: (a) the previous note's
                    # bit5 (no release) skipped the length-end ADSR kill and
                    # the ROM's fetch writes ctrl over an already-on gate;
                    # (b) v2 pitch bit7 (no-fetch) changes pitch WITHOUT the
                    # instrument fetch. Both = a tie with a pitch update (a
                    # retrigger + $7D pre-kill audibly chops the voice)
                    out.append(MONEvent(note=pitch, dur=n.ticks,
                                        instr=cur_instr, wprog=0,
                                        retrig=False, tie=True))
                else:
                    out.append(MONEvent(note=pitch, dur=n.ticks,
                                        instr=cur_instr, wprog=0, retrig=True))
                prev_norel = n.no_release

    sw_per = 0                # v2 fractional tempo: dead-frame period
    sw_c0 = 0                 #   and first dead frame (song-global)

    @property
    def frames_per_tick(self):
        return self._fpt

    def tick_to_frame(self, ticks):
        return ticks_to_frames(ticks, self._fpt, self.sw_per, self.sw_c0)

    def frame_to_tick(self, frame):
        if not self.sw_per:
            return max(0, (frame + self._fpt - 1) // self._fpt)
        t = max(0, (frame + self._fpt - 1) // self._fpt)   # lower bound-ish
        while self.tick_to_frame(t) > frame and t > 0:
            t -= 1
        while self.tick_to_frame(t) < frame:
            t += 1
        return t

    def _voice_blocks(self, v):
        return [(0, self.voices[v])] if self.voices[v] else []

    def note_freq(self, note):
        return self.m.note_freq(note & 0x7F)

    def instrument(self, idx):
        ins = self.m.instrument(idx)
        return {'ad': ins['ad'], 'sr': ins['sr'],
                'waveform': ins['ctrl'] or 0x41,
                'pw': (ins['pwlo'] | (ins['pwhi'] << 8)) & 0x0FFF,
                'pulseval': ins['pulsespeed'], 'fx': ins['fx'],
                'wave_prog': 0, 'flags': 0, 'raw': [0] * 8}


class HPReplay:
    """py65-replay of the ORIGINAL ROM for the HP pulse engine's initial state.

    The ROM ships nonzero pulsedelay values in its load image (Monty: [0,1,29])
    and NEVER resets the counter at note fetch, so a part starting mid-song must
    inherit the exact per-voice pulsedelay/pulsedir and per-instrument live PW
    the ROM had at that frame. Addresses are found relocation-safe from the
    pulsework code itself."""

    def __init__(self, sid, song, m):
        from py65.devices.mpu6502 import MPU
        d, la, h = load_sid(sid)
        self.m = m
        self.mpu = MPU()
        for i, b in enumerate(d):
            self.mpu.memory[(la + i) & 0xFFFF] = b
        raw = bytes(d)
        # compilation rips: window the pulsework signature scan to m's module
        # (each embedded player has its own pulsedelay/pulsedir)
        mhits = HubbardModule.module_hits(d)
        if len(mhits) > 1:
            k = getattr(m, 'module', 0)
            w_lo = 0 if k == 0 else mhits[k - 1] + 1
            w_hi = mhits[k] + 1
        else:
            w_lo, w_hi = 0, len(raw)
        self.pd = self.pdir = None
        pd_i = -1
        for i in range(max(0, w_lo), min(len(raw) - 7, w_hi)):
            # pulsedelay: AND #$1F ... DEC abs,x / BPL
            if (raw[i] == 0xDE and raw[i + 3] == 0x10
                    and b'\x29\x1f' in raw[max(0, i - 8):i]):
                self.pd = raw[i + 1] | (raw[i + 2] << 8)
                pd_i = i
            # pulsedir: CMP #$0E / BNE / INC abs,x
            if (raw[i] == 0xC9 and raw[i + 1] == 0x0E and raw[i + 2] == 0xD0
                    and raw[i + 4] == 0xFE):
                self.pdir = raw[i + 5] | (raw[i + 6] << 8)
        # mode A (fx bit3 fast-PWM) exists only in later revisions: AND #$08 in
        # the pulsework body (Commando/Zoids yes, Monty no — its drums carry
        # bit3 with a different meaning and must NOT select fast-PWM)
        self.mode_a = (pd_i >= 0
                       and b'\x29\x08' in raw[max(0, pd_i - 96):pd_i + 96])
        self._call(h.init_address, song)
        self.play = h.play_address
        self.frame = 0

    def _call(self, addr, a=0):
        mp = self.mpu
        mp.a, mp.x, mp.y = a & 0xFF, 0, 0
        mp.pc = addr
        mp.memory[0x1FF] = 0xFF
        mp.memory[0x1FE] = 0xFE
        mp.sp = 0xFD
        for _ in range(2_000_000):
            if mp.pc == 0xFFFF:
                return
            mp.step()

    def state_at(self, frame):
        """State snapshot at ORIG frame `frame` (non-decreasing calls only)."""
        while self.frame < frame:
            self._call(self.play)
            self.frame += 1
        mem = self.mpu.memory
        base = self.m.lay.instr
        return {
            'pdly': [mem[self.pd + v] for v in range(3)] if self.pd else [0] * 3,
            'pdir': [mem[self.pdir + v] & 1 for v in range(3)] if self.pdir else [0] * 3,
            'live_pw': {i: (mem[base + i * 8] | (mem[base + i * 8 + 1] << 8)) & 0x0FFF
                        for i in range(32)},
            'mode_a': self.mode_a,
        }


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
    n_mod = HubbardModule.module_count(d)
    if n_mod > 1:
        # compilation rip: PSID song -> embedded module (its own full player);
        # the song WITHIN a module is always table entry 0
        mm = detect_module_map(d, la, h.init_address, max(SONG + 1, n_mod))
        mod = mm.get(SONG, 0)
        print(f"  compilation rip: {n_mod} modules, psid song {SONG} -> module {mod}")
        m = HubbardModule(d, la, module=mod)
        dsong = 0
    else:
        m = HubbardModule(d, la)
        dsong = SONG
    voices, totals = decode_song(m, dsong)
    phase = find_phase(SID, SONG, m, voices)
    shim = HubbardShim(m, dsong, phase)
    if m.lay.swallow_period:
        shim.sw_per = m.lay.swallow_period
        shim.sw_c0 = swallow_state(d, la, h.init_address, SONG, m.lay)
        print(f"  fractional tempo: swallow period={shim.sw_per} "
              f"first-skip={shim.sw_c0}")

    def part_swallow(t0):
        """(period, frames-until-first-skip) at part window start t0."""
        if not shim.sw_per:
            return None
        per, c0 = shim.sw_per, shim.sw_c0
        d0 = c0 if t0 <= c0 else c0 + ((t0 - c0 + per - 1) // per) * per
        return (per, d0 - t0)
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

    hpr = HPReplay(SID, SONG, m) if shim.hp_engine else None

    adaptive = warg.lower() in ("auto", "a")
    if not adaptive:
        t1 = min(span, int(warg) * 50)
        br = BM.build_native_song(shim, SID, SONG, {}, [], win=(0, t1),
                                  traces=traces)
        if hpr:
            shim.hp_state = hpr.state_at(0)
        shim.swallow = part_swallow(0)
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
    maxp = int(os.environ.get('HUBBARD_MAX_PARTS', '0')) or 10**9
    while t0 < span and len(bounds) < maxp:
        t1 = min(t0 + STEP, span)
        while t1 < span and fits(t0, min(t1 + STEP, span)):
            t1 = min(t1 + STEP, span)
        bounds.append((t0, t1))
        t0 = t1
    print(f"  packed into {len(bounds)} adaptive parts"
          + (" (HUBBARD_MAX_PARTS cap)" if len(bounds) >= maxp else ""))
    for part, (t0, t1) in enumerate(bounds, 1):
        br = BM.build_native_song(shim, SID, SONG, {}, [], win=(t0, t1),
                                  traces=traces)
        if hpr:
            shim.hp_state = hpr.state_at(t0)
        shim.swallow = part_swallow(t0)
        out = os.path.join(ROOT, "out", "hubbard",
                           f"{base}_song{SONG}_part{part:02d}.sf2")
        BM.emit_one(shim, br, out,
                    f"part {part}/{len(bounds)} ({t0 // 50}-{t1 // 50}s)")


if __name__ == "__main__":
    main()
