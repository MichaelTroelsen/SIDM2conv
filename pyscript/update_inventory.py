#!/usr/bin/env python3
"""
Update FILE_INVENTORY.md with current repository structure.
Run this after adding/removing files or reorganizing directories.
"""

import os
from pathlib import Path
from datetime import datetime

def get_file_info(path):
    """Get file size and category."""
    size = path.stat().st_size
    if size < 1024:
        size_str = f"{size}B"
    elif size < 1024 * 1024:
        size_str = f"{size/1024:.1f}KB"
    else:
        size_str = f"{size/(1024*1024):.1f}MB"
    return size_str

def scan_directory(base_path, rel_path=""):
    """Scan directory and return file tree."""
    full_path = base_path / rel_path if rel_path else base_path
    files = {"dirs": {}, "files": []}

    try:
        for item in sorted(full_path.iterdir()):
            rel_item = item.relative_to(base_path)

            if item.is_dir():
                # Skip hidden dirs and common excludes
                if item.name.startswith('.') or item.name in ['__pycache__', 'node_modules']:
                    continue
                files["dirs"][item.name] = scan_directory(base_path, rel_item)
            else:
                # Skip hidden files and common excludes
                if item.name.startswith('.') or item.suffix in ['.pyc', '.log']:
                    continue
                size = get_file_info(item)
                files["files"].append((item.name, size))
    except PermissionError:
        pass

    return files

def format_tree(tree, indent=0, prefix=""):
    """Format file tree as markdown."""
    lines = []

    # Files first
    for name, size in tree["files"]:
        lines.append(f"{prefix}├── {name} ({size})")

    # Then directories
    dirs = list(tree["dirs"].items())
    for i, (name, subtree) in enumerate(dirs):
        is_last = (i == len(dirs) - 1)
        connector = "└──" if is_last else "├──"
        lines.append(f"{prefix}{connector} {name}/")

        # Count files and dirs in subtree
        file_count = len(subtree["files"])
        dir_count = len(subtree["dirs"])
        if file_count > 0 or dir_count > 0:
            new_prefix = prefix + ("    " if is_last else "│   ")
            lines.extend(format_tree(subtree, indent + 1, new_prefix))

    return lines

def main():
    # Get repository root (parent of pyscript/ directory)
    base_path = Path(__file__).parent.parent

    # Scan repository
    tree = scan_directory(base_path)

    # Build inventory
    inventory = f"""# File Inventory

**Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Repository Structure

"""

    # Add tree
    inventory += "```\n"
    inventory += "SIDM2/\n"
    inventory += "\n".join(format_tree(tree, prefix=""))
    inventory += "\n```\n"

    # Add category summaries
    inventory += """
## File Categories

### Root (Production)
- **Scripts**: Main conversion pipeline scripts
- **Documentation**: Core project documentation

### temp-exp/ (Experimental)
- **Purpose**: ALL experimental and debug work
- **Scripts**: Test, debug, analysis scripts
- **Rule**: Can be deleted/archived when no longer needed

### archived/ (Old Documentation)
- **Purpose**: Superseded but potentially useful documents
- **Contents**: Old analysis, completed experiments
- **Rule**: Can be cleaned up periodically

### sidm2/ (Core Package)
- **Purpose**: Core Python modules and utilities
- **Contents**: Parser, writer, extraction modules

### docs/ (Official Documentation)
- **Purpose**: Format specs, disassembly, conversion strategies
- **Contents**: Markdown documentation files

### output/ (Production Outputs)
- **Purpose**: Final conversion outputs
- **Rule**: Experimental outputs go to temp-exp/output/

### SID/ (Input Files)
- **Purpose**: Source SID music files for conversion

### tools/ (External Tools)
- **Purpose**: External binaries (siddump, player-id, etc.)

## Management Rules

See `FILE_MANAGEMENT_RULES.md` for complete rules.

### Quick Rules
1. Production scripts → Root
2. Experiments → temp-exp/
3. Old docs → archived/
4. Update inventory after changes: `python update_inventory.py`

### New Experiment Workflow
```bash
# Work in temp-exp
cd temp-exp
# Create your experiment
vim my_experiment.py
# Run it
python my_experiment.py

# If successful and production-ready:
mv my_experiment.py ../
python ../update_inventory.py

# If failed or temporary:
# Just delete it or leave in temp-exp for reference
```

## Cleanup Schedule
- **After each feature**: Clean temp-exp/
- **Weekly**: Review temp-exp/ for deletable files
- **Monthly**: Archive old experiments
"""

    # Write inventory to docs/
    inventory_path = base_path / "docs" / "FILE_INVENTORY.md"
    inventory_path.write_text(inventory, encoding='utf-8')

    print(f"[OK] Updated {inventory_path}")
    print(f"     Files in root: {len(tree['files'])}")
    print(f"     Subdirectories: {len(tree['dirs'])}")

if __name__ == '__main__':
    main()
