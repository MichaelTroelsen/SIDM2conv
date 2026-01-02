# Accuracy Heatmap Tool - User Guide

**Version**: 1.0.0
**Date**: 2026-01-01
**Part of**: SIDM2 v3.0.3

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Understanding the Heatmap](#understanding-the-heatmap)
4. [Visualization Modes](#visualization-modes)
5. [Reading Patterns](#reading-patterns)
6. [Interactive Features](#interactive-features)
7. [Use Cases](#use-cases)
8. [Command Reference](#command-reference)
9. [Interpreting Colors](#interpreting-colors)
10. [Advanced Usage](#advanced-usage)
11. [Troubleshooting](#troubleshooting)
12. [Tips & Tricks](#tips--tricks)

---

## Overview

The **Accuracy Heatmap Tool** generates interactive Canvas-based visualizations showing frame-by-frame, register-by-register accuracy between two SID files. It's perfect for:

- Identifying problematic registers in conversions
- Finding timing drift issues
- Spotting systematic differences
- Validating conversion accuracy
- Understanding where conversions fail

### What It Does

1. **Traces both SID files** frame-by-frame using the CPU emulator
2. **Compares register writes** for all 29 SID registers across all frames
3. **Generates interactive heatmap** with 4 visualization modes
4. **Shows exact values** on hover for detailed analysis
5. **Provides zoom/pan** for exploring large datasets

### Key Features

- **4 Visualization Modes**: Binary match, delta magnitude, register groups, frame accuracy
- **Interactive Tooltips**: Hover to see exact register values and differences
- **Zoom Controls**: Zoom in/out to focus on specific frame ranges
- **Canvas Rendering**: Fast, smooth rendering for large heatmaps (1000+ frames)
- **Accuracy Statistics**: Overall accuracy, matches/total, dimensions
- **Self-Contained HTML**: Single file with no external dependencies

---

## Quick Start

### Basic Usage

Compare two SID files and generate a heatmap:

```bash
accuracy-heatmap.bat original.sid converted.sid
```

This generates `heatmap_<timestamp>.html` with:
- 300 frames traced
- Mode 1 (Binary Match/Mismatch) active by default
- Interactive tooltips, zoom, and mode switching

### Specify Frame Count

Trace more frames for longer analysis:

```bash
accuracy-heatmap.bat file_a.sid file_b.sid --frames 1500
```

### Custom Output File

Specify output filename:

```bash
accuracy-heatmap.bat original.sid converted.sid --output my_analysis.html
```

### Verbose Mode

See detailed progress:

```bash
accuracy-heatmap.bat file_a.sid file_b.sid -v
```

Debug mode (very detailed):

```bash
accuracy-heatmap.bat file_a.sid file_b.sid -vv
```

---

## Understanding the Heatmap

### Layout

The heatmap displays data in a grid:

- **X-Axis (Horizontal)**: Frame numbers (0, 50, 100, 150, ...)
- **Y-Axis (Vertical)**: 29 SID registers (V1_FREQ_LO, V1_FREQ_HI, ..., ENV3)

Each cell represents one register at one frame.

### Register Order (Y-Axis)

The 29 SID registers are displayed from top to bottom:

**Voice 1 (Registers 0-6)**:
- V1_FREQ_LO (0x00)
- V1_FREQ_HI (0x01)
- V1_PW_LO (0x02)
- V1_PW_HI (0x03)
- V1_CTRL (0x04)
- V1_AD (0x05)
- V1_SR (0x06)

**Voice 2 (Registers 7-13)**:
- V2_FREQ_LO (0x07)
- V2_FREQ_HI (0x08)
- V2_PW_LO (0x09)
- V2_PW_HI (0x0A)
- V2_CTRL (0x0B)
- V2_AD (0x0C)
- V2_SR (0x0D)

**Voice 3 (Registers 14-20)**:
- V3_FREQ_LO (0x0E)
- V3_FREQ_HI (0x0F)
- V3_PW_LO (0x10)
- V3_PW_HI (0x11)
- V3_CTRL (0x12)
- V3_AD (0x13)
- V3_SR (0x14)

**Filter & Global (Registers 21-28)**:
- FC_LO (0x15)
- FC_HI (0x16)
- RES_FILT (0x17)
- MODE_VOL (0x18)
- POT_X (0x19) - Read-only
- POT_Y (0x1A) - Read-only
- OSC3_RAND (0x1B) - Read-only
- ENV3 (0x1C) - Read-only

### Frame Timeline (X-Axis)

- Each column = 1 frame (1/50th or 1/60th second depending on timing mode)
- Frame numbers shown every 50 frames
- Scroll horizontally to see later frames

---

## Visualization Modes

The heatmap supports 4 different visualization modes, switchable via the sidebar.

### Mode 1: Binary Match/Mismatch

**What It Shows**: Simple green/red coloring based on whether register values match.

**Color Meaning**:
- **Green**: Values match exactly (File A = File B)
- **Red**: Values differ (File A ≠ File B)

**Best For**:
- Quick overview of where differences occur
- Identifying problematic register clusters
- Finding systematic mismatches

**Example Interpretation**:
- Solid green column = Perfect frame (all 29 registers match)
- Solid red column = Complete mismatch (all registers differ)
- Mixed column = Partial match (some registers match, others differ)

### Mode 2: Value Delta Magnitude

**What It Shows**: Color intensity based on the magnitude of the difference.

**Color Meaning**:
- **Light Green**: No difference (delta = 0)
- **Yellow/Orange**: Medium difference (delta ≈ 128)
- **Red**: Maximum difference (delta = 255)

**Best For**:
- Identifying how severe differences are
- Finding registers with small vs large errors
- Prioritizing fixes (fix large deltas first)

**Example Interpretation**:
- Light green = Values very close (e.g., 0x10 vs 0x11)
- Red = Values very different (e.g., 0x00 vs 0xFF)

### Mode 3: Register Group Highlighting

**What It Shows**: Different colors for Voice 1/2/3 and Filter, with brightness indicating match/mismatch.

**Color Meaning**:
- **Red** (bright): Voice 1 match, **Red** (dark): Voice 1 mismatch
- **Blue** (bright): Voice 2 match, **Blue** (dark): Voice 2 mismatch
- **Green** (bright): Voice 3 match, **Green** (dark): Voice 3 mismatch
- **Orange** (bright): Filter match, **Orange** (dark): Filter mismatch

**Best For**:
- Identifying which voices have problems
- Seeing voice-specific patterns
- Diagnosing polyphonic issues

**Example Interpretation**:
- Bright red rows at top = Voice 1 working perfectly
- Dark blue rows in middle = Voice 2 has issues
- Mixed brightness = Some voices work, others don't

### Mode 4: Frame Accuracy Summary

**What It Shows**: Per-frame accuracy percentage, with each column colored by overall frame accuracy.

**Color Meaning**:
- **Green**: 100% accuracy (all 29 registers match)
- **Yellow**: 50% accuracy (about half match)
- **Red**: 0% accuracy (no registers match)

**Best For**:
- Identifying problem frames
- Finding timing drift (gradual color change)
- Quick overview of overall accuracy trend

**Example Interpretation**:
- Solid green = Perfect conversion
- Gradual red → green = Initialization issues, stabilizes later
- Green → red = Timing drift or phase shift

---

## Reading Patterns

Learn to recognize common accuracy patterns in the heatmap.

### Vertical Lines (Consistent Register Issue)

**Pattern**: Solid vertical line (same color across many frames)

**Meaning**: One specific register consistently differs or matches

**Likely Causes**:
- Register not implemented in conversion
- Systematic calculation error
- Missing feature (e.g., filter not converted)

**Action**: Focus on that specific register's conversion code

### Horizontal Lines (Frame-Specific Issue)

**Pattern**: Solid horizontal line (all registers same color for one frame)

**Meaning**: Specific frame has unusual behavior

**Likely Causes**:
- Init frame differences (often frame 0)
- Timing synchronization issue
- Loop boundary problem

**Action**: Investigate that specific frame's execution

### Diagonal Lines (Timing Drift)

**Pattern**: Diagonal pattern from top-left to bottom-right

**Meaning**: Gradual timing shift between files

**Likely Causes**:
- Clock speed difference
- Raster timing mismatch
- Cycle count drift

**Action**: Check timing synchronization code

### Clusters (Localized Problems)

**Pattern**: Rectangle or block of same color

**Meaning**: Multiple registers affected during specific frame range

**Likely Causes**:
- Feature used only in that section (e.g., filter sweep)
- Data table corruption
- Phase boundary issue

**Action**: Check what happens musically in that frame range

### Checkerboard (Alternating Pattern)

**Pattern**: Alternating colors like a checkerboard

**Meaning**: Value oscillating between two states

**Likely Causes**:
- Off-by-one frame error
- ADSR envelope mismatch
- Vibrato timing issue

**Action**: Compare frame N and frame N+1 values

### Solid Color Blocks

**Pattern**: Large uniform areas of single color

**Meaning**:
- **Solid Green**: Perfect match for that region
- **Solid Red**: Complete mismatch for that region

**Likely Causes**:
- Working feature (green) vs broken feature (red)
- Different playback routine used

**Action**: Identify feature boundaries, fix broken regions

---

## Interactive Features

### Hover Tooltips

**How**: Move mouse over any cell in the heatmap

**Shows**:
- Frame number
- Register name (e.g., "V1_FREQ_HI")
- File A value (hex and decimal)
- File B value (hex and decimal)
- Delta (absolute difference)
- Match status ([MATCH] or [DIFF])

**Example Tooltip**:
```
Frame 42, V1_FREQ_HI
File A: $1F (31)
File B: $20 (32)
Delta: 1 [DIFF]
```

**Usage**: Hover to inspect exact values causing mismatches

### Zoom Controls

**Buttons**:
- **Zoom In (+)**: Increase cell size (see more detail)
- **Zoom Out (-)**: Decrease cell size (see more frames)
- **Reset**: Return to default zoom level

**Keyboard Shortcuts**:
- `+` or `=`: Zoom in
- `-`: Zoom out
- `0`: Reset zoom

**Zoom Range**: 0.25x (25%) to 5.0x (500%)

**Usage**: Zoom in to focus on specific frame ranges or registers

### Scrolling

**How**: Use browser scrollbars or mouse wheel

**Purpose**:
- Scroll horizontally to see later frames
- Scroll vertically to see different registers

**Tip**: Zoom in first, then scroll to explore details

### Mode Switching

**How**: Click mode buttons in sidebar (or radio buttons)

**Modes**:
1. Binary Match/Mismatch
2. Value Delta Magnitude
3. Register Group Highlighting
4. Frame Accuracy Summary

**Effect**: Heatmap redraws immediately with new color scheme

**Legend**: Updates automatically to show current mode's color meanings

---

## Use Cases

### 1. Validating SID Conversion Accuracy

**Goal**: Verify converted SF2 file matches original SID

**Steps**:
1. Convert SID to SF2, then back to SID
2. Generate heatmap comparing original vs round-trip
3. Look for green (perfect match)
4. Investigate any red areas (differences)

**Interpretation**:
- 100% green = Perfect conversion
- Some red = Identify which registers failed conversion
- Lots of red = Major conversion issues

### 2. Finding Problem Registers

**Goal**: Identify specific SID registers causing accuracy issues

**Steps**:
1. Generate heatmap
2. Switch to Mode 1 (Binary Match/Mismatch)
3. Look for vertical red lines
4. Hover to see which register
5. Focus conversion efforts on that register

**Example**:
- Red line at V1_PW_HI = Pulse width conversion broken
- Red lines at FC_LO/FC_HI = Filter not implemented

### 3. Detecting Timing Drift

**Goal**: Find gradual timing synchronization issues

**Steps**:
1. Generate heatmap with many frames (1000+)
2. Switch to Mode 4 (Frame Accuracy)
3. Look for gradual color changes (green → yellow → red)
4. Identify frame where drift starts

**Interpretation**:
- Gradual shift = Timing drift
- Sudden shift = Phase change or loop

### 4. Comparing Different Conversion Methods

**Goal**: Evaluate which conversion driver/method works best

**Steps**:
1. Convert SID with Driver A → File A
2. Convert SID with Driver B → File B
3. Generate heatmap comparing File A vs File B
4. Compare accuracy percentages

**Interpretation**:
- More green = Better conversion
- Different patterns = Different failure modes

### 5. Debugging Specific Frames

**Goal**: Understand why frame 142 sounds wrong

**Steps**:
1. Generate heatmap
2. Zoom in on frame 142
3. Hover over red cells to see exact value differences
4. Compare with neighboring frames
5. Identify what changed

**Usage**: Pinpoint exact register causing audible glitch

---

## Command Reference

### Full Syntax

```bash
accuracy-heatmap.bat <file_a> <file_b> [options]
```

### Positional Arguments

| Argument | Description |
|----------|-------------|
| `file_a` | First SID file (original) |
| `file_b` | Second SID file (converted) |

### Optional Arguments

| Flag | Long Form | Type | Default | Description |
|------|-----------|------|---------|-------------|
| `-f` | `--frames` | int | 300 | Number of frames to trace |
| `-o` | `--output` | str | `heatmap_<timestamp>.html` | Output HTML filename |
| `-m` | `--mode` | int | 1 | Default visualization mode (1-4) |
| `-v` | `--verbose` | flag | 0 | Increase verbosity (-v, -vv) |
| `-h` | `--help` | flag | - | Show help message |

### Examples

**Basic comparison (300 frames)**:
```bash
accuracy-heatmap.bat original.sid converted.sid
```

**Long analysis (1500 frames)**:
```bash
accuracy-heatmap.bat original.sid converted.sid --frames 1500
```

**Custom output file**:
```bash
accuracy-heatmap.bat a.sid b.sid --output my_heatmap.html
```

**Start with Mode 2 (Delta Magnitude)**:
```bash
accuracy-heatmap.bat a.sid b.sid --mode 2
```

**Verbose output**:
```bash
accuracy-heatmap.bat a.sid b.sid -v
```

**Debug mode (very detailed)**:
```bash
accuracy-heatmap.bat a.sid b.sid -vv
```

**Everything combined**:
```bash
accuracy-heatmap.bat original.sid converted.sid --frames 1000 --output detailed_analysis.html --mode 3 -vv
```

---

## Interpreting Colors

### Mode 1: Binary Match/Mismatch

| Color | Meaning | Interpretation |
|-------|---------|----------------|
| Green (#56ab2f) | Match | File A value = File B value |
| Red (#eb3349) | Mismatch | File A value ≠ File B value |

### Mode 2: Value Delta Magnitude

| Color | Meaning | Delta Range | Interpretation |
|-------|---------|-------------|----------------|
| Light Green (#a8e063) | No difference | 0 | Values identical |
| Yellow/Orange | Medium difference | 64-192 | Values somewhat different |
| Red (#eb3349) | Maximum difference | 255 | Values completely different |

**Gradient**: Green (0) → Yellow (128) → Red (255)

### Mode 3: Register Group Highlighting

| Color | Voice/Group | Bright = | Dark = |
|-------|-------------|----------|--------|
| Red (#eb3349) | Voice 1 (Regs 0-6) | Match | Mismatch |
| Blue (#569cd6) | Voice 2 (Regs 7-13) | Match | Mismatch |
| Green (#56ab2f) | Voice 3 (Regs 14-20) | Match | Mismatch |
| Orange (#f09819) | Filter (Regs 21-24) | Match | Mismatch |

**Brightness**: 100% = match, 60% = mismatch (40% darker)

### Mode 4: Frame Accuracy

| Color | Meaning | Accuracy Range |
|-------|---------|----------------|
| Green (#56ab2f) | Perfect frame | 100% (all 29 registers match) |
| Yellow | Medium accuracy | 50% (about half match) |
| Red (#eb3349) | No matches | 0% (no registers match) |

**Gradient**: Red (0%) → Yellow (50%) → Green (100%)

---

## Advanced Usage

### Large Frame Counts (1000+)

**Recommendation**: Start with default (300 frames), increase if needed

**Performance**:
- 300 frames: ~8KB grid data, instant rendering
- 1000 frames: ~30KB grid data, <1 second rendering
- 3000 frames: ~90KB grid data, 1-2 seconds rendering

**Zoom Strategy**:
1. Generate heatmap with full frame count
2. Zoom out to see overall pattern
3. Zoom in on problem areas
4. Use scroll to navigate

### Comparing Multiple Conversions

**Workflow**:
1. Convert with Driver A: `original.sid` → `converted_a.sid`
2. Convert with Driver B: `original.sid` → `converted_b.sid`
3. Compare A vs B: `accuracy-heatmap.bat converted_a.sid converted_b.sid`
4. Compare A vs original: `accuracy-heatmap.bat original.sid converted_a.sid`
5. Compare B vs original: `accuracy-heatmap.bat original.sid converted_b.sid`

**Analysis**: Identify which driver has better accuracy

### Batch Analysis

**Goal**: Generate heatmaps for many SID pairs

**Script Example** (PowerShell):
```powershell
Get-ChildItem *.sid | ForEach-Object {
    $original = $_.FullName
    $converted = "converted_" + $_.Name
    $output = "heatmap_" + $_.BaseName + ".html"

    accuracy-heatmap.bat $original $converted --output $output --frames 500
}
```

### Integration with Testing Pipeline

**CI/CD Integration**:
```bash
# In your test script
python pyscript/accuracy_heatmap_tool.py original.sid converted.sid --frames 300 --output results/heatmap.html -v

# Check exit code (0 = success)
if [ $? -eq 0 ]; then
    echo "Heatmap generated successfully"
else
    echo "Heatmap generation failed"
    exit 1
fi
```

### Extracting Accuracy Metrics

**Manual Extraction**:
Open generated HTML in browser, check sidebar for:
- Overall Accuracy %
- Matches / Total cells
- Dimensions (frames × registers)

**Automated Extraction** (future feature):
Currently not supported. Future versions may add `--json` output for CI/CD.

---

## Troubleshooting

### "File not found" Error

**Error**:
```
[ERROR] File not found: my_file.sid
```

**Cause**: SID file path is incorrect or file doesn't exist

**Solution**:
1. Check file path spelling
2. Use absolute path: `C:\path\to\file.sid`
3. Verify file exists: `ls my_file.sid`

### "Failed to parse SID file" Error

**Error**:
```
[ERROR] Failed to trace File A: Failed to parse SID file
```

**Cause**: File is not a valid PSID/RSID format

**Solution**:
1. Verify file has PSID or RSID magic bytes
2. Check file isn't corrupted
3. Try opening in VICE/VSID to confirm it's valid

### "Failed to trace" Error

**Error**:
```
[ERROR] Failed to trace File A: <exception>
```

**Cause**: CPU emulator crashed during execution

**Solution**:
1. Reduce frame count: `--frames 100`
2. Try `-vv` for detailed debug output
3. Check if SID file uses unsupported features
4. Report bug with specific SID file if reproducible

### HTML File Too Large

**Symptom**: Generated HTML is 5+ MB, slow to open

**Cause**: Too many frames traced (e.g., 10,000 frames)

**Solution**:
1. Reduce frame count: `--frames 1000` (max recommended: 3000)
2. Split analysis into multiple runs
3. Modern browsers handle up to ~10MB fine, but prefer <1MB

### Heatmap Rendering Too Slow

**Symptom**: Heatmap takes >5 seconds to redraw when switching modes

**Cause**: Very large heatmap (5000+ frames) or old browser

**Solution**:
1. Use modern browser (Chrome/Firefox/Edge latest)
2. Reduce frame count
3. Zoom out (smaller cells = less rendering work)
4. Close other browser tabs (free up memory)

### Tooltips Not Showing

**Symptom**: Mouse hover doesn't show tooltip

**Cause**: Mouse not positioned over heatmap canvas

**Solution**:
1. Move mouse over colored cells (not axis labels)
2. Check browser console for JavaScript errors (F12)
3. Try refreshing page (Ctrl+R)

### Colors Look Wrong

**Symptom**: Expected green but seeing red, or vice versa

**Cause**: Different visualization mode active

**Solution**:
1. Check which mode is selected in sidebar
2. Mode 1 = Green/Red (match/mismatch)
3. Mode 2 = Green/Yellow/Red (delta magnitude)
4. Mode 3 = Red/Blue/Green/Orange (voice groups)
5. Mode 4 = Red/Yellow/Green (frame accuracy)

---

## Tips & Tricks

### 1. Start with Small Frame Counts

- Begin with `--frames 100` for quick analysis
- Increase to `--frames 300` (default) for normal analysis
- Only use `--frames 1000+` for detailed long-form analysis

### 2. Use Mode 1 for Quick Overview

- Mode 1 (Binary Match/Mismatch) gives fastest visual assessment
- Switch to other modes for detailed investigation

### 3. Combine with Trace Viewer

**Workflow**:
1. Use heatmap to identify problem frame (e.g., frame 142)
2. Use trace viewer to see exact register writes for that frame
3. Compare side-by-side to understand difference

### 4. Look for Symmetry

- **Perfect conversion**: Symmetrical patterns (if original uses patterns)
- **Broken conversion**: Asymmetric or noisy patterns

### 5. Check Init Phase Separately

- Frame 0 often has different pattern (init writes)
- If frame 0 is all red but rest is green = init differences only
- If frame 0 is green but rest is red = playback differences

### 6. Use Register Groups to Diagnose Voices

- Mode 3 (Register Groups) clearly shows which voice fails
- Red rows (Voice 1) vs Blue rows (Voice 2) vs Green rows (Voice 3)
- If one voice's rows are all bright = that voice works perfectly

### 7. Compare Against Self for Sanity Check

```bash
accuracy-heatmap.bat file.sid file.sid
```

- Should produce 100% accuracy (all green)
- If not 100% = tool bug or file playback non-determinism

### 8. Save Important Heatmaps

- Use descriptive filenames: `--output laxity_driver_v1_vs_v2.html`
- Archive heatmaps for regression testing
- Compare new conversions against baseline heatmaps

### 9. Zoom Workflow

1. **Zoom Out**: See overall pattern (10,000+ cells on screen)
2. **Identify Problem Area**: Spot red clusters
3. **Zoom In**: Focus on specific frames/registers
4. **Hover**: Get exact values

### 10. Interpret Patterns Musically

- **Verse/Chorus Structure**: Should show repeating patterns
- **Intro Section**: Often unique pattern (no repetition)
- **Filter Sweep**: Should show smooth gradient in FC_LO/FC_HI rows
- **Drum Hit**: Should show spike in waveform/envelope registers

---

## Summary

The **Accuracy Heatmap Tool** provides a powerful visual way to:

1. **Identify accuracy issues** in SID conversions
2. **Diagnose specific problem registers** causing failures
3. **Understand timing and synchronization** issues
4. **Compare different conversion methods** quantitatively
5. **Validate conversion accuracy** before release

### Key Takeaways

- **Start simple**: Use Mode 1 with 300 frames
- **Drill down**: Zoom in on problem areas
- **Use tooltips**: Inspect exact values on hover
- **Switch modes**: Different modes reveal different insights
- **Combine tools**: Use with trace viewer for complete analysis

### Next Steps

- Read [Trace Comparison Guide](TRACE_COMPARISON_GUIDE.md) for detailed trace analysis
- See [Troubleshooting Guide](TROUBLESHOOTING.md) for common conversion issues
- Check [Best Practices](BEST_PRACTICES.md) for conversion workflow tips

---

**End of Guide** | For questions, see [FAQ.md](FAQ.md) or [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
