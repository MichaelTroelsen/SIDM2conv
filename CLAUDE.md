# CLAUDE.md - Project Guide for AI Assistants

## Project Overview

SID to SF2 Converter - Converts Commodore 64 SID music files (Laxity NewPlayer v21) to SID Factory II (.sf2) format for editing and remixing.

**Supported Formats**:
- **Input**: Laxity NewPlayer v21 SID files only
- **Output**: SID Factory II .sf2 format (Driver 11 or NP20)

---

## Quick Start

### Conversion Workflow

```bash
# Convert single file (auto-detects format)
python scripts/sid_to_sf2.py SID/input.sid output/SongName/New/output.sf2

# Convert Laxity SID with high accuracy (99.93% frame accuracy - v1.8.0)
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity

# Quick validation test for Laxity driver
python test_laxity_accuracy.py

# Batch convert all SID files (generates both NP20 and Driver 11 versions)
python scripts/convert_all.py

# Batch convert with round-trip validation
python scripts/convert_all.py --roundtrip

# Test single file round-trip (SID→SF2→SID)
python scripts/test_roundtrip.py SID/input.sid

# Complete pipeline with full validation (13 steps: conversion, sequence extraction, player analysis, packing, dumps, accuracy, WAV, hex, trace, info, disassembly, validation, MIDI comparison)
# NEW in v1.2: SIDtool MIDI comparison integrated for Python emulator validation!
# NEW in v1.3: SIDdecompiler player structure analysis integrated!
# NEW in v1.4.1: Automatic accuracy calculation integrated!
# NEW in v1.8.0: Laxity driver support with 99.93% accuracy!
python complete_pipeline_with_validation.py

# CI/CD workflow runs automatically on PR/push (v1.4.2)
# See .github/workflows/validation.yml
```

### SF2 Viewer (NEW - v2.1)

Professional GUI tool to view and analyze SF2 files:

```bash
# Windows (simplest - batch launcher with auto-dependency installation)
cd SIDM2
launch_sf2_viewer.bat

# Or cross-platform with Python launcher
cd SIDM2
python launch_sf2_viewer.py

# Or direct launch (requires PyQt6 installed)
cd SIDM2
python sf2_viewer_gui.py
```

**Features:**
- Drag-and-drop SF2 file loading
- **Recent Files menu** for quick access to last 10 files
- Multi-tab interface (8 tabs):
  - Overview: File info and validation
  - Header Blocks: SF2 block structure
  - Tables: Music data tables (spreadsheet view)
  - Memory Map: Visual memory layout
  - OrderList: Sequence playback order
  - Sequences: Step-by-step sequence data
  - **Visualization**: Waveform, filter, and envelope graphs
  - **Playback**: Audio preview with play/pause/volume
- View all SF2 block types and table data
- File validation summary
- Professional PyQt6 GUI matching SID Factory II layout

**New Features (v2.1):**
- **Recent Files Menu**: Quick access to last 10 opened files with persistent storage
- **Visualization Tab**: Graph waveforms, filter curves, and ADSR envelopes
- **Playback Tab**: Convert SF2→SID→WAV and play audio with volume control
- Real-time position tracking and status display


---

## Project Structure

