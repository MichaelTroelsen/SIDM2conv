"""Detect 1988 2000 A.D. cluster files (Echo_Beat + Galax_it_y).

This is a 2-file sub-cluster of the Vibrants V20 inventory that shares a
single player binary at different load addresses:

  - Echo_Beat.sid     (load $0400, 1644 B)
  - Galax_it_y.sid    (load $1000, 1984 B)

NOT included (separate player despite same "1988 2000 A.D." copyright):

  - James_Bond_Theme_Remix.sid  (singleton variant)

# Architecture summary

Reverse-engineered 2026-05-26. See `memory/vibrants-2000ad-cluster-re.md`
for the full detail.

The shared player has a distinctive 16-byte signature at `load+$0`:

    4C XX XX     JMP init_routine
    4C XX XX     JMP stop_routine
    2C XX XX     BIT running_flag    ; PSID play_addr = load+$6
    30 01        BMI +1 (skip RTS)
    60           RTS
    A9 00        LDA #$00
    8D XX XX     STA $XXXX

Detector signature bytes (offset-fixed): `[0]=0x4C, [3]=0x4C, [6]=0x2C`,
followed by `30 01 60 A9` at `[9..12]`.

Voice byte-stream architecture (orderlist + pattern model, NP21-style):

- Per-voice orderlist pointers at `load+$493` (LO bytes, 3 entries for
  V0/V1/V2) and `load+$496` (HI bytes, 3 entries). These offsets are
  fixed across cluster files (encoded as the same LDA absolute,X in
  the player code body).
- Each voice's orderlist is a sequence of pattern indices terminated
  by `$FE` (end) or `$FF` (loop).
- Pattern pointers themselves are at FILE-SPECIFIC addresses — `$1788`
  / `$178E` for Galax_it_y, `$0A29` / `$0A2D` for Echo_Beat. The
  player code is identical between cluster files but the data sections
  vary in size per song, so anything past the variable-sized data
  shifts in absolute terms. Located dynamically via
  `_find_pattern_ptr_table` (opcode-signature scan).
- Each pattern is a sequence of byte pairs (duration+octave, note)
  until a `$FF` terminator at the pattern level.

Per-byte semantics within a pattern:

  byte 1:
    $00..$7F → duration: low 5 bits + 1 = tick count; bit 5 = octave flag
    $80..$FE → command prefix; payload follows in byte 2
    $FF      → end of pattern → advance orderlist

  byte 2 (when byte 1 is a duration):
    $00      → gate off (rest)
    non-zero → note value (added to per-voice transpose, then LUT lookup)

# What this detector enables

A future `np21_edit_area_builder` enhancement can use the detected
ptr addresses to redirect the existing ch_seq_ptr + shadow buffer
pipeline (same trick as Wizax-A / Zetrex-YP) at the orderlist + pattern
tables. The byte streams aren't NP21-compatible byte-for-byte
(different note encoding, duration in bits 0-4 not 0-3, etc.) but a
per-variant transform can map them to NP21 format for editor view.

# What this detector does NOT (yet) enable

This module is detection only. The actual EXTRACTOR (orderlist+pattern
walker producing NP21-format streams) is the next step and is not in
this module.
"""
from __future__ import annotations
from typing import NamedTuple, Optional


class Vibrants2000ADLayout(NamedTuple):
    """Resolved addresses for the 2000 A.D. cluster player.

    All addresses are absolute C64 addresses (load_addr + offset).
    """
    voice_orderlist_lo_addr: int   # load + $493 (3 bytes: V0/V1/V2 ptr LO; fixed offset)
    voice_orderlist_hi_addr: int   # load + $496 (3 bytes: V0/V1/V2 ptr HI; fixed offset)
    pattern_ptr_lo_addr: int       # File-specific: $1788 (Galax) / $0A29 (Echo);
                                   # located by `_find_pattern_ptr_table` dynamic scan.
    pattern_ptr_hi_addr: int       # File-specific: $178E (Galax) / $0A2D (Echo).
    voice_orderlist_addrs: tuple   # (V0_orderlist, V1_orderlist, V2_orderlist) absolute addrs


