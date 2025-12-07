# SID Factory II Driver Reference

*Complete specifications for all SF2 drivers*

## Overview

SID Factory II uses a modular driver system. Each driver has different capabilities, table layouts, and memory footprints. Choose the driver that best fits your needs.

| Driver | Name | Description | Tables |
|--------|------|-------------|--------|
| 11 | The Standard | Full-featured luxury driver | All |
| 12 | The Barber | Extremely simple, basic effects | Minimal |
| 13 | The Hubbard Experience | Rob Hubbard sound emulation | Custom |
| 14 | The Experiment | Short gate-off timing | Most |
| 15 | Tiny mark I | Small with zero-page vars | Wave only |
| 16 | Tiny mark II | Smallest, no commands | Wave only |

---

## Driver 11 - The Standard

The default "luxury" driver with all features and effects.

### Versions

| Version | Changes |
|---------|---------|
| 11.00 | Original default driver |
| 11.01 | Added fret slide command |
| 11.02 | Added pulse table index, tempo table index, main volume commands |
| 11.03 | Added additional filter enable flag |
| 11.04 | Added note event delay |
| 11.05 | Fret slide removed, HR table 16→8 rows, skip pulse reset flag added |

### Instruments (6 bytes)

| Byte | Description |
|------|-------------|
| 0 | AD (Attack/Decay) |
| 1 | SR (Sustain/Release) |
| 2 | Flags |
| 3 | Filter table index |
| 4 | Pulse table index |
| 5 | Wave table index |

**Flags:**

| Bit | Description |
|-----|-------------|
| $80 | Enable hard restart |
| $40 | Start filter program |
| $20 | [11.03] Enable filter on channel |
| $10 | Oscillator reset (waveform 09 on first frame) |
| $08 | Skip resetting pulse program on note on |
| $0x | Hard restart table index (0-7) |

### Commands (3 bytes)

| Type | XX | YY | Description |
|------|----|----|-------------|
| T0 | XX | YY | Slide up/down - XXYY = 16-bit speed |
| T1 | XX | YY | Vibrato - XX=frequency, YY=amplitude |
| T2 | XX | YY | Portamento - XXYY = 16-bit speed |
| T3 | XX | YY | Arpeggio - XX=speed, YY=table index |
| T4 | XX | YY | [11.01-11.04] Fret slide |
| T8 | XX | YY | Set local ADSR |
| T9 | XX | YY | Set instrument ADSR |
| Ta | -- | XX | Filter program |
| Tb | -- | XX | Wave program |
| Tc | -- | XX | [11.02] Pulse program |
| Td | -- | XX | [11.02] Tempo program |
| Te | -- | -X | [11.02] Main volume |
| Tf | -- | XX | Increase demo value |

**Note**: T value = delay in ticks for driver 11.04.

### Wave Table

| Col 0 | Col 1 | Description |
|-------|-------|-------------|
| XX | YY | Waveform XX, note offset YY ($80-$DF = absolute) |
| $7F | XX | Jump to index XX |

### Pulse Table

| Byte 0 | Byte 1 | Byte 2 | Description |
|--------|--------|--------|-------------|
| $8X XX | YY | | Set pulse XXX, for YY frames |
| $0X XX | YY | | Add XXX to pulse, for YY frames |
| $7F -- | XX | | Jump to index XX |

### Filter Table

| Byte 0 | Byte 1/2 | Byte 3 | Description |
|--------|----------|--------|-------------|
| $XY YY | RB | | Set filter if X>8: X=passband, YYY=cutoff, R=resonance, B=channel bitmask |
| $0X XX | YY | | Add XXX to cutoff, for YY frames |
| $7F -- | XX | | Jump to index XX |

### Arpeggio Table

| Value | Description |
|-------|-------------|
| XX | Semitones to add (if XX < $70) |
| $7X | Jump to relative index X |

**Known bugs**: None

---

## Driver 12 - The Barber

An extremely simple driver with only basic effects. Minimal memory footprint.

