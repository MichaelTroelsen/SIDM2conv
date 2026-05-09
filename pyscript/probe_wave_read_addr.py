"""Phase B.0: trace which memory addresses the NP21 player reads when
it writes to osc<v>_control ($D404/$D40B/$D412). The LDA-source address
right before each STA into those registers IS the wave-read location.

Wraps a py65 MPU with a memory access recorder that buffers the last
N reads. When a write to $D404, $D40B, or $D412 is detected, we
emit the most-recent read-source addr (and value) — that's the
wave-table cell the player just transferred to the SID.

Usage:  py -3 pyscript/probe_wave_read_addr.py SID/Stinsens_Last_Night_of_89.sid
"""
import sys
from collections import Counter, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from py65.devices.mpu6502 import MPU


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


# SID register names + map of "interesting" registers per voice
SID_BASE = 0xD400
OSC_CONTROL = {0xD404: 'osc1_control', 0xD40B: 'osc2_control', 0xD412: 'osc3_control'}
OSC_FREQ_LO = {0xD400: 'osc1_freq_lo', 0xD407: 'osc2_freq_lo', 0xD40E: 'osc3_freq_lo'}
OSC_FREQ_HI = {0xD401: 'osc1_freq_hi', 0xD408: 'osc2_freq_hi', 0xD40F: 'osc3_freq_hi'}
OSC_AD      = {0xD405: 'osc1_attack_decay', 0xD40C: 'osc2_attack_decay', 0xD413: 'osc3_attack_decay'}
OSC_SR      = {0xD406: 'osc1_sustain_release', 0xD40D: 'osc2_sustain_release', 0xD414: 'osc3_sustain_release'}


def trace(path: str, n_play_ticks: int = 30, max_recent_reads: int = 8):
    sid_la, init, play, c64 = parse_psid(path)
    print(f'\n=== {Path(path).name} ===')
    print(f'  load=${sid_la:04X} init=${init:04X} play=${play:04X}')

    mpu = MPU()
    for i in range(0x10000): mpu.memory[i] = 0
    n = min(len(c64), 0x10000 - sid_la)
    for i in range(n): mpu.memory[sid_la + i] = c64[i]

    # Wrap memory with a tracing list
    recent_reads: deque = deque(maxlen=max_recent_reads)
    write_sources: Counter = Counter()    # (sid_reg, src_addr) → count
    write_records: list = []              # (frame, pc, sid_reg, src_addr, src_val)

    # Optional: a SECOND-level trace target. When set, also record
    # WRITES to this address, and link each write back to the most-
    # recent read that provided the value. Used to chain back from
    # an "intermediate" address (e.g. $15B1) to the static wave table.
    chase_addrs = sys.argv[2:] if len(sys.argv) > 2 else []
    chase_set = {int(x, 16) for x in chase_addrs}
    chase_records: list = []   # (addr, source_addr, source_val)

    class TracingMemory(list):
        def __getitem__(self, idx):
            if isinstance(idx, int) and 0x0000 <= idx <= 0xFFFF:
                # Skip recording reads of SID registers themselves
                if not (0xD400 <= idx <= 0xD41F):
                    recent_reads.append((idx, super().__getitem__(idx)))
            return super().__getitem__(idx)

        def __setitem__(self, idx, value):
            if isinstance(idx, int) and idx in chase_set:
                if recent_reads:
                    matched = None
                    for src_addr, src_val in reversed(list(recent_reads)):
                        if src_val == (value & 0xFF):
                            matched = (src_addr, src_val); break
                    chase_records.append((idx,
                                          matched[0] if matched else None,
                                          value & 0xFF))
            if isinstance(idx, int) and 0xD400 <= idx <= 0xD41F:
                # Found a SID register write. Look at recent reads.
                if recent_reads:
                    # The matching read should be at most 1-3 reads back
                    # (LDA src; ...; STA dst is a couple insns).
                    # We take the most recent non-zero address read whose
                    # value matches the byte being written.
                    matched = None
                    for src_addr, src_val in reversed(list(recent_reads)):
                        if src_val == (value & 0xFF):
                            matched = (src_addr, src_val)
                            break
                    if matched is None and recent_reads:
                        # No exact value match — fall back to the most
                        # recent non-instruction-fetch read. (Skip reads
                        # at the current PC region.)
                        matched = recent_reads[-1]
                    write_records.append((current_frame[0], mpu.pc, idx,
                                          matched[0] if matched else None,
                                          value & 0xFF))
            return super().__setitem__(idx, value)

    new_mem = TracingMemory([0] * 0x10000)
    n = min(len(c64), 0x10000 - sid_la)
    for i in range(n): new_mem[sid_la + i] = c64[i]
    mpu.memory = new_mem

    def call(entry):
        sentinel = 0xFFFE
        new_mem[0x0100 | mpu.sp] = (sentinel >> 8) & 0xFF
        mpu.sp = (mpu.sp - 1) & 0xFF
        new_mem[0x0100 | mpu.sp] = sentinel & 0xFF
        mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.pc = entry
        for _ in range(200_000):
            try: mpu.step()
            except Exception: return False
            if mpu.pc == 0xFFFF: return True
        return False

    mpu.a = mpu.x = mpu.y = 0
    current_frame = [0]   # mutable so the closure can update
    if not call(init):
        print('  INIT failed'); return

    recent_reads.clear()
    for tick in range(n_play_ticks):
        current_frame[0] = tick
        if not call(play):
            print(f'  PLAY tick {tick}: did not return'); break

    # Aggregate by (sid_reg, src_addr)
    print(f'  recorded {len(write_records)} SID register writes across {n_play_ticks} ticks')
    by_reg = {}
    for frame, pc, sid_reg, src_addr, src_val in write_records:
        by_reg.setdefault(sid_reg, []).append((src_addr, src_val))

    # Show osc<v>_control sources
    for reg in (0xD404, 0xD40B, 0xD412):
        if reg not in by_reg: continue
        print(f'\n  {OSC_CONTROL[reg]} (${reg:04X}) — {len(by_reg[reg])} writes:')
        # Collect source addrs that appear MOST often
        addrs = Counter(addr for addr, _ in by_reg[reg] if addr is not None)
        for addr, n in addrs.most_common(5):
            sample_vals = sorted(set(v for a, v in by_reg[reg] if a == addr))
            sv = ','.join(f'${v:02X}' for v in sample_vals[:6])
            print(f'    src=${addr:04X}  count={n}  values seen: [{sv}{"…" if len(sample_vals)>6 else ""}]')

    if chase_records:
        print(f'\n  --- chase report: writes to {[hex(a) for a in chase_set]} ---')
        by_chase: dict = {}
        for addr, src_addr, src_val in chase_records:
            by_chase.setdefault(addr, []).append((src_addr, src_val))
        for addr, recs in by_chase.items():
            print(f'  ${addr:04X} — {len(recs)} writes')
            srcs = Counter(s for s, _ in recs if s is not None)
            for s, n in srcs.most_common(5):
                vals = sorted(set(v for ss, v in recs if ss == s))
                sv = ','.join(f'${v:02X}' for v in vals[:6])
                print(f'    src=${s:04X}  count={n}  values: [{sv}{"…" if len(vals)>6 else ""}]')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    for p in sys.argv[1:]:
        trace(p)
