"""Detect the Martin Galway "1st-generation" player (1984-mid-1987).

Reverse-engineered from Martin Galway's own commented source
(github.com/MartinGalway/C64_music), 2026-05-28. Full engine map:
`docs/analysis/GALWAY_1STGEN_ENGINE.md`.

# What the 1st-gen player is

NOT a flat-table player (unlike SF2 Driver 11 / Laxity NP21). Each of the
3 SID voices runs a **bytecode interpreter** over a per-channel command
stream (`PCn` program counter, read via `(PCn),Y`). Stream bytes < `$C0`
are note records (`[note][duration]`, 2 bytes); bytes >= `$C0 = COM` are
commands dispatched through a per-voice jump table `vtn`
(Ret/Call/Jmp/For/Next/Transp/Vlm/Filter/Freq/... — 22 opcodes). A
separate per-voice synth stage (`SOUNDn`) writes the SID voice registers
each frame. This is why a Driver-11 table remap can't reproduce it
faithfully — the music is an executed program (loops, calls, inline code).

# Detection signatures (validated against the SID/Galway_Martin/ corpus)

Two co-occurring code idioms (operands wildcarded; the VM code is shared
across files so only operands — ZP/table addresses — vary):

1. **Command dispatch** — the `read.byteN` site. Universal prefix
   `C9 C0  90 ??` (`CMP #$C0 ; BCC not-control`) followed by one of three
   variant tails:

   - `indirect`  : computed `JMP (vt0)` (self-modifies the low operand byte).
                   `ADC #imm` + `STA abs` + `JMP (ind)` within a short window;
                   `INY` may precede the ADC (Wizball/Arkanoid: `C8 69 ?? 8D
                   ?? ?? [B1 ??] 6C ?? ??`) or follow the STA (Parallax:
                   `69 ?? 8D ?? ?? C8 6C ?? ??`). `vt0` = the `6C` operand.
   - `indexed`   : `AA BD ?? ?? 8D ?? ?? …` (TAX ; LDA vt0-192,X). `vt0` =
                   that `LDA abs,X` operand + `$C0`. Green Beret-style.
   - `masked`    : `29 3F AA BD ?? ?? 8D ?? ?? …` (AND #$3F ; TAX ; LDA
                   vt0,X). `vt0` = that `LDA abs,X` operand (read directly).
                   Rambo-style.

2. **Note frequency write** — the `NOTE0` site:
   `BC ?? ??  BD ?? ??  …  8D 00 D4  8C 01 D4`
   (`LDY HiFrq,X ; LDA LoFrq,X ; … ; STA $D400 ; STY $D401`). Gives the
   `LoFrq`/`HiFrq` split byte-table addresses.

3. (confidence booster) **INITSOUND reset loop**:
   `A9 08 9D 00 D4 A9 00 9D 00 D4 CA 10` — distinctive double-store clear.

Detection = (dispatch variant found) AND (note-freq idiom found).
`confidence = "high"` when the init loop is also present, else `"medium"`.

# Relocation — reported addresses are RUNTIME

Several Galway SIDs load at one address but copy the player to another at
init (e.g. Game Over loads at $0F00 but runs at $E000; Green Beret loads
at $9F90, tables at $ED00). The operand-encoded addresses below are the
player's RUNTIME addresses and may fall OUTSIDE [sid_la, sid_la+len).
Do NOT validate them against the load range; their mutual self-consistency
(vt0 / LoFrq / HiFrq clustering in one region) is the real signal.

# Coverage

- All three dispatch encodings (indirect / indexed / masked) are handled,
  covering every 1st-gen file in the SID/Galway_Martin/ corpus that carries
  the engine (incl. Parallax = indirect-reordered, Rambo = masked).
- Distinguishes 1st-gen from 2nd-gen: the known 2nd-gen files (Athena,
  Times of Lore, Insects in Space) match NEITHER idiom and return None.

# Status

Detection only. No extractor, no conversion wire-in (checkpoint-first,
per the v3.5.x detector-before-extractor discipline). The intended use is
the anchor for a future audio-embed path and/or editor-view extractor.
See `memory/galway-1stgen-engine-map.md`.
"""
from __future__ import annotations

from typing import NamedTuple, Optional


class Galway1stGenLayout(NamedTuple):
    """Located Martin Galway 1st-gen player structures.

    All addresses are RUNTIME (operand-encoded) — see module docstring on
    relocation; they may differ from the SID load address.
    """
    dispatch_variant: str        # "indirect" | "indexed" | "masked"
    dispatch_addr: int           # runtime addr of the read.byteN dispatch site
    vt0_addr: int                # runtime addr of the voice-0 command jump table
    lofrq_addr: int              # LoFrq table (note -> freq low byte)
    hifrq_addr: int              # HiFrq table (note -> freq high byte)
    note_write_addr: int         # runtime addr of the STA $D400/$D401 note write
    initsound_addr: Optional[int]  # INITSOUND reset-loop addr, or None
    confidence: str              # "high" (init loop found) | "medium"