# Player signature at load+$0..$F (16 bytes).
# Format: `4C ?? ?? 4C ?? ?? 2C ?? ?? 30 01 60 A9 00 8D ??`
# The 3-byte JMP targets vary by file (relocated), so we match on the
# fixed opcode bytes at known offsets.
_FIXED_BYTES_AT_OFFSETS = {
    0: 0x4C,    # JMP (init)
    3: 0x4C,    # JMP (stop)
    6: 0x2C,    # BIT (running-flag check at PLAY entry)
    9: 0x30,    # BMI +1
    10: 0x01,
    11: 0x60,   # RTS
    12: 0xA9,   # LDA #
    13: 0x00,
    14: 0x8D,   # STA $XXXX
}

# The voice-orderlist ptr table sits at a fixed file-relative offset
# (`load+$493`/`load+$496`) — the player code has `LDA $XX93,X` /
# `LDA $XX96,X` instructions where the high byte is `(load_hi + 4)`.
_VOICE_OL_LO_OFF = 0x493
_VOICE_OL_HI_OFF = 0x496

# The PATTERN-ptr table address is FILE-SPECIFIC (data section size
# differs per song; the player code is identical between cluster files
# but the data tables shift). Always located via dynamic scan; see
# `_find_pattern_ptr_table` below.
#
# Earlier RE notes assumed `load+$788`/`load+$78E` — that's only correct
# for Galax_it_y (load $1000, size $7C0). Echo_Beat (load $0400, size
# $66C) puts the pattern ptr table at `load+$629`/`load+$62D`, past the
# end of where a $788 lookup would land.


def _has_2000ad_signature(c64_data: bytes) -> bool:
    """Check the fixed-byte signature at offsets 0/3/6/9-14."""
    if len(c64_data) < 16:
        return False
    return all(c64_data[off] == val for off, val in _FIXED_BYTES_AT_OFFSETS.items())


def _voice_orderlists_in_range(c64_data: bytes, sid_la: int) -> Optional[tuple]:
    """Read the 3 voice orderlist pointers from the binary and validate
    they all point WITHIN the binary's address range.

    Returns the 3-tuple of orderlist addresses on success, None otherwise.
    """
    if len(c64_data) < _VOICE_OL_HI_OFF + 3:
        return None
    ol_lo = c64_data[_VOICE_OL_LO_OFF:_VOICE_OL_LO_OFF + 3]
    ol_hi = c64_data[_VOICE_OL_HI_OFF:_VOICE_OL_HI_OFF + 3]
    addrs = tuple((lo | (hi << 8)) for lo, hi in zip(ol_lo, ol_hi))
    binary_end = sid_la + len(c64_data)
    if not all(sid_la <= a < binary_end for a in addrs):
        return None
    return addrs


