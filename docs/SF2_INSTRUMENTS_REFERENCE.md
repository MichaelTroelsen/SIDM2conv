# SID Factory II - Instruments Reference

> **📄 Document Metadata**
> **Created From**: Web scraping of official SID Factory II tutorials
> **Source URLs**:
> - https://blog.chordian.net/2022/08/27/composing-in-sid-factory-ii-part-1-introduction/
> - https://blog.chordian.net/2022/08/27/composing-in-sid-factory-ii-part-4-instruments/
>
> **Date Created**: 2025-12-17
> **Last Updated**: 2025-12-17
> **Update Check**: Recommended every 6 months

## Overview

Instruments in SID Factory II define how notes sound on the Commodore 64's SID chip. Each instrument is a 6-byte structure that controls envelope, waveform, and effects.

**Key Concept**: Instruments are referenced by sequences via the instrument column (leftmost in sequence editor).

---

## Instrument Structure (6 Bytes)

Each instrument consists of exactly **6 bytes**:

```
Byte 1: Attack/Decay (ADSR high nibble, low nibble)
Byte 2: Sustain/Release (ADSR high nibble, low nibble)
Byte 3: Control Flags + HR table pointer
Byte 4: Pulse width table index
Byte 5: Filter table index
Byte 6: Wave table starting index
```

### Example Instrument

```
Instrument 02: 00 c8 80 00 00 05
```

Breaking down each byte:
- **Byte 1**: `00` = Attack 0 (instant), Decay 0 (instant)
- **Byte 2**: `c8` = Sustain C (loud), Release 8 (medium fade)
- **Byte 3**: `80` = Hard Restart enabled (bit 7 = 1), HR table pointer 0
- **Byte 4**: `00` = No pulse width table
- **Byte 5**: `00` = No filter table
- **Byte 6**: `05` = Wave table starts at line 05

---

## ADSR Envelope System

**ADSR** = Attack, Decay, Sustain, Release (volume envelope over time)

### Byte 1: Attack/Decay

- **High nibble (bits 4-7)**: Attack (0-F)
- **Low nibble (bits 0-3)**: Decay (0-F)

**Example**: `04` = Attack 0, Decay 4

### Byte 2: Sustain/Release

- **High nibble (bits 4-7)**: Sustain (0-F)
- **Low nibble (bits 0-3)**: Release (0-F)

**Example**: `69` = Sustain 6, Release 9

### ADSR Parameters

| Parameter | Range | Description |
|-----------|-------|-------------|
| **Attack (A)** | 0-F | Time to reach maximum volume from silence |
| | 0 | Nearly instant (2ms) |
| | F | Very slow (~8 seconds) |
| **Decay (D)** | 0-F | Time from max volume to sustain level |
| | 0 | Instant |
| | F | Very slow (~24 seconds) |
| **Sustain (S)** | 0-F | Held volume level while note plays |
| | 0 | Silent |
| | F | Maximum volume |
| **Release (R)** | 0-F | Fade time from sustain to silence after gate-off |
| | 0 | Instant cut |
| | F | Very slow (~24 seconds) |

### ADSR Behavior

**Gate On** (note triggers like `C-5`):
1. Attack phase: Volume rises from 0 to max
2. Decay phase: Volume falls from max to sustain level
3. Sustain phase: Volume holds at sustain level while note plays

**Gate Off** (silence trigger `---`):
- SID chip immediately abandons attack/decay phases
- Jumps directly to release phase
- Volume fades from current level to silence

**Sustain Lines** (`+++`):
- Keep gate on, maintain sustain phase
- Do NOT retrigger envelope
- Continue holding current ADSR state

---

## Byte 3: Control Flags & HR Pointer

Byte 3 is a bit field with special flags and a table pointer:

```
Bit 7 (80): Hard Restart enable
Bit 6 (40): Unused
Bit 5 (20): Unused
Bit 4 (10): Test Bit / Oscillator Reset
Bits 0-3 (0-F): Hard Restart table pointer
```

### Flag Values

| Value | Meaning |
|-------|---------|
| 00 | No flags, no HR table |
| 10 | Test bit enabled |
| 80 | Hard Restart enabled, HR table pointer 0 |
| 90 | Hard Restart + Test Bit enabled |
| 8F | Hard Restart enabled, HR table pointer F |

