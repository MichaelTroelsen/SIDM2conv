# CLAUDE.md - AI Assistant Quick Reference

**Project**: SIDM2 - SID to SF2 Converter | **Version**: 2.5.3 | **Updated**: 2025-12-22

---

## 30-Second Overview

Converts C64 SID files (Laxity NewPlayer v21) to SID Factory II (.sf2) format. Custom Laxity driver achieves **99.93% frame accuracy**. Includes SF2 Viewer GUI, Conversion Cockpit GUI, validation system, and 164+ passing tests.

**Key**: Laxity NP21 → Laxity Driver (99.93%) | SF2-Exported → Driver 11 (100%)

---

## Critical Rules

1. **Keep Root Clean**: ALL .py files in `pyscript/` only. No .py in root.
2. **Run Tests**: `test-all.bat` (164+ tests) before committing
3. **Update Docs**: Update README.md, CLAUDE.md, docs/ when changing code

**Enforcement**: `cleanup.bat --scan` | **See**: `docs/guides/ROOT_FOLDER_RULES.md`

---

## Quick Commands

```bash
# Convert (99.93% accuracy)
sid-to-sf2.bat input.sid output.sf2 --driver laxity

# View/Export SF2
sf2-viewer.bat [file.sf2]              # GUI viewer
sf2-export.bat file.sf2                # Text export

# Batch Operations
batch-convert-laxity.bat               # All Laxity files
test-all.bat                           # All 164+ tests
cleanup.bat                            # Clean + update inventory

# Conversion Cockpit
conversion-cockpit.bat                 # Mission control GUI
```

**Logging** (v2.5.3): `-v/-vv` (verbose), `-q` (quiet), `--debug`, `--log-file`, `--log-json`

---

## Project Structure

```
SIDM2/
├── pyscript/           # ALL Python scripts (v2.5)
│   ├── conversion_cockpit_gui.py    # Batch conversion GUI
│   ├── sf2_viewer_gui.py            # SF2 viewer GUI
│   ├── sf2_to_text_exporter.py      # Text exporter
│   └── test_*.py                    # 164+ unit tests
│
├── scripts/            # Production tools
│   ├── sid_to_sf2.py               # Main converter
│   ├── sf2_to_sid.py               # SF2 packer
│   └── validate_sid_accuracy.py    # Validator
│
├── sidm2/              # Core package
│   ├── laxity_parser.py, laxity_converter.py
│   ├── sf2_packer.py, cpu6502_emulator.py
│   └── logging_config.py (v2.0.0)
│
├── tools/              # External tools
│   └── siddump.exe, SIDwinder.exe, SID2WAV.EXE
│
├── G5/drivers/         # SF2 drivers
│   └── sf2driver_laxity_00.prg (8KB, 99.93%)
│
├── docs/               # Documentation
│   ├── guides/         # User guides
│   ├── reference/      # Technical docs
│   └── ARCHITECTURE.md # System design
│
└── *.bat               # Launchers (10 files)
```

**Complete listing**: `docs/FILE_INVENTORY.md`

---

## Essential Constants

**Laxity**: `INIT=0x1000`, `PLAY=0x10A1`, `INSTRUMENTS=0x1A6B`, `WAVE=0x1ACB`
**SF2 Driver 11**: `SEQ=0x0903`, `INST=0x0A03`, `WAVE=0x0B03`, `PULSE=0x0D03`, `FILTER=0x0F03`
**Control**: `END=0x7F`, `GATE_ON=0x7E`, `GATE_OFF=0x80`, `TRANSPOSE=0xA0`

**Full reference**: `docs/ARCHITECTURE.md`

---

## Known Limitations

| Source → Driver | Accuracy | Status |
|----------------|----------|--------|
| SF2 → Driver 11 | 100% | ✅ Perfect |
| Laxity → Laxity | 99.93% | ✅ Production |
| Laxity → Driver 11 | 1-8% | ⚠️ Use Laxity driver |

**Other**: Only Laxity NP21 supported, single subtune only, 0% filter accuracy

---

## Documentation Index

### Start Here
- **README.md** - Complete project docs
- **docs/guides/TROUBLESHOOTING.md** ⭐ - Error solutions
- **CLAUDE.md** - This file

### User Guides
- `docs/guides/SF2_VIEWER_GUIDE.md` - SF2 Viewer + text exporter
- `docs/guides/CONVERSION_COCKPIT_USER_GUIDE.md` - Batch conversion GUI
- `docs/guides/LAXITY_DRIVER_USER_GUIDE.md` - Laxity driver guide
- `docs/guides/VALIDATION_GUIDE.md` - Validation system
- `docs/guides/LOGGING_AND_ERROR_HANDLING_GUIDE.md` - Logging (v2.5.3)

### Technical Refs
- `docs/ARCHITECTURE.md` - System architecture
- `docs/COMPONENTS_REFERENCE.md` - Python API
- `docs/SF2_FORMAT_SPEC.md` - SF2 format
- `docs/reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md` - Laxity internals

### Quick Help
| Need | Document |
|------|----------|
| Error fix | `docs/guides/TROUBLESHOOTING.md` ⭐ |
| Logging | `docs/guides/LOGGING_AND_ERROR_HANDLING_GUIDE.md` |
| SF2 format | `docs/SF2_FORMAT_SPEC.md` |
| Laxity driver | `docs/guides/LAXITY_DRIVER_USER_GUIDE.md` |

**Complete index**: `docs/INDEX.md`

---

## For AI Assistants

### Tool Usage

**Task Tool (Explore)**: Open-ended searches ("How does X work?", "Where is Y handled?")
**EnterPlanMode**: Non-trivial implementations (multiple files, architecture decisions)
**Read/Grep**: Specific files or patterns

### Before Committing

1. Run `test-all.bat` (164+ tests must pass)
2. Update README.md if features changed
3. Update CLAUDE.md if structure changed
4. Update docs/ if API changed
5. Run `update-inventory.bat` if files added/removed

### Common Workflows

**Convert & Validate**:
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
python scripts/validate_sid_accuracy.py input.sid output.sid
```

**Debug Conversion**:
1. Check `output/*/New/info.txt` for warnings
2. Compare dumps: `tools/siddump.exe original.sid` vs `exported.sid`
3. Compare audio: `original.wav` vs `exported.wav`

**Explore Codebase**:
- Use Task(Explore) for broad questions
- Use Read for specific files
- Use Grep for finding patterns

---

## Version History

### v2.5.3 (2025-12-22) - Enhanced Logging
- Enhanced Logging System v2.0.0 (4 levels, JSON, rotation)
- CLI flags: `-v`, `-vv`, `-q`, `--debug`, `--log-file`, `--log-json`
- Backward compatible

### Recent Versions
- **v2.5.0** - Conversion Cockpit GUI (mission control for batch conversion)
- **v2.3.0** - Documentation consolidation
- **v2.2.0** - SF2 Viewer single-track support
- **v2.0.0** - SF2 Viewer GUI released
- **v1.8.0** - Laxity driver (99.93% accuracy)

**Complete history**: `CHANGELOG.md`

---

**End of Quick Reference**

**Lines**: ~170 (compacted from 260) | **For full docs**: See README.md and docs/
