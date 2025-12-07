# SID Factory II Format Specification

*Based on the official SID Factory II User Manual (2023-09-30) and source code analysis*

## Overview

SID Factory II (.sf2) files are C64 PRG files containing a music driver plus structured music data. They can be loaded in the SID Factory II editor or executed directly on a C64/emulator using `SYS4093`.

**Key Insight**: SF2 format is *driver-dependent*. The table layouts, sizes, and meanings change based on which driver is loaded. This specification focuses on **Driver 11**, the default "luxury" driver with full features.

## File Structure

```
Offset      Content
--------    ----------------------------------
$0000-0001  Load address (2 bytes, little-endian)
$0002-07FF  Driver code (~2KB)
$0800+      Header blocks (configuration)
$0900+      Music data tables
```

### File Identification

```cpp
// Driver ID marker at top address
DRIVER_ID_MARKER = 0x1337

// Auxiliary data vector (5 bytes before init address)
AUX_DATA_POINTER_ADDRESS = 0x0FFB

// IRQ vector (2 bytes before init address)
```

### Table Layout Types

SF2 supports two memory layouts for tables:

| Type | Value | Description |
|------|-------|-------------|
| RowMajor | 0 | Traditional row-by-row storage |
| ColumnMajor | 1 | Column-by-column (used by Driver 11 instruments) |

**Column-Major Example** (Driver 11 instruments, 32 × 6 bytes):
```
Memory layout:
$0A03-$0A22: All AD values (column 0)
$0A23-$0A42: All SR values (column 1)
$0A43-$0A62: All Flags values (column 2)
$0A63-$0A82: All Filter indices (column 3)
$0A83-$0AA2: All Pulse indices (column 4)
$0AA3-$0AC2: All Wave indices (column 5)
```

### Header Block IDs

SF2 uses a block-based header system:

| ID | Description |
|----|-------------|
| 1 | Descriptor (driver info) |
| 2 | Driver Common (addresses) |
| 3 | Driver Tables (table definitions) |
| 4 | Instrument Descriptor |
| 5 | Music Data (pointers) |
| 6 | Table Color Rules |
| 7 | Insert/Delete Rules |
| 8 | Action Rules |
| 9 | Instrument Data Descriptor |
| 255 | End marker |

## Music Data Tables

### Table Offsets (Driver 11)

| Table | Offset | Size | Description |
|-------|--------|------|-------------|
| Sequence Pointers | $0903 | var | Order lists and sequences |
| Instruments | $0A03 | 256 | 32 instruments × 8 bytes |
| Wave | $0B03 | 256 | 128 entries × 2 bytes |
| Pulse | $0D03 | 256 | 64 entries × 4 bytes |
| Filter | $0F03 | 256 | 64 entries × 4 bytes |

---

## Table Formats

### Init Table

The Init table configures song initialization:

| Column | Description |
|--------|-------------|
| 0 | Tempo table pointer (row index) |
| 1 | Main volume ($0F = maximum) |

Example: `00 0F` = Start at tempo row 0, full volume

Multiple entries support multi-song files (game music with main theme + jingles).

### Tempo Table

Defines song speed as **frames per row**. The driver updates at 50Hz (PAL) or 60Hz (NTSC).

| Value | Description |
|-------|-------------|
| $02-$FE | Frames per row (smaller = faster) |
| $7F XX | Wrap to row XX |
| $00 | Terminator for shorter chains |

**Examples:**
- `04 7F 00` = Constant speed 4
- `02 03 7F 00` = Alternating 2-3 for shuffle feel
- `02 02 03 7F 00` = 2⅓ average speed

**Note**: Minimum practical value is usually `$02` due to hard restart timing requirements.

### HR (Hard Restart) Table

Hard restart defeats the SID's "ADSR bug" - a timing issue causing notes to stumble (Martin Galway's "school band effect").

| Column | Description |
|--------|-------------|
| 0 | Attack/Decay for HR frame |
| 1 | Sustain/Release for HR frame |

**Default value**: `0F 00` (fast decay to silence)

