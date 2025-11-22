# SID to SID Factory II Converter

**Version 0.4.0** | Build Date: 2025-11-22

A Python tool for converting Commodore 64 `.sid` files into SID Factory II `.sf2` project files.

## Overview

This converter analyzes SID files that use Laxity's player routine and attempts to extract the music data for conversion to the SID Factory II editable format. It was specifically developed for `Unboxed_Ending_8580.sid` by DRAX (Thomas Mogensen) with player by Laxity (Thomas Egeskov Petersen).

**Note**: This is an experimental reverse-engineering tool. Results may require manual refinement in SID Factory II.

## Installation

No external dependencies required - uses Python standard library only.

```bash
# Requires Python 3.7+
python --version
```

## Usage

### Basic Conversion

```bash
python sid_to_sf2.py <input.sid> [output.sf2] [--driver {np20,driver11}]
```

Examples:
```bash
# Convert using NP20 driver (default, recommended for Laxity files)
python sid_to_sf2.py Unboxed_Ending_8580.sid output.sf2

# Convert using NP20 driver explicitly
python sid_to_sf2.py Unboxed_Ending_8580.sid output.sf2 --driver np20

# Convert using Driver 11
python sid_to_sf2.py Unboxed_Ending_8580.sid output.sf2 --driver driver11
```

### Driver Selection

- **np20** (default) - JCH NewPlayer 20 driver, most similar to Laxity format
- **driver11** - Standard SF2 Driver 11, more features but different instrument format

### Deep Analysis

```bash
python analyze_sid.py <input.sid>
```

### Laxity Format Analysis

```bash
python laxity_analyzer.py <input.sid>
```

### Batch Conversion

Convert all SID files in a directory:

```bash
python convert_all.py [--driver {np20,driver11}] [--input SID] [--output SF2]
```

Examples:
```bash
# Convert all SIDs in SID folder to SF2 folder (default)
python convert_all.py

# Use driver11 instead of np20
python convert_all.py --driver driver11

# Custom input/output directories
python convert_all.py --input my_sids --output converted
```

The batch converter generates three files per SID:
- `.sf2` - SID Factory II project file
- `_info.txt` - Detailed extraction info with all tables
- `.dump` - SID register dump (60 seconds of playback)

#### Info File Contents

The `_info.txt` file contains comprehensive extraction data:

- **Source File**: Filename, name, author, copyright, detected player
- **Memory Layout**: Load/init/play addresses, data size
- **Conversion Result**: Output file, size, driver, tempo, sequence/instrument counts
- **Instruments Table**: All extracted instruments with AD/SR values and names
- **Commands Table**: All 16 commands with usage counts from sequences
- **Wave Table**: Waveform entries with note offsets and descriptions
- **Pulse Table**: Pulse width modulation entries
- **Filter Table**: Filter sweep entries
- **HR/Tempo/Arp/Init Tables**: Additional configuration tables

Example Commands Table output:
```
Idx  Name          Used
  0  Slide Up      -
  1  Slide Down    53x
  2  Vibrato       13x
  3  Portamento    -
  ...
```

## File Formats

### PSID/RSID Format (Input)

The SID file format is the standard for distributing Commodore 64 music. It contains:

#### Header Structure (Version 2)

| Offset | Size | Description |
|--------|------|-------------|
| $00-$03 | 4 | Magic ID: "PSID" or "RSID" |
| $04-$05 | 2 | Version (big-endian) |
| $06-$07 | 2 | Data offset |
| $08-$09 | 2 | Load address (0 = embedded in data) |
| $0A-$0B | 2 | Init address |
| $0C-$0D | 2 | Play address |
| $0E-$0F | 2 | Number of songs |
| $10-$11 | 2 | Start song |
| $12-$15 | 4 | Speed flags |
| $16-$35 | 32 | Song name (null-terminated) |
| $36-$55 | 32 | Author name |
| $56-$75 | 32 | Copyright info |
| $76-$7B | 6 | V2+ flags and SID addresses |
| $7C+ | - | C64 program data |

The C64 data section contains compiled 6502 machine code with the player routine and encoded music data.

### JCH NewPlayer v21 Format (Laxity Player)

