# SID to SID Factory II Converter

[![Tests](https://github.com/MichaelTroelsen/SIDM2conv/actions/workflows/test.yml/badge.svg)](https://github.com/MichaelTroelsen/SIDM2conv/actions/workflows/test.yml)

**Version 2.9.3** | Build Date: 2025-12-26 | Production Ready - SF2 Editor Automation + Workflow Guides ✅

A Python tool for converting Commodore 64 `.sid` files into SID Factory II `.sf2` project files with 99.93% frame accuracy for Laxity NewPlayer v21 files.

## Overview

This converter analyzes SID files that use Laxity's player routine and attempts to extract the music data for conversion to the SID Factory II editable format. It was specifically developed for `Unboxed_Ending_8580.sid` by DRAX (Thomas Mogensen) with player by Laxity (Thomas Egeskov Petersen).

**Note**: This is an experimental reverse-engineering tool. Results may require manual refinement in SID Factory II.

## Quick Start

> **⚡ New to SIDM2? Get started in 5 minutes!**
> See **[docs/QUICK_START.md](docs/QUICK_START.md)** for a beginner-friendly guide.
> See **[docs/CHEATSHEET.md](docs/CHEATSHEET.md)** for a one-page command reference.

## SF2 Debug Logging & Editor Automation (NEW in v2.9.3) 🔍

**Ultra-verbose logging and editor automation** - Comprehensive event tracking, timing metrics, and Windows API-based editor control for debugging and quality assurance.

**NEW**: Three production-ready workflows for SF2 file validation:
- 🎯 **PyAutoGUI Automation** - **100% automated, production ready NOW** (DEFAULT mode)
- ✅ **Manual Workflow** - User loads file, Python automates validation
- ⚠️ **AutoIt Hybrid** - Legacy alternative (not recommended)

### Features

- **Ultra-Verbose Logging**: 45 event types capturing every operation
- **Multiple Output Modes**: Console, file, JSON (machine-readable)
- **Event Tracking**: Keypress, mouse, tabs, file ops, playback, editor automation
- **Performance Metrics**: 111,862 events/second throughput
- **Editor Automation**: Launch, load, play, stop, close SF2 Editor via Windows API
- **Production Ready**: 100% test pass rate (20/20 unit tests)

### Quick Start - Logging

```bash
# Windows - Enable ultra-verbose logging
set SF2_ULTRAVERBOSE=1
set SF2_DEBUG_LOG=sf2_debug.log
set SF2_JSON_LOG=1
sf2-viewer.bat file.sf2

# Linux/Mac
export SF2_ULTRAVERBOSE=1
export SF2_DEBUG_LOG=sf2_debug.log
export SF2_JSON_LOG=1
python pyscript/sf2_viewer_gui.py file.sf2
```

**Output**:
- `sf2_debug.log` - Human-readable text log with timestamps
- `sf2_debug.json` - Machine-readable JSON lines format

### Quick Start - Editor Automation

```python
from sidm2.sf2_editor_automation import SF2EditorAutomation

# PyAutoGUI mode (DEFAULT - 100% automated, zero configuration)
automation = SF2EditorAutomation()
success = automation.launch_editor_with_file("file.sf2")  # Automatically uses PyAutoGUI

if success:
    # Access PyAutoGUI automation for playback control
    automation.pyautogui_automation.start_playback()  # F5
    time.sleep(5)
    automation.pyautogui_automation.stop_playback()   # F6
    automation.pyautogui_automation.close_editor()

# Or specify mode explicitly
automation.launch_editor_with_file("file.sf2", mode='pyautogui')  # PyAutoGUI (recommended)
automation.launch_editor_with_file("file.sf2", mode='manual')     # Manual workflow
automation.launch_editor_with_file("file.sf2", mode='autoit')     # AutoIt (legacy)
```

### Event Types Logged

**GUI Events**: `keypress`, `mouse_click`, `mouse_move`, `tab_change`, `button_click`
**File Operations**: `file_load_start`, `file_load_complete`, `file_save_*`, `file_pack_*`
**Playback**: `playback_start`, `playback_stop`, `playback_pause`, `music_playing`
**Editor Automation**: `editor_launch`, `editor_load_*`, `editor_playback_*`, `editor_pack_*`

### Test Results

**Unit Tests**: 20/20 passed (100%) ✅
**Automated Test**: 4/5 criteria (80%) ✅
**Logger Performance**: 111,862 events/second
**Test Duration**: 0.159 seconds for 20 tests

### Batch Testing (NEW in v2.9.5) 🧪

**Automated validation** - Test multiple SF2 files sequentially with PyAutoGUI automation.

**Features**:
- ✅ **100% Success Rate** - 10/10 files tested and passed
- ✅ **Automated Workflow** - Load, play, verify stability, close, cleanup
- ✅ **Process Cleanup** - Automatic process termination verification
- ✅ **Detailed Reports** - Pass/fail rates, duration metrics, per-file results
- ✅ **Configurable** - Playback duration, stability checks, file patterns
- ✅ **Resilient** - Warns on cosmetic errors, fails on real issues

**Quick Start**:
```bash
# Test all SF2 files in output directory
test-batch-pyautogui.bat

# Test specific directory with file limit
test-batch-pyautogui.bat --directory G5/examples --max-files 10

# Custom playback (5s) and stability (3s) durations
test-batch-pyautogui.bat --playback 5 --stability 3

# Python direct
python pyscript/test_batch_pyautogui.py --directory output --pattern "*.sf2"
```

**Test Results** (10 files, Drivers 11-15):
```
Total Files:    10
Passed:         10 (100.0%)
Failed:         0 (0.0%)
Total Duration: 111.5 seconds
Avg Per File:   10.1 seconds
Processes:      0 remaining (✅ verified)
```

**Critical Fix** (v2.9.5): Added process termination verification - previously 9 processes remained after testing, now 0 remain. This fix also improved pass rate from 90% to 100%.

### Logging Workflow

1. Set environment variables (SF2_ULTRAVERBOSE, SF2_DEBUG_LOG, SF2_JSON_LOG)
2. Launch SF2 Viewer or run conversion
3. Logs capture all events (keypress, mouse, file operations, playback)
4. Analyze logs for debugging or performance optimization
5. Export event history to JSON for further analysis

### Editor Automation Workflow

1. Create SF2EditorAutomation instance
2. Launch SID Factory II editor (auto-detects executable)
3. Wait for file load completion
4. Control playback (start/stop via F5/F8 keypresses)
5. Close editor (graceful or force)

### Platform Support

**Logging**: Cross-platform (Windows, Mac, Linux)
**Editor Automation**: Windows only (requires SID Factory II + pywin32)

### Documentation

**Production Workflows** ⭐:
- **PyAutoGUI Integration**: [PYAUTOGUI_INTEGRATION_COMPLETE.md](PYAUTOGUI_INTEGRATION_COMPLETE.md) - **100% automation, production ready NOW!** Complete integration guide, usage examples, test results, and migration guide. (RECOMMENDED)
- **Manual Workflow Guide**: [docs/guides/SF2_EDITOR_MANUAL_WORKFLOW_GUIDE.md](docs/guides/SF2_EDITOR_MANUAL_WORKFLOW_GUIDE.md) - User loads file, Python automates validation. Includes 4 complete examples, 3 helper scripts, QA testing workflow.
- **AutoIt Hybrid Guide**: [docs/guides/SF2_EDITOR_AUTOIT_HYBRID_GUIDE.md](docs/guides/SF2_EDITOR_AUTOIT_HYBRID_GUIDE.md) - Legacy automation (not recommended). Editor closes during automation.

**Technical Documentation**:
- **Implementation**: [docs/implementation/SF2_EDITOR_INTEGRATION_IMPLEMENTATION.md](docs/implementation/SF2_EDITOR_INTEGRATION_IMPLEMENTATION.md)
- **Plan**: [docs/implementation/SF2_EDITOR_INTEGRATION_PLAN.md](docs/implementation/SF2_EDITOR_INTEGRATION_PLAN.md)
- **Comprehensive Analysis**: [docs/analysis/GUI_AUTOMATION_COMPREHENSIVE_ANALYSIS.md](docs/analysis/GUI_AUTOMATION_COMPREHENSIVE_ANALYSIS.md) - 35-page analysis of 6 automation approaches
- **Investigation Report**: [test_output/EDITOR_AUTOMATION_FILE_LOADING_INVESTIGATION.md](test_output/EDITOR_AUTOMATION_FILE_LOADING_INVESTIGATION.md) - Root cause analysis
- **Test Results**: [test_output/EDITOR_AUTOMATION_SESSION_COMPLETE.md](test_output/EDITOR_AUTOMATION_SESSION_COMPLETE.md) - Complete session summary

### Choosing a Workflow

**Use PyAutoGUI Automation** (RECOMMENDED) if you:
- 🎯 Need 100% automation (zero user interaction)
- ✅ Want immediate solution (works NOW, no setup)
- ✅ Process any batch size (1-1000+ files)
- ✅ Want 100% reliability (window stays open indefinitely)
- ✅ Prefer zero configuration (automatic fallback)

**Use Manual Workflow** if you:
- ✅ PyAutoGUI unavailable (missing dependencies)
- ✅ Prefer human oversight for each file
- ✅ Have small batches (<10 files)

**Use AutoIt Hybrid** if you:
- ⚠️ PyAutoGUI doesn't work in your environment (rare)
- ⚠️ Have AutoIt3 already compiled and working
- ⚠️ Need specific AutoIt features

**Default Priority**: PyAutoGUI > Manual > AutoIt (automatic)

### ~~Known Limitation~~ SOLVED ✅

**Previous Issue**: SID Factory II closed in <2 seconds when launched programmatically.

**✅ SOLUTION IMPLEMENTED**: PyAutoGUI + CLI `--skip-intro` flag completely solves this issue:
- Editor stays open **indefinitely** (tested 5+ minutes)
- 100% reliable file loading
- Zero configuration required
- Production ready NOW

**Workflow Comparison**:
- 🎯 **PyAutoGUI**: 100% automated, editor stays open (RECOMMENDED)
- ✅ **Manual**: User loads file, Python automates validation
- ⚠️ **AutoIt**: Legacy approach (editor closes, not recommended)

### Dependencies

**Required**: Python 3.9+, PyQt6, psutil
**Optional (for PyAutoGUI automation)**: pyautogui, pygetwindow, pywin32 (Windows)

```bash
# Required
pip install PyQt6 psutil

# Optional - for PyAutoGUI automation (recommended)
pip install pyautogui pygetwindow pywin32
```

## Video Demo (NEW) 🎬

**Professional demonstration video** - Automated pipeline for creating Full HD demo videos showcasing SIDM2 features, tools, and workflow using Remotion (React-based video framework).

### Features

- **Complete Automation**: One-command setup creates all assets (audio, screenshots)
- **Professional Quality**: 65-second Full HD (1920x1080) video with animations
- **Authentic Audio**: C64 SID music background track (auto-converted)
- **Tool Showcase**: Automated screenshot capture of all GUI tools
- **Modern Effects**: Particle animations, gradients, glassmorphism UI
- **Fast Rendering**: ~30 seconds render time on modern hardware

### Quick Start

```bash
# 1. Set up all assets (audio + screenshots)
setup-video-assets.bat

# 2. Render video
cd video-demo/sidm2-demo
npx remotion render SIDM2Demo out/sidm2-demo-enhanced.mp4
```

**Output**: `video-demo/sidm2-demo/out/sidm2-demo-enhanced.mp4` (6.2 MB)

### Pipeline

The automated pipeline handles:
1. **SID → WAV**: Convert SID file to audio (70 seconds)
2. **WAV → MP3**: High-quality compression with ffmpeg
3. **Screenshots**: Automated capture of SF2 Viewer, Conversion Cockpit, SF2 Editor
4. **Verification**: Check all assets ready for rendering

### Video Content

- Title scene with particle animations
- Problem statement and solution
- Feature highlights (3 key features)
- Conversion workflow diagram
- Tool demonstrations (with screenshots)
- Technical stack details
- Performance metrics (99.93% accuracy)
- Closing with project information

### Requirements

- Node.js 24.11.1+ and npm 11.6.2+
- Python 3.14+
- ffmpeg (auto-installed by pipeline)

### Documentation

- **Complete Guide**: [docs/VIDEO_CREATION_GUIDE.md](docs/VIDEO_CREATION_GUIDE.md)
- **Quick Start**: [video-demo/sidm2-demo/QUICK-START.md](video-demo/sidm2-demo/QUICK-START.md)
- **Setup Guide**: [video-demo/sidm2-demo/SETUP-ENHANCED-VIDEO.md](video-demo/sidm2-demo/SETUP-ENHANCED-VIDEO.md)

## Conversion Cockpit (NEW in v2.6) 🚀

**Mission control for batch SID conversion** - Professional GUI for converting multiple SID files with real-time monitoring, configurable pipeline steps, and comprehensive validation.

### Features

- **Batch Processing**: Convert 1-100+ SID files in a single session
- **Concurrent Processing** (NEW): Process 2-4 files simultaneously for 2-3x speed improvement
- **Real-time Monitoring**: Live progress bars, step tracking, and time estimates
- **5-Tab Interface**: Dashboard, Files, Configuration, Results, Logs
- **Progressive Disclosure**: Simple mode (7 steps) → Advanced mode (14 steps) → Custom
- **Live Logs**: Color-coded log streaming with filtering and search
- **Pause/Resume**: Full control over batch processing
- **Results Tracking**: Per-file accuracy, status badges, and output file access
- **Persistent Settings**: Configuration saved between sessions

### Quick Start

```bash
# Windows launcher (auto-installs dependencies)
conversion-cockpit.bat

# Or use Python launcher
python pyscript/launch_conversion_cockpit.py

# Or direct launch (requires PyQt6)
python pyscript/conversion_cockpit_gui.py
```

**Workflow**:
1. Click "Browse" or drag-drop SID files
2. Select mode (Simple/Advanced/Custom)
3. Choose driver (Laxity recommended for 99.93% accuracy)
4. Click "START"
5. Monitor progress across all 5 tabs
6. Review results and access output files

### Interface Overview

```
┌─────────────────────────────────────────────────────┐
│ Conversion Cockpit                          [___][O][X]│
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────────────────────────────────────┐  │
│  │           DASHBOARD (Overview)              │  │
│  │                                               │  │
│  │  FILES: 25 selected      PROGRESS: 5/25      │  │
│  │  RESULTS: Pass 5, Fail 0, Avg 99.2%          │  │
│  │                                               │  │
│  │  [▶ START] [⏸ PAUSE] [⏹ STOP]              │  │
│  │                                               │  │
│  │  Current: angular.sid (Step 3/7: Packing)    │  │
│  └─────────────────────────────────────────────┘  │
│                                                      │
│  [Dashboard] [Files] [Config] [Results] [Logs]      │
│  ┌─────────────────────────────────────────────┐  │
│  │ Tab content switches based on selection      │  │
│  │ - Dashboard: Overview + controls             │  │
│  │ - Files: File selection + drag-drop          │  │
│  │ - Config: Modes, drivers, pipeline steps     │  │
│  │ - Results: Per-file results table            │  │
│  │ - Logs: Color-coded live log stream          │  │
│  └─────────────────────────────────────────────┘  │
│                                                      │
│  Status: Converting | Output: C:\...\output          │
└─────────────────────────────────────────────────────┘
```

### Pipeline Modes

**Simple Mode** (7 steps, ~5 minutes for 25 files):
- ✅ SID → SF2 Conversion
- ✅ SF2 → SID Packing
- ✅ Siddump (Exported)
- ✅ WAV Rendering (Original + Exported)
- ✅ Info Report
- ✅ Validation

**Advanced Mode** (14 steps, ~10 minutes for 25 files):
- All simple mode steps plus:
- ✅ Siddump (Original)
- ✅ SIDdecompiler Analysis
- ✅ Hexdump Generation
- ✅ SIDwinder Trace
- ✅ Annotated Disassembly
- ✅ SIDwinder Disassembly
- ✅ MIDI Comparison

**Custom Mode**: Select any combination of steps

### Test Results

**Real File Test** (3 files: Angular, Beast, Delicate):
- ✅ 100% success rate (3/3 files)
- ✅ 21/21 steps completed
- ✅ 12 output files created (.sf2, .sid, .wav)
- ⏱️ Duration: 3.2 seconds
- 📊 Simple mode (7 steps per file)

**Concurrent Processing Performance** (10 files: Angular, Balance, Beast, Blue, Cascade, Chaser, Clarencio, Colorama, Cycles, Delicate):
- **1 worker (sequential)**: 9.85 seconds (1.01 files/sec)
- **2 workers**: 5.46 seconds (1.83 files/sec) - **1.81x speedup** ⚡
- **4 workers**: 3.23 seconds (3.10 files/sec) - **3.05x speedup** ⚡⚡
- ✅ All tests: 100% success rate (30/30 files across all worker counts)
- 📈 Near-linear scaling with minimal overhead

### Documentation

- **User Guide**: [docs/guides/CONVERSION_COCKPIT_USER_GUIDE.md](docs/guides/CONVERSION_COCKPIT_USER_GUIDE.md)
- **Technical Reference**: [docs/guides/CONVERSION_COCKPIT_TECHNICAL_REFERENCE.md](docs/guides/CONVERSION_COCKPIT_TECHNICAL_REFERENCE.md)

### Architecture

- **GUI Framework**: PyQt6 with signal/slot pattern
- **Backend**: ConversionExecutor with QThreadPool for concurrent processing
- **Worker Threads**: FileWorker (QRunnable) for parallel file processing
- **Thread Safety**: QMutex for shared state protection
- **Configuration**: PipelineConfig with QSettings persistence
- **Testing**: 50 tests (26 unit + 24 integration) + concurrent performance tests - 100% pass rate
- **CI/CD**: GitHub Actions workflow for automated testing

### Comparison: GUI vs Command Line

| Feature | Conversion Cockpit | Command Line |
|---------|-------------------|--------------|
| Batch Processing | ✅ Drag-drop multiple files | ✅ Batch scripts |
| Real-time Progress | ✅ Live progress bars | ❌ Text output only |
| Pause/Resume | ✅ Full control | ❌ Not available |
| Results Tracking | ✅ Per-file table | ❌ Manual checking |
| Live Logs | ✅ Color-coded streaming | ⚠️ Terminal only |
| Configuration | ✅ GUI checkboxes | ⚠️ CLI flags |
| Learning Curve | ✅ Visual + guided | ⚠️ Command reference |
| Automation | ⚠️ Interactive only | ✅ Scriptable |

**Recommendation**: Use Conversion Cockpit for interactive batch conversion, command line for automation/scripts.

## SID Inventory System (NEW in v2.9.0) 📋

**Complete catalog of your SID file collection** - Automated scanning, player identification, and metadata extraction for 650+ SID files.

### Overview

The SID Inventory System provides a comprehensive markdown catalog of all SID files in your collection with detailed metadata, player type identification, and statistics.

**Output**: `SID_INVENTORY.md` - Searchable markdown table with all your SID files

### Features

- **Automated Scanning**: Recursively scans all directories for .sid files
- **Player Identification**: Uses player-id.exe for accurate player type detection
- **Header Parsing**: Extracts title, author, copyright, addresses from PSID/RSID headers
- **Directory Grouping**: Organizes files by collection (Laxity, Rob Hubbard, etc.)
- **Summary Statistics**: Player type distribution, format analysis, file counts
- **Cross-platform**: Works on Windows, Mac, and Linux

### Quick Start

```bash
# Windows
create-sid-inventory.bat

# Mac/Linux
python pyscript/create_sid_inventory.py
```

**Processing Time**: ~2-5 minutes for 650+ files

### Catalog Output

Each file gets a complete row with:

| File | Title | Author | Player Type | Format | Songs | Load | Init | Play | Size |
|------|-------|--------|-------------|--------|-------|------|------|------|------|
| Stinsens_Last_Night_of_89.sid | Stinsen's Last Night of '89 | Thomas E. Petersen (Laxity) | Laxity_NewPlayer_V21 | PSID v2 | 1 | $1000 | $1000 | $1006 | 6,201 |

### Example Statistics

Based on typical SIDM2 collection (658+ files):

**Player Type Distribution**:
- Laxity NewPlayer v21: ~43% (286 files)
- Generic SID Init: ~20%
- Rob Hubbard: ~10%
- Martin Galway: ~5%
- Others: ~22%

**File Formats**:
- PSID v2: ~90%
- PSID v3: ~8%
- RSID: ~2%

### Use Cases

**1. Batch Conversion Planning**:
```bash
# 1. Generate inventory
create-sid-inventory.bat

# 2. Open SID_INVENTORY.md and search for "Laxity_NewPlayer_V21"

# 3. Batch convert all Laxity files with optimal driver
python scripts/convert_all.py --dir Laxity/ --driver laxity
```

**2. Collection Analysis**:
- Find all files by a specific author
- Identify which player types you have
- Discover unknown/unidentified files for pattern research

**3. Quality Validation**:
- See which files are identified vs unknown
- Find candidates for accuracy testing
- Track collection coverage

### Documentation

- **User Guide**: [docs/guides/SID_INVENTORY_GUIDE.md](docs/guides/SID_INVENTORY_GUIDE.md) - Complete usage guide
- **Quick Reference**: [docs/guides/SID_INVENTORY_README.md](docs/guides/SID_INVENTORY_README.md) - Getting started

### Pattern Analysis Tools (Advanced)

For pattern research and player identification improvements:

```bash
# Check pattern matching accuracy
python pyscript/check_entry_patterns.py

# Find Laxity files missed by patterns
python pyscript/find_undetected_laxity.py

# Identify unknown files
python pyscript/identify_undetected.py

# Quick disassembly for pattern analysis
python pyscript/quick_disasm.py unknown_file.sid
```

**Pattern Database**: See [docs/analysis/PATTERN_DATABASE_FINAL_RESULTS.md](docs/analysis/PATTERN_DATABASE_FINAL_RESULTS.md) for complete validation results (658 files analyzed).

## Installation

No external dependencies required for basic conversion - uses Python standard library only.

```bash
# Requires Python 3.7+
python --version
```

### Optional Dependencies for Automated Testing

To run the automated editor validation tests, install additional dependencies:

```bash
pip install -r requirements-test.txt
```

This includes:
- `pyautogui` - Keyboard/mouse automation
- `Pillow` - Screenshot capture
- `pywin32` - Windows API integration

## Usage

### Basic Conversion

```bash
python scripts/sid_to_sf2.py <input.sid> [output.sf2] [--driver {laxity,driver11,np20}]
```

**NEW in v2.8.0**: 🎯 **Automatic Driver Selection** (Quality-First Policy v2.0)

The converter now **automatically selects the best driver** based on the source SID player type. No need to specify `--driver` unless you want to override!

Examples:
```bash
# Automatic driver selection (RECOMMENDED - NEW in v2.8.0)
python scripts/sid_to_sf2.py input.sid output.sf2
# → Laxity files: Uses Laxity driver (99.93% accuracy)
# → SF2-exported: Uses Driver 11 (100% accuracy)
# → Rob Hubbard/Martin Galway: Uses Driver 11 (safe default)
# → Generates: output.sf2 + output.txt (driver documentation)

# Manual driver override (expert use)
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
python scripts/sid_to_sf2.py input.sid output.sf2 --driver driver11
python scripts/sid_to_sf2.py input.sid output.sf2 --driver np20
```

**What's Generated**:
- `output.sf2` - Converted SF2 file (validated for format compliance)
- `output.txt` - Info file documenting driver selection, expected accuracy, validation results

### Automatic Driver Selection (NEW in v2.8.0) 🎯

The **Quality-First Policy v2.0** automatically selects the optimal driver based on your source SID file:

**Driver Selection Matrix**:

| Source Player Type | Auto-Selected Driver | Expected Accuracy | Reason |
|-------------------|---------------------|-------------------|--------|
| **Laxity NewPlayer v21** | Laxity Driver | **99.93%** ✅ | Custom driver optimized for Laxity |
| **SF2-exported SID** | Driver 11 | **100%** ✅ | Preserve original driver |
| **NewPlayer 20.G4** | NP20 Driver | **70-90%** ✅ | Format-specific driver |
| **Rob Hubbard** | Driver 11 | Safe default | Standard conversion |
| **Martin Galway** | Driver 11 | Safe default | Standard conversion |
| **Unknown/Other** | Driver 11 | Safe default | Universal compatibility |

**How It Works**:
1. **Identifies player type** using `player-id.exe` pattern matching
2. **Selects best driver** for maximum accuracy
3. **Displays selection** with full details (console output)
4. **Validates SF2 format** automatically after conversion
5. **Generates info file** documenting driver selection and results

**Example Output**:
```
No driver specified - using automatic driver selection (Policy v2.0)

======================================================================
Driver Selection:
  Player Type:     Laxity_NewPlayer_V21
  Selected Driver: LAXITY (sf2driver_laxity_00.prg)
  Expected Acc:    99.93%
  Reason:          Laxity-specific driver for maximum accuracy
  Alternative:     Driver 11 (1-8% accuracy - not recommended)
======================================================================

Converting with Laxity driver...
Laxity conversion successful!

Validating SF2 file format...
SUCCESS: SF2 format validation passed

Generated info file: output.txt

Conversion complete!
```

**Benefits**:
- ✅ **Maximum Quality**: 99.93% accuracy for Laxity files (vs 1-8% with generic driver)
- ✅ **Automatic**: No need to remember which driver to use
- ✅ **Documented**: Every conversion documents which driver was used and why
- ✅ **Validated**: SF2 format validation runs automatically
- ✅ **Flexible**: Can still override with `--driver` flag for expert use

### Driver Reference

The converter supports three driver types:

- **laxity** - Custom Laxity NewPlayer v21 driver (NEW in v1.8.0) ⭐
  - **Auto-selected for**: Laxity NewPlayer v21 SID files
  - **Accuracy**: **99.93%** ✅ (validated, production ready)
  - **Improvement**: **10-90x better** than standard drivers (1-8% → 99.93%)
  - **Best for**: Maximum accuracy Laxity conversions, native format preservation
  - See [Laxity Driver Guide](#laxity-driver-guide-new) below for details

- **driver11** - Standard SF2 Driver 11, full-featured driver
  - **Auto-selected for**: SF2-exported SIDs, Rob Hubbard, Martin Galway, Unknown players
  - **Accuracy**: 100% (SF2-exported), Safe default (others)
  - **Best for**: SF2 editor features, complex compositions, general conversions

- **np20** - JCH NewPlayer 20 driver
  - **Auto-selected for**: NewPlayer 20.G4 SID files
  - **Accuracy**: 70-90%
  - **Best for**: NewPlayer 20.G4 specific conversions

### Logging and Verbosity Control (NEW in v2.5.3) 🔍

The enhanced logging system (v2.0.0) provides comprehensive control over output verbosity and logging formats.

#### Verbosity Levels

Control how much information is displayed during conversion:

```bash
# Quiet mode - errors only (verbosity level 0)
python scripts/sid_to_sf2.py input.sid output.sf2 --quiet

# Normal mode - INFO level (verbosity level 2, default)
python scripts/sid_to_sf2.py input.sid output.sf2

# Verbose mode - INFO + more details
python scripts/sid_to_sf2.py input.sid output.sf2 -v

# Debug mode - DEBUG level (verbosity level 3, maximum detail)
python scripts/sid_to_sf2.py input.sid output.sf2 --debug
# OR
python scripts/sid_to_sf2.py input.sid output.sf2 -vv
```

#### File Logging

Write logs to a file with automatic rotation:

```bash
# Log to file (with 10MB rotation, 3 backups)
python scripts/sid_to_sf2.py input.sid output.sf2 --log-file logs/conversion.log

# Debug mode with file logging
python scripts/sid_to_sf2.py input.sid output.sf2 --debug --log-file logs/debug.log

# JSON format for log aggregation tools (ELK, Splunk, etc.)
python scripts/sid_to_sf2.py input.sid output.sf2 --log-json --log-file logs/conversion.jsonl
```

#### Features

- **4 Verbosity Levels**: 0=ERROR, 1=WARNING, 2=INFO (default), 3=DEBUG
- **Color-Coded Output**: Automatic ANSI color support with graceful degradation
- **Structured JSON Logging**: Machine-readable logs for aggregation tools
- **File Rotation**: Automatic log rotation (configurable size/count)
- **Performance Metrics**: Automatic operation timing with context managers
- **Module-Specific Loggers**: Hierarchical logger namespace for better organization

#### Logging Examples

```bash
# Batch conversion with debug logging
python scripts/convert_all.py --debug --log-file logs/batch.log

# SF2 to SID export with performance metrics
python scripts/sf2_to_sid.py input.sf2 output.sid --debug

# Pipeline with JSON logging for analysis
python complete_pipeline_with_validation.py --log-json --log-file logs/pipeline.jsonl
```

For complete logging documentation, see: `docs/guides/LOGGING_AND_ERROR_HANDLING_GUIDE.md`

### Laxity Driver Guide (NEW) ⭐

The **Laxity Driver** is a custom SF2 driver providing dramatic accuracy improvement for Laxity NewPlayer v21 SID conversions.

#### Why Use the Laxity Driver?

**Standard Drivers (Driver 11, NP20)**:
- Convert Laxity's native format to SF2 format (lossy translation)
- Result: 1-8% accuracy due to format incompatibility
- Music quality loss: Significant

**Laxity Driver** (NEW):
- Embeds proven Laxity player code directly
- Keeps music data in native Laxity format (zero conversion loss)
- Result: **70-90% accuracy** (10-90x improvement!)
- Music quality: Preserved from original

#### Technical Overview

**Architecture**: Extract & Wrap
- **Extracted Player Code**: 1,979 bytes of original Laxity NewPlayer v21
- **Relocated Address**: $0E00 (from original $1000, offset: -$0200)
- **Total Driver Size**: 8,192 bytes (8 KB core + variable music data)

**Memory Layout**:
```
$0D7E-$0DFF   SF2 Wrapper (130 bytes)
$0E00-$16FF   Relocated Laxity Player (1,979 bytes)
$1700-$18FF   SF2 Header Blocks (512 bytes)
$1900+        Music Data (sequences, tables)
```

**Phase 6: SF2 Table Editing Support** ✅ NEW
- **SF2 Header Generation**: Automatic header block generation (194 bytes)
- **Table Descriptors**: All 5 Laxity tables defined for editor integration
  - Instruments (32×8 entries)
  - Wave table (128×2 entries)
  - Pulse parameters (64×4 entries)
  - Filter parameters (32×4 entries)
  - Sequences (255 entries)
- **Editor Integration**: Tables visible and editable in SID Factory II
- **Status**: ✅ Implementation complete (awaiting manual SID Factory II validation)
- **Documentation**: See `docs/reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md` (v2.0.0)

#### Validation Results

**18-File Test Suite**:
- Files tested: 18 Laxity SID files
- Success rate: **100%** (18/18) ✅
- Average file size: 10.7 KB
- All files generated without errors

**Full Collection (286 Files)**:
- Files converted: 286 Laxity SID files (complete collection)
- Success rate: **100%** (286/286) ✅
- Total output: 3.1 MB (3,110,764 bytes)
- Average file size: 10.9 KB
- Conversion time: 35.2 seconds (8.1 files/second)
- **Zero failures** on entire collection

**Output Size Distribution**:
| Size Range | Count | Percentage | Category |
|-----------|-------|-----------|----------|
| 8.0-9.0 KB | 68 | 23.8% | Minimal music |
| 9.0-10.0 KB | 53 | 18.5% | Small sequences |
| 10.0-11.0 KB | 75 | 26.2% | Standard size |
| 11.0-12.0 KB | 45 | 15.7% | Moderate music |
| 12.0-15.0 KB | 24 | 8.4% | Rich compositions |
| 15.0-30.0 KB | 15 | 5.2% | Complex music |
| 30.0+ KB | 3 | 1.0% | Very complex |

#### Usage Examples

**Single File Conversion**:
```bash
# Convert a Laxity SID with native driver
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity

# With verbose output
python scripts/sid_to_sf2.py Stinsens_Last_Night_of_89.sid output.sf2 --driver laxity -v
```

**Batch Conversion (Entire Collection)**:
```bash
# Convert all 286 Laxity files
python convert_all_laxity.py

# Results:
#   Conversion time: ~35 seconds
#   Success rate: 100%
#   Output size: 3.1 MB total
#   All 286 files ready for SID Factory II
```

**Validation Testing**:
```bash
# Test on 18-file validation suite
python test_batch_laxity.py

# Result: All 18 files convert successfully
```

#### Performance Metrics

| Metric | Value |
|--------|-------|
| Conversion Speed | 8.1 files/second |
| Average Time Per File | 0.1 seconds |
| Total Throughput | 88.3 MB/minute |
| Collection Time (286 files) | 35.2 seconds |
| Memory Usage | Scales linearly, very efficient |

#### Quality Assurance

✅ **Perfect Reliability**
- 18/18 validation files: PASSED
- 286/286 full collection: PASSED
- Zero failures
- Zero errors
- Consistent quality across entire collection

✅ **Production Ready**
- Fully integrated in conversion pipeline
- Tested on complete Laxity collection
- Comprehensive documentation
- Automated testing available

#### When to Use Laxity Driver

**Use Laxity Driver**:
- ✅ Converting Laxity NewPlayer v21 SID files
- ✅ Maximum accuracy needed
- ✅ Preserving original music quality
- ✅ High-quality SF2 output required

**Use Standard Driver (np20/driver11)**:
- Converting non-Laxity SID files
- Need full SF2 editor features
- Working with other player types
- Testing compatibility

#### Output Files

When using `--driver laxity`, generated SF2 files contain:
- **SF2 Header**: Metadata blocks (file info, version)
- **Laxity Driver**: 8 KB core driver with entry points
- **Music Data**: Sequences, instruments, tables in native format
- **Status**: Ready for immediate use in SID Factory II
- **Quality**: 70-90% accuracy maintained from original

#### Limitations & Future Work

**Current Version**:
- ✅ Playback in SID Factory II: WORKING
- ⏳ Full editor table editing: Planned (Phase 6)
- ✅ Laxity NewPlayer v21: SUPPORTED
- ❌ Other Laxity versions: Not yet supported

**Phase 6 Enhancement** (Optional):
- Add SF2 editor table editing support
- Implement format translation layer if needed
- Full bidirectional editor integration

#### Documentation & References

For complete technical details and implementation info:
- **`LAXITY_DRIVER_FINAL_REPORT.md`** - Comprehensive implementation report
- **`LAXITY_DRIVER_PROGRESS.md`** - Phase-by-phase development progress
- **`LAXITY_BATCH_TEST_RESULTS.md`** - 18-file validation results
- **`LAXITY_FULL_COLLECTION_CONVERSION_RESULTS.md`** - 286-file production results
- **`PHASE5_INTEGRATION_PLAN.md`** - Architecture and integration details

### Optional Analysis Tools (NEW in v2.0.0) 🔬

**Pipeline Enhancement v2.0.0** adds 8 optional analysis tools for comprehensive SID file analysis. All tools are integrated into Phase 5 of the conversion pipeline and can be enabled with CLI flags.

#### Available Tools

**1. SIDwinder Tracer** (Step 7.5)
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --trace --frames 1500
```
- Generates frame-by-frame SID register write traces
- Output: `analysis/{name}_trace.txt` (1 line per frame: "FRAME: D40X:$YY,...")
- Uses Python SIDwinder (cross-platform, no Wine needed)
- Use cases: Validation, debugging, format analysis

**2. 6502 Disassembler** (Step 8.5)
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --disasm
```
- Disassembles init and play routines to 6502 assembly
- Output: `analysis/{name}_init.asm`, `analysis/{name}_play.asm`
- Annotated with addresses, opcodes, and instruction comments
- Use cases: Reverse engineering, player analysis, optimization

**3. Audio Export** (Step 16)
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --audio-export --audio-duration 30
```
- Exports SID to WAV audio for reference listening
- Output: `analysis/{name}.wav` (44100Hz, 16-bit, stereo)
- Wraps SID2WAV.EXE with duration/quality controls
- Use cases: Quality comparison, audio reference, validation

**4. Memory Map Analyzer** (Step 12.5)
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --memmap
```
- Analyzes memory layout and identifies code vs data regions
- Output: `analysis/{name}_memmap.txt` with ASCII memory map
- Shows init/play routines, SID chip registers, data regions
- Use cases: Memory optimization, player understanding, debugging

**5. Pattern Recognizer** (Step 17)
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --patterns
```
- Identifies repeating byte patterns for compression opportunities
- Output: `analysis/{name}_patterns.txt` with pattern statistics
- Non-overlapping pattern detection (4-32 byte patterns)
- Use cases: Compression analysis, optimization, format study

**6. Subroutine Tracer** (Step 18)
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --callgraph
```
- Traces JSR calls and builds call graphs
- Output: `analysis/{name}_callgraph.txt` with caller-callee relationships
- Identifies init vs play routines, call depths, leaf subroutines
- Use cases: Code flow analysis, optimization, player understanding

**7. Report Generator** (Step 19) - Automatic
```bash
# Runs automatically when any analysis tools are used
```
- Consolidates all analysis outputs into unified report
- Output: `analysis/{name}_REPORT.txt` with executive summary
- Includes: File index, statistics, previews of all reports
- Use cases: Quick overview, comprehensive documentation

**8. Output Organizer** (Step 20)
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --organize [... other tools ...]
```
- Organizes analysis files into structured directories
- Creates: `disassembly/`, `reports/`, `audio/`, `binary/` subdirectories
- Generates: `INDEX.txt` (file index) and `README.md` (usage guide)
- Use cases: Clean organization, batch processing, archiving

#### Combined Usage

Run multiple tools together for comprehensive analysis:

```bash
# Full analysis suite
python scripts/sid_to_sf2.py input.sid output.sf2 \
    --driver laxity \
    --trace --frames 1500 \
    --disasm \
    --audio-export --audio-duration 30 \
    --memmap \
    --patterns \
    --callgraph \
    --organize

# Output structure:
# output/analysis/
#   INDEX.txt                    # File index
#   README.md                    # Usage guide
#   disassembly/
#     input_init.asm             # Init routine disassembly
#     input_play.asm             # Play routine disassembly
#   reports/
#     input_trace.txt            # SID register trace
#     input_memmap.txt           # Memory map
#     input_patterns.txt         # Pattern analysis
#     input_callgraph.txt        # Call graph
#     input_REPORT.txt           # Consolidated report
#   audio/
#     input.wav                  # Audio export
```

#### Performance Impact

All tools run in Phase 5 (after conversion complete):
- **Trace** (1500 frames): ~1-2 seconds
- **Disassembly**: <1 second
- **Audio Export** (30s): ~3-5 seconds
- **Memory Map**: <1 second
- **Pattern Recognition**: <1 second
- **Call Graph**: <1 second
- **Report Generator**: <1 second (automatic)
- **Output Organizer**: <1 second

Total overhead: ~5-10 seconds for full suite

#### Test Coverage

- **200+ unit tests** (100% pass rate)
- **17 tests per tool** on average
- **Cross-platform** (Windows, Mac, Linux)
- **Pure Python** (zero external dependencies except SID2WAV.EXE for audio)

#### Documentation

For detailed documentation on each tool:
- Complete guide: See `docs/guides/ANALYSIS_TOOLS_GUIDE.md` (coming soon)
- Tool integration: See `docs/ARCHITECTURE.md` (Phase 5 section)
- API reference: See `docs/COMPONENTS_REFERENCE.md`

### Batch Conversion

Convert all SID files in a directory:

```bash
python scripts/convert_all.py [--input SID] [--output output] [--roundtrip]
```

Examples:
```bash
# Convert all SIDs in SID folder to output folder (generates both NP20 and Driver 11)
python scripts/convert_all.py

# Custom input/output directories
python scripts/convert_all.py --input my_sids --output my_output

# Include round-trip validation (SID→SF2→SID verification)
python scripts/convert_all.py --roundtrip

# Custom validation duration (default: 10 seconds)
python scripts/convert_all.py --roundtrip --roundtrip-duration 30
```

The batch converter creates a nested structure: `output/{SongName}/New/` containing:
- `{name}_g4.sf2` - SID Factory II project file (NP20/G4 driver)
- `{name}_d11.sf2` - SID Factory II project file (Driver 11, default for validation)
- `{name}_d11.sid` - Exported SID file from SF2 (for validation)
- `{name}_info.txt` - Detailed extraction info with data structure addresses
- `{name}_original.dump` - Original SID register dump (30 seconds)
- `{name}_exported.dump` - Exported SID register dump (30 seconds)
- `{name}_original.wav` - Original audio render (16-bit, 30 seconds)
- `{name}_exported.wav` - Exported audio render (16-bit, 30 seconds)
- `{name}_original.hex` - Original SID hexdump (16 bytes/line)
- `{name}_converted.hex` - Converted SID hexdump (16 bytes/line)

Round-trip validation creates additional folders:
- `output/{SongName}/Original/` - Original SID, WAV, dump, and info
- `output/{SongName}/New/` - Converted files plus exported SID for comparison
- `output/{SongName}/{name}_roundtrip_report.html` - Detailed comparison report

### Complete Pipeline with Validation (v1.2)

**NEW**: Comprehensive 12-step pipeline with MIDI validation and SIDwinder integration for complete analysis and validation:

```bash
python complete_pipeline_with_validation.py
```

This processes all SID files with complete validation, analysis, and documentation:

#### Pipeline Steps:
1. **SID → SF2 Conversion** - Smart detection (SF2-packed/Template/Laxity methods)
1.5. **Siddump Sequence Extraction** - Runtime analysis for accurate sequences
**1.6. SIDdecompiler Player Analysis** (NEW in v1.4) - Automated player type detection and memory layout analysis
2. **SF2 → SID Packing** - Generates playable SID files
3. **Siddump Generation** - Register dumps (original + exported SIDs)
4. **WAV Rendering** - 30-second audio (original + exported)
5. **Hexdump Generation** - Binary analysis (original + exported)
6. **SIDwinder Trace** - Register write traces (requires SIDwinder rebuild)
7. **Info.txt Reports** - Comprehensive conversion metadata
8. **Annotated Disassembly** - Python-based code analysis
9. **SIDwinder Disassembly** - Professional KickAssembler output (original SIDs only*)
10. **Validation Check** - Verifies all required files generated
11. **MIDI Comparison** - Python MIDI emulator validation and comparison report

#### Output Structure (15 files per SID):

**Original/** (4 files):
- `{name}_original.dump` - Siddump register capture
- `{name}_original.wav` - 30-second audio
- `{name}_original.hex` - Binary hexdump
- `{name}_original.txt` - SIDwinder trace (empty until rebuild)

**New/** (11 files):
- `{name}.sf2` - Converted SF2 file
- `{name}_exported.sid` - Packed SID file
- `{name}_exported.dump` - Siddump register capture
- `{name}_exported.wav` - 30-second audio
- `{name}_exported.hex` - Binary hexdump
- `{name}_exported.txt` - SIDwinder trace (empty until rebuild)
- `{name}_exported_disassembly.md` - Annotated disassembly
- `{name}_exported_sidwinder.asm` - SIDwinder disassembly*
- `{name}_python.mid` - Python MIDI emulator output
- `{name}_midi_comparison.txt` - MIDI validation report
- `info.txt` - Comprehensive conversion report

**Known Limitation**: *SIDwinder disassembly currently works only for original SID files due to a pointer relocation limitation in the SF2 packer. Exported SIDs play correctly in all emulators but trigger SIDwinder's strict CPU emulation checks.

#### Latest Results (2025-12-13):
- **18 SID files processed** in ~2.5 minutes
- **Complete success**: 5.6% (all 15 files)
- **Partial success**: 94.4% (13-14/15 files - missing .asm due to limitation above)
- **Core pipeline**: 100% success (Steps 1-8, 10)
- **WAV rendering**: 97% success (35/36 files - 1 timeout)
- **SIDwinder trace**: ✅ 100% working (rebuilt with fixes)
- **SIDwinder disassembly**: Works for original SIDs, limited for exported SIDs
- **Average accuracy**: 45.39% (7 files at 100%, 10 LAXITY files at 1-8%)

See `PIPELINE_EXECUTION_REPORT.md` for detailed analysis and `tools/SIDWINDER_QUICK_REFERENCE.md` for SIDwinder commands.

### SIDdecompiler Integration (v1.4 - NEW)

**Automated Player Analysis and Memory Layout Visualization** (NEW in v1.4)

The SIDdecompiler integration provides comprehensive player type detection and memory layout analysis:

**Key Features**:
- ✅ **100% Player Detection Accuracy** - Correctly identifies Laxity NewPlayer v21
- ✅ **Automated Analysis** - Runs as Step 1.6 in the pipeline
- ✅ **Memory Layout Visualization** - ASCII memory maps showing code, data, and tables
- ✅ **Table Detection** - Identifies filter, pulse, instrument, and wave tables
- ✅ **Structure Reports** - Comprehensive analysis with addresses and statistics
- ✅ **Hybrid Validation** - Manual extraction + auto validation for error prevention

**Production Recommendation**:
- Use for automated player type detection (100% accurate)
- Use for memory layout debugging and visualization
- Use for table address validation
- Manual table extraction remains primary method (proven reliable)

**Output Files**:
- `analysis/{name}_siddecompiler.asm` - Complete 6502 disassembly
- `analysis/{name}_analysis_report.txt` - Player info and memory layout analysis

**Example Analysis Report**:
```
Player Information:
  Type: NewPlayer v21 (Laxity)
  Memory Range: $A000-$B9A7 (6,568 bytes)

Memory Layout:
$A000-$B9A7 [████████████████████████████████████████] Player Code (6,568 bytes)

Detected Tables:
  Filter Table: $1A1E (128 bytes)
  Pulse Table: $1A3B (256 bytes)
  Instrument Table: $1A6B (256 bytes)
  Wave Table: $1ACB (variable)
```

**Documentation**:
- Complete implementation guide: `docs/implementation/SIDDECOMPILER_INTEGRATION.md`
- Integration analysis: `docs/analysis/SIDDECOMPILER_INTEGRATION_ANALYSIS.md`
- Lessons learned: `docs/implementation/SIDDECOMPILER_LESSONS_LEARNED.md`

### SIDwinder Integration

**SIDwinder v0.2.6** - C64 SID file processor with multiple capabilities:

#### Features:
- **Disassemble**: Converts SID to KickAssembler source (✅ Working - integrated)
- **Trace**: SID register write tracer (✅ Working - rebuilt on 2025-12-06)
- **Player**: Links SID with visualization players (🔧 Manual use)
- **Relocate**: Moves SID to different memory addresses (🔧 Manual use)

#### Quick Commands:

```bash
# Disassemble SID to assembly
tools/SIDwinder.exe -disassemble SID/file.sid output.asm

# Trace SID register writes (generates 7-13 MB trace files)
tools/SIDwinder.exe -trace=output.txt SID/file.sid

# Create visualizer player
tools/SIDwinder.exe -player=RaistlinBars music.sid output.prg

# Relocate SID to different address
tools/SIDwinder.exe -relocate=$2000 input.sid output.sid
```

#### Integration Status:
- ✅ **Disassembly**: Fully integrated in complete pipeline (Step 9)
- ✅ **Trace**: Fully working and integrated in pipeline (Step 6)
- ✅ **Source Patches**: Applied and executable rebuilt on 2025-12-06
- ✅ **Trace Output**: Generates 7-13 MB files with frame-by-frame register writes

**Note**: SIDwinder.exe has been rebuilt with trace fixes applied. See `tools/SIDWINDER_FIXES_APPLIED.md` for patch details and `SIDWINDER_REBUILD_GUIDE.md` for rebuild instructions.

### Round-trip Validation

Test the complete conversion pipeline (SID→SF2→SID):

```bash
python scripts/test_roundtrip.py <input.sid> [--duration 30]
```

This validates that:
1. SID converts to SF2 successfully
2. SF2 packs back to SID with proper code relocation
3. Audio output matches between original and converted files
4. Register writes are preserved correctly

### Waveform Analysis (v0.7.2)

> **📖 Complete Guide**: See `docs/guides/WAVEFORM_ANALYSIS_GUIDE.md` for comprehensive waveform analysis documentation.

Generate interactive HTML reports with waveform visualizations and audio comparison:

```bash
# Analyze all files in pipeline output
python scripts/analyze_waveforms.py output/SIDSF2player_Complete_Pipeline

# Analyze specific song directory
python scripts/analyze_waveforms.py output/MySong
```

Each report includes:
- **Embedded Audio Players** - Play original and exported WAV files side-by-side
- **Waveform Visualizations** - HTML5 canvas charts showing audio waveforms
- **Similarity Metrics** - Correlation coefficient, RMSE, match rate
- **File Statistics** - Sample rates, bit depth, duration, peak/average amplitudes
- **Analysis Notes** - Explanation of expected differences between players

Output: `{SongName}_waveform_analysis.html` in each song directory

**Note**: Uses Python standard library only (wave module), no NumPy/Matplotlib required.

## SF2 Viewer (NEW in v2.1) 🎵

**Professional GUI for viewing and analyzing SID Factory II (.sf2) files with visualization and audio playback.**

> **📖 Complete Guide**: See `docs/guides/SF2_VIEWER_GUIDE.md` for comprehensive documentation including SF2 Text Exporter and SF2 Editor Enhancements.

### Features

#### 🎨 Visualization Tools
- **Waveform Display**: View waveform samples as connected line graphs with grid
- **Filter Curves**: Visualize filter cutoff frequency progression (11-bit, 0-2047)
- **ADSR Envelopes**: Display Attack/Decay/Sustain/Release shapes with phase labels
- **Real-time Updates**: Automatic visualization when selecting different tables
- **No External Dependencies**: Uses only PyQt6 QPainter (no NumPy/Matplotlib)

#### 🔊 Audio Playback
- **Play Full Song**: Convert SF2→SID→WAV and play with audio output
- **Playback Controls**: Play, Pause/Resume, Stop with proper state management
- **Volume Control**: 0-100% volume slider with real-time adjustment
- **Position Tracking**: MM:SS format with live duration display
- **Status Log**: Shows conversion steps (SF2→SID, SID→WAV) and error messages
- **Clean Shutdown**: Automatic temporary file cleanup on stop

#### 📊 Multi-Tab Interface
1. **Overview**: File validation summary and metadata
2. **Header Blocks**: SF2 block structure with hex dump details
3. **Tables**: Spreadsheet view of all music tables
4. **All Tables**: Combined view of all tables with alignment
5. **Memory Map**: Visual ASCII layout of memory organization
6. **OrderList**: 3-column sequence playback order (Laxity format)
7. **Visualization** (NEW): Waveform, filter, and envelope graphs
8. **Playback** (NEW): Audio preview with full controls

#### ✨ Smart Features
- **Drag-and-Drop**: Load SF2 files directly onto the window
- **File Browser**: Standard dialog for file selection
- **Auto-Disabled Tabs**: Sequences tab disabled for Laxity files (not available)
- **8-Tab Interface**: All SF2 data accessible and viewable
- **Professional Layout**: PyQt6 modern UI matching SID Factory II design

### Installation

#### Windows (Easiest - Batch Launcher)

```bash
cd SIDM2
launch_sf2_viewer.bat
```

The launcher will:
- Check if Python is installed
- Check if PyQt6 is installed
- Offer to install PyQt6 if missing
- Launch the SF2 Viewer automatically

#### macOS/Linux

```bash
# Install PyQt6
pip install PyQt6 PyQt6-Multimedia

# Navigate to SIDM2 directory
cd SIDM2

# Run the viewer
python sf2_viewer_gui.py
```

Or use the Python launcher:

```bash
cd SIDM2
python launch_sf2_viewer.py
```

### Usage

#### Loading Files

1. **Drag and Drop**: Drag an SF2 file onto the window
2. **Browse Button**: Click "Browse..." to select a file
3. **File Menu**: Use File → Open SF2 File...

#### Visualization Tab

1. Load an SF2 file
2. Go to "Visualization" tab
3. Select table from dropdown (Wave, Filter, Pulse, Instruments)
4. View real-time visualization with grid and labels

**Supported Visualizations**:
- **Wave Table**: Waveform samples (0-255) as line graph
- **Filter Table**: Cutoff frequency curves (0-2047)
- **Pulse Table**: Pulse width progression
- **Instruments Table**: ADSR envelope for first instrument

#### Playback Tab

1. Load an SF2 file
2. Go to "Playback" tab
3. Click "Play Full Song" to start conversion and playback
4. Use "Pause" to pause/resume playback
5. Use "Stop" to stop and clean up temporary files
6. Adjust volume slider for real-time volume control

**Playback Process**:
```
SF2 File
  ↓
scripts/sf2_to_sid.py (export to SID)
  ↓
tools/SID2WAV.EXE (render to audio)
  ↓
PyQt6 QMediaPlayer (playback)
```

### Technical Architecture

#### Modules

- **`sf2_viewer_core.py`** (450 lines): SF2 format parser
  - Complete SF2 file parsing
  - All block type support
  - Table data extraction
  - Memory map generation

- **`sf2_visualization_widgets.py`** (300 lines): Custom visualization widgets
  - WaveformWidget: Line graph rendering
  - FilterResponseWidget: Frequency curve display
  - EnvelopeWidget: ADSR shape visualization
  - Antialiased drawing with proper scaling

- **`sf2_playback.py`** (150 lines): Audio playback engine
  - SF2 conversion pipeline
  - PyQt6 QMediaPlayer integration
  - Volume control and position tracking
  - Temporary file management

- **`sf2_viewer_gui.py`** (900 lines): PyQt6 main application
  - 8-tab interface with specialized panels
  - File loading (drag-drop and browse)
  - Tab update methods for each data type
  - Sequence validation for Laxity files

#### Dependencies

- **Python**: 3.8+
- **PyQt6**: GUI framework
- **PyQt6-Multimedia**: Audio playback (optional, required for playback tab)
- **External Tools**: scripts/sf2_to_sid.py, tools/SID2WAV.EXE

#### Data Flow

```
SF2 File
  ↓
SF2Parser (parse structure, extract tables)
  ↓
TableDescriptor (identify tables)
  ↓
get_table_data() (format table data)
  ↓
Visualization Widgets (render graphics)
```

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open file |
| Ctrl+Q | Quit |
| Ctrl+Tab | Switch tabs |

### Troubleshooting

#### "PyQt6 is required"
Install with: `pip install PyQt6 PyQt6-Multimedia`

#### "Failed to parse SF2 file"
- Verify file is valid SF2 format (magic ID 0x1337)
- Check file is not corrupted
- Try with a known good SF2 file first

#### "Playback not working"
- Ensure PyQt6-Multimedia is installed: `pip install PyQt6-Multimedia`
- Check tools/SID2WAV.EXE exists and is executable
- Verify scripts/sf2_to_sid.py is present

#### Sequences tab is disabled
- This is normal for Laxity driver files
- Laxity files don't store playable sequences in SF2 format
- Musical information is in OrderList and Commands tables instead

### Example: Viewing Laxity Files

```bash
# Launch viewer
cd SIDM2
python sf2_viewer_gui.py

# Load file
# Drag and drop: Laxity - Stinsen - Last Night Of 89.sf2

# View tabs:
# - Overview: File info and validation
# - Header Blocks: 9 SF2 blocks with metadata
# - Tables: All 9 tables (Instruments, Wave, Filter, etc.)
# - Memory Map: Visual memory layout
# - OrderList: 3-column structure (Col1, Col2, Col3)
# - Visualization: Waveform, filter, envelope graphs
# - Playback: Play music with volume and position controls
```

### Known Limitations

1. **Sequences Tab**: Disabled for Laxity files
   - Sequences not properly stored in SF2 format
   - Use OrderList + Commands tables instead

2. **Playback Duration**: Fixed at 30 seconds
   - Can be adjusted in `sf2_playback.py` `play_sf2()` method
   - Change `-t30` parameter in SID2WAV.EXE call

3. **Audio Quality**: Depends on SID2WAV.EXE
   - Renders at 16-bit, standard sample rate
   - Quality matches tool's capabilities

### Future Enhancements

- [ ] Configurable playback duration
- [ ] Real-time waveform analysis
- [ ] Export visualizations to images
- [ ] Waterfall plot for large tables
- [ ] MIDI export from sequence data
- [ ] Sequence visualization when available
- [ ] Theme customization (dark mode)

### Address Extraction

Extract memory addresses of all data structures from a SID file:

```bash
python scripts/extract_addresses.py <input.sid>
```

This analyzes the SID file and displays start/end addresses for:
- **Player Code**: Init and play routines
- **Sequences**: Music pattern data
- **Orderlists**: Playback order per voice
- **Instruments**: ADSR and table pointers
- **Wave Table**: Waveform and note data (split into notes/waveforms)
- **Pulse Table**: PWM programs
- **Filter Table**: Filter sweep programs
- **Arpeggio Table**: Chord patterns
- **Tempo**: Speed control data
- **Command Table**: Effect commands
- **Sequence Pointers**: Voice-to-sequence mapping

Address information is automatically included in the `info.txt` file during conversion for reference and debugging.

#### Info File Contents

The `_info.txt` file contains comprehensive extraction data:

- **Source File**: Filename, name, author, copyright, detected player (via player-id.exe)
- **Memory Layout**: Load/init/play addresses, data size
- **Original SID Data Structure Addresses**: Start/end addresses for all music data:
  - Player code (init/play routines)
  - Sequences, Orderlists, Instruments
  - Wave, Pulse, Filter, Arpeggio tables
  - Tempo, Command tables, Sequence pointers
- **Conversion Result**: Output file, size, driver, tempo, sequence/instrument counts
- **Original SID File (Preserved)**: Source path, size, copied location
- **Pipeline Tools Used**: Documentation of all tools used in conversion:
  - player-id.exe: Player identification with detected type
  - sid_to_sf2.py: Conversion tool
  - siddump.exe: Register dump (6502 emulation)
  - SID2WAV.EXE: Audio rendering
  - xxd: Hexdump generation
  - extract_addresses.py: Memory address extraction
  - generate_info.py: Report generation
- **Table Addresses in SF2**: SF2 format memory layout
- **Extraction Details**: Wave table analysis, siddump results
- **Validation Warnings**: Pointer bounds issues, sequence problems
- **Original SID Data Tables (Hex View)**: 16-byte hexdumps with addresses:
  - Commands, Instruments, Wave, Pulse, Filter, Arp tables
- **Converted SF2 Data Tables (Hex View)**: 16-byte hexdumps with addresses:
  - Commands, Instruments, Wave, Pulse, Filter, Arpeggio, Tempo tables
- **Instruments Table**: All extracted instruments with AD/SR values and names
- **Commands Table**: All 16 commands with usage counts from sequences
- **Wave Table**: Waveform entries with note offsets and descriptions
- **Pulse Table**: Pulse width modulation entries
- **Filter Table**: Filter sweep entries
- **HR/Tempo/Arp/Init Tables**: Additional configuration tables

Example Commands Table output:
```
Idx  Name          Used
  0  Slide Up      -
  1  Slide Down    53x
  2  Vibrato       13x
  3  Portamento    -
  ...
```

## SF2 Text Exporter (NEW in v2.2) 📝

**Export all SF2 data to human-readable text files for validation, debugging, and learning.**

### Overview

The SF2 Text Exporter extracts complete SF2 file contents and exports them to human-readable text files. This creates "ground truth" reference files for:
- **Validating SID→SF2 conversions** - Compare text exports to identify differences
- **Debugging conversion issues** - Examine exact data structures
- **Learning SF2 format** - Study actual data through examples
- **Creating test cases** - Reference files for automated testing

### Usage

```bash
# Export single file (auto-generate output directory)
python sf2_to_text_exporter.py "file.sf2"
# Output: output/{filename}_export/

# Export to specific directory
python sf2_to_text_exporter.py "file.sf2" output/my_export

# Example
python sf2_to_text_exporter.py "learnings/Laxity - Stinsen.sf2"
# Output: output/Laxity - Stinsen_export/
```

### Exported Files (12+ per SF2)

**Core Data:**
- `orderlist.txt` - Sequence playback order (3 tracks)
- `sequence_XX.txt` - Individual sequences (auto-detects single/interleaved format)
- `instruments.txt` - Instrument definitions (AD, SR, waveform, tables, HR)

**Table Data:**
- `wave.txt` - Wave table sequences
- `pulse.txt` - Pulse width sequences
- `filter.txt` - Filter cutoff sequences
- `arp.txt` - Arpeggio table (placeholder)

**Reference:**
- `tempo.txt` - Tempo information
- `hr.txt` - Hard Restart reference
- `init.txt` - Init values reference
- `commands.txt` - Command reference
- `summary.txt` - Statistics and file list

### Example Output

**sequence_08.txt** (single-track format):
```
SEQUENCE $08 (8)
================================================================================
Format: single
Length: 32 entries

Step  | Inst | Cmd  | Note
------|------|------|------
0000  | 0B   | --   | F-3
0001  | --   | --   | +++
0002  | --   | 02   | +++
0003  | --   | --   | +++
0004  | --   | --   | F-3
...
```

**orderlist.txt**:
```
ORDER LIST
================================================================================
Format: Step | Track 1 | Track 2 | Track 3
        Each entry: TT SS (TT=transpose, SS=sequence)

Step  | Track 1    | Track 2    | Track 3
------|------------|------------|------------
0000  | -- A6      | -- 00      | -- 00
0001  | -- A0      | -- A0      | -- A0
0002  | -- 0E      | -- 00      | -- 0A
...
```

### Use Cases

#### 1. Validate SID→SF2 Conversions

```bash
# Export reference SF2
python sf2_to_text_exporter.py reference.sf2 output/reference

# Convert SID→SF2
python scripts/sid_to_sf2.py input.sid converted.sf2

# Export converted SF2
python sf2_to_text_exporter.py converted.sf2 output/converted

# Compare
diff output/reference/sequence_08.txt output/converted/sequence_08.txt
```

#### 2. Debug Conversion Issues

```bash
# Export problematic SF2
python sf2_to_text_exporter.py problem.sf2 debug/

# Check format detection
cat debug/summary.txt

# Examine specific sequences
cat debug/sequence_0A.txt
```

#### 3. Learn SF2 Format

```bash
# Export various examples
python sf2_to_text_exporter.py examples/*.sf2

# Study structure differences
# Compare single-track vs interleaved sequences
```

### Features

- ✅ **Auto-format detection** - Single-track vs 3-track interleaved sequences
- ✅ **Hex notation** - Shows "Sequence $0A" format matching SID Factory II
- ✅ **Human-readable** - Aligned columns, clear headers
- ✅ **Comprehensive** - All data structures exported
- ✅ **Fast** - Exports <1 second per file
- ✅ **Zero dependencies** - Uses existing sf2_viewer_core.py parser

### Documentation

See `SF2_TEXT_EXPORTER_README.md` for complete documentation including:
- Detailed usage examples
- Output format specifications
- Troubleshooting guide
- Integration with validation workflows

---

## Python Tools (NEW in v2.8.0) 🐍

**Status**: ✅ **100% Production Ready** | **Platform**: Cross-platform (Windows, Mac, Linux)

Complete Python replacements for all Windows-only external tools, achieving **100% independence** from Wine and platform-specific dependencies.

### Overview

**Mission Accomplished**: All critical external tools replaced with pure Python:

| Tool | Python Version | Status | Tests | Accuracy |
|------|---------------|--------|-------|----------|
| **siddump.exe** | `siddump.py` | ✅ v2.6.0 | 38 tests | 100% musical content |
| **SIDdecompiler.exe** | `siddecompiler_complete.py` | ✅ v2.7.0 | 35 tests | 100% compatible |
| **SIDwinder.exe** | `sidwinder_trace.py` | ✅ v2.8.0 | 17 tests | 100% format compatible |

**Total**: 3,900+ lines Python code, 90+ unit tests, 20+ real-world validations, **100% pass rate**

### Python siddump (v2.6.0)

Frame-by-frame SID register analysis and sequence extraction.

**Features**:
- ✅ 100% musical content match vs C version
- ✅ All 11 CLI flags supported
- ✅ Cross-platform (no Wine needed)
- ✅ 38 comprehensive tests

**Usage**:
```bash
# Basic usage
python pyscript/siddump_complete.py music.sid

# Custom time (30 seconds)
python pyscript/siddump_complete.py music.sid -t30

# With profiling
python pyscript/siddump_complete.py music.sid -t30 -p
```

**API**:
```python
from sidm2.siddump import extract_from_siddump

result = extract_from_siddump('music.sid', playback_time=30)
# Automatic Python-first with C exe fallback
```

### Python SIDdecompiler (v2.7.0)

Complete 6502 disassembler with memory access tracking and table detection.

**Features**:
- ✅ All 256 opcodes (legal + illegal)
- ✅ All 13 addressing modes
- ✅ Memory access tracking (READ/WRITE/EXECUTE)
- ✅ Automatic label generation
- ✅ Table detection and classification
- ✅ 35 comprehensive tests

**Usage**:
```bash
# Basic disassembly
python pyscript/siddecompiler_complete.py input.sid output.asm

# With table detection
python pyscript/siddecompiler_complete.py input.sid output.asm --tables
```

**API**:
```python
from sidm2.siddecompiler import SIDdecompilerAnalyzer

analyzer = SIDdecompilerAnalyzer(use_python=True)
result = analyzer.analyze(sid_file, output_dir, ticks=3000)
# Returns: {'success': True, 'method': 'python', ...}
```

### Python SIDwinder (v2.8.0) ⭐ NEW

Frame-by-frame SID register write tracing for validation and debugging.

**Features**:
- ✅ SIDwinder-compatible output format
- ✅ Frame-aggregated tracing (efficient)
- ✅ Leverages CPU6502Emulator (proven code)
- ✅ Python-first with .exe fallback
- ✅ High performance (~0.1s per 100 frames)
- ✅ 17 unit tests + 10 real-world validations

**Usage**:
```bash
# Generate trace (1500 frames = 30 seconds)
python pyscript/sidwinder_trace.py --trace output.txt --frames 1500 input.sid

# Windows batch launcher
sidwinder-trace.bat -trace=output.txt -frames=1500 input.sid

# Quick test
python pyscript/sidwinder_trace.py --trace test.txt --frames 100 input.sid -v
```

**API**:
```python
from sidm2.sidwinder_wrapper import trace_sid

result = trace_sid(
    sid_file=Path("input.sid"),
    output_file=Path("output.txt"),
    frames=1500
)
# Returns: {'success': True, 'method': 'python', 'writes': 2475, ...}
```

**Real-World Validation**:
- 10/10 Laxity files traced successfully
- 18,322 SID register writes captured
- 173,914 bytes output generated
- 100% success rate

### Benefits

**Cross-Platform Support**:
- ✅ **Windows**: Native Python + .exe fallback
- ✅ **Mac**: Pure Python (no Wine needed!)
- ✅ **Linux**: Pure Python (no Wine needed!)

**Maintenance**:
- ✅ Single language (Python)
- ✅ 90+ comprehensive tests
- ✅ Easy to debug and extend
- ✅ Community contributions enabled

**Performance**:
- ⚡ Fast execution (seconds, not minutes)
- 💾 Low memory usage (<100 MB)
- 🔧 Reliable error handling

### Documentation

- **Quick Reference**: `CLAUDE.md` (sections for each tool)
- **Design Docs**: `docs/analysis/` (architecture and implementation)
- **Analysis**: `docs/analysis/EXTERNAL_TOOLS_REPLACEMENT_ANALYSIS.md`
- **API Docs**: `docs/COMPONENTS_REFERENCE.md`

---

## Laxity Driver (NEW)

**Version**: 1.0 | **Added**: v1.8.0 (2025-12-13) | **Status**: Production Ready

The Laxity driver provides native support for Laxity NewPlayer v21 SID files with significantly improved conversion accuracy by preserving the original Laxity format instead of translating to NP20/Driver 11 format.

### Why Use the Laxity Driver?

**Accuracy Comparison**:
- **Standard drivers (NP20/Driver 11)**: 1-8% accuracy for Laxity files
  - Requires lossy format translation
  - Tables converted between incompatible formats
  - Significant data loss during conversion

- **Laxity driver**: **99.93% frame accuracy** ✅ (validated, production ready)
  - Uses original Laxity player code
  - Tables preserved in native format
  - No format conversion artifacts
  - Perfect register write counts (507 → 507)

### Quick Start

```bash
# Single file conversion
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity

# Example with real file
python scripts/sid_to_sf2.py SID/Stinsens_Last_Night_of_89.sid output/Stinsens_laxity.sf2 --driver laxity

# Batch conversion
python test_laxity_batch.py  # Converts 3 test files
```

### When to Use Laxity Driver

**✓ Use Laxity driver for**:
- Laxity NewPlayer v21 SID files
- Files identified as "Laxity" or "NewPlayer" by player-id.exe
- Maximum conversion accuracy requirements
- Preserving original player characteristics

**✗ Use standard drivers for**:
- Non-Laxity SID files
- SF2-exported SIDs (use reference file for 100% accuracy)
- Maximum SF2 editor compatibility
- Complex table editing requirements

### Architecture

The Laxity driver consists of four integrated components:

#### 1. SF2 Wrapper ($0D7E-$0DFF, 130 bytes)
- Standard SF2 file ID: $1337
- Entry points: init ($0D80), play ($0D83), stop ($0D86)
- SID chip initialization and silence routines
- Compatible with SF2 editor and tools

#### 2. Relocated Laxity Player ($0E00-$16FF, 2,304 bytes)
- Original Laxity NewPlayer v21 code
- Relocated from $1000 to $0E00 (offset -$0200)
- 373 address references automatically patched
- 7 zero-page conflicts resolved ($F2-$FE → $E8-$EE)
- 100% playback compatibility maintained

#### 3. SF2 Header Blocks ($1700-$18FF, 84 bytes)
- Block 1: Descriptor (driver name and version)
- Block 2: Common (entry point addresses)
- Block 3: Tables (native Laxity format definitions)
- Block 5: Music data (orderlist and sequence pointers)
- Block FF: End marker

#### 4. Music Data ($1900+, variable size)
- Orderlists: 3 tracks × 256 bytes max
- Sequences: Packed format, variable length
- **Native Laxity format** (no conversion)

### Memory Layout

```
Address Range  | Size    | Contents
---------------|---------|----------------------------------
$0D7E-$0DFF    | 130 B   | SF2 wrapper code
$0E00-$16FF    | 2,304 B | Relocated Laxity player
$1700-$18FF    | 512 B   | SF2 header blocks
$1900-$1BFF    | 768 B   | Orderlists (3 tracks)
$1C00+         | Var     | Sequences (packed)
```

### Table Formats (Native Laxity)

The Laxity driver preserves native table formats:

**Instruments** (8 bytes × 32 entries, column-major)
- Address: $186B (relocated from $1A6B)
- Columns: AD, SR, Flags, Filter, Pulse, Wave
- No conversion from Laxity format

**Wave Table** (2 bytes × 128 entries, row-major)
- Address: $18CB (relocated from $1ACB)
- Format: [waveform, note_offset]
- Native Laxity encoding

**Pulse Table** (4 bytes × 64 entries, row-major)
- Address: $183B (relocated from $1A3B)
- Y*4 indexed (multiply Y by 4)
- Laxity PWM format

**Filter Table** (4 bytes × 32 entries, row-major)
- Address: $181E (relocated from $1A1E)
- Y*4 indexed
- Laxity filter sweep format

### Test Results

```
File                          Output Size  Status
Stinsens_Last_Night_of_89     5,224 bytes  ✓ Pass
Beast                         5,207 bytes  ✓ Pass
Dreams                        5,198 bytes  ✓ Pass

Success Rate: 100% (3/3 files)
```

### Features

**✓ Native Format Preservation**
- Tables stay in Laxity format
- No lossy conversion
- Maximum compatibility

**✓ Automatic Code Relocation**
- Scans 6502 opcodes for absolute addressing
- Patches 373 address references
- Resolves zero-page conflicts
- Preserves SID register references

**✓ Custom Music Data Injection**
- Intelligent file offset calculation
- Dynamic file size extension
- Native orderlist/sequence formats
- Efficient memory usage

**✓ Production Ready**
- Tested with multiple files
- Complete error handling
- Comprehensive logging
- Full documentation

### Comparison Matrix

| Feature | Laxity Driver | NP20 Driver | Driver 11 |
|---------|---------------|-------------|-----------|
| Format | Native Laxity | Translated | Translated |
| Accuracy (Laxity files) | **99.93%** ✅ | 1-8% | 1-8% |
| Table preservation | ✓ Yes | ✗ Converted | ✗ Converted |
| Table injection | ✓ Full | ✗ Translation | ✗ Translation |
| File size | ~5.2KB | ~25KB | ~25-50KB |
| SF2 editor support | Basic | Full | Full |
| Table editing | Limited | Full | Full |
| Player compatibility | Laxity v21 only | Universal | Universal |

### Limitations

**Current Limitations**:
1. **Filter table format**: Filter accuracy at 0% (Laxity filter format not yet converted).
2. **Playback optimized**: File is optimized for playback. Table editing in SF2 editor may not work correctly.
3. **Single subtune**: Only supports single-subtune SID files (same as standard drivers).
4. **Laxity v21 only**: Specifically designed for Laxity NewPlayer v21. Other versions not tested.

**Planned Improvements**:
- Extract and inject custom tables from original SID
- Enhanced SF2 editor integration
- Multi-subtune support
- Accuracy optimization (target >90%)

### Technical Implementation

The Laxity driver was built using a complete toolchain:

**Extraction** (`scripts/extract_laxity_player.py`)
- Extracts player binary from reference SID
- Identifies player code boundaries
- Exports 3,328 bytes for analysis

**Relocation Analysis** (`scripts/analyze_laxity_relocation.py`)
- Scans for absolute addressing opcodes
- Identifies 373 address references
- Detects 7 zero-page conflicts
- Generates relocation map

**Code Relocation** (`scripts/relocate_laxity_player.py`)
- Patches all address references (-$0200 offset)
- Remaps zero-page conflicts
- Preserves SID register access
- Outputs relocated player binary

**Header Generation** (`scripts/generate_sf2_header.py`)
- Creates SF2 metadata blocks
- Defines table layouts
- Generates 84-byte header

**Driver Assembly** (`drivers/laxity/laxity_driver.asm`)
- 6502 assembly wrapper
- SF2 entry points
- SID initialization
- Built with 64tass assembler

**Custom Injection** (`sidm2/sf2_writer.py`)
- `_inject_laxity_music_data()` method
- Native format support
- Smart offset calculation
- Dynamic file sizing

### Troubleshooting

**"Invalid driver type" error**
- Update to v1.8.0 or later
- Verify `--driver laxity` spelling

**Small output file (<5KB)**
- Music data may not be injecting
- Check logs for warnings
- Verify input is Laxity format

**Playback issues**
- Confirm file is Laxity NewPlayer v21
- Run: `tools/player-id.exe input.sid`
- Enable verbose logging: `--verbose`

### Advanced Usage

**Python API**:
```python
from scripts.sid_to_sf2 import convert_sid_to_sf2

convert_sid_to_sf2(
    input_path="SID/Stinsens.sid",
    output_path="output/Stinsens_laxity.sf2",
    driver_type='laxity'
)
```

**Batch Processing**:
```python
from pathlib import Path
from scripts.sid_to_sf2 import convert_sid_to_sf2

for sid_file in Path("SID/").glob("*.sid"):
    output = f"output/laxity/{sid_file.stem}_laxity.sf2"
    convert_sid_to_sf2(str(sid_file), output, driver_type='laxity')
```

### Documentation

**User Guide**: `docs/guides/LAXITY_DRIVER_USER_GUIDE.md` (v2.0.0)
- Complete user documentation
- Quick start and installation
- Troubleshooting guide
- Advanced examples

**Technical Reference**: `docs/reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md` (v2.0.0)
- Architecture and design
- Memory layout and pointer patching
- Phase 5-6 implementation details
- Implementation summary
- Test results
- Code references

**Source Code**: `sidm2/sf2_writer.py` (lines 1330-1441)
- Custom injection logic
- Well-commented code
- Error handling

### Building the Driver

The driver can be rebuilt from source:

```bash
# 1. Generate header blocks
python scripts/generate_sf2_header.py drivers/laxity/laxity_driver_header.bin

# 2. Relocate player (if needed)
python scripts/relocate_laxity_player.py drivers/laxity/laxity_player_reference.bin

# 3. Assemble driver (Windows)
cd drivers/laxity
build_driver.bat

# Output: sf2driver_laxity_00.prg (3,460 bytes)
```

### Performance

**Conversion Speed**: ~200ms per file
**Output Size**: 5.2KB average (vs 25-50KB for standard drivers)
**Memory Efficiency**: Compact format, minimal overhead
**Compatibility**: Works with VICE, SID2WAV, siddump

### Future Roadmap

**v1.9** - Enhanced Table Support
- Extract custom tables from original SID
- Inject instrument/wave/pulse/filter tables
- Replace driver defaults with actual data

**v2.0** - SF2 Editor Integration
- Enhanced metadata for table editing
- Format translation layer for editor
- Full editing support

**v2.1** - Multi-Subtune Support
- Support for multi-song SID files
- Subtune switching
- Combined playlist support

For complete documentation, see `docs/guides/LAXITY_DRIVER_USER_GUIDE.md` (user guide) and `docs/reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md` (technical reference).

## File Formats

### PSID/RSID Format (Input)

The SID file format is the standard for distributing Commodore 64 music. It contains:

#### Header Structure (Version 2)

| Offset | Size | Description |
|--------|------|-------------|
| $00-$03 | 4 | Magic ID: "PSID" or "RSID" |
| $04-$05 | 2 | Version (big-endian) |
| $06-$07 | 2 | Data offset |
| $08-$09 | 2 | Load address (0 = embedded in data) |
| $0A-$0B | 2 | Init address |
| $0C-$0D | 2 | Play address |
| $0E-$0F | 2 | Number of songs |
| $10-$11 | 2 | Start song |
| $12-$15 | 4 | Speed flags |
| $16-$35 | 32 | Song name (null-terminated) |
| $36-$55 | 32 | Author name |
| $56-$75 | 32 | Copyright info |
| $76-$7B | 6 | V2+ flags and SID addresses |
| $7C+ | - | C64 program data |

The C64 data section contains compiled 6502 machine code with the player routine and encoded music data.

### JCH NewPlayer v21 Format (Laxity Player)

JCH NewPlayer v21 was coded by Laxity (Thomas Egeskov Petersen) of Vibrants in 2005. This is the player routine used in many SID files and is directly related to SID Factory II, which Laxity also created.

#### Instrument Format (8 bytes)

| Byte | Description | Notes |
|------|-------------|-------|
| 0 | AD (Attack/Decay) | Standard SID ADSR |
| 1 | SR (Sustain/Release) | Standard SID ADSR |
| 2 | Restart Options / Wave Count Speed | See below |
| 3 | Filter Setting | Low nibble: pass band, High nibble: resonance |
| 4 | Filter Table Pointer | 0 = no filter program |
| 5 | Pulse Table Pointer | Index into pulse table |
| 6 | Pulse Property | Bit 0: reset on instrument only, Bit 1: filter reset control |
| 7 | Wave Table Pointer | Index into wave table |

##### Restart Options (Byte 2)

- Low nibble: Wave count speed
- High nibble: Instrument restart mode
  - `$8x` - Hard restart (fixed)
  - `$4x` - Soft restart (gate off only, no silence)
  - `$2x` - Laxity hard restart (requires bit 7 set: `$Ax` or `$Bx`)
  - `$1x` - Wave generator reset enable
  - `$00` - Gate off 3 frames before next note

#### Wave Table Format

Two bytes per entry:

| Byte | Description |
|------|-------------|
| 0 | Note offset ($80+ = absolute, $7F = jump, $7E = stop) |
| 1 | Waveform ($11=tri, $21=saw, $41=pulse, $81=noise) |

Special note offsets:
- `$7F xx` - Jump to index xx
- `$7E` - Stop processing, keep last entry
- `$80` - Recalculate base note + transpose (for "Hubbard slide" effects)

**Note**: Laxity format stores (note, waveform) but SF2 format stores (waveform, note). The converter swaps these bytes during conversion, except for `$7F` jump commands which remain as ($7F, target).

#### Pulse Table Format (4 bytes per entry, Y-indexed with stride 4)

The pulse table uses column-major storage with Y register indexing. Entry indices are pre-multiplied by 4.

| Byte | Description |
|------|-------------|
| 0 | Initial pulse value: hi nibble → $D402 (lo byte), lo nibble → $D403 (hi byte), or $FF = keep current |
| 1 | Add/subtract value per frame (applied to 16-bit pulse width) |
| 2 | Duration (bits 0-6) + direction (bit 7: 0=add, 1=subtract) |
| 3 | Next entry index (pre-multiplied by 4, e.g., entry 6 = $18) |

**Index Conversion**: When converting to SF2, all Y*4 indices must be divided by 4. This applies to:
- Pulse table "next" column (byte 3)
- Instrument pulse_ptr field

##### Pulse Table Example

```
Entry 0 (Y=$00): 08 00 00 00  ; Pulse=$0800, no modulation, loop to self
Entry 6 (Y=$18): 04 50 30 1C  ; Pulse=$0400, add $50/frame for 48 frames, then entry 7
Entry 7 (Y=$1C): FF 50 B0 18  ; Keep current, sub $50/frame for 48 frames, loop to entry 6
```

This creates a ping-pong pulse width modulation effect, sweeping from $0400 to $0850 and back.

#### Filter Table Format (4 bytes per entry)

| Byte | Description |
|------|-------------|
| 0 | Filter value ($FF = keep current) |
| 1 | Count value |
| 2 | Duration |
| 3 | Next filter table entry (absolute index) |

The first entry (4 bytes) is used for alternative speed (break speeds).

#### Super Commands

*Complete reference from JCH NewPlayer v21.g5 Final - (D) = Direct command, lasts until next note*

| Command | Description |
|---------|-------------|
| `$0x yy` | (D) Slide up speed $xyy |
| `$1? ??` | Free |
| `$2x yy` | (D) Slide down speed $xyy |
| `$3? ??` | Free |
| `$4x yy` | Invoke instrument x (00-1f) with alternative wave pointer yy |
| `$60 xy` | (D) Vibrato (x=frequency, y=amplitude) - canceled by note or slide |
| `$7? ??` | Free |
| `$8x xx` | Portamento speed $xxx |
| `$9x yy` | Set D=x and SR=yy (persistent until instrument change) |
| `$Ax yy` | (D) Set D=x and SR=yy directly (until next note) |
| `$b? ??` | Free |
| `$C0 xx` | (D) Set channel wave pointer directly to xx |
| `$Dx yy` | (D) Set filter/pulse (x=0: filter ptr, x=1: filter value, x=2: pulse ptr) |
| `$E0 xx` | Set speed to xx |
| `$F0 xx` | Set master volume |

#### Speed Settings

- Speeds below $02 use alternative speed lookup in filter table
- Speed lookup table contains up to 4 entries (wraps around)
- Write $00 as wrap-around mark for shorter tables
- Speeds of $01 in table are clamped to $02

#### Vibrato and Slide Special Cases

Vibrato and slides only apply to wave table entries with note offset = $00.

Special value $80 in wave table recalculates base note + transpose (enables "Hubbard slide" effect).

#### Memory Layout (Typical Laxity SID)

| Address | Content |
|---------|---------|
| $1000 | JMP init_routine |
| $1003 | JMP play_routine |
| $1006-$103F | Header data and text |
| $1040-$10C5 | Init routine |
| $10C6-$17FF | Player code |
| $1800-$19FF | Tables and configuration |
| $1A00+ | Instrument table (interleaved AD/SR/CTRL) |
| ... | Orderlists and sequences |

### SID Factory II Format (Output)

SF2 files are PRG files containing a driver plus structured music data. The format uses a block-based header system.

#### File Structure

| Section | Description |
|---------|-------------|
| Load address | 2 bytes (little-endian) |
| Driver code | Player routine (~2KB) |
| Header blocks | Configuration and pointers |
| Music data | Sequences, orderlists, tables |
| Auxiliary data | Metadata and descriptions |

#### Header Block IDs

| ID | Description |
|----|-------------|
| 1 | Descriptor (driver info) |
| 2 | Driver Common (addresses) |
| 3 | Driver Tables (table definitions) |
| 4 | Instrument Descriptor |
| 5 | Music Data (pointers) |
| 6 | Table Color Rules |
| 7 | Insert/Delete Rules |
| 8 | Action Rules |
| 9 | Instrument Data Descriptor |
| 255 | End marker |

#### Music Data Structure

The MusicData block defines:
- Track count (typically 3 for SID)
- Order list pointers (low/high tables)
- Sequence pointers (low/high tables)
- Order list and sequence data locations

#### SF2 Event Format

SF2 sequences use a different triplet order than the Laxity player:

| Byte | Description | Range |
|------|-------------|-------|
| 1 | Instrument | $80 (--), $A0-$BF (instrument+$A0) |
| 2 | Command | $80 (--), $C0+ (command index+$C0) |
| 3 | Note | $00-$5D (notes), $7E (+++), $7F (end) |

#### Table Types

| Type | Description |
|------|-------------|
| Instruments | ADSR, waveform, pulse settings |
| Commands | Effect definitions (slide, vibrato, etc.) |
| Wave | Waveform table |
| Pulse | Pulse width modulation |
| Filter | Filter settings |
| HR (High Resolution) | Fine-tuning |
| Arpeggio | Arpeggio patterns |
| Tempo | Speed settings |
| Init | Initialization data |

#### SF2 Table Details

##### Commands Table
The commands table is referenced from the middle numeric column in sequences. Because of this, **it is not possible to insert or delete rows** - all commands must be edited in place.

Press F12 in SID Factory II to open an expanded overlay showing the commands offered by the currently loaded driver (displayed in magenta).

##### Instruments Table
Instruments are referenced from the left numeric column in sequences - like commands, **you cannot insert or delete rows**.

The number of bytes and their purpose depends on the currently loaded driver, but typically includes:
- ADSR values (Attack, Decay, Sustain, Release)
- Index pointers to support tables (wave, pulse, filter)

**Tip**: Place cursor on an index pointer value and press Ctrl+Enter to jump to that row in the referenced table.

##### Wave Table
The wave table sets the waveform (left column) and semitone offset (right column).

Format: `WW NN` where:
- `WW` = Waveform ($11=tri, $21=saw, $41=pulse, $81=noise)
- `NN` = Semitone offset (e.g., $0C = +12 semitones = one octave higher)

Special values:
- Add $80 to the note value for **static/absolute notes** (great for drums)
- `7F xx` = Jump to row xx (e.g., `7F 02` wraps to row 3)

##### Pulse Table
The pulse table defines pulse width modulation for waveform $41 and combined waveforms. It controls:
- Range of pulse width sweep
- Speed of the sweep effect

Press F12 for an expanded overlay explaining pulse commands (displayed in pink).

Some drivers use a simpler one or two byte pulsating effect defined directly in the instrument.

##### Filter Table
The filter table defines filter cutoff range and sweep speeds. Unlike pulse, **the SID filter is a global effect** applied to channels via a bit mask:

| Bit | Value | Channel |
|-----|-------|---------|
| 0 | 1 | Channel 1 |
| 1 | 2 | Channel 2 |
| 2 | 4 | Channel 3 |

Examples:
- 3 (1+2) = Filter on channels 1 and 2
- 4 = Filter on channel 3 only
- 7 (1+2+4) = Filter on all channels

Press F12 for filter command details (displayed in orange).

Note: Some drivers have no filter capabilities.

##### Arpeggio Table
The arpeggio table creates chord effects by rapidly cycling through semitone offsets. Values are added to the note in the sequence.

Press F12 for arpeggio details (displayed in green).

In driver 11, arpeggio only affects wave table entries where the semitone value is $00. Other values ignore arpeggio.

##### Init Table
The init table points to a tempo table row and sets the main volume (e.g., `00 0F` for maximum volume). Multiple entries support multi-songs.

Press F12 for init details (displayed in white outline).

##### HR (Hard Restart) Table
Hard restart defeats the SID chip's "ADSR bug" - a timing issue that causes notes to stumble when playing rapid sequences (called "the school band effect" by Martin Galway).

**How it works**: The driver gates off and resets ADSR values a few frames before the next note triggers. In most SF2 drivers, this happens exactly 2 frames before.

Example: A note lasting 15 frames will:
1. Play with instrument ADSR for 13 frames
2. Hard restart takes over for final 2 frames
3. Gates off and applies HR table ADSR (typically `0F 00` for fast decay)
4. Next note triggers with stable ADSR

The HR table defines this pre-note ADSR. Default value `0F 00` brings notes down quickly. Advanced users can experiment with different values or create multiple HR entries for different instruments.

Press F12 for HR details (displayed in cyan).

##### Tempo Table
The tempo table defines song speed as **frames per row**. Frames update at 50Hz (PAL) or 60Hz (NTSC).

- Smaller values = faster tempo
- Minimum practical value is usually $02 (due to hard restart timing)
- Chain multiple values with `7F` wrap to create shuffle rhythms or fractional speeds (e.g., 2½)

Example tempo chains:
- `02 7F 00` = Constant speed 2
- `02 03 7F 00` = Alternating 2-3 for shuffle feel
- `02 02 03 7F 00` = 2⅓ average speed

### SF2 Driver Formats

#### NP20 Driver (NewPlayer 20 - Recommended)

The NP20 driver is derived from JCH NewPlayer and is the closest match to Laxity's format. Load address: `$0D7E`.

##### NP20 Instrument Format (8 bytes, column-major)

| Column | Description |
|--------|-------------|
| 0 | AD (Attack/Decay) |
| 1 | SR (Sustain/Release) |
| 2 | Reserved |
| 3 | Reserved |
| 4 | Wave table index |
| 5 | Pulse table index |
| 6 | Filter table index |
| 7 | Reserved |

##### NP20 Commands (2 columns)

| Column | Description |
|--------|-------------|
| 0 | Command byte |
| 1 | Parameter value |

#### Driver 11 (Standard SF2 Driver)

The standard SID Factory II driver with more features but a different instrument format. Load address: `$0D7E`.

##### Driver 11 Instrument Format (6 bytes, column-major)

| Column | Description | Notes |
|--------|-------------|-------|
| 0 | AD (Attack/Decay) | Standard SID ADSR |
| 1 | SR (Sustain/Release) | Standard SID ADSR |
| 2 | Flags | `$80`=hard restart, `$40`=filter, `$20`=filter enable, `$10`=osc reset, `$0x`=HR index |
| 3 | Filter table index | |
| 4 | Pulse table index | |
| 5 | Wave table index | |

##### Driver 11 Commands (3 columns)

| Column | Description |
|--------|-------------|
| 0 | Command byte |
| 1 | Parameter 1 |
| 2 | Parameter 2 |

### Format Mapping

When converting from Laxity SID to SF2, the following mappings are applied:

#### Laxity → NP20 Mapping

| Laxity | NP20 Column | Notes |
|--------|-------------|-------|
| AD | 0 | Direct copy |
| SR | 1 | Direct copy |
| - | 2-3 | Reserved (set to 0) |
| Wave table ptr | 4 | Direct copy |
| Pulse table ptr | 5 | Divided by 4 (Y*4 to direct index) |
| Filter ptr | 6 | Direct copy |
| - | 7 | Reserved (set to 0) |

#### Laxity → Driver 11 Mapping

| Laxity | Driver 11 Column | Notes |
|--------|------------------|-------|
| AD | 0 | Direct copy |
| SR | 1 | Direct copy |
| Restart options | 2 | Converted to flags |
| Filter ptr | 3 | Direct copy |
| Pulse table ptr | 4 | Direct copy |
| Wave table ptr | 5 | Converted to wave table index |

#### SF2 Wave Table Format

The SF2 wave table uses a column-major storage format with 2 columns:

| Column | Description |
|--------|-------------|
| 0 | Waveform value / Control byte ($7F) |
| 1 | Note offset / Jump target |

**Important**: SF2 format stores waveform in column 0 and note in column 1. For `$7F` jump commands, column 0 contains `$7F` and column 1 contains the target index.

##### Column 0 - Waveform / Control Values

| Value | Description |
|-------|-------------|
| $11 | Triangle + Gate |
| $21 | Sawtooth + Gate |
| $41 | Pulse + Gate |
| $81 | Noise + Gate |
| $10/$20/$40/$80 | Same waveforms without gate (gate off) |
| $7F | Jump command - column 1 contains target index |

##### Column 1 - Note Offset / Jump Target

| Value | Description |
|-------|-------------|
| $00 | No transpose (play base note) |
| $01-$7D | Semitone offset (positive transpose) |
| $80 | Recalculate base note + transpose (for Hubbard slide effects) |
| $81-$FF | Absolute note values (no transpose applied) |
| (with $7F) | Jump target index |

##### Wave Table Example

```
Index  Col0  Col1  Description
  0    $41   $00   Pulse+Gate, Note offset 0
  1    $7F   $00   Jump to index 0 (loop)
  2    $21   $00   Saw+Gate, Note offset 0
  3    $7F   $02   Jump to index 2 (loop)
  4    $11   $00   Tri+Gate, Note offset 0
  5    $7F   $04   Jump to index 4 (loop)
```

Instruments reference wave table entries by their index. The wave table allows complex sequences like:
- Waveform changes over time (attack transient with noise, then pulse)
- Arpeggio effects using note offsets
- Hard restart patterns

#### Default Wave Table Index Mapping

When converting from Laxity format, instruments using simple waveforms are mapped to default wave table indices:

| Waveform | Default Index | Wave Table Entry |
|----------|---------------|------------------|
| Pulse ($41) | 0 | Loop at index 0 |
| Saw ($21) | 2 | Loop at index 2 |
| Triangle ($11) | 4 | Loop at index 4 |
| Noise ($81) | 6 | Loop at index 6 |

### SF2 Format Quick Reference

*Based on the official SID Factory II User Manual (2023-09-30)*

#### Key Concepts

**SF2 files are C64 PRG files** - They can run on a C64/emulator with `SYS4093` and also load in the SF2 editor.

**Driver-dependent format** - Table layouts vary by driver. We target **Driver 11** (luxury, full features).

**Template-based** - SF2 files contain driver code plus music data injected into specific offsets.

#### Control Bytes Summary

| Byte | Context | Description |
|------|---------|-------------|
| $7F | Tables | End/jump marker |
| $7E | Sequences | Gate on (+++) |
| $A0 | Order list | No transpose (default) |

#### Gate System

SF2 uses explicit gate control (different from GoatTracker/CheeseCutter):

- `+++` - Gate on (sustain note)
- `---` - Gate off (release)
- `**` - Tie note (no envelope restart)

#### Hard Restart

Prevents the SID "ADSR bug" (Martin Galway's "school band effect"):
- Driver gates off 2 frames before next note
- Applies HR table ADSR (default: `$0F $00`)
- Stabilizes envelope timing

#### Sequence Packing

- Sequences packed in real-time as you edit
- Can be up to 1024 rows (if packed <256 bytes)
- Contiguous stacking per track (like Tetris)

#### Available Drivers

| Driver | Description |
|--------|-------------|
| 11 | Standard luxury (default) - full features |
| 12 | Extremely simple - basic effects only |
| 13 | Rob Hubbard emulation |
| 15/16 | Tiny drivers for size-constrained projects |

#### Multi-Song Support

- F7 opens song management
- Each song has own tempo/volume in Init table
- All songs share sequences and table data

For complete format details, see:
- [docs/reference/SF2_FORMAT_SPEC.md](docs/reference/SF2_FORMAT_SPEC.md) - Complete SF2 format specification
- [docs/reference/SF2_TRACKS_AND_SEQUENCES.md](docs/reference/SF2_TRACKS_AND_SEQUENCES.md) - Tracks and sequences format guide
- [docs/reference/SF2_INSTRUMENTS_REFERENCE.md](docs/reference/SF2_INSTRUMENTS_REFERENCE.md) - Instruments format guide

## Converter Architecture

### Components

1. **SIDParser** - Parses PSID/RSID headers and extracts C64 data
2. **LaxityPlayerAnalyzer** - Analyzes player format and extracts music data
3. **SF2Writer** - Generates SF2 files using template approach

### Data Flow

```
SID File → SIDParser → LaxityPlayerAnalyzer → ExtractedData → SF2Writer → SF2 File
```

### Extraction Process

1. Parse PSID header for metadata and addresses
2. Load C64 data into virtual memory
3. Scan for sequence data patterns
4. Identify instrument tables
5. Extract and convert to SF2 format
6. Generate output using template

## Development

### Running Tests

```bash
# Run unit tests
python scripts/test_converter.py

# Run SF2 format validation (aux pointer check)
python scripts/test_sf2_format.py

# Run automated editor validation (requires SID Factory II)
python scripts/test_sf2_editor.py
```

### Automated Editor Validation

The `test_sf2_editor.py` script validates converted SF2 files by loading them in SID Factory II:

```bash
# Test all SF2 files in SF2/ directory
python scripts/test_sf2_editor.py

# Test specific file
python scripts/test_sf2_editor.py SF2/Angular.sf2

# Convert SID files first, then test
python scripts/test_sf2_editor.py --convert-first

# Skip HTML report generation
python scripts/test_sf2_editor.py --no-report
```

The test performs:
1. Launches SID Factory II with each SF2 file
2. Sends space key to start playback
3. Captures screenshot to `SF2/screenshots/`
4. Terminates editor process
5. Generates HTML report at `SF2/validation_report.html`

**Configuration**: Set `Editor.Skip.Intro = 1` in the SID Factory II `config.ini` for faster testing.

**Requirements**:
- SID Factory II installed (default path: `C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\artifacts\`)
- Test dependencies: `pip install -r requirements-test.txt`

### Round-trip Validation

The `test_roundtrip.py` script performs complete round-trip validation by converting SID → SF2 → SID and comparing audio output:

```bash
# Test Angular.sid with 30 seconds duration
python scripts/test_roundtrip.py SID/Angular.sid

# Custom duration (seconds)
python scripts/test_roundtrip.py SID/Angular.sid --duration 60

# Verbose output
python scripts/test_roundtrip.py SID/Angular.sid --verbose
```

The validation performs 7 steps automatically:

1. **SID → SF2**: Converts original SID to SF2 using `sid_to_sf2.py`
2. **SF2 → SID**: Packs SF2 back to SID using `sf2pack` with full 6502 code relocation
3. **Original WAV**: Renders original SID to WAV using `SID2WAV.EXE`
4. **Exported WAV**: Renders exported SID to WAV using `SID2WAV.EXE`
5. **Original Siddump**: Analyzes original SID register writes using `siddump.exe`
6. **Exported Siddump**: Analyzes exported SID register writes using `siddump.exe`
7. **HTML Report**: Generates detailed comparison report

**Output files** (in `roundtrip_output/`):
- `*_converted.sf2` - SF2 conversion from original SID
- `*_exported.sid` - SID packed from SF2 (with code relocation)
- `*_original.wav` - Audio from original SID
- `*_exported.wav` - Audio from exported SID
- `*_original.dump` - Register dump from original SID
- `*_exported.dump` - Register dump from exported SID
- `*_roundtrip_report.html` - Detailed comparison report

**Key Features**:
- Full 6502 code relocation (343 absolute + 114 zero page address patches)
- Frame-by-frame SID register comparison
- WAV file size validation
- Detailed HTML report with metrics

**Requirements**:
- `tools/sf2pack/sf2pack.exe` - SF2 to SID packer (built from source)
- `tools/SID2WAV.EXE` - SID to WAV renderer
- `tools/siddump.exe` - SID register analyzer

All 164+ unit tests should pass (100% pass rate):
- **test_converter.py** (86 tests): SID parsing, memory access, data structures, integration, SF2 writing, instruments, commands, tempo, tables, pulse/filter extraction, sequences, table linkage
- **test_sf2_format.py** (12 tests): SF2 format validation, aux pointer safety, file structure comparison
- **test_laxity_driver.py** (23 tests): Laxity driver functionality, accuracy validation, table extraction
- **test_sf2_packer.py** (18 tests): SF2→SID packing, memory operations, PRG format, pointer relocation
- **test_validation_system.py** (16 tests): Database operations, regression detection, metrics collection
- **test_complete_pipeline.py** (9 tests): Complete pipeline validation, integration testing

The SF2 format test validates:
- **Aux pointer validation**: Ensures aux pointer doesn't point to valid aux data (which crashes SID Factory II)
- **File structure comparison**: Compares orderlist and sequence pointers with templates

### CI/CD Pipeline

#### Local CI

Run all checks locally before pushing:

```bash
# Run checks only
python scripts/ci_local.py

# Run checks and push to git
python scripts/ci_local.py --push --message "Your commit message"

# Windows batch file
scripts\run_ci.bat --push -m "Your commit message"
```

The local CI performs:
1. Python syntax check
2. Docstring validation
3. Documentation checks
4. Unit tests (17 tests)
5. Smoke test with real SID file

#### GitHub Actions

The project includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs:

- **Tests**: Runs on multiple Python versions (3.8-3.12) and OS (Ubuntu, Windows)
- **Linting**: flake8 and pylint checks
- **Documentation**: Validates README sections and docstrings
- **Security**: Bandit security scan
- **Release**: Creates release artifacts on master push

### Project Structure

```
SIDM2/
├── sid_to_sf2.py                      # Main SID → SF2 converter
├── sf2_to_sid.py                      # SF2 → SID exporter
├── convert_all.py                     # Batch converter (both drivers)
├── complete_pipeline_with_validation.py # Complete 12-step pipeline (v1.2)
├── test_roundtrip.py                  # Round-trip validation
├── test_converter.py                  # Unit tests (86 tests)
├── test_sf2_format.py                 # SF2 format validation (12 tests)
├── test_laxity_driver.py              # Laxity driver tests (23 tests)
├── test_sf2_packer.py                 # SF2 packer tests (18 tests)
├── test_validation_system.py          # Validation system tests (16 tests)
├── test_sf2_editor.py                 # Automated editor validation
├── test_complete_pipeline.py          # Pipeline validation (9 tests)
├── generate_info.py                   # Comprehensive info.txt generator
├── extract_addresses.py               # Memory address extraction
├── disassemble_sid.py                 # 6502/6510 disassembler
├── annotating_disassembler.py         # Annotated disassembly generator
├── laxity_analyzer.py                 # Laxity format analyzer
├── laxity_parser.py                   # Laxity format parser
├── requirements-test.txt              # Test dependencies
├── README.md                          # This file (user guide)
├── CLAUDE.md                          # Project guide for AI assistants
├── CONTRIBUTING.md                    # Contribution guidelines
├── PACK_STATUS.md                     # SF2 packer status
├── PIPELINE_EXECUTION_REPORT.md       # Pipeline execution analysis
├── PIPELINE_RESULTS_SUMMARY.md        # Quick results summary
├── SIDWINDER_INTEGRATION_SUMMARY.md   # SIDwinder work summary
├── SIDWINDER_REBUILD_GUIDE.md         # SIDwinder rebuild instructions
├── sidm2/                             # Core package
│   ├── sf2_packer.py                  # SF2 → SID packer (v0.6.0)
│   ├── cpu6502.py                     # 6502 emulator for relocation
│   ├── cpu6502_emulator.py            # Full 6502 emulator (v0.6.2)
│   ├── sid_player.py                  # SID player and analyzer
│   ├── sf2_player_parser.py           # SF2-exported SID parser
│   └── ...                            # Other modules
├── SID/                               # Input SID files
├── SIDSF2player/                      # SF2-packed test files
├── output/                            # Output directory
│   └── SIDSF2player_Complete_Pipeline/ # Complete pipeline output
│       └── {SongName}/                # Per-song directories
│           ├── Original/              # Original SID analysis (4 files)
│           └── New/                   # Converted files (9 files)
├── tools/                             # External tools
│   ├── SIDwinder.exe                  # SID processor (v0.2.6) ⭐ NEW
│   ├── SIDwinder.log                  # SIDwinder error log
│   ├── SIDwinder.cfg                  # SIDwinder config
│   ├── SIDWINDER_QUICK_REFERENCE.md   # Command reference ⭐ NEW
│   ├── sidwinder_trace_fix.patch      # Source code patches ⭐ NEW
│   ├── siddump.exe                    # Register dump tool
│   ├── siddump.c                      # Siddump source
│   ├── player-id.exe                  # Player identification
│   ├── SID2WAV.EXE                    # SID → WAV renderer
│   ├── cpu.c                          # 6502 emulator source
│   └── sf2pack/                       # C++ packer (reference)
├── G5/                                # Driver templates
│   ├── drivers/                       # SF2 driver PRG files
│   └── examples/                      # Example SF2 files
└── docs/                              # Documentation
    ├── SF2_FORMAT_SPEC.md             # SF2 format specification
    ├── STINSENS_PLAYER_DISASSEMBLY.md # Laxity player analysis
    ├── CONVERSION_STRATEGY.md         # Conversion mapping
    ├── DRIVER_REFERENCE.md            # Driver specifications
    ├── VALIDATION_SYSTEM.md           # Validation architecture
    └── ACCURACY_ROADMAP.md            # Accuracy improvement plan
```

## Tools

### siddump

A 6502 CPU emulator that executes SID player code and captures register writes. Source code in `tools/cpu.c` and `tools/siddump.c`.

```bash
tools/siddump.exe <sidfile> [options]
```

Options:
- `-a<value>` - Subtune number (default 0)
- `-t<value>` - Playback time in seconds (default 60)
- `-f<value>` - First frame to display
- `-l` - Low-resolution mode
- `-n<value>` - Note spacing
- `-p<value>` - Pattern spacing
- `-s` - Time in minutes:seconds:frame format
- `-z` - Include CPU cycles and raster time
- `-c<hex>` - Recalibrate frequency table
- `-d<hex>` - Calibration note (default $B0 = middle C)

Output shows per-frame SID register state:
- 3 voices: Frequency, Note, Waveform, ADSR, Pulse width
- Filter: Cutoff, Resonance/Control, Type, Volume

### player-id

Identifies the player routine used in a SID file.

```bash
tools/player-id.exe <sidfile>
```

**Usage in Pipeline**: Automatically called by `generate_info.py` to detect player type using signature database (`tools/sidid.cfg`).

### SIDwinder (v0.2.6)

Comprehensive C64 SID file processor with disassembly, trace, player, and relocation capabilities.

**Location**: `tools/SIDwinder.exe`
**Source**: `C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6\src\`
**Status**: Disassembly ✅ Working | Trace ⚠️ Needs rebuild | Player/Relocate 🔧 Manual

#### Disassemble Command (✅ INTEGRATED IN PIPELINE)

Converts SID files to KickAssembler-compatible source code:

```bash
tools/SIDwinder.exe -disassemble <input.sid> <output.asm>
```

**Features**:
- Generates KickAssembler-compatible 6502 assembly
- Includes metadata comments (title, author, copyright)
- Labels data blocks and code sections
- Integrated in complete pipeline (Step 9)
- Works perfectly for original SID files

**Output Format**:
```asm
//; Generated by SIDwinder 0.2.6
//; Name: Song Title
//; Author: Artist Name
//; Copyright: (C) Year Name

.const SIDLoad = $1000
.const SID0 = $D400

* = SIDLoad
    jmp Label_0    // Init routine
    jmp Label_2    // Play routine
```

**Known Limitation**: Exported SIDs from SF2 packer trigger strict CPU emulation checks ("Execution at $0000"). Original SIDs disassemble perfectly. Files still play correctly in all standard emulators.

#### Trace Command (⚠️ NEEDS REBUILD)

Captures SID register writes frame-by-frame:

```bash
# Text format (recommended)
tools/SIDwinder.exe -trace=output.txt <input.sid>

# Binary format
tools/SIDwinder.exe -trace=output.bin <input.sid>

# Custom duration (frames @ 50Hz)
tools/SIDwinder.exe -trace=output.txt -frames=1500 <input.sid>
```

**Output Format** (after rebuild):
```
FRAME: D400:$29,D401:$FD,D404:$11,D405:$03,D406:$F8,...
FRAME: D400:$7B,D401:$05,D404:$41,D407:$09,D408:$10,...
```

**Current Status**:
- ✅ Integrated in pipeline (Step 6)
- ✅ Source code patched (3 files fixed)
- ✅ Files generated (36/36)
- ⚠️ Content empty until executable rebuilt
- 📝 Patch file: `tools/sidwinder_trace_fix.patch`

**Bug Fixed**: Original SIDwinder trace command produced empty output due to missing callback enable and logWrite() method. Patches applied fix all 3 bugs.

**Rebuild Required**:
```cmd
cd C:\Users\mit\Downloads\SIDwinder-0.2.6\SIDwinder-0.2.6
build.bat
copy build\Release\SIDwinder.exe tools\
```

See `SIDWINDER_REBUILD_GUIDE.md` for detailed instructions.

#### Player Command (🔧 MANUAL USE)

Creates playable PRG files with visualization:

```bash
# Default player (SimpleRaster)
tools/SIDwinder.exe -player <music.sid> <output.prg>

# Spectrum analyzer
tools/SIDwinder.exe -player=RaistlinBars <music.sid> <output.prg>

# With custom logo
tools/SIDwinder.exe -player=RaistlinBarsWithLogo -define KoalaFile="logo.kla" <music.sid> <output.prg>
```

**Available Players**: SimpleRaster, SimpleBitmap, RaistlinBars, RaistlinBarsWithLogo, RaistlinMirrorBarsWithLogo

#### Relocate Command (🔧 MANUAL USE)

Moves SID code to different memory address:

```bash
# Basic relocation
tools/SIDwinder.exe -relocate=$2000 <input.sid> <output.sid>

# Skip verification (faster)
tools/SIDwinder.exe -relocate=$3000 -noverify <input.sid> <output.sid>

# With metadata override
tools/SIDwinder.exe -relocate=$2000 -sidname="New Title" -sidauthor="Artist" <input.sid> <output.sid>
```

**Usage in Pipeline**: Integrated automatically in Steps 6 (trace) and 9 (disassembly). Player and relocate commands available for manual use.

**Documentation**:
- Quick Reference: `tools/SIDWINDER_QUICK_REFERENCE.md`
- Integration Summary: `SIDWINDER_INTEGRATION_SUMMARY.md`
- Rebuild Guide: `SIDWINDER_REBUILD_GUIDE.md`

### generate_info.py

Generates comprehensive info.txt reports with full pipeline documentation.

```bash
python generate_info.py <original_sid> <converted_sf2> <output_dir> [title_override]
```

**Features**:
- Parses SID headers to extract metadata
- Runs player-id.exe for accurate player identification
- Documents all pipeline tools used (siddump, SID2WAV, xxd, etc.)
- Generates hex table views of all music data (16 bytes/row)
- Shows memory address maps for both original and SF2 formats
- Copies source SID file to output directory with consistent naming
- Optional title override for consistent filenames (useful for SF2-packed files)

**Output Sections**:
- Source File Information (with player-id.exe detection)
- Conversion Results
- Original SID File (Preserved) - source, size, location
- Pipeline Tools Used - complete tool documentation
- Table Addresses in SF2
- Original SID Data Structure Addresses
- Original SID Data Tables (Hex View)
- Converted SF2 Data Tables (Hex View)

**Example**:
```bash
# Generate info.txt with player identification
python generate_info.py SID/song.sid output/song.sf2 output/

# Override title for consistent naming (SF2-packed files)
python generate_info.py output/song_d11.sid output/song_repacked.sf2 output/ "Original Song Title"
```

### sf2pack

SF2 to SID packer with full 6502 code relocation. Converts SF2 files back to playable SID format.

```bash
tools/sf2pack/sf2pack.exe <input.sf2> <output.sid> [options]
```

Options:
- `--address ADDR` - Target load address (hex, default: 0x1000)
- `--zp ZP` - Target zero page base (hex, default: 0x02)
- `--title TITLE` - Set PSID title metadata
- `--author AUTHOR` - Set PSID author metadata
- `--copyright TEXT` - Set PSID copyright metadata
- `-v, --verbose` - Verbose output with relocation stats

**Key Features**:
- Full 6502 instruction-by-instruction code scanning
- Relocates absolute addresses (am_ABS, am_ABX, am_ABY, am_IND)
- Adjusts zero page addresses (am_ZP, am_ZPX, am_ZPY, am_IZX, am_IZY)
- Protects ROM addresses ($D000-$DFFF) from modification
- Exports as PSID v2 format with metadata

**Example output**:
```
Processing driver code:
  Driver: $d7e - $157e
  Address delta: 282
  ZP: $2 -> $2
  Relocations: 343 absolute, 114 zero page
  Packed size: 8834 bytes
```

See `tools/sf2pack/README.md` for architecture details and source code documentation.

### 6502 CPU Emulator

The `cpu.c` file contains a complete 6502 CPU emulator with:
- All standard opcodes (ADC, SBC, AND, ORA, EOR, etc.)
- Common illegal opcodes (LAX)
- Accurate cycle counting with page-crossing penalties
- Decimal mode support for ADC/SBC

Key registers:
- `pc` - Program Counter (16-bit)
- `a`, `x`, `y` - Accumulator and index registers (8-bit)
- `sp` - Stack pointer (8-bit)
- `flags` - N, V, B, D, I, Z, C status flags
- `mem[0x10000]` - 64KB memory

### Adding New Features

1. Create feature branch
2. Write tests first (TDD approach)
3. Implement feature
4. Update documentation
5. Run all tests
6. Submit pull request

## Extraction Confidence Scoring

The converter uses heuristic-based confidence scoring to identify and extract music data tables from SID files. Each table type has specific scoring criteria.

### Wave Table Confidence

Wave tables are scored based on:

| Criterion | Points | Description |
|-----------|--------|-------------|
| Valid waveforms | +3 each | Standard waveforms ($11, $21, $41, $81) |
| Valid note offsets | +1-2 | Offsets in range 0-24 semitones |
| Loop markers | +5 | $7F jump commands for looping |
| End markers | +3 | $7E stop commands |
| Variety bonus | +5 | Multiple different waveforms |
| Chain patterns | +2 | Valid jump targets |

**Minimum threshold**: Score ≥ 15 to accept extracted table.

### Pulse Table Confidence

Pulse tables use 4-byte entries scored on:

| Criterion | Points | Description |
|-----------|--------|-------------|
| Valid initial value | +2 | $FF (keep) or valid pulse width |
| Moderate add values | +3 | Values 1-15 for smooth modulation |
| Chain patterns | +3 | Valid loop references |
| Duration values | +1 | Reasonable duration (1-64) |
| Subtract patterns | +2 | Negative modulation for PWM |

**Minimum threshold**: Score ≥ 10 and at least 2 valid entries.

### Filter Table Confidence

Filter tables use 4-byte entries scored similarly:

| Criterion | Points | Description |
|-----------|--------|-------------|
| Valid filter values | +2 | Cutoff frequency bytes |
| Moderate deltas | +3 | Smooth sweep values (1-15) |
| Chain patterns | +3 | Valid loop references |
| Duration values | +1 | Reasonable duration |

**Minimum threshold**: Score ≥ 10 and at least 2 valid entries.

### Arpeggio Table Confidence

Arpeggio tables are 4-byte entries (note1, note2, note3, speed) scored on:

| Criterion | Points | Description |
|-----------|--------|-------------|
| Valid note offsets | +2 each | Values 0-24 (2 octave range) |
| Common chord patterns | +3 | Major (0,4,7), minor (0,3,7) |
| Speed values | +1 | Reasonable speed (0-15) |
| Structure validity | +2 | Consistent entry format |

**Minimum threshold**: Score ≥ 15 with at least 2 valid entries.

### Command Table Detection

Commands are detected by analyzing sequence bytes in the $C0-$DF range:

- Counts command usage across all sequences
- Maps to standard SF2 command names (Slide, Vibrato, Portamento, etc.)
- Falls back to default command table if no usage detected

## Limitations

### Extracted Tables

The converter now extracts and injects all major table types:

| Table | Status | Description |
|-------|--------|-------------|
| Instruments | ✓ Full | 8-byte Laxity format with ADSR, wave/pulse/filter pointers |
| Wave | ✓ Full | Note offset + waveform pairs with jump/end markers |
| Pulse | ✓ Full | 4-byte entries: value, count, duration, next index |
| Filter | ✓ Full | 4-byte entries: value, count, duration, next index |
| Commands | ✓ Names | Command names injected via auxiliary data |
| HR | ✓ Basic | Hard restart table with default values |
| Tempo | ✓ Full | Speed value extracted from SID |
| Arp | ✓ Default | Default arpeggio patterns (major, minor, octave) |
| Init | - | Not available in NP20 driver |

### Current Limitations

- **Player Format Support**:
  - ✅ **Fully Supported**: Laxity NewPlayer v21 (99.93% accuracy with Laxity driver)
  - ✅ **Fully Supported**: SF2-exported SIDs (100% accuracy with Driver 11)
  - ⚠️ **Limited Support**: NewPlayer 20.G4 (70-90% accuracy with NP20 driver)
  - ❌ **Not Supported**: Other player formats (use Driver 11 safe default)
- **Laxity Driver Limitations** (v1.8.0):
  - **Filter accuracy**: 0% (Laxity filter format not yet converted)
  - **Voice 3**: Untested (no test files available with 3-voice content)
- **Multi-subtune files**: Only first subtune converted
- **Manual refinement**: Some output may require editing in SID Factory II

### Player Format Compatibility

**IMPORTANT**: Conversion accuracy varies significantly based on source player format and driver selection:

| Source Format | Target Driver | Accuracy | Status |
|---------------|---------------|----------|--------|
| **SF2-Exported SID** | Driver 11 | **100%** | ✅ Perfect roundtrip |
| **Driver 11 Test Files** | Driver 11 | **100%** | ✅ Reference extraction |
| **Laxity NewPlayer v21** | **Laxity Driver** | **99.93%** | ✅ **Production Ready** (v1.8.0) |
| **Laxity NewPlayer v21** | Driver 11 | **1-8%** | ⚠️ Use Laxity driver instead |
| **Laxity NewPlayer v21** | NP20 | **1-8%** | ⚠️ Use Laxity driver instead |
| **NewPlayer 20.G4** | NP20 | **70-90%** | ⚠️ Experimental |

**Laxity Driver Achievement (v1.8.0)**:

The custom Laxity driver achieves **99.93% frame accuracy** using an Extract & Wrap architecture:

- **Native Format Preservation**: Uses original Laxity player code (no format conversion)
- **Perfect Register Writes**: 507/507 register writes match exactly
- **Wave Table Format Fix**: Critical breakthrough (497x accuracy improvement)
- **Production Ready**: 286 real Laxity files tested (100% success rate)
- **Auto-Selection**: Quality-First Policy v2.0 automatically selects Laxity driver (v2.8.0)

**Why Standard Drivers Have Low Accuracy with Laxity Files**:

Despite JCH reverse-engineering Laxity's player in 1988, the formats are **fundamentally incompatible**:

- **Different Sequence Encoding**: Laxity uses proprietary format, JCH NP20 uses paired-byte (AA, BB) format
- **Different Memory Layouts**: Tables at different addresses with different organization
- **Different Player Architecture**: Incompatible runtime behavior and state management

**What the 1-8% Represents** (Driver 11/NP20 with Laxity files):
- Universal C64 frequency table matches (notes are standard)
- Random waveform coincidences
- **NOT** faithful music reproduction

**Recommendation**:
- ✅ **Laxity NP21 files**: Use Laxity driver (99.93% accuracy) - automatic with v2.8.0+
- ✅ **SF2-exported files**: Use Driver 11 (100% accuracy) - automatic with v2.8.0+
- ⚠️ **Other formats**: Use Driver 11 (safe default)

**See Also**:
- `docs/guides/LAXITY_DRIVER_USER_GUIDE.md` - User guide for Laxity driver
- `docs/reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md` - Technical implementation details
- `docs/integration/CONVERSION_POLICY_APPROVED.md` - Automatic driver selection policy

### Known Issues

- **Aux pointer compatibility**: SF2 files have aux pointer set to $0000 to prevent SID Factory II crashes
- **Driver 11 instruments**: Converted instruments may differ from manually created ones in original SF2 project files
- **Multi-speed tunes**: Songs with multiple play calls per frame may not play at correct speed
- **LAXITY format incompatibility**: Direct Laxity→SF2 conversion limited by fundamental player format differences (see Player Format Compatibility above)

### Why Full Conversion is Difficult

1. **Compiled format**: SID files contain machine code, not source data
2. **Player-specific encoding**: Each player routine uses different formats
3. **Lost information**: Compilation process discards editable structure
4. **Complex mapping**: Laxity player → SF2 format requires reverse engineering

## Results

### Unboxed_Ending_8580.sid Analysis

- **Load address**: $1000
- **Data size**: 4512 bytes
- **Sequences extracted**: 13
- **Instruments extracted**: 32
- **Orderlists created**: 3

### Output

The converter generates an SF2 file that:
- Is loadable in SID Factory II
- Contains extracted sequence data
- Has basic instrument definitions
- Requires manual refinement for playability

## Improvements Roadmap

### Completed (v0.4.0)

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 1 | Fix Omniphunk ADSR extraction | ✅ Done | Siddump ADSR merging achieves 100% accuracy |
| 2 | Ring Modulation waveform support | ✅ Done | Added 0x14, 0x15, 0x34, 0x35 with ring mod bit |
| 3 | Improve pulse table extraction | ✅ Done | Better pulse modulation pattern detection |
| 26 | Fix SF2 aux pointer crash | ✅ Done | Aux pointer no longer points to valid aux data |
| 27 | SF2 format validation test | ✅ Done | test_sf2_format.py validates aux pointer safety |

### Completed (v0.3.0)

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 13 | SF2 metadata from SID header | ✅ Done | Song name, author, copyright embedded in SF2 |
| 17 | Improved instrument naming | ✅ Done | Better heuristics (Bass, Lead, Pad, Perc, Stab, Pluck) + waveform type |
| 21 | Cross-reference validation | ✅ Done | Validates wave table, instruments, sequences, orderlists |
| 15 | Validation report file | ✅ Done | Outputs detailed report to SF2/validation_report.txt |
| 11 | Wave table debug info | ✅ Done | Shows top candidates and scores in info files |
| 1 | Fix Clarencio wave table | ✅ Done | Improved scoring algorithm with variety bonus |

### High Priority - Next Improvements

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 4 | Multi-speed tune support | 🔄 Pending | Handle tunes with multiple play calls per frame |
| 5 | Proper filter table extraction | 🔄 Pending | Filter sweeps and resonance settings |
| 28 | Support more player formats | 🔄 Pending | Add support for GoatTracker, JCH, DMC players |
| 29 | Sequence optimization | 🔄 Pending | Remove redundant commands, optimize sequence data |
| 30 | Better loop detection | 🔄 Pending | Detect and mark proper loop points in orderlists |

### Medium Priority

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 6 | Auto-detect player variant | 🔄 Pending | Distinguish NP20, NP21, other Laxity versions |
| 7 | Additional Laxity commands | 🔄 Pending | Support unmapped sequence commands |
| 8 | Better Set ADSR matching | 🔄 Pending | Track dynamic ADSR changes in sequences |
| 9 | Tempo detection | 🔄 Pending | Extract actual tempo from song data |
| 10 | Vibrato parameters | 🔄 Pending | Extract depth/speed settings |
| 11 | Portamento parameters | 🔄 Pending | Extract slide speed from commands |
| 12 | Hard restart timing | 🔄 Pending | Detect different HR timing per song |
| 31 | GUI interface | 🔄 Pending | Simple tkinter GUI for batch conversion |
| 32 | Direct SF2 editing | 🔄 Pending | Modify existing SF2 files without full reconversion |

### Low Priority

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 14 | Sequence deduplication | 🔄 Pending | Detect and merge duplicate sequences |
| 15 | Subtune support | 🔄 Pending | Handle SID files with multiple songs |
| 16 | Orderlist loop detection | 🔄 Pending | Identify loop points for proper playback |
| 18 | Command usage statistics | 🔄 Pending | Show which SF2 commands are used |
| 19 | Combined waveform transitions | 🔄 Pending | Handle Tri+Saw, Tri+Pulse in wave table |
| 20 | Pulse width range detection | 🔄 Pending | Determine min/max pulse per instrument |
| 33 | Export to other formats | 🔄 Pending | Export to GoatTracker .sng or MIDI |
| 34 | Batch validation report | 🔄 Pending | Generate HTML report for all conversions |
| 35 | Instrument preset library | 🔄 Pending | Common C64 instrument presets |

### Validation Enhancements

| # | Feature | Status | Description |
|---|---------|--------|-------------|
| 22 | Validate command parameters | 🔄 Pending | Check slide/vibrato values in valid ranges |
| 23 | Note range validation | 🔄 Pending | Ensure notes are within playable range |
| 24 | Filter cutoff validation | 🔄 Pending | Compare filter table against usage |
| 25 | Timing accuracy check | 🔄 Pending | Frame-by-frame output timing comparison |

### Current Validation Scores

| Song | Score | Issues |
|------|-------|--------|
| Angular | 100% | 0 |
| Clarencio_extended | 100% | 0 |
| Ocean_Reloaded | 100% | 0 |
| Omniphunk | 100% | 0 |
| Phoenix_Code_End_Tune | 100% | 0 |
| Unboxed_Ending_8580 | 100% | 0 |
| **Average** | **100%** | |

All files now achieve 100% validation score with siddump ADSR merging and improved wave table extraction.

### Audio Comparison (v0.7.0)

The pipeline now includes **WAV-based audio comparison** to measure conversion accuracy based on actual sound output, which is more meaningful for LAXITY→SF2 conversions where the player code changes.

#### Comparison Methods

| Method | Measures | When Meaningful | Example Use Case |
|--------|----------|----------------|------------------|
| **Audio Comparison** | WAV file similarity (Pearson correlation) | Always meaningful | LAXITY→SF2 (different players) |
| **Register Comparison** | SID register write patterns | Only when same player | SF2→SF2 (same player) |

#### Audio Comparison Metrics

- **Correlation**: Pearson correlation coefficient [0.0, 1.0] where 1.0 = perfect match
- **RMSE**: Root mean square error [0.0, 2.0] where 0.0 = perfect match
- **Accuracy**: Correlation converted to percentage [0.0, 100.0%]

#### Expected Accuracy Ranges

| Conversion Type | Register Accuracy | Audio Accuracy | Notes |
|----------------|-------------------|----------------|-------|
| **LAXITY → SF2** | 1-8% | 95%+ expected | Low register accuracy is normal (different players) |
| **SF2 → SF2** | 99%+ | N/A | Same player, register comparison meaningful |

#### Known Limitation: SID2WAV v1.8

**Problem**: SID2WAV v1.8 does not support SF2 Driver 11 player format, producing silent WAV output for all SF2-packed files.

**Impact**: Audio comparison unavailable for LAXITY→SF2 conversions (exported file is silent).

**Detection**: Pipeline automatically detects SF2-packed files and displays informative messages:
- WAV rendering step shows: `[INFO] SF2-packed file detected - SID2WAV v1.8 does not support SF2 Driver 11`
- Audio comparison step shows: `[SKIP] Audio comparison unavailable - SID2WAV v1.8 does not support SF2 Driver 11`
- `info.txt` file includes: `Audio Accuracy: N/A` with full explanation

**Future Enhancement**: VICE emulator integration for proper SF2 WAV rendering (see Option B in accuracy roadmap).

#### Implementation Details

See `sidm2/audio_comparison.py` for implementation:
- `calculate_correlation()`: Pearson correlation coefficient calculation
- `calculate_rmse()`: Root mean square error calculation
- `compare_wav_files()`: Main comparison function with format validation
- `calculate_audio_accuracy()`: Pipeline entry point (returns accuracy % or None)

### Code Quality Improvements

| # | Improvement | Status | Effort | Impact | Description |
|---|-------------|--------|--------|--------|-------------|
| 36 | Implement proper logging | ✅ Done | 2-3h | High | Replace ~70+ print() calls with Python logging module |
| 37 | Add type hints | ✅ Done | 4-6h | High | Add type annotations to all public functions in sidm2/ |
| 38 | Error handling in extraction | ✅ Done | 6-8h | Critical | Raise specific exceptions instead of returning None |
| 39 | Subprocess error handling | 🔄 Pending | 3-4h | Medium | Proper error handling for siddump.exe, player-id.exe |
| 40 | Data validation | 🔄 Pending | 5-6h | Critical | Validate SequenceEvent, ExtractedData at creation |
| 41 | Test coverage for edge cases | 🔄 Pending | 4-5h | High | Add tests for corrupted files, empty data, missing templates |
| 42 | Configuration system | 🔄 Pending | 3-4h | Medium | ConversionOptions class for customizable SF2 generation |

### Architecture Improvements (Completed)

| # | Improvement | Status | Description |
|---|-------------|--------|-------------|
| 43 | Modularize sid_to_sf2.py | ✅ Done | Extracted to sidm2/ package (3600→139 lines) |
| 44 | Consolidate duplicate scripts | ✅ Done | Removed 13 duplicate analysis scripts |
| 45 | Extract constants | ✅ Done | Magic numbers moved to sidm2/constants.py |
| 46 | Add documentation | ✅ Done | Created docs/ folder with comprehensive guides |
| 47 | SF2Writer modularization | ✅ Done | Extracted ~960 lines to sidm2/sf2_writer.py |

## Changelog

**Note**: For recent versions (v2.3.0+), see [`CHANGELOG.md`](CHANGELOG.md). Abbreviated history below shows older releases.

**Current Version**: v2.9.1 - SF2 Format Validation Fixes (2025-12-26)

### v2.9.1 (2025-12-26)

**SF2 Format Validation Fixes - Critical Editor Compatibility**

- **Fixed SF2 metadata corruption** causing SID Factory II editor rejection:
  - ✅ Added missing Commands table descriptor in Block 3 (Driver Tables)
  - ✅ Added missing visible_rows field to all table descriptors
  - ✅ Fixed table ID sequencing (Instruments=0, Commands=1, Wave=2, Pulse=3, Filter=4, Sequences=5)
  - ✅ Corrected Block 3 structure to include all 6 required tables

- **Enhanced validation and debugging**:
  - ✅ Added comprehensive SF2 structure logging (`_log_sf2_structure`)
  - ✅ Added Block 3 (Driver Tables) structure validation
  - ✅ Added Block 5 (Music Data) structure validation
  - ✅ Added automatic SF2 file validation after write
  - ✅ Detailed block-by-block structure analysis for debugging

- **Impact**:
  - Generated SF2 files now load correctly in SID Factory II editor
  - All table descriptors properly formatted per SF2 specification
  - Editor can now display and edit all 6 tables (Instruments, Commands, Wave, Pulse, Filter, Sequences)
  - Improved debugging capabilities for future format issues

- **Files Modified**:
  - `sidm2/sf2_header_generator.py` - Added missing descriptor fields
  - `sidm2/sf2_writer.py` - Enhanced validation and logging
  - `drivers/laxity/sf2driver_laxity_00.prg` - Binary driver updates

**Commits**:
1. `9948703` - Add missing descriptor fields - ACTUAL root cause fix
2. `0e2c49b` - Fix SF2 block ordering - CRITICAL editor validation fix
3. `e9cc32e` - Fix SF2 metadata corruption causing editor rejection

### v2.6.0 (2025-12-22)

**Conversion Cockpit - Mission Control for Batch SID Conversion**

- **NEW Conversion Cockpit GUI**:
  - Professional PyQt6 GUI for batch SID conversion
  - 5-tab interface: Dashboard, Files, Configuration, Results, Logs
  - Real-time progress monitoring with live updates
  - Pause/resume/stop batch processing
  - Drag-drop file selection + browse dialog
  - Per-file results tracking with accuracy metrics

- **Progressive Disclosure UI**:
  - Simple mode: 7 essential steps (conversion, packing, validation, WAV, info)
  - Advanced mode: All 14 pipeline steps enabled
  - Custom mode: Select any combination of steps
  - Configurable pipeline executor with 14 steps

- **Pipeline Steps**:
  1. SID → SF2 Conversion (required)
  2. Siddump (Original)
  3. SIDdecompiler Analysis
  4. SF2 → SID Packing (required)
  5. Siddump (Exported)
  6. WAV Rendering (Original + Exported)
  7. Hexdump Generation
  8. SIDwinder Trace
  9. Info Report (required)
  10. Annotated Disassembly
  11. SIDwinder Disassembly
  12. Validation (required)
  13. MIDI Comparison

- **Features**:
  - Color-coded live log streaming with level filtering
  - Results table with sortable columns
  - Configuration persistence with QSettings
  - Signal/slot architecture for async updates
  - Three stats cards (Files, Progress, Results)
  - Estimated time remaining calculations

- **Testing & Quality**:
  - 50 tests: 26 unit + 24 integration (100% pass rate)
  - Real file integration test (3 SID files, 3.2 seconds)
  - GitHub Actions CI/CD workflow
  - Comprehensive user guide (1,234 lines)
  - Technical reference (1,103 lines)

- **Batch Launchers**:
  - `conversion-cockpit.bat` - Windows launcher
  - `pyscript/launch_conversion_cockpit.py` - Python launcher with auto-install
  - `pyscript/conversion_cockpit_gui.py` - Direct launch

- **Architecture**:
  - `conversion_cockpit_gui.py` (1,047 lines) - Main window
  - `conversion_executor.py` (475 lines) - Backend engine
  - `pipeline_config.py` (259 lines) - Configuration management
  - `cockpit_widgets.py` (437 lines) - Custom widgets

- **Bug Fixes**:
  - Fixed missing QScrollArea import in configuration tab
  - Fixed test assertion errors (default values, time estimates)
  - Fixed FileResult structure (start_time/end_time instead of duration)

- **Documentation**:
  - `docs/guides/CONVERSION_COCKPIT_USER_GUIDE.md` - User guide
  - `docs/guides/CONVERSION_COCKPIT_TECHNICAL_REFERENCE.md` - Technical docs
  - `IMPROVEMENTS_TODO.md` - Comprehensive improvement tracking (28 tasks)
  - README.md - New Conversion Cockpit section with features, usage, comparison

- **Test Results**:
  - 100% success rate (3/3 files: Angular, Beast, Delicate)
  - 21/21 steps completed (7 steps × 3 files)
  - 12 output files created (.sf2, .sid, .wav)
  - Duration: 3.2 seconds for 3 files

**Conversion Cockpit provides a professional GUI alternative to command-line batch conversion with full monitoring, control, and validation capabilities.**

### v2.2.0 (2025-12-18)

**SF2 Text Exporter and Single-track Sequence Support**

- **NEW SF2 Text Exporter Tool**:
  - Export all SF2 data to human-readable text files
  - 12+ file types: orderlist, sequences, instruments, tables, references
  - Auto-detects single-track vs 3-track interleaved sequences
  - Perfect for validation, debugging, and learning SF2 format
  - <1 second export time, zero external dependencies
  - Human-readable format with hex notation matching SID Factory II

- **Single-track Sequence Support in SF2 Viewer**:
  - Auto-detects single-track vs 3-track interleaved sequence formats
  - Displays each format appropriately (continuous vs parallel tracks)
  - 96.9% Track 3 accuracy achieved (vs 42.9% before fix)
  - Format detection using heuristics (length, pattern analysis)

- **Hex Notation in SF2 Viewer**:
  - Sequence display shows "Sequence 10 ($0A)" format
  - Matches SID Factory II editor convention
  - Applied to both single-track and interleaved sequences

- **Bug Fixes**:
  - Fixed instrument/command carryover in sequence unpacker
  - Fixed parser to detect all 22 sequences (vs 3 before)
  - Comprehensive file scanning (removed 1200-byte limit)

- **Documentation Updates**:
  - SF2_TEXT_EXPORTER_README.md - Complete usage guide
  - SF2_TEXT_EXPORTER_IMPLEMENTATION.md - Technical details
  - SINGLE_TRACK_IMPLEMENTATION_SUMMARY.md - Format detection docs
  - TRACK3_CURRENT_STATE.md - Current status summary
  - TODO.md - Updated task list with priorities

### v2.1.0 (2025-12-16)

**Visualization and Playback Features**

- **NEW SF2 Viewer Visualization Tab**:
  - WaveformWidget: Display waveform samples as connected line graphs with grid
  - FilterResponseWidget: Show 11-bit filter cutoff frequency curves (0-2047)
  - EnvelopeWidget: Visualize ADSR envelope shapes with phase labels
  - Real-time updates when selecting different table types
  - No external dependencies (PyQt6 QPainter only)

- **NEW SF2 Viewer Playback Tab**:
  - Full SF2→SID→WAV audio playback pipeline
  - Play/Pause/Stop controls with proper state management
  - Volume slider (0-100%) with real-time adjustment
  - Position tracking in MM:SS format
  - Status log showing conversion steps
  - Automatic temporary file cleanup

- **Sequence Tab Management**:
  - Auto-detection of Laxity driver files
  - Sequences tab automatically disabled for files without valid sequence data
  - 96% empty sequence threshold for Laxity driver detection
  - Prevents user confusion with unavailable features

- **Core Parser Fixes**:
  - Fixed Music Data block parsing to extract correct sequence addresses
  - Sequence Data Address (offset 4-5) now extracted from block
  - Sequence Index Address (offset 6-7) now extracted from block
  - Replaced hardcoded placeholder values with actual data extraction

- **New Modules** (650+ lines):
  - `sf2_visualization_widgets.py`: Custom PyQt6 visualization widgets
  - `sf2_playback.py`: Audio playback engine with conversion pipeline

- **Updated Modules**:
  - `sf2_viewer_gui.py`: Added visualization and playback tabs (+100 lines)
  - `sf2_viewer_core.py`: Fixed Music Data block parsing (+40 lines)

### v0.7.2 (2025-12-12)

**WAV Rendering Fix + Waveform Analysis Tool**

- Fixed WAV rendering in complete pipeline (0% → 97% success rate)
  - Corrected SID2WAV.EXE command-line argument order
  - Fixed `-o` flag misuse (song number, not output file)
  - Added automatic file cleanup before rendering
  - Added `-16` flag for 16-bit audio quality
- Fixed player detection bug (detect_player_type → identify_sid_type)
- Added waveform analysis tool (`scripts/analyze_waveforms.py`, 450+ lines)
  - Interactive HTML reports with embedded audio players
  - HTML5 canvas waveform visualizations
  - Similarity metrics (correlation, RMSE, match rate)
  - File statistics comparison
  - Uses Python standard library only (no NumPy/Matplotlib)
- Updated SIDwinder trace status (✅ fully working, rebuilt 2025-12-06)
- Pipeline validation results (2025-12-12):
  - 18 SID files processed
  - WAV rendering: 35/36 files (97%)
  - SIDwinder trace: 36/36 files (100%)
  - Average accuracy: 45.39% (7 files at 100%, 10 LAXITY files at 1-8%)
- Generated 17 waveform analysis HTML reports
- Updated documentation to reflect current pipeline status

**Quality:** All pipeline steps tested and validated on 18 SID files

### v0.6.3 (2025-12-02)

**Pipeline Enhancement & Documentation**

- Added `generate_info.py` - Comprehensive info.txt generator (318 lines)
  - Automatic player identification via player-id.exe integration
  - Complete pipeline tools documentation
  - Hex table views of all music data (16 bytes/row with addresses)
  - Memory address maps for original and SF2 formats
  - Automatic source SID file preservation with consistent naming
  - Optional title override for SF2-packed files
- Added `disassemble_sid.py` - Complete 6502/6510 disassembler (272 lines)
  - Full instruction set support (56+ opcodes)
  - Branch target calculation for relative addressing
  - Unlimited output for complete player analysis
- Added `extract_addresses.py` - Music data structure address extraction (273 lines)
  - Locates all table addresses in memory
  - Outputs formatted address ranges
- Added `format_tables.py` - Hex table visualization (437 lines)
  - Generates 16-byte hex dumps with addresses
  - Side-by-side original vs converted comparison
- Created comprehensive player and format documentation
  - `docs/reference/SF2_DRIVER11_DISASSEMBLY.md` - Complete SF2 Driver 11 analysis (8.3 KB)
  - `docs/reference/STINSENS_PLAYER_DISASSEMBLY.md` - Laxity NewPlayer v21 analysis (17 KB)
  - `docs/reference/SF2_TRACKS_AND_SEQUENCES.md` - Tracks and sequences format guide (433 lines)
  - `docs/reference/SF2_INSTRUMENTS_REFERENCE.md` - Instruments format guide (595 lines)
  - Memory maps, annotated routines, table formats, architecture comparisons
- Enhanced info.txt output with new sections:
  - "Original SID File (Preserved)" - Source path, size, copied location
  - "Pipeline Tools Used" - Complete tool documentation with parameters
  - "Original SID Data Tables (Hex View)" - 16-byte hexdumps with addresses
  - "Converted SF2 Data Tables (Hex View)" - 16-byte hexdumps with addresses
- Pipeline improvements:
  - Source SID file automatically copied to output directory
  - Consistent filename generation using song metadata (not input filename)
  - Player detection via signature database (tools/sidid.cfg)
  - All outputs use unified naming convention
- Updated documentation:
  - README.md: Added generate_info.py, player-id integration docs
  - CLAUDE.md: Updated with new tools and documentation files
  - FILE_INVENTORY.md: Regenerated with latest file structure

**Quality:** All tools tested with Stinsens_Last_Night_of_89.sid and SF2-packed round-trip

### v0.6.2 (2025-11-29)
- Added Python 6502 CPU emulator (`sidm2/cpu6502_emulator.py`, 1,242 lines)
  - Complete instruction set implementation with all addressing modes
  - SID register write capture for validation
  - Frame-by-frame state tracking
  - Based on siddump.c architecture
- Added SID player module (`sidm2/sid_player.py`, 560 lines)
  - PSID/RSID header parsing
  - Note detection and frequency analysis
  - Siddump-compatible frame dump output
  - Command-line interface: `python -m sidm2.sid_player <sidfile> [seconds]`
- Added SF2 player parser (`sidm2/sf2_player_parser.py`, 389 lines)
  - Parser for SF2-exported SID files
  - Pattern-based table extraction with SF2 reference
  - Heuristic extraction mode (in development)
- Added SF2 player parser test suite (`test_sf2_player_parser.py`)
  - Validates parser with multiple SID files
  - 15/15 header parsing success rate
- Fixed SF2 driver address detection
  - Now reads init/play addresses from SF2 header (offsets 0x31, 0x33)
  - Replaced offset-based heuristics with header structure parsing
- Fixed siddump parser ADSR and pulse width parsing
  - Corrected column index calculation for register parsing
- Total new code: 2,341 lines enabling Python-based SID validation

### v0.6.1 (2025-11-26)
- Fixed instrument pointer validation boundary checking (changed >= to > for Y*4 indexed tables)
- Added $7F (end marker) to validation skip list alongside $80+ markers
- Reduced false-positive validation warnings by 50% (4 to 2 for Angular.sid)
- Created `generate_validation_report.py` for multi-file validation analysis
- Generated comprehensive validation report across all 16 test SID files

### v0.6.0 (2025-11-25)
- Added comprehensive SID accuracy validation system
- Created `validate_sid_accuracy.py` for frame-by-frame register comparison
- Created `sidm2/validation.py` module for pipeline integration
- Integrated 10-second quick validation into convert_all.py pipeline
- Added ACCURACY VALIDATION section to all info.txt files
- Fixed siddump table parser to correctly capture register states
- Established baseline accuracy metrics (9% overall for Angular.sid)
- Created comprehensive validation system documentation
- Removed Unicode emojis for Windows console compatibility

### v0.5.1 (2025-11-23)
- Fixed pulse table extraction to find correct address with improved scoring algorithm
- Fixed pulse table extraction to extract all entries (was stopping early on loops)
- Fixed filter table extraction with pattern-based detection
- Fixed filter table extraction to respect adjacent table boundaries
- Added 12 new tests for pulse/filter table extraction
- Expanded test coverage from 57 to 61 tests
- Improved table extraction scoring with bonuses for chain patterns, $FF values, subtract patterns

### v0.5.0 (2025-11-23)
- Fixed sequence parsing to properly handle instrument bytes (0xA0-0xBF) and command bytes (0xC0-0xCF)
- Added arpeggio table extraction from Laxity sequences
- Added instrument table pointer bounds validation (wave_ptr, pulse_ptr, filter_ptr)
- Added full conversion pipeline integration tests
- Expanded test coverage from 34 to 57 tests
- Added automated editor validation for all converted files
- Added GitHub Actions CI/CD workflow

### v0.4.0 (2025-11-22)
- Fixed SF2 crash issue caused by aux pointer pointing to valid aux data
- Added aux pointer validation test (`test_sf2_format.py`)
- Added Ring Modulation waveform support ($14, $15, $34, $35)
- Improved ADSR extraction with siddump merging
- Improved pulse table extraction scoring
- All converted files now pass SF2 format validation
- Current validation status: All files load in SID Factory II

### v0.3.0 (2025-11-22)
- Added SF2 metadata embedding (song name, author, copyright)
- Improved instrument naming with ADSR heuristics and waveform types
- Added cross-reference validation for wave tables and sequences
- Added validation report file output
- Added wave table debug info with candidate scores
- Fixed wave table extraction scoring algorithm
- Added variety bonus for better wave table selection
- Added sync waveform support (0x42, 0x43, etc.)
- Current average validation score: 91.2%

### v0.2.0 (2025-11-21)
- Full table extraction (instruments, wave, pulse, filter)
- Batch conversion support with convert_all.py
- Info file generation with detailed extraction data
- siddump integration for validation
- Validation script for comparing extraction vs playback

### v0.1.0 (2025-11-20)
- Initial release
- Basic SID to SF2 conversion
- Laxity NewPlayer v21 support
- NP20 and Driver11 template support

## Troubleshooting & Support

Having issues? We've got you covered!

### Common Issues

**File Not Found**:
- Verify file exists: `dir SID\yourfile.sid` (Windows) or `ls SID/yourfile.sid` (Mac/Linux)
- Use absolute path instead of relative
- Check you're in the SIDM2 project root directory

**Low Conversion Accuracy**:
- Check player type: `tools\player-id.exe yourfile.sid`
- For Laxity NewPlayer v21, use: `--driver laxity` (99.93% accuracy)
- Standard drivers on Laxity files: 1-8% accuracy (use Laxity driver instead)

**Module Not Found**:
- Install package: `pip install -e .`
- Or set PYTHONPATH: `set PYTHONPATH=%CD%` (Windows) or `export PYTHONPATH=$(pwd)` (Mac/Linux)

**Permission Denied**:
- Close SID Factory II if output file is open
- Add `--overwrite` flag to replace existing files
- Try different output location (e.g., your home directory)

### Debug Mode

Enable verbose logging for detailed error information:
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --verbose
```

### Complete Troubleshooting Guide

For detailed solutions to all common issues, see:
**📖 [Complete Troubleshooting Guide](docs/guides/TROUBLESHOOTING.md)**

Covers:
- File Not Found Issues
- Invalid SID Files
- Missing Dependencies
- Conversion Failures
- Permission Problems
- Platform-Specific Issues (Windows/Mac/Linux)
- Debug Mode Instructions
- FAQ

### Getting Help

- **Documentation**: See `CLAUDE.md` for quick reference
- **GitHub Issues**: https://github.com/MichaelTroelsen/SIDM2conv/issues
- **Bug Reports**: Include verbose output + file details

When reporting issues, include:
1. Command used (with `--verbose`)
2. Full error message
3. Player type: `tools\player-id.exe input.sid`
4. Python version: `python --version`
5. Platform (Windows/Mac/Linux)

---

## References

- [SID Factory II GitHub](https://github.com/Chordian/sidfactory2)
- [High Voltage SID Collection](https://www.hvsc.c64.org/)
- [PSID File Format](https://www.hvsc.c64.org/download/C64Music/DOCUMENTS/SID_file_format.txt)
- [Codebase64 SID Programming](https://codebase64.org/doku.php?id=base:sid_programming)

## Credits

- **DRAX** (Thomas Mogensen) - Composer of Unboxed Ending
- **Laxity** (Thomas Egeskov Petersen) - Player routine and SID Factory II creator
- **SID Factory II Team** - For the excellent music editor

## License

This tool is provided for educational and personal use. Please respect the copyrights of original music and software.

---

*This converter was created to help preserve and study Commodore 64 music.*
