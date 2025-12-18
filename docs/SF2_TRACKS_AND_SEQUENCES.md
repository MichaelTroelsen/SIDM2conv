# SID Factory II - Tracks and Sequences Format

> **📄 Document Metadata**
> **Created From**: Web scraping of official SID Factory II tutorials
> **Source URLs**:
> - https://blog.chordian.net/2022/08/27/composing-in-sid-factory-ii-part-1-introduction/
> - https://blog.chordian.net/2022/08/27/composing-in-sid-factory-ii-part-2-sequences/
> - https://blog.chordian.net/2022/08/27/composing-in-sid-factory-ii-part-3-tracks/
>
> **Date Created**: 2025-12-17
> **Last Updated**: 2025-12-17
> **Update Check**: Recommended every 6 months

## Overview

SID Factory II uses a dual-level system:
1. **OrderList** - Defines which sequences play on each track
2. **Sequences** - Contain the actual musical data (notes, instruments, commands)

The editor leverages the Commodore 64's SID chip architecture with **three independent voices**, displayed as three parallel tracks in the editor.

**Key Characteristics:**
- **128 sequences maximum** - Each can be referenced by multiple tracks
- **1000+ rows per sequence** - Achieved via real-time packing technique
- **Independent track lengths** - Tracks don't have to be aligned
- **Flexible looping** - Each track can loop independently

---

## OrderList Format

### Entry Structure: **XXYY** (4 hex characters)

- **XX** = Transpose value (semitone offset)
  - Range: `80` (-32 semitones) to `BF` (+31 semitones)
  - `A0` = No transpose (default, 0 semitones)
  - `94` = One octave lower (-12 semitones)
  - `AC` = One octave higher (+12 semitones)
  - `A3` = Transpose up 3 semitones
  - Formula: Transpose = (XX - 0xA0) semitones

- **YY** = Sequence number (00-7F, 0-127 decimal)
  - Points to which sequence to play
  - Same sequence can be used with different transpositions

### Example OrderList Entries

```
A00A  ← Transpose A0 (default), Sequence 0A (10)
AC15  ← Transpose AC (+12 semitones = +1 octave), Sequence 15 (21)
9408  ← Transpose 94 (-12 semitones = -1 octave), Sequence 08 (8)
A301  ← Transpose A3 (+3 semitones), Sequence 01 (1)
```

**Usage:**
- Allows sequence reuse at different pitches
- Conserves memory by sharing sequence data
- Common for basslines and melodic patterns

---

## Sequence Entry Format

### Structure: **AA BB CCC** (3 columns)

- **AA** = Instrument (2 hex chars)
  - `00-1F` = Instrument number (displayed as `00`, `0A`, `1F`, etc.)
  - `--` = No instrument change (continue using previous)
  - **See**: `SF2_INSTRUMENTS_REFERENCE.md` for complete instrument documentation

- **BB** = Command (2 hex chars)
  - `00-3F` = Command number (displayed as `00`, `02`, `12`, etc.)
  - `--` = No command

- **CCC** = Note (3-4 characters)
  - Musical notes: `C-0` through `B-9` (e.g., `F-3`, `D#3`, `A-4`)
  - `+++` = Gate on (sustain/hold previous note)
  - `---` = Gate off (silence)
  - `END` = End of sequence marker

### Field Widths

- Instrument: **2 characters** (e.g., `0A`, `--`)
- Command: **2 characters** (e.g., `02`, `--`)
- Note: **3-4 characters** (e.g., `F-3`, `D#3`, `+++`)

---

## Common Commands

Based on SF2 format:

| Code | Name  | Description |
|------|-------|-------------|
| 01   | Inst  | Set instrument |
| 02   | Vol   | Volume change |
| 03   | Arp   | Arpeggio |
| 04   | Port  | Portamento |
| 05   | Vib   | Vibrato |
| 06   | Trem  | Tremolo |
| 07   | Duty  | Duty cycle |
| 08   | Filt  | Filter |
| 09   | Res   | Resonance |
| 0A   | HRst  | Hard restart |
| 0B   | Skip  | Skip |
| 0C   | Dly   | Delay |
| 0D   | Gate  | Gate control |

---

## Complete Example with Interpretation

### Reference Data

```
Track 3
a00a 0b -- F-3
     -- -- +++
     -- 02 +++
     -- -- +++
     -- -- F-3
```

### Line-by-Line Interpretation

**Line 1: `a00a 0b -- F-3`**
- **OrderList Entry**: `a00a`
  - Transpose: `a0` (default, no transpose)
  - Sequence: `0a` (sequence number 10)
- **Sequence Data**: `0b -- F-3`
  - Instrument: `0b` (instrument 11)
  - Command: `--` (no command)
  - Note: `F-3` (F in octave 3)
- **Action**: Set instrument 11, play note F-3

