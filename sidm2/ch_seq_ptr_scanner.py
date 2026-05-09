"""Auto-detect the ch_seq_ptr table location for an arbitrary NP21 player.

Different NP21 variants put the voice pointer table at different addresses
(Stinsen-class: $1A1C/$1A1F; native Laxity NewPlayer V21 variants:
unknown). Rather than RE each variant by hand, this module scans
post-INIT memory for byte patterns that LOOK like a 3-byte voice
pointer table and validates them by walking the sequence at each
candidate address.

Approach:
1. Run the SID's INIT in py65 (sidm2.sid_init_runner). Get 64KB snapshot.
2. Run a few PLAY ticks too — some players initialise their pointers
   on the first PLAY rather than during INIT.
3. Scan the binary's address range for 6-byte windows of the form
   `[lo0][lo1][lo2] [hi0][hi1][hi2]` where each
   `(hiK << 8) | loK` is INSIDE the binary range AND walking from
   that address yields a plausible NP21 sequence (terminator at
   $FF or $7F within 256 bytes; reasonable mix of byte values).
4. Score each candidate. Highest-scoring window's first 3 bytes
   = ch_seq_ptr lo table; next 3 bytes = hi table.

Scoring weights known-good NP21 sequence shape (prefix bytes
0xA0-0xBF for instrument changes, 0x80-0x9F durations, 0x01-0x6F
notes, etc.).
"""
from __future__ import annotations
from typing import Optional, Tuple

from sidm2.sid_init_runner import run_init


def _walk_sequence(mem, addr: int, sid_la: int, c64_len: int,
                   max_bytes: int = 256) -> Optional[bytes]:
    """Walk an NP21 sequence from `addr`, return its body or None.

    Body must terminate at $FF (loop) or $7F (end) within max_bytes.
    """
    if not (sid_la <= addr < sid_la + c64_len):
        return None
    body = bytearray()
    for j in range(max_bytes):
        if addr + j >= 0x10000:
            return None
        b = mem[addr + j]
        if b == 0xFF or b == 0x7F:
            return bytes(body)
        body.append(b)
    return None  # exceeded max without terminator


def _score_sequence(body: bytes) -> int:
    """Score how "NP21-like" a candidate sequence body is.

    Discriminators:
      - body must start with $A0-$BF (instrument prefix) — canonical
        NP21 voice stream beginning. Hard reject otherwise.
      - body must have >= 60% of its bytes below $80 (notes/rests/
        durations dominate real NP21; uniform random bytes (e.g.,
        machine code) only have ~50% < $80 statistically).
      - body must have at least 2 of {instr, dur, note, cmd} traits.
      - body must NOT be mostly zeros or have very low byte-value
        entropy.
    """
    if not body or len(body) < 8:
        return -1000

    if not (0xA0 <= body[0] <= 0xBF):
        return -1000

    # Statistical signature: NP21 voice streams have ~75-85% of bytes
    # in the note/rest/duration range ($00-$9F). Random machine code
    # is more uniform — closer to 50-65%. A 70% floor cleanly separates
    # real voice streams from random code byte runs.
    n_below_a0 = sum(1 for b in body if b < 0xA0)
    if n_below_a0 / len(body) < 0.70:
        return -1000

    has_instr = any(0xA0 <= b <= 0xBF for b in body)
    has_dur   = any(0x80 <= b <= 0x9F for b in body)
    has_note  = any(0x01 <= b <= 0x6F for b in body)
    has_cmd   = any(0xC0 <= b <= 0xFE for b in body)
    n_traits  = sum([has_instr, has_dur, has_note, has_cmd])
    if n_traits < 2:
        return -1000

    if body.count(0x00) > len(body) // 2:
        return -1000
    if len(set(body)) < 5 and len(body) > 15:
        return -1000

    score = 0
    if has_instr: score += 5
    if has_dur:   score += 3
    if has_note:  score += 5
    if has_cmd:   score += 2
    # Length: real NP21 voice streams loop quickly, typically 20-100
    # bytes per voice segment. >200 bytes is suspicious (could indicate
    # walking past the real terminator into adjacent data).
    if 20 <= len(body) <= 100:  score += 5
    elif 100 < len(body) <= 200: score += 2
    elif len(body) > 200:        score -= 3
    return score


