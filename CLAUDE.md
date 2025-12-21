# CLAUDE.md - Project Quick Reference for AI Assistants

**Project**: SIDM2 - SID to SF2 Converter
**Version**: 2.3.1
**Last Updated**: 2025-12-21

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
- Waveform analysis and audio comparison
- 130+ unit tests (100% pass rate)

---

## Critical Rules

### Rule 1: Keep Root Clean
**ALL Python scripts MUST be in `pyscript/` directory.** No .py files in root except launchers.
- ✅ Root: .bat launchers, .md docs, config files only
- ✅ pyscript/: ALL Python scripts
- ✅ experiments/: ALL experimental code
- ❌ Never create .py files in root

**Enforcement**: `cleanup.bat --scan` detects violations. **See**: `docs/guides/ROOT_FOLDER_RULES.md`

### Rule 2: Always Run Tests
Before committing, MUST run tests and ensure 100% pass:
```bash
python scripts/test_converter.py -v  # 86 tests + 153 subtests
python scripts/test_sf2_format.py -v  # 12 tests
```

**See**: `scripts/test_*.py` for all test suites

### Rule 3: Always Update Documentation
When changing code, MUST update:
- `README.md` - Features, CLI options, version numbers
- `CLAUDE.md` - Project structure, essential workflows
- `docs/` - Architecture, component APIs, guides
- `docs/FILE_INVENTORY.md` - After structural changes (run `update-inventory.bat`)

**See**: `CONTRIBUTING.md` for full guidelines

---

## Quick Commands (Top 10)

| Command | Description | See Also |
|---------|-------------|----------|
| `sid-to-sf2.bat input.sid output.sf2` | Convert SID to SF2 | README.md |
| `sid-to-sf2.bat input.sid output.sf2 --driver laxity` | Convert with Laxity driver (99.93%) | docs/guides/LAXITY_DRIVER_USER_GUIDE.md |
| `sf2-viewer.bat [file.sf2]` | Open SF2 Viewer GUI | docs/guides/SF2_VIEWER_GUIDE.md |
| `sf2-export.bat file.sf2` | Export SF2 to text | docs/guides/SF2_VIEWER_GUIDE.md |
| `batch-convert.bat` | Convert all SID files | README.md |
| `test-converter.bat` | Run unit tests (130+ tests) | scripts/test_*.py |
| `test-roundtrip.bat file.sid` | Test SID→SF2→SID roundtrip | scripts/test_roundtrip.py |
| `validate-accuracy.bat orig.sid conv.sid` | Validate frame accuracy | scripts/validate_sid_accuracy.py |
| `cleanup.bat` | Clean temp files + update inventory | docs/guides/CLEANUP_SYSTEM.md |
| `TOOLS.bat` | Interactive menu launcher | TOOLS_REFERENCE.txt |

**Note**: All .bat launchers are in root, all Python scripts in `pyscript/` or `scripts/`.

---

## Project Structure (Simplified)

