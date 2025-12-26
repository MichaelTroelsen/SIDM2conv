# CLAUDE.md - AI Assistant Quick Reference

**Project**: SIDM2 - SID to SF2 Converter | **Version**: 2.9.6 | **Updated**: 2025-12-26

---

## 30-Second Overview

Converts C64 SID files (Laxity NewPlayer v21) to SID Factory II (.sf2) format. Custom Laxity driver achieves **99.93% frame accuracy**. Includes SF2 Viewer GUI, Conversion Cockpit GUI, **SID Inventory System** (658+ files cataloged), **Python siddump** (100% complete), **Python SIDwinder** (100% complete), **Batch Testing** (100% validated), **Complete User Documentation** (3,400+ lines), **CI/CD System** (5 workflows), validation system, and 200+ passing tests.

**Key**: 🎯 **Auto-Select Driver (v2.8.0)** | 📋 **SID Inventory (v2.9.0)** | ✅ **SF2 Format Fixed (v2.9.1)** | 🤖 **PyAutoGUI (v2.9.4)** | 🧪 **Batch Testing (v2.9.5)** | 📚 **User Docs (v2.9.6)** | 🔄 **CI/CD (v2.9.6)** | Laxity → 99.93% | SF2 → 100%

---

## Critical Rules

1. **Keep Root Clean**: ALL .py files in `pyscript/` only. No .py in root.
2. **Run Tests**: `test-all.bat` (164+ tests) before committing
3. **Update Docs**: Update README.md, CLAUDE.md, docs/ when changing code

**Enforcement**: `cleanup.bat --scan` | **See**: `docs/guides/ROOT_FOLDER_RULES.md`

---

## Quick Commands

```bash
# Convert (AUTOMATIC driver selection - NEW v2.8.0 🎯)
sid-to-sf2.bat input.sid output.sf2
# → Auto-selects: Laxity (99.93%), SF2 (100%), Others (safe default)
# → Generates: output.sf2 + output.txt (driver documentation)
# → Validates: SF2 format automatically

# Manual override (expert use)
sid-to-sf2.bat input.sid output.sf2 --driver laxity

# View/Export SF2
sf2-viewer.bat [file.sf2]              # GUI viewer
sf2-export.bat file.sf2                # Text export

# Batch Operations
batch-convert-laxity.bat               # All Laxity files
test-all.bat                           # All 200+ tests
cleanup.bat                            # Clean + update inventory

# Conversion Cockpit
conversion-cockpit.bat                 # Mission control GUI

# Batch Testing (v2.9.5)
test-batch-pyautogui.bat               # Test multiple SF2 files
test-batch-pyautogui.bat --directory G5/examples --max-files 10
test-batch-pyautogui.bat --playback 5 --stability 3
python pyscript/test_batch_pyautogui.py --directory output

# Python siddump (v2.6.0)
python pyscript/siddump_complete.py input.sid -t30  # Frame analysis
python pyscript/test_siddump.py -v                  # Run 38 unit tests

# Python SIDwinder (v2.8.0)
python pyscript/sidwinder_trace.py --trace output.txt --frames 1500 input.sid
sidwinder-trace.bat -trace=output.txt -frames=1500 input.sid  # Batch launcher

# SID Inventory System (v2.9.0)
create-sid-inventory.bat                # Generate complete SID catalog (658+ files)
python pyscript/create_sid_inventory.py # Cross-platform inventory generator

# Pattern Analysis Tools (v2.9.0)
python pyscript/check_entry_patterns.py      # Validate pattern matches
python pyscript/find_undetected_laxity.py    # Find missed Laxity files
python pyscript/identify_undetected.py       # Analyze unknown files
python pyscript/quick_disasm.py file.sid     # Quick 6502 disassembly

# VSID Integration (v2.9.6) - Audio Export
install-vice.bat                             # Install VICE emulator (includes VSID)
python pyscript/install_vice.py              # Cross-platform VICE installer
test-vsid-integration.bat                    # Test VSID integration (100% pass rate)

# Video Creation (NEW)
setup-video-assets.bat                       # Create all video assets (audio + screenshots)
install-ffmpeg.bat                           # Install ffmpeg for audio conversion
cd video-demo/sidm2-demo && npm start        # Preview video
cd video-demo/sidm2-demo && npx remotion render SIDM2Demo out/sidm2-demo-enhanced.mp4  # Render final video

# SF2 Editor Automation (v2.9.4)
python -c "from sidm2.sf2_editor_automation import SF2EditorAutomation; a = SF2EditorAutomation(); a.launch_editor_with_file('file.sf2')"
```

