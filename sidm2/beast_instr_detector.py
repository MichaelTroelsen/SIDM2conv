"""Detect the Beast-class row-major NP21 instrument table.

Beast-class NP21 binaries (verified for `Beast.sid`) store instruments
in a ROW-MAJOR layout, 8 bytes per instrument, with AD at byte 5 and
SR at byte 6 of each row. The table starts at $1B38 (binary offset
$0B38 with load=$1000).

Per-row byte layout:
    +0..+4: NP21-internal flags / pointers (untouched by Phase B.2)
    +5: AD (Attack/Decay)
    +6: SR (Sustain/Release)
    +7: NP21-internal (untouched)

Direct-edit RE confirmed AD/SR positions by patching $1B3D / $1B45
($07→$5A and $07→$3C respectively) and observing osc2_attack_decay
register write flips in zig64 trace.

Other byte offsets within the row (0..4 and 7) likely contain
HR/Filter/Pulse/Wave-related fields but their exact semantics aren't
RE'd. Phase B.2 wire-up only propagates AD+SR; user edits to other
F2 columns won't affect Beast playback.
"""
from __future__ import annotations
from typing import Optional, NamedTuple


class BeastInstrLayout(NamedTuple):
    table_addr: int       # absolute address of instrument table start
    n_instruments: int    # number of 8-byte rows in use
    ad_offset: int        # AD field offset within row
    sr_offset: int        # SR field offset within row


# Beast signature: row 0 of the instrument table at binary offset $0B38.
# Matches the bytes at $1B38: '70 00 00 00 00 07 F8 10' followed by row
# 1 at $1B40: '00 00 04 00 00 07 E8 10'.
BEAST_SIG_OFFSET = 0x0B38
BEAST_SIG_BYTES = bytes([
    0x70, 0x00, 0x00, 0x00, 0x00, 0x07, 0xF8, 0x10,
    0x00, 0x00, 0x04, 0x00, 0x00, 0x07, 0xE8, 0x10,
])


def detect_beast_layout(c64_data: bytes, load_addr: int
                        ) -> Optional[BeastInstrLayout]:
    """Match Beast's row-major instrument table at $1B38."""
    if len(c64_data) < BEAST_SIG_OFFSET + 0x80:
        return None
    if c64_data[BEAST_SIG_OFFSET : BEAST_SIG_OFFSET + 16] != BEAST_SIG_BYTES:
        return None

    # Count contiguous 8-byte rows by walking forward looking for non-zero
    # AD bytes (offset 5 within each row). Stop at the first all-zero AD
    # in a row that has all-zero AD/SR (i.e., terminator), capped at 24.
    n = 0
    for i in range(24):
        row_off = BEAST_SIG_OFFSET + i * 8
        if row_off + 8 > len(c64_data):
            break
        ad = c64_data[row_off + 5]
        sr = c64_data[row_off + 6]
        if ad == 0 and sr == 0:
            # Treat all-zero AD+SR as terminator (instrument unused)
            # AFTER first non-zero row. Always include row 0.
            if i > 0:
                break
        n = i + 1
    if n == 0:
        return None

    return BeastInstrLayout(
        table_addr=load_addr + BEAST_SIG_OFFSET,
        n_instruments=n,
        ad_offset=5,
        sr_offset=6,
    )


def extract_beast_instruments(c64_data: bytes, load_addr: int
                              ) -> Optional[list[dict]]:
    """Read AD/SR from Beast's row-major instrument table into the
    extract_laxity_instruments dict shape. Returns None if not Beast."""
    layout = detect_beast_layout(c64_data, load_addr)
    if layout is None:
        return None
    base = layout.table_addr - load_addr
    instruments = []
    for i in range(layout.n_instruments):
        row_off = base + i * 8
        ad = c64_data[row_off + layout.ad_offset]
        sr = c64_data[row_off + layout.sr_offset]
        instruments.append({
            'index': i,
            'ad': ad,
            'sr': sr,
            'restart': 0,
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