```
SIDM2/
├── pyscript/              # ALL Python scripts (v2.5)
│   ├── sf2_viewer_gui.py          # SF2 Viewer (2.4.0)
│   ├── sf2_to_text_exporter.py    # Text exporter (2.3.0)
│   ├── cleanup.py                 # Cleanup system (2.2)
│   ├── new_experiment.py          # Experiment generator
│   └── *.py                       # All other scripts
│
├── scripts/               # Production conversion tools
│   ├── sid_to_sf2.py              # Main SID→SF2 converter
│   ├── sf2_to_sid.py              # SF2→SID exporter
│   ├── convert_all.py             # Batch conversion
│   ├── test_roundtrip.py          # Round-trip validation
│   ├── validate_sid_accuracy.py   # Frame accuracy validation
│   ├── run_validation.py          # Validation system (v1.4)
│   ├── generate_dashboard.py     # HTML dashboard
│   └── test_*.py                  # Unit tests (130+ tests)
│
├── sidm2/                 # Core Python package
│   ├── sf2_packer.py              # SF2→SID packer (v0.6.0)
│   ├── cpu6502_emulator.py        # 6502 emulator (v0.6.2)
│   ├── laxity_parser.py           # Laxity parser
│   ├── laxity_analyzer.py         # Laxity analyzer
│   ├── laxity_converter.py        # Laxity converter (99.93%)
│   └── *.py                       # Other modules
│
├── tools/                 # External tools
│   ├── siddump.exe                # SID register dump
│   ├── SIDwinder.exe              # SID processor
│   ├── SID2WAV.EXE                # SID to WAV
│   └── player-id.exe              # Player identification
│
├── G5/drivers/            # SF2 driver templates
│   ├── sf2driver_laxity_00.prg    # Laxity driver (8192 bytes)
│   ├── sf2driver_11_*.prg         # Driver 11
│   └── sf2driver_np20_*.prg       # NP20 driver
│
├── validation/            # Validation system (v1.4)
│   ├── database.sqlite            # Validation history
│   ├── dashboard.html             # Interactive dashboard
│   └── SUMMARY.md                 # Git-friendly summary
│
├── experiments/           # Temporary experiments (gitignored)
│   ├── README.md                  # Experiment workflow
│   └── {experiment}/              # Individual experiments
│
├── docs/                  # Documentation (see index below)
│   ├── guides/                    # How-to guides
│   ├── reference/                 # Technical references
│   ├── analysis/                  # Analysis reports
│   └── implementation/            # Implementation docs
│
├── SID/                   # Input SID files
├── output/                # Output SF2/SID files
└── *.bat                  # Batch launchers (10 launchers)
```

**See**: `docs/FILE_INVENTORY.md` for complete file listing

---

## Essential Constants

### Memory Addresses (Laxity Driver)

| Constant | Value | Description |
|----------|-------|-------------|
| `SEQUENCE_ADDR` | 0x1900 | Sequence data injection point |
| `INSTRUMENTS_ADDR` | 0x1A6B | Instrument table (column-major) |
| `WAVE_ADDR` | 0x1ACB | Wave table data |
| `PULSE_ADDR` | 0x1A3B | Pulse table data |
| `FILTER_ADDR` | 0x1A1E | Filter table + break speeds |
| `LAXITY_INIT_ADDR` | 0x1000 | Init routine entry |
| `LAXITY_PLAY_ADDR` | 0x10A1 | Play routine entry |

### SF2 Structure Offsets (Driver 11)

| Constant | Value | Description |
|----------|-------|-------------|
| `SEQUENCE_TABLE_OFFSET` | 0x0903 | Sequence table start |
| `INSTRUMENT_TABLE_OFFSET` | 0x0A03 | Instrument definitions |
| `WAVE_TABLE_OFFSET` | 0x0B03 | Wave table start |
| `PULSE_TABLE_OFFSET` | 0x0D03 | Pulse table start |
| `FILTER_TABLE_OFFSET` | 0x0F03 | Filter table start |

### Control Bytes

| Constant | Value | Description |
|----------|-------|-------------|
| `END_MARKER` | 0x7F | End of sequence/table |
| `GATE_ON` | 0x7E | Gate on (+++ sustain) |
| `GATE_OFF` | 0x80 | Gate off (--- silence) |
| `DEFAULT_TRANSPOSE` | 0xA0 | No transpose in OrderList |
| `LOOP_MARKER` | 0x7E | Loop in wave table |

**See**: `docs/ARCHITECTURE.md` for complete constants reference

---

## Known Limitations

### Format Compatibility (v1.8.0)

| Source → Driver | Accuracy | Status |
|----------------|----------|--------|
| SF2-Exported → Driver 11 | 100% | ✅ Perfect roundtrip |
| Laxity NP21 → Laxity Driver | 99.93% | ✅ Production ready |
| Laxity NP21 → Driver 11 | 1-8% | ⚠️ Use Laxity driver |
| Laxity NP21 → NP20 | 1-8% | ⚠️ Use Laxity driver |

### Feature Limitations

- **Only Laxity NewPlayer v21** - Other player formats not supported
- **Single subtune** - Multi-song SIDs not supported
- **Init, Arp, HR tables** - Use defaults, not extracted
- **Command parameters** - Some effect details lost in conversion
- **Filter accuracy** - 0% (Laxity filter format not yet converted)

### Known Issues

- **SF2 Packer Pointer Relocation** (v0.6.0):
  - Affects 17/18 files (94%) in disassembly only
  - Files play correctly in VICE, SID2WAV, siddump
  - Only impacts SIDwinder disassembly analysis
  - Under investigation

