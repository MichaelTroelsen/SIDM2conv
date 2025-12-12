# CLAUDE.md - Project Guide for AI Assistants

## Project Overview

SID to SF2 Converter - Converts Commodore 64 SID music files (Laxity NewPlayer v21) to SID Factory II (.sf2) format for editing and remixing.

**Supported Formats**:
- **Input**: Laxity NewPlayer v21 SID files only
- **Output**: SID Factory II .sf2 format (Driver 11 or NP20)

---

## Quick Start

```bash
# Convert single file
python scripts/sid_to_sf2.py SID/input.sid output/SongName/New/output.sf2

# Batch convert all SID files (generates both NP20 and Driver 11 versions)
python scripts/convert_all.py

# Batch convert with round-trip validation
python scripts/convert_all.py --roundtrip

# Test single file round-trip (SID→SF2→SID)
python scripts/test_roundtrip.py SID/input.sid

# Complete pipeline with full validation (11+ steps: conversion, packing, dumps, accuracy, WAV, hex, trace, info, disassembly, validation)
# NEW in v1.4.1: Automatic accuracy calculation integrated!
python complete_pipeline_with_validation.py

# CI/CD workflow runs automatically on PR/push (v1.4.2)
# See .github/workflows/validation.yml
```

---

## Project Structure

```
SIDM2/
├── complete_pipeline_with_validation.py  # Complete 11-step pipeline (main entry point)
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
│   ├── accuracy.py        # Accuracy calculation module (v1.4.1)
│   └── validation.py      # Validation utilities (v0.6.0)
│
├── tools/                 # External tools
│   ├── siddump.exe        # SID register dump tool (6502 emulation)
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
├── docs/                  # Documentation (see Documentation Index below)
└── learnings/             # Reference materials and source docs
```

---

## Essential Workflows

### Single File Conversion

```bash
# 1. Convert SID to SF2
python scripts/sid_to_sf2.py SID/Song.sid output/Song/New/Song.sf2

# 2. Check conversion report
cat output/Song/New/info.txt
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

```bash
# Unit tests (69 tests)
python scripts/test_converter.py -v

# Format validation tests (12 tests)
python scripts/test_sf2_format.py -v

# Pipeline tests (19 tests)
python scripts/test_complete_pipeline.py -v
```

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

### Core Documentation
- **docs/ARCHITECTURE.md** - Complete system architecture (NEW)
  - Conversion flow (8 steps)
  - Table extraction strategy
  - SF2 template-based approach
  - Gate system and hard restart
  - Format differences (Laxity vs SF2)
  - Command mappings
  - Complete pipeline (11 steps)
  - SF2 driver reference

- **docs/COMPONENTS_REFERENCE.md** - Python modules reference (NEW)
  - Core converter (sid_to_sf2.py)
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
- **docs/SF2_DRIVER11_DISASSEMBLY.md** - SF2 Driver 11 player analysis
- **docs/STINSENS_PLAYER_DISASSEMBLY.md** - Laxity NewPlayer v21 analysis
- **docs/CONVERSION_STRATEGY.md** - Laxity to SF2 mapping details
- **docs/DRIVER_REFERENCE.md** - All driver specifications (11-16)
- **docs/format-specification.md** - PSID/RSID formats

### Analysis and Source Code
- **docs/SF2_SOURCE_ANALYSIS.md** - SF2 editor source code analysis
- **docs/SIDDUMP_ANALYSIS.md** - Siddump source code analysis
- **tools/SIDWINDER_ANALYSIS.md** - SIDwinder v0.2.6 source analysis (600+ lines)
- **tools/SIDWINDER_QUICK_REFERENCE.md** - SIDwinder command reference
- **tools/RETRODEBUGGER_ANALYSIS.md** - RetroDebugger analysis (70KB+)

### Validation and Testing
- **docs/VALIDATION_SYSTEM.md** - Three-tier validation architecture (v0.6.0)
- **docs/VALIDATION_DASHBOARD_DESIGN.md** - Dashboard & regression tracking system (v1.4)
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

- **v1.3** (2025-12-11) - Added siddump_extractor.py for runtime sequence extraction
- **v1.2** (2025-12-06) - Added SIDwinder trace to pipeline (requires rebuild)
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
- **Format questions** → `docs/SF2_FORMAT_SPEC.md`, `docs/format-specification.md`
- **Validation questions** → `docs/VALIDATION_SYSTEM.md`
- **Accuracy questions** → `docs/ACCURACY_ROADMAP.md`

**Documentation structure optimized for AI assistants**:
- **CLAUDE.md** (this file) - Quick reference loaded on every conversation
- **docs/*** - Detailed documentation loaded on-demand
- **Clear navigation** - Links to detailed docs when more info needed
