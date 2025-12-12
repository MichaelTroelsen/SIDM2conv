# Validation Dashboard & Regression Tracking System

## Overview

A comprehensive validation system that tracks conversion quality, detects regressions, and provides a visual dashboard for monitoring the SIDM2 pipeline.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Validation System                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐ │
│  │  Validation  │───▶│  Validation  │───▶│  Dashboard   │ │
│  │    Runner    │    │   Database   │    │  Generator   │ │
│  └──────────────┘    └──────────────┘    └──────────────┘ │
│         │                    │                    │         │
│         │                    │                    │         │
│  ┌──────▼──────┐    ┌───────▼────┐    ┌──────────▼─────┐ │
│  │   Metrics   │    │ Regression │    │   HTML/JSON    │ │
│  │ Collection  │    │  Detector  │    │    Reports     │ │
│  └─────────────┘    └────────────┘    └────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Validation Database

**Format**: SQLite database for structured queries + JSON for interchange

**Schema**:
```sql
-- Validation runs (one per pipeline execution)
CREATE TABLE validation_runs (
    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    git_commit TEXT,
    pipeline_version TEXT,
    notes TEXT
);

-- File results (one per file per run)
CREATE TABLE file_results (
    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    filename TEXT NOT NULL,

    -- Conversion metrics
    conversion_method TEXT,
    conversion_success BOOLEAN,
    conversion_time_ms INTEGER,

    -- File sizes
    original_size INTEGER,
    sf2_size INTEGER,
    exported_size INTEGER,

    -- Accuracy metrics (from validate_sid_accuracy.py)
    overall_accuracy REAL,
    frame_accuracy REAL,
    voice_accuracy REAL,
    register_accuracy REAL,
    filter_accuracy REAL,

    -- Pipeline steps success
    step1_conversion BOOLEAN,
    step2_packing BOOLEAN,
    step3_siddump BOOLEAN,
    step4_wav BOOLEAN,
    step5_hexdump BOOLEAN,
    step6_trace BOOLEAN,
    step7_info BOOLEAN,
    step8_disasm_python BOOLEAN,
    step9_disasm_sidwinder BOOLEAN,

    -- Quality indicators
    sidwinder_warnings INTEGER,
    audio_diff_rms REAL,

    FOREIGN KEY (run_id) REFERENCES validation_runs(run_id)
);

-- Metrics history for trend analysis
CREATE TABLE metric_trends (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER,
    metric_name TEXT,
    metric_value REAL,
    FOREIGN KEY (run_id) REFERENCES validation_runs(run_id)
);
```

### 2. Validation Runner

**Script**: `scripts/run_validation.py`

**Responsibilities**:
- Execute complete pipeline on all test files
- Collect metrics from each step
- Parse existing outputs (dumps, info.txt, etc.)
- Calculate accuracy scores
- Store results in database
- Detect regressions by comparing with previous run

**Usage**:
```bash
# Run validation on all files
python scripts/run_validation.py

# Run with specific baseline for comparison
python scripts/run_validation.py --baseline run_42

# Quick validation (subset of files)
python scripts/run_validation.py --quick

# Export results to JSON
python scripts/run_validation.py --export validation_results.json
```

### 3. Dashboard Generator

**Script**: `scripts/generate_dashboard.py`

**Outputs**:
1. **HTML Dashboard** (`validation/dashboard.html`)
   - Overview summary (pass rates, avg accuracy)
   - File-by-file results table
   - Trend charts (accuracy over time)
   - Regression alerts
   - Recent changes comparison

2. **JSON Report** (`validation/latest.json`)
   - Machine-readable format
   - For CI/CD integration

3. **Markdown Summary** (`validation/SUMMARY.md`)
   - Git-friendly format
   - Commit to track changes

**Features**:
- Interactive charts using Chart.js
- Sortable/filterable tables
- Color-coded pass/fail indicators
- Drill-down into individual file details
- Diff view for regressions

### 4. Regression Detector

**Integrated into Validation Runner**

**Detection Rules**:
```python
# Regression if:
- Overall accuracy drops > 5%
- Any file that was passing now fails
- File size increases > 20%
- New SIDwinder warnings appear
- Audio diff increases > threshold
```

**Alerts**:
- Console warning during validation
- Dashboard highlights regressions in red
- Optional: Email/webhook notification

## Metrics Tracked

