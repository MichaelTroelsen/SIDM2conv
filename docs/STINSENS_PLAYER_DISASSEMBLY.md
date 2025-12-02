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

### Wave Table Format

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