```
SIDM2/
├── complete_pipeline_with_validation.py  # Complete 13-step pipeline with player analysis + MIDI validation (main entry point)
├── cleanup.py                            # Automated cleanup tool (v2.2)
├── new_experiment.py                     # Experiment template generator
├── update_inventory.py                   # File inventory updater
│
├── SIDM2/                 # SF2 Viewer Application (v2.1 - Recent Files + Visualization + Playback)
│   ├── sf2_viewer_core.py              # SF2 format parser (450 lines)
│   ├── sf2_viewer_gui.py               # PyQt6 GUI application (1000+ lines) - UPDATED with Recent Files
│   ├── sf2_visualization_widgets.py    # Visualization widgets (300 lines)
│   ├── sf2_playback.py                 # Playback engine (200 lines)
│   ├── launch_sf2_viewer.py            # Python launcher with auto-install (90 lines)
│   ├── launch_sf2_viewer.bat           # Windows batch launcher with dependency check
│   ├── test_sf2_viewer.py              # Test suite (160 lines, 100% pass rate)
│   ├── SF2_VIEWER_IMPLEMENTATION_SUMMARY.md # Technical summary
│   ├── VIEWER_COMPLETE.txt             # Completion summary
│
├── scripts/               # Conversion and utility scripts
│   ├── sid_to_sf2.py          # Main SID→SF2 converter
│   ├── sf2_to_sid.py          # SF2→SID exporter (uses sf2_packer.py)
│   ├── convert_all.py         # Batch conversion with validation
│   ├── test_roundtrip.py      # Round-trip validation (SID→SF2→SID)
│   ├── validate_sid_accuracy.py # Frame-by-frame accuracy validation
│   ├── generate_validation_report.py # Multi-file validation reports
│   ├── run_validation.py      # Validation system runner (v1.4)
│   ├── generate_dashboard.py  # Dashboard generator (v1.4)
│   ├── analyze_waveforms.py   # Waveform analysis & HTML report generator (v0.7.2)
│   ├── test_midi_comparison.py # Python MIDI emulator vs SIDtool comparison
│   ├── compare_musical_content.py # Musical content validator (note sequences)
│   ├── disassemble_sid.py     # 6502 disassembler
│   ├── extract_addresses.py   # Extract data structure addresses
│   ├── validation/            # Validation system modules (v1.4)
│   │   ├── database.py        # SQLite validation tracking
│   │   ├── metrics.py         # Metrics collection
│   │   ├── regression.py      # Regression detection
│   │   └── dashboard.py       # HTML dashboard generation
│   └── test_*.py              # Unit tests (69 converter tests, 12 format tests, 19 pipeline tests)
│
├── sidm2/                 # Core Python package
│   ├── sf2_packer.py      # SF2→SID packer with pointer relocation (v0.6.0)
│   ├── cpu6502.py         # 6502 CPU emulator for relocation
│   ├── cpu6502_emulator.py # Full 6502 emulator with SID capture (v0.6.2)
│   ├── sid_player.py      # SID file player and analyzer (v0.6.2)
│   ├── sf2_player_parser.py # SF2-exported SID parser (v0.6.2)
│   ├── siddump_extractor.py # Runtime sequence extraction (v1.3)
│   ├── siddecompiler.py   # SIDdecompiler wrapper for player analysis (v1.3)
│   ├── sid_to_midi_emulator.py # Python MIDI emulator (100% accuracy on select files)
│   ├── midi_sequence_extractor.py # MIDI→SF2 sequence converter
│   ├── gate_inference.py  # Waveform-based gate detection (v1.5.0)
│   ├── accuracy.py        # Accuracy calculation module (v1.4.1)
│   └── validation.py      # Validation utilities (v0.6.0)
│
├── tools/                 # External tools
│   ├── siddump.exe        # SID register dump tool (6502 emulation)
│   ├── SIDdecompiler.exe  # Emulation-based disassembler (player structure analysis)
│   ├── player-id.exe      # Player type identification
│   ├── SID2WAV.EXE        # SID to WAV renderer
│   ├── SIDwinder.exe      # SID processor (disassembly, trace, player, relocate)
│   └── sf2pack/           # C++ SF2→SID packer (reference implementation)
│
├── SID/                   # Input SID files (7 test files)
├── output/                # Output folder with per-song structure
│   └── {SongName}/
│       ├── Original/      # Original SID, WAV, dump (round-trip only)
│       └── New/           # Converted SF2 + exported SID files
│
├── validation/            # Validation system data (v1.4)
│   ├── database.sqlite    # SQLite validation history
│   ├── dashboard.html     # Interactive HTML dashboard
│   └── SUMMARY.md         # Markdown summary (git-friendly)
│
├── G5/                    # Driver templates
│   ├── drivers/           # SF2 driver PRG files (11, 12, 13, 14, 15, 16, NP20)
│   └── examples/          # Example SF2 files for each driver
│
├── .github/               # GitHub configuration (v1.4.2)
│   └── workflows/
│       └── validation.yml # CI/CD validation workflow
│
├── experiments/           # Temporary experiments (gitignored, v2.0)
│   ├── README.md          # Experiment workflow guide
│   ├── {experiment}/      # Individual experiments with self-cleanup
│   └── ARCHIVE/           # Valuable findings (optional)
│
├── docs/                  # Documentation (see Documentation Index below)
│   ├── FILE_INVENTORY.md  # Repository structure tracking
│   └── guides/
│       └── CLEANUP_SYSTEM.md  # Cleanup system guide (v2.2)
│
└── learnings/             # Reference materials and source docs
```

---

## Essential Workflows

### Single File Conversion

```bash
# 1. Convert SID to SF2
python scripts/sid_to_sf2.py SID/Song.sid output/Song/New/Song.sf2

# 2. Convert with MIDI-based sequence extraction (high accuracy)
python scripts/sid_to_sf2.py SID/Song.sid output/Song/New/Song.sf2 --use-midi

# 3. Check conversion report
cat output/Song/New/info.txt
```