JCH NewPlayer v21 was coded by Laxity (Thomas Egeskov Petersen) of Vibrants in 2005. This is the player routine used in many SID files and is directly related to SID Factory II, which Laxity also created.

#### Instrument Format (8 bytes)

| Byte | Description | Notes |
|------|-------------|-------|
| 0 | AD (Attack/Decay) | Standard SID ADSR |
| 1 | SR (Sustain/Release) | Standard SID ADSR |
| 2 | Restart Options / Wave Count Speed | See below |
| 3 | Filter Setting | Low nibble: pass band, High nibble: resonance |
| 4 | Filter Table Pointer | 0 = no filter program |
| 5 | Pulse Table Pointer | Index into pulse table |
| 6 | Pulse Property | Bit 0: reset on instrument only, Bit 1: filter reset control |
| 7 | Wave Table Pointer | Index into wave table |

##### Restart Options (Byte 2)

- Low nibble: Wave count speed
- High nibble: Instrument restart mode
  - `$8x` - Hard restart (fixed)
  - `$4x` - Soft restart (gate off only, no silence)
  - `$2x` - Laxity hard restart (requires bit 7 set: `$Ax` or `$Bx`)
  - `$1x` - Wave generator reset enable
  - `$00` - Gate off 3 frames before next note

#### Wave Table Format

Two bytes per entry:

| Byte | Description |
|------|-------------|
| 0 | Note offset ($80+ = absolute, $7F = jump, $7E = stop) |
| 1 | Waveform ($11=tri, $21=saw, $41=pulse, $81=noise) |

Special note offsets:
- `$7F xx` - Jump to index xx
- `$7E` - Stop processing, keep last entry
- `$80` - Recalculate base note + transpose (for "Hubbard slide" effects)

#### Pulse Table Format (4 bytes per entry)

| Byte | Description |
|------|-------------|
| 0 | Pulse value ($FF = keep current) |
| 1 | Count value |
| 2 | Duration (bits 0-6) and direction (bit 7) |
| 3 | Next pulse table entry (absolute index) |

#### Filter Table Format (4 bytes per entry)

| Byte | Description |
|------|-------------|
| 0 | Filter value ($FF = keep current) |
| 1 | Count value |
| 2 | Duration |
| 3 | Next filter table entry (absolute index) |

The first entry (4 bytes) is used for alternative speed (break speeds).

#### Super Commands

| Command | Description |
|---------|-------------|
| `$0x yy` | Slide up speed $xyy |
| `$2x yy` | Slide down speed $xyy |
| `$4x yy` | Invoke instrument x with alternative wave pointer yy |
| `$60 xy` | Vibrato (x=frequency, y=amplitude) |
| `$8x xx` | Portamento speed $xxx |
| `$9x yy` | Set D=x and SR=yy (persistent) |
| `$Ax yy` | Set D=x and SR=yy directly (until next note) |
| `$C0 xx` | Set channel wave pointer directly to xx |
| `$Dx yy` | Set filter/pulse (x=0: filter ptr, x=1: filter value, x=2: pulse ptr) |
| `$E0 xx` | Set speed to xx |
| `$F0 xx` | Set master volume |

#### Speed Settings

- Speeds below $02 use alternative speed lookup in filter table
- Speed lookup table contains up to 4 entries (wraps around)
- Write $00 as wrap-around mark for shorter tables

#### Memory Layout (Typical Laxity SID)

| Address | Content |
|---------|---------|
| $1000 | JMP init_routine |
| $1003 | JMP play_routine |
| $1006-$103F | Header data and text |
| $1040-$10C5 | Init routine |
| $10C6-$17FF | Player code |
| $1800-$19FF | Tables and configuration |
| $1A00+ | Instrument table (interleaved AD/SR/CTRL) |
| ... | Orderlists and sequences |

### SID Factory II Format (Output)

SF2 files are PRG files containing a driver plus structured music data. The format uses a block-based header system.

#### File Structure

| Section | Description |
|---------|-------------|
| Load address | 2 bytes (little-endian) |
| Driver code | Player routine (~2KB) |
| Header blocks | Configuration and pointers |
| Music data | Sequences, orderlists, tables |
| Auxiliary data | Metadata and descriptions |

