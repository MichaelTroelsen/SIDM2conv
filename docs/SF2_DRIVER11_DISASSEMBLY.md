# SID Factory II Driver 11 Player Disassembly

Complete annotated disassembly of the SF2 Driver 11 player from Stinsens_Last_Night_of_89_d11.sf2

## File Information

- **Format**: PSID v2
- **Load Address**: $0D7E
- **Init Address**: $1006 (but jumps through $1000)
- **Play Address**: $16C8 (data reference, actual play at $15ED via $1003)
- **File Size**: 8,436 bytes
- **Driver**: SID Factory II Driver 11 ("Luxury" driver with full features)

## Memory Map

```
$0D7E - $0FFF : Music Data Section (641 bytes)
                - Sequences (voice patterns)
                - Orderlists (song structure)
                - Init table pointer
                - Tempo data
                - HR (Hard Restart) values

$1000 - $1005 : Jump Table
$1006 - $15E3 : Driver Code (Play Routine)
$15E4 - $15EC : Init Routine
$15ED - $15F2 : Play Entry Point
$15F3 - $1683 : Frequency & Divisor Tables

$1664 - $1665 : Init Table (2 bytes)
$1684 - $16A3 : HR (Hard Restart) Table (32 bytes)
$16A4 - $1783 : Driver Variables & State
$1784 - $1843 : Instruments Table (6×32 = 192 bytes, column-major)
$1844 - $1903 : Commands Table (3×64 = 192 bytes)
$1904 - $1923 : Padding/Reserved
$1924 - $1B23 : Wave Table (2×256 = 512 bytes)
$1B24 - $1E23 : Pulse Table (3×256 = 768 bytes)
$1E24 - $2123 : Filter Table (3×256 = 768 bytes)
$2124 - $2223 : Arpeggio Table (1×256 = 256 bytes)
$2224 - $2323 : Tempo Table (1×256 = 256 bytes)
```

## Key Player Variables (RAM)

Driver state area at $16A4-$1783:

```
$16CB - Tempo counter
$16CC - Player state flags
  Bit 6: Play enabled ($40 = playing, $00 = stopped)
  Bit 7: Initialized ($80 = ready)
$16CD - Current subtune number
$16CE - Speed/tempo value
$16CF - Tempo backup
$16D0 - Volume (low nibble)
$16D1 - Filter control (bits 4-6)

Voice State Areas (per-voice):
$16C8-$1740 : Voice 1 state
$1741-$17B9 : Voice 2 state
$17BA-$1832 : Voice 3 state

Each voice state includes:
- Sequence position pointers
- Current note & instrument
- ADSR values
- Waveform control
- Effect parameters
```

## Jump Table ($1000-$1005)

```asm
;---------------------------------------------------------------
; Entry Points
;---------------------------------------------------------------
$1000  4C E4 15      JMP    $15E4         ; Init routine
$1003  4C ED 15      JMP    $15ED         ; Play routine
```

## Init Routine ($15E4-$15EC)

```asm
;---------------------------------------------------------------
; Init Routine - Called once to start playback
;---------------------------------------------------------------
$15E4  8D CD 16      STA    $16CD         ; Store subtune number
$15E7  A9 00         LDA    #$00          ;
$15E9  8D CC 16      STA    $16CC         ; Clear player state flags
$15EC  60            RTS                  ; Return
```

The init routine stores the subtune number and clears the player state, preparing for playback.

## Play Entry Point ($15ED-$15F2)

```asm
;---------------------------------------------------------------
; Play Entry Point - Called every frame (50/60 Hz)
;---------------------------------------------------------------
$15ED  A9 40         LDA    #$40          ; Set play flag bit
$15EF  8D CC 16      STA    $16cc         ; Enable playback
$15F2  60            RTS                  ; Return
```

This entry point sets the "playing" flag and returns. The actual play routine is integrated into the main code starting at $1006.

## Main Driver Code ($1006-$15E3)

The main driver code starting at $1006 handles:

