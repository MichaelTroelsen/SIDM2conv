#!/usr/bin/env python3
"""
Create enhanced SID collections inventory with improved player detection.
Lists all files with metadata, player identification, and beautiful formatting.
"""

import os
import struct
from pathlib import Path
from collections import defaultdict, OrderedDict
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.enhanced_player_detection import EnhancedPlayerDetector, get_player_id


def parse_sid_header(filepath):
    """Parse PSID/RSID header"""
    result = {
        'load_addr': None,
        'init_addr': None,
        'play_addr': None,
        'name': None,
        'author': None,
        'released': None,
        'subtunes': 0,
    }

    try:
        with open(filepath, 'rb') as f:
            header = f.read(126)

            if len(header) < 122:
                return result

            result['load_addr'] = struct.unpack('>H', header[8:10])[0]
            result['init_addr'] = struct.unpack('>H', header[10:12])[0]
            result['play_addr'] = struct.unpack('>H', header[12:14])[0]
            result['subtunes'] = struct.unpack('>H', header[14:16])[0]

            name = header[16:48].split(b'\x00')[0].decode('ascii', errors='ignore').strip()
            author = header[48:80].split(b'\x00')[0].decode('ascii', errors='ignore').strip()
            released = header[80:112].split(b'\x00')[0].decode('ascii', errors='ignore').strip()

            if name:
                result['name'] = name
            if author:
                result['author'] = author
            if released:
                result['released'] = released

    except Exception as e:
        pass

    return result


def analyze_collection_enhanced(dirpath, detector):
    """Analyze collection with enhanced player detection"""
    results = {
        'total_files': 0,
        'files': [],
        'player_stats': defaultdict(int),
        'player_files': defaultdict(list),
    }

    if not os.path.isdir(dirpath):
        return results

    sid_files = sorted(Path(dirpath).glob("*.sid"))
    results['total_files'] = len(sid_files)

    for sid_file in sid_files:
        metadata = parse_sid_header(str(sid_file))

        # Detect player type
        player_type, confidence = detector.detect_player(sid_file)
        player_id = get_player_id(player_type)

        file_info = {
            'filename': sid_file.name,
            'size': sid_file.stat().st_size,
            'load_addr': f"${metadata['load_addr']:04X}" if metadata['load_addr'] else "N/A",
            'init_addr': f"${metadata['init_addr']:04X}" if metadata['init_addr'] else "N/A",
            'play_addr': f"${metadata['play_addr']:04X}" if metadata['play_addr'] else "N/A",
            'subtunes': metadata['subtunes'],
            'author': metadata['author'] or "Unknown",
            'player_type': player_type,
            'player_id': player_id,
            'confidence': confidence,
        }

        results['files'].append(file_info)
        results['player_stats'][player_type] += 1
        results['player_files'][player_type].append(sid_file.name)

    return results