#### Header Block IDs

| ID | Description |
|----|-------------|
| 1 | Descriptor (driver info) |
| 2 | Driver Common (addresses) |
| 3 | Driver Tables (table definitions) |
| 4 | Instrument Descriptor |
| 5 | Music Data (pointers) |
| 6 | Table Color Rules |
| 7 | Insert/Delete Rules |
| 8 | Action Rules |
| 9 | Instrument Data Descriptor |
| 255 | End marker |

#### Music Data Structure

The MusicData block defines:
- Track count (typically 3 for SID)
- Order list pointers (low/high tables)
- Sequence pointers (low/high tables)
- Order list and sequence data locations

#### SF2 Event Format

SF2 sequences use a different triplet order than the Laxity player:

| Byte | Description | Range |
|------|-------------|-------|
| 1 | Instrument | $80 (--), $A0-$BF (instrument+$A0) |
| 2 | Command | $80 (--), $C0+ (command index+$C0) |
| 3 | Note | $00-$5D (notes), $7E (+++), $7F (end) |

#### Table Types

| Type | Description |
|------|-------------|
| Instruments | ADSR, waveform, pulse settings |
| Commands | Effect definitions (slide, vibrato, etc.) |
| Wave | Waveform table |
| Pulse | Pulse width modulation |
| Filter | Filter settings |
| HR (High Resolution) | Fine-tuning |
| Arpeggio | Arpeggio patterns |
| Tempo | Speed settings |
| Init | Initialization data |

### SF2 Driver Formats

#### NP20 Driver (NewPlayer 20 - Recommended)

The NP20 driver is derived from JCH NewPlayer and is the closest match to Laxity's format. Load address: `$0D7E`.

##### NP20 Instrument Format (8 bytes, column-major)

| Column | Description |
|--------|-------------|
| 0 | AD (Attack/Decay) |
| 1 | SR (Sustain/Release) |
| 2 | Wave table index |
| 3 | Pulse table index |
| 4 | Filter table index |
| 5 | Command |
| 6 | Vibrato |
| 7 | Command value |

##### NP20 Commands (2 columns)

| Column | Description |
|--------|-------------|
| 0 | Command byte |
| 1 | Parameter value |

#### Driver 11 (Standard SF2 Driver)

The standard SID Factory II driver with more features but a different instrument format. Load address: `$0D7E`.

##### Driver 11 Instrument Format (6 bytes, column-major)

| Column | Description | Notes |
|--------|-------------|-------|
| 0 | AD (Attack/Decay) | Standard SID ADSR |
| 1 | SR (Sustain/Release) | Standard SID ADSR |
| 2 | Flags | `$80`=hard restart, `$40`=filter, `$20`=filter enable, `$10`=osc reset, `$0x`=HR index |
| 3 | Filter table index | |
| 4 | Pulse table index | |
| 5 | Wave table index | |

##### Driver 11 Commands (3 columns)

| Column | Description |
|--------|-------------|
| 0 | Command byte |
| 1 | Parameter 1 |
| 2 | Parameter 2 |

### Format Mapping

When converting from Laxity SID to SF2, the following mappings are applied:

#### Laxity → NP20 Mapping

| Laxity | NP20 Column | Notes |
|--------|-------------|-------|
| AD | 0 | Direct copy |
| SR | 1 | Direct copy |
| Wave table ptr | 2 | Converted to wave table index |
| Pulse table ptr | 3 | Direct copy |
| Filter ptr | 4 | Direct copy |
| - | 5-7 | Set to 0 (no command/vibrato) |

#### Laxity → Driver 11 Mapping

| Laxity | Driver 11 Column | Notes |
|--------|------------------|-------|
| AD | 0 | Direct copy |
| SR | 1 | Direct copy |
| Restart options | 2 | Converted to flags |
| Filter ptr | 3 | Direct copy |
| Pulse table ptr | 4 | Direct copy |
| Wave table ptr | 5 | Converted to wave table index |

#### SF2 Wave Table Format

The SF2 wave table uses a column-major storage format with 2 columns:

| Column | Description |
|--------|-------------|
| 0 | Note offset / Control byte |
| 1 | Waveform value |

