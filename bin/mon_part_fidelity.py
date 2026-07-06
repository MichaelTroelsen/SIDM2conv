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

# infer the original SID from the part filename ("<Tune>_sub<N>..." -> <Tune>.sid)
tune = os.path.basename(part).split("_sub")[0].split("_native")[0]
orig_sid = os.path.join("SID", "Tel_Jeroen", f"{tune}.sid")
orig = F.per_frame(orig_sid, [f"-a{sub}", f"-t{(off0 // 50) + secs + 1}"])
prb = F.per_frame(probe, [f"-t{secs + 1}"])
n = min(len(orig) - off0, len(prb), secs * 50) - 4

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
print(f"{os.path.basename(part)}  {n} frames from {off0 // 50}s "
      f"(native play=$1003, engine delay={dly})\n")
print(f"  {'voice':6} {'freq%':>6} {'wf%':>6} {'pulse%':>7}")
for vi in range(3):
    keys = ("freq", "wf", "pul")
    tot = {k: 0 for k in keys}
    ok = {k: 0 for k in keys}
    for i in range(n):
        o, p = orig[off0 + i][0][vi], prb[i][0][vi]
        for k in keys:
            if o[k] is None and p[k] is None:
                continue
            tot[k] += 1
            if k == "freq":
                ok[k] += F._semi(o[k]) == F._semi(p[k])
            else:
                ok[k] += o[k] == p[k]
    def pct(k):
        return 100.0 * ok[k] / tot[k] if tot[k] else 100.0
    print(f"  osc{vi + 1:<3} {pct('freq'):6.1f} {pct('wf'):6.1f} {pct('pul'):7.1f}")
ftot = fok = 0
for i in range(n):
    o, p = orig[off0 + i][1], prb[i][1]
    if o is None and p is None:
        continue
    ftot += 1
    fok += o == p
print(f"\n  filter cutoff match: {100.0 * fok / ftot if ftot else 100:.1f}%")
