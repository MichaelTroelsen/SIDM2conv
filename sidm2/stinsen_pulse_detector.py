"""Detect the Stinsen-class NP21 pulse-program byte stream.

Stinsen-class binaries (verified for `Stinsens_Last_Night_of_89.sid`)
store pulse-width animation as two parallel byte streams:

    PW lo bytes at $1957 (binary offset $0957 with load=$1000)
    PW hi bytes at $193E (binary offset $093E, delta -$19 from PW lo)

Each pulse-program-step has one byte in each stream. The player walks
both pointers in lockstep as voices transition to a new pulse step.
All 3 voices share the same byte stream — when V0 hits a new step,
voice V1 + V2 also load that step's value into their PW scratches at
$17E6-$17EB.

Verified 2026-05-11 via py65 instruction-tracing + direct-edit-patch:
- Patching binary[$0957] = $XX flips D402 (V0 PW lo) writes to $XX.
  Same byte also propagates to D409 (V1) and D410 (V2) at their
  respective step-transition moments.
- Patching binary[$093E] = $YY flips D403/D40A/D411 (V0/V1/V2 PW hi)
  similarly.

See `memory/stinsen-pulse-architecture.md` for the full RE writeup.

Detection: piggyback off the existing Stinsen instrument-table
signature at $1800 (already used by `stinsen_instr_detector`). If
that matches, the pulse bytes ALSO live at the canonical offsets.
"""
from __future__ import annotations
from typing import Optional, NamedTuple

from .stinsen_instr_detector import detect_stinsen_layout


class StinsenPulseLayout(NamedTuple):
    pw_lo_addr: int    # absolute address of PW lo byte stream start
    pw_hi_addr: int    # absolute address of PW hi byte stream start
    n_steps: int       # number of pulse-program steps (16 = SF2 default)


# Stinsen pulse byte stream addresses (relative to load_addr = $1000).
STINSEN_PULSE_LO_OFF = 0x0957
STINSEN_PULSE_HI_OFF = 0x093E

# SF2's pulse editor view has 16 rows by default. Stinsen's actual
# table has ~25 entries (PW hi at $193E..$1956, PW lo at $1957..$196F,
# delta = $19 = 25 between them). We propagate only the first 16 to
# match the SF2 view; later steps remain untouched in the NP21 binary.
STINSEN_PULSE_N_STEPS_DEFAULT = 16


def detect_stinsen_pulse_layout(c64_data: bytes, load_addr: int
                                ) -> Optional[StinsenPulseLayout]:
    """Return a StinsenPulseLayout if the binary matches Stinsen-class
    layout (same signature check as `detect_stinsen_layout`), else None.
    """
    # Reuse the instr-detector's signature so we never claim pulse-layout
    # on a binary that doesn't have the matching instr layout.
    if detect_stinsen_layout(c64_data, load_addr) is None:
        return None

    # Sanity: both byte streams must fit within the binary.
    needed_end = STINSEN_PULSE_LO_OFF + STINSEN_PULSE_N_STEPS_DEFAULT
    if needed_end > len(c64_data):
        return None

    return StinsenPulseLayout(
        pw_lo_addr=load_addr + STINSEN_PULSE_LO_OFF,
        pw_hi_addr=load_addr + STINSEN_PULSE_HI_OFF,
        n_steps=STINSEN_PULSE_N_STEPS_DEFAULT,
    )
