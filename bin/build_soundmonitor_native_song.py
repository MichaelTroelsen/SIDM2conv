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
from sidm2.fidelity_common import freq_to_semi, score_pct
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
            streams[v].append((fr, kind, note, instr, arp))
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
    freerun_pulse = 1         # SM's triangle PWM is PERIODIC: allow_loop captures
                              # one cycle + LOOP (exact forever) instead of a
                              # capped capture that FREEZES mid-sweep on long
                              # notes (the audible pulse residual)
    pulse_loop = 1            # compile the driver's $7f+byte1 LOOP path (it is
                              # HARD_RESTART-gated otherwise, and SM is not HR)
    pulse_tie = 1             # SM's note-set re-inits the PW base (rec[4]) on
                              # EVERY note incl. legato -> tie events restart
                              # the pulse program too (each tie's own captured
                              # segment plays; no cross-chain freeze)
    sid_model = 6581          # per the HVSC flag (user-confirmed 6581)
    # THE INSTRUMENT-CAP OPTIMIZER (user directive 2026-07-11): SM's per-note
    # wave captures manufacture artificial instrument variety (Dance part 1:
    # 10 source instruments -> 31 slots). Two guarded transforms collapse it:
    wave_canon = 1 if os.environ.get('SM_WCANON', '1') != '0' else 0
                              # first-row boundary-bleed normalization (a
                              # 1-frame class; kill-switch SM_WCANON=0)
    release_wf = 1 if os.environ.get('SM_RELWF', '1') != '0' else 0
                              # rec[8] release tails -> gate-off rows + the
                              # driver's RELEASE_WF feature (SM_RELWF=0 off)
    pulse_canon = 1 if os.environ.get('SM_PCANON', '1') != '0' else 0
                              # canonical-pulse substitution (the non-HR path
                              # is UNROLL-GUARDED = lossless): SM's PWM
                              # restarts per note (PULSE_TIE), so shorter
                              # notes' captures are exact prefixes of the
                              # canonical — without this every duration is a
                              # distinct program and the (FM,pulse) bundle
                              # channel explodes (Dance binds on bundles
                              # 62-63/63 in every window). SM_PCANON=0 off.
    fm_loop = 1 if os.environ.get('SM_FMLOOP', '1') != '0' else 0
                              # periodic FM tails (constant-depth vibrato) on
                              # notes longer than FM_CAP loop instead of
                              # freezing at the capture cap (guarded exact;
                              # SM_FMLOOP=0 off)
    filter_tie = 1 if os.environ.get('SM_FTIE', '1') != '0' else 0
                              # SM restarts the cutoff envelope on EVERY
                              # note-set of the routed voice incl. legato ->
                              # tie events are filter-drive-eligible in the
                              # engine, and the shim adds same-pitch ties at
                              # observed cutoff re-attacks so each restart has
                              # a row to fire from (SM_FTIE=0 off)

    def __init__(self, m, streams, span, onsets=None, frames=None,
                 legato_set=frozenset(), phase=0, filt_resplit=None):
        self.m = m
        # STEP-GRID mode: SM's step is (speed+1) frames and every emulated
        # gate-rise lands on that grid at one residue (measured: all ~ 1 mod 3
        # across the corpus). Running the driver at TEMPO=speed (fpt frames/row)
        # instead of TEMPO=1 stores 1/3 the sequence rows -> the per-window
        # byte/event caps go 3x further (fewer parts) and the editor shows
        # notes densely (one musical step per row). Falls back to fpt=1 when
        # the grid isn't clean (mixed speeds, e.g. Dreamix's speed-3 row).
        from collections import Counter
        speeds = Counter(hdr['speed'] for _, hdr in m.row_chain())
        fpt = speeds.most_common(1)[0][0] + 1
        self._fpt = 1
        self.onset_delay = 0
        self.voices = [[] for _ in range(3)]
        prep = []
        # STRUCTURAL ARPS (the bundle lever): SM's chord arps are 8-step
        # semitone tables from the row headers, cycled 1 step/frame and reset
        # at the note-set — expressible EXACTLY as a looping SEMITONE FM
        # program (pitch-independent, one program per chord shape) instead of
        # a per-note Hz unroll. Dedup the tables -> wprog ids; _arp_fm_for
        # emits the program and the engine's semitone-grid guard accepts or
        # falls back per note. SM_ARP=0 kill-switch.
        self._arps = []
        arp_ids = {}
        for v in range(3):
            out = self.voices[v]
            notes = [(fr, note, instr, arp)
                     for fr, kind, note, instr, arp in streams[v]
                     if kind in ('note', 'legato')]
            changes = []
            for fr, note, instr, arp in notes:
                w = 0
                if arp is not None and any(arp):
                    if arp not in arp_ids:
                        arp_ids[arp] = len(self._arps) + 1
                        self._arps.append(arp)
                    w = arp_ids[arp]
                changes.append((fr, instr, w))
            tie_set = set()
            if v in legato_set:
                # decode-driven: one note per PITCH CHANGE at its decode frame
                # (aligned by `phase`) — the schedule for voices whose gated
                # release waveform makes gate-rises collapse the whole voice.
                ons, prev = [], None
                for fr, note, instr, arp in notes:
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
                for fr, note, instr, arp in notes:  # ascending frames
                    f = fr + phase
                    while gi < len(gates) and gates[gi] <= f:
                        last_evt = gates[gi]
                        gi += 1
                    # split margin: decode boundaries arrive every ~12-30
                    # frames, so a threshold of FM_CAP left events up to ~280
                    # frames — the tail past the 256-frame FM capture FROZE
                    # (Dance's glides). Split at FM_CAP-40 so events stay
                    # under the capture window.
                    if (f >= 0 and note != prev and f not in gate_near
                            and f - last_evt >= BM.FM_CAP - 40):
                        tie_set.add(f)
                        last_evt = f
                    prev = note
                # FILTER TIES (the instrument-cap optimizer's filter prong):
                # SM restarts its cutoff envelope on EVERY note-set of the
                # filter-routed voice — including same-pitch legato sets,
                # which produce no row at all above. Without a row, each
                # re-attack stays embedded in the previous drive's captured
                # filter program, so every drive gets a DISTINCT program
                # (Dance part 8: 15 programs / 247 rows / 32 slots). Add a
                # same-pitch TIE at each decode note-set that coincides with
                # an observed cutoff re-attack (±2 frames): the row lets the
                # driver restart the canonical envelope there; the per-drive
                # exactness guard keeps everything else byte-identical.
                if self.filter_tie and filt_resplit:
                    # filt_resplit: {attack_frame: routed voice AT that frame}
                    # — SM switches routing per section, so credit per frame
                    for fr, note, instr, arp in notes:
                        f = fr + phase
                        if (f >= 0 and f not in gate_near and f not in tie_set
                                and any(filt_resplit.get(f + d) == v
                                        for d in (-2, -1, 0, 1, 2))):
                            tie_set.add(f)
                ons = sorted(set(ons) | tie_set)
            prep.append((v, out, ons, tie_set, changes))

        # GRID SELECTION over ALL voices' events: pick the COARSEST grid
        # (multiples of the step) where every GATE shares one residue and
        # every TIE lands within +-1 frame of it (a >1-frame tie snap
        # regressed the tie-heavy files hard — Final_Luv pulse 100 -> 8).
        # Coarser grids = tighter editor rows (Poppy_Road's notes are all on
        # a 12-frame musical grid -> 1 row per 4 steps).
        if (onsets is not None and len(speeds) == 1 and fpt > 1
                and os.environ.get('SM_GRID', '1') != '0'):
            gate_frames = [f for v in range(3) for f in onsets[v]]
            tie_frames = [f for _, _, ons, ties, _ in prep for f in ties]
            for mult in (4, 2, 1):
                g = fpt * mult
                res = Counter(f % g for f in gate_frames)
                if len(res) != 1:
                    continue
                r = res.most_common(1)[0][0]
                if all(min((f - r) % g, g - ((f - r) % g)) <= 1
                       for f in tie_frames):
                    self.onset_delay = r
                    self._fpt = g
                    break

        for v, out, ons, tie_set, changes in prep:
            if not ons:
                continue
            # events carry (tick, frame): ticks drive durations/rows on the
            # step grid; frames drive trace-resolved pitch (_sem). Tie frames
            # can sit 1 off the gate grid -> snap by rounding.
            fpt_, dly = self._fpt, self.onset_delay
            evs, seen = [], set()
            for f in ons:
                t = max(0, round((f - dly) / fpt_)) if fpt_ > 1 else f
                if t not in seen:
                    seen.add(t)
                    evs.append((t, f))
            span_t = span // fpt_ if fpt_ > 1 else span
            if evs[0][0] > 0:
                out.append(MONEvent(note=0, dur=evs[0][0], instr=0,
                                    wprog=0, retrig=False, rest=True))
            ci = 0
            cur = changes[0][1] if changes else 0
            cur_w = changes[0][2] if changes else 0
            tail = max(1, 8 // fpt_)
            for i, (t, o) in enumerate(evs):
                while ci < len(changes) and changes[ci][0] + phase <= o + 2:
                    cur = changes[ci][1]
                    cur_w = changes[ci][2]
                    ci += 1
                nxt = evs[i + 1][0] if i + 1 < len(evs) else min(t + tail, span_t)
                note = _sem(frames, v, o) if frames is not None else 48
                tie = o in tie_set
                out.append(MONEvent(note=note, dur=max(1, nxt - t),
                                    instr=cur, wprog=cur_w, retrig=not tie,
                                    tie=tie))

    @property
    def frames_per_tick(self):
        return self._fpt

    def tick_to_frame(self, ticks):
        return ticks * self._fpt

    def frame_to_tick(self, frame):
        # MUST invert tick_to_frame on the grid: the engine computes each
        # part's lead rest rows as first_tick - frame_to_tick(window_start);
        # the old identity version made lead NEGATIVE (clamped 0) for every
        # grid part >= 2, so ALL VOICES started their first in-window note at
        # row 0 — a per-voice inter-voice DESYNC of up to the first-note
        # offsets (Dance part05 measured v0 freq 28.7 vs v1 97 at one global
        # delay). round matches the event-tick snapping.
        return max(0, round(frame / self._fpt))

    def _voice_blocks(self, v):
        return [(0, self.voices[v])] if self.voices[v] else []

    # STRUCTURAL ARPS: expose the deduped row-header chord tables via the
    # engine's MoN-style interface (_arp_fm_for). SM cycles 8 semitone
    # offsets at 1 step/frame ('dur' 0 -> fps 1), reset at the note-set ->
    # a looping SEMITONE program is exact by construction (the driver looks
    # up the same freq table the engine indexes). tbl_arp_idx nonzero passes
    # the engine's gate; arp_struct enables it without MON_ARP_STRUCT.
    arp_struct = 1 if os.environ.get('SM_ARP', '1') != '0' else 0
    tbl_arp_idx = 1

    def arp_program(self, wprog):
        if not wprog or wprog > len(self._arps):
            return None
        return {'dur': 0, 'steps': list(self._arps[wprog - 1]), 'loop': True}

    def note_freq(self, note):
        return _pal(note)

    def instrument(self, idx):
        rec = self.m.sound(idx)
        return {'ad': rec[1], 'sr': rec[2],
                'waveform': rec[0] or 0x41,   # hint; real wf captured per-frame
                'release_wf': rec[8],         # REST writes this to $D404 — the
                                              # duration-positioned tail byte
                                              # (drives the RELEASE_WF split)
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
    # GRID-ALIGN interior part boundaries: an arbitrary t0 makes the engine's
    # window-start tick round((t0-delay)/fpt) land up to ±(fpt-1)/2 frames off
    # the trace, shifting each later part's voices by DIFFERENT amounts vs the
    # global alignment (Dance part09 v1 played its drum roll 2 frames early:
    # 48% freq strict on a per-frame-alternating section). Snapping t0 to the
    # gate grid (t0 ≡ onset_delay mod fpt) makes the tick origin exact.
    fpt = shim.frames_per_tick
    dly = getattr(shim, 'onset_delay', 0)

    def align(f):
        if fpt <= 1 or f >= span:
            return f
        return max(0, f - ((f - dly) % fpt))
    bounds, t0 = [], 0
    maxp = int(os.environ.get('SM_MAX_PARTS', '0')) or 10**9
    while t0 < span and len(bounds) < maxp:
        t1 = align(min(t0 + STEP, span))
        if t1 <= t0:
            t1 = min(t0 + STEP, span)
        while t1 < span and fits(t0, align(min(t1 + STEP, span))):
            nxt = align(min(t1 + STEP, span))
            t1 = nxt if nxt > t1 else min(t1 + STEP, span)
        bounds.append((t0, t1))
        t0 = t1
    parts = []
    for part, (t0, t1) in enumerate(bounds, 1):
        out = os.path.join(ROOT, "out", "soundmonitor",
                           f"{base_name}_part{part:02d}.sf2")
        if emit:
            br = BM.build_native_song(shim, SID, 0, {}, [], win=(t0, t1),
                                      traces=traces)
            # exact FRAME bounds in the label: grid-aligned bounds are no
            # longer 2s multiples, and a sweep that reconstructs t0 from the
            # rounded seconds lands frames off (strict scores collapse on
            # grid content). _opt_sweep_corpus parses the f-form.
            BM.emit_one(shim, br, out, f"part {part}/{len(bounds)} "
                        f"({t0 // 50}-{t1 // 50}s, {t0}-{t1}f)")
        parts.append((out, t0, t1))
    if emit:
        BM.prune_stale_parts(os.path.join(ROOT, "out", "soundmonitor",
                                          base_name), len(bounds))
    return parts


def _r(p):
    """Round a score for display; None (no evidence) stays visibly 'n/a'."""
    return round(p, 1) if p is not None else "n/a"


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
    # None for a voice with no comparable frames — NOT 100.0. See
    # sidm2.fidelity_common.score_pct: an empty comparison is "no test ran".
    return [score_pct(ok[v], tot[v]) for v in range(3)]


def find_phase(streams, onsets):
    """Align the decode frame clock to the emulated gate-rises (the decode's
    first step is nominally frame 0; emulation places it a couple of frames
    later)."""
    dec = [set(fr for fr, kind, _, _, _ in streams[v] if kind == 'note')
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
        for fr, kind, note, instr, arp in streams[v]:
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

    # within_frame: SM's note-set retriggers by writing gate OFF then ON inside
    # ONE play call — end-of-frame state stays 1, so the state-based scan (and
    # siddump!) miss EVERY such retrigger. Building those notes legato choked
    # the envelope (no re-attack -> decays to sustain and stays there): the
    # whole song rendered at HALF loudness with every register metric at 100%.
    onsets = measure_onsets(d, la, h.init_address, h.play_address,
                            min(span, len(traces[0])), within_frame=True)
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

    # FILTER-TIE resplit input: every observed cutoff re-attack frame (fast
    # $D416 jump — BM.FILT_FAST, same threshold as drive detection) mapped to
    # the voice the $D417 routing bits credit AT that frame (SM switches
    # filter routing per section). The shim adds same-pitch ties at note-sets
    # that coincide, so the driver can restart the canonical envelope there.
    ftr = traces[1]
    resplit = {f: {1: 0, 2: 1, 4: 2}.get(ftr[f][1] & 0x07)
               for f in range(1, len(ftr))
               if abs(ftr[f][0] - ftr[f - 1][0]) >= BM.FILT_FAST}
    if resplit:
        print(f"  filter: {len(resplit)} re-attack frames "
              f"(routing-credited per frame)")

    legato_set = frozenset()
    ab_on = (adaptive and use_onsets
             and os.environ.get("SM_LEGATO_AB", "1") != "0")
    if ab_on:
        cands = legato_candidates(streams, onsets)
        if cands:
            sk = dict(onsets=onsets, frames=traces[0], phase=phase,
                      filt_resplit=resplit)
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
            # A voice with no comparable frames scores None on BOTH sides: the
            # A/B is INCONCLUSIVE for it, so it keeps the default (gate). Same
            # outcome as before, but now it is a decision rather than an artifact
            # of two fabricated 100.0s comparing equal — and it is visible.
            legato_set = frozenset(
                v for v in cands
                if fl[v] is not None and fg[v] is not None and fl[v] > fg[v] + 1.0)
            _ab = [v for v in sorted(cands) if fl[v] is None or fg[v] is None]
            print(f"  legato A/B: gate={[_r(fg[v]) for v in sorted(cands)]} "
                  f"legato={[_r(fl[v]) for v in sorted(cands)]} "
                  f"-> legato voices {sorted(legato_set)}"
                  + (f"  (no data, kept gate: {_ab})" if _ab else ""))

    shim = SMShim(m, streams, span, onsets=onsets if use_onsets else None,
                  frames=traces[0], legato_set=legato_set, phase=phase,
                  filt_resplit=resplit)

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