def _scan_table_at(mem, table_lo: int, table_hi: int,
                   sid_la: int, c64_len: int) -> Optional[Tuple[int, list[int], list[int]]]:
    """Try interpreting `mem[table_lo..lo+3]` + `mem[table_hi..hi+3]` as
    voice pointer lo/hi tables. Returns (total_score, ptrs, body_lens)
    or None if not all 3 voices yield valid sequences.
    """
    if (table_lo + 3 > 0x10000 or table_hi + 3 > 0x10000):
        return None
    ptrs = []
    bodies = []
    for v in range(3):
        lo = mem[table_lo + v]
        hi = mem[table_hi + v]
        addr = (hi << 8) | lo
        ptrs.append(addr)
        body = _walk_sequence(mem, addr, sid_la, c64_len)
        if body is None:
            return None
        bodies.append(body)
    total_score = sum(_score_sequence(b) for b in bodies)
    return total_score, ptrs, [len(b) for b in bodies]


def find_ch_seq_ptr_in_memory(mem: bytearray, sid_la: int, c64_len: int,
                              search_lo: int = 0x0100,
                              search_hi: int = 0x2400,
                              min_score: int = 30,
                              ) -> Optional[Tuple[int, int, list[int], int]]:
    """Find the (lo_table_addr, hi_table_addr) pair in memory.

    Constrains hi_addr = lo_addr + 3 (the universal NP21 packing —
    Stinsen confirms this and it's the most space-efficient layout
    for a 3-byte-by-3-byte table). For each candidate lo_addr,
    walks the 3 voice sequences from `(mem[lo+v], mem[hi+v])` and
    scores the resulting bodies. Returns the highest-scoring pair
    if its score exceeds min_score.

    Returns:
        (lo_table_addr, hi_table_addr, ptrs, score) or None.
    """
    best = None  # (score, lo, hi, ptrs)
    upper = min(search_hi, 0x10000) - 6

    for lo_addr in range(search_lo, upper):
        hi_addr = lo_addr + 3
        r = _scan_table_at(mem, lo_addr, hi_addr, sid_la, c64_len)
        if r is None:
            continue
        score, ptrs, body_lens = r
        if best is None or score > best[0]:
            best = (score, lo_addr, hi_addr, ptrs, body_lens)

    if best is None or best[0] < min_score:
        return None
    score, lo, hi, ptrs, _ = best
    return lo, hi, ptrs, score


def find_lda_abs_x_pairs(c64_data: bytes, sid_la: int) -> list[tuple[int, int]]:
    """Statically scan the binary for `LDA abs,X` ($BD lo hi) instructions
    whose operands form a (T, T+3) pair within a small window. The player
    MUST contain such a pair to load the voice ch_seq_ptr lo and hi
    tables, and the table itself sits at the addr T (lo table) + T+3 (hi
    table). This is the strongest fingerprint of the ch_seq_ptr location.

    Returns list of (lo_table_addr, hi_table_addr) candidates.
    """
    OP_LDA_ABS_X = 0xBD
    candidates = []
    seen = set()
    n = len(c64_data)

    # Find all LDA abs,X opcodes
    lda_addrs = []   # list of (instruction_offset, target_addr)
    for off in range(n - 2):
        if c64_data[off] == OP_LDA_ABS_X:
            target = c64_data[off + 1] | (c64_data[off + 2] << 8)
            lda_addrs.append((off, target))

    # Look for pairs (a, b) where b = a + 3 and the two LDAs are within
    # 16 bytes of each other (typical "load lo table, load hi table"
    # idiom in NP21 player loops).
    for i, (off_i, t_i) in enumerate(lda_addrs):
        for off_j, t_j in lda_addrs[i+1 : i+10]:    # nearby instructions
            if off_j - off_i > 32:
                break
            if t_j == t_i + 3:
                key = (t_i, t_j)
                if key not in seen:
                    seen.add(key)
                    candidates.append(key)
            elif t_i == t_j + 3:
                key = (t_j, t_i)
                if key not in seen:
                    seen.add(key)
                    candidates.append(key)
    return candidates


