# CLAUDE.md - Project Guide for AI Assistants

## Project Overview

SID to SF2 Converter - Converts Commodore 64 SID music files to SID Factory II (.sf2) format for editing and remixing.

## Quick Start

```bash
# Convert single file
python sid_to_sf2.py SID/input.sid output/SongName/New/output.sf2

# Batch convert all SID files (generates both NP20 and Driver 11 versions)
# Creates structure: output/{SongName}/New/{files}
python convert_all.py

# Batch convert with round-trip validation
python convert_all.py --roundtrip

# Test single file round-trip (SID→SF2→SID)
# Creates structure: output/{SongName}/Original/ and /New/
python test_roundtrip.py SID/input.sid
```

## Project Structure

```
SIDM2/
├── sid_to_sf2.py          # Main converter
├── convert_all.py         # Batch conversion script (with SF2→SID export)
├── test_converter.py      # Unit tests (69 tests)
├── test_sf2_format.py     # Format validation tests
├── test_roundtrip.py      # Round-trip validation (SID→SF2→SID)
├── laxity_parser.py       # Dedicated Laxity player parser
├── validate_psid.py       # PSID header validation utility
├── PACK_STATUS.md         # SF2 packer status and test results
├── sidm2/                 # Core package
│   ├── sf2_packer.py      # SF2 to SID packer (NEW v0.6.0)
│   ├── cpu6502.py         # 6502 CPU emulator for pointer relocation
│   └── ...                # Other modules
├── SID/                   # Input SID files
├── output/                # Output folder with nested structure
│   └── {SongName}/        # Per-song directory
│       ├── Original/      # Original SID, WAV, dump (round-trip only)
│       └── New/           # Converted SF2 + exported SID files
├── tools/                 # External tools
│   ├── siddump.exe        # SID register dump tool
│   ├── player-id.exe      # Player identification
│   ├── SID2WAV.EXE        # SID to WAV renderer
│   └── sf2pack/           # C++ SF2 to SID packer (reference)
├── G5/                    # Driver templates
│   ├── drivers/           # SF2 driver PRG files (11, 12, 13, 14, 15, 16, NP20)
│   ├── examples/          # Example SF2 files for each driver
│   └── NewPlayer v21.G5 Final/  # Laxity source format template
├── docs/                  # Documentation
│   ├── SF2_FORMAT_SPEC.md       # Complete SF2 format specification
│   ├── CONVERSION_STRATEGY.md   # Laxity to SF2 mapping
│   ├── DRIVER_REFERENCE.md      # All driver specifications
│   ├── SF2_SOURCE_ANALYSIS.md   # SF2 editor source code analysis
│   └── format-specification.md  # PSID/RSID formats
└── learnings/             # Reference materials and source docs
```

## Key Components

### Main Converter (`sid_to_sf2.py`)
- `SIDParser` class - Parses PSID/RSID headers
- `LaxityPlayerAnalyzer` class - Extracts music data from Laxity player
- `SF2Writer` class - Writes SF2 format using templates
- Table extraction functions for wave, pulse, filter tables

### Python SF2 Packer (`sidm2/sf2_packer.py`) - NEW in v0.6.0
- Pure Python implementation of SF2 to SID packing
- Generates VSID-compatible SID files with correct sound playback
- Uses `sidm2/cpu6502.py` for 6502 instruction-level pointer relocation
- Integrated into `convert_all.py` for automatic SID export
- Average output size: ~3,800 bytes (comparable to manual exports)
- See `PACK_STATUS.md` for implementation details and test results

### External Tools
- `tools/siddump.exe` - Dumps SID register writes (6502 emulator)
- `tools/player-id.exe` - Identifies SID player type
- `tools/SID2WAV.EXE` - Converts SID to WAV audio files
- `validate_psid.py` - PSID header validation utility
- `tools/sf2pack/` - C++ SF2 to SID packer (reference implementation)
  - `sf2pack.exe` - Main packer executable
  - `packer_simple.cpp` - Core relocation logic (343 abs + 114 ZP relocations)
  - `opcodes.cpp` - Complete 256-opcode 6502 lookup table
  - `c64memory.cpp` - 64KB memory management
  - `psidfile.cpp` - PSID v2 file export
