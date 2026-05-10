"""Detect the Stinsen-class column-major NP21 instrument table.

Stinsen-class NP21 binaries (verified for `Stinsens_Last_Night_of_89.sid`)
store instruments in a COLUMN-MAJOR layout:

    AD column at $1808 (binary offset $0808 with load=$1000): one byte
                       per instrument, up to 20 instruments.
    SR column at $181C (binary offset $081C, delta $14 from AD).

The "instr 0" first-tick INIT defaults at $18D8/$18D9 are SEPARATE
from this table — they're loaded once on the first PLAY tick, then
the main table at $1808/$181C is the source for instrument-prefix
events.

Other columns (HR/restart, pulse_ptr, wave_ptr) live further into the
table region but their exact destination addresses haven't been
verified by direct-edit experimentation yet. See
memory/stinsen-instr-layout.md.

Detection strategy: match the binary signature at relative offset
$0800-$080F. The first 8 bytes look like leading flags `02 02 00 02
00 00 00 10` and the next 8 are the AD column's first 8 entries.

We're conservative: only Stinsen-exact-signature matches return a
positive result. Other Laxity NP21 variants (Beast, Angular, ...)
will fall through to the existing detector flow.
"""
from __future__ import annotations
from typing import Optional, NamedTuple


class StinsenInstrLayout(NamedTuple):
    ad_col_addr: int      # absolute address of AD column start
    sr_col_addr: int      # absolute address of SR column start
    n_instruments: int    # how many slots are USED (active in the
                           # voice sequences); upper bound = 20.


# Conservative signature: the leading flag bytes Stinsen has at $1800.
# Subject to refinement when more variants are inspected.
STINSEN_SIG_OFFSET = 0x0800   # binary offset (load+$0800 = $1800 for load=$1000)
STINSEN_SIG_BYTES  = bytes([0x02, 0x02, 0x00, 0x02, 0x00, 0x00, 0x00, 0x10])


def detect_stinsen_layout(c64_data: bytes, load_addr: int
                          ) -> Optional[StinsenInstrLayout]:
    """Return a StinsenInstrLayout if the binary matches the
    Stinsen-class column-major layout, else None.

    The layout is fixed-offset:
        AD column: load_addr + $0808
        SR column: load_addr + $081C  (= AD + $14)
    """
    if len(c64_data) < STINSEN_SIG_OFFSET + 0x40:
        return None
    if c64_data[STINSEN_SIG_OFFSET : STINSEN_SIG_OFFSET + 8] != STINSEN_SIG_BYTES:
        return None

    ad_col_off = STINSEN_SIG_OFFSET + 8        # $0808
    sr_col_off = ad_col_off + 0x14             # $081C

    # Sanity: SR column must be within the binary.
    if sr_col_off + 20 > len(c64_data):
        return None

    # Count active instruments by scanning the AD column for non-zero
    # entries. (The 20-slot column is sparsely populated.) We keep
    # everything up to and including the last non-zero AD byte, capped
    # at 20.
    ad_col = c64_data[ad_col_off : ad_col_off + 20]
    last_nonzero = -1
    for i, b in enumerate(ad_col):
        if b != 0:
            last_nonzero = i
    if last_nonzero < 0:
        return None    # all-zero AD column → not a real instrument table
    n = min(last_nonzero + 1, 20)

    return StinsenInstrLayout(
        ad_col_addr=load_addr + ad_col_off,
        sr_col_addr=load_addr + sr_col_off,
        n_instruments=n,
    )


def extract_stinsen_instruments(c64_data: bytes, load_addr: int
                                ) -> Optional[list[dict]]:
    """Read the AD/SR columns into a list of instrument dicts in the
    same shape as `extract_laxity_instruments`. Returns None if the
    binary doesn't match Stinsen layout.

    Only AD + SR are populated from the binary; other fields use
    NP21-equivalent defaults (we haven't yet RE'd HR/Pulse/Wave column
    destination addresses for Stinsen).
    """
    layout = detect_stinsen_layout(c64_data, load_addr)
    if layout is None:
        return None

    ad_col_off = layout.ad_col_addr - load_addr
    sr_col_off = layout.sr_col_addr - load_addr
    instruments = []
    for i in range(layout.n_instruments):
        ad = c64_data[ad_col_off + i]
        sr = c64_data[sr_col_off + i]
        instruments.append({
            'index': i,
            'ad': ad,
            'sr': sr,
            'restart': 0,        # HR / flags1 — not yet RE'd
            'filter_setting': 0,
            'filter_ptr': 0,
            'pulse_ptr': 0,
            'pulse_property': 0,
            'wave_ptr': 0,
            'ctrl': 0x41,
            'wave_for_sf2': 0x41,
            'name': f'Instr {i:02d}',
        })
    return instruments