### Instruments (4 bytes)

| Byte | Description |
|------|-------------|
| 0 | AD |
| 1 | SR |
| 2 | Waveform |
| 3 | Pulse width XY (X=mid 4 bits, Y=top 4 bits) |

### Commands (2 bytes)

| Byte 0 | Byte 1 | Description |
|--------|--------|-------------|
| $0X | XX | Slide up - XXX = 12-bit speed |
| $1X | XX | Slide down - XXX = 12-bit speed |
| $2X | -Y | Vibrato - X=frequency, Y=amplitude |

**Known bugs**: None

---

## Driver 13 - The Hubbard Experience

Emulates the sound of Rob Hubbard's legendary C64 driver.

### Instruments (7 bytes)

| Byte | Description |
|------|-------------|
| 0 | AD |
| 1 | SR |
| 2 | Waveform |
| 3 | Pulse width XY (X=speed, Y=high nibble start) |
| 4 | Pulse sweep range |
| 5 | Flags |
| 6 | Arp properties XY (X=regularity, Y=speed) |

**Flags:**

| Bit | Description |
|-----|-------------|
| $8X | Alternate arpeggio (X=semitones added) |
| $40 | Dive effect |
| $20 | Ignore order list transposition |
| $10 | Add noise at beginning of note |

### Commands (2 bytes)

| Byte 0 | Byte 1 | Description |
|--------|--------|-------------|
| $0X | XX | Slide up - XXX = 12-bit speed |
| $1X | XX | Slide down - XXX = 12-bit speed |
| $2X | -Y | Vibrato - X=frequency, Y=amplitude |

**Known bugs**: None

---

## Driver 14 - The Experiment

Experimental approach allowing very short gate-off durations. Higher chance of instability.

### Instruments (6 bytes)

| Byte | Description |
|------|-------------|
| 0 | AD |
| 1 | SR |
| 2 | Flags |
| 3 | Filter table index |
| 4 | Pulse table index |
| 5 | Wave table index |

**Flags:**

| Bit | Description |
|-----|-------------|
| $80 | Enable "immediate response" hard restart |
| $40 | Start filter program |

### Commands (2 bytes)

| Byte 0 | Byte 1 | YY | Description |
|--------|--------|-----|-------------|
| $00 | XX | YY | Slide up/down - XXYY = 16-bit speed |
| $01 | XX | YY | Vibrato - XX=frequency, YY=amplitude |

### Tables

Wave, Pulse, and Filter tables same as Driver 11.

**Known bugs**: None

---

## Driver 15 - Tiny, mark I

Small driver with all variables in zero-page. Hard restart always on.

### Instruments (5 bytes)

| Byte | Description |
|------|-------------|
| 0 | AD |
| 1 | SR |
| 2 | Pulse width XY (X=mid 4 bits, Y=top 4 bits) |
| 3 | Linear pulse sweep XY (X=add to mid, Y=add to top) |
| 4 | Wave table index |

### Commands (2 bytes)

| Byte 0 | Byte 1 | Description |
|--------|--------|-------------|
| $0X | XX | Slide up - XXX = 12-bit speed |
| $1X | XX | Slide down - XXX = 12-bit speed |
| $2X | -Y | Vibrato - X=frequency, Y=amplitude |
| $3X | YY | Wave program - YY=table index |

### Wave Table

Same as Driver 11.

### Version Updates (15.02)

- Changed HR to set ADSR to $0F00 (not just SR=$00)
- Programs run during next-note phase (was suspended)
- Added wave program command ($3X YY)
- Added stop marker support

**Known bugs**: None

---

## Driver 16 - Tiny, mark II

Smallest driver possible. No commands available. Hard restart always on.

### Instruments (5 bytes)

| Byte | Description |
|------|-------------|
| 0 | AD |
| 1 | SR |
| 2 | Pulse width XY |
| 3 | Linear pulse sweep XY |
| 4 | Wave table index |

### Commands

N/A - No commands available.

### Wave Table

Same as Driver 11.

