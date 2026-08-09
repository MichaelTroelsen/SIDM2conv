# HardTrack Composer — instrument fields 6/7/12 and the slide commands

Closes open item 4 of the HardTrack arc ("identify instrument fields 6, 7, 12;
confirm the global filter sweep's un-reset cursor"). Method: the player was run
under RetroDebugger and the consumers of every field table were read off the
live, execute-marked disassembly, then each reading was checked against a
falsifiable prediction over the whole corpus.

> **Why this is a separate file.** It was written while two other sessions held
> uncommitted edits to `hardtrack_parser.py` and `HARDTRACK.md`. Fold it into
> HARDTRACK.md's field table and filter section when they land; nothing here
> needs to stay standalone.

## All 13 fields are read by the player

A sliding scan for every 3-byte absolute opcode whose operand equals a field
table base finds a reference to **all 13 fields in all 33 decodable files** —
none is editor-only storage. Fields 6, 7 and 12 are consumed in one block, the
filter setup at note-on (addresses are `Love_tune_2`, `n=32`, base `$1715`):

```
138F  LDA $1895,Y   ; f12 -- 0 => voice's filter routing OFF ($13CB path)
1394  PHA / AND #$0F / ASL x4 / STA $15BD    ; low nibble  -> $D418 mode nibble
139F  PLA / AND #$F0 / ORA ($101F & $0F)
13AA  ORA $16D7,X   ; this voice's filter-route bit
13AD  STA $101F / STA $D417                  ; high nibble -> RESONANCE
13B3  LDA $17F5,Y   ; f7  -> STA $15B2
13B9  LDA $17D5,Y   ; f6  -> STA $158F
13BF  LDA #$00 / STA $15B5                   ; delta  := 0
13C4  LDA #$03 / STA $16B2                   ; delay  := 3 frames
```

`$15B2`, `$15BD`, `$158F` and `$15B5` are **self-modified operands** inside the
filter engine, which is why a static operand scan alone never named them:

```
1589  DEC $16B2 / BNE $15B1        ; step delay
158E  LDY #$10                     ; <- $158F  = program CURSOR
1590  INC $158F
1593  LDA $1983,Y                  ; the filter program
1596  CMP #$80 / BNE $15A4
159A  INY / LDA $1983,Y / STA $158F / JMP $158E   ; $80 <idx> = jump
15A4  STA $15B5                    ; <- delta per frame
15A7  INY / INC $158F / LDA $1983,Y / STA $16B2   ; <- delay
15B1  LDA #$5A                     ; <- $15B2  = cutoff ACCUMULATOR
15B3  CLC / ADC #$40               ; <- $15B5  = delta
15B6  STA $15B2 / STA $D416        ; cutoff
15BC  LDA #$30                     ; <- $15BD  = mode nibble
15BE  ORA $1006 / STA $D418        ; ORed with the volume byte
```

| field | role |
|---|---|
| **6** | start **cursor into the filter program** (the `LDY #` operand at `$158E`) |
| **7** | **initial cutoff** — seeds the accumulator the sweep adds to, `-> $D416` |
| **12** | `(resonance << 4) \| mode`; **zero means this voice is not routed through the filter** |

### Three predictions, all confirmed on the corpus

Over 926 instruments in 33 files, 153 have `f12 != 0`:

- **f12 low nibble** is confined to `{0,1,3,4,5,6,9,14}` — every one a valid
  `$D418` high-nibble pattern (LP/BP/HP, plus `$80` voice-3-off). It is *not*
  spread over 0-15, which is what a byte with some other meaning would look like.
- **f12 high nibble** is `$F` for 131 of 153 — max resonance, exactly the
  distribution a resonance field should have on filter instruments.
- **f6 is even in 153 of 153 cases**, max 14. The program is `[delta][delay]`
  pairs, so a cursor into it must be pair-aligned. A byte meaning anything else
  would not be even every time.
- f7 spreads across the whole 0-255 range in all eight 32-wide buckets — a cutoff.

### The filter sweep is per-instrument, not merely "global"

HARDTRACK.md currently calls it "a third, song-level program … its cursor lives
in self-modified code and `init` does not reset it". Both halves are true but the
conclusion drawn from them is too weak: the **table** is song-level and there is
only one filter engine (the SID has one filter), but the **entry point (f6), the
starting cutoff (f7) and the resonance/mode/routing (f12) are per-instrument and
are rewritten on every note-on**, with delta reset to 0 and delay to 3 frames. It
behaves as a per-instrument filter envelope sharing one global step table.

The un-reset cursor is confirmed and is only about `init`: the saved `LDY #`
operand differs per file (`$10` in `Love_tune_2`, `$04` in `Zakplus`, `$00` in
`Jazzloor`), so a ripped file does carry whatever it was saved with — but that
value survives only until the first note-on of a filtered instrument.

### Relocation-safe recovery

The filter program table is recoverable by signature, like every other address:

```python
_SIG_FILTPROG = [0xA0, _W, 0xEE, _W, _W, 0xB9, _W, _W, 0xC9, 0x80]
#   ldy #cursor / inc cursor / lda FILTPROG,y / cmp #$80
#   +1 = the saved cursor, +6/+7 = the table address
```

**Unique in 33 of 33 decodable files.**

## `$63` and `$64` are slide UP and slide DOWN

Not slide-versus-portamento. Both handlers are identical apart from one store:

```
1151  CMP #$63 / STA $16A6,X / LDA #$00 / STA $16A9,X   ; direction := 0
1168  CMP #$64 / STA $16A6,X / STA $16A9,X              ; direction := $64
      ; both then: INC pattern cursor / LDA ($FB),Y / STA $16AC,X   = step
```

and the engine branches on that byte alone:

```
14A5  LDA $16A6,X / BEQ (vibrato path)
14AA  LDA $16A9,X / BNE $14C7
14AF  LDA $1694,X / CLC / ADC $16AC,X / BCS -> INC $1691,X    ; UP
14C7  LDA $1694,X / SEC / SBC $16AC,X / BCC -> DEC $1691,X    ; DOWN
```

There is **no target note** — it is a continuous per-frame pitch ramp of
`$16AC` units, running until the state is cleared. Calling `$64` a portamento
implies a destination the engine does not have.

`$1691`/`$1694` were confirmed live to be the per-voice frequency hi/lo: in a
paused snapshot they read `$CC00 / $3426 / $02xx` while `$D400-$D40F` held
exactly the same three values. Injecting `$16A6=$63, $16A9=$00, $16AC=$80` into
voice 0 of a running tune drove it `$CC00 -> $FF00` (saturating up); switching to
`$16A6=$64, $16A9=$64` drove it `$FF00 -> $0685`.

`sidm2/hardtrack_parser.py` names these `CMD_SLIDE` / `CMD_PORTA`;
`CMD_SLIDE_UP` / `CMD_SLIDE_DOWN` would say what the player does.

## Also seen in passing

`$14DF` onward, reached when no slide is active, is a **vibrato** engine: delay
`$16F8,X`, depth `$101C,X`, step count `$16FB,X`/`$16BF,X`, phase
`$16EC,X`/`$16FE,X`. It is the most likely consumer of instrument fields 8-11,
which are currently documented only as "nibbles -> counters", "param block" and
"synth-program parameters". Not investigated further here.

## Reproducing

The tune has to be *run*, so it needs an IRQ: wrap the module as a PRG with a
BASIC stub, `JSR init`, a raster IRQ calling `play`, and an idle loop, then
`retro_load` it and jump the PC to the wrapper. (Watch the idle loop's own
address — a `JMP` whose operand overlaps its target sends the CPU somewhere
else and the tune keeps playing from the IRQ for a while regardless, which
looks like a working run.)

---

# Addendum — a second, independent pass

Everything above was reached by driving the *player* under RetroDebugger. The
sections below come from a separate pass that read the same consumers off a
static disassembly and then booted the *editor*. The three field identities
(f6 cursor, f7 initial cutoff, f12 resonance/mode/routing) and the slide
direction reading were reproduced independently and are not restated here.

Every count below is regenerated by `pyscript/hardtrack_player_xref.py` and
pinned by `pyscript/test_hardtrack_player_xref.py` (101 tests), so none of it
has to be taken on trust:

```
33 decodable modules in SID/Shogoon
  every field read exactly once (field 5: 3x)  OK 33/33
  field 5 masked only with $03/$10/$80         OK 33/33
  slide byte: 2 handlers + 1 note-on clear     OK 33/33
```

## Field 5 bit 4 gates the filter re-arm — it is not a hard restart

`sidm2/hardtrack_parser.py` exposes bit 4 of the flag byte as `hard_restart`.
The player never uses it that way. Field 5 is read exactly three times per
file, and the masks are `$03`, `$10`, `$80` in **33 of 33** modules — bits 2,
5 and 6 are never consulted at all. Bit 4's single consumer sits immediately
in front of the filter block the sections above describe:

```
137D  LDA F5,Y / AND #$10 / BEQ $138F      ; bit clear -> arm the filter
1384  LDA $1701,X / CMP $1704,X / BNE $138F ; note changed -> arm it anyway
138C  JMP $13D7                             ; same note again -> skip the
                                            ; WHOLE filter re-arm
$138F  LDA F12,Y ...                        ; (the filter block)
```

So bit 4 means *"on a repeated note, do not restart this instrument's filter
envelope"* — it suppresses one re-arm, and it reaches nothing else. Nothing in
the player restarts anything else on account of it. A Stage B driver that
implements it as a general hard restart will retrigger envelopes the original
holds.

## What ends a slide

The engine above runs "until the state is cleared", and what clears it is the
next note-on. The slide-active byte has exactly three stores in **33 of 33**
modules — the `$63` handler, the `$64` handler, and one `LDA #$00` inside the
note-on reset block (`$1315` in `Altered_States_Tune_1`, alongside the vibrato
and portamento state):

```
130A  LDA #$00 / STA $16DD,X / STA $16FE,X / STA $16AF,X / STA $16A6,X
```

A ramp therefore lives from its command byte to the next note on that voice,
and no further — which is what bounds it, given it has no target pitch.

## The editor boots — and does not label the fields

`whats-next.md` listed running the editor as "the strongest untapped lever" for
these fields, on the grounds that `bin/hardtrack composer/-HARDTRACK 1.PRG` is
crunched and yields nothing to a static scan. It does boot, and it does not
answer the question. Recording both halves so the lever is not picked up again.

It is a two-stage self-relocator, not a one-shot cruncher. `$0810` prints a
Polish banner (`DEKOMPRESJA, POCZEKAJ OK.10 SEKUND...`), copies a 49-byte
trampoline to `$0340` and jumps there; the trampoline banks RAM in, shifts
`$0900-$FFFF` down to `$0801`, and jumps to `$080B` of what it just moved — a
second PRG whose own stub relocates a decruncher to `$0100`. Then the editor
comes up: three 32-entry orderlists, `SPEED`/`SONG`/`OCT`, a 3-voice pattern
grid, and `HARDTRACK COMPOSER V.1.0`.

The main screen carries no field names — it is unlabelled hex throughout, and
the only words on it are `SPEED`, `SONG`, `OCT` and the title. F1 and F7 did not
switch views. Finding an instrument screen with its own labelling was not
achieved, and since the semantics are now settled twice over from the
consumers, editor labels would only corroborate.

**The gotcha that cost the most time here: `retro_load` does not clear RAM.**
Loading without a preceding `retro_reset` left the *previous* session's program
in memory, `retro_load` still reported `"loaded"`, and the PC ran into a `BRK`
in stale RAM at `$4C3D`. Several turns went into debugging a crash in someone
else's program. Read a few bytes at the load address and compare them against
the file before believing a load happened — the tool's success status does not
establish it.
