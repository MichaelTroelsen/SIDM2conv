# Stinsen's Last Night of '89 - Laxity Player Disassembly

**Author**: Thomas E. Petersen (Laxity)
**Copyright**: 2021 Bonzai
**Player**: Laxity NewPlayer v21

## Memory Map

| Address Range | Description |
|---------------|-------------|
| $1000-$1005   | Init routine entry point |
| $1006-$10A0   | Play routine entry point |
| $10A1-$1900   | Player code (sequence processing, SID updates) |
| $1900-$199F   | Player state variables (159 bytes) |
| $199F-$19A5   | Sequence pointers (3 voices × 2 bytes) |
| $1914-$1934   | Wave table - Note offsets (32 bytes) |
| $1934-$1954   | Wave table - Waveforms (32 bytes) |
| $1A1E-$1A4E   | Filter table (16 entries × 3 bytes = 48 bytes) |
| $1A3B-$1A7B   | Pulse table (16 entries × 4 bytes = 64 bytes) |
| $1A6B-$1AAB   | Instrument table (8 instruments × 8 bytes = 64 bytes) |
| $1A8B-$1ACB   | Arpeggio table (16 entries × 4 bytes = 64 bytes) |
| $1ADB-$1B9B   | Command table (64 commands × 3 bytes = 192 bytes) |

## Key Player Variables (Zero Page & RAM)

| Address | Size | Description |
|---------|------|-------------|
| $FC-$FD | 2    | Temporary pointer for sequence/table access |
| $1780   | 1    | Initial sequence pointer index |
| $1781   | 1    | Init flag ($80 = initialized) |
| $1782   | 1    | Current subtune number |
| $1783   | 1    | Tempo counter (counts down to 0) |
| $1784   | 1    | Tempo table pointer |
| $1785-$1786 | 2 | Filter and resonance settings |
| $178F+X | 3    | Per-voice: Note duration counter |
| $1792+X | 3    | Per-voice: Sequence data pointer (current position) |
| $1795+X | 3    | Per-voice: Sequence active flag |
| $1798+X | 3    | Per-voice: Event position in wave table |
| $179B+X | 3    | Per-voice: Current instrument number |
| $17B0+X | 3    | Per-voice: Transpose value |
| $17F8+X | 3    | Per-voice: Speed/timing flags |

## Annotated Disassembly

### Init Routine ($1000-$1048)

