# SF2 Sequences and Orderlists - Detailed Technical Guide

**Version:** 1.0
**Date:** 2025-12-15
**Status:** Reference Guide

---

## Overview

Sequences and Orderlists form the backbone of music data in SF2 files:

- **Orderlists**: Define the song structure (which sequences play in what order)
- **Sequences**: Contain the actual note and command data that the player executes

Together, they create the complete musical composition.

---

## Table of Contents

1. [Orderlist Structure](#orderlist-structure)
2. [Sequence Structure](#sequence-structure)
3. [Note Format](#note-format)
4. [Commands](#commands)
5. [Memory Layout](#memory-layout)
6. [Editor Integration](#editor-integration)

---

## Orderlist Structure

### Purpose

The Orderlist is a list of sequence indices that defines the song structure.

```
OrderList Address (from Music Data Block):
[Seq 0] [Seq 1] [Seq 2] ... [Seq N] [END]

Each entry is 1 byte: 0x00-0x7F (sequence index), 0x7F (end)
```

### Value Meanings

| Value | Meaning | Purpose |
|-------|---------|---------|
| 0x00-0x7F | Sequence index 0-127 | Play this sequence |
| 0x7F | End of song / Loop point | Return to beginning or stop |
| 0x80-0xFE | Reserved | (not used in standard players) |

### Example Orderlist

```
OrderList at $0A80:
Byte Value  Sequence
---- -----  ----------
0    0x00   Intro (Seq 0)
1    0x01   Verse (Seq 1)
2    0x01   Verse again
3    0x02   Chorus (Seq 2)
4    0x01   Verse (back to Seq 1)
5    0x02   Chorus (Seq 2)
6    0x03   Bridge (Seq 3)
7    0x02   Final chorus (Seq 2)
8    0x7F   END - return to start
```

### Special Cases

**Loop Point:**
The first occurrence of 0x7F is the loop point. When playback reaches 0x7F, it jumps back to byte 0.

**Song Length:**
Count bytes until 0x7F to determine song structure length.

```python
def get_orderlist_length(orderlist_data):
    """Count entries until end marker"""
    for i, byte in enumerate(orderlist_data):
        if byte == 0x7F:
            return i
    return len(orderlist_data)
```

---

## Sequence Structure

### Overview

A sequence contains the actual musical data:
- Notes (pitch values)
- Commands (effects, volume, instrument changes)
- Timing (duration values)

```
Sequence Format (variable length):

[Note 0] [Command 0] [Param] [Duration 0]
[Note 1] [Command 1] [Param] [Duration 1]
...
[0x7F]  [END MARKER]
```

### Detailed Format

Each sequence entry can be 2-4 bytes:

```
Byte 0: Note Value
        0x00-0x6F   Note on (MIDI note 0-111)
        0x7E        Note off (--- in editor)
        0x7F        End/Jump marker

Byte 1: Command (if Note != 0x7F)
        0x00        No command
        0x01-0x0F   Standard commands
        0x10+       Extended commands

Byte 2: Command Parameter (if command requires it)
        Format depends on command type
        Usually 0x00-0xFF or 0x00-0x7F

Byte 3: Duration
        0x01-0x7F   Duration in ticks (1/4 to 32+ notes)
        0x00        Use default duration
        0x80+       Extended duration
```

### Note Values (MIDI Format)

SF2 uses standard MIDI note numbering:

```
Note Value   Note Name   Frequency
-----------  ---------   ---------
0x00         C-0         ~8.2 Hz
0x01         C#0         ~8.7 Hz
...
0x0C         C-1         ~16.4 Hz
0x18         C-2         ~32.7 Hz
0x24         C-3         ~65.4 Hz
0x30         C-4         ~130.8 Hz (Middle C in standard tuning)
0x3C         C-5         ~261.6 Hz
0x48         C-6         ~523.3 Hz
0x54         C-7         ~1047 Hz
0x5F         B-7         ~1976 Hz
0x6F         B-8         ~3951 Hz (highest MIDI note)

Formula: Frequency = 440 * 2^((MIDI - 69) / 12)
```

### Special Note Values

| Value | Meaning | Behavior |
|-------|---------|----------|
| 0x00-0x6F | Note On | Trigger new note with specified pitch |
| 0x7E | Note Off (Gate OFF) | Stop current note (--- in editor) |
| 0x7F | End / Jump | End sequence or jump command |

### Command Format

Commands modify note behavior or trigger effects:

```
Standard Command Layout:
[Command ID] [Parameter] [Duration]

Example Sequence Entry:
0x30       Note C-4
0x01       Change instrument command
0x05       To instrument 5
0x04       Duration: 4 ticks (1 note)
```

### Duration Values

Duration specifies how long the note plays:

```
Duration (Ticks)
-----------
0x01  = 1 tick  (~1/4 note)
0x02  = 2 ticks (~1/2 note)
0x04  = 4 ticks (1 note)
0x08  = 8 ticks (2 notes)
0x10  = 16 ticks (4 notes)
0x20  = 32 ticks (8 notes)

Tempo determines tick duration:
Tempo 6: 50 ticks/second (PAL)
        Frame-based sync: 1 frame = 1 tick at 50Hz
        1 note = 6 ticks = 120ms = 8.33 notes/second
```

---

## Note Format

### Complete Example Sequence

```
Raw bytes in memory (Music Data area):

Address  Byte   Decode
-------  ----   ------
$0A00    0x30   Note: C-4
$0A01    0x01   Command: Change instrument
$0A02    0x03   Parameter: Instrument 3
$0A03    0x04   Duration: 4 ticks

$0A04    0x32   Note: D-4 (C-4 + 2 semitones)
$0A05    0x00   Command: None
$0A06    0x04   Duration: 4 ticks

$0A07    0x7E   Note: OFF (--- in editor)
$0A08    0x00   Command: None
$0A09    0x04   Duration: 4 ticks (rest)

$0A0A    0x30   Note: C-4 (return)
$0A0B    0x00   Command: None
$0A0C    0x08   Duration: 8 ticks

$0A0D    0x7F   END MARKER
$0A0E    ...    Next sequence

Decoded Music:
C-4 (inst 3, 4 ticks) → D-4 (4 ticks) → Rest (4 ticks) → C-4 (8 ticks) → END
```

---

## Commands

### Command Set Reference

#### 0x01: Instrument Change

```
Format: [0x01] [Instrument#]

Example: 0x01 0x05 = Change to instrument 5
Parameter: 0x00-0x1F (up to 32 instruments)
```

#### 0x02: Volume

```
Format: [0x02] [Volume]

Example: 0x02 0x0F = Set volume to maximum
Parameter: 0x00-0x0F (16 volume levels)
```

#### 0x03: Arpeggio

```
Format: [0x03] [Semi1] [Semi2] [Semi3...]

Example: 0x03 0x00 0x04 0x07 = Major chord pattern
Plays: Base note → +4 semitones → +7 semitones → repeat

Typical Patterns:
  0x00 0x04 0x07  Major chord (C E G)
  0x00 0x03 0x07  Minor chord (C Eb G)
  0x00 0x05 0x09  Other patterns
```

#### 0x04: Portamento (Pitch Slide)

```
Format: [0x04] [TargetNote] [Speed]

Example: 0x04 0x30 0x02 = Slide to C-4, speed 2
Parameters:
  TargetNote: 0x00-0x6F (MIDI note)
  Speed: 0x01-0x7F (1=slow, 127=fast)
```

#### 0x05: Vibrato (Pitch Wobble)

```
Format: [0x05] [Depth] [Speed]

Example: 0x05 0x02 0x04 = Depth 2, Speed 4
Parameters:
  Depth: 0x00-0x7F (pitch deviation in semitones/100)
  Speed: 0x00-0x7F (wobble frequency)
```

#### 0x06: Tremolo (Volume Wobble)

```
Format: [0x06] [Depth] [Speed]

Example: 0x06 0x02 0x04 = Depth 2, Speed 4
Parameters:
  Depth: 0x00-0x0F (volume variation)
  Speed: 0x00-0x7F (wobble frequency)
```

#### 0x07: Duty (Pulse Width Sweep)

```
Format: [0x07] [TargetDuty] [Speed]

Example: 0x07 0x800 0x02 = Sweep to pulse 0x800, speed 2
Parameters:
  TargetDuty: 0x0000-0x0FFF (12-bit SID pulse register)
  Speed: 0x00-0x7F (sweep speed)
```

#### 0x08: Filter Sweep

```
Format: [0x08] [TargetFreq] [Speed]

Example: 0x08 0x100 0x02 = Sweep to cutoff 0x100, speed 2
Parameters:
  TargetFreq: 0x00-0x7FF (11-bit SID cutoff)
  Speed: 0x00-0x7F (sweep speed)
```

#### 0x09: Filter Resonance

```
Format: [0x09] [Resonance]

Example: 0x09 0x0F = Maximum resonance
Parameter: 0x00-0x0F (4-bit SID resonance)
```

#### 0x0A: Hard Restart (ADSR Trigger)

```
Format: [0x0A] (no parameters)

Effect: Force ADSR envelope restart on next note
Useful for: Creating sharp attack transients
```

#### 0x0B: Skip

```
Format: [0x0B] [SkipRows]

Example: 0x0B 0x10 = Skip forward 16 rows
Parameter: 0x00-0x7F (number of sequence entries to skip)
```

#### 0x0C: Delay

```
Format: [0x0C] [DelayTicks]

Example: 0x0C 0x08 = Delay note by 8 ticks
Parameter: 0x00-0x7F (ticks to delay note trigger)
```

#### 0x0D: Gate Control

```
Format: [0x0D] [State]

Example: 0x0D 0x01 = Gate ON
Parameter: 0x00 = Gate OFF, 0x01 = Gate ON

Effect: Manual gate control (overrides note on/off)
```

#### 0x0F: End/Return

```
Format: [0x0F] (no parameters)

Effect: End current sequence, return to orderlist
Or: Jump command with extended format
```

---

## Memory Layout

### SF2 Music Data Section

```
From Music Data Block (Block 0x05):

Offset Description
------ -----------
+0     Number of tracks (usually 1)
+2     OrderList address
+4     Sequence data start
+6     Sequence index table address
+8     Default sequence length
+9     Default tempo

Typical Layout Example (Broware):

OrderList Area ($0A80-$0A8F):
  00 00 01 02 7F        [Intro, Verse, Verse, Chorus, END]

Sequence Index Table ($0A90-$0ABF):
  $0A90-$0A9F   Pointers to Sequences 0-15
  Each pointer is 2 bytes (u16 LE)

Sequence Data ($0AA0 onward):
  Seq 0 (Intro):  [$0AA0] Note Note Command Duration Note OFF... [END]
  Seq 1 (Verse):  [$0AB0] Note Note Note Command... [END]
  Seq 2 (Chorus): [$0AC0] Note Command Command... [END]
  ...

Tables ($0B00+):
  Instruments, Wave, Pulse, Filter, Commands tables
```

### Sequence Pointer Table

```
Sequence Index Table Location: (from Music Data Block + 4)
Example: $0A90

Each sequence needs a pointer:

Address   Value    Meaning
-------   -----    -------
$0A90     0x00 0x0A  Seq 0 at $0A00
$0A92     0x10 0x0A  Seq 1 at $0A10
$0A94     0x20 0x0A  Seq 2 at $0A20
$0A96     0x30 0x0A  Seq 3 at $0A30
...

This allows orderlist entries to reference sequences by index:
OrderList[0] = 0x00 → Sequence Index Table[0] → Address $0A00
```

---

## Editor Integration

### SID Factory II Editor Display

In the SID Factory II editor, sequences appear as:

```
Orderlist View:
┌─ Song Order ─────────────────┐
│ 0: Sequence #0              │
│ 1: Sequence #1              │
│ 2: Sequence #1              │
│ 3: Sequence #2              │
│ 4: Sequence #1              │
└─────────────────────────────┘

Sequence Editor View (Sequence #1):
┌─ Sequence 1 ──────────────────────────────┐
│ Step  Note Cmd Param Duration Comment     │
├─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┤
│  0   C-4  .   -    4      Base note       │
│  1   D-4  .   -    4                      │
│  2   E-4  .   -    4                      │
│  3   --   .   -    4      Rest            │
│  4   G-4  01  03   8      Inst 3          │
│  5   A-4  05  02   4      Vibrato depth 2 │
│  6   G-4  .   -    4                      │
│  7   F#4  .   -    2                      │
│  8   [END]                                │
└────────────────────────────────────────┘
```

### Musical Notation to SF2 Mapping

```
SID Factory II Notation → SF2 Binary

C-4 (Note C-4, duration 1/4 note)
  → 0x30 0x00 0x04

D-4 with volume command
  → 0x32 0x02 0x0F 0x04

-- (Note off, rest 1 note)
  → 0x7E 0x00 0x04

Inst change to #5
  → 0x00 0x01 0x05 0x00

Portamento to G-4, speed 2
  → 0x00 0x04 0x43 0x02 0x04

Vibrato effect
  → 0x00 0x05 0x02 0x04 0x04
```

---

## Practical Example: "Twinkle Twinkle Little Star"

### Musical Score

```
Twinkle, Twinkle, Little Star
Melody (8 notes): C C G G A A G
Timing: 4 quarter notes each
```

### SF2 Binary Representation

```
Memory Address: $0AA0 (Sequence 0)

Offset  Byte   Meaning                Duration
------  ----   -------                --------
$0AA0   0x30   C-4 (Middle C)         1 note
$0AA1   0x00   No command
$0AA2   0x04   Duration: 4 ticks

$0AA3   0x30   C-4 again              1 note
$0AA4   0x00
$0AA5   0x04

$0AA6   0x43   G-4                    1 note
$0AA7   0x00
$0AA8   0x04

$0AA9   0x43   G-4 again              1 note
$0AAA   0x00
$0AAAB  0x04

$0AAC   0x45   A-4                    1 note
$0AAD   0x00
$0AAE   0x04

$0AAF   0x45   A-4 again              1 note
$0AB0   0x00
$0AB1   0x04

$0AB2   0x43   G-4                    1 note
$0AB3   0x00
$0AB4   0x04

$0AB5   0x7F   END MARKER
```

### Hexdump Output

```
00AA0: 30 00 04 30 00 04 43 00 04 43 00 04 45 00 04 45
00AB0: 00 04 43 00 04 7F ...
```

---

## Implementation Notes

### Sequence Parser

```python
def parse_sequence(data, address):
    """Parse a sequence from binary data"""
    sequence = []
    pos = address

    while pos < len(data):
        note = data[pos]

        if note == 0x7F:  # End marker
            break

        command = data[pos + 1]

        # Parse based on command
        if command == 0x00:
            # No command, just duration
            duration = data[pos + 2]
            sequence.append({
                'note': note,
                'command': None,
                'duration': duration
            })
            pos += 3
        elif command in [0x01, 0x02, 0x0B, 0x0C, 0x0D, 0x09]:
            # Single parameter commands
            param = data[pos + 2]
            duration = data[pos + 3]
            sequence.append({
                'note': note,
                'command': command,
                'param': param,
                'duration': duration
            })
            pos += 4
        elif command in [0x03, 0x04, 0x05, 0x06, 0x07, 0x08]:
            # Two parameter commands
            param1 = data[pos + 2]
            param2 = data[pos + 3]
            duration = data[pos + 4]
            sequence.append({
                'note': note,
                'command': command,
                'param1': param1,
                'param2': param2,
                'duration': duration
            })
            pos += 5
        else:
            pos += 4  # Skip unknown

    return sequence
```

---

## References

- SF2_FORMAT_COMPLETE_GUIDE.md - Related format documentation
- SID Factory II Manual - Official documentation
- MIDI Specification - Note numbering reference
- 6502 Assembly Reference - Player implementation details

---

Generated from SF2 Viewer implementation and SID Factory II source analysis.
