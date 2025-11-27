#!/usr/bin/env python3
"""
Generate overview summary of all SID conversions.

Scans the output directory and creates an HTML summary file with:
- Overall conversion statistics
- Confidence scores for each SID file
- Status indicators and color coding
- Links to individual info files

Usage:
    python generate_overview.py [output_dir]
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from validate_psid import PSIDValidator
from sidm2 import get_logger

logger = get_logger(__name__)


def parse_info_file(info_file: Path) -> Optional[Dict]:
    """Extract confidence score, status, and driver info from info file.

    Returns:
        Dict with score, status, original_driver, or None if not found
    """
    try:
        with open(info_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Look for "Overall Score: XX.X%"
        score_match = re.search(r'Overall Score:\s*([\d.]+)%', content)
        if not score_match:
            return None

        score = float(score_match.group(1))

        # Determine status based on score
        if score >= 90:
            status = "Excellent"
        elif score >= 75:
            status = "Good"
        elif score >= 60:
            status = "Fair"
        else:
            status = "Poor"

        # Extract original player/driver
        player_match = re.search(r'Player:\s+(.+)', content)
        original_driver = player_match.group(1).strip() if player_match else "Unknown"

        return {
            'score': score,
            'status': status,
            'original_driver': original_driver
        }
    except Exception as e:
        logger.error(f"Error parsing {info_file}: {e}")
        return None


def scan_output_directory(output_dir: Path) -> List[Dict]:
    """Scan output directory for all converted SID files.

    Returns:
        List of dicts with song info and confidence scores
    """
    results = []

    if not output_dir.exists():
        return results

    # Find all song directories
    for song_dir in sorted(output_dir.iterdir()):
        if not song_dir.is_dir():
            continue

        song_name = song_dir.name
        new_dir = song_dir / "New"
        original_dir = song_dir / "Original"

        if not new_dir.exists():
            continue

        # Look for info file
        info_file = new_dir / f"{song_name}_info.txt"
        if not info_file.exists():
            continue

        # Check for SF2 files
        g4_file = new_dir / f"{song_name}_g4.sf2"
        d11_file = new_dir / f"{song_name}_d11.sf2"

        g4_exists = g4_file.exists()
        d11_exists = d11_file.exists()

        # Get file sizes
        g4_size = g4_file.stat().st_size if g4_exists else 0
        d11_size = d11_file.stat().st_size if d11_exists else 0

        # Check for SID files
        original_sid = original_dir / f"{song_name}.sid" if original_dir.exists() else None
        exported_sid = new_dir / f"{song_name}_exported.sid"

        # Validate exported SID if it exists
        psid_status = "N/A"
        if exported_sid.exists():
            try:
                validator = PSIDValidator(exported_sid)
                is_valid = validator.validate()
                if is_valid:
                    if validator.warnings:
                        psid_status = f"Valid ({len(validator.warnings)}w)"
                    else:
                        psid_status = "Valid"
                else:
                    psid_status = f"Invalid ({len(validator.errors)}e)"
            except Exception as e:
                psid_status = "Error"

        # Parse info file for confidence and driver info
        info_data = parse_info_file(info_file)

        results.append({
            'name': song_name,
            'info_file': info_file,
            'g4_exists': g4_exists,
            'd11_exists': d11_exists,
            'g4_size': g4_size,
            'd11_size': d11_size,
            'original_sid': original_sid,
            'exported_sid': exported_sid,
            'psid_status': psid_status,
            'confidence': info_data['score'] if info_data else 0.0,
            'status': info_data['status'] if info_data else "Unknown",
            'original_driver': info_data['original_driver'] if info_data else "Unknown"
        })

    return results


def generate_html_overview(results: List[Dict], output_file: Path):
    """Generate HTML overview file with all conversion results."""

    # Calculate statistics
    total_conversions = len(results)
    successful = len([r for r in results if r['g4_exists'] and r['d11_exists']])
    avg_confidence = sum(r['confidence'] for r in results) / len(results) if results else 0.0

    status_counts = {}
    for r in results:
        status = r['status']
        status_counts[status] = status_counts.get(status, 0) + 1

    # Generate HTML
    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SID to SF2 Conversion Overview</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-value {{
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stat-label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 30px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .confidence {{
            font-weight: bold;
            font-size: 18px;
        }}
        .status-excellent {{
            color: #2e7d32;
            background-color: #c8e6c9;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 600;
        }}
        .status-good {{
            color: #1976d2;
            background-color: #bbdefb;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 600;
        }}
        .status-fair {{
            color: #f57c00;
            background-color: #ffe0b2;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 600;
        }}
        .status-poor {{
            color: #c62828;
            background-color: #ffcdd2;
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: 600;
        }}
        .file-size {{
            color: #666;
            font-size: 0.9em;
        }}
        a {{
            color: #1976d2;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .timestamp {{
            color: #999;
            font-size: 0.9em;
            margin-top: 30px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>SID to SF2 Conversion Overview</h1>

        <div class="stats">
            <div class="stat-box">
                <div class="stat-value">{total_conversions}</div>
                <div class="stat-label">Total Conversions</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{successful}</div>
                <div class="stat-label">Successful</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{avg_confidence:.1f}%</div>
                <div class="stat-label">Average Confidence</div>
            </div>
        </div>

        <h2>Conversion Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Song Name</th>
                    <th>Confidence</th>
                    <th>Status</th>
                    <th>Original Driver</th>
                    <th>New Driver</th>
                    <th>Original SID</th>
                    <th>Exported SID</th>
                    <th>PSID</th>
                    <th>Info</th>
                </tr>
            </thead>
            <tbody>
'''

    # Sort by confidence score (descending)
    sorted_results = sorted(results, key=lambda x: x['confidence'], reverse=True)

    for r in sorted_results:
        status_class = f"status-{r['status'].lower()}"

        # Build links for SID files
        if r['original_sid'] and r['original_sid'].exists():
            orig_sid_size = r['original_sid'].stat().st_size
            orig_sid_link = f"{r['name']}/Original/{r['name']}.sid"
            orig_sid_str = f'<a href="{orig_sid_link}">{orig_sid_size:,} bytes</a>'
        else:
            orig_sid_str = "—"

        if r['exported_sid'].exists():
            exp_sid_size = r['exported_sid'].stat().st_size
            exp_sid_link = f"{r['name']}/New/{r['name']}_exported.sid"
            exp_sid_str = f'<a href="{exp_sid_link}">{exp_sid_size:,} bytes</a>'
        else:
            exp_sid_str = "—"

        # PSID status with color coding
        psid_status = r['psid_status']
        if "Valid" in psid_status and "w)" in psid_status:
            psid_class = "file-size"  # Gray for valid with warnings
            psid_display = psid_status
        elif psid_status == "Valid":
            psid_class = "status-excellent"
            psid_display = "Valid"
        elif "Invalid" in psid_status:
            psid_class = "status-poor"
            psid_display = psid_status
        else:
            psid_class = "file-size"
            psid_display = psid_status

        # Relative path to info file
        info_link = f"{r['name']}/New/{r['name']}_info.txt"

        # Format driver names
        orig_driver = r['original_driver'].replace('_', ' ')
        new_driver = "Driver 11 + NP20"  # Both drivers are exported

        html += f'''                <tr>
                    <td><strong>{r['name']}</strong></td>
                    <td class="confidence">{r['confidence']:.1f}%</td>
                    <td><span class="{status_class}">{r['status']}</span></td>
                    <td class="file-size">{orig_driver}</td>
                    <td class="file-size">{new_driver}</td>
                    <td class="file-size">{orig_sid_str}</td>
                    <td class="file-size">{exp_sid_str}</td>
                    <td><span class="{psid_class}">{psid_display}</span></td>
                    <td><a href="{info_link}">View Details</a></td>
                </tr>
'''

    html += f'''            </tbody>
        </table>

        <div class="timestamp">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
'''

    # Write HTML file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    logger.info(f"Generated overview: {output_file}")


def main():
    """Main entry point."""
    output_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('output')

    if not output_dir.exists():
        logger.error(f"Error: Output directory '{output_dir}' does not exist")
        sys.exit(1)

    logger.info(f"Scanning {output_dir}...")
    results = scan_output_directory(output_dir)

    if not results:
        logger.warning("No conversions found in output directory")
        sys.exit(1)

    logger.info(f"Found {len(results)} converted SID files")

    overview_file = output_dir / "conversion_summary.html"
    generate_html_overview(results, overview_file)

    # Print summary to console
    logger.info("\nConversion Summary:")
    logger.info("=" * 60)
    for r in sorted(results, key=lambda x: x['confidence'], reverse=True):
        logger.info(f"{r['name']:30s} {r['confidence']:5.1f}% {r['status']}")


if __name__ == '__main__':
    main()
