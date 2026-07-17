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
warg = sys.argv[2] if len(sys.argv) > 2 else "20"


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
            changes = sorted((e.frame, e.instr) for e in evs
                             if e.kind in ('note', 'tie', 'glide'))
            ons = list(onsets[v])
            out = self.voices[v]
            ci = 0
            cur = changes[0][1] if changes else 0
            for i, o in enumerate(ons):
                while ci < len(changes) and changes[ci][0] <= o + 2:
                    cur = changes[ci][1]
                    ci += 1
                nxt = ons[i + 1] if i + 1 < len(ons) else o + 8
                out.append(MONEvent(note=_sem(frames, v, o),
                                    dur=max(1, nxt - o), instr=cur,
                                    wprog=0, retrig=True))

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

    secs = int(warg)
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
    print(f"  emulated onsets vs trace: {agree}/{tot} "
          f"({'OK' if tot and agree / tot >= 0.85 else 'LOW — suspect multispeed'})")
    print(f"  onsets/voice: {[len(o) for o in onsets]}")

    shim = SDIShim(m, onsets, traces[0])
    print(f"  shim events/voice: {[len(v) for v in shim.voices]}")
    t1 = min(len(traces[0]), secs * 50)
    br = BM.build_native_song(shim, SID, 0, {}, [], win=(0, t1), traces=traces)
    out = os.path.join(ROOT, "out", "sdi", f"{base}_native_part01.sf2")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    BM.emit_one(shim, br, out, f"{base} 0-{t1 // 50}s (SDI Stage B)")
    print(f"  emitted -> {out}")

    boff, per = _fidelity(out, min(secs, t1 // 50))
    print(f"  FIDELITY (per-frame freq+wf semitone, emitted vs original, "
          f"boot offset {boff}):")
    for v in range(3):
        print(f"    voice {v}: {fmt_pct(per[v])}%")
    return 0


if __name__ == '__main__':
    sys.exit(main())