**Logging** (v2.5.3): `-v/-vv` (verbose), `-q` (quiet), `--debug`, `--log-file`, `--log-json`

---

## Automatic Driver Selection (v2.8.0) 🎯

**Quality-First Policy v2.0**: Auto-selects best driver based on source SID player type.

**Driver Matrix**:

| Source Player | Driver | Accuracy | Reason |
|--------------|--------|----------|--------|
| **Laxity NP21** | Laxity | **99.93%** ✅ | Custom optimized |
| **SF2-exported** | Driver 11 | **100%** ✅ | Perfect roundtrip |
| **NewPlayer 20.G4** | NP20 | **70-90%** ✅ | Format-specific |
| **Rob Hubbard/Martin Galway/Unknown** | Driver 11 | Safe default | Standard |

**Workflow**: Identify player → Select driver → Display selection → Convert → Validate → Generate info file

**Output**: `output.sf2` (validated) + `output.txt` (driver selection, accuracy, validation)

**Benefits**: ✅ Max quality | ✅ Automatic | ✅ Documented | ✅ Validated | ✅ Flexible override

**See**: `CONVERSION_POLICY_APPROVED.md`

---

## Python Tools

### Python siddump (v2.6.0) ✅
Pure Python replacement for siddump.exe. **100% musical content match**, cross-platform, zero dependencies.

```bash
python pyscript/siddump_complete.py music.sid -t30   # 30 seconds
python pyscript/siddump_complete.py music.sid -t30 -p # + profiling
```

**Features**: All 11 CLI flags, 38 unit tests (100% pass), auto-used by sidm2/siddump.py
**Docs**: `docs/implementation/SIDDUMP_PYTHON_IMPLEMENTATION.md`

### Python SIDwinder (v2.8.0) ✅
Pure Python SIDwinder.exe trace replacement. **100% format compatible**, cross-platform.

```bash
python pyscript/sidwinder_trace.py --trace output.txt --frames 1500 input.sid
sidwinder-trace.bat -trace=output.txt -frames=1500 input.sid  # Batch
```

**Features**: Frame-aggregated tracing, 17 unit tests + 10 real-world files (100% pass), ~0.1s per 100 frames
**Docs**: `docs/analysis/SIDWINDER_PYTHON_DESIGN.md`

### VSID Integration (v2.9.6) ✅
**100% automated** SID→WAV conversion using **VSID (VICE emulator)** for better accuracy. Automatic fallback to SID2WAV.

```python
from sidm2.vsid_wrapper import VSIDIntegration

# Direct VSID export
result = VSIDIntegration.export_to_wav(
    sid_file=Path("input.sid"),
    output_file=Path("output.wav"),
    duration=30,
    verbose=1
)

# Automatic VSID/SID2WAV selection (preferred)
from sidm2.audio_export_wrapper import AudioExportIntegration

result = AudioExportIntegration.export_to_wav(
    sid_file=Path("input.sid"),
    output_file=Path("output.wav"),
    duration=30  # Auto-uses VSID if available
)
print(f"Tool used: {result['tool']}")  # 'vsid' or 'sid2wav'
```

**Features**: Cross-platform, VICE-quality emulation, automatic tool selection, 100% backward compatible
**Benefits**: Better accuracy, active maintenance, open source
**Status**: ✅ Production ready (3/3 tests + 120 core tests passing)
**Docs**: `docs/VSID_INTEGRATION_GUIDE.md`

### SF2 Editor Automation (v2.9.4) 🤖
**100% automated** SF2 file loading and validation using **PyAutoGUI** as the default mode.

