# Filter Table Read Instructions - Stinsens_Last_Night_of_89.sid

## Filter Table Read Code (Lines 660-735)

```asm
; =========================================
; FILTER TABLE READ - 3 Tables
; =========================================

Label_80:  ; Address $15EF
lda DataBlock_6 + $EB           ; Check filter active flag
bmi Label_86
beq Label_87

ldy DataBlock_6 + $ED           ; Y = filter entry index
dec DataBlock_6 + $EC           ; Decrement duration counter
bpl Label_84                    ; Continue if not expired

; Move to next filter entry
iny

; 1. READ FILTER HIGH BYTE (Table 1 at $1989)
lda DataBlock_6 + $2E8,Y        ; $15FF: Read filter high/control
cmp #$7F                        ; Check for end marker
bne Label_82

; Check loop marker
tya
cmp DataBlock_6 + $31C,Y        ; $1607: Compare with Table 3 (loop point)
bne Label_81
lda #$00
sta DataBlock_6 + $EB           ; Disable filter
jmp Label_87

Label_81:
lda DataBlock_6 + $31C,Y        ; $1614: Read loop point from Table 3
tay                             ; Jump to loop position

Label_82:  ; Address $1618
; 2. READ FILTER VALUE (Table 1)
lda DataBlock_6 + $2E8,Y        ; Read filter high byte
bpl Label_83                    ; Branch if positive (delta mode)

; Negative = absolute set + extract resonance/voice bits
and #$70                        ; Extract bits 6-4 (resonance)
sta DataBlock_6 + $E5           ; Store resonance

lda DataBlock_6 + $2E8,Y        ; $1622: Read Table 1 again
and #$0F                        ; Extract bits 3-0 (filter high nibble)
sta DataBlock_6 + $E9           ; Store filter high

; 3. READ FILTER LOW BYTE (Table 2 at $19A3)
lda DataBlock_6 + $302,Y        ; $162A: Read filter low byte
sta DataBlock_6 + $E8           ; Store filter low

; 4. READ DURATION (Table 3 at $19BD)
lda DataBlock_6 + $31C,Y        ; $1630: Read duration
sta DataBlock_6 + $E6           ; Store voice routing bits
jmp Label_85

Label_83:  ; Delta mode - address $1639
; 5. READ DURATION FOR DELTA (Table 3)
lda DataBlock_6 + $31C,Y        ; Read duration counter reset value
sta DataBlock_6 + $EC           ; Store as counter

Label_84:  ; Address $163F
; Add filter delta
lda DataBlock_6 + $E8           ; Get current filter low
clc

; 6. ADD FILTER DELTA LOW (Table 2)
adc DataBlock_6 + $302,Y        ; $1643: Add delta from Table 2
sta DataBlock_6 + $E8           ; Store new filter low

lda DataBlock_6 + $E9           ; Get current filter high
; 7. ADD FILTER DELTA HIGH (Table 1)
adc DataBlock_6 + $2E8,Y        ; $164C: Add delta from Table 1
sta DataBlock_6 + $E9           ; Store new filter high

Label_85:  ; Address $1652
sty DataBlock_6 + $ED           ; Save filter entry index

Label_86:  ; Address $1655
lda #$40
sta DataBlock_6 + $EB           ; Set filter active flag

Label_87:  ; Address $165A - Write to SID
; Process filter value (divide by 16 for cutoff)
lda DataBlock_6 + $E9           ; Filter high
sta ZP_0
lda DataBlock_6 + $E8           ; Filter low
lsr ZP_0                        ; Shift right 4 times
ror                             ; (divide by 16)
tax
lsr ZP_0
ror
lsr ZP_0
ror
lsr ZP_0
ror
tay

; Write filter registers
lda DataBlock_6 + $E6           ; Voice routing bits
ora DataBlock_6 + $E7           ; OR with volume
sta SID0+23                     ; $1676: Write to $D417 (routing/volume)

sty SID0+22                     ; $1679: Write to $D416 (filter low)

txa
and #$07                        ; Mask to 3 bits
sta SID0+21                     ; $167F: Write to $D415 (filter high)

lda DataBlock_6 + $E4           ; Volume/mode bits
ora DataBlock_6 + $E5           ; OR with resonance
sta SID0+24                     ; $1688: Write to $D418 (volume/mode)
```

## Memory Layout - Laxity NewPlayer v21

**DataBlock_6 Base Address**: `$16A1`

### THREE Filter Tables (Laxity Format):

1. **Filter High/Control Table**: DataBlock_6 + $2E8 = `$1989`
   - Lines 668, 681, 685, 702: `lda DataBlock_6 + $2E8,Y`
   - Filter cutoff high nibble (bits 3-0)
   - Resonance (bits 6-4 when negative)
   - Negative (bit 7=1) = absolute value
   - Positive (bit 7=0) = delta to add

