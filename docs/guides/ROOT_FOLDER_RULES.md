# Root Folder Management Rules

**Version**: 2.0
**Date**: 2025-12-21
**Status**: Production Rule
**Changes**: v2.0 - Added pyscript/ directory for ALL Python scripts

---

## Core Rule: Keep Root Folder Clean

### RULE: Main folder should be kept clean

**Purpose**: Maintain a clean, organized repository structure where the root directory only contains essential files and launchers.

**Enforcement**: Automated cleanup script with git-tracking protection

---

## What Belongs in Root

### ✅ ALLOWED in Root Directory

**1. Essential Configuration Files**:
```
.gitignore              - Git ignore rules
.gitattributes          - Git attributes
pytest.ini              - Test configuration
requirements.txt        - Python dependencies
requirements-test.txt   - Test dependencies
sidm2_config.example.json - Example configuration
SIDwinder.cfg           - SIDwinder configuration
```

**2. Standard Documentation Files**:
```
README.md               - Main project documentation
CONTRIBUTING.md         - Contribution guidelines
CHANGELOG.md            - Version history
CLAUDE.md               - AI assistant quick reference
LICENSE                 - Project license (if exists)
```

**3. Committed Documentation** (git-tracked):
```
CONSOLIDATION_2025-12-21_COMPLETE.md  - v2.4.0 consolidation
SF2_VIEWER_FEATURE_PARITY_PLAN.md     - v2.4.0 planning
SF2_VIEWER_V2.4_COMPLETE.md           - v2.4.0 summary
TRACK_VIEW_TEST_RESULTS.md            - v2.4.0 testing
```

**4. Batch Launchers** (.bat files):
```
sf2-viewer.bat          - SF2 Viewer launcher
sf2-export.bat          - SF2 Text Exporter launcher
sid-to-sf2.bat          - SID to SF2 converter
sf2-to-sid.bat          - SF2 to SID converter
pipeline.bat            - Pipeline launcher
cleanup.bat             - Cleanup launcher
batch-convert.bat       - Batch converter
batch-convert-laxity.bat - Laxity batch converter
test-converter.bat      - Test runner
test-roundtrip.bat      - Roundtrip tester
validate-accuracy.bat   - Accuracy validator
update-inventory.bat    - Inventory updater
TOOLS.bat               - Interactive menu launcher
```

**5. Reference Files**:
```
TOOLS_REFERENCE.txt     - Complete tools reference
```

**Note**: All Python scripts (.py files) should be in the `pyscript/` directory. The root directory should ONLY contain .bat launcher files and documentation.

---

## What Does NOT Belong in Root

### ❌ FORBIDDEN in Root Directory

**1. Python Scripts** (NEW RULE - v2.5):
```
❌ ANY .py file          - ALL Python scripts must be in pyscript/ directory
```

**Enforcement**: Batch launchers reference `pyscript/` for all Python scripts.

**2. Experiments & Tests**:
```
❌ experiment_*.py      - Use experiments/ directory instead
❌ test_*.py            - Use pyscript/ directory (if production) or experiments/
❌ debug_*.py           - Use experiments/ directory
❌ scratch_*.py         - Use experiments/ directory
❌ temp_*.py            - Use experiments/ directory
```

**3. Temporary Files**:
```
❌ *.tmp                - Temporary files
❌ *.temp               - Temporary files
❌ *_temp.*             - Temporary files
❌ *_tmp.*              - Temporary files
```

**4. Session Documentation**:
```
❌ *_ANALYSIS.md        - Should be in docs/analysis/
❌ *_IMPLEMENTATION.md  - Should be in docs/implementation/
❌ *_STATUS.md          - Should be in docs/analysis/
❌ *_NOTES.md           - Should be in docs/guides/
```

**Exception**: Committed documentation files (tracked by git) are allowed.

**5. Backup Files**:
```
❌ *_backup.*           - Backup files
❌ *_old.*              - Old files
❌ *.bak                - Backup files
```

**6. Output Files**:
```
❌ *.sf2                - Should be in output/ or learnings/
❌ *.sid                - Should be in SID/ or output/
❌ *.dump               - Should be in output/
❌ *.wav                - Should be in output/
❌ *.hex                - Should be in output/
```

**7. Log Files**:
```
❌ *.log                - Log files
❌ pipeline_*.log       - Pipeline logs
```

**Exception**: `SIDwinder.log` is allowed (kept for debugging).

---

## Directory Structure

### Proper Organization

```
SIDM2/
├── Root/                           # Clean, essential files only
│   ├── *.bat                       # Batch launchers (ONLY .bat files)
│   ├── *.md (standard)             # README, CLAUDE, CONTRIBUTING, CHANGELOG
│   ├── *.md (committed)            # Git-tracked documentation
│   └── config files                # .gitignore, pytest.ini, etc.
│
├── pyscript/                       # ALL Python scripts (NEW - v2.5)
│   ├── sf2_viewer_gui.py           # SF2 Viewer GUI
│   ├── sf2_to_text_exporter.py     # SF2 Text Exporter
│   ├── cleanup.py                  # Cleanup tool
│   ├── update_inventory.py         # Inventory updater
│   ├── complete_pipeline_with_validation.py  # Pipeline
│   └── *.py                        # All other Python scripts
│
├── experiments/                    # ALL experiments go here
│   ├── my_experiment/
│   │   ├── experiment.py
│   │   ├── README.md
│   │   ├── output/
│   │   └── cleanup scripts
│   └── ARCHIVE/                    # Valuable findings
│
├── scripts/                        # Production conversion scripts
│   ├── sid_to_sf2.py
│   ├── convert_all.py
│   ├── test_*.py                   # Test scripts
│   └── validate_*.py               # Validation scripts
│
├── docs/                           # All documentation
│   ├── guides/
│   ├── analysis/
│   ├── implementation/
│   └── reference/
│
├── output/                         # All output files
│   └── {SongName}/
│       ├── Original/
│       └── New/
│
└── SID/                            # Input SID files
```

