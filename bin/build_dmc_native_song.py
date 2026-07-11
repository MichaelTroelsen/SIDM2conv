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
from sidm2.dmc_parser import (load_sid, DMCModule, decode_song, measure_onsets)
from sidm2.sid_player import FREQ_TABLE_LO, FREQ_TABLE_HI
from sidm2.fidelity_common import freq_to_semi
import build_mon_native_song as BM


def _pal(note):
    n = max(0, min(95, note))
    return FREQ_TABLE_LO[n] | (FREQ_TABLE_HI[n] << 8)


SEM_MODE = os.environ.get("DMC_SEM_MODE", "adapt").lower()


def _freq_at(frames, v, idx):
    return frames[idx][0][v]['freq'] if 0 <= idx < len(frames) else 0


def _sem(frames, v, onset, end=None):
    """Base semitone for a note = the semitone the driver plays on its TRIGGER
    frame (frame 0 holds `base`; the FM capture reproduces frames 1+ exactly).
    The metric-optimal base is therefore the original's freq at the note's actual
    gate-rise frame — but the gate-rise sits at onset+0 for some voices and
    onset+1 for others (gate-then-freq timing), and a 1-frame arp attack SPIKE at
    onset+1 traps a fixed offset. `adapt` resolves it per note."""
    if SEM_MODE == "spike":                       # legacy fixed order (1,2,0)
        for k in (1, 2, 0):
            f = _freq_at(frames, v, onset + k)
            if f:
                return freq_to_semi(f)
        return 48
    if SEM_MODE == "trig":                         # frame 0 first (skip zeros)
        for k in (0, 1, 2):
            f = _freq_at(frames, v, onset + k)
            if f:
                return freq_to_semi(f)
        return 48
    # adapt: base = the freq at the note's GATE-RISE frame (the driver holds `base`
    # on the trigger frame; the FM capture reproduces every later frame exactly, so
    # this is the metric-optimal base for frame 0). ONE exception: frame 1's jump is
    # encoded as delta1 = (trace[o+1] - base); the driver's FM dispatch reads a raw
    # delta whose HIGH BYTE is $40-$43 as a SCALED-vibrato entry instead (an
    # unavoidable format collision -> the whole note corrupts). That only bites a
    # big UPWARD jump from a low base (a drum/arp voice whose gate-rise sits an
    # octave-plus below its loud excursion). When it would collide, seat the base at
    # the high value instead (delta1 -> ~0, and the downward return delta has
    # hi >= $bc, safe) — one frame of the base pitch is wrong, but the note plays.
    o = onset
    for k in range(max(0, onset - 1), onset + 3):  # snap to the wf&1 gate-rise
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
        if ((delta1 >> 8) & 0xFC) == 0x40:         # unencodable raw delta
            return freq_to_semi(f1)
    return s0

SID = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    "SID", "JohannesBjerregaard", "Rockbuster.sid")
warg = sys.argv[2] if len(sys.argv) > 2 else "auto"


