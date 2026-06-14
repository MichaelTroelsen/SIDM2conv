"""Measure CPU steps (≈cycles) the driver's INIT and each PLAY call take, run as
the flat image SF2II loads. SF2II aborts with 'emulation of 6510 code exceeded'
when a call runs past its per-frame cycle window (~19656 PAL cycles), so a play
call far above a few thousand steps is the bug. Reports the worst frames."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from py65.devices.mpu6502 import MPU

SF2 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "galway_native_song.sf2")
FRAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 600
INIT, PLAY = 0x1000, 0x1003

data = open(SF2, "rb").read()
load = data[0] | (data[1] << 8)
m = MPU()
for i, b in enumerate(data[2:]):
    m.memory[(load + i) & 0xFFFF] = b


def call(addr, cap=2_000_000):
    SENT = 0x4FFF
    m.memory[0x1FF] = SENT >> 8
    m.memory[0x1FE] = SENT & 0xFF
    m.sp = 0xFD
    m.pc = addr
    n = 0
    while n < cap:
        if m.pc == SENT or m.pc == (SENT + 1) & 0xFFFF:
            return n
        m.step()
        n += 1
    return -1  # ran away


ni = call(INIT)
print(f"{SF2}\n INIT: {ni} steps" + ("  *** RUNAWAY ***" if ni < 0 else ""))
worst = []
runaways = 0
for f in range(FRAMES):
    n = call(PLAY)
    if n < 0:
        runaways += 1
        worst.append((f, -1))
        if runaways <= 3:
            print(f"  frame {f}: PLAY RUNAWAY (no RTS within cap)")
        continue
    worst.append((f, n))
peaks = sorted((w for w in worst if w[1] >= 0), key=lambda x: -x[1])[:5]
print(f" PLAY over {FRAMES} frames: runaways={runaways}")
print(f"   max steps: {peaks}")
print(f"   typical (frame 0..3): {[worst[i][1] for i in range(min(4,len(worst)))]}")
