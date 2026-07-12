"""Shared 6502 idiom locators for player reverse engineering.

The recurring building blocks of every player parser (Laxity, DMC, Hubbard,
Sound Monitor, SDI...), extracted so the next parser starts from a tested
library instead of a blank flow-disassembly. Companion knowledge base:
docs/players/PATTERNS.md (the technique catalog — symptom -> exploit).

Everything here is RELOCATION-SAFE: locate by short distinctive instruction
runs with wildcarded operands, then extract the operands — never by fixed
offsets (editors assemble the player per song, so addresses shift; see
PATTERNS.md P6).
"""
from typing import List, Optional, Tuple

WILD = -1


def find_pattern(d, pat: List[int], start: int = 0) -> Optional[int]:
    """First offset of `pat` in d from `start`; -1 entries are wildcards.

    The workhorse of relocation-safe location: encode the *idiom* (opcodes +
    structural literals), wildcard the operands, read the addresses out of
    the match. Verify extracted data addresses point at sane file offsets —
    a pattern match with garbage operands is a FALSE LOCATE (PATTERNS.md D2).
    """
    n = len(pat)
    for i in range(start, len(d) - n + 1):
        ok = True
        for k, b in enumerate(pat):
            if b >= 0 and d[i + k] != b:
                ok = False
                break
        if ok:
            return i
    return None


def find_all(d, pat: List[int]) -> List[int]:
    """Every offset matching `pat` — use to enumerate ALL writers/readers of
    a state cell (flow-following disassembly misses paths behind unfollowed
    dispatch; raw greps don't — PATTERNS.md D6)."""
    out = []
    i = 0
    while True:
        i = find_pattern(d, pat, i)
        if i is None:
            return out
        out.append(i)
        i += 1


def word_at(d, off: int) -> int:
    """Little-endian word (the operand of an absolute-mode instruction)."""
    return d[off] | (d[off + 1] << 8)


def scan_freq_tables(d, la: int, gap: int = 0x60, entries: int = 96,
                     octave_from: int = 36, octave_to: int = 60,
                     min_hits: int = 20) -> Optional[Tuple[int, int]]:
    """Content-verified freq-table locate -> (lo_addr, hi_addr) or None.

    Collects every `LDA $nnnn,Y` read target, then looks for two targets
    exactly `gap` apart whose combined 16-bit words DOUBLE per octave.
    Content verification beats lone byte patterns for data tables
    (PATTERNS.md D3): a code idiom can match anywhere, but only a real
    frequency table doubles every 12 entries.

    Proven on the SDI corpus (gap $60) — Laxity/DMC-style tables with other
    gaps: pass `gap` accordingly.
    """
    reads = set()
    raw = bytes(d)
    k = 0
    while True:
        k = raw.find(b"\xb9", k)          # LDA abs,Y
        if k < 0 or k + 2 >= len(raw):
            break
        a = raw[k + 1] | (raw[k + 2] << 8)
        if la <= a < la + len(d) - entries - 1:
            reads.add(a)
        k += 1
    for a in sorted(reads):
        for lo_a, hi_a in ((a + gap, a), (a, a + gap)):
            if lo_a not in reads or hi_a not in reads:
                continue
            f = [(d[lo_a - la + n] | (d[hi_a - la + n] << 8))
                 for n in range(entries)]
            hits = sum(1 for n in range(octave_from, octave_to)
                       if f[n] and abs(f[n + 12] / f[n] - 2) < 0.02)
            if hits >= min_hits:
                return lo_a, hi_a
    return None


def follow_immediate_poke(d, la: int, imm_off: int) -> Optional[int]:
    """The self-modified-immediate follower (PATTERNS.md: tempo pokes).

    `imm_off` = the file offset of an immediate operand (e.g. the reload in
    `LDA #imm / STA $tempo`). Players poke such immediates from song data at
    init (`LDA $src / STA $imm_addr`), so the static byte is pre-poke junk.
    Returns the poked SOURCE value if an `AD src STA imm_addr` writer exists,
    else None (caller keeps the static byte).

    Found the B-variant tempo bug in SDI (static 6 vs real 1).
    """
    imm_addr = la + imm_off
    j = find_pattern(d, [0xAD, WILD, WILD, 0x8D,
                         imm_addr & 0xFF, (imm_addr >> 8) & 0xFF])
    if j is None:
        return None
    src = word_at(d, j + 1)
    if 0 <= src - la < len(d):
        return d[src - la]
    return None


def bounded_init(d, la: int, init_addr: int, a_reg: int = 0,
                 max_steps: int = 2_000_000):
    """Run INIT in py65 until RTS, a JMP-to-self spin, or the step cap.

    For the wrapper / self-installed-IRQ class (play=$0000: Galway, SDI V —
    PATTERNS.md P3): INIT installs a raster handler and never returns, so a
    plain call-runner's loop guard trips. Detects the terminal spin by
    PC == previous PC (JMP *). Vectors often install BEFORE the module init
    runs — do NOT stop on the first vector write (SDI V left voices unset).

    Returns (memory_image_bytes, irq_vector, hw_vector) or (None, 0, 0) if
    py65 is unavailable or the image can't load.
    """
    try:
        from py65.devices.mpu6502 import MPU
    except ImportError:
        return None, 0, 0
    mpu = MPU()
    for i in range(0x10000):
        mpu.memory[i] = 0
    n = min(len(d), 0x10000 - la)
    if n <= 0:
        return None, 0, 0
    for i in range(n):
        mpu.memory[la + i] = d[i]
    # RTS sentinel: pops $FFFE, increments to $FFFF
    mpu.memory[0x0100 | mpu.sp] = 0xFF
    mpu.sp = (mpu.sp - 1) & 0xFF
    mpu.memory[0x0100 | mpu.sp] = 0xFE
    mpu.sp = (mpu.sp - 1) & 0xFF
    mpu.pc = init_addr
    mpu.a = a_reg
    prev = -1
    for _ in range(max_steps):
        pc = mpu.pc
        if pc >= 0xFFFE:                  # returned
            break
        if pc == prev:                    # JMP-to-self spin
            break
        prev = pc
        mpu.step()
    irq = mpu.memory[0x314] | (mpu.memory[0x315] << 8)
    hw = mpu.memory[0xFFFE] | (mpu.memory[0xFFFF] << 8)
    return bytes(mpu.memory), irq, hw