def _match(b: bytes, i: int, pat) -> bool:
    if i + len(pat) > len(b):
        return False
    return all(p is None or b[i + j] == p for j, p in enumerate(pat))


def _word(b: bytes, i: int) -> int:
    return b[i] | (b[i + 1] << 8)


def _find_dispatch(b: bytes):
    """First command-dispatch site. Returns (file_off, variant, vt0) or None.

    All sites share the prefix `C9 C0 90 ??` (CMP #$C0 ; BCC). The tail
    encodes how the command byte selects a `vtn` jump-table entry:

      indirect  computed `JMP (vtn)` (self-modifies the low operand byte).
                ADC #imm + STA abs + JMP (ind) appear within a short window;
                INY may sit before the ADC (Wizball/Arkanoid) or after the
                STA (Parallax), and Wizball inserts a `LDA (zp),Y`. vt0 = the
                `6C` (JMP indirect) operand.
      indexed   `AA BD <vt0-192>` — TAX ; LDA vt0-192,X. vt0 = operand+$C0.
                (Green Beret)
      masked    `29 3F AA BD <vt0>` — AND #$3F ; TAX ; LDA vt0,X. vt0 =
                operand (read directly). (Rambo)
    """
    n = len(b)
    for i in range(n):
        if not _match(b, i, [0xC9, 0xC0, 0x90, None]):  # CMP #$C0 ; BCC
            continue
        # masked (Rambo): AND #$3F ; TAX ; LDA vt0,X
        if _match(b, i + 4, [0x29, 0x3F, 0xAA, 0xBD, None, None, 0x8D]):
            return (i, "masked", _word(b, i + 8))
        # indexed (Green Beret): TAX ; LDA vt0-192,X ; STA abs
        if _match(b, i + 4, [0xAA, 0xBD, None, None, 0x8D]):
            return (i, "indexed", (_word(b, i + 6) + 0xC0) & 0xFFFF)
        # indirect: ADC #imm (at i+4 or i+5) + STA abs + ... + JMP (vt0)
        if b[i + 4] == 0x69 or (i + 5 < n and b[i + 5] == 0x69):
            seen_sta = False
            for k in range(i + 5, min(i + 15, n - 2)):
                if b[k] == 0x8D:
                    seen_sta = True
                elif b[k] == 0x6C and seen_sta:  # JMP (ind)
                    return (i, "indirect", _word(b, k + 1))
    return None


def _find_note_write(b: bytes):
    """First NOTE0 freq write. Returns (file_off, lofrq, hifrq) or None."""
    n = len(b)
    for i in range(n):
        # STA $D400 ; STY $D401
        if not _match(b, i, [0x8D, 0x00, 0xD4, 0x8C, 0x01, 0xD4]):
            continue
        # look back for LDY HiFrq,X (BC) ; LDA LoFrq,X (BD)
        for k in range(max(0, i - 16), i):
            if b[k] == 0xBC and k + 5 < n and b[k + 3] == 0xBD:
                return (i, _word(b, k + 4), _word(b, k + 1))
    return None


def _find_initsound(b: bytes) -> Optional[int]:
    for i in range(len(b)):
        if _match(b, i, [0xA9, 0x08, 0x9D, 0x00, 0xD4,
                         0xA9, 0x00, 0x9D, 0x00, 0xD4, 0xCA, 0x10]):
            return i
    return None


def detect_galway_1stgen(
    c64_data: bytes,
    sid_la: int,
) -> Optional[Galway1stGenLayout]:
    """Detect the Martin Galway 1st-gen player in a C64 binary image.

    Args:
        c64_data: the C64 binary (PSID data after the header / load word).
        sid_la: the SID load address (used only to convert file offsets to
            addresses for the dispatch/note-write/init SITE locations; the
            vt0/LoFrq/HiFrq addresses are runtime operands — see module
            docstring on relocation).

    Returns a Galway1stGenLayout, or None if the player is not present.
    """
    disp = _find_dispatch(c64_data)
    note = _find_note_write(c64_data)
    if disp is None or note is None:
        return None

    init_off = _find_initsound(c64_data)
    return Galway1stGenLayout(
        dispatch_variant=disp[1],
        dispatch_addr=sid_la + disp[0],
        vt0_addr=disp[2],
        lofrq_addr=note[1],
        hifrq_addr=note[2],
        note_write_addr=sid_la + note[0],
        initsound_addr=(sid_la + init_off) if init_off is not None else None,
        confidence="high" if init_off is not None else "medium",
    )
