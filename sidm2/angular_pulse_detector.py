"""Detect Angular-class NP21 pulse byte-stream layout (F4).

Angular uses identical encoding to Beast (nibble-packed PW byte at
offset 0 of each 4-byte step record) at base `$1A3B`. Handler at
$1404-$1418 verified by disasm 2026-05-12.

Step record layout matches Beast:
    byte 0: cmd byte ($FF=skip, else high nibble=PW lo, low nibble=PW hi)
    byte 1: PW lo sweep delta
    byte 2: flags + duration
    byte 3: additional sweep parameter

Verified 2026-05-12 by direct-edit-patch: $1A3B = $C0 →
V1 PW lo writes +399 to $C0; PW hi stays $00.
"""
from __future__ import annotations
from typing import Optional, NamedTuple

from .angular_instr_detector import detect_angular_layout


class AngularPulseLayout(NamedTuple):
    stream_addr: int
    n_steps: int


ANGULAR_PULSE_STREAM_OFF = 0x0A3B
ANGULAR_PULSE_N_STEPS_DEFAULT = 16


def detect_angular_pulse_layout(c64_data: bytes, load_addr: int
                                  ) -> Optional[AngularPulseLayout]:
    if detect_angular_layout(c64_data, load_addr) is None:
        return None
    needed_end = ANGULAR_PULSE_STREAM_OFF + ANGULAR_PULSE_N_STEPS_DEFAULT * 4
    if needed_end > len(c64_data):
        return None
    return AngularPulseLayout(
        stream_addr=load_addr + ANGULAR_PULSE_STREAM_OFF,
        n_steps=ANGULAR_PULSE_N_STEPS_DEFAULT,
    )
