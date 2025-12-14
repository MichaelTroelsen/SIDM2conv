#!/usr/bin/env python3
"""
Create a new experiment with proper structure and auto-cleanup

Usage:
    python new_experiment.py "experiment_name"
    python new_experiment.py "experiment_name" --description "What I'm testing"
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

EXPERIMENT_TEMPLATE = '''#!/usr/bin/env python3
"""
Experiment: {name}
Purpose: {description}
Date: {date}
Status: IN_PROGRESS
"""

import sys
from pathlib import Path

# Add parent directory to path to import sidm2 modules
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    print("[EXPERIMENT] {name}")
    print("[EXPERIMENT] {description}")
    print()

    # Your experiment code here
    print("[TODO] Implement experiment")

    print()
    print("[EXPERIMENT] Complete")

if __name__ == '__main__':
    main()
'''

README_TEMPLATE = '''# Experiment: {name}

**Purpose**: {description}
**Date**: {date}
**Status**: IN_PROGRESS

## Hypothesis

[What you think will happen]

## Method

[How you're testing it]

1. Step 1
2. Step 2
3. Step 3

## Results

[What actually happened]

### Expected
- ...

### Actual
- ...

## Conclusion

[What you learned]

## Next Steps

- [ ] [Action item 1]
- [ ] [Action item 2]

## Files Generated

- `output/` - Generated output files
- `*.log` - Log files

## Cleanup

Run `./cleanup.sh` when done to remove all generated files.
'''

CLEANUP_TEMPLATE = '''#!/bin/bash
# Auto-generated cleanup script for experiment: {name}

echo "[CLEANUP] Cleaning experiment: {name}"

# Remove output directory
if [ -d "output" ]; then
    echo "  - Removing output/"
    rm -rf output/
fi

# Remove log files
if ls *.log 1> /dev/null 2>&1; then
    echo "  - Removing log files"
    rm -f *.log
fi

# Remove temporary files
if ls *.tmp 1> /dev/null 2>&1; then
    echo "  - Removing temp files"
    rm -f *.tmp
fi

# Remove test output files
if ls test_*.* 1> /dev/null 2>&1; then
    echo "  - Removing test files"
    rm -f test_*.*
fi

echo "[CLEANUP] Done"
'''

CLEANUP_BAT_TEMPLATE = '''@echo off
REM Auto-generated cleanup script for experiment: {name}

echo [CLEANUP] Cleaning experiment: {name}

REM Remove output directory
if exist output (
    echo   - Removing output/
    rmdir /s /q output
)

REM Remove log files
if exist *.log (
    echo   - Removing log files
    del /q *.log
)

REM Remove temporary files
if exist *.tmp (
    echo   - Removing temp files
    del /q *.tmp
)

REM Remove test output files
if exist test_*.* (
    echo   - Removing test files
    del /q test_*.*
)

echo [CLEANUP] Done
'''

def create_experiment(name, description="[Experiment description]"):
    """Create a new experiment directory with template files"""

    # Validate name
    if not name.replace('_', '').replace('-', '').isalnum():
        print("[ERROR] Experiment name must be alphanumeric (underscores and hyphens allowed)")
        return False

    # Create experiment directory
    exp_dir = Path("experiments") / name
    if exp_dir.exists():
        print(f"[ERROR] Experiment '{name}' already exists at: {exp_dir}")
        return False

    exp_dir.mkdir(parents=True)
    print(f"[CREATE] Experiment directory: {exp_dir}")

    # Create output directory
    output_dir = exp_dir / "output"
    output_dir.mkdir()
    (output_dir / ".gitkeep").touch()
    print(f"[CREATE] Output directory: {output_dir}")

    # Get current date
    date = datetime.now().strftime("%Y-%m-%d")

    # Create experiment.py
    experiment_file = exp_dir / "experiment.py"
    experiment_file.write_text(EXPERIMENT_TEMPLATE.format(
        name=name,
        description=description,
        date=date
    ))
    print(f"[CREATE] Experiment script: {experiment_file}")

    # Create README.md
    readme_file = exp_dir / "README.md"
    readme_file.write_text(README_TEMPLATE.format(
        name=name,
        description=description,
        date=date
    ))
    print(f"[CREATE] README: {readme_file}")

    # Create cleanup scripts
    cleanup_sh = exp_dir / "cleanup.sh"
    cleanup_sh.write_text(CLEANUP_TEMPLATE.format(name=name))
    cleanup_sh.chmod(0o755)  # Make executable
    print(f"[CREATE] Cleanup script (Unix): {cleanup_sh}")

    cleanup_bat = exp_dir / "cleanup.bat"
    cleanup_bat.write_text(CLEANUP_BAT_TEMPLATE.format(name=name))
    print(f"[CREATE] Cleanup script (Windows): {cleanup_bat}")

    # Success message
    print()
    print("="*80)
    print(f"[SUCCESS] Experiment '{name}' created!")
    print("="*80)
    print()
    print("Next steps:")
    print(f"  1. cd experiments/{name}")
    print(f"  2. Edit experiment.py (implement your test)")
    print(f"  3. Edit README.md (document as you go)")
    print(f"  4. python experiment.py (run the experiment)")
    print(f"  5. ./cleanup.sh or cleanup.bat (when done)")
    print()
    print("To delete this experiment:")
    print(f"  python cleanup.py --experiments  # (will include this experiment)")
    print()

    return True

def main():
    parser = argparse.ArgumentParser(
        description='Create a new experiment with proper structure',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python new_experiment.py "wave_table_fix"
  python new_experiment.py "filter_format" --description "Test filter format conversion"

The experiment will be created in experiments/{name}/ with:
  - experiment.py (template script)
  - README.md (documentation template)
  - output/ (for generated files)
  - cleanup.sh / cleanup.bat (cleanup scripts)
        '''
    )
    parser.add_argument('name', help='Experiment name (alphanumeric, underscores, hyphens)')
    parser.add_argument('--description', '-d', default='[Experiment description]',
                      help='One-line description of what you\'re testing')

    args = parser.parse_args()

    # Create experiments directory if it doesn't exist
    Path("experiments").mkdir(exist_ok=True)

    # Create experiment
    if not create_experiment(args.name, args.description):
        sys.exit(1)

if __name__ == '__main__':
    main()
