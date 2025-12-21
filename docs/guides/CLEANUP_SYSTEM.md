# SIDM2 Cleanup System - Complete Guide

**Version**: 2.3
**Date**: 2025-12-21

---

## Quick Summary

This project now has a comprehensive cleanup system with:

✅ **Automated cleanup tool** (`cleanup.py`)
✅ **Git-aware protection** (never deletes committed files)
✅ **Dedicated experiments directory** (`experiments/`)
✅ **Experiment template system** (`new_experiment.py`)
✅ **Updated .gitignore** (prevents committing experiments)
✅ **Self-cleaning experiments** (each has cleanup script)
✅ **Misplaced documentation detection** (auto-organizes MD files)
✅ **Automatic inventory updates** (keeps FILE_INVENTORY.md current)
✅ **Safety features** (backup lists, confirmation, protected files)

---

## Table of Contents

1. [Can I Delete the Output Folder?](#can-i-delete-the-output-folder)
2. [Cleanup Tools Usage](#cleanup-tools-usage)
3. [Critical Protection Rules](#critical-protection-rules)
4. [Documentation Organization](#documentation-organization)
5. [File Inventory Management](#file-inventory-management)
6. [Experiment Workflow](#experiment-workflow)
7. [File Organization](#file-organization)
8. [Cleanup Schedule](#cleanup-schedule)
9. [.gitignore Protection](#gitignore-protection)
10. [Safety Features](#safety-features)
11. [Integration with Git](#integration-with-git)
12. [Common Scenarios](#common-scenarios)
13. [Incident Report & Lessons Learned](#incident-report--lessons-learned)
14. [Emergency Cleanup & Recovery](#emergency-cleanup--recovery)
15. [Quick Reference](#quick-reference)

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

# Clean and auto-update FILE_INVENTORY.md (recommended)
python cleanup.py --clean --update-inventory

# Clean only output directory
python cleanup.py --output-only --clean

# Clean only experiments
python cleanup.py --experiments --clean

# Clean everything (root + output + experiments)
python cleanup.py --all --clean

# Force mode (no confirmation) with inventory update
python cleanup.py --clean --force --update-inventory
```

**New in v2.2**: The `--update-inventory` flag automatically updates `FILE_INVENTORY.md` after successful cleanup, keeping it in sync with the repository state.

**New in v2.3**: Git-aware protection prevents deletion of committed files.

### Current Cleanup Results

Based on latest scan (2025-12-21):

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

## Critical Protection Rules

### RULE 1: NEVER Clean Git-Tracked Files

**Implementation**: Added 2025-12-21 after v2.4.0 cleanup incident

```python
def should_keep(self, path):
    """Check if a file should be preserved"""
    # RULE 1: NEVER clean files tracked by git
    if self.is_git_tracked(path):
        return True
    # ... other rules
```

**Purpose**: Prevent cleanup script from deleting committed documentation files.

**How It Works**:
1. Before cleaning any file, check if it's tracked by git
2. If `git ls-files --error-unmatch <file>` returns 0 (success), file is tracked
3. Tracked files are ALWAYS preserved, regardless of naming patterns

**Example**:
```bash
# These files are tracked by git, so they're preserved:
CONSOLIDATION_2025-12-21_COMPLETE.md    ✓ Preserved (git tracked)
SF2_VIEWER_FEATURE_PARITY_PLAN.md       ✓ Preserved (git tracked)
SF2_VIEWER_V2.4_COMPLETE.md             ✓ Preserved (git tracked)
TRACK_VIEW_TEST_RESULTS.md              ✓ Preserved (git tracked)
test_track_view_parity.py               ✓ Preserved (git tracked)

# These files are NOT tracked, so they're cleaned:
SF2_EDITOR_BUILD_SUMMARY.md             ✗ Cleaned (not tracked)
CONTEXT.md                              ✗ Cleaned (not tracked)
test_all_sequences.py                   ✗ Cleaned (not tracked)
```

### RULE 2: Explicit Keep Files

Files in `KEEP_FILES` list are always preserved:

```python
KEEP_FILES = [
    'test_laxity_accuracy.py',              # Production validation
    'complete_pipeline_with_validation.py',
    'SIDwinder.log',                        # Main log
    # v2.4.0 Documentation (committed)
    'SF2_VIEWER_FEATURE_PARITY_PLAN.md',
    'SF2_VIEWER_V2.4_COMPLETE.md',
    'TRACK_VIEW_TEST_RESULTS.md',
    'CONSOLIDATION_2025-12-21_COMPLETE.md',
    'test_track_view_parity.py',
]
```

**Note**: This list is now redundant due to RULE 1 (git tracking), but serves as explicit documentation of important files.

### RULE 3: Keep Directories

Directories in `KEEP_DIRS` list are always preserved:

```python
KEEP_DIRS = [
    'output/SIDSF2player_Complete_Pipeline',  # Main pipeline output
    'validation',                             # Validation system data
    'scripts/test_*.py',                      # Unit tests
]
```

### What Gets Cleaned (If Not Git-Tracked)

**Test Files**:
```python
test_*.py       # Temporary test scripts (root only)
test_*.log      # Test logs
test_*.sf2      # Test SF2 files
test_*.sid      # Test SID files
test_*.wav      # Test audio files
test_*.dump     # Test register dumps
test_*.html     # Test HTML reports
```

**Temporary Files**:
```python
temp_*          # Temporary files
tmp_*           # Temp files
*.tmp           # Temp extension
*.temp          # Temp extension
*_temp.*        # Temp suffix
*_tmp.*         # Tmp suffix
```

**Backup Files**:
```python
*_backup.*      # Backup suffix
*_old.*         # Old suffix
*.bak           # Backup extension
*.backup        # Backup extension
```

**Experiment Files**:
```python
experiment_*    # Experiment prefix
debug_*         # Debug prefix
scratch_*       # Scratch prefix
```

**Log Files**:
```python
*.log           # Log files (except SIDwinder.log)
pipeline_*.log  # Pipeline logs
```

**Validation HTML**:
```python
validation_test_*.html  # Temporary validation reports
```

### Output Directories That Get Cleaned

```python
output/test_*           # Test output directories
output/Test_*           # Test output (capitalized)
output/midi_comparison  # MIDI comparison temp dir
output/Laxity_Test      # Laxity test dir
```

### Testing Git Protection

```bash
# Create test file
echo "test" > test_file.txt

# Run cleanup scan
python cleanup.py --scan
# Result: test_file.txt appears in cleanup list

# Add to git
git add test_file.txt
git commit -m "test: Add test file"

# Run cleanup scan again
python cleanup.py --scan
# Result: test_file.txt NOT in cleanup list (protected by RULE 1)
```

---

## Documentation Organization

### Automatic Misplaced Documentation Detection (NEW in v2.1)

The cleanup system automatically detects documentation files that are in the wrong location and suggests where they should go.

**Standard Root Documentation** (always kept in root):
- `README.md` - Main project documentation
- `CONTRIBUTING.md` - Contribution guidelines
- `CHANGELOG.md` - Version history
- `CLAUDE.md` - AI assistant quick reference

**All other .md files in root are considered misplaced** and will be detected during cleanup.

### How It Works

```bash
# Default scan includes misplaced docs check
python cleanup.py --scan

# Output shows misplaced files with suggested locations
[4/4] Scanning for misplaced documentation...

[FILES TO CLEAN]
  Misplaced Doc -> Docs/Analysis/ (3 files):
    - LAXITY_ACCURACY_ANALYSIS.md (45.2 KB)
    - LAXITY_DRIVER_RESEARCH_SUMMARY.md (23.1 KB)
    - SF2_VALIDATION_STATUS.md (12.8 KB)

  Misplaced Doc -> Docs/Implementation/ (1 files):
    - RUNTIME_TABLE_BUILDING_IMPLEMENTATION.md (18.4 KB)
```

### Documentation Mapping Rules

The cleanup system uses pattern matching to suggest appropriate locations:

| File Pattern | Suggested Location | Example |
|--------------|-------------------|---------|
| `*_ANALYSIS.md` | `docs/analysis/` | `LAXITY_ACCURACY_ANALYSIS.md` |
| `*_RESEARCH*.md` | `docs/analysis/` | `LAXITY_DRIVER_RESEARCH_SUMMARY.md` |
| `*_REPORT.md` | `docs/reference/` | `LAXITY_NP20_RESEARCH_REPORT.md` |
| `*_IMPLEMENTATION.md` | `docs/implementation/` | `RUNTIME_TABLE_BUILDING_IMPLEMENTATION.md` |
| `STATUS.md` | `docs/` | `STATUS.md` |
| `*_STATUS.md` | `docs/analysis/` | `SF2_VALIDATION_STATUS.md` |
| `*_NOTES.md` | `docs/guides/` | `VALIDATION_SYSTEM_NOTES.md` |
| `*_CONSOLIDATION*.md` | `docs/archive/` | `KNOWLEDGE_CONSOLIDATION.md` |
| `CONSOLIDATION_*.md` | `docs/archive/` | `CONSOLIDATION_2025-12-21_COMPLETE.md` |
| `*_SYSTEM.md` | `docs/guides/` | `CLEANUP_SYSTEM.md` |
| `VALIDATION_*.md` | `docs/guides/` | `VALIDATION_GUIDE.md` |
| `external-repositories.md` | `docs/reference/` | `external-repositories.md` |
| `sourcerepository.md` | `docs/reference/` | `sourcerepository.md` |

**Note**: These patterns only apply to files NOT tracked by git. If a file matches these patterns but is already committed, it stays in place (RULE 1).

### Manual Documentation Organization

To organize misplaced docs manually:

```bash
# Move using git to preserve history
git mv ROOT_FILE.md docs/appropriate_location/ROOT_FILE.md

# Example
git mv LAXITY_ACCURACY_ANALYSIS.md docs/analysis/LAXITY_ACCURACY_ANALYSIS.md
```

### Benefits

✅ **Keeps root directory clean** - Only 4 standard MD files in root
✅ **Organized documentation** - Files automatically categorized
✅ **Prevents clutter** - Detects misplaced docs during regular cleanup scans
✅ **Git history preserved** - Uses `git mv` when cleanup tool moves files
✅ **Clear categories** - Analysis, implementation, guides, reference, archive

---

## File Inventory Management

### Automatic Inventory Updates (NEW in v2.2)

The cleanup system can automatically update `FILE_INVENTORY.md` after cleanup operations to keep it in sync with the repository state.

**How It Works**:

```bash
# Clean with automatic inventory update
python cleanup.py --clean --update-inventory

# Output shows:
# [COMPLETE] Cleanup finished! 15 files and 5 directories removed.
#            Backup list: cleanup_backup_20251221_120500.txt
#
# [INVENTORY] Updating FILE_INVENTORY.md...
# [INVENTORY] Updated successfully
#             [OK] Updated FILE_INVENTORY.md
#             Files in root: 20
#             Subdirectories: 16
```

### When to Update Inventory

**Automatically** (recommended):
- After cleanup operations: `--clean --update-inventory`
- Before releases: `--all --clean --force --update-inventory`

**Manually**:
```bash
# Update inventory manually anytime
python pyscript/update_inventory.py
```

### What's Tracked

`FILE_INVENTORY.md` contains:
- ✅ **Complete file tree** - All files and directories
- ✅ **File sizes** - Human-readable format (B, KB, MB)
- ✅ **Category summaries** - Purpose of each directory
- ✅ **Management rules** - Quick reference for organization
- ✅ **Last updated timestamp** - When inventory was generated

### Benefits

✅ **Always current** - Inventory stays in sync with repository
✅ **Easy tracking** - See what changed after cleanup
✅ **Git-friendly** - Track file organization changes
✅ **Automated** - No manual maintenance needed

### Integration with Cleanup Schedule

```bash
# Daily cleanup (with inventory)
python cleanup.py --clean --update-inventory

# Weekly full cleanup (with inventory)
python cleanup.py --all --clean --update-inventory

# Before releases (forced, with inventory)
python cleanup.py --all --clean --force --update-inventory
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
| Documentation | Root | Standard only | `README.md`, `CLAUDE.md` | ✅ YES |
| Documentation | `docs/` | Any | `ARCHITECTURE.md` | ✅ YES |
| Misplaced Docs | Root | Analysis/Status/etc | `*_ANALYSIS.md` | ⚠️ Move to docs/ |
| Test Files | Root | `test_` | `test_debug.py` | ❌ Clean |
| Temp Files | Root | `temp_`, `tmp_` | `temp_output.wav` | ❌ Clean |
| Logs | Root | `*.log` | `pipeline.log` | ❌ Clean |

---

## Cleanup Schedule

### Daily (If Active Development)
```bash
# Quick scan
python cleanup.py --scan

# Clean if > 10 MB (with inventory update)
python cleanup.py --clean --update-inventory
```

### Weekly
```bash
# Full scan
python cleanup.py --all --scan

# Clean experiments (with inventory)
python cleanup.py --experiments --clean --update-inventory

# Clean output tests (with inventory)
python cleanup.py --output-only --clean --update-inventory
```

### Monthly
```bash
# Full cleanup (with inventory)
python cleanup.py --all --clean --update-inventory

# Review output directory size
du -sh output/* | sort -h
```

### Before Releases
```bash
# Clean everything (forced, with inventory)
python cleanup.py --all --clean --force --update-inventory

# Delete entire output (regenerate later)
rm -rf output/

# Commit clean state (inventory already updated)
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
*_backup.*
*_old.*
*.tmp
*.temp
*.bak
*.backup

# Experiment files
experiment_*
debug_*
scratch_*

# Generated outputs
output/

# Cleanup backups
cleanup_backup_*.txt

# Logs (except main log)
*.log
!SIDwinder.log

# Validation HTML (generated)
validation_test_*.html

# Python cache
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
```

**Result**: Experiments and temporary files never get committed.

---

## Safety Features

### 1. Backup Lists
Every cleanup creates a backup list:
```
cleanup_backup_20251221_093045.txt
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
- **Git-tracked files** (RULE 1 - automatic)
- `test_laxity_accuracy.py` (production script)
- `complete_pipeline_with_validation.py`
- `scripts/test_*.py` (unit tests)
- `validation/` (historical data)
- `SIDwinder.log` (main log)

### 4. Scan Mode
Default mode is `--scan` (safe, no changes):
```bash
python cleanup.py  # Same as --scan
```

### 5. Git-Aware Protection (NEW in v2.3)
Automatically checks if files are tracked by git before cleaning:
```python
def is_git_tracked(self, path):
    """Check if a file is tracked by git"""
    result = subprocess.run(
        ['git', 'ls-files', '--error-unmatch', path],
        capture_output=True
    )
    return result.returncode == 0  # 0 = tracked
```

---

## Integration with Git

### Pre-Commit Hook (Optional)

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
    echo "Run: python cleanup.py --clean --update-inventory"
    echo ""
fi
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
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

### "I need to keep a directory"

Add to `KEEP_DIRS` in `cleanup.py`:
```python
KEEP_DIRS = [
    'output/SIDSF2player_Complete_Pipeline',
    'output/my_special_tests',  # Add here
]
```

---

## Incident Report & Lessons Learned

### v2.4.0 Cleanup Incident (2025-12-21)

#### What Happened

The cleanup script deleted 5 committed documentation files during v2.4.0 cleanup:

```
DELETED BY MISTAKE:
- CONSOLIDATION_2025-12-21_COMPLETE.md
- SF2_VIEWER_FEATURE_PARITY_PLAN.md
- SF2_VIEWER_V2.4_COMPLETE.md
- TRACK_VIEW_TEST_RESULTS.md
- test_track_view_parity.py
```

**Root Cause**: Cleanup script didn't check if files were tracked by git before deleting.

#### Fix Implemented

Added RULE 1: Git-tracking check to `should_keep()` method:

```python
def should_keep(self, path):
    # RULE 1: NEVER clean files tracked by git
    if self.is_git_tracked(path):
        return True
    # ... other rules
```

#### Recovery

Files were restored using:

```bash
git restore CONSOLIDATION_2025-12-21_COMPLETE.md
git restore SF2_VIEWER_FEATURE_PARITY_PLAN.md
git restore SF2_VIEWER_V2.4_COMPLETE.md
git restore TRACK_VIEW_TEST_RESULTS.md
git restore test_track_view_parity.py
```

#### Lesson Learned

**Always check git tracking before cleanup operations.**

This is now enforced by RULE 1 in the cleanup script (v2.3+).

---

## Emergency Cleanup & Recovery

### If You Accidentally Deleted Something Important

**Step 1: Check backup list**:
```bash
cat cleanup_backup_*.txt
```

The backup list shows everything that was deleted with full paths.

**Step 2: Restore from git** (if committed):
```bash
# Restore single file
git checkout HEAD -- path/to/file

# Restore all deleted files from last commit
git checkout HEAD -- .
```

**Step 3: Restore from pipeline** (if it's output):
```bash
# Regenerate pipeline outputs
python complete_pipeline_with_validation.py
```

**Step 4: Check git history** (if you need older version):
```bash
# Find when file was deleted
git log --all --full-history -- path/to/file

# Restore from specific commit
git checkout <commit-hash> -- path/to/file
```

### If Cleanup Removed Too Much

**Review what was deleted**:
```bash
cat cleanup_backup_YYYYMMDD_HHMMSS.txt
```

**Restore selectively**:
```bash
# For each important file in backup list
git checkout HEAD -- path/to/important/file
```

### If You Need to Prevent Future Deletions

**Commit important files**:
```bash
# Add to git BEFORE running cleanup
git add important_documentation.md
git commit -m "docs: Add important documentation"

# Now protected by RULE 1 (git tracking)
python cleanup.py --clean
```

**Or add to keep list** (if you don't want to commit):
```python
# Edit cleanup.py
KEEP_FILES = [
    'test_laxity_accuracy.py',
    'my_important_file.py',  # Add here
]
```

---

## Quick Reference

### Most Common Commands

```bash
# 1. Scan before cleanup (recommended first step)
python cleanup.py --scan

# 2. Clean with inventory update (recommended)
python cleanup.py --clean --update-inventory

# 3. Create new experiment
python new_experiment.py "my_experiment"

# 4. Clean experiments (with inventory)
python cleanup.py --experiments --clean --update-inventory

# 5. Nuclear option (delete all generated files, update inventory)
python cleanup.py --all --clean --force --update-inventory
rm -rf output/

# 6. Update inventory manually
python pyscript/update_inventory.py
```

### Protection Checklist

Before cleanup, ensure:
- ✅ Important files are committed (git-tracked)
- ✅ Experiments you want to keep are moved to experiments/ARCHIVE/
- ✅ You've reviewed scan output (`--scan`)
- ✅ Backup list will be created (automatic)

### When to Use Which Flag

| Scenario | Command |
|----------|---------|
| Daily maintenance | `--clean --update-inventory` |
| Output cleanup | `--output-only --clean --update-inventory` |
| Experiment cleanup | `--experiments --clean --update-inventory` |
| Full cleanup | `--all --clean --update-inventory` |
| Before release | `--all --clean --force --update-inventory` |
| Just preview | `--scan` |

### File Organization Best Practices

1. **Production code** → `scripts/` or `sidm2/`
2. **Unit tests** → `scripts/test_*.py`
3. **Experiments** → `experiments/` (temporary)
4. **Documentation** → `docs/` (categorized)
5. **Generated outputs** → `output/` (deletable)
6. **Validation data** → `validation/` (keep for history)

---

## Cleanup System Files

```
cleanup.py                    # Main cleanup tool (with git protection)
new_experiment.py             # Experiment template creator
pyscript/update_inventory.py # File inventory updater
experiments/README.md         # Experiment system guide
docs/guides/CLEANUP_SYSTEM.md # Complete guide (this file)
.gitignore                    # Updated with cleanup patterns
```

---

## Summary

The cleanup system provides:

✅ **Automated detection** of experimental/temporary files
✅ **Git-aware protection** (never deletes committed files - v2.3)
✅ **Documentation organization** (auto-detects misplaced MD files)
✅ **File inventory management** (auto-updates FILE_INVENTORY.md)
✅ **Dedicated experiments/** directory for temporary work
✅ **Self-cleaning experiments** with built-in cleanup scripts
✅ **Safety features** (confirmation, backups, protected files)
✅ **Clear organization** (production vs experiments vs docs)
✅ **Simple workflow** (create → develop → cleanup → track)
✅ **Emergency recovery** (backup lists, git restore)

**Goal**: Keep the project clean and organized by making cleanup automatic, safe, and easy.

---

For detailed information, see:
- **Tool source**: `cleanup.py`
- **Experiment guide**: `experiments/README.md`
- **File inventory**: `docs/FILE_INVENTORY.md`

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

**Version**: 2.3
**Last Updated**: 2025-12-21
**Status**: Production Ready