def generate_enhanced_inventory():
    """Generate beautifully formatted collection inventory"""
    collections = OrderedDict([
        ('Hubbard_Rob', './Hubbard_Rob'),
        ('Galway_Martin', './Galway_Martin'),
        ('Tel_Jeroen', './Tel_Jeroen'),
        ('Fun_Fun', './Fun_Fun'),
        ('Laxity', './Laxity'),
    ])

    detector = EnhancedPlayerDetector()
    doc = []

    # Header
    doc.append("=" * 120)
    doc.append("SID MUSIC COLLECTIONS - COMPREHENSIVE INVENTORY")
    doc.append("=" * 120)
    doc.append("")
    doc.append("Complete listing of all SID files with enhanced player type identification")
    doc.append("Generated: 2025-12-14")
    doc.append("Total Collections: 5 | Total Files: 620")
    doc.append("")
    doc.append("=" * 120)
    doc.append("")

    total_all_files = 0
    all_player_stats = defaultdict(int)
    all_analyses = {}

    # Analyze each collection
    for coll_name, coll_path in collections.items():
        print(f"Analyzing {coll_name}...", file=sys.stderr)

        analysis = analyze_collection_enhanced(coll_path, detector)
        all_analyses[coll_name] = analysis
        total_files = analysis['total_files']
        total_all_files += total_files

        # Collection header
        doc.append("")
        doc.append("╔" + "═" * 118 + "╗")
        doc.append("║ " + f"{coll_name.upper()}".ljust(116) + " ║")
        doc.append("╠" + "═" * 118 + "╣")
        doc.append("║ " + f"Directory: {coll_path}".ljust(116) + " ║")
        doc.append("║ " + f"Total Files: {total_files}".ljust(116) + " ║")
        doc.append("╚" + "═" * 118 + "╝")
        doc.append("")

        # Player type distribution
        doc.append("PLAYER TYPE DISTRIBUTION:")
        doc.append("-" * 120)

        stats_list = sorted(analysis['player_stats'].items(), key=lambda x: -x[1])
        for player_type, count in stats_list:
            percentage = (count / total_files * 100) if total_files > 0 else 0
            player_id = get_player_id(player_type)
            bar_width = int(percentage / 2)  # 50% scale
            bar = "█" * bar_width + "░" * (50 - bar_width)
            doc.append(f"  {player_type:25} {player_id:25} {bar} {count:3d} ({percentage:5.1f}%)")
            all_player_stats[player_type] += count

        doc.append("")

        # File listing
        doc.append("FILES:")
        doc.append("-" * 120)
        doc.append(f"{'#':>4} {'Filename':<35} {'Player Type':<22} {'Player-ID':<18} {'Size':>8} {'Subtunes':>8}")
        doc.append("-" * 120)

        for idx, file_info in enumerate(analysis['files'], 1):
            filename = file_info['filename']
            if len(filename) > 34:
                filename = filename[:31] + "..."

            player_type = file_info['player_type']
            if len(player_type) > 21:
                player_type = player_type[:18] + "..."

            doc.append(
                f"{idx:>4} {filename:<35} {player_type:<22} {file_info['player_id']:<18} "
                f"{file_info['size']:>8} {file_info['subtunes']:>8}"
            )

        doc.append("")

    # Global summary
    doc.append("")
    doc.append("=" * 120)
    doc.append("GLOBAL SUMMARY")
    doc.append("=" * 120)
    doc.append("")
    doc.append(f"Total Files Analyzed: {total_all_files}")
    doc.append(f"Collections Analyzed: {len(collections)}")
    doc.append(f"Unique Player Types Detected: {len(all_player_stats)}")
    doc.append("")

    # Player type distribution across all collections
    doc.append("PLAYER TYPE DISTRIBUTION (ALL COLLECTIONS):")
    doc.append("-" * 120)

    sorted_players = sorted(all_player_stats.items(), key=lambda x: -x[1])
    for player_type, count in sorted_players:
        percentage = (count / total_all_files * 100) if total_all_files > 0 else 0
        player_id = get_player_id(player_type)
        bar_width = int(percentage / 1.5)  # 66% scale for global view
        bar = "█" * bar_width + "░" * (66 - bar_width)
        doc.append(f"  {player_type:25} {player_id:25} {bar} {count:3d} ({percentage:5.1f}%)")

    doc.append("")

    # Player-ID reference
    doc.append("")
    doc.append("=" * 120)
    doc.append("PLAYER-ID REFERENCE")
    doc.append("=" * 120)
    doc.append("")
    doc.append("Player-ID Format: PLAYER_NAME_NNN (where NNN is sequence number)")
    doc.append("")

    player_reference = set()
    for analysis in all_analyses.values():
        for file_info in analysis['files']:
            player_reference.add((file_info['player_type'], file_info['player_id']))

    sorted_reference = sorted(player_reference, key=lambda x: x[1])
    for player_type, player_id in sorted_reference:
        doc.append(f"  {player_id:<30} = {player_type}")

    doc.append("")

    # Collection comparison
    doc.append("=" * 120)
    doc.append("COLLECTION COMPARISON")
    doc.append("=" * 120)
    doc.append("")

    # Build comparison table
    doc.append(f"{'Player Type':<30}", )
    for coll_name in collections.keys():
        doc[-1] += f" {coll_name:>15}"

    doc.append("-" * 120)

    for player_type in sorted(all_player_stats.keys()):
        line = f"{player_type:<30}"
        for coll_name in collections.keys():
            count = all_analyses[coll_name]['player_stats'].get(player_type, 0)
            line += f" {count:>15}"
        doc.append(line)

    doc.append("")

    # Interesting statistics
    doc.append("=" * 120)
    doc.append("INTERESTING STATISTICS")
    doc.append("=" * 120)
    doc.append("")

    # Find largest file
    all_files = []
    for analysis in all_analyses.values():
        all_files.extend(analysis['files'])

    if all_files:
        largest = max(all_files, key=lambda x: x['size'])
        smallest = min(all_files, key=lambda x: x['size'])
        avg_size = sum(f['size'] for f in all_files) / len(all_files)

        doc.append(f"Largest File:     {largest['filename']} ({largest['size']} bytes)")
        doc.append(f"Smallest File:    {smallest['filename']} ({smallest['size']} bytes)")
        doc.append(f"Average Size:     {avg_size:.0f} bytes")
        doc.append(f"Total Data:       {sum(f['size'] for f in all_files) / 1024 / 1024:.2f} MB")
        doc.append("")

        # Subtune statistics
        total_subtunes = sum(f['subtunes'] for f in all_files)
        avg_subtunes = total_subtunes / len(all_files) if all_files else 0
        doc.append(f"Total Subtunes:   {total_subtunes}")
        doc.append(f"Average Subtunes: {avg_subtunes:.1f}")
        doc.append("")

    # Footer
    doc.append("=" * 120)
    doc.append("Document generated: 2025-12-14 by enhanced_collection_inventory.py")
    doc.append("Player detection: Enhanced detection with composer, signature, and address analysis")
    doc.append("=" * 120)

    return "\n".join(doc)


if __name__ == "__main__":
    print("Generating enhanced SID collections inventory...", file=sys.stderr)
    document = generate_enhanced_inventory()

    # Save to file
    output_path = "SID_COLLECTIONS_ENHANCED_INVENTORY.md"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(document)

    print(f"[DONE] Document saved to: {output_path}", file=sys.stderr)
    print()
    print(document)
