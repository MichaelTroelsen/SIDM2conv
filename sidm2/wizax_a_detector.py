"""Detect Wizax-A files and locate their voice byte-stream pointer table.

Wizax-A is a pre-NP21 player used by Thomas E. Petersen (Laxity) in the
late-1980s era. 4 files in the Laxity corpus use it:
  - 2000_A_D.sid (load $1000)
  - Fight_TST_II.sid (load $1000)
  - Hall_of_Fame.sid (load $C000)
  - Min_Axel_F.sid (load $1000)

Architecture (RE'd 2026-05-12, see `memory/wizax-a-byte-stream-re.md`):

* The player has a distinctive 11-byte voice-control-clear sequence
  `A9 00 8D 04 D4 8D 0B D4 8D 12 D4` (LDA #0; STA $D404; STA $D40B;
  STA $D412 — clear all 3 voice control registers) appearing near
  the start of the binary (after a variable-length JMP-table prefix).

* Each voice has its own byte stream pointed-at by a ZP pair. The
  setup is `LDA ptr_lo_table,Y; STA $zp_lo; LDA ptr_hi_table,Y; STA $zp_hi`
  — a 10-byte opcode sequence we scan for.

* The ptr_lo_table / ptr_hi_table addresses are FILE-SPECIFIC (the
  player code is identical but data sections vary in size per song,
  so the table location shifts). Detection MUST scan dynamically.

* Voice byte streams are NP21-compatible: `$01-$6F` are notes,
  `$80-$9F` are duration / command prefixes, `$FF` is loop marker.

For F1 (sequences) edit propagation: the existing NP21 multipat
translator + shadow buffer + ch_seq_ptr patching pipeline should work
IF we redirect it to use the Wizax-A ptr table addresses instead of
NP21's hardcoded `$0A1C/$0A1F`. That's what
`detect_wizax_a_layout()` enables in the conversion pipeline.

⚠ Behavioral caveats:

1. The translator's NP21-to-shadow byte translation uses NP21 command
   byte semantics. Wizax-A command bytes ($87, $8B, $83, etc.) may
   have different meanings, so edit propagation could mis-translate
   commands. Notes + durations (the most common edits) should round-
   trip correctly.

2. The existing F2/F3/F4/F5 wire-ups (instr/wave/pulse/filter) won't
   fire because Wizax-A has no NP21 instrument/wave tables. Only F1
   sequences will be display+edit-able. The other editor columns
   stay empty.
"""
from __future__ import annotations
from typing import Optional, NamedTuple


class WizaxALayout(NamedTuple):
    ptr_lo_addr: int    # absolute address of voice ptr-lo table (3 bytes)
    ptr_hi_addr: int    # absolute address of voice ptr-hi table (3 bytes)
    zp_lo: int          # ZP page used for low byte of stream pointer
    zp_hi: int          # ZP page used for high byte


# Wizax-A signature: 11-byte voice-control-clear sequence appearing
# within the first 128 bytes (after the JMP-table prefix). Same
# signature as the existing vibrants_v20_detector check; duplicated
# here to keep this module standalone.
_WIZAX_A_SIG_BYTES = bytes([
    0xA9, 0x00, 0x8D, 0x04, 0xD4,
    0x8D, 0x0B, 0xD4, 0x8D, 0x12, 0xD4,
])


def _has_wizax_a_signature(c64_data: bytes) -> bool:
    """Match the voice-control-clear opcode sequence in first 128 bytes."""
    return _WIZAX_A_SIG_BYTES in c64_data[:128]


def _find_ptr_table_setup(c64_data: bytes) -> Optional[tuple[int, int, int, int]]:
    """Scan for the 10-byte ptr-table setup sequence:

        B9 [lo1] [hi1]   ; LDA ptr_lo_table,Y
        85 [zp_lo]        ; STA $zp_lo
        B9 [lo2] [hi2]   ; LDA ptr_hi_table,Y
        85 [zp_hi]        ; STA $zp_hi

    Returns (ptr_lo_addr, ptr_hi_addr, zp_lo, zp_hi) or None.
    """
    for i in range(len(c64_data) - 10):
        if (c64_data[i]     == 0xB9 and
            c64_data[i + 3] == 0x85 and
            c64_data[i + 5] == 0xB9 and
            c64_data[i + 8] == 0x85):
            ptr_lo_addr = c64_data[i + 1] | (c64_data[i + 2] << 8)
            zp_lo       = c64_data[i + 4]
            ptr_hi_addr = c64_data[i + 6] | (c64_data[i + 7] << 8)
            zp_hi       = c64_data[i + 9]
            # ZP addresses are typically adjacent (zp+1) for a 16-bit
            # pointer pair, but Wizax-A's setup uses consecutive ZP
            # bytes anyway: $58/$59 (2000_A_D), $FD/$FE (Fight_TST_II,
            # Hall_of_Fame), $4B/$4D (Min_Axel_F — note non-adjacent).
            # Min_Axel_F uses $4B + $4D not $4B + $4C — so the zp_hi
            # constraint is loose.
            if zp_lo > 0xFE or zp_hi > 0xFF:
                continue
            # ptr table delta should be small (data section size between
            # them). Observed deltas: $31, $35, $6E. Cap at $400 to avoid
            # false positives on long jumps to far data.
            delta = abs(ptr_hi_addr - ptr_lo_addr)
            if delta == 0 or delta > 0x400:
                continue
            return (ptr_lo_addr, ptr_hi_addr, zp_lo, zp_hi)
    return None


def detect_wizax_a_layout(c64_data: bytes, load_addr: int
                          ) -> Optional[WizaxALayout]:
    """Return WizaxALayout if the binary matches Wizax-A, else None.

    Matching criteria:
    1. 11-byte voice-control-clear signature appears in first 128 bytes.
    2. Player setup pattern `B9 lo hi 85 zp B9 lo hi 85 zp` appears
       anywhere in the binary.
    3. Both ptr table addresses fall within the binary's load range.
    4. The 3 voice pointers (lo[0..2] + hi[0..2]) all yield in-range
       stream addresses inside the binary.
    """
    if not _has_wizax_a_signature(c64_data):
        return None
    result = _find_ptr_table_setup(c64_data)
    if result is None:
        return None
    ptr_lo_addr, ptr_hi_addr, zp_lo, zp_hi = result
    # Both ptr tables must be in-range
    binary_end = load_addr + len(c64_data)
    if not (load_addr <= ptr_lo_addr < binary_end and
            load_addr <= ptr_hi_addr < binary_end):
        return None
    # Each voice pointer must point inside the binary
    ptr_lo_off = ptr_lo_addr - load_addr
    ptr_hi_off = ptr_hi_addr - load_addr
    if ptr_lo_off + 3 > len(c64_data) or ptr_hi_off + 3 > len(c64_data):
        return None
    for v in range(3):
        lo = c64_data[ptr_lo_off + v]
        hi = c64_data[ptr_hi_off + v]
        addr = (hi << 8) | lo
        if not (load_addr <= addr < binary_end):
            return None
    return WizaxALayout(
        ptr_lo_addr=ptr_lo_addr,
        ptr_hi_addr=ptr_hi_addr,
        zp_lo=zp_lo,
        zp_hi=zp_hi,
    )
