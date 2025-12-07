# Technical Analysis - SIDM2 Project

**Comprehensive technical analysis consolidating all research findings**

**Last Updated**: 2025-12-07
**Version**: 0.7.0

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [SF2 Format Analysis](#sf2-format-analysis)
3. [Laxity Player Analysis](#laxity-player-analysis)
4. [SID File Analysis](#sid-file-analysis)
5. [Siddump Tool Analysis](#siddump-tool-analysis)
6. [Audio Quality Analysis](#audio-quality-analysis)
7. [Reverse Engineering Findings](#reverse-engineering-findings)
8. [General Findings](#general-findings)

---

## Executive Summary

This document consolidates all technical analysis performed on the SIDM2 project, including:

- **SF2 Format**: Deep dive into SID Factory II file structure and driver internals
- **Laxity Player**: Analysis of NewPlayer v21 memory layout and algorithms
- **SID Files**: Understanding PSID/RSID structure and player detection
- **Siddump**: How the validation tool works internally
- **Audio Quality**: Analysis of conversion accuracy and quality metrics
- **Reverse Engineering**: Extracting SF2 data from packed SID files

### Current Accuracy Status

**Conversion Accuracy** (as of v0.6.5):
- **SF2-originated files**: 17/25 (68%) achieve 100% roundtrip accuracy
- **Laxity files**: 8/25 (32%) have 1-5% accuracy gaps
- **Root Cause**: Format differences between Laxity NewPlayer and SF2 drivers

**Key Insight**: SF2-originated files roundtrip perfectly because they already match SF2 driver format. Laxity files need improved conversion logic to bridge format gaps.

---

## SF2 Format Analysis

*Source: SF2 editor C++ source code analysis*

### Overview

SID Factory II uses a driver-based architecture where music data is separate from the playback driver. The driver code (~2KB of 6502 assembly) is complex and varies between versions.

**Source Location**: `SIDFactoryII/source/`

### Key Source Files

| File | Purpose |
|------|---------|
| `converters/utils/sf2_interface.h/cpp` | Core SF2 format handling |
| `driver/driver_info.h/cpp` | Driver structure parsing |
| `datasources/datasource_*.h` | Table access patterns |
| `utils/c64file.h/cpp` | PRG file handling |

### Driver Structure

All SF2 drivers share this basic structure:

```
SF2 File Layout:
├── PRG Header (2 bytes) - Load address
├── Driver Code (~2KB) - 6502 player routine
├── Driver Data - Init table, tempo, HR
├── Song Data Tables:
│   ├── Sequence Table
│   ├── Instrument Table (column-major, 6 bytes × 32)
│   ├── Command Table (3 bytes × 32)
│   ├── Wave Table
│   ├── Pulse Table (4 bytes per entry)
│   ├── Filter Table (4 bytes per entry)
│   ├── Arpeggio Table
│   └── Hard Restart Table
└── Auxiliary Data (patterns, orderlists)
```

### Table Definition Structure

From `driver_info.h`:

```cpp
struct TableDefinition {
    unsigned char m_Type;          // 0x00=Generic, 0x80=Instruments, 0x81=Commands
    unsigned char m_DataLayout;    // 0=RowMajor, 1=ColumnMajor
    unsigned short m_Address;      // Start address in memory
    unsigned char m_ColumnCount;
    unsigned char m_RowCount;
}
```

### Driver Identification

SF2 files are identified by:
1. **Driver ID marker** `0x1337` at driver top address
2. **Auxiliary data pointer** at `0x0FFB`
3. **Driver version** encoded in header

### Critical Implementation Details

**1. Instrument Table** (Column-Major):
- 32 instruments × 6 bytes
- Layout: All ADSR_AD values, then all ADSR_SR, then all Wave indices, etc.
- **Not** row-major like most tables

**2. Sequence Events**:
```cpp
struct Event {
    unsigned char m_Instrument;    // 0x80+ = no change
    unsigned char m_Command;       // 0x80+ = no change
    unsigned char m_Note;          // 0-95 or control codes
}
```

**3. Control Bytes**:
- `0x7F` - End marker / Jump command
- `0x7E` - Loop marker (wave table) / Gate on (sequences)
- `0x80` - Gate off (---)
- `0x81-0xFF` - Instrument/command "no change"

**4. Wrap Format**:
Tables can wrap to beginning. Format:
- Last entry points to wrap position
- Wrap position must be within valid table range

### SF2 vs Laxity Key Differences

| Aspect | Laxity NewPlayer | SF2 Driver |
|--------|------------------|------------|
| **Wave table** | (note, waveform) | (waveform, note) |
| **Pulse indices** | Y×4 pre-multiplied | Direct indices |
| **Gate** | Implicit | Explicit (+++ / ---) |
| **Instrument layout** | Row-major | Column-major |

---

## Laxity Player Analysis

*Source: NewPlayer v21 disassembly from Angular.sid*

### Overview

Laxity's NewPlayer v21 (aka JCH NewPlayer) is one of the most popular C64 music players. Understanding its internals is critical for accurate table extraction.

**Reference Song**: Angular by DRAX (Thomas Mogensen), 2017

### Memory Map

```
Address Range    Purpose
$1000-$103E      Entry points and metadata
$103F-$10A0      Init routine (song initialization)
$10A1-$1830      Play routine (main player loop)
$1833-$18F2      Frequency tables (96 notes × 2 bytes)
$18F3-$18FF      State flags and voice offsets
$1900-$199E      Per-voice state arrays
$199F-$19AC      Sequence pointer table
$19AD-$19E6      Wave table (offsets)
$19E7-$1A1D      Wave table (waveforms)
$1A1E-$1A3A      Filter/tempo table
$1A3B-$1A6A      Pulse table (16 entries × 3 bytes)
$1A6B-$1AAA      Instrument table (8 instruments × 8 bytes)
$1AAB-$1ADA      Command table
$1ADB-$????      Pattern data (sequences)
```

### Key Algorithms

**1. Frequency Table Lookup**:
```assembly
; Note indexing (0-95 for 8 octaves)
note_index = note_value & $3F
freq_lo = freq_table[note_index * 2]
freq_hi = freq_table[note_index * 2 + 1]
```

**2. Wave Table Format**:
```
Entry: [note_offset] [waveform]
- note_offset: 0 = use sequence note, $80+ = recalculate with offset
- waveform: $00-$FF SID waveform control byte
```

**3. Pulse Table**:
```
Entry: [pw_lo] [pw_hi] [speed]
- Pre-multiplied indices (Y register × 4)
- Need to divide by 4 for SF2 conversion
```

**4. Instrument Table** (8 bytes):
```
[ADSR_AD] [ADSR_SR] [wave_idx] [pulse_idx]
[filter_idx] [vib_depth] [vib_speed] [flags]
```

### Extraction Challenges

1. **Dynamic Pointers**: Sequence pointers calculated at runtime
2. **Compressed Data**: Pattern data uses control bytes for efficiency
3. **Shared Tables**: Multiple instruments may reference same wave/pulse entries
4. **Variable Lengths**: Tables don't have explicit size markers

---

## SID File Analysis

*Binary structure analysis of SID files*

### PSID/RSID Format

All SID files start with a 124-byte header:

```
Offset  Size  Field
0x00    4     Magic ('PSID' or 'RSID')
0x04    2     Version (usually 0x0002)
0x06    2     Data offset (usually 0x007C = 124 bytes)
0x08    2     Load address (0x0000 = read from data)
0x0A    2     Init address
0x0C    2     Play address
0x0E    2     Number of songs
0x10    2     Default song (1-based)
0x12    4     Speed (bit field for PAL/NTSC)
0x16    32    Title (null-terminated)
0x36    32    Author
0x56    32    Copyright/Released
0x76    2     Flags
0x78    1     Start page (relocat information)
0x79    1     Page length
0x7A    2     Reserved
0x7C+   ...   C64 data
```

### Player Detection

Use `tools/player-id.exe` to identify player type:

```bash
player-id.exe file.sid
# Output: "NewPlayer_v21/Laxity" or "SidFactory_II/Laxity"
```

Common players:
- `NewPlayer_v21/Laxity` - Original Laxity files
- `SidFactory_II/Laxity` - SF2-exported files
- `Compute!'s_Sidplayer/Craig_Chamberlain` - Old tracker files

### SF2-Packed SID Identification

SF2-exported SID files have characteristic signatures:

```
Load address: $1000
Init address: $1000
Play address: $1003
```

Entry point pattern:
```assembly
$1000:  LDA #$00        ; A9 00
$1002:  STA $????       ; 8D ?? ??
```

---

## Siddump Tool Analysis

*How siddump validates SID output*

### Architecture

Siddump is a 6502 CPU emulator that runs SID files and captures register writes frame-by-frame.

**Components**:
- `cpu.c` - Full 6502 emulator (~1200 lines)
- `siddump.c` - Main program (~520 lines)
- `mem.h` - 64KB memory model

### How It Works

1. **Load SID**: Parse PSID header, load C64 data at specified address
2. **Init**: Call init routine at init_addr with song number in A register
3. **Emulate**: Run play routine at 50Hz (PAL) or 60Hz (NTSC)
4. **Capture**: Record all writes to SID registers ($D400-$D41C)
5. **Output**: Print frame-by-frame register dump

### Output Format

```
Frames    Freq1   Freq2   Freq3   PW1  PW2  PW3  Ctl1 Ctl2 Ctl3 Att1 Att2 Att3 Fc  Res Mod Vol
00000000: 00 00 | 00 00 | 00 00 | 000 | 000 | 000 | 00 | 00 | 00 | 00 | 00 | 00 | 000 | 00 | 00 | 0F
00000001: 0E 2E | 00 00 | 00 00 | 000 | 000 | 000 | 21 | 00 | 00 | 09 | 00 | 00 | 000 | 00 | 00 | 0F
```

### Usage

```bash
# Basic 30-second dump
tools/siddump.exe SID/file.sid -t30 > file.dump

# With cycle counts
tools/siddump.exe SID/file.sid -z -t30 > file.dump

# Specific subtune
tools/siddump.exe SID/file.sid -a2 -t30 > file.dump
```

### Validation Strategy

Compare original SID dump vs exported SID dump:
1. Parse both dumps frame-by-frame
2. Calculate accuracy per voice, per register, per frame
3. Weight by importance (frequency > waveform > filter)
4. Generate accuracy percentage

---

## Audio Quality Analysis

*Analysis of conversion accuracy and audio quality*

### Methodology

Compare original SID vs converted SF2→SID using multiple metrics:

1. **Siddump comparison**: Register-level accuracy
2. **WAV comparison**: Audio waveform similarity
3. **Manual listening**: Subjective quality assessment

### Current Results (v0.6.5)

**Register Accuracy**:
- Best case: 100% (SF2-originated files)
- Typical Laxity: 95-99% (minor timing/envelope differences)
- Problem cases: 85-94% (incorrect table extraction)

**Common Issues**:

| Issue | Impact | Frequency |
|-------|--------|-----------|
| Incorrect wave table | Wrong timbres | 15% of files |
| Missing pulse modulation | Flat sound | 20% of files |
| Filter differences | EQ changes | 10% of files |
| Timing/tempo drift | Slight speed difference | 5% of files |

### Quality Factors

**High Impact** (easily audible):
- Waveform selection (triangle vs pulse vs sawtooth)
- Note frequencies
- Attack/decay/sustain/release envelopes

**Medium Impact** (sometimes audible):
- Pulse width modulation depth
- Filter cutoff and resonance
- Vibrato depth/speed

**Low Impact** (rarely audible):
- Exact timing of register writes
- Order of register updates within same frame
- Micro-timing variations

---

## Reverse Engineering Findings

*Extracting SF2 data from SF2-packed SID files*

### Test Case: Stinsen's Last Night of '89

**Files**:
- Original SF2: `learnings/Stinsen - Last Night Of 89.sf2` (17,252 bytes)
- Exported SID: `SIDSF2Player/SF2packed_Stinsens_Last_Night_of_89.sid` (6,075 bytes)
- Reverse-engineered SF2: `output/Stinsens_SF2Packed/New/Stinsens_SF2Packed_d11.sf2` (8,395 bytes)

### Current Accuracy: ~75%

**What's Working** ✓:
- Table structure: 100% - All 9 tables found at correct offsets
- Load address: $0744 (matches)
- Init address: $1209 (matches)
- Wave table: 100% extracted (64 entries)
- Pulse table: 100% extracted (32 entries)
- Instrument count: Correct (25 instruments)

**What's Partial** ⚠:
- Sequence data: ~80% accurate (some control codes misinterpreted)
- Orderlist: ~70% accurate (transpose values need work)
- Commands: ~60% extracted (parameter decoding incomplete)

**What's Missing** ✗:
- Init table: Not extracted (uses default)
- Tempo table: Not extracted (uses default)
- HR table: Not extracted (uses default)

### Extraction Method

**Approach 1: With Reference SF2** (REFERENCE method)
- Use original SF2 as template
- Copy driver code exactly
- Extract only song data from SID
- **Result**: 95-100% accuracy

**Approach 2: Template-Based** (TEMPLATE method)
- Use generic driver template
- Extract tables via pattern matching
- **Result**: 70-80% accuracy

**Approach 3: Laxity Analysis** (LAXITY method)
- For original Laxity NewPlayer files
- Analyze player code to find tables
- Convert Laxity format to SF2
- **Result**: 50-70% accuracy (needs improvement)

---

## General Findings

### Successful Patterns

1. **SF2 Roundtrip**: SF2→SID→SF2 works perfectly (100% accuracy)
2. **Player Detection**: player-id.exe is highly reliable
3. **Table Extraction**: Pattern-based scoring works well for SF2-packed files
4. **Siddump Validation**: Excellent for verifying conversion accuracy

### Remaining Challenges

1. **Laxity Conversion**: Bridging format gaps between Laxity and SF2
2. **Dynamic Data**: Handling runtime-calculated pointers and patterns
3. **Driver Variations**: Supporting all SF2 driver versions (11-16, NP20)
4. **Compressed Patterns**: Efficiently extracting packed sequence data

### Recommendations

1. **Prioritize SF2 roundtrip**: Focus on perfect SF2→SID→SF2 conversion
2. **Improve Laxity converter**: Better format translation for NewPlayer files
3. **Expand driver support**: Test with all driver variations
4. **Automated testing**: Run validation suite on all changes

---

## References

- [SF2 Format Specification](../reference/SF2_FORMAT_SPEC.md)
- [Driver Reference](../reference/DRIVER_REFERENCE.md)
- [Conversion Strategy](../reference/CONVERSION_STRATEGY.md)
- [Stinsen's Player Disassembly](../reference/STINSENS_PLAYER_DISASSEMBLY.md)
- [Validation System](../guides/VALIDATION_GUIDE.md)
- [Accuracy Roadmap](ACCURACY_ROADMAP.md)

---

**Document Status**: Consolidated from 9 analysis documents
**Next Review**: After major conversion improvements
**Maintainer**: SIDM2 Project
