# Experiments Directory

This directory contains temporary experiments, prototypes, and proofs of concept.

**Everything in this directory is gitignored and will be cleaned up regularly.**

---

## Quick Start

### Create New Experiment

```bash
# Use the experiment template
python new_experiment.py "wave_table_analysis"
```

This creates:
```
experiments/
└── wave_table_analysis/
    ├── experiment.py       # Your code
    ├── README.md          # Description and findings
    ├── output/            # Generated files
    └── cleanup.sh         # Auto-cleanup script
```

### Work on Experiment

```bash
cd experiments/wave_table_analysis
python experiment.py
```

### When Done

```bash
# Document findings
vim README.md

# Cleanup
./cleanup.sh

# Or cleanup all experiments
python cleanup.py --experiments
```

---

## Directory Structure

```
experiments/
├── README.md (this file)
├── TEMPLATE/                    # Template for new experiments
│   ├── experiment.py
│   ├── README.md
│   ├── cleanup.sh
│   └── .gitkeep
│
├── {experiment_name}/           # Your experiments
│   ├── experiment.py            # Main script
│   ├── README.md               # Findings and notes
│   ├── output/                 # Generated files
│   └── cleanup.sh              # Cleanup script
│
└── ARCHIVE/                     # Successful experiments (optional)
    └── {experiment_name}/       # Moved here if valuable
        └── FINDINGS.md          # Documented results
```

---

## Experiment Lifecycle

### 1. Create
```bash
python new_experiment.py "my_experiment"
cd experiments/my_experiment
```

### 2. Develop
```bash
# Edit experiment.py
vim experiment.py

# Run experiments
python experiment.py

# Document as you go
vim README.md
```

### 3. Complete

**If successful**:
```bash
# Document findings in README.md
vim README.md

# Archive (optional)
python archive_experiment.py my_experiment

# Or move to production
mv experiment.py ../../scripts/feature_name.py
```

**If failed**:
```bash
# Document why in README.md
vim README.md

# Cleanup
./cleanup.sh
```

### 4. Cleanup
```bash
# Single experiment
cd experiments/my_experiment && ./cleanup.sh

# All experiments
python cleanup.py --experiments

# Nuclear option (delete all experiments)
rm -rf experiments/*/
```

---

## Experiment Template

Every experiment should have:

### experiment.py
```python
#!/usr/bin/env python3
"""
Experiment: [Name]
Purpose: [One-line description]
Date: YYYY-MM-DD
Status: IN_PROGRESS | SUCCESS | FAILED
"""

def main():
    print("[EXPERIMENT] Starting...")

    # Your experiment code here

    print("[EXPERIMENT] Complete")

if __name__ == '__main__':
    main()
```

### README.md
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

### cleanup.sh
```bash
#!/bin/bash
# Auto-generated cleanup script
echo "Cleaning experiment: {experiment_name}"
rm -rf output/
rm -f *.log *.tmp
echo "Done"
```

---

## Automatic Cleanup

Experiments are automatically cleaned by:

### 1. Gitignore
The entire `experiments/` directory is gitignored, so nothing gets committed.

### 2. Cleanup Tool
```bash
# Scan for cleanable experiments
python cleanup.py --experiments --scan

# Clean all experiments
python cleanup.py --experiments --clean
```

### 3. Pre-Commit Hook
The git pre-commit hook warns if experiments/ is getting large.

---

## Best Practices

### DO
- ✅ Create one experiment per idea
- ✅ Document as you go
- ✅ Use descriptive names
- ✅ Run cleanup when done
- ✅ Archive valuable findings
- ✅ Keep experiments small and focused

### DON'T
- ❌ Commit experiments to git
- ❌ Leave experiments running indefinitely
- ❌ Mix multiple ideas in one experiment
- ❌ Forget to document findings
- ❌ Keep failed experiments without documentation

---

## Archive Successful Experiments

If an experiment produces valuable insights:

```bash
# Archive with findings
python archive_experiment.py wave_table_analysis

# Or manually
mkdir -p experiments/ARCHIVE/wave_table_analysis
cp experiments/wave_table_analysis/README.md \
   experiments/ARCHIVE/wave_table_analysis/FINDINGS.md
```

Archived experiments are kept for reference but cleaned of code/data.

---

## Cleanup Schedule

### Daily
- Review active experiments
- Cleanup completed experiments

### Weekly
- Archive valuable experiments
- Delete failed/abandoned experiments

### Monthly
- Review ARCHIVE for outdated findings
- Full cleanup: `python cleanup.py --experiments --force`

---

## Example Workflow

```bash
# Monday: Start new experiment
python new_experiment.py "filter_format_fix"
cd experiments/filter_format_fix
vim experiment.py

# Tuesday: Run and iterate
python experiment.py > output/results.txt
vim README.md  # Document findings

# Wednesday: Success! Move to production
vim README.md  # Final documentation
python archive_experiment.py filter_format_fix
mv experiment.py ../../sidm2/filter_converter.py

# Cleanup
./cleanup.sh

# Or: Failed experiment
vim README.md  # Document why it failed
./cleanup.sh
cd ../..
```

---

## Integration with Main Cleanup

The main cleanup tool (`cleanup.py`) knows about experiments:

```bash
# Normal cleanup (root + output)
python cleanup.py --clean

# Experiments only
python cleanup.py --experiments

# Everything
python cleanup.py --all --clean
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

---

## Summary

Experiments directory provides:
- ✅ Dedicated space for temporary code
- ✅ Automatic gitignore
- ✅ Self-cleaning structure
- ✅ Documentation template
- ✅ Easy cleanup
- ✅ Archive for valuable findings

**Remember**: Experiments are temporary. Production code lives in `scripts/` or `sidm2/`.
