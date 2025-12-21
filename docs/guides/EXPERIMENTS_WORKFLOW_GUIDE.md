# Experiment Workflow Guide

Complete guide to the experiment system for rapid prototyping and testing.

**Version**: 2.2
**Last Updated**: 2025-12-21

---

## Overview

The experiment system provides a dedicated, organized space for temporary code, prototypes, and proofs of concept. All experimental work is conducted in the `experiments/` directory with automatic cleanup and gitignore protection.

### ⚠️ MANDATORY RULE

**ALL EXPERIMENTAL WORK MUST BE CONDUCTED IN THE `experiments/` FOLDER.**

**DO:**
- ✅ Testing new OCR approaches → `experiments/ocr_testing/`
- ✅ Trying different parsers → `experiments/parser_prototype/`
- ✅ Prototyping new features → `experiments/feature_name/`
- ✅ Debugging theories → `experiments/debug_issue_123/`

**DON'T:**
- ❌ Create test files in the root directory
- ❌ Create experimental scripts in `scripts/` or `sidm2/`
- ❌ Leave temporary files scattered around

**If you're not sure it will work, put it in `experiments/` first!**

---

## Quick Start

### Create New Experiment

```bash
# Basic creation
python pyscript/new_experiment.py "wave_table_analysis"

# With description
python pyscript/new_experiment.py "filter_fix" --description "Test filter format conversion"
```

**Creates:**
```
experiments/wave_table_analysis/
├── experiment.py       # Template script with your code
├── README.md          # Documentation template
├── output/            # Generated files directory
├── cleanup.sh         # Unix cleanup script
└── cleanup.bat        # Windows cleanup script
```

### Basic Workflow

```bash
# 1. Create experiment
python pyscript/new_experiment.py "my_test"

# 2. Work in experiment directory
cd experiments/my_test
vim experiment.py

# 3. Run experiment
python experiment.py

# 4. Document findings
vim README.md

# 5. Cleanup when done
./cleanup.bat  # Windows
./cleanup.sh   # Unix/Mac
```

---

## Directory Structure

```
experiments/
├── README.md                    # This file (experiment system guide)
├── TEMPLATE/                    # Template for new experiments
│   ├── experiment.py
│   ├── README.md
│   ├── cleanup.sh
│   └── cleanup.bat
│
├── {experiment_name}/           # Your experiments
│   ├── experiment.py            # Main script
│   ├── README.md               # Findings and notes
│   ├── output/                 # Generated files
│   ├── cleanup.sh              # Unix cleanup
│   └── cleanup.bat             # Windows cleanup
│
└── ARCHIVE/                     # Successful experiments (optional)
    └── {experiment_name}/       # Moved here if valuable
        └── FINDINGS.md          # Documented results
```

---

## Experiment Lifecycle

### Phase 1: Create

```bash
# Create new experiment
python pyscript/new_experiment.py "my_experiment"

# Navigate to experiment directory
cd experiments/my_experiment

# Review template files
ls -la
```

**Files Created:**
- `experiment.py` - Template Python script
- `README.md` - Documentation template
- `output/` - Directory for generated files
- `cleanup.sh` - Unix cleanup script
- `cleanup.bat` - Windows cleanup script

### Phase 2: Develop

```bash
# Edit experiment code
vim experiment.py

# Run experiments
python experiment.py

# Check results
ls output/

# Document findings as you go
vim README.md
```

**Development Tips:**
- Start with small tests
- Document assumptions
- Save intermediate results
- Note unexpected behaviors
- Keep README.md updated

### Phase 3: Complete

**If Successful:**
```bash
# Document final findings in README.md
vim README.md

# Option A: Archive for reference
python pyscript/archive_experiment.py my_experiment

# Option B: Move to production
mv experiment.py ../../scripts/feature_name.py

# Option C: Integrate into module
cp key_functions.py ../../sidm2/new_module.py
```

**If Failed:**
```bash
# Document why it failed in README.md
vim README.md

# Note what you learned
# Note what didn't work
# Note next approaches to try

# Cleanup
./cleanup.bat
```

### Phase 4: Cleanup

```bash
# Single experiment cleanup
cd experiments/my_experiment && ./cleanup.bat

# All experiments
python pyscript/cleanup.py --experiments

# Nuclear option (delete all experiments)
rm -rf experiments/*/
```

---

## Experiment Templates

### experiment.py Template

```python
#!/usr/bin/env python3
"""
Experiment: [Name]
Purpose: [One-line description]
Date: YYYY-MM-DD
Status: IN_PROGRESS | SUCCESS | FAILED
"""

import sys
import os

def main():
    print("[EXPERIMENT] Starting...")

    # Your experiment code here

    print("[EXPERIMENT] Complete")

if __name__ == '__main__':
    main()
```

### README.md Template

