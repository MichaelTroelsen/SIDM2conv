# File Management Rules

## Directory Structure

```
SIDM2/
├── *.py (core/production scripts only)
├── *.md (core documentation only)
├── temp-exp/           # ALL experimental work goes here
│   ├── *.py           # Debug/test scripts
│   ├── *.md           # Analysis/experiment notes
│   └── output/        # Experimental outputs
├── archived/          # Old documentation and deprecated scripts
├── sidm2/            # Core Python package
├── output/           # Production outputs only
├── docs/             # Official documentation
└── tests/            # Production test files
```

## Rules

### 1. Root Directory
**ONLY production files allowed:**
- Main conversion scripts (sid_to_sf2.py, complete_pipeline_with_validation.py, etc.)
- Core documentation (README.md, CLAUDE.md, CONTRIBUTING.md)
- Current status tracking (STINSEN_CONVERSION_STATUS.md, FILE_INVENTORY.md)

### 2. temp-exp/ Directory
**ALL experimental work MUST go here:**
- Debug scripts (analyze_*.py, check_*.py, test_*.py, verify_*.py)
- Exploration scripts (find_*.py, search_*.py, show_*.py)
- Quick fixes (fix_*.py)
- Experiment documentation (*_ANALYSIS.md, *_SUCCESS.md)

**Naming Convention:**
- Debug: `debug_<feature>.py`
- Check: `check_<feature>.py`
- Test: `test_<feature>.py`
- Analysis: `<FEATURE>_ANALYSIS.md`

### 3. archived/ Directory
**For deprecated but potentially useful files:**
- Old versions of scripts
- Completed experiment documentation
- Superseded analysis documents

### 4. File Lifecycle

```
New experiment → temp-exp/ → {Success: promote to root OR Archive: move to archived/}
                           → {Failure: delete or move to archived/}
```

### 5. Promotion to Root
A temp-exp file can be promoted to root if:
- ✅ It's production-ready (no hardcoded paths, proper error handling)
- ✅ It's documented in CLAUDE.md
- ✅ It's tested and working
- ✅ It's part of the main conversion pipeline

### 6. Cleanup Schedule
- **Weekly**: Review temp-exp/ and delete failed experiments
- **Monthly**: Archive old experiments that are no longer relevant
- **After major feature**: Clean up all related experimental files

### 7. FILE_INVENTORY.md
**MUST be updated:**
- When adding a new production script to root
- When promoting from temp-exp to root
- When archiving files
- After cleanup sessions

**Update command:**
```bash
python update_inventory.py
```

## Current File Categories

### Core Production (Root)
- Main conversion scripts
- Pipeline scripts
- Core documentation

### Experimental (temp-exp/)
- All debug/test/analysis scripts
- Experiment documentation

### Archived (archived/)
- Old documentation
- Deprecated scripts

### Package (sidm2/)
- Core Python modules
- Utility functions

### Documentation (docs/)
- Format specifications
- Disassembly analysis
- Conversion strategies

### Tests (tests/)
- Production test files
- Validation scripts