**How it works**: The driver gates off 2 frames before the next note and applies the HR ADSR. This stabilizes envelope timing.

### Instruments Table

Referenced from the left column in sequences. **Cannot insert/delete rows** - all 32 instruments must be edited in place.

#### Driver 11 Format (6 bytes, column-major)

| Column | Description | Notes |
|--------|-------------|-------|
| 0 | AD (Attack/Decay) | Standard SID ADSR |
| 1 | SR (Sustain/Release) | Standard SID ADSR |
| 2 | Flags | See below |
| 3 | Filter table index | Pointer to filter program |
| 4 | Pulse table index | Pointer to pulse program |
| 5 | Wave table index | Pointer to wave program |

**Flags Byte (Column 2):**

| Bit | Value | Description |
|-----|-------|-------------|
| 7 | $80 | Hard restart enable |
| 6 | $40 | Filter on |
| 5 | $20 | Filter enable (allows toggling) |
| 4 | $10 | Oscillator reset enable |
| 0-3 | $0x | HR table index |

### Commands Table

Referenced from the middle column in sequences. **Cannot insert/delete rows**.

#### Driver 11 Format (3 columns)

| Column | Description |
|--------|-------------|
| 0 | Command byte |
| 1 | Parameter 1 |
| 2 | Parameter 2 |

#### Driver 11 Command Reference

*From notes_driver11.txt and source code analysis*

| Type | XX | YY | Description |
|------|----|----|-------------|
| T0 | XX | YY | Slide up/down - XXYY = 16-bit speed |
| T1 | XX | YY | Vibrato - XX=frequency, YY=amplitude (smaller=stronger) |
| T2 | XX | YY | Portamento - XXYY = 16-bit speed (use 02 80 00 to disable) |
| T3 | XX | YY | Arpeggio - XX=speed, YY=arp table index |
| T4 | XX | YY | [11.01-11.04] Fret slide - XX=00-7f up/80-ff down, YY=semitones |
| T8 | XX | YY | Set local ADSR (until next note) |
| T9 | XX | YY | Set instrument ADSR (until different instrument) |
| Ta | -- | XX | Filter program - XX=table index |
| Tb | -- | XX | Wave program - XX=table index |
| Tc | -- | XX | [11.02] Pulse program - XX=table index |
| Td | -- | XX | [11.02] Tempo program - XX=table index |
| Te | -- | -X | [11.02] Main volume - X=0-f |
| Tf | -- | XX | Increase demo value - XX=amount |

**Note**: The T value (0-f) becomes the delay in ticks for driver 11.04.

#### Command Byte Values (from source)

```cpp
Cmd_Slide = 0x00
Cmd_Vibrato = 0x01
Cmd_Portamento = 0x02
Cmd_Arpeggio = 0x03
Cmd_Fret = 0x04
Cmd_ADSR_Note = 0x08
Cmd_ADSR_Persist = 0x09
Cmd_Index_Filter = 0x0a
Cmd_Index_Wave = 0x0b
Cmd_Index_Pulse = 0x0c      // Driver 11.02+
Cmd_Tempo = 0x0d            // Driver 11.02+
Cmd_Volume = 0x0e           // Driver 11.02+
Cmd_Demo_Flag = 0x0f
```

#### Driver 11 Version Differences

| Version | Changes |
|---------|---------|
| 11.00 | Original default driver |
| 11.01 | Added fret slide command |
| 11.02 | Added pulse/tempo/volume commands |
| 11.03 | Added additional filter enable flag |
| 11.04 | Added note event delay |
| 11.05 | Fret slide removed, HR table 16→8 rows, skip pulse reset flag |

Press F12 in SID Factory II for command overlay (shown in magenta).

### Wave Table

Defines waveform sequences for instruments.

| Column | Description |
|--------|-------------|
| 0 | Waveform / Control byte |
| 1 | Note offset / Jump target |

**Column 0 - Waveform Values:**

