# SID Registers Reference

Quick reference for Commodore 64 Sound Interface Device (6581 SID chip) registers.

**Memory Range**: 54272-54300 ($D400-$D41C)

---

## Overview

The SID chip provides:
- **3 independent voices** with 16-bit frequency resolution
- **4 waveforms** per voice: Triangle, Sawtooth, Pulse, Noise
- **ADSR envelope** shaping per voice
- **Oscillator sync** and **ring modulation**
- **Programmable filters**: High-pass, low-pass, band-pass, notch
- **Volume control**: 0-15 levels

**Important**: Most SID registers are **write-only** (cannot be read back via PEEK).

---

## Voice Registers

Each voice has identical register layout. Offsets shown for Voice 1; add $07 for Voice 2, $0E for Voice 3.

### Frequency Control (16-bit)

| Address | Name | Description |
|---------|------|-------------|
| $D400 | FRELO1 | Voice 1 Frequency (low byte) |
| $D401 | FREHI1 | Voice 1 Frequency (high byte) |

**Formula**: `FREQUENCY = (REGISTER_VALUE × 0.060959458) Hz` (NTSC)

Where `REGISTER_VALUE = LOW_BYTE + (HIGH_BYTE × 256)`

**Range**: 0 Hz to ~4000 Hz in 65536 steps (over 8 octaves)

### Pulse Width Control (12-bit)

| Address | Name | Description |
|---------|------|-------------|
| $D402 | PWLO1 | Voice 1 Pulse Width (low byte) |
| $D403 | PWHI1 | Voice 1 Pulse Width (high nybble, bits 0-3) |

**Formula**: `PULSE_WIDTH = (REGISTER_VALUE / 40.95)%`

**Range**: 0-4095 (duty cycle 0-100%)

### Control Register

| Address | Name | Bits | Description |
|---------|------|------|-------------|
| $D404 | VCREG1 | - | Voice 1 Control Register |

**Bit Layout**:
- **Bit 0**: Gate (1=Attack/Decay/Sustain, 0=Release)
- **Bit 1**: Sync (1=Sync with Oscillator 3)
- **Bit 2**: Ring Modulation (1=Ring mod with Oscillator 3)
- **Bit 3**: Test (1=Disable oscillator)
- **Bit 4**: Triangle waveform
- **Bit 5**: Sawtooth waveform
- **Bit 6**: Pulse waveform
- **Bit 7**: Noise waveform

**Notes**:
- Must select one waveform (bits 4-7) for sound output
- Setting multiple waveform bits creates logical AND (not recommended for noise+other)
- Gate bit (0) starts/stops ADSR envelope cycle

### Attack/Decay Register

| Address | Name | Bits | Description |
|---------|------|------|-------------|
| $D405 | ATDCY1 | 4-7 | Attack duration (0-15) |
| | | 0-3 | Decay duration (0-15) |

**Attack Durations** (bits 4-7):
```
0=2ms    1=8ms     2=16ms    3=24ms
4=38ms   5=56ms    6=68ms    7=80ms
8=100ms  9=250ms   10=500ms  11=800ms
12=1s    13=3s     14=5s     15=8s
```

**Decay Durations** (bits 0-3):
```
0=6ms    1=24ms    2=48ms    3=72ms
4=114ms  5=168ms   6=204ms   7=240ms
8=300ms  9=750ms   10=1.5s   11=2.4s
12=3s    13=9s     14=15s    15=24s
```

**Formula**: `REGISTER_VALUE = (ATTACK × 16) + DECAY`

### Sustain/Release Register

| Address | Name | Bits | Description |
|---------|------|------|-------------|
| $D406 | SUREL1 | 4-7 | Sustain level (0-15) |
| | | 0-3 | Release duration (0-15) |

**Sustain Levels** (bits 4-7):
- 0 = No volume
- 15 = Peak volume (from attack phase)

**Release Durations** (bits 0-3): Same as Decay durations above

---

## Complete Voice Register Map

| Voice 1 | Voice 2 | Voice 3 | Register |
|---------|---------|---------|----------|
| $D400 | $D407 | $D40E | Frequency Low |
| $D401 | $D408 | $D40F | Frequency High |
| $D402 | $D409 | $D410 | Pulse Width Low |
| $D403 | $D40A | $D411 | Pulse Width High |
| $D404 | $D40B | $D412 | Control Register |
| $D405 | $D40C | $D413 | Attack/Decay |
| $D406 | $D40D | $D414 | Sustain/Release |

**Voice 2 Control Register** ($D40B):
- Bit 1: Sync with Oscillator 1
- Bit 2: Ring mod with Oscillator 1

**Voice 3 Control Register** ($D412):
- Bit 1: Sync with Oscillator 2
- Bit 2: Ring mod with Oscillator 2

---

## Filter Registers

### Cutoff Frequency (11-bit)

| Address | Name | Description |
|---------|------|-------------|
| $D415 | CUTLO | Filter Cutoff Low (bits 0-2) |
| $D416 | CUTHI | Filter Cutoff High (8 bits) |

**Formula**: `FREQUENCY = (REGISTER_VALUE × 5.8) + 30 Hz`

Where `REGISTER_VALUE = LOW_BITS + (HIGH_BYTE × 8)`

