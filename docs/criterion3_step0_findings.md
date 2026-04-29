# Criterion 3 — Step 0 findings (NP21 byte semantics truth table)

**Date**: 2026-04-29
**Outcome**: v3.1.9's `+1` note shift was based on a wrong assumption.
Fixed in v3.2.2.

## Question

Step 0 of the criterion-3 plan (`docs/criterion3_plan.md`) asked: what does
each byte value actually mean to the NP21 player at runtime? The brief, the
existing converter at `sf2_writer.py:1693`, and the player disassembly were
all suspected of disagreeing.

## Method

1. Convert `SID/Laxity/Stinsens_Last_Night_of_89.sid` with the v3.2.1
   converter, dump the first 32 bytes of each voice's sequence pointed at by
   `c64_data[$0A1C+v]` / `c64_data[$0A1F+v]`.
2. Cross-check byte-by-byte with the player code at
   `drivers/laxity/laxity_player_disassembly.asm:111-156` (corresponds to
   addresses `$10C9-$1108` in the relocated player).

## Decisive code path

The reader at `$10F4-$10FB` decides what every "data byte with MSB clear"
(i.e. `< $80`) means:

```
$10F4: sta DataBlock_6+$103,X  ; store note byte into active-note slot
$10F7: beq Label_13            ; if A == 0x00 → "no new note" path
$10F9: cmp #$7E
$10FB: bne Label_14            ; if A != 0x7E → "real note" path

Label_13: inc DataBlock_6+$100,X  ; "no new note": only bumps the tick counter.
                                  ; The currently-active note keeps playing
                                  ; (gate stays in whatever state it is in).
Label_14: lda DataBlock_6+$10F,X  ; "real note": copy the byte into the
          sta DataBlock_6+$112,X  ; play-this-note slot, fresh trigger.
```

So:

| NP21 byte | Player branch                | Effect                         |
| --------- | ---------------------------- | ------------------------------ |
| `$00`     | Label_13 (via `BEQ`)         | No new note, no gate change    |
| `$7E`     | Label_13 (via `CMP/BNE`)     | Tie: keep current note playing |
| `$01-$7D` | Label_14 (via `BNE` fallthr) | Trigger this pitch             |

`$00` is **explicitly not "the lowest C"**. It is the same code path as
`$7E` (tie/no-event). Both are "this row of the sequence does not change
which pitch is sounding."

## Cross-check with real data

Stinsen voice 1 sequence (offset `$1A9B` in NP21 binary):

```
a0 00 12 06 06 06 07 25 25 16 17 06 06 18 25 25 06 06 06 06 1d 21 ff 00 ...
```

Byte 0 is `$A0` (set-instrument prefix) and byte 1 is `$00`. Per the
disassembly at `$10D9-$10E2`:

```
cmp #$A0           ; byte = $A0 → instrument byte
bcc Label_10
sta DataBlock_6+$106,X   ; store instrument index
iny
lda (ZP_0),Y       ; read NEXT byte ($00)
bpl Label_12       ; $00 has MSB clear → jump to Label_12
```

Label_12 stores `$00` into the note slot, then `BEQ Label_13` (no new note).

So the original song's voice-1 first frame is: "set instrument $A0, no
note this tick". Under the v3.1.9 converter the editor sees `$A0 $01` —
"set instrument $A0, play C-0". A note that does not exist in the source
appears in the editor.

## Impact

The bug existed since v3.1.9 (2026-03-30). It did not break playback
because the player reads from the embedded NP21 binary at `$1A1C/$1A1F`,
not from the SF2 edit area where the fix lives. zig64 frame-set match
stayed at 100% on both reference songs throughout.

The bug only manifests in the editor display — every silence-row in NP21
shows up as a C-0 note, and every actual note appears one semitone higher
than the original NP21 pitch. Hasn't been visually noticed because:

- No song in the test corpus has notes in the `$70-$7D` range that would
  also collide with the SF2 tie byte under the old shift (max we saw is
  `$26`).
- Visual confirmation in the actual SF2 editor was an outstanding manual
  test.

## SF2 packed sequence format reference

Source: `SIDFactoryII/source/runtime/editor/datasources/datasource_sequence.cpp`,
`DataSourceSequence::Unpack` lines 197-267. Pure-Python port:
`pyscript/verify_editor_view.py`.

| SF2 byte    | Meaning                                       |
| ----------- | --------------------------------------------- |
| `$00`       | gate off                                      |
| `$01-$6F`   | notes (`$01` = C-0; chromatic; `$6F` = max)   |
| `$7E`       | tie / note-on                                 |
| `$7F`       | end of sequence                               |
| `$80-$9F`   | duration byte (low nibble = ticks; bit 4=tie) |
| `$A0-$BF`   | set-instrument prefix                         |
| `$C0-$FF`   | command prefix (next byte = payload)          |

The reader asserts `value < 0x80` after stripping all control prefixes
— so any byte in `$70-$7D` would crash the editor's `Unpack`. The shift in
v3.1.9 was unsafe for that range; fixed by clamping to `$6F` in v3.2.2.

## Correct mapping (shipped in v3.2.2)

```
NP21 0x00       → SF2 0x00          (no event / gate off)
NP21 0x01-0x6F  → SF2 0x01-0x6F     (identity)
NP21 0x70-0x7D  → SF2 0x6F          (clamp; NP21 has wider pitch range)
NP21 0x7E       → SF2 0x7E          (tie/gate-on)
NP21 0x80-0xFF  → SF2 0x80-0xFF     (identity for all control bytes)
```

NP21 `$7F` (true end-of-data) is unreachable in body bytes because
`_extract_raw_seq` stops at the loop terminator before any `$7F` is
emitted into the SF2 edit area.

## Implication for the criterion 3 plan

The reverse direction (SF2 → NP21 in the runtime translator at `$0F0E`)
needs the inverse of the v3.2.2 mapping:

```
SF2 0x00       → NP21 0x00          (no event)
SF2 0x01-0x6F  → NP21 0x01-0x6F     (identity)
SF2 0x7E       → NP21 0x7E          (tie)
SF2 0x7F       → NP21 0xFF, 0x00    (end → emit NP21 loop terminator)
SF2 0x80-0xFF  → NP21 0x80-0xFF     (identity)
```

Identity in both directions for almost everything. The only true work the
runtime translator has to do is rewrite SF2's `$7F` end-of-sequence into
NP21's `$FF $00` loop-to-start marker. Compare with the original criterion 3
plan's per-byte transform (Step 3 pseudocode at `docs/criterion3_plan.md`),
which assumed a shift was needed — that pseudocode can be simplified.
