"""Probe a Laxity NP21 SID file's orderlist structure to determine whether
each voice plays a single looping sequence (Stinsen-like) OR a chain of
multiple distinct sequences (multi-pattern song).

Reads:
  - PSID load_addr from file header
  - ch_seq_ptr at $0A1C/$0A1F (voice 0/1/2 current-sequence pointers)
  - Walks each voice's sequence to find the `0xFF <loop_target>` terminator,
    and reports body length + loop target

Then walks the actual NP21 orderlist tables to count distinct sequences per
voice. Laxity's NP21 has the orderlist pointer table at known offsets
(player-version-dependent); for now we just inspect ch_seq_ptr behavior.

Usage: py -3 pyscript/probe_orderlist.py <path/to/file.sid> [more.sid ...]
"""
import struct, sys
from pathlib import Path

CH_SEQ_LO = 0x0A1C
CH_SEQ_HI = 0x0A1F


def parse_psid(path):
    buf = open(path, 'rb').read()
    if buf[:4] not in (b'PSID', b'RSID'):
        raise ValueError(f'{path}: not a PSID/RSID')
    data_off = (buf[6] << 8) | buf[7]
    psid_load = (buf[8] << 8) | buf[9]
    init_addr = (buf[10] << 8) | buf[11]
    play_addr = (buf[12] << 8) | buf[13]
    if psid_load == 0:
        psid_load = buf[data_off] | (buf[data_off + 1] << 8)
        c64 = buf[data_off + 2:]
    else:
        c64 = buf[data_off:]
    return psid_load, init_addr, play_addr, c64


def extract_seq(c64, sid_la, addr):
    """Walk an NP21 sequence: returns (body_len, loop_target | None, hit_end)."""
    off = addr - sid_la
    if off < 0 or off >= len(c64):
        return None, None, False
    body_len = 0
    j = 0
    while j < 256 and off + j < len(c64):
        b = c64[off + j]
        if b == 0x7F:
            return body_len, None, True       # end-of-data
        if b == 0xFF:
            lt = c64[off + j + 1] if off + j + 1 < len(c64) else 0
            return body_len, lt, False         # loop marker
        body_len += 1
        j += 1
    return body_len, None, False


def probe(path):
    psid_load, init, play, c64 = parse_psid(path)
    print(f'\n=== {Path(path).name} ===')
    print(f'  psid_load=${psid_load:04X}  init=${init:04X}  play=${play:04X}  c64_size={len(c64)}')

    # Voice ch_seq_ptrs
    ptrs = []
    for v in range(3):
        if CH_SEQ_LO + v < len(c64) and CH_SEQ_HI + v < len(c64):
            lo = c64[CH_SEQ_LO + v]
            hi = c64[CH_SEQ_HI + v]
            seq_addr = (hi << 8) | lo
            ptrs.append(seq_addr)
        else:
            ptrs.append(None)
    distinct = set(p for p in ptrs if p)

    print(f'  ch_seq_ptr per voice: {[f"${p:04X}" if p else "?" for p in ptrs]}')
    print(f'  distinct seq addrs: {len(distinct)} ({sorted(f"${p:04X}" for p in distinct)})')

    # Walk each distinct sequence
    for addr in sorted(distinct):
        body_len, loop, hit_end = extract_seq(c64, psid_load, addr)
        if body_len is None:
            print(f'  ${addr:04X}: out of c64 range')
            continue
        kind = 'END' if hit_end else (f'LOOP_TO_Y={loop:#04x}' if loop is not None else 'TRUNCATED')
        print(f'  ${addr:04X}: body={body_len}B  terminator={kind}')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    for p in sys.argv[1:]:
        try:
            probe(p)
        except Exception as e:
            print(f'\n!! {p}: {e}')
