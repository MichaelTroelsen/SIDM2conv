# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2025-12-10

### Added - Siddump Integration
- **NEW MODULE**: `sidm2/siddump_extractor.py` (438 lines)
  - Runtime-based sequence extraction using siddump
  - Parses frame-by-frame SID register captures
  - Detects repeating patterns across 3 voices
  - Converts to SF2 format with proper gate on/off markers
- **Pipeline Enhancement**: Added Step 1.5 to complete_pipeline_with_validation.py
  - Hybrid approach: static tables + runtime sequences
  - 11-step pipeline (was 10)
  - `inject_siddump_sequences()` function for SF2 injection
- **Documentation**:
  - `SIDDUMP_INTEGRATION_SUMMARY.md` - Complete technical summary
  - Updated CLAUDE.md with module documentation

### Fixed
- **Critical**: SF2 sequence format causing editor crashes
  - Implemented proper gate on/off markers per SF2 manual
  - `0x7E` = gate on (+++), `0x80` = gate off (---)
  - Sequences now load correctly in SID Factory II

### Changed
- Updated pipeline step numbering (now 11 steps with 1.5 added)
- Enhanced `SF2_VALIDATION_STATUS.md` with fix details

---

## [1.2.0] - 2025-12-09

### Added - SIDwinder Integration
- **SIDwinder Disassembly**: Integrated SIDwinder into pipeline (Step 9)
  - Generates professional KickAssembler-compatible `.asm` files
  - Works with original SID files (100% success)
- **SIDwinder Trace**: Added trace generation (Step 6)
  - Currently produces empty files (needs SIDwinder rebuild)
  - Patch file ready: `tools/sidwinder_trace_fix.patch`
- **Documentation**:
  - `SIDWINDER_INTEGRATION_SUMMARY.md`
  - `tools/SIDWINDER_QUICK_REFERENCE.md`
  - `tools/SIDWINDER_FIXES_APPLIED.md`

### Known Issues
- SIDwinder disassembly fails on 17/18 exported SID files
  - Root cause: Pointer relocation bug in sf2_packer.py
  - Files play correctly in all emulators (VICE, SID2WAV, siddump)
  - Only affects SIDwinder's strict CPU emulation

---

## [1.1.0] - 2025-12-08

### Added - Pipeline Enhancements
- **Info.txt Generation**: Comprehensive conversion reports
  - Player identification with player-id.exe
  - Address mapping and metadata
  - Conversion method tracking
- **Python Disassembly**: Annotated disassembly generation (Step 8)
  - Custom 6502 disassembler
  - Address and table annotations
- **Hexdump Generation**: Binary comparison support (Step 5)

---

## [1.0.0] - 2025-12-07

### Added - Complete Pipeline
- **`complete_pipeline_with_validation.py`**: 10-step conversion pipeline
  1. SID → SF2 Conversion (static table extraction)
  2. SF2 → SID Packing
  3. Siddump Generation (register dumps)
  4. WAV Rendering (30-second audio)
  5. Hexdump Generation
  6. Info.txt Reports
  7. Python Disassembly
  8. Validation Check
- **Smart Detection**: Automatically identifies SF2-packed vs Laxity format
- **Three Conversion Methods**:
  - REFERENCE: Uses original SF2 as template (100% accuracy)
  - TEMPLATE: Uses generic SF2 template
  - LAXITY: Parses Laxity NewPlayer format
- **Output Structure**: Organized `{filename}/Original/` and `{filename}/New/` folders
- **Validation System**: Checks for all required output files

### Tests
- `test_complete_pipeline.py` (19 tests)
- File type identification tests
- Output integrity validation

---

## [0.6.2] - 2025-12-06

### Added - SID Emulation & Analysis
- **`sidm2/cpu6502_emulator.py`**: Full 6502 CPU emulator (1,242 lines)
  - Complete instruction set with all addressing modes
  - SID register write capture
  - Frame-by-frame state tracking
  - Based on siddump.c architecture
- **`sidm2/sid_player.py`**: High-level SID file player (560 lines)
  - PSID/RSID header parsing
  - Note detection and frequency analysis
  - Siddump-compatible frame dump output
