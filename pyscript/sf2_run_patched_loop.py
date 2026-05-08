"""Repeatedly run the patched SIDFactoryII against an SF2 file until N
total trials, OR until M CRASH trials have been captured (whichever
first). For each CRASH, save the full stderr log under /tmp/sf2_crash_NN.log
so we can post-mortem the per-component bracket logs.
"""
import os, sys, time, shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sf2_load_test as h

PATCHED = r'C:\Users\mit\AppData\Local\Temp\sf2-src\sidfactory2\Release\SIDFactoryII.exe'
h.EDITOR = PATCHED

def main(argv):
    if not argv:
        print('usage: sf2_run_patched_loop.py <file.sf2> [N=20] [maxCrashes=4]')
        sys.exit(1)
    sf2 = argv[0]
    N = int(argv[1]) if len(argv) > 1 else 20
    M = int(argv[2]) if len(argv) > 2 else 4

    pass_n = crash_n = 0
    crash_logs = []
    out_dir = Path(r'C:\Users\mit\AppData\Local\Temp')

    for i in range(1, N + 1):
        print(f'\n>>> trial {i}/{N}', flush=True)
        r = h.test_one(sf2)
        v = r['verdict']
        print(f'  verdict={v}  exit={r["exit_code"]}  elapsed={r["elapsed_s"]:.1f}s')
        if v == 'PASS':
            pass_n += 1
        elif v == 'CRASH':
            crash_n += 1
            log_src = r.get('stderr_log')
            if log_src and Path(log_src).exists():
                dst = out_dir / f'sf2_crash_{crash_n:02d}.log'
                shutil.copy(log_src, dst)
                crash_logs.append(str(dst))
                print(f'  saved -> {dst}')
            if crash_n >= M:
                print(f'\n[stop] reached {M} crashes')
                break
    print(f'\n=== summary ===  PASS={pass_n}  CRASH={crash_n}')
    print('crash logs:')
    for p in crash_logs:
        print(' ', p)

if __name__ == '__main__':
    main(sys.argv[1:])