###  MIDI-Based Sequence Extraction (NEW)

High-accuracy sequence extraction using Python MIDI emulator:

```bash
# Convert with MIDI extraction (validated 100% accuracy on 3/17 files)
python scripts/sid_to_sf2.py SID/Beast.sid output/Beast.sf2 --use-midi

# MIDI emulator achieves:
# - 100% perfect match: Beast.sid, Delicate.sid, Ocean_Reloaded.sid
# - 100.66% overall accuracy (10793 vs 10722 notes across 17 files)
# - Batch synth processing matching SIDtool behavior
```

**Features**:
- Frame-based SID register capture
- Batch synth collection (like SIDtool)
- Legato note detection
- MIDI note conversion with exact formula
- Integration pending for sequence data

### SIDdecompiler Player Analysis (v1.4 - NEW)

SIDdecompiler integration provides automated player type detection and memory layout analysis:

```bash
# SIDdecompiler runs automatically as Step 1.6 in the pipeline
python complete_pipeline_with_validation.py

# See analysis output:
ls output/SongName/New/analysis/
# Output:
# - {basename}_siddecompiler.asm      # Complete 6502 disassembly
# - {basename}_analysis_report.txt    # Player info & memory layout
```

**Key Features**:
- ✅ **Player Detection**: 100% accuracy on Laxity NewPlayer v21 files
- ✅ **Memory Layout**: Visual ASCII maps showing code, tables, data regions
- ✅ **Table Detection**: Identifies filter, pulse, instrument, wave tables
- ✅ **Memory Analysis**: Provides memory region validation for error prevention
- ✅ **Structure Reports**: Comprehensive analysis with version info and statistics

**Production Recommendation** (v1.4):
- Use manual table extraction (proven reliable)
- Use SIDdecompiler for player type detection (100% accurate)
- Use memory layout validation (error prevention)
- Hybrid approach: manual extraction + auto validation

**Example Output**:
```
Player Information:
  Type: NewPlayer v21 (Laxity)
  Version: 21
  Memory Range: $A000-$B9A7 (6,568 bytes)

Memory Layout:
$A000-$B9A7 [████████████████████████████████████████] Player Code (6,568 bytes)

Detected Tables (with addresses):
  Filter Table: $1A1E (128 bytes)
  Pulse Table: $1A3B (256 bytes)
  Instrument Table: $1A6B (256 bytes)
  Wave Table: $1ACB (variable)
```

### Complete Validation Pipeline

For thorough conversion with all validation data:

```bash
# 1. Convert SID to SF2
python scripts/sid_to_sf2.py SID/Song.sid output/Song/New/Song_d11.sf2

# 2. Generate siddump from original
tools/siddump.exe SID/Song.sid -t30 > output/Song/New/Song_original.dump

# 3. Generate WAV from original
tools/SID2WAV.EXE -t30 -16 SID/Song.sid output/Song/New/Song_original.wav

# 4. Export SF2 back to SID
python scripts/sf2_to_sid.py output/Song/New/Song_d11.sf2 output/Song/New/Song_d11.sid

# 5. Generate siddump from exported
tools/siddump.exe output/Song/New/Song_d11.sid -t30 > output/Song/New/Song_exported.dump

# 6. Generate WAV from exported
tools/SID2WAV.EXE -t30 -16 output/Song/New/Song_d11.sid output/Song/New/Song_exported.wav

# 7. Compare dumps and WAVs for validation
```

**Pipeline Outputs**: 9 files (SF2, SID, 2×dump, 2×WAV, 2×hex, info.txt)

### Debugging Extraction Issues

```bash
# 1. Run siddump to check register patterns
tools/siddump.exe SID/file.sid > output/file.dump

# 2. Extract and verify table addresses
python scripts/extract_addresses.py SID/file.sid

# 3. Check info.txt for warnings
cat output/SongName/New/info.txt

# 4. Compare hexdumps for binary differences
xxd SID/file.sid > original.hex
xxd output/file.sid > converted.hex
diff original.hex converted.hex
```

### Validation System (v1.4)

Systematic validation with regression tracking and HTML dashboard:

```bash
# Run validation on all pipeline outputs
python scripts/run_validation.py --notes "After bug fix"

# Run with regression detection against previous run
python scripts/run_validation.py --baseline 1 --notes "Regression check"

# Generate interactive HTML dashboard
python scripts/generate_dashboard.py

# Generate both HTML and markdown summary
python scripts/generate_dashboard.py --markdown validation/SUMMARY.md

# Compare two validation runs
python scripts/run_validation.py --compare 1 2

# Quick validation (subset of files)
python scripts/run_validation.py --quick

# Export results to JSON for CI/CD
python scripts/run_validation.py --export results.json
```

