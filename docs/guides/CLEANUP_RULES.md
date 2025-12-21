# Cleanup Script Rules and Guidelines

**Last Updated**: 2025-12-21
**Version**: 1.0
**Script**: `cleanup.py`

---

## Overview

The cleanup script (`cleanup.py`) automatically identifies and removes temporary, experimental, and test files from the repository. This document defines the rules that govern what gets cleaned and what gets preserved.

---

## Critical Rule: Git-Tracked Files

### RULE 1: NEVER Clean Git-Tracked Files

**Implementation**: Added 2025-12-21 after v2.4.0 cleanup incident

```python
def is_git_tracked(self, path):
    """Check if a file is tracked by git"""
    # Uses: git ls-files --error-unmatch <path>
    # Returns: True if file is tracked, False otherwise
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

---

## Explicit Keep Lists

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

---

## Cleanup Patterns

### Files That Get Cleaned (If Not Git-Tracked)

**Test Files**:
```python
test_*.py       # Temporary test scripts
test_*.log      # Test logs
test_*.sf2      # Test SF2 files
test_*.sid      # Test SID files
test_*.wav      # Test audio files
test_*.dump     # Test register dumps
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

### Output Directories That Get Cleaned

```python
output/test_*           # Test output directories
output/Test_*           # Test output (capitalized)
output/midi_comparison  # MIDI comparison temp dir
output/Laxity_Test     # Laxity test dir
```

---

## Misplaced Documentation

The cleanup script can move (not delete) misplaced documentation files from root to `docs/`:

### Standard Root Documentation (Always Stay in Root)

```python
README.md           # Main project docs
CONTRIBUTING.md     # Contribution guidelines
CHANGELOG.md        # Version history
CLAUDE.md           # AI assistant quick reference
```

### Misplaced Documentation Mapping (Root → docs/)

```python
*_ANALYSIS.md       → docs/analysis/
*_RESEARCH*.md      → docs/analysis/
*_REPORT.md         → docs/reference/
*_IMPLEMENTATION.md → docs/implementation/
*_STATUS.md         → docs/analysis/
*_NOTES.md          → docs/guides/
*_CONSOLIDATION*.md → docs/archive/
CONSOLIDATION_*.md  → docs/archive/
*_SYSTEM.md         → docs/guides/
VALIDATION_*.md     → docs/guides/
```

**Note**: These patterns only apply to files NOT tracked by git. If a file matches these patterns but is already committed, it stays in place (RULE 1).

---

## Usage

### Scan Only (Recommended First Step)

```bash
python cleanup.py --scan
```

Shows what would be cleaned without actually deleting anything.

### Clean with Confirmation

```bash
python cleanup.py --clean
```

Prompts for confirmation before deleting files.

### Clean with Force (No Confirmation)

```bash
python cleanup.py --clean --force
```

Deletes files immediately without confirmation.

### Clean with Inventory Update

```bash
python cleanup.py --clean --update-inventory
```

Cleans files and automatically updates `docs/FILE_INVENTORY.md`.

### Clean Output Directory Only

```bash
python cleanup.py --output-only --clean
```

Only cleans test directories in `output/`.

---

## Safety Features

### 1. Backup List

Every cleanup creates a backup list file:

```
cleanup_backup_YYYYMMDD_HHMMSS.txt
```

This file contains paths of all deleted files/directories for recovery if needed.

### 2. Git-Aware Protection

The script checks `git ls-files` to ensure committed files are never deleted.

### 3. Explicit Keep Lists

Important files are explicitly listed in `KEEP_FILES` for double protection.

### 4. Dry-Run Mode

The `--scan` flag allows you to preview what would be cleaned before actually deleting.

---

## Best Practices

### 1. Always Scan First

```bash
# GOOD: Scan first, then clean
python cleanup.py --scan
python cleanup.py --clean --update-inventory

# BAD: Clean immediately without review
python cleanup.py --clean --force
```

### 2. Update Inventory After Cleanup

```bash
python cleanup.py --clean --update-inventory
```

This keeps `docs/FILE_INVENTORY.md` synchronized with repository state.

### 3. Commit Important Documentation

If you create documentation that should be preserved:

```bash
# Add to git BEFORE running cleanup
git add important_documentation.md
git commit -m "docs: Add important documentation"

# Now safe from cleanup (RULE 1 protection)
python cleanup.py --clean
```

### 4. Review Backup Lists

After cleanup, review the backup list to ensure nothing important was deleted:

```bash
cat cleanup_backup_20251221_092113.txt
```

### 5. Regular Cleanup Schedule

**Daily** (if active development):
```bash
python cleanup.py --scan
```

**Weekly**:
```bash
python cleanup.py --clean --update-inventory
```

**Before Releases**:
```bash
python cleanup.py --all --clean --force --update-inventory
git add -A
git commit -m "chore: Cleanup before release"
```

---

## Incident Report: v2.4.0 Cleanup

### What Happened (2025-12-21)

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

### Fix Implemented

Added RULE 1: Git-tracking check to `should_keep()` method:

```python
def should_keep(self, path):
    # RULE 1: NEVER clean files tracked by git
    if self.is_git_tracked(path):
        return True
    # ... other rules
```

### Recovery

Files were restored using:

```bash
git restore CONSOLIDATION_2025-12-21_COMPLETE.md
git restore SF2_VIEWER_FEATURE_PARITY_PLAN.md
git restore SF2_VIEWER_V2.4_COMPLETE.md
git restore TRACK_VIEW_TEST_RESULTS.md
git restore test_track_view_parity.py
```

### Lesson Learned

**Always check git tracking before cleanup operations.**

This is now enforced by RULE 1 in the cleanup script.

---

## Testing the Protection

### Verify Git-Tracked Files Are Protected

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

## Future Improvements

### Potential Enhancements

1. **Interactive Mode**: Allow user to select which files to clean
2. **Smart Archive**: Move session docs to `docs/archive/` instead of deleting
3. **Age-Based Cleanup**: Delete files older than X days
4. **Size-Based Cleanup**: Target large temporary files first
5. **Whitelist Patterns**: Allow user to specify patterns to always keep

---

## Related Documentation

- **cleanup.py**: The cleanup script itself
- **docs/FILE_INVENTORY.md**: Current repository structure
- **docs/guides/CLEANUP_SYSTEM.md**: Complete cleanup system guide

---

**🤖 Generated with [Claude Code](https://claude.com/claude-code)**

**Version**: 1.0
**Date**: 2025-12-21
**Status**: Production Ready