**Line 2: `     -- -- +++`**
- **OrderList**: (blank, continues previous sequence)
- **Sequence Data**: `-- -- +++`
  - Instrument: `--` (no change, keep instrument 11)
  - Command: `--` (no command)
  - Note: `+++` (gate on, sustain note)
- **Action**: Keep note F-3 playing (sustain)

**Line 3: `     -- 02 +++`**
- **OrderList**: (blank, continues)
- **Sequence Data**: `-- 02 +++`
  - Instrument: `--` (no change)
  - Command: `02` (Volume command)
  - Note: `+++` (gate on)
- **Action**: Apply volume command while sustaining note

**Line 4: `     -- -- +++`**
- **OrderList**: (blank, continues)
- **Sequence Data**: `-- -- +++`
  - Instrument: `--` (no change)
  - Command: `--` (no command)
  - Note: `+++` (gate on)
- **Action**: Continue sustaining note

**Line 5: `     -- -- F-3`**
- **OrderList**: (blank, continues)
- **Sequence Data**: `-- -- F-3`
  - Instrument: `--` (no change)
  - Command: `--` (no command)
  - Note: `F-3` (retrigger)
- **Action**: Retrigger note F-3 (play again)

---

## Musical Pattern Explanation

This sequence demonstrates a common SID music pattern:

```
Step 0: Trigger note F-3 with instrument
Step 1: Sustain (gate on)
Step 2: Apply effect while sustaining
Step 3: Continue sustaining
Step 4: Retrigger same note
```

### Gate Control

- **`+++` (Gate On)**: Keeps the note playing/sustaining
  - Does NOT retrigger the note
  - Maintains current pitch and envelope state
  - Used to create held notes

- **Note Name (e.g., `F-3`)**: Triggers/retriggers a note
  - Starts attack phase of ADSR envelope
  - Can be same or different pitch
  - Resets envelope even if same note

- **`---` (Gate Off)**: Silences the note
  - Triggers release phase of envelope
  - Used for gaps/rests

---

## Track System

### 3-Track Parallel Format

SID Factory II displays 3 tracks in parallel (one per SID voice):

```
      Track 1           Track 2           Track 3
Step  In Cmd Note       In Cmd Note       In Cmd Note
----  -- --- ----       -- --- ----       -- --- ----
0000  0A 02  F-3        -- --  C-3        0B --  A-4
0001  -- --  +++        -- --  +++        -- --  +++
0002  -- 05  +++        -- 02  E-3        -- 02  +++
```

### Storage Format

Sequences are stored with 3 tracks interleaved:
- **Entry 0, 1, 2** = Track 1, Track 2, Track 3 at Step 0
- **Entry 3, 4, 5** = Track 1, Track 2, Track 3 at Step 1
- **Entry 6, 7, 8** = Track 1, Track 2, Track 3 at Step 2
- etc.

To extract Track 3:
- Take entries at indices: 2, 5, 8, 11, 14, ... (every 3rd starting from 2)

---

## Sequence Stacking System

SID Factory II uses **contiguous sequence stacking** (like JCH editor and CheeseCutter):

- All sequences in each voice can have different lengths
- Sequences are stacked on top of each other
- Like "perfect Tetris" - sequences fit together without gaps
- Independent lengths per track allow complex arrangements

---

## Display Format in SF2 Viewer

### Sequence Tab Format

```
      Track 1           Track 2           Track 3
Step  In Cmd Note       In Cmd Note       In Cmd Note
----  -- --- ----       -- --- ----       -- --- ----
0000  0A 02  F-3        -- --  C-3        0B --  A-4
0001  -- --  +++        -- --  +++        -- --  +++
0002  -- 05  +++        -- 02  E-3        -- 02  +++
0003  -- --  G-3        -- --  +++        -- --  D-4
```

### Column Specifications

- **Step**: 4 hex digits (0000-FFFF)
- **In** (Instrument): 2 characters (`--` or `00-1F`)
- **Cmd** (Command): 2 characters (`--` or `00-3F`)
- **Note**: 3-4 characters (`C-0` to `B-9`, `+++`, `---`, `END`)

---

## Parsing Rules

### Reference File Format

Lines can be:

1. **With OrderList prefix**: `a00a 0b -- F-3`
   - Parse as: `XXYY AA BB CCC`
   - Extract: OrderList entry (`a00a`), Instrument (`0b`), Command (`--`), Note (`F-3`)

2. **Without OrderList prefix**: `     -- -- +++`
   - Parse as: `AA BB CCC`
   - Extract: Instrument (`--`), Command (`--`), Note (`+++`)

3. **Header**: `Track 3`
   - Skip (metadata)

4. **Empty lines**
   - Skip

### Normalization

When comparing data:
- Convert to lowercase for case-insensitive comparison
- Strip extra whitespace
- `--` is equivalent to "no change" or "empty" field

---

## Implementation Notes

### SequenceEntry Structure

