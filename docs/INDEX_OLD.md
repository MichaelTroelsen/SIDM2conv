# Complete Documentation Index - SIDM2 Project

**Updated**: 2025-12-06
**Pipeline Version**: 1.2
**SIDwinder Integration**: Complete

This document provides a comprehensive navigation guide to all project documentation, organized by topic and use case.

---

## Quick Start

| Document | Purpose | Audience |
|----------|---------|----------|
| [README.md](README.md) | User guide and complete reference | End users |
| [CLAUDE.md](CLAUDE.md) | AI assistant project guide | AI/LLMs |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines | Contributors |

---

## Pipeline Documentation

### Complete Pipeline (v1.2)

| Document | Content |
|----------|---------|
| [Complete Pipeline in README.md](README.md#complete-pipeline-with-validation-v12) | User guide with examples |
| [Complete Pipeline in CLAUDE.md](CLAUDE.md#complete-pipeline-with-validation---new-in-v10-updated-v12) | Technical specification |
| [PIPELINE_EXECUTION_REPORT.md](PIPELINE_EXECUTION_REPORT.md) | Detailed execution analysis (18 files, 2025-12-06) |
| [PIPELINE_RESULTS_SUMMARY.md](PIPELINE_RESULTS_SUMMARY.md) | Quick results summary |

### Pipeline Components

**10 Steps**:
1. SID → SF2 Conversion (3 methods: Reference/Template/Laxity)
2. SF2 → SID Packing (Python packer v0.6.0)
3. Siddump Generation (siddump.exe - register dumps)
4. WAV Rendering (SID2WAV.EXE - 30-second audio)
5. Hexdump Generation (xxd - binary analysis)
6. **SIDwinder Trace** (NEW v1.2 - register write traces)
7. Info.txt Reports (generate_info.py)
8. Annotated Disassembly (annotating_disassembler.py)
9. **SIDwinder Disassembly** (NEW v1.1 - KickAssembler output)
10. Validation Check (13 files verified)

**Output**: 13 files per SID (4 in Original/, 9 in New/)

---

## SIDwinder Integration Documentation

### Overview Documents

| Document | Content |
|----------|---------|
| [SIDwinder in README.md](README.md#sidwinder-integration) | User guide with all commands |
| [SIDwinder in CLAUDE.md](CLAUDE.md#sidwinder-tool-details) | Technical details and integration |
| [SIDWINDER_INTEGRATION_SUMMARY.md](SIDWINDER_INTEGRATION_SUMMARY.md) | Complete integration work summary |
| [SIDWINDER_REBUILD_GUIDE.md](SIDWINDER_REBUILD_GUIDE.md) | How to rebuild executable |
| [tools/SIDWINDER_QUICK_REFERENCE.md](tools/SIDWINDER_QUICK_REFERENCE.md) | Command quick reference |

### Technical Details

**Version**: SIDwinder v0.2.6
**Source**: `C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6\src\`
**Executable**: `tools/SIDwinder.exe`

**4 Main Features**:
1. ✅ **Disassemble** - Converts SID to KickAssembler source (WORKING - integrated)
2. ⚠️ **Trace** - SID register write tracer (NEEDS REBUILD - source patched)
3. 🔧 **Player** - Links SID with visualization players (manual use)
4. 🔧 **Relocate** - Moves SID to different memory addresses (manual use)

**Integration Status**:
- Step 6: Trace generation (files created, content pending rebuild)
- Step 9: Disassembly generation (works for original SIDs)

**Patches Applied**:
- `SIDEmulator.cpp` - Fixed callback enable (line 129)
- `TraceLogger.h` - Added logWrite() declaration
- `TraceLogger.cpp` - Implemented logWrite() method
- Patch file: `tools/sidwinder_trace_fix.patch`

### Known Limitations

**SIDwinder Disassembly of Exported SIDs**:
- **Impact**: 17/18 exported SIDs fail with "Execution at $0000"
- **Cause**: Pointer relocation bug in `sidm2/sf2_packer.py`
- **Scope**: Only affects SIDwinder's strict emulation
- **Workaround**: Original SIDs disassemble perfectly
- **Note**: Files play correctly in all standard emulators (VICE, SID2WAV, siddump)

**SIDwinder Trace Content**:
- **Status**: Files generated (36/36), content empty until rebuild
- **Fix**: Rebuild SIDwinder.exe with applied patches
- **See**: SIDWINDER_REBUILD_GUIDE.md

---

## Format Documentation

### SID Formats

| Document | Content |
|----------|---------|
| [PSID/RSID Format in README.md](README.md#psidrsid-format-input) | Header structure and C64 data |
| [Laxity NewPlayer v21 in README.md](README.md#jch-newplayer-v21-format-laxity-player) | Complete format specification |
| [STINSENS_PLAYER_DISASSEMBLY.md](docs/STINSENS_PLAYER_DISASSEMBLY.md) | Full Laxity player disassembly |

### SF2 Formats

| Document | Content |
|----------|---------|
| [SF2_FORMAT_SPEC.md](docs/SF2_FORMAT_SPEC.md) | Complete SF2 format specification |
| [DRIVER_REFERENCE.md](docs/DRIVER_REFERENCE.md) | All driver specifications (11-16, NP20) |
| [CONVERSION_STRATEGY.md](docs/CONVERSION_STRATEGY.md) | Laxity to SF2 mapping details |

### Implementation Analysis

| Document | Content |
|----------|---------|
| [SF2_SOURCE_ANALYSIS.md](docs/SF2_SOURCE_ANALYSIS.md) | SF2 editor source code analysis |
| [SIDDUMP_ANALYSIS.md](docs/SIDDUMP_ANALYSIS.md) | Siddump tool source analysis |

---

## Tool Documentation

### External Tools

| Tool | Location | Documentation |
|------|----------|---------------|
| **SIDwinder** | tools/SIDwinder.exe | [README.md](README.md#sidwinder-v026), [Quick Reference](tools/SIDWINDER_QUICK_REFERENCE.md) |
| **siddump** | tools/siddump.exe | [README.md](README.md#siddump), [CLAUDE.md](CLAUDE.md#siddump-tool-details) |
| **player-id** | tools/player-id.exe | [README.md](README.md#player-id) |
| **SID2WAV** | tools/SID2WAV.EXE | [CLAUDE.md](CLAUDE.md#external-tools) |
| **sf2pack** | tools/sf2pack/sf2pack.exe | [README.md](README.md#sf2pack) |

### Python Tools

| Tool | Purpose | Documentation |
|------|---------|---------------|
| sid_to_sf2.py | Main converter | [README.md](README.md#basic-conversion) |
| sf2_to_sid.py | SF2 exporter | [CLAUDE.md](CLAUDE.md#python-sf2-packer-sidm2sf2_packerpy---new-in-v060) |
| convert_all.py | Batch converter | [README.md](README.md#batch-conversion) |
| complete_pipeline_with_validation.py | Complete pipeline | [README.md](README.md#complete-pipeline-with-validation-v12) |
| generate_info.py | Info.txt generator | [README.md](README.md#generate_infopy) |
| extract_addresses.py | Address extraction | [README.md](README.md#address-extraction) |
| annotating_disassembler.py | Python disassembly | [CLAUDE.md](CLAUDE.md#main-converter-sid_to_sf2py) |

---

## Validation Documentation

### Validation System

| Document | Content |
|----------|---------|
| [VALIDATION_SYSTEM.md](docs/VALIDATION_SYSTEM.md) | Three-tier validation architecture |
| [ACCURACY_ROADMAP.md](docs/ACCURACY_ROADMAP.md) | Plan to reach 99% accuracy |
| [PACK_STATUS.md](PACK_STATUS.md) | SF2 packer implementation status |

### Test Suites

| Test File | Purpose | Test Count |
|-----------|---------|------------|
| test_converter.py | Unit tests | 69 tests |
| test_sf2_format.py | Format validation | Multiple |
| test_complete_pipeline.py | Pipeline validation | 19 tests |
| test_sf2_editor.py | Editor automation | N/A |

### Validation Tools

| Tool | Purpose |
|------|---------|
| test_roundtrip.py | Complete SID→SF2→SID validation |
| validate_sid_accuracy.py | Frame-by-frame register comparison |
| generate_validation_report.py | Multi-file validation reports |

---

## Development Documentation

### Architecture

| Topic | Documentation |
|-------|---------------|
| Project Structure | [README.md](README.md#project-structure), [CLAUDE.md](CLAUDE.md#project-structure) |
| Code Conventions | [CLAUDE.md](CLAUDE.md#code-conventions) |
| Important Constants | [CLAUDE.md](CLAUDE.md#important-constants) |
| CI/CD Rules | [CLAUDE.md](CLAUDE.md#cicd-rules) |

### Package Modules (sidm2/)

| Module | Purpose |
|--------|---------|
| sf2_packer.py | SF2 → SID packer (v0.6.0) |
| cpu6502.py | 6502 emulator for pointer relocation |
| cpu6502_emulator.py | Full 6502 emulator (v0.6.2) |
| sid_player.py | SID player and analyzer |
| sf2_player_parser.py | SF2-exported SID parser |

---

## Pipeline Execution Results

### Latest Run (2025-12-06)

| Metric | Result |
|--------|--------|
| **Total SID files** | 18 |
| **Execution time** | ~2.5 minutes |
| **Complete success** | 1/18 (5.6%) - all 13 files |
| **Partial success** | 17/18 (94.4%) - 12/13 files |
| **Total files generated** | 229 files |

### Step-by-Step Results

| Step | Success Rate | Status |
|------|--------------|--------|
| 1-5, 7-8 | 100% | ✅ Perfect |
| 6. SIDwinder Trace | 100% files | ⚠️ Empty (rebuild needed) |
| 9. SIDwinder Disassembly | 5.6% | ❌ Packer limitation |
| 10. Validation | 94.4% partial | ⚠️ Depends on step 9 |

**Files Generated per SID**:
- **Original/**: 4 files (.dump, .hex, .txt, .wav)
- **New/**: 8-9 files (.sf2, .sid, .dump, .hex, .txt, .wav, info.txt, _disassembly.md, _sidwinder.asm*)

*_sidwinder.asm missing for 17/18 files due to known limitation

**See**: [PIPELINE_EXECUTION_REPORT.md](PIPELINE_EXECUTION_REPORT.md) for detailed analysis

---

## File Formats Reference

### Input Files

- **PSID v2**: Standard SID file format
- **Laxity NewPlayer v21**: JCH NewPlayer format
- **SF2**: SID Factory II project files

### Output Files

#### Per-Song Output (13 files total)

**Original/** (4 files):
1. `{name}_original.dump` - Siddump register capture
2. `{name}_original.hex` - Binary hexdump (xxd format)
3. `{name}_original.txt` - SIDwinder trace (empty until rebuild)
4. `{name}_original.wav` - 30-second audio rendering

**New/** (9 files):
1. `{name}.sf2` - Converted SF2 file
2. `{name}_exported.sid` - Packed SID file
3. `{name}_exported.dump` - Siddump register capture
4. `{name}_exported.hex` - Binary hexdump
5. `{name}_exported.txt` - SIDwinder trace (empty until rebuild)
6. `{name}_exported.wav` - 30-second audio rendering
7. `{name}_exported_disassembly.md` - Python annotated disassembly
8. `{name}_exported_sidwinder.asm` - SIDwinder disassembly (limited)
9. `info.txt` - Comprehensive conversion report

---

## Quick Command Reference

### Core Workflows

```bash
# Complete pipeline (recommended)
python complete_pipeline_with_validation.py

# Single file conversion
python sid_to_sf2.py SID/song.sid output.sf2

# Round-trip validation
python test_roundtrip.py SID/song.sid

# Batch conversion
python convert_all.py

# SIDwinder disassembly
tools/SIDwinder.exe -disassemble SID/song.sid output.asm

# SIDwinder trace (after rebuild)
tools/SIDwinder.exe -trace=output.txt SID/song.sid
```

### Testing

```bash
# Run all unit tests
python test_converter.py

# Pipeline validation
python test_complete_pipeline.py -v

# Format tests
python test_sf2_format.py
```

---

## Documentation Changelog

### 2025-12-06 (Pipeline v1.2)

**Added**:
- SIDwinder integration (Steps 6 & 9)
- Complete pipeline documentation
- SIDwinder command reference
- Pipeline execution reports
- Known limitations documentation

**Updated**:
- README.md - Complete SIDwinder integration
- CLAUDE.md - Pipeline v1.2 details
- Project structure - All new files
- Tool documentation - SIDwinder sections

**Created**:
- SIDWINDER_INTEGRATION_SUMMARY.md
- SIDWINDER_REBUILD_GUIDE.md
- tools/SIDWINDER_QUICK_REFERENCE.md
- PIPELINE_EXECUTION_REPORT.md
- PIPELINE_RESULTS_SUMMARY.md
- COMPLETE_DOCUMENTATION_INDEX.md (this file)

### Previous Versions

- v0.6.3 (2025-12-02) - Pipeline enhancement, info.txt improvements
- v0.6.2 - CPU 6502 emulator, SID player, SF2 player parser
- v0.6.1 - Multi-file validation reporting
- v0.6.0 - Python SF2 packer, validation system

---

## Navigation Guide

### I want to...

**...use the tool**:
→ Start with [README.md](README.md)

**...understand how it works**:
→ Read [CLAUDE.md](CLAUDE.md)

**...use SIDwinder**:
→ See [tools/SIDWINDER_QUICK_REFERENCE.md](tools/SIDWINDER_QUICK_REFERENCE.md)

**...run the complete pipeline**:
→ See [Complete Pipeline in README.md](README.md#complete-pipeline-with-validation-v12)

**...understand SID formats**:
→ See [Laxity NewPlayer in README.md](README.md#jch-newplayer-v21-format-laxity-player)

**...understand SF2 formats**:
→ See [SF2_FORMAT_SPEC.md](docs/SF2_FORMAT_SPEC.md)

**...see pipeline results**:
→ See [PIPELINE_EXECUTION_REPORT.md](PIPELINE_EXECUTION_REPORT.md)

**...rebuild SIDwinder**:
→ See [SIDWINDER_REBUILD_GUIDE.md](SIDWINDER_REBUILD_GUIDE.md)

**...contribute code**:
→ See [CONTRIBUTING.md](CONTRIBUTING.md) and [CLAUDE.md](CLAUDE.md#cicd-rules)

**...validate accuracy**:
→ See [VALIDATION_SYSTEM.md](docs/VALIDATION_SYSTEM.md)

---

## Document Hierarchy

```
SIDM2/
├── README.md ..................... PRIMARY USER GUIDE
├── CLAUDE.md ..................... AI ASSISTANT GUIDE
├── COMPLETE_DOCUMENTATION_INDEX.md  THIS FILE - NAVIGATION HUB
│
├── Pipeline Documentation
│   ├── PIPELINE_EXECUTION_REPORT.md ....... Detailed execution analysis
│   ├── PIPELINE_RESULTS_SUMMARY.md ........ Quick results summary
│   └── PACK_STATUS.md ..................... SF2 packer status
│
├── SIDwinder Documentation
│   ├── SIDWINDER_INTEGRATION_SUMMARY.md ... Complete integration work
│   ├── SIDWINDER_REBUILD_GUIDE.md ......... Rebuild instructions
│   └── tools/SIDWINDER_QUICK_REFERENCE.md . Command reference
│
├── Format Documentation
│   ├── docs/SF2_FORMAT_SPEC.md ............ SF2 complete spec
│   ├── docs/DRIVER_REFERENCE.md ........... All drivers (11-16, NP20)
│   ├── docs/STINSENS_PLAYER_DISASSEMBLY.md  Laxity player analysis
│   └── docs/CONVERSION_STRATEGY.md ........ Laxity→SF2 mapping
│
└── Validation Documentation
    ├── docs/VALIDATION_SYSTEM.md .......... Validation architecture
    └── docs/ACCURACY_ROADMAP.md ........... Accuracy improvement plan
```

---

**Last Updated**: 2025-12-06
**Pipeline Version**: 1.2
**Total Documentation Files**: 20+
**Status**: Complete and comprehensive
