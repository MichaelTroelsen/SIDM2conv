# Laxity NewPlayer V21 Format Documentation

This document describes the internal format of SID files using the Laxity NewPlayer V21 driver, based on analysis of Angular.sid by Thomas Mogensen (DRAX).

## Overview

The Laxity NewPlayer V21 is a music driver for the Commodore 64 SID chip. It uses a table-driven approach with:
- **Orderlists** - Sequence playback order for each of 3 channels
- **Sequences** - Note and command data
- **Instruments** - ADSR envelope and wave table pointer
- **Tables** - Wave, Pulse, Filter modulation data

## Memory Layout (Angular.sid)

```
Address Range     Size    Content
--------------------------------------------
$1000-$1002       3       Init jump (JMP to init code)
$1003-$1005       3       Play jump (JMP to play routine)
$1006-$1832       ?       Player code
$1833-$18F2     192       Frequency table (96 notes * 2 bytes)
$19AF-$19E6      56       Wave table (28 entries * 2 bytes)
$1A27-$1A6A      68       Pulse table (varies)
$1A6B-$1ADB     113       Instrument table (16 instruments)
$1ADC-$1AEF      20       Filter table
$1AF2-$1B1B      42       Orderlists (3 channels)
$1B1C-$1B37      28       Sequence pointers (70 sequences)
$1B38-$1EC4     909       Sequence data
```

## File Structure

### PSID Header (124 bytes)

```
Offset  Size  Field           Value (Angular.sid)
----------------------------------------------
$00     4     Magic ID        "PSID"
$04     2     Version         $0002
$06     2     Data offset     $007C (124)
$08     2     Load address    $0000 (in data)
$0A     2     Init address    $1000
$0C     2     Play address    $1003
$0E     2     Songs           $0001
$10     2     Start song      $0001
$12     4     Speed           $00000000
$16     32    Name            "Angular"
$36     32    Author          "Thomas Mogensen (DRAX)"
$56     32    Copyright       "2017 Camelot/Vibrants"
```

### C64 Data

After the header, data is loaded to memory starting at the load address embedded in the first 2 bytes of data.

## Sequence Byte Encoding

Sequences contain note and control data with specific byte ranges:

| Byte Range  | Meaning           | Description |
|-------------|-------------------|-------------|
| $00-$5D     | Note              | Note index (C-0 to B-7, 94 notes) |
| $7E         | Tie               | Hold previous note |
| $7F         | End/Loop          | End sequence or loop marker |
| $80-$9F     | Duration          | Note length (value & $1F) |
| $A0-$BF     | Instrument        | Instrument number (value & $1F) |
| $C0-$CF     | Command           | Command type (value & $0F) |
| $D0-$FF     | Command parameter | Parameter for previous command |

### Duration Values

The duration is encoded as `$80 + duration_value` where duration_value is 0-31:

```
$80 = duration 0 (very short)
$81 = duration 1
...
$9F = duration 31 (longest)
```

### Example Sequence Parsing

```
Bytes: 85 A0 30 91 A1 2C 89 A0 30
Parse:
  $85 = Duration 5
  $A0 = Instrument 0
  $30 = Note C-4 (48)
  $91 = Duration 17
  $A1 = Instrument 1
  $2C = Note E-3 (44)
  $89 = Duration 9
  $A0 = Instrument 0
  $30 = Note C-4 (48)
```

## Orderlist Format

Each channel has an orderlist that controls sequence playback. The orderlist consists of entries with this format:

```
Entry format: [Transpose] [Sequence Number]

Where:
  Transpose:  Signed offset added to all notes (bit 7 set = negative)
  Sequence:   Index into sequence pointer table
```

### Transpose Calculation

**CRITICAL**: The transpose byte in the orderlist MUST be added to each note in the sequence:

```
Final note = Sequence note + (Orderlist transpose & $7F)

If transpose bit 7 is set:
  Final note = Sequence note - (Orderlist transpose & $7F)
```

### Orderlist End Markers

```
$7F = Loop to beginning
$7E = End of orderlist
```

### Example Orderlist (Channel 1)

```
Address: $1AF2
Data:    00 00 00 02 00 04 00 06 7F

Parse:
  Entry 0: Transpose=0, Sequence=0
  Entry 1: Transpose=0, Sequence=2
  Entry 2: Transpose=0, Sequence=4
  Entry 3: Transpose=0, Sequence=6
  Entry 4: $7F = Loop to start
```

## Instrument Table

Each instrument is 7 bytes:

```
Offset  Size  Field         Description
-----------------------------------------
0       1     Attack/Decay  SID $D405/6/7 value
1       1     Sustain/Rel   SID $D406/7/8 value
2       1     Wave Ptr      Index into wave table
3       1     Pulse Ptr     Index into pulse table (or $FF for none)
4       1     Filter Ptr    Index into filter table (or $FF for none)
5       1     HR Ptr        Hard restart table pointer
6       1     Extra         Additional flags
```

### Example Instrument

```
Instrument 0 at $1A6B:
  Bytes: 03 F8 00 FF FF 00 00

  AD = $03 (Attack=0, Decay=3)
  SR = $F8 (Sustain=15, Release=8)
  Wave Ptr = $00 (wave table entry 0)
  Pulse Ptr = $FF (no pulse)
  Filter Ptr = $FF (no filter)
```