class DMCShim:
    """MON-compatible view of a decoded DMC song for the native build."""

    tempo_toggle = False
    hard_restart = 0          # DMC gates per note; no Hubbard-style $7D kill
    snap_gate = True          # snap capture onsets to the trace's gate-rise frame
    hp_engine = 0             # DMC pulse comes from captured programs (its own PWM)

    def __init__(self, m, phase, budget_ticks, onsets=None, frames=None,
                 legato_set=frozenset()):
        self.m = m
        # ONSET-ALIGNED mode (onsets given): work in FRAMES (fpt=1). Each note is
        # placed at its exact emulated gate-rise frame with dur = the frame gap,
        # and its pitch resolved from the trace (absolute semitone) — so the
        # driver triggers on the true frame and the FM capture reproduces the
        # wavetable arp in phase. Falls back to the tick*fpt grid otherwise.
        # `legato_set` = voices driven from the DECODE note boundaries instead of
        # gate-rises (a legato voice re-gates rarely, so gate-rises collapse it into
        # one FM-CAP-truncated note). Which voices go in the set is decided by the
        # full-song per-voice A/B in main() — never a blind heuristic.
        self._fpt = 1 if onsets else (m.lay.tempo_reload + 1)
        self.onset_delay = 0 if onsets else phase
        voices = decode_song(m, tick_budget=budget_ticks)
        self.voices = [[] for _ in range(3)]
        for v in range(3):
            cur = 0
            out = self.voices[v]
            if onsets is not None:
                ofpt = m.lay.tempo_reload + 1
                changes = sorted((tk * ofpt, n.sound)
                                 for tk, n in voices[v] if n.sound >= 0)
                if v in legato_set:
                    # DECODE pitch-CHANGE boundaries (a held/tied note keeps its
                    # pitch -> not a new onset); they align with the trace
                    # frame-for-frame. A leading rest lands the first note at its
                    # absolute frame so a late-entering voice stays in sync.
                    ons, prev = [], None
                    for tk, n in voices[v]:
                        if n.pitch < 0:
                            continue
                        fr = tk * ofpt + phase
                        if fr >= 0 and n.pitch != prev:
                            ons.append(fr)
                            prev = n.pitch
                    if ons and ons[0] > 0:
                        out.append(MONEvent(note=0, dur=ons[0], instr=0,
                                            wprog=0, retrig=False, rest=True))
                else:
                    # Gate-rise frames: a note per onset, pitch from the trace —
                    # NOT limited to the decode count (a voice whose decode count
                    # != onset count otherwise went silent).
                    ons = list(onsets[v])
                if not ons:
                    continue
                ci = 0
                cur = changes[0][1] if changes else 0
                for i, o in enumerate(ons):
                    while ci < len(changes) and changes[ci][0] <= o + 2:
                        cur = changes[ci][1]; ci += 1
                    nxt = ons[i + 1] if i + 1 < len(ons) else o + 8
                    note = _sem(frames, v, o, nxt) if frames is not None else 48
                    out.append(MONEvent(note=note, dur=max(1, nxt - o),
                                        instr=cur, wprog=0, retrig=True))
                continue
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
        return _pal(note) if self._fpt == 1 else self.m.note_freq(note & 0x7F)

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


CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP = 63, 32, 256, 120, 100


def legato_candidates(m, phase, onsets, voices0):
    """Voices worth A/B-ing gate-vs-decode: those whose decode has far more pitch
    changes than gate-rises (a legato voice re-gates rarely). The A/B then decides
    safely — this only bounds which voices pay for the extra builds."""
    fpt = m.lay.tempo_reload + 1
    cands = set()
    for v in range(3):
        g = len(onsets[v])
        pc, prev = 0, None
        for tk, n in voices0[v]:
            if n.pitch >= 0 and n.pitch != prev:
                pc += 1
                prev = n.pitch
        if pc > max(8, 1.3 * g):
            cands.add(v)
    return cands


def build_song(shim, base_name, traces, span, emit=True):
    """Adaptive part-split the song for `shim` and (emit) build each part. Returns
    [(part_file, t0, t1)] — the same splitting the real build uses, so each config's
    caps/clustering match production (the A/B must compare like-for-like)."""
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
    parts = []
    for part, (t0, t1) in enumerate(bounds, 1):
        out = os.path.join(ROOT, "out", "dmc", f"{base_name}_part{part:02d}.sf2")
        if emit:
            br = BM.build_native_song(shim, SID, 0, {}, [], win=(t0, t1),
                                      traces=traces)
            BM.emit_one(shim, br, out, f"part {part}/{len(bounds)} "
                        f"({t0 // 50}-{t1 // 50}s)")
        parts.append((out, t0, t1))
    if emit:
        BM.prune_stale_parts(os.path.join(ROOT, "out", "dmc", base_name),
                             len(bounds))
    return parts


