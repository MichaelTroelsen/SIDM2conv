# SIDM2 Tutorials

**Version**: 2.9.6
**Updated**: 2025-12-26

Step-by-step tutorials for common SIDM2 workflows.

---

## Tutorial Index

### Beginner
1. [Your First Conversion](#tutorial-1-your-first-conversion) - Convert a SID file
2. [Viewing SF2 Files](#tutorial-2-viewing-sf2-files) - Explore converted data
3. [Understanding Driver Selection](#tutorial-3-understanding-driver-selection) - How automatic selection works

### Intermediate
4. [Batch Converting a Collection](#tutorial-4-batch-converting-a-collection) - Process multiple files
5. [Using the Conversion Cockpit](#tutorial-5-using-the-conversion-cockpit) - GUI workflow
6. [Editing in SID Factory II](#tutorial-6-editing-in-sid-factory-ii) - Complete edit workflow

### Advanced
7. [Validating Conversion Accuracy](#tutorial-7-validating-conversion-accuracy) - Frame-level analysis
8. [Batch Testing Your Files](#tutorial-8-batch-testing-your-files) - Automated QA
9. [Custom Python Workflows](#tutorial-9-custom-python-workflows) - Scripting

---

## Tutorial 1: Your First Conversion

**Goal**: Convert a single SID file to SF2 format

**Time**: 2 minutes

**Prerequisites**: Python 3.8+ installed

### Step 1: Get a Test File

We'll use the included test file `Angular.sid`:

```bash
# Verify it exists
dir SID\Angular.sid
```

If not found, download any SID file from [HVSC](https://www.hvsc.c64.org/).

### Step 2: Run Conversion

**Windows**:
```bash
sid-to-sf2.bat SID/Angular.sid test.sf2
```

**Mac/Linux**:
```bash
python scripts/sid_to_sf2.py SID/Angular.sid test.sf2
```

### Step 3: Check Output

You should see:

```
Analyzing SID file: SID/Angular.sid
Player identified: Unknown
Driver selected: driver11 (Safe default for generic SID files)
Expected accuracy: Standard conversion quality

Converting...
[OK] Conversion complete

Validating SF2 format...
[OK] SF2 format valid

Output written to: test.sf2
Driver info written to: test.txt
```

### Step 4: Verify Files

```bash
# Check SF2 file (should be ~10KB)
dir test.sf2

# Check driver info
type test.txt
```

The `.txt` file contains:
- Player type identified
- Driver selected
- Expected accuracy
- SF2 validation results

### Success!

You've converted your first SID file. The SF2 is ready to open in SID Factory II.

**Next**: [Tutorial 2](#tutorial-2-viewing-sf2-files) - View the converted file

---

## Tutorial 2: Viewing SF2 Files

**Goal**: Explore SF2 file contents using the SF2 Viewer

**Time**: 3 minutes

**Prerequisites**:
- Completed Tutorial 1
- PyQt6 installed (`pip install PyQt6`)

### Step 1: Launch SF2 Viewer

**Windows**:
```bash
sf2-viewer.bat test.sf2
```

**Mac/Linux**:
```bash
python pyscript/sf2_viewer_gui.py test.sf2
```

### Step 2: Explore the Interface

The viewer shows 6 tabs:

1. **Voice 1/2/3 Orderlists** - Pattern order for each voice
2. **Sequences** - Note and control sequences
3. **Instruments** - ADSR, waveform, pulse, filter settings
4. **Tables** - Wave, pulse, filter, arpeggio data

### Step 3: View Voice 1 Orderlist

Click **"Voice 1 Orderlist"** tab:

```
Position | Sequence | Transpose
---------|----------|----------
00       | 01       | 00
01       | 02       | 00
02       | 03       | 00
...
```

This shows which sequences play in which order.

### Step 4: View Sequences

Click **"Sequences"** tab and select a sequence:

```
Sequence 01:
00: C-4  INST:01
01: ---  ----
02: E-4  INST:01
03: ---  ----
...
```

Shows notes, instruments, and control codes.

### Step 5: View Instruments

Click **"Instruments"** tab:

```
Instrument 01:
  ADSR: A=08 D=00 S=0F R=00
  Waveform: Sawtooth
  Pulse Width: 0800
  Filter: Enabled (Cutoff: 0800)
```

Shows complete instrument settings.

### Step 6: Export as Text

Click **"Export as Text"** button:

```bash
# Creates test_export.txt with complete dump
```

### Success!

You can now view and export SF2 file contents.

**Next**: [Tutorial 3](#tutorial-3-understanding-driver-selection) - Learn about drivers

---

## Tutorial 3: Understanding Driver Selection

**Goal**: Learn how SIDM2 automatically selects the best driver

**Time**: 5 minutes

**Prerequisites**: Basic understanding of SID files

### Step 1: Identify Player Types

SIDM2 can identify these player types:

- **Laxity NewPlayer v21** - Custom player (99.93% accuracy)
- **SF2-exported** - Already in SF2 format (100% roundtrip)
- **NewPlayer 20.G4** - Standard player (70-90% accuracy)
- **Rob Hubbard/Martin Galway** - Classic formats
- **Unknown** - Unidentified players

### Step 2: Convert a Laxity File

```bash
# Get a Laxity file from your collection
sid-to-sf2.bat SID/laxity_song.sid output.sf2

# Check the output
type output.txt
```

You'll see:

```
Player identified: Laxity NewPlayer v21
Driver selected: laxity
Expected accuracy: 99.93% frame accuracy
```

### Step 3: Convert an SF2-Exported File

```bash
# Export an SF2 to SID first
python scripts/sf2_to_sid.py G5/examples/Driver_11_Test.sf2 temp.sid

# Convert back
sid-to-sf2.bat temp.sid roundtrip.sf2
type roundtrip.txt
```

Output:

```
Player identified: SF2-exported (Driver 11)
Driver selected: driver11
Expected accuracy: 100% (perfect roundtrip)
```

### Step 4: Convert an Unknown File

```bash
sid-to-sf2.bat SID/unknown_song.sid test.sf2
type test.txt
```

Output:

```
Player identified: Unknown
Driver selected: driver11
Expected accuracy: Standard conversion quality
```

### Step 5: Manual Override

Sometimes you may want to override auto-selection:

```bash
# Force Laxity driver
sid-to-sf2.bat SID/song.sid output.sf2 --driver laxity

# Force NP20 driver
sid-to-sf2.bat SID/song.sid output.sf2 --driver np20
```

### Understanding the Matrix

| Source | Auto Driver | Accuracy | When to Override |
|--------|------------|----------|------------------|
| Laxity NP21 | `laxity` | 99.93% | Never (optimal) |
| SF2-exported | `driver11` | 100% | Never (perfect) |
| NP20.G4 | `np20` | 70-90% | Never (optimal) |
| Unknown | `driver11` | Varies | Try other drivers if issues |

### Success!

You understand how automatic driver selection works.

**Next**: [Tutorial 4](#tutorial-4-batch-converting-a-collection) - Convert multiple files

---

## Tutorial 4: Batch Converting a Collection

**Goal**: Convert an entire folder of SID files

**Time**: 5-10 minutes

**Prerequisites**: Folder of SID files

### Step 1: Organize Your Files

```bash
# Create structure
mkdir SID
mkdir SF2

# Copy your SID files to SID folder
copy C:\Music\*.sid SID\
```

### Step 2: Option A - Use Built-in Batch Script

For Laxity files:

```bash
batch-convert-laxity.bat
```

This converts all SID files in `SID/` folder using Laxity driver, outputs to `SF2/`.

### Step 3: Option B - Custom Batch Script

Create `convert_all.bat`:

```batch
@echo off
echo Converting all SID files...

for %%f in (SID\*.sid) do (
    echo Converting %%~nf.sid...
    python scripts/sid_to_sf2.py "%%f" "SF2\%%~nf.sf2"
)

echo Done! Check SF2 folder for results.
pause
```

Run it:

```bash
convert_all.bat
```

### Step 4: Option C - Use Python Script

Create `batch_convert.py`:

```python
import os
import subprocess
from pathlib import Path

sid_dir = Path("SID")
sf2_dir = Path("SF2")
sf2_dir.mkdir(exist_ok=True)

sid_files = list(sid_dir.glob("*.sid"))
print(f"Found {len(sid_files)} SID files")

for i, sid_file in enumerate(sid_files, 1):
    sf2_file = sf2_dir / f"{sid_file.stem}.sf2"
    print(f"[{i}/{len(sid_files)}] Converting {sid_file.name}...")

    result = subprocess.run([
        "python", "scripts/sid_to_sf2.py",
        str(sid_file), str(sf2_file)
    ])

    if result.returncode == 0:
        print(f"  [OK] Created {sf2_file.name}")
    else:
        print(f"  [FAIL] Conversion failed")

print(f"\nCompleted: {len(sid_files)} files")
```

Run it:

```bash
python batch_convert.py
```

### Step 5: Verify Results

```bash
# Check output folder
dir SF2

# Check a few .txt files for driver selection
type SF2\song1.txt
type SF2\song2.txt
```

### Step 6: Review Conversions

Create a summary script `summarize_results.py`:

```python
from pathlib import Path
import re

sf2_dir = Path("SF2")
txt_files = list(sf2_dir.glob("*.txt"))

drivers = {}
for txt_file in txt_files:
    content = txt_file.read_text()
    match = re.search(r"Driver selected: (\w+)", content)
    if match:
        driver = match.group(1)
        drivers[driver] = drivers.get(driver, 0) + 1

print("Conversion Summary:")
print("=" * 40)
for driver, count in sorted(drivers.items()):
    print(f"{driver:15} {count:3} files")
print("=" * 40)
print(f"Total:          {len(txt_files):3} files")
```

Run it:

```bash
python summarize_results.py
```

Output:

```
Conversion Summary:
========================================
driver11        42 files
laxity          15 files
np20             8 files
========================================
Total:          65 files
```

### Success!

You've batch converted an entire collection.

**Next**: [Tutorial 5](#tutorial-5-using-the-conversion-cockpit) - Use the GUI

---

## Tutorial 5: Using the Conversion Cockpit

**Goal**: Use the GUI for batch conversion with visual feedback

**Time**: 5 minutes

**Prerequisites**: PyQt6 installed (`pip install PyQt6`)

### Step 1: Launch Conversion Cockpit

```bash
conversion-cockpit.bat
```

Or:

```bash
python pyscript/conversion_cockpit_gui.py
```

### Step 2: Add Files

**Option A - Add Individual Files**:
1. Click **"Add Files"**
2. Browse to SID folder
3. Select multiple SID files (Ctrl+click)
4. Click **"Open"**

**Option B - Add Entire Folder**:
1. Click **"Add Folder"**
2. Browse to SID folder
3. Click **"Select Folder"**
4. All SID files added automatically

### Step 3: Review File List

The table shows:

| Column | Description |
|--------|-------------|
| **Filename** | SID file name |
| **Player** | Detected player type |
| **Driver** | Auto-selected driver |
| **Status** | Pending/Converting/Complete/Failed |
| **Output** | Output SF2 path |

### Step 4: Configure Output

1. Click **"Browse"** next to "Output Directory"
2. Select SF2 output folder
3. Output files will be created there

### Step 5: Start Conversion

1. Click **"Convert All"** button
2. Watch progress bar
3. Status updates in real-time:
   - Yellow = Converting
   - Green = Complete
   - Red = Failed

### Step 6: View Results

**In the table**:
- Green rows = Successful conversion
- Red rows = Failed (check error message)

**Right-click menu**:
- **View SF2** - Opens SF2 Viewer
- **Open Folder** - Opens output directory
- **Copy Path** - Copies SF2 path to clipboard

### Step 7: Export Results

1. Click **"Export Log"**
2. Choose location
3. Creates summary report:

```
Conversion Report
================
Date: 2025-12-26
Total Files: 25
Successful: 24
Failed: 1

Details:
--------
song1.sid -> song1.sf2 [OK] (driver11)
song2.sid -> song2.sf2 [OK] (laxity)
...
```

### Success!

You've completed a GUI-based batch conversion.

**Next**: [Tutorial 6](#tutorial-6-editing-in-sid-factory-ii) - Edit converted files

---

## Tutorial 6: Editing in SID Factory II

**Goal**: Complete workflow from SID → SF2 → Edit → SID

**Time**: 10 minutes

**Prerequisites**: SID Factory II installed

### Step 1: Convert SID to SF2

```bash
sid-to-sf2.bat SID/original.sid editable.sf2
```

### Step 2: Open in SID Factory II

1. Launch SID Factory II
2. File → Open
3. Browse to `editable.sf2`
4. Click **Open**

### Step 3: Explore the File

**View Orderlists**:
- Click **"Orderlist"** tab
- See pattern order for each voice

**View Sequences**:
- Click **"Sequence"** tab
- Browse sequences with arrow keys
- See notes, instruments, effects

**View Instruments**:
- Click **"Instrument"** tab
- See ADSR, waveform, pulse, filter settings

**View Tables**:
- Click **"Tables"** tab
- Wave, pulse, filter, arpeggio tables

### Step 4: Make Edits

**Example 1: Change a Note**:
1. Go to Sequence tab
2. Select sequence 01
3. Move to note C-4
4. Press D key to change to D-4

**Example 2: Modify Instrument**:
1. Go to Instrument tab
2. Select instrument 01
3. Change Attack from 08 to 0F (faster attack)
4. Change Waveform from Sawtooth to Pulse

**Example 3: Edit Orderlist**:
1. Go to Orderlist tab
2. Select Voice 1
3. Insert new pattern entry
4. Set sequence and transpose values

### Step 5: Test Your Changes

1. Press **F5** to play
2. Listen to modifications
3. Press **F6** to stop
4. Adjust until satisfied

### Step 6: Save SF2

1. File → Save
2. Choose filename: `edited.sf2`
3. Click **Save**

### Step 7: Export to SID

```bash
python scripts/sf2_to_sid.py edited.sf2 final.sid
```

### Step 8: Test in VICE

```bash
C:\winvice\bin\vsid.exe final.sid
```

Or play in any SID player.

### Step 9: Compare Original vs Edited

**Original**:
```bash
python pyscript/siddump_complete.py SID/original.sid -t30
```

**Edited**:
```bash
python pyscript/siddump_complete.py final.sid -t30
```

Compare the dumps to see your changes.

### Success!

You've completed a full edit workflow.

**Next**: [Tutorial 7](#tutorial-7-validating-conversion-accuracy) - Validate accuracy

---

## Tutorial 7: Validating Conversion Accuracy

**Goal**: Measure frame-by-frame accuracy of conversion

**Time**: 5 minutes

**Prerequisites**: Original SID + converted SID

### Step 1: Prepare Files

```bash
# Original SID
copy SID\original.sid test\

# Convert to SF2
sid-to-sf2.bat test/original.sid test/converted.sf2

# Export SF2 back to SID
python scripts/sf2_to_sid.py test/converted.sf2 test/converted.sid
```

### Step 2: Run Validation

```bash
python scripts/validate_sid_accuracy.py test/original.sid test/converted.sid
```

### Step 3: Review Results

Output:

```
Frame-by-Frame Accuracy Analysis
=================================

File 1: test/original.sid
File 2: test/converted.sid

Analyzing 1500 frames (60 seconds)...

Results:
--------
Total Frames:        1500
Matching Frames:     1498
Accuracy:            99.87%

Register Differences:
Voice 1 Frequency:   2 frames
Voice 2 Waveform:    0 frames
Voice 3 Gate:        0 frames
Filter Cutoff:       0 frames

Summary: EXCELLENT (>99%)
```

### Step 4: Detailed Analysis

For deep dive, use Python siddump:

```bash
# Dump original (30 seconds = 1800 frames)
python pyscript/siddump_complete.py test/original.sid -t30 > original.txt

# Dump converted
python pyscript/siddump_complete.py test/converted.sid -t30 > converted.txt

# Compare
fc original.txt converted.txt
```

Or use diff tool:

```bash
diff -u original.txt converted.txt | head -100
```

### Step 5: Analyze Differences

**Perfect match (100%)**:
```
Files are identical
```

**Near-perfect (99%+)**:
```
< Frame 0042: V1:1234 V2:5678 V3:9ABC
> Frame 0042: V1:1235 V2:5678 V3:9ABC
```

1-2 bit differences are normal for complex players.

**Poor match (<90%)**:
```
Multiple register differences every frame
```

May indicate wrong driver - try different driver.

### Step 6: Trace Analysis

For detailed investigation:

```bash
# Trace original
python pyscript/sidwinder_trace.py --trace original_trace.txt --frames 1500 test/original.sid

# Trace converted
python pyscript/sidwinder_trace.py --trace converted_trace.txt --frames 1500 test/converted.sid

# Compare traces
diff -u original_trace.txt converted_trace.txt
```

Shows exact SID register writes frame-by-frame.

### Success!

You can now validate conversion accuracy scientifically.

**Next**: [Tutorial 8](#tutorial-8-batch-testing-your-files) - Automated QA

---

## Tutorial 8: Batch Testing Your Files

**Goal**: Automatically test multiple SF2 files for quality assurance

**Time**: 10 minutes

**Prerequisites**:
- PyAutoGUI installed (`pip install pyautogui pygetwindow pywin32`)
- SID Factory II installed

### Step 1: Prepare Test Files

```bash
# Convert some test files
sid-to-sf2.bat SID/test1.sid SF2/test1.sf2
sid-to-sf2.bat SID/test2.sid SF2/test2.sf2
sid-to-sf2.bat SID/test3.sid SF2/test3.sf2
```

### Step 2: Basic Batch Test

```bash
# Test all SF2 files in output directory
test-batch-pyautogui.bat
```

### Step 3: Watch Automation

You'll see:

```
Batch Testing SF2 Files with PyAutoGUI Automation
==================================================

Finding SF2 files in: output
Found 10 SF2 files to test

[1/10] Testing: test1.sf2
  Launching editor...
  [OK] Editor launched
  [OK] File loaded: test1.sf2
  Testing playback (3s)...
  [OK] Playback control successful
  Verifying stability (2s)...
  [OK] Window stable
  Closing editor...
  [OK] Editor closed
  [OK] Process terminated
  Duration: 8.5s

[2/10] Testing: test2.sf2
  ...
```

### Step 4: Review Results

Final summary:

```
===========================================
Batch Test Results
===========================================
Total Files:    10
Passed:         10 (100.0%)
Failed:         0 (0.0%)
Total Duration: 95.2 seconds
Avg Per File:   9.5 seconds
===========================================

Process Cleanup Verification:
Remaining SIDFactoryII.exe processes: 0
[OK] All processes cleaned up successfully
```

### Step 5: Custom Test Parameters

```bash
# Test specific directory
test-batch-pyautogui.bat --directory G5/examples

# Limit number of files
test-batch-pyautogui.bat --max-files 5

# Longer playback test
test-batch-pyautogui.bat --playback 10

# Longer stability check
test-batch-pyautogui.bat --stability 5

# Custom timeout
test-batch-pyautogui.bat --timeout 30
```

### Step 6: Troubleshooting Failed Tests

If a test fails:

```
[5/10] Testing: problematic.sf2
  Launching editor...
  [OK] Editor launched
  [FAIL] File failed to load
  Duration: 5.2s
```

**Check**:
1. Open file manually in SID Factory II
2. Check if SF2 is valid: `sf2-viewer.bat problematic.sf2`
3. Check validation: `type problematic.txt`
4. Try reconverting with different driver

### Step 7: Integration with CI/CD

The batch test system is integrated with GitHub Actions:

```yaml
# .github/workflows/batch-testing.yml
- name: Run batch test
  run: test-batch-pyautogui.bat --max-files 10
```

Runs automatically on every push!

### Success!

You can now run automated QA on your conversions.

**Next**: [Tutorial 9](#tutorial-9-custom-python-workflows) - Advanced scripting

---

## Tutorial 9: Custom Python Workflows

**Goal**: Create custom automation scripts using SIDM2 components

**Time**: 15 minutes

**Prerequisites**: Python programming knowledge

### Step 1: Import SIDM2 Components

```python
# conversion_workflow.py
from pathlib import Path
import sys

# Add sidm2 to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.laxity_parser import LaxityParser
from sidm2.sf2_writer import SF2Writer
from sidm2.driver_selector import DriverSelector
from sidm2.sf2_packer import SF2Packer
```

### Step 2: Custom Conversion Function

```python
def convert_with_validation(sid_path, sf2_path, min_accuracy=95.0):
    """Convert SID to SF2 with accuracy validation"""

    # Select driver
    selector = DriverSelector()
    player_type, driver = selector.select_driver(sid_path)

    print(f"Player: {player_type}")
    print(f"Driver: {driver}")

    # Convert
    if driver == "laxity":
        parser = LaxityParser()
        data = parser.parse_sid(sid_path)

        writer = SF2Writer()
        writer.write_sf2(sf2_path, data)

        expected_accuracy = 99.93
    else:
        # Use standard conversion
        packer = SF2Packer()
        packer.pack_sid_to_sf2(sid_path, sf2_path)
        expected_accuracy = 85.0

    # Validate
    if expected_accuracy < min_accuracy:
        print(f"Warning: Expected accuracy {expected_accuracy}% is below minimum {min_accuracy}%")
        return False

    print(f"[OK] Conversion complete (expected accuracy: {expected_accuracy}%)")
    return True
```

### Step 3: Batch Analysis Script

```python
def analyze_collection(sid_dir):
    """Analyze SID collection and categorize by player type"""

    sid_files = list(Path(sid_dir).glob("*.sid"))
    selector = DriverSelector()

    categories = {}

    for sid_file in sid_files:
        player_type, driver = selector.select_driver(str(sid_file))

        if player_type not in categories:
            categories[player_type] = []

        categories[player_type].append(sid_file.name)

    # Report
    print("Collection Analysis")
    print("=" * 60)

    for player_type, files in sorted(categories.items()):
        print(f"\n{player_type}: {len(files)} files")
        for filename in files[:5]:  # Show first 5
            print(f"  - {filename}")
        if len(files) > 5:
            print(f"  ... and {len(files) - 5} more")

    print(f"\nTotal: {len(sid_files)} files")

    return categories
```

### Step 4: Quality Control Script

```python
def quality_check(sf2_path):
    """Check SF2 file quality"""

    from sidm2.sf2_reader import SF2Reader

    reader = SF2Reader()
    data = reader.read_sf2(sf2_path)

    issues = []

    # Check for empty sequences
    for i, seq in enumerate(data.sequences):
        if len(seq) == 0:
            issues.append(f"Sequence {i:02d} is empty")

    # Check for unused instruments
    used_instruments = set()
    for seq in data.sequences:
        for note in seq:
            if note.instrument:
                used_instruments.add(note.instrument)

    for i in range(len(data.instruments)):
        if i not in used_instruments:
            issues.append(f"Instrument {i:02d} is unused")

    # Report
    if issues:
        print(f"Quality Issues ({len(issues)}):")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("[OK] Quality check passed")
        return True
```

### Step 5: Automated Pipeline

```python
def automated_pipeline(sid_dir, sf2_dir, validate=True):
    """Complete automated conversion pipeline"""

    sid_dir = Path(sid_dir)
    sf2_dir = Path(sf2_dir)
    sf2_dir.mkdir(exist_ok=True)

    sid_files = list(sid_dir.glob("*.sid"))

    results = {
        "success": [],
        "failed": [],
        "low_quality": []
    }

    for i, sid_file in enumerate(sid_files, 1):
        print(f"\n[{i}/{len(sid_files)}] Processing {sid_file.name}")

        sf2_file = sf2_dir / f"{sid_file.stem}.sf2"

        # Convert
        try:
            success = convert_with_validation(str(sid_file), str(sf2_file))
            if not success:
                results["failed"].append(sid_file.name)
                continue
        except Exception as e:
            print(f"[FAIL] Conversion error: {e}")
            results["failed"].append(sid_file.name)
            continue

        # Validate quality
        if validate:
            if not quality_check(str(sf2_file)):
                results["low_quality"].append(sid_file.name)
            else:
                results["success"].append(sid_file.name)
        else:
            results["success"].append(sid_file.name)

    # Final report
    print("\n" + "=" * 60)
    print("Pipeline Complete")
    print("=" * 60)
    print(f"Successful:  {len(results['success'])}")
    print(f"Failed:      {len(results['failed'])}")
    print(f"Low Quality: {len(results['low_quality'])}")

    return results
```

### Step 6: Run Your Workflow

```python
# main.py
if __name__ == "__main__":
    # Analyze collection
    categories = analyze_collection("SID")

    # Run pipeline
    results = automated_pipeline("SID", "SF2", validate=True)

    # Export report
    with open("pipeline_report.txt", "w") as f:
        f.write("Conversion Pipeline Report\n")
        f.write("=" * 60 + "\n")
        f.write(f"Successful: {len(results['success'])}\n")
        for name in results['success']:
            f.write(f"  [OK] {name}\n")
        f.write(f"\nFailed: {len(results['failed'])}\n")
        for name in results['failed']:
            f.write(f"  [FAIL] {name}\n")
```

Execute:

```bash
python main.py
```

### Success!

You can now create custom Python workflows using SIDM2 components.

**Next Steps**: Explore [Best Practices](BEST_PRACTICES.md) for optimization tips

---

## Tutorial Quick Reference

| # | Tutorial | Time | Difficulty |
|---|----------|------|------------|
| 1 | Your First Conversion | 2 min | Beginner |
| 2 | Viewing SF2 Files | 3 min | Beginner |
| 3 | Understanding Driver Selection | 5 min | Beginner |
| 4 | Batch Converting a Collection | 10 min | Intermediate |
| 5 | Using the Conversion Cockpit | 5 min | Intermediate |
| 6 | Editing in SID Factory II | 10 min | Intermediate |
| 7 | Validating Conversion Accuracy | 5 min | Advanced |
| 8 | Batch Testing Your Files | 10 min | Advanced |
| 9 | Custom Python Workflows | 15 min | Advanced |

---

## Additional Resources

### Documentation
- **[Getting Started](GETTING_STARTED.md)** - Installation and basics
- **[Best Practices](BEST_PRACTICES.md)** - Expert tips
- **[FAQ](FAQ.md)** - Common questions

### Technical References
- **[SF2 Format Spec](../SF2_FORMAT_SPEC.md)** - Format details
- **[Components Reference](../COMPONENTS_REFERENCE.md)** - Python API
- **[Architecture](../ARCHITECTURE.md)** - System design

### Troubleshooting
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - Error solutions
- **[Logging Guide](LOGGING_AND_ERROR_HANDLING_GUIDE.md)** - Debug techniques

---

**Completed all tutorials?** You're now a SIDM2 expert!

**Questions?** Check the [FAQ](FAQ.md) or file an issue on GitHub.

---

**Last Updated**: 2025-12-26
**Version**: 2.9.6
**Status**: Production Ready
