# SIDM2 Project Context

**Version**: 2.9.0
**Last Updated**: 2025-12-26
**Status**: 🚧 Active Development - SF2 Format Validation Fixes
**Current Focus**: SF2 Editor Compatibility & Metadata Validation

---

## Current State Snapshot

### What We're Working On RIGHT NOW (2025-12-26)

**Critical Issue**: SF2 files being rejected by SID Factory II editor due to metadata format issues.

**Active Changes** (uncommitted):
- `sidm2/sf2_header_generator.py` - Adding missing descriptor fields
  - ✅ Added Commands table descriptor (was missing!)
  - ✅ Added visible_rows field to all table descriptors
  - ✅ Fixed table ID sequencing (0-5 instead of 0-4)
- `sidm2/sf2_writer.py` - Enhanced validation and logging
  - ✅ Added detailed SF2 structure logging (`_log_sf2_structure`)
  - ✅ Added Block 3 (Driver Tables) structure validation
  - ✅ Added Block 5 (Music Data) structure validation
  - ✅ Added SF2 file validation after write
- `drivers/laxity/sf2driver_laxity_00.prg` - Binary driver updates
  - ⚠️ Multiple backup versions present (`.backup`, `.new`, `.old_order`)
  - 🔍 Iterative testing in progress

**Recent Commits** (critical fixes):
1. `9948703` - "Add missing descriptor fields - ACTUAL root cause fix"
2. `0e2c49b` - "Fix SF2 block ordering - CRITICAL editor validation fix"
3. `e9cc32e` - "Fix SF2 metadata corruption causing editor rejection"
4. `555e7ca` - "Clean up root folder and strengthen test file rules"
5. `efd88ec` - "Correct player detection to prevent Laxity files being misidentified"

### What Just Happened (Context for Understanding)

**SF2 Format Validation Crisis** (Dec 25-26, 2025):
- **Problem**: Generated SF2 files rejected by SID Factory II editor
- **Root Cause**: Missing descriptor fields + incorrect block ordering
- **Impact**: All generated SF2 files potentially invalid for editing
- **Resolution**: In progress (3 commits + active changes)

**Investigation Steps Taken**:
1. Compared working SF2 files vs generated ones (binary diff)
2. Identified missing Commands table in Block 3
3. Discovered missing visible_rows field in table descriptors
4. Found block ordering issues (magic number placement)
5. Added extensive logging to debug structure

**Current Testing**:
- Multiple driver file backups suggest iterative validation
- SID Factory II being tested with generated files
- Likely using test files: `Stinsens_Last_Night_of_89.sid`, `Broware.sid`

---

## Project Overview

### What is SIDM2?

SIDM2 converts Commodore 64 SID music files to SID Factory II (SF2) format for editing and remixing.

**Key Achievement**: 99.93% frame accuracy for Laxity NewPlayer v21 files using custom driver.

### Core Technologies

- **Language**: Python 3.9+
- **GUI Framework**: PyQt6 (for SF2 Viewer and Conversion Cockpit)
- **External Tools**:
  - `tools/siddump.exe` (SID emulator/validator)
  - `tools/player-id.exe` (player type detection)
  - `tools/SIDwinder.exe` (disassembler)
  - `tools/SIDdecompiler.exe` (memory layout analyzer)

### Architecture

```
Input: SID file → Analysis → Driver Selection → SF2 Generation → Validation → Output: SF2 file
                                                                    ↓
                                     SF2 file → Packing → Output: Playable SID file
```

**Driver Selection Matrix** (Quality-First Policy v2.0):
- Laxity NP21 → Laxity Driver (99.93% accuracy)
- SF2-exported → Driver 11 (100% accuracy)
- NewPlayer 20 → NP20 Driver (70-90% accuracy)
- Unknown → Driver 11 (safe default)

---

## Key Statistics

### Accuracy Metrics
- **Laxity Driver**: 99.93% frame accuracy (507/507 register writes)
- **SF2 Roundtrip**: 100% accuracy (perfect)
- **Test Suite**: 200+ tests, 100% pass rate
- **Real-world Validation**: 286 Laxity files, 100% success

### Codebase Stats
- **Python Files**: ~30 active scripts (68 archived)
- **Test Coverage**: 200+ tests across 12 test files
- **Documentation**: 40+ markdown files in `docs/`
- **SID Collection**: 658+ files cataloged (v2.9.0)

### Performance
- **Conversion Speed**: 8.1 files/second (Laxity batch)
- **Concurrent Processing**: 3.1x speedup with 4 workers
- **SF2 Viewer Launch**: <2 seconds
- **Validation Run**: ~1 minute for 18 files

