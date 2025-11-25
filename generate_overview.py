#!/usr/bin/env python3
"""
Generate overview of all conversion confidence scores.

Parses all _info.txt files in SF2 directory and creates a combined
overview report showing confidence metrics across all converted files.

Usage:
    python generate_overview.py
    python generate_overview.py --output SF2/confidence_overview.txt
"""

import os
import re
import argparse
from datetime import datetime
from pathlib import Path


def parse_confidence_from_info(info_path: str) -> dict:
    """
    Parse confidence scores from an _info.txt file.

    Args:
        info_path: Path to the _info.txt file

    Returns:
        Dictionary with confidence data
    """
    result = {
        'filename': os.path.basename(info_path).replace('_info.txt', ''),
        'overall': 0.0,
        'components': {},
        'notes': [],
    }

    try:
        with open(info_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find overall score
        overall_match = re.search(r'Overall Score:\s*(\d+\.?\d*)%', content)
        if overall_match:
            result['overall'] = float(overall_match.group(1))

        # Parse component scores from the table
        # Pattern: ComponentName     XX.X% Status
        component_pattern = r'^\s*(\w[\w\s]+?)\s+(\d+\.?\d*)%\s+(\w+)'
        for match in re.finditer(component_pattern, content, re.MULTILINE):
            name = match.group(1).strip()
            score = float(match.group(2))
            status = match.group(3)

            # Normalize component names
            name_key = name.lower().replace(' ', '_')
            result['components'][name_key] = {
                'score': score,
                'status': status
            }

        # Extract notes
        notes_section = re.search(r'Notes:\n((?:\s*-.*\n)+)', content)
        if notes_section:
            for line in notes_section.group(1).split('\n'):
                line = line.strip()
                if line.startswith('-'):
                    result['notes'].append(line[1:].strip())

        # Extract song metadata
        name_match = re.search(r'Name:\s*(.+)$', content, re.MULTILINE)
        if name_match:
            result['song_name'] = name_match.group(1).strip()

        author_match = re.search(r'Author:\s*(.+)$', content, re.MULTILINE)
        if author_match:
            result['author'] = author_match.group(1).strip()

    except Exception as e:
        result['error'] = str(e)

    return result


def generate_overview(sf2_dir: str = 'SF2', output_path: str = None) -> str:
    """
    Generate overview report from all _info.txt files.

    Args:
        sf2_dir: Directory containing _info.txt files
        output_path: Optional output file path

    Returns:
        Report content as string
    """
    # Find all info files
    info_files = sorted(Path(sf2_dir).glob('*_info.txt'))

    if not info_files:
        return "No _info.txt files found in {sf2_dir}"

    # Parse all files
    all_data = []
    for info_file in info_files:
        data = parse_confidence_from_info(str(info_file))
        all_data.append(data)

    # Generate report
    lines = [
        "Extraction Confidence Overview",
        "=" * 70,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"Files analyzed: {len(all_data)}",
        "",
        "=" * 70,
        "Summary by File",
        "=" * 70,
        "",
    ]

    # Sort by overall score descending
    all_data_sorted = sorted(all_data, key=lambda x: x['overall'], reverse=True)

    # Header
    lines.append(f"{'File':<25} {'Overall':>8} {'Instr':>7} {'Wave':>7} {'Pulse':>7} {'Filter':>7} {'Order':>7}")
    lines.append("-" * 70)

    for data in all_data_sorted:
        filename = data['filename'][:24]
        overall = f"{data['overall']:.1f}%"

        # Get component scores
        instr = data['components'].get('instruments', {}).get('score', 0)
        wave = data['components'].get('wave_table', {}).get('score', 0)
        pulse = data['components'].get('pulse_table', {}).get('score', 0)
        filt = data['components'].get('filter_table', {}).get('score', 0)
        order = data['components'].get('orderlist', {}).get('score', 0)

        lines.append(
            f"{filename:<25} {overall:>8} {instr:>6.1f}% {wave:>6.1f}% "
            f"{pulse:>6.1f}% {filt:>6.1f}% {order:>6.1f}%"
        )

    # Statistics
    lines.extend([
        "",
        "=" * 70,
        "Statistics",
        "=" * 70,
        "",
    ])

    if all_data:
        overall_scores = [d['overall'] for d in all_data]
        avg_overall = sum(overall_scores) / len(overall_scores)
        min_overall = min(overall_scores)
        max_overall = max(overall_scores)

        lines.append(f"Overall Score Statistics:")
        lines.append(f"  Average: {avg_overall:.1f}%")
        lines.append(f"  Minimum: {min_overall:.1f}%")
        lines.append(f"  Maximum: {max_overall:.1f}%")
        lines.append("")

        # Count by status
        excellent = sum(1 for s in overall_scores if s >= 90)
        good = sum(1 for s in overall_scores if 75 <= s < 90)
        fair = sum(1 for s in overall_scores if 50 <= s < 75)
        low = sum(1 for s in overall_scores if s < 50)

        lines.append(f"Quality Distribution:")
        lines.append(f"  Excellent (90%+): {excellent}")
        lines.append(f"  Good (75-90%):    {good}")
        lines.append(f"  Fair (50-75%):    {fair}")
        lines.append(f"  Low (<50%):       {low}")
        lines.append("")

        # Component averages
        component_names = ['instruments', 'wave_table', 'pulse_table', 'filter_table',
                          'orderlist', 'commands', 'tempo', 'arpeggio', 'notes']

        lines.append("Component Averages:")
        for comp_name in component_names:
            scores = [d['components'].get(comp_name, {}).get('score', 0) for d in all_data]
            if scores:
                avg = sum(scores) / len(scores)
                display_name = comp_name.replace('_', ' ').title()
                lines.append(f"  {display_name:<15}: {avg:.1f}%")
        lines.append("")

    # Files with issues
    files_with_notes = [d for d in all_data if d.get('notes')]
    if files_with_notes:
        lines.extend([
            "=" * 70,
            "Files with Issues",
            "=" * 70,
            "",
        ])

        for data in files_with_notes:
            lines.append(f"{data['filename']}:")
            for note in data['notes'][:3]:  # Show first 3 notes
                lines.append(f"  - {note}")
            if len(data['notes']) > 3:
                lines.append(f"  - ... and {len(data['notes']) - 3} more")
            lines.append("")

    # Detailed component breakdown
    lines.extend([
        "=" * 70,
        "Detailed Component Scores",
        "=" * 70,
        "",
    ])

    # Second header with more components
    lines.append(f"{'File':<20} {'Cmd':>6} {'Tempo':>6} {'Arp':>6} {'Notes':>6}")
    lines.append("-" * 44)

    for data in all_data_sorted:
        filename = data['filename'][:19]
        cmd = data['components'].get('commands', {}).get('score', 0)
        tempo = data['components'].get('tempo', {}).get('score', 0)
        arp = data['components'].get('arpeggio', {}).get('score', 0)
        notes = data['components'].get('notes', {}).get('score', 0)

        lines.append(f"{filename:<20} {cmd:>5.1f}% {tempo:>5.1f}% {arp:>5.1f}% {notes:>5.1f}%")

    # Footer
    lines.extend([
        "",
        "=" * 70,
        f"End of report",
        "=" * 70,
    ])

    report = "\n".join(lines)

    # Write to file if specified
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"Overview written to: {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Generate confidence score overview from all _info.txt files"
    )
    parser.add_argument(
        "--sf2-dir",
        default="SF2",
        help="Directory containing _info.txt files (default: SF2)"
    )
    parser.add_argument(
        "--output", "-o",
        default="SF2/confidence_overview.txt",
        help="Output file path (default: SF2/confidence_overview.txt)"
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print report to console"
    )

    args = parser.parse_args()

    report = generate_overview(args.sf2_dir, args.output)

    if args.print:
        print(report)


if __name__ == "__main__":
    main()