---

## Experiment Workflow (REQUIRED)

### How to Run Experiments Properly

**1. Create Experiment Structure**:
```bash
python new_experiment.py "my_experiment"
```

**2. Work in Experiment Directory**:
```bash
cd experiments/my_experiment
python experiment.py
```

**3. Clean Up After Completion**:
```bash
# If experiment failed or not needed:
cd experiments/my_experiment
cleanup.bat   # or cleanup.sh on Unix

# If experiment succeeded:
# - Move useful code to scripts/ or sidm2/
# - Archive findings in experiments/ARCHIVE/
# - Clean up temporary files
```

**4. NEVER Run Experiments in Root**:
```bash
# ❌ WRONG - Creates mess in root
cd SIDM2
python test_my_idea.py

# ✅ CORRECT - Clean organization
python new_experiment.py "test_my_idea"
cd experiments/test_my_idea
python experiment.py
```

---

## Enforcement

### Automated Cleanup

The cleanup script (`cleanup.py`) automatically enforces these rules:

**RULE 1: Git-Tracked Files Protected**:
- ANY file tracked by git is NEVER cleaned
- Committed documentation stays in root
- Core modules stay in root

**RULE 2: Explicit Keep List**:
- Files in `KEEP_FILES` list are preserved
- Essential tools protected

**RULE 3: Pattern-Based Cleanup**:
- `test_*.py` in root → cleaned (unless git-tracked)
- `experiment_*.py` in root → cleaned
- `temp_*`, `tmp_*` → cleaned
- Session documentation → cleaned (unless git-tracked)

### Manual Enforcement

**Before Committing**:
```bash
# 1. Scan for violations
python cleanup.py --scan

# 2. Clean if needed
python cleanup.py --clean

# 3. Update inventory
python update_inventory.py

# 4. Commit
git add -A
git commit -m "chore: Cleanup before commit"
```

**Daily Workflow**:
```bash
# At end of day:
cleanup.bat --scan
cleanup.bat --clean --update-inventory
```

---

## Benefits of Clean Root

### Why Keep Root Clean?

**1. Professional Appearance**:
- Clean repository structure
- Easy to navigate
- Clear organization

**2. Easier Collaboration**:
- Contributors see clear structure
- Less confusion about where files go
- Consistent organization

**3. Better Git History**:
- Fewer unnecessary files in commits
- Clear what's production vs experiment
- Easier to track important changes

**4. Automated Tools Work Better**:
- Cleanup script more effective
- Inventory tracking accurate
- CI/CD pipelines cleaner

**5. Faster Development**:
- Find files quickly
- Less clutter to search through
- Clear separation of concerns

---

## Violations and Fixes

### Common Violations

**Violation 1: Test Files in Root**
```bash
# ❌ WRONG
SIDM2/test_my_feature.py

# ✅ FIX
experiments/test_my_feature/experiment.py
# or
scripts/test_my_feature.py (if production test)
```

**Violation 2: Session Documentation in Root**
```bash
# ❌ WRONG
SIDM2/IMPLEMENTATION_NOTES.md

# ✅ FIX
docs/implementation/IMPLEMENTATION_NOTES.md
```

**Violation 3: Output Files in Root**
```bash
# ❌ WRONG
SIDM2/test_output.sf2
SIDM2/debug.dump

# ✅ FIX
output/test_output/test_output.sf2
experiments/debug/debug.dump
```

**Violation 4: Experiments in Root**
```bash
# ❌ WRONG
cd SIDM2
python experiment.py

# ✅ FIX
python new_experiment.py "my_experiment"
cd experiments/my_experiment
python experiment.py
```

---

## Exception Process

### How to Request Exception

If you believe a file should stay in root:

**1. Check if it's git-tracked**:
```bash
git ls-files --error-unmatch <file>
```
- If tracked, it's already protected (RULE 1)

**2. Check if it's essential**:
- Is it a core module used by multiple scripts?
- Is it a standard documentation file?
- Is it a production tool?

**3. Add to Keep List** (if approved):
```python
# In cleanup.py:
KEEP_FILES = [
    # ... existing files ...
    'your_file.py',  # Reason: essential for X
]
```

**4. Document the Exception**:
- Add comment explaining why
- Update this document
- Update CLAUDE.md if needed

---

## Related Documentation

- **cleanup.py**: The cleanup script
- **docs/guides/CLEANUP_RULES.md**: Detailed cleanup rules
- **docs/guides/CLEANUP_SYSTEM.md**: Complete cleanup guide
- **docs/FILE_INVENTORY.md**: Current repository structure
- **CLAUDE.md**: AI assistant quick reference

---

## Summary

**The Golden Rule**:
> Keep the root directory clean and organized. Experiments go in experiments/, scripts go in scripts/, documentation goes in docs/, and output goes in output/.

**Enforcement**:
- Automated: `cleanup.py` with git-tracking protection
- Manual: Daily cleanup scans
- CI/CD: Validation in GitHub Actions

**Benefits**:
- Professional repository
- Easy navigation
- Better collaboration
- Cleaner git history

---

**🤖 Generated with [Claude Code](https://claude.com/claude-code)**

**Version**: 1.0
**Date**: 2025-12-21
**Status**: Production Rule
