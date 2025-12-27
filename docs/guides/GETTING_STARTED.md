# Getting Started with SIDM2

**Version**: 2.9.7
**Updated**: 2025-12-27

Welcome to SIDM2! This guide will help you get up and running quickly.

---

## What is SIDM2?

SIDM2 converts Commodore 64 SID music files to SID Factory II (.sf2) format with exceptional accuracy:

- **Laxity files**: 99.93% frame accuracy
- **SF2-exported files**: 100% perfect roundtrip
- **Other formats**: Safe, reliable conversion

Perfect for music preservation, editing in SID Factory II, or batch processing SID collections.

---

## Prerequisites

### Required

1. **Python 3.8+** - Download from [python.org](https://www.python.org/)
2. **Windows OS** - Most features require Windows (SID Factory II, automation)

### Optional

- **SID Factory II** - For editing converted files ([Download](https://blog.chordian.net/sf2/))
- **VICE Emulator** - For playing SID files ([Download](https://vice-emu.sourceforge.io/))

---

## Quick Installation

### Step 1: Clone or Download

```bash
git clone https://github.com/MichaelTroelsen/SIDM2conv.git
cd SIDM2conv
```

Or download ZIP from GitHub and extract.

### Step 2: Install Python Dependencies

**Basic conversion** (no dependencies required):
```bash
# All core conversion features work without any pip installs!
python scripts/sid_to_sf2.py input.sid output.sf2
```

**Optional GUI tools** (for SF2 Viewer and Conversion Cockpit):
```bash
pip install PyQt6
```

**Optional automation** (for batch testing):
```bash
pip install pyautogui pygetwindow pywin32
```

### Step 3: Verify Installation

```bash
# Test basic conversion
sid-to-sf2.bat SID/Angular.sid test.sf2

# Should create test.sf2 and test.txt
```

Success! You're ready to convert SID files.

---

## 5-Minute Quick Start

### Convert Your First SID File

**Option 1: Using Batch File** (Windows - Easiest)
```bash
sid-to-sf2.bat input.sid output.sf2
```

**Option 2: Using Python** (Cross-platform)
```bash
python scripts/sid_to_sf2.py input.sid output.sf2
```

**What Happens**:
1. Analyzes input.sid to identify player type
2. Automatically selects best driver (Laxity/SF2/NP20/Driver11)
3. Converts to output.sf2 format
4. Validates SF2 format integrity
5. Creates output.txt with driver info and validation results

**Output Files**:
- `output.sf2` - Converted file (ready for SID Factory II)
- `output.txt` - Driver selection details, accuracy info, validation report

### View the Converted File

**Option 1: In SID Factory II** (Recommended)
```bash
# Open SID Factory II, then File > Open > output.sf2
```

**Option 2: In SF2 Viewer** (Quick preview)
```bash
sf2-viewer.bat output.sf2
```

Shows all tables, sequences, instruments, and wave data in a GUI.

### Export as Text

```bash
sf2-export.bat output.sf2
```

Creates `output_export.txt` with complete SF2 dump (orderlists, sequences, instruments, tables).

---

## Basic Workflows

### Workflow 1: Single File Conversion

```bash
# Automatic driver selection (recommended)
sid-to-sf2.bat music.sid music.sf2

# Check the .txt file for driver selection
type music.txt
```

**Manual driver override** (expert use):
```bash
sid-to-sf2.bat music.sid music.sf2 --driver laxity
```

### Workflow 2: Batch Convert a Folder

**Convert all Laxity files**:
```bash
batch-convert-laxity.bat
```

Converts all SID files in `SID/` folder using Laxity driver, outputs to `SF2/`.

**Custom batch conversion**:
```bash
# Create your own batch script
for %%f in (SID\*.sid) do (
    python scripts/sid_to_sf2.py "%%f" "SF2\%%~nf.sf2"
)
```

### Workflow 3: Edit in SID Factory II

1. **Convert**:
   ```bash
   sid-to-sf2.bat original.sid editable.sf2
   ```

2. **Open in SID Factory II**:
   - Launch SID Factory II
   - File > Open > `editable.sf2`
   - Edit tables, sequences, instruments

3. **Export back to SID**:
   ```bash
   python scripts/sf2_to_sid.py editable.sf2 final.sid
   ```

4. **Test in VICE**:
   ```bash
   C:\winvice\bin\vsid.exe final.sid
   ```

### Workflow 4: Validate Accuracy

```bash
# Compare original vs converted
python scripts/validate_sid_accuracy.py original.sid converted.sid
```

Generates frame-by-frame comparison report.

---

## Using the Conversion Cockpit (GUI)

**Launch**:
```bash
conversion-cockpit.bat
```

**Features**:
- Visual file browser for SID files
- Automatic driver selection display
- One-click batch conversion
- Real-time progress tracking
- View conversion results
- Launch SF2 Viewer from results

**Workflow**:
1. Click "Browse" to select SID files or folder
2. Review detected player types
3. Click "Convert All"
4. Monitor progress bar
5. View results in table
6. Right-click any result to view in SF2 Viewer

---

## Using Batch Testing (Automation)

**Test converted files automatically**:
```bash
# Test all SF2 files in output folder
test-batch-pyautogui.bat

# Test specific folder with file limit
test-batch-pyautogui.bat --directory G5/examples --max-files 10
```

**What it does**:
1. Loads each SF2 file in SID Factory II
2. Starts playback (F5)
3. Plays for 3 seconds
4. Stops playback (F6)
5. Verifies window stability (2 seconds)
6. Closes editor
7. Verifies process cleanup
8. Reports results

**Requirements**:
```bash
pip install pyautogui pygetwindow pywin32
```

**Results**:
```
Total Files:    10
Passed:         10 (100.0%)
Failed:         0 (0.0%)
Avg Per File:   10.1 seconds
Processes:      0 remaining (verified)
```

---

## Understanding Driver Selection

SIDM2 automatically selects the best driver based on the source SID player type.

### Driver Matrix

| Source Player | Auto-Selected Driver | Accuracy | Use Case |
|--------------|---------------------|----------|----------|
| **Laxity NewPlayer v21** | `laxity` | **99.93%** | Laxity files |
| **SF2-exported** | `driver11` | **100%** | Perfect roundtrip |
| **NewPlayer 20.G4** | `np20` | 70-90% | NP20 files |
| **Rob Hubbard/Martin Galway/Unknown** | `driver11` | Safe default | Generic |

### How It Works

1. **Analyze**: Examines SID file structure
2. **Identify**: Detects player type (Laxity, SF2, NP20, etc.)
3. **Select**: Chooses optimal driver
4. **Convert**: Uses selected driver
5. **Validate**: Verifies SF2 format integrity
6. **Document**: Creates .txt file with details

### Manual Override

Only needed for expert use or troubleshooting:

```bash
sid-to-sf2.bat input.sid output.sf2 --driver laxity
sid-to-sf2.bat input.sid output.sf2 --driver driver11
sid-to-sf2.bat input.sid output.sf2 --driver np20
```

---

## Common Tasks

### View SF2 Tables

```bash
sf2-viewer.bat music.sf2
```

Shows:
- Voice 1/2/3 orderlists
- Sequences (with control codes)
- Instruments (ADSR, waveform, pulse, filter)
- Wave, pulse, filter, arpeggio tables

### Export SF2 as Text

```bash
sf2-export.bat music.sf2
```

Creates `music_export.txt` with complete data dump.

### Compare Original vs Converted

```bash
# Using Python siddump (cross-platform)
python pyscript/siddump_complete.py original.sid -t30
python pyscript/siddump_complete.py converted.sid -t30

# Compare frame dumps
```

### Analyze SID Structure

```bash
# Quick disassembly
python pyscript/quick_disasm.py music.sid

# Full trace analysis (Python SIDwinder)
python pyscript/sidwinder_trace.py --trace output.txt --frames 1500 music.sid
```

### Check Player Type

```bash
# Automatic detection
python scripts/sid_to_sf2.py music.sid test.sf2

# Check the .txt file for player identification
type test.txt
```

---

## Troubleshooting

### "No module named 'PyQt6'"

**Problem**: SF2 Viewer or Conversion Cockpit won't launch

**Solution**:
```bash
pip install PyQt6
```

### "No module named 'pyautogui'"

**Problem**: Batch testing won't run

**Solution**:
```bash
pip install pyautogui pygetwindow pywin32
```

### "SID Factory II not found"

**Problem**: Automation can't find editor

**Solution**:
1. Download from https://blog.chordian.net/sf2/
2. Extract to `bin/SIDFactoryII.exe`
3. Or update `config/sf2_automation.ini` with custom path

### Conversion Produces Empty SF2

**Problem**: Output.sf2 is only 8KB (driver template)

**Possible causes**:
1. Wrong driver selected - check output.txt
2. Unsupported player type
3. Corrupted SID file

**Solution**:
```bash
# Try different drivers
sid-to-sf2.bat input.sid output.sf2 --driver driver11
sid-to-sf2.bat input.sid output.sf2 --driver laxity
```

### SF2 Won't Open in SID Factory II

**Problem**: Editor shows "Invalid SF2 file"

**Check validation**:
```bash
# Look at the .txt file - validation section at bottom
type output.txt
```

If validation failed, file may be corrupted or incompatible.

### Need More Help?

See **[Complete Troubleshooting Guide](TROUBLESHOOTING.md)** for:
- Detailed error solutions
- Platform-specific issues
- Advanced debugging
- Performance optimization

---

## What's Next?

### Learn More

1. **[Tutorials](TUTORIALS.md)** - Step-by-step workflows
2. **[Best Practices](BEST_PRACTICES.md)** - Expert tips and patterns
3. **[FAQ](FAQ.md)** - Common questions answered

### Advanced Topics

- **[SF2 Format Specification](../reference/SF2_FORMAT_SPEC.md)** - Deep dive into format
- **[Laxity Driver Technical Reference](../reference/LAXITY_DRIVER_TECHNICAL_REFERENCE.md)** - Driver internals
- **[Components Reference](../COMPONENTS_REFERENCE.md)** - Python API

### Testing

```bash
# Run all tests (200+ tests)
test-all.bat

# Specific test suites
python -m pytest pyscript/test_siddump.py -v
python -m pytest pyscript/test_sidwinder.py -v
```

---

## Quick Reference Card

### Essential Commands

```bash
# Convert
sid-to-sf2.bat input.sid output.sf2

# View
sf2-viewer.bat output.sf2

# Export
sf2-export.bat output.sf2

# Batch convert
batch-convert-laxity.bat

# GUI tools
conversion-cockpit.bat
sf2-viewer.bat

# Batch testing
test-batch-pyautogui.bat

# Tests
test-all.bat
```

### File Locations

```
SIDM2/
├── scripts/           # Conversion tools
├── pyscript/          # Python utilities
├── sidm2/             # Core package
├── G5/drivers/        # SF2 drivers
├── SID/               # Input SID files
├── SF2/               # Output SF2 files
├── output/            # Conversion results
├── config/            # Configuration files
└── docs/              # Documentation
```

### Getting Help

- **Quick Reference**: `CLAUDE.md`
- **Full Documentation**: `README.md`
- **Troubleshooting**: `docs/guides/TROUBLESHOOTING.md`
- **Issues**: https://github.com/MichaelTroelsen/SIDM2conv/issues

---

**You're all set!** Start converting SID files with `sid-to-sf2.bat` and explore the tools.

**Next**: Check out [Tutorials](TUTORIALS.md) for step-by-step workflows.

---

**Last Updated**: 2025-12-27
**Version**: 2.9.7
**Status**: Production Ready