- `tools/cpu.c` - 6502 CPU emulator source
- `tools/siddump.c` - Siddump main program source

### Validation Tools

#### SID Accuracy Validation (NEW in v0.6.0)
- `validate_sid_accuracy.py` - Frame-by-frame register comparison tool
  - Compares original SID vs exported SID using siddump register captures
  - Measures Overall (weighted), Frame, Voice, Register, and Filter accuracy
  - Default 30-second validation for detailed analysis
  - Generates accuracy reports with grades (EXCELLENT/GOOD/FAIR/POOR)
  - See `docs/VALIDATION_SYSTEM.md` for architecture details

- `sidm2/validation.py` - Lightweight validation module for pipeline integration
  - `quick_validate()` - 10-second validation for batch processing
  - `generate_accuracy_summary()` - Formats results for info.txt files
  - `get_accuracy_grade()` - Converts accuracy to quality grade
  - Integrated into `convert_all.py` automatically

- Accuracy metrics formula:
  ```
  Overall = Frame×0.40 + Voice×0.30 + Register×0.20 + Filter×0.10
  ```

- Baseline accuracy (v0.6.0):
  - Angular.sid: 9.0% overall (POOR)
  - Target: 99% overall (see `docs/ACCURACY_ROADMAP.md`)

#### Round-trip Validation
- `test_roundtrip.py` - Complete SID→SF2→SID round-trip validation
  - Performs 8-step automated testing (setup, convert, pack, render WAVs, siddump both, report)
  - Generates HTML reports with detailed comparisons
  - Uses siddump for register-level verification
  - Organized output: `roundtrip_output/{SongName}/Original/` and `roundtrip_output/{SongName}/New/`
- `convert_all.py --roundtrip` - Batch conversion with integrated round-trip validation

### Siddump Tool Details

Siddump emulates a 6502 CPU to run SID files and capture register writes frame-by-frame:

```bash
# Basic usage
tools/siddump.exe SID/file.sid > SF2/file.dump

# With timing info
tools/siddump.exe SID/file.sid -z -t30
```

**Key options:** `-a<n>` (subtune), `-t<n>` (seconds), `-z` (cycles)

See `docs/SIDDUMP_ANALYSIS.md` for full source code analysis.

## Supported Formats

**Input**: Laxity NewPlayer v21 SID files only
**Output**: SID Factory II .sf2 format (Driver 11 or NP20)

### Example SID Files

The `SID/` directory contains 7 example files (all Laxity NewPlayer v21):

| File | Description |
|------|-------------|
| Angular.sid | DRAX, 2017 - Primary test file |
| angular_new.sid | Modified Angular version |
| Clarencio_extended.sid | Extended tune |
| Ocean_Reloaded.sid | Ocean loader style |
| Omniphunk.sid | Phunk style |
| Phoenix_Code_End_Tune.sid | End tune |
| Unboxed_Ending_8580.sid | 8580 SID optimized |

See `docs/SID_FILE_ANALYSIS.md` for binary structure analysis using Angular.sid.

## Running Tests

```bash
python test_converter.py
python test_sf2_format.py
```

## CI/CD Rules

**IMPORTANT: Always follow these rules when making changes:**

### 1. Always Run Tests
Before committing any code changes, you MUST:
- Run `python test_converter.py` and ensure all tests pass
- Run `python test_sf2_format.py` for format validation tests
- If tests fail, fix the issues before committing

### 2. Always Update Documentation
When making code changes, you MUST update relevant documentation:
- Update `README.md` if adding/changing features or CLI options
- Update `CLAUDE.md` if changing project structure or conventions
- Update `docs/` files if changing architecture or API
- Keep version numbers in sync across files
- Update improvement status in README when completing items

## Common Tasks