```asm
;===============================================================================
; Init Routine - Called once to initialize the player
; Entry: A = subtune number (0-based)
;===============================================================================
$1000  00            BRK                   ; Safety break (shouldn't be called)
$1001  10 4C         BPL    $104F          ; Jump table entry
$1003  92            .byte  $92            ; Data bytes (part of jump table)
$1004  16 4C         ASL    $4C,X
$1006  9B            .byte  $9B            ; Play routine entry marker

;---------------------------------------------------------------
; Actual Init Code Starts Here
;---------------------------------------------------------------
$1007  A9 00         LDA    #$00           ; A = 0 (default subtune)
$1009  2C 81 17      BIT    $1781          ; Check if already initialized
$100C  30 44         BMI    $1052          ; If bit 7 set ($80), skip to quick init
$100E  70 38         BVS    $1048          ; If bit 6 set, jump to SID silence routine

;---------------------------------------------------------------
; Full Initialization (First Time)
;---------------------------------------------------------------
$1010  A2 75         LDX    #$75           ; X = 117 (size of state area)
$1012  9D 82 17      STA    $1782,X        ; Clear $1782-$17F7 (player state)
.loop:
$1015  CA            DEX                   ; Decrement X
$1016  D0 FA         BNE    $1012          ; Loop until all bytes cleared

;---------------------------------------------------------------
; Load Subtune Configuration
;---------------------------------------------------------------
$1018  AE 82 17      LDX    $1782          ; X = subtune number (always 0 here)
$101B  BD FB 17      LDA    $17FB,X        ; Load initial tempo table pointer
$101E  8D 80 17      STA    $1780          ; Store as starting point
$1021  8D 84 17      STA    $1784          ; Store as current tempo pointer

$1024  BD FC 17      LDA    $17FC,X        ; Load filter/resonance settings
$1027  29 0F         AND    #$0F           ; Mask low nibble (filter type)
$1029  8D 85 17      STA    $1785          ; Store filter type
$102C  BD FC 17      LDA    $17FC,X        ; Load again
$102F  29 70         AND    #$70           ; Mask bits 4-6 (resonance)
$1031  8D 86 17      STA    $1786          ; Store resonance

;---------------------------------------------------------------
; Initialize Tempo and Speed
;---------------------------------------------------------------
$1034  A9 02         LDA    #$02           ; Default speed = 2
$1036  8D 83 17      STA    $1783          ; Set tempo counter
$1039  8D F8 17      STA    $17F8          ; Voice 1 speed
$103C  8D F9 17      STA    $17F9          ; Voice 2 speed
$103F  8D FA 17      STA    $17FA          ; Voice 3 speed

$1042  A9 80         LDA    #$80           ; Set init flag
$1044  8D 81 17      STA    $1781          ; Mark as initialized
$1047  60            RTS                   ; Return

;---------------------------------------------------------------
; SID Silence Routine - Mute all voices
;---------------------------------------------------------------
$1048  8D 04 D4      STA    $D404          ; Voice 1 Control = 0 (gate off)
$104B  8D 0B D4      STA    $D40B          ; Voice 2 Control = 0
$104E  8D 12 D4      STA    $D412          ; Voice 3 Control = 0
$1051  60            RTS                   ; Return

;---------------------------------------------------------------
; Quick Init (Re-init without clearing state)
;---------------------------------------------------------------
$1052  CE 83 17      DEC    $1783          ; Decrement tempo counter
$1055  10 17         BPL    $106E          ; If not zero, skip tempo processing
```

### Play Routine ($1006 and beyond)

The play routine is called 50 times per second (PAL) to update the music.

