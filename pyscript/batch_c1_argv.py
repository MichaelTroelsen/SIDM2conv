"""Alternative C1 test using SF2II argv-load instead of pyautogui F10.

Per v3.5.27 memory: 10 Laxity files (Jingles, Mikuk, Patterns,
Schmold_Skool, Quark, Space_Game, Too_Much_Hubbard, IAME, Quit_Wizax,
Shit_2) crash 100% on F10-load but load fine via argv-load. The
existing C1 test (`batch_c1_overnight.py`) uses pyautogui F10, which
exposes a SF2II GUI bug unrelated to our converter.

This test spawns `SIDFactoryII.exe <sf2_path> --skip-intro` and
classifies the outcome:
  - PASS  : process alive after `total_timeout` seconds (loaded OK)
  - CRASH : process exited before timeout (with exit code)
  - NO_SF2: SF2 conversion failed (no file to test)

Much faster than the F10 test (no GUI driving), so we can run the
full 286-file corpus in ~20 minutes.

Usage:
  py -3 pyscript/batch_c1_argv.py SID/Laxity [N=3] [out.csv]

Each file is tested N times (default 3 — argv-load is deterministic
so 3 trials catches any heap-state nondeterminism while keeping it
fast).
"""
import csv
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONV = ROOT / "scripts" / "sid_to_sf2.py"
EDITOR = ROOT / "bin" / "SIDFactoryII.exe"


def test_argv_load(sf2_path: Path, timeout: float = 4.0) -> dict:
    """Spawn SF2II with the SF2 as argv[1]. Wait up to `timeout` seconds
    for the process to either crash (exit) or stabilize.

    Returns: dict with 'verdict' (PASS|CRASH|NO_WINDOW), 'exit_code',
    'elapsed_s', 'stderr_tail'.
    """
    result = {'verdict': 'UNKNOWN', 'exit_code': None,
              'elapsed_s': 0.0, 'stderr_tail': ''}
    t0 = time.time()
    proc = subprocess.Popen(
        [str(EDITOR), str(sf2_path), '--skip-intro'],
        cwd=str(EDITOR.parent),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    deadline = t0 + timeout
    while time.time() < deadline:
        rc = proc.poll()
        if rc is not None:
            result['verdict'] = 'CRASH'
            result['exit_code'] = rc
            result['elapsed_s'] = round(time.time() - t0, 2)
            try:
                tail = proc.stderr.read()[-500:].replace('\n', ' | ')
                result['stderr_tail'] = tail
            except Exception:
                pass
            return result
        time.sleep(0.1)
    # Still alive after timeout — loaded OK
    proc.kill()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    result['verdict'] = 'PASS'
    result['elapsed_s'] = round(time.time() - t0, 2)
    return result


def main(argv):
    args = [a for a in argv if not a.startswith('--')]
    sid_dir = Path(args[0]) if args else ROOT / "SID" / "Laxity"
    N = int(args[1]) if len(args) > 1 else 3
    out_csv = Path(args[2]) if len(args) > 2 else ROOT / "pyscript" / "baselines" / "laxity_c1_argv_v3554.csv"

    sids = sorted(sid_dir.glob('*.sid'))
    print(f"Testing {len(sids)} files x {N} trials each = {len(sids)*N} argv-load checks")
    print(f"Estimated wall-clock: {len(sids)*N*4 / 60:.0f} min", flush=True)

    with open(out_csv, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['file', 'pass', 'crash', 'no_sf2', 'N', 'rate_pct', 'first_crash_tail'])

        t0 = time.time()
        for i, sid in enumerate(sids, 1):
            name = sid.stem
            sf2 = ROOT / "bin" / f"_lxargv_{name[:40]}.sf2"
            for p in (sf2, sf2.with_suffix('.txt')):
                try: p.unlink()
                except FileNotFoundError: pass
            rc = subprocess.run(
                [sys.executable, str(CONV), str(sid), str(sf2), '-q'],
                capture_output=True, text=True, cwd=str(ROOT),
            )
            if rc.returncode != 0 or not sf2.exists():
                w.writerow([name, 0, 0, N, N, 0, 'CONV_FAIL'])
                f.flush()
                print(f"[{i}/{len(sids)}] {name}: CONV_FAIL", flush=True)
                continue

            ok = crash = 0
            first_tail = ''
            for t in range(N):
                r = test_argv_load(sf2)
                if r['verdict'] == 'PASS':
                    ok += 1
                elif r['verdict'] == 'CRASH':
                    crash += 1
                    if not first_tail and r['stderr_tail']:
                        first_tail = r['stderr_tail'][:200]
            rate = round(100 * ok / N)
            w.writerow([name, ok, crash, 0, N, rate, first_tail])
            f.flush()
            elapsed = time.time() - t0
            eta = elapsed / i * (len(sids) - i)
            print(f"[{i}/{len(sids)}] {name}: {ok}/{N} ({rate}%)  "
                  f"elapsed={elapsed/60:.1f}m  ETA={eta/60:.0f}m", flush=True)
            try: sf2.unlink()
            except FileNotFoundError: pass

    print(f"\nDONE in {(time.time()-t0)/60:.1f}min. Results: {out_csv}")


if __name__ == '__main__':
    main(sys.argv[1:])
