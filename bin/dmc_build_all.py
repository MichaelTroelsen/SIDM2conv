"""Survey + build the whole DMC (Bjerregaard) corpus -> native SF2 parts.

Two phases (builds are SEQUENTIAL — the shared MoN drivers_src scratch forbids
concurrency):
  --dry   categorize all 88 files (no builds): tables-located? onset-eligible?
  (build) build every onset-eligible file (auto parts) with a per-file timeout.

Categories per file:
  NO-TABLES  the signature parser couldn't locate all four tables (a variant).
  ELIGIBLE   emulated onsets agree >=85% with siddump -> onset-aligned build.
  FALLBACK   tables located but onsets disagree (multispeed/self-IRQ/legato) ->
             the build falls back to the tick grid (lower fidelity).

  py -3 bin/dmc_build_all.py --dry
  py -3 bin/dmc_build_all.py           # build eligible (detached; timeout-proof)
"""
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "bin"))
os.chdir(ROOT)

from sidm2.dmc_parser import (load_sid, DMCModule, decode_song, measure_onsets)
from sidm2.fidelity_common import siddump_note_onsets

DRY = '--dry' in sys.argv
AGREE_FRAMES = 800        # ~16s window is plenty to judge onset agreement
MIN_ONSETS = 8            # below this a voice is silent/near-silent in the window


def survey(path):
    """-> (category, agree, total, note) without building."""
    d, la, h = load_sid(path)
    m = DMCModule(d, la)
    if not (m.lay.sector_lo and m.lay.sound and m.lay.freq and m.lay.trk_lo):
        return "NO-TABLES", 0, 0, "signature miss (variant)"
    onsets = measure_onsets(d, la, h.init_address, h.play_address, AGREE_FRAMES)
    real = siddump_note_onsets(path, ['-a0', '-t16'])
    agree = tot = 0
    for v in range(3):
        rl = set(fr for fr, _ in (real[v] if isinstance(real, (list, tuple))
                                  else real.get(v, [])) if fr < AGREE_FRAMES - 100)
        em = set(onsets[v])
        agree += sum(1 for fr in rl if fr in em or fr + 1 in em or fr - 1 in em)
        tot += len(rl)
    if tot < MIN_ONSETS:
        return "FALLBACK", agree, tot, f"sparse ({tot} onsets/16s)"
    pct = agree / tot
    cat = "ELIGIBLE" if pct >= 0.85 else "FALLBACK"
    return cat, agree, tot, f"{100*pct:.0f}% onset-agree"


def main():
    files = sorted(glob.glob("SID/JohannesBjerregaard/*.sid"))
    cats = {"NO-TABLES": [], "ELIGIBLE": [], "FALLBACK": [], "ERROR": []}
    for path in files:
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            cat, ag, tot, note = survey(path)
        except Exception as e:
            cats["ERROR"].append(name)
            print(f"  {name:28} ERROR {str(e)[:50]}")
            continue
        cats[cat].append(name)
        print(f"  {name:28} {cat:9} {note}")
    print(f"\n=== SURVEY: {len(files)} files ===")
    for k in ("ELIGIBLE", "FALLBACK", "NO-TABLES", "ERROR"):
        print(f"  {k:10} {len(cats[k])}")
    if DRY:
        return

    built, failed = [], []
    for name in cats["ELIGIBLE"]:
        path = f"SID/JohannesBjerregaard/{name}.sid"
        print(f"\n##### building {name} (auto)")
        try:
            r = subprocess.run(
                [sys.executable, 'bin/build_dmc_native_song.py', path, 'auto'],
                capture_output=True, text=True, timeout=3600)
        except subprocess.TimeoutExpired:
            print("    TIMEOUT (>60min) — skipping")
            failed.append((name, 'timeout'))
            continue
        tail = (r.stdout or '').strip().splitlines()
        print('   ', tail[-1] if tail else '(no output)')
        (built if r.returncode == 0 else failed).append(
            name if r.returncode == 0 else (name, (r.stderr or '')[-200:]))
        # restore the shared generated driver scratch between builds
        for f in ("layout.inc", "freqtable.inc"):
            os.system(f'git checkout -- "drivers_src/mon/{f}" 2>NUL')
    print(f"\nBUILT {len(built)}; FAILED {len(failed)}")
    for item in failed:
        print(f"  FAIL {item}")


if __name__ == '__main__':
    main()
