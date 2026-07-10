"""Sound Monitor (Huelsbeck) SID -> native SF2 (Stage B).

The SM parser (sidm2/soundmonitor_parser.py, 99.9% onset-validated) provides
step-timed note events; a MON-compatible shim feeds bin/build_mon_native_song's
build_native_song — the same trace-driven engine that produced Hawkeye/Hubbard/
DMC. Every note's per-frame freq / waveform / pulse / filter is captured from
the siddump trace, so the native driver reproduces SM's chord-arps, glides,
bends, gated release waveforms and filter sweeps without modelling them.

Notes are placed ONSET-ALIGNED: at the exact emulated $D404 gate-rise frames
(sidm2.dmc_parser.measure_onsets — player-agnostic), pitch resolved from the
trace. Voices that rarely re-gate (SM's gated-release instruments make whole
voices legato) are A/B'd against a decode-driven schedule per voice, exactly
like the DMC builder.

  py -3 bin/build_soundmonitor_native_song.py SID/Fun_Fun/Final_Luv.sid [secs|auto]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)

from sidm2.mon_parser import MONEvent
from sidm2.soundmonitor_parser import (load_sid, is_soundmonitor,
                                       SoundMonitorModule)
from sidm2.dmc_parser import measure_onsets
from sidm2.sid_player import FREQ_TABLE_LO, FREQ_TABLE_HI
from sidm2.fidelity_common import freq_to_semi
import build_mon_native_song as BM


def _pal(note):
    n = max(0, min(95, note))
    return FREQ_TABLE_LO[n] | (FREQ_TABLE_HI[n] << 8)


def _freq_at(frames, v, idx):
    return frames[idx][0][v]['freq'] if 0 <= idx < len(frames) else 0


def _sem(frames, v, onset):
    """Base semitone = the original's freq at the note's gate-rise frame (the
    driver holds `base` on the trigger frame; the FM capture reproduces every
    later frame). Guard the FM $40-$43 raw-delta collision by seating the base
    high when frame 1's jump would collide (see the DMC builder / memory)."""
    o = onset
    for k in range(max(0, onset - 1), onset + 3):    # snap to the wf&1 gate-rise
        wf = frames[k][0][v]['wf'] if k < len(frames) else 0
        pwf = frames[k - 1][0][v]['wf'] if 0 < k < len(frames) else 0
        if (wf & 1) and not (pwf & 1):
            o = k
            break
    f0 = _freq_at(frames, v, o) or _freq_at(frames, v, o + 1) \
        or _freq_at(frames, v, o + 2)
    if not f0:
        return 48
    s0 = freq_to_semi(f0)
    f1 = _freq_at(frames, v, o + 1)
    if f1:
        delta1 = (f1 - _pal(s0)) & 0xFFFF
        if ((delta1 >> 8) & 0xFC) == 0x40:           # unencodable raw delta
            return freq_to_semi(f1)
    return s0


def decode_streams(m):
    """SM events -> per-voice [(frame, kind, note, instr)] with the play
    routine's exact frame timing (init divider preset 7 -> the first step lasts
    8 frames, later steps speed+1; see $C93A/$C4BC)."""
    ev = m.events()
    streams = [[], [], []]
    # walk rows once for the shared frame clock
    frame_of = {}                       # (row, step) -> frame
    frame = 0
    first = True
    for row, hdr in m.row_chain():
        for step in range(hdr['length']):
            frame_of[(row, step)] = frame
            frame += 8 if first else hdr['speed'] + 1
            first = False
    for v in range(3):
        for row, step, kind, note, instr, arp, glide in ev[v]:
            fr = frame_of.get((row, step))
            if fr is None:
                continue
            streams[v].append((fr, kind, note, instr))
    return streams, frame


SID = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    "SID", "Fun_Fun", "Final_Luv.sid")
warg = sys.argv[2] if len(sys.argv) > 2 else "auto"