1. **Initialization Check** ($1006-$100E)
```asm
$1006  A9 00         LDA    #$00          ;
$1008  2C CC 16      BIT    $16CC         ; Test player state flags
$100B  30 44         BMI    $1051         ; Branch if initialized (bit 7 set)
$100D  70 38         BVS    $1047         ; Branch if overflow set
```

2. **First-Time Initialization** ($100F-$1046)
```asm
$100F  A2 73         LDX    #$73          ; X = 115 (state area size)
$1011  9D CD 16      STA    $16CD,X       ; Clear state area
$1014  CA            DEX                  ; Decrement counter
$1015  D0 FA         BNE    $1011         ; Loop until done

; Load init table values
$1017  AE CD 16      LDX    $16CD         ; Get subtune number
$101A  BD 44 17      LDA    $1744,X       ; Read tempo row pointer
$101D  8D CB 16      STA    $16CB         ; Store tempo counter
$1020  8D CF 16      STA    $16CF         ; Store tempo backup

$1023  BD 64 17      LDA    $1764,X       ; Read init byte (volume + filter)
$1026  29 0F         AND    #$0F          ; Isolate volume (low nibble)
$1028  8D D0 16      STA    $16D0         ; Store volume

$102B  BD 64 17      LDA    $1764,X       ; Read init byte again
$102E  29 70         AND    #$70          ; Isolate filter control (bits 4-6)
$1030  8D D1 16      STA    $16D1         ; Store filter control

; Initialize sequence pointers for all voices
$1033  A9 02         LDA    #$02          ; Start at row 2 of orderlist
$1035  8D CE 16      STA    $16CE         ; Store speed
$1038  8D 41 17      STA    $1741         ; Voice 2 sequence position
$103B  8D 42 17      STA    $1742         ;
$103E  8D 43 17      STA    $1743         ; Voice 3 sequence position

$1041  A9 80         LDA    #$80          ; Set initialized flag
$1043  8D CC 16      STA    $16CC         ; Mark as initialized
$1046  60            RTS                  ; Return
```

3. **SID Register Updates** ($1047-$1050)
```asm
$1047  8D 04 D4      STA    $D404         ; Voice 1 Control Register
$104A  8D 0B D4      STA    $D40B         ; Voice 2 Control Register
$104D  8D 12 D4      STA    $D412         ; Voice 3 Control Register
$1050  60            RTS                  ; Return
```

4. **Frame Processing Loop** ($1051-$15E3)

The main playback loop processes each frame:
- Decrements tempo counter
- When counter reaches zero:
  - Advances to next row in sequences
  - Reads note/instrument/command data
  - Updates SID registers
  - Processes effects (vibrato, slides, arpeggios, etc.)
  - Handles gate on/off for envelopes
  - Manages hard restart (HR) for clean note attacks

## Driver Architecture

### SF2 Driver 11 Key Features

1. **Column-Major Instrument Storage**
   - Instruments stored as 6 bytes × 32 slots
   - Format: [ADSR_AD, ADSR_SR, Wave_ptr, Pulse_ptr, Filter_ptr, Flags]

2. **Interleaved Wave Table**
   - 2 bytes per entry: [waveform, note_offset]
   - Contrast with Laxity's split arrays

3. **3-Byte Commands**
   - Full command table with parameter support
   - Includes slide, vibrato, portamento, ADSR control, tempo, volume

4. **Separate Table Sections**
   - Wave, Pulse, Filter, Arpeggio, Tempo all have dedicated 256-byte sections
   - Allows larger tables than Laxity format

5. **Hard Restart System**
   - 32-byte HR table with ADSR values
   - Prevents SID ADSR bug by gating off before new notes

### Comparison with Laxity Player

| Feature | Laxity NewPlayer v21 | SF2 Driver 11 |
|---------|---------------------|---------------|
| Load Address | $1000 | $0D7E |
| Instrument Storage | 8 bytes row-major | 6 bytes column-major |
| Wave Table | Split (notes + waveforms) | Interleaved (waveform + note) |
| Pulse Table | Pre-multiplied indices | Direct indices |
| Table Sizes | Variable (typically 32-128) | Fixed 256-byte sections |
| Command Format | Variable length | 3-byte fixed |
| HR Table | Implicit/default | Explicit 32-entry table |
| Tempo Table | Part of filter table | Separate 256-byte section |
| Code Size | ~2.3 KB | ~3.5 KB |
| Data Size | ~1.0 KB | ~3.5 KB (with tables) |
| Total Size | ~3.3 KB | ~7.0 KB |