```asm
;===============================================================================
; Main Play Loop - Processes each voice
;===============================================================================

;---------------------------------------------------------------
; Tempo Processing
;---------------------------------------------------------------
$1057  AE 84 17      LDX    $1784          ; Load tempo table pointer
$105A  BD 19 1A      LDA    $1A19,X        ; Read tempo value from table
$105D  8D 83 17      STA    $1783          ; Set new tempo counter
$1060  E8            INX                   ; Advance to next tempo entry
$1061  BD 19 1A      LDA    $1A19,X        ; Check next byte
$1064  C9 7F         CMP    #$7F           ; Is it end marker ($7F)?
$1066  D0 03         BNE    $106B          ; If not, continue
$1068  AE 80 17      LDX    $1780          ; Yes - wrap to start of tempo table
$106B  8E 84 17      STX    $1784          ; Update tempo pointer

;---------------------------------------------------------------
; Voice Loop - Process Each Voice (X = 0, 1, 2)
;---------------------------------------------------------------
$106E  A2 02         LDX    #$02           ; Start with voice 3 (index 2)

.voice_loop:
$1070  BD F8 17      LDA    $17F8,X        ; Load voice speed flag
$1073  C9 01         CMP    #$01           ; Is speed = 1?
$1075  D0 39         BNE    $10B0          ; If not, skip sequence processing

;---------------------------------------------------------------
; Check if voice needs new note
;---------------------------------------------------------------
$1077  BD 95 17      LDA    $1795,X        ; Check if sequence is active
$107A  D0 34         BNE    $10B0          ; If already active, skip
$107C  FE 95 17      INC    $1795,X        ; Mark sequence as active

;---------------------------------------------------------------
; Load Sequence Pointer for this Voice
;---------------------------------------------------------------
$107F  BD 1C 1A      LDA    $1A1C,X        ; Load sequence pointer low byte
$1082  85 FC         STA    $FC            ; Store in zero page pointer
$1084  BD 1F 1A      LDA    $1A1F,X        ; Load sequence pointer high byte
$1087  85 FD         STA    $FD            ; Complete zero page pointer ($FC/$FD)

;---------------------------------------------------------------
; Read Sequence Event (3 bytes: Note, Instrument, Command)
;---------------------------------------------------------------
$1089  BC 92 17      LDY    $1792,X        ; Y = current position in sequence
$108C  B1 FC         LDA    ($FC),Y        ; Read first byte (note/transpose)
$108E  10 09         BPL    $1099          ; If bit 7 clear, it's a note
$1090  38            SEC                   ; Bit 7 set = transpose value
$1091  E9 A0         SBC    #$A0           ; Subtract $A0 to get signed transpose
$1093  9D B0 17      STA    $17B0,X        ; Store transpose for this voice
$1096  C8            INY                   ; Advance to next byte
$1097  B1 FC         LDA    ($FC),Y        ; Read actual note value

$1099  9D 9B 17      STA    $179B,X        ; Store note/instrument value
$109C  C8            INY                   ; Advance to next byte
$109D  B1 FC         LDA    ($FC),Y        ; Read third byte (command)
$109F  C9 FF         CMP    #$FF           ; Is it $FF (loop marker)?
$10A1  D0 04         BNE    $10A7          ; If not, continue
$10A3  C8            INY                   ; Yes - read loop position
$10A4  B1 FC         LDA    ($FC),Y        ; Get loop target
$10A6  A8            TAY                   ; Y = new sequence position

$10A7  98            TYA                   ; A = sequence position
$10A8  9D 92 17      STA    $1792,X        ; Update sequence pointer
$10AB  A9 00         LDA    #$00           ; Reset event position
$10AD  9D 98 17      STA    $1798,X        ; Store in voice event position

;---------------------------------------------------------------
; Process Note Duration
;---------------------------------------------------------------
$10B0  AD 83 17      LDA    $1783          ; Load tempo counter
$10B3  D0 6D         BNE    $1122          ; If not zero, skip to next voice
$10B5  DE 8F 17      DEC    $178F,X        ; Decrement note duration
$10B8  10 68         BPL    $1122          ; If still positive, skip to next voice

;---------------------------------------------------------------
; Read Instrument/Wave Table
;---------------------------------------------------------------
$10BA  BC 9B 17      LDY    $179B,X        ; Y = instrument number
$10BD  B9 22 1A      LDA    $1A22,Y        ; Read wave table offset (note)
$10C0  85 FC         STA    $FC            ; Store in pointer low
$10C2  B9 49 1A      LDA    $1A49,Y        ; Read wave table offset (waveform)
$10C5  85 FD         STA    $FD            ; Store in pointer high

$10C7  BC 98 17      LDY    $1798,X        ; Y = position in wave table
$10CA  B1 FC         LDA    ($FC),Y        ; Read wave entry byte
$10CC  10 27         BPL    $10F5          ; If bit 7 clear, process as note

;---------------------------------------------------------------
; Special Wave Table Commands
;---------------------------------------------------------------
$10CE  C9 C0         CMP    #$C0           ; Check if $C0 or above
$10D0  90 08         BCC    $10DA          ; If below $C0, handle as command

; Note: Commands $80-$BF are wave table jump/loop commands
; Commands $C0+ are treated as special gate/control commands
```

### Instrument Table Format

Location: **$1A6B-$1AAB** (64 bytes, 8 instruments × 8 bytes)

Each instrument is 8 bytes:

```asm
;===============================================================================
; Instrument Format (8 bytes per instrument)
;===============================================================================
; Offset 0: Attack/Decay (ADSR)
; Offset 1: Sustain/Release (ADSR)
; Offset 2: Wave table pointer
; Offset 3: Pulse table pointer
; Offset 4: Filter table pointer
; Offset 5: Arpeggio table pointer
; Offset 6: Flags/Options
; Offset 7: Vibrato/Other settings
```

#### Hex Dump (from Stinsen's Last Night of '89)

