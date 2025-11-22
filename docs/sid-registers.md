# SID Chip Register Reference

## Overview

The SID (Sound Interface Device) chip is located at memory addresses `$D400-$D41C` (54272-54300 decimal). It contains three independent voices, each with its own oscillator, envelope generator, and control registers.

## Voice 1 Registers ($D400-$D406)

| Address | Decimal | Function | Bits |
|---------|---------|----------|------|
| `$D400` | 54272 | Frequency low byte | 7-0: Freq bits 0-7 |
| `$D401` | 54273 | Frequency high byte | 7-0: Freq bits 8-15 |
| `$D402` | 54274 | Pulse width low byte | 7-0: PW bits 0-7 |
| `$D403` | 54275 | Pulse width high byte | 3-0: PW bits 8-11 |
| `$D404` | 54276 | Control register | See below |
| `$D405` | 54277 | Attack/Decay | 7-4: Attack, 3-0: Decay |
| `$D406` | 54278 | Sustain/Release | 7-4: Sustain, 3-0: Release |

### Control Register ($D404) Bit Layout

| Bit | Function |
|-----|----------|
| 7 | Noise waveform |
| 6 | Pulse waveform |
| 5 | Sawtooth waveform |
| 4 | Triangle waveform |
| 3 | Test bit |
| 2 | Ring modulation with voice 3 |
| 1 | Synchronize with voice 3 |
| 0 | Gate (start/stop envelope) |

## Voice 2 Registers ($D407-$D40D)

| Address | Decimal | Function | Bits |
|---------|---------|----------|------|
| `$D407` | 54279 | Frequency low byte | 7-0: Freq bits 0-7 |
| `$D408` | 54280 | Frequency high byte | 7-0: Freq bits 8-15 |
| `$D409` | 54281 | Pulse width low byte | 7-0: PW bits 0-7 |
| `$D40A` | 54282 | Pulse width high byte | 3-0: PW bits 8-11 |
| `$D40B` | 54283 | Control register | See below |
| `$D40C` | 54284 | Attack/Decay | 7-4: Attack, 3-0: Decay |
| `$D40D` | 54285 | Sustain/Release | 7-4: Sustain, 3-0: Release |

### Control Register ($D40B) Bit Layout

| Bit | Function |
|-----|----------|
| 7 | Noise waveform |
| 6 | Pulse waveform |
| 5 | Sawtooth waveform |
| 4 | Triangle waveform |
| 3 | Test bit |
| 2 | Ring modulation with voice 1 |
| 1 | Synchronize with voice 1 |
| 0 | Gate (start/stop envelope) |

## Voice 3 Registers ($D40E-$D414)

| Address | Decimal | Function | Bits |
|---------|---------|----------|------|
| `$D40E` | 54286 | Frequency low byte | 7-0: Freq bits 0-7 |
| `$D40F` | 54287 | Frequency high byte | 7-0: Freq bits 8-15 |
| `$D410` | 54288 | Pulse width low byte | 7-0: PW bits 0-7 |
| `$D411` | 54289 | Pulse width high byte | 3-0: PW bits 8-11 |
| `$D412` | 54290 | Control register | See below |
| `$D413` | 54291 | Attack/Decay | 7-4: Attack, 3-0: Decay |
| `$D414` | 54292 | Sustain/Release | 7-4: Sustain, 3-0: Release |

### Control Register ($D412) Bit Layout

| Bit | Function |
|-----|----------|
| 7 | Noise waveform |
| 6 | Pulse waveform |
| 5 | Sawtooth waveform |
| 4 | Triangle waveform |
| 3 | Test bit |
| 2 | Ring modulation with voice 2 |
| 1 | Synchronize with voice 2 |
| 0 | Gate (start/stop envelope) |

## Filter Registers ($D415-$D418)

| Address | Decimal | Function | Bits |
|---------|---------|----------|------|
| `$D415` | 54293 | Filter cutoff low | 2-0: Cutoff bits 0-2 |
| `$D416` | 54294 | Filter cutoff high | 7-0: Cutoff bits 3-10 |
| `$D417` | 54295 | Filter resonance/routing | See below |
| `$D418` | 54296 | Filter mode/volume | See below |

