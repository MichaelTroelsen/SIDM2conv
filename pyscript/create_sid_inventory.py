"""Create SID Inventory - Comprehensive catalog of all SID files.

Scans all SID files (excluding output folder) and generates a detailed
markdown inventory using multiple tools:
- SID header parser (title, author, copyright, addresses)
- player-id.exe (player type identification)
- File system info (size, path)

Output: SID_INVENTORY.md with grid/table view
"""

import sys
import subprocess
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime


def parse_sid_header(sid_data: bytes) -> Optional[Dict]:
    """Parse PSID/RSID file header.

    Args:
        sid_data: Complete SID file data

    Returns:
        Dictionary with header information or None if invalid
    """
    if len(sid_data) < 0x7C:
        return None

    magic = sid_data[0:4].decode('ascii', errors='ignore')
    if magic not in ('PSID', 'RSID'):
        return None

    version = (sid_data[4] << 8) | sid_data[5]
    data_offset = (sid_data[6] << 8) | sid_data[7]
    load_addr = (sid_data[8] << 8) | sid_data[9]
    init_addr = (sid_data[0xA] << 8) | sid_data[0xB]
    play_addr = (sid_data[0xC] << 8) | sid_data[0xD]
    songs = (sid_data[0xE] << 8) | sid_data[0xF]
    start_song = (sid_data[0x10] << 8) | sid_data[0x11]

    # Extract strings (null-terminated)
    title = sid_data[0x16:0x36].decode('ascii', errors='ignore').rstrip('\x00').strip()
    author = sid_data[0x36:0x56].decode('ascii', errors='ignore').rstrip('\x00').strip()
    copyright = sid_data[0x56:0x76].decode('ascii', errors='ignore').rstrip('\x00').strip()

    # Handle embedded load address
    if load_addr == 0 and len(sid_data) > data_offset + 2:
        load_addr = sid_data[data_offset] | (sid_data[data_offset + 1] << 8)

    return {
        'format': magic,
        'version': version,
        'load_addr': load_addr,
        'init_addr': init_addr,
        'play_addr': play_addr,
        'songs': songs,
        'start_song': start_song,
        'title': title or '(untitled)',
        'author': author or '(unknown)',
        'copyright': copyright or '(no copyright)',
    }