```
Address: $1A6B-$1AAB  Size: 64 bytes  Count: 8 instruments
================================================================================
00: 25 25 25 25 26 26 27 a0 0e 0f 0f 0f 0f 11 01 05
10: 01 04 ac 02 03 a0 13 14 13 15 0e 11 01 05 01 04
20: ac 02 1b a0 13 14 13 15 1c 1c 1c 1c ac 02 1f 20
30: ff 00 a0 00 12 06 06 06 07 25 25 16 17 06 06 18
```

#### Decoded Instruments

| Inst | AD   | SR   | Wave | Pulse | Filter | Arp  | Flags | Vib  |
|------|------|------|------|-------|--------|------|-------|------|
| 0    | $25  | $25  | $25  | $25   | $26    | $26  | $27   | $A0  |
| 1    | $0E  | $0F  | $0F  | $0F   | $0F    | $11  | $01   | $05  |
| 2    | $01  | $04  | $AC  | $02   | $03    | $A0  | $13   | $14  |
| 3    | $13  | $15  | $0E  | $11   | $01    | $05  | $01   | $04  |
| 4    | $AC  | $02  | $1B  | $A0   | $13    | $14  | $13   | $15  |
| 5    | $1C  | $1C  | $1C  | $1C   | $AC    | $02  | $1F   | $20  |
| 6    | $FF  | $00  | $A0  | $00   | $12    | $06  | $06   | $06  |
| 7    | $07  | $25  | $25  | $16   | $17    | $06  | $06   | $18  |

### Wave Table Format

**Location**: Two separate sequential tables (not interleaved)

**Table 1 - Waveforms** at **$18DA** (DataBlock_6 + $239):
- Waveform bytes (triangle, pulse, sawtooth, noise)
- End marker: $7F

**Table 2 - Note Offsets** at **$190C** (DataBlock_6 + $26B):
- Note offset bytes (0-95 or transpose markers)
- Special values: $00 = base note, $80-$FF = transpose

```asm
;===============================================================================
; Wave Table Structure (2 Tables - Laxity NewPlayer v21)
;===============================================================================
; Table 1: Waveforms at $18DA (DataBlock_6 + $239)
;   Each byte is a waveform value:
;     Bits 0-3: Waveform type
;       $01 = Triangle
;       $02 = Sawtooth
;       $04 = Pulse
;       $08 = Noise
;     Bit 4: Gate bit
;     $7F = End marker
;
; Table 2: Note Offsets at $190C (DataBlock_6 + $26B)
;   Each byte is a note offset or transpose marker:
;     $00 = Base note (no offset)
;     $01-$5F = Note offset (0-95)
;     $80-$FF = Transpose markers
;     $C0 = Common transpose value
```

#### Read Instructions (from disassembly analysis):

```asm
; Address $1543-$156F - Wave table read routine
ldy wave_index                  ; Y = current wave entry index

; Read waveform from Table 1
lda DataBlock_6 + $239,Y        ; $1543: Read waveform from $18DA
sta DataBlock_6 + $14B,X        ; Store for voice X

; Read note offset from Table 2
lda DataBlock_6 + $26B,Y        ; $154A: Read note offset from $190C
beq use_previous                ; If $00, skip frequency update
cmp #$81                        ; Check for transpose marker
bcs handle_transpose
clc
adc DataBlock_6 + $118,X        ; Add transpose value

handle_transpose:
and #$7F                        ; Mask to 7 bits
tay                             ; Use as frequency table index
lda DataBlock_6 + $60,Y         ; Read freq low from $1701
sta DataBlock_6 + $13F,X
lda DataBlock_6,Y               ; Read freq high from $16A1
sta DataBlock_6 + $142,X
```

#### Hex Dump (from Stinsen's Last Night of '89)

**Table 1 - Waveforms at $18DA**:
```
21 21 41 7F 81 41 41 41 7F 81 41 80 80 7F 81 01
7F 81 15 11 11 7F 81 7F 21 7F 21 11 7F 51 7F 15
40 7F 53 7F 81 01 7F 41 7F 20 7F 81 41 40 80 7F
13 7F
```

