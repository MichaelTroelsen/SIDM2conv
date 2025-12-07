# CLAUDE.md - Project Guide for AI Assistants

## Project Overview

SID to SF2 Converter - Converts Commodore 64 SID music files to SID Factory II (.sf2) format for editing and remixing.

## Quick Start

```bash
# Convert single file
python scripts/sid_to_sf2.py SID/input.sid output/SongName/New/output.sf2

# Batch convert all SID files (generates both NP20 and Driver 11 versions)
# Creates structure: output/{SongName}/New/{files}
python scripts/convert_all.py

# Batch convert with round-trip validation
python scripts/convert_all.py --roundtrip

# Test single file round-trip (SID→SF2→SID)
# Creates structure: output/{SongName}/Original/ and /New/
python scripts/test_roundtrip.py SID/input.sid

# Complete pipeline with full validation (NEW in v1.0)
# Processes all SID files with ALL 7 pipeline steps:
# 1. SID→SF2 conversion  2. SF2→SID packing  3. Siddump generation
# 4. WAV rendering  5. Hexdump generation  6. Info.txt reports  7. Validation
python complete_pipeline_with_validation.py
```

## Project Structure

```
SIDM2/
├── complete_pipeline_with_validation.py  # Complete 10-step pipeline (main entry point)
├── scripts/               # All conversion and utility scripts
│   ├── sid_to_sf2.py          # Main converter
│   ├── sf2_to_sid.py          # SF2 to SID exporter
│   ├── disassemble_sid.py     # 6502/6510 disassembler for SID files
│   ├── extract_addresses.py   # Extract data structure addresses from SID files
│   ├── format_tables.py       # Generate hex table views of music data
│   ├── convert_all.py         # Batch conversion script (with SF2→SID export)
│   ├── test_converter.py      # Unit tests (69 tests)
│   ├── test_sf2_format.py     # Format validation tests
│   ├── test_roundtrip.py      # Round-trip validation (SID→SF2→SID)
│   ├── test_complete_pipeline.py  # Pipeline validation tests
│   ├── laxity_parser.py       # Dedicated Laxity player parser
│   ├── validate_psid.py       # PSID header validation utility
│   ├── validate_sid_accuracy.py # SID accuracy validation
│   ├── generate_info.py       # Info.txt generation
│   ├── generate_validation_report.py # Validation report generator
│   └── ...                # Other utility scripts
├── sidm2/                 # Core package
│   ├── sf2_packer.py      # SF2 to SID packer (v0.6.0)
│   ├── cpu6502.py         # 6502 CPU emulator for pointer relocation
│   ├── cpu6502_emulator.py # Full 6502 emulator with SID capture (v0.6.2)
│   ├── sid_player.py      # SID file player and analyzer (v0.6.2)
│   ├── sf2_player_parser.py # SF2-exported SID parser (v0.6.2)
│   └── ...                # Other modules
├── SID/                   # Input SID files
├── output/                # Output folder with nested structure
│   └── {SongName}/        # Per-song directory
│       ├── Original/      # Original SID, WAV, dump (round-trip only)
│       └── New/           # Converted SF2 + exported SID files
├── docs/                  # Documentation files
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
│   ├── SF2_FORMAT_SPEC.md           # Complete SF2 format specification
│   ├── SF2_DRIVER11_DISASSEMBLY.md  # SF2 Driver 11 player analysis
│   ├── STINSENS_PLAYER_DISASSEMBLY.md # Laxity NewPlayer v21 analysis
│   ├── CONVERSION_STRATEGY.md       # Laxity to SF2 mapping
│   ├── DRIVER_REFERENCE.md          # All driver specifications
│   ├── SF2_SOURCE_ANALYSIS.md       # SF2 editor source code analysis
│   └── format-specification.md      # PSID/RSID formats
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
- **Known Limitation**: Pointer relocation bug affects SIDwinder disassembly
  - Affects 17/18 files in pipeline testing (94%)
  - Files play correctly in VICE, SID2WAV, siddump, and other emulators
  - Only impacts SIDwinder's strict CPU emulation
  - Under investigation - see `PIPELINE_EXECUTION_REPORT.md` for details
- See `PACK_STATUS.md` for implementation details and test results

### Python SID Emulation & Analysis Modules - NEW in v0.6.2

#### CPU 6502 Emulator (`sidm2/cpu6502_emulator.py`)
- Full 6502 CPU emulator implementation (1,242 lines)
- Complete instruction set with all addressing modes
- SID register write capture for validation
- Frame-by-frame state tracking
- Tested with real SID files (Angular.sid, etc.)
- Based on siddump.c architecture
- Usage: `from sidm2.cpu6502_emulator import CPU6502Emulator`

#### SID Player (`sidm2/sid_player.py`)
- High-level SID file player and analyzer (560 lines)
- PSID/RSID header parsing
- Note detection and frequency analysis
- Siddump-compatible frame dump output
- Playback result analysis
- Usage: `python -m sidm2.sid_player <sidfile> [seconds]`

#### SF2 Player Parser (`sidm2/sf2_player_parser.py`)
- Parser for SF2-exported SID files (389 lines)
- Pattern-based table extraction with SF2 reference
- Heuristic extraction mode (in development)
- Tested with 15 SIDSF2player files
- Header parsing: 100% success rate
- Table extraction: Works with matching SF2 reference
- Usage: `from sidm2.sf2_player_parser import SF2PlayerParser`

#### Test Suite (`test_sf2_player_parser.py`)
- Validation tests for SF2 player parser
- Tests multiple SID files with/without reference
- Reports extraction success rates
- Example output structure validation

### External Tools
- `tools/siddump.exe` - Dumps SID register writes (6502 emulator)
- `tools/player-id.exe` - Identifies SID player type
- `tools/SID2WAV.EXE` - Converts SID to WAV audio files
- `tools/SIDwinder.exe` - SID file processor (v0.2.6)
  - **Disassembly**: Converts SID to assembly (✅ Working - integrated in pipeline)
  - **Trace**: SID register write tracer (⚠️ Has bugs - fix available, needs rebuild)
  - **Player**: Links SID with visualization players
  - **Relocate**: Moves SID to different memory addresses
  - Source: `C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6\src`
  - Patch file: `tools/sidwinder_trace_fix.patch` (fixes trace functionality)
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

#### Multi-File Validation Report (NEW in v0.6.1)
- `generate_validation_report.py` - Comprehensive validation report generator
  - Validates all SID files in a directory
  - Generates HTML report (`output/validation_report.html`) with statistics and analysis
  - Identifies systematic vs file-specific validation issues
  - Categorizes warnings (Instrument Pointer Bounds, Note Range, etc.)
  - Current status: 16 test files validated with improved boundary checking
  - False-positive warnings reduced by 50% for Angular.sid (4→2)

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

#### Complete Pipeline with Validation - NEW in v1.0 (Updated v1.2)

`complete_pipeline_with_validation.py` - Comprehensive 10-step conversion pipeline

**Purpose**: Batch process all SID files with complete validation and analysis

**The 10 Pipeline Steps**:
1. **SID → SF2 Conversion**: Smart detection uses reference/template/Laxity methods
2. **SF2 → SID Packing**: Generates playable SID files from SF2
3. **Siddump Generation**: Creates register dumps for original + exported SIDs
4. **WAV Rendering**: Renders 30-second audio files for original + exported SIDs
5. **Hexdump Generation**: Creates xxd-format hex dumps for binary analysis
6. **SIDwinder Trace**: SID register trace for original + exported SIDs (NEW v1.2 - requires rebuilt SIDwinder)
7. **Info.txt Reports**: Generates comprehensive conversion reports with metadata
8. **Annotated Disassembly**: Python-based disassembly with annotations
9. **SIDwinder Disassembly**: Professional disassembly using SIDwinder (NEW in v1.1)
10. **Validation Check**: Verifies all required files were generated correctly

**Output Structure**:
```
output/SIDSF2player_Complete_Pipeline/
├── {filename}/
│   ├── Original/
│   │   ├── {filename}_original.dump    # Siddump register capture
│   │   ├── {filename}_original.wav     # Audio rendering
│   │   ├── {filename}_original.hex     # Binary hexdump
│   │   └── {filename}_original.txt     # SIDwinder trace (NEW - needs rebuild)
│   └── New/
│       ├── {filename}.sf2                   # Converted SF2 file
│       ├── {filename}_exported.sid          # Packed SID file
│       ├── {filename}_exported.dump         # Siddump register capture
│       ├── {filename}_exported.wav          # Audio rendering
│       ├── {filename}_exported.hex          # Binary hexdump
│       ├── {filename}_exported.txt          # SIDwinder trace (NEW - needs rebuild)
│       ├── {filename}_exported_disassembly.md  # Annotated disassembly
│       ├── {filename}_exported_sidwinder.asm   # SIDwinder disassembly (see limitation*)
│       └── info.txt                         # Comprehensive report
```

*Note: SIDwinder disassembly currently only works for original SID files due to a pointer relocation bug in the packer.

**Smart File Type Detection**:
- **SF2-packed**: `load=$1000`, `init=$1000`, `play=$1003`
- **Laxity format**: High load addresses (`>=$A000`) or Laxity init patterns
- Automatically selects appropriate conversion method

**Conversion Methods**:
- **REFERENCE**: Uses original SF2 as template (100% table accuracy)
- **TEMPLATE**: Uses generic SF2 template (variable accuracy)
- **LAXITY**: Parses original Laxity NewPlayer format

**Validation System**:
- Checks for all 13 required files (9 in New/, 4 in Original/)
- Reports missing files and completion status
- Status: COMPLETE (all files), PARTIAL (some missing)
- Note: Trace files require rebuilt SIDwinder.exe to generate

**Unit Tests**: `test_complete_pipeline.py` (19 tests)
- File requirements validation
- Pipeline validation with real output
- File type identification (SF2-packed vs Laxity)
- Output file integrity (size, format)
- Directory structure validation
- Header parsing tests

**Usage**:
```bash
python complete_pipeline_with_validation.py
```

**Test Suite**:
```bash
python scripts/test_complete_pipeline.py -v
```

**Latest Execution Results** (2025-12-06):
- **Total Files Processed**: 18 SID files
- **Complete Success**: 1/18 (5.6%) - All 13 files generated
- **Partial Success**: 17/18 (94.4%) - 12/13 files generated (missing .asm)
- **Step Success Rates**:
  - Steps 1-5, 7-8: 100% success (conversion, dumps, WAV, hexdump, info, Python disassembly)
  - Step 6 (SIDwinder trace): 100% file generation (empty until rebuild)
  - Step 9 (SIDwinder disassembly): 5.6% success (packer bug affects 17 files)
  - Step 10 (Validation): 94.4% partial completion

**Known Limitation - SIDwinder Disassembly of Exported SIDs**:
- **Impact**: 17/18 exported SID files fail disassembly with "Execution at $0000" error
- **Root Cause**: Pointer relocation bug in `sidm2/sf2_packer.py` - likely indirect jumps or jump table data
- **Scope**: Only affects SIDwinder's strict emulation; files play correctly in VICE, SID2WAV, and siddump
- **Workaround**: Original SID files disassemble successfully with SIDwinder
- **Status**: Known limitation - requires dedicated debugging session with CPU trace analysis
- **Note**: This does not affect music playback or most validation operations

**SIDwinder Trace Status**:
- Files generated successfully (36/36)
- Content empty until SIDwinder.exe rebuilt with patches
- See `tools/SIDWINDER_QUICK_REFERENCE.md` for rebuild instructions

See `PIPELINE_EXECUTION_REPORT.md` for comprehensive execution analysis.

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

### SIDwinder Tool Details

SIDwinder (v0.2.6) is a comprehensive C64 SID file processor with multiple capabilities:

```bash
# Disassemble SID to assembly code (WORKING - integrated in pipeline)
tools/SIDwinder.exe -disassemble SID/file.sid output.asm