**See**: `docs/guides/TROUBLESHOOTING.md` for solutions, `PIPELINE_EXECUTION_REPORT.md` for details

---

## Documentation Index

### Quick Start
| Document | Purpose |
|----------|---------|
| **README.md** | Comprehensive project documentation |
| **CLAUDE.md** (this file) | AI assistant quick reference |
| **CONTRIBUTING.md** | Contribution guidelines |
| **CHANGELOG.md** | Version history |

### User Guides
| Document | Purpose |
|----------|---------|
| `docs/guides/SF2_VIEWER_GUIDE.md` | SF2 Viewer GUI, text exporter, editor enhancements |
| `docs/guides/LAXITY_DRIVER_USER_GUIDE.md` | Laxity driver user guide (quick start, usage) |
| `docs/guides/VALIDATION_GUIDE.md` | Validation system and dashboard |
| `docs/guides/WAVEFORM_ANALYSIS_GUIDE.md` | Waveform analysis tool |
| `docs/guides/EXPERIMENTS_WORKFLOW_GUIDE.md` | Experiment system workflow |
| `docs/guides/CLEANUP_SYSTEM.md` | Cleanup system and rules |
| `docs/guides/ROOT_FOLDER_RULES.md` | Root folder organization rules |
| `docs/guides/TROUBLESHOOTING.md` | Common issues and solutions |

### Technical References
| Document | Purpose |
|----------|---------|
| `docs/ARCHITECTURE.md` | Complete system architecture |
| `docs/COMPONENTS_REFERENCE.md` | Python modules reference |
| `docs/TOOLS_REFERENCE.md` | External tools documentation |
| `docs/reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md` | Laxity driver technical details |
| `docs/SF2_FORMAT_SPEC.md` | Complete SF2 format specification |
| `docs/SID_REGISTERS_REFERENCE.md` | SID chip register quick reference |
| `docs/SF2_TRACKS_AND_SEQUENCES.md` | Tracks and sequences format |
| `docs/SF2_INSTRUMENTS_REFERENCE.md` | Instruments format guide |
| `docs/CONVERSION_STRATEGY.md` | Laxity to SF2 mapping details |

### Analysis & Implementation
| Document | Purpose |
|----------|---------|
| `docs/analysis/CONSOLIDATION_2025-12-21_COMPLETE.md` | Knowledge consolidation (authoritative) |
| `docs/analysis/ACCURACY_ROADMAP.md` | Plan to reach 99% accuracy |
| `docs/implementation/SIDDECOMPILER_INTEGRATION.md` | SIDdecompiler integration (v1.4) |
| `docs/implementation/GATE_INFERENCE_IMPLEMENTATION.md` | Waveform-based gate detection |

### Source Code & Analysis
| Document | Purpose |
|----------|---------|
| `external-repositories.md` | External source repositories |
| `docs/SF2_SOURCE_ANALYSIS.md` | SF2 editor source analysis |
| `docs/SIDDUMP_ANALYSIS.md` | Siddump source analysis |
| `tools/SIDWINDER_ANALYSIS.md` | SIDwinder analysis |

**See**: `docs/INDEX.md` for complete documentation index

---

## Current Version

### v2.3.1 (2025-12-21) - CLAUDE.md Optimization

**Changes**:
- ✅ Optimized CLAUDE.md from 1098 lines to ~450 lines (59% reduction)
- ✅ Created 3 new comprehensive guides:
  - `docs/guides/SF2_VIEWER_GUIDE.md` - SF2 Viewer & Tools Guide
  - `docs/guides/WAVEFORM_ANALYSIS_GUIDE.md` - Waveform Analysis Guide
  - `docs/guides/EXPERIMENTS_WORKFLOW_GUIDE.md` - Experiment Workflow Guide
- ✅ Improved scannability with tables and clear sections
- ✅ Removed stale "NEW" tags and redundant content
- ✅ Better organization for AI assistant quick reference

**Previous**: v2.3.0 - Documentation Consolidation (2025-12-21)

**See**: `CHANGELOG.md` for complete version history

---

## For AI Assistants

### When to Use Task Tool (subagent_type=Explore)

