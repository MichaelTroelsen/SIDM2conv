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
  V0/V1/V2) and `load+$496` (HI bytes, 3 entries).
- Each voice's orderlist is a sequence of pattern indices terminated
  by `$FE` (end) or `$FF` (loop).
- Pattern pointers themselves are at `load+$788` (LO) and `load+$78E`
  (HI), indexed by the pattern index from the orderlist.
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
    voice_orderlist_lo_addr: int   # load + $493 (3 bytes: V0/V1/V2 ptr LO)
    voice_orderlist_hi_addr: int   # load + $496 (3 bytes: V0/V1/V2 ptr HI)
    pattern_ptr_lo_addr: int       # load + $788 (LO bytes for pattern ptr table)
    pattern_ptr_hi_addr: int       # load + $78E (HI bytes for pattern ptr table)
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

# Offsets within the binary where the orderlist+pattern data lives.
# These offsets are HARDCODED in the player (the player's own code
# does `LDA $XX 9F,X` etc. where the high byte is implicit in the
# player's load).
_VOICE_OL_LO_OFF = 0x493
_VOICE_OL_HI_OFF = 0x496
_PATTERN_PTR_LO_OFF = 0x788
_PATTERN_PTR_HI_OFF = 0x78E


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

    # The copyright check is currently advisory — the signature +
    # orderlist range check are strong enough on their own. If the
    # copyright is provided we log-only (not gate). Future tightening
    # could enforce.
    return Vibrants2000ADLayout(
        voice_orderlist_lo_addr=sid_la + _VOICE_OL_LO_OFF,
        voice_orderlist_hi_addr=sid_la + _VOICE_OL_HI_OFF,
        pattern_ptr_lo_addr=sid_la + _PATTERN_PTR_LO_OFF,
        pattern_ptr_hi_addr=sid_la + _PATTERN_PTR_HI_OFF,
        voice_orderlist_addrs=addrs,
    )