def detect_ch_seq_ptr(c64_data: bytes, sid_la: int, init_addr: int,
                     play_addr: Optional[int] = None,
                     n_play_ticks: int = 3) -> Optional[Tuple[int, int, list[int], int]]:
    """High-level: find ch_seq_ptr by combining static disasm
    (LDA abs,X pair detection) with runtime memory-read tracing
    during PLAY ticks. The voice ch_seq_ptr table will be in the
    PLAY-time read set, so we restrict candidates to that intersection.

    Returns (lo_table_addr, hi_table_addr, voice_seq_addrs, score) or None.
    """
    # Try to use runtime tracing if we have play_addr (preferred)
    play_reads: set[int] = set()
    mem: Optional[bytearray] = None
    if play_addr is not None and n_play_ticks > 0:
        from sidm2.sid_init_runner import trace_play_reads
        r = trace_play_reads(c64_data, sid_la, init_addr, play_addr, n_play_ticks)
        if r is not None:
            mem, play_reads = r

    # Fall back to plain INIT-only run
    if mem is None:
        mem = run_init(c64_data, sid_la, init_addr)
        if mem is None:
            return None

    # Static scan: find `LDA abs,X` pairs that look like ch_seq_ptr loads
    pairs = find_lda_abs_x_pairs(c64_data, sid_la)

    # Also: build a set of (lo, hi) candidates from PLAY-read addresses.
    # If two consecutive read addresses (or any pair with delta=3) both
    # appear, that's a strong candidate for ch_seq_ptr table location.
    if play_reads:
        for addr in sorted(play_reads):
            if (addr + 3) in play_reads:
                pairs.append((addr, addr + 3))
        # Also generic offset: voice 0/1/2 reads consecutive addrs
        for addr in sorted(play_reads):
            if all((addr + d) in play_reads for d in (0, 1, 2, 3, 4, 5)):
                pairs.append((addr, addr + 3))

    # Deduplicate and validate
    seen = set()
    best = None
    for lo_addr, hi_addr in pairs:
        if (lo_addr, hi_addr) in seen:
            continue
        seen.add((lo_addr, hi_addr))
        if lo_addr + 3 > 0x10000 or hi_addr + 3 > 0x10000:
            continue
        r = _scan_table_at(mem, lo_addr, hi_addr, sid_la, len(c64_data))
        if r is None:
            continue
        score, ptrs, body_lens = r
        # Reject candidates where all 3 voice ptrs are identical
        if len(set(ptrs)) < 2:
            continue
        # The PLAY-read set helps as a *filter* (must appear there)
        # but not as a tiebreaker — code addresses also appear in
        # play_reads because of instruction fetch. We require that all
        # 6 bytes of the table (lo[0..2] + hi[0..2]) were read during
        # PLAY: that's specific to data reads of the voice pointer
        # table, not instruction fetches which read sequentially.
        if play_reads:
            need = [lo_addr + v for v in range(3)] + [hi_addr + v for v in range(3)]
            if not all(a in play_reads for a in need):
                continue
        if best is None or score > best[0]:
            best = (score, lo_addr, hi_addr, ptrs)

    # Fallback: brute-force scan if nothing passed
    if best is None:
        r = find_ch_seq_ptr_in_memory(
            mem, sid_la, len(c64_data),
            search_lo=sid_la, search_hi=sid_la + len(c64_data))
        if r is not None:
            lo_addr, hi_addr, ptrs, score = r
            best = (score, lo_addr, hi_addr, ptrs)

    # Reject candidates whose score is non-positive. The scorer applies
    # large negative penalties (-1000) for hard-fail conditions; a
    # summed score <= 0 means at least one voice body tripped a hard
    # reject, so the candidate is not a real ch_seq_ptr.
    if best is None or best[0] <= 0:
        return None
    score, lo, hi, ptrs = best
    return lo, hi, ptrs, score