```python
@dataclass
class SequenceEntry:
    note: int        # 0x00-0x6F (notes), 0x7E (+++), 0x7F (END)
    instrument: int  # 0x80=no change, 0xA0-0xBF=instrument
    command: int     # 0x80=no change, 0xC0-0xFF=command
    param1: int      # Command parameter 1
    param2: int      # Command parameter 2
    duration: int    # Duration in ticks
```

### Display Methods

```python
entry.instrument_display()  # Returns: "--" or "0A"
entry.command_display()     # Returns: "--" or "02"
entry.note_name()          # Returns: "F-3", "+++", "---", "END"
```

### Raw Value Encoding

- **Instrument**:
  - `0x80` = No change (`--`)
  - `0x90` = Tie note
  - `0xA0-0xBF` = Instrument (index = value & 0x1F)

- **Command**:
  - `0x80` = No change (`--`)
  - `0xC0-0xFF` = Command (index = value & 0x3F)

- **Note**:
  - `0x00` = Gate off (`---`)
  - `0x01-0x7D` = Musical notes (MIDI-style)
  - `0x7E` = Gate on (`+++`)
  - `0x7F` = End marker (`END`)

---

## Summary

**Key Concepts:**

1. **OrderList** = Which sequences play (XXYY format)
2. **Sequences** = Musical data (AA BB CCC format)
3. **3 Tracks** = 3 parallel voices for SID chip
4. **Gate Control** = `+++` sustains, note names trigger/retrigger
5. **Stacking** = Sequences stack contiguously, independent lengths

**Format Widths:**

- OrderList entry: 4 chars (XXYY)
- Instrument: 2 chars (AA)
- Command: 2 chars (BB)
- Note: 3-4 chars (CCC)

**Special Values:**

- `--` = No change/empty
- `+++` = Gate on (sustain)
- `---` = Gate off (silence)
- `A0` = Default transpose

---

## Track Operations

### Navigation

- **Tab** - Move to next track (Track 1 → 2 → 3 → 1)
- **Shift+Tab** - Move to previous track (Track 3 → 2 → 1 → 3)
- Position preserved when switching tracks

### Track Toggling

Isolate tracks during composition:
- **Ctrl+1** - Toggle Track 1 on/off
- **Ctrl+2** - Toggle Track 2 on/off
- **Ctrl+3** - Toggle Track 3 on/off

Useful for:
- Focusing on specific voice arrangements
- Checking individual track balance
- Debugging musical issues

### Sequence Management

- **Ctrl+D** - Duplicate current sequence
- **Ctrl+C** - Copy sequence data
- **Ctrl+V** - Paste sequence data
- **F5** - Resize sequence (set row count)
- **Ctrl+Z** - Undo
- **Ctrl+Y** - Redo

### Common Patterns

**Shared Sequences:**
```
Track 1: A00A  (seq 0A, default transpose)
Track 2: A00A  (same sequence, shared)
Track 3: AC0A  (same sequence, +1 octave)
```

**Independent Sequences:**
```
Track 1: A001  (seq 01 - bassline)
Track 2: A002  (seq 02 - chords)
Track 3: A003  (seq 03 - melody)
```

**Loop Patterns:**
Track 1 can loop back while Track 2 and 3 continue forward, enabling:
- Repeating basslines under changing melodies
- Drum patterns under chord progressions
- Creative layering before eventual sync

---

## Typical Sequence Sizes

Based on SID Factory II usage patterns:

- **Small sequences**: 16-32 rows (4-8 bars at 4 rows/bar)
- **Medium sequences**: 32-64 rows (8-16 bars)
- **Large sequences**: 64-128 rows (16-32 bars)
- **Maximum**: 1000+ rows (via real-time packing)

Common row counts:
- `020` hex = 32 rows (default for short patterns)
- `040` hex = 64 rows (default for longer patterns)
- `080` hex = 128 rows (for complex arrangements)

---

## Sources and References

**Official SID Factory II Resources:**
- [Tutorial Part 1 - Introduction](https://blog.chordian.net/2022/08/27/composing-in-sid-factory-ii-part-1-introduction/)
- [Tutorial Part 2 - Sequences](https://blog.chordian.net/2022/08/27/composing-in-sid-factory-ii-part-2-sequences/)
- [Tutorial Part 3 - Tracks](https://blog.chordian.net/2022/08/27/composing-in-sid-factory-ii-part-3-tracks/)
- [Tutorial Part 4 - Instruments](https://blog.chordian.net/2022/08/27/composing-in-sid-factory-ii-part-4-instruments/)
- [SID Factory II Main Site](https://blog.chordian.net/sf2/)
- [GitHub Repository](https://github.com/Chordian/sidfactory2)

---

**Date Created**: 2025-12-17
**Last Updated**: 2025-12-17
**Reference**: SID Factory II Editor (Official Tutorials)
**Related Files**: `track_3.txt`, `compare_track3_v2.py`, `sf2_viewer_gui.py`
**MCP Resources**: mcp-c64 (tdz-c64-knowledge)