# Trace SID register writes (BROKEN - fix available)
tools/SIDwinder.exe -trace=output.txt SID/file.sid

# Create player PRG with visualizations
tools/SIDwinder.exe -player=RaistlinBars music.sid music.prg

# Relocate SID to different address
tools/SIDwinder.exe -relocate=$2000 input.sid output.sid
```

**Disassembly Features**:
- Generates KickAssembler-compatible source code
- Includes metadata (title, author, copyright) as comments
- Labels data blocks and code sections
- Integrated into complete_pipeline_with_validation.py
- Output: `.asm` files with full 6502 disassembly

**Trace Bug & Fix**:
The `-trace` command currently produces empty output due to two bugs:
1. SID write callback not enabled for trace-only commands (line 124 in SIDEmulator.cpp)
2. TraceLogger missing public `logWrite()` method

**Status**: ✅ Source code patched | ⚠️ Needs rebuild | 🔧 Integrated in pipeline

A complete fix is available in `tools/sidwinder_trace_fix.patch` and has been applied to the source files. To rebuild:

```bash
cd C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6

# Source files already patched, just rebuild:
build.bat

# Copy new executable to tools
copy build\Release\SIDwinder.exe C:\Users\mit\claude\c64server\SIDM2\tools\
```

**Pipeline Integration**:
- ✅ Trace generation added to `complete_pipeline_with_validation.py` (Step 6)
- Generates `.txt` files for both original and exported SIDs
- 30-second traces (1500 frames @ 50Hz)
- Will work automatically once SIDwinder.exe is rebuilt
- Shows "[WARN - needs rebuilt SIDwinder]" until rebuild is complete

See `tools/sidwinder_trace_fix.patch` for patch details.

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
python scripts/test_converter.py
python scripts/test_sf2_format.py
```

