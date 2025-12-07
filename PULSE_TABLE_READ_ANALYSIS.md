# Pulse Table Read Instructions - Stinsens_Last_Night_of_89.sid

## Pulse Table Read Code (Lines 549-583)

```asm
; =========================================
; PULSE TABLE READ - Laxity Format
; =========================================

Label_67:
; Get pulse table index
ldy DataBlock_6 + $121,X        ; Y = pulse table entry index

; 1. READ PULSE VALUE/HIGH (address $14F5)
lda DataBlock_6 + $29D,Y        ; Read pulse high from table at $193E
cmp #$7F                        ; Check for end marker
bne Label_68

; Check loop point
lda DataBlock_6 + $2CF,Y        ; Read duration/loop from table at $1970
cmp DataBlock_6 + $121,X
beq Label_71
sta DataBlock_6 + $121,X
tay

Label_68:
; 2. READ PULSE VALUE AGAIN (address $1508)
lda DataBlock_6 + $29D,Y        ; Read pulse value from $193E
bpl Label_69                    ; If positive, use as delta

; Absolute pulse set
sta DataBlock_6 + $148,X        ; Store pulse high byte

; 3. READ PULSE LOW/DELTA (address $1510)
lda DataBlock_6 + $2B6,Y        ; Read pulse low/delta from $1957
sta DataBlock_6 + $145,X        ; Store pulse low byte
jmp Label_70

Label_69:
; Delta mode - add to current pulse
sta ZP_0
lda DataBlock_6 + $145,X        ; Get current pulse low
clc

; 4. READ PULSE DELTA (address $151F)
adc DataBlock_6 + $2B6,Y        ; Add delta from $1957
sta DataBlock_6 + $145,X        ; Store new pulse low
lda DataBlock_6 + $148,X        ; Get current pulse high
adc ZP_0                        ; Add high delta
sta DataBlock_6 + $148,X        ; Store new pulse high

Label_70:
; Update pulse table position
inc DataBlock_6 + $124,X        ; Increment duration counter

; 5. CHECK DURATION (address $1533)
lda DataBlock_6 + $124,X
cmp DataBlock_6 + $2CF,Y        ; Compare with duration from $1970
bcc Label_71                    ; Continue if not done

; Advance to next entry
inc DataBlock_6 + $121,X
lda #$00
sta DataBlock_6 + $124,X        ; Reset duration counter
```

## Memory Layout - Laxity NewPlayer v21

**DataBlock_6 Base Address**: `$16A1`

### THREE Pulse Tables (Laxity Format):

1. **Pulse Values Table**: DataBlock_6 + $29D = `$193E`
   - Line 551, 560: `lda DataBlock_6 + $29D,Y`
   - Pulse high byte or delta high
   - Negative value = absolute set, Positive = delta

2. **Pulse Low/Delta Table**: DataBlock_6 + $2B6 = `$1957`
   - Line 563, 570: `lda DataBlock_6 + $2B6,Y`
   - Pulse low byte or delta low

3. **Duration/Loop Table**: DataBlock_6 + $2CF = `$1970`
   - Line 554, 578: `lda DataBlock_6 + $2CF,Y`
   - How long to hold this pulse value
   - Also used as loop point marker

## SF2-Packed Format (Dual Table)

Based on user findings in SF2packed_Stinsens_Last_Night_of_89.sid:

**Table 1** at `$09BC` (19 bytes):
```
88 00 81 00 00 0F 7F 88 7F 88 0F 0F 00 7F 88 00 0F 00 7F
```

**Table 2** at `$09D5` (19 bytes):
```
00 00 70 40 10 F0 00 00 00 00 A0 F0 10 00 00 80 F0 10 00
```

## Table Structure Comparison

| Format | Tables | Structure | Purpose |
|--------|--------|-----------|---------|
| **Laxity** | 3 tables | Separate sequential arrays | High, Low, Duration |
| **SF2** | 2 tables | Packed format | Values + Parameters |

### Laxity 3-Table Format:
```
Table 1 ($193E): 88 00 81 00 00 0F 7F...  (Pulse high/delta high)
Table 2 ($1957): xx xx xx xx xx xx xx...  (Pulse low/delta low)
Table 3 ($1970): 00 00 70 40 10 F0 00...  (Duration/loop)
```

