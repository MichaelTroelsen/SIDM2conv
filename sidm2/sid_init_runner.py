"""Run a SID file's INIT routine in a 6502 emulator and return the
post-init memory snapshot.

Used by `_build_np21_sf2_edit_area` to recover `ch_seq_ptr` for
"Class B" Laxity NP21 files — those whose binary leaves the
ch_seq_ptr table at $1A1C/$1A1F uninitialized (the player's INIT
populates it at runtime). Without this, the editor view is
empty placeholder; with it, real per-voice sequences are extracted.

Approach:
1. Set up py65 MPU's full 64KB RAM.
2. Copy c64_data into emulated memory at sid_la.
3. Push sentinel return address $FFFF onto the stack.
4. Set PC = init_addr.
5. Step the MPU until PC reaches $FFFF or a budget of cycles is
   exhausted.
6. Return the post-INIT memory.

Caveats:
- 64KB RAM model. No C64 ROMs (KERNAL/BASIC) are available — INIT
  routines that JSR into $A000/$E000 will fail.
- I/O writes to $D400-$D41F (SID) are accepted as RAM writes.
- VIC-II at $D000-$D3FF, CIA at $DC00-$DDFF: any reads return 0.
- Most NP21 INIT routines are self-contained and don't need ROMs.
  Files that do (e.g., some Hubbard players) will have the runner
  fail or return garbage — the writer falls back to the original
  uninitialized-pointer extraction in that case.
"""
from __future__ import annotations

from typing import Optional


def run_init(c64_data: bytes, sid_la: int, init_addr: int,
             max_cycles: int = 1_000_000, subtune: int = 0) -> Optional[bytearray]:
    """Run the SID's INIT routine in a 6502 emulator and return
    the 64KB memory image post-init.

    Args:
        subtune: value passed in A (PSID subtune index, 0-based). Some
            players leave the per-voice pointers unset / spin forever for
            certain subtunes, so callers may sweep this.

    Returns None if the run errors out (unimplemented opcode, infinite
    loop guard tripped, etc.). The caller should fall back to
    pre-init extraction.
    """
    try:
        from py65.devices.mpu6502 import MPU
    except ImportError:
        return None

    mpu = MPU()
    # py65's default memory is a 64KB list-of-int. Reset it explicitly
    # (some versions don't zero-fill on construct).
    for i in range(0x10000):
        mpu.memory[i] = 0

    # Load c64_data at sid_la
    end = min(sid_la + len(c64_data), 0x10000)
    n = end - sid_la
    if n <= 0:
        return None
    for i in range(n):
        mpu.memory[sid_la + i] = c64_data[i]

    # Stack: push return address $FFFF (high byte first, then low byte
    # — RTS pops PC-1 then increments)
    sentinel_pc = 0xFFFE   # RTS will pop $FFFE and increment to $FFFF
    mpu.memory[0x0100 | mpu.sp] = (sentinel_pc >> 8) & 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF
    mpu.memory[0x0100 | mpu.sp] = sentinel_pc & 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF

    # Set up PC for INIT
    mpu.pc = init_addr
    # Standard PSID convention: A=subtune (0 = first subtune), X/Y=0
    mpu.a = subtune & 0xFF
    mpu.x = 0
    mpu.y = 0

    # Step the CPU until PC hits the sentinel ($FFFF) or budget exhausted.
    cycles = 0
    try:
        while cycles < max_cycles:
            if mpu.pc == 0xFFFF:
                # INIT returned cleanly via the sentinel
                break
            mpu.step()
            cycles += 1
        else:
            # Budget exhausted — INIT may be in an infinite loop
            return None
    except Exception:
        # Any emulator error (unknown opcode, bad branch, etc.)
        return None

    # Return a copy of memory as bytearray
    return bytearray(mpu.memory[i] for i in range(0x10000))