##### Column 0 - Note Offset / Control Bytes

| Value | Description |
|-------|-------------|
| $00 | No transpose (play base note) |
| $01-$7D | Semitone offset (positive transpose) |
| $7E | End/Hold - stop processing, keep last entry |
| $7F | Jump - next byte is target index |
| $80 | Recalculate base note + transpose (for Hubbard slide effects) |
| $81-$FF | Absolute note values (no transpose applied) |

##### Column 1 - Waveform Values

| Value | Description |
|-------|-------------|
| $11 | Triangle + Gate |
| $21 | Sawtooth + Gate |
| $41 | Pulse + Gate |
| $81 | Noise + Gate |
| $10/$20/$40/$80 | Same waveforms without gate (gate off) |

##### Wave Table Example

```
Index  Col0  Col1  Description
  0    $00   $41   Note offset 0, Pulse+Gate
  1    $7F   $00   Jump to index 0 (loop)
  2    $00   $21   Note offset 0, Saw+Gate
  3    $7F   $02   Jump to index 2 (loop)
  4    $00   $11   Note offset 0, Tri+Gate
  5    $7F   $04   Jump to index 4 (loop)
```

Instruments reference wave table entries by their index. The wave table allows complex sequences like:
- Waveform changes over time (attack transient with noise, then pulse)
- Arpeggio effects using note offsets
- Hard restart patterns

#### Default Wave Table Index Mapping

When converting from Laxity format, instruments using simple waveforms are mapped to default wave table indices:

| Waveform | Default Index | Wave Table Entry |
|----------|---------------|------------------|
| Pulse ($41) | 0 | Loop at index 0 |
| Saw ($21) | 2 | Loop at index 2 |
| Triangle ($11) | 4 | Loop at index 4 |
| Noise ($81) | 6 | Loop at index 6 |

## Converter Architecture

### Components

1. **SIDParser** - Parses PSID/RSID headers and extracts C64 data
2. **LaxityPlayerAnalyzer** - Analyzes player format and extracts music data
3. **SF2Writer** - Generates SF2 files using template approach

### Data Flow

```
SID File → SIDParser → LaxityPlayerAnalyzer → ExtractedData → SF2Writer → SF2 File
```

### Extraction Process

1. Parse PSID header for metadata and addresses
2. Load C64 data into virtual memory
3. Scan for sequence data patterns
4. Identify instrument tables
5. Extract and convert to SF2 format
6. Generate output using template

## Development

### Running Tests

```bash
# Run unit tests
python test_converter.py

# Run SF2 format validation (aux pointer check)
python test_sf2_format.py
```

All 34 unit tests should pass:
- SID parsing tests
- Memory access tests
- Data structure tests
- Integration tests with real SID files
- SF2 writing tests
- Instrument encoding tests
- Feature validation tests (instruments, commands, tempo, tables)

The SF2 format test validates:
- **Aux pointer validation**: Ensures aux pointer doesn't point to valid aux data (which crashes SID Factory II)
- **File structure comparison**: Compares orderlist and sequence pointers with templates

### CI/CD Pipeline

#### Local CI

Run all checks locally before pushing:

```bash
# Run checks only
python scripts/ci_local.py

# Run checks and push to git
python scripts/ci_local.py --push --message "Your commit message"

# Windows batch file
scripts\run_ci.bat --push -m "Your commit message"
```

The local CI performs:
1. Python syntax check
2. Docstring validation
3. Documentation checks
4. Unit tests (17 tests)
5. Smoke test with real SID file

#### GitHub Actions

The project includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs:

- **Tests**: Runs on multiple Python versions (3.8-3.12) and OS (Ubuntu, Windows)
- **Linting**: flake8 and pylint checks
- **Documentation**: Validates README sections and docstrings
- **Security**: Bandit security scan
- **Release**: Creates release artifacts on master push

### Project Structure

