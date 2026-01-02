# Trace Comparison Tool - User Guide

**Version**: 1.0.0
**Date**: 2026-01-01
**Tool**: `trace-compare.bat` / `trace_comparison_tool.py`

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Understanding the HTML Report](#understanding-the-html-report)
4. [Key Metrics Explained](#key-metrics-explained)
5. [Use Cases](#use-cases)
6. [Interpreting Results](#interpreting-results)
7. [Advanced Usage](#advanced-usage)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)
10. [Tips & Tricks](#tips--tricks)

---

## Overview

The **Trace Comparison Tool** compares two SID files by executing them and comparing their SID register writes frame-by-frame. This is the definitive way to validate conversion accuracy, debug player differences, or analyze SID format variations.

### What It Does

1. **Traces** both SID files (captures all register writes during execution)
2. **Compares** the traces frame-by-frame
3. **Calculates** comprehensive metrics (frame match %, register accuracy, voice accuracy)
4. **Generates** interactive HTML report with tabbed interface

### When to Use It

- **Validate conversions**: Check SID→SF2→SID roundtrip accuracy
- **Compare drivers**: Analyze differences between Laxity vs Driver11
- **Debug timing**: Identify where execution diverges
- **Verify players**: Confirm player code produces identical output

---

## Quick Start

### Basic Comparison

Compare two SID files and generate HTML report:

```bash
trace-compare.bat original.sid converted.sid
```

**Output**: `comparison_<timestamp>.html` (opens in browser)

### With Options

```bash
# Custom number of frames (default: 300)
trace-compare.bat original.sid converted.sid --frames 1500

# Custom output filename
trace-compare.bat a.sid b.sid --output my_comparison.html

# Verbose output (see trace progress)
trace-compare.bat a.sid b.sid -v

# Very verbose (debug info)
trace-compare.bat a.sid b.sid -vv

# Quick comparison without HTML (just metrics)
trace-compare.bat a.sid b.sid --no-html
```

### Example Workflow

```bash
# 1. Convert Laxity SID to SF2 and back
sid-to-sf2.bat Laxity/Broware.sid Broware.sf2 --driver laxity
sf2-to-sid.bat Broware.sf2 Broware_exported.sid

# 2. Compare original vs roundtrip
trace-compare.bat Laxity/Broware.sid Broware_exported.sid --frames 1500

# 3. Open comparison_<timestamp>.html in browser
# 4. Check Frame Match % - should be 99%+
```

---

## Understanding the HTML Report

The HTML report has **3 tabs** plus a **sidebar** with key metrics.

### Sidebar (Always Visible)

**4 Key Metrics**:
1. **Frame Match**: % of frames with identical register writes
2. **Register Acc.**: Average accuracy across all 29 SID registers
3. **Voice 1/2/3**: Overall accuracy for each of the 3 SID voices
4. **Total Diffs**: Count of all register write differences

Color coding:
- **Green**: Excellent (≥90%)
- **Orange/Yellow**: Warning (70-89%)
- **Red**: Error (<70% or high diff count)

### Tab 1: File A

Shows complete trace visualization for the first SID file.

**Sections**:
- **Initialization**: Collapsible list of init writes (one-time setup)
- **Frame Timeline**: Visual timeline with bars (height = write count)
  - Click bars to jump to specific frame
  - Drag slider to navigate smoothly
- **Frame Viewer**: Shows all register writes for current frame
- **Register States**: Real-time display of all SID register values
  - Organized by voice (Voice 1/2/3, Filter)
  - Updates as you navigate frames

### Tab 2: File B

Identical layout to File A, shows the second SID file's trace.

### Tab 3: Differences

Highlights differences between the two files.

**Sections**:
- **Initialization Phase**: Table showing init write differences
  - Register, File A value, File B value, Delta
- **Frame Match Timeline**: Visual timeline color-coded by accuracy
  - **Green**: 100% match (perfect)
  - **Light Green**: 90-99% match (very good)
  - **Orange**: 50-89% match (moderate)
  - **Red**: <50% match (poor)
- **Frame Diff Viewer**: Side-by-side comparison for current frame
  - Shows only registers that differ
  - Color-coded: Blue (File A), Purple (File B)

### Interactive Features

**Timeline Navigation**:
- **Click bars**: Jump to specific frame instantly
- **Drag slider**: Smooth navigation through all frames
- **Current frame**: Displayed above slider

**Tab Switching**:
- Click tab buttons to switch between File A, File B, Differences
- Sidebar metrics stay visible across all tabs
- Frame sliders are synced (navigating in one tab updates others)

**Register Display**:
- Real-time updates as you navigate frames
- Values shown in hexadecimal ($XX format)
- Organized by register group (Voice 1, 2, 3, Filter)

---

## Key Metrics Explained

### 1. Frame Match %

**Definition**: Percentage of frames where all register writes are identical.

**Calculation**:
- Frame is a "match" if every register has the same value in both traces
- Frame Match % = (perfect frames / total frames) × 100

**Interpretation**:
- **100%**: Perfect match (files are identical)
- **95-99%**: Excellent (minor differences, likely acceptable)
- **90-94%**: Good (some differences, investigate)
- **70-89%**: Moderate (significant differences)
- **<70%**: Poor (major differences)

**Example**:
```
Frame Match: 99.20% (248 / 250 frames)
```
Out of 250 frames, 248 were perfect matches. Only 2 frames had any differences.

### 2. Register Accuracy

**Definition**: Per-register match percentage across all frames.

**Calculation**:
- For each of 29 SID registers, count matches vs total writes
- Overall Register Accuracy = average of all register accuracies

**Breakdown**:
The tool shows accuracy for each register individually:
- Voice 1: Frequency Lo/Hi, Pulse Width, Control, Attack/Decay, Sustain/Release
- Voice 2: (same 7 registers)
- Voice 3: (same 7 registers)
- Filter: Cutoff Lo/Hi, Resonance/Routing, Mode/Volume

**Interpretation**:
- **100%**: Register always has correct value
- **90-99%**: Occasional mismatches
- **<90%**: Frequent mismatches (investigate this register)

**Example**:
```
Register Accuracy: 98.50%

Breakdown (top mismatches):
  Voice1_FreqLo: 95.2%  ← Some frequency differences
  Voice1_Control: 100%  ← Perfect waveform match
  Filter_Mode: 0%       ← Filter completely wrong
```

### 3. Voice Accuracy

**Definition**: Per-voice accuracy for frequency, waveform, ADSR, and pulse width.

**Components**:
- **Frequency**: 16-bit frequency register (Freq Lo + Freq Hi)
- **Waveform**: Control register (gate, sync, ring, waveform selection)
- **ADSR**: Attack/Decay + Sustain/Release envelope registers
- **Pulse**: 12-bit pulse width (Pulse Lo + Pulse Hi)

**Calculation**:
- Track matches for each component across all frames
- Overall Voice Accuracy = average of 4 components

**Interpretation**:
- **100%**: Voice is perfectly replicated
- **90-99%**: Minor deviations (usually acceptable)
- **70-89%**: Noticeable differences (may affect sound)
- **<70%**: Major differences (will sound different)

**Example**:
```
Voice 1: 95.50% (Freq:100%, Wave:90%, ADSR:95%, Pulse:97%)
Voice 2: 88.20% (Freq:75%, Wave:100%, ADSR:89%, Pulse:89%)
Voice 3: 0.00% (Freq:0%, Wave:0%, ADSR:0%, Pulse:0%)
```

**Analysis**: Voice 3 is completely different (might be unused), Voice 1 is excellent, Voice 2 has some frequency issues.

### 4. Total Diff Count

**Definition**: Total number of register write mismatches.

**Breakdown**:
- **Init phase**: Differences during initialization
- **Frame phase**: Differences during playback frames

**Interpretation**:
- **0 diffs**: Perfect match
- **1-50 diffs**: Excellent (minor differences)
- **50-500 diffs**: Moderate (some differences)
- **500+ diffs**: Significant differences

**Context Matters**:
- 100 diffs over 3000 frames = 0.03 diffs/frame (good)
- 100 diffs over 10 frames = 10 diffs/frame (poor)

**Example**:
```
Total Differences: 245
  Init phase:      12
  Frame phase:     233
```

**Analysis**: 12 diffs during init (register setup), 233 diffs across frames (about 1 diff per frame if 250 frames traced).

---

## Use Cases

### 1. Validate SID→SF2→SID Conversion

**Goal**: Verify lossless roundtrip conversion.

**Steps**:
```bash
# Convert to SF2
sid-to-sf2.bat original.sid temp.sf2 --driver laxity

# Convert back to SID
sf2-to-sid.bat temp.sf2 roundtrip.sid

# Compare
trace-compare.bat original.sid roundtrip.sid --frames 1500
```

**Expected Results**:
- Frame Match: **99%+** (near-perfect)
- Voice 1/2/3 Accuracy: **99%+**
- Total Diffs: **<50** (minimal differences)

**What to Check**:
- Frame Match Timeline: Should be mostly green
- Voice Accuracy: All voices should be 95%+
- Diff Viewer: Check what differs (often filter or timing)

### 2. Compare Different Drivers

**Goal**: Understand how Laxity driver differs from Driver11.

**Steps**:
```bash
# Convert using Laxity driver
sid-to-sf2.bat original.sid laxity.sf2 --driver laxity
sf2-to-sid.bat laxity.sf2 laxity_exported.sid

# Convert using Driver11
sid-to-sf2.bat original.sid driver11.sf2 --driver driver11
sf2-to-sid.bat driver11.sf2 driver11_exported.sid

# Compare drivers
trace-compare.bat laxity_exported.sid driver11_exported.sid --frames 1500
```

**Expected Results**:
- Frame Match: **70-90%** (drivers encode differently)
- Voice Accuracy: Variable (depends on driver compatibility)
- Differences: Focus on control bytes, note encoding

**What to Check**:
- Which registers differ most?
- Are frequency tables accurate?
- How are control bytes encoded?

### 3. Debug Timing Issues

**Goal**: Find where execution starts to diverge.

**Steps**:
```bash
# Compare with many frames
trace-compare.bat original.sid converted.sid --frames 3000 -v
```

**Analysis**:
1. **Frame Match Timeline**: Look for where green turns to orange/red
   - If divergence starts immediately: Init phase issue
   - If divergence starts later: Timing drift or accumulation error
   - If intermittent red bars: Periodic differences (e.g., every 16 frames)

2. **Voice Accuracy**: Which voice diverges first?
   - Voice 1 first: Main melody issue
   - Voice 3 first: Bass/drums issue
   - All at once: Synchronization problem

3. **Diff Viewer**: Navigate to first divergent frame
   - Check which registers differ
   - Compare register values to understand pattern

### 4. Verify Player Code

**Goal**: Confirm two different player implementations produce identical output.

**Steps**:
```bash
# Compare different player versions
trace-compare.bat laxity_v20.sid laxity_v21.sid --frames 1500
```

**Expected Results**:
- Frame Match: **100%** (if players are compatible)
- Total Diffs: **0** (identical execution)

**If Not Matching**:
- Check player version compatibility
- Look for optimization differences
- Verify table formats match

### 5. Analyze File Variations

**Goal**: Understand how different SID file versions differ.

**Steps**:
```bash
# Compare original vs remix
trace-compare.bat original.sid remix.sid --frames 1500

# Compare different subtunes
trace-compare.bat tune_sub1.sid tune_sub2.sid --frames 1500
```

**What to Look For**:
- New voices added?
- Different instruments?
- Tempo changes?
- Filter usage differences?

---

## Interpreting Results

### Scenario 1: Perfect Match

```
Frame Match:        100.00% (1500 / 1500 frames)
Register Accuracy:  100.00%
Voice Accuracies:
  Voice 1:        100.00% (Freq:100%, Wave:100%, ADSR:100%, Pulse:100%)
  Voice 2:        100.00% (Freq:100%, Wave:100%, ADSR:100%, Pulse:100%)
  Voice 3:        100.00% (Freq:100%, Wave:100%, ADSR:100%, Pulse:100%)
Total Differences:  0
```

**Interpretation**: ✅ **PERFECT** - Files are byte-for-byte identical in execution.

**Conclusion**: Conversion is lossless, player code is identical, or files are duplicates.

### Scenario 2: Excellent Match (99%+)

```
Frame Match:        99.20% (1488 / 1500 frames)
Register Accuracy:  99.50%
Voice Accuracies:
  Voice 1:        99.80% (Freq:100%, Wave:100%, ADSR:98%, Pulse:100%)
  Voice 2:        99.50% (Freq:100%, Wave:99%, ADSR:99%, Pulse:100%)
  Voice 3:        99.20% (Freq:100%, Wave:100%, ADSR:97%, Pulse:100%)
Total Differences:  45
```

**Interpretation**: ✅ **EXCELLENT** - Very minor differences, likely acceptable.

**Common Causes**:
- Filter register differences (often 0% accuracy, OK if filter unused)
- ADSR envelope rounding
- Timing drift (accumulated small errors)

**Action**: Check Diff Viewer for pattern. If differences are in unused registers or filter, likely OK.

### Scenario 3: Good Match (90-95%)

```
Frame Match:        92.50% (1387 / 1500 frames)
Register Accuracy:  94.20%
Voice Accuracies:
  Voice 1:        95.50% (Freq:100%, Wave:90%, ADSR:95%, Pulse:97%)
  Voice 2:        92.80% (Freq:88%, Wave:100%, ADSR:90%, Pulse:93%)
  Voice 3:        94.30% (Freq:92%, Wave:100%, ADSR:91%, Pulse:95%)
Total Differences:  312
```

**Interpretation**: ✓ **GOOD** - Some differences, but mostly accurate.

**Common Causes**:
- Note encoding differences (different drivers)
- Control byte format variations
- Table rounding

**Action**: Check specific registers with low accuracy. If frequency/waveform are high, sound should be close.

### Scenario 4: Moderate Match (70-90%)

```
Frame Match:        78.00% (1170 / 1500 frames)
Register Accuracy:  82.50%
Voice Accuracies:
  Voice 1:        85.00% (Freq:75%, Wave:90%, ADSR:85%, Pulse:90%)
  Voice 2:        80.20% (Freq:70%, Wave:95%, ADSR:75%, Pulse:80%)
  Voice 3:        82.30% (Freq:72%, Wave:90%, ADSR:80%, Pulse:88%)
Total Differences:  856
```

**Interpretation**: ⚠ **MODERATE** - Noticeable differences, investigate.

**Common Causes**:
- Incompatible drivers (e.g., Laxity→Driver11 without custom driver)
- Wrong driver selected
- Player code differences
- Format conversion issues

**Action**:
1. Check driver selection (--driver laxity for Laxity files)
2. Review Frame Match Timeline for divergence pattern
3. Inspect Diff Viewer for systematic differences

### Scenario 5: Poor Match (<70%)

```
Frame Match:        45.20% (678 / 1500 frames)
Register Accuracy:  52.80%
Voice Accuracies:
  Voice 1:        50.50% (Freq:40%, Wave:55%, ADSR:50%, Pulse:57%)
  Voice 2:        48.30% (Freq:38%, Wave:60%, ADSR:45%, Pulse:50%)
  Voice 3:        60.00% (Freq:50%, Wave:70%, ADSR:60%, Pulse:60%)
Total Differences:  2847
```

**Interpretation**: ❌ **POOR** - Major differences detected.

**Common Causes**:
- Wrong driver used
- Different player formats (not compatible)
- Corruption during conversion
- Completely different files

**Action**:
1. **Verify inputs**: Are these the same tune?
2. **Check driver**: Did you use `--driver laxity` for Laxity files?
3. **Review conversion**: Did sid-to-sf2 report errors?
4. **Compare metadata**: Check SID headers match

---

## Advanced Usage

### Trace Many Frames (Full Song)

```bash
# Trace entire 3-minute song (3600 frames = 60 seconds @ 60Hz)
trace-compare.bat original.sid converted.sid --frames 3600
```

**Note**: Large frame counts produce larger HTML files (may be slow to load in browser).

### Compare Specific Subtunes

```bash
# Create temp copies with specific subtune
cp original.sid original_sub1.sid
cp original.sid original_sub2.sid

# Edit SID headers to set start_song

# Compare
trace-compare.bat original_sub1.sid original_sub2.sid
```

### Quick Comparison (No HTML)

```bash
# Just print metrics, skip HTML generation
trace-compare.bat original.sid converted.sid --no-html
```

**Use Case**: Batch testing many files, only need metrics.

### Automated Testing

```bash
# Script to test all Laxity files
for file in Laxity/*.sid; do
    basename=$(basename "$file" .sid)
    sid-to-sf2.bat "$file" "temp/${basename}.sf2" --driver laxity
    sf2-to-sid.bat "temp/${basename}.sf2" "temp/${basename}_exported.sid"
    trace-compare.bat "$file" "temp/${basename}_exported.sid" --frames 1500 --no-html > "results/${basename}.txt"
done
```

---

## Troubleshooting

### Issue: "SID file not found"

**Cause**: File path incorrect or file doesn't exist.

**Solution**:
```bash
# Use absolute path
trace-compare.bat "C:/full/path/to/file.sid" other.sid

# Or navigate to directory first
cd Laxity
trace-compare.bat Broware.sid ../other.sid
```

### Issue: "Trace timeout" or "Infinite loop detected"

**Cause**: SID file has infinite loop or very long init phase.

**Solution**:
```bash
# Try fewer frames
trace-compare.bat file.sid other.sid --frames 100

# Use -v to see where it gets stuck
trace-compare.bat file.sid other.sid -vv
```

### Issue: HTML file is huge (>10MB)

**Cause**: Too many frames traced.

**Solution**:
```bash
# Reduce frame count
trace-compare.bat file.sid other.sid --frames 500

# Focus on first 2 seconds of playback
trace-compare.bat file.sid other.sid --frames 120
```

**Note**: 500 frames is usually enough to identify issues.

### Issue: "Different frame counts" warning

**Cause**: Files have different execution lengths.

**Explanation**: Tool compares up to the minimum frame count. This is normal if files differ in length.

**Action**: Check if this is expected (e.g., different song versions).

### Issue: All voice accuracies are 0%

**Cause**: Files are completely different (different songs).

**Solution**: Verify you're comparing the correct files. Check SID headers with:
```bash
siddump original.sid
siddump other.sid
```

### Issue: Frame Match is perfect but sound is different

**Possible Causes**:
1. **Different clock speeds**: PAL vs NTSC
2. **Different SID chip**: 6581 vs 8580
3. **Filter differences**: Filter accuracy is 0% but may matter
4. **Playback issues**: Not a trace comparison issue

**Action**: Compare actual audio output with VSID or real hardware.

---

## Best Practices

### 1. Use Appropriate Frame Counts

- **Quick check**: 100-300 frames (2-5 seconds)
- **Standard validation**: 1500 frames (25 seconds)
- **Full song**: 3000-7200 frames (50-120 seconds)

**Rule of Thumb**: If issues appear in first 300 frames, they'll likely persist throughout.

### 2. Start with Small Frame Counts

```bash
# First, quick check
trace-compare.bat file.sid other.sid --frames 100

# If good, extend
trace-compare.bat file.sid other.sid --frames 1500
```

### 3. Use Correct Driver for Input Files

| File Source | Driver to Use |
|-------------|---------------|
| Laxity NewPlayer v21 | `--driver laxity` |
| SF2-exported (Driver 11) | `--driver driver11` |
| Laxity NewPlayer v20 (G4) | `--driver np20` |
| Unknown/Other | `--driver driver11` (default) |

**Critical**: Using wrong driver will show poor match even if conversion is correct.

### 4. Focus on Voice Accuracy, Not Just Frame Match

Frame Match % can be misleading if differences are in unused registers.

**Better metric**: Voice accuracy for voices 1/2/3.

### 5. Check Init Phase Separately

Init differences often affect entire playback.

**In HTML**:
- Go to Differences tab
- Check "Initialization Phase" section first
- If many init diffs, expect frame diffs too

### 6. Use Timeline to Identify Divergence Points

Don't just look at overall accuracy - check **when** differences occur.

**Patterns**:
- **All red from start**: Init issue or wrong driver
- **Green then red**: Timing drift or accumulation error
- **Periodic red bars**: Repeating pattern (e.g., every 16 frames)
- **Random red bars**: Sporadic differences

### 7. Compare Converted File to Reference, Not Original

```bash
# GOOD: Compare exported SID to SF2 reference
trace-compare.bat reference.sf2 exported.sid

# LESS USEFUL: Compare original SID to SF2
trace-compare.bat original.sid exported.sf2
```

**Reason**: SID and SF2 are different formats. Compare within same format.

---

## Tips & Tricks

### Quick Validation Script

```bash
# validate_conversion.bat
@echo off
set INPUT=%1
set BASENAME=%~n1

sid-to-sf2.bat "%INPUT%" temp.sf2 --driver laxity
sf2-to-sid.bat temp.sf2 temp_exported.sid
trace-compare.bat "%INPUT%" temp_exported.sid --frames 1500 --output "%BASENAME%_comparison.html"

echo.
echo Comparison complete: %BASENAME%_comparison.html
echo Open in browser to view results.
```

**Usage**:
```bash
validate_conversion.bat Laxity/Broware.sid
```

### Batch Compare Multiple Files

```bash
# compare_all.bat
for %%f in (*.sid) do (
    echo Comparing %%f...
    trace-compare.bat "%%f" "converted/%%f" --no-html > "results/%%~nf.txt"
)
```

### Extract Accuracy from HTML

HTML file contains embedded JavaScript with all metrics. Search for:
```javascript
frameAccuracy = [100.0, 98.5, 100.0, ...]
```

### Compare Two Versions Side-by-Side

```bash
# Compare v1 vs v2
trace-compare.bat tune_v1.sid tune_v2.sid --output comparison_v1_vs_v2.html

# Open HTML to see what changed between versions
```

### Focus on Specific Voices

In HTML Diff Viewer, filter by register address:
- **Voice 1**: $D400-$D406
- **Voice 2**: $D407-$D40D
- **Voice 3**: $D40E-$D414
- **Filter**: $D415-$D418

### Use Verbose Mode for Debugging

```bash
# See exactly what's happening during trace
trace-compare.bat file.sid other.sid -vv
```

**Output**:
```
[DEBUG] Tracing init phase...
[DEBUG] Init: 47 writes captured
[DEBUG] Tracing frame 0...
[DEBUG] Frame 0: 12 writes captured
...
```

---

## See Also

- **Validation Guide**: `docs/guides/VALIDATION_GUIDE.md` - SID accuracy validation workflow
- **SIDwinder HTML Trace Guide**: `docs/guides/SIDWINDER_HTML_TRACE_GUIDE.md` - Single SID trace visualization
- **Validation Dashboard Guide**: `docs/guides/VALIDATION_DASHBOARD_GUIDE.md` - Batch validation results
- **Best Practices**: `docs/guides/BEST_PRACTICES.md` - General SIDM2 best practices

---

**End of Guide**