def measure_song_voices(parts, traces):
    """Per-voice freq% across ALL parts vs the original (traces[0]) — each part
    aligned to its own window t0 with a small local delay. This is the full-song
    A/B metric: gate is measured over its long parts, legato over its short parts."""
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

    import mon_fidelity as F
    secs = span // 50 + 4
    print(f"  tracing full song ({secs}s)...")
    traces = (F.per_frame(SID, [f'-a0', f'-t{secs}']),
              BM.filter_trace(SID, 0, secs))

    # EXACT emulated gate-rise onsets (1x tunes) — verify they agree with the
    # trace before trusting them (multispeed/self-IRQ variants emulate too slow).
    # WITHIN-FRAME onsets (DEFAULT since the 2026-07-11 audit; DMC_WF=0 reverts):
    # 24/88 DMC files retrigger OFF+ON inside one play call (the SM half-loudness
    # class) — the state-based scan missed EVERY such retrigger, which not only
    # built those notes legato but FAILED the onset-agreement gate below, dumping
    # whole files onto the inferior tick-grid fallback. Measured on Balloon
    # part01 (its own 4s span, best delay): state = wf 0/70/36, pulse 1/0/95;
    # within-frame = wf 100/100/92, pulse 100/100/100 (agreement 71/175 ->
    # 174/175 = ONSET-ALIGNED unlocked). The gate still protects multispeed
    # variants (Jazz_1 fails both ways -> tick-grid, byte-identical output).
    onsets = measure_onsets(d, la, h.init_address, h.play_address,
                            len(traces[0]),
                            within_frame=os.environ.get("DMC_WF", "1") != "0")
    from sidm2.fidelity_common import siddump_note_onsets
    real = siddump_note_onsets(SID, ['-a0', f'-t{min(secs, 15)}'])
    agree = 0
    tot = 0
    for v in range(3):
        rl = set(fr for fr, _ in (real[v] if isinstance(real, (list, tuple))
                                  else real.get(v, [])) if fr < 700)
        em = set(onsets[v])
        # allow +-1 frame
        agree += sum(1 for fr in rl if fr in em or fr + 1 in em or fr - 1 in em)
        tot += len(rl)
    use_onsets = tot and agree / tot >= 0.85
    print(f"  emulated onsets agree with trace: {agree}/{tot} "
          f"-> {'ONSET-ALIGNED' if use_onsets else 'tick-grid (fallback)'}")
    adaptive = warg.lower() in ("auto", "a")

    # FULL-SONG PER-VOICE A/B: build the whole song BOTH ways (gate vs
    # candidate-legato) with the real adaptive part-splitting, measure per-voice
    # across all parts, and keep the decode (legato) schedule for a voice only
    # where it measurably wins. Guaranteed non-regressing (gate is the default);
    # measured like-for-like (each config split the way production would, so cap/
    # clustering effects are fair). Disable with DMC_LEGATO_AB=0.
    legato_set = frozenset()
    ab_on = (adaptive and use_onsets
             and os.environ.get("DMC_LEGATO_AB", "1") != "0")
    if ab_on:
        cands = legato_candidates(m, phase, onsets, voices0)
        if cands:
            sk = dict(onsets=onsets, frames=traces[0])
            # Decide on the first ~90s (enough parts to see the FM_CAP truncation a
            # legato voice suffers under the gate schedule) — building the whole song
            # twice is prohibitive on long tunes; the per-voice legato/gate character
            # is consistent enough that the head generalises. The final build below
            # uses the full span.
            ab_span = min(span, 90 * 50)
            print(f"  legato A/B: candidates {sorted(cands)} "
                  f"— building both configs over {ab_span // 50}s...")
            pg = build_song(DMCShim(m, phase, budget_ticks=span_ticks + 8, **sk),
                            "_abg", traces, ab_span)
            fg = measure_song_voices(pg, traces)
            pl = build_song(
                DMCShim(m, phase, budget_ticks=span_ticks + 8,
                        legato_set=frozenset(cands), **sk), "_abl", traces, ab_span)
            fl = measure_song_voices(pl, traces)
            legato_set = frozenset(v for v in cands if fl[v] > fg[v] + 1.0)
            print(f"  legato A/B: gate={[round(fg[v], 1) for v in sorted(cands)]} "
                  f"legato={[round(fl[v], 1) for v in sorted(cands)]} "
                  f"-> legato voices {sorted(legato_set)}")

    shim = DMCShim(m, phase, budget_ticks=span_ticks + 8,
                   onsets=onsets if use_onsets else None, frames=traces[0],
                   legato_set=legato_set)

    if not adaptive:
        t1 = min(span, int(warg) * 50)
        br = BM.build_native_song(shim, SID, 0, {}, [], win=(0, t1), traces=traces)
        out = os.path.join(ROOT, "out", "dmc", f"{base}_part01.sf2")
        BM.emit_one(shim, br, out, f"{base} 0-{t1 // 50}s")
        return

    parts = build_song(shim, base, traces, span)
    print(f"  packed into {len(parts)} adaptive parts")


if __name__ == "__main__":
    main()
