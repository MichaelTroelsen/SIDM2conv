"""Survey C3 (edit-propagation) wiring across a SID directory.

For each file, convert and parse the converter log for:
  - F1 (sequences): "skipping patch" -> skip, else wired
  - F2 (instruments): "Stage 7 .*instr" routine present
  - F3 (wave):        "Stage 7 wave-split-copy" present
  - F4 (pulse):       "Stage 7 .*pulse" present
  - F5 (filter):      "Stage 7 .*filter" present
  - ch_seq_ptr autodetect score
Writes CSV + prints aggregate cluster counts.

NOTE: "wired" != "propagates to playback" — the wave/instr/pulse/filter
detector may point at addresses the variant's player doesn't actually
read (see Cycles in memory/sid-root-4-criterion-status.md). This survey
measures WIRING presence, not verified propagation.

Usage:  py -3 pyscript/batch_c3_survey.py <sid_dir> [out_csv]
"""
import csv, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONV = ROOT / "scripts" / "sid_to_sf2.py"

RE_SKIP = re.compile(r"skipping patch|reverted default ch_seq_ptr patch|skip_ch_seq_patch")
RE_WAVE = re.compile(r"Stage 7 wave-split-copy")
RE_INSTR = re.compile(r"Stage 7 .*instr", re.I)
RE_PULSE = re.compile(r"Stage 7 .*pulse", re.I)
RE_FILTER = re.compile(r"Stage 7 .*filter", re.I)
RE_SCORE = re.compile(r"ch_seq_ptr autodetect:.*score=(\d+)")
RE_V20 = re.compile(r"Vibrants V20")


def main(argv):
    sid_dir = Path(argv[0]) if argv else ROOT / "SID" / "Laxity"
    out_csv = Path(argv[1]) if len(argv) > 1 else ROOT / "bin" / "_laxity_c3.csv"
    sids = sorted(sid_dir.glob("*.sid"))

    results = []
    tally = {"F1_wired": 0, "F2": 0, "F3": 0, "F4": 0, "F5": 0,
             "v20": 0, "conv_fail": 0, "all5": 0}
    for i, sid in enumerate(sids, 1):
        name = sid.stem
        sf2 = ROOT / "bin" / f"_c3_{name[:36]}.sf2"
        for p in (sf2, sf2.with_suffix(".txt")):
            try: p.unlink()
            except FileNotFoundError: pass
        rc = subprocess.run([sys.executable, str(CONV), str(sid), str(sf2)],
                            capture_output=True, text=True, cwd=str(ROOT))
        log = rc.stderr + rc.stdout
        if rc.returncode != 0 or not sf2.exists():
            results.append((name, "CONV_FAIL", "", "", "", "", "", ""))
            tally["conv_fail"] += 1
            print(f"[{i}/{len(sids)}] {name}: CONV_FAIL", flush=True)
            continue
        f1 = "skip" if RE_SKIP.search(log) else "wired"
        f2 = "Y" if RE_INSTR.search(log) else ""
        f3 = "Y" if RE_WAVE.search(log) else ""
        f4 = "Y" if RE_PULSE.search(log) else ""
        f5 = "Y" if RE_FILTER.search(log) else ""
        v20 = "Y" if RE_V20.search(log) else ""
        m = RE_SCORE.search(log)
        score = m.group(1) if m else ""
        results.append((name, "OK", f1, f2, f3, f4, f5, v20, score))
        if f1 == "wired": tally["F1_wired"] += 1
        if f2: tally["F2"] += 1
        if f3: tally["F3"] += 1
        if f4: tally["F4"] += 1
        if f5: tally["F5"] += 1
        if v20: tally["v20"] += 1
        if f1 == "wired" and f2 and f3 and f4 and f5:
            tally["all5"] += 1
        print(f"[{i}/{len(sids)}] {name}: F1={f1} F2={f2 or '-'} "
              f"F3={f3 or '-'} F4={f4 or '-'} F5={f5 or '-'} "
              f"{'V20' if v20 else ''} score={score}", flush=True)

        try: sf2.unlink()
        except FileNotFoundError: pass

    with open(out_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "convert", "F1", "F2_instr", "F3_wave",
                    "F4_pulse", "F5_filter", "V20", "ch_seq_score"])
        w.writerows(results)

    n = len(sids)
    print("\n========== C3 WIRING AGGREGATE ==========")
    print(f"Total files:            {n}")
    print(f"Convert failures:       {tally['conv_fail']}")
    print(f"F1 sequences wired:     {tally['F1_wired']}/{n}")
    print(f"F2 instruments wired:   {tally['F2']}/{n}")
    print(f"F3 wave wired:          {tally['F3']}/{n}")
    print(f"F4 pulse wired:         {tally['F4']}/{n}")
    print(f"F5 filter wired:        {tally['F5']}/{n}")
    print(f"Vibrants V20 detected:  {tally['v20']}/{n}")
    print(f"ALL 5 columns wired:    {tally['all5']}/{n}  (strict-C3 wiring)")
    print(f"CSV: {out_csv}")


if __name__ == "__main__":
    main(sys.argv[1:])
