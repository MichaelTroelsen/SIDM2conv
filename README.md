# SID to SID Factory II Converter

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

#### Wave Table Index Mapping

| Waveform | Index |
|----------|-------|
| Saw ($21) | 0 |
| Pulse ($41) | 2 |
| Triangle ($11) | 4 |
| Noise ($81) | 6 |

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
python test_converter.py
```

All 34 tests should pass:
- SID parsing tests
- Memory access tests
- Data structure tests
- Integration tests with real SID files
- SF2 writing tests
- Instrument encoding tests
- Feature validation tests (instruments, commands, tempo, tables)

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
├── analyze_sid.py       # Deep analysis tool
├── laxity_analyzer.py   # Laxity format analyzer
├── test_converter.py    # Unit tests
├── README.md            # This file
├── CONTRIBUTING.md      # Contribution guidelines
├── Unboxed_Ending_8580.sid  # Sample input
└── sf2driver11_00.prg   # SF2 driver (optional)
```

### Adding New Features

1. Create feature branch
2. Write tests first (TDD approach)
3. Implement feature
4. Update documentation
5. Run all tests
6. Submit pull request

## Limitations

### Current Limitations

- **Template-based output**: Uses existing SF2 file as template
- **Incomplete data injection**: Extracted data shown but not fully injected
- **Single player support**: Optimized for Laxity player only
- **Manual refinement needed**: Output may require editing in SF2

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

## Future Improvements

1. **Full data injection**: Replace template data with extracted music
2. **Pointer table parsing**: Properly identify and use pointer tables
3. **Multiple player support**: Add support for other common players
4. **Better heuristics**: Improve sequence/instrument detection
5. **Validation**: Verify extracted data integrity

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
