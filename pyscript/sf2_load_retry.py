"""Retry F10-load until SF2II accepts the file or max attempts reached.

Background: SIDFactoryII has a heap-state-dependent crash on F10-load
of our raw-NP21 SF2 files. The file ALWAYS plays correctly when load
succeeds — the crash is in the editor view's setup, not the parser.
Pass rate is ~60% on Stinsen, ~27% on Unboxed (per project-status memory).

This wrapper retries until success. Per-attempt success rate baselines:
Stinsen ~60%, Unboxed ~27% (worst case). At 27%, expected attempts =
1/0.27 ≈ 3.7; std dev is ~3.2. The 99th-percentile attempt count is
~14. Empirically (5 cycles on Unboxed, 2026-05-06): one cycle hit
attempt 10. Default max_attempts=15 covers 99% of Unboxed cycles
(1 - 0.73^15 = 99.0%) and >99.99% on Stinsen, with worst-case wall
time bound at ~90s.

Usage:
    py -3 pyscript/sf2_load_retry.py <file.sf2> [max_attempts]

Exit codes:
    0  one of the attempts succeeded
    1  all attempts crashed (file may be malformed or harness misconfigured)
    2  invalid arguments
"""
import os
import sys
import time
from pathlib import Path

# Reuse the existing harness's per-attempt logic.
sys.path.insert(0, str(Path(__file__).parent))
import sf2_load_test as harness


def load_with_retry(sf2_path: str, max_attempts: int = 15,
                    per_attempt_timeout: float = 12.0,
                    verbose: bool = True) -> dict:
    """Try F10-loading sf2_path up to max_attempts times.

    Returns a dict:
      verdict        : 'PASS' if any attempt succeeded, else 'CRASH'
      attempts       : number of attempts made (1..max_attempts)
      first_pass     : 1-indexed attempt number that passed, or None
      attempt_log    : list of (verdict, elapsed_s, exit_code) for each attempt
    """
    abs_path = str(Path(sf2_path).absolute())
    if not Path(abs_path).exists():
        return {'verdict': 'MISSING', 'attempts': 0, 'first_pass': None,
                'attempt_log': []}

    log = []
    for attempt in range(1, max_attempts + 1):
        result = harness.test_one(abs_path, total_timeout=per_attempt_timeout)
        log.append((result['verdict'], result.get('elapsed_s'),
                    result.get('exit_code')))
        if verbose:
            print(f'  attempt {attempt}/{max_attempts}: '
                  f'{result["verdict"]} '
                  f'(elapsed={result.get("elapsed_s")}s, '
                  f'exit={result.get("exit_code")})',
                  flush=True)
        if result['verdict'] == 'PASS':
            return {'verdict': 'PASS', 'attempts': attempt,
                    'first_pass': attempt, 'attempt_log': log}
        # Brief pause between attempts so SF2II's window can fully release
        # before next launch.
        time.sleep(0.5)

    return {'verdict': 'CRASH', 'attempts': max_attempts,
            'first_pass': None, 'attempt_log': log}


def main(argv):
    if not argv:
        print(__doc__)
        sys.exit(2)
    sf2_path = argv[0]
    max_attempts = int(argv[1]) if len(argv) >= 2 else 15

    if not os.path.exists(sf2_path):
        print(f'ERROR: file not found: {sf2_path}', file=sys.stderr)
        sys.exit(2)

    print(f'Loading {sf2_path} (max {max_attempts} attempts)...', flush=True)
    t_start = time.time()
    result = load_with_retry(sf2_path, max_attempts=max_attempts)
    elapsed = time.time() - t_start

    print()
    if result['verdict'] == 'PASS':
        print(f'SUCCESS: loaded on attempt {result["first_pass"]}/{result["attempts"]} '
              f'(total wall time {elapsed:.1f}s)')
        sys.exit(0)
    else:
        print(f'FAIL: all {result["attempts"]} attempts crashed '
              f'(total wall time {elapsed:.1f}s)')
        crashes = [v for v, _, _ in result['attempt_log'] if v == 'CRASH']
        print(f'  crash count: {len(crashes)}/{result["attempts"]}')
        sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1:])
