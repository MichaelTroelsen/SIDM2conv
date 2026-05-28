"""Detect the NP21-G4 single-byte-packed wave table.

A subset of the NP21-G4 NewPlayer family (Laxity's G4 variant + Thomas
Mogensen / DRAX's fork of it) packs the wave program into ONE byte per
step instead of the 2-byte (note_offset, waveform) rows that the
Stinsen / Beast / Angular variants use:

    bits 0-3 (low nibble): note offset (added to the base note)
    bits 6-7 (high 2 bits): waveform select

The player reads a wave-program byte and splits it with two masks. The
canonical read path (Dreams, $137F):

    B9 8A 1B    LDA $1B8A,Y    ; ← wave table, Y = per-voice wave-prog pos
    A8          TAY            ; reuse the byte as an index
    29 0F       AND #$0F       ; low nibble = note offset
    9D 24 19    STA $1924,X    ; → note-offset scratch
    ...
    98          TYA            ; recover the byte
    29 C0       AND #$C0       ; high 2 bits = waveform select

# This is a FALLBACK detector

⚠ The `LDA abs,Y; TAY; AND #$0F; … TYA; AND #$mask` packed-split idiom
ALSO appears in the Stinsen/Beast/Angular players — but at their PULSE
or FILTER read sites, NOT their wave read (those variants use 2-byte
wave rows located by `find_wave_table_from_player_code`). So this
detector mislocates if used as the primary wave-table source for a
2-byte-format file (e.g. it returns $1B3F for Beast, whose real wave
table is $19AD/$19E7).

Therefore this detector MUST be consulted only as a FALLBACK — when
`extract_all_laxity_tables` returns no `wave_data_addr` (the standard
2-byte heuristic failed). For the four DRAX "None wired" files
(Colorama, Delicate, Dreams, Omniphunk) the standard heuristic does
fail, and this detector returns the RE-verified correct wave table:

    Colorama  $1BDD    Delicate  $1C51
    Dreams    $1B8A    Omniphunk $1B73

It also matches the Laxity-G4 files (21_G4_demo_tune_*, Ocean_Reloaded)
which share the single-byte format.

# Status: detector checkpoint (v3.5.67)

This module is detection only. The wave-program EXTRACTOR (decode the
single-byte stream into SF2 editor rows) and the F3 write-back routine
(re-pack edited rows into the single-byte format) are the next steps
and are NOT in this module. See `memory/drax-np21-cluster-re.md`.
"""
from __future__ import annotations
from typing import NamedTuple, Optional


class PackedWaveLayout(NamedTuple):
    """Resolved addresses for an NP21-G4 single-byte-packed wave table."""
    wave_table_addr: int    # absolute address of the packed wave program table
    wave_read_addr: int     # absolute address of the `LDA wave_table,Y` instr
    waveform_mask: int      # the high-bit mask (e.g. $C0) used to extract waveform


def detect_packed_wave_table(
    c64_data: bytes,
    sid_la: int,
) -> Optional[PackedWaveLayout]:
    """Locate the single-byte-packed wave table via its read-path signature.

    Matches the first occurrence of:

        B9 <lo> <hi>   ; LDA wave_table,Y
        A8             ; TAY
        29 0F          ; AND #$0F  (low nibble = note offset)
        ...            ; (up to ~20 bytes)
        98             ; TYA
        29 <mask>      ; AND #<high-bit mask>  (waveform select)

    where the `B9` operand is in the binary's address range.

    Args:
        c64_data: The NP21 binary bytes.
        sid_la:   The binary's C64 load address.

    Returns:
        PackedWaveLayout, or None if the signature isn't present.

    ⚠ FALLBACK ONLY — see module docstring. Do not use to override a
    successful 2-byte wave detection; the idiom also appears at
    pulse/filter read sites in 2-byte-format players.
    """
    end = sid_la + len(c64_data)
    n = len(c64_data)
    for i in range(n - 6):
        if not (c64_data[i] == 0xB9          # LDA abs,Y
                and c64_data[i + 3] == 0xA8  # TAY
                and c64_data[i + 4] == 0x29  # AND #
                and c64_data[i + 5] == 0x0F):  # #$0F (low nibble)
            continue
        tbl = c64_data[i + 1] | (c64_data[i + 2] << 8)
        if not (sid_la <= tbl < end):
            continue
        # Look for TYA (98) + AND # (29 mask) within the next ~20 bytes —
        # the waveform-select extraction from the same loaded byte.
        window_start = i + 6
        window_end = min(i + 26, n - 1)
        for k in range(window_start, window_end):
            if c64_data[k] == 0x98 and c64_data[k + 1] == 0x29:
                mask = c64_data[k + 2]
                return PackedWaveLayout(
                    wave_table_addr=tbl,
                    wave_read_addr=sid_la + i,
                    waveform_mask=mask,
                )
    return None