### Combining Flags

To combine multiple flags, add the hex values:
- Hard Restart (80) + Test Bit (10) = 90
- Hard Restart (80) + HR pointer 3 = 83

### Bit Editor

Press **Shift+Enter** while editing Byte 3 to open a GUI bit selector for easier flag manipulation.

---

## Hard Restart (HR) System

**Purpose**: Prevents ADSR envelope "stumbling" during rapid note sequences by resetting the envelope cleanly.

### How It Works

When Hard Restart is enabled:
1. Approximately **2 ticks before** the next note triggers
2. Gate turns off temporarily
3. Alternate ADSR values (from HR table) are applied
4. Creates a brief "staccato" effect
5. Ensures clean envelope retriggering on next note

### Enabling Hard Restart

**Byte 3**: Set bit 7 (add `80` hex)
- Example: `00` → `80` (HR enabled, pointer 0)
- Example: `00` → `83` (HR enabled, pointer 3)

### HR Table Pointer

**Lower nibble of Byte 3** (bits 0-3) points to HR ADSR values:
- `80` = HR enabled, use HR table entry 0
- `81` = HR enabled, use HR table entry 1
- `8F` = HR enabled, use HR table entry F

### Default HR ADSR

**Recommended**: `0F 00`
- Attack F (very slow) + Decay 0 (instant)
- Sustain 0 (silent) + Release 0 (instant)
- This combination works well for most cases

### When to Use HR

Use Hard Restart when:
- Playing rapid note sequences
- Retriggering same note repeatedly
- Envelope not resetting cleanly
- Notes sound "slurred" or "muddy"

Skip Hard Restart when:
- Using slow attack/decay for pads
- Intentional legato effects desired
- Single long sustained notes

---

## Test Bit / Oscillator Reset

**Purpose**: Unlocks the noise waveform (81) when combined with incompatible waveforms.

### The Problem

Noise waveform (`81`) cannot combine with other waveforms:
- Attempting combinations locks the SID oscillator
- Results in silence or stuck tones
- Requires oscillator reset to unlock

### The Solution

**Byte 3**: Set bit 4 (add `10` hex)
- Activates test bit briefly at note start
- Prevents oscillator lockup
- No audible downsides

### Enabling Test Bit

- Add `10` to Byte 3: `00` → `10`
- Or combine with HR: `80` → `90`
- Use **Shift+Enter** bit editor for easy toggling

### When to Use Test Bit

**Always use when**:
- Using noise waveform (81)
- Switching between noise and other waveforms
- Creating percussion/drum sounds
- Want guaranteed oscillator stability

**Safe to leave permanently enabled** - no negative effects on other waveforms.

---

## Waveforms

The SID chip has 4 primary waveforms, each with distinct sonic characteristics.

### Primary Waveforms

| Value | Waveform | Characteristics | Best For |
|-------|----------|-----------------|----------|
| **11** | Triangle | Subdued, sine-like, mellow | Basslines, sub-bass |
| **21** | Sawtooth | Bright, rich harmonics | Leads, strings, brass |
| **41** | Pulse/Square | Modulation-capable, hollow | Chords, arpeggios, bass |
| **81** | Noise | White noise, chaotic | Drums, percussion, effects |

### Waveform Details

**Triangle (11)**:
- Closest to pure sine wave
- Soft, warm tone
- Minimal harmonic content
- Excellent for bass frequencies

**Sawtooth (21)**:
- Richest harmonic content
- Bright, buzzy character
- Classic analog synth sound
- Works well for melodic leads

**Pulse (41)**:
- Requires pulse width modulation
- Defaults to zero pulse width = **SILENT**
- Must use pulse table (Byte 4) or will produce no sound
- Hollow, woody character when modulated

**Noise (81)**:
- Random white noise
- No pitch control (always same "frequency")
- Perfect for hi-hats, snares, crashes
- Cannot combine with other waveforms safely

### Combined Waveforms (8580 SID Only)

**Warning**: These sound different on 6581 vs 8580 chips!

| Value | Combination | 8580 Character | 6581 Behavior |
|-------|-------------|----------------|---------------|
| **31** | Triangle + Sawtooth | Thin, nasal | Different timbre |
| **51** | Triangle + Pulse | Audible on both | Audible on both |
| **61** | Sawtooth + Pulse | Organ-like, hollow | Different timbre |
| **71** | Tri + Saw + Pulse | Very thin, metallic | Different timbre |