**Table 2 - Note Offsets at $190C**:
```
80 80 00 02 C0 A1 9A 00 07 C4 AC C0 BC 0C C0 00
0F C0 00 76 74 14 B4 12 00 18 00 00 1B 00 1D C5
00 20 00 22 C0 00 25 00 27 00 29 C7 AE A5 C0 2E
00 30
```

**SF2 Format** (for comparison): Interleaves these into (waveform, note) pairs at $0958

### Pulse Table Format

**Location**: Three separate sequential tables (not interleaved)

**Table 1 - Pulse High/Delta High** at **$193E** (DataBlock_6 + $29D):
- Pulse width high byte or delta high
- Negative (bit 7=1) = absolute set
- Positive (bit 7=0) = delta to add

**Table 2 - Pulse Low/Delta Low** at **$1957** (DataBlock_6 + $2B6):
- Pulse width low byte or delta low
- Always paired with Table 1 value

**Table 3 - Duration** at **$1970** (DataBlock_6 + $2CF):
- Number of frames to hold this pulse value
- Also contains loop markers

```asm
;===============================================================================
; Pulse Table Structure (3 Tables - Laxity NewPlayer v21)
;===============================================================================
; Table 1: Pulse High at $193E (DataBlock_6 + $29D)
;   Pulse width high byte or delta:
;     Bit 7 = 1 (negative): Absolute pulse set mode
;     Bit 7 = 0 (positive): Delta mode (add to current)
;     $7F = End marker
;
; Table 2: Pulse Low at $1957 (DataBlock_6 + $2B6)
;   Pulse width low byte or delta low:
;     Always used in conjunction with Table 1
;     8-bit value combined with Table 1 for 16-bit pulse
;
; Table 3: Duration at $1970 (DataBlock_6 + $2CF)
;   Duration in frames:
;     How many frames to hold this pulse value
;     Also used for loop point markers
```

#### Read Instructions (from disassembly analysis):

```asm
; Address $14F2-$152F - Pulse table read routine
ldy DataBlock_6 + $121,X        ; Y = pulse entry index

; Read pulse high byte from Table 1
lda DataBlock_6 + $29D,Y        ; $14F5: Read pulse high from $193E
cmp #$7F                        ; Check end marker
bne process_pulse

; Check loop point from Table 3
lda DataBlock_6 + $2CF,Y        ; $14FC: Read duration/loop from $1970
cmp DataBlock_6 + $121,X
beq done
sta DataBlock_6 + $121,X
tay

process_pulse:
lda DataBlock_6 + $29D,Y        ; $1508: Read pulse value again
bpl delta_mode                  ; Branch if positive (delta)

; Absolute set mode
sta DataBlock_6 + $148,X        ; Store pulse high

; Read pulse low byte from Table 2
lda DataBlock_6 + $2B6,Y        ; $1510: Read pulse low from $1957
sta DataBlock_6 + $145,X        ; Store pulse low
jmp update_duration

delta_mode:
; Add delta to current pulse
sta ZP_0                        ; Save high delta
lda DataBlock_6 + $145,X        ; Get current pulse low
clc
adc DataBlock_6 + $2B6,Y        ; $151F: Add delta from Table 2
sta DataBlock_6 + $145,X
lda DataBlock_6 + $148,X
adc ZP_0                        ; Add high delta
sta DataBlock_6 + $148,X

update_duration:
inc DataBlock_6 + $124,X        ; Increment frame counter
lda DataBlock_6 + $124,X
cmp DataBlock_6 + $2CF,Y        ; $1533: Compare with duration
bcc done
inc DataBlock_6 + $121,X        ; Next pulse entry
lda #$00
sta DataBlock_6 + $124,X        ; Reset counter
```

#### Hex Dump (from Stinsen's Last Night of '89)

**Table 1 - Pulse High at $193E**:
```
88 00 81 00 00 0F 7F 88 7F 88 0F 0F 00 7F 88 00 0F 00 7F
```

**Table 2 - Pulse Low at $1957**:
```
(Need to extract from original file - paired with Table 1)
```

**Table 3 - Duration at $1970**:
```
00 00 70 40 10 F0 00 00 00 00 A0 F0 10 00 00 80 F0 10 00
```

