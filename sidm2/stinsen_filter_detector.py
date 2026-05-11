"""Detect the Stinsen-class NP21 filter command byte streams.

Stinsen-class binaries store the filter program as **three parallel
byte streams** that the player's filter handler at $15F6-$167F walks
in lockstep:

    cmd byte stream  at $1989 (binary offset $0989 with load=$1000)
    val byte stream  at $19A3 (delta +$1A from cmd stream)
    aux byte stream  at $19BD (delta +$1A from val stream)

Each step index Y picks one byte from each stream. The bit 7 of
$1989[Y] determines the command type:

    bit 7 SET ($80-$FF) → SET command:
        $1989[Y] & $0F   → accumulator high (cutoff_hi base)
        $19A3[Y]         → accumulator low
        $19BD[Y]         → resonance + voice-routing (latched to D417)
    bit 7 CLEAR ($00-$7E) → SWEEP command:
        $1989[Y]:$19A3[Y] = 16-bit signed delta added to accumulator
        $19BD[Y]         → step duration counter
    $7F                  = step terminator / loop target (if
                            $19BD[Y] != Y, jump Y to $19BD[Y])

The accumulator is rendered each tick via right-shifts into D415/D416,
and $1787|$1788 → D417, $178A → D418 (mode/volume).

For SF2-edit-area propagation: we copy raw bytes back to the streams.
The player re-interprets the state machine on the next step
transition. SF2 editor users see raw bytes (the state-machine semantics
aren't decoded for display; users editing need to know the format).

Verified 2026-05-11 via py65 trace + direct-edit-patch:
- Bulk patch $19BD..$19D0 → +143 D417 writes flipped to marker (the
  res-routing values pass through directly).
- $1989 and $19A3 byte patches DO change accumulator behavior on next
  step transition; observable via D416 (cutoff_hi) value drift in
  trace diff.

See `memory/stinsen-filter-architecture.md` for the full RE writeup.

Detection: piggyback off the existing Stinsen instrument-table
signature at $1800 (same as the wave + pulse detectors).
"""
from __future__ import annotations
from typing import Optional, NamedTuple

from .stinsen_instr_detector import detect_stinsen_layout


class StinsenFilterLayout(NamedTuple):
    cmd_addr: int       # absolute address of cmd byte stream ($1989)
    val_addr: int       # absolute address of val byte stream ($19A3)
    aux_addr: int       # absolute address of aux byte stream ($19BD)
    n_steps: int        # SF2 default = 16 rows


STINSEN_FILTER_CMD_OFF = 0x0989
STINSEN_FILTER_VAL_OFF = 0x09A3
STINSEN_FILTER_AUX_OFF = 0x09BD

# SF2's filter editor view has 16 rows by default. The real Stinsen
# program has up to 20 entries before the next table region; we copy
# only the first 16 to match the SF2 view (later steps stay untouched
# in the NP21 binary, which is fine — they're only reached if the
# program advances past row 15).
STINSEN_FILTER_N_STEPS_DEFAULT = 16


def detect_stinsen_filter_layout(c64_data: bytes, load_addr: int
                                  ) -> Optional[StinsenFilterLayout]:
    """Return a StinsenFilterLayout if the binary matches Stinsen-class
    layout (uses the existing instr-table signature check), else None.
    """
    if detect_stinsen_layout(c64_data, load_addr) is None:
        return None

    needed_end = STINSEN_FILTER_AUX_OFF + STINSEN_FILTER_N_STEPS_DEFAULT
    if needed_end > len(c64_data):
        return None

    return StinsenFilterLayout(
        cmd_addr=load_addr + STINSEN_FILTER_CMD_OFF,
        val_addr=load_addr + STINSEN_FILTER_VAL_OFF,
        aux_addr=load_addr + STINSEN_FILTER_AUX_OFF,
        n_steps=STINSEN_FILTER_N_STEPS_DEFAULT,
    )
