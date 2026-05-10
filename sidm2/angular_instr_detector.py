"""Detect the Angular-class row-major NP21 instrument table.

Angular-class NP21 binaries (verified for `Angular.sid`) store
instruments in a ROW-MAJOR layout, **2 bytes per instrument** (AD
followed by SR), starting at $1ADB. This is the most compact layout
seen so far — Stinsen uses column-major (separate AD/SR columns at
$1808/$181C), Beast uses row-major 8B/instrument (AD at +5, SR at +6
within each row).

Direct-edit RE confirmed 2026-05-10:
- Patch $1ADB ($0F → $5A): osc<v>_attack_decay flips on instr-0
  selection events.
- Patch $1ADC ($01 → $66): osc<v>_sustain_release flips similarly.

The chase probe also showed $1ADE = $28 read as SR for v2/v3 — that's
the SR for instr 1 (since instr 1 = $1ADD/$1ADE per 2-byte stride).

Per-row byte layout:
    +0: AD
    +1: SR
"""
from __future__ import annotations
from typing import Optional, NamedTuple


class AngularInstrLayout(NamedTuple):
    table_addr: int       # absolute address of instr table start
    n_instruments: int    # number of 2-byte rows in use
    ad_offset: int        # always 0
    sr_offset: int        # always 1


# Angular signature: bytes at $1AD8-$1AE0 — leading zeros + the first
# few instrument entries. The pattern '00 00 00 0F 01 A0 28 60 32' is
# distinctive enough (3 leading zeros, then AD/SR pairs starting with
# the verified $0F/$01 instr-0 entry).
ANGULAR_SIG_OFFSET = 0x0AD8
ANGULAR_SIG_BYTES  = bytes([0x00, 0x00, 0x00, 0x0F, 0x01, 0xA0, 0x28])
ANGULAR_TABLE_OFFSET = 0x0ADB    # binary offset of instr 0 AD


def detect_angular_layout(c64_data: bytes, load_addr: int
                          ) -> Optional[AngularInstrLayout]:
    if len(c64_data) < ANGULAR_TABLE_OFFSET + 0x40:
        return None
    if c64_data[ANGULAR_SIG_OFFSET : ANGULAR_SIG_OFFSET + len(ANGULAR_SIG_BYTES)] != ANGULAR_SIG_BYTES:
        return None

    # Count instruments by walking 2-byte rows from $1ADB until both
    # AD and SR are zero (terminator), capped at 24 rows.
    n = 0
    for i in range(24):
        row_off = ANGULAR_TABLE_OFFSET + i * 2
        if row_off + 2 > len(c64_data):
            break
        ad = c64_data[row_off]
        sr = c64_data[row_off + 1]
        if ad == 0 and sr == 0:
            if i > 0:
                break
        n = i + 1
    if n == 0:
        return None

    return AngularInstrLayout(
        table_addr=load_addr + ANGULAR_TABLE_OFFSET,
        n_instruments=n,
        ad_offset=0,
        sr_offset=1,
    )


def extract_angular_instruments(c64_data: bytes, load_addr: int
                                ) -> Optional[list[dict]]:
    layout = detect_angular_layout(c64_data, load_addr)
    if layout is None:
        return None
    base = layout.table_addr - load_addr
    instruments = []
    for i in range(layout.n_instruments):
        ad = c64_data[base + i * 2]
        sr = c64_data[base + i * 2 + 1]
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
