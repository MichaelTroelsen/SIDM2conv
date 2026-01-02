# Batch Analysis Tool Guide

**SIDM2 v3.1.0** | Multi-File SID Comparison Tool | Updated 2026-01-02

The Batch Analysis Tool automatically compares multiple pairs of SID files, generating comprehensive accuracy reports with visual heatmaps, detailed comparisons, and aggregate statistics.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [Usage Examples](#usage-examples)
5. [Command-Line Options](#command-line-options)
6. [Output Formats](#output-formats)
7. [File Pairing Logic](#file-pairing-logic)
8. [Understanding Results](#understanding-results)
9. [Integration](#integration)
10. [Troubleshooting](#troubleshooting)
11. [Advanced Usage](#advanced-usage)

---

## Overview

### What It Does

The Batch Analysis Tool automates the comparison of multiple SID file pairs by:

1. **Auto-Pairing Files** - Matches files from two directories by basename
2. **Per-Pair Analysis** - For each pair:
   - Traces both SID files (frame-by-frame SID register writes)
   - Compares traces to calculate accuracy metrics
   - Generates visual accuracy heatmap (HTML)
   - Creates detailed comparison report (HTML with tabbed interface)
3. **Aggregate Reporting** - Combines all results into:
   - Interactive HTML summary with sortable table and charts
   - CSV spreadsheet export
   - JSON machine-readable export

### When to Use

- **After batch conversion** - Validate 10, 50, 100+ conversions at once
- **Quality assurance** - Check conversion accuracy across entire music collection
- **Driver comparison** - Compare different conversion drivers (Laxity vs Driver11)
- **Before release** - Verify no regressions in conversion quality
- **Documentation** - Generate visual proof of conversion accuracy

### Key Features

- **Automatic file pairing** - Handles `_exported`, `_laxity`, `.sf2` suffixes
- **Comprehensive metrics** - Frame match %, register accuracy, per-voice accuracy
- **Visual analysis** - Heatmaps show exactly where differences occur
- **Interactive reports** - Sortable tables, charts, search/filter
- **Multiple formats** - HTML (interactive), CSV (spreadsheet), JSON (automation)
- **Error handling** - Failed pairs don't stop batch, partial results preserved
- **Performance** - ~2-5 seconds per pair, progress indicators

---

## Quick Start

### 5-Minute Tutorial

```bash
# 1. Prepare two directories with SID files
#    - originals/   (source SID files)
#    - exported/    (converted SID files with matching names + suffix)

# 2. Run batch analysis
batch-analysis.bat originals/ exported/ -o results/

# 3. Open the HTML report
start results/batch_summary.html
```

### Example Output

```
================================================================================
BATCH SID ANALYSIS
================================================================================

Finding SID pairs...
  Found 25 pairs

Analyzing pairs...
[1/25] song1.sid vs song1_exported.sid
  [OK] 99.8% accuracy, 2.3s
[2/25] song2.sid vs song2_exported.sid
  [OK] 94.2% accuracy, 2.1s
...

================================================================================
SUMMARY
================================================================================
Total Pairs:        25
Successful:         24 (96.0%)
Failed:             1

Accuracy:
  Avg Frame Match:  96.5%
  Avg Register:     97.2%
  Best:             song1.sid (99.8%)
  Worst:            song15.sid (82.3%)

Voice Accuracy:
  Voice 1:          98.1%
  Voice 2:          96.8%
  Voice 3:          94.5%

Duration:           58.2 seconds (2.3s per pair)

Output:
  HTML Report:      C:\...\results\batch_summary.html
  CSV Export:       C:\...\results\batch_results.csv
  JSON Export:      C:\...\results\batch_results.json
  Heatmaps:         results\heatmaps (24 files)
  Comparisons:      results\comparisons (24 files)

Interpretation:
  [EXCELLENT] Very high accuracy across all pairs
================================================================================
```

---

## Installation

### Prerequisites

- **Python 3.8+** (already required for SIDM2)
- **SIDwinder** (C64 emulator for tracing - included in SIDM2)
- **Existing SIDM2 installation** (batch analysis tool is included)

### Verify Installation

```bash
# Check batch analysis tool is available
batch-analysis.bat --help

# Should display help text with usage examples
```

No additional installation needed - the batch analysis tool is included with SIDM2.

---

## Usage Examples

### Basic Usage

```bash
# Compare all files in two directories
batch-analysis.bat originals/ exported/

# Custom output directory
batch-analysis.bat originals/ exported/ -o my_results/

# Limit tracing to 500 frames per file
batch-analysis.bat originals/ exported/ --frames 500
```

### Performance Options

```bash
# Skip heatmap generation (faster - saves ~1s per pair)
batch-analysis.bat originals/ exported/ --no-heatmaps

# Skip comparison HTMLs (faster - saves ~0.5s per pair)
batch-analysis.bat originals/ exported/ --no-comparisons

# Skip both for fastest metrics-only analysis
batch-analysis.bat originals/ exported/ --no-heatmaps --no-comparisons

# Expected speedup: 3-4s → 1-2s per pair
```

### Export Options

```bash
# Skip HTML summary report (CSV + JSON only)
batch-analysis.bat originals/ exported/ --no-html

# Skip CSV export
batch-analysis.bat originals/ exported/ --no-csv

# Skip JSON export
batch-analysis.bat originals/ exported/ --no-json

# Minimal output (HTML summary only, no individual reports)
batch-analysis.bat originals/ exported/ --no-heatmaps --no-comparisons --no-csv --no-json
```

### Verbose Output

```bash
# Normal verbosity (default)
batch-analysis.bat originals/ exported/

# Verbose mode (show detailed progress)
batch-analysis.bat originals/ exported/ -v

# Very verbose mode (show all trace details)
batch-analysis.bat originals/ exported/ -vv
```

### Real-World Scenarios

**Validate batch conversion**:
```bash
# After running batch-convert-laxity.bat
batch-analysis.bat SID/ output/converted/ -o validation_report/
```

**Quick quality check (no visuals)**:
```bash
# Fast metrics-only check
batch-analysis.bat originals/ exported/ --no-heatmaps --no-comparisons
# Open batch_summary.html → see accuracy at a glance
```

**Full documentation (all artifacts)**:
```bash
# Generate everything for thorough review
batch-analysis.bat originals/ exported/ --frames 1000 -v
# Review individual heatmaps and comparison HTMLs for problematic files
```

**Compare two driver versions**:
```bash
# Convert with Driver 11
batch-convert.bat SID/ output/driver11/ --driver driver11

# Convert with Laxity driver
batch-convert.bat SID/ output/laxity/ --driver laxity

# Compare results
batch-analysis.bat output/driver11/ output/laxity/ -o driver_comparison/
```

---

## Command-Line Options

### Positional Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `dir_a` | Directory with original SID files | `originals/` |
| `dir_b` | Directory with converted/exported SID files | `exported/` |

### Output Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `-o DIR`<br>`--output DIR` | Output directory | `batch_analysis_output` | `-o results/` |

### Analysis Options

| Option | Description | Default | Example |
|--------|-------------|---------|---------|
| `-f N`<br>`--frames N` | Frames to trace per file | `300` | `--frames 500` |

### Generation Options

| Option | Description | Default |
|--------|-------------|---------|
| `--no-heatmaps` | Skip heatmap generation (faster) | Generate heatmaps |
| `--no-comparisons` | Skip comparison HTML generation | Generate comparisons |
| `--no-html` | Skip HTML summary report | Generate HTML |
| `--no-csv` | Skip CSV export | Generate CSV |
| `--no-json` | Skip JSON export | Generate JSON |

### Other Options

| Option | Description | Default |
|--------|-------------|---------|
| `-v` | Verbose output (progress details) | Normal verbosity |
| `-vv` | Very verbose (trace details) | Normal verbosity |
| `--help` | Show help and exit | - |

---

## Output Formats

### Directory Structure

```
batch_analysis_output/
├── batch_summary.html       # Main interactive report
├── batch_results.csv        # Spreadsheet export
├── batch_results.json       # Machine-readable export
├── heatmaps/
│   ├── song1_heatmap.html
│   ├── song2_heatmap.html
│   └── ...
└── comparisons/
    ├── song1_comparison.html
    ├── song2_comparison.html
    └── ...
```

### 1. HTML Summary Report (`batch_summary.html`)

**Interactive web page with**:
- **Overview Cards** - Total pairs, success rate, avg accuracy, duration
- **Accuracy Distribution Chart** - Histogram showing accuracy spread (Chart.js)
- **Sortable Results Table** - Click column headers to sort (ascending/descending)
  - Filename pairs
  - Frame match % (with color-coded accuracy bar)
  - Register accuracy %
  - Total differences count
  - Status badge (success/partial/failed)
  - Duration
  - Links to heatmap and comparison HTML
- **Search/Filter** - Live filter by filename
- **Best/Worst Highlights** - Quick navigation to extremes

**Visual Design**:
- Dark VS Code theme (matches other SIDM2 tools)
- Color-coded accuracy:
  - 95-100%: Green (excellent)
  - 80-95%: Yellow (good)
  - <80%: Orange/Red (needs review)

**Example**:
```
Open in browser → Interactive sortable table
Click "Frame Match %" header → Sort by accuracy
Click on heatmap link → View individual file analysis
```

### 2. CSV Export (`batch_results.csv`)

**22 columns for spreadsheet analysis**:
```csv
filename_a,filename_b,frame_match_percent,register_accuracy,
voice1_freq,voice1_wave,voice1_adsr,voice1_pulse,
voice2_freq,voice2_wave,voice2_adsr,voice2_pulse,
voice3_freq,voice3_wave,voice3_adsr,voice3_pulse,
total_diffs,frames_traced,status,duration,
heatmap_path,comparison_path
```

**Use Cases**:
- Open in Excel/LibreOffice Calc
- Import into database
- Generate custom charts/pivots
- Statistical analysis

**Example**:
```csv
song1.sid,song1_exported.sid,99.8,99.9,100.0,98.5,99.2,100.0,...,success,2.3,heatmaps/song1_heatmap.html,comparisons/song1_comparison.html
```

### 3. JSON Export (`batch_results.json`)

**Structured data for automation**:
```json
{
  "summary": {
    "total_pairs": 25,
    "successful": 24,
    "failed": 1,
    "partial": 0,
    "avg_frame_match": 96.5,
    "avg_register_accuracy": 97.2,
    "best_match": {
      "filename": "song1.sid",
      "accuracy": 99.8
    },
    "worst_match": {
      "filename": "song15.sid",
      "accuracy": 82.3
    },
    "avg_voice1_accuracy": 98.1,
    "avg_voice2_accuracy": 96.8,
    "avg_voice3_accuracy": 94.5,
    "total_duration": 58.2,
    "avg_duration_per_pair": 2.3
  },
  "config": {
    "frames": 300,
    "generate_heatmaps": true,
    "generate_comparisons": true
  },
  "results": [
    {
      "filename_a": "song1.sid",
      "filename_b": "song1_exported.sid",
      "path_a": "originals\\song1.sid",
      "path_b": "exported\\song1_exported.sid",
      "metrics": {
        "frame_match_percent": 99.8,
        "register_accuracy": 99.9,
        "total_diffs": 12,
        "voice_accuracy": {
          "voice1": {
            "frequency": 100.0,
            "waveform": 98.5,
            "adsr": 99.2,
            "pulse": 100.0
          },
          "voice2": {...},
          "voice3": {...}
        }
      },
      "artifacts": {
        "heatmap_path": "heatmaps/song1_heatmap.html",
        "comparison_path": "comparisons/song1_comparison.html"
      },
      "status": "success",
      "error_message": null,
      "duration": 2.3,
      "frames_traced": 300
    },
    ...
  ]
}
```

**Use Cases**:
- Parse with Python scripts
- Import into testing frameworks
- CI/CD integration
- Programmatic analysis

### 4. Individual Heatmaps (`heatmaps/*.html`)

**Visual accuracy map per pair**:
- Frame-by-frame accuracy (rows = frames, columns = registers)
- Color gradient: Green (match) → Yellow (minor diff) → Red (major diff)
- Hover tooltips show exact values
- Identifies exactly where differences occur in the SID trace

**When to Use**:
- File shows low accuracy (<95%) in summary
- Need to understand where conversion differs
- Visual debugging of conversion issues

**Example**:
```
Open song1_heatmap.html → See frame 150-200 has red cells in Voice2 Waveform
→ Indicates waveform differences during that time period
```

### 5. Individual Comparisons (`comparisons/*.html`)

**Detailed side-by-side comparison**:
- **Overview Tab** - Summary metrics, accuracy stats
- **Detailed Comparison Tab** - Frame-by-frame register values (file A vs file B)
- **Differences Tab** - Only frames with differences
- **Statistics Tab** - Per-register accuracy breakdown

**When to Use**:
- Need exact register values for debugging
- Comparing two files in detail
- Understanding conversion differences at register level

**Example**:
```
Open song1_comparison.html
→ Overview tab: 99.8% frame match, 12 total differences
→ Differences tab: Shows frames 45, 112, 205 have Voice2 waveform mismatches
→ Detailed tab: See exact register values at those frames
```

---

## File Pairing Logic

### How It Works

The tool automatically pairs files from `dir_a` and `dir_b` by matching **basenames** after removing common suffixes.

### Suffix Removal Order

The tool removes suffixes in this order (stops after first match):

1. `_laxity_exported`
2. `_np20_exported`
3. `_d11_exported`
4. `.sf2_exported`
5. `_exported`
6. `_laxity`
7. `_np20`
8. `_d11`
9. `.sf2`

**Important**: Only **one suffix** is removed per filename to avoid over-normalization.

### Pairing Examples

| File in `dir_a` | File in `dir_b` | Matched? | Why |
|-----------------|-----------------|----------|-----|
| `song.sid` | `song_exported.sid` | ✅ Yes | `song_exported` → `song` (removed `_exported`) |
| `song.sid` | `song_laxity_exported.sid` | ✅ Yes | `song_laxity_exported` → `song` (removed `_laxity_exported`) |
| `song.sid` | `song.sf2_exported.sid` | ✅ Yes | `song.sf2_exported` → `song` (removed `.sf2_exported`) |
| `song.sid` | `song_laxity.sid` | ✅ Yes | `song_laxity` → `song` (removed `_laxity`) |
| `song.sid` | `song_d11.sid` | ✅ Yes | `song_d11` → `song` (removed `_d11`) |
| `song.sid` | `song_different.sid` | ❌ No | No matching suffix |
| `song_old.sid` | `song_new.sid` | ❌ No | Different basenames |

### Case Sensitivity

- **Windows**: Case-insensitive matching (`Song.sid` matches `song_exported.sid`)
- **Linux/Mac**: Case-sensitive by default (configure OS if needed)

### Multiple Matches

If multiple files in `dir_b` match the same file in `dir_a`, the tool uses the **first match found** (alphabetical order).

**Example**:
```
dir_a/
  song.sid

dir_b/
  song_exported.sid
  song_laxity_exported.sid

Result: song.sid paired with song_exported.sid (first alphabetically)
```

To avoid ambiguity, ensure unique naming in `dir_b`.

### Unpaired Files

Files in `dir_a` or `dir_b` without a match are **skipped** (reported in console output).

**Example**:
```
Finding SID pairs...
  Directory A: originals
  Directory B: exported
  Found 24 pairs
  [WARNING] 2 files in dir_a had no match in dir_b:
    - originals/orphan1.sid
    - originals/orphan2.sid
```

---

## Understanding Results

### Interpretation Guide

#### Frame Match Percentage

**What It Measures**: Percentage of frames where **all** SID registers match exactly.

| Range | Interpretation | Recommendation |
|-------|----------------|----------------|
| 95-100% | Excellent | Conversion is very accurate |
| 80-95% | Good | Minor differences, review heatmap |
| 60-80% | Moderate | Significant differences, investigate |
| <60% | Poor | Major issues, check conversion settings |

#### Register Accuracy

**What It Measures**: Percentage of individual register writes that match.

- **Higher than frame match %** - Most frames have only 1-2 register differences
- **Similar to frame match %** - Differences are spread across many registers

#### Voice Accuracy (Per Register)

**What It Measures**: Accuracy for each register type:
- **Frequency** (2 registers: freq_lo, freq_hi)
- **Waveform** (1 register: control)
- **ADSR** (2 registers: attack/decay, sustain/release)
- **Pulse** (2 registers: pulse_lo, pulse_hi)

**Use Case**: Identify which parameters are problematic.

**Example**:
```
Voice 1 Frequency: 100.0%  ← Perfect pitch
Voice 1 Waveform:  85.2%   ← Waveform conversion issues
Voice 1 ADSR:      99.1%   ← Envelope mostly correct
Voice 1 Pulse:     92.3%   ← Pulse width some differences
```

**Action**: Focus on fixing waveform conversion logic.

### Status Flags

| Status | Meaning | Typical Cause |
|--------|---------|---------------|
| `success` | Both files traced and compared successfully | Normal |
| `partial` | Tracing succeeded but heatmap/comparison failed | Disk space, permissions |
| `failed` | Tracing failed for one or both files | Corrupt SID, invalid format |

### Common Patterns

**All 100% accuracy**:
- Files are identical (expected if testing with copies)
- Perfect conversion (rare but possible)

**Consistent 99.x% accuracy**:
- High-quality conversion with minor differences
- Likely timing or rounding differences

**Wide accuracy spread (50%-100%)**:
- Conversion quality varies by file complexity
- Some files suit the driver better than others

**All files <50% accuracy**:
- Wrong driver selected (e.g., using Driver 11 for Laxity files)
- Conversion pipeline issue

---

## Integration

### Standalone CLI

**Use directly from command line**:
```bash
batch-analysis.bat originals/ exported/
```

**No integration needed** - Works independently.

### Validation Pipeline Integration

**✅ IMPLEMENTED** - Batch analysis fully integrated with SIDM2 validation system.

**How to Use**:
```bash
# Run batch analysis and store in validation database
batch-analysis-validate.bat originals/ exported/

# With custom options
batch-analysis-validate.bat originals/ exported/ --frames 500 --notes "Testing v3.1"

# Link to existing validation run
batch-analysis-validate.bat originals/ exported/ --run-id 5

# Generate dashboard with batch results
validation-dashboard.bat
```

**Features**:
- **Database Storage**: Results stored in `batch_analysis_results` and `batch_analysis_pair_results` tables
- **Git Tracking**: Auto-links to current git commit
- **Dashboard Display**: Batch results appear in "Batch Analysis" section of validation dashboard
- **Trend Analysis**: Track accuracy over multiple runs
- **Metrics Integration**: Batch metrics added to validation trends

**What's Stored**:
- Summary metrics (total pairs, success rate, avg accuracy)
- Per-pair details (frame match %, register accuracy, voice metrics)
- Links to HTML/CSV/JSON reports
- Configuration (frames, directories, options)
- Run metadata (timestamp, git commit, notes)

**View in Dashboard**:
```bash
# After running batch analysis
validation-dashboard.bat

# Dashboard shows:
# - Batch Analysis section in sidebar
# - Table with all batch runs (recent 10)
# - Links to HTML reports, CSV, JSON
# - Color-coded success rates and accuracy
# - Per-run statistics
```

### Conversion Cockpit GUI Integration

**✅ IMPLEMENTED** - Batch Analysis tab now available in Conversion Cockpit.

**How to Use**:

1. **Launch Conversion Cockpit**:
   ```bash
   conversion-cockpit.bat
   ```

2. **Navigate to Batch Analysis Tab**:
   - Click **"🔬 Batch Analysis"** (5th tab)

3. **Configure Analysis**:
   - **Dir A (Originals)**: Click "📁 Browse" → Select originals folder
   - **Dir B (Converted)**: Click "📁 Browse" → Select converted folder
   - **Output Directory**: Click "📁 Browse" → Select output folder
   - **Frames to trace**: Enter number (default: 300)
   - **Options**:
     - ✅ Generate accuracy heatmaps
     - ✅ Generate comparison HTMLs
     - ✅ Store results in validation database

4. **Run Analysis**:
   - Click **"🚀 Run Batch Analysis"**
   - Progress shown in status bar
   - Results populate table when complete

5. **View Results**:
   - **Results Table**: Per-pair metrics with color-coded status
     - 🟢 Green = Success (>95% accuracy)
     - 🟠 Orange = Partial (80-95% accuracy)
     - 🔴 Red = Failed (<80% accuracy)
   - **Stats Label**: Total pairs, success rate, avg accuracy
   - **Output Buttons**:
     - **📊 Open HTML Summary** - Interactive report
     - **📄 Open CSV Export** - Spreadsheet data
     - **📋 Open JSON Export** - Machine-readable results
     - **📁 Open Output Folder** - Browse all files

**Features**:
- **Integrated Workflow**: Run conversion → Run analysis (all in one tool)
- **Visual Feedback**: Color-coded status, sortable table
- **One-Click Access**: Direct links to all output files
- **Validation Option**: Check "Store in validation database" to integrate with validation pipeline
- **Auto-Population**: Directories pre-filled after batch conversion

**Typical Workflow**:
1. **Batch Conversion Tab**: Convert 25 files → Wait for completion
2. **Batch Analysis Tab**: Already configured → Click "Run Batch Analysis"
3. **Review Results**: Table shows all pairs → Click "Open HTML Summary" for details
4. **Validation Dashboard**: Run `validation-dashboard.bat` to see trends

### CI/CD Integration

**Use JSON output for automation**:

```bash
# Run batch analysis in CI pipeline
batch-analysis.bat originals/ exported/ --no-html --frames 300

# Parse JSON results
python ci/check_accuracy.py batch_analysis_output/batch_results.json

# Fail build if avg accuracy < 95%
```

**Example Python script**:
```python
import json
import sys

with open('batch_analysis_output/batch_results.json') as f:
    data = json.load(f)

avg_accuracy = data['summary']['avg_frame_match']

if avg_accuracy < 95.0:
    print(f"[FAIL] Average accuracy {avg_accuracy:.2f}% below threshold (95%)")
    sys.exit(1)
else:
    print(f"[PASS] Average accuracy {avg_accuracy:.2f}%")
    sys.exit(0)
```

---

## Troubleshooting

### Common Issues

#### "No pairs found"

**Symptoms**:
```
Finding SID pairs...
  Found 0 pairs
```

**Causes**:
1. **No matching files** - Basenames don't match after suffix removal
2. **Wrong directories** - Check paths are correct
3. **Files in wrong directory** - All files in one directory

**Solutions**:
```bash
# Check what files exist
ls originals/
ls exported/

# Verify naming convention
# Expected: originals/song.sid, exported/song_exported.sid

# If names don't match, rename files
# Example: exported/song_laxity.sid → exported/song_laxity_exported.sid
```

#### "Tracing failed for *.sid"

**Symptoms**:
```
[1/10] song.sid vs song_exported.sid
  Tracing song.sid...
  [ERROR] Tracing failed: Invalid SID format
```

**Causes**:
1. **Corrupt SID file** - File is damaged
2. **Invalid format** - Not a valid SID file
3. **Missing SIDwinder** - Emulator not found

**Solutions**:
```bash
# Verify SID file
python pyscript/siddump_complete.py song.sid

# If corrupt, re-export from source
# If invalid, check file is actually a SID

# Check SIDwinder exists
ls tools/SIDwinder.exe  # Windows
ls tools/SIDwinder      # Linux/Mac
```

#### "Permission denied" writing outputs

**Symptoms**:
```
[ERROR] Failed to write batch_summary.html: Permission denied
```

**Causes**:
1. **Output directory is read-only**
2. **File already open** - HTML/CSV open in browser/Excel
3. **Insufficient permissions**

**Solutions**:
```bash
# Close all open report files
# Use different output directory
batch-analysis.bat originals/ exported/ -o results_new/

# Check permissions
ls -la batch_analysis_output/
```

#### Slow performance (>10s per pair)

**Symptoms**:
```
[1/10] song.sid vs song_exported.sid
  [OK] 99.8% accuracy, 15.3s    ← Too slow
```

**Causes**:
1. **Too many frames** - Default 300, or set higher
2. **Disk I/O** - Output directory on slow drive
3. **Large SID files** - Complex files take longer

**Solutions**:
```bash
# Reduce frame count
batch-analysis.bat originals/ exported/ --frames 100

# Skip optional outputs
batch-analysis.bat originals/ exported/ --no-heatmaps --no-comparisons

# Use local SSD for output
batch-analysis.bat originals/ exported/ -o C:/temp/results/
```

### Debug Mode

**Enable verbose output**:
```bash
# Show detailed progress
batch-analysis.bat originals/ exported/ -v

# Show trace details
batch-analysis.bat originals/ exported/ -vv
```

**Check log output**:
```
[1/10] song.sid vs song_exported.sid
  Tracing song.sid...
    [TRACE] Loaded: originals/song.sid (3907 bytes)
    [TRACE] Init: $1000, Play: $10A1
    [TRACE] Tracing 300 frames...
    [TRACE] Completed: 300 frames, 1247 register writes
  Tracing song_exported.sid...
    [TRACE] Loaded: exported/song_exported.sid (3907 bytes)
    [TRACE] Init: $1000, Play: $10A1
    [TRACE] Tracing 300 frames...
    [TRACE] Completed: 300 frames, 1247 register writes
  Comparing traces...
    [TRACE] Frame matches: 298/300 (99.3%)
    [TRACE] Register matches: 1245/1247 (99.8%)
  [OK] 99.3% accuracy, 2.1s
```

---

## Advanced Usage

### Custom File Pairing

If automatic pairing doesn't work for your naming convention, create a Python script:

```python
# custom_batch_analysis.py
from pathlib import Path
from pyscript.batch_analysis_engine import BatchAnalysisEngine, BatchAnalysisConfig

# Define custom pairs
pairs = [
    (Path("originals/track01.sid"), Path("converted/track01_new.sid")),
    (Path("originals/track02.sid"), Path("converted/track02_new.sid")),
    # ... more pairs
]

# Create config
config = BatchAnalysisConfig(
    dir_a=Path("originals"),
    dir_b=Path("converted"),
    output_dir=Path("results"),
    frames=300,
    generate_heatmaps=True,
    generate_comparisons=True,
)

# Run analysis with custom pairs
engine = BatchAnalysisEngine(config)
engine.pairs = pairs  # Override auto-paired list
summary = engine.run()

print(f"Average accuracy: {summary.avg_frame_match:.2f}%")
```

### Parallel Processing

**Coming Soon**: Multi-core batch analysis.

**Current**: Sequential processing (1 pair at a time)
**Planned**: Process multiple pairs in parallel using Python multiprocessing

**Estimated speedup**: 3-4x on quad-core systems

### Custom Metrics

Extract specific metrics from JSON output:

```python
# analyze_results.py
import json

with open('batch_analysis_output/batch_results.json') as f:
    data = json.load(f)

# Find files with Voice 2 accuracy < 90%
voice2_issues = [
    r for r in data['results']
    if r['metrics']['voice_accuracy']['voice2']['frequency'] < 90.0
]

print(f"Files with Voice 2 frequency issues: {len(voice2_issues)}")
for r in voice2_issues:
    filename = r['filename_a']
    accuracy = r['metrics']['voice_accuracy']['voice2']['frequency']
    print(f"  {filename}: {accuracy:.2f}%")
```

### Regression Testing

Compare two batch runs to detect regressions:

```bash
# Baseline (v3.0)
batch-analysis.bat originals/ exported_v3.0/ -o baseline/

# New version (v3.1)
batch-analysis.bat originals/ exported_v3.1/ -o new_version/

# Compare
python compare_batch_runs.py baseline/batch_results.json new_version/batch_results.json
```

```python
# compare_batch_runs.py
import json
import sys

def load_results(path):
    with open(path) as f:
        return json.load(f)

baseline = load_results(sys.argv[1])
new_ver = load_results(sys.argv[2])

baseline_avg = baseline['summary']['avg_frame_match']
new_avg = new_ver['summary']['avg_frame_match']

diff = new_avg - baseline_avg

print(f"Baseline:    {baseline_avg:.2f}%")
print(f"New version: {new_avg:.2f}%")
print(f"Change:      {diff:+.2f}%")

if diff < -1.0:
    print("[REGRESSION] Accuracy decreased by >1%")
    sys.exit(1)
elif diff > 1.0:
    print("[IMPROVEMENT] Accuracy increased by >1%")
    sys.exit(0)
else:
    print("[NO CHANGE] Within ±1% tolerance")
    sys.exit(0)
```

---

## Performance Tips

### Optimize for Speed

**Fastest configuration** (metrics only):
```bash
batch-analysis.bat originals/ exported/ --frames 100 --no-heatmaps --no-comparisons --no-csv --no-json
# Expected: <1s per pair
```

**Balanced configuration** (HTML summary + key metrics):
```bash
batch-analysis.bat originals/ exported/ --frames 300 --no-heatmaps --no-comparisons
# Expected: 1-2s per pair
```

**Full analysis** (all artifacts):
```bash
batch-analysis.bat originals/ exported/ --frames 300
# Expected: 2-5s per pair
```

### Disk I/O Optimization

- Use **SSD** for output directory
- Use **local drive** (not network share)
- **Close Excel/browser** before running (avoid file locks)

### Memory Optimization

- **Reduce frames** if running out of memory (`--frames 100`)
- **Process in batches** - Analyze 20-30 files at a time instead of 100+

---

## Summary

The Batch Analysis Tool provides comprehensive automated comparison of multiple SID file pairs, with:

✅ **Automatic file pairing** - Handles common naming conventions
✅ **Comprehensive metrics** - Frame match, register accuracy, per-voice breakdown
✅ **Visual analysis** - Heatmaps and detailed comparison HTMLs
✅ **Multiple formats** - Interactive HTML, CSV, JSON
✅ **Error handling** - Failed pairs don't stop batch
✅ **Performance** - 2-5s per pair, configurable

**Quick Start**:
```bash
batch-analysis.bat originals/ exported/ -o results/
start results/batch_summary.html
```

**Documentation**:
- This guide: `docs/guides/BATCH_ANALYSIS_GUIDE.md`
- Architecture: `docs/ARCHITECTURE.md`
- Troubleshooting: `docs/guides/TROUBLESHOOTING.md`

**Support**:
- GitHub Issues: https://github.com/MichaelTroelsen/SIDM2conv/issues
- Documentation Index: `docs/INDEX.md`

---

**End of Guide** | Updated 2026-01-02 | SIDM2 v3.1.0