**SF2 Format** (for comparison): Interleaves Table 1+2 into pairs at $09BC, keeps Table 3 at $09D5

### Filter Table Format

**Location**: Three separate sequential tables (not interleaved)

**Table 1 - Filter High/Resonance** at **$1989** (DataBlock_6 + $2E8):
- Filter cutoff high nibble (bits 3-0)
- Resonance (bits 6-4) when negative
- Negative (bit 7=1) = absolute set
- Positive (bit 7=0) = delta to add

**Table 2 - Filter Low** at **$19A3** (DataBlock_6 + $302):
- Filter cutoff low byte or delta low
- 8-bit value combined with Table 1

**Table 3 - Duration/Routing** at **$19BD** (DataBlock_6 + $31C):
- Voice routing bits (which voices use filter)
- Duration (how many frames)
- Loop markers

```asm
;===============================================================================
; Filter Table Structure (3 Tables - Laxity NewPlayer v21)
;===============================================================================
; Table 1: Filter High/Resonance at $1989 (DataBlock_6 + $2E8)
;   When negative (bit 7=1) - Absolute set mode:
;     Bits 6-4: Resonance (0-7)
;     Bits 3-0: Filter cutoff high nibble
;   When positive (bit 7=0) - Delta mode:
;     Bits 6-0: Delta to add to filter high
;
; Table 2: Filter Low at $19A3 (DataBlock_6 + $302)
;   Filter cutoff low byte or delta low:
;     8-bit value for full 12-bit filter cutoff
;     Combined as: cutoff = (high_nibble << 8) | low_byte
;
; Table 3: Duration/Routing at $19BD (DataBlock_6 + $31C)
;   Voice routing and duration:
;     Bits 7-4: Voice routing (which voices filtered)
;     Bits 3-0: Duration in frames or loop marker
```

#### Read Instructions (from disassembly analysis):

```asm
; Address $15EF-$1690 - Filter table read routine
ldy DataBlock_6 + $ED           ; Y = filter entry index
dec DataBlock_6 + $EC           ; Decrement duration
bpl continue                    ; Continue if not expired

iny                             ; Move to next entry

; Read filter high from Table 1
lda DataBlock_6 + $2E8,Y        ; $15FF: Read filter high from $1989
cmp #$7F                        ; Check end marker
bne process_filter

; Check loop point from Table 3
tya
cmp DataBlock_6 + $31C,Y        ; $1607: Compare with loop point
bne jump_to_loop
lda #$00
sta DataBlock_6 + $EB           ; Disable filter
jmp done

jump_to_loop:
lda DataBlock_6 + $31C,Y        ; $1614: Read loop point
tay

process_filter:
lda DataBlock_6 + $2E8,Y        ; $1618: Read filter value
bpl delta_mode                  ; Branch if positive

; Absolute set mode - extract resonance and filter
and #$70                        ; Extract resonance (bits 6-4)
sta DataBlock_6 + $E5           ; Store resonance
lda DataBlock_6 + $2E8,Y        ; Read again
and #$0F                        ; Extract filter high nibble
sta DataBlock_6 + $E9

; Read filter low from Table 2
lda DataBlock_6 + $302,Y        ; $162A: Read filter low from $19A3
sta DataBlock_6 + $E8

; Read duration/routing from Table 3
lda DataBlock_6 + $31C,Y        ; $1630: Read duration/routing from $19BD
sta DataBlock_6 + $E6           ; Store routing bits
jmp write_sid

delta_mode:
; Read duration and add delta
lda DataBlock_6 + $31C,Y        ; $1639: Read duration
sta DataBlock_6 + $EC           ; Store counter

lda DataBlock_6 + $E8           ; Get current filter low
clc
adc DataBlock_6 + $302,Y        ; $1643: Add delta from Table 2
sta DataBlock_6 + $E8
lda DataBlock_6 + $E9           ; Get current filter high
adc DataBlock_6 + $2E8,Y        ; $164C: Add delta from Table 1
sta DataBlock_6 + $E9

write_sid:
; Filter cutoff is divided by 16 before writing to SID
; SID registers: $D415 (high 3 bits), $D416 (low 8 bits)
; $D417 (routing + volume), $D418 (resonance + mode)
```

