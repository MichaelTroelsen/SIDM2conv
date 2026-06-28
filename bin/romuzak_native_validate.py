"""Deterministic byte-fidelity check for the native ROMUZAK driver SF2.

Runs the native-driver SF2 in py65 (the SAME 6502 the driver runs in SF2II) AND
the original SID, both via the cycle-accurate trace, and diffs per-voice per-frame
(freq / waveform / pulse / AD-SR). Unlike bin/sf2ii_vs_real.py this needs no
real-time SF2II capture, so it's reproducible and works full-length.

  py -3 bin/romuzak_native_validate.py [SID] [seconds]

RELIABLE for FREQ/WAVEFORM/AD-SR on the melodic voices (osc1/osc2) -- deterministic
and full-length, unlike the real-time sf2ii_vs_real (whose alignment drifts past
~16s). CAVEATS (py65 != SF2II's 6510, plus per-metric alignment): the DRUM voice's
freq is hyper-sensitive to 1-frame alignment (it changes pitch every frame) so it
under-reports here -- trust sf2ii_vs_real for the drum; PULSE shows a ramp that is
correct in SHAPE but a few frames out of phase (the real player holds the base ~3
frames before ramping), so it under-reports too. Use both tools together.
"""
import math
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))

from sidm2.sid_parser import SIDParser
from sidm2 import galway_trace_extract as T
from sidm2.sf2_parser import parse_sf2_blocks
from sidm2.models import SF2DriverInfo
from scripts.sf2_to_sid import PSIDHeader


def _psid(data, load, init, play):
    h = PSIDHeader(load_address=load, init_address=init, play_address=play)
    h.songs, h.start_song = 1, 1
    return h.to_bytes() + data


def _semi(f):
    return -1 if f < 8 else max(0, min(95, round(12 * math.log2(f / 0x1167) + 48)))


def _trace(path, init, play, sub, n):
    reg = T.run_trace(path, n, init, play, sub)

    def ser(vi, fld):
        d = reg.get((vi, fld), {})
        out, cur = [], 0
        for i in range(n):
            if i in d:
                cur = d[i]
            out.append(cur)
        return out
    V = {}
    for v in range(3):
        V[v] = {
            "freq": [(ser(v, "freq_hi")[i] << 8) | ser(v, "freq_lo")[i] for i in range(n)],
            "wf": ser(v, "control"),
            "pw": [((ser(v, "pw_hi")[i] & 0xF) << 8) | ser(v, "pw_lo")[i] for i in range(n)],
            "ad": ser(v, "attack_decay"),
            "sr": ser(v, "sustain_release"),
        }
    return V


def main():
    sid = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        ROOT, "SID", "Fun_Fun", "Delirious_9_tune_1.sid")
    secs = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    n = secs * 50
    name = os.path.splitext(os.path.basename(sid))[0]
    native = os.path.join(ROOT, "out", "romuzak", name + "_native.sf2")

    h = SIDParser(sid).parse_header()
    real = _trace(sid, h.init_address, h.play_address, (h.start_song or 1) - 1, n)

    sf2 = open(native, "rb").read()
    di = SF2DriverInfo()
    la = parse_sf2_blocks(bytearray(sf2), di)
    op = os.path.join(ROOT, "out", "_native_probe.sid")
    open(op, "wb").write(_psid(sf2[2:], la, 0x1000, 0x1003))   # DRV_PLAY = $1003
    ours = _trace(op, 0x1000, 0x1003, 0, n)

    # Per-voice, per-metric best offset (+-8), gated/sounding frames only -- like
    # sf2ii_vs_real (a freq-vs-pulse offset gap = the two envelopes are phase-desynced).
    DR = range(-8, 9)

    def gated(v, i):
        return real[v]["freq"][i] > 0 and (real[v]["wf"][i] & 1)

    def best(v, cmp):
        bo, bh, bt, bd = 0, -1, 1, None
        for off in DR:
            h = t = 0
            dh = Counter()
            for i in range(n):
                j = i + off
                if 0 <= j < n and gated(v, i):
                    t += 1
                    ok, d = cmp(v, i, j)
                    h += ok
                    if d is not None:
                        dh[d] += 1
            if h > bh:
                bo, bh, bt, bd = off, h, t, dh
        return bo, bh, bt, bd

    def c_freq(v, i, j):
        d = _semi(ours[v]["freq"][j]) - _semi(real[v]["freq"][i])
        return (d == 0), d
    def c_wf(v, i, j):
        return (ours[v]["wf"][j] == real[v]["wf"][i]), None
    def c_pw(v, i, j):
        return (ours[v]["pw"][j] == real[v]["pw"][i]), None
    def c_ad(v, i, j):
        return (ours[v]["ad"][j] == real[v]["ad"][i]
                and ours[v]["sr"][j] == real[v]["sr"][i]), None

    print(f"{name}: {secs}s ({n} frames), deterministic py65 trace")
    print(f"  {'voice':5} {'freq':>16} {'waveform':>12} {'pulse':>12} {'AD/SR':>12}")
    for v in range(3):
        of, fh, ft, fdh = best(v, c_freq)
        _, wh, wt, _ = best(v, c_wf)
        _, ph, pt, _ = best(v, c_pw)
        _, ah, at, _ = best(v, c_ad)
        if ft == 0:
            print(f"  osc{v+1:<2}  (silent)")
            continue
        p = lambda h, t: f"{100*h//t}% ({h}/{t})"
        print(f"  osc{v+1:<2} {p(fh,ft):>16} {p(wh,wt):>12} {p(ph,pt):>12} {p(ah,at):>12}")
        top = [f"{d:+d}:{c}" for d, c in fdh.most_common(5) if d != 0]
        if top:
            print(f"        freq deltas (ours-real): {'  '.join(top)}")


if __name__ == "__main__":
    main()
