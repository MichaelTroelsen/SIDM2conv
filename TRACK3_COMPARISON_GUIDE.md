# Track 3 Comparison Test Guide

This guide explains how to use the `test_track3_comparison.py` tool to validate Track 3 extraction from SF2 files.

## Overview

The Track 3 comparison tool helps you:
1. Extract Track 3 data from SF2 files
2. Compare extracted data with expected reference data
3. Generate detailed comparison reports (text and HTML)

## Quick Start

### Step 1: Create Reference File

First, you need a reference file with the expected Track 3 data. You can either:

**Option A: Create manually**

Create `track_3.txt` with this format:
```
Step  In Cmd Note
----  -- --- ----
0000  01 -- C-3
0001  -- -- ---
0002  01 -- D-3
0003  -- -- +++
```

**Option B: Extract from known-good SF2 file**

```bash
python test_track3_comparison.py path/to/good.sf2 --extract --sequence 0 > track_3_reference.txt
```

### Step 2: Run Comparison

Compare an SF2 file against your reference:

```bash
# Text report (default)
python test_track3_comparison.py path/to/test.sf2 track_3_reference.txt

# Side-by-side text comparison
python test_track3_comparison.py path/to/test.sf2 track_3_reference.txt --side-by-side

# HTML report with color coding
python test_track3_comparison.py path/to/test.sf2 track_3_reference.txt --html track3_comparison.html
```

### Step 3: Review Results

The tool shows:
- **Match rate**: Percentage of identical steps
- **Differences**: Line-by-line comparison of mismatches
- **Field-level details**: Exactly which fields differ (instrument, command, note)

## Reference File Format

The reference file must follow this exact format:

```
Step  In Cmd Note
----  -- --- ----
0000  01 -- C-3
0001  -- -- ---
0002  02 0F D#4
```

**Format Details**:
- Line 1: Column headers (must include "Step", "In", "Cmd", "Note")
- Line 2: Separator line with dashes
- Data lines: `STEP  In Cmd Note` (positions matter!)
  - Step: 4-digit hex (0000-FFFF)
  - Space (2 chars)
  - Instrument: 2 chars (hex or "--")
  - Space
  - Command: 2 chars (hex or "--")
  - Space
  - Note: 4 chars (e.g., "C-3 ", "---", "+++")

## Command Line Options

```
python test_track3_comparison.py <sf2_file> [reference_file] [options]

Arguments:
  sf2_file          Path to SF2 file to test
  reference_file    Path to reference Track 3 text file (optional if --extract)

Options:
  --sequence N, -s N    Sequence index to extract (default: 0)
  --extract, -e         Extract Track 3 and output as reference format
  --html FILE           Generate HTML comparison report to FILE
  --side-by-side, -sbs  Generate side-by-side text comparison
```

## Usage Examples

### Example 1: Create Reference from Known-Good File

```bash
# Extract Track 3 from sequence 0
python test_track3_comparison.py output/MySong/New/MySong_d11.sf2 --extract > track_3_expected.txt

# Verify the reference looks correct
cat track_3_expected.txt
```

### Example 2: Compare Two Files

```bash
# Compare test file against reference
python test_track3_comparison.py output/MySong/New/MySong_laxity.sf2 track_3_expected.txt

# Output example:
# ================================================================================
# TRACK 3 COMPARISON REPORT
# ================================================================================
#
# Total steps:     256
# Matched:         240 (93.8%)
# Differences:     16 (6.2%)
#
# DIFFERENCES:
# --------------------------------------------------------------------------------
#
# Step 0012: MISMATCH
#   Extracted: 01 -- C-3
#   Reference: 02 -- C-3
#     • Instrument: 01 ≠ 02
```

### Example 3: Generate HTML Report

```bash
# Generate visual HTML report
python test_track3_comparison.py output/MySong/New/MySong_laxity.sf2 track_3_expected.txt \
    --html track3_report.html

# Open in browser
# The HTML report shows:
# - Color-coded differences (red = mismatch, yellow = extra, blue = missing)
# - Side-by-side comparison table
# - Match rate statistics
# - Highlighted differing fields
```

### Example 4: Side-by-Side Text Comparison

```bash
# Get detailed side-by-side view
python test_track3_comparison.py output/MySong/New/MySong_laxity.sf2 track_3_expected.txt --side-by-side

# Output example:
# ================================================================================
# TRACK 3 SIDE-BY-SIDE COMPARISON
# ================================================================================
#
# Step  EXTRACTED          REFERENCE          STATUS
#       In Cmd Note        In Cmd Note
# ----  -- --- ----        -- --- ----        ------
# 0000  01 -- C-3          01 -- C-3          ✓ OK
# 0001  -- -- ---          -- -- ---          ✓ OK
# 0002  01 -- D-3          02 -- D-3          ✗ DIFF
# 0003  -- -- +++          -- -- +++          ✓ OK
```

### Example 5: Test Different Sequences

```bash
# Most SF2 files have sequence 0, but you can test others
python test_track3_comparison.py file.sf2 track_3_ref.txt --sequence 1
python test_track3_comparison.py file.sf2 track_3_ref.txt --sequence 2
```

