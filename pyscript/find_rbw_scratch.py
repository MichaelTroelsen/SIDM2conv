"""Find read-before-write addresses in a window during INIT + early PLAY.

For low-load SF2 files the header lands in $0600-$080D. If the embedded
player READS a scratch byte there before WRITING it, it sees a header
byte instead of its expected (zero) init value → audio divergence.
This runs the ORIGINAL SID binary in py65 and reports which window
addresses are read before first write (= the conflict set).

Usage:  py -3 pyscript/find_rbw_scratch.py <file.sid> [win_lo win_hi frames]
Default window $0600-$08FF, 12 PLAY frames.
"""
import struct, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def parse_psid(p):
    d = Path(p).read_bytes()
    do = struct.unpack(">H", d[6:8])[0]
    la = struct.unpack(">H", d[8:10])[0]
    ia = struct.unpack(">H", d[10:12])[0]
    pa = struct.unpack(">H", d[12:14])[0]
    c = d[do:]
    if la == 0:
        la = struct.unpack("<H", c[:2])[0]; c = c[2:]
    if ia == 0: ia = la
    if pa == 0: pa = ia + 3
    return la, ia, pa, c


def main(argv):
    sid = argv[0]
    win_lo = int(argv[1], 0) if len(argv) > 1 else 0x0600
    win_hi = int(argv[2], 0) if len(argv) > 2 else 0x08FF
    frames = int(argv[3]) if len(argv) > 3 else 12

    la, ia, pa, c = parse_psid(sid)
    from py65.devices.mpu6502 import MPU
    mpu = MPU()
    for i in range(0x10000):
        mpu.memory[i] = 0
    for i in range(len(c)):
        mpu.memory[(la + i) & 0xFFFF] = c[i]

    written = set()
    rbw = {}            # addr -> first read PC (before any write)
    base_read = mpu.memory.__class__.__getitem__ if False else None

    # py65 MPU.memory is a plain list; wrap __getitem__/__setitem__ via a
    # subclass proxy.
    real = mpu.memory

    class Obs(list):
        def __getitem__(self, a):
            if isinstance(a, int) and win_lo <= a <= win_hi and a not in written:
                rbw.setdefault(a, mpu.pc)
            return list.__getitem__(self, a)
        def __setitem__(self, a, v):
            if isinstance(a, int) and win_lo <= a <= win_hi:
                written.add(a)
            list.__setitem__(self, a, v)

    obs = Obs(real)
    mpu.memory = obs

    def run_to_rts(entry, max_cycles=2_000_000):
        mpu.pc = entry
        sp0 = mpu.sp
        # push sentinel return
        sent = 0xFFF0
        mpu.memory[0x0100 | mpu.sp] = (sent >> 8) & 0xFF
        mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.memory[0x0100 | mpu.sp] = sent & 0xFF
        mpu.sp = (mpu.sp - 1) & 0xFF
        cyc = 0
        while cyc < max_cycles:
            if mpu.pc == sent:
                break
            mpu.step()
            cyc += 1

    mpu.a = 0  # subtune 0
    run_to_rts(ia)
    for _ in range(frames):
        run_to_rts(pa)

    print(f"{Path(sid).stem}: load=${la:04X} init=${ia:04X} play=${pa:04X}")
    rbw_in = sorted(rbw)
    print(f"read-before-write in ${win_lo:04X}-${win_hi:04X}: {len(rbw_in)}")
    if rbw_in:
        print(f"  range ${rbw_in[0]:04X}-${rbw_in[-1]:04X}")
        # cluster summary: contiguous-ish runs
        runs = []
        s = p = rbw_in[0]
        for a in rbw_in[1:]:
            if a - p > 8:
                runs.append((s, p)); s = a
            p = a
        runs.append((s, p))
        for lo, hi in runs:
            print(f"  run ${lo:04X}-${hi:04X} ({hi - lo + 1}B span)")
        print("  addrs: " + " ".join(f"${a:04X}" for a in rbw_in[:40]))


if __name__ == "__main__":
    main(sys.argv[1:])
