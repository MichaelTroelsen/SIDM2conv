# SIDM2 Cleanup Guide

**Purpose**: Maintain a clean project structure by managing experimental, temporary, and test files.

---

## Quick Start

```bash
# See what would be cleaned
python cleanup.py --scan

# Clean everything (with confirmation)
python cleanup.py --clean

# Clean without confirmation
python cleanup.py --clean --force

# Clean only output directory
python cleanup.py --output-only --clean
```

---

## What Gets Cleaned

### Automatic Cleanup (cleanup.py)

#### Root Directory Files

**Test Files**:
- `test_*.py` (except `test_laxity_accuracy.py` - production script)
- `test_*.log`
- `test_*.sf2`, `test_*.sid`, `test_*.wav`
- `test_*.dump`, `test_*.html`

**Temporary Files**:
- `temp_*`, `tmp_*`
- `*.tmp`, `*.temp`
- `*_temp.*`, `*_tmp.*`

**Backup Files**:
- `*_backup.*`, `*_old.*`
- `*.bak`, `*.backup`

**Experiment Files**:
- `experiment_*`
- `debug_*`
- `scratch_*`

**Log Files**:
- `*.log` (except `SIDwinder.log`)
- `pipeline_*.log`

**Validation HTML**:
- `validation_test_*.html` (temporary validation reports)

#### Output Directory

**Test Directories**:
- `output/test_*`
- `output/Test_*`
- `output/midi_comparison`
- `output/Laxity_Test`

**Keep**: `output/SIDSF2player_Complete_Pipeline` (main pipeline output)

### What's Protected

**Production Files** (never cleaned):
- `test_laxity_accuracy.py` - Production validation script
- `complete_pipeline_with_validation.py` - Main pipeline
- `SIDwinder.log` - Main log file
- All files in `scripts/test_*.py` - Unit tests
- `output/SIDSF2player_Complete_Pipeline/` - Pipeline results
- `validation/` - Validation system data

---

## Manual Cleanup Checklist

### Before Major Commits

1. **Run cleanup scan**:
   ```bash
   python cleanup.py --scan
   ```

2. **Review the report** - Verify nothing important gets deleted

3. **Clean if safe**:
   ```bash
   python cleanup.py --clean
   ```

4. **Update file inventory**:
   ```bash
   python update_inventory.py
   ```

### Monthly Maintenance

1. **Check for large files**:
   ```bash
   du -sh output/* | sort -h
   ```

2. **Review git status** for uncommitted experiments:
   ```bash
   git status --ignored
   ```

3. **Clean output directory**:
   ```bash
   python cleanup.py --output-only --clean
   ```

---

## File Organization Best Practices

### Where to Put Things

```
SIDM2/
├── scripts/              # Production scripts (committed)
│   ├── sid_to_sf2.py
│   ├── test_*.py        # Unit tests (keep)
│   └── ...
│
├── sidm2/                # Core package (committed)
│
├── experiments/          # Temporary experiments (gitignored)
│   ├── test_*.py        # Quick tests
│   ├── scratch_*.py     # Proof of concepts
│   └── ...
│
├── output/               # Generated outputs (gitignored)
│   ├── SIDSF2player_Complete_Pipeline/  # Keep
│   └── test_*/          # Clean periodically
│
├── validation/           # Validation data (committed)
│   ├── database.sqlite
│   ├── dashboard.html
│   └── SUMMARY.md
│
└── docs/                 # Documentation (committed)
```

### Naming Conventions

**Production files** (keep forever):
- No special prefix
- Documented in README/CLAUDE.md
- Examples: `sid_to_sf2.py`, `complete_pipeline_with_validation.py`

**Unit tests** (keep):
- In `scripts/` directory
- Prefix: `test_`
- Examples: `scripts/test_converter.py`, `scripts/test_sf2_format.py`

**Temporary experiments** (clean regularly):
- Prefix: `test_`, `temp_`, `experiment_`, `debug_`, `scratch_`
- Location: Root or `experiments/` directory
- Examples: `test_wave_fix.py`, `experiment_pointer_scan.py`

