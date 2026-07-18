"""SID Duzz' It (SDI, Gallefoss/Tjelta) -> native SF2 (Stage B) — FIRST CUT.

Trace-driven shim into bin/build_mon_native_song's build_native_song, exactly
like the DMC/Sound-Monitor builders: notes are placed at the EMULATED $D404
gate-rise frames (sidm2.dmc_parser.measure_onsets, player-agnostic), each note's
base pitch is resolved from the trace, and the engine CAPTURES every per-frame
freq / waveform / pulse / filter. So the per-frame WFPRG ARPEGGIOS that cap SDI
Stage A at strict ~50 (see docs/players/SDI.md — the E/DELTA/V pitch ceiling)
come out byte-exact without the offline decoder modelling them.

STATUS: first cut. Onset-aligned single-window build + an inline per-frame
freq+wf fidelity read vs the original (never emit blind). Variant E exemplar
(2_Young_2_Die). The C class writes $D404=$08 (TEST) as its hard-restart — its
gate model needs care before trusting C here; start with E/DELTA (no TEST).

  py -3 bin/build_sdi_native_song.py SID/Gallefoss_Glenn/2_Young_2_Die.sid [secs]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)

from sidm2.mon_parser import MONEvent                                  # noqa: E402
from sidm2.sdi_parser import load_sid, SDIModule                       # noqa: E402
from sidm2.dmc_parser import measure_onsets                            # noqa: E402
from sidm2.sid_player import FREQ_TABLE_LO, FREQ_TABLE_HI              # noqa: E402
from sidm2.fidelity_common import (                                    # noqa: E402
    freq_to_semi, siddump_per_frame, siddump_note_onsets, psid_wrap,
    score_pct, fmt_pct)
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo           # noqa: E402
from sdi_to_sf2 import instrument_adsr                                 # noqa: E402
import build_mon_native_song as BM                                     # noqa: E402

SID = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    "SID", "Gallefoss_Glenn", "2_Young_2_Die.sid")
warg = sys.argv[2] if len(sys.argv) > 2 else "auto"

CAP_B, CAP_I, CAP_TBL, CAP_SEG, STEP = 63, 32, 256, 120, 100   # 2s probe step


def _pal(note):
    n = max(0, min(95, note))
    return FREQ_TABLE_LO[n] | (FREQ_TABLE_HI[n] << 8)


def _freq_at(frames, v, idx):
    return frames[idx][0][v]['freq'] if 0 <= idx < len(frames) else 0


def _sem(frames, v, onset):
    """Base semitone = the original's freq at the note's gate-rise frame (frame 0
    holds `base`; the FM capture reproduces frames 1+). Snap to the wf&1 gate
    rise in onset..onset+2, and guard the FM $40-$43 raw-delta collision by
    seating the base high when frame 1's jump would collide (the DMC builder's
    _sem, adapt mode)."""
    o = onset
    for k in range(max(0, onset - 1), onset + 3):
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
        if ((delta1 >> 8) & 0xFC) == 0x40:
            return freq_to_semi(f1)
    return s0


class SDIShim:
    """MON-compatible, onset-aligned view of a decoded SDI song (fpt=1, notes at
    trace gate-rises, pitch from the trace, per-frame timbre captured)."""

    tempo_toggle = False
    hard_restart = 0          # E/DELTA gate per note; the C-class $D404=$08 TEST
                              # path is NOT handled here yet (see docstring)
    snap_gate = True
    hp_engine = 0             # SDI pulse comes from captured programs

    def __init__(self, m, onsets, frames):
        self.m = m
        self._fpt = 1
        self.onset_delay = 0
        self._onset_mode = True
        self.voices = [[] for _ in range(3)]
        for v in range(3):
            # instrument-change schedule from the offline decode (which sound is
            # active at each frame); the onset FRAMES + pitch come from the trace.
            evs = m.decode_voice(v)
            notes = [e for e in evs if e.kind in ('note', 'tie', 'glide')]
            changes = sorted((e.frame, e.instr) for e in notes)
            # LEGATO voices (DELTA/E's tie engine): the note re-gates rarely, so
            # measure_onsets (gate-rise detection) collapses the whole voice into
            # ~1 note (Delta_Slow v2: 1 gate-rise, but the real voice GLIDES to a
            # new pitch every ~5 frames under one held gate). The decode marks the
            # pitch changes but on a UNIFORM tick grid that drifts from the real
            # (non-uniform 4/5/5 segment) lengths. So drive legato voices from the
            # TRACE's own pitch-change frames -- drift-free and exactly the
            # trace-driven placement Stage B is built on -- with TIES (retrig
            # False) so the envelope never re-attacks (the real waveform stays
            # $41). Voices whose gate-rises keep up with the decode stay on them.
            gate = list(onsets[v])
            # LEGATO only for voices that essentially NEVER re-gate (Delta_Slow v2
            # = ONE gate-rise for the whole song, but glides constantly). A voice
            # that re-gates REGULARLY -- even a fast per-frame arp that decodes to
            # far more note events than gate-rises (Moi_Funk v1: 46 gates, ~100
            # decode notes) -- must stay on the GATE-RISE path: one note per gate,
            # the FM capture reproduces the arp between gates. The old
            # `gate < 0.5*notes` test caught those arp voices and fragmented them
            # into 1-frame ties the capture can't restart every frame (37%).
            legato = len(notes) > 8 and len(gate) <= max(2, len(notes) // 20)
            if legato:
                start = gate[0] if gate else 2
                ons, prev = [], None
                for f in range(start, len(frames)):
                    s = freq_to_semi(frames[f][0][v]['freq'])
                    if s >= 0 and s != prev:
                        ons.append(f)
                        prev = s
            else:
                ons = gate
            out = self.voices[v]
            # LEADING REST for a late-entering voice: events are placed
            # sequentially by duration, so without a rest of `ons[0]` frames the
            # whole voice is shifted EARLY by its first-onset frame. Negligible
            # when a voice starts at frame ~0, but catastrophic for a voice that
            # enters late (Bahbar v2's first gate is frame 769 — it was playing
            # 769 frames early, 0% on every part past the first).
            if ons and ons[0] > 0:
                out.append(MONEvent(note=0, dur=ons[0], instr=0,
                                    wprog=0, retrig=False, rest=True))
            # A voice's LAST note holds until the voice actually goes silent, not
            # a fixed +8. Neurotica_short's voices re-gate through frame 1873 then
            # SUSTAIN a held tail to ~3499 (last active frame); cutting the last
            # note to 8 frames left ~1600 frames emit-silent while the original
            # sustained (part 4 tanked to ~30%). Scan the trace forward from the
            # last onset while the voice's waveform stays active.
            def sustain_end(o):
                f = o
                while f + 1 < len(frames) and (frames[f + 1][0][v]['wf'] or 0):
                    f += 1
                return max(o + 8, f + 1)
            ci = 0
            cur = changes[0][1] if changes else 0
            for i, o in enumerate(ons):
                while ci < len(changes) and changes[ci][0] <= o + 2:
                    cur = changes[ci][1]
                    ci += 1
                nxt = ons[i + 1] if i + 1 < len(ons) else sustain_end(o)
                # A legato voice re-gates once and then GLIDES (real waveform
                # stays $41); emit TIES after the first note so the envelope
                # doesn't re-attack (matching the trace) while each segment still
                # gets its own in-cap FM capture of that portion of the glide.
                # (One sustained note freezes at FM_CAP; retrig re-gates wrong.)
                tie = legato and i > 0
                out.append(MONEvent(note=_sem(frames, v, o),
                                    dur=max(1, nxt - o), instr=cur,
                                    wprog=0, retrig=not tie, tie=tie))

    @property
    def frames_per_tick(self):
        return self._fpt

    def tick_to_frame(self, ticks):
        return ticks

    def frame_to_tick(self, frame):
        return max(0, frame)

    def _voice_blocks(self, v):
        return [(0, self.voices[v])] if self.voices[v] else []

    def note_freq(self, note):
        return _pal(note)                 # onset mode: notes are PAL semitones

    def instrument(self, idx):
        ad, sr = instrument_adsr(self.m, idx)
        return {'ad': ad, 'sr': sr if sr else 0xF9, 'waveform': 0x41,
                'pw': 0x800, 'pulseval': 0, 'fx': 0,
                'wave_prog': 0, 'flags': 0, 'raw': []}


def build_song(shim, base, traces, span):
    """Adaptive part-split so no window exceeds the caps (the 63-bundle warning
    on long songs). Copied from the DMC/SM builders. Returns [(file, t0, t1)]."""
    def fits(t0, t1):
        nb, ni, nw, nf, ns = BM.build_native_song(
            shim, SID, 0, {}, [], win=(t0, t1), traces=traces, count_only=True)
        return (nb <= CAP_B and ni <= CAP_I and nw <= CAP_TBL
                and nf <= CAP_TBL and ns <= CAP_SEG)
    bounds, t0 = [], 0
    while t0 < span:
        t1 = min(t0 + STEP, span)
        while t1 < span and fits(t0, min(t1 + STEP, span)):
            t1 = min(t1 + STEP, span)
        bounds.append((t0, t1))
        t0 = t1
    parts = []
    for part, (t0, t1) in enumerate(bounds, 1):
        out = os.path.join(ROOT, "out", "sdi", f"{base}_native_part{part:02d}.sf2")
        br = BM.build_native_song(shim, SID, 0, {}, [], win=(t0, t1), traces=traces)
        BM.emit_one(shim, br, out, f"part {part}/{len(bounds)} "
                    f"({t0 // 50}-{t1 // 50}s) SDI Stage B")
        parts.append((out, t0, t1))
    BM.prune_stale_parts(os.path.join(ROOT, "out", "sdi", base), len(bounds))
    return parts


def measure_parts(parts, orig):
    """Per-voice freq+wf semitone agreement across ALL parts vs the original
    (`orig` = the full per-frame trace). Each part covers original frames
    [t0,t1); trace the part SF2 from its own frame 0, fit a small local boot
    offset, and compare its window to orig[t0:t1]."""
    ok = [0, 0, 0]
    tot = [0, 0, 0]
    for pf, t0, t1 in parts:
        sf2 = open(pf, 'rb').read()
        info = SF2DriverInfo()
        sla = parse_sf2_blocks(sf2, info)
        probe = pf[:-4] + ".sid"
        open(probe, 'wb').write(psid_wrap(sf2[2:], sla, 0x1000, 0x1003))
        dur = (t1 - t0) // 50 + 2
        b = siddump_per_frame(probe, ['-a0', f'-t{dur}'])

        def sc(v, off):
            o = t = 0
            for i in range(t1 - t0):
                fa = orig[t0 + i][0][v]['freq'] if t0 + i < len(orig) else 0
                j = i + off
                fb = b[j][0][v]['freq'] if 0 <= j < len(b) else 0
                if not fa and not fb:
                    continue
                t += 1
                if freq_to_semi(fa) == freq_to_semi(fb):
                    o += 1
            return o, t
        boff = max(range(-4, 9), key=lambda o: sum(sc(v, o)[0] for v in range(3)))
        for v in range(3):
            o, t = sc(v, boff)
            ok[v] += o
            tot[v] += t
    return [score_pct(ok[v], tot[v]) for v in range(3)]


def _fidelity(sf2_path, secs):
    """Honest inline read: per-frame freq+wf semitone agreement, emitted SF2 vs
    original, per voice. Wrap the native SF2 as a PSID and siddump both."""
    sf2 = open(sf2_path, 'rb').read()
    info = SF2DriverInfo()
    sla = parse_sf2_blocks(sf2, info)
    probe = os.path.join('out', 'sdi', '_sdi_native_probe.sid')
    open(probe, 'wb').write(psid_wrap(sf2[2:], sla, 0x1000, 0x1003))
    a = siddump_per_frame(SID, ['-a0', f'-t{secs}'])
    b = siddump_per_frame(probe, ['-a0', f'-t{secs}'])

    def score(v, off):
        ok = tot = 0
        for i in range(len(a)):
            j = i + off
            if not (0 <= j < len(b)):
                continue
            fa = a[i][0][v]['freq']
            fb = b[j][0][v]['freq']
            if not fa and not fb:
                continue
            tot += 1
            if freq_to_semi(fa) == freq_to_semi(fb):
                ok += 1
        return ok, tot

    # ONE global boot offset (the native driver boots a few frames late); fit it
    # on total agreement, then report per voice at that offset.
    best = max(range(-4, 13), key=lambda o: sum(score(v, o)[0] for v in range(3)))
    per = [score_pct(*score(v, best)) for v in range(3)]
    return best, per


def main():
    d, la, h = load_sid(SID)
    m = SDIModule(d, la)
    base = os.path.splitext(os.path.basename(SID))[0]
    print(f"{base}: la=${la:04X} variant={m.lay.variant} "
          f"init=${h.init_address:04X} play=${h.play_address:04X}")

    adaptive = warg.lower() in ("auto", "a")
    # span = the decoded song length (last onset + tail); trace that + a margin.
    dec_span = max((e.frame for v in range(3) for e in m.decode_voice(v)),
                   default=0) + 100
    secs = (dec_span // 50 + 4) if adaptive else int(warg)
    import mon_fidelity as F
    print(f"  tracing {secs}s...")
    traces = (F.per_frame(SID, ['-a0', f'-t{secs}']),
              BM.filter_trace(SID, 0, secs))
    onsets = measure_onsets(d, la, h.init_address, h.play_address,
                            len(traces[0]))

    # onset-agreement gate vs siddump (multispeed/self-IRQ emulate too slow)
    real = siddump_note_onsets(SID, ['-a0', f'-t{min(secs, 15)}'])
    agree = tot = 0
    for v in range(3):
        rl = set(fr for fr, _ in (real[v] if isinstance(real, (list, tuple))
                                  else real.get(v, [])) if fr < 700)
        em = set(onsets[v])
        agree += sum(1 for fr in rl if em & {fr - 1, fr, fr + 1})
        tot += len(rl)
    ok = bool(tot) and agree / tot >= 0.85
    print(f"  emulated onsets vs trace: {agree}/{tot} "
          f"({'OK' if ok else 'LOW — suspect multispeed/self-IRQ'})")
    print(f"  onsets/voice: {[len(o) for o in onsets]}")
    if not ok and '--force' not in sys.argv:
        # play=$0000 self-IRQ (variant V) and true multispeed can't be driven by
        # measure_onsets (the wrapper installs its own IRQ; the standard init/play
        # trace runs too slow). Emitting anyway produces a garbage SF2 with a
        # meaningless both-silent fidelity score -- refuse it (this session's
        # "builds != sounds right" rule). Those need the 2x/4x wrapper drive, a
        # separate Stage B unit. --force to probe regardless.
        print("  REFUSING to build: this file cannot be driven by measure_onsets "
              "(variant V / self-IRQ / multispeed). Needs the wrapper drive.")
        return 1

    shim = SDIShim(m, onsets, traces[0])
    print(f"  shim events/voice: {[len(v) for v in shim.voices]}")
    os.makedirs(os.path.join(ROOT, "out", "sdi"), exist_ok=True)

    if adaptive:
        span = min(len(traces[0]), dec_span)
        parts = build_song(shim, base, traces, span)
        print(f"  packed into {len(parts)} adaptive part(s)")
        per = measure_parts(parts, traces[0])
        label = "all parts vs original"
    else:
        t1 = min(len(traces[0]), secs * 50)
        br = BM.build_native_song(shim, SID, 0, {}, [], win=(0, t1), traces=traces)
        out = os.path.join(ROOT, "out", "sdi", f"{base}_native_part01.sf2")
        BM.emit_one(shim, br, out, f"{base} 0-{t1 // 50}s (SDI Stage B)")
        print(f"  emitted -> {out}")
        _boff, per = _fidelity(out, min(secs, t1 // 50))
        label = f"single window 0-{t1 // 50}s"
    print(f"  FIDELITY (per-frame freq+wf semitone, {label}):")
    for v in range(3):
        print(f"    voice {v}: {fmt_pct(per[v])}%")
    return 0


if __name__ == '__main__':
    sys.exit(main())
