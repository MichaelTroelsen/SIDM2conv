#!/usr/bin/env python3
"""
Automatic File Inventory Generator
Regenerates FILE_INVENTORY.md with current file status
"""

import os
import json
from datetime import datetime
from pathlib import Path

def get_file_status(mtime_str):
    """Determine file status based on modification time"""
    if mtime_str >= '2025-11':
        return '🟢 Active'
    elif mtime_str >= '2025-10':
        return '🟡 Old'
    else:
        return '🟡 Old'

def generate_inventory():
    """Generate complete file inventory"""

    inventory = {
        'Main Entry Point': [],
        'Scripts (scripts/)': [],
        'Core Package (sidm2/)': [],
        'Tests': [],
        'Documentation': [],
        'Tools': [],
        'Templates (G5/)': [],
        'Example Files (SID/)': [],
        'Player Files (SIDSF2player/)': [],
        'Configuration': []
    }

    # Scan project files
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', '.pytest_cache', 'node_modules', 'output', 'roundtrip_output', '.claude', 'temp']]

        for file in files:
            filepath = os.path.join(root, file)

            # Skip special files
            if file.endswith(('.pyc', '.pyo')) or file in ['file_inventory.json', 'nul']:
                continue

            try:
                relpath = os.path.relpath(filepath, '.').replace('\\', '/')
                stat = os.stat(filepath)
                size = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')
                status = get_file_status(mtime)

                # Categorize
                if 'sidm2/' in relpath and file.endswith('.py'):
                    inventory['Core Package (sidm2/)'].append((relpath, size, mtime, status))
                elif 'scripts/' in relpath and file.endswith('.py'):
                    # Separate test scripts
                    if file.startswith('test_'):
                        inventory['Tests'].append((relpath, size, mtime, status))
                    else:
                        inventory['Scripts (scripts/)'].append((relpath, size, mtime, status))
                elif '/docs/' in relpath or (file.endswith('.md') and 'docs/' in relpath):
                    inventory['Documentation'].append((relpath, size, mtime, status))
                elif file.endswith('.md') and '/' not in relpath:
                    # Root markdown files
                    inventory['Documentation'].append((relpath, size, mtime, status))
                elif 'tools/' in relpath:
                    inventory['Tools'].append((relpath, size, mtime, status))
                elif 'G5/' in relpath:
                    inventory['Templates (G5/)'].append((relpath, size, mtime, status))
                elif 'SID/' in relpath and file.endswith('.sid'):
                    inventory['Example Files (SID/)'].append((relpath, size, mtime, status))
                elif 'SIDSF2player/' in relpath:
                    inventory['Player Files (SIDSF2player/)'].append((relpath, size, mtime, status))
                elif file.endswith(('.json', '.yml', '.yaml', '.toml', '.ini', '.cfg', '.gitignore')):
                    inventory['Configuration'].append((relpath, size, mtime, status))
                elif '/' not in relpath and file.endswith('.py'):
                    # Main entry point script
                    inventory['Main Entry Point'].append((relpath, size, mtime, status))

            except (OSError, PermissionError):
                continue

    return inventory

def write_inventory_markdown(inventory):
    """Write inventory to FILE_INVENTORY.md"""

    md = [
        '# SIDM2 File Inventory',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
        '',
        '## Purpose',
        'This inventory categorizes all project files with their purpose and recommendations for cleanup.',
        'Files are marked as:',
        '- 🟢 **Active** - Core functionality, recently updated (Nov 2025)',
        '- 🟡 **Old** - Not recently updated, review for cleanup',
        '',
        '**Note**: This file is auto-generated. Run `python update_inventory.py` to refresh.',
        '',
        '---',
        ''
    ]

    # File descriptions
    descriptions = {
        'sid_to_sf2.py': 'Main SID to SF2 converter (v0.6.3)',
        'convert_all.py': 'Batch converter (v0.6.3)',
        'sf2_to_sid.py': 'SF2 to SID packer (v1.0.0)',
        'validate_psid.py': 'PSID header validator',
        'validate_sid_accuracy.py': 'Frame-by-frame accuracy checker',
        'validate_conversion.py': 'Conversion validation',
        'update_inventory.py': 'Auto-generates FILE_INVENTORY.md',
    }

    for category, items in inventory.items():
        if items:
            md.append(f'## {category}')
            md.append('')
            md.append('| File | Size (bytes) | Last Modified | Status |')
            md.append('|------|--------------|---------------|--------|')

            for path, size, mtime, status in sorted(items, key=lambda x: x[2], reverse=True)[:100]:
                filename = os.path.basename(path)
                desc = descriptions.get(filename, '')
                display = f'{path} - {desc}' if desc else path
                md.append(f'| {display} | {size:,} | {mtime} | {status} |')

            md.append('')

    # Add cleanup recommendations
    md.extend([
        '---',
        '',
        '## Cleanup Recommendations',
        '',
        '### Safe to Remove (if confirmed unused)',
        '1. **output/** directory contents - Can be regenerated',
        '2. **roundtrip_output/** directory contents - Can be regenerated',
        '',
        '### Keep Everything Else',
        '- All sidm2/ package files are core functionality',
        '- All test files are part of the test suite',
        '- All documentation provides valuable reference',
        '- All G5/ templates are required for conversion',
        '- All SID/ example files are test references',
        '',
        '---',
        '',
        '## Usage',
        '',
        'To update this inventory, run:',
        '```bash',
        'python scripts/update_inventory.py',
        '```',
        '',
        '---',
        '',
        f'Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
    ])

    # Write to file
    with open('FILE_INVENTORY.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))

    print('FILE_INVENTORY.md updated successfully')
    print(f'Total categories: {len([c for c in inventory.values() if c])}')
    print(f'Total files tracked: {sum(len(items) for items in inventory.values())}')

if __name__ == '__main__':
    print('Generating file inventory...')
    inventory = generate_inventory()
    write_inventory_markdown(inventory)
