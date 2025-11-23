# Format Specifications

## PSID/RSID File Format

### Header Structure (v2)

| Offset | Size | Description |
|--------|------|-------------|
| $00 | 4 | Magic ID ('PSID' or 'RSID') |
| $04 | 2 | Version (big-endian) |
| $06 | 2 | Data offset |
| $08 | 2 | Load address |
| $0A | 2 | Init address |
| $0C | 2 | Play address |
| $0E | 2 | Number of songs |
| $10 | 2 | Start song |
| $12 | 4 | Speed flags |
| $16 | 32 | Song name (PETSCII) |
| $36 | 32 | Author name |
| $56 | 32 | Copyright |
| $76 | 2 | Flags (v2+) |
| $78 | 1 | Start page (v2+) |
| $79 | 1 | Page length (v2+) |
| $7A | 2 | Reserved (v2+) |

### Concrete Example: Angular.sid

```
Offset  Hex              Value        Field
------  ---------------  -----------  ----------------
$00-03  50 53 49 44      "PSID"       Magic ID
$04-05  00 02            2            Version
$06-07  00 7C            $007C        Data offset (124)
$08-09  00 00            0            Load address (from data)
$0A-0B  10 00            $1000        Init address
$0C-0D  10 03            $1003        Play address
$0E-0F  00 01            1            Number of songs
$10-11  00 01            1            Start song
$12-15  00 00 00 00      0            Speed flags (VBI)
$16-35  "Angular"                     Song name
$36-55  "Thomas Mogensen (DRAX)"      Author
$56-75  "2017 Camelot/Vibrants"       Copyright
$76-77  00 24            $0024        Flags (PAL, 6581)
$7C-7D  00 10            $1000        Load addr (little-endian)
```

**Notes:**
- Header values are big-endian (except load address in data section)
- Load address $0000 in header means read from first 2 bytes of data
- C64 data starts at offset $7E and loads to $1000

See `docs/SID_FILE_ANALYSIS.md` for complete binary analysis.

### Version Differences

**Version 1:**
- 118 byte header
- No flags field
- No start/page fields

**Version 2:**
- 124 byte header
- Adds flags, start page, page length
- RSID format introduced

**Version 3/4:**
- Same as v2
- Additional flag bits defined

### Flags Field (v2+)

