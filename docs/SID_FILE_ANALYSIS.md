# SID File Binary Analysis

*Detailed walkthrough of actual SID file structure using Angular.sid*

## Overview

This document analyzes the binary structure of a real SID file (Angular.sid by DRAX) to demonstrate how to parse PSID/RSID files and identify the player type.

**File**: `SID/Angular.sid`
**Artist**: Thomas Mogensen (DRAX)
**Year**: 2017
**Player**: Laxity NewPlayer v21

---

## PSID Header Structure

### Header Bytes (Offset $00-$7B)

```
Offset  Hex              Description
------  ---------------  ------------------------------------
$00-03  50 53 49 44      Magic ID: "PSID"
$04-05  00 02            Version: 2 (big-endian)
$06-07  00 7C            Data offset: $007C (124 bytes)
$08-09  00 00            Load address: 0 (read from data)
$0A-0B  10 00            Init address: $1000
$0C-0D  10 03            Play address: $1003
$0E-0F  00 01            Number of songs: 1
$10-11  00 01            Start song: 1
$12-15  00 00 00 00      Speed flags: 0 (VBI timing)
$16-35  "Angular" + padding (32 bytes)
$36-55  "Thomas Mogensen (DRAX)" + padding (32 bytes)
$56-75  "2017 Camelot/Vibrants" + padding (32 bytes)
$76-77  00 24            Flags: PAL, 6581 SID
$78     00               Start page
$79     00               Page length
$7A-7B  00 00            Reserved
```

### Field Details

**Version ($04-05)**: `00 02`
- Version 2 PSID format
- 124-byte header (vs 118 for v1)

**Load Address ($08-09)**: `00 00`
- Zero means read from first 2 bytes of data section
- Actual load address is $1000

**Init Address ($0A-0B)**: `10 00`
- Entry point for initialization
- Call with subtune in A register: `JSR $1000`

**Play Address ($0C-0D)**: `10 03`
- Entry point for play routine
- Called once per frame (50Hz PAL): `JSR $1003`

**Flags ($76-77)**: `00 24`
```
Bit 0:   0 = Not MUS data
Bit 1:   0 = Built-in player
Bits 2-3: 01 = PAL only
Bits 4-5: 00 = Unknown SID model (default 6581)
Bits 6-7: 00 = No second SID
```

---

## C64 Data Section

### Load Address Detection

Since header load address is $0000, read from data:

```
Offset  Hex     Description
------  ------  -----------
$7C-7D  00 10   Load address: $1000 (little-endian)
```

The C64 data starts at offset $7E and loads to $1000.

### Player Identification

At offset ~$80 in the file (memory $1000), look for player signature:

```
Text found: "X-PLAYER BY LAXITY.MUSIC BY DRAX"
```

This confirms it's a **Laxity NewPlayer** format.

### Memory Layout (After Loading)

```
$1000-$1002    JMP to init routine
$1003-$1005    JMP to play routine
$1006-$17FF    Player code
$1800+         Music data and tables
```

---

## Identifying Laxity Player

### Text Signatures

Laxity SID files often contain embedded text:
- `"X-PLAYER BY LAXITY"`
- `"LAXITY"`
- Player version info

### Code Patterns

At init routine ($1000), look for:

```assembly
; Typical Laxity init pattern
JMP $xxxx       ; Jump to actual init
JMP $xxxx       ; Jump to play routine
; ...
LDA #$00        ; Clear value
STA $xxxx       ; Store to state
```

Byte sequence: `4C xx xx 4C xx xx ... A9 00 8D`

### Table Locations

Laxity v21 typical addresses:
- Frequency tables: $1800-$18FF
- State variables: $1900-$19FF
- Wave table: $1A00-$1A7F
- Pulse table: $1A80-$1AFF
- Instrument table: $1B00-$1B7F
- Sequence data: $1B80+

---

## Hex Dump Example

### First 128 Bytes of Angular.sid

```
00000000: 5053 4944 0002 007c 0000 1000 1003 0001  PSID...|........
00000010: 0001 0000 0000 416e 6775 6c61 7200 0000  ......Angular...
00000020: 0000 0000 0000 0000 0000 0000 0000 0000  ................
00000030: 0000 0000 0000 5468 6f6d 6173 204d 6f67  ......Thomas Mog
00000040: 656e 7365 6e20 2844 5241 5829 0000 0000  ensen (DRAX)....
00000050: 0000 0000 0000 3230 3137 2043 616d 656c  ......2017 Camel
00000060: 6f74 2f56 6962 7261 6e74 7300 0000 0000  ot/Vibrants.....
00000070: 0000 0000 0000 0024 0000 0000 0010 4cxx  .......$......L.
```

