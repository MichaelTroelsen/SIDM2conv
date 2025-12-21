# SIDDUMP Deep-Dive Analysis

## Executive Summary

SIDDUMP v1.08 is a SID file emulation and analysis tool that uses a 6502 CPU emulator to run SID music code and capture register writes frame-by-frame. This document provides a comprehensive technical analysis of its architecture, output format, and integration strategies for extracting musical sequences.

**Key Capabilities:**
- Full 6502 CPU emulation with cycle-accurate timing
- SID register capture after each frame (50Hz PAL timing)
- Note detection via frequency table matching
- Delta tracking for vibrato/portamento detection
- Filter and master volume analysis

**Primary Use Case:** Converting live SID register states into editable music tracker data (SF2 format).

---

## 1. Architecture Overview

### 1.1 Component Structure

```
siddump.c (main program, 547 lines)
├── PSID/RSID header parsing
├── 64KB memory model (C64 emulation)
├── Frame loop (50 frames/second)
├── SID register capture (post-play routine)
├── Output formatting (pipe-delimited tables)
└── Note detection algorithm

cpu.c (6502 emulator, 1184 lines)
├── Full 6502 instruction set (256 opcodes)
├── Cycle-accurate timing tables
├── Illegal opcode support (limited)
├── Stack operations ($0100-$01FF)
└── Memory read/write macros
```

### 1.2 Data Structures

#### Channel State (CHANNEL struct)
```c
typedef struct
{
  unsigned short freq;    // SID frequency register (16-bit)
  unsigned short pulse;   // Pulse width (12-bit, 0x000-0xFFF)
  unsigned short adsr;    // ADSR envelope (16-bit: AD|SR)
  unsigned char wave;     // Waveform + gate control byte
  int note;               // Detected note number (0-95, -1=invalid)
} CHANNEL;
```

**State Tracking:**
- `chn[3]` - Current frame state (3 voices)
- `prevchn[3]` - Previous frame state (for delta detection)
- `prevchn2[3]` - Two frames back (for gate-on detection)

#### Filter State (FILTER struct)
```c
typedef struct
{
  unsigned short cutoff;  // 11-bit filter cutoff frequency
  unsigned char ctrl;     // Filter control (voice routing)
  unsigned char type;     // Filter type + master volume
} FILTER;
```

### 1.3 Execution Flow

```
1. Parse PSID Header
   ├── Load address (where to place code in C64 memory)
   ├── Init address (setup routine entry point)
   └── Play address (frame routine entry point)

2. Load SID Data
   └── Copy PRG data to mem[loadaddress...loadend]

3. Run Init Routine
   ├── initcpu(initaddress, subtune, 0, 0)
   ├── Execute until RTS/BRK (max 1,048,576 instructions)
   └── Handle SID detection wait loops ($d012 incrementing)

4. Frame Loop (repeat N times)
   ├── initcpu(playaddress, 0, 0, 0)
   ├── Execute until RTS/BRK
   ├── Read SID registers ($d400-$d418)
   ├── Detect notes via frequency matching
   ├── Format and print frame row
   └── Update state buffers

5. Output Results
   └── Pipe-delimited table to stdout
```

---

## 2. Output Format Analysis

### 2.1 Table Structure

**Header Format:**
```
| Frame | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | FCut RC Typ V |
+-------+---------------------------+---------------------------+---------------------------+---------------+
```

**Column Layout:**
1. Frame number (0-based)
2. Voice 1 data (27 chars)
3. Voice 2 data (27 chars)
4. Voice 3 data (27 chars)
5. Filter + volume (15 chars)

### 2.2 Voice Column Formats

SIDDUMP uses **two display modes** for each voice column:

#### Format 1: Note Event (New Note Triggered)
```
3426  G-5 C3  21 0F01 450
│     │   │   │  │    └─ Pulse width (3 hex)
│     │   │   │  └────── ADSR envelope (4 hex)
│     │   │   └───────── Waveform byte (2 hex)
│     │   └───────────── Absolute note (hex, |0x80)
│     └───────────────── Note name (C-0 to B-7)
└─────────────────────── Frequency (4 hex)
```

