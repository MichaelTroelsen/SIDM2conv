"""Overnight C1 (F10-load) batch for a whole SID directory.

Converts each SID -> SF2, then runs the pyautogui F10-load test N times.
Writes results to a CSV *incrementally* (one row per file, flushed) so an
interruption (crash / reboot / Ctrl-C) leaves a partial-but-valid CSV and
the run can be resumed (already-done files are skipped if --resume).

Usage:
  py -3 pyscript/batch_c1_overnight.py <sid_dir> [N=15] [out_csv] [--resume]

Recommended overnight invocation (all 286 Laxity files, N=15):
  py -3 pyscript/batch_c1_overnight.py SID/Laxity 15 bin/_laxity_c1.csv

To resume after an interruption:
  py -3 pyscript/batch_c1_overnight.py SID/Laxity 15 bin/_laxity_c1.csv --resume

Do NOT touch the keyboard/mouse while it runs — pyautogui drives the GUI.
"""
import csv, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pyscript"))
import sf2_load_test as h

CONV = ROOT / "scripts" / "sid_to_sf2.py"


def load_done(csv_path: Path) -> set:
    done = set()
    if csv_path.exists():
        with open(csv_path, newline="") as f:
            for row in csv.reader(f):
                if row and row[0] != "file":
                    done.add(row[0])
    return done


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    resume = "--resume" in argv
    sid_dir = Path(args[0]) if args else ROOT / "SID" / "Laxity"
    N = int(args[1]) if len(args) > 1 else 15
    out_csv = Path(args[2]) if len(args) > 2 else ROOT / "bin" / "_laxity_c1.csv"

    sids = sorted(sid_dir.glob("*.sid"))
    done = load_done(out_csv) if resume else set()

    # Open CSV in append mode if resuming + file exists, else write header
    new_file = not (resume and out_csv.exists())
    f = open(out_csv, "a", newline="")
    w = csv.writer(f)
    if new_file:
        w.writerow(["file", "pass", "crash", "other", "N", "rate_pct", "first_crash_tail"])
        f.flush()

    t0 = time.time()
    n_total = len(sids)
    for i, sid in enumerate(sids, 1):
        name = sid.stem
        if name in done:
            print(f"[{i}/{n_total}] {name}: SKIP (already in CSV)", flush=True)
            continue
        sf2 = ROOT / "bin" / f"_lxc1_{name[:40]}.sf2"
        for p in (sf2, sf2.with_suffix(".txt")):
            try: p.unlink()
            except FileNotFoundError: pass
        rc = subprocess.run([sys.executable, str(CONV), str(sid), str(sf2), "-q"],
                             capture_output=True, text=True, cwd=str(ROOT))
        if rc.returncode != 0 or not sf2.exists():
            w.writerow([name, 0, 0, 0, N, 0, "CONV_FAIL"]); f.flush()
            print(f"[{i}/{n_total}] {name}: CONV_FAIL", flush=True)
            continue

        ok = crash = other = 0
        first_tail = ""
        for t in range(1, N + 1):
            r = h.test_one(str(sf2))
            v = r["verdict"]
            if v == "PASS":
                ok += 1
            elif v == "CRASH":
                crash += 1
                if not first_tail:
                    first_tail = (r.get("stderr_tail") or "")[:200].replace("\n", " ")
            else:
                other += 1
        rate = round(100 * ok / N)
        w.writerow([name, ok, crash, other, N, rate, first_tail]); f.flush()
        elapsed = time.time() - t0
        eta = elapsed / i * (n_total - i)
        print(f"[{i}/{n_total}] {name}: {ok}/{N} PASS ({rate}%)  "
              f"elapsed={elapsed/60:.0f}m ETA={eta/60:.0f}m", flush=True)
        # clean staging file to avoid filling bin/
        try: sf2.unlink()
        except FileNotFoundError: pass

    f.close()
    print(f"\nDONE. Results: {out_csv}  ({(time.time()-t0)/60:.0f} min total)")


if __name__ == "__main__":
    main(sys.argv[1:])
