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

Location: **$1914-$1954** (64 bytes total, split into 2×32 byte arrays)

The wave table is split into two parallel arrays:

```asm
;===============================================================================
; Wave Table Structure
;===============================================================================
; $1914-$1933: Note offsets (32 entries)
;   Each byte is a note offset (0-95) or special marker:
;   $7F = Loop marker
;   $7E = Gate on (sustain)
;   $80 = Note offset special (recalculate frequency)
;
; $1934-$1953: Waveforms (32 entries)
;   Bits 0-3: Waveform type
;     $01 = Triangle
;     $02 = Sawtooth
;     $04 = Pulse
;     $08 = Noise
;   Bit 4: Gate bit
;   Bits 5-7: Additional control flags
```

#### Hex Dump (from Stinsen's Last Night of '89)

```
Address: $1914-$1954  Size: 64 bytes (32 notes + 32 waveforms)
================================================================================
00: 9a 00 07 c4 ac c0 bc 0c c0 00 0f c0 00 76 74 14
10: b4 12 00 18 00 00 1b 00 1d c5 00 20 00 22 c0 00
20: 25 00 27 00 29 c7 ae a5 c0 2e 00 30 88 00 81 00
30: 00 0f 7f 88 7f 88 0f 0f 00 7f 88 00 0f 00 7f 86
```

**Structure breakdown:**
- Bytes $00-$1F (0-31): Note offsets / Waveform control bytes
- Bytes $20-$3F (32-63): Waveform selection bytes

### Pulse Table Format

Location: **$1A3B-$1A7B** (64 bytes, 16 entries × 4 bytes)

The pulse table controls pulse width modulation (PWM) programs. Each entry is 4 bytes:

```asm
;===============================================================================
; Pulse Table Entry Format (4 bytes per entry)
;===============================================================================
; Byte 0: Initial pulse width value (bits 0-7 of 12-bit value)
; Byte 1: Delta (change per frame)
; Byte 2: Duration (frames to run)
; Byte 3: Next entry (chain to another pulse program)
;
; Special values:
;   $7F in byte 0 = End of pulse program
;   $00 delta = Static pulse width (no modulation)
```

#### Hex Dump (from Stinsen's Last Night of '89)

```
Address: $1A3B-$1A7B  Size: 64 bytes  Count: 16 entries
================================================================================
00: ba db a7 b9 cd 25 f3 b1 62 ad b9 c0 e1 31 af 30
10: 1a 1a 1a 1b 1b 1c 1c 1d 1d 1e 1f 1f 1f 1f 20 20
20: 20 20 20 20 20 21 21 21 21 22 22 22 23 23 24 25
30: 25 25 25 25 26 26 27 a0 0e 0f 0f 0f 0f 11 01 05
```

### Filter Table Format

Location: **$1A1E-$1A4E** (48 bytes, 16 entries × 3 bytes)

The filter table contains filter cutoff and resonance programs:

```asm
;===============================================================================
; Filter Table Entry Format (3 bytes per entry)
;===============================================================================
; Byte 0: Filter cutoff frequency (0-255)
; Byte 1: Resonance setting (bits 4-7) + filter routing (bits 0-3)
;         Bits 0-3: Voice enable (bit 0=V1, bit 1=V2, bit 2=V3)
;         Bit 3: External input enable
;         Bits 4-7: Resonance (0-15)
; Byte 2: Filter type/mode
;         Bit 0: Low-pass
;         Bit 1: Band-pass
;         Bit 2: High-pass
```

#### Hex Dump (from Stinsen's Last Night of '89)

```
Address: $1A1E-$1A4E  Size: 48 bytes  Count: 16 entries
================================================================================
00: 70 9b b3 1a 1a 1a d1 d5 f7 97 ec 57 ba 3b fc ae
10: 30 47 5e 75 28 4c 6e 80 99 a9 cb 2e 99 ba db a7
20: b9 cd 25 f3 b1 62 ad b9 c0 e1 31 af 30 1a 1a 1a
```

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
