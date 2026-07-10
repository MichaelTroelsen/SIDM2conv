"""Scratch: measure fidelity of a NATIVE windowed part SF2 vs the original window.
Part 1 starts at song frame 0 (no leading-rest offset), so it aligns directly to
the original's first N frames. Wraps the part's SF2 bytes as a PSID (native driver
play=$1003) and compares freq(semitone)/wf/pulse/filter per voice.

Usage: py -3 bin/_verify_part.py out/mon/Hawkeye_sub0_part01.sf2 0 106
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)

import bin.mon_sf2_validate as v
import bin.mon_fidelity as F
from sidm2.sf2_parser import parse_sf2_blocks, SF2DriverInfo

part = sys.argv[1]
sub = int(sys.argv[2])
secs = int(sys.argv[3])
if secs <= 0:
    # secs=0 used to make n negative -> ALL comparison loops empty -> a
    # VACUOUS "100.0" (real, painful lesson: a silent SF2 measured perfect).
    # Default to 20s, capped below by the probe's actual length.
    secs = 20
# 4th arg = the part's start second in the original song (its window t0). The part
# plays from its own frame 0 (a leading rest positions the first note), so part frame
# k == original frame off0+k.
off0 = int(sys.argv[4]) * 50 if len(sys.argv) > 4 else 0

sf2 = bytearray(open(part, "rb").read())
info = SF2DriverInfo()
sla = parse_sf2_blocks(sf2, info)
# probe name derived from the part file: concurrent fidelity runs previously
# clobbered a single shared probe and measured each other's SF2s (near-zero
# freq/pulse with wf ~25-45% = the corrupted-probe signature)
probe = os.path.join(
    "out", f"_verify_probe_{os.path.splitext(os.path.basename(part))[0]}.sid")
open(probe, "wb").write(v._psid(bytes(sf2[2:]), sla, 0x1000, 0x1003))

# infer the original SID from the part filename ("<Tune>_sub<N>..." -> <Tune>.sid).
# strip the _partNN suffix too (Fun_Fun/Bjerregaard parts have no _sub segment).
tune = os.path.basename(part).split("_sub")[0].split("_song")[0].split("_native")[0]
if "_part" in tune:
    tune = tune.split("_part")[0]
for folder in ("Tel_Jeroen", "Hubbard_Rob", "Fun_Fun", "JohannesBjerregaard"):
    orig_sid = os.path.join("SID", folder, f"{tune}.sid")
    if os.path.exists(orig_sid):
        break
orig = F.per_frame(orig_sid, [f"-a{sub}", f"-t{(off0 // 50) + secs + 1}"])
prb = F.per_frame(probe, [f"-t{secs + 1}"])
n = min(len(orig) - off0, len(prb), secs * 50) - 4
if n <= 0:
    sys.exit(f"FIDELITY ERROR: empty comparison window (n={n}) — "
             f"orig={len(orig)} off0={off0} probe={len(prb)} secs={secs}")
# AUTO-CAP at the part's end: a windowed part covers only its own span, then the
# driver LOOPS it from the start — measuring past that compares the replayed
# beginning against later song content and fabricates a giant tail "residual"
# (Shockway part01 = 0-22s, measured at 25s -> a phantom 148-frame freq run at
# 1098+). Detect the loop restart by self-similarity: the earliest late frame
# where a 40-frame window of all-voice freqs equals the probe's own opening.
def _sig(i):
    return tuple(prb[i + j][0][v]["freq"] for j in range(40) for v in range(3))
if n > 300:
    head = _sig(2)
    for i in range(250, n - 45):
        if _sig(i) == head:
            print(f"  [note] probe loops back to its start at frame {i} — "
                  f"capping the window there (was {n} frames; the part ends "
                  f"before `secs`)")
            n = i
            break

# constant engine output delay (e.g. Supremacy writes SID registers 2 frames after
# the sequencer tick, which the native driver doesn't reproduce): align it out with
# a small freq-match search, like every other fidelity tool (mon_fidelity etc.).
def _score(d):
    s = 0
    for i in range(0, n, 2):
        for vi in range(3):
            a = orig[off0 + d + i][0][vi]["freq"]
            b = prb[i][0][vi]["freq"]
            if a and b and F._semi(a) == F._semi(b):
                s += 1
    return s
# bidirectional: a window whose boundary-continuation tick rounds off the swing
# grid can start a frame or two EARLY relative to the window label (negative
# delay) — a one-sided search mis-aligns the whole part (39% "loss" that was
# really a constant -1 shift). Constant shifts are a nuisance parameter.
dly = max(range(-4 if off0 >= 4 else -off0, 7), key=_score)
off0 += dly

# PER-VOICE delay refinement: voices can sit a frame apart from the shared delay
# (the original staggers its per-voice register writes across the play call, the
# driver writes them together). One global dly then costs a phantom ~1-2% on the
# offset voice. Refine ±2 frames per voice by freq agreement.
def _vscore(vi, extra):
    s = 0
    base = off0 + extra
    for i in range(0, n, 2):
        if 0 <= base + i < len(orig):
            a = orig[base + i][0][vi]["freq"]
            b = prb[i][0][vi]["freq"]
            if a and b and F._semi(a) == F._semi(b):
                s += 1
    return s
vdly = [max(range(-2, 3), key=lambda e, v=vi: _vscore(v, e)) for vi in range(3)]

print(f"{os.path.basename(part)}  {n} frames from {off0 // 50}s "
      f"(native play=$1003, engine delay={dly}, per-voice {vdly})\n")
print(f"  {'voice':6} {'freq%':>6} {'wf%':>6} {'pulse%':>7}   skew-tolerant (f/w/p)")
for vi in range(3):
    keys = ("freq", "wf", "pul")
    tot = {k: 0 for k in keys}
    ok = {k: 0 for k in keys}
    skew = {k: 0 for k in keys}          # mismatch that equals a ±1-frame neighbour
    o0 = off0 + vdly[vi]

    def _val(frames_row, k):
        v = frames_row[0][vi][k]
        return None if v is None else (F._semi(v) if k == "freq" else v)
    for i in range(n):
        if not (0 <= o0 + i < len(orig)):
            continue
        o, p = orig[o0 + i], prb[i]
        for k in keys:
            a, b = _val(o, k), _val(p, k)
            if a is None and b is None:
                continue
            tot[k] += 1
            if a == b:
                ok[k] += 1
                continue
            # RESIDUAL CLASSIFICATION: if the probe value matches the original one
            # frame earlier/later (a value TRANSITION landing a frame off), the
            # mismatch is 1-frame SKEW — an inaudible register-write phase artifact,
            # not a content error. Whatever remains after skew is REAL residual.
            prev = _val(orig[o0 + i - 1], k) if o0 + i - 1 >= 0 else None
            nxt = _val(orig[o0 + i + 1], k) if o0 + i + 1 < len(orig) else None
            if b is not None and (b == prev or b == nxt):
                skew[k] += 1
    def pct(k):
        return 100.0 * ok[k] / tot[k] if tot[k] else 100.0
    def spct(k):
        return 100.0 * (ok[k] + skew[k]) / tot[k] if tot[k] else 100.0
    print(f"  osc{vi + 1:<3} {pct('freq'):6.1f} {pct('wf'):6.1f} {pct('pul'):7.1f}"
          f"   ({spct('freq'):5.1f}/{spct('wf'):5.1f}/{spct('pul'):5.1f})")
    # MISMATCH CLUSTERS: where the real residual lives. For any register under
    # 99.5% strict, compress its mismatch frames into runs and show the top 3 —
    # a cluster at a note onset = capture/base problem there; a long sustained
    # run = a wrong program; scattered singletons = timing jitter.
    for k in keys:
        if pct(k) >= 99.5 or not tot[k]:
            continue
        miss = []
        for i in range(n):
            if not (0 <= o0 + i < len(orig)):
                continue
            a, b = _val(orig[o0 + i], k), _val(prb[i], k)
            if (a is None and b is None) or a == b:
                continue
            miss.append(i)
        runs, s = [], None
        for j, f in enumerate(miss):
            if s is None:
                s = f
            if j + 1 == len(miss) or miss[j + 1] > f + 3:   # gap>3 ends a run
                runs.append((s, f))
                s = None
        runs.sort(key=lambda r: r[0] - r[1])                 # longest first
        top = "  ".join(f"{a}-{b}({b - a + 1}f)" for a, b in runs[:3])
        print(f"        {k:4} residual: {len(miss)}f in {len(runs)} runs; "
              f"top: {top}")
ftot = fok = 0
for i in range(n):
    o, p = orig[off0 + i][1], prb[i][1]
    if o is None and p is None:
        continue
    ftot += 1
    fok += o == p
print(f"\n  filter cutoff match: {100.0 * fok / ftot if ftot else 100:.1f}%")