### Adding a new SID file
1. Place .sid file in `SID/` directory
2. Run `python sid_to_sf2.py SID/file.sid SF2/file.sf2`
3. Check `SF2/file_info.txt` for extraction details

### Debugging extraction issues
1. Run `tools/siddump.exe SID/file.sid > SF2/file.dump`
2. Check dump for register patterns
3. Review `SF2/file_info.txt` for table addresses

### Round-trip validation
1. Run `python test_roundtrip.py SID/file.sid`
2. Check `roundtrip_output/file_roundtrip_report.html` for results
3. Compare `file_original.dump` and `file_exported.dump` for register differences
4. Listen to `file_original.wav` and `file_exported.wav` for audio quality

### Packing SF2 back to SID
1. Build sf2pack: `cd tools/sf2pack && mingw32-make`
2. Pack file: `tools/sf2pack/sf2pack.exe SF2/file.sf2 output.sid --title "Title" --author "Author"`
3. Test with VICE: Load output.sid in C64 emulator
4. Verify relocation with `-v` flag for detailed stats

## Known Limitations

- Only supports Laxity NewPlayer v21
- Single subtune per file (multi-song SIDs not supported)
- Init, Arp, HR tables use defaults (not extracted)
- Command parameters not fully extracted

## Code Conventions

- Memory addresses as hex: `0x1000`, `0x1AF3`
- Table sizes: typically 32, 64, or 128 entries
- Control bytes: `0x7F` (end), `0x7E` (loop)
- Waveforms: `0x01` (triangle), `0x10` (triangle+gate), `0x11` (pulse), etc.

## Important Constants

```python
# SF2 structure offsets (Driver 11)
SEQUENCE_TABLE_OFFSET = 0x0903
INSTRUMENT_TABLE_OFFSET = 0x0A03
WAVE_TABLE_OFFSET = 0x0B03
PULSE_TABLE_OFFSET = 0x0D03
FILTER_TABLE_OFFSET = 0x0F03

# Laxity player markers
LAXITY_INIT_PATTERN = [0xA9, 0x00, 0x8D]  # LDA #$00, STA

# Laxity NewPlayer v21 memory layout (from angular.asm disassembly)
LAXITY_INIT_ADDR = 0x1000        # Init routine entry
LAXITY_PLAY_ADDR = 0x10A1        # Play routine entry
LAXITY_FREQ_TABLE = 0x1833       # Frequency lookup (96 notes × 2 bytes)
LAXITY_STATE_BASE = 0x1900       # Per-voice state arrays
LAXITY_SEQ_PTRS = 0x199F         # Sequence pointer table
LAXITY_WAVE_TABLE = 0x19AD       # Wave table (offsets)
LAXITY_WAVE_FORMS = 0x19E7       # Wave table (waveforms)
LAXITY_FILTER_TABLE = 0x1A1E     # Filter/tempo table
LAXITY_PULSE_TABLE = 0x1A3B      # Pulse table
LAXITY_INSTR_TABLE = 0x1A6B      # Instrument table (8 × 8 bytes)
LAXITY_CMD_TABLE = 0x1ADB        # Command table

# SF2 control bytes
END_MARKER = 0x7F        # End of table / Jump command
LOOP_MARKER = 0x7E       # Loop marker in wave table
GATE_ON = 0x7E           # +++ in sequences
GATE_OFF = 0x80          # --- in sequences
DEFAULT_TRANSPOSE = 0xA0 # No transpose in order list

# Default HR values (hard restart)
HR_DEFAULT_AD = 0x0F     # Fast attack, immediate decay
HR_DEFAULT_SR = 0x00     # No sustain, no release

# SF2 file identification (from source)
DRIVER_ID_MARKER = 0x1337    # At driver top address
AUX_DATA_POINTER = 0x0FFB    # Auxiliary data vector

# Command byte values (from SF2 source)
CMD_SLIDE = 0x00
CMD_VIBRATO = 0x01
CMD_PORTAMENTO = 0x02
CMD_ARPEGGIO = 0x03
CMD_FRET = 0x04
CMD_ADSR_NOTE = 0x08
CMD_ADSR_PERSIST = 0x09
CMD_INDEX_FILTER = 0x0A
CMD_INDEX_WAVE = 0x0B
CMD_INDEX_PULSE = 0x0C      # Driver 11.02+
CMD_TEMPO = 0x0D            # Driver 11.02+
CMD_VOLUME = 0x0E           # Driver 11.02+
CMD_DEMO_FLAG = 0x0F

# Table type constants
TABLE_TYPE_GENERIC = 0x00
TABLE_TYPE_INSTRUMENTS = 0x80
TABLE_TYPE_COMMANDS = 0x81
```