**Breakdown:**
- `50534944` = "PSID"
- `0002` = Version 2
- `007c` = Data offset 124
- `1000` = Init address (big-endian in header)
- `1003` = Play address
- `0001` = 1 song
- After header: `0010` = $1000 load address (little-endian)
- `4C` = JMP opcode

---

## Parsing Algorithm

### Python Implementation

```python
import struct

def parse_sid_header(data):
    """Parse PSID/RSID header from binary data."""

    # Check magic
    magic = data[0:4].decode('ascii')
    if magic not in ('PSID', 'RSID'):
        raise ValueError(f"Invalid magic: {magic}")

    # Parse header fields (big-endian)
    version = struct.unpack('>H', data[4:6])[0]
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_addr = struct.unpack('>H', data[8:10])[0]
    init_addr = struct.unpack('>H', data[10:12])[0]
    play_addr = struct.unpack('>H', data[12:14])[0]
    num_songs = struct.unpack('>H', data[14:16])[0]
    start_song = struct.unpack('>H', data[16:18])[0]
    speed = struct.unpack('>I', data[18:22])[0]

    # Parse strings (null-terminated, padded to 32 bytes)
    name = data[0x16:0x36].split(b'\x00')[0].decode('latin-1')
    author = data[0x36:0x56].split(b'\x00')[0].decode('latin-1')
    copyright = data[0x56:0x76].split(b'\x00')[0].decode('latin-1')

    # Version 2+ fields
    if version >= 2:
        flags = struct.unpack('>H', data[0x76:0x78])[0]
    else:
        flags = 0

    # If load address is 0, read from data
    if load_addr == 0:
        load_addr = struct.unpack('<H', data[data_offset:data_offset+2])[0]
        c64_data_start = data_offset + 2
    else:
        c64_data_start = data_offset

    return {
        'magic': magic,
        'version': version,
        'data_offset': data_offset,
        'load_address': load_addr,
        'init_address': init_addr,
        'play_address': play_addr,
        'num_songs': num_songs,
        'start_song': start_song,
        'speed': speed,
        'name': name,
        'author': author,
        'copyright': copyright,
        'flags': flags,
        'c64_data_start': c64_data_start
    }

def identify_player(c64_memory, load_addr):
    """Identify the player type from C64 memory."""

    # Check for Laxity text signatures
    mem_str = bytes(c64_memory).decode('latin-1', errors='ignore')

    if 'LAXITY' in mem_str.upper():
        return 'Laxity NewPlayer'
    if 'GOAT' in mem_str.upper():
        return 'GoatTracker'
    if 'JCH' in mem_str.upper():
        return 'JCH NewPlayer'

    # Check init pattern
    init_code = c64_memory[load_addr:load_addr+16]
    if init_code[0] == 0x4C:  # JMP
        return 'Unknown (JMP pattern)'

    return 'Unknown'
```

---

## Angular.sid Analysis Summary

| Field | Value | Notes |
|-------|-------|-------|
| Magic | PSID | Standard SID file |
| Version | 2 | 124-byte header |
| Load Address | $1000 | Standard Laxity location |
| Init Address | $1000 | Initializes player |
| Play Address | $1003 | Called at 50Hz |
| Songs | 1 | Single tune |
| Speed | VBI | Vertical blank timing |
| Clock | PAL | 50Hz frame rate |
| SID Model | Unknown | Works on 6581/8580 |
| Player | Laxity v21 | Identified by text |
| Author | DRAX | Thomas Mogensen |
| Year | 2017 | Camelot/Vibrants |

---

## Other Example SID Files

Files in `SID/` directory:

| File | Player | Notes |
|------|--------|-------|
| Angular.sid | Laxity v21 | DRAX, 2017 |
| angular_new.sid | Laxity v21 | Modified version |
| Clarencio_extended.sid | Laxity v21 | Extended tune |
| Ocean_Reloaded.sid | Laxity v21 | Ocean loader style |
| Omniphunk.sid | Laxity v21 | Phunk style |
| Phoenix_Code_End_Tune.sid | Laxity v21 | End tune |
| Unboxed_Ending_8580.sid | Laxity v21 | 8580 SID optimized |

All example files use the Laxity NewPlayer v21 format.

---

## Validation Checklist

When analyzing a SID file:

- [ ] Magic is "PSID" or "RSID"
- [ ] Version is 1, 2, 3, or 4
- [ ] Data offset points past header
- [ ] Load address is valid ($0000-$FFFF)
- [ ] Init address is within loaded range
- [ ] Play address is within loaded range
- [ ] Player type identified
- [ ] C64 data loads without overflow

---

## References

- [Format Specification](format-specification.md) - PSID/RSID header structure
- [Laxity Player Analysis](LAXITY_PLAYER_ANALYSIS.md) - Player code details
- [Conversion Strategy](CONVERSION_STRATEGY.md) - How to extract data
- [High Voltage SID Collection](https://hvsc.c64.org/) - SID file archive
