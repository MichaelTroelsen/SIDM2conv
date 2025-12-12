# Wave Table Read Instructions - Stinsens_Last_Night_of_89.sid

## Wave Table Read Code (Lines 591-606)

```asm
; Address $1551-1553 - READ WAVEFORM from wave table
lda DataBlock_6 + $239,Y        ; Y = wave table entry index
                                 ; Reads from wave table at DataBlock_6 + $239

Label_72:
sta DataBlock_6 + $14B,X         ; Store waveform for voice X

; Address $1557-1559 - READ NOTE OFFSET from wave table
lda DataBlock_6 + $26B,Y         ; Y = same wave table entry index
                                 ; Reads from note offset table at DataBlock_6 + $26B

beq Label_74                     ; If note = $00, skip
cmp #$81                         ; Check if >= $81 (special value)
bcs Label_73                     ; Branch if special
clc
adc DataBlock_6 + $118,X         ; Add transpose value

Label_73:
and #$7F                         ; Mask to 7 bits
tay                             ; Use note as index into frequency table

; Address $1567-1569 - READ FREQUENCY LOW BYTE
lda DataBlock_6 + $60,Y          ; Read freq low from frequency table
sta DataBlock_6 + $13F,X

; Address $156D-156F - READ FREQUENCY HIGH BYTE
lda DataBlock_6,Y                ; Read freq high from frequency table
jmp Label_75

Label_74:
lda DataBlock_6 + $139,X         ; Use previous waveform if note = $00
sta DataBlock_6 + $13F,X
lda DataBlock_6 + $13C,X         ; Use previous frequency
Label_75:
sta DataBlock_6 + $142,X         ; Store frequency high byte
```

## Memory Layout

**DataBlock_6 Base Address**: `$16A1` (from SID file disassembly)

### Wave Table Addresses:

1. **Waveform Table**: DataBlock_6 + $239 = `$18DA`
   - Line 591: `lda DataBlock_6 + $239,Y`
   - Reads waveform byte (21, 41, 7F, 81, etc.)

2. **Note Offset Table**: DataBlock_6 + $26B = `$190C`
   - Line 594: `lda DataBlock_6 + $26B,Y`
   - Reads note offset byte (80, 00, 02, C0, etc.)

3. **Frequency Table Low**: DataBlock_6 + $60 = `$1701`
   - Line 603: `lda DataBlock_6 + $60,Y`
   - Frequency table low bytes indexed by note value

4. **Frequency Table High**: DataBlock_6 + $00 = `$16A1`
   - Line 605: `lda DataBlock_6,Y`
   - Frequency table high bytes indexed by note value

## Key Observations

### Dual Table Format (Laxity NewPlayer v21):

The Laxity player stores wave table data in TWO separate tables:

```
$18DA: 21 21 41 7F 81 41 41 41...  (WAVEFORM bytes)
$190C: 80 80 00 02 C0 A1 9A 00...  (NOTE OFFSET bytes)
```

**Not interleaved** - separate sequential tables!

### Reading Pattern:

```
For wave entry index Y:
  1. Read waveform from $18DA + Y
  2. Read note offset from $190C + Y
  3. Process note (add transpose, handle special values)
  4. Use processed note to index frequency table
  5. Read freq_low from $1701 + note
  6. Read freq_high from $16A1 + note
```

### Comparison to SF2 Format:

| Format | Structure | Waveform Location | Note Location |
|--------|-----------|-------------------|---------------|
| **Laxity** | Two separate tables | $18DA (sequential) | $190C (sequential) |
| **SF2** | Interleaved pairs | $0958 (pairs: wf, note) | $0958 (same, interleaved) |

## Conversion Implications

### Laxity → SF2 Conversion:

```python
# Laxity format (separate tables):
laxity_waveforms = data[0x18DA:0x18DA+50]  # Waveform bytes
laxity_notes = data[0x190C:0x190C+50]      # Note offset bytes

# Convert to SF2 format (interleaved pairs):
sf2_wave_table = []
for i in range(len(laxity_waveforms)):
    sf2_wave_table.append(laxity_waveforms[i])  # Waveform first
    sf2_wave_table.append(laxity_notes[i])      # Note second

# Write to SF2 at $0958
```

### SF2 → Laxity Conversion:

```python
# SF2 format (interleaved pairs):
sf2_wave_table = data[0x0958:0x09BB]

# Extract to Laxity format (separate tables):
laxity_waveforms = []
laxity_notes = []
for i in range(0, len(sf2_wave_table), 2):
    laxity_waveforms.append(sf2_wave_table[i])    # Even bytes = waveform
    laxity_notes.append(sf2_wave_table[i+1])      # Odd bytes = note

# Write waveforms to $18DA
# Write notes to $190C
```

## Instruction Details

### LDA DataBlock_6 + $239,Y

**Opcode**: `B9 DA 18` (LDA absolute,Y)
- **B9**: LDA absolute indexed Y
- **DA 18**: Address $18DA

**Effect**: Load accumulator with byte at address ($18DA + Y)

### LDA DataBlock_6 + $26B,Y

**Opcode**: `B9 0C 19` (LDA absolute,Y)
- **B9**: LDA absolute indexed Y
- **0C 19**: Address $190C

**Effect**: Load accumulator with byte at address ($190C + Y)

## Special Note Values

From the code (line 596-602):

- **$00**: No note change - reuse previous waveform/frequency
- **$80-$FF**: Special values (transpose markers, control bytes)
- **$7F**: End marker (from wave table data)
- **$81**: Control byte / transpose indicator

## Usage in Player

1. **Init Phase**: Set up wave table pointers at DataBlock_6 + $239 and + $26B
2. **Play Phase**:
   - Y register holds current wave table entry index
   - Read waveform byte from $18DA,Y
   - Read note offset from $190C,Y
   - Process and write to SID registers
3. **Loop**: Increment Y, check for end marker ($7F), loop or advance

---

**Analysis Date**: 2025-12-07
**SID File**: Stinsens_Last_Night_of_89.sid (Laxity NewPlayer v21)
**Disassembly Tool**: SIDwinder 0.2.6