## Architecture Notes

### Conversion Flow
1. Parse SID header (PSID v2)
2. Identify player type via player-id.exe
3. Load SID data into 64KB memory model
4. Extract tables (instruments, wave, pulse, filter)
5. Extract sequences from pattern data
6. Load SF2 template for target driver
7. Inject extracted data into template
8. Write output .sf2 file

### Table Extraction Strategy
- Search for pointer patterns in player code
- Score candidates based on validity heuristics
- Extract entries until end marker (0x7F/0x7E)

### SF2 Template-Based Approach

SF2 files are driver-dependent - table layouts vary by driver version. We use a template approach:

1. **Load driver template** - Pre-built SF2 file with driver code and empty tables
2. **Inject extracted data** - Write instruments, wave, pulse, filter tables at known offsets
3. **Update pointers** - Adjust sequence and orderlist pointers

This is more reliable than building SF2 files from scratch because:
- Driver code is complex (~2KB of 6502 assembly)
- Header blocks have intricate interdependencies
- Offsets must align exactly with driver expectations

### Key Format Differences (Laxity vs SF2)

| Aspect | Laxity NewPlayer | SID Factory II |
|--------|------------------|----------------|
| Wave table bytes | (note, waveform) | (waveform, note) |
| Pulse table indices | Y*4 pre-multiplied | Direct indices |
| Gate handling | Implicit | Explicit (+++ / ---) |

### Gate System

SF2 uses explicit gate on/off (different from GoatTracker/CheeseCutter):

```
+++ = Gate on (sustain)
--- = Gate off (release)
**  = Tie note (no envelope restart)
```

This provides precise envelope control but requires more rows per note.

### Hard Restart

Prevents SID's "ADSR bug" (Martin Galway's "school band effect"):

1. Driver gates off 2 frames before next note
2. Applies HR table ADSR (default: `$0F $00`)
3. Next note triggers with stabilized envelope

Most instruments should have HR enabled via flags byte.

### Laxity Super Command Mappings

Key commands to handle during conversion:

| Laxity | SF2 | Notes |
|--------|-----|-------|
| $0x yy | T0 slide | Direct mapping |
| $2x yy | T0 slide down | Direct mapping |
| $60 xy | T1 vibrato | x→XX, y→YY |
| $8x xx | T2 portamento | Direct mapping |
| $9x yy | T9 set ADSR | Persistent |
| $ax yy | T8 local ADSR | Until next note |
| $e0 xx | Td tempo | Speed change |
| $f0 xx | Te volume | Master volume |

### Special Wave Table Cases

**$80 Note Offset**: Recalculates base note + transpose without overwriting frequency. Used for "Hubbard slide" effect.

**Vibrato/Slide Limitation**: Only applies to wave entries with note offset = $00. Non-zero offsets are ignored.

### Speed/Break Speed System

Laxity speeds $00 and $01 trigger alternative speed lookup:
- Uses first 4 bytes of filter table
- Wraps automatically
- $00 in table = wrap marker

## Improvement Opportunities

See README.md for full improvement list with status tracking.

### Completed ✅
- Modularize `sid_to_sf2.py` into separate files (sidm2 package)
- Consolidate duplicate analysis scripts
- Extract magic numbers to constants
- Add comprehensive documentation
- Fixed pulse table extraction with improved scoring algorithm
- Fixed filter table extraction with pattern-based detection
- Added 12 tests for pulse/filter table extraction (61 tests total)

