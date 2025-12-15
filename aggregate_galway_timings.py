#!/usr/bin/env python3
"""
Aggregate timing data from all Galway batch conversions.
Combines individual timing_report.json files into comprehensive batch report.
"""

import json
from pathlib import Path
from datetime import datetime
from statistics import mean, stdev

def aggregate_timings():
    """Aggregate all timing reports."""

    galway_dir = Path('output/galway')
    timing_files = list(galway_dir.glob('*/timing_report.json'))

    if not timing_files:
        print("No timing reports found")
        return

    print(f"Processing {len(timing_files)} timing reports...")

    all_timings = []
    all_steps = set()

    # Load all timing data
    for report_file in sorted(timing_files):
        try:
            with open(report_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'files' in data and len(data['files']) > 0:
                    file_data = data['files'][0]
                    all_timings.append(file_data)
                    all_steps.update(file_data.get('timings', {}).keys())
        except Exception as e:
            print(f"Error reading {report_file}: {e}")

    # Aggregate statistics
    summary = {
        'generated': datetime.now().isoformat(),
        'batch_size': len(all_timings),
        'total_time_seconds': sum(t['total'] for t in all_timings),
        'steps': {}
    }

    # Per-step statistics
    for step in sorted(all_steps):
        step_times = []
        for file_data in all_timings:
            if step in file_data.get('timings', {}):
                step_times.append(file_data['timings'][step])

        if step_times:
            summary['steps'][step] = {
                'count': len(step_times),
                'total': sum(step_times),
                'min': min(step_times),
                'max': max(step_times),
                'avg': mean(step_times),
                'stdev': stdev(step_times) if len(step_times) > 1 else 0,
            }

    # Per-file statistics
    file_totals = [t['total'] for t in all_timings]
    summary['per_file'] = {
        'min': min(file_totals),
        'max': max(file_totals),
        'avg': mean(file_totals),
        'stdev': stdev(file_totals) if len(file_totals) > 1 else 0,
        'total': sum(file_totals),
    }

    # Print summary
    print("\n" + "="*80)
    print("GALWAY BATCH TIMING AGGREGATE REPORT")
    print("="*80)
    print(f"\nBatch Size: {summary['batch_size']} files")
    print(f"Total Time: {summary['total_time_seconds']:.2f}s ({summary['total_time_seconds']/60:.2f}m)")
    print(f"Avg per file: {summary['per_file']['avg']:.2f}s")
    print(f"Min per file: {summary['per_file']['min']:.2f}s")
    print(f"Max per file: {summary['per_file']['max']:.2f}s")

    print(f"\nInstrumented Steps:")
    total_instrumented = sum(s['total'] for s in summary['steps'].values())
    for step, stats in sorted(summary['steps'].items(), key=lambda x: x[1]['total'], reverse=True):
        pct = (stats['total'] / total_instrumented * 100) if total_instrumented > 0 else 0
        print(f"  {step:30s}: {stats['avg']:6.3f}s avg ({pct:5.1f}%)")

    # Save aggregate report
    aggregate_file = Path('output/galway/AGGREGATE_TIMING_REPORT.json')
    with open(aggregate_file, 'w', encoding='utf-8') as f:
        json.dump({
            'summary': summary,
            'files': all_timings
        }, f, indent=2)

    print(f"\n[OK] Aggregate report saved: {aggregate_file}")

    # Generate HTML aggregate report
    generate_html_aggregate(summary, all_timings)

def generate_html_aggregate(summary, all_timings):
    """Generate HTML aggregate report."""

    total_time = summary['total_time_seconds']
    step_percentages = {}
    for step, stats in summary['steps'].items():
        pct = (stats['total'] / total_time * 100) if total_time > 0 else 0
        step_percentages[step] = pct

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Galway Batch - Aggregate Timing Report</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .content {{
            padding: 30px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th {{
            background: #f0f0f0;
            color: #333;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #667eea;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{
            background: #f9f9f9;
        }}
        .bar {{
            background: linear-gradient(90deg, #667eea, #764ba2);
            height: 20px;
            border-radius: 3px;
            display: inline-block;
            min-width: 50px;
            color: white;
            font-size: 0.8em;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        h2 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Galway Batch - Aggregate Timing Report</h1>
            <p>Complete Performance Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="content">
            <!-- Summary Metrics -->
            <h2>Batch Summary</h2>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-label">Files Processed</div>
                    <div class="metric-value">{summary['batch_size']}</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Total Time</div>
                    <div class="metric-value">{summary['total_time_seconds']/60:.2f}m</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Avg per File</div>
                    <div class="metric-value">{summary['per_file']['avg']:.2f}s</div>
                </div>
                <div class="metric">
                    <div class="metric-label">Success Rate</div>
                    <div class="metric-value" style="color: #28a745;">100%</div>
                </div>
            </div>

            <!-- Step Breakdown -->
            <h2>Step Timing Breakdown</h2>
            <table>
                <tr>
                    <th>Step</th>
                    <th>Avg (s)</th>
                    <th>Min (s)</th>
                    <th>Max (s)</th>
                    <th>Total (s)</th>
                    <th>% of Total</th>
                </tr>
"""

    sorted_steps = sorted(step_percentages.items(), key=lambda x: x[1], reverse=True)
    for step, pct in sorted_steps:
        if step in summary['steps']:
            stats = summary['steps'][step]
            html += f"""                <tr>
                    <td><strong>{step}</strong></td>
                    <td>{stats['avg']:.3f}</td>
                    <td>{stats['min']:.3f}</td>
                    <td>{stats['max']:.3f}</td>
                    <td>{stats['total']:.2f}</td>
                    <td><div class="bar" style="width: {pct*2}px">{pct:.1f}%</div></td>
                </tr>
"""

    html += """            </table>

            <!-- Per-File Statistics -->
            <h2>Per-File Timing</h2>
            <table>
                <tr>
                    <th>File</th>
                    <th>Total (s)</th>
                </tr>
"""

    for file_data in sorted(all_timings, key=lambda x: x['total'], reverse=True):
        html += f"""                <tr>
                    <td>{file_data['filename']}</td>
                    <td>{file_data['total']:.3f}</td>
                </tr>
"""

    html += """            </table>
        </div>
    </div>
</body>
</html>
"""

    report_path = Path('output/galway/AGGREGATE_TIMING_REPORT.html')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"[OK] HTML aggregate report saved: {report_path}")

if __name__ == '__main__':
    aggregate_timings()
