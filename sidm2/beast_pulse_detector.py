"""Detect Beast-class NP21 pulse byte-stream layout (F4).

Beast stores the pulse program as 4-byte step records starting at
`$1AC5`. Per-step encoding (RE'd 2026-05-12 by disassembling the
handler at $13C4-$13DA):

    byte 0 (cmd): cmd & $FF = $FF means SKIP STEP. Otherwise:
                  high nibble (& $F0) → PW lo scratch ($1911+X)
                  low nibble  (& $0F) → PW hi scratch ($1914+X)
                  (i.e., PW lo and PW hi are NIBBLE-PACKED into one byte)
    byte 1: PW lo sweep delta (added to scratch each tick via ADC)
    byte 2: flags + duration
            bit 7 = sweep direction toggle
            bits 0-6 = step duration counter
    byte 3: additional sweep parameter (stored to $190B+X)

Verified 2026-05-12 via direct-edit-patch + py65 trace:
- Patching $1AC5 = $A0 → V0 PW lo writes +208 to $A0 (high nibble);
  V0 PW hi stays $00 (low nibble of $A0).

The pulse byte stream feeds the SAME scratch architecture as Stinsen
($17E6-$17EB), Beast ($1911-$1916), Angular ($197B-$1980). Beast's
encoding is more compact than Stinsen's (4 bytes/step vs 6 bytes/step
across 3 parallel arrays).
"""
from __future__ import annotations
from typing import Optional, NamedTuple

from .beast_instr_detector import detect_beast_layout


class BeastPulseLayout(NamedTuple):
    stream_addr: int    # absolute address of first byte of step 0
    n_steps: int        # 16 (SF2 default — matches Block 3 pulse view)


BEAST_PULSE_STREAM_OFF = 0x0AC5
BEAST_PULSE_N_STEPS_DEFAULT = 16


def detect_beast_pulse_layout(c64_data: bytes, load_addr: int
                                ) -> Optional[BeastPulseLayout]:
    if detect_beast_layout(c64_data, load_addr) is None:
        return None
    needed_end = BEAST_PULSE_STREAM_OFF + BEAST_PULSE_N_STEPS_DEFAULT * 4
    if needed_end > len(c64_data):
        return None
    return BeastPulseLayout(
        stream_addr=load_addr + BEAST_PULSE_STREAM_OFF,
        n_steps=BEAST_PULSE_N_STEPS_DEFAULT,
    )
