# Laxity NewPlayer v21 Disassembly Analysis

*Detailed analysis of the Laxity player from Angular.sid disassembly*

## Overview

This document analyzes the disassembled Laxity NewPlayer v21 code from `test89/angular.asm`. Understanding this player internals is critical for reliable table extraction.

**Song**: Angular by Thomas Mogensen (DRAX), 2017 Camelot/Vibrants

---

## Memory Map

```
$1000-$103E    Entry points and metadata
$103F-$10A0    Init routine (song initialization)
$10A1-$1830    Play routine (main player loop)
$1833-$18F2    Frequency tables (96 notes × 2 bytes)
$18F3-$18FF    State flags and voice offsets
$1900-$199C    State variables (per-voice arrays)
$199F-$19AC    Sequence pointers and init data
$19AD-$19E6    Wave table
$19E7-$1A1D    Waveform values in wave table
$1A1E-$1A3A    Filter/tempo table
$1A3B-$1A6A    Pulse table
$1A6B-$1ADA    Instrument table
$1ADB+         Command table
$1B1B+         Sequence data pointers
```

---

## Entry Points

### Init Routine ($1000)

```assembly
initSongs:
    jmp  W103F+1        ; Jump to actual init at $1040
```

The init routine at $103F-$109B:
1. Loads song number (accumulator × 2 = index)
2. Sets up track pointers from table at $199F
3. Initializes state variables
4. Sets filter routing mask

### Play Routine ($10A1)

```assembly
playSound:
    jmp  W10A1          ; Main player entry

W10A1:
    bit  W18F3          ; Check player state
    bvs  W10D9          ; If bit 6 set: silence all voices
    bpl  W10E5          ; If bit 7 clear: process music
    ; ... first-call initialization
```

**State flags at $18F3:**
- Bit 7 ($80): First call - initialize player
- Bit 6 ($40): Song ended - silence voices
- Bit 7 clear: Normal playback

---

## Voice Processing

The player processes 3 voices in reverse order (X = 2, 1, 0):

```assembly
W1113:
    ldx  #$02           ; Start with voice 2
    ; ... process voice X
W17D2:
    dex                 ; Next voice
    bmi  W17D8          ; Done when X < 0
    jmp  W1113          ; Continue loop
```

### Per-Voice State Arrays

All state variables are indexed by X (voice number 0-2):

| Address | Size | Description |
|---------|------|-------------|
| $1901+x | 3 | Current sequence position (lo) |
| $1903+x | 3 | Current sequence position (hi) |
| $1905+x | 3 | Sequence start address (lo) |
| $1909+x | 3 | Sequence start address (hi) |
| $1913+x | 3 | Gate flag |
| $1916+x | 3 | Duration counter value |
| $1919+x | 3 | Current duration countdown |
| $191C+x | 3 | Note trigger state |
| $191F+x | 3 | Note age counter |
| $1921+x | 3 | Note + transpose value |
| $1923+x | 3 | Effect type |
| $1928+x | 3 | Processing flags |
| $192B+x | 3 | Transpose value |
| $192E+x | 3 | Base transpose |
| $1931+x | 3 | Current note |
| $1934+x | 3 | Instrument index × 8 |
| $1937+x | 3 | Command index × 2 |
| $1940+x | 3 | Frequency (lo) |
| $1942+x | 3 | Frequency (hi) |
| $1946+x | 3 | Sequence byte |
| $1948+x | 3 | New sequence flag |
| $194C+x | 3 | Sequence offset |

---

## Sequence Parsing

### Sequence Loop ($11B5)

```assembly
W11B5:
    lda  ($FB),y        ; Read sequence byte
    bmi  W11D1          ; If >= $80: command/instrument
    sta  W1931,x        ; Store as note
    beq  W11C2          ; $00 = rest
    cmp  #$7E           ; $7E = gate continue
    bne  W11C8          ; Else: note with transpose
```

### Byte Decoding