### Per-File Metrics
1. **Conversion Success**: Boolean (did conversion complete?)
2. **Accuracy Scores**: Overall, Frame, Voice, Register, Filter (0-100%)
3. **File Sizes**: Original, SF2, Exported (bytes)
4. **Pipeline Steps**: Success/Failure for each of 9 steps
5. **Quality Indicators**:
   - SIDwinder warnings count
   - Audio RMS difference
   - Hexdump diff percentage
   - Siddump match percentage

### Aggregate Metrics
1. **Pass Rate**: % of files completing all steps
2. **Average Accuracy**: Mean across all files
3. **File Size Efficiency**: Avg exported/original ratio
4. **Success by Method**: REFERENCE vs TEMPLATE vs LAXITY
5. **Trend Direction**: Improving/Declining/Stable

## Dashboard Layout

### Section 1: Overview
```
╔══════════════════════════════════════════════════════════╗
║  SIDM2 Validation Dashboard                              ║
║  Run: 2025-12-12 08:30:45 | Commit: 40688e4             ║
╠══════════════════════════════════════════════════════════╣
║  📊 Overall Metrics                                      ║
║  • Files Tested: 18                                      ║
║  • Pass Rate: 100% (18/18)                              ║
║  • Avg Accuracy: 68.2% (↑ 2.3% from last run)          ║
║  • Avg File Size: 3,842 bytes                           ║
║  • Regressions: 0 🎉                                    ║
╚══════════════════════════════════════════════════════════╝
```

### Section 2: Trend Charts
- Accuracy over time (line chart)
- Pass rate over time
- File size trends
- Success by conversion method

### Section 3: File Results Table
| File | Method | Accuracy | Steps | Size | Status | Details |
|------|--------|----------|-------|------|--------|---------|
| Stinsens | LAXITY | 72.4% | 9/9 ✅ | 3.8KB | ✅ PASS | [View] |
| Cocktail | TEMPLATE | 71.2% | 9/9 ✅ | 3.9KB | ✅ PASS | [View] |
| ...

### Section 4: Regressions (if any)
```
⚠️  REGRESSIONS DETECTED (2)

1. Angular.sid
   - Accuracy: 68.2% → 62.1% (-6.1%) ❌
   - Cause: Unknown

2. Broware.sid
   - Step 9 (SIDwinder): Pass → Fail ❌
   - Error: "Execution timeout"
```

### Section 5: Detailed File View
Clicking a file shows:
- Full metrics history
- Accuracy breakdown by category
- Pipeline step details
- Diff from previous run
- Links to generated files

## Usage Workflow

### 1. Run Validation
```bash
# After making code changes
python scripts/run_validation.py

# View dashboard
open validation/dashboard.html
```

### 2. CI/CD Integration
```yaml
# .github/workflows/validation.yml
- name: Run Validation
  run: python scripts/run_validation.py --export results.json

- name: Check for Regressions
  run: |
    if grep -q '"regressions": [^0]' results.json; then
      echo "Regressions detected!"
      exit 1
    fi
```

### 3. Track Progress
```bash
# Generate trend report
python scripts/generate_dashboard.py --trends --since "7 days ago"

# Compare two specific runs
python scripts/generate_dashboard.py --compare run_42 run_45
```

## File Structure

```
SIDM2/
├── validation/                    # Validation data directory
│   ├── database.sqlite           # SQLite database
│   ├── dashboard.html            # Interactive dashboard
│   ├── latest.json               # Latest results (JSON)
│   ├── SUMMARY.md                # Latest summary (Markdown)
│   └── runs/                     # Per-run detailed data
│       ├── run_001/
│       ├── run_002/
│       └── ...
├── scripts/
│   ├── run_validation.py         # Main validation runner
│   ├── generate_dashboard.py    # Dashboard generator
│   └── validation/               # Validation utilities
│       ├── __init__.py
│       ├── database.py           # DB operations
│       ├── metrics.py            # Metric collection
│       ├── regression.py         # Regression detection
│       └── dashboard.py          # HTML generation
```

## Implementation Phases

### Phase 1: Core Infrastructure (P0) - ✅ COMPLETED
- [x] Design architecture
- [x] Create database schema
- [x] Build validation runner skeleton
- [x] Implement basic metric collection

### Phase 2: Dashboard (P0) - ✅ COMPLETED
- [x] Create HTML template
- [x] Generate basic dashboard
- [x] Add file results table
- [x] Add trend charts