```markdown
# Experiment: [Name]

**Purpose**: [What you're trying to learn/prove]
**Date**: YYYY-MM-DD
**Status**: IN_PROGRESS | SUCCESS | FAILED

## Hypothesis
[What you think will happen]

## Method
[How you're testing it]

## Results
[What actually happened]

## Conclusion
[What you learned]

## Next Steps
[What to do with this information]
```

### cleanup.bat Template (Windows)

```batch
@echo off
REM Auto-generated cleanup script
echo Cleaning experiment: {experiment_name}
if exist output rmdir /s /q output
del /q *.log *.tmp 2>nul
echo Done
```

### cleanup.sh Template (Unix/Mac)

```bash
#!/bin/bash
# Auto-generated cleanup script
echo "Cleaning experiment: {experiment_name}"
rm -rf output/
rm -f *.log *.tmp
echo "Done"
```

---

## Integration with Cleanup System

The main cleanup tool integrates with the experiment system:

### Experiment-Specific Cleanup

```bash
# Scan for cleanable experiments
python pyscript/cleanup.py --experiments --scan

# Clean all experiments
python pyscript/cleanup.py --experiments --clean

# Force clean (no confirmation)
python pyscript/cleanup.py --experiments --clean --force
```

### Combined Cleanup

```bash
# Normal cleanup (root + output)
python pyscript/cleanup.py --clean

# Experiments included
python pyscript/cleanup.py --all --clean

# With inventory update
python pyscript/cleanup.py --all --clean --update-inventory
```

### Automatic Protection

**Gitignored:**
- Entire `experiments/` directory is in `.gitignore`
- Nothing gets committed accidentally
- Safe to work with sensitive data

**Cleanup Rules:**
- Experiments older than 7 days flagged
- Large experiments flagged (>10 MB)
- Empty experiments flagged
- Undocumented experiments flagged

---

## Best Practices

### DO ✅

1. **Create one experiment per idea**
   - Keep experiments focused and small
   - Easier to understand and debug
   - Faster to iterate

2. **Document as you go**
   - Update README.md regularly
   - Note assumptions and decisions
   - Record unexpected behaviors

3. **Use descriptive names**
   - `wave_table_fix` not `test1`
   - `filter_format_analysis` not `experiment`
   - Helps find experiments later

4. **Run cleanup when done**
   - Don't leave experiments indefinitely
   - Keep `experiments/` directory clean
   - Archive valuable findings first

5. **Archive valuable findings**
   - Move FINDINGS.md to ARCHIVE/
   - Document what worked
   - Reference in main documentation

6. **Keep experiments small and focused**
   - Test one thing at a time
   - Limit scope creep
   - Faster iteration

### DON'T ❌

1. **Commit experiments to git**
   - Experiments are temporary
   - Move to production first
   - Keep git history clean

2. **Leave experiments running indefinitely**
   - Cleanup after 1-7 days
   - Archive or delete
   - Don't accumulate cruft

3. **Mix multiple ideas in one experiment**
   - Hard to understand results
   - Difficult to extract findings
   - Create separate experiments

4. **Forget to document findings**
   - Always update README.md
   - Note what worked and didn't
   - Future you will thank you

5. **Keep failed experiments without documentation**
   - Document why it failed
   - Note what you learned
   - Then cleanup

---

## Archiving Successful Experiments

When an experiment produces valuable insights, archive it:

### Manual Archive

```bash
# Create archive directory
mkdir -p experiments/ARCHIVE/wave_table_analysis

# Copy documentation
cp experiments/wave_table_analysis/README.md \
   experiments/ARCHIVE/wave_table_analysis/FINDINGS.md

# Optionally copy key code snippets
cp experiments/wave_table_analysis/critical_function.py \
   experiments/ARCHIVE/wave_table_analysis/

# Cleanup original
cd experiments/wave_table_analysis && ./cleanup.bat
```

### Automated Archive (if available)

```bash
# Use archive script
python pyscript/archive_experiment.py wave_table_analysis
```

**Archive Structure:**
```
experiments/ARCHIVE/
└── wave_table_analysis/
    ├── FINDINGS.md        # Documented results
    ├── key_snippet.py     # Important code (optional)
    └── screenshots/       # Visual documentation (optional)
```

**Archive Contents:**
- FINDINGS.md - What you learned
- Code snippets - Critical algorithms only
- Screenshots - Visual proof of concept
- References - Links to related work

---

## Cleanup Schedule

### Daily (if active development)

```bash
# Review active experiments
ls experiments/

# Cleanup completed experiments
cd experiments/my_completed_test && ./cleanup.bat
```

### Weekly

```bash
# Archive valuable experiments
python pyscript/archive_experiment.py valuable_test

# Delete failed/abandoned experiments
python pyscript/cleanup.py --experiments --clean

# Update inventory
python pyscript/cleanup.py --experiments --scan
```

### Monthly

```bash
# Review ARCHIVE for outdated findings
ls experiments/ARCHIVE/

# Full cleanup with force
python pyscript/cleanup.py --experiments --force

# Clean everything
python pyscript/cleanup.py --all --clean --update-inventory
```

