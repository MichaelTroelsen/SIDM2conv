# SID to SID Factory II Converter

[![Tests](https://github.com/MichaelTroelsen/SIDM2conv/actions/workflows/test.yml/badge.svg)](https://github.com/MichaelTroelsen/SIDM2conv/actions/workflows/test.yml)

**Version 0.7.0** | Build Date: 2025-11-26

A Python tool for converting Commodore 64 `.sid` files into SID Factory II `.sf2` project files.

## Overview

This converter analyzes SID files that use Laxity's player routine and attempts to extract the music data for conversion to the SID Factory II editable format. It was specifically developed for `Unboxed_Ending_8580.sid` by DRAX (Thomas Mogensen) with player by Laxity (Thomas Egeskov Petersen).

**Note**: This is an experimental reverse-engineering tool. Results may require manual refinement in SID Factory II.

## Installation

No external dependencies required for basic conversion - uses Python standard library only.

```bash
# Requires Python 3.7+
python --version
```

### Optional Dependencies for Automated Testing

To run the automated editor validation tests, install additional dependencies:

```bash
pip install -r requirements-test.txt
```

This includes:
- `pyautogui` - Keyboard/mouse automation
- `Pillow` - Screenshot capture
- `pywin32` - Windows API integration

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

### Batch Conversion

Convert all SID files in a directory:

```bash
python convert_all.py [--input SID] [--output output] [--roundtrip]
```

Examples:
```bash
# Convert all SIDs in SID folder to output folder (generates both NP20 and Driver 11)
python convert_all.py

# Custom input/output directories
python convert_all.py --input my_sids --output my_output

# Include round-trip validation (SID→SF2→SID verification)
python convert_all.py --roundtrip

# Custom validation duration (default: 10 seconds)
python convert_all.py --roundtrip --roundtrip-duration 30
```

The batch converter creates a nested structure: `output/{SongName}/New/` containing:
- `{name}_g4.sf2` - SID Factory II project file (NP20/G4 driver)
- `{name}_d11.sf2` - SID Factory II project file (Driver 11, default for validation)
- `{name}_info.txt` - Detailed extraction info with all tables
- `{name}.dump` - SID register dump (60 seconds of playback)

Round-trip validation creates additional folders:
- `output/{SongName}/Original/` - Original SID, WAV, dump, and info
- `output/{SongName}/New/` - Converted files plus exported SID for comparison
- `output/{SongName}/{name}_roundtrip_report.html` - Detailed comparison report

### Round-trip Validation

Test the complete conversion pipeline (SID→SF2→SID):

```bash
python test_roundtrip.py <input.sid> [--duration 30]
```

This validates that:
1. SID converts to SF2 successfully
2. SF2 packs back to SID with proper code relocation
3. Audio output matches between original and converted files
4. Register writes are preserved correctly

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

**Note**: Laxity format stores (note, waveform) but SF2 format stores (waveform, note). The converter swaps these bytes during conversion, except for `$7F` jump commands which remain as ($7F, target).

#### Pulse Table Format (4 bytes per entry, Y-indexed with stride 4)

The pulse table uses column-major storage with Y register indexing. Entry indices are pre-multiplied by 4.

| Byte | Description |
|------|-------------|
| 0 | Initial pulse value: hi nibble → $D402 (lo byte), lo nibble → $D403 (hi byte), or $FF = keep current |
| 1 | Add/subtract value per frame (applied to 16-bit pulse width) |
| 2 | Duration (bits 0-6) + direction (bit 7: 0=add, 1=subtract) |
| 3 | Next entry index (pre-multiplied by 4, e.g., entry 6 = $18) |

**Index Conversion**: When converting to SF2, all Y*4 indices must be divided by 4. This applies to:
- Pulse table "next" column (byte 3)
- Instrument pulse_ptr field

##### Pulse Table Example

```
Entry 0 (Y=$00): 08 00 00 00  ; Pulse=$0800, no modulation, loop to self
Entry 6 (Y=$18): 04 50 30 1C  ; Pulse=$0400, add $50/frame for 48 frames, then entry 7
Entry 7 (Y=$1C): FF 50 B0 18  ; Keep current, sub $50/frame for 48 frames, loop to entry 6
```

This creates a ping-pong pulse width modulation effect, sweeping from $0400 to $0850 and back.

#### Filter Table Format (4 bytes per entry)

| Byte | Description |
|------|-------------|
| 0 | Filter value ($FF = keep current) |
| 1 | Count value |
| 2 | Duration |
| 3 | Next filter table entry (absolute index) |

The first entry (4 bytes) is used for alternative speed (break speeds).

#### Super Commands

*Complete reference from JCH NewPlayer v21.g5 Final - (D) = Direct command, lasts until next note*

| Command | Description |
|---------|-------------|
| `$0x yy` | (D) Slide up speed $xyy |
| `$1? ??` | Free |
| `$2x yy` | (D) Slide down speed $xyy |
| `$3? ??` | Free |
| `$4x yy` | Invoke instrument x (00-1f) with alternative wave pointer yy |
| `$60 xy` | (D) Vibrato (x=frequency, y=amplitude) - canceled by note or slide |
| `$7? ??` | Free |
| `$8x xx` | Portamento speed $xxx |
| `$9x yy` | Set D=x and SR=yy (persistent until instrument change) |
| `$Ax yy` | (D) Set D=x and SR=yy directly (until next note) |
| `$b? ??` | Free |
| `$C0 xx` | (D) Set channel wave pointer directly to xx |
| `$Dx yy` | (D) Set filter/pulse (x=0: filter ptr, x=1: filter value, x=2: pulse ptr) |
| `$E0 xx` | Set speed to xx |
| `$F0 xx` | Set master volume |

#### Speed Settings

- Speeds below $02 use alternative speed lookup in filter table
- Speed lookup table contains up to 4 entries (wraps around)
- Write $00 as wrap-around mark for shorter tables
- Speeds of $01 in table are clamped to $02

#### Vibrato and Slide Special Cases

Vibrato and slides only apply to wave table entries with note offset = $00.

Special value $80 in wave table recalculates base note + transpose (enables "Hubbard slide" effect).

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

#### SF2 Table Details

##### Commands Table
The commands table is referenced from the middle numeric column in sequences. Because of this, **it is not possible to insert or delete rows** - all commands must be edited in place.

Press F12 in SID Factory II to open an expanded overlay showing the commands offered by the currently loaded driver (displayed in magenta).

##### Instruments Table
Instruments are referenced from the left numeric column in sequences - like commands, **you cannot insert or delete rows**.

The number of bytes and their purpose depends on the currently loaded driver, but typically includes:
- ADSR values (Attack, Decay, Sustain, Release)
- Index pointers to support tables (wave, pulse, filter)

**Tip**: Place cursor on an index pointer value and press Ctrl+Enter to jump to that row in the referenced table.

##### Wave Table
The wave table sets the waveform (left column) and semitone offset (right column).

Format: `WW NN` where:
- `WW` = Waveform ($11=tri, $21=saw, $41=pulse, $81=noise)
- `NN` = Semitone offset (e.g., $0C = +12 semitones = one octave higher)

Special values:
- Add $80 to the note value for **static/absolute notes** (great for drums)
- `7F xx` = Jump to row xx (e.g., `7F 02` wraps to row 3)

##### Pulse Table
The pulse table defines pulse width modulation for waveform $41 and combined waveforms. It controls:
- Range of pulse width sweep
- Speed of the sweep effect

Press F12 for an expanded overlay explaining pulse commands (displayed in pink).

Some drivers use a simpler one or two byte pulsating effect defined directly in the instrument.

##### Filter Table
The filter table defines filter cutoff range and sweep speeds. Unlike pulse, **the SID filter is a global effect** applied to channels via a bit mask:

| Bit | Value | Channel |
|-----|-------|---------|
| 0 | 1 | Channel 1 |
| 1 | 2 | Channel 2 |
| 2 | 4 | Channel 3 |

Examples:
- 3 (1+2) = Filter on channels 1 and 2
- 4 = Filter on channel 3 only
- 7 (1+2+4) = Filter on all channels

Press F12 for filter command details (displayed in orange).

Note: Some drivers have no filter capabilities.

##### Arpeggio Table
The arpeggio table creates chord effects by rapidly cycling through semitone offsets. Values are added to the note in the sequence.

Press F12 for arpeggio details (displayed in green).

In driver 11, arpeggio only affects wave table entries where the semitone value is $00. Other values ignore arpeggio.

##### Init Table
The init table points to a tempo table row and sets the main volume (e.g., `00 0F` for maximum volume). Multiple entries support multi-songs.

Press F12 for init details (displayed in white outline).

##### HR (Hard Restart) Table
Hard restart defeats the SID chip's "ADSR bug" - a timing issue that causes notes to stumble when playing rapid sequences (called "the school band effect" by Martin Galway).

**How it works**: The driver gates off and resets ADSR values a few frames before the next note triggers. In most SF2 drivers, this happens exactly 2 frames before.

Example: A note lasting 15 frames will:
1. Play with instrument ADSR for 13 frames
2. Hard restart takes over for final 2 frames
3. Gates off and applies HR table ADSR (typically `0F 00` for fast decay)
4. Next note triggers with stable ADSR

The HR table defines this pre-note ADSR. Default value `0F 00` brings notes down quickly. Advanced users can experiment with different values or create multiple HR entries for different instruments.

Press F12 for HR details (displayed in cyan).

##### Tempo Table
The tempo table defines song speed as **frames per row**. Frames update at 50Hz (PAL) or 60Hz (NTSC).

- Smaller values = faster tempo
- Minimum practical value is usually $02 (due to hard restart timing)
- Chain multiple values with `7F` wrap to create shuffle rhythms or fractional speeds (e.g., 2½)

Example tempo chains:
- `02 7F 00` = Constant speed 2
- `02 03 7F 00` = Alternating 2-3 for shuffle feel
- `02 02 03 7F 00` = 2⅓ average speed

### SF2 Driver Formats

#### NP20 Driver (NewPlayer 20 - Recommended)

The NP20 driver is derived from JCH NewPlayer and is the closest match to Laxity's format. Load address: `$0D7E`.

##### NP20 Instrument Format (8 bytes, column-major)

| Column | Description |
|--------|-------------|
| 0 | AD (Attack/Decay) |
| 1 | SR (Sustain/Release) |
| 2 | Reserved |
| 3 | Reserved |
| 4 | Wave table index |
| 5 | Pulse table index |
| 6 | Filter table index |
| 7 | Reserved |

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
| - | 2-3 | Reserved (set to 0) |
| Wave table ptr | 4 | Direct copy |
| Pulse table ptr | 5 | Divided by 4 (Y*4 to direct index) |
| Filter ptr | 6 | Direct copy |
| - | 7 | Reserved (set to 0) |

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
| 0 | Waveform value / Control byte ($7F) |
| 1 | Note offset / Jump target |

**Important**: SF2 format stores waveform in column 0 and note in column 1. For `$7F` jump commands, column 0 contains `$7F` and column 1 contains the target index.

##### Column 0 - Waveform / Control Values

| Value | Description |
|-------|-------------|
| $11 | Triangle + Gate |
| $21 | Sawtooth + Gate |
| $41 | Pulse + Gate |
| $81 | Noise + Gate |
| $10/$20/$40/$80 | Same waveforms without gate (gate off) |
| $7F | Jump command - column 1 contains target index |

##### Column 1 - Note Offset / Jump Target

| Value | Description |
|-------|-------------|
| $00 | No transpose (play base note) |
| $01-$7D | Semitone offset (positive transpose) |
| $80 | Recalculate base note + transpose (for Hubbard slide effects) |
| $81-$FF | Absolute note values (no transpose applied) |
| (with $7F) | Jump target index |

##### Wave Table Example

```
Index  Col0  Col1  Description
  0    $41   $00   Pulse+Gate, Note offset 0
  1    $7F   $00   Jump to index 0 (loop)
  2    $21   $00   Saw+Gate, Note offset 0
  3    $7F   $02   Jump to index 2 (loop)
  4    $11   $00   Tri+Gate, Note offset 0
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

### SF2 Format Quick Reference

*Based on the official SID Factory II User Manual (2023-09-30)*

#### Key Concepts

**SF2 files are C64 PRG files** - They can run on a C64/emulator with `SYS4093` and also load in the SF2 editor.

**Driver-dependent format** - Table layouts vary by driver. We target **Driver 11** (luxury, full features).

**Template-based** - SF2 files contain driver code plus music data injected into specific offsets.

#### Control Bytes Summary

| Byte | Context | Description |
|------|---------|-------------|
| $7F | Tables | End/jump marker |
| $7E | Sequences | Gate on (+++) |
| $A0 | Order list | No transpose (default) |

#### Gate System

SF2 uses explicit gate control (different from GoatTracker/CheeseCutter):

- `+++` - Gate on (sustain note)
- `---` - Gate off (release)
- `**` - Tie note (no envelope restart)

#### Hard Restart

Prevents the SID "ADSR bug" (Martin Galway's "school band effect"):
- Driver gates off 2 frames before next note
- Applies HR table ADSR (default: `$0F $00`)
- Stabilizes envelope timing

#### Sequence Packing

- Sequences packed in real-time as you edit
- Can be up to 1024 rows (if packed <256 bytes)
- Contiguous stacking per track (like Tetris)

#### Available Drivers

| Driver | Description |
|--------|-------------|
| 11 | Standard luxury (default) - full features |
| 12 | Extremely simple - basic effects only |
| 13 | Rob Hubbard emulation |
| 15/16 | Tiny drivers for size-constrained projects |

#### Multi-Song Support

- F7 opens song management
- Each song has own tempo/volume in Init table
- All songs share sequences and table data

For complete format details, see [docs/SF2_FORMAT_SPEC.md](docs/SF2_FORMAT_SPEC.md).

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

# Run automated editor validation (requires SID Factory II)
python test_sf2_editor.py
```

### Automated Editor Validation

The `test_sf2_editor.py` script validates converted SF2 files by loading them in SID Factory II:

```bash
# Test all SF2 files in SF2/ directory
python test_sf2_editor.py

# Test specific file
python test_sf2_editor.py SF2/Angular.sf2

# Convert SID files first, then test
python test_sf2_editor.py --convert-first

# Skip HTML report generation
python test_sf2_editor.py --no-report
```

The test performs:
1. Launches SID Factory II with each SF2 file
2. Sends space key to start playback
3. Captures screenshot to `SF2/screenshots/`
4. Terminates editor process
5. Generates HTML report at `SF2/validation_report.html`

**Configuration**: Set `Editor.Skip.Intro = 1` in the SID Factory II `config.ini` for faster testing.

**Requirements**:
- SID Factory II installed (default path: `C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\artifacts\`)
- Test dependencies: `pip install -r requirements-test.txt`

### Round-trip Validation

The `test_roundtrip.py` script performs complete round-trip validation by converting SID → SF2 → SID and comparing audio output:

```bash
# Test Angular.sid with 30 seconds duration
python test_roundtrip.py SID/Angular.sid

# Custom duration (seconds)
python test_roundtrip.py SID/Angular.sid --duration 60

# Verbose output
python test_roundtrip.py SID/Angular.sid --verbose
```

The validation performs 7 steps automatically:

1. **SID → SF2**: Converts original SID to SF2 using `sid_to_sf2.py`
2. **SF2 → SID**: Packs SF2 back to SID using `sf2pack` with full 6502 code relocation
3. **Original WAV**: Renders original SID to WAV using `SID2WAV.EXE`
4. **Exported WAV**: Renders exported SID to WAV using `SID2WAV.EXE`
5. **Original Siddump**: Analyzes original SID register writes using `siddump.exe`
6. **Exported Siddump**: Analyzes exported SID register writes using `siddump.exe`
7. **HTML Report**: Generates detailed comparison report

**Output files** (in `roundtrip_output/`):
- `*_converted.sf2` - SF2 conversion from original SID
- `*_exported.sid` - SID packed from SF2 (with code relocation)
- `*_original.wav` - Audio from original SID
- `*_exported.wav` - Audio from exported SID
- `*_original.dump` - Register dump from original SID
- `*_exported.dump` - Register dump from exported SID
- `*_roundtrip_report.html` - Detailed comparison report

**Key Features**:
- Full 6502 code relocation (343 absolute + 114 zero page address patches)
- Frame-by-frame SID register comparison
- WAV file size validation
- Detailed HTML report with metrics

**Requirements**:
- `tools/sf2pack/sf2pack.exe` - SF2 to SID packer (built from source)
- `tools/SID2WAV.EXE` - SID to WAV renderer
- `tools/siddump.exe` - SID register analyzer

All 69 unit tests should pass:
- SID parsing tests (7 tests)
- Memory access tests
- Data structure tests
- Integration tests with real SID files
- SF2 writing tests (2 tests)
- Instrument encoding tests
- Feature validation tests (instruments, commands, tempo, tables)
- Pulse table extraction tests (5 tests)
- Filter table extraction tests (7 tests)
- Sequence parsing edge cases (18 tests)
- Table linkage validation (3 tests)

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
├── test_sf2_editor.py   # Automated editor validation
├── requirements-test.txt # Test dependencies
├── README.md            # This file
├── CONTRIBUTING.md      # Contribution guidelines
├── SID/                 # Input SID files
├── SF2/                 # Output SF2 files
│   └── screenshots/     # Editor screenshots from validation
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

### sf2pack

SF2 to SID packer with full 6502 code relocation. Converts SF2 files back to playable SID format.

```bash
tools/sf2pack/sf2pack.exe <input.sf2> <output.sid> [options]
```

Options:
- `--address ADDR` - Target load address (hex, default: 0x1000)
- `--zp ZP` - Target zero page base (hex, default: 0x02)
- `--title TITLE` - Set PSID title metadata
- `--author AUTHOR` - Set PSID author metadata
- `--copyright TEXT` - Set PSID copyright metadata
- `-v, --verbose` - Verbose output with relocation stats

**Key Features**:
- Full 6502 instruction-by-instruction code scanning
- Relocates absolute addresses (am_ABS, am_ABX, am_ABY, am_IND)
- Adjusts zero page addresses (am_ZP, am_ZPX, am_ZPY, am_IZX, am_IZY)
- Protects ROM addresses ($D000-$DFFF) from modification
- Exports as PSID v2 format with metadata

**Example output**:
```
Processing driver code:
  Driver: $d7e - $157e
  Address delta: 282
  ZP: $2 -> $2
  Relocations: 343 absolute, 114 zero page
  Packed size: 8834 bytes
```

See `tools/sf2pack/README.md` for architecture details and source code documentation.

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

## Extraction Confidence Scoring

The converter uses heuristic-based confidence scoring to identify and extract music data tables from SID files. Each table type has specific scoring criteria.

### Wave Table Confidence

Wave tables are scored based on:

| Criterion | Points | Description |
|-----------|--------|-------------|
| Valid waveforms | +3 each | Standard waveforms ($11, $21, $41, $81) |
| Valid note offsets | +1-2 | Offsets in range 0-24 semitones |
| Loop markers | +5 | $7F jump commands for looping |
| End markers | +3 | $7E stop commands |
| Variety bonus | +5 | Multiple different waveforms |
| Chain patterns | +2 | Valid jump targets |

**Minimum threshold**: Score ≥ 15 to accept extracted table.

### Pulse Table Confidence

Pulse tables use 4-byte entries scored on:

| Criterion | Points | Description |
|-----------|--------|-------------|
| Valid initial value | +2 | $FF (keep) or valid pulse width |
| Moderate add values | +3 | Values 1-15 for smooth modulation |
| Chain patterns | +3 | Valid loop references |
| Duration values | +1 | Reasonable duration (1-64) |
| Subtract patterns | +2 | Negative modulation for PWM |

**Minimum threshold**: Score ≥ 10 and at least 2 valid entries.

### Filter Table Confidence

Filter tables use 4-byte entries scored similarly:

| Criterion | Points | Description |
|-----------|--------|-------------|
| Valid filter values | +2 | Cutoff frequency bytes |
| Moderate deltas | +3 | Smooth sweep values (1-15) |
| Chain patterns | +3 | Valid loop references |
| Duration values | +1 | Reasonable duration |

**Minimum threshold**: Score ≥ 10 and at least 2 valid entries.

### Arpeggio Table Confidence

Arpeggio tables are 4-byte entries (note1, note2, note3, speed) scored on:

| Criterion | Points | Description |
|-----------|--------|-------------|
| Valid note offsets | +2 each | Values 0-24 (2 octave range) |
| Common chord patterns | +3 | Major (0,4,7), minor (0,3,7) |
| Speed values | +1 | Reasonable speed (0-15) |
| Structure validity | +2 | Consistent entry format |

**Minimum threshold**: Score ≥ 15 with at least 2 valid entries.

### Command Table Detection

Commands are detected by analyzing sequence bytes in the $C0-$DF range:

- Counts command usage across all sequences
- Maps to standard SF2 command names (Slide, Vibrato, Portamento, etc.)
- Falls back to default command table if no usage detected

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

### v0.6.0 (2025-11-25)
- Added comprehensive SID accuracy validation system
- Created `validate_sid_accuracy.py` for frame-by-frame register comparison
- Created `sidm2/validation.py` module for pipeline integration
- Integrated 10-second quick validation into convert_all.py pipeline
- Added ACCURACY VALIDATION section to all info.txt files
- Fixed siddump table parser to correctly capture register states
- Established baseline accuracy metrics (9% overall for Angular.sid)
- Created comprehensive validation system documentation
- Removed Unicode emojis for Windows console compatibility

### v0.5.1 (2025-11-23)
- Fixed pulse table extraction to find correct address with improved scoring algorithm
- Fixed pulse table extraction to extract all entries (was stopping early on loops)
- Fixed filter table extraction with pattern-based detection
- Fixed filter table extraction to respect adjacent table boundaries
- Added 12 new tests for pulse/filter table extraction
- Expanded test coverage from 57 to 61 tests
- Improved table extraction scoring with bonuses for chain patterns, $FF values, subtract patterns

### v0.5.0 (2025-11-23)
- Fixed sequence parsing to properly handle instrument bytes (0xA0-0xBF) and command bytes (0xC0-0xCF)
- Added arpeggio table extraction from Laxity sequences
- Added instrument table pointer bounds validation (wave_ptr, pulse_ptr, filter_ptr)
- Added full conversion pipeline integration tests
- Expanded test coverage from 34 to 57 tests
- Added automated editor validation for all converted files
- Added GitHub Actions CI/CD workflow

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
