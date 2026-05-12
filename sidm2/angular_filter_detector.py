"""Detect Angular-class NP21 filter byte-stream layout (F5).

Angular mirrors Beast architecturally with different addresses:
    cutoff_hi byte stream at $1A1F (16+ entries)
    res_routing latched     at $100A (single byte — shared with Beast)
    mode_vol  latched       at $1009 (single byte — shared with Beast)

Verified 2026-05-12 via py65 trace + direct-edit-patch:
- Patching $1A1F+offset → D416 cutoff_hi register writes flipped
  (+28 at offset 4 marker, +15 at offset 16 marker).
- Patching $100A → D417 res_routing flipped (+3 marker writes).

Cutoff_lo (D415) is NOT used by Angular (0 register writes observed).

Detection: piggyback off the existing Angular instr-table signature.
"""
from __future__ import annotations
from typing import Optional, NamedTuple

from .angular_instr_detector import detect_angular_layout


class AngularFilterLayout(NamedTuple):
    cutoff_hi_stream_addr: int
    n_steps: int


ANGULAR_FILTER_CUTOFF_HI_OFF = 0x0A1F
ANGULAR_FILTER_N_STEPS_DEFAULT = 16


def detect_angular_filter_layout(c64_data: bytes, load_addr: int
                                   ) -> Optional[AngularFilterLayout]:
    if detect_angular_layout(c64_data, load_addr) is None:
        return None
    needed_end = ANGULAR_FILTER_CUTOFF_HI_OFF + ANGULAR_FILTER_N_STEPS_DEFAULT
    if needed_end > len(c64_data):
        return None
    return AngularFilterLayout(
        cutoff_hi_stream_addr=load_addr + ANGULAR_FILTER_CUTOFF_HI_OFF,
        n_steps=ANGULAR_FILTER_N_STEPS_DEFAULT,
    )