---

## Example Workflows

### Workflow 1: Quick Test

```bash
# Monday morning: Idea to test wave table format
python pyscript/new_experiment.py "wave_test"
cd experiments/wave_test
vim experiment.py  # Add test code

# Monday afternoon: Run test
python experiment.py > output/results.txt
cat output/results.txt  # Check results

# Result: Failed, document and cleanup
vim README.md  # Note: "Approach doesn't work because..."
./cleanup.bat
```

### Workflow 2: Multi-Day Investigation

```bash
# Monday: Start investigation
python pyscript/new_experiment.py "filter_format_fix"
cd experiments/filter_format_fix
vim experiment.py  # Initial approach

# Tuesday: Iterate
python experiment.py
vim experiment.py  # Adjust based on results
python experiment.py
vim README.md  # Document findings

# Wednesday: Success!
vim README.md  # Final documentation
python pyscript/archive_experiment.py filter_format_fix
mv experiment.py ../../sidm2/filter_converter.py

# Cleanup
./cleanup.bat
```

### Workflow 3: Prototype Feature

```bash
# Week 1: Prototype
python pyscript/new_experiment.py "sf2_viewer_prototype"
cd experiments/sf2_viewer_prototype
# ... develop prototype over several days ...

# Week 2: Integrate
vim README.md  # Document design decisions
mkdir ../../pyscript/sf2_viewer/
cp *.py ../../pyscript/sf2_viewer/
python pyscript/archive_experiment.py sf2_viewer_prototype

# Cleanup
./cleanup.bat
```

---

## Integration with Documentation

When experiments produce insights, update relevant documentation:

### Update Architecture Docs

If experiment reveals architectural insight:
```bash
vim docs/ARCHITECTURE.md
# Add section: "Lessons from {experiment_name}"
```

### Update Component Docs

If experiment improves component understanding:
```bash
vim docs/COMPONENTS_REFERENCE.md
# Update component description with findings
```

### Update Guides

If experiment creates new workflow:
```bash
vim docs/guides/NEW_WORKFLOW.md
# Document the new approach
```

---

## FAQ

**Q: Can I commit an experiment?**
A: No. Experiments are gitignored. Move to production first.

**Q: How long should I keep experiments?**
A: Delete after documenting findings (usually 1-7 days).

**Q: What if I need to share an experiment?**
A: Document in README.md, archive it, or move to production.

**Q: Can I have nested experiments?**
A: No. Keep experiments flat and focused.

**Q: What if my experiment needs production code?**
A: Import from `scripts/` or `sidm2/` - don't copy code.

**Q: How do I test experiments?**
A: Run directly: `python experiment.py` - no formal testing needed.

**Q: What if an experiment becomes permanent?**
A: Move to `scripts/` or `pyscript/` and integrate properly.

**Q: Can I use external data in experiments?**
A: Yes, but document data sources in README.md.

**Q: What if experiment output is large?**
A: Use `output/` directory - it's cleaned automatically.

**Q: How do I reference archived experiments?**
A: Link to `experiments/ARCHIVE/{name}/FINDINGS.md` in docs.

---

## Troubleshooting

### Experiment Creation Fails

**Issue**: `new_experiment.py` not found

**Solution**:
```bash
# Ensure you're in project root
cd /path/to/SIDM2

# Check script exists
ls pyscript/new_experiment.py

# Run with full path
python pyscript/new_experiment.py "my_test"
```

### Cleanup Doesn't Work

**Issue**: `cleanup.bat` fails

**Solution**:
```bash
# Make scripts executable (Unix/Mac)
chmod +x cleanup.sh

# Run with explicit interpreter (Windows)
cmd.exe /c cleanup.bat

# Manual cleanup
rm -rf output/
rm -f *.log *.tmp
```

### Experiment Not Gitignored

**Issue**: Git shows experiment files

**Solution**:
```bash
# Check .gitignore has experiments/
cat .gitignore | grep experiments

# Should show:
# experiments/

# If missing, add it
echo "experiments/" >> .gitignore
```

---

## Related Documentation

- **Cleanup System**: `docs/guides/CLEANUP_SYSTEM.md`
- **Root Folder Rules**: `docs/guides/ROOT_FOLDER_RULES.md`
- **File Inventory**: `docs/FILE_INVENTORY.md`
- **Architecture**: `docs/ARCHITECTURE.md`

---

## Summary

The experiment system provides:
- ✅ Dedicated space for temporary code
- ✅ Automatic gitignore protection
- ✅ Self-cleaning structure with scripts
- ✅ Documentation templates
- ✅ Easy cleanup and archiving
- ✅ Archive for valuable findings
- ✅ Integration with main cleanup system

**Remember**: Experiments are temporary. Production code lives in `scripts/` or `pyscript/` or `sidm2/`.

---

**Last Updated**: 2025-12-21
**Version**: 2.2
**Related Script**: `pyscript/new_experiment.py`
