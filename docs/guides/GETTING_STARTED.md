# Getting Started with SIDM2

**Version**: 2.9.7
**Updated**: 2025-12-27
**Reviewed against**: v3.5.10 (2026-05-12) — install + first-conversion steps unchanged. Editor-edit propagation now closed for sequences, instruments (AD+SR), wave, pulse, and filter across Stinsen + Beast + Angular variants (Stage 7 complete v3.5.10); does not affect this guide's getting-started content.

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

## Standalone binary — what it would bundle, and what stays on your machine

`sidm2.spec` (repo root) is a PyInstaller spec for a console `sid-to-sf2`
binary:

```
pip install pyinstaller
pyinstaller sidm2.spec        # -> dist/sid-to-sf2/sid-to-sf2.exe
```

✅ **It builds.** First built 2026-09-05 with PyInstaller 6.22.2: exit 0, a
3.36 MB `sid-to-sf2.exe` inside a 41 MB bundle directory, and it converts a real
file end to end.

⚠️ **But you must run it from a SIDM2 checkout root, or it silently produces a
broken file.** Measured on the same build, converting `SID/Angular.sid` twice
with the same binary and the same arguments:

| run from | driver chosen | result |
|---|---|---|
| a checkout root | `LAXITY` — "Laxity-specific driver for maximum accuracy" | 9,029 bytes, valid |
| anywhere else | `DRIVER11`, player `Unknown` | 7,408 bytes, **`Instruments table (0x80) MISSING - file will be rejected!`** |

**Both runs exit 0.** The second one prints `SF2 FILE VALIDATION FAILED` among
its log lines and then reports success, so a script checking the exit code sees
a clean conversion and gets a file SID Factory II will refuse. Per the accuracy
matrix, native Laxity through Driver 11 is the 1–8% path — so this is not a
cosmetic difference, it is the documented bad conversion.

The cause is not the packaging. `sidm2/conversion_pipeline.py` resolves
`player-id.exe` relative to `os.getcwd()` rather than to the bundle, and nothing
in the tree consults `sys._MEIPASS`, so outside a checkout the identifier is
never found and driver auto-selection falls back to its safe default. Until a
frozen-mode path helper lands (tracked as
`sidm2-has-no-frozen-mode-tool-resolution`), treat the binary as
"portable executable, non-portable working directory".

**The workaround is `--driver`, and it fully recovers the result** — measured,
not assumed. Running the same binary from outside the checkout with
`--driver laxity` produced a file **byte-identical** to the in-checkout run
(md5 `a46642f7…`, 9,029 bytes) with no validation errors. Naming the driver
skips auto-selection, so `player-id.exe` is never needed. Only auto-selection
depends on the working directory; everything downstream of it does not.

### The external tools are NOT Python, so they are not "just imported"

SIDM2 shells out to several helper executables. A frozen binary can carry some
of them and cannot carry the rest, and the difference decides whether a feature
works or fails at runtime:

| tool | where it lives | in a binary |
|---|---|---|
| `player-id.exe` | `tools/`, tracked | **bundled** — driver auto-selection needs it |
| `siddump.exe` | `tools/`, tracked | bundled |
| `SIDwinder.exe` | `tools/`, tracked | bundled |
| `SIDdecompiler.exe` | `tools/`, tracked | bundled |
| `sidm2-sid-trace.exe` | `tools/`, tracked | bundled |
| `sidplayfp` | `tools/sidplayfp/`, 9 tracked files | bundled (exe + its data files) |
| **VICE** (`vsid.exe`) | a separate install, e.g. `C:\winvice\bin` | **NOT bundled** — stays on your machine |
| **SID Factory II** (`SIDFactoryII.exe`) | a separate install / `bin/` | **NOT bundled** |

So audio export via VICE, and anything that drives the SID Factory II editor,
still require those programs to be installed and findable **even when running
the binary**. Everything in the first six rows travels with it.

### Two things must be fixed before the binary can work

These are code changes, not packaging options, and a build made without them
produces an executable that starts fine and then fails on its first conversion:

1. **Nothing in the codebase looks in `sys._MEIPASS`.** PyInstaller unpacks
   bundled data there; code that does not consult it cannot see the `tools/`
   directory it just shipped. There are currently **zero** references to
   `sys._MEIPASS` or `sys.frozen` anywhere in the tree.
2. **One tool path is resolved from the working directory.**
   `sidm2/conversion_pipeline.py:339` builds
   `os.path.join(os.getcwd(), 'tools', 'player-id.exe')`, so the lookup depends
   on where the user happens to be standing rather than on where the program
   is. Run the binary from your Music folder and driver auto-selection breaks.

The fix for both is one helper that prefers `sys._MEIPASS` when frozen and
falls back to the repo layout otherwise, used everywhere a tool path is built.

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

**Last Updated**: 2025-12-27 (reviewed 2026-05-12 against v3.5.10)
**Version**: 2.9.7
**Status**: Production Ready