## Interpreting Results

### Text Report

The default text report shows:
1. **Summary**: Total steps, match count, difference count
2. **Differences**: Detailed list of all mismatches with field-level breakdown

**Status Indicators**:
- `✓ Perfect match!` - All steps identical
- `Step XXXX: MISMATCH` - Fields differ
- `Step XXXX: EXTRA` - Extra step in extracted (not in reference)
- `Step XXXX: MISSING` - Missing step in extracted (exists in reference)

### HTML Report

The HTML report provides:
- **Color coding**:
  - Green: Matching steps
  - Red: Mismatches
  - Yellow: Extra steps
  - Blue: Missing steps
- **Highlighted fields**: Differing fields shown in orange
- **Match rate**: Large percentage display
- **Interactive table**: Full side-by-side comparison

## Workflow Integration

### Daily Testing Workflow

```bash
# 1. Create reference from known-good conversion
python test_track3_comparison.py output/Reference/song.sf2 --extract > references/song_track3.txt

# 2. Make changes to extraction code
# ... edit sf2_viewer_core.py or conversion scripts ...

# 3. Test against reference
python test_track3_comparison.py output/Test/song.sf2 references/song_track3.txt --html results/track3.html

# 4. Review HTML report in browser
# 5. If OK, update reference; if not, fix code and repeat
```

### Batch Testing Multiple Files

```bash
#!/bin/bash
# batch_test_track3.sh

for sf2_file in output/*/New/*_laxity.sf2; do
    basename=$(basename "$sf2_file" .sf2)
    ref_file="references/${basename}_track3.txt"

    if [ -f "$ref_file" ]; then
        echo "Testing: $basename"
        python test_track3_comparison.py "$sf2_file" "$ref_file" --html "results/${basename}_track3.html"
    fi
done
```

## Troubleshooting

### Error: "No sequences found"
- SF2 file doesn't contain sequence data
- Try using --extract to see what's in the file
- Check if file is corrupted or incomplete

### Error: "Sequence X not found"
- Requested sequence index doesn't exist
- Use --sequence 0 for the first sequence
- Check how many sequences the file contains

### Reference file parse errors
- Verify reference file format matches exactly
- Check spacing (must be exact)
- Ensure step numbers are 4-digit hex
- Make sure header lines are present

### All steps show as MISMATCH
- Reference file might be from wrong sequence
- Extraction code might have changed significantly
- Verify reference was created correctly

## Advanced Usage

### Creating Test Suites

```python
# test_suite_track3.py
import subprocess
import sys

test_cases = [
    ("output/Song1/New/Song1_laxity.sf2", "references/song1_track3.txt"),
    ("output/Song2/New/Song2_laxity.sf2", "references/song2_track3.txt"),
    # ... more test cases ...
]

failures = 0
for sf2_file, ref_file in test_cases:
    result = subprocess.run(
        ["python", "test_track3_comparison.py", sf2_file, ref_file],
        capture_output=True,
        text=True
    )

    # Check if 100% match
    if "100.0%" in result.stdout:
        print(f"✓ PASS: {sf2_file}")
    else:
        print(f"✗ FAIL: {sf2_file}")
        failures += 1

sys.exit(failures)
```

### Automated CI/CD Integration

```yaml
# .github/workflows/track3_validation.yml
name: Track 3 Validation

on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Test Track 3 extraction
        run: |
          python test_track3_comparison.py \
            output/Test/test.sf2 \
            references/test_track3.txt \
            --html track3_report.html
      - name: Upload report
        uses: actions/upload-artifact@v2
        with:
          name: track3-comparison
          path: track3_report.html
```

## Reference File Management

### Best Practices

1. **Version control**: Keep reference files in git
2. **Naming convention**: `{song_name}_track3.txt` or `{song_name}_seq{N}_track3.txt`
3. **Directory structure**:
   ```
   references/
   ├── song1_track3.txt
   ├── song2_track3.txt
   └── README.md
   ```
4. **Documentation**: Note which SF2 file each reference was created from
5. **Updates**: When extraction improves, update references with new extracts

### Creating a Reference Library

```bash
#!/bin/bash
# create_reference_library.sh

mkdir -p references

for sf2_file in output/*/New/*_laxity.sf2; do
    basename=$(basename "$sf2_file" _laxity.sf2)
    ref_file="references/${basename}_track3.txt"

    echo "Creating reference: $ref_file"
    python test_track3_comparison.py "$sf2_file" --extract > "$ref_file"
done

echo "Created $(ls references/*.txt | wc -l) reference files"
```

## Contributing

If you improve the Track 3 comparison tool:
1. Update this guide
2. Add new examples
3. Document new features
4. Update reference file format if changed

## See Also

- `SF2_VIEWER_IMPLEMENTATION_SUMMARY.md` - SF2 viewer architecture
- `docs/SF2_TRACKS_AND_SEQUENCES.md` - Track/sequence format details
- `sf2_viewer_core.py` - Track 3 extraction implementation
- `CLAUDE.md` - Project overview and conventions
