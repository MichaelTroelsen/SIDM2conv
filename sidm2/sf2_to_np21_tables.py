"""SF2-edit-area → NP21-binary table format conversions (Stage 7 Phase A).

The runtime translator at $0F0E (sidm2.sf2_to_np21) bridges sequence
edits between the SF2 editor view and the embedded NP21 player. This
module is the analogous spec for the OTHER tables the editor exposes:
instruments (F2), wave (F3), pulse (F4), filter (F5).

Each function takes the SF2 edit area bytes for a table plus the
EXISTING NP21 binary bytes at the destination, and returns the new
NP21 bytes to write back. Most NP21 columns map 1:1 to SF2 edit area
columns; some NP21 fields don't exist in the SF2 view at all and must
be PRESERVED across the conversion.

Phase A (this module): pure Python, fully unit-tested.
Phase B (next session): 6502 emission integrated into the runtime
                        translator at $0F0E.
Phase C (next session): end-to-end zig64 verification that edits in
                        the SF2 editor propagate to playback.
"""
from __future__ import annotations

# Column counts per SF2 edit area Block 3 spec (Stinsen-class layout)
SF2_INSTR_COLS  = 6
SF2_WAVE_COLS   = 2
SF2_PULSE_COLS  = 3
SF2_FILTER_COLS = 3

# Column counts per NP21 binary layout
NP21_INSTR_COLS  = 8
NP21_PULSE_COLS  = 4

# Default table sizes (matches Stinsen v3.4.0+ writer)
DEFAULT_INSTR_ROWS  = 32
DEFAULT_WAVE_ROWS   = 32
DEFAULT_PULSE_ROWS  = 16


def convert_wave_table(sf2_bytes: bytes, n_rows: int = DEFAULT_WAVE_ROWS) -> bytes:
    """Wave: identity copy. SF2 and NP21 both store rows of
    (note_offset, waveform) pairs. The byte layout is identical.

    Args:
        sf2_bytes: SF2 edit area bytes for the wave table; expected
                   to be at least n_rows * 2 bytes long.
        n_rows: number of rows to copy (default 32).

    Returns:
        n_rows * 2 bytes ready to write into the NP21 binary at
        wave_table_addr ($1942 for Stinsen).
    """
    n = n_rows * SF2_WAVE_COLS
    if len(sf2_bytes) < n:
        raise ValueError(f"SF2 wave bytes too short: {len(sf2_bytes)} < {n}")
    return bytes(sf2_bytes[:n])