#### Hex Dump (from Stinsen's Last Night of '89)

**Table 1 - Filter High/Resonance at $1989**:
```
(Need to extract from original file)
```

**Table 2 - Filter Low at $19A3**:
```
(Need to extract from original file)
```

**Table 3 - Duration/Routing at $19BD**:
```
(Need to extract from original file)
```

**Note**: Filter cutoff is stored as 12-bit value but divided by 16 before
writing to SID ($D415 gets 3 bits, $D416 gets 8 bits for 11-bit SID cutoff)

### Arpeggio Table Format

Location: **$1A8B-$1ACB** (64 bytes, 16 entries × 4 bytes)

The arpeggio table contains note offset patterns for creating chords:

```asm
;===============================================================================
; Arpeggio Table Entry Format (4 bytes per entry)
;===============================================================================
; Bytes 0-3: Semitone offsets applied in sequence
;   Each byte is a signed offset (-128 to +127 semitones)
;   Applied cyclically to base note
;
; Common patterns:
;   00 04 07 = Major chord (root, major 3rd, perfect 5th)
;   00 03 07 = Minor chord (root, minor 3rd, perfect 5th)
;   00 00 0C = Octave arpeggio
;   $7F = End marker / Hold last offset
```

#### Hex Dump (from Stinsen's Last Night of '89)

```
Address: $1A8B-$1ACB  Size: 64 bytes  Count: 16 entries
================================================================================
00: ac 02 1b a0 13 14 13 15 1c 1c 1c 1c ac 02 1f 20
10: ff 00 a0 00 12 06 06 06 07 25 25 16 17 06 06 18
20: 25 25 06 06 06 06 1d 21 ff 00 a0 0a 0a 0b 0c a2
30: 0a a0 10 08 09 19 ac 0d a0 0b 10 08 09 1a ac 0d
```

### SID Register Updates

```asm
;===============================================================================
; SID Register Write Routines
;===============================================================================

; Voice 1 Base: $D400-$D406
; Voice 2 Base: $D407-$D40D
; Voice 3 Base: $D40E-$D414
; Global:       $D415-$D418

; Frequency calculation uses lookup table at $1833
; Base frequency + note offset + transpose + vibrato/portamento
```

### Command Table

The command table at $1ADB contains 64 commands × 3 bytes each:

```asm
;===============================================================================
; Command Format (3 bytes per command)
;===============================================================================
; Byte 0: Command type
;   $00 = No command
;   $01-$0F = Various effects (slide, vibrato, etc.)
; Byte 1: Command parameter 1
; Byte 2: Command parameter 2

; Common commands:
; $00 yy = Slide up by yy
; $01 yy = Slide down by yy
; $02 xy = Vibrato (x=speed, y=depth)
; $03 yy = Portamento to note yy
; $04 yy = Arpeggio pattern yy
; $08 ad = Set ADSR (persistent)
; $09 ad = Set ADSR (one note only)
; $0A xx = Set filter cutoff
; $0B xx = Set waveform
; $0C xx = Set pulse width
; $0D xx = Set tempo/speed
; $0E xx = Set volume
```

#### Hex Dump (from Stinsen's Last Night of '89)

```
Address: $1ADB-$1B9B  Size: 192 bytes  Count: 64 commands × 3 bytes
================================================================================
00: 39 39 c4 a9 39 c4 a0 83 39 80 39 00 83 39 c5 81
10: 3a c5 a9 3a c4 a0 85 39 c4 a9 81 39 39 7f ca a0
20: 81 30 30 80 30 00 ca a9 81 30 ca a0 83 30 cb 80
30: 2b 00 c4 85 2d c4 a9 81 2d d0 2d 2d c4 a0 80 2d
40: 00 81 2d c4 a9 2d ca a0 2e 2e 80 2e 00 ca a9 81
50: 2e ca a0 83 2e cb 80 29 00 c4 85 2b c4 a9 81 2b
60: d0 2b 2b c4 a0 80 2b 00 81 2b c4 a9 2b ca a0 2d
70: 2d 80 2d 00 ca a9 81 2d ca a0 83 2d cb 80 28 00
80: c6 85 29 80 29 00 c6 a9 81 29 c6 a0 80 29 00 81
90: 29 c6 a9 29 29 ca a0 2b 2b 80 2b 00 ca a9 81 2b
a0: ca a0 83 2b cb 80 26 00 cc 85 29 cc a9 81 29 d0
b0: 29 29 cc a0 80 29 00 29 00 cc a9 81 29 7f cb a9
```

