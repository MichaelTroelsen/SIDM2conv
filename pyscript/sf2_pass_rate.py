"""Measure SIDFactoryII F10-load pass rate for a given .sf2 file.

Usage:  py -3 pyscript/sf2_pass_rate.py <file.sf2> [N=15]

Reuses sf2_load_test.test_one(); prints PASS/CRASH count + first crash
verdict's stderr tail.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sf2_load_test as h

def main(argv):
    if not argv:
        print(__doc__); sys.exit(1)
    sf2 = argv[0]
    N = int(argv[1]) if len(argv) > 1 else 15

    pass_count = 0
    crash_count = 0
    other = 0
    first_crash_tail = None

    for i in range(1, N + 1):
        print(f'\n>>> trial {i}/{N}', flush=True)
        r = h.test_one(sf2)
        v = r['verdict']
        print(f'  verdict={v}  exit={r["exit_code"]}  elapsed={r["elapsed_s"]:.1f}s')
        if v == 'PASS':
            pass_count += 1
        elif v == 'CRASH':
            crash_count += 1
            if first_crash_tail is None and r.get('stderr_tail'):
                first_crash_tail = r['stderr_tail']
        else:
            other += 1

    print('\n=== Summary ===')
    print(f'PASS:  {pass_count}/{N}  ({100*pass_count/N:.0f}%)')
    print(f'CRASH: {crash_count}/{N}  ({100*crash_count/N:.0f}%)')
    if other:
        print(f'OTHER: {other}/{N}')
    if first_crash_tail:
        print('\n--- first CRASH stderr tail ---')
        print(first_crash_tail)

if __name__ == '__main__':
    main(sys.argv[1:])
