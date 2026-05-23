"""ch_seq_ptr patch safety gate (v3.5.28).

The `_inject_laxity_raw_np21` path patches the bytes at $1A1C-$1A21 in the
embedded NP21 binary, repointing them at the shadow buffer. For a standard
NP21 player (Stinsen/Unboxed) this is intentional — the player reads
ch_seq_ptr to fetch the per-voice sequence stream; redirecting it through
the shadow buffer is what makes criterion-3 edit propagation possible.

For OTHER files the bytes at $1A1C-$1A21 happen to LOOK like in-range
pointers (passing `_ptrs_in_range_check`) but are NOT actually ch_seq_ptr
— they are part of some other data table that the player reads. Patching
them corrupts that data and produces wrong audio.

Canonical example: Dark_Fun.sid (2023 Genesis Project). Bytes at
$1A1C-$1A21 = `54 7C 1B 1B 1B 1B` → pointers $1B54/$1B7C/$1B1B which DO
land on valid-looking NP21 byte streams. But the player at $10C1 reads
`LDA $1A1E,Y` (one byte, Y-indexed) — using $1A1E as a data table, not
as voice-2's ch_seq_ptr lo byte. After patch, $1A1E = $1F (shadow addr
low byte) instead of $1B → wrong data → spurious register writes.

The gate: emulate the patch under py65 with the shadow buffer mirroring
the original byte streams, and compare SID-register-write tuples against
the unpatched original. If they match, the patch is functionally
transparent (= the player uses ch_seq_ptr as designed); apply it. If
they differ, the patch is corrupting something else; skip it.
"""
from __future__ import annotations
from typing import List, Tuple


def _trace_register_writes(c64_data: bytes, sid_la: int,
                            init_addr: int, play_addr: int,
                            shadow_overlay: dict | None = None,
                            n_play: int = 5,
                            max_init_cyc: int = 20_000,
                            max_play_cyc: int = 100_000,
                            early_exit_check=None
                            ) -> List[Tuple[int, int, int]]:
    """Run py65 INIT + n PLAY ticks; return list of (frame, reg_off, value)
    writes to $D400-$D418.

    `max_init_cyc` is bounded — some players have CIA-IRQ-style INIT that
    busy-waits and never naturally exits. 200k cycles is generous enough
    for legitimate INIT (most complete in <50k) while keeping wall-clock
    cost ~1-2 seconds per file.

    `early_exit_check`, if provided, is called after each write; if it
    returns True, tracing terminates immediately. Used by the safety
    gate to detect a divergence and skip remaining work.
    """
    from py65.devices.mpu6502 import MPU
    mpu = MPU()
    for i in range(0x10000):
        mpu.memory[i] = 0
    for i, b in enumerate(c64_data):
        mpu.memory[(sid_la + i) & 0xFFFF] = b
    if shadow_overlay:
        for addr, byte in shadow_overlay.items():
            mpu.memory[addr & 0xFFFF] = byte

    writes: List[Tuple[int, int, int]] = []
    frame_no = [0]
    abort = [False]
    real = mpu.memory

    class Obs(list):
        def __getitem__(self, a):
            return list.__getitem__(self, a)

        def __setitem__(self, a, v):
            if isinstance(a, int) and 0xD400 <= a <= 0xD418:
                writes.append((frame_no[0], a - 0xD400, v))
                if early_exit_check is not None and early_exit_check(writes):
                    abort[0] = True
            list.__setitem__(self, a, v)

    mpu.memory = Obs(real)

    def run(entry: int, max_cyc: int) -> None:
        mpu.pc = entry
        sent = 0xFFF0
        mpu.memory[0x0100 | mpu.sp] = (sent >> 8) & 0xFF
        mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.memory[0x0100 | mpu.sp] = sent & 0xFF
        mpu.sp = (mpu.sp - 1) & 0xFF
        cyc = 0
        while cyc < max_cyc:
            if mpu.pc == sent or abort[0]:
                return
            mpu.step()
            cyc += 1

    mpu.a = 0
    run(init_addr, max_init_cyc)
    for f in range(n_play):
        if abort[0]:
            break
        frame_no[0] = f
        run(play_addr, max_play_cyc)
    return writes