```python
from sidm2.sf2_editor_automation import SF2EditorAutomation

# Automatic PyAutoGUI mode (DEFAULT - zero configuration)
automation = SF2EditorAutomation()
success = automation.launch_editor_with_file("file.sf2")

if success:
    automation.pyautogui_automation.start_playback()  # F5
    time.sleep(5)
    automation.pyautogui_automation.stop_playback()   # F6
    automation.pyautogui_automation.close_editor()

# Explicit mode selection
automation.launch_editor_with_file("file.sf2", mode='pyautogui')  # Recommended
automation.launch_editor_with_file("file.sf2", mode='manual')     # User loads file
automation.launch_editor_with_file("file.sf2", mode='autoit')     # Legacy (not recommended)
```

**Features**: 100% automated file loading, zero configuration, indefinite window stability, automatic mode fallback
**Modes**: PyAutoGUI (default) > Manual > AutoIt (automatic priority)
**Status**: ✅ Production ready (all tests passing)
**Docs**: `PYAUTOGUI_INTEGRATION_COMPLETE.md`

---

## Project Structure

```
SIDM2/
├── pyscript/           # ALL Python scripts (v2.6)
│   ├── siddump_complete.py, sidwinder_trace.py  # Python tools
│   ├── conversion_cockpit_gui.py, sf2_viewer_gui.py
│   └── test_*.py                    # 200+ unit tests
├── scripts/            # Production tools
│   ├── sid_to_sf2.py               # Main converter
│   ├── sf2_to_sid.py, validate_sid_accuracy.py
├── sidm2/              # Core package
│   ├── laxity_parser.py, laxity_converter.py, sf2_packer.py
│   ├── driver_selector.py (v2.8.0), siddump.py, logging_config.py
├── tools/              # External tools (optional fallback)
├── G5/drivers/         # SF2 drivers (laxity, driver11, np20)
├── docs/               # Documentation
└── *.bat               # Launchers
```

**Complete**: `docs/FILE_INVENTORY.md`

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

### User Guides (NEW v2.9.6) 📚
**Complete Documentation Suite** - 3,400+ lines for all skill levels:
- **`docs/guides/GETTING_STARTED.md`** ⭐ - 5-minute quick start (beginner)
- **`docs/guides/TUTORIALS.md`** ⭐ - 9 step-by-step tutorials (all levels)
- **`docs/guides/FAQ.md`** ⭐ - 30+ Q&A pairs (quick answers)
- **`docs/guides/BEST_PRACTICES.md`** ⭐ - Expert optimization (advanced)

**Specialized Guides**:
- `docs/guides/SF2_VIEWER_GUIDE.md` - SF2 Viewer + text exporter
- `docs/guides/CONVERSION_COCKPIT_USER_GUIDE.md` - Batch conversion GUI
- `docs/guides/LAXITY_DRIVER_USER_GUIDE.md` - Laxity driver guide
- `docs/guides/VALIDATION_GUIDE.md` - Validation system
- `docs/guides/LOGGING_AND_ERROR_HANDLING_GUIDE.md` - Logging (v2.5.3)
- `docs/guides/TROUBLESHOOTING.md` - Error solutions
- `PYAUTOGUI_INTEGRATION_COMPLETE.md` - PyAutoGUI automation (v2.9.4)

### Technical Refs
- `docs/ARCHITECTURE.md` - System architecture
- `docs/COMPONENTS_REFERENCE.md` - Python API
- `docs/SF2_FORMAT_SPEC.md` - SF2 format
- `docs/reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md` - Laxity internals

### Quick Help
| Need | Document |
|------|----------|
| **Get started** | `docs/guides/GETTING_STARTED.md` ⭐ |
| **Learn workflows** | `docs/guides/TUTORIALS.md` ⭐ |
| **Quick answers** | `docs/guides/FAQ.md` ⭐ |
| **Optimize** | `docs/guides/BEST_PRACTICES.md` ⭐ |
| Error fix | `docs/guides/TROUBLESHOOTING.md` |
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

1. Run `test-all.bat` (200+ tests must pass)
2. Update README.md if features changed
3. Update CLAUDE.md if structure changed
4. Update docs/ if API changed
5. Run `update-inventory.bat` if files added/removed

### Common Workflows

