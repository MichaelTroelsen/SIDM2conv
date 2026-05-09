"""Count how many Laxity files now extract real patterns thanks to the
ch_seq_ptr autodetector.

Compares against the old probe_multipattern.py classes (A: ch_seq_ptr
valid; B/C: not valid). For B/C files, runs the full converter and
measures whether num_patterns > 0 in the SF2 edit area.

Usage: py -3 pyscript/probe_classb_lift.py SID/Laxity/*.sid
"""
import logging, subprocess, sys
from pathlib import Path

logging.basicConfig(level=logging.ERROR)
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CONVERTER = ROOT / 'scripts' / 'sid_to_sf2.py'


def parse_psid(p):
    buf = open(p, 'rb').read()
    do = (buf[6] << 8) | buf[7]
    load = (buf[8] << 8) | buf[9]
    if load == 0:
        load = buf[do] | (buf[do+1] << 8)
        c64 = buf[do+2:]
    else:
        c64 = buf[do:]
    return load, bytes(c64)


def ch_seq_ptr_was_valid(c64, sid_la):
    for v in range(3):
        if 0x0A1C + v >= len(c64) or 0x0A1F + v >= len(c64): continue
        seq = (c64[0x0A1F + v] << 8) | c64[0x0A1C + v]
        if sid_la <= seq < sid_la + len(c64): return True
    return False


def convert_check(sid: Path):
    """Convert and check log for "ch_seq_ptr autodetect" + edit-area pattern count."""
    out = ROOT / 'bin' / f'_lift_{sid.stem[:30]}.sf2'
    out_txt = out.with_suffix('.txt')
    for p in (out, out_txt):
        try: p.unlink()
        except FileNotFoundError: pass
    rc = subprocess.run(
        [sys.executable, str(CONVERTER), str(sid), str(out)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    success = (rc.returncode == 0)
    stream = rc.stderr + rc.stdout
    detected = ('ch_seq_ptr autodetect' in stream)
    n_patterns = 0
    if 'No NP21 patterns found' in stream:
        n_patterns = 0
    else:
        import re
        # Match "(N pat" — the multiplication char varies by console encoding
        # (× under utf-8, � under cp1252)
        m = re.search(r'\((\d+) pat\W', stream)
        if m: n_patterns = int(m.group(1))
        else: n_patterns = -1
    # Cleanup test artifacts
    for p in (out, out_txt):
        try: p.unlink()
        except FileNotFoundError: pass
    return success, detected, n_patterns


def main(paths):
    total = 0
    classes = {'A_native': 0, 'B_lifted': 0, 'B_failed': 0, 'C_unchanged': 0,
               'CONVERT_FAIL': 0}
    lifted = []
    failed_examples = []
    for p in paths:
        sid = Path(p)
        try:
            sid_la, c64 = parse_psid(p)
        except Exception:
            continue
        total += 1
        was_valid = ch_seq_ptr_was_valid(c64, sid_la)
        success, detected, n_pat = convert_check(sid)
        if not success:
            classes['CONVERT_FAIL'] += 1
            continue
        if was_valid and not detected:
            classes['A_native'] += 1   # Default $0A1C/$0A1F path worked
        elif detected and n_pat > 0:
            classes['B_lifted'] += 1
            lifted.append(sid.name)
        elif n_pat == 0:
            classes['C_unchanged'] += 1   # No patterns → empty fallback
        else:
            classes['B_failed'] += 1
            if len(failed_examples) < 8:
                failed_examples.append(sid.name)   # Autodetect ran but yielded no patterns
    print(f'\n=== summary ({total} files) ===')
    for k, v in classes.items():
        print(f'  {k:>15s}: {v:>4d}  ({100*v/max(total,1):.0f}%)')
    if lifted:
        print(f'\n  examples of B_lifted ({min(len(lifted), 8)} of {len(lifted)}):')
        for f in lifted[:8]:
            print(f'    {f}')
    if failed_examples:
        print(f'\n  examples of B_failed ({len(failed_examples)} of {classes["B_failed"]}):')
        for f in failed_examples:
            print(f'    {f}')


if __name__ == '__main__':
    main(sys.argv[1:])