## CI/CD Rules

**IMPORTANT: Always follow these rules when making changes:**

### 1. Always Run Tests
Before committing any code changes, you MUST:
- Run `python scripts/test_converter.py` and ensure all tests pass
- Run `python scripts/test_sf2_format.py` for format validation tests
- If tests fail, fix the issues before committing

### 2. Always Update Documentation
When making code changes, you MUST update relevant documentation:
- Update `README.md` if adding/changing features or CLI options
- Update `CLAUDE.md` if changing project structure or conventions
- Update `docs/` files if changing architecture or API
- Keep version numbers in sync across files
- Update improvement status in README when completing items

**IMPORTANT: Update Documentation with Knowledge Gained**
When working on tasks, you MUST document any new knowledge or discoveries:
- If you create new scripts or tools, add them to the Project Structure
- If you discover new conversion steps, update the Common Tasks section
- If you find better workflows, document them in CLAUDE.md
- If you learn specifics about the SID/SF2 format, update relevant docs
- Keep the documentation current with actual working practices
- Document complete pipelines and all outputs they generate

### 3. Always Update File Inventory
After making structural changes (adding/removing files, reorganizing), you MUST:
- Run `python update_inventory.py` to regenerate FILE_INVENTORY.md
- Review the updated inventory for any cleanup opportunities
- Commit the updated FILE_INVENTORY.md with your changes