```assembly
; At W11D1 - byte >= $80
W11D1:
    cmp  #$C0
    bmi  W11E7          ; $80-$BF: not command
    and  #$3F           ; $C0-$FF: command
    asl                 ; × 2 for index
    sta  W1937,x        ; Store command index
    ...

W11E7:
    cmp  #$A0
    bmi  W1204          ; $80-$9F: not instrument
    and  #$1F           ; $A0-$BF: instrument
    asl
    asl
    asl                 ; × 8 for index
    sta  W1934,x        ; Store instrument index
    ...

W1204:
    cmp  #$90
    bmi  W120B          ; $80-$8F: rest value
    inc  W1913,x        ; $90-$9F: set gate flag
```

**Sequence Byte Encoding:**

| Range | Meaning |
|-------|---------|
| $00 | Rest (gate stays on) |
| $01-$5F | Note value |
| $7E | Gate continue (+++) |
| $7F | End of sequence |
| $80-$8F | Rest with specific duration |
| $90-$9F | Duration value with gate flag |
| $A0-$BF | Instrument (index = (byte & $1F) × 8) |
| $C0-$FF | Command (index = (byte & $3F) × 2) |

---

## Command Processing

### Command Decoding ($1629-$173F)

Commands are processed when the processing flag bit 1 is set:

```assembly
W1629:
    tya
    and  #$FD           ; Clear command flag
    sta  W1928,x
    ldy  W1937,x        ; Get command index
    lda  W1ADB,y        ; Read command byte 0
    sta  $FB
    and  #$F0           ; Get command type
    sta  $FC
    bpl  W1640          ; $00-$7F: standard commands
    jmp  W16AC          ; $80-$FF: special commands
```

### Standard Commands ($1640-$16A9)

```assembly
; $00-$0F: Slide up
W1640:
    bne  W1657          ; If not $00
    lda  $FB
    and  #$0F
    sta  W196F,x        ; Speed hi
    lda  W1ADB+1,y
    sta  W196C,x        ; Speed lo
    lda  #$01
    sta  W1923+2,x      ; Effect type = 1 (slide up)
    jmp  W173F

; $20: Slide down
W1657:
    cmp  #$20
    bne  W1670
    ; Similar to slide up but effect type = 2

; $60: Vibrato
W1670:
    cmp  #$60
    bne  W16A9
    lda  #$03
    sta  W1923+2,x      ; Effect type = 3 (vibrato)
    ; Decode amplitude and speed...
```

### Special Commands ($16AC-$173F)

```assembly
; $90: Set decay (local ADSR)
W16AC:
    cmp  #$90
    bne  W16CF
    ; Set AD/SR directly

; $A0: Set persistent ADSR
W16CF:
    cmp  #$A0
    bne  W16EC
    ; Set AD/SR and store in instrument

; $C0: Wave table pointer
W16EC:
    cmp  #$C0
    bne  W16F9
    lda  W1ADB+1,y
    sta  W1990,x        ; Set wave index

; $D0: Filter/pulse control
W16F9:
    cmp  #$D0
    bne  W1733
    ; $D0 = filter ptr, $D1 = filter value, $D2 = pulse ptr

; $F0: Master volume
W1733:
    cmp  #$F0
    bne  W173F
    lda  W1ADB+1,y
    and  #$0F
    sta  W1008+1        ; Set volume
```

---

## Instrument Processing

### Instrument Setup ($12F2-$13BA)

When a note triggers with a new instrument:

```assembly
W12F2:
    lda  W1928,x
    and  #$01           ; Check instrument flag
    beq  W1311          ; Skip if no new instrument

    lda  W1934,x        ; Get instrument index (× 8)
    sta  W101D,x
    tay
    lda  W1A6B,y        ; Byte 0: AD
    sta  W193A,x
    lda  W1A6B+1,y      ; Byte 1: SR
    sta  W193D,x
    lda  #$00
    sta  W1923+2,x      ; Clear effect type
```

### Reading Instrument Data ($133D-$13BA)