def trace_play_reads(c64_data: bytes, sid_la: int, init_addr: int,
                     play_addr: int, n_ticks: int = 3
                     ) -> Optional[tuple[bytearray, set[int]]]:
    """Run INIT once, then PLAY n_ticks times, recording every memory
    read address. Returns (final_memory, set_of_read_addresses) or None
    on emulator error.

    The voice ch_seq_ptr table will be in the read set every PLAY tick
    — that's how the player advances each voice's stream.
    """
    try:
        from py65.devices.mpu6502 import MPU
    except ImportError:
        return None

    # Track reads via a small wrapper around the memory list. py65's
    # MPU calls memory[addr] for reads, both via __getitem__ and
    # potentially via slice. We capture all reads by replacing memory
    # with a list-like object.
    reads: set[int] = set()

    class TracingMemory(list):
        def __getitem__(self, idx):
            if isinstance(idx, int):
                if 0x0000 <= idx <= 0xFFFF:
                    reads.add(idx)
                return super().__getitem__(idx)
            return super().__getitem__(idx)
        # __setitem__: pass through, no tracing needed for our purpose

    mpu = MPU()
    new_mem = TracingMemory([0] * 0x10000)
    # Copy c64_data
    end = min(sid_la + len(c64_data), 0x10000)
    n = end - sid_la
    if n <= 0:
        return None
    for i in range(n):
        new_mem[sid_la + i] = c64_data[i]
    mpu.memory = new_mem

    def call(entry):
        sentinel = 0xFFFE
        new_mem[0x0100 | mpu.sp] = (sentinel >> 8) & 0xFF
        mpu.sp = (mpu.sp - 1) & 0xFF
        new_mem[0x0100 | mpu.sp] = sentinel & 0xFF
        mpu.sp = (mpu.sp - 1) & 0xFF
        mpu.pc = entry
        for _ in range(200_000):
            try:
                mpu.step()
            except Exception:
                return False
            if mpu.pc == 0xFFFF:
                return True
        return False

    mpu.a = mpu.x = mpu.y = 0
    if not call(init_addr):
        return None

    # Clear reads from INIT — only care about PLAY-time reads
    reads.clear()

    for _ in range(n_ticks):
        if not call(play_addr):
            return None

    # Snapshot post-final-PLAY memory. Bypass TracingMemory.__getitem__
    # (which would add every i to `reads`, polluting the set with all
    # 65536 addresses and making it useless as a candidate filter).
    snapshot = bytearray(0x10000)
    for i in range(0x10000):
        snapshot[i] = list.__getitem__(new_mem, i)
    return snapshot, reads


def recover_ch_seq_ptr(c64_data: bytes, sid_la: int, init_addr: int,
                       ch_seq_lo: int = 0x1A1C,
                       ch_seq_hi: int = 0x1A1F) -> Optional[list[int]]:
    """Return the post-INIT ch_seq_ptr values per voice, or None on failure.

    Args:
        ch_seq_lo: absolute C64 address of the lo-byte table (3 bytes)
        ch_seq_hi: absolute C64 address of the hi-byte table (3 bytes)

    Default addresses match the Stinsen/Unboxed NP21 layout where the
    binary loads at $1000 — ch_seq_ptr table sits at $1A1C/$1A1F. For
    binaries loaded elsewhere, the same OFFSETS into the binary apply
    (binary+0x0A1C / binary+0x0A1F), so callers usually pass
    ch_seq_lo = sid_la + 0x0A1C, ch_seq_hi = sid_la + 0x0A1F.
    """
    mem = run_init(c64_data, sid_la, init_addr)
    if mem is None:
        return None
    ptrs = []
    for v in range(3):
        if ch_seq_lo + v >= 0x10000 or ch_seq_hi + v >= 0x10000:
            return None
        lo = mem[ch_seq_lo + v]
        hi = mem[ch_seq_hi + v]
        ptrs.append((hi << 8) | lo)
    return ptrs