### In Progress 🔄
- Add proper logging instead of print statements
- Add type hints to all public functions
- Error handling in critical extraction functions

### Pending
- Test coverage for edge cases
- Configuration system for SF2 generation
- Support for additional player formats
- Detect row-major vs column-major table layouts
- Implement proper wrap format handling per table type

## Dependencies

- Python 3.x
- No external Python packages required
- Windows tools: siddump.exe, player-id.exe

## File Format References

- `README.md` - Comprehensive format documentation
- `CONTRIBUTING.md` - Contribution guidelines
- `docs/SF2_FORMAT_SPEC.md` - Complete SF2 format specification
- `docs/CONVERSION_STRATEGY.md` - Laxity to SF2 mapping details
- `docs/DRIVER_REFERENCE.md` - All driver specifications (11-16)
- `docs/SF2_SOURCE_ANALYSIS.md` - SF2 editor source code analysis
- `docs/LAXITY_PLAYER_ANALYSIS.md` - Disassembled Laxity player walkthrough
- `docs/SIDDUMP_ANALYSIS.md` - Siddump tool source code analysis
- `docs/VALIDATION_SYSTEM.md` - Three-tier validation architecture (NEW v0.6.0)
- `docs/ACCURACY_ROADMAP.md` - Plan to reach 99% accuracy (NEW v0.6.0)
- `docs/format-specification.md` - PSID/RSID and Laxity formats
- SID Factory II User Manual (2023-09-30) - Official documentation

## SF2 Editor Source Reference

The SF2 editor source code provides authoritative implementation details:

**Source Location**: `SIDFactoryII/source/`

### Key Source Files

| File | Purpose |
|------|---------|
| `converters/utils/sf2_interface.h/cpp` | Core SF2 format handling |
| `driver/driver_info.h/cpp` | Driver structure parsing |
| `datasources/datasource_*.h` | Table access patterns |
| `utils/c64file.h/cpp` | PRG file handling |
| `converters/mod/converter_mod.cpp` | MOD conversion reference |

### Important Structures

```cpp
// Table definition from driver_info.h
struct TableDefinition {
    m_Type: unsigned char       // 0x00=Generic, 0x80=Instruments, 0x81=Commands
    m_DataLayout: unsigned char // 0=RowMajor, 1=ColumnMajor
    m_Address: unsigned short   // Start address in memory
    m_ColumnCount, m_RowCount: unsigned char
}

// Sequence event from datasource_sequence.h
struct Event {
    unsigned char m_Instrument;    // 0x80+ = no change
    unsigned char m_Command;       // 0x80+ = no change
    unsigned char m_Note;
}
```

See `docs/SF2_SOURCE_ANALYSIS.md` for complete analysis.

## SF2 Driver Reference

### Driver 11 (Default)

The "luxury" driver with full features:
- Separate tables: Wave, Pulse, Filter, Arp, HR, Tempo, Init
- 12-bit pulse and filter control
- 32 instruments × 6 bytes (column-major)
- 3-column commands

### Table Summary

| Table | Purpose | Format |
|-------|---------|--------|
| Init | Song init (tempo ptr, volume) | `tempo_row volume` |
| Tempo | Speed as frames/row | `speed ... 7F wrap_row` |
| HR | Hard restart ADSR | `AD SR` (default: `0F 00`) |
| Instruments | ADSR + table pointers | 6 bytes column-major |
| Commands | Effects (slide, vibrato) | 3 bytes |
| Wave | Waveform sequences | `waveform note_offset` |
| Pulse | PWM programs | 4 bytes (value, delta, dur, next) |
| Filter | Filter sweeps | 4 bytes |
| Arp | Chord patterns | Semitone offsets |

### Other Drivers

| Driver | Use Case |
|--------|----------|
| 12 | Extremely simple, minimal features |
| 13 | Rob Hubbard sound emulation |
| 15/16 | Tiny drivers for size-constrained projects |