**Outputs**:
- `validation/database.sqlite` - SQLite database with complete history
- `validation/dashboard.html` - Interactive dashboard with charts
- `validation/SUMMARY.md` - Git-friendly markdown summary

**Features**:
- Tracks 9 pipeline steps per file (conversion → disassembly)
- Regression detection (accuracy drops, step failures, size increases)
- Trend visualization with Chart.js
- Pass rates, aggregate metrics, file-by-file results
- Configurable thresholds (5% accuracy, 20% size)

### Automated CI/CD (v1.4.2)

GitHub Actions workflow automatically validates every PR and push:

```yaml
# .github/workflows/validation.yml runs automatically on:
# - Pull requests to master/main
# - Pushes to master/main
```

**What it does**:
- Runs validation on existing pipeline outputs
- Compares against baseline (previous commit)
- Detects regressions and blocks PR if found
- Posts validation summary as PR comment
- Auto-commits validation results to master (with [skip ci])
- Uploads dashboard as artifact

**Regression Rules**:
- Accuracy drops >5%: ❌ FAIL
- Step failures (pass → fail): ❌ FAIL
- File size increases >20%: ⚠️ WARN
- New warnings: ⚠️ WARN

**Workflow triggers on changes to**:
- `sidm2/**` - Core modules
- `scripts/**` - Pipeline scripts
- `complete_pipeline_with_validation.py`
- `.github/workflows/validation.yml`

**Viewing Results**:
- PR comment shows validation summary
- Artifacts include interactive dashboard
- Validation results committed to `validation/`

### Waveform Analysis (v0.7.2)

Generate interactive HTML reports with audio waveform visualization:

```bash
# Analyze all files in pipeline output
python scripts/analyze_waveforms.py output/SIDSF2player_Complete_Pipeline

# Analyze specific song directory
python scripts/analyze_waveforms.py output/MySong
```

**Outputs** (per song):
- `{SongName}_waveform_analysis.html` - Interactive HTML report with:
  - Embedded audio players (original + exported WAV files)
  - HTML5 canvas waveform visualizations
  - Similarity metrics (correlation, RMSE, match rate)
  - File statistics comparison table
  - Analysis notes explaining expected differences

**Features**:
- Uses Python standard library only (wave module)
- No NumPy/Matplotlib dependency
- Self-contained HTML files
- ~450 lines of code

**Use Case**: Visual comparison of original (Laxity) vs exported (SF2) audio output. Expected to show differences since different players are used.

---

## Project Maintenance

### Cleanup System (v2.2)

Comprehensive automated cleanup system for managing experimental files, documentation organization, and file inventory:

```bash
# Quick scan (shows what would be cleaned)
python cleanup.py --scan

# Clean root + output directories
python cleanup.py --clean

# Clean with automatic inventory update (recommended)
python cleanup.py --clean --update-inventory

# Clean everything (root + output + experiments)
python cleanup.py --all --clean --update-inventory

# Force mode (no confirmation)
python cleanup.py --clean --force --update-inventory
```

**Features**:
- ✅ **Test file detection** - `test_*.py`, `test_*.log`, etc.
- ✅ **Temporary file detection** - `temp_*`, `tmp_*`, `*.tmp`
- ✅ **Output directory cleanup** - `output/test_*`, `output/Test_*`
- ✅ **Experiment management** - `experiments/` subdirectories
- ✅ **Misplaced doc detection** - Auto-organizes MD files to `docs/`
- ✅ **File inventory updates** - Auto-updates `docs/FILE_INVENTORY.md`
- ✅ **Safety features** - Confirmation, backups, protected files

**Scan Output**:
```
[1/4] Scanning root directory...
[2/4] Scanning output directory...
[3/4] Scanning for temporary outputs...
[4/4] Scanning for misplaced documentation...

Total items: 15 files + 5 directories
Total size: 2.5 MB
```

### Experiment Workflow

Create structured experiments with automatic cleanup:

```bash
# Create new experiment
python new_experiment.py "wave_table_analysis"

# Or with description
python new_experiment.py "filter_fix" --description "Test filter format conversion"
```

**Creates**:
```
experiments/wave_table_analysis/
├── experiment.py       # Template script
├── README.md          # Documentation template
├── output/            # Generated files
├── cleanup.sh         # Unix cleanup script
└── cleanup.bat        # Windows cleanup script
```

**Workflow**:
1. Create experiment: `python new_experiment.py "my_test"`
2. Work in `experiments/my_test/`
3. Run: `python experiments/my_test/experiment.py`
4. Document findings in `README.md`
5. Cleanup: `cd experiments/my_test && ./cleanup.bat`