| Value | Waveform |
|-------|----------|
| $11 | Triangle + Gate |
| $21 | Sawtooth + Gate |
| $41 | Pulse + Gate |
| $81 | Noise + Gate |
| $10/$20/$40/$80 | Same without gate |
| $7F | Jump command |

**Column 1 - Note Offset:**

| Value | Description |
|-------|-------------|
| $00 | No transpose |
| $01-$7D | Semitone offset (e.g., $0C = +12 = octave) |
| $80+ | Absolute note (great for drums) |
| (with $7F) | Jump target row index |

**Example:**
```
Index  Col0  Col1  Description
  0    $41   $00   Pulse+Gate, no transpose
  1    $41   $0C   Pulse+Gate, +1 octave
  2    $7F   $00   Jump to index 0 (loop)
```

**Note**: In Driver 11, arpeggio only affects wave entries where Column 1 = `$00`.

### Pulse Table

Defines pulse width modulation for waveform $41.

| Column | Description |
|--------|-------------|
| 0 | Pulse value (hi nibble→lo, lo nibble→hi) or $FF=keep |
| 1 | Add/subtract delta per frame (16-bit) |
| 2 | Duration (bits 0-6) + direction (bit 7: 0=add, 1=sub) |
| 3 | Next entry index |

**Pulse Width**: 12-bit (0-4095), most pronounced at 2048.

**Example ping-pong:**
```
Entry 0: 04 50 30 04  ; Start $0400, add $50 for 48 frames, goto 1
Entry 1: FF 50 B0 00  ; Keep current, sub $50 for 48 frames, goto 0
```

### Filter Table

Defines filter cutoff sweeps. **Filter is global** - one register for all channels.

| Column | Description |
|--------|-------------|
| 0 | Filter cutoff value ($FF = keep current) |
| 1 | Count/delta value |
| 2 | Duration |
| 3 | Next entry index |

**Voice Bitmask** (for routing):

| Bit | Value | Channel |
|-----|-------|---------|
| 0 | 1 | Voice 1 |
| 1 | 2 | Voice 2 |
| 2 | 4 | Voice 3 |

Examples: 3 = voices 1+2, 7 = all voices

**Filter Range**: 11-bit (0-2047), all values unique (unlike pulse).

### Arp (Arpeggio) Table

Separate chord table (Driver 11 feature). Values are semitone offsets added to the note.

| Value | Description |
|-------|-------------|
| $00-$7D | Semitone offset |
| $7F XX | Jump to row XX |

**Note**: Arpeggio only affects wave table entries with note offset = `$00`.

---

## Sequence and Track Structure

### Tracks

Three tracks for three SID voices. Each track has:
- **Order list**: Sequence references with transpose
- **Sequences**: Actual note/instrument/command data

### Order List Format

Each entry is 4 hex digits: `XXYY`

| XX | Description |
|----|-------------|
| $94 | -12 semitones (one octave down) |
| $A0 | No transpose (default) |
| $AC | +12 semitones (one octave up) |

YY = Sequence number ($00-$FF)

### Sequence Format

Three columns per row:

| Column | Description | Values |
|--------|-------------|--------|
| 1 | Instrument | $80 (--), $A0-$BF (instrument+$A0) |
| 2 | Command | $80 (--), $C0+ (command+$C0) |
| 3 | Note | See below |

**Note Values:**

| Value | Description |
|-------|-------------|
| $00-$5D | Notes (C-0 to B-7) |
| $7E | `+++` (gate on / sustain) |
| $7F | End of sequence |
| $80 | `---` (gate off / release) |

**Special:**
- `**` in instrument column = tie note (no restart)

### Sequence Packing (from source)

Sequences use persistence encoding for efficiency. If instrument/command is same as previous event, use `$80` marker instead of repeating the value:

```cpp
struct Event {
    unsigned char m_Instrument;    // 0x80+ = no change
    unsigned char m_Command;       // 0x80+ = no change
    unsigned char m_Note;          // Note value
}

// Packing algorithm:
lastInstr = 0x80
lastCmd = 0x80

for each event:
    if event.instrument == lastInstr:
        write 0x80
    else:
        write event.instrument
        lastInstr = event.instrument

    // Similar for command
    write event.note
```