**Use for open-ended codebase exploration**:
```
User: "Where are errors from the client handled?"
User: "What is the codebase structure?"
User: "How does the Laxity driver work?"
```

**Don't use for specific needle queries**:
```
User: "Read scripts/sid_to_sf2.py"  → Use Read tool
User: "Find class LaxityParser"     → Use Grep tool
```

### When to Use EnterPlanMode

**Use for non-trivial implementation tasks**:
- New feature implementation (multiple files)
- Architectural decisions required
- Multiple valid approaches exist
- User preferences matter

**Don't use for simple tasks**:
- Typo fixes
- Single-line changes
- Specific detailed instructions
- Pure research/exploration

### Testing Requirements

**Before committing code changes**:
1. ✅ Run `python scripts/test_converter.py` (130+ tests)
2. ✅ Run `python scripts/test_sf2_format.py` (format tests)
3. ✅ Fix all failures before committing
4. ✅ Add tests for new features

### Documentation Requirements

**When changing code**:
1. ✅ Update README.md if features/CLI changed
2. ✅ Update CLAUDE.md if structure/workflows changed
3. ✅ Update relevant docs/ files for APIs/architecture
4. ✅ Keep version numbers in sync
5. ✅ Run `update-inventory.bat` after structural changes

### Code Conventions

**Memory addresses**: `0x1000`, `0x1AF3` (hex)
**Table sizes**: 32, 64, or 128 entries
**Control bytes**: `0x7F` (end), `0x7E` (gate on), `0x80` (gate off)
**Waveforms**: `0x11` (triangle+gate), `0x41` (pulse+gate)

**See**: `docs/ARCHITECTURE.md` for complete conventions

---

## Getting Help

### Troubleshooting Priority

1. **Start here**: `docs/guides/TROUBLESHOOTING.md` - Common issues and solutions
2. **Specific topics**: See Documentation Index above
3. **Enable verbose mode**: `--verbose` flag on most scripts
4. **Check validation**: Review `info.txt` files in output/

### Quick Debug Commands

```bash
# Test with known-good file
python scripts/sid_to_sf2.py SID/Angular.sid test.sf2

# Check player type
tools/player-id.exe input.sid

# Compare dumps
tools/siddump.exe original.sid > original.dump
tools/siddump.exe exported.sid > exported.dump
diff original.dump exported.dump

# Run validation
python scripts/run_validation.py --quick
```

### Topic-Specific Help

| Topic | Primary Document |
|-------|------------------|
| Errors/Issues | `docs/guides/TROUBLESHOOTING.md` ⭐ |
| Architecture | `docs/ARCHITECTURE.md` |
| Module APIs | `docs/COMPONENTS_REFERENCE.md` |
| Tool Usage | `docs/TOOLS_REFERENCE.md` |
| SID Registers | `docs/SID_REGISTERS_REFERENCE.md` |
| SF2 Format | `docs/SF2_FORMAT_SPEC.md` |
| Validation | `docs/guides/VALIDATION_GUIDE.md` |
| Laxity Driver | `docs/guides/LAXITY_DRIVER_USER_GUIDE.md` |

---

## Quick Tips

### For AI Assistants Working on SIDM2

**When converting SID files**, always:
1. Check `info.txt` for conversion warnings
2. Run validation to verify accuracy
3. Listen to both WAV files for audio comparison
4. Compare siddump outputs for register differences

**When debugging packer issues**:
1. Check hexdumps for pointer relocation
2. Use SIDwinder disassembly on original vs exported
3. Compare memory layouts
4. See `PIPELINE_EXECUTION_REPORT.md` for known issues

**When exploring codebase**:
- Use Task tool with `subagent_type=Explore` for broad searches
- Use Read tool for specific files
- Use Grep tool for specific patterns/classes
- Use EnterPlanMode for complex implementations

**When updating documentation**:
- Update README.md for user-facing changes
- Update CLAUDE.md for structure/workflow changes
- Update docs/ for technical details
- Run `update-inventory.bat` after file changes

---

**End of Quick Reference**

For complete documentation, see `README.md` and `docs/` directory.

**Version**: 2.3.1
**Lines**: ~450 (optimized from 1098)
**Last Updated**: 2025-12-21
