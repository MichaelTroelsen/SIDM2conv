"""Diagnostic: load a native-Galway .sf2 as the flat memory image SF2II loads
(from its $0D7E load word), call the driver's INIT then PLAY for N frames, and
dump the per-voice SID registers that actually determine whether a voice makes
sound: freq ($D400/1), control/gate ($D404 bit0), waveform ($D404 hi nibble),
and the master volume ($D418 low nibble). Surfaces "no sound" causes the
build's freq-only headless check misses (gate off / waveform 0 / volume 0)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from py65.devices.mpu6502 import MPU

SF2 = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "out", "galway_trace_song.sf2")
FRAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 1800
INIT, PLAY = 0x1000, 0x1003


def main():
    data = open(SF2, "rb").read()
    load = data[0] | (data[1] << 8)
    print(f"{SF2}: load=${load:04X} size={len(data)}")
    m = MPU()
    for i, b in enumerate(data[2:]):
        m.memory[(load + i) & 0xFFFF] = b

    def call(addr):
        SENT = 0x4FFF
        m.memory[0x1FF] = SENT >> 8
        m.memory[0x1FE] = SENT & 0xFF
        m.sp = 0xFD
        m.pc = addr
        for _ in range(200000):
            if m.pc == (SENT + 1) & 0xFFFF or m.pc == SENT:
                return
            m.step()

    call(INIT)
    base = [0xD400, 0xD407, 0xD40E]
    # per-voice running stats
    gate_on = [0, 0, 0]
    wf_seen = [set(), set(), set()]
    freq_nz = [0, 0, 0]
    vol_seen = set()
    samples = []
    for f in range(FRAMES):
        call(PLAY)
        vol_seen.add(m.memory[0xD418] & 0x0F)
        row = []
        for v in range(3):
            fr = m.memory[base[v]] | (m.memory[base[v] + 1] << 8)
            ctrl = m.memory[base[v] + 4]
            pw = m.memory[base[v] + 2] | ((m.memory[base[v] + 3] & 0x0F) << 8)
            gate_on[v] += ctrl & 0x01
            wf_seen[v].add(ctrl & 0xF0)
            if fr:
                freq_nz[v] += 1
            row.append((fr, ctrl, pw))
        if f < 8 or f % 300 == 0:
            samples.append((f, row, m.memory[0xD418] & 0x0F))

    print("\n frame | V0 freq/ctrl/pw   V1 freq/ctrl/pw   V2 freq/ctrl/pw  | vol")
    for f, row, vol in samples:
        s = "  ".join(f"${r[0]:04X}/${r[1]:02X}/${r[2]:03X}" for r in row)
        print(f" {f:5d} | {s} | {vol}")

    print(f"\nmaster volume nibbles seen: {sorted(vol_seen)}")
    for v in range(3):
        print(f" osc{v+1}: gate-on {gate_on[v]:5d}/{FRAMES} frames, "
              f"freq!=0 {freq_nz[v]:5d}, waveform hi-nibbles {sorted(hex(w) for w in wf_seen[v])}")
        audible = gate_on[v] and freq_nz[v] and any(w for w in wf_seen[v]) and any(vol_seen)
        print(f"        -> {'AUDIBLE' if audible else 'SILENT'}")


if __name__ == "__main__":
    main()