def is_ch_seq_patch_safe(c64_data: bytes, sid_la: int,
                          init_addr: int, play_addr: int,
                          lo_off: int, hi_off: int,
                          shadow_base: int = 0x3000,
                          n_play: int = 16) -> bool:
    """Return True if patching $1A1C-$1A21 with shadow_base addresses
    produces identical SID register writes vs the unpatched original.

    Tests the FUNCTIONAL invariant of the shadow-buffer architecture: if
    the player reads ch_seq_ptr → shadow → mirrored bytes, audio must
    match the original (the stream content is byte-for-byte equal).
    If audio DIFFERS, the patch is touching memory used for something
    other than ch_seq_ptr.

    Args:
        c64_data: original SID binary (starts at sid_la in memory).
        sid_la: load address.
        init_addr, play_addr: PSID entry points.
        lo_off, hi_off: ch_seq_ptr lo/hi table offsets WITHIN c64_data
                        (= absolute addr - sid_la).
        shadow_base: scratch RAM page for the test shadow buffer (must
                     be outside the binary; default $3000).
        n_play: number of PLAY ticks to simulate.

    Returns:
        True  → patch is safe (player uses these bytes as ch_seq_ptr).
        False → patch corrupts audio (player uses bytes for other data).
    """
    # Validate offsets are inside c64_data with room for 3 voice slots
    if (lo_off < 0 or hi_off < 0
        or lo_off + 3 > len(c64_data)
        or hi_off + 3 > len(c64_data)):
        return False

    orig_ptrs = [(c64_data[hi_off + v] << 8) | c64_data[lo_off + v]
                 for v in range(3)]
    # Pointers must be in-range to be testable
    if not all(sid_la <= p < sid_la + len(c64_data) for p in orig_ptrs):
        return False

    # Original audio trace
    writes_orig = _trace_register_writes(c64_data, sid_la, init_addr,
                                          play_addr, n_play=n_play)

    # Build patched c64_data: $1A1C..$1A21 → shadow_base addresses
    patched = bytearray(c64_data)
    for v in range(3):
        sh = shadow_base + v * 0x100
        patched[lo_off + v] = sh & 0xFF
        patched[hi_off + v] = (sh >> 8) & 0xFF

    # Shadow overlay: copy the bytes from orig_ptrs[v] into shadow slot v
    # until $7F terminator (or 256 bytes max).
    overlay = {}
    for v in range(3):
        sh = shadow_base + v * 0x100
        src_addr = orig_ptrs[v]
        for j in range(256):
            src_off = src_addr - sid_la + j
            if src_off < 0 or src_off >= len(c64_data):
                overlay[sh + j] = 0x7F
                break
            b = c64_data[src_off]
            overlay[sh + j] = b
            if b == 0x7F:
                break

    # Early-exit check: stop tracing the patched simulation as soon as
    # its writes diverge from the original (which we already traced).
    # This cuts gate runtime on UNSAFE files from ~1-2s to ~100ms.
    def _diverged(writes_so_far):
        idx = len(writes_so_far) - 1
        return idx >= len(writes_orig) or writes_orig[idx] != writes_so_far[idx]

    writes_patched = _trace_register_writes(bytes(patched), sid_la,
                                             init_addr, play_addr,
                                             shadow_overlay=overlay,
                                             n_play=n_play,
                                             early_exit_check=_diverged)

    # Early-exit means we already detected divergence
    if len(writes_patched) < len(writes_orig):
        # Either aborted on divergence, or patched produced fewer writes
        # → not safe.
        return False
    if len(writes_orig) != len(writes_patched):
        return False
    for a, b in zip(writes_orig, writes_patched):
        if a != b:
            return False
    return True