### Filter Control ($D417) Bit Layout

| Bits | Function |
|------|----------|
| 7-4 | Filter resonance (0-15) |
| 3 | Filter external input |
| 2 | Filter voice 3 |
| 1 | Filter voice 2 |
| 0 | Filter voice 1 |

### Mode/Volume ($D418) Bit Layout

| Bit | Function |
|-----|----------|
| 7 | Mute voice 3 |
| 6 | High-pass filter |
| 5 | Band-pass filter |
| 4 | Low-pass filter |
| 3-0 | Main volume (0-15) |

## Waveform Values

Common waveform byte values for control registers:

| Value | Waveform | Description |
|-------|----------|-------------|
| `$01` | - | Gate only |
| `$11` | Triangle | Triangle + gate |
| `$21` | Sawtooth | Sawtooth + gate |
| `$41` | Pulse | Pulse + gate |
| `$81` | Noise | Noise + gate |
| `$15` | Triangle | Triangle + ring mod + gate |
| `$31` | Tri+Saw | Combined waveforms |
| `$51` | Tri+Pulse | Combined waveforms |

## ADSR Timing

### Attack Times (bits 7-4)

| Value | Time (ms) |
|-------|-----------|
| 0 | 2 |
| 1 | 8 |
| 2 | 16 |
| 3 | 24 |
| 4 | 38 |
| 5 | 56 |
| 6 | 68 |
| 7 | 80 |
| 8 | 100 |
| 9 | 250 |
| 10 | 500 |
| 11 | 800 |
| 12 | 1000 |
| 13 | 3000 |
| 14 | 5000 |
| 15 | 8000 |

### Decay/Release Times (bits 3-0)

| Value | Time (ms) |
|-------|-----------|
| 0 | 6 |
| 1 | 24 |
| 2 | 48 |
| 3 | 72 |
| 4 | 114 |
| 5 | 168 |
| 6 | 204 |
| 7 | 240 |
| 8 | 300 |
| 9 | 750 |
| 10 | 1500 |
| 11 | 2400 |
| 12 | 3000 |
| 13 | 9000 |
| 14 | 15000 |
| 15 | 24000 |

## Frequency Calculation

The SID uses a 16-bit frequency value:

```
Frequency = (Fout × 16777216) / Fclk
```

Where:
- `Fout` = Desired output frequency in Hz
- `Fclk` = System clock (PAL: 985248 Hz, NTSC: 1022727 Hz)

### Note Frequency Table (PAL)

| Note | Freq (Hz) | SID Value |
|------|-----------|-----------|
| C-0 | 16.35 | $0112 |
| C-1 | 32.70 | $0224 |
| C-2 | 65.41 | $0448 |
| C-3 | 130.81 | $0890 |
| C-4 | 261.63 | $1120 |
| C-5 | 523.25 | $2240 |
| C-6 | 1046.50 | $4480 |
| C-7 | 2093.00 | $8900 |

## Usage in Converter

The converter reads SID register writes from `siddump.exe` output to:

1. **Track voice usage** - Which voices are active
2. **Extract ADSR values** - From $D405/$D40C/$D413
3. **Identify waveforms** - From control registers
4. **Analyze filter usage** - From $D417/$D418
5. **Map frequencies to notes** - Using frequency table

### Register Mapping in Code

```python
SID_REGISTERS = {
    0x00: 'freq_lo_1',
    0x01: 'freq_hi_1',
    0x02: 'pw_lo_1',
    0x03: 'pw_hi_1',
    0x04: 'ctrl_1',
    0x05: 'ad_1',
    0x06: 'sr_1',
    # ... voice 2 at 0x07-0x0D
    # ... voice 3 at 0x0E-0x14
    0x15: 'fc_lo',
    0x16: 'fc_hi',
    0x17: 'res_filt',
    0x18: 'mode_vol',
}
```
