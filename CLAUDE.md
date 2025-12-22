# CLAUDE.md - Project Quick Reference for AI Assistants

**Project**: SIDM2 - SID to SF2 Converter
**Version**: 2.5.3
**Last Updated**: 2025-12-22

---

## 30-Second Overview

Converts Commodore 64 SID music files (Laxity NewPlayer v21) to SID Factory II (.sf2) format for editing. Features custom Laxity driver with **99.93% frame accuracy**, comprehensive validation system, and professional GUI tools.

**Supported**:
- Input: Laxity NewPlayer v21 SID files
- Output: SID Factory II .sf2 format
- Drivers: Custom Laxity driver (99.93%), Driver 11, NP20

**Key Components**:
- SID→SF2 converter with table extraction
- SF2 Viewer GUI (PyQt6) with 8-tab interface
- Validation system with HTML dashboard
- Enhanced logging with verbosity control (v2.5.3)
- 164+ unit tests (100% pass rate)

---

## Critical Rules

### Rule 1: Keep Root Clean
**ALL Python scripts MUST be in `pyscript/` directory.** No .py files in root except launchers.
- ✅ Root: .bat launchers, .md docs, config files only
- ✅ pyscript/: ALL Python scripts
- ✅ experiments/: ALL experimental code
- ❌ Never create .py files in root

**Enforcement**: `cleanup.bat --scan` | **See**: `docs/guides/ROOT_FOLDER_RULES.md`

### Rule 2: Always Run Tests
Before committing: `test-all.bat` (164+ tests, 100% pass required)

### Rule 3: Always Update Documentation
When changing code: Update README.md, CLAUDE.md, docs/, and run `update-inventory.bat` after structural changes.

---

## Quick Commands (Top 10)

| Command | Description |
|---------|-------------|
| `sid-to-sf2.bat input.sid output.sf2` | Convert SID to SF2 |
| `sid-to-sf2.bat input.sid output.sf2 --driver laxity` | Convert with Laxity driver (99.93%) |
| `sf2-viewer.bat [file.sf2]` | Open SF2 Viewer GUI |
| `sf2-export.bat file.sf2` | Export SF2 to text |
| `batch-convert.bat` | Convert all SID files |
| `test-all.bat` | Run 164+ unit tests |
| `test-roundtrip.bat file.sid` | Test SID→SF2→SID roundtrip |
| `validate-accuracy.bat orig.sid conv.sid` | Validate frame accuracy |
| `cleanup.bat` | Clean temp files + update inventory |
| `TOOLS.bat` | Interactive menu launcher |

**Logging flags** (NEW v2.5.3): `-v/-vv` (verbose), `-q` (quiet), `--debug`, `--log-file`, `--log-json`

**Example**: `python scripts/sid_to_sf2.py input.sid output.sf2 --debug --log-file logs/debug.log`

---

## Project Structure (Simplified)

```
SIDM2/
├── pyscript/              # ALL Python scripts (v2.5)
│   ├── sf2_viewer_gui.py, sf2_to_text_exporter.py
│   ├── cleanup.py, new_experiment.py
│   └── *.py (all other Python scripts)
│
├── scripts/               # Production conversion tools
│   ├── sid_to_sf2.py, sf2_to_sid.py, convert_all.py
│   ├── test_*.py (164+ tests)
│   └── validate_sid_accuracy.py, run_validation.py
│
├── sidm2/                 # Core Python package
│   ├── sf2_packer.py, cpu6502_emulator.py
│   ├── laxity_parser.py, laxity_converter.py
│   └── logging_config.py (v2.0.0)
│
├── tools/                 # External tools
│   └── siddump.exe, SIDwinder.exe, SID2WAV.EXE, player-id.exe
│
├── G5/drivers/            # SF2 driver templates
│   └── sf2driver_laxity_00.prg (8192 bytes), sf2driver_11_*.prg
│
├── validation/            # Validation system (v1.4)
│   └── database.sqlite, dashboard.html, SUMMARY.md
│
├── docs/                  # Documentation
│   ├── guides/            # How-to guides
│   ├── reference/         # Technical references
│   ├── analysis/          # Analysis reports
│   └── implementation/    # Implementation docs
│
├── experiments/           # Temporary experiments (gitignored)
├── SID/                   # Input SID files
├── output/                # Output SF2/SID files
└── *.bat                  # Batch launchers (10 launchers)
```

**See**: `docs/FILE_INVENTORY.md` for complete listing

---

## Essential Constants

### Laxity Driver Memory
`SEQUENCE_ADDR=0x1900`, `INSTRUMENTS_ADDR=0x1A6B`, `WAVE_ADDR=0x1ACB`, `LAXITY_INIT=0x1000`, `LAXITY_PLAY=0x10A1`

### SF2 Driver 11 Offsets
`SEQUENCE_TABLE=0x0903`, `INSTRUMENT_TABLE=0x0A03`, `WAVE_TABLE=0x0B03`, `PULSE_TABLE=0x0D03`, `FILTER_TABLE=0x0F03`

### Control Bytes
`END_MARKER=0x7F`, `GATE_ON=0x7E` (+++ sustain), `GATE_OFF=0x80` (--- silence), `DEFAULT_TRANSPOSE=0xA0`, `LOOP_MARKER=0x7E`