class SMShim:
    """MON-compatible view of a decoded Sound Monitor song."""

    tempo_toggle = False
    hard_restart = 0
    snap_gate = True
    hp_engine = 0             # SM pulse/vibrato come from captured programs

    def __init__(self, m, streams, span, onsets=None, frames=None,
                 legato_set=frozenset(), phase=0):
        self.m = m
        self._fpt = 1
        self.onset_delay = 0
        self.voices = [[] for _ in range(3)]
        for v in range(3):
            out = self.voices[v]
            notes = [(fr, note, instr) for fr, kind, note, instr in streams[v]
                     if kind in ('note', 'legato')]
            changes = [(fr, instr) for fr, note, instr in notes]
            tie_set = set()
            if v in legato_set:
                # decode-driven: one note per PITCH CHANGE at its decode frame
                # (aligned by `phase`) — the schedule for voices whose gated
                # release waveform makes gate-rises collapse the whole voice.
                ons, prev = [], None
                for fr, note, instr in notes:
                    f = fr + phase
                    if f >= 0 and note != prev:
                        ons.append(f)
                        prev = note
            else:
                ons = list(onsets[v]) if onsets else [fr + phase
                                                      for fr, _, _ in notes]
                # TIE SPLITS: SM notes that arrive while the gate is already on
                # change pitch WITHOUT a gate-rise (mixed voices do this per
                # section, so the per-voice legato A/B can't catch it — Fuck_Off
                # osc2 held a wrong pitch for 1080 frames). The decode knows
                # every note boundary; add the uncovered ones as TIE events
                # (the native driver re-seats freq + starts a fresh FM/wave
                # capture without restarting the envelope — the Supremacy $FB
                # mechanism). ONLY past the FM capture window: a pitch change
                # within FM_CAP frames of the last event is already reproduced
                # exactly by the captured FM program — splitting those doubles
                # the bundle count (Dance 10 -> 20 parts) for zero fidelity.
                gate_near = set()
                for g in ons:
                    gate_near.update(range(g - 2, g + 3))
                gates = sorted(ons)
                gi = 0
                last_evt = -10**9      # most recent gate or tie before f
                prev = None
                for fr, note, instr in notes:      # ascending frames
                    f = fr + phase
                    while gi < len(gates) and gates[gi] <= f:
                        last_evt = gates[gi]
                        gi += 1
                    if (f >= 0 and note != prev and f not in gate_near
                            and f - last_evt >= BM.FM_CAP - 2):
                        tie_set.add(f)
                        last_evt = f
                    prev = note
                ons = sorted(set(ons) | tie_set)
            if not ons:
                continue
            if ons[0] > 0:
                out.append(MONEvent(note=0, dur=ons[0], instr=0,
                                    wprog=0, retrig=False, rest=True))
            ci = 0
            cur = changes[0][1] if changes else 0
            for i, o in enumerate(ons):
                while ci < len(changes) and changes[ci][0] + phase <= o + 2:
                    cur = changes[ci][1]
                    ci += 1
                nxt = ons[i + 1] if i + 1 < len(ons) else min(o + 8, span)
                note = _sem(frames, v, o) if frames is not None else 48
                tie = o in tie_set
                out.append(MONEvent(note=note, dur=max(1, nxt - o),
                                    instr=cur, wprog=0, retrig=not tie,
                                    tie=tie))

    @property
    def frames_per_tick(self):
        return self._fpt

    def tick_to_frame(self, ticks):
        return ticks * self._fpt

    def frame_to_tick(self, frame):
        return max(0, frame)

    def _voice_blocks(self, v):
        return [(0, self.voices[v])] if self.voices[v] else []

    def note_freq(self, note):
        return _pal(note)

    def instrument(self, idx):
        rec = self.m.sound(idx)
        return {'ad': rec[1], 'sr': rec[2],
                'waveform': rec[0] or 0x41,   # hint; real wf captured per-frame
                'pw': 0x800, 'pulseval': 0, 'fx': 0,
                'wave_prog': 0, 'flags': 0, 'raw': list(rec)}


CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP = 63, 32, 256, 120, 100


def build_song(shim, base_name, traces, span, emit=True):
    """Adaptive part-split + build, identical policy to the DMC builder."""
    def fits(t0, t1):
        nb, ni, nw, nf, ns = BM.build_native_song(
            shim, SID, 0, {}, [], win=(t0, t1), traces=traces, count_only=True)
        return (nb <= CAP_B and ni <= CAP_I and nw <= CAP_TBL
                and nf <= CAP_TBL and ns <= CAP_SEG)
    bounds, t0 = [], 0
    maxp = int(os.environ.get('SM_MAX_PARTS', '0')) or 10**9
    while t0 < span and len(bounds) < maxp:
        t1 = min(t0 + STEP, span)
        while t1 < span and fits(t0, min(t1 + STEP, span)):
            t1 = min(t1 + STEP, span)
        bounds.append((t0, t1))
        t0 = t1
    parts = []
    for part, (t0, t1) in enumerate(bounds, 1):
        out = os.path.join(ROOT, "out", "soundmonitor",
                           f"{base_name}_part{part:02d}.sf2")
        if emit:
            br = BM.build_native_song(shim, SID, 0, {}, [], win=(t0, t1),
                                      traces=traces)
            BM.emit_one(shim, br, out, f"part {part}/{len(bounds)} "
                        f"({t0 // 50}-{t1 // 50}s)")
        parts.append((out, t0, t1))
    if emit:
        BM.prune_stale_parts(os.path.join(ROOT, "out", "soundmonitor",
                                          base_name), len(bounds))
    return parts


def measure_song_voices(parts, traces):
    """Per-voice freq% across all parts vs the original (the DMC A/B metric)."""
    import bin.mon_sf2_validate as V
    import mon_fidelity as F
    from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo
    orig = traces[0]
    ok = [0, 0, 0]
    tot = [0, 0, 0]
    for pf, t0, t1 in parts:
        try:
            sf2 = bytearray(open(pf, "rb").read())
            info = SF2DriverInfo()
            sla = parse_sf2_blocks(sf2, info)
            probe = pf[:-4] + ".sid"
            open(probe, "wb").write(V._psid(bytes(sf2[2:]), sla, 0x1000, 0x1003))
        except Exception:
            continue
        dur = t1 - t0
        prb = F.per_frame(probe, [f"-t{dur // 50 + 2}"])
        n = min(len(prb), dur, len(orig) - t0) - 4
        if n <= 0:
            continue

        def sc(dly):
            s = 0
            for i in range(0, n, 3):
                for v in range(3):
                    if 0 <= t0 + dly + i < len(orig):
                        a = orig[t0 + dly + i][0][v]['freq']
                        b = prb[i][0][v]['freq']
                        if a and b and F._semi(a) == F._semi(b):
                            s += 1
            return s
        dly = max(range(-6, 10), key=sc)
        for v in range(3):
            for i in range(n):
                if not (0 <= t0 + dly + i < len(orig)):
                    continue
                a = orig[t0 + dly + i][0][v]['freq']
                b = prb[i][0][v]['freq']
                if a is None and b is None:
                    continue
                tot[v] += 1
                ok[v] += (a and b and F._semi(a) == F._semi(b))
    return [100.0 * ok[v] / tot[v] if tot[v] else 100.0 for v in range(3)]


def find_phase(streams, onsets):
    """Align the decode frame clock to the emulated gate-rises (the decode's
    first step is nominally frame 0; emulation places it a couple of frames
    later)."""
    dec = [set(fr for fr, kind, _, _ in streams[v] if kind == 'note')
           for v in range(3)]

    def score(ph):
        s = 0
        for v in range(3):
            em = set(onsets[v])
            s += sum(1 for f in dec[v]
                     if (f + ph) in em or (f + ph + 1) in em
                     or (f + ph - 1) in em)
        return s
    return max(range(0, 8), key=score)