**Known bugs**: None

---

## Choosing a Driver

### Full Featured Music → Driver 11
- All effects available
- Largest memory footprint
- Best for standalone tunes

### Game Music (Size Limited) → Driver 15/16
- Minimal memory usage
- Zero-page variables
- Limited effects

### Rob Hubbard Style → Driver 13
- Authentic pulse/arp effects
- Special dive and noise features

### Simple Tunes → Driver 12
- Very small footprint
- Basic slide/vibrato only

### Experimental → Driver 14
- Short gate-off timing
- May be unstable

---

## Common Table Formats

### Wave Table (All Drivers)

| Col 0 | Col 1 | Description |
|-------|-------|-------------|
| Waveform | Note offset | Standard entry |
| $7F | Index | Jump command |

**Note offsets:**
- $00-$7F = Semitones to add
- $80-$DF = Absolute note value

### Pulse Table (Drivers 11, 14)

4 bytes per entry with set/add commands and jump.

### Filter Table (Drivers 11, 14)

4 bytes per entry with set/add commands, routing, and jump.

---

## Driver Files

All SF2 driver templates are located in `G5/drivers/`:

| File | Driver | Version |
|------|--------|---------|
| sf2driver11_00.prg | 11 | 11.00 |
| sf2driver11_01.prg | 11 | 11.01 |
| sf2driver11_02.prg | 11 | 11.02 |
| sf2driver11_03.prg | 11 | 11.03 |
| sf2driver11_04.prg | 11 | 11.04 |
| sf2driver11_04_01.prg | 11 | 11.04.01 |
| sf2driver11_05.prg | 11 | 11.05 |
| sf2driver12_00.prg | 12 | 12.00 |
| sf2driver12_00_01.prg | 12 | 12.00.01 |
| sf2driver13_00.prg | 13 | 13.00 |
| sf2driver13_00_01.prg | 13 | 13.00.01 |
| sf2driver14_00.prg | 14 | 14.00 |
| sf2driver14_00_01.prg | 14 | 14.00.01 |
| sf2driver15_00.prg | 15 | 15.00 |
| sf2driver15_01.prg | 15 | 15.01 |
| sf2driver15_02.prg | 15 | 15.02 |
| sf2driver16_00.prg | 16 | 16.00 |
| sf2driver16_01.prg | 16 | 16.01 |
| sf2driver16_01_01.prg | 16 | 16.01.01 |
| sf2driver_np20_00.prg | NP20 | 00 |

The Laxity NewPlayer v21 source template is in `G5/NewPlayer v21.G5 Final/21.g5 clean.prg`.

---

## Example SF2 Files

Example songs demonstrating each driver are in `G5/examples/`:

| File | Driver | Feature Demonstrated |
|------|--------|----------------------|
| Driver 11 Test - Arpeggio.sf2 | 11 | Arpeggio table usage |
| Driver 11 Test - Filter.sf2 | 11 | Filter table sweeps |
| Driver 11 Test - Polyphonic.sf2 | 11 | Multi-voice composition |
| Driver 11 Test - Tie Notes.sf2 | 11 | Tie note (**) feature |
| Driver 12 Test - The Barber.sf2 | 12 | Minimal driver capabilities |
| Driver 13 Test - Hubbard.sf2 | 13 | Rob Hubbard style effects |
| Driver 14 Test - Heavy.sf2 | 14 | Short gate timing |
| Driver 14 Test - Long Sequence.sf2 | 14 | Extended sequence packing |
| Driver 14 Test - Medieval.sf2 | 14 | Medieval style music |
| Driver 15 Test - Mood.sf2 | 15 | Tiny driver with mood |
| Driver 16 Test - Busy.sf2 | 16 | Smallest driver, no commands |

Load these in SID Factory II to study table formats and feature usage.

---

## References

- [SF2 Format Specification](SF2_FORMAT_SPEC.md)
- [Conversion Strategy](CONVERSION_STRATEGY.md)
- SID Factory II User Manual