def identify_player(sid_file: Path, player_id_exe: Path) -> str:
    """Identify SID player using player-id.exe.

    Args:
        sid_file: Path to SID file
        player_id_exe: Path to player-id.exe

    Returns:
        Player name or 'UNIDENTIFIED'
    """
    if not player_id_exe.exists():
        return 'N/A (player-id.exe not found)'

    try:
        result = subprocess.run(
            [str(player_id_exe), str(sid_file)],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Parse output - look for the filename line
        for line in result.stdout.split('\n'):
            if sid_file.name in line:
                # Extract player name (after filename)
                # Format: "filename.sid                    PlayerName"
                # Split on filename and take everything after it
                parts = line.split(sid_file.name)
                if len(parts) >= 2:
                    player = parts[1].strip()
                    if player:
                        return player

        return 'UNIDENTIFIED'

    except subprocess.TimeoutExpired:
        return 'TIMEOUT'
    except Exception as e:
        return f'ERROR: {str(e)[:30]}'


def scan_sid_files(root_dir: Path, exclude_dirs: List[str] = None) -> List[Path]:
    """Scan for all SID files, excluding specified directories.

    Args:
        root_dir: Root directory to scan
        exclude_dirs: List of directory names to exclude (default: ['output'])

    Returns:
        List of SID file paths
    """
    if exclude_dirs is None:
        exclude_dirs = ['output']

    sid_files = []

    for sid_file in root_dir.rglob('*.sid'):
        # Check if file is in excluded directory
        excluded = False
        for exclude in exclude_dirs:
            if exclude in sid_file.parts:
                excluded = True
                break

        if not excluded:
            sid_files.append(sid_file)

    return sorted(sid_files)


def create_inventory_markdown(sid_files: List[Path], output_file: Path, player_id_exe: Path):
    """Create markdown inventory file.

    Args:
        sid_files: List of SID files to inventory
        output_file: Path to output markdown file
        player_id_exe: Path to player-id.exe
    """
    print(f"Creating SID inventory for {len(sid_files)} files...")
    print(f"Output: {output_file}")
    print("=" * 70)

    # Group files by directory
    by_directory = {}
    for sid_file in sid_files:
        # Get directory relative to current working directory
        try:
            rel_path = sid_file.relative_to(Path.cwd())
            dir_name = rel_path.parts[0] if len(rel_path.parts) > 1 else 'Root'
        except ValueError:
            dir_name = 'Other'

        if dir_name not in by_directory:
            by_directory[dir_name] = []
        by_directory[dir_name].append(sid_file)

    # Start markdown file
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write('# SID File Inventory\n\n')
        f.write(f'**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'**Total Files**: {len(sid_files)}\n')
        f.write(f'**Directories**: {len(by_directory)}\n\n')

        # Tools used
        f.write('## Tools Used\n\n')
        f.write('1. **SID Header Parser** - Extracts title, author, copyright, addresses from PSID/RSID header\n')
        f.write('2. **player-id.exe** - Identifies SID player type using pattern matching\n')
        f.write('3. **File System** - File size and path information\n\n')

        # Table of contents
        f.write('## Directories\n\n')
        for dir_name in sorted(by_directory.keys()):
            count = len(by_directory[dir_name])
            f.write(f'- [{dir_name}](#{dir_name.lower().replace(" ", "-")}) ({count} files)\n')
        f.write('\n---\n\n')

        # Process each directory
        total_processed = 0
        for dir_name in sorted(by_directory.keys()):
            files = by_directory[dir_name]

            f.write(f'## {dir_name}\n\n')
            f.write(f'**Files**: {len(files)}\n\n')

            # Table header
            f.write('| File | Title | Author | Player Type | Format | Songs | Load | Init | Play | Size |\n')
            f.write('|------|-------|--------|-------------|--------|-------|------|------|------|------|\n')

            # Process each file
            for sid_file in files:
                total_processed += 1

                # Progress indicator
                if total_processed % 10 == 0:
                    print(f'  Processed {total_processed}/{len(sid_files)}...')

                # Get file info
                file_size = sid_file.stat().st_size

                # Parse SID header
                try:
                    sid_data = sid_file.read_bytes()
                    header = parse_sid_header(sid_data)
                except Exception as e:
                    header = None
                    print(f'  WARNING: Failed to parse {sid_file.name}: {e}')

                # Identify player
                player = identify_player(sid_file, player_id_exe)

                # Write table row
                if header:
                    # Truncate long strings for table
                    title = header['title'][:30] + '...' if len(header['title']) > 30 else header['title']
                    author = header['author'][:20] + '...' if len(header['author']) > 20 else header['author']
                    player_short = player[:25] + '...' if len(player) > 25 else player

                    f.write(f'| {sid_file.name} ')
                    f.write(f'| {title} ')
                    f.write(f'| {author} ')
                    f.write(f'| {player_short} ')
                    f.write(f'| {header["format"]} v{header["version"]} ')
                    f.write(f'| {header["songs"]} ')
                    f.write(f'| ${header["load_addr"]:04X} ')
                    f.write(f'| ${header["init_addr"]:04X} ')
                    f.write(f'| ${header["play_addr"]:04X} ')
                    f.write(f'| {file_size:,} |\n')
                else:
                    f.write(f'| {sid_file.name} ')
                    f.write(f'| ERROR ')
                    f.write(f'| - ')
                    f.write(f'| {player} ')
                    f.write(f'| - ')
                    f.write(f'| - ')
                    f.write(f'| - ')
                    f.write(f'| - ')
                    f.write(f'| - ')
                    f.write(f'| {file_size:,} |\n')

            f.write('\n')

        # Summary statistics
        f.write('---\n\n')
        f.write('## Summary Statistics\n\n')

        # Count by format
        format_counts = {}
        player_counts = {}
        total_size = 0
        total_songs = 0

        for sid_file in sid_files:
            try:
                sid_data = sid_file.read_bytes()
                header = parse_sid_header(sid_data)
                total_size += sid_file.stat().st_size

                if header:
                    fmt = f"{header['format']} v{header['version']}"
                    format_counts[fmt] = format_counts.get(fmt, 0) + 1
                    total_songs += header['songs']

                player = identify_player(sid_file, player_id_exe)
                player_counts[player] = player_counts.get(player, 0) + 1
            except:
                pass

        f.write('### File Formats\n\n')
        for fmt in sorted(format_counts.keys()):
            count = format_counts[fmt]
            pct = (count / len(sid_files) * 100) if len(sid_files) > 0 else 0
            f.write(f'- **{fmt}**: {count} files ({pct:.1f}%)\n')

        f.write('\n### Player Types (Top 10)\n\n')
        for player, count in sorted(player_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            pct = (count / len(sid_files) * 100) if len(sid_files) > 0 else 0
            f.write(f'- **{player}**: {count} files ({pct:.1f}%)\n')

        f.write(f'\n### Total Statistics\n\n')
        f.write(f'- **Total Files**: {len(sid_files)}\n')
        f.write(f'- **Total Size**: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)\n')
        f.write(f'- **Total Songs/Subtunes**: {total_songs}\n')
        f.write(f'- **Average File Size**: {total_size // len(sid_files):,} bytes\n')
        f.write(f'- **Average Songs per File**: {total_songs / len(sid_files):.1f}\n')

    print("=" * 70)
    print(f"SUCCESS: Inventory created: {output_file}")
    print(f"         Total files: {len(sid_files)}")
    print(f"         Total size: {total_size / 1024 / 1024:.2f} MB")


def main():
    """Main entry point."""
    print("SID File Inventory Creator")
    print("=" * 70)

    # Paths
    root_dir = Path(__file__).parent.parent
    output_file = root_dir / 'SID_INVENTORY.md'
    player_id_exe = root_dir / 'tools' / 'player-id.exe'

    # Check player-id.exe
    if not player_id_exe.exists():
        print(f"WARNING: player-id.exe not found at {player_id_exe}")
        print("Player identification will be skipped.")

    # Scan for SID files
    print(f"\nScanning for SID files in {root_dir}...")
    print("(Excluding 'output' directory)")

    sid_files = scan_sid_files(root_dir, exclude_dirs=['output'])

    if not sid_files:
        print("ERROR: No SID files found!")
        return 1

    print(f"Found {len(sid_files)} SID files")
    print()

    # Create inventory
    create_inventory_markdown(sid_files, output_file, player_id_exe)

    return 0


if __name__ == '__main__':
    sys.exit(main())