**If successful**:
- Move code to `scripts/` or `sidm2/`
- Archive findings in `experiments/ARCHIVE/`
- Clean up with: `python cleanup.py --experiments --clean`

### Documentation Organization

Standard root documentation (always kept in root):
- `README.md` - Main project documentation
- `CONTRIBUTING.md` - Contribution guidelines
- `CHANGELOG.md` - Version history
- `CLAUDE.md` - AI assistant quick reference

**All other MD files** are automatically detected as misplaced and suggested for `docs/`:
- `*_ANALYSIS.md` → `docs/analysis/`
- `*_IMPLEMENTATION.md` → `docs/implementation/`
- `*_STATUS.md` → `docs/analysis/`
- `*_NOTES.md` → `docs/guides/`
- And more (see `docs/guides/CLEANUP_SYSTEM.md`)

### File Inventory Management

Automatically track repository structure:

```bash
# Update inventory manually
python update_inventory.py

# Auto-update during cleanup (recommended)
python cleanup.py --clean --update-inventory
```

**Tracks**:
- Complete file tree with sizes
- Category summaries
- Management rules
- Last updated timestamp

**Location**: `docs/FILE_INVENTORY.md`

### Cleanup Schedule

**Daily** (if active development):
```bash
python cleanup.py --clean --update-inventory
```

**Weekly**:
```bash
python cleanup.py --all --clean --update-inventory
```

**Before releases**:
```bash
python cleanup.py --all --clean --force --update-inventory
git add -A
git commit -m "chore: Cleanup before release"
```

**Documentation**: See `docs/guides/CLEANUP_SYSTEM.md` for complete guide.

---

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
- If you discover new conversion steps, update the Essential Workflows section
- If you find better workflows, document them in CLAUDE.md
- If you learn specifics about the SID/SF2 format, update relevant docs
- Keep the documentation current with actual working practices
- Document complete pipelines and all outputs they generate

### 3. Always Update File Inventory

After making structural changes (adding/removing files, reorganizing), you MUST:
- Run `python update_inventory.py` to regenerate FILE_INVENTORY.md
- Review the updated inventory for any cleanup opportunities
- Commit the updated FILE_INVENTORY.md with your changes

**When to update inventory**:
- After adding new files to the project
- After removing or moving files
- After major refactoring
- Before creating releases
- When cleaning up old files

---

## Code Conventions

- Memory addresses as hex: `0x1000`, `0x1AF3`
- Table sizes: typically 32, 64, or 128 entries
- Control bytes: `0x7F` (end), `0x7E` (loop/gate on)
- Waveforms: `0x01` (triangle), `0x10` (triangle+gate), `0x11` (pulse), etc.

---

## Essential Constants

```python
# SF2 structure offsets (Driver 11)
SEQUENCE_TABLE_OFFSET = 0x0903
INSTRUMENT_TABLE_OFFSET = 0x0A03
WAVE_TABLE_OFFSET = 0x0B03
PULSE_TABLE_OFFSET = 0x0D03
FILTER_TABLE_OFFSET = 0x0F03

# Laxity player markers
LAXITY_INIT_PATTERN = [0xA9, 0x00, 0x8D]  # LDA #$00, STA
LAXITY_INIT_ADDR = 0x1000        # Init routine entry
LAXITY_PLAY_ADDR = 0x10A1        # Play routine entry

# SF2 control bytes
END_MARKER = 0x7F        # End of table / Jump command
LOOP_MARKER = 0x7E       # Loop marker in wave table
GATE_ON = 0x7E           # +++ in sequences
GATE_OFF = 0x80          # --- in sequences
DEFAULT_TRANSPOSE = 0xA0 # No transpose in order list

# Default HR values (hard restart)
HR_DEFAULT_AD = 0x0F     # Fast attack, immediate decay
HR_DEFAULT_SR = 0x00     # No sustain, no release
```

**Full Constants Reference**: See `docs/ARCHITECTURE.md` for complete list including all Laxity memory addresses and SF2 command bytes.

---

## Known Limitations

- **Player Format Compatibility** (v1.8.0 - UPDATED):
  - **SF2-Exported SIDs**: 100% accuracy ✅ (perfect roundtrip)
  - **Laxity NewPlayer v21 → Laxity Driver**: **99.93% accuracy** ✅ (production ready)
  - **Laxity NewPlayer v21 → Driver 11**: 1-8% accuracy ⚠️ (use Laxity driver instead)
  - **Laxity NewPlayer v21 → NP20**: 1-8% accuracy ⚠️ (use Laxity driver instead)
  - **Root Cause**: Format incompatibility solved with custom Laxity driver
  - **See**: `docs/LAXITY_DRIVER_IMPLEMENTATION.md` for complete documentation