```
SIDM2/
├── sid_to_sf2.py        # Main converter
├── convert_all.py       # Batch converter
├── analyze_sid.py       # Deep analysis tool
├── laxity_analyzer.py   # Laxity format analyzer
├── laxity_parser.py     # Laxity format parser
├── test_converter.py    # Unit tests
├── test_sf2_format.py   # SF2 format validation tests
├── README.md            # This file
├── CONTRIBUTING.md      # Contribution guidelines
├── SID/                 # Input SID files
├── SF2/                 # Output SF2 files
└── tools/               # Analysis tools
    ├── siddump.exe      # SID register dump tool
    ├── player-id.exe    # Player identification tool
    └── cpu.c            # 6502 CPU emulator source
```

## Tools

### siddump

A 6502 CPU emulator that executes SID player code and captures register writes. Source code in `tools/cpu.c` and `tools/siddump.c`.

```bash
tools/siddump.exe <sidfile> [options]
```

Options:
- `-a<value>` - Subtune number (default 0)
- `-t<value>` - Playback time in seconds (default 60)
- `-f<value>` - First frame to display
- `-l` - Low-resolution mode
- `-n<value>` - Note spacing
- `-p<value>` - Pattern spacing
- `-s` - Time in minutes:seconds:frame format
- `-z` - Include CPU cycles and raster time
- `-c<hex>` - Recalibrate frequency table
- `-d<hex>` - Calibration note (default $B0 = middle C)

Output shows per-frame SID register state:
- 3 voices: Frequency, Note, Waveform, ADSR, Pulse width
- Filter: Cutoff, Resonance/Control, Type, Volume

### player-id

Identifies the player routine used in a SID file.

```bash
tools/player-id.exe <sidfile>
```

### 6502 CPU Emulator

The `cpu.c` file contains a complete 6502 CPU emulator with:
- All standard opcodes (ADC, SBC, AND, ORA, EOR, etc.)
- Common illegal opcodes (LAX)
- Accurate cycle counting with page-crossing penalties
- Decimal mode support for ADC/SBC

Key registers:
- `pc` - Program Counter (16-bit)
- `a`, `x`, `y` - Accumulator and index registers (8-bit)
- `sp` - Stack pointer (8-bit)
- `flags` - N, V, B, D, I, Z, C status flags
- `mem[0x10000]` - 64KB memory

### Adding New Features

1. Create feature branch
2. Write tests first (TDD approach)
3. Implement feature
4. Update documentation
5. Run all tests
6. Submit pull request

## Limitations

### Extracted Tables

The converter now extracts and injects all major table types:

| Table | Status | Description |
|-------|--------|-------------|
| Instruments | ✓ Full | 8-byte Laxity format with ADSR, wave/pulse/filter pointers |
| Wave | ✓ Full | Note offset + waveform pairs with jump/end markers |
| Pulse | ✓ Full | 4-byte entries: value, count, duration, next index |
| Filter | ✓ Full | 4-byte entries: value, count, duration, next index |
| Commands | ✓ Names | Command names injected via auxiliary data |
| HR | ✓ Basic | Hard restart table with default values |
| Tempo | ✓ Full | Speed value extracted from SID |
| Arp | ✓ Default | Default arpeggio patterns (major, minor, octave) |
| Init | - | Not available in NP20 driver |

### Current Limitations

- **Single player support**: Optimized for Laxity NewPlayer v21 only
- **Some tables use defaults**: Init and Arp may need manual editing
- **Manual refinement needed**: Output may require editing in SF2

### Known Issues

- **Aux pointer compatibility**: SF2 files have aux pointer set to $0000 to prevent SID Factory II crashes
- **Driver 11 instruments**: Converted instruments may differ from manually created ones in original SF2 project files
- **Multi-speed tunes**: Songs with multiple play calls per frame may not play at correct speed

### Why Full Conversion is Difficult

1. **Compiled format**: SID files contain machine code, not source data
2. **Player-specific encoding**: Each player routine uses different formats
3. **Lost information**: Compilation process discards editable structure
4. **Complex mapping**: Laxity player → SF2 format requires reverse engineering

## Results

### Unboxed_Ending_8580.sid Analysis

- **Load address**: $1000
- **Data size**: 4512 bytes
- **Sequences extracted**: 13
- **Instruments extracted**: 32
- **Orderlists created**: 3

### Output

The converter generates an SF2 file that:
- Is loadable in SID Factory II
- Contains extracted sequence data
- Has basic instrument definitions
- Requires manual refinement for playability