**See**: `docs/ARCHITECTURE.md` for complete reference

---

## Known Limitations

### Format Compatibility
| Source → Driver | Accuracy | Status |
|----------------|----------|--------|
| SF2-Exported → Driver 11 | 100% | ✅ Perfect roundtrip |
| Laxity NP21 → Laxity Driver | 99.93% | ✅ Production ready |
| Laxity NP21 → Driver 11 | 1-8% | ⚠️ Use Laxity driver |

### Feature Limitations
- **Only Laxity NewPlayer v21** - Other formats not supported
- **Single subtune** - Multi-song SIDs not supported
- **Filter accuracy** - 0% (Laxity filter format not yet converted)

**See**: `docs/guides/TROUBLESHOOTING.md` for solutions

---

## Documentation Quick Reference

### Essential Docs (Start Here)
- **README.md** - Comprehensive project documentation
- **CLAUDE.md** - AI assistant quick reference (this file)
- **docs/guides/TROUBLESHOOTING.md** ⭐ - Start here for errors
- **docs/ARCHITECTURE.md** - Complete system architecture
- **CHANGELOG.md** - Version history

### User Guides (How-To)
- `docs/guides/SF2_VIEWER_GUIDE.md` - SF2 Viewer GUI, text exporter
- `docs/guides/LAXITY_DRIVER_USER_GUIDE.md` - Laxity driver (99.93% accuracy)
- `docs/guides/VALIDATION_GUIDE.md` - Validation system and dashboard
- `docs/guides/CLEANUP_SYSTEM.md` - Cleanup system and rules
- `docs/guides/LOGGING_AND_ERROR_HANDLING_GUIDE.md` - Enhanced logging (v2.5.3)

### Technical References (Deep Dive)
- `docs/COMPONENTS_REFERENCE.md` - Python modules API reference
- `docs/TOOLS_REFERENCE.md` - External tools documentation
- `docs/reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md` - Laxity technical details
- `docs/SF2_FORMAT_SPEC.md` - Complete SF2 format specification
- `docs/SID_REGISTERS_REFERENCE.md` - SID chip register reference

### Topic-Specific Help
| Topic | Primary Document |
|-------|------------------|
| Errors/Issues | `docs/guides/TROUBLESHOOTING.md` ⭐ |
| Logging/Errors | `docs/guides/LOGGING_AND_ERROR_HANDLING_GUIDE.md` |
| SF2 Format | `docs/SF2_FORMAT_SPEC.md`, `docs/SF2_TRACKS_AND_SEQUENCES.md` |
| Laxity Driver | `docs/guides/LAXITY_DRIVER_USER_GUIDE.md` (user), `docs/reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md` (technical) |

**Complete index**: `docs/INDEX.md`

---

## For AI Assistants

### When to Use Specialized Tools

**Task Tool (subagent_type=Explore)** - For open-ended exploration:
- "Where are errors handled?" / "How does the Laxity driver work?"
- Don't use for: "Read scripts/sid_to_sf2.py" (use Read), "Find class LaxityParser" (use Grep)

**EnterPlanMode** - For non-trivial implementations:
- New features (multiple files), architectural decisions, multiple approaches
- Don't use for: Typo fixes, single-line changes, specific instructions

### Testing & Documentation Requirements

**Before committing**:
1. ✅ Run `test-all.bat` (164+ tests, 100% pass required)
2. ✅ Update README.md if features/CLI changed
3. ✅ Update CLAUDE.md if structure/workflows changed
4. ✅ Update docs/ for APIs/architecture changes
5. ✅ Run `update-inventory.bat` after file structure changes

### Code Conventions
**Memory addresses**: `0x1000`, `0x1AF3` (hex) | **Table sizes**: 32, 64, 128 entries
**Control bytes**: `0x7F` (end), `0x7E` (gate on), `0x80` (gate off)

### Common Workflows

**Converting SID files**:
1. Check `info.txt` for warnings
2. Run validation to verify accuracy
3. Compare WAV files for audio differences
4. Compare siddump outputs for register differences

**Debugging packer issues**:
1. Check hexdumps for pointer relocation
2. Use SIDwinder disassembly (original vs exported)
3. See `PIPELINE_EXECUTION_REPORT.md` for known issues

**Exploring codebase**:
- Task tool (Explore) for broad searches
- Read tool for specific files
- Grep tool for patterns/classes
- EnterPlanMode for complex implementations

---

## Current Version

### v2.5.3 (2025-12-22) - Enhanced Logging & Error Handling

**Key Features**:
- ✅ Enhanced Logging System v2.0.0 (482 lines)
  - 4 verbosity levels, color-coded output, JSON logging
  - File rotation (10MB, 3 backups), performance metrics
- ✅ Script Integration (5 CLI flags: -v, -q, --debug, --log-file, --log-json)
- ✅ Backward compatible (default INFO level unchanged)

**Previous**: v2.3.1 - CLAUDE.md Optimization | **See**: `CHANGELOG.md` for complete history

---

**End of Quick Reference**

For complete documentation, see `README.md` and `docs/` directory.

**Version**: 2.5.3 | **Lines**: ~260 (compacted from 461) | **Last Updated**: 2025-12-22