**When to update inventory:**
- After adding new files to the project
- After removing or moving files
- After major refactoring
- Before creating releases
- When cleaning up old files

## Common Tasks

### Complete Conversion Pipeline (Recommended)

For a thorough conversion with all outputs and validation data:

```bash
# 1. Convert SID to SF2
python scripts/sid_to_sf2.py SID/Song.sid output/Song/New/Song_d11.sf2

# 2. Generate siddump from original SID
tools/siddump.exe SID/Song.sid -t30 > output/Song/New/Song_original.dump

# 3. Generate WAV from original SID
tools/SID2WAV.EXE -t30 -16 SID/Song.sid output/Song/New/Song_original.wav

# 4. Export SF2 back to SID
python scripts/sf2_to_sid.py output/Song/New/Song_d11.sf2 output/Song/New/Song_d11.sid

# 5. Generate siddump from exported SID
tools/siddump.exe output/Song/New/Song_d11.sid -t30 > output/Song/New/Song_exported.dump

# 6. Generate WAV from exported SID
tools/SID2WAV.EXE -t30 -16 output/Song/New/Song_d11.sid output/Song/New/Song_exported.wav

# 7. Generate hexdumps for binary comparison
xxd SID/Song.sid > output/Song/New/Song_original.hex
xxd output/Song/New/Song_d11.sid > output/Song/New/Song_converted.hex

# 8. Extract data structure addresses
python scripts/extract_addresses.py SID/Song.sid
```