2. **Filter Low Table**: DataBlock_6 + $302 = `$19A3`
   - Lines 688, 699: `lda DataBlock_6 + $302,Y`
   - Filter cutoff low byte
   - Or delta low byte

3. **Duration/Routing Table**: DataBlock_6 + $31C = `$19BD`
   - Lines 672, 678, 690, 694: `lda DataBlock_6 + $31C,Y`
   - Duration (how many frames to hold)
   - Voice routing bits (which voices are filtered)
   - Loop point markers

## Filter Value Format

### Table 1 Entry (when negative):
```
Bit 7: 1 (negative = absolute set)
Bit 6-4: Resonance (0-7)
Bit 3-0: Filter cutoff high nibble
```

### Table 1 Entry (when positive):
```
Bit 7: 0 (positive = delta)
Bit 6-0: Delta to add to filter high
```

### Table 2 Entry:
```
8-bit filter cutoff low byte or delta low
```

### Table 3 Entry:
```
Bit 7-4: Voice routing (which voices pass through filter)
Bit 3-0: Duration or loop marker
```

## Filter Cutoff Calculation

The filter cutoff is a 12-bit value (0-$FFF) but stored as:
- High nibble (4 bits) in Table 1
- Low byte (8 bits) in Table 2

Combined: `cutoff = (high_nibble << 8) | low_byte`

Then divided by 16 before writing to SID:
```
SID_cutoff = cutoff / 16
SID_D415 = (SID_cutoff >> 8) & $07  ; 3 bits
SID_D416 = SID_cutoff & $FF         ; 8 bits
```

## SID Register Mapping

```
$D415 (SID0+21): Filter cutoff high (3 bits)
$D416 (SID0+22): Filter cutoff low (8 bits)
$D417 (SID0+23): Voice routing (bits 0-3) + Volume (bits 4-7)
$D418 (SID0+24): Resonance (bits 4-7) + Filter mode (bits 0-3)
```

## Filter Processing Algorithm

```
For filter entry Y:
  1. Read filter_high from Table 1 ($2E8 + Y)
  2. Read filter_low from Table 2 ($302 + Y)
  3. Read duration/routing from Table 3 ($31C + Y)

  If filter_high < 0 (bit 7 set):
    // Absolute set mode
    resonance = (filter_high >> 4) & $07
    cutoff_high = filter_high & $0F
    cutoff_low = filter_low
    routing = duration
  Else:
    // Delta mode
    cutoff_high += filter_high
    cutoff_low += filter_low

  Hold for 'duration' frames
  Advance to next entry when duration expires
```

## Example Filter Entry

### Entry: Set filter cutoff to $4F0, resonance $30, route voices 1+2
```
Table 1[$n]: $BF  (negative, bits: 1_011_1111)
              └─ bit7=1: absolute
              └─ bit6-4=011: resonance = 3
              └─ bit3-0=1111: high nibble = $F

Table 2[$n]: $00  (low byte = $00)

Table 3[$n]: $43  (routing + duration)
              └─ bit6-4=010: voices 1+2
              └─ bit3-0=0011: duration = 3 frames

Result:
  Filter cutoff = $F00 (high=$F, low=$00)
  After /16 = $F0
  SID writes:
    $D415 = $07 (high 3 bits of $F0)
    $D416 = $00 (low byte of $F0)
    $D417 = $43 (routing + volume)
    $D418 = $30 (resonance $3 << 4)
```

## 3-Table Structure Summary

**Laxity Filter Format (3 tables)**:
```
Table 1 ($1989): BF 00 81 ...  (High nibble + resonance/control)
Table 2 ($19A3): 00 F0 00 ...  (Low byte)
Table 3 ($19BD): 43 10 20 ...  (Duration + routing)
```

**Similar to Pulse/Wave**:
- Table 1: Main value or delta
- Table 2: Secondary value or delta
- Table 3: Duration/control parameters

## Conversion Laxity → SF2

The SF2 format likely consolidates these 3 tables into 2:

```python
# Laxity has 3 separate tables
laxity_filter_high = data[0x1989:0x19A2]  # 26 bytes
laxity_filter_low = data[0x19A3:0x19BC]   # 26 bytes
laxity_duration = data[0x19BD:0x19D6]     # 26 bytes

# SF2 possibly interleaves high/low
sf2_filter_table1 = []
for i in range(len(laxity_filter_high)):
    sf2_filter_table1.append(laxity_filter_high[i])
    sf2_filter_table1.append(laxity_filter_low[i])

# SF2 Table 2: Duration/routing (same as Laxity Table 3)
sf2_filter_table2 = laxity_duration
```

---

**Analysis Date**: 2025-12-07
**SID File**: Stinsens_Last_Night_of_89.sid (Laxity NewPlayer v21)
**Disassembly Tool**: SIDwinder 0.2.6

**Pattern Confirmed**: All three table types (Wave, Pulse, Filter) use the **3-table structure** in Laxity format:
1. Main value/delta table
2. Secondary value/delta table
3. Duration/control table
