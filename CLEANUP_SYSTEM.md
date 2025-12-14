# SIDM2 Cleanup System - Complete Guide

**Version**: 2.0
**Date**: 2025-12-14

---

## Quick Summary

This project now has a comprehensive cleanup system with:

✅ **Automated cleanup tool** (`cleanup.py`)
✅ **Dedicated experiments directory** (`experiments/`)
✅ **Experiment template system** (`new_experiment.py`)
✅ **Updated .gitignore** (prevents committing experiments)
✅ **Self-cleaning experiments** (each has cleanup script)
✅ **Complete documentation** (`docs/CLEANUP_GUIDE.md`)

---

## Can I Delete the Output Folder?

### Short Answer: **YES**

Everything in `output/` is generated and can be safely deleted.

### What's in Output

```
output/
├── SIDSF2player_Complete_Pipeline/  # Main pipeline results
│   └── [18 song directories]        # Can regenerate (10-30 min)
│
├── test_*/                          # Test outputs - DELETE
├── Test_*/                          # Test outputs - DELETE
├── midi_comparison/                 # Temporary - DELETE
└── Laxity_Test/                     # Experimental - DELETE
```

### What to Keep (NOT in output/)

```
validation/                # Validation history - KEEP
├── database.sqlite       # Historical validation data
├── dashboard.html        # Interactive dashboard
└── SUMMARY.md            # Markdown summary
```

### Regeneration Times

| Directory | Regeneration Time | Command |
|-----------|------------------|---------|
| Complete Pipeline | ~10 min (no WAV) | `python complete_pipeline_with_validation.py` |
| Complete Pipeline | ~30 min (with WAV) | Same |
| Validation Data | ~1 min | `python scripts/run_validation.py` |

**Recommendation**: Delete `output/` whenever it gets large (>100 MB). Keep `validation/` for history.

---

## Cleanup Tools Usage

### cleanup.py - Main Cleanup Tool

```bash
# Scan everything (safe, no changes)
python cleanup.py --scan

# Clean root + output (default)
python cleanup.py --clean

# Clean only output directory
python cleanup.py --output-only --clean

# Clean only experiments
python cleanup.py --experiments --clean

# Clean everything (root + output + experiments)
python cleanup.py --all --clean

# Force mode (no confirmation)
python cleanup.py --clean --force
```

### Current Cleanup Results

Based on latest scan (2025-12-14):

```
Files to clean: 41
  - Log files: 22 files
  - Test files: 16 files
  - Orphaned outputs: 3 files

Directories to clean: 18
  - output/test_* directories

Total size: 2.5 MB
```

---

## Experiment Workflow

### 1. Create New Experiment

```bash
# Create experiment with template
python new_experiment.py "wave_table_analysis"

# Or with description
python new_experiment.py "filter_fix" --description "Test filter format conversion"
```

This creates:
```
experiments/wave_table_analysis/
├── experiment.py       # Template script
├── README.md          # Documentation template
├── output/            # Generated files
├── cleanup.sh         # Unix cleanup script
└── cleanup.bat        # Windows cleanup script
```

### 2. Work on Experiment

```bash
cd experiments/wave_table_analysis

# Edit experiment code
vim experiment.py

# Run experiment
python experiment.py

# Document findings
vim README.md
```

### 3. Complete Experiment

**If successful**:
```bash
# Document in README.md
vim README.md

# Move to production
mv experiment.py ../../scripts/wave_table_converter.py

# Cleanup
./cleanup.bat  # Windows
# or
./cleanup.sh   # Unix
```

**If failed**:
```bash
# Document why it failed
vim README.md

# Cleanup
./cleanup.bat
```

### 4. Cleanup All Experiments

```bash
# From project root
python cleanup.py --experiments --clean
```

---

## File Organization

### Where Things Go

```
SIDM2/
├── scripts/              # ✅ Production scripts (committed)
│   ├── sid_to_sf2.py
│   └── test_*.py        # Unit tests (keep)
│
├── sidm2/                # ✅ Core package (committed)
│   ├── sf2_packer.py
│   └── ...
│
├── experiments/          # ⚠️ Temporary (gitignored, auto-cleanup)
│   ├── README.md        # How to use experiments
│   ├── {experiment}/    # Your experiments
│   └── ARCHIVE/         # Valuable findings (optional)
│
├── output/               # ⚠️ Generated (gitignored, can delete)
│   ├── SIDSF2player_Complete_Pipeline/  # Keep (or regenerate)
│   └── test_*/          # Delete
│
├── validation/           # ✅ Keep (historical data)
│   ├── database.sqlite
│   └── dashboard.html
│
└── docs/                 # ✅ Documentation (committed)
    ├── CLEANUP_GUIDE.md
    └── ...
```

### Naming Conventions

