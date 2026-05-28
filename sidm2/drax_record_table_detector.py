"""Detect the DRAX/NP21-G4 instrument table (8-byte records).

History:
  - v3.5.67 `np21_packed_wave_detector` mislabeled this as a flat
    single-byte "wave table".
  - v3.5.68 corrected to "8-byte structured-record table, identity TBD".
  - v3.5.69 RESOLVED the identity: it is the **INSTRUMENT TABLE**.

# What this is (resolved v3.5.69)

The Y index at the field reads comes from `$18C8,X`, which is set to
`instrument_number * 8`:

    $11A9: CMP #$A0           ; sequence byte ≥ $A0 = "set instrument"
    $11AD: AND #$1F           ; instrument number 0-31
    $11AF: ASL A / ASL / ASL  ; × 8
    $11B2: STA $18C8,X        ; → Y source for the $1B8A reads

`$18C8` is SET on the set-instrument command and is NEVER incremented
per-frame (no INC/ADC on it), so the reads index whole 8-byte
instrument records — this is the instrument table, not a wave-program
table. The `& $1F` mask caps it at 32 instruments × 8 = 256 bytes;
the next table (a wave/arp program) begins right after at ~$1C8F.

The player reads several fields of the current instrument's record
with that Y (Dreams, $1316-$137F):

    LDA $1B8A,Y    ; +0  packed note-offset(low nibble) + ctrl(high bits)
    LDA $1B8B,Y    ; +1  (AD-ish; AND #$0F << 4 → $18E3)
    LDA $1B8C,Y    ; +2  command (BEQ skip if zero)
    LDA $1B8D,Y    ; +3  → $1906/$1909 scratch
    LDA $1B8E,Y    ; +4  flag bits (AND #$02)

The data confirms the 8-byte stride (clean 8-byte periodicity, ~32
records before the region ends).

The +0-field decode (note in low nibble, 2-bit selector in high bits)
is real; the full per-field semantics (bytes 1-7) are only partially
RE'd — enough to confirm "instrument record", not enough to emit a
faithful SF2 instrument row yet.

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

# Detected instrument-table addresses (RE-verified)

    Colorama  $1BDD    Delicate  $1C51
    Dreams    $1B8A    Omniphunk $1B73

Also matches Laxity's own G4 files (21_G4_demo_tune_*, Ocean_Reloaded).

# FALLBACK-only

⚠ The `LDA abs,Y; TAY; AND #$0F; … TYA; AND #mask` idiom also appears at
the PULSE/FILTER read sites of the 2-byte-format players (Beast/Angular),
where it returns a non-instrument-table address (e.g. $1B3F for Beast).
So this locator must only be consulted as a fallback — and note its
real use is the DRAX cluster's F2 (instrument) anchor, NOT F3 (wave);
the existing 2-byte wave detector already handles Beast/Angular.

# Status

Detection only. No extractor and no wire-in yet. The table IDENTITY is
now resolved (instrument table), but the full 8-byte record FIELD
semantics (bytes 1-7) are only partially RE'd — not yet enough to emit
a faithful SF2 instrument row. Building the instrument extractor is the
next step. See `memory/drax-np21-cluster-re.md`.
"""
from __future__ import annotations
from typing import NamedTuple, Optional


class DraxRecordTableLayout(NamedTuple):
    """Located DRAX/NP21-G4 INSTRUMENT table (8-byte records).

    `record_table_addr` is the instrument-table base (indexed by
    instrument_number * 8, up to 32 instruments). Field semantics of
    each 8-byte record are only partially RE'd — see module docstring.
    """
    record_table_addr: int   # absolute address of the instrument-table base
    field0_read_addr: int    # absolute address of the `LDA table,Y` (+0 field) instr
    field0_high_mask: int    # high-bit mask applied to the +0 field (e.g. $C0)


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
