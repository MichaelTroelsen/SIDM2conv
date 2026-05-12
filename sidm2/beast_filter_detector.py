"""Detect Beast-class NP21 filter byte-stream layout (F5).

Beast stores the filter program as:
    cutoff_hi byte stream at $1A7D (16+ entries)
    res_routing latched     at $100A (single byte)
    mode_vol  latched       at $1009 (single byte)

Verified 2026-05-12 via py65 trace + direct-edit-patch:
- Patching $1A7D+offset bytes → D416 cutoff_hi register writes flipped
  (+34 at offset 16 marker test).
- Patching $100A → D417 res_routing flipped (+3 marker writes).
- $1009 is essentially static; mode_vol doesn't animate in observed
  trace window.

Cutoff_lo (D415) is NOT used by Beast (0 register writes in 400 ticks).

The simple cutoff_hi-only F5 wire-up writes SF2 col 0 → $1A7D+row;
res_routing + mode_vol can't be safely array-indexed (they'd corrupt
adjacent code at $100A+ / $1009+ for row > 0) so they stay static —
edits to SF2 cols 1 + 2 do not propagate for Beast.

Detection: piggyback off the existing Beast instr-table signature at
$1B38.
"""
from __future__ import annotations
from typing import Optional, NamedTuple

from .beast_instr_detector import detect_beast_layout


class BeastFilterLayout(NamedTuple):
    cutoff_hi_stream_addr: int   # absolute address of cutoff_hi byte stream
    n_steps: int                  # 16 (SF2 default)


BEAST_FILTER_CUTOFF_HI_OFF = 0x0A7D
BEAST_FILTER_N_STEPS_DEFAULT = 16


def detect_beast_filter_layout(c64_data: bytes, load_addr: int
                                ) -> Optional[BeastFilterLayout]:
    if detect_beast_layout(c64_data, load_addr) is None:
        return None
    needed_end = BEAST_FILTER_CUTOFF_HI_OFF + BEAST_FILTER_N_STEPS_DEFAULT
    if needed_end > len(c64_data):
        return None
    return BeastFilterLayout(
        cutoff_hi_stream_addr=load_addr + BEAST_FILTER_CUTOFF_HI_OFF,
        n_steps=BEAST_FILTER_N_STEPS_DEFAULT,
    )