**Important**: Combined waveforms are **8580-specific**. Use caution if targeting 6581 compatibility.

### Waveform Incompatibility

**NEVER combine noise with other waveforms**:
- `81 + 11` = Oscillator lockup
- `81 + 21` = Oscillator lockup
- `81 + 41` = Oscillator lockup

**Solution**: Use Test Bit (Byte 3, bit 4 = `10`) to reset oscillator.

---

## Wave Tables

Wave tables allow **per-tick waveform changes** and **transposition effects**.

### Wave Table Structure

Each wave table line contains **2 bytes**:

```
Byte 1: Waveform value (11, 21, 41, 81) OR loop marker (7F)
Byte 2: Semitone offset from played note OR static frequency
```

### Example Wave Table

```
Line 05: 81 ca    (Noise, static frequency CA)
Line 06: 41 a8    (Pulse, static frequency A8)
Line 07: 41 a4    (Pulse, static frequency A4)
Line 08: 80 ca    (Noise gated off, static freq CA)
Line 09: 7f 08    (Loop back to line 08)
```

### Byte 1: Waveform or Loop

**Waveform values** (00-7F):
- `11` = Triangle
- `21` = Sawtooth
- `41` = Pulse
- `81` = Noise
- Combined values (31, 51, 61, 71)

**Special values**:
- `7F` = Loop marker (jump to line specified in Byte 2)
- `80` = Gate off (trigger release phase)

### Byte 2: Transposition or Static Frequency

**Relative transposition** (00-7F):
- `00` = No transposition (play note as-is)
- `01-7F` = Semitone offset from played note
- `0C` = +12 semitones (one octave up)
- `F4` = -12 semitones (one octave down, wraps around)

**Static frequency** (80-DF, bit 7 set):
- Ignores played note entirely
- Plays fixed frequency regardless of sequence
- `CA`, `A8`, `A4` = Fixed pitches for drums
- **Side effect**: Effect commands (slide, vibrato) won't work

### Wave Table Processing

**Playback**:
1. Player reads one wave table line per tick
2. Applies waveform and transposition
3. Advances to next line
4. Continues until loop marker (`7F`)
5. Jumps to line specified in loop's Byte 2

**Example Flow**:
```
Tick 0: Line 05 (81 ca) - Noise at pitch CA
Tick 1: Line 06 (41 a8) - Pulse at pitch A8
Tick 2: Line 07 (41 a4) - Pulse at pitch A4
Tick 3: Line 08 (80 ca) - Gate off
Tick 4: Line 09 (7f 08) - Loop to line 08
Tick 5: Line 08 (80 ca) - Gate off (repeats)
```

### Loop Command

**Format**: `7F [target_line]`

**Examples**:
- `7F 00` = Loop to line 00 (beginning)
- `7F 05` = Loop to line 05
- `7F 08` = Loop to line 08 (current-1, creates sustain)

**Usage**:
- Sustain waveform indefinitely
- Create repeating patterns
- Return to earlier position for variation

---

## Pulse Width Tables

Pulse waveform (`41`) requires pulse width modulation to produce sound.

### Pulse Width Format

**3 bytes per entry** defining pulse width envelope over time.

### Example Pulse Table

```
Entry 00: 84 00 00
Entry 01: 7F 00 00
```

### Pulse Width Values

Pulse width is a **12-bit value** (0-4095) controlling duty cycle:
- `000` hex = 0% duty cycle (silent)
- `800` hex = 50% duty cycle (square wave)
- `FFF` hex = 100% duty cycle (thin sound)

**Modulating pulse width** creates the characteristic "phasing" sound of pulse waveforms.

### When to Use Pulse Tables

- When using pulse waveform (`41`)
- For classic square wave sounds
- For PWM (Pulse Width Modulation) effects
- For rich, evolving timbres

---

## Practical Example: Snare Drum

Complete instrument definition for a snare drum sound:

### Instrument Table Entry

```
Instrument 02: 00 c8 80 00 00 05
```

