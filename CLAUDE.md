# CLAUDE.md - AI Assistant Quick Reference

**Project**: SIDM2 - SID to SF2 Converter | **Version**: 2.8.0 | **Updated**: 2025-12-22

---

## 30-Second Overview

Converts C64 SID files (Laxity NewPlayer v21) to SID Factory II (.sf2) format. Custom Laxity driver achieves **99.93% frame accuracy**. Includes SF2 Viewer GUI, Conversion Cockpit GUI, **Python siddump** (100% complete), validation system, and 200+ passing tests.

**Key**: Laxity NP21 → Laxity Driver (99.93%) | SF2-Exported → Driver 11 (100%) | **Pure Python Pipeline**

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
test-all.bat                           # All 200+ tests
cleanup.bat                            # Clean + update inventory

# Conversion Cockpit
conversion-cockpit.bat                 # Mission control GUI

# Python siddump (v2.6.0)
python pyscript/siddump_complete.py input.sid -t30  # Frame analysis
python pyscript/test_siddump.py -v                  # Run 38 unit tests

# Python SIDwinder (NEW v2.8.0)
python pyscript/sidwinder_trace.py --trace output.txt --frames 1500 input.sid
sidwinder-trace.bat -trace=output.txt -frames=1500 input.sid  # Batch launcher
```

**Logging** (v2.5.3): `-v/-vv` (verbose), `-q` (quiet), `--debug`, `--log-file`, `--log-json`

---

## Python siddump (v2.6.0) 🎉

**Status**: ✅ **Production Ready** | **Accuracy**: 100% musical content match

Pure Python replacement for siddump.exe with zero external dependencies.

### Quick Start

```bash
# Basic usage (60 seconds default)
python pyscript/siddump_complete.py music.sid

# Custom time (30 seconds)
python pyscript/siddump_complete.py music.sid -t30

# Profiling mode (show CPU cycles)
python pyscript/siddump_complete.py music.sid -t30 -p

# Time format (mm:ss.ff)
python pyscript/siddump_complete.py music.sid -t30 -z

# Start from frame 100
python pyscript/siddump_complete.py music.sid -t30 -f100
```

### Features

- ✅ **100% musical content match** vs C version (frequencies, notes, waveforms, ADSR, pulse)
- ✅ **All 11 CLI flags** supported (-a, -c, -d, -f, -l, -n, -o, -p, -s, -t, -z)
- ✅ **Cross-platform** (Mac/Linux/Windows)
- ✅ **38 unit tests** (100% pass rate)
- ✅ **Integrated** (used by sidm2/siddump.py wrapper by default)
- ⚠️ **2.8x slower** than C (acceptable - 30s dump in 4.2s)

### Integration

Python version is used **automatically** by default:

```python
from sidm2.siddump import extract_from_siddump

# Uses Python siddump automatically
result = extract_from_siddump('music.sid', playback_time=30)

# Force C exe (if needed)
result = extract_from_siddump('music.sid', playback_time=30, use_python=False)
```

### Documentation

- **Implementation**: `docs/implementation/SIDDUMP_PYTHON_IMPLEMENTATION.md`
- **Unit Tests**: `pyscript/test_siddump.py` (38 tests)
- **Analysis**: `docs/analysis/EXTERNAL_TOOLS_REPLACEMENT_ANALYSIS.md`

---

## Python SIDwinder (v2.8.0) 🎉

**Status**: ✅ **Production Ready** | **Accuracy**: 100% format compatible | **Platform**: Cross-platform

Pure Python replacement for SIDwinder.exe trace functionality with zero external dependencies.

### Quick Start

```bash
# Basic usage (1500 frames = 30 seconds @ 50Hz)
python pyscript/sidwinder_trace.py --trace output.txt --frames 1500 input.sid

# Batch launcher
sidwinder-trace.bat -trace=output.txt -frames=1500 input.sid

# Quick test (100 frames)
python pyscript/sidwinder_trace.py --trace test.txt --frames 100 input.sid