- **`sidm2/sf2_player_parser.py`**: SF2-exported SID parser (389 lines)
  - Pattern-based table extraction
  - Heuristic extraction mode
  - Tested with 15 SIDSF2player files

---

## [0.6.1] - 2025-12-05

### Added - Validation Enhancements
- **`generate_validation_report.py`**: Multi-file validation report generator
  - HTML report with statistics and analysis
  - Categorizes warnings (Instrument Pointer Bounds, Note Range, etc.)
  - Identifies systematic vs file-specific issues
- **Improved Boundary Checking**: Reduced false-positive warnings by 50%

---

## [0.6.0] - 2025-12-04

### Added - SID Accuracy Validation
- **`validate_sid_accuracy.py`**: Frame-by-frame register comparison
  - Compares original SID vs exported SID using siddump
  - Measures Overall, Frame, Voice, Register, and Filter accuracy
  - 30-second validation for detailed analysis
  - Generates accuracy grades (EXCELLENT/GOOD/FAIR/POOR)
- **`sidm2/validation.py`**: Lightweight validation for pipeline
  - `quick_validate()` for 10-second batch validation
  - `generate_accuracy_summary()` for info.txt files
- **Documentation**:
  - `docs/VALIDATION_SYSTEM.md` - Three-tier architecture
  - `docs/ACCURACY_ROADMAP.md` - Plan to reach 99% accuracy

### Metrics
- Accuracy formula: `Overall = Frame×0.40 + Voice×0.30 + Register×0.20 + Filter×0.10`
- Baseline: Angular.sid at 9.0% overall (POOR)
- Target: 99% overall accuracy

---

## [0.5.0] - 2025-11-30

### Added - Python SF2 Packer
- **`sidm2/sf2_packer.py`**: Pure Python SF2 to SID packer
  - Generates VSID-compatible SID files
  - Uses `sidm2/cpu6502.py` for pointer relocation
  - Average output: ~3,800 bytes
  - Integrated into `convert_all.py`
- **`PACK_STATUS.md`**: Implementation details and test results

### Known Issues
- Pointer relocation bug affects SIDwinder disassembly (94% of files)
- Files play correctly in VICE, SID2WAV, siddump

---

## [0.4.0] - 2025-11-25

### Added - Round-trip Validation
- **`test_roundtrip.py`**: Complete SID→SF2→SID validation
  - 8-step automated testing
  - HTML reports with detailed comparisons
  - Uses siddump for register-level verification
- **`convert_all.py --roundtrip`**: Batch round-trip validation

---

## [0.3.0] - 2025-11-20

### Added - Batch Conversion
- **`convert_all.py`**: Batch conversion script
  - Processes all SID files in directory
  - Generates both NP20 and Driver 11 versions
  - Creates organized output structure

---

## [0.2.0] - 2025-11-15

### Added - SF2 Export
- **`sf2_to_sid.py`**: SF2 to SID exporter
  - Exports SF2 files back to playable SID format
  - PSID v2 header generation
  - Integration with driver templates

---

## [0.1.0] - 2025-11-10

### Added - Initial Release
- **`sid_to_sf2.py`**: Core SID to SF2 converter
  - Laxity NewPlayer v21 support
  - Table extraction (instruments, wave, pulse, filter)
  - SF2 Driver 11 template-based approach
- **Test Suite**: 69 tests
- **Documentation**:
  - README.md with format specifications
  - SF2_FORMAT_SPEC.md
  - DRIVER_REFERENCE.md

---

## Archive

### Experimental Files (Archived 2025-12-10)

All experimental scripts and documentation moved to `archive/` directory:

**Experiments** (`archive/experiments/`):
- 40+ experimental Python scripts for sequence extraction research
- Various approaches to SF2 format reverse engineering
- Siddump parsing experiments
- Table extraction prototypes

**Old Documentation** (`archive/old_docs/`):
- Multiple status reports from development process
- Sequence extraction investigation notes
- Format analysis documents
- Test verification reports

See `archive/README.md` for details on archived content.

---

## [Unreleased]

### To Do
- Fix pointer relocation bug in sf2_packer.py
- Improve accuracy from 9% to 99% (see ACCURACY_ROADMAP.md)
- Rebuild SIDwinder.exe with trace fixes
- Add support for additional player formats
- Implement sequence optimization and deduplication
