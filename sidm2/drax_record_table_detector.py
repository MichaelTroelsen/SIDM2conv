"""Detect the DRAX/NP21-G4 8-byte structured-record table.

Supersedes `np21_packed_wave_detector` (v3.5.67), which mislabeled this
table as a flat single-byte "wave table". v3.5.68 correction: it is a
table of **8-byte structured records**, not flat single-byte entries.

# What this is

A subset of the NP21-G4 NewPlayer family (Laxity's G4 variant + Thomas
Mogensen / DRAX's fork) uses a per-voice step/instrument table whose
records are 8 bytes wide. The player reads several fields of the same
record with one Y index (Dreams, $1316-$137F):

    LDA $1B8A,Y    ; +0 field
    LDA $1B8B,Y    ; +1 field
    LDA $1B8C,Y    ; +2 field
    LDA $1B8D,Y    ; +3 field
    LDA $1B8E,Y    ; +4 field

The data confirms the 8-byte stride (clean 8-byte periodicity in the
table region).

## The +0 field IS a packed note+waveform byte

The detection signature keys on the +0-field read + decode (Dreams,
$137F):

    B9 8A 1B    LDA $1B8A,Y    ; +0 field
    A8          TAY
    29 0F       AND #$0F       ; low nibble = note offset → scratch
    ...
    98          TYA
    29 C0       AND #$C0       ; high 2 bits (waveform-ish / gate path)

So the +0 byte packs a note offset (low nibble) and a 2-bit selector
(high bits). That part of the v3.5.67 RE was correct. What was WRONG
was extrapolating "the whole table is flat single-byte entries" — it
is 8-byte records, and the other fields (+1 = AD-ish, +2 = command,
+3/+4 = more step data) are NOT decoded by this detector.

## Wave table vs instrument table: UNRESOLVED

Whether this 8-byte-record table is the wave-program-step table or the
instrument table is not yet determined. The field layout (packed
note+wf at +0, AD-ish at +1, command at +2) is consistent with either.
Resolving it needs tracing whether Y is a per-frame wave-step position
or a per-note instrument index. Until resolved, this module only
claims to LOCATE the table, not to interpret its full semantics.

# Detected addresses (RE-verified locations, semantics TBD)

    Colorama  $1BDD    Delicate  $1C51
    Dreams    $1B8A    Omniphunk $1B73

Also matches Laxity's own G4 files (21_G4_demo_tune_*, Ocean_Reloaded).

# FALLBACK-only

⚠ The `LDA abs,Y; TAY; AND #$0F; … TYA; AND #mask` idiom also appears at
the PULSE/FILTER read sites of the 2-byte-format players (Beast/Angular),
where it returns a non-table address (e.g. $1B3F for Beast, whose real
wave table is $19AD via the 2-byte detector). So this locator must only
be consulted as a fallback, when the standard 2-byte detector fails.

# Status

Detection only. No extractor and no wire-in. The exact record format
(and wave-vs-instrument identity) is still under investigation — see
`memory/drax-np21-cluster-re.md`. Do NOT build an extractor on this
until the record semantics are confirmed.
"""
from __future__ import annotations
from typing import NamedTuple, Optional


class DraxRecordTableLayout(NamedTuple):
    """Located DRAX/NP21-G4 8-byte-record table (semantics TBD)."""
    record_table_addr: int   # absolute address of the 8-byte-record table base
    field0_read_addr: int    # absolute address of the `LDA table,Y` (+0 field) instr
    field0_high_mask: int    # the high-bit mask applied to the +0 field (e.g. $C0)


def detect_drax_record_table(
    c64_data: bytes,
    sid_la: int,
) -> Optional[DraxRecordTableLayout]:
    """Locate the DRAX 8-byte-record table via its +0-field read signature.

    Matches the first occurrence of:

        B9 <lo> <hi>   ; LDA table,Y   (+0 field of an 8-byte record)
        A8             ; TAY
        29 0F          ; AND #$0F      (low nibble = note offset)
        ...            ; (up to ~20 bytes)
        98             ; TYA
        29 <mask>      ; AND #<mask>   (high-bit selector on the +0 byte)

    where the `B9` operand is in the binary's address range.

    Returns a DraxRecordTableLayout, or None if the signature is absent.

    ⚠ FALLBACK ONLY — the idiom also appears at pulse/filter sites in
    2-byte-format players. See module docstring.
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
        window_end = min(i + 26, n - 1)
        for k in range(i + 6, window_end):
            if c64_data[k] == 0x98 and c64_data[k + 1] == 0x29:
                return DraxRecordTableLayout(
                    record_table_addr=tbl,
                    field0_read_addr=sid_la + i,
                    field0_high_mask=c64_data[k + 2],
                )
    return None
