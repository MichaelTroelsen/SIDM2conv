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
      - body[0] must look like a valid NP21 stream byte: any of
        $01-$6F (note), $80-$9F (duration), $A0-$BF (instrument
        prefix), or $C0-$FE (command). Hard reject for $00 / $7E /
        $7F (special markers — invalid as stream start).
      - body must have >= 70% of its bytes below $A0 (notes/rests/
        durations dominate real NP21; uniform random bytes (e.g.,
        machine code) only have ~62% < $A0 statistically).
      - body must have at least 2 of {instr, dur, note, cmd} traits.
      - body must NOT be mostly zeros or have very low byte-value
        entropy.

    The body[0] rule was previously stricter ("must be $A0-$BF
    instrument prefix"), but verified-good Beast voice bodies start
    with a note or duration byte (the player relies on a
    pre-initialised current-instrument from INIT). The other
    discriminators (% < $A0, traits, no zeros, entropy) still filter
    out random byte runs.

    Per-voice scoring contract: -1000 means "hard reject — this voice
    body is illegal NP21 (random bytes, illegal start marker, etc.)".
    Score 0 means "ambiguous, too short to assess reliably" — bodies
    < 8 bytes are typically silent / placeholder voices, not junk.
    `_scan_table_at` sums per-voice scores; treating short bodies as
    -1000 used to poison the total, rejecting otherwise-valid tables
    just because one voice happens to be silent (single-byte terminator
    or 2-3 note stream). Returning 0 lets the other voices' positive
    scores carry the candidate to acceptance (v3.5.6).
    """
    if not body:
        return -1000
    if len(body) < 8:
        return 0

    # body[0] must be a valid NP21 stream byte. Reject $00 (no event)
    # and $7E/$7F (special markers — never legitimate stream start).
    b0 = body[0]
    if b0 == 0x00 or b0 == 0x7E or b0 == 0x7F:
        return -1000
    if not (0x01 <= b0 <= 0xFE):
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
    # Entropy rule: very low byte-set sizes indicate "junk" code-byte
    # runs only if the body is also long. Real NP21 voice streams can
    # be long runs of the same note value (held notes), so we require
    # a fairly low unique count AND a longer body before rejecting.
    if len(set(body)) < 3 and len(body) > 30:
        return -1000

    score = 0
    if has_instr: score += 5
    if has_dur:   score += 3
    if has_note:  score += 5
    if has_cmd:   score += 2
    # Bonus: bodies starting with an instrument prefix ($A0-$BF) are
    # more likely real (Stinsen-class). Bodies starting with notes /
    # durations / commands are also legitimate (Beast-class) but
    # slightly more likely to false-positive on random data.
    if 0xA0 <= b0 <= 0xBF:  score += 3
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
        # Reject candidates where all 3 voice ptrs are identical — that
        # never represents a real 3-voice ch_seq_ptr table. Same filter
        # the static-disasm path applies.
        if len(set(ptrs)) < 2:
            continue
        if best is None or score > best[0]:
            best = (score, lo_addr, hi_addr, ptrs, body_lens)

    if best is None or best[0] < min_score:
        return None
    score, lo, hi, ptrs, _ = best
    return lo, hi, ptrs, score


def find_lda_abs_x_pairs(c64_data: bytes, sid_la: int) -> list[tuple[int, int]]:
    """Backwards-compat shim — see `find_indexed_load_pairs`."""
    return find_indexed_load_pairs(c64_data, sid_la, opcodes=(0xBD,))


# 6502 absolute,indexed load opcodes (3-byte instructions: opcode + lo + hi)
#
#   $BD  LDA abs,X   — most common voice-pointer-load idiom
#   $B9  LDA abs,Y   — alternative; some NP21 variants use Y-indexing
#   $BE  LDX abs,Y   — load X from table[Y]; rare but possible
#   $BC  LDY abs,X   — load Y from table[X]; rare but possible
#
# All four can plausibly appear as a `load lo, load hi` voice-ptr idiom.
# We accept any pair of these instructions whose operands differ by
# exactly 3, regardless of mix.
DEFAULT_LOAD_OPCODES = (0xBD, 0xB9, 0xBE, 0xBC)


def find_indexed_load_pairs(c64_data: bytes, sid_la: int,
                            opcodes: tuple[int, ...] = DEFAULT_LOAD_OPCODES,
                            max_distance: int = 32,
                            ) -> list[tuple[int, int]]:
    """Statically scan the binary for absolute,indexed load instructions
    (opcode + lo + hi) whose operands form a (T, T+3) pair within
    `max_distance` bytes. The player MUST contain such a pair to load
    the voice ch_seq_ptr lo and hi tables, and the table itself sits
    at the lower address (lo table) and lower+3 (hi table).

    `opcodes` defaults to all four 6502 absolute-indexed load forms
    (LDA abs,X / LDA abs,Y / LDX abs,Y / LDY abs,X). Caller can restrict
    via opcodes=(0xBD,) for x-only, etc.

    Returns deduplicated list of (lo_table_addr, hi_table_addr) candidates.
    """
    candidates = []
    seen: set[tuple[int, int]] = set()
    n = len(c64_data)
    op_set = set(opcodes)

    # Find all matching instructions
    loads = []   # list of (instruction_offset, target_addr)
    for off in range(n - 2):
        if c64_data[off] in op_set:
            target = c64_data[off + 1] | (c64_data[off + 2] << 8)
            loads.append((off, target))

    # Look for pairs (a, b) where b = a + 3 and the two loads are
    # within `max_distance` bytes of each other (typical "load lo
    # table, load hi table" idiom in NP21 player loops).
    for i, (off_i, t_i) in enumerate(loads):
        # Probe a small forward window — typical idiom is ~3-15 bytes
        for off_j, t_j in loads[i+1 : i+15]:
            if off_j - off_i > max_distance:
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

    # Static scan: find indexed-load pairs that look like ch_seq_ptr loads.
    # We accept all four absolute,indexed forms (LDA abs,X / LDA abs,Y /
    # LDX abs,Y / LDY abs,X) — the canonical voice-pointer-load idiom is
    #     load voice_seq_lo_table, <reg>
    #     load voice_seq_hi_table, <reg>     (with hi = lo + 3)
    # but variants exist where the player uses Y instead of X, or mixes
    # registers between the two loads.
    pairs = find_indexed_load_pairs(c64_data, sid_la)

    # Also scan POST-INIT memory in the binary's range. Some NP21 player
    # variants use self-modifying code: INIT writes the table address into
    # an `LDA $XXXX,X` operand at runtime. Those patches are in mpu.memory
    # but NOT in c64_data, so the static scan above misses them.
    bin_end = min(sid_la + len(c64_data), 0x10000)
    post_init_bytes = bytes(mem[sid_la:bin_end])
    pairs_post = find_indexed_load_pairs(post_init_bytes, sid_la)
    # Dedupe — most pairs will overlap with the static scan
    seen_pairs = set(pairs)
    for p in pairs_post:
        if p not in seen_pairs:
            seen_pairs.add(p)
            pairs.append(p)

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
        # PLAY-read coverage is a SCORE BONUS, not a hard reject. Some
        # NP21 variants only touch one voice per PLAY tick (IRQ-dispatched
        # or counter-rotated voice handling), so within `n_play_ticks`
        # not all 6 table bytes get read — but the table is still real.
        # Adding +1 per byte found (max +6) preserves Stinsen/Unboxed
        # selectivity (their base scores are 50-100+, dwarfing the bonus)
        # while letting structurally-valid candidates with weak PLAY
        # observation still win over near-random alternatives.
        #
        # Special case: if ALL 6 table bytes appear in the PLAY-read set,
        # this is overwhelming evidence the player uses this exact table as
        # ch_seq_ptr during every PLAY tick. Promote score above the
        # acceptance threshold even when sequence bodies score negatively
        # (e.g., all-note sequences with b0=0x00 / n_traits<2). Note: audio
        # is unaffected — we only change the editor view, not the embedded
        # NP21 binary. _scan_table_at already validated that all 3 pointers
        # are in-range and each walks to a terminator within 256 bytes.
        if play_reads:
            need = [lo_addr + v for v in range(3)] + [hi_addr + v for v in range(3)]
            n_hits = sum(1 for a in need if a in play_reads)
            score += n_hits
            if n_hits == 6:
                score = max(score, 5)
        if best is None or score > best[0]:
            best = (score, lo_addr, hi_addr, ptrs)

    # Fallback: brute-force scan if static candidates yielded no usable
    # result. Run when EITHER (a) we found nothing, OR (b) the best
    # static candidate has score <= 0 (would be rejected by the final
    # filter anyway). Without (b), a single junk static-paired candidate
    # with negative score short-circuits the brute-force pass that might
    # find a real table.
    if best is None or best[0] <= 0:
        r = find_ch_seq_ptr_in_memory(
            mem, sid_la, len(c64_data),
            search_lo=sid_la, search_hi=sid_la + len(c64_data))
        if r is not None:
            lo_addr, hi_addr, ptrs, score = r
            # Only adopt the brute-force result if it beats the static best
            if best is None or score > best[0]:
                best = (score, lo_addr, hi_addr, ptrs)

    # Reject candidates whose score is non-positive. The scorer applies
    # large negative penalties (-1000) for hard-fail conditions; a
    # summed score <= 0 means at least one voice body tripped a hard
    # reject, so the candidate is not a real ch_seq_ptr.
    if best is None or best[0] <= 0:
        return None
    score, lo, hi, ptrs = best
    return lo, hi, ptrs, score