**Parsing Example:**
- Frequency: `0x3426` (13350 decimal)
- Note name: `G-5` (G in octave 5)
- Absolute: `0xC3` (bit 7 set = new note)
- Waveform: `0x21` (gate + pulse)
- ADSR: `0x0F01` (AD=$0F, SR=$01)
- Pulse: `0x450` (1104/4095 duty cycle)

#### Format 2: Delta (Frequency Change)
```
2BD6 (E-5 C0) .. .... 4A0
│     │   │   │  │    └─ Pulse width changed
│     │   │   │  └────── ADSR unchanged (....)
│     │   │   └───────── Waveform unchanged (..)
│     │   └───────────── Note detected (in parens)
│     └───────────────── Note name (in parens)
└─────────────────────── New frequency
```

**Parsing Example:**
- Frequency: `0x2BD6` (changed from previous)
- Note: `(E-5 C0)` - parentheses indicate slide/vibrato
- Waveform: `..` - no change
- ADSR: `....` - no change
- Pulse: `0x4A0` - changed

#### Format 3: No Change
```
....  ... ..  .. .... ...
```
All fields show dots - no SID register changes this frame.

### 2.3 Field Decoding Rules

| Field | Display | Meaning |
|-------|---------|---------|
| Freq | `XXXX` | Hex frequency (new value) |
| Freq | `....` | No change from previous |
| Note | `C-5` | New note detected (no parens) |
| Note | `(C-5 XX)` | Frequency changed, same note |
| Note | `... ..` | No note playing (wave < 0x10) |
| Abs | `XX` | Absolute note (0-95, or'd with 0x80) |
| WF | `XX` | Waveform byte changed |
| WF | `..` | Waveform unchanged |
| ADSR | `XXXX` | Envelope changed |
| ADSR | `....` | Envelope unchanged |
| Pul | `XXX` | Pulse width changed |
| Pul | `...` | Pulse unchanged |

### 2.4 Waveform Byte Decoding

The waveform byte (`$d404`, `$d40B`, `$d412`) has this bit layout:

```
Bit 7: Noise
Bit 6: Pulse
Bit 5: Sawtooth
Bit 4: Triangle
Bit 3: Test bit
Bit 2: Ring modulation
Bit 1: Sync
Bit 0: Gate (1=note on, 0=release)
```

**Common Values:**
- `0x00` - All off (voice silent)
- `0x01` - Triangle only, no gate
- `0x10` - Triangle, gate on
- `0x11` - Triangle + gate
- `0x21` - Pulse + gate
- `0x41` - Sawtooth + gate
- `0x81` - Noise + gate

**Note Detection Rule:**
Siddump only detects notes when `wave >= 0x10` (gate bit set or test bit set).

### 2.5 Filter Column Format

```
A000 F1 Low F
│    │  │   └─ Master volume (0-F)
│    │  └───── Filter type (Off/Low/Bnd/Hi/etc)
│    └──────── Filter control byte ($d417)
└───────────── Cutoff frequency (11-bit, $d415-$d416)
```

**Filter Type Strings:**
```c
const char *filtername[] = {
  "Off",  // 0b000 - Filter disabled
  "Low",  // 0b001 - Low-pass
  "Bnd",  // 0b010 - Band-pass
  "L+B",  // 0b011 - Low+Band
  "Hi ",  // 0b100 - High-pass
  "L+H",  // 0b101 - Low+High
  "B+H",  // 0b110 - Band+High
  "LBH"   // 0b111 - All three
};
```

---

## 3. Sequence Detection Algorithms

### 3.1 Note Event Detection

**Keyoff-Keyon Sequence Detection** (lines 374-379):
```c
// Detect gate-off followed by gate-on (new note trigger)
if (chn[c].wave >= 0x10)
{
  if ((chn[c].wave & 1) &&
      ((!(prevchn2[c].wave & 1)) || (prevchn2[c].wave < 0x10)))
    prevchn[c].note = -1;  // Mark as new note trigger
}
```

**Logic:**
1. Current frame has gate set (`wave >= 0x10`)
2. Current frame has gate bit 0 set (`wave & 1`)
3. Two frames ago, gate bit 0 was clear OR wave was below 0x10
4. Result: New note trigger detected

**Why This Works:**
- SID music players typically gate-off before gating-on a new note
- This prevents envelope restart artifacts
- Detection looks 2 frames back to catch the transition

### 3.2 Note Number Calculation

**Frequency Matching Algorithm** (lines 393-405):

```c
// Find closest frequency in table (96 notes, C-0 to B-7)
for (d = 0; d < 96; d++)
{
  int cmpfreq = freqtbllo[d] | (freqtblhi[d] << 8);
  int freq = chn[c].freq;

  if (abs(freq - cmpfreq) < dist)
  {
    dist = abs(freq - cmpfreq);
    // Favor the old note (sticky vibrato)
    if (d == prevchn[c].note)
      dist /= oldnotefactor;  // Default = 1
    chn[c].note = d;
  }
}
```

**Sticky Note Logic:**
- When frequency changes slightly (vibrato), keep same note
- `-o<factor>` option increases stickiness (e.g., `-o4`)
- Helps display vibrato as frequency deltas, not note changes

### 3.3 Sequence Building Strategy

To extract SF2 sequences from siddump output:

```python
def build_sequence(frames):
    """
    Convert siddump frames to SF2 sequence format.

    SF2 sequence entry: [instrument, command, note]
    Special values:
    - 0x7E in note = gate on (+++)
    - 0x80 in note = gate off (---)
    - 0x7F in note = end marker
    - 0x80+ in inst/cmd = no change (--)
    """
    sequence = []

    for frame in frames:
        # Parse siddump line
        freq, note_str, wave, adsr, pulse = parse_voice_column(frame)

        # Detect new note (no parentheses, wave has gate)
        if not note_str.startswith('(') and wave >= 0x10:
            note_num = parse_note(note_str)  # "G-5" -> 67

            # New note entry
            sequence.append([0x00, 0x00, note_num])

            # Gate on to sustain
            sequence.append([0x80, 0x80, 0x7E])

    # End marker
    sequence.append([0x00, 0x00, 0x7F])

    return sequence
```

---

## 4. Critical Implementation Details

### 4.1 Memory Layout

**C64 Memory Map:**
```
$0000-$00FF: Zero page (fast access)
$0100-$01FF: Stack (grows downward from $01FF)
$D400-$D418: SID registers (25 bytes)
$D011-$D012: VIC registers (for raster wait detection)
$FFFE-$FFFF: IRQ vector (when Kernal ROM enabled)
```

**SID Register Map:**
```c
// Voice 1: $d400-$d406 (7 bytes)
mem[0xd400 + 7*c]     // Frequency low
mem[0xd401 + 7*c]     // Frequency high
mem[0xd402 + 7*c]     // Pulse width low
mem[0xd403 + 7*c]     // Pulse width high (bits 0-3)
mem[0xd404 + 7*c]     // Waveform + control
mem[0xd405 + 7*c]     // Attack/Decay
mem[0xd406 + 7*c]     // Sustain/Release

// Filter: $d415-$d418 (4 bytes)
mem[0xd415]           // Cutoff low (bits 0-2)
mem[0xd416]           // Cutoff high (bits 3-10)
mem[0xd417]           // Filter control (voice routing)
mem[0xd418]           // Filter type (bits 4-6) + volume (bits 0-3)
```

### 4.2 Register Capture Points

**Post-Play Routine Capture** (lines 346-356):
```c
// After playroutine completes, read SID state
for (c = 0; c < 3; c++)
{
  chn[c].freq = mem[0xd400 + 7*c] | (mem[0xd401 + 7*c] << 8);
  chn[c].pulse = (mem[0xd402 + 7*c] | (mem[0xd403 + 7*c] << 8)) & 0xfff;
  chn[c].wave = mem[0xd404 + 7*c];
  chn[c].adsr = mem[0xd406 + 7*c] | (mem[0xd405 + 7*c] << 8);
}
```

**Key Point:** SID state is captured *after* the play routine exits, not during execution. This gives a single snapshot per frame.

### 4.3 Timing and Synchronization

**PAL Timing:**
- 50 frames per second (50Hz)
- Each frame = 20ms
- 312 raster lines per frame
- 63 cycles per raster line
- ~19656 cycles per frame

**CPU Cycle Profiling** (`-z` option):
```c
if (profiling)
{
  int cycles = cpucycles;
  int rasterlines = (cycles + 62) / 63;
  int badlines = ((cycles + 503) / 504);
  int rasterlinesbad = (badlines * 40 + cycles + 62) / 63;
  sprintf(&output[strlen(output)], "| %4d %02X %02X ",
          cycles, rasterlines, rasterlinesbad);
}
```

**Badline Correction:**
- Every 8th raster line is a "badline" (character data fetch)
- Badlines steal 40 cycles from CPU
- Affects playroutine performance calculations

### 4.4 Edge Cases and Limitations

#### Hard Restart Detection
Siddump **cannot** detect hard restart (HR) operations because:
- HR requires monitoring ADSR changes 2 frames *before* a note
- Siddump displays per-frame state, not multi-frame sequences
- HR is a player-side optimization, not visible in register dumps

**Solution:** Use static analysis of player code to detect HR patterns.

#### Illegal Opcodes
Limited support for illegal 6502 opcodes:
- `LAX` - Load A and X (opcodes 0xa3, 0xa7, 0xaf, 0xb3, 0xb7)
- `NOP` variants - 2-byte and 3-byte NOPs
- Most other illegals cause `Error: Unknown opcode` and exit

**Impact:** Some SID files with advanced player code may fail to run.

#### Init Routine Timeout
Max 1,048,576 instructions in init routine (line 286):
```c
if (instr > MAX_INSTR)
{
  printf("Warning: CPU executed a high number of instructions in init\n");
  break;
}
```

**Why:** Prevents infinite loops in broken SID files or advanced players with detection routines.

#### SID Detection Workaround
Lines 278-284 handle SID model detection loops:
```c
// Allow SID model detection (including $d011 wait) to eventually terminate
++mem[0xd012];  // Fake raster line incrementing
if (!mem[0xd012] || ((mem[0xd011] & 0x80) && mem[0xd012] >= 0x38))
{
  mem[0xd011] ^= 0x80;  // Toggle MSB
  mem[0xd012] = 0x00;   // Wrap to line 0
}
```

**Purpose:** Break out of `BIT $d011 / BPL *-3` style detection loops that wait for raster line changes.

---

## 5. Integration Guidelines

### 5.1 Best Practices for Parsing Output

#### Robust Line Parser
```python
import re

def parse_siddump_line(line):
    """Parse a siddump output line."""
    # Skip non-data lines
    if not line.startswith('|') or 'Frame' in line or '---' in line:
        return None

    # Split by pipes and strip
    parts = [p.strip() for p in line.split('|')]
    parts = [p for p in parts if p]  # Remove empty

    if len(parts) < 5:  # Need frame + 3 voices + filter
        return None

    try:
        frame = int(parts[0])
    except ValueError:
        return None

    # Parse each voice
    voices = []
    for i in range(3):
        voice_data = parse_voice_column(parts[i+1])
        voices.append(voice_data)

    # Parse filter
    filter_data = parse_filter_column(parts[4])

    return {
        'frame': frame,
        'voices': voices,
        'filter': filter_data
    }
```

#### Voice Column Parser
```python
def parse_voice_column(text):
    """
    Parse voice column supporting both formats:
    1. "3426  G-5 C3  21 0F01 450" (note event)
    2. "2BD6 (E-5 C0) .. .... 4A0" (delta)
    3. "....  ... ..  .. .... ..." (no change)
    """
    if text.startswith('....'):
        return None

    parts = text.split()
    if len(parts) < 4:
        return None

    # Frequency (always first)
    freq = int(parts[0], 16) if parts[0] != '....' else None

    # Detect format
    if parts[1].startswith('('):
        # Delta format: "(E-5 C0)"
        note_str = parts[1].strip('()')
        note_name = note_str.split()[0]  # "E-5"
        note_abs = int(note_str.split()[1], 16)  # "C0"
        is_delta = True
        wave_idx = 2
    else:
        # Note format: "G-5 C3"
        note_name = parts[1]
        note_abs = int(parts[2], 16)
        is_delta = False
        wave_idx = 3

    # Waveform
    wave = int(parts[wave_idx], 16) if parts[wave_idx] != '..' else None

    # ADSR
    adsr_str = parts[wave_idx + 1]
    adsr = int(adsr_str, 16) if adsr_str != '....' else None

    # Pulse
    pulse_str = parts[wave_idx + 2]
    pulse = int(pulse_str, 16) if pulse_str != '...' else None

    return {
        'freq': freq,
        'note_name': note_name,
        'note_abs': note_abs,
        'is_delta': is_delta,
        'wave': wave,
        'adsr': adsr,
        'pulse': pulse
    }
```

### 5.2 Extracting Musical Sequences

#### Sequence Building Algorithm
```python
def extract_sequences_per_voice(siddump_output):
    """
    Extract sequences for each voice from siddump.

    Returns: List of 3 voice sequences
    """
    frames = parse_all_frames(siddump_output)
    sequences = [[], [], []]  # 3 voices

    for voice_idx in range(3):
        current_pattern = []
        prev_note = None

        for frame in frames:
            voice = frame['voices'][voice_idx]
            if not voice:
                continue

            # Detect new note (not a delta)
            if not voice['is_delta'] and voice['wave'] and (voice['wave'] >= 0x10):
                # If we have a pattern, save it
                if current_pattern:
                    sequences[voice_idx].append(current_pattern)

                # Start new pattern
                note_num = note_name_to_midi(voice['note_name'])
                current_pattern = [{
                    'note': note_num,
                    'wave': voice['wave'],
                    'adsr': voice['adsr'],
                    'pulse': voice['pulse'],
                    'instrument': detect_instrument(voice['adsr'])
                }]
                prev_note = note_num

            elif voice['is_delta'] and prev_note:
                # Continuation (vibrato/slide)
                # Just track that note is sustaining
                current_pattern.append({
                    'note': prev_note,
                    'freq_delta': voice['freq'],
                    'wave': voice['wave'],
                    'adsr': voice['adsr'],
                    'pulse': voice['pulse']
                })

        # Save final pattern
        if current_pattern:
            sequences[voice_idx].append(current_pattern)

    return sequences
```

### 5.3 Mapping Siddump Data to SF2 Format

#### SF2 Sequence Format
```
SF2 uses 3-column format: [instrument, command, note]

Special note values:
- 0x00-0x7D: Note number (0=C-0, 119=B-9)
- 0x7E: Gate on (+++), sustain current note
- 0x7F: End marker, jump back to loop point
- 0x80: Gate off (---), trigger release

Special inst/cmd values:
- 0x00-0x7F: Valid instrument/command number
- 0x80+: No change (--)
```

#### Conversion Strategy
```python
def siddump_pattern_to_sf2_sequence(pattern):
    """
    Convert a siddump pattern to SF2 sequence.

    Pattern: List of note events with frame data
    Returns: List of [inst, cmd, note] entries
    """
    sequence = []
    NO_CHANGE = 0x80
    GATE_ON = 0x7E
    GATE_OFF = 0x80
    END = 0x7F

    for i, event in enumerate(pattern):
        note = event['note']
        inst = event.get('instrument', 0)

        # Add note trigger
        sequence.append([inst, 0x00, note])

        # Add gate on to sustain
        sequence.append([NO_CHANGE, NO_CHANGE, GATE_ON])

        # If next event is a new note, add gate off
        if i < len(pattern) - 1:
            next_event = pattern[i + 1]
            if 'note' in next_event and next_event['note'] != note:
                sequence.append([NO_CHANGE, NO_CHANGE, GATE_OFF])

    # End marker
    sequence.append([0x00, 0x00, END])

    return sequence
```

### 5.4 Common Pitfalls to Avoid

#### Pitfall 1: Ignoring Delta Format
**Problem:** Only parsing note events, missing frequency changes.

**Solution:** Track both formats and use delta information for effects (vibrato, portamento).

#### Pitfall 2: Not Handling Dots
**Problem:** Treating `....` or `..` as hex values.

**Solution:** Check for dots before parsing hex, return None or previous value.

#### Pitfall 3: Incorrect Note Detection
**Problem:** Treating all frequency changes as new notes.

**Solution:** Use the `is_delta` flag and check for parentheses in note display.

#### Pitfall 4: Missing End Markers
**Problem:** Sequences without 0x7F end marker cause player crashes.

**Solution:** Always append `[0x00, 0x00, 0x7F]` to every sequence.

#### Pitfall 5: Gate Logic Errors
**Problem:** Not adding gate on/off commands, causing stuck notes.

**Solution:** Follow note → gate-on → [sustain] → gate-off → next-note pattern.

---

## 6. Advanced Topics

### 6.1 Frequency Table Calibration

**Default Table** (lines 57-75):
```c
// PAL C64 frequency table for equal temperament
// Calculated as: freq = (note_hz * 16777216) / 985248
// Where 985248 is PAL CPU clock rate
```

**Recalibration** (`-c` and `-d` options):
```bash
# Recalibrate using middle C = 0x1200 instead of default 0x1168
siddump file.sid -c1200 -db0
```

**Use Case:** Some SID players use custom frequency tables (e.g., Microtonal music).

### 6.2 Low-Resolution Mode

**Purpose:** Display one row per note instead of every frame.

```bash
siddump file.sid -l -n4
# -l: Low-res mode
# -n4: Show every 4th frame
```

**Effect:**
- Reduces output size for long tunes
- Makes pattern structure more visible
- Hides vibrato and quick envelope changes

### 6.3 Pattern Spacing

**Purpose:** Visual grouping of notes into musical phrases.

```bash
siddump file.sid -n4 -p16
# -n4: Frame spacing (4 frames per row)
# -p16: Pattern spacing (16 rows per pattern)
```

**Output:**
```
+=======+===========================+...  # Pattern separator
| ... rows ...
+-------+---------------------------+...  # Note separator
```

---

## 7. Source Code Reference

### 7.1 Key Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `main()` | siddump.c:77 | Entry point, argument parsing, main loop |
| `runcpu()` | cpu.c:297 | Execute one 6502 instruction |
| `initcpu()` | cpu.c:286 | Initialize CPU state for routine call |
| Note detection | siddump.c:393-405 | Frequency-to-note matching |
| Gate detection | siddump.c:374-379 | Keyoff-keyon sequence |
| Output formatting | siddump.c:358-513 | Generate pipe-delimited table |

### 7.2 Important Constants

```c
// Limits
#define MAX_INSTR 0x100000    // Max instructions per routine (1M)

// CPU flags
#define FN 0x80  // Negative
#define FV 0x40  // Overflow
#define FB 0x10  // Break
#define FD 0x08  // Decimal
#define FI 0x04  // Interrupt disable
#define FZ 0x02  // Zero
#define FC 0x01  // Carry

// SID register offsets
#define SID_BASE 0xd400
#define SID_VOICE_SIZE 7       // Bytes per voice
#define SID_FILTER_BASE 0xd415

// Note constants
#define NUM_NOTES 96           // C-0 to B-7
#define MIDDLE_C 48            // C-4 in 0-95 scale
```

### 7.3 Addressing Modes

All implemented in `cpu.c` using macros:

```c
#define IMMEDIATE()   (LO())                              // #$nn
#define ZEROPAGE()    (LO() & 0xff)                       // $nn
#define ZEROPAGEX()   ((LO() + x) & 0xff)                 // $nn,X
#define ZEROPAGEY()   ((LO() + y) & 0xff)                 // $nn,Y
#define ABSOLUTE()    (LO() | (HI() << 8))                // $nnnn
#define ABSOLUTEX()   (((LO() | (HI() << 8)) + x) & 0xffff) // $nnnn,X
#define ABSOLUTEY()   (((LO() | (HI() << 8)) + y) & 0xffff) // $nnnn,Y
#define INDIRECTX()   (MEM((LO() + x) & 0xff) | ...)      // ($nn,X)
#define INDIRECTY()   (((MEM(LO()) | ...) + y) & 0xffff)  // ($nn),Y
```

---

## 8. Debugging and Troubleshooting

### 8.1 Common Errors

#### Error: Unknown opcode $XX at $XXXX
**Cause:** SID uses illegal 6502 opcode not implemented in siddump.

**Solution:**
1. Check if SID file is valid PSID/RSID
2. Try player-id.exe to identify player format
3. Some players require full 6502 emulation

#### Error: CPU executed abnormally high amount of instructions
**Cause:** Playroutine took >1M instructions (infinite loop or very complex code).

**Solution:**
1. Check if play address is correct
2. Some SIDs have broken headers
3. Try different subtune with `-a<n>` option

#### Warning: CPU executed a high number of instructions in init
**Cause:** Init routine is complex (decompression, table generation).

**Solution:** This is usually harmless - init completes, playback continues.

### 8.2 Validation Checks

```python
def validate_siddump_output(output):
    """Validate siddump output structure."""
    lines = output.split('\n')

    # Check for header
    if not any('| Frame |' in line for line in lines[:10]):
        raise ValueError("Missing siddump header")

    # Check for data rows
    data_rows = [l for l in lines if l.startswith('|') and 'Frame' not in l]
    if len(data_rows) < 10:
        raise ValueError("Too few data rows, playback may have failed")

    # Check format consistency
    for row in data_rows[:10]:
        parts = row.split('|')
        if len(parts) < 6:
            raise ValueError(f"Malformed row: {row}")

    return True
```

---

## 9. Performance Considerations

### 9.1 CPU Cycle Profiling

Using `-z` option shows per-frame CPU usage:

```
| ... | Cycl RL RB |
| ... | 4200 42 4A |
```

- **Cycl**: CPU cycles used
- **RL**: Raster lines (cycles/63)
- **RB**: Raster lines with badline correction

**Use Cases:**
- Optimize SID player code
- Ensure playroutine fits in frame budget (~19,000 cycles)
- Compare player efficiency

### 9.2 Memory Access Patterns

The `WRITE()` macro (commented out in cpu.c:31-34) can track memory writes:

```c
#define WRITE(address) { cpuwritemap[(address) >> 6] = 1; }
```

**Potential Use:** Track which 64-byte blocks are written to (player memory footprint).

---

## 10. Conclusion

### Key Takeaways

1. **Siddump is a passive observer** - It runs SID code and captures final register state per frame, not real-time changes.

2. **Two output formats** - Recognize note events vs deltas (parentheses are the key).

3. **Gate detection is crucial** - Look 2 frames back to detect note triggers.

4. **SF2 conversion requires post-processing** - Siddump output needs transformation to SF2 sequence format with gate commands.

5. **Edge cases matter** - Handle dots, missing data, and format variations robustly.

### Recommended Tools

```python
# Complete parsing stack
from sidm2.siddump_extractor import extract_sequences_from_siddump
from sidm2.siddump import extract_from_siddump

# Full pipeline
sequences, orderlists = extract_sequences_from_siddump('song.sid', seconds=30)
```

### Further Reading

- `docs/SF2_FORMAT_SPEC.md` - SF2 file format details
- `docs/STINSENS_PLAYER_DISASSEMBLY.md` - Laxity player analysis
- `CLAUDE.md` - Complete project documentation
- `sidm2/siddump_extractor.py` - Reference implementation

---

**Document Version:** 1.0
**Last Updated:** 2025-12-10
**Author:** Claude Code Analysis
**Source:** SIDDUMP v1.08 by Lasse Oorni and Stein Pedersen
