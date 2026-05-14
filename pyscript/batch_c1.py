"""Batch C1 (F10-load) check on a list of SF2 files.

Usage:  py -3 pyscript/batch_c1.py [N=15] file1.sf2 file2.sf2 ...

Prints per-file PASS/N and final totals. Sequential — pyautogui needs screen focus.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sf2_load_test as h


def main(argv):
    if not argv:
        print(__doc__); sys.exit(2)
    try:
        N = int(argv[0])
        files = argv[1:]
    except ValueError:
        N = 15
        files = argv

    results = []
    for sf2 in files:
        sf2 = str(Path(sf2).absolute())
        name = Path(sf2).stem
        print(f"\n=== {name} ===", flush=True)
        ok = crash = other = 0
        first_crash_tail = None
        for i in range(1, N + 1):
            r = h.test_one(sf2)
            v = r['verdict']
            print(f"  trial {i}/{N}: {v}", flush=True)
            if v == 'PASS':
                ok += 1
            elif v == 'CRASH':
                crash += 1
                if first_crash_tail is None:
                    first_crash_tail = r.get('stderr_tail')
            else:
                other += 1
        results.append((name, ok, crash, other, N, first_crash_tail))

    print("\n\n========== summary ==========")
    print(f"{'file':<40s} {'PASS':>6s} {'CRASH':>6s} {'OTHER':>6s} {'rate':>6s}")
    for name, ok, crash, other, n, _ in results:
        print(f"{name:<40s} {ok:>6d} {crash:>6d} {other:>6d} {100*ok/n:>5.0f}%")
    total_p = sum(r[1] for r in results)
    total_n = sum(r[4] for r in results)
    print(f"{'TOTAL':<40s} {total_p:>6d} {sum(r[2] for r in results):>6d} "
          f"{sum(r[3] for r in results):>6d} {100*total_p/total_n if total_n else 0:>5.0f}%")


if __name__ == "__main__":
    main(sys.argv[1:])