**Range**: 30 Hz to ~12,000 Hz in 2048 steps

### Resonance and Voice Routing

| Address | Name | Bits | Description |
|---------|------|------|-------------|
| $D417 | RESON | 0 | Filter Voice 1 (1=yes) |
| | | 1 | Filter Voice 2 (1=yes) |
| | | 2 | Filter Voice 3 (1=yes) |
| | | 3 | Filter External Input (1=yes) |
| | | 4-7 | Resonance (0-15) |

**Resonance**: Peaks volume near cutoff frequency (0=none, 15=max)

### Volume and Filter Select

| Address | Name | Bits | Description |
|---------|------|------|-------------|
| $D418 | SIGVOL | 0-3 | Volume (0-15) |
| | | 4 | Low-pass filter (1=on) |
| | | 5 | Band-pass filter (1=on) |
| | | 6 | High-pass filter (1=on) |
| | | 7 | Voice 3 Off (1=disconnect output) |

**Filter Types**:
- **Low-pass**: Suppress frequencies above cutoff
- **High-pass**: Suppress frequencies below cutoff
- **Band-pass**: Suppress frequencies away from cutoff
- **Notch** (high+low): Suppress frequencies near cutoff

**Attenuation Rates**:
- High/low-pass: 12 dB/octave
- Band-pass: 6 dB/octave

---

## Read-Only Registers

### Game Paddles

| Address | Name | Description |
|---------|------|-------------|
| $D419 | POTX | Read Paddle 1 or 3 (0-255) |
| $D41A | POTY | Read Paddle 2 or 4 (0-255) |

**Note**: Requires setting CIA #1 Port A ($DC00) to select paddle pair.

### Oscillator 3 Output

| Address | Name | Description |
|---------|------|-------------|
| $D41B | RANDOM | Oscillator 3 Waveform Output (upper 8 bits) |

**Uses**:
- **Sawtooth**: 0→255 ramp
- **Triangle**: 0→255→0 cycle
- **Pulse**: 0 or 255
- **Noise**: Random 0-255 (random number generator)

**Common Use**: Modulation source for frequency, pulse width, or filter cutoff

### Envelope 3 Output

| Address | Name | Description |
|---------|------|-------------|
| $D41C | ENV3 | Envelope Generator 3 Output |

**Note**: Requires gate bit (bit 0) of Control Register 3 to be set.

**Common Use**: Modulation source for ADSR-controlled effects

---

## Unused Registers

| Address Range | Description |
|---------------|-------------|
| $D41D-$D41F | Not connected (read as $FF, write ignored) |
| $D420-$D7FF | Mirror images of $D400-$D41F (avoid using) |

---

## Common Programming Patterns

### Playing a Note

```
1. Set Volume Register ($D418 bits 0-3) to non-zero
2. Set Frequency Registers ($D400/$D401)
3. Set ADSR Envelope ($D405/$D406)
4. Set Pulse Width if using pulse waveform ($D402/$D403)
5. Set Control Register: waveform + gate on ($D404 = waveform|0x01)
```

### Stopping a Note

```
Option 1: Gate off (release cycle)
  - Write Control Register with gate bit 0, keep waveform ($D404 = waveform|0x00)

Option 2: Immediate silence
  - Set waveform to 0 ($D404 = 0x00)
  - OR set frequency to 0
  - OR set volume to 0
```

### ADSR Envelope Cycle

```
Gate 1→0 transition:
  ATTACK → DECAY → SUSTAIN (hold) → RELEASE (on gate 0)

Notes:
- Sustain phase holds until gate=0
- Release may not reach full 0 volume
- Use waveform=0 or volume=0 to ensure silence
```

---

## Quick Reference Values

### Common Frequencies (NTSC)

| Note | Freq (Hz) | Register Value |
|------|-----------|----------------|
| C-0 | 16.35 | 268 ($010C) |
| A-4 | 440.00 | 7217 ($1C31) |
| C-8 | 4186.01 | 68645 ($10C05) |

### Common ADSR Settings

| Type | Attack | Decay | Sustain | Release | Hex |
|------|--------|-------|---------|---------|-----|
| Pluck | Fast | Medium | Low | Fast | $08/$31 |
| Organ | Fast | None | High | Fast | $00/$F1 |
| Pad | Slow | Slow | High | Slow | $AA/$FB |
| Drum | Fast | Fast | None | Fast | $00/$01 |

### Common Waveforms (Control Register)

| Waveform | Bit Pattern | Hex | With Gate |
|----------|-------------|-----|-----------|
| Triangle | 00010000 | $10 | $11 |
| Sawtooth | 00100000 | $20 | $21 |
| Pulse | 01000000 | $40 | $41 |
| Noise | 10000000 | $80 | $81 |

---

## See Also

- **learnings/sidmitlearn.txt** - Full SID register documentation (source)
- **docs/STINSENS_PLAYER_DISASSEMBLY.md** - Laxity player implementation
- **docs/SF2_DRIVER11_DISASSEMBLY.md** - SF2 player implementation
- **docs/CONVERSION_STRATEGY.md** - Laxity to SF2 mapping

---

*Reference extracted from Commodore 64 Programmer's Reference Guide*