### Phase 3: Regression Detection (P1) - ✅ COMPLETED
- [x] Implement comparison logic
- [x] Add regression rules
- [x] Create alerts system
- [x] Add diff visualization

### Phase 4: Polish & Integration (P1) - 🚧 IN PROGRESS
- [x] Add command-line options
- [x] Create documentation
- [ ] Add CI/CD integration
- [ ] Optimize performance

### Phase 5: Advanced Features (P2) - 📋 PLANNED
- [ ] Email notifications
- [ ] Slack/webhook integration
- [ ] Custom metric plugins
- [ ] Historical data export

## Benefits

### For Development
- **Immediate feedback** on code changes
- **Catch regressions** before they reach production
- **Track progress** toward accuracy goals
- **Identify problematic files** quickly

### For Testing
- **Systematic validation** of all test files
- **Automated quality checks**
- **Historical comparison** to see trends
- **Easy triage** of failures

### For Reporting
- **Visual progress** for stakeholders
- **Data-driven decisions** on priorities
- **Confidence metrics** for releases
- **Documentation** of quality improvements

## Success Metrics

The validation system itself will be measured by:
1. **Coverage**: 100% of test files validated
2. **Speed**: < 5 minutes for full validation run
3. **Accuracy**: Catches 100% of known regressions
4. **Usability**: Dashboard loaded < 1 second
5. **Adoption**: Used in every PR/release

## Implementation Summary

**Implemented**: 2025-12-12
**Status**: Core system complete and operational

### What Was Built

1. **Database System** (`scripts/validation/database.py`)
   - SQLite backend with 3 tables (validation_runs, file_results, metric_trends)
   - Complete CRUD operations for runs, results, and metrics
   - Run comparison for regression detection
   - JSON export capabilities

2. **Metrics Collection** (`scripts/validation/metrics.py`)
   - Collects metrics from all pipeline output files
   - Tracks 9 pipeline steps (conversion → disassembly)
   - Parses info.txt for accuracy data and conversion method
   - Calculates aggregate metrics (pass rate, avg accuracy, file size efficiency)

3. **Regression Detection** (`scripts/validation/regression.py`)
   - Compares two validation runs to detect regressions
   - Detection rules:
     - Accuracy drops >5% (critical regression)
     - Any step changing from pass → fail (critical regression)
     - File size increases >20% (regression)
     - New warnings (warning level)
   - Formatted reports with severity levels

4. **Validation Runner** (`scripts/run_validation.py`)
   - Command-line tool to run validation on all test files
   - Collects metrics and stores in database
   - Optional regression detection against baseline
   - JSON export support
   - Quick mode for subset testing

5. **Dashboard Generator** (`scripts/generate_dashboard.py`)
   - Generates interactive HTML dashboard
   - Responsive design with gradient cards
   - Trend charts using Chart.js
   - Sortable results table
   - Optional markdown summary generation

### Usage

```bash
# Run validation on all pipeline outputs
python scripts/run_validation.py --notes "After pointer fix"

# Run with regression detection
python scripts/run_validation.py --baseline 1 --notes "Test regression"

# Generate HTML dashboard
python scripts/generate_dashboard.py

# Generate both HTML and markdown
python scripts/generate_dashboard.py --markdown validation/SUMMARY.md

# Compare two runs
python scripts/run_validation.py --compare 1 2

# Quick validation (subset of files)
python scripts/run_validation.py --quick
```

### Test Results

**First Run** (2025-12-12):
- 18 files tested
- 100% pass rate
- All 9 pipeline steps completed successfully
- Database: `validation/database.sqlite`
- Dashboard: `validation/dashboard.html`

### Known Limitations

1. **Accuracy Metrics**: Currently showing 0% because accuracy calculation (validate_sid_accuracy.py) is not integrated into the main pipeline. This requires:
   - Running validate_sid_accuracy.py separately
   - Updating info.txt with accuracy results
   - Or integrating accuracy validation into complete_pipeline_with_validation.py

2. **Windows Console**: Requires UTF-8 encoding fix for emoji display (already implemented)

### Next Steps

1. Integrate accuracy validation into main pipeline
2. Add CI/CD integration (GitHub Actions)
3. Optimize metric collection for large batches
4. Add email/webhook notifications for regressions