- **Only supports Laxity NewPlayer v21** - Other player formats not supported
- **Single subtune per file** - Multi-song SIDs not supported
- **Init, Arp, HR tables use defaults** - Not extracted from original
- **Command parameters not fully extracted** - Some effect details lost
- **SF2 Packer Pointer Relocation Bug** (v0.6.0):
  - Affects 17/18 files in pipeline testing (94%)
  - Files play correctly in VICE, SID2WAV, siddump
  - Only impacts SIDwinder disassembly ("Execution at $0000" error)
  - Under investigation - see `PIPELINE_EXECUTION_REPORT.md`

---

## Running Tests

All tests pass with 100% success rate (v1.4):

```bash
# Unit tests (86 tests + 153 subtests = 100% pass rate)
python scripts/test_converter.py -v
# Result: ✅ 86 passed, 153 subtests passed

# Format validation tests (12 tests)
python scripts/test_sf2_format.py -v

# Pipeline tests (19 tests)
python scripts/test_complete_pipeline.py -v
```

**Test Coverage**:
- ✅ SID parsing and header extraction
- ✅ Laxity player analysis
- ✅ Table extraction (filter, pulse, instruments)
- ✅ Sequence parsing and command mapping
- ✅ SF2 conversion pipeline
- ✅ Roundtrip validation (SID→SF2→SID)
- ✅ All 18 real SID files convertible

---

## Dependencies

- Python 3.x (no external packages required)
- Windows tools: siddump.exe, player-id.exe, SID2WAV.EXE, SIDwinder.exe
- Optional: MinGW (for building C++ sf2pack reference implementation)

---

## Documentation Index

### Quick References
- **CLAUDE.md** (this file) - AI assistant quick reference
- **README.md** - Comprehensive project documentation
- **CONTRIBUTING.md** - Contribution guidelines
- **external-repositories.md** - External source code repositories (NEW)
  - SID Factory II complete source (with driver assembly code)
  - VICE emulator source
  - RetroDebugger source
  - SID-Depacker source

### Core Documentation
- **docs/ARCHITECTURE.md** - Complete system architecture
  - Conversion flow (8 steps)
  - Table extraction strategy
  - SF2 template-based approach
  - Gate system and hard restart
  - Format differences (Laxity vs SF2)
  - Command mappings
  - Complete pipeline (11 steps)
  - SF2 driver reference

- **docs/LAXITY_DRIVER_IMPLEMENTATION.md** - Laxity driver complete guide (v1.8.0)
  - Implementation overview (Phases 1-6)
  - Wave table format fix (99.93% accuracy breakthrough)
  - Memory layout and pointer patching
  - Validation results and production readiness
  - Usage guide and troubleshooting
  - See also: `docs/implementation/` for detailed technical docs

- **docs/SIDDECOMPILER_INTEGRATION.md** - SIDdecompiler analysis integration (v1.4 - NEW)
  - Overview and architecture
  - Phase 1: Basic integration (wrapper module)
  - Phase 2: Enhanced analysis (player detection, memory layout)
  - Phase 3: Auto-detection feasibility (hybrid approach)
  - Phase 4: Validation and impact analysis
  - Production recommendations
  - Test results and metrics

- **docs/analysis/PHASE2_ENHANCEMENTS_SUMMARY.md** - Phase 2 detailed report
  - Enhanced player detection (100 lines added)
  - Memory layout parser (70 lines added)
  - Visual memory map generation (30 lines added)
  - Enhanced structure reports (90 lines added)
  - Test results and integration status

- **docs/analysis/PHASE3_4_VALIDATION_REPORT.md** - Phase 3 & 4 detailed report
  - Auto-detection integration analysis
  - Manual vs auto-detection comparison
  - Detection accuracy results
  - Production recommendations
  - Metrics summary and completion status

- **docs/COMPONENTS_REFERENCE.md** - Python modules reference
  - Core converter (sid_to_sf2.py)
  - SIDdecompiler analyzer (siddecompiler.py v1.4)
  - SF2 Packer (sf2_packer.py v0.6.0)
  - CPU 6502 Emulator (cpu6502_emulator.py v0.6.2)
  - SID Player (sid_player.py v0.6.2)
  - SF2 Player Parser (sf2_player_parser.py v0.6.2)
  - Siddump Extractor (siddump_extractor.py v1.3)
  - Validation system (validation.py v0.6.0)