## Improvements Roadmap

### Completed (v0.4.0)

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 1 | Fix Omniphunk ADSR extraction | ✅ Done | Siddump ADSR merging achieves 100% accuracy |
| 2 | Ring Modulation waveform support | ✅ Done | Added 0x14, 0x15, 0x34, 0x35 with ring mod bit |
| 3 | Improve pulse table extraction | ✅ Done | Better pulse modulation pattern detection |
| 26 | Fix SF2 aux pointer crash | ✅ Done | Aux pointer no longer points to valid aux data |
| 27 | SF2 format validation test | ✅ Done | test_sf2_format.py validates aux pointer safety |

### Completed (v0.3.0)

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 13 | SF2 metadata from SID header | ✅ Done | Song name, author, copyright embedded in SF2 |
| 17 | Improved instrument naming | ✅ Done | Better heuristics (Bass, Lead, Pad, Perc, Stab, Pluck) + waveform type |
| 21 | Cross-reference validation | ✅ Done | Validates wave table, instruments, sequences, orderlists |
| 15 | Validation report file | ✅ Done | Outputs detailed report to SF2/validation_report.txt |
| 11 | Wave table debug info | ✅ Done | Shows top candidates and scores in info files |
| 1 | Fix Clarencio wave table | ✅ Done | Improved scoring algorithm with variety bonus |

### High Priority - Next Improvements

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 4 | Multi-speed tune support | 🔄 Pending | Handle tunes with multiple play calls per frame |
| 5 | Proper filter table extraction | 🔄 Pending | Filter sweeps and resonance settings |
| 28 | Support more player formats | 🔄 Pending | Add support for GoatTracker, JCH, DMC players |
| 29 | Sequence optimization | 🔄 Pending | Remove redundant commands, optimize sequence data |
| 30 | Better loop detection | 🔄 Pending | Detect and mark proper loop points in orderlists |

### Medium Priority

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 6 | Auto-detect player variant | 🔄 Pending | Distinguish NP20, NP21, other Laxity versions |
| 7 | Additional Laxity commands | 🔄 Pending | Support unmapped sequence commands |
| 8 | Better Set ADSR matching | 🔄 Pending | Track dynamic ADSR changes in sequences |
| 9 | Tempo detection | 🔄 Pending | Extract actual tempo from song data |
| 10 | Vibrato parameters | 🔄 Pending | Extract depth/speed settings |
| 11 | Portamento parameters | 🔄 Pending | Extract slide speed from commands |
| 12 | Hard restart timing | 🔄 Pending | Detect different HR timing per song |
| 31 | GUI interface | 🔄 Pending | Simple tkinter GUI for batch conversion |
| 32 | Direct SF2 editing | 🔄 Pending | Modify existing SF2 files without full reconversion |

### Low Priority

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 14 | Sequence deduplication | 🔄 Pending | Detect and merge duplicate sequences |
| 15 | Subtune support | 🔄 Pending | Handle SID files with multiple songs |
| 16 | Orderlist loop detection | 🔄 Pending | Identify loop points for proper playback |
| 18 | Command usage statistics | 🔄 Pending | Show which SF2 commands are used |
| 19 | Combined waveform transitions | 🔄 Pending | Handle Tri+Saw, Tri+Pulse in wave table |
| 20 | Pulse width range detection | 🔄 Pending | Determine min/max pulse per instrument |
| 33 | Export to other formats | 🔄 Pending | Export to GoatTracker .sng or MIDI |
| 34 | Batch validation report | 🔄 Pending | Generate HTML report for all conversions |
| 35 | Instrument preset library | 🔄 Pending | Common C64 instrument presets |

### Validation Enhancements

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 22 | Validate command parameters | 🔄 Pending | Check slide/vibrato values in valid ranges |
| 23 | Note range validation | 🔄 Pending | Ensure notes are within playable range |
| 24 | Filter cutoff validation | 🔄 Pending | Compare filter table against usage |
| 25 | Timing accuracy check | 🔄 Pending | Frame-by-frame output timing comparison |

### Current Validation Scores

