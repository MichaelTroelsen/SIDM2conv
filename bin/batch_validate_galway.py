"""Batch objective SF2II validation of the whole Galway corpus. For each out/galway_sf2/
<tune>.sf2, run sf2ii_vs_real.py against the original SID and record the real-SF2II
per-voice fidelity (freq/waveform/pulse/AD-SR). Auto-detects multispeed: tries ms=1 and
retries higher (2/4/8) only if the freq match is low (legato tunes use multispeed). Prints
a corpus table + a summary count of tunes that reach >=95% freq on every gated voice.

Usage: py -3 bin/batch_validate_galway.py [seconds] [name-substr]
"""
import os, re, sys, glob, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sidm2.sid_parser import SIDParser
SUBTUNE = {"Combat_School": 1, "Yie_Ar_Kung_Fu_II": 3}   # match build_galway_corpus.py
SECS = sys.argv[1] if len(sys.argv) > 1 else "16"
FILT = sys.argv[2] if len(sys.argv) > 2 else ""
SIDD = os.path.join(ROOT, "SID", "Galway_Martin")
SF2D = os.path.join(ROOT, "out", "galway_sf2")

LINE = re.compile(r"osc(\d): freq (\d+)%.*?waveform (\d+)%.*?pulse (\d+)%.*?AD/SR (\d+)%.*?\((\d+)/(\d+)\)")


def parse(out):
    """-> {osc: (freq,wave,pulse,adsr,tot)} for gated voices (tot>0)."""
    res = {}
    for ln in out.splitlines():
        m = re.search(r"osc(\d): freq (\d+)%\S*\s+\((\d+)/(\d+)\)\s+waveform (\d+)%\S*\s+\((\d+)/(\d+)\)\s+pulse (\d+)%\S*\s+\((\d+)/(\d+)\)\s+AD/SR (\d+)%", ln)
        if not m:
            continue
        v = int(m.group(1)); tot = int(m.group(4))
        res[v] = (int(m.group(2)), int(m.group(5)), int(m.group(8)), int(m.group(11)), tot)
    return res


def subtune_of(name, sid):
    if name in SUBTUNE:
        return SUBTUNE[name]
    return (SIDParser(sid).parse_header().start_song or 1) - 1


def run(sid, sf2, ms, st):
    r = subprocess.run([sys.executable, os.path.join(ROOT, "bin", "sf2ii_vs_real.py"),
                        sid, sf2, SECS, str(ms), str(st)], capture_output=True, text=True, cwd=ROOT)
    return r.stdout


def avg_freq(res):
    g = [r for r in res.values() if r[4] > 0]
    return sum(r[0] for r in g) / len(g) if g else 0


rows = []
sids = sorted(glob.glob(os.path.join(SIDD, "*.sid")))
for sid in sids:
    name = os.path.splitext(os.path.basename(sid))[0]
    if FILT and FILT not in name:
        continue
    sf2 = os.path.join(SF2D, name + ".sf2")
    if not os.path.exists(sf2):
        rows.append((name, None, None)); print(f"{name:32s} NO SF2"); continue
    st = subtune_of(name, sid)
    best = None; bestms = 1
    for ms in (1, 2, 4, 8):
        res = parse(run(sid, sf2, ms, st))
        af = avg_freq(res)
        if best is None or af > avg_freq(best):
            best, bestms = res, ms
        if af >= 95:
            break
    rows.append((name, bestms, best))
    g = [r for r in best.values() if r[4] > 0]
    if g:
        fr = sum(r[0] for r in g) / len(g); wv = sum(r[1] for r in g) / len(g)
        pu = sum(r[2] for r in g) / len(g); ad = sum(r[3] for r in g) / len(g)
        print(f"{name:32s} ms{bestms} | freq {fr:3.0f} wave {wv:3.0f} pulse {pu:3.0f} adsr {ad:3.0f} | "
              + " ".join(f"o{v+1}:{best[v][0]}/{best[v][2]}" for v in sorted(best)))
    else:
        print(f"{name:32s} ms{bestms} | (no gated voices captured)")
    sys.stdout.flush()

# summary
good = [n for n, m, r in rows if r and all(v[0] >= 95 and v[2] >= 90 for v in r.values() if v[4] > 0) and any(v[4] > 0 for v in r.values())]
print(f"\n=== {len(good)}/{len(rows)} tunes >=95% freq & >=90% pulse on every gated voice ===")
print("GOOD:", ", ".join(good))