## Frequency Tables ($15F3-$1683)

The driver includes comprehensive lookup tables for note frequency calculations:

### Note-to-Speed Divisor Table ($15F3-$1662)

Used for effect speed calculations (vibrato, slides):
```
$15F3: 01 01 01 01 01 01 01 01 01 01 01 02 02 02 02 02
       ^                                   ^
       Note 0 (C-0)                        Note 11 (B-0)

$1603: 02 02 02 02 03 03 03 03 03 04 04 04 04 05 05 05
       ^                                   ^
       Note 12 (C-1)                       Note 23 (B-1)

[... continues for full 96-note range ...]

$165D: 96 BD E7 13 42 74 A9 E0 1B 5A 9B E2 2C 7B CE 27
       ^                                   ^
       Note 84 (C-7)                       Note 95 (B-7)
```

### Frequency Table ($1664-$1683)

Direct note-to-SID-frequency lookups for octave-independent frequency calculation.

## Data Section ($0D7E-$0FFF)

The data section before the driver code contains:

1. **Sequences** - Pattern data for each voice
   - 3 bytes per row: [instrument, command, note]
   - Special values:
     - `$80+` = No change (tie note)
     - `$7F` = End marker / Jump command
     - `$7E` = Gate off (---)

2. **Orderlists** - Song structure
   - One orderlist per voice
   - Points to sequence numbers
   - `$A0+` values indicate transpose amount

3. **Init Data** - Initial tempo and volume settings

## Table Formats

### Instruments Table ($1784-$1843)

Column-major storage: 6 bytes × 32 instruments

```
Byte 0: ADSR Attack/Decay
Byte 1: ADSR Sustain/Release
Byte 2: Wave table pointer (index)
Byte 3: Pulse table pointer (index)
Byte 4: Filter table pointer (index)
Byte 5: Flags
  Bit 0: Enable HR (Hard Restart)
  Bit 1-7: Reserved
```

### Wave Table ($1924-$1B23)

2 bytes × 256 entries:
```
Byte 0: Waveform byte
  Bit 0: Gate (1 = on)
  Bit 1: Sync
  Bit 2: Ring Mod
  Bit 3: Test
  Bit 4: Triangle
  Bit 5: Sawtooth
  Bit 6: Pulse
  Bit 7: Noise

Byte 1: Note offset (relative transpose)
  $00 = No change (vibrato/slide applies)
  $01-$7F = Add to base note
  $80 = Special: Recalculate frequency without overwriting
```

### Pulse Table ($1B24-$1E23)

3 bytes × 256 entries:
```
Byte 0: Pulse width low byte
Byte 1: Pulse width high byte (bits 0-3 only)
Byte 2: Next entry index ($7F = end/repeat)
```

### Filter Table ($1E24-$2123)

3 bytes × 256 entries:
```
Byte 0: Cutoff frequency (11-bit, high 3 bits in byte 1)
Byte 1: Cutoff high bits + resonance
  Bits 0-2: Cutoff bits 8-10
  Bits 4-7: Resonance
Byte 2: Filter routing
  Bit 0: Voice 1 filtered
  Bit 1: Voice 2 filtered
  Bit 2: Voice 3 filtered
  Bit 4: Low-pass
  Bit 5: Band-pass
  Bit 6: High-pass
```

### Arpeggio Table ($2124-$2223)

1 byte × 256 entries:
```
Semitone offsets for chord arpeggios
$7F = End/Loop marker
```

### Tempo Table ($2224-$2323)

1 byte × 256 entries:
```
Speed values (frames per row)
$7F = End/Loop marker
$00 = Special: Wrap to beginning
```

## Command System

Commands are stored in the Commands Table ($1844-$1903) as 3-byte entries:

