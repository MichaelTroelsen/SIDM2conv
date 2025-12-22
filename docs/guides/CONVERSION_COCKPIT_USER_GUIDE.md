# Conversion Cockpit User Guide

**Version**: 1.0.0
**Date**: 2025-12-22
**Author**: SIDM2 Project

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [User Interface Overview](#user-interface-overview)
5. [Basic Workflows](#basic-workflows)
6. [Configuration Guide](#configuration-guide)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Introduction

### What is Conversion Cockpit?

Conversion Cockpit is a professional GUI application for batch converting Commodore 64 SID music files to SID Factory II (.sf2) format. It provides mission-control style monitoring with:

- **Real-time progress visualization**
- **Configurable 14-step conversion pipeline**
- **Live log streaming with color-coded output**
- **Per-file results tracking with accuracy metrics**
- **Simple and Advanced modes for different user needs**

### Who is this for?

- **End Users**: Simple mode provides one-click batch conversion with essential steps
- **Power Users**: Advanced mode provides full control over all 14 pipeline steps
- **SID Musicians**: Convert Laxity SID files to SF2 for editing and remixing

### Key Features

✅ **Batch Processing**: Convert 1-100+ SID files in one operation
✅ **Pause/Resume**: Interrupt and continue processing at any time
✅ **Progress Monitoring**: Real-time file and step progress with time estimates
✅ **Configurable Pipeline**: Choose which validation and analysis steps to run
✅ **Persistent Settings**: Configuration saves automatically between sessions
✅ **Drag-and-Drop**: Add files by dragging from Windows Explorer
✅ **Results Table**: View accuracy, status, and detailed results for each file

---

## Installation

### Prerequisites

- **Windows 10/11** (primary platform)
- **Python 3.8+** installed and in PATH
- **Git** (for cloning repository)

### Step 1: Clone Repository

```bash
git clone https://github.com/YourUsername/SIDM2.git
cd SIDM2
```

### Step 2: Launch Conversion Cockpit

The launcher will automatically install PyQt6 if needed:

```bash
conversion-cockpit.bat
```

Or use the Python launcher:

```bash
python pyscript/launch_conversion_cockpit.py
```

### Step 3: First Launch

On first launch, if PyQt6 is not installed:

1. You'll see a prompt: **"PyQt6 NOT FOUND"**
2. Press **Y** to install automatically (takes ~1 minute)
3. The Conversion Cockpit will launch automatically after installation

---

## Quick Start

### Convert Files in 5 Minutes

**1. Launch Conversion Cockpit**

```bash
conversion-cockpit.bat
```

**2. Add Files**

Click **Files** tab → **Browse** → Select your SID files → **Open**

Or drag-and-drop SID files directly into the file list.

**3. Configure (Simple Mode)**

- Mode: **Simple** (default - 7 essential steps)
- Driver: **Laxity** (default - 99.93% accuracy)
- Output: `output/` (default)

**4. Start Conversion**

Click **▶ START** button on Dashboard tab.

**5. Monitor Progress**

Watch real-time progress on Dashboard:
- File progress bar (e.g., 5/25 files)
- Step progress bar (e.g., Step 3/7)
- Live logs with color-coded output

**6. View Results**

Click **Results** tab to see:
- Per-file accuracy percentages
- Pass/Fail status with color coding
- Detailed results for each file

**Done!** Your converted .sf2 files are in `output/{SongName}/New/`

---

## User Interface Overview

### Main Window Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ [File] [Settings] [Help]                    Conversion Cockpit │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ [🏠 Dashboard] [📁 Files] [⚙️ Config] [📊 Results] [📝 Logs]   │
│                                                                 │
│ [Tab Content Area - switches based on selected tab]            │
│                                                                 │
│ Status: Ready | Output: C:\...\output | Mode: Simple           │
└─────────────────────────────────────────────────────────────────┘
```

### The 5 Tabs

#### 🏠 Dashboard Tab

**Purpose**: At-a-glance status during batch processing

**What You'll See**:
- **Stats Cards**: Files (total, selected, estimated time), Progress (current file, step, time), Results (pass/fail/accuracy)
- **Control Panel**: Start, Pause, Stop, Settings buttons
- **Current Operation**: Shows which file and step is being processed right now

**When to Use**: Leave this tab open during batch processing to monitor overall progress.

---

#### 📁 Files Tab

**Purpose**: Select which SID files to convert

**Features**:
- **Browse Button**: Open file dialog to select SID files
- **Drag & Drop**: Drag SID files from Windows Explorer
- **Checkboxes**: Check/uncheck individual files
- **Select All/None**: Bulk selection buttons
- **File Count**: Shows "23 of 25 files selected"

**Workflow**:
1. Click **Browse** or drag files into list
2. Check/uncheck files you want to convert
3. Click **Select All** or **Select None** for bulk operations

---

#### ⚙️ Configuration Tab

**Purpose**: Configure conversion parameters and pipeline steps

**Sections**:
1. **Mode Selection**: Simple (7 steps), Advanced (14 steps), Custom
2. **Driver Configuration**: Choose driver (Laxity/Driver 11/NP20), output directory
3. **Pipeline Steps**: Check/uncheck 14 individual steps
4. **Logging & Validation**: Log level, validation duration
5. **Execution Options**: Timeout, stop on error

**Most Common Settings**:
- **Mode**: Simple (for most users)
- **Driver**: Laxity (99.93% accuracy)
- **Output**: `output/` (default)

---

#### 📊 Results Tab

**Purpose**: View detailed per-file conversion results

**Table Columns**:
- **File**: SID filename
- **Driver**: Which driver was used (Laxity/Driver 11/NP20)
- **Steps**: Steps completed (e.g., 7/7)
- **Accuracy**: Frame accuracy percentage (e.g., 99.93%)
- **Status**: ✅ Passed / ⚠️ Warning / ❌ Failed
- **Action**: View button for detailed info

**Color Coding**:
- **Green** (>95%): Excellent accuracy
- **Yellow** (80-95%): Acceptable accuracy
- **Red** (<80%): Low accuracy or failed

**Features**:
- Sortable columns (click header to sort)
- Filter by status (show only passed/failed/warnings)
- View button opens detailed result dialog

---

#### 📝 Logs Tab

**Purpose**: Real-time log streaming with filtering

**Features**:
- **Color-Coded Output**: ERROR (red), WARN (yellow), INFO (gray), DEBUG (cyan)
- **Level Filter**: Dropdown to show only specific log levels
- **Text Search**: Find specific messages in logs
- **Auto-Scroll**: Automatically scrolls to latest log (toggleable)
- **Export**: Save logs to text file

**When to Use**: Monitor detailed progress, debug issues, review warnings.

---

## Basic Workflows

### Workflow 1: Simple Batch Conversion

**Goal**: Convert multiple SID files with minimal configuration

**Steps**:

1. **Launch**: `conversion-cockpit.bat`

2. **Add Files**:
   - Go to **Files** tab
   - Click **Browse**
   - Select multiple SID files (Ctrl+Click or Shift+Click)
   - Click **Open**

3. **Verify Settings**:
   - Go to **Config** tab
   - Ensure **Simple Mode** is selected
   - Ensure **Driver: Laxity** is selected
   - Verify **Output Directory**: `output/`

4. **Start Conversion**:
   - Go to **Dashboard** tab
   - Click **▶ START**

5. **Monitor Progress**:
   - Watch file progress bar (e.g., 5/25 files)
   - Watch step progress bar (e.g., Step 3/7)
   - View live logs for detailed status

6. **View Results**:
   - When complete, go to **Results** tab
   - Review accuracy percentages
   - Check for any failed conversions

7. **Access Output Files**:
   - Open `output/{SongName}/New/` folders
   - Find `.sf2` files ready for SID Factory II

---

### Workflow 2: Advanced Pipeline with Full Validation

**Goal**: Run full 14-step pipeline with analysis and validation

**Steps**:

1. **Switch to Advanced Mode**:
   - Go to **Config** tab
   - Select **Advanced Mode**
   - All 14 steps will be enabled automatically

2. **Review Enabled Steps**:
   - ✅ SID → SF2 Conversion (Required)
   - ✅ Siddump (Original)
   - ✅ SIDdecompiler Analysis
   - ✅ SF2 → SID Packing
   - ✅ Siddump (Exported)
   - ✅ WAV Rendering (Original)
   - ✅ WAV Rendering (Exported)
   - ✅ Hexdump Generation
   - ✅ SIDwinder Trace
   - ✅ Info Report
   - ✅ Annotated Disassembly
   - ✅ SIDwinder Disassembly
   - ✅ Validation (File checks)
   - ✅ MIDI Comparison

3. **Add Files** (same as Workflow 1)

4. **Start Conversion**:
   - Click **▶ START**
   - *Note: Advanced mode takes longer (2-3x) due to extra steps*

5. **Review Analysis Outputs**:
   - After completion, open `output/{SongName}/New/analysis/`
   - Find: siddump files, traces, disassemblies, info.txt

6. **Check Validation Results**:
   - Go to **Results** tab
   - Review accuracy percentages
   - Click **View** button to see detailed validation data

---

### Workflow 3: Custom Pipeline (Power Users)

**Goal**: Create custom pipeline with specific steps

**Steps**:

1. **Select Custom Mode**:
   - Go to **Config** tab
   - Select **Custom Mode**

2. **Choose Specific Steps**:
   - ✅ SID → SF2 Conversion (always required)
   - ✅ SF2 → SID Packing
   - ✅ Validation
   - ✅ WAV Rendering (both)
   - ✅ Siddump (both)
   - ❌ Uncheck steps you don't need (e.g., hexdump, traces)

3. **Save Configuration**:
   - Click **Save Configuration** button
   - Your custom preset is saved and will persist between sessions

4. **Run Conversion**: Same as Workflow 1

5. **Load Configuration Later**:
   - Next time you launch, click **Load Configuration**
   - Your custom preset will be restored

---

## Configuration Guide

### Mode Selection

**Simple Mode** (Default)
- **Purpose**: Essential steps only for fast batch conversion
- **Steps**: 7 (conversion, packing, dumps, WAV, info, validation)
- **Time**: ~70 seconds per file
- **Use When**: You just want working .sf2 files quickly

**Advanced Mode**
- **Purpose**: Full pipeline with all analysis and validation
- **Steps**: 14 (all steps enabled)
- **Time**: ~120-180 seconds per file
- **Use When**: You need detailed analysis, traces, disassemblies

**Custom Mode**
- **Purpose**: Pick exactly which steps you want
- **Steps**: 1-14 (you choose)
- **Time**: Varies based on selection
- **Use When**: You have specific needs (e.g., only WAV rendering)

---

### Driver Selection

**Laxity Driver** (Recommended)
- **Accuracy**: 99.93% frame accuracy
- **Use For**: Laxity NewPlayer v21 SID files
- **Output**: Highly accurate conversions ready for editing

**Driver 11**
- **Accuracy**: 1-8% for Laxity files, 100% for SF2-exported SIDs
- **Use For**: SF2-exported SIDs (roundtrip testing)
- **Output**: Basic conversion, low accuracy for Laxity

**NP20 Driver**
- **Accuracy**: 1-8% for Laxity files
- **Use For**: Experimental, not recommended for Laxity
- **Output**: Alternative driver format

**Recommendation**: Use **Laxity** driver for all Laxity NewPlayer v21 SID files.

---

### Pipeline Steps Explained

**Required Steps**:
1. **SID → SF2 Conversion**: Converts SID to SF2 format (always required)

**Essential Steps** (Simple Mode):
4. **SF2 → SID Packing**: Exports SF2 back to SID for validation
5. **Siddump (Exported)**: Generates register dump for validation
6. **WAV Rendering (Original)**: Renders original SID to audio
7. **WAV Rendering (Exported)**: Renders exported SID to audio
9. **Info Report**: Generates info.txt with conversion summary
12. **Validation**: Checks file integrity and accuracy

**Analysis Steps** (Advanced Mode):
2. **Siddump (Original)**: Register dump of original SID
3. **SIDdecompiler Analysis**: Player structure analysis
8. **Hexdump Generation**: Binary hexdump for debugging
9. **SIDwinder Trace**: Execution trace of SID player
10. **Annotated Disassembly**: Human-readable disassembly
11. **SIDwinder Disassembly**: SIDwinder-generated disassembly
13. **MIDI Comparison**: Compare MIDI output vs emulator

---

### Output Directory Structure

After conversion, files are organized as:

```
output/
└── {SongName}/
    └── New/
        ├── {SongName}_d11.sf2          # Converted SF2 file
        ├── {SongName}_d11.sid          # Exported SID file
        ├── {SongName}_original.dump    # Original siddump
        ├── {SongName}_exported.dump    # Exported siddump
        ├── {SongName}_original.wav     # Original audio
        ├── {SongName}_exported.wav     # Exported audio
        ├── info.txt                    # Conversion report
        └── analysis/
            ├── {SongName}_trace.txt        # Execution trace
            ├── {SongName}_siddecompiler.asm # SIDdecompiler output
            ├── {SongName}_disassembly.asm   # Annotated disassembly
            └── {SongName}_analysis_report.txt # Analysis report
```

---

## Advanced Features

### Pause and Resume

**Pause During Processing**:
1. Click **⏸ PAUSE** button
2. Current file finishes processing
3. Batch pauses before next file

**Resume Processing**:
1. Click **▶ START** again (button text changes to "Resume")
2. Batch continues from where it left off

**Use Cases**:
- Need to check an intermediate result
- Want to free up CPU for other tasks temporarily
- System resource management

---

### Stop and Restart

**Stop Processing**:
1. Click **⏹ STOP** button
2. Confirmation dialog appears
3. Click **Yes** to stop immediately

**Result**:
- Completed files remain in output directory
- Incomplete files are partially processed
- Results table shows completed files only

**Restart**:
- Uncheck already-completed files in Files tab
- Click **▶ START** to process remaining files

---

### Configuration Persistence

**Auto-Save**:
- Configuration saves automatically when you change settings
- Settings persist between sessions
- No manual save required (unless using presets)

**Manual Save/Load**:
- **Save Configuration**: Saves current settings as custom preset
- **Load Configuration**: Restores saved preset
- **Reset Configuration**: Restores default settings

**What's Saved**:
- Mode (Simple/Advanced/Custom)
- Driver selection
- Output directory
- Enabled pipeline steps
- Logging options
- Execution options

---

### Drag-and-Drop File Adding

**Method 1: Drag Files**:
1. Open Windows Explorer
2. Select one or more .sid files
3. Drag files into Conversion Cockpit file list
4. Files are added automatically

**Method 2: Drag Folder**:
1. Drag a folder containing .sid files
2. All .sid files in folder are added
3. Subfolders are included if "Include subdirectories" is checked

---

### Log Filtering and Search

**Filter by Level**:
1. Go to **Logs** tab
2. Click **Level** dropdown
3. Select: ALL / ERROR / WARN / INFO / DEBUG
4. View filtered logs

**Text Search**:
1. Type keyword in **Search** box
2. Matching lines are highlighted
3. Click **X** to clear search

**Export Logs**:
1. Click **Export** button
2. Choose save location
3. Logs saved as text file with timestamp

---

## Troubleshooting

### Issue 1: PyQt6 Installation Fails

**Symptoms**:
- "PyQt6 installation failed" error
- Launcher exits without starting GUI

**Solutions**:

**Solution A: Manual Installation**
```bash
python -m pip install PyQt6
python pyscript/launch_conversion_cockpit.py
```

**Solution B: Check Python Version**
```bash
python --version
# Should be Python 3.8 or newer
```

**Solution C: Update pip**
```bash
python -m pip install --upgrade pip
python -m pip install PyQt6
```

---

### Issue 2: Conversion Fails for All Files

**Symptoms**:
- All files show ❌ Failed status
- Logs show "Command not found" errors

**Solutions**:

**Check Dependencies**:
1. Verify `scripts/sid_to_sf2.py` exists
2. Verify `tools/siddump.exe` exists
3. Verify `tools/SID2WAV.EXE` exists

**Check Python Path**:
1. Open Command Prompt
2. Run: `python --version`
3. Should show Python 3.8+

**Check Working Directory**:
1. Verify you're in `SIDM2/` directory
2. Run: `cd C:\path\to\SIDM2`
3. Run: `conversion-cockpit.bat`

---

### Issue 3: Low Accuracy Results (<10%)

**Symptoms**:
- Results tab shows accuracy <10%
- Audio sounds wrong

**Solutions**:

**Check Driver Selection**:
1. Go to **Config** tab
2. Verify **Driver: Laxity** is selected
3. If Driver 11 or NP20 selected, change to Laxity

**Check File Type**:
1. Verify SID files are Laxity NewPlayer v21
2. Run: `tools/player-id.exe input.sid`
3. Should show "NewPlayer v21 (Laxity)"

**Try Different Driver**:
- Some files may work better with Driver 11
- Switch driver in Config tab and reconvert

---

### Issue 4: GUI Freezes During Conversion

**Symptoms**:
- Window becomes unresponsive
- Progress bars stop updating

**Solutions**:

**Wait for Timeout**:
- Default timeout is 120 seconds per step
- Long steps (disassembly, trace) may take time
- Check Logs tab for "Processing..." messages

**Increase Timeout**:
1. Go to **Config** tab
2. Find **Execution Options**
3. Increase **Step Timeout** to 300 seconds
4. Restart conversion

**Disable Long Steps**:
1. Switch to **Custom Mode**
2. Uncheck: SIDwinder Trace, Disassemblies
3. These steps can take 60-120 seconds each

---

### Issue 5: Output Files Missing

**Symptoms**:
- Results tab shows "Passed" but files not found
- Output directory is empty

**Solutions**:

**Check Output Directory**:
1. Go to **Config** tab
2. Note **Output Directory** path
3. Open that path in Windows Explorer
4. Look for `{SongName}/New/` subdirectories

**Check File Permissions**:
1. Verify you have write permission to output directory
2. Try changing output directory to Desktop

**Check Results Status**:
1. Go to **Results** tab
2. Click **View** button for a file
3. Review detailed error messages

---

## FAQ

### General Questions

**Q: What SID formats are supported?**

A: Currently only **Laxity NewPlayer v21** SID files are supported with high accuracy (99.93%). SF2-exported SIDs (roundtrip testing) work perfectly with Driver 11.

**Q: Can I convert non-Laxity SID files?**

A: Yes, but accuracy will be low (1-8%). The converter is optimized for Laxity format. Support for other player formats may be added in future versions.

**Q: How long does conversion take?**

A:
- **Simple Mode**: ~70 seconds per file (7 steps)
- **Advanced Mode**: ~120-180 seconds per file (14 steps)
- For 25 files: 30-75 minutes depending on mode

**Q: Can I run multiple instances?**

A: Yes, but each instance should use a different output directory to avoid conflicts.

---

### Conversion Questions

**Q: What's the difference between drivers?**

A:
- **Laxity**: 99.93% accuracy for Laxity SIDs, custom driver
- **Driver 11**: 100% for SF2-exported SIDs, 1-8% for Laxity
- **NP20**: Experimental, low accuracy for Laxity

**Q: Why is my accuracy so low?**

A: Most common reasons:
1. Wrong driver selected (use Laxity for Laxity files)
2. File is not Laxity NewPlayer v21 format
3. File is corrupted or incomplete

**Q: Can I edit the .sf2 files?**

A: Yes! Open them in **SID Factory II** editor. The .sf2 format is designed for editing sequences, instruments, and tables.

**Q: What if validation fails?**

A: Validation failure means:
- File integrity check failed
- Output file missing or corrupted
- Conversion process encountered error

Review Logs tab for specific error message.

---

### Configuration Questions

**Q: Which mode should I use?**

A:
- **Simple Mode**: For most users, fast batch conversion
- **Advanced Mode**: For detailed analysis and validation
- **Custom Mode**: When you need specific steps only

**Q: What if I only want WAV files?**

A:
1. Select **Custom Mode**
2. Check only: Conversion, WAV (Original), WAV (Exported)
3. Uncheck all other steps

**Q: Can I save multiple configurations?**

A: Currently only one custom configuration can be saved. You can switch between Simple/Advanced presets and your Custom preset.

**Q: Where are settings saved?**

A: Settings are saved in Windows Registry under `HKEY_CURRENT_USER\Software\SIDM2\ConversionCockpit` using Qt's QSettings system.

---

### Output Questions

**Q: Where are output files located?**

A: Default location: `output/{SongName}/New/`

For analysis files: `output/{SongName}/New/analysis/`

**Q: Can I change output directory?**

A: Yes:
1. Go to **Config** tab
2. Click **Browse** next to Output Directory
3. Select new directory
4. Click **OK**

**Q: What files are generated in Simple Mode?**

A:
- `{name}_d11.sf2` - Converted SF2 file
- `{name}_d11.sid` - Exported SID file
- `{name}_exported.dump` - Register dump
- `{name}_original.wav` - Original audio
- `{name}_exported.wav` - Exported audio
- `info.txt` - Conversion report

**Q: What files are generated in Advanced Mode?**

A: All Simple Mode files plus:
- `{name}_original.dump` - Original register dump
- Analysis folder with traces, disassemblies, reports

---

### Troubleshooting Questions

**Q: Why does the GUI freeze?**

A: The GUI may appear frozen during long operations (disassembly, trace). Check Logs tab - if it's still updating, processing is active. Increase timeout in Config tab if needed.

**Q: Can I cancel a stuck conversion?**

A: Yes, click **⏹ STOP** button. Current step will timeout after 120 seconds (or configured timeout), then batch will stop.

**Q: What if a file fails?**

A:
1. Review error in Logs tab
2. Click **View** in Results tab for details
3. Common issues: file not found, wrong format, permission denied

**Q: Can I retry failed files?**

A: Yes:
1. Note which files failed in Results tab
2. Go to Files tab
3. Uncheck passed files, keep failed files checked
4. Click **▶ START** to retry

---

## Keyboard Shortcuts

- **Ctrl+O**: Open file browser (Files tab)
- **Ctrl+S**: Save configuration (Config tab)
- **Ctrl+L**: Focus search box (Logs tab)
- **F5**: Refresh results table (Results tab)
- **Escape**: Stop conversion (confirmation required)

---

## Getting Help

### Documentation

- **User Guide**: This document
- **Technical Reference**: `docs/guides/CONVERSION_COCKPIT_TECHNICAL_REFERENCE.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Troubleshooting**: `docs/guides/TROUBLESHOOTING.md`

### Support

- **GitHub Issues**: https://github.com/YourUsername/SIDM2/issues
- **Discussions**: https://github.com/YourUsername/SIDM2/discussions

### Reporting Bugs

When reporting bugs, include:
1. Python version (`python --version`)
2. PyQt6 version (`python -c "import PyQt6; print(PyQt6.__version__)"`)
3. Error message from Logs tab
4. Steps to reproduce
5. SID file that caused issue (if possible)

---

## Appendix A: Glossary

- **SID**: Sound Interface Device, Commodore 64 sound chip
- **SF2**: SID Factory II file format for editing music
- **Laxity**: Player format created by Laxity/NewPlayer v21
- **Driver**: SF2 player code that interprets SF2 data
- **Pipeline**: Sequence of conversion and validation steps
- **Siddump**: Tool that captures SID register writes
- **Frame Accuracy**: Percentage of SID register writes that match original
- **Roundtrip**: Converting SID→SF2→SID and comparing to original

---

## Appendix B: Command-Line Alternatives

For advanced users who prefer command-line:

**Single File Conversion**:
```bash
python scripts/sid_to_sf2.py input.sid output.sf2 --driver laxity
```

**Batch Conversion**:
```bash
python scripts/convert_all.py
```

**Complete Pipeline**:
```bash
python pyscript/complete_pipeline_with_validation.py
```

**Validation**:
```bash
python scripts/validate_sid_accuracy.py original.sid exported.sid
```

---

## Appendix C: Version History

**v1.0.0** (2025-12-22)
- Initial release
- Simple/Advanced/Custom modes
- 14-step configurable pipeline
- Real-time monitoring and logging
- Pause/Resume functionality
- Persistent configuration
- Results table with accuracy tracking

---

**End of User Guide**

For technical details, see: `CONVERSION_COCKPIT_TECHNICAL_REFERENCE.md`

Generated by SIDM2 Project - 2025-12-22