| Bit | Description |
|-----|-------------|
| 0 | MUS data (Compute!'s Sidplayer) |
| 1 | PSID specific |
| 2-3 | Clock: 0=Unknown, 1=PAL, 2=NTSC, 3=Both |
| 4-5 | SID model: 0=Unknown, 1=6581, 2=8580, 3=Both |
| 6-7 | Second SID address (v3+) |
| 8-9 | Third SID address (v4+) |

### Speed Flags

32 bits, one per subtune (up to 32 songs):
- `0`: Vertical blank (50Hz PAL / 60Hz NTSC)
- `1`: CIA timer (~60Hz)

---

## Laxity NewPlayer Format

### Memory Layout

Typical arrangement for Laxity v21:

```
$1000-$10FF: Player code (init)
$1100-$17FF: Player code (play)
$1800-$1FFF: Music data tables
$2000-$2FFF: Sequence data
$3000+: Additional data
```

### Instrument Table

8 bytes per instrument:

| Byte | Description |
|------|-------------|
| 0 | Attack/Decay |
| 1 | Sustain/Release |
| 2 | Wave table pointer (index) |
| 3 | Pulse table pointer (index) |
| 4 | Filter table pointer (index) |
| 5 | Pulse width low byte |
| 6 | Pulse width high / flags |
| 7 | Vibrato settings |

**Flags in byte 6:**
- Bits 0-3: Pulse width high
- Bit 4: Enable arpeggio
- Bit 5: Enable portamento
- Bit 6: Reserved
- Bit 7: Hard restart

### Wave Table Format

2 bytes per entry:

| Byte | Description |
|------|-------------|
| 0 | Duration (frames) or control |
| 1 | Waveform / note offset |

**Control Values (byte 0):**
- `$00-$7D`: Duration in frames
- `$7E`: Loop to byte 1 offset
- `$7F`: End of table

**Waveform Values (byte 1):**
- Bits 0-3: Gate, sync, ring, test
- Bits 4-7: Waveform selection

### Pulse Table Format

2 bytes per entry:

| Byte | Description |
|------|-------------|
| 0 | Duration or control |
| 1 | Pulse value or delta |

**Modes:**
- Absolute: Set pulse width directly
- Relative: Add/subtract from current
- Sweep: Automatic modulation

### Filter Table Format

2 bytes per entry:

| Byte | Description |
|------|-------------|
| 0 | Duration or control |
| 1 | Filter value or delta |

**Filter routing also controlled via this table.**

### Sequence Format

Variable-length byte stream:

| Range | Description |
|-------|-------------|
| $00-$5F | Note values (C-0 to B-7) |
| $60-$7F | Note with duration |
| $80-$9F | Rest (duration in bits 0-4) |
| $A0-$BF | Tie/hold |
| $C0-$CF | Commands |
| $D0-$EF | Extended commands |
| $F0-$FE | Special functions |
| $FF | End of sequence |

### Command List

| Code | Command | Parameter |
|------|---------|-----------|
| $C0 | Slide Up | Speed |
| $C1 | Slide Down | Speed |
| $C2 | Set Vibrato | Depth/speed |
| $C3 | Portamento | Speed |
| $C4 | Set ADSR | AD, SR |
| $C5 | Set Wave | Index |
| $C6 | Set Pulse | Index |
| $C7 | Set Filter | Index |
| $C8 | Arpeggio | Pattern |
| $C9 | Tempo | Value |
| $CA | Transpose | Semitones |
| $CB | Volume | Level |
| $CC | Filter Ctrl | Routing |
| $CD | PWM | Speed |
| $CE | FM | Speed |
| $CF | Special | Sub-command |

---

## SID Factory II Format (.sf2)

### File Structure

```
Offset      Size    Description
$0000       64      Header
$0040       2048    Driver code
$0840       128     Configuration
$08C0       64      Metadata
$0900       varies  Music data
```

### Header (64 bytes)

| Offset | Size | Description |
|--------|------|-------------|
| $00 | 4 | Magic "SF2\x00" |
| $04 | 2 | Format version |
| $06 | 2 | Driver type |
| $08 | 32 | Song name |
| $28 | 32 | Author name |

### Driver Types

| ID | Name | Description |
|----|------|-------------|
| 0 | Basic | Minimal driver |
| 11 | Driver11 | Standard Laxity |
| 20 | NP20 | NewPlayer 2.0 |

### Music Data Sections

| Offset | Size | Description |
|--------|------|-------------|
| $0903 | var | Sequence pointers |
| $0A03 | 256 | Instrument table (32 × 8) |
| $0B03 | 256 | Wave table (128 × 2) |
| $0D03 | 256 | Pulse table (128 × 2) |
| $0F03 | 256 | Filter table (128 × 2) |
| $1103 | var | Init table |
| $1203 | var | Arpeggio table |
| $1303 | var | HR table |
| $1403 | var | Sequence data |

### Instrument Format (SF2)

8 bytes per instrument (same as Laxity):

```
Byte 0: AD
Byte 1: SR
Byte 2: Wave pointer
Byte 3: Pulse pointer
Byte 4: Filter pointer
Byte 5: PW low
Byte 6: PW high/flags
Byte 7: Vibrato
```

### Table Entry Format

All tables use 2-byte entries:

```
Byte 0: Duration/control
Byte 1: Value/parameter
```

Control codes:
- `$7F`: End
- `$7E`: Loop
- `$00-$7D`: Duration

---

## Siddump Output Format

Text format from siddump.exe (see `docs/SIDDUMP_ANALYSIS.md` for full source analysis):

```
| Frame | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | FCut RC Typ V |
+-------+---------------------------+---------------------------+---------------------------+---------------+
|     0 | 0000  ... ..  00 0000 000 | 0000  ... ..  00 0000 000 | 0000  ... ..  00 0000 000 | 0000 00 Off 0 |
|     1 | 1CD6  C-4 B0  41 09F0 800 | 0000  ... ..  00 0000 000 | 0E6B  C-3 A4  21 08A0 000 | 0400 8F Low F |
```

### Column Descriptions

**Per Voice (3 voices):**
- `Freq`: 16-bit frequency value ($D400/$D401)
- `Note`: Note name (C-0 to B-7)
- `Abs`: Absolute note value ($80-$DF)
- `WF`: Waveform byte ($D404)
- `ADSR`: Attack/Decay + Sustain/Release ($D405/$D406)
- `Pul`: Pulse width 12-bit ($D402/$D403)

**Filter:**
- `FCut`: Filter cutoff ($D415/$D416)
- `RC`: Resonance/routing ($D417)
- `Typ`: Filter type (Off/Low/Bnd/Hi/L+B/L+H/B+H/LBH)
- `V`: Master volume ($D418 low nibble)

### Special Notations

- `....` = Same as previous frame
- `...` = No note/data
- `(C-4 B0)` = Note changed without gate trigger
- `(+ 000A)` = Frequency sliding up
- `(- 0010)` = Frequency sliding down

### Parsing Example

```python
def parse_siddump_line(line):
    # Frame | V1 data | V2 data | V3 data | Filter
    parts = line.split('|')
    if len(parts) < 6:
        return None

    frame = int(parts[1].strip())
    voices = []

    for i in range(3):
        voice_data = parts[2 + i].strip().split()
        freq = int(voice_data[0], 16)
        note = voice_data[1]
        wf = int(voice_data[3], 16)
        adsr = int(voice_data[4], 16)
        voices.append({
            'freq': freq,
            'note': note,
            'waveform': wf,
            'adsr': adsr
        })

    filter_data = parts[5].strip().split()
    filter_info = {
        'cutoff': int(filter_data[0], 16),
        'resonance': int(filter_data[1], 16)
    }

    return {
        'frame': frame,
        'voices': voices,
        'filter': filter_info
    }
```

---

## Player-ID Output Format

Text output from player-id.exe:

```
File: song.sid
Player: Laxity NewPlayer v21
Confidence: 95%
Init: $1000
Play: $1003
```

### Supported Players

| ID String | Player |
|-----------|--------|
| Laxity NewPlayer | All versions |
| GoatTracker | GoatTracker player |
| JCH | JCH NewPlayer |
| DMC | Demo Music Creator |
| Noise | NoiseTracker |

### Parsing Example

```python
def parse_player_id(output):
    result = {}
    for line in output.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip().lower()] = value.strip()
    return result
```

---

## Frequency Tables

### PAL (985248 Hz clock)

| Note | Octave 0 | Octave 4 | Octave 7 |
|------|----------|----------|----------|
| C | $0112 | $1120 | $8900 |
| C# | $0123 | $1230 | $9180 |
| D | $0134 | $1340 | $9A00 |
| D# | $0146 | $1460 | $A380 |
| E | $015A | $15A0 | $AD00 |
| F | $016E | $16E0 | $B700 |
| F# | $0184 | $1840 | $C200 |
| G | $019B | $19B0 | $CD80 |
| G# | $01B4 | $1B40 | $DA00 |
| A | $01CE | $1CE0 | $E700 |
| A# | $01E9 | $1E90 | $F480 |
| B | $0206 | $2060 | $FF00 |

### NTSC (1022727 Hz clock)

Multiply PAL values by 1.038 for NTSC frequencies.

---

## Waveform Reference

### Single Waveforms

| Value | Waveform |
|-------|----------|
| $10 | Triangle |
| $20 | Sawtooth |
| $40 | Pulse |
| $80 | Noise |

### Combined Waveforms

| Value | Waveforms |
|-------|-----------|
| $30 | Triangle + Sawtooth |
| $50 | Triangle + Pulse |
| $60 | Sawtooth + Pulse |
| $70 | Tri + Saw + Pulse |

### With Gate

Add $01 for gate bit:
- $11 = Triangle + Gate
- $41 = Pulse + Gate
- $81 = Noise + Gate

### Special Values

| Value | Meaning |
|-------|---------|
| $00 | Gate off (release) |
| $01 | Gate only (silence) |
| $09 | Gate + Test (mute) |
| $FE | Ring mod + all waves |

---

## ADSR Reference

### Attack Times

| Value | Milliseconds |
|-------|-------------|
| 0 | 2 |
| 2 | 16 |
| 5 | 56 |
| 8 | 100 |
| 10 | 500 |
| 12 | 1000 |
| 15 | 8000 |

### Decay/Release Times

| Value | Milliseconds |
|-------|-------------|
| 0 | 6 |
| 2 | 48 |
| 5 | 168 |
| 8 | 300 |
| 10 | 1500 |
| 12 | 3000 |
| 15 | 24000 |

### Common ADSR Combinations

| AD | SR | Description |
|----|-----|-------------|
| $09 | $00 | Snappy lead |
| $00 | $F0 | Sustained pad |
| $0A | $A9 | Soft lead |
| $08 | $89 | Bass |
| $00 | $00 | Percussion |