```assembly
W133D:
    ldy  W1934,x        ; Instrument index
    lda  W1989+1,x
    cmp  #$FF
    bne  W134A
    lda  W1A72,y        ; Wave table pointer (byte 7)
W134A:
    sta  W1990,x        ; Store wave index

    lda  W193A,x        ; AD
    sta  W1980+1,x
    lda  W193D,x        ; SR
    sta  W1984,x

    lda  W1A71,y        ; Flags (byte 6)
    ; Process flags...

    lda  W1A6D+1,y      ; Filter byte (byte 3)
    beq  W13B1          ; If 0: no filter
    ; Setup filter routing...
```

---

## Frequency Tables

### Note Frequency Lookup ($1833-$18F2)

```assembly
frequencyLo:            ; $1833
    .byte $16           ; C-0 lo
frequencyHi:            ; $1834
    .byte $01           ; C-0 hi
W1835:
    .byte $27, $01, $38, $01, $4B, $01, $5F, $01...
    ; C#0, D-0, D#0, E-0... up to B-7
```

**Total: 96 notes (8 octaves × 12 semitones)**

Frequency calculation:
```assembly
    ldy  W1921+1,x      ; Note + transpose
    lda  frequencyLo,y
    clc
    adc  W18FE,x        ; Fine tune offset
    sta  W1940,x        ; Store frequency lo
    lda  frequencyHi,y
    adc  #$00
    sta  W1942+1,x      ; Store frequency hi
```

---

## SID Register Writes

### Per-Voice Registers ($173F-$1779)

```assembly
W173F:
    ldy  W18F9+2,x      ; Voice offset (0, 7, 14)
    lda  W100C,x
    sta  $D400,y        ; Frequency lo
    lda  W100E+1,x
    sta  $D401,y        ; Frequency hi
    lda  W1984,x
    sta  $D406,y        ; Sustain/Release
    lda  W1980+1,x
    sta  $D405,y        ; Attack/Decay
    lda  W197A+1,x
    sta  $D402,y        ; Pulse width lo
    lda  W197D+1,x
    sta  $D403,y        ; Pulse width hi
    lda  W1987,x
    and  W101A,x        ; Waveform & gate mask
    sta  $D404,y        ; Control register
```

### Filter and Volume ($17D8-$1830)

```assembly
W17D8:
    lda  W194F+1
    sta  $D416          ; Filter cutoff hi
    lda  W100A
    sta  $D417          ; Filter routing/resonance
    lda  W1008+1
    ora  W194F
    sta  $D418          ; Volume & filter mode
```

---

## Wave Table Processing

### Wave Table Format

Located at $19AD-$1A1D with waveforms at $19E7:

```assembly
W15A6:
    ldy  W1990,x        ; Wave table index
    lda  W19AD+2,y      ; Note offset byte
    cmp  #$00
    bne  W15BF          ; If not 0: process offset
    ; Use current frequency
    jmp  W15EB

W15BF:
    bpl  W15CB          ; $01-$7F: relative offset
    cmp  #$80
    beq  W15C9          ; $80: special (recalc base)
    asl                 ; $81-$FF: absolute note
    jmp  W15D4

W15EB:
    lda  W19E7,y        ; Get waveform
    sta  W1987,x        ; Store for output
    dec  W198B+2,x      ; Duration countdown
    bpl  W1614
    ; Advance to next entry...
```

**Wave Table Byte Layout:**

| Byte | Description |
|------|-------------|
| $19AD+y | Note offset or control |
| $19E7+y | Waveform value |

**Control Values:**
- $00: Use current note
- $01-$7F: Relative semitone offset
- $80: Recalculate base (Hubbard slide)
- $81-$DF: Absolute note value
- $7E: Loop marker
- $7F: Jump command

---

## Effect Processing

### Effect Types ($1459-$15A6)

