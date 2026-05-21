"""Detect Zetrex/YP files and locate their voice byte-stream pointer table.

Zetrex/YP is a pre-NP21 player shared across:
  - Jewels.sid   (1988 Zetrex/Jewels,    load $E000)
  - Waste.sid    (1988 Zetrex 2005,      load $E000)
  - Racer.sid    (1987 Yield Point Music, load $E000)

Architecture (RE'd 2026-05-12, see `memory/wizax-a-byte-stream-re.md`
for the analogous Wizax-A architecture this mirrors):

* Player-code signature: 35 bytes at c64_data offset 9 (the
  init/scratch-zero loop), shared with vibrants_v20_detector's
  `_ZETREX_YP_SIG_BYTES`.

* Voice-pointer-setup pattern at fixed PC `$E0B6` (offset $0B6 within
  the binary):
    `B9 lo_table_lo lo_table_hi   ; LDA ptr_lo_table,Y
     85 zp_lo                      ; STA $zp_lo
     B9 hi_table_lo hi_table_hi   ; LDA ptr_hi_table,Y
     85 zp_hi                      ; STA $zp_hi`

  The operands are FILE-SPECIFIC (ptr-table addresses + ZP pair),
  observed combinations:
    - Jewels: $E849/$E859 ZP $FE/$FF (delta $10)
    - Waste:  $E961/$E96C ZP $FE/$FF (delta $0B)
    - Racer:  $E849/$E86C ZP $1B/$1C (delta $23)

* Per-voice current note: $E51C+X scratch (X = voice index 0/1/2)
* Freq LUT at $E447 (lo) / $E448 (hi) — 2-byte cells, note*2 = index

For F1 (sequences) edit propagation: same approach as Wizax-A. The
existing NP21 multipat-translator + shadow-buffer + ch_seq_ptr
patching pipeline works IF we redirect it to use Zetrex/YP's
ptr-table addresses instead of NP21's $0A1C/$0A1F.
"""
from __future__ import annotations
from typing import Optional, NamedTuple


class ZetrexYPLayout(NamedTuple):
    ptr_lo_addr: int    # absolute address of voice ptr-lo table (3 bytes)
    ptr_hi_addr: int    # absolute address of voice ptr-hi table (3 bytes)
    zp_lo: int          # ZP page used for low byte of stream pointer
    zp_hi: int          # ZP page used for high byte


# 35-byte player init signature at offset 9 (shared with vibrants_v20_detector)
_ZETREX_YP_SIG_OFFSET = 9
_ZETREX_YP_SIG_BYTES = bytes([
    0x2C, 0x4A, 0xE5, 0x30, 0x29, 0x50, 0x3E,
    0xA2, 0x02, 0xA9, 0x00, 0xBC, 0x09, 0xE5,
    0x99, 0x04, 0xD4, 0x9D, 0x0D, 0xE5, 0x9D,
    0x10, 0xE5, 0x9D, 0x13, 0xE5, 0x9D, 0x19,
    0xE5, 0x99, 0x06, 0xD4, 0xA9, 0x11, 0x9D,
])


# Voice-pointer-setup pattern at fixed offset $0B6 ($E0B6 absolute for
# load $E000). All 3 cluster files have the SAME player code at this
# offset, but the operand bytes (ptr-table addrs + ZP) are file-specific.
_PTR_SETUP_OFFSET = 0x0B6


def _has_zetrex_yp_signature(c64_data: bytes) -> bool:
    """Match the 35-byte init signature at offset 9."""
    if len(c64_data) < _ZETREX_YP_SIG_OFFSET + len(_ZETREX_YP_SIG_BYTES):
        return False
    return (c64_data[_ZETREX_YP_SIG_OFFSET :
                     _ZETREX_YP_SIG_OFFSET + len(_ZETREX_YP_SIG_BYTES)]
            == _ZETREX_YP_SIG_BYTES)


def _read_ptr_setup(c64_data: bytes) -> Optional[tuple[int, int, int, int]]:
    """Decode the 10-byte ptr-table-setup at offset $0B6.
    Returns (ptr_lo_addr, ptr_hi_addr, zp_lo, zp_hi) or None.
    """
    if _PTR_SETUP_OFFSET + 10 > len(c64_data):
        return None
    # Expected: B9 lo hi 85 zp B9 lo hi 85 zp
    if (c64_data[_PTR_SETUP_OFFSET]     != 0xB9 or
        c64_data[_PTR_SETUP_OFFSET + 3] != 0x85 or
        c64_data[_PTR_SETUP_OFFSET + 5] != 0xB9 or
        c64_data[_PTR_SETUP_OFFSET + 8] != 0x85):
        return None
    ptr_lo_addr = c64_data[_PTR_SETUP_OFFSET + 1] | (c64_data[_PTR_SETUP_OFFSET + 2] << 8)
    zp_lo       = c64_data[_PTR_SETUP_OFFSET + 4]
    ptr_hi_addr = c64_data[_PTR_SETUP_OFFSET + 6] | (c64_data[_PTR_SETUP_OFFSET + 7] << 8)
    zp_hi       = c64_data[_PTR_SETUP_OFFSET + 9]
    # ZP pair must be adjacent (16-bit pointer)
    if zp_hi != zp_lo + 1:
        return None
    # Delta between lo and hi tables must be > 3 (else it's a 2-byte
    # adjacent pair like the freq LUT at $E447/$E448, not a 3-byte
    # parallel-array table pair).
    delta = ptr_hi_addr - ptr_lo_addr
    if delta <= 3 or delta > 0x100:
        return None
    return (ptr_lo_addr, ptr_hi_addr, zp_lo, zp_hi)


def detect_zetrex_yp_layout(c64_data: bytes, load_addr: int,
                            copyright_str: str = ''
                            ) -> Optional[ZetrexYPLayout]:
    """Return ZetrexYPLayout if the binary matches Zetrex/YP, else None.

    Matching criteria:
    0. (NEW v3.5.26) When `copyright_str` is provided, gate on
       Vibrants-V20 detection — same false-positive cleanup as
       wizax_a_detector. Without this gate the byte-pattern signature
       alone matched some regular Laxity NP21 files (Edie_Ball, Racer
       in the corpus C2-divergent list) → wrong ch_seq_ptr patch →
       audio corruption.
    1. 35-byte init signature at offset 9.
    2. 10-byte ptr-table-setup at offset $0B6 (decoded operands).
    3. Both ptr-table addresses fall within the binary.
    4. All 3 voice pointers (lo[0..2] + hi[0..2]) yield in-range
       stream addresses inside the binary.
    """
    if copyright_str:
        from sidm2.vibrants_v20_detector import detect_vibrants_v20
        if detect_vibrants_v20(c64_data, load_addr, copyright_str) is None:
            return None
    if not _has_zetrex_yp_signature(c64_data):
        return None
    decoded = _read_ptr_setup(c64_data)
    if decoded is None:
        return None
    ptr_lo_addr, ptr_hi_addr, zp_lo, zp_hi = decoded
    binary_end = load_addr + len(c64_data)
    if not (load_addr <= ptr_lo_addr < binary_end and
            load_addr <= ptr_hi_addr < binary_end):
        return None
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
    return ZetrexYPLayout(
        ptr_lo_addr=ptr_lo_addr,
        ptr_hi_addr=ptr_hi_addr,
        zp_lo=zp_lo,
        zp_hi=zp_hi,
    )