| Song | Score | Issues |
|------|-------|--------|
| Angular | 100% | 0 |
| Clarencio_extended | 100% | 0 |
| Ocean_Reloaded | 100% | 0 |
| Omniphunk | 100% | 0 |
| Phoenix_Code_End_Tune | 100% | 0 |
| Unboxed_Ending_8580 | 100% | 0 |
| **Average** | **100%** | |

All files now achieve 100% validation score with siddump ADSR merging and improved wave table extraction.

### Code Quality Improvements

| # | Improvement | Status | Effort | Impact | Description |
|---|-------------|--------|--------|--------|-------------|
| 36 | Implement proper logging | ✅ Done | 2-3h | High | Replace ~70+ print() calls with Python logging module |
| 37 | Add type hints | ✅ Done | 4-6h | High | Add type annotations to all public functions in sidm2/ |
| 38 | Error handling in extraction | ✅ Done | 6-8h | Critical | Raise specific exceptions instead of returning None |
| 39 | Subprocess error handling | 🔄 Pending | 3-4h | Medium | Proper error handling for siddump.exe, player-id.exe |
| 40 | Data validation | 🔄 Pending | 5-6h | Critical | Validate SequenceEvent, ExtractedData at creation |
| 41 | Test coverage for edge cases | 🔄 Pending | 4-5h | High | Add tests for corrupted files, empty data, missing templates |
| 42 | Configuration system | 🔄 Pending | 3-4h | Medium | ConversionOptions class for customizable SF2 generation |

### Architecture Improvements (Completed)

| # | Improvement | Status | Description |
|---|-------------|--------|-------------|
| 43 | Modularize sid_to_sf2.py | ✅ Done | Extracted to sidm2/ package (3600→139 lines) |
| 44 | Consolidate duplicate scripts | ✅ Done | Removed 13 duplicate analysis scripts |
| 45 | Extract constants | ✅ Done | Magic numbers moved to sidm2/constants.py |
| 46 | Add documentation | ✅ Done | Created docs/ folder with comprehensive guides |
| 47 | SF2Writer modularization | ✅ Done | Extracted ~960 lines to sidm2/sf2_writer.py |

## Changelog

### v0.4.0 (2025-11-22)
- Fixed SF2 crash issue caused by aux pointer pointing to valid aux data
- Added aux pointer validation test (`test_sf2_format.py`)
- Added Ring Modulation waveform support ($14, $15, $34, $35)
- Improved ADSR extraction with siddump merging
- Improved pulse table extraction scoring
- All converted files now pass SF2 format validation
- Current validation status: All files load in SID Factory II

### v0.3.0 (2025-11-22)
- Added SF2 metadata embedding (song name, author, copyright)
- Improved instrument naming with ADSR heuristics and waveform types
- Added cross-reference validation for wave tables and sequences
- Added validation report file output
- Added wave table debug info with candidate scores
- Fixed wave table extraction scoring algorithm
- Added variety bonus for better wave table selection
- Added sync waveform support (0x42, 0x43, etc.)
- Current average validation score: 91.2%

### v0.2.0 (2025-11-21)
- Full table extraction (instruments, wave, pulse, filter)
- Batch conversion support with convert_all.py
- Info file generation with detailed extraction data
- siddump integration for validation
- Validation script for comparing extraction vs playback

### v0.1.0 (2025-11-20)
- Initial release
- Basic SID to SF2 conversion
- Laxity NewPlayer v21 support
- NP20 and Driver11 template support

## References

- [SID Factory II GitHub](https://github.com/Chordian/sidfactory2)
- [High Voltage SID Collection](https://www.hvsc.c64.org/)
- [PSID File Format](https://www.hvsc.c64.org/download/C64Music/DOCUMENTS/SID_file_format.txt)
- [Codebase64 SID Programming](https://codebase64.org/doku.php?id=base:sid_programming)

## Credits

- **DRAX** (Thomas Mogensen) - Composer of Unboxed Ending
- **Laxity** (Thomas Egeskov Petersen) - Player routine and SID Factory II creator
- **SID Factory II Team** - For the excellent music editor

## License

This tool is provided for educational and personal use. Please respect the copyrights of original music and software.

---

*This converter was created to help preserve and study Commodore 64 music.*
