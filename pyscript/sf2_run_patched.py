"""Run the SIDM2-patched SF2II.exe with our test SF2 and capture stderr.
Reuses the SendInput-driving approach from sf2_load_test.py but points at
the patched binary in /tmp/sf2-src/sidfactory2/Release/.
"""
import os, sys, time, subprocess, tempfile, shutil
from pathlib import Path

# Use Windows path for /tmp
PATCHED_BIN_DIR = Path(r'C:\Users\mit\AppData\Local\Temp\sf2-src\sidfactory2\Release')
EDITOR = str(PATCHED_BIN_DIR / 'SIDFactoryII.exe')

# Reuse harness driver
sys.path.insert(0, str(Path(__file__).parent))
import sf2_load_test as h

# Override the EDITOR
h.EDITOR = EDITOR

if len(sys.argv) < 2:
    print('usage: sf2_run_patched.py <file.sf2>'); sys.exit(1)

src = sys.argv[1]
res = h.test_one(src, total_timeout=15.0)
print(f'verdict={res["verdict"]} elapsed={res["elapsed_s"]}s exit={res["exit_code"]}')
print(f'stderr_log: {res.get("stderr_log")}')
print()
# Print last 30 lines of stderr
log = res.get('stderr_log')
if log and Path(log).exists():
    lines = open(log, 'r', encoding='utf-8', errors='replace').read().splitlines()
    print('--- stderr (last 60 lines) ---')
    for ln in lines[-60:]:
        print(ln)
