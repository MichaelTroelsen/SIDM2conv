"""GUI-confirm a Hawkeye/MoN native-driver part in the REAL SF2II: run the
instrumented SF2II_dbg (argv-load + auto-play), capture its actual per-frame SID
output, and compare freq(semitone)/waveform/pulse/FILTER-cutoff to the original
Hawkeye over the matching window. Confirms the part LOADS and PLAYS in SF2II's own
6510 engine (not just the headless py65 probe).

  py -3 bin/mon_sf2ii_confirm.py out/mon/Hawkeye_sub0_partNN.sf2 SUB SECS [START_SEC]
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)
from bin.sf2ii_vs_real import capture_sf2ii
import bin.mon_fidelity as F

part = sys.argv[1]
sub = int(sys.argv[2])
secs = int(sys.argv[3])
off0 = int(sys.argv[4]) * 50 if len(sys.argv) > 4 else 0

print(f"capturing {secs}s of REAL SF2II playback of {os.path.basename(part)} ...")
ours = capture_sf2ii(part, secs + 3)
if not ours:
    print("  FAIL: no SIDFR frames captured -> SF2II did NOT load/play the part")
    sys.exit(1)
print(f"  captured {len(ours)} SF2II frames (loaded + ran)")

tune = os.path.basename(part).split("_sub")[0].split("_song")[0].split("_native")[0]
for _folder in ("Tel_Jeroen", "Hubbard_Rob"):
    _cand = os.path.join("SID", _folder, f"{tune}.sid")
    if os.path.exists(_cand):
        break
orig = F.per_frame(_cand, [f"-a{sub}", f"-t{(off0 // 50) + secs + 2}"])


def ov(b, v):
    base = 7 * v
    return {"freq": b[base] | (b[base + 1] << 8), "wf": b[base + 4],
            "pul": b[base + 2] | ((b[base + 3] & 0xF) << 8)}


def ocut(b):
    return (b[22] << 3) | (b[21] & 7)


have = sorted(ours)


def score(offg):
    s = 0
    for f in have:
        sf = f - offg
        if sf < 0 or off0 + sf >= len(orig):
            continue
        for v in range(3):
            a, b = orig[off0 + sf][0][v]["freq"], ov(ours[f], v)["freq"]
            if a and b and F._semi(a) == F._semi(b):
                s += 1
    return s


offg = max(range(0, 400), key=score)
fr = [f for f in have if 0 <= f - offg and off0 + (f - offg) < len(orig)][:secs * 50]
silent = all(ov(ours[f], v)["freq"] == 0 for f in fr for v in range(3))
if silent:
    print("  FAIL: SF2II output is silent (all voices freq 0)")
    sys.exit(1)
print(f"  aligned at dbg->song offset {offg}; {len(fr)} comparable frames\n")
print(f"  {'voice':6} {'freq%':>6} {'wf%':>6} {'pulse%':>7}")
for v in range(3):
    keys = ("freq", "wf", "pul")
    tot = {k: 0 for k in keys}
    ok = {k: 0 for k in keys}
    for f in fr:
        o = orig[off0 + (f - offg)][0][v]
        p = ov(ours[f], v)
        for k in keys:
            tot[k] += 1
            if k == "freq":
                ok[k] += F._semi(o[k] or 0) == F._semi(p["freq"])
            elif k == "wf":
                ok[k] += (o["wf"] or 0) == p["wf"]
            else:
                ok[k] += (o["pul"] or 0) == p["pul"]

    def pct(k):
        # None when nothing was comparable — see fidelity_common.score_pct.
        return F.score_pct(ok[k], tot[k])
    print(f"  osc{v + 1:<3} {F.fmt_pct(pct('freq'), 6)} {F.fmt_pct(pct('wf'), 6)}"
          f" {F.fmt_pct(pct('pul'), 7)}")
ftot = fok = 0
for f in fr:
    oc = orig[off0 + (f - offg)][1]
    if oc is None:
        continue
    ftot += 1
    fok += oc == ocut(ours[f])
_f = F.score_pct(fok, ftot)
print(f"\n  filter cutoff match: "
      + (f"{_f:.1f}%" if _f is not None
         else "n/a (no filter data — the tune never writes cutoff)"))
print("\n  RESULT: part LOADS and PLAYS in real SF2II.")
