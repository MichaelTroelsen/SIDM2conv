# SIDM2 Frequently Asked Questions (FAQ)

**Version**: 2.9.6
**Updated**: 2025-12-26

Common questions and answers about SIDM2.

---

## Table of Contents

### Getting Started
- [What is SIDM2?](#what-is-sidm2)
- [What can I do with SIDM2?](#what-can-i-do-with-sidm2)
- [Do I need to install anything?](#do-i-need-to-install-anything)
- [Is SIDM2 free?](#is-sidm2-free)

### Conversion
- [How do I convert a SID file?](#how-do-i-convert-a-sid-file)
- [Which driver should I use?](#which-driver-should-i-use)
- [Why is my conversion accuracy low?](#why-is-my-conversion-accuracy-low)
- [Can I convert multiple files at once?](#can-i-convert-multiple-files-at-once)
- [What does the .txt file contain?](#what-does-the-txt-file-contain)

### Compatibility
- [What SID formats are supported?](#what-sid-formats-are-supported)
- [Can I edit SF2 files?](#can-i-edit-sf2-files)
- [Does it work on Mac/Linux?](#does-it-work-on-maclinux)
- [Why do I need Windows for some features?](#why-do-i-need-windows-for-some-features)

### Quality
- [How accurate are conversions?](#how-accurate-are-conversions)
- [How do I validate conversion quality?](#how-do-i-validate-conversion-quality)
- [Why doesn't my SF2 sound exactly like the SID?](#why-doesnt-my-sf2-sound-exactly-like-the-sid)
- [Can I improve conversion accuracy?](#can-i-improve-conversion-accuracy)

### Tools
- [What is the SF2 Viewer?](#what-is-the-sf2-viewer)
- [What is the Conversion Cockpit?](#what-is-the-conversion-cockpit)
- [What is batch testing?](#what-is-batch-testing)
- [What is Python siddump?](#what-is-python-siddump)

### Troubleshooting
- [Conversion fails with error](#conversion-fails-with-error)
- [SF2 won't open in SID Factory II](#sf2-wont-open-in-sid-factory-ii)
- [PyQt6 import error](#pyqt6-import-error)
- [Process remains after closing editor](#process-remains-after-closing-editor)

### Advanced
- [Can I use SIDM2 in my own scripts?](#can-i-use-sidm2-in-my-own-scripts)
- [How do I contribute to SIDM2?](#how-do-i-contribute-to-sidm2)
- [Where can I get help?](#where-can-i-get-help)

---

## Getting Started

### What is SIDM2?

**Answer**: SIDM2 is a converter for Commodore 64 SID music files to SID Factory II (.sf2) format.

**Key features**:
- Automatic driver selection for optimal quality
- 99.93% accuracy for Laxity files
- 100% accuracy for SF2-exported files
- GUI tools for viewing and batch conversion
- Comprehensive validation system

**Use cases**:
- Music preservation
- Editing C64 music in SID Factory II
- Batch processing SID collections
- Converting for modern playback

---

### What can I do with SIDM2?

**Answer**: Many things!

**Basic**:
- Convert SID files to SF2 format
- View SF2 file contents
- Export SF2 data as text

**Intermediate**:
- Batch convert entire collections
- Edit converted files in SID Factory II
- Validate conversion accuracy

**Advanced**:
- Automate workflows with Python API
- Create custom conversion pipelines
- Analyze SID file structure
- Compare original vs converted files

**Example workflow**:
1. Convert SID to SF2
2. Edit in SID Factory II
3. Export back to SID
4. Play in VICE emulator

---

### Do I need to install anything?

**Answer**: Minimal requirements!

**Required** (all platforms):
- Python 3.8 or newer

**Optional** (for specific features):
- **PyQt6** - For SF2 Viewer and Conversion Cockpit GUIs
  ```bash
  pip install PyQt6
  ```

- **PyAutoGUI** - For batch testing automation
  ```bash
  pip install pyautogui pygetwindow pywin32
  ```

- **SID Factory II** - For editing SF2 files (Windows only)

**Core conversion** works with zero dependencies!

---

### Is SIDM2 free?

**Answer**: Yes, completely free and open source!

**License**: MIT License
**Source code**: https://github.com/MichaelTroelsen/SIDM2conv
**Cost**: $0

You can:
- Use it commercially
- Modify it
- Distribute it
- Include it in other projects

---

## Conversion

### How do I convert a SID file?

**Answer**: Very simple!

**Windows**:
```bash
sid-to-sf2.bat input.sid output.sf2
```

**Mac/Linux**:
```bash
python scripts/sid_to_sf2.py input.sid output.sf2
```

**Output**:
- `output.sf2` - Converted file
- `output.txt` - Driver info and validation

**What happens**:
1. Analyzes SID file
2. Identifies player type
3. Selects best driver automatically
4. Converts to SF2 format
5. Validates output
6. Creates info file

**Time**: ~0.5 seconds per file

---

### Which driver should I use?

**Answer**: Let SIDM2 choose automatically!

**Automatic selection** (recommended):
```bash
sid-to-sf2.bat input.sid output.sf2
```

SIDM2 detects the player type and selects the optimal driver:

| Player Type | Driver | Accuracy |
|------------|--------|----------|
| Laxity NP21 | laxity | 99.93% |
| SF2-exported | driver11 | 100% |
| NewPlayer 20.G4 | np20 | 70-90% |
| Unknown | driver11 | Safe default |

**Manual override** (expert only):
```bash
sid-to-sf2.bat input.sid output.sf2 --driver laxity
```

**Check selection**:
```bash
type output.txt
```

---

### Why is my conversion accuracy low?

**Answer**: Several possible reasons.

**Check driver selection**:
```bash
type output.txt
```

If driver is wrong, try manual override:
```bash
sid-to-sf2.bat input.sid output.sf2 --driver laxity
```

**Common causes**:
1. **Unsupported player** - File uses player that isn't Laxity/NP20/SF2
2. **Wrong driver** - Auto-detection failed (rare)
3. **Corrupted SID** - Original file has issues
4. **Complex player** - Some players are harder to convert

**Solutions**:
1. Check player type in output.txt
2. Try different drivers manually
3. Verify original SID plays correctly in VICE
4. Check for known limitations (see CLAUDE.md)

---

### Can I convert multiple files at once?

**Answer**: Yes! Multiple ways to do it.

**Method 1: Built-in batch script** (for Laxity files):
```bash
batch-convert-laxity.bat
```

**Method 2: GUI** (easiest):
```bash
conversion-cockpit.bat
# Add folder, click "Convert All"
```

**Method 3: Custom batch script**:
```batch
for %%f in (SID\*.sid) do (
    sid-to-sf2.bat "%%f" "SF2\%%~nf.sf2"
)
```

**Method 4: Python script**:
```python
from pathlib import Path
import subprocess

for sid_file in Path("SID").glob("*.sid"):
    sf2_file = Path("SF2") / f"{sid_file.stem}.sf2"
    subprocess.run(["python", "scripts/sid_to_sf2.py", str(sid_file), str(sf2_file)])
```

**Performance**: ~2 conversions per second on average

---

### What does the .txt file contain?

**Answer**: Complete conversion metadata.

**Example output.txt**:
```
SID to SF2 Conversion Report
============================

Source File: input.sid
Output File: output.sf2
Conversion Date: 2025-12-26 10:30:45

Player Detection
----------------
Player identified: Laxity NewPlayer v21
Driver selected: laxity
Expected accuracy: 99.93% frame accuracy

Conversion Details
------------------
Init Address: $1000
Play Address: $10A1
Songs: 1 (converted song 1)

SF2 Format Validation
---------------------
[OK] SF2 format valid
[OK] All required blocks present
[OK] Header metadata correct
[OK] Voice orderlists valid (3 voices)
[OK] Sequences valid (256 sequences)
[OK] Instruments valid (32 instruments)
[OK] Tables valid (wave, pulse, filter, arpeggio)

File Sizes
----------
Input SID:  25,600 bytes
Output SF2: 11,234 bytes

Status: SUCCESS
```

**Use this to**:
- Verify driver selection
- Check validation status
- Troubleshoot issues
- Document conversions

---

## Compatibility

### What SID formats are supported?

**Answer**: Primarily Laxity NewPlayer v21 and SF2-exported files.

**Fully supported** (optimal quality):
- **Laxity NewPlayer v21** - 99.93% accuracy
- **SF2-exported files** - 100% roundtrip

**Partially supported** (good quality):
- **NewPlayer 20.G4** - 70-90% accuracy
- **Rob Hubbard player** - Via Driver 11
- **Martin Galway player** - Via Driver 11

**Not supported**:
- JCH player
- GoatTracker files
- Other custom players (may work with driver11 but lower quality)

**Check compatibility**:
```bash
sid-to-sf2.bat unknown.sid test.sf2
type test.txt  # Check player detection
```

---

### Can I edit SF2 files?

**Answer**: Yes! That's a major feature.

**In SID Factory II** (recommended):
1. Convert SID to SF2
2. Open in SID Factory II
3. Edit sequences, instruments, tables
4. Save as SF2
5. Export back to SID if needed

**In SF2 Viewer** (view only):
```bash
sf2-viewer.bat file.sf2
```

Shows all data but can't edit. Can export as text.

**Programmatically** (Python API):
```python
from sidm2.sf2_reader import SF2Reader
from sidm2.sf2_writer import SF2Writer

reader = SF2Reader()
data = reader.read_sf2("input.sf2")

# Modify data
data.sequences[0].notes[5] = Note("C-4", instrument=1)

writer = SF2Writer()
writer.write_sf2("output.sf2", data)
```

---

### Does it work on Mac/Linux?

**Answer**: Mostly yes, with some limitations.

**Works on all platforms**:
- ✅ Core conversion (SID → SF2)
- ✅ Python siddump
- ✅ Python SIDwinder
- ✅ SF2 text export
- ✅ Validation scripts

**Windows only**:
- ❌ SID Factory II (no Mac/Linux version)
- ❌ Batch testing (uses Windows automation)
- ❌ Some external tools (tools/ folder)

**Cross-platform workflow**:
1. Convert on Mac/Linux
2. Transfer SF2 to Windows
3. Edit in SID Factory II on Windows
4. Transfer back

Or use Wine/VM for Windows tools.

---

### Why do I need Windows for some features?

**Answer**: Because of SID Factory II.

**SID Factory II**:
- Windows-only application
- No official Mac/Linux version
- Required for editing SF2 files
- Used by batch testing for validation

**Workarounds**:
1. **Wine** - Run SID Factory II on Mac/Linux via Wine
2. **VM** - Use Windows VM (VirtualBox, Parallels)
3. **Dual boot** - Boot into Windows when needed
4. **Remote** - Use Windows machine remotely

**Pure conversion** doesn't require Windows - only editing does.

---

## Quality

### How accurate are conversions?

**Answer**: Very accurate! Depends on source player.

**By player type**:

| Player | Driver | Accuracy | Status |
|--------|--------|----------|--------|
| **Laxity NP21** | laxity | **99.93%** | Production |
| **SF2-exported** | driver11 | **100%** | Perfect |
| **NewPlayer 20.G4** | np20 | 70-90% | Good |
| **Unknown** | driver11 | Varies | Safe |

**What does 99.93% mean?**:
- Out of 1500 frames (60 seconds)
- 1499 frames match exactly
- 1 frame has minor difference
- Essentially identical

**Measured by**:
- Frame-by-frame SID register comparison
- Audio waveform analysis
- Manual listening tests

---

### How do I validate conversion quality?

**Answer**: Multiple validation methods available.

**Method 1: Automatic validation** (built-in):
```bash
sid-to-sf2.bat input.sid output.sf2
type output.txt  # Check validation section
```

**Method 2: Frame comparison**:
```bash
# Export SF2 back to SID
python scripts/sf2_to_sid.py output.sf2 roundtrip.sid

# Validate
python scripts/validate_sid_accuracy.py input.sid roundtrip.sid
```

**Method 3: siddump comparison**:
```bash
python pyscript/siddump_complete.py input.sid -t30 > original.txt
python pyscript/siddump_complete.py roundtrip.sid -t30 > converted.txt
diff original.txt converted.txt
```

**Method 4: Audio comparison**:
- Play both in VICE and listen
- Export to WAV and compare waveforms

**Method 5: Batch testing**:
```bash
test-batch-pyautogui.bat
```

Tests file loading and playback in SID Factory II.

---

### Why doesn't my SF2 sound exactly like the SID?

**Answer**: Depends on accuracy level and player type.

**If using Laxity driver (99.93%)**:
- Should sound nearly identical
- Tiny differences (<0.1%) may exist in complex sections
- Filter accuracy is 0% (known limitation)

**If using other drivers**:
- 70-90% accuracy is normal
- Some differences expected
- Still musically correct

**Common causes of differences**:
1. **Filter not converted** - Filter table not fully supported yet
2. **Wrong driver** - Check output.txt for driver selection
3. **Unsupported player** - Some players can't convert perfectly
4. **Timing differences** - Frame timing may vary slightly

**Solutions**:
1. Verify driver selection is correct
2. Try different drivers manually
3. Check known limitations in CLAUDE.md
4. For critical conversions, use Laxity files only

---

### Can I improve conversion accuracy?

**Answer**: Usually automatic selection is optimal, but you can try:

**1. Manual driver testing**:
```bash
sid-to-sf2.bat file.sid test_laxity.sf2 --driver laxity
sid-to-sf2.bat file.sid test_np20.sf2 --driver np20
sid-to-sf2.bat file.sid test_d11.sf2 --driver driver11

# Compare accuracy
python scripts/validate_sid_accuracy.py file.sid test_laxity.sid
python scripts/validate_sid_accuracy.py file.sid test_np20.sid
python scripts/validate_sid_accuracy.py file.sid test_d11.sid
```

Use whichever gives highest accuracy.

**2. Source file quality**:
- Ensure original SID plays correctly in VICE
- Try different SID version if available
- Check for corrupted files

**3. Player identification**:
If auto-detection fails, you can help it by:
- Checking SID file documentation
- Analyzing code with Python SIDwinder
- Comparing with known player types

**4. Custom driver development**:
For unsupported players, you can create custom drivers (advanced).

---

## Tools

### What is the SF2 Viewer?

**Answer**: GUI tool for viewing SF2 file contents.

**Launch**:
```bash
sf2-viewer.bat [file.sf2]
```

**Features**:
- **Voice Orderlists** - Pattern order for each voice
- **Sequences** - Note sequences with control codes
- **Instruments** - ADSR, waveform, pulse, filter
- **Tables** - Wave, pulse, filter, arpeggio data
- **Export** - Save as text file

**Use cases**:
- Verify conversion quality
- Explore SF2 structure
- Debug issues
- Learn SF2 format
- Export for documentation

**Requirements**: PyQt6 (`pip install PyQt6`)

---

### What is the Conversion Cockpit?

**Answer**: GUI for batch conversion with visual feedback.

**Launch**:
```bash
conversion-cockpit.bat
```

**Features**:
- Visual file browser
- Automatic driver selection display
- One-click batch conversion
- Real-time progress tracking
- Results table with status
- Right-click to view in SF2 Viewer
- Export conversion report

**Workflow**:
1. Add files or folder
2. Review player detection
3. Click "Convert All"
4. Monitor progress
5. View results
6. Right-click to open in viewer

**Requirements**: PyQt6 (`pip install PyQt6`)

---

### What is batch testing?

**Answer**: Automated quality assurance system.

**What it does**:
1. Opens each SF2 file in SID Factory II
2. Starts playback (F5)
3. Plays for 3 seconds
4. Stops playback (F6)
5. Verifies window stability
6. Closes editor
7. Verifies process cleanup
8. Reports results

**Run**:
```bash
test-batch-pyautogui.bat
```

**Results** (example):
```
Total Files:    10
Passed:         10 (100.0%)
Failed:         0 (0.0%)
Processes:      0 remaining
```

**Requirements**:
- PyAutoGUI (`pip install pyautogui pygetwindow pywin32`)
- SID Factory II installed

**Use for**:
- Validating conversions
- QA before distribution
- Regression testing
- CI/CD integration

---

### What is Python siddump?

**Answer**: Pure Python replacement for siddump.exe.

**What it does**:
- Dumps SID register writes frame-by-frame
- Shows voice frequencies, waveforms, ADSR, filter
- Identical output to siddump.exe (100% match)
- Cross-platform (Mac/Linux/Windows)
- Zero dependencies

**Run**:
```bash
# Dump 30 seconds
python pyscript/siddump_complete.py music.sid -t30

# With profiling
python pyscript/siddump_complete.py music.sid -t30 -p
```

**Output** (example):
```
Frame 0000: V1:1234 W:4 A:08 D:00 S:0F R:00  V2:5678 ...
Frame 0001: V1:1234 W:4 A:08 D:00 S:0F R:00  V2:5678 ...
...
```

**Use for**:
- Comparing original vs converted
- Analyzing SID structure
- Debugging conversion issues
- Creating test baselines

---

## Troubleshooting

### Conversion fails with error

**Problem**: Conversion crashes or shows error

**Solution**:

**1. Check error message**:
```bash
sid-to-sf2.bat file.sid output.sf2
# Read error carefully
```

**2. Enable verbose logging**:
```bash
python scripts/sid_to_sf2.py file.sid output.sf2 -vv
```

**3. Common errors**:

**FileNotFoundError**:
```
Solution: Check file path is correct
```

**PermissionError**:
```
Solution: Check file isn't open in another program
```

**Player detection failed**:
```
Solution: Try manual driver selection
sid-to-sf2.bat file.sid output.sf2 --driver driver11
```

**4. Check logs**:
```bash
python scripts/sid_to_sf2.py file.sid output.sf2 --log-file debug.log -vv
type debug.log
```

**5. File issue on GitHub** if problem persists:
https://github.com/MichaelTroelsen/SIDM2conv/issues

---

### SF2 won't open in SID Factory II

**Problem**: Editor shows "Invalid SF2 file" or crashes

**Solution**:

**1. Check validation**:
```bash
type output.txt
```

Look for:
```
[OK] SF2 format valid
```

If `[FAIL]`, file is corrupted.

**2. Verify file size**:
```bash
dir output.sf2
```

Should be 10-40 KB typically. If only 8 KB, conversion failed.

**3. Try SF2 Viewer**:
```bash
sf2-viewer.bat output.sf2
```

If viewer can't open it, file is definitely corrupted.

**4. Reconvert**:
```bash
# Try different driver
sid-to-sf2.bat input.sid output.sf2 --driver laxity
```

**5. Check SID Factory II version**:
- Minimum version: 2023-10-02 or newer
- Download latest from https://blog.chordian.net/sf2/

---

### PyQt6 import error

**Problem**: `ModuleNotFoundError: No module named 'PyQt6'`

**Solution**:

**Install PyQt6**:
```bash
pip install PyQt6
```

**If that fails**:
```bash
# Use Python 3.11 or newer (PyQt6 requirement)
python --version

# Or try with Python3 explicitly
pip3 install PyQt6

# Or with full path
C:\Python311\Scripts\pip.exe install PyQt6
```

**Verify installation**:
```python
python -c "from PyQt6.QtWidgets import QApplication; print('PyQt6 works!')"
```

**Alternative**:
Use command-line tools instead of GUI:
```bash
# Instead of sf2-viewer.bat
sf2-export.bat file.sf2  # Text export

# Instead of conversion-cockpit.bat
# Use batch scripts or custom Python script
```

---

### Process remains after closing editor

**Problem**: SIDFactoryII.exe still running after batch test

**Solution**:

**Check processes**:
```bash
tasklist | findstr SIDFactoryII
```

**Kill manually**:
```bash
taskkill /F /IM SIDFactoryII.exe
```

**This is fixed in v2.9.5+**:
- Batch testing now includes process termination verification
- Automatic force kill if graceful close fails
- Zero lingering processes after tests

**If using older version**:
```bash
# Update to v2.9.5+
git pull origin master
```

**For custom scripts**:
```python
# Add process cleanup
import subprocess

process = subprocess.Popen(["SIDFactoryII.exe", "file.sf2"])
# ... do work ...
process.kill()  # Force termination
process.wait(timeout=2)
```

---

## Advanced

### Can I use SIDM2 in my own scripts?

**Answer**: Absolutely! Python API available.

**Basic conversion**:
```python
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sf2_packer import SF2Packer

packer = SF2Packer()
packer.pack_sid_to_sf2("input.sid", "output.sf2")
```

**With driver selection**:
```python
from sidm2.driver_selector import DriverSelector
from sidm2.laxity_converter import LaxityConverter

selector = DriverSelector()
player_type, driver = selector.select_driver("input.sid")

if driver == "laxity":
    converter = LaxityConverter()
    converter.convert("input.sid", "output.sf2")
```

**Custom workflow**:
```python
from sidm2.sf2_reader import SF2Reader
from sidm2.sf2_writer import SF2Writer

# Read SF2
reader = SF2Reader()
data = reader.read_sf2("input.sf2")

# Modify
data.sequences[0].notes[5] = Note("C-4", instrument=1)

# Write
writer = SF2Writer()
writer.write_sf2("output.sf2", data)
```

**See**: `docs/COMPONENTS_REFERENCE.md` for complete API

---

### How do I contribute to SIDM2?

**Answer**: Contributions welcome!

**Ways to contribute**:

**1. Report bugs**:
- File issue on GitHub
- Include SID file if possible
- Provide error logs

**2. Suggest features**:
- Open GitHub issue
- Describe use case
- Explain expected behavior

**3. Submit code**:
```bash
# Fork repository
git clone https://github.com/YourName/SIDM2conv.git
cd SIDM2conv

# Create branch
git checkout -b feature-name

# Make changes
# ... edit files ...

# Test
test-all.bat

# Commit
git add .
git commit -m "Add feature"

# Push
git push origin feature-name

# Create pull request on GitHub
```

**4. Improve documentation**:
- Fix typos
- Add examples
- Clarify explanations

**5. Share conversions**:
- Test with your SID collection
- Report accuracy results
- Help identify player types

**Guidelines**:
- Follow existing code style
- Add tests for new features
- Update documentation
- Run `test-all.bat` before submitting

---

### Where can I get help?

**Answer**: Multiple resources available!

**Documentation**:
1. **[Getting Started](GETTING_STARTED.md)** - Basics
2. **[Tutorials](TUTORIALS.md)** - Step-by-step
3. **[Best Practices](BEST_PRACTICES.md)** - Expert tips
4. **[Troubleshooting](TROUBLESHOOTING.md)** - Error solutions
5. **[README.md](../../README.md)** - Complete reference

**Community**:
- **GitHub Issues**: https://github.com/MichaelTroelsen/SIDM2conv/issues
- **GitHub Discussions**: https://github.com/MichaelTroelsen/SIDM2conv/discussions

**Quick help**:
```bash
# Command help
python scripts/sid_to_sf2.py --help

# Error diagnosis
python scripts/sid_to_sf2.py file.sid output.sf2 -vv --debug
```

**Bug reports**:
Include:
- Error message
- Input SID file (if possible)
- Output logs (--log-file)
- SIDM2 version
- Python version
- Operating system

**Feature requests**:
Describe:
- Use case
- Expected behavior
- Why it would be useful

---

## Quick Reference

### Most Common Questions

1. **How do I convert?** → `sid-to-sf2.bat input.sid output.sf2`
2. **Which driver?** → Let it auto-select (check output.txt)
3. **Batch convert?** → Use `conversion-cockpit.bat` or `batch-convert-laxity.bat`
4. **View SF2?** → `sf2-viewer.bat file.sf2`
5. **Accuracy?** → 99.93% for Laxity, 100% for SF2-exported

### Quick Commands

```bash
# Convert
sid-to-sf2.bat input.sid output.sf2

# View
sf2-viewer.bat output.sf2

# Batch
conversion-cockpit.bat

# Test
test-batch-pyautogui.bat

# Validate
python scripts/validate_sid_accuracy.py original.sid converted.sid
```

---

## Still Have Questions?

**Check these resources**:
- [Getting Started](GETTING_STARTED.md)
- [Tutorials](TUTORIALS.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [GitHub Issues](https://github.com/MichaelTroelsen/SIDM2conv/issues)

**Or ask on**:
- GitHub Discussions
- Project issues page

---

**Last Updated**: 2025-12-26
**Version**: 2.9.6
**Status**: Production Ready