def legato_candidates(streams, onsets):
    """Voices whose decode has far more pitch changes than gate-rises."""
    cands = set()
    for v in range(3):
        g = len(onsets[v])
        pc, prev = 0, None
        for fr, kind, note, instr in streams[v]:
            if kind in ('note', 'legato') and note != prev:
                pc += 1
                prev = note
        if pc > max(8, 1.3 * g):
            cands.add(v)
    return cands


def main():
    d, la, h = load_sid(SID)
    if not is_soundmonitor(d, la, h):
        sys.exit(f"not a Sound Monitor rip: {SID}")
    m = SoundMonitorModule(d, la)
    streams, span = decode_streams(m)
    base = os.path.splitext(os.path.basename(SID))[0]
    print(f"{base}: rows={len(m.row_chain())} span={span // 50}s "
          f"events={[len(s) for s in streams]}")

    import mon_fidelity as F
    secs = span // 50 + 4
    print(f"  tracing full song ({secs}s)...")
    traces = (F.per_frame(SID, ['-a0', f'-t{secs}']),
              BM.filter_trace(SID, 0, secs))

    onsets = measure_onsets(d, la, h.init_address, h.play_address,
                            min(span, len(traces[0])))
    from sidm2.fidelity_common import siddump_note_onsets
    real = siddump_note_onsets(SID, ['-a0', f'-t{min(secs, 15)}'])
    agree = 0
    tot = 0
    for v in range(3):
        rl = set(fr for fr, _ in (real[v] if isinstance(real, (list, tuple))
                                  else real.get(v, [])) if fr < 700)
        em = set(onsets[v])
        agree += sum(1 for fr in rl if fr in em or fr + 1 in em or fr - 1 in em)
        tot += len(rl)
    use_onsets = tot and agree / tot >= 0.85
    print(f"  emulated onsets agree with trace: {agree}/{tot} "
          f"-> {'ONSET-ALIGNED' if use_onsets else 'decode-grid (fallback)'}")
    phase = find_phase(streams, onsets)
    print(f"  decode->trace phase: +{phase} frames")
    adaptive = warg.lower() in ("auto", "a")

    legato_set = frozenset()
    ab_on = (adaptive and use_onsets
             and os.environ.get("SM_LEGATO_AB", "1") != "0")
    if ab_on:
        cands = legato_candidates(streams, onsets)
        if cands:
            sk = dict(onsets=onsets, frames=traces[0], phase=phase)
            ab_span = min(span, 90 * 50)
            print(f"  legato A/B: candidates {sorted(cands)} "
                  f"— building both configs over {ab_span // 50}s...")
            pg = build_song(SMShim(m, streams, span, **sk), "_abg", traces,
                            ab_span)
            fg = measure_song_voices(pg, traces)
            pl = build_song(SMShim(m, streams, span,
                                   legato_set=frozenset(cands), **sk),
                            "_abl", traces, ab_span)
            fl = measure_song_voices(pl, traces)
            legato_set = frozenset(v for v in cands if fl[v] > fg[v] + 1.0)
            print(f"  legato A/B: gate={[round(fg[v], 1) for v in sorted(cands)]} "
                  f"legato={[round(fl[v], 1) for v in sorted(cands)]} "
                  f"-> legato voices {sorted(legato_set)}")

    shim = SMShim(m, streams, span, onsets=onsets if use_onsets else None,
                  frames=traces[0], legato_set=legato_set, phase=phase)

    if not adaptive:
        t1 = min(span, int(warg) * 50)
        br = BM.build_native_song(shim, SID, 0, {}, [], win=(0, t1),
                                  traces=traces)
        out = os.path.join(ROOT, "out", "soundmonitor", f"{base}_part01.sf2")
        BM.emit_one(shim, br, out, f"{base} 0-{t1 // 50}s")
        return

    parts = build_song(shim, base, traces, span)
    print(f"  packed into {len(parts)} adaptive parts")


if __name__ == "__main__":
    main()