### Order List Entry (from source)

```cpp
struct Entry {
    unsigned char m_Transposition;
    unsigned char m_SequenceIndex;
}
```

- Max 256 entries per track
- Packed format with loop index marker at end

### Gate System

SF2 uses explicit gate on/off (different from GoatTracker/CheeseCutter):

```
Row  Inst  Cmd  Note
  0   02   --   C-4    ; Note triggers, ADSR attacks
  1   --   --   +++    ; Gate stays on, sustain
  2   --   --   +++    ; Still sustaining
  3   --   --   ---    ; Gate off, release begins
```

This provides precise control over envelope behavior.

### Contiguous Sequence Stacking

Sequences in each track can have different lengths - they stack like Tetris blocks. This is the same system used in JCH's original C64 editor and CheeseCutter.

---

## Control Bytes Reference

| Byte | Context | Description |
|------|---------|-------------|
| $7F | Tables | End marker / Jump command |
| $7E | Wave table | Loop marker |
| $7F | Tempo | Wrap to next byte index |
| $A0 | Order list | No transpose |
| `+++` | Sequence | Gate on (sustain) |
| `---` | Sequence | Gate off (release) |
| `**` | Sequence | Tie note |

---

## Available Drivers

| Driver | Description |
|--------|-------------|
| 11 | Standard (luxury) - full features, default |
| 12 | Extremely simple, basic effects only |
| 13 | Rob Hubbard emulation |
| 14 | Experimental gate-off timing |
| 15 | Tiny mark I (expanded from 12) |
| 16 | Tiny mark II (no commands) |

**Changing drivers**: Load a driver with F10, then import your tune with Ctrl+F10.

---

## Multi-Song Support

SF2 files support multiple songs (useful for game music):

- F7 opens song management dialog
- Each song has its own bookmarks and Init table entry
- All songs **share** sequences and table data
- Songs can loop or end (Ctrl+L toggles)

---

## Packing and Export

When finished composing:

1. F6 → Utilities menu
2. **Optimize** (optional): Removes unused data, renumbers tables
3. **Pack**: Choose memory location and zero page addresses

**Export Formats:**
- No extension = PRG file (default)
- `.sid` extension = SID file (prompts for metadata)

**Note**: The optimizer may renumber instruments/commands.

---

## Key Differences from Laxity Format

| Aspect | Laxity NewPlayer | SID Factory II |
|--------|------------------|----------------|
| Wave table order | (note, waveform) | (waveform, note) |
| Pulse indices | Y*4 (pre-multiplied) | Direct indices |
| Gate system | Implicit | Explicit (+++ / ---) |
| Table pointers | Absolute addresses | Relative indices |
| Driver | Compiled in | Modular/selectable |

---

## Visualizers

SF2 provides visual feedback:

**Pulse Bars** (3 voices):
- Width represents current pulse (0-4095)
- Center line = 2048 (most pronounced)
- Background color changes when voice is filtered

**Filter Bar**:
- Shows filter cutoff (0-2047)
- All values unique (no mirror like pulse)

---

## Configuration

Settings are in INI files:
- `config.ini` - Main configuration
- `user.ini` - User overrides
- `color_schemes/` - Color scheme files

macOS/Linux: Place `user.ini` in `~/.config/sidfactory2/`

---

## Import/Conversion

SF2 can convert from:
- **MOD** - Amiga 4-voice
- **SNG** - GoatTracker 2
- **CT** - CheeseCutter
- **NP20.G4** - JCH NewPlayer 20 source files

All conversions target Driver 11.

---

## References

- [SID Factory II GitHub](https://github.com/Chordian/sidfactory2)
- [SID Factory II User Manual](https://sidfactory2.com/) (2023-09-30)
- [Source Code Analysis](SF2_SOURCE_ANALYSIS.md)
- [Driver Reference](DRIVER_REFERENCE.md)
- Coded by Thomas Egeskov Petersen (Laxity)
- Mac version by Michel de Bree
- Manual by Jens-Christian Huus