---

## Project Structure

```
SIDM2/
├── pyscript/              # ALL Python scripts (v2.6+)
│   ├── conversion_cockpit_gui.py       # Batch conversion GUI
│   ├── sf2_viewer_gui.py               # SF2 file viewer
│   ├── siddump_complete.py             # Python siddump (100% complete)
│   ├── sidwinder_trace.py              # Python SIDwinder (100% complete)
│   ├── create_sid_inventory.py         # SID catalog generator (v2.9)
│   └── test_*.py                       # 200+ unit tests
├── scripts/               # Production conversion tools
│   ├── sid_to_sf2.py                  # Main SID→SF2 converter
│   ├── sf2_to_sid.py                  # SF2→SID packer
│   └── validate_sid_accuracy.py       # Frame-by-frame validator
├── sidm2/                 # Core Python package
│   ├── laxity_parser.py               # Laxity format parser
│   ├── laxity_converter.py            # Laxity→SF2 converter
│   ├── sf2_packer.py                  # SF2→SID packer
│   ├── sf2_header_generator.py        # ⚠️ ACTIVE: SF2 header generation
│   ├── sf2_writer.py                  # ⚠️ ACTIVE: SF2 file writer
│   ├── driver_selector.py             # Auto driver selection (v2.8)
│   └── siddump.py                     # Siddump integration
├── drivers/
│   └── laxity/
│       └── sf2driver_laxity_00.prg    # ⚠️ ACTIVE: Custom Laxity driver
├── G5/drivers/            # SF2 driver templates
│   ├── driver11_template.sf2
│   ├── np20_template.sf2
│   └── examples/
├── docs/                  # Documentation (40+ files)
│   ├── guides/            # User guides
│   ├── reference/         # Technical references
│   ├── analysis/          # Research & analysis docs
│   ├── implementation/    # Implementation details
│   └── integration/       # Policy & integration docs (v2.9)
├── validation/            # Validation system data
│   ├── database.sqlite    # Historical validation data
│   └── dashboard.html     # Interactive dashboard
├── test_collections/      # 658+ SID test files
│   ├── Laxity/           # 286 Laxity NP21 files
│   ├── Tel_Jeroen/       # 150+ Jeroen Tel files
│   ├── Hubbard_Rob/      # 100+ Rob Hubbard files
│   └── Galway_Martin/    # 60+ Martin Galway files
└── *.bat                  # Windows launchers
```

---

## Current Issues & Blockers

### 🔴 Critical (Blocking Release)

**SF2 Editor Compatibility** (Active Work):
- **Issue**: Generated SF2 files rejected by SID Factory II editor
- **Status**: 3 commits + active changes in progress
- **Impact**: Users cannot edit generated SF2 files
- **ETA**: Testing in progress (1-2 days)

### 🟡 Known Limitations

1. **Filter Accuracy**: 0% (Laxity filter format not converted)
   - Impact: Filter effects not preserved
   - Workaround: Manual editing in SF2 editor

2. **Voice 3**: Untested (no test files available)
   - Impact: Unknown if 3-voice files work correctly
   - Workaround: Test with 2-voice files only

3. **Multi-subtune**: Not supported
   - Impact: Only first subtune converted
   - Workaround: Extract subtunes separately

4. **Pointer Relocation Bug** (Medium Priority):
   - **Issue**: 17/18 files fail SIDwinder disassembly
   - **Impact**: Debugging only (files play correctly)
   - **Status**: Investigation ongoing

---

## Development Guidelines

### Before Making Changes

1. **Check git status** - Understand what's currently modified
2. **Read recent commits** - Understand recent changes
3. **Check this file** - Understand current focus
4. **Run tests** - Ensure baseline works: `test-all.bat`

### Before Committing

1. **Run tests**: `test-all.bat` (200+ tests must pass)
2. **Update docs**:
   - README.md (if features changed)
   - CLAUDE.md (if structure changed)
   - This file (CONTEXT.md) with current state
3. **Run cleanup**: `cleanup.bat --scan` (if files added/removed)
4. **Update inventory**: `update-inventory.bat` (if files moved)

### File Organization Rules

⚠️ **CRITICAL**: ALL `.py` files MUST be in `pyscript/` or `scripts/` or `sidm2/`
- ❌ NO `.py` files in project root
- ✅ Use `cleanup.bat --scan` to check compliance
- 📋 See `docs/guides/ROOT_FOLDER_RULES.md`

### Testing Workflow