def _find_pattern_ptr_table(c64_data: bytes, sid_la: int) -> Optional[tuple]:
    """Scan the orderlist-advance code for the pattern_ptr LO/HI table
    addresses.

    The end-of-orderlist handler emits this code sequence (Galax_it_y
    illustration, load $1000):

        48 98 9D F2 14   ; PHA; TYA; STA $14F2,X   (save pattern index, advance Y)
        68 A8            ; PLA; TAY               (recover index → Y)
        B9 88 17         ; LDA $1788,Y           ← pattern_ptr_LO_TABLE
        9D BF 14         ; STA $14BF,X           (current pat ptr lo)
        B9 8E 17         ; LDA $178E,Y           ← pattern_ptr_HI_TABLE
        9D C2 14         ; STA $14C2,X           (current pat ptr hi)

    The two LDA absolute-Y operands give the two table addresses. The
    `$14` byte (scratch page) is `(load_hi + 4)`. Returns
    `(pat_lo_addr, pat_hi_addr)` or None if not found.

    The validation also hardcodes the scratch-slot LOW byte (`$BF` for
    the current-pattern-pointer-LO slot at `$14BF+X`). This is the
    standard Galax/Echo player layout; if a future cluster file
    relocates the scratch slot, the validation will reject it and the
    detector returns None. The locator's `find()` is also first-match-
    only — if a coincidental signature prefix appears in data BEFORE
    the real player code and the suffix doesn't match, the file is
    rejected silently.
    """
    scratch_hi = (sid_la >> 8) + 4
    if scratch_hi > 0xFF:
        return None
    sig = bytes([0x48, 0x98, 0x9D, 0xF2, scratch_hi, 0x68, 0xA8, 0xB9])
    # v3.5.66: scan past first-match failures so a coincidental prefix
    # in data doesn't reject the whole file.
    start = 0
    while True:
        idx = c64_data.find(sig, start)
        if idx < 0:
            return None
        p = idx + len(sig)
        if p + 8 > len(c64_data):
            return None
        pat_lo_addr = c64_data[p] | (c64_data[p + 1] << 8)
        # Standard Galax-class scratch slot: STA $XXBF,X for current
        # pat ptr LO. If a future cluster file uses a different scratch
        # slot, the byte at `p+3` would differ and validation falls
        # through to the next `find()` iteration.
        if (c64_data[p + 2] == 0x9D
                and c64_data[p + 3] == 0xBF
                and c64_data[p + 4] == scratch_hi
                and c64_data[p + 5] == 0xB9):
            break
        # Suffix mismatch — try the next occurrence (a coincidental
        # prefix in data); v3.5.58-v3.5.65 bailed here, rejecting files
        # whose real signature came after a data-region false match.
        start = idx + 1
    pat_hi_addr = c64_data[p + 6] | (c64_data[p + 7] << 8)
    return pat_lo_addr, pat_hi_addr


def detect_2000ad_layout(
    c64_data: bytes,
    sid_la: int,
    copyright_str: str = '',
) -> Optional[Vibrants2000ADLayout]:
    """Detect the 1988 2000 A.D. cluster shared player and return its
    layout addresses.

    Detection criteria (all must hold):
      1. Binary has the 16-byte fixed signature at `load+$0..$F`.
      2. The voice orderlist pointers at `load+$493`/`load+$496` parse
         to 3 absolute addresses that all fall within the binary's
         address range.
      3. (Optional, currently advisory) Copyright contains "2000 A.D."
         hint — this helps disambiguate from any future file that
         happens to have the same opcode signature by accident.

    Args:
        c64_data: The raw NP21 binary bytes.
        sid_la: The binary's C64 load address.
        copyright_str: PSID copyright string. Empty string skips the
            copyright check (signature alone is the trigger). Pass
            `self.data.header.copyright` in production calls.

    Returns:
        Vibrants2000ADLayout with the resolved table addresses, or
        None if the file doesn't match the cluster.
    """
    if not _has_2000ad_signature(c64_data):
        return None

    addrs = _voice_orderlists_in_range(c64_data, sid_la)
    if addrs is None:
        return None

    pat_ptrs = _find_pattern_ptr_table(c64_data, sid_la)
    if pat_ptrs is None:
        return None
    pat_lo_addr, pat_hi_addr = pat_ptrs
    binary_end = sid_la + len(c64_data)
    if not (sid_la <= pat_lo_addr < binary_end and
            sid_la <= pat_hi_addr < binary_end):
        return None

    # The copyright check is currently advisory — the signature +
    # orderlist range check are strong enough on their own.
    return Vibrants2000ADLayout(
        voice_orderlist_lo_addr=sid_la + _VOICE_OL_LO_OFF,
        voice_orderlist_hi_addr=sid_la + _VOICE_OL_HI_OFF,
        pattern_ptr_lo_addr=pat_lo_addr,
        pattern_ptr_hi_addr=pat_hi_addr,
        voice_orderlist_addrs=addrs,
    )