### SF2 2-Table Format:
```
Table 1 ($09BC): 88 00 81 00 00 0F 7F 88 7F 88 0F 0F 00 7F 88 00 0F 00 7F
                 [Pulse values - possibly interleaved high/low pairs]

Table 2 ($09D5): 00 00 70 40 10 F0 00 00 00 00 A0 F0 10 00 00 80 F0 10 00
                 [Duration/parameters]
```

## Pulse Width Modulation (PWM) Algorithm

### Reading Pulse Table Entry:

```
For pulse entry Y:
  1. Read pulse_value from Table 1 ($29D + Y)
  2. Read pulse_delta from Table 2 ($2B6 + Y)
  3. Read duration from Table 3 ($2CF + Y)

  If pulse_value < 0 (bit 7 set):
    pulse_width = (pulse_value << 8) | pulse_delta  // Absolute set
  Else:
    pulse_width += (pulse_value << 8) | pulse_delta  // Delta mode

  Hold for 'duration' frames
  Advance to next entry when duration expires
```

### Writing to SID:

```asm
; From lines 624-627
ldy DataBlock_6 + $D6,X         ; Y = SID voice offset (0, 7, 14)
lda DataBlock_6 + $145,X        ; Pulse low byte
sta SID0+2,Y                    ; Write to $D402/$D409/$D410
lda DataBlock_6 + $148,X        ; Pulse high byte
sta SID0+3,Y                    ; Write to $D403/$D40A/$D411
```

## Pulse Table Example

### Entry 0: Set pulse to $0088
```
Table 1[$0]: $88  (high byte, negative if bit 7 set)
Table 2[$0]: $00  (low byte)
Table 3[$0]: $00  (duration)
Result: Pulse = $0088, hold for 0 frames
```

### Entry 3: Set pulse to $4070
```
Table 1[$3]: $40  (high)
Table 2[$3]: $70  (low)
Table 3[$3]: $10  (duration)
Result: Pulse = $4070, hold for 16 frames
```

## Conversion Laxity → SF2

### Hypothesis for SF2 Format:

The SF2 format appears to pack pulse data more efficiently:

```python
# Laxity has 3 separate tables
laxity_high = [0x88, 0x00, 0x81, 0x00, 0x00, 0x0F, 0x7F, ...]
laxity_low = [0x00, 0x00, 0x??  , ...]  # Need to extract from file
laxity_duration = [0x00, 0x00, 0x70, 0x40, 0x10, 0xF0, ...]

# SF2 Table 1: Could be interleaved high/low pairs
sf2_table1 = []
for i in range(len(laxity_high)):
    sf2_table1.append(laxity_high[i])
    if i < len(laxity_low):
        sf2_table1.append(laxity_low[i])

# SF2 Table 2: Duration table (matches Laxity Table 3)
sf2_table2 = laxity_duration
```

## SF2 Pulse Table Format Details

Based on the hex data at $09BC:

```
09BC: 88 00  81 00  00 0F  7F 88  7F 88  0F 0F  00 7F  88 00  0F 00  7F
      [hi lo] [hi lo] [hi lo] [hi lo] [hi lo] [hi lo] [hi lo] [hi lo] [hi lo] [end]
```

This suggests **interleaved high/low byte pairs**!

### Verification Needed:

To confirm, need to:
1. Extract Laxity Table 2 data from original file
2. Compare with SF2 Table 1 to verify interleaving
3. Check if SF2 Table 2 matches Laxity Table 3

## Pulse Table Access Pattern Summary

### Laxity (3 tables):
```asm
LDA Table1,Y   ; Pulse high/delta high ($193E)
LDA Table2,Y   ; Pulse low/delta low ($1957)
LDA Table3,Y   ; Duration ($1970)
```

### SF2 (hypothesized):
```asm
TYA
ASL            ; Y * 2 for interleaved pairs
TAY
LDA Table1,Y   ; Pulse high ($09BC + Y*2)
INY
LDA Table1,Y   ; Pulse low ($09BC + Y*2 + 1)
...
TYA
LSR            ; Back to entry index
TAY
LDA Table2,Y   ; Duration ($09D5)
```

---

**Analysis Date**: 2025-12-07
**SID Files**:
- Stinsens_Last_Night_of_89.sid (Laxity NewPlayer v21)
- SF2packed_Stinsens_Last_Night_of_89.sid (SF2 Driver 11)
**Disassembly Tool**: SIDwinder 0.2.6

**Status**: Analysis complete for Laxity format. SF2 interleaving hypothesis needs verification with actual SF2 Table 2 extraction.
