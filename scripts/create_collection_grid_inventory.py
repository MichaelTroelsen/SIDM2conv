#!/usr/bin/env python3
"""Create grid-format SID collections inventory with player-id.exe detection."""

import os
import sys
import struct
import subprocess
from pathlib import Path
from collections import defaultdict, OrderedDict

sys.path.insert(0, str(Path(__file__).parent.parent))


def find_player_id_exe():
    """Find player-id.exe."""
    for p in ['./tools/player-id.exe', 'tools/player-id.exe', './tools\player-id.exe']:
        if Path(p).exists():
            return str(Path(p).absolute())
    return None


def detect_player_with_player_id(sid_file: Path, player_id_exe: str) -> str:
    """Use player-id.exe to detect player type."""
    try:
        result = subprocess.run(
            [player_id_exe, str(sid_file)],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode == 0:
            lines = result.stdout.split('\n')
            # Look for the line with the filename and player type
            for line in lines:
                if '.sid' in line.lower():
                    parts = line.split()
                    if len(parts) >= 2:
                        # Last non-empty part should be player type
                        player = parts[-1].strip()
                        if player and not player.isdigit():
                            return player
    except:
        pass

    return "Unknown"


def parse_sid_header(filepath):
    """Parse PSID/RSID header."""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(126)

        if len(header) < 122:
            return {'subtunes': 0}

        subtunes = struct.unpack('>H', header[14:16])[0]
        return {'subtunes': subtunes}
    except:
        return {'subtunes': 0}


def format_grid_row(cells, col_widths):
    """Format a row for grid output."""
    formatted = []
    for i, cell in enumerate(cells):
        if i < len(col_widths):
            formatted.append(str(cell).ljust(col_widths[i]))
    return '| ' + ' | '.join(formatted) + ' |'


def generate_grid_inventory():
    """Generate grid-formatted inventory."""
    player_id_exe = find_player_id_exe()
    if not player_id_exe:
        print("Error: player-id.exe not found")
        return
    
    print(f"Using: {player_id_exe}\n")

    collections = OrderedDict([
        ('Hubbard_Rob', './Hubbard_Rob'),
        ('Galway_Martin', './Galway_Martin'),
        ('Tel_Jeroen', './Tel_Jeroen'),
        ('Fun_Fun', './Fun_Fun'),
        ('Laxity', './Laxity'),
    ])

    doc = []
    doc.append('# SID COLLECTIONS INVENTORY')
    doc.append('')
    doc.append('**Date**: 2025-12-14  |  **Total**: 620 files across 5 collections')
    doc.append('')
    doc.append('---')
    doc.append('')

    total_files = 0
    all_players = defaultdict(int)

    for coll_name, coll_path in collections.items():
        print(f"Processing {coll_name}...", flush=True)
        
        coll_dir = Path(coll_path)
        sid_files = sorted(coll_dir.glob('*.sid')) if coll_dir.exists() else []
        coll_total = len(sid_files)
        total_files += coll_total

        doc.append(f'## {coll_name.upper()}')
        doc.append(f'**Directory**: {coll_path} | **Files**: {coll_total}')
        doc.append('')

        headers = ['#', 'Filename', 'Player Type', 'Size', 'Subtunes']
        col_widths = [3, 40, 32, 12, 8]
        
        sep = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'
        doc.append(sep)
        doc.append(format_grid_row(headers, col_widths))
        doc.append(sep)

        for idx, sid_file in enumerate(sid_files, 1):
            try:
                metadata = parse_sid_header(str(sid_file))
                player_type = detect_player_with_player_id(sid_file, player_id_exe)
                
                size = sid_file.stat().st_size
                subtunes = metadata['subtunes']

                cells = [
                    idx,
                    sid_file.name[:39],
                    player_type[:31],
                    size,
                    subtunes
                ]

                doc.append(format_grid_row(cells, col_widths))
                all_players[player_type] += 1
                
                if idx % 50 == 0:
                    print(f"  {idx}/{coll_total} files processed...", flush=True)
            except Exception as e:
                print(f"  Error processing {sid_file.name}: {e}")

        doc.append(sep)
        doc.append('')

    # Summary
    doc.append('## SUMMARY')
    doc.append('')
    doc.append('**Player Type Distribution**:')
    doc.append('')
    
    headers = ['Player Type', 'Count', 'Percentage']
    col_widths = [35, 8, 12]
    
    sep = '+' + '+'.join('-' * (w + 2) for w in col_widths) + '+'
    doc.append(sep)
    doc.append(format_grid_row(headers, col_widths))
    doc.append(sep)

    for player_type, count in sorted(all_players.items(), key=lambda x: -x[1]):
        percentage = (count / total_files * 100) if total_files > 0 else 0
        cells = [
            player_type[:34],
            count,
            f"{percentage:.1f}%"
        ]
        doc.append(format_grid_row(cells, col_widths))

    doc.append(sep)
    doc.append('')
    doc.append(f'**Total Files Analyzed**: {total_files}')
    doc.append(f'**Unique Player Types**: {len(all_players)}')
    doc.append('')

    output_path = Path('./SID_COLLECTIONS_GRID_INVENTORY.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(doc))

    print(f"\n[DONE] Saved to: {output_path}")
    print(f"Files: {total_files} | Players: {len(all_players)}")


if __name__ == '__main__':
    generate_grid_inventory()