| Type | Location | Prefix | Example | Keep? |
|------|----------|--------|---------|-------|
| Production | `scripts/` | None | `sid_to_sf2.py` | ✅ YES |
| Unit Tests | `scripts/` | `test_` | `test_converter.py` | ✅ YES |
| Experiments | `experiments/` | Any | `wave_fix/` | ⚠️ Temporary |
| Test Files | Root | `test_` | `test_debug.py` | ❌ Clean |
| Temp Files | Root | `temp_`, `tmp_` | `temp_output.wav` | ❌ Clean |
| Logs | Root | `*.log` | `pipeline.log` | ❌ Clean |

---

## Cleanup Schedule

### Daily (If Active Development)
```bash
# Quick scan
python cleanup.py --scan

# Clean if > 10 MB
python cleanup.py --clean
```

### Weekly
```bash
# Full scan
python cleanup.py --all --scan

# Clean experiments
python cleanup.py --experiments --clean

# Clean output tests
python cleanup.py --output-only --clean
```

### Monthly
```bash
# Full cleanup
python cleanup.py --all --clean

# Update file inventory
python update_inventory.py
```

### Before Releases
```bash
# Clean everything
python cleanup.py --all --clean --force

# Delete entire output (regenerate later)
rm -rf output/

# Update inventory
python update_inventory.py

# Commit clean state
git add -A
git commit -m "chore: Cleanup before release"
```

---

## .gitignore Protection

The `.gitignore` file prevents these from being committed:

```gitignore
# Experiments (entire directory)
experiments/

# Root test files
/test_*.py
/test_*.log
/test_*.html

# Temporary files
temp_*
tmp_*
*_temp.*
*_tmp.*

# Generated outputs
output/

# Cleanup backups
cleanup_backup_*.txt
```

**Result**: Experiments and temporary files never get committed.

---

## Safety Features

### 1. Backup Lists
Every cleanup creates a backup list:
```
cleanup_backup_20251214_093045.txt
```

Contains: All files and directories that were removed.

### 2. Confirmation
By default, cleanup asks for confirmation:
```
[WARNING] About to remove 41 files and 18 directories
          Total size: 2.5 MB

Proceed? (yes/no):
```

Use `--force` to skip.

### 3. Protected Files
These are NEVER cleaned:
- `test_laxity_accuracy.py` (production script)
- `complete_pipeline_with_validation.py`
- `scripts/test_*.py` (unit tests)
- `validation/` (historical data)

### 4. Scan Mode
Default mode is `--scan` (safe, no changes):
```bash
python cleanup.py  # Same as --scan
```

---

## Integration with Git

### Pre-Commit Hook (Optional)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Warn about large experiments before commit

python cleanup.py --experiments --scan | grep "Total size"
```

### CI/CD Integration

Add to `.github/workflows/`:

```yaml
- name: Check for cleanup candidates
  run: |
    python cleanup.py --scan
    # Fail if > 100 MB
```

---

## Common Scenarios

### "I have a large experiment I need to keep"

Move to ARCHIVE:
```bash
mkdir -p experiments/ARCHIVE/my_experiment
cp experiments/my_experiment/README.md \
   experiments/ARCHIVE/my_experiment/FINDINGS.md
```

### "I accidentally deleted something"

Check backup list:
```bash
cat cleanup_backup_*.txt
```

Restore from git (if committed):
```bash
git checkout HEAD -- path/to/file
```

### "Output folder is 500 MB"

Safe to delete entirely:
```bash
rm -rf output/
# Regenerate if needed
python complete_pipeline_with_validation.py
```

### "I want to keep some test files"

Add to `KEEP_FILES` in `cleanup.py`:
```python
KEEP_FILES = [
    'test_laxity_accuracy.py',
    'test_my_special_test.py',  # Add here
]
```

---

## Cleanup System Files

```
cleanup.py                    # Main cleanup tool
new_experiment.py             # Experiment template creator
experiments/README.md         # Experiment system guide
docs/CLEANUP_GUIDE.md         # Detailed cleanup guide
CLEANUP_SYSTEM.md (this file) # Quick reference
.gitignore                    # Updated with cleanup patterns
```

---

## Summary

The cleanup system provides:

✅ **Automated detection** of experimental/temporary files
✅ **Dedicated experiments/** directory for temporary work
✅ **Self-cleaning experiments** with built-in cleanup scripts
✅ **Safety features** (confirmation, backups, protected files)
✅ **Clear organization** (production vs experiments)
✅ **Simple workflow** (create → develop → cleanup)

**Goal**: Keep the project clean and organized by making cleanup automatic and easy.

---

## Quick Commands

```bash
# Most common cleanup
python cleanup.py --clean

# Create new experiment
python new_experiment.py "my_experiment"

# Clean experiments
python cleanup.py --experiments --clean

# Nuclear option (delete all generated files)
python cleanup.py --all --clean --force
rm -rf output/
```

---

For detailed information, see:
- **Usage guide**: `docs/CLEANUP_GUIDE.md`
- **Experiment guide**: `experiments/README.md`
- **Tool source**: `cleanup.py`