## Wave Table

The wave table controls waveform changes and pitch modulation. Each entry is 2 bytes:

```
Byte 0: Note offset (signed) or control
Byte 1: Waveform or jump target

Control bytes:
  $7F = Jump to entry (byte 1 = target index)
  $80+ = Set absolute waveform with note recalc
```

### Wave Table Format

```
Byte 0    Byte 1    Meaning
-----------------------------------
$00-$7E   $xx       Note offset, waveform
$7F       $xx       Jump to entry xx
$80+      $xx       Absolute waveform + note recalc
```

### Example Wave Table Entries

```
Index  Byte0  Byte1  Description
---------------------------------
0      $81    $DF    Waveform $DF, note +129 (recalc)
1      $41    $00    Waveform $00, note +65
2      $7F    $01    Jump to entry 1 (loop)
3      $81    $DF    Waveform $DF, note +129
```

### Waveform Bit Meanings

```
Bit 7: Noise
Bit 6: Pulse
Bit 5: Sawtooth
Bit 4: Triangle
Bit 3: Test
Bit 2: Ring mod
Bit 1: Sync
Bit 0: Gate

Common values:
  $11 = Triangle + Gate
  $21 = Sawtooth + Gate
  $41 = Pulse + Gate
  $81 = Noise + Gate
```

## Pulse Table

Controls pulse width modulation (PWM). Each entry varies but typically:

```
Byte 0: Control/value
Byte 1: Pulse width high
Byte 2: Duration/speed
Byte 3: Next entry pointer
```

### Pulse Table Format

```
Control values:
  $00-$7F = Pulse width change
  $FF = Jump/loop marker
```

## Filter Table

Controls SID filter modulation:

```
Byte 0: Filter cutoff change
Byte 1: Resonance/routing
Byte 2: Duration
Byte 3: Next entry
```

## Frequency Table

The player contains a frequency table mapping note indices (0-95) to SID frequency values:

```
Note 0  (C-0):  $0112
Note 12 (C-1):  $0224
Note 24 (C-2):  $0448
Note 36 (C-3):  $0890
Note 48 (C-4):  $1120
Note 60 (C-5):  $2240
Note 72 (C-6):  $4480
Note 84 (C-7):  $8900
```

## Command Types

Commands ($C0-$CF) modify playback:

```
Command  Name           Parameter
---------------------------------
$C0      Slide Up       Speed
$C1      Slide Down     Speed
$C2      Vibrato        Depth/speed
$C3      Portamento     Speed
$C4      Set ADSR       AD, SR values
$C5      Set Filter     Cutoff, resonance
$C6      Set Wave       Wave table index
$C7      Set Pulse      Pulse width
$C8      Set Speed      New tempo
$C9      Set Volume     Volume level
$CA      Arpeggio       Arp table index
$CB      Note Cut       Cut time
$CC      Legato         Enable/disable
$CD      Retrigger      Count
$CE      Delay          Frames
$CF      End            Stop channel
```

## Conversion Considerations

### Note Mapping Issues

When converting to SF2 format, consider:

1. **Transpose**: Each orderlist entry has a transpose byte that offsets all notes in that sequence
2. **Wave table offsets**: Wave table entries can add/subtract from the base note
3. **Arpeggio**: Notes may cycle through arpeggio patterns

### Critical Conversion Steps

1. Parse orderlist for each channel
2. For each orderlist entry:
   - Get transpose value
   - Get sequence number
   - Parse sequence bytes
   - Apply transpose to each note: `final_note = seq_note + transpose`
3. Extract and map all tables

### Common Mistakes

1. **Not applying transpose** - Results in wrong notes
2. **Including duration bytes as notes** - Bytes $80-$9F are durations, not notes
3. **Wrong table offsets** - Tables must be found by pattern matching, not fixed offsets

## Finding Tables in Unknown Files

Tables can be located by:

### Instrument Table
- Look for sequences of valid AD/SR values
- Entries should have reasonable wave pointers (small indices)
- Score based on validity of all fields

### Wave Table
- Look for pairs with valid waveforms ($00-$FF)
- Should have $7F jump markers for loops
- Note offsets typically $00-$7F or $80+ for recalc

### Sequence Pointers
- 16-bit pointers in sequence
- All should point within data range
- Typically grouped together

## Angular.sid Specific Data

### Extracted Values

```
Instruments: 16
Sequences: 70
Wave entries: 28
Pulse entries: 12
Filter entries: 1
```

### Sample Sequence 0

```
Address: $1B38
Bytes: 85 A0 30 91 A1 2C 89 A0 30 ...

Parsed:
  Duration=5, Inst=0, Note=C-4
  Duration=17, Inst=1, Note=E-3
  Duration=9, Inst=0, Note=C-4
  ...
```

### Sample Orderlist Channel 1

```
Address: $1AF2
Entries: (0,0) (0,2) (0,4) (0,6) ... LOOP
```

## References

- SID Factory II documentation
- HVSC (High Voltage SID Collection)
- Original Laxity player source code

## Version History

- 2025-11-23: Initial documentation based on Angular.sid analysis