- **docs/TOOLS_REFERENCE.md** - External tools documentation (NEW)
  - siddump.exe - Register dump tool
  - SIDwinder.exe - SID processor (disassembly, trace, player, relocate)
  - SID2WAV.EXE - Audio renderer
  - player-id.exe - Player identification
  - sf2pack - C++ reference packer
  - RetroDebugger - Real-time debugger (not integrated)

### Format Specifications
- **docs/SID_REGISTERS_REFERENCE.md** - SID chip register quick reference (NEW)
- **docs/SF2_FORMAT_SPEC.md** - Complete SF2 format specification
- **docs/SF2_TRACKS_AND_SEQUENCES.md** - Tracks and sequences format guide (NEW)
  - OrderList format (XXYY: transpose + sequence)
  - Sequence entry format (AA BB CCC: instrument + command + note)
  - Gate control system (+++ sustain vs note retrigger)
  - 3-track parallel system for SID voices
  - Sequence storage and interleaving
  - Track operations and keyboard shortcuts
  - Official SID Factory II tutorial references
- **docs/SF2_INSTRUMENTS_REFERENCE.md** - Instruments format guide (NEW)
  - 6-byte instrument structure
  - ADSR envelope system (Attack/Decay/Sustain/Release)
  - Hard Restart mechanism (bit 7, 2-tick pre-gate-off)
  - Test Bit / Oscillator Reset (bit 4)
  - Waveforms (Triangle 11, Sawtooth 21, Pulse 41, Noise 81)
  - Wave table system with loop commands
  - Pulse width tables
  - Practical examples (snare drum, ADSR patterns)
  - Official SID Factory II tutorial references
- **docs/SF2_DRIVER11_DISASSEMBLY.md** - SF2 Driver 11 player analysis
- **docs/STINSENS_PLAYER_DISASSEMBLY.md** - Laxity NewPlayer v21 analysis
- **docs/CONVERSION_STRATEGY.md** - Laxity to SF2 mapping details
- **docs/DRIVER_REFERENCE.md** - All driver specifications (11-16)
- **docs/format-specification.md** - PSID/RSID formats

### Analysis and Source Code
- **sourcerepository.md** - Complete source code repository index (NEW)
  - C/C++ source (sf2pack, siddump, sf2export, prg2sid)
  - 6502 assembly source (Laxity NewPlayer v21, SID players)
  - Python conversion algorithms
  - Codebase64 archive (100+ projects)
  - Build configurations and disk images
- **docs/SF2_SOURCE_ANALYSIS.md** - SF2 editor source code analysis
- **docs/SIDDUMP_ANALYSIS.md** - Siddump source code analysis
- **tools/SIDWINDER_ANALYSIS.md** - SIDwinder v0.2.6 source analysis (600+ lines)
- **tools/SIDWINDER_QUICK_REFERENCE.md** - SIDwinder command reference
- **tools/RETRODEBUGGER_ANALYSIS.md** - RetroDebugger analysis (70KB+)

### Validation and Testing
- **docs/VALIDATION_SYSTEM.md** - Three-tier validation architecture (v0.6.0)
- **docs/VALIDATION_DASHBOARD_DESIGN.md** - Dashboard & regression tracking system (v1.4)
- **docs/GATE_INFERENCE_IMPLEMENTATION.md** - Waveform-based gate detection (v1.5.0)
- **docs/ACCURACY_ROADMAP.md** - Plan to reach 99% accuracy (v0.6.0)
- **PIPELINE_EXECUTION_REPORT.md** - Complete pipeline execution analysis

### Status Documents
- **PACK_STATUS.md** - SF2 packer implementation details
- **FILE_INVENTORY.md** - Complete file listing

---

## Quick Tips

### For AI Assistants

**When exploring the codebase**, use the Task tool with `subagent_type=Explore` for efficient searching:
```
User: "Where are errors from the client handled?"
Assistant: [Use Task tool with subagent_type=Explore]
```

**When planning implementations**, use EnterPlanMode for non-trivial tasks:
```
User: "Add a new feature to handle user authentication"
Assistant: [Use EnterPlanMode to explore and design approach first]
```

**When converting SID files**, always:
1. Check `info.txt` for conversion warnings
2. Run validation to verify accuracy
3. Listen to both WAV files for audio comparison
4. Compare siddump outputs for register-level differences

**When debugging packer issues**:
1. Check hexdumps for pointer relocation
2. Use SIDwinder disassembly on original (works) vs exported (may fail)
3. Compare memory layouts
4. See `PIPELINE_EXECUTION_REPORT.md` for known issues

---