**Generated outputs** (clean when done):
- In `output/` directory
- Prefix directories with `test_` or `Test_`
- Examples: `output/test_broware/`, `output/Test_NoSiddump/`

---

## .gitignore Strategy

The `.gitignore` file should exclude:

```gitignore
# Experiments and temporary files
experiments/
test_*.py          # Root test files (not scripts/test_*.py)
temp_*
tmp_*
*_temp.*
*_tmp.*
experiment_*
debug_*
scratch_*

# Generated outputs
output/*/          # All output subdirectories
!output/SIDSF2player_Complete_Pipeline/  # Except pipeline

# Logs (except main log)
*.log
!SIDwinder.log

# Temporary files
*.tmp
*.temp
*.bak
*.backup
*_backup.*
*_old.*

# Validation HTML (generated)
validation_test_*.html

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
```

---

## Cleanup Automation

### Git Pre-Commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Auto-cleanup before commits

echo "Running cleanup scan..."
python cleanup.py --scan

# If there are files to clean, warn
if [ $? -eq 0 ]; then
    echo ""
    echo "⚠️  Cleanup recommended before commit"
    echo "Run: python cleanup.py --clean"
    echo ""
fi
```

### CI/CD Integration

Add to `.github/workflows/validation.yml`:

```yaml
- name: Check for experimental files
  run: |
    python cleanup.py --scan
    # Fail if too many temp files
```

---

## Emergency Cleanup

If you accidentally deleted something important:

1. **Check backup list**:
   ```bash
   cat cleanup_backup_*.txt
   ```

2. **Restore from git** (if committed):
   ```bash
   git checkout HEAD -- path/to/file
   ```

3. **Restore from pipeline** (if it's output):
   ```bash
   python complete_pipeline_with_validation.py
   ```

---

## Cleanup Schedule

### Daily
- Review `git status` for uncommitted experiments
- Move experiments to `experiments/` directory

### Weekly
- Run `python cleanup.py --scan`
- Clean if > 100 MB of temp files

### Monthly
- Run `python cleanup.py --clean`
- Review `output/` directory size
- Update `.gitignore` if new patterns emerge

### Before Releases
- Full cleanup: `python cleanup.py --clean --force`
- Update file inventory: `python update_inventory.py`
- Commit clean state

---

## Common Issues

### "I need to keep a test file"

Add it to `KEEP_FILES` in `cleanup.py`:

```python
KEEP_FILES = [
    'test_laxity_accuracy.py',
    'test_my_important_test.py',  # Add here
]
```

### "Cleanup removed too much"

Check the backup list:
```bash
cat cleanup_backup_YYYYMMDD_HHMMSS.txt
```

### "How do I exclude a directory?"

Add to `KEEP_DIRS` in `cleanup.py`:

```python
KEEP_DIRS = [
    'output/SIDSF2player_Complete_Pipeline',
    'output/my_special_tests',  # Add here
]
```

---

## Integration with Development Workflow

### When Starting New Experiments

1. Create in `experiments/` directory:
   ```bash
   mkdir -p experiments
   vim experiments/test_new_feature.py
   ```

2. Use clear naming: `test_`, `experiment_`, `scratch_`

3. Keep experiments local (gitignored)

### When Experiment Succeeds

1. **Move to proper location**:
   - Production script → `scripts/`
   - Unit test → `scripts/test_*.py`
   - Core module → `sidm2/`

2. **Clean up experiment files**:
   ```bash
   python cleanup.py --clean
   ```

3. **Update documentation**:
   - Add to README.md if user-facing
   - Add to CLAUDE.md if significant

### When Experiment Fails

1. **Document findings** (if valuable):
   ```bash
   echo "Experiment: ... Result: ..." >> docs/EXPERIMENTS_LOG.md
   ```

2. **Delete experiment files**:
   ```bash
   python cleanup.py --clean
   ```

---

## Summary

- **Use `cleanup.py`** for automated cleanup
- **Follow naming conventions** for easy identification
- **Keep experiments in `experiments/`** directory
- **Run cleanup before major commits**
- **Update `.gitignore`** as new patterns emerge
- **Document important findings** before deleting

**Goal**: Maintain a clean, organized project where production code is clearly separated from experiments.
