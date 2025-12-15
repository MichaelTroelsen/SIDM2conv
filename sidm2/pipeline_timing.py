"""
Pipeline timing instrumentation and reporting.

Tracks per-step execution times and generates comprehensive timing reports.
"""

import json
import time
from pathlib import Path
from datetime import datetime
from statistics import mean, stdev


class PipelineTimer:
    """Context manager for timing pipeline steps."""

    def __init__(self, step_name, result_dict=None):
        self.step_name = step_name
        self.result_dict = result_dict or {}
        self.start_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self.start_time
        if self.result_dict is not None:
            if 'timings' not in self.result_dict:
                self.result_dict['timings'] = {}
            self.result_dict['timings'][self.step_name] = self.elapsed


class TimingAnalyzer:
    """Analyzes timing data from pipeline results."""

    def __init__(self, results):
        self.results = results

    def get_step_times(self, step_name):
        """Get all times for a specific step across all files."""
        times = []
        for result in self.results:
            if 'timings' in result and step_name in result['timings']:
                times.append(result['timings'][step_name])
        return times

    def analyze_step(self, step_name):
        """Analyze timing statistics for a step."""
        times = self.get_step_times(step_name)
        if not times:
            return None

        return {
            'count': len(times),
            'total': sum(times),
            'min': min(times),
            'max': max(times),
            'avg': mean(times),
            'stdev': stdev(times) if len(times) > 1 else 0,
        }

    def get_file_total_time(self, result):
        """Get total time for a file."""
        if 'timings' in result:
            return sum(result['timings'].values())
        return 0

    def get_all_total_times(self):
        """Get total times for all files."""
        return [self.get_file_total_time(r) for r in self.results]

    def generate_summary(self):
        """Generate timing summary statistics."""
        all_steps = set()
        for result in self.results:
            if 'timings' in result:
                all_steps.update(result['timings'].keys())

        summary = {
            'files_processed': len(self.results),
            'total_pipeline_time': sum(self.get_all_total_times()),
            'steps': {}
        }

        for step in sorted(all_steps):
            analysis = self.analyze_step(step)
            if analysis:
                summary['steps'][step] = analysis

        file_times = self.get_all_total_times()
        if file_times:
            summary['per_file_stats'] = {
                'min': min(file_times),
                'max': max(file_times),
                'avg': mean(file_times),
                'total': sum(file_times),
            }

        return summary


def generate_timing_report_html(results, output_base, summary):
    """Generate HTML timing report."""

    # Calculate time contribution percentages
    total_time = summary['total_pipeline_time']
    step_percentages = {}
    for step, stats in summary['steps'].items():
        percentage = (stats['total'] / total_time * 100) if total_time > 0 else 0
        step_percentages[step] = percentage

    # Sort by contribution
    sorted_steps = sorted(step_percentages.items(), key=lambda x: x[1], reverse=True)

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Pipeline Timing Report</title>
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
        .header p {{
            margin: 10px 0 0 0;
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
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
            margin-right: 10px;
            min-width: 50px;
            color: white;
            font-size: 0.8em;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .footer {{
            background: #f5f5f5;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #eee;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Pipeline Timing Report</h1>
            <p>Performance Analysis - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>

        <div class="content">
            <!-- Summary Section -->
            <div class="section">
                <h2>Summary</h2>
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-label">Files Processed</div>
                        <div class="metric-value">{summary['files_processed']}</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Total Time</div>
                        <div class="metric-value">{summary['total_pipeline_time']/60:.1f}m</div>
                    </div>
                    <div class="metric">
                        <div class="metric-label">Avg per File</div>
                        <div class="metric-value">{summary['per_file_stats']['avg']:.1f}s</div>
                    </div>
                </div>
            </div>

            <!-- Per-Step Analysis -->
            <div class="section">
                <h2>Step Timing Breakdown</h2>
                <table>
                    <tr>
                        <th>Step</th>
                        <th>Avg Time (s)</th>
                        <th>Min (s)</th>
                        <th>Max (s)</th>
                        <th>Total (s)</th>
                        <th>% of Total</th>
                    </tr>
"""

    for step, percentage in sorted_steps:
        if step in summary['steps']:
            stats = summary['steps'][step]
            html += f"""                    <tr>
                        <td><strong>{step}</strong></td>
                        <td>{stats['avg']:.2f}</td>
                        <td>{stats['min']:.2f}</td>
                        <td>{stats['max']:.2f}</td>
                        <td>{stats['total']:.2f}</td>
                        <td>
                            <div class="bar" style="width: {percentage*2}px">{percentage:.1f}%</div>
                        </td>
                    </tr>
"""

    html += """                </table>
            </div>

            <!-- File-by-File Details -->
            <div class="section">
                <h2>File-by-File Timing</h2>
                <table>
                    <tr>
                        <th>File</th>
                        <th>Total Time (s)</th>
                        <th>Status</th>
                    </tr>
"""

    for result in results:
        total_time = sum(result.get('timings', {}).values())
        filename = result.get('filename', 'Unknown')
        complete = result.get('validation', {}).get('complete', False)
        status = '[OK]' if complete else '[PARTIAL]'
        html += f"""                    <tr>
                        <td>{filename}</td>
                        <td>{total_time:.2f}</td>
                        <td>{status}</td>
                    </tr>
"""

    html += """                </table>
            </div>
        </div>

        <div class="footer">
            <p>Generated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</p>
            <p>Output Directory: """ + str(output_base) + """</p>
        </div>
    </div>
</body>
</html>
"""

    report_path = Path(output_base) / 'TIMING_REPORT.html'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return report_path


def generate_timing_report_json(results, output_base, summary):
    """Generate JSON timing report for CI/CD integration."""

    report_path = Path(output_base) / 'timing_report.json'
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'generated': datetime.now().isoformat(),
            'summary': summary,
            'files': [
                {
                    'filename': r.get('filename'),
                    'timings': r.get('timings', {}),
                    'total': sum(r.get('timings', {}).values()),
                    'complete': r.get('validation', {}).get('complete', False),
                }
                for r in results
            ]
        }, f, indent=2)

    return report_path


def generate_timing_reports(results, output_base):
    """Generate all timing reports."""

    analyzer = TimingAnalyzer(results)
    summary = analyzer.generate_summary()

    # Generate HTML report
    html_report = generate_timing_report_html(results, output_base, summary)
    print(f'[OK] HTML timing report: {html_report}')

    # Generate JSON report for CI/CD
    json_report = generate_timing_report_json(results, output_base, summary)
    print(f'[OK] JSON timing report: {json_report}')

    return {
        'html': html_report,
        'json': json_report,
        'summary': summary,
    }