```bash
# Quick test (specific module)
python -m pytest scripts/test_converter.py -v

# Full test suite (all 200+ tests)
test-all.bat

# Specific test case
python -m pytest scripts/test_converter.py::TestConverter::test_laxity_accuracy -v

# Coverage report
python -m pytest --cov=sidm2 --cov-report=html
```

---

## Quick Reference

### Common Tasks

**Convert single file**:
```bash
sid-to-sf2.bat input.sid output.sf2
```

**Batch convert Laxity files**:
```bash
batch-convert-laxity.bat
```

**View SF2 file**:
```bash
sf2-viewer.bat [file.sf2]
```

**Launch Conversion Cockpit**:
```bash
conversion-cockpit.bat
```

**Generate SID inventory**:
```bash
create-sid-inventory.bat
```

**Validate conversion accuracy**:
```bash
python scripts/validate_sid_accuracy.py input.sid output.sid
```

### Important Files

**Configuration**:
- `.claude/settings.local.json` - Claude Code settings
- `.gitignore` - Git ignore rules

**Documentation**:
- `README.md` - Main project documentation
- `CLAUDE.md` - AI assistant quick reference
- `CONTEXT.md` - This file (current state)
- `docs/STATUS.md` - Project status overview
- `docs/ROADMAP.md` - Future plans

**Core Modules**:
- `sidm2/sf2_writer.py` - ⚠️ Currently being modified
- `sidm2/sf2_header_generator.py` - ⚠️ Currently being modified
- `sidm2/laxity_converter.py` - Laxity conversion logic
- `sidm2/sf2_packer.py` - SF2→SID packing

---

## Version History (Recent)

### v2.9.0 (2025-12-24) - SID Inventory System
- SID Inventory System (658+ files cataloged)
- Pattern Database (validated player identification)
- Pattern Analysis Tools (5 new scripts)
- Policy Documentation (organized in docs/integration/)

### v2.8.0 (2025-12-22) - Auto Driver Selection
- Automatic Driver Selection (Quality-First Policy v2.0)
- Python SIDwinder (100% complete, cross-platform)
- Driver documentation (info files for conversions)
- SF2 format validation (automatic after conversion)

### v2.6.0 (2025-12-22) - Python siddump
- Python siddump (100% musical content accuracy)
- 38 unit tests (100% pass rate)
- Cross-platform (Mac/Linux/Windows)

### v2.5.3 (2025-12-22) - Enhanced Logging
- Enhanced Logging System v2.0.0 (4 levels, JSON, rotation)
- CLI flags: `-v`, `-vv`, `-q`, `--debug`, `--log-file`

---

## Next Steps

### Immediate (This Week)
1. ✅ Complete SF2 format validation fixes
2. ✅ Test with SID Factory II editor
3. ✅ Commit working changes
4. 📝 Update documentation (README, CHANGELOG)
5. 🚀 Release v2.9.1 with fixes

### Short Term (This Month)
1. Implement filter support (Roadmap Track 1.1)
2. Investigate 100% accuracy gap (Roadmap Track 1.3)
3. Expand test coverage to 250+ tests

### Medium Term (This Quarter)
1. Fix pointer relocation bug
2. Add NP20 driver support
3. Improve error messages
4. Publish user guide

---

## References

- **Main Docs**: `README.md`, `CLAUDE.md`, `docs/STATUS.md`
- **Roadmap**: `docs/ROADMAP.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Troubleshooting**: `docs/guides/TROUBLESHOOTING.md`
- **Changelog**: `CHANGELOG.md`

---

## Notes for AI Assistants

### Current Context (2025-12-26)

**Active Work**: SF2 format validation fixes in progress
**Files Modified**: `sf2_header_generator.py`, `sf2_writer.py`, `sf2driver_laxity_00.prg`
**Issue**: SID Factory II editor rejection due to missing metadata fields
**Status**: 3 commits completed, additional changes uncommitted

### When Starting New Tasks

1. **Read this file first** - Understand current state
2. **Check git status** - See active changes
3. **Review recent commits** - Understand recent work
4. **Ask questions** - Clarify before proceeding

### Tool Usage Guidelines

- **Task(Explore)**: For open-ended codebase exploration
- **EnterPlanMode**: For non-trivial implementations
- **Read/Grep**: For specific files or patterns
- **TodoWrite**: Track multi-step tasks (use proactively)

### Testing Requirements

- **Always run**: `test-all.bat` before committing
- **Never commit**: If tests fail
- **Update docs**: When behavior changes

---

**Last Updated**: 2025-12-26
**Updated By**: Claude Sonnet 4.5
**Next Review**: After SF2 validation fixes complete

