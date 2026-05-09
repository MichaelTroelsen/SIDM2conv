"""Test the ch_seq_ptr scanner across known files."""
import sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sidm2.ch_seq_ptr_scanner import detect_ch_seq_ptr


def parse_psid(p):
    buf = open(p, 'rb').read()
    do = (buf[6] << 8) | buf[7]
    load = (buf[8] << 8) | buf[9]
    init = (buf[10] << 8) | buf[11]
    play = (buf[12] << 8) | buf[13]
    if load == 0:
        load = buf[do] | (buf[do+1] << 8)
        c64 = buf[do+2:]
    else:
        c64 = buf[do:]
    return load, init, play, bytes(c64)


def main(paths, expected=None):
    for path in paths:
        load, init, play, c64 = parse_psid(path)
        t0 = time.time()
        result = detect_ch_seq_ptr(c64, load, init, play_addr=play, n_play_ticks=3)
        dt = time.time() - t0
        if result is None:
            print(f'  {Path(path).name:<35s}  no candidate found  ({dt:.1f}s)')
            continue
        lo_addr, hi_addr, ptrs, score = result
        ptr_str = ' '.join(f'${p:04X}' for p in ptrs)
        valid = sum(1 for p in ptrs if load <= p < load + len(c64))
        print(f'  {Path(path).name:<35s}  lo=${lo_addr:04X} hi=${hi_addr:04X}  '
              f'ptrs=[{ptr_str}]  valid={valid}/3  score={score}  ({dt:.1f}s)')
        if expected:
            ex_lo, ex_hi = expected.get(Path(path).name, (None, None))
            if ex_lo is not None:
                ok = (lo_addr == ex_lo and hi_addr == ex_hi)
                print(f'      expected lo=${ex_lo:04X} hi=${ex_hi:04X}  match={ok}')


if __name__ == '__main__':
    main(sys.argv[1:], expected={
        'Stinsens_Last_Night_of_89.sid': (0x1A1C, 0x1A1F),
        'Unboxed_Ending_8580.sid':       (0x1A1C, 0x1A1F),
    })