**Note:** Command bytes are organized in groups of 3 (type, param1, param2). Special markers like $7F indicate end-of-table, and $80-$FF ranges are used for extended command parameters.

## Player Execution Flow

1. **Init ($1000)**:
   - Clear player state ($1782-$17F7)
   - Load subtune configuration
   - Set initial tempo
   - Initialize all 3 voice speeds
   - Set init flag to $80

2. **Play ($1006)** - Called every frame (50Hz):
   - Decrement tempo counter
   - If zero, read next tempo value from table
   - For each voice (3, 2, 1, 0):
     - Check if voice speed = 1 (active)
     - Read sequence data (note + instrument + command)
     - Process transpose values
     - Handle sequence loops ($FF marker)
     - Decrement note duration
     - If duration = 0, fetch new note from wave table
     - Apply commands (effects)
     - Calculate frequency using note table
     - Update SID registers

3. **Frequency Calculation**:
   - Base note from sequence
   - + Transpose value (if set)
   - + Note offset from wave table
   - + Vibrato/portamento offset
   - = Final frequency (looked up in table at $1833)

4. **Gate Handling**:
   - Gate on: Set bit 0 of SID control register
   - Gate off: Clear bit 0
   - Hard restart: Gate off for 2 frames, then on with new ADSR

## Key Data Structures

### Sequence Pointers ($199F-$19A5)
```
$199F-$19A0: Voice 1 sequence pointer
$19A1-$19A2: Voice 2 sequence pointer
$19A3-$19A4: Voice 3 sequence pointer
```

### Tempo Table ($1A1E+)
```
Speed values (frames per row) followed by $7F wrap marker
Example: 02 02 02 02 7F = constant speed of 2
```

### Per-Voice State (3 bytes each for voices 0-2)
```
$178F+X: Note duration counter
$1792+X: Current position in sequence
$1795+X: Sequence active flag
$1798+X: Position in wave table
$179B+X: Current instrument number
$17B0+X: Transpose value
$17F8+X: Voice speed flag
```

## Notes on This Implementation

This Laxity player uses several optimization techniques:

1. **Column-major table storage**: Wave table split into separate note/waveform arrays
2. **Packed sequences**: 3-byte events (note, instrument, command)
3. **Tempo table**: Variable speed support with loop marker
4. **Transpose in sequence**: $A0+ values are transpose adjustments
5. **Wave table programs**: Each instrument points to wave table sequence
6. **Gate optimization**: Minimal gate toggling for smooth playback

## Differences from SID Factory II

| Feature | Laxity Player | SF2 Driver 11 |
|---------|---------------|---------------|
| Wave table | Split (notes/waveforms) | Interleaved pairs |
| Instruments | 8 bytes | 6 bytes (column-major) |
| Sequences | 3 bytes/event | 3 bytes/event (similar) |
| Pulse table | 4 bytes/entry | 3 bytes/entry |
| Commands | 3 bytes × 64 | 3 bytes × 64 |
| Tempo | Table-based | Table-based |
| Gate | Implicit in wave | Explicit (+++ / ---) |

## Memory Usage

- **Player code**: ~2,304 bytes ($1000-$1900)
- **Player state**: ~159 bytes ($1900-$199F)
- **Music data**: ~600 bytes (all tables)
- **Total**: ~3,063 bytes

---

*This disassembly documents the Laxity NewPlayer v21 as used in "Stinsen's Last Night of '89" (2021)*