**Convert & Validate**:
```bash
python scripts/sid_to_sf2.py input.sid output.sf2  # Auto-selects driver
python scripts/validate_sid_accuracy.py input.sid output.sid
```

**Debug Conversion**:
1. Check `output.txt` info file for driver selection and validation
2. Compare dumps: `python pyscript/siddump_complete.py original.sid -t30` vs `exported.sid`
3. Compare audio: `original.wav` vs `exported.wav`

**Explore Codebase**:
- Use Task(Explore) for broad questions
- Use Read for specific files
- Use Grep for finding patterns

---

## Version History

### v2.9.6 (2025-12-26) - CI/CD + User Documentation ✅
- **Complete User Documentation** (3,400+ lines: Getting Started, Tutorials, FAQ, Best Practices)
- **CI/CD System** (5 GitHub Actions workflows, automated testing on every push)
- **Workflow Modernization** (Updated ci.yml and test.yml for current project structure)
- **VSID Integration** (Replaces SID2WAV with VICE VSID player for cross-platform audio)
- **Documentation Status** (All guides production-ready, README updated with navigation)
- **Batch Testing Workflow** (Automated validation in GitHub Actions)

### v2.9.5 (2025-12-26) - Batch Testing & Critical Process Fix ✅
- **Batch Testing System** (100% success rate, 10/10 files validated)
- **Critical Process Fix** (Editor processes now terminate properly, 0 lingering)
- **100% Pass Rate** (Improved from 90% to 100% with process cleanup)
- **Automated Validation** (test-batch-pyautogui.bat with detailed reporting)

### v2.9.4 (2025-12-26) - PyAutoGUI Automation ✅
- **PyAutoGUI Integration** (100% automated SF2 file loading, production ready)
- **CLI --skip-intro Flag** (SID Factory II source code modification)
- **Default Automation Mode** (PyAutoGUI > Manual > AutoIt automatic priority)
- **Zero Configuration** (Works immediately, automatic fallback)
- **100% Test Pass Rate** (All integration tests passing)

### v2.9.1 (2025-12-26) - SF2 Format Validation Fixes ✅
- **SF2 Metadata Fixes** (Critical editor compatibility - SID Factory II acceptance)
- **Missing Descriptor Fields** (Commands table, visible_rows field added)
- **Enhanced Validation** (Comprehensive SF2 structure logging and validation)
- **Production Ready** (Generated SF2 files now load correctly in editor)

### v2.9.0 (2025-12-24) - SID Inventory System + Pattern Database ✅
- **SID Inventory System** (Complete catalog of 658+ SID files)
- **Pattern Database** (Validated player type identification, 658 files analyzed)
- **Pattern Analysis Tools** (5 new scripts for pattern research)
- **Policy Documentation** (Organized in docs/integration/)

### v2.8.0 (2025-12-22) - Automatic Driver Selection + Python SIDwinder ✅
- **Automatic Driver Selection** (Quality-First Policy v2.0)
- **Python SIDwinder** (100% complete, cross-platform trace functionality)
- **Driver documentation** (info files for every conversion)
- **SF2 format validation** (automatic after every conversion)

### v2.6.0 (2025-12-22) - Python siddump Complete ✅
- **Python siddump** (595 lines, 100% musical content accuracy)
- **38 unit tests** (100% pass rate)
- **Cross-platform** (Mac/Linux/Windows)

### v2.5.3 (2025-12-22) - Enhanced Logging
- Enhanced Logging System v2.0.0 (4 levels, JSON, rotation)
- CLI flags: `-v`, `-vv`, `-q`, `--debug`, `--log-file`, `--log-json`

### Recent Versions
- **v2.5.0** - Conversion Cockpit GUI
- **v2.3.0** - Documentation consolidation
- **v2.2.0** - SF2 Viewer single-track support
- **v2.0.0** - 8 optional analysis tools (SIDwinder Tracer, 6502 Disassembler, Audio Export, Memory Map, Pattern Recognizer, Subroutine Tracer, Report Generator, Output Organizer)
- **v1.8.0** - Laxity driver (99.93% accuracy)

**Complete history**: `CHANGELOG.md`

---

**End of Quick Reference**

**Lines**: ~270 (compacted from 445) | **For full docs**: See README.md and docs/
