"""Per-frame timbre fidelity metric for the MoN Stage-A/B SF2 vs the original SID.

Converts the tune to SF2, wraps it as a PSID probe, siddumps BOTH the probe and the
original, fill-forwards every SID register to a full per-frame state, aligns the constant
Driver-11 boot offset, and reports per-voice % match for waveform / pulse / filter (and
freq-by-nearest-semitone) within one song length. This is the fast headless loop for
Stage-B work (no GUI), complementing bin/mon_sf2_validate.py (note onsets only).

  py -3 bin/mon_fidelity.py                 # Hawkeye subtune 3
  py -3 bin/mon_fidelity.py path.sid SUB SECONDS
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import bin.mon_sf2_validate as v   # build_probe, _psid
from sidm2.fidelity_common import siddump_per_frame as per_frame  # noqa: F401 (re-exported)
from sidm2.fidelity_common import freq_to_semi as _semi           # noqa: F401 (re-exported)
from sidm2.fidelity_common import score_pct, fmt_pct              # noqa: F401 (re-exported)


def main():
    os.chdir(ROOT)
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join('SID', 'Tel_Jeroen', 'Hawkeye.sid')
    sub = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    secs = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    os.makedirs('out', exist_ok=True)
    probe = os.path.join('out', '_mon_fid_probe.sid')
    open(probe, 'wb').write(v.build_probe(path, sub))
    orig = per_frame(path, [f'-a{sub}', f'-t{secs + 1}'])
    prb = per_frame(probe, [f'-t{secs + 2}'])

    # align the constant Driver-11 boot offset by maximizing freq-semitone agreement
    def score(off):
        m = min(len(orig), len(prb) - off, secs * 50)
        s = 0
        for i in range(m):
            for vi in range(3):
                a, b = orig[i][0][vi]['freq'], prb[i + off][0][vi]['freq']
                if a and b and _semi(a) == _semi(b):
                    s += 1
        return s
    off = max(range(0, 12), key=score)
    n = min(len(orig), len(prb) - off, secs * 50)
    print(f"{os.path.basename(path)} subtune {sub}  boot offset={off}  {n} frames\n")

    reg_keys = ('freq', 'wf', 'pul')
    print(f"  {'voice':6} {'freq%':>6} {'wf%':>6} {'pulse%':>7}")
    for vi in range(3):
        tot = {k: 0 for k in reg_keys}
        ok = {k: 0 for k in reg_keys}
        for i in range(n):
            o = orig[i][0][vi]
            p = prb[i + off][0][vi]
            for k in reg_keys:
                if o[k] is None and p[k] is None:
                    continue
                tot[k] += 1
                if k == 'freq':
                    if _semi(o[k]) == _semi(p[k]):
                        ok[k] += 1
                elif o[k] == p[k]:
                    ok[k] += 1
        def pct(k):
            # None when nothing was comparable — see fidelity_common.score_pct.
            return score_pct(ok[k], tot[k])
        print(f"  osc{vi + 1:<3} {fmt_pct(pct('freq'), 6)} {fmt_pct(pct('wf'), 6)}"
              f" {fmt_pct(pct('pul'), 7)}")
    # global filter
    ftot = fok = 0
    for i in range(n):
        o = orig[i][1]
        p = prb[i + off][1]
        if o is None and p is None:
            continue
        ftot += 1
        if o == p:
            fok += 1
    _f = score_pct(fok, ftot)
    print(f"\n  filter cutoff match: "
          + (f"{_f:.1f}%" if _f is not None
             else "n/a (no filter data — the tune never writes cutoff)"))
    return 0


if __name__ == '__main__':
    sys.exit(main())