# Verbose mode
python pyscript/sidwinder_trace.py --trace output.txt --frames 1500 input.sid -v
```

### Features

- ✅ **100% SIDwinder-compatible output format** (FRAME: D40X:$YY,...)
- ✅ **Frame-aggregated tracing** (1 line per frame, efficient for validation)
- ✅ **Cross-platform** (Windows, Mac, Linux - no Wine needed)
- ✅ **Leverages CPU6502Emulator** (1,242 lines reused, proven code)
- ✅ **Python-first with .exe fallback** (automatic graceful degradation)
- ✅ **High performance** (~0.1 seconds per 100 frames)
- ✅ **Comprehensive testing** (17 unit tests + 10 real-world files, 100% pass)

### API Usage

```python
# Use wrapper (Python-first with .exe fallback)
from sidm2.sidwinder_wrapper import trace_sid
from pathlib import Path

result = trace_sid(
    sid_file=Path("input.sid"),
    output_file=Path("output.txt"),
    frames=1500,
    use_python=True  # Default
)

# Returns: {'success': True, 'method': 'python', 'writes': 2475, 'frames': 1500, ...}

# Direct Python usage (no fallback)
from pyscript.sidtracer import SIDTracer
from pyscript.trace_formatter import TraceFormatter

tracer = SIDTracer(Path("input.sid"), verbose=1)
trace_data = tracer.trace(frames=1500)
TraceFormatter.write_trace_file(trace_data, Path("output.txt"))
```

### Real-World Validation

**10/10 Laxity SID files** tested successfully:
- Total: 18,322 SID writes captured
- Output: 173,914 bytes generated
- Success rate: 100% (zero failures)
- Performance: Avg 0.1s per 100 frames

### Documentation

- **Design**: `docs/analysis/SIDWINDER_PYTHON_DESIGN.md`
- **Unit Tests**: `pyscript/test_sidwinder_trace.py` (17 tests)
- **Real-World Tests**: `pyscript/test_sidwinder_realworld.py` (10 files)
- **Analysis**: `docs/analysis/EXTERNAL_TOOLS_REPLACEMENT_ANALYSIS.md`

---

## Project Structure

```
SIDM2/
├── pyscript/           # ALL Python scripts (v2.6)
│   ├── siddump_complete.py          # Python siddump (595 lines, NEW v2.6.0)
│   ├── conversion_cockpit_gui.py    # Batch conversion GUI
│   ├── sf2_viewer_gui.py            # SF2 viewer GUI
│   ├── sf2_to_text_exporter.py      # Text exporter
│   └── test_*.py                    # 200+ unit tests (38 for siddump)
│
├── scripts/            # Production tools
│   ├── sid_to_sf2.py               # Main converter
│   ├── sf2_to_sid.py               # SF2 packer
│   └── validate_sid_accuracy.py    # Validator
│
├── sidm2/              # Core package
│   ├── laxity_parser.py, laxity_converter.py
│   ├── sf2_packer.py, cpu6502_emulator.py
│   ├── siddump.py (uses Python version, v2.6.0)
│   └── logging_config.py (v2.0.0)
│
├── tools/              # External tools (optional)
│   └── siddump.exe (fallback), SIDwinder.exe, SID2WAV.EXE
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

1. Run `test-all.bat` (200+ tests must pass)
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
2. Compare dumps: `python pyscript/siddump_complete.py original.sid -t30` vs `exported.sid`
3. Compare audio: `original.wav` vs `exported.wav`
4. Use C siddump for exact filter matching (if needed): `tools/siddump.exe original.sid -t30`

**Explore Codebase**:
- Use Task(Explore) for broad questions
- Use Read for specific files
- Use Grep for finding patterns

---

## Version History

### v2.6.0 (2025-12-22) - Python siddump Complete ✅
- **Python siddump implementation** (595 lines, 100% complete)
- **38 unit tests** (100% pass rate)
- **100% musical content accuracy** vs C version
- **Wrapper integration** (sidm2/siddump.py uses Python by default)
- **Cross-platform** (Mac/Linux/Windows)
- **Zero external dependencies** (pure Python)
- Production ready with automatic fallback to C exe

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