| Command | Byte 0 | Byte 1 | Byte 2 | Description |
|---------|--------|--------|--------|-------------|
| T0 | $00 | speed | amount | Slide up/down |
| T1 | $01 | speed | depth | Vibrato |
| T2 | $02 | speed | target | Portamento to note |
| T3 | $03 | pattern | speed | Arpeggio |
| T4 | $04 | fret | - | Fret (fixed note offset) |
| T8 | $08 | AD | SR | Local ADSR (this note only) |
| T9 | $09 | AD | SR | Set ADSR (persistent) |
| TA | $0A | index | - | Set filter table index |
| TB | $0B | index | - | Set wave table index |
| TC | $0C | index | - | Set pulse table index |
| TD | $0D | tempo | - | Set tempo (speed) |
| TE | $0E | volume | - | Set master volume |
| TF | $0F | flag | - | Demo mode flag |

## Execution Flow

1. **First Call (Init)**
   - Entry at $1006
   - Check initialized flag at $16CC
   - If not initialized:
     - Clear 115 bytes of state area
     - Load init table (tempo, volume, filter)
     - Initialize all voice sequence pointers
     - Set initialized flag ($80)
   - Return

2. **Subsequent Calls (Play)**
   - Entry at $1003 → $15ED
   - Set play flag ($40)
   - Main loop:
     - Check tempo counter
     - If zero:
       - Process next row for each voice
       - Read sequence data (instrument, command, note)
       - Update SID registers
       - Apply effects
       - Handle gate on/off
     - If non-zero:
       - Decrement counter
       - Continue effects (vibrato, slides)
   - Update SID registers
   - Return

3. **Per-Voice Processing**
   - Check orderlist position
   - Read current sequence
   - Parse 3-byte events: [instrument, command, note]
   - Handle special values:
     - `$80+` instrument = no change
     - `$80+` command = no change
     - `$7F` note = end/jump
     - `$7E` note = gate off
   - Apply transpose from orderlist
   - Look up frequency from table
   - Write to SID registers:
     - $D400-$D401: Frequency (Voice 1)
     - $D402-$D403: Pulse width
     - $D404: Control register (waveform + gate)
     - $D405-$D406: ADSR
     - (Similar for voices 2 and 3)

4. **Hard Restart Handling**
   - If instrument has HR flag:
     - 2 frames before next note:
       - Gate off
       - Apply HR ADSR values from table
     - Next frame:
       - Gate on with new note
       - Apply normal instrument ADSR
   - Prevents SID ADSR bug

## Notes on SF2 Format

### Benefits of Driver 11

1. **Larger Tables** - 256-byte sections allow more complex instruments
2. **Flexible Commands** - 3-byte format supports rich effects
3. **Clean Envelopes** - HR system prevents ADSR artifacts
4. **Editor Integration** - Designed for SID Factory II editor workflow

### Limitations

1. **File Size** - ~7 KB total (driver + tables + data)
2. **Memory Usage** - Loads at $0D7E, occupies significant C64 memory
3. **Complexity** - More complex than simple players like Laxity
4. **Fixed Limits** - 32 instruments, 64 commands, 256-entry tables

### Conversion Considerations

When converting from Laxity to SF2:
- **Instrument format** must be converted from 8-byte row-major to 6-byte column-major
- **Wave table** must be interleaved (waveform + note pairs)
- **Pulse indices** must be converted from pre-multiplied to direct
- **Gate commands** must be made explicit (`+++` and `---`)
- **HR values** should be provided for clean note attacks
- **Table sizes** can expand from Laxity's typical 32-128 to SF2's 256

## Conclusion

SF2 Driver 11 is a "luxury" driver optimized for editor workflow and sound quality. It trades file size and complexity for flexibility and cleaner sound output. The column-major storage, explicit gate control, and hard restart system make it suitable for complex multi-instrument compositions.

The driver's integration with SID Factory II allows real-time editing and preview, making it ideal for composition and arrangement work on the C64.

---

*Disassembled from: output/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89_d11.sid*
*Generated: 2025-12-02*