## Version History

- **v2.1.0** (2025-12-17) - **Recent Files + Visualization + Playback** - Added Recent Files menu with persistent storage (10 files), waveform/filter/envelope visualization, and audio playback controls
- **v2.0.0** (2025-12-15) - **SF2 Viewer released** - Professional PyQt6 GUI for viewing SF2 files
- **v1.8.0** (2025-12-14) - **Laxity driver with 99.93% accuracy** (production ready)
- **v1.7.0** (2025-12-12) - NP20 driver support + Format compatibility research
- **v0.7.2** (2025-12-12) - WAV rendering fix + Waveform analysis tool
- **v1.6.0** (2025-12-12) - Runtime table building implementation
- **v1.5.0** (2025-12-12) - Waveform-based gate inference system
- **v1.4.1** (2025-12-12) - Accuracy validation baseline (71.0% average)
- **v1.3** (2025-12-11) - Added siddump_extractor.py for runtime sequence extraction
- **v1.2** (2025-12-06) - Added SIDwinder trace to pipeline (now working - rebuilt)
- **v1.1** (2025-12-06) - Added SIDwinder disassembly to pipeline
- **v1.0** (2025-12-05) - Complete pipeline with 11 steps
- **v0.6.2** (2025-11-28) - Added CPU emulator, SID player, SF2 parser modules
- **v0.6.1** (2025-11-25) - Multi-file validation reports
- **v0.6.0** (2025-11-20) - Python SF2 packer, accuracy validation system
- **v0.5.0** (2025-10-15) - Initial working converter

---

## Getting Help

**If you encounter issues**:
1. Check `docs/ARCHITECTURE.md` for system details
2. Check `docs/COMPONENTS_REFERENCE.md` for API documentation
3. Check `docs/TOOLS_REFERENCE.md` for tool usage
4. Review `info.txt` files for conversion warnings
5. Run tests to verify system integrity
6. Check `PIPELINE_EXECUTION_REPORT.md` for known limitations

**For specific topics**:
- **Architecture questions** → `docs/ARCHITECTURE.md`
- **Module API questions** → `docs/COMPONENTS_REFERENCE.md`
- **Tool usage questions** → `docs/TOOLS_REFERENCE.md`
- **SID register questions** → `docs/SID_REGISTERS_REFERENCE.md`
- **SF2 format questions** → `docs/SF2_FORMAT_SPEC.md`, `docs/format-specification.md`
- **SF2 tracks/sequences** → `docs/SF2_TRACKS_AND_SEQUENCES.md`
- **SF2 instruments** → `docs/SF2_INSTRUMENTS_REFERENCE.md`
- **Validation questions** → `docs/VALIDATION_SYSTEM.md`
- **Gate inference questions** → `docs/GATE_INFERENCE_IMPLEMENTATION.md`

**Documentation structure optimized for AI assistants**:
- **CLAUDE.md** (this file) - Quick reference loaded on every conversation
- **docs/*** - Detailed documentation loaded on-demand
- **Clear navigation** - Links to detailed docs when more info needed

---

## Version History

- **v2.0.0** (2025-12-14) - Production Ready Release! 100% validated on 286 real Laxity SID files. Complete Laxity driver with SF2 table editing. Zero failures, 6.4 files/sec throughput. Full documentation.
- **v1.9.0** (2025-12-14) - Phase 6 Complete: SF2 table editing implementation, header generator, batch test tool
- **v1.8.0** (2025-12-13) - Phase 5 Complete: Laxity driver API integration, conversion pipeline support
- **v1.7.0** (2025-12-12) - NP20 driver support + Format compatibility research
- **v0.7.2** (2025-12-12) - WAV rendering fix + Waveform analysis tool
- **v1.6.0** (2025-12-12) - Runtime table building implementation
- **v1.5.0** (2025-12-12) - Waveform-based gate inference system
- **v1.4.1** (2025-12-12) - Accuracy validation baseline (71.0% average)
- **v1.3** (2025-12-11) - Added siddump_extractor.py for runtime sequence extraction
- **v1.2** (2025-12-06) - Added SIDwinder trace to pipeline (now working - rebuilt)
- **v1.1** (2025-12-06) - Added SIDwinder disassembly to pipeline
- **v1.0** (2025-12-05) - Complete pipeline with 11 steps
- **v0.6.2** (2025-11-28) - Added CPU emulator, SID player, SF2 parser modules
- **v0.6.1** (2025-11-25) - Multi-file validation reports
- **v0.6.0** (2025-11-20) - Python SF2 packer, accuracy validation system
- **v0.5.0** (2025-10-15) - Initial working converter