**Pipeline Outputs (9 files):**
1. `Song_d11.sf2` - SF2 format file
2. `Song_d11.sid` - Exported SID file
3. `Song_original.dump` - Original SID register dump
4. `Song_exported.dump` - Exported SID register dump
5. `Song_original.wav` - Original audio (30s)
6. `Song_exported.wav` - Exported audio (30s)
7. `Song_original.hex` - Original SID hexdump
8. `Song_converted.hex` - Converted SID hexdump
9. `info.txt` - Comprehensive conversion report with address mapping

**What Each File Provides:**
- `.sf2` - Editable music data in SID Factory II format
- `.sid` - Playable SID file for emulators
- `.dump` - Register-level comparison for accuracy validation
- `.wav` - Audio comparison for quality validation
- `.hex` - Byte-level binary comparison for debugging
- `info.txt` - Complete metadata, addresses, and validation warnings

### Quick Single File Conversion
1. Place .sid file in `SID/` directory
2. Run `python scripts/sid_to_sf2.py SID/file.sid output/SongName/New/file.sf2`
3. Check `output/SongName/New/info.txt` for extraction details

### Extracting Data Structure Addresses
Use `extract_addresses.py` to analyze SID file memory layout:

```bash
python scripts/extract_addresses.py SID/file.sid
```

This extracts start/end addresses for:
- Player code (init/play routines)
- Sequences, Orderlists, Instruments
- Wave, Pulse, Filter, Arpeggio tables
- Tempo, Command tables, Sequence pointers

Addresses are automatically included in `info.txt` during conversion.

### Debugging Extraction Issues
1. Run `tools/siddump.exe SID/file.sid > output/file.dump`
2. Check dump for register patterns
3. Run `python scripts/extract_addresses.py SID/file.sid` to verify table locations
4. Review `output/SongName/New/info.txt` for warnings and addresses
5. Compare hexdumps to identify specific byte differences

### Round-Trip Validation
1. Run `python test_roundtrip.py SID/file.sid`
2. Check `roundtrip_output/file_roundtrip_report.html` for results
3. Compare `file_original.dump` and `file_exported.dump` for register differences
4. Listen to `file_original.wav` and `file_exported.wav` for audio quality

### Manual SF2 to SID Packing (Reference Implementation)
1. Build sf2pack: `cd tools/sf2pack && mingw32-make`
2. Pack file: `tools/sf2pack/sf2pack.exe SF2/file.sf2 output.sid --title "Title" --author "Author"`
3. Test with VICE: Load output.sid in C64 emulator
4. Verify relocation with `-v` flag for detailed stats

Note: The Python `sf2_to_sid.py` is now the recommended method for SF2→SID conversion.

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
- `docs/SF2_DRIVER11_DISASSEMBLY.md` - Complete SF2 Driver 11 player analysis (NEW)
- `docs/STINSENS_PLAYER_DISASSEMBLY.md` - Laxity NewPlayer v21 disassembly (NEW)
- `docs/CONVERSION_STRATEGY.md` - Laxity to SF2 mapping details
- `docs/DRIVER_REFERENCE.md` - All driver specifications (11-16)
- `docs/SF2_SOURCE_ANALYSIS.md` - SF2 editor source code analysis
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