def convert_instruments_table(sf2_bytes: bytes, np21_existing: bytes,
                              n_rows: int = DEFAULT_INSTR_ROWS) -> bytes:
    """Instruments: row-by-row merge. NP21 has 8 bytes/row, SF2 has 6.

    NP21 row layout (per `extract_laxity_instruments`):
        byte 0: AD            (Attack/Decay)
        byte 1: SR            (Sustain/Release)
        byte 2: flags1        (= "restart"/HR in SF2)
        byte 3: flags2        (NOT exposed in SF2 — preserved)
        byte 4: flags3        (NOT exposed in SF2 — preserved)
        byte 5: pulse_param   (NOT exposed in SF2 — preserved)
        byte 6: pulse_ptr
        byte 7: wave_ptr

    SF2 edit area row layout (Stage 3 in `sf2_writer.py` line ~2879):
        col 0: AD          ← NP21 byte 0
        col 1: SR          ← NP21 byte 1
        col 2: HR          ← NP21 byte 2
        col 3: Filter      synthesized (always 0); NOT used on write-back
        col 4: Pulse       ← NP21 byte 6
        col 5: Wave        ← NP21 byte 7

    On SF2→NP21 propagation (this function): we write back the 5 fields
    the SF2 view actually exposes (AD/SR/HR/Pulse/Wave); NP21 bytes 3/4/5
    are read from `np21_existing` and preserved unchanged. The Filter
    column (SF2 col 3) is not propagated because NP21's filter selection
    is global per song, not per instrument.

    Args:
        sf2_bytes:     n_rows * 6 bytes from the SF2 edit area
        np21_existing: n_rows * 8 bytes currently in the NP21 binary
        n_rows:        number of rows (default 32)

    Returns:
        n_rows * 8 bytes ready to write back into the NP21 binary at
        instr_addr ($1A6B for Stinsen).
    """
    sf2_n  = n_rows * SF2_INSTR_COLS
    np21_n = n_rows * NP21_INSTR_COLS
    if len(sf2_bytes) < sf2_n:
        raise ValueError(f"SF2 instr bytes too short: {len(sf2_bytes)} < {sf2_n}")
    if len(np21_existing) < np21_n:
        raise ValueError(f"NP21 existing too short: {len(np21_existing)} < {np21_n}")

    out = bytearray(np21_n)
    for r in range(n_rows):
        sf2_off  = r * SF2_INSTR_COLS
        np21_off = r * NP21_INSTR_COLS

        # SF2 → NP21 propagated fields
        out[np21_off + 0] = sf2_bytes[sf2_off + 0]   # AD
        out[np21_off + 1] = sf2_bytes[sf2_off + 1]   # SR
        out[np21_off + 2] = sf2_bytes[sf2_off + 2]   # HR (flags1)
        # bytes 3, 4, 5 preserved from existing NP21
        out[np21_off + 3] = np21_existing[np21_off + 3]   # flags2
        out[np21_off + 4] = np21_existing[np21_off + 4]   # flags3
        out[np21_off + 5] = np21_existing[np21_off + 5]   # pulse_param
        out[np21_off + 6] = sf2_bytes[sf2_off + 4]   # Pulse ptr
        out[np21_off + 7] = sf2_bytes[sf2_off + 5]   # Wave ptr

    return bytes(out)


def convert_pulse_table(sf2_bytes: bytes, np21_existing: bytes,
                        n_rows: int = DEFAULT_PULSE_ROWS) -> bytes:
    """Pulse: row-by-row merge. NP21 has 4 bytes/row, SF2 has 3.

    SF2 emits cols 0..2 of each NP21 4-byte row (per `sf2_writer.py`
    Stage 4 emit comment: "drop the last byte, which is the next-program
    pointer in NP21 internals"). On write-back: copy SF2 cols 0..2 into
    NP21 bytes 0..2, preserve byte 3 from existing NP21.

    Args:
        sf2_bytes:     n_rows * 3 bytes from the SF2 edit area
        np21_existing: n_rows * 4 bytes currently in the NP21 binary
        n_rows:        number of rows (default 16)

    Returns:
        n_rows * 4 bytes ready to write back into the NP21 binary at
        pulse_table_addr ($1A3B for Stinsen).
    """
    sf2_n  = n_rows * SF2_PULSE_COLS
    np21_n = n_rows * NP21_PULSE_COLS
    if len(sf2_bytes) < sf2_n:
        raise ValueError(f"SF2 pulse bytes too short: {len(sf2_bytes)} < {sf2_n}")
    if len(np21_existing) < np21_n:
        raise ValueError(f"NP21 existing too short: {len(np21_existing)} < {np21_n}")

    out = bytearray(np21_n)
    for r in range(n_rows):
        sf2_off  = r * SF2_PULSE_COLS
        np21_off = r * NP21_PULSE_COLS
        out[np21_off + 0] = sf2_bytes[sf2_off + 0]
        out[np21_off + 1] = sf2_bytes[sf2_off + 1]
        out[np21_off + 2] = sf2_bytes[sf2_off + 2]
        out[np21_off + 3] = np21_existing[np21_off + 3]   # next-program ptr — preserved
    return bytes(out)


# Filter conversion: deferred to Phase B. NP21 stores three parallel arrays
# (resonance, sweep, mode) at filter_addr / +0x1A / +0x34 (Stinsen layout
# documented in `sidm2/sf2_writer.py:_build_np21_sf2_edit_area`). The SF2
# edit area presents them as a single 3-column table. The conversion needs
# to split the 3-col table back into three parallel arrays. Doable, but the
# layout is variant-dependent (different NP21 sub-versions have different
# offsets for the parallel arrays), so it's left for Phase B when a
# variant-detection pass exists.