```assembly
W1451:
    lda  W1923+2,x      ; Effect type
    bne  W1459
    jmp  W15A6          ; No effect

W1459:
    cmp  #$01
    beq  W1460          ; Slide up
    jmp  W1476

W1460:
    ; Add delta to frequency
    lda  W1940,x
    clc
    adc  W196C,x        ; Slide speed lo
    sta  W1940,x
    lda  W1942+1,x
    adc  W196F,x        ; Slide speed hi
    sta  W1942+1,x
    jmp  W15A6

W1476:
    cmp  #$02
    beq  W147D          ; Slide down
    jmp  W1493

W147D:
    ; Subtract delta from frequency
    ...

W1493:
    cmp  #$03
    beq  W149A          ; Vibrato
    jmp  W152E

W152E:
    cmp  #$81
    beq  W1535          ; Portamento
    jmp  W15A6
```

---

## Key Patterns for Table Discovery

### Pattern: Instrument Table Access

```assembly
    lda  W1934,x        ; Instrument index × 8
    tay
    lda  W1A6B,y        ; Table base $1A6B
    sta  W193A,x        ; AD value
    lda  W1A6B+1,y      ; Table + 1
    sta  W193D,x        ; SR value
```

**Signature**: `LDA (addr),Y` followed by `STA` to state array

### Pattern: Sequence Pointer Setup

```assembly
    lda  W199F,y        ; Pointer table lo
    sta  W1901,x        ; Current position lo
    sta  W1905+2,x      ; Start position lo
    iny
    lda  W199F,y        ; Pointer table hi
    sta  W1903+1,x      ; Current position hi
    sta  W1909+1,x      ; Start position hi
```

### Pattern: Filter Table Access

```assembly
    lda  W1A1E+1,y      ; Filter table at $1A1F
    cmp  #$FF
    beq  W1820          ; Skip if $FF
    sta  W194F+1        ; Set cutoff
```

### Pattern: Wave Table Loop Check

```assembly
    lda  W19AD+2,y      ; Wave entry
    cmp  #$7E           ; Loop marker?
    bne  W1608
    dey
    jmp  W1610          ; Go back one entry

W1608:
    cmp  #$7F           ; Jump marker?
    bne  W1610
    lda  W19E7,y        ; Get jump target
    tay
```

---

## Important Addresses Summary

### Entry Points
| Address | Function |
|---------|----------|
| $1000 | Init (jump) |
| $1040 | Init (actual) |
| $10A1 | Play |

### Tables
| Address | Table | Size |
|---------|-------|------|
| $1833 | Frequency table | 192 bytes (96 × 2) |
| $199F | Sequence pointers | Variable |
| $19AD | Wave table (offsets) | Variable |
| $19E7 | Wave table (waveforms) | Variable |
| $1A1E | Filter/tempo table | Variable |
| $1A3B | Pulse table | Variable |
| $1A6B | Instrument table | 64 bytes (8 × 8) |
| $1ADB | Command table | Variable |
| $1B1B | Sequence data ptrs | Variable |

### State Variables
| Address | Per-Voice | Description |
|---------|-----------|-------------|
| $18F3 | No | Player state flags |
| $18F4 | No | Song end flag |
| $18F5 | No | Voice mask (1, 2, 4) |
| $18F9 | No | SID register offset (0, 7, 14) |
| $190C | No | Speed counter |
| $190F | No | Tempo index |

---

## Extraction Heuristics Explained

Based on this analysis, we can understand why the extraction heuristics work:

### 1. Instrument Table Scoring

Look for 8-byte entries where:
- Bytes 0-1 (AD/SR) have values $00-$FF but commonly $0x-$Fx
- Byte 6 (flags) typically $00-$0F or $80+
- Byte 7 (wave ptr) points to valid wave table range

### 2. Wave Table Detection

Look for 2-byte entries where:
- Byte 0 is valid waveform ($01, $11, $21, $41, $81) or control ($7E, $7F)
- Byte 1 is note offset ($00-$5F) or jump target

### 3. Sequence Parsing

Valid sequences have:
- Notes in range $00-$5F
- Instruments encoded as $A0-$BF
- Commands encoded as $C0-$FF
- End marker $7F

---

## References

- [Conversion Strategy](CONVERSION_STRATEGY.md)
- [SF2 Format Specification](SF2_FORMAT_SPEC.md)
- [SID Registers](sid-registers.md)
- Original file: `test89/angular.asm`