**Breakdown**:
- `00` = Attack 0 (instant), Decay 0 (instant)
- `c8` = Sustain C (loud), Release 8 (medium fade)
- `80` = Hard Restart enabled, HR pointer 0
- `00` = No pulse table
- `00` = No filter table
- `05` = Wave table starts at line 05

### Wave Table (Lines 05-09)

```
05: 81 ca    (Noise - high pitch, static frequency)
06: 41 a8    (Pulse - medium pitch, static)
07: 41 a4    (Pulse - slightly lower pitch, static)
08: 80 ca    (Gate off to trigger release)
09: 7f 08    (Loop to line 08, sustain release)
```

**How It Sounds**:
1. **Tick 0** (line 05): Burst of high-pitched noise (snare "snap")
2. **Tick 1** (line 06): Switch to pulse at medium pitch (snare "body")
3. **Tick 2** (line 07): Slightly lower pulse (pitch drop)
4. **Tick 3** (line 08): Gate off, starts release phase (fade out)
5. **Tick 4+** (line 09): Loop sustains release until next note

**Why Static Frequencies**:
- Ensures drum sounds identical regardless of note played in sequence
- `C-3` or `A#5` will produce same snare pitch
- Prevents melodic variation in percussion

---

## Keyboard Shortcuts

### Navigation

- **Alt+I** - Jump to Instrument table
- **Alt+W** - Jump to Wave table
- **Alt+P** - Jump to Pulse table
- **Alt+F** - Jump to Filter table
- **Ctrl+Enter** - Jump from instrument Byte 6 to corresponding wave table line

### Testing

- **Shift+Q** - Test Track 1 instrument
- **Shift+W** - Test Track 2 instrument
- **Shift+E** - Test Track 3 instrument

### Editing

- **Shift+Enter** - Bit editor for Byte 3 (flags)
- **F3/F4** - Adjust octave
- **Ctrl+D** - Duplicate instrument
- **Ctrl+C/V** - Copy/paste

---

## Storage Efficiency Tips

### Use Gate-On Lines

**Instead of**:
```
C-3   (gate on)
---   (gate off)
C-3   (gate on again)
```

**Use**:
```
C-3   (initial trigger)
+++   (sustain)
C-3   (retrigger)
```

**Benefits**:
- Saves packer bytes during sequence compression
- Minimizes file size
- Cleaner ADSR envelope behavior
- Faster playback processing

### Reuse Instruments

- Share instruments across sequences
- Use transposition for variation
- Create instrument "families" with subtle differences

---

## Common ADSR Patterns

### Quick Pluck (0469)

```
Byte 1: 04 (Attack 0, Decay 4)
Byte 2: 69 (Sustain 6, Release 9)
```

**Character**: Fast attack, medium decay, loud sustain, medium release
**Use**: Plucked strings, guitar, harp

### Slow Pad (8AC8)

```
Byte 1: 8A (Attack 8, Decay A)
Byte 2: C8 (Sustain C, Release 8)
```

**Character**: Slow attack, slow decay, loud sustain, medium release
**Use**: Pads, strings, atmospheric sounds

### Percussive Hit (00C8)

```
Byte 1: 00 (Attack 0, Decay 0)
Byte 2: C8 (Sustain C, Release 8)
```

**Character**: Instant attack, instant to sustain, loud, medium release
**Use**: Drums, percussion, sharp hits

### Organ Sustain (00F0)

```
Byte 1: 00 (Attack 0, Decay 0)
Byte 2: F0 (Sustain F, Release 0)
```

**Character**: Instant attack, max sustain, instant release
**Use**: Organ, sustained tones, square leads

---

## Sources and References

**Official SID Factory II Tutorials**:
- [Part 1 - Introduction](https://blog.chordian.net/2022/08/27/composing-in-sid-factory-ii-part-1-introduction/)
- [Part 4 - Instruments](https://blog.chordian.net/2022/08/27/composing-in-sid-factory-ii-part-4-instruments/)
- [SID Factory II Main Site](https://blog.chordian.net/sf2/)

**Related Documentation**:
- `SF2_TRACKS_AND_SEQUENCES.md` - Track and sequence format
- `sf2_viewer_core.py` - SequenceEntry implementation
- `sf2_viewer_gui.py` - Instrument display

---

**Date Created**: 2025-12-17
**Reference**: SID Factory II Official Tutorials
**Related Files**: `track_3.txt`, `compare_track3_v2.py`
