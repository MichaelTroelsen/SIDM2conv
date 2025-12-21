#!/usr/bin/env python3
"""
Pipeline with detailed timing analysis for each step.

Tracks execution time for all pipeline steps and generates HTML reports
showing timing breakdown to identify bottlenecks.

Usage:
    python pipeline_with_timings.py input.sid output_dir/
"""

import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime
import json


class PipelineTimer:
    """Track timing for pipeline steps."""

    def __init__(self, output_dir):
        self.output_dir = Path(output_dir)
        self.steps = {}
        self.start_time = time.time()

    def start_step(self, step_name):
        """Start timing a step."""
        self.steps[step_name] = {
            'name': step_name,
            'start': time.time(),
            'end': None,
            'duration': None,
            'status': 'running'
        }

    def end_step(self, step_name, status='success'):
        """End timing a step."""
        if step_name in self.steps:
            end_time = time.time()
            self.steps[step_name]['end'] = end_time
            self.steps[step_name]['duration'] = end_time - self.steps[step_name]['start']
            self.steps[step_name]['status'] = status

    def get_summary(self):
        """Get timing summary."""
        total = sum(s['duration'] for s in self.steps.values() if s['duration'])
        return {
            'total_duration': time.time() - self.start_time,
            'pipeline_duration': total,
            'steps': sorted(
                [(s['name'], s['duration']) for s in self.steps.values() if s['duration']],
                key=lambda x: x[1],
                reverse=True
            )
        }

    def generate_html_report(self, filename):
        """Generate HTML report of timings."""
        summary = self.get_summary()

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Pipeline Timing Analysis</title>
    <style>
        body {{ font-family: monospace; margin: 20px; background: #f5f5f5; }}
        h1 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; background: white; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background: #4CAF50; color: white; }}
        tr:hover {{ background: #f9f9f9; }}
        .duration {{ text-align: right; font-weight: bold; }}
        .bar {{ background: #4CAF50; height: 20px; }}
        .percent {{ color: #666; }}
        .total {{ background: #e8f5e9; font-weight: bold; }}
        .bottleneck {{ background: #ffcccc; }}
    </style>
</head>
<body>
    <h1>Pipeline Timing Analysis</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

    <h2>Summary</h2>
    <table>
        <tr class="total">
            <td>Total Pipeline Time</td>
            <td class="duration">{summary['total_duration']:.1f}s</td>
        </tr>
        <tr>
            <td>Measured Steps</td>
            <td class="duration">{summary['pipeline_duration']:.1f}s</td>
        </tr>
    </table>

    <h2>Steps (sorted by duration)</h2>
    <table>
        <tr>
            <th>Step</th>
            <th class="duration">Duration (s)</th>
            <th>Percentage</th>
            <th>Visualization</th>
        </tr>
"""

        max_duration = max((d for _, d in summary['steps']), default=1)

        for step_name, duration in summary['steps']:
            percent = 100 * duration / summary['pipeline_duration'] if summary['pipeline_duration'] > 0 else 0
            bar_width = int(percent * 3)  # Scale to ~300px max

            # Highlight bottlenecks (>30% of time)
            is_bottleneck = percent > 30
            row_class = 'bottleneck' if is_bottleneck else ''

            html += f"""
        <tr class="{row_class}">
            <td>{step_name}</td>
            <td class="duration">{duration:.1f}s</td>
            <td><span class="percent">{percent:.1f}%</span></td>
            <td><div class="bar" style="width: {bar_width}px;"></div></td>
        </tr>
"""

        html += """
    </table>

    <h2>Optimization Recommendations</h2>
    <ul>
"""

        # Find top bottlenecks
        for step_name, duration in summary['steps'][:3]:
            percent = 100 * duration / summary['pipeline_duration']
            if percent > 20:
                if 'WAV' in step_name:
                    html += f"<li><strong>{step_name}</strong> ({percent:.0f}%): Consider using VICE rendering in background or skip for faster processing</li>"
                elif 'MIDI' in step_name or 'EMULATOR' in step_name:
                    html += f"<li><strong>{step_name}</strong> ({percent:.0f}%): Consider skipping or optimizing emulation step</li>"
                elif 'DISASSEMBLY' in step_name or 'ANALYSIS' in step_name:
                    html += f"<li><strong>{step_name}</strong> ({percent:.0f}%): Consider running in background or using simplified analysis</li>"
                else:
                    html += f"<li><strong>{step_name}</strong> ({percent:.0f}%): Review for optimization opportunities</li>"

        html += """
    </ul>

    <h2>Raw Data (JSON)</h2>
    <pre>
"""

        json_data = {
            'timestamp': datetime.now().isoformat(),
            'total_duration': summary['total_duration'],
            'pipeline_duration': summary['pipeline_duration'],
            'steps': [{'name': n, 'duration_s': d} for n, d in summary['steps']]
        }

        html += json.dumps(json_data, indent=2)
        html += """
    </pre>
</body>
</html>
"""

        with open(filename, 'w') as f:
            f.write(html)


def run_timed_pipeline_step(name, command, timeout=300):
    """Run a command and time it."""
    start = time.time()
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True
        )
        duration = time.time() - start
        success = result.returncode == 0
        return duration, success, result.stderr if not success else ""
    except subprocess.TimeoutExpired:
        return time.time() - start, False, "Timeout"
    except Exception as e:
        return time.time() - start, False, str(e)


# Example usage showing how to integrate into pipeline
if __name__ == '__main__':
    # Create timer
    timer = PipelineTimer('/tmp')

    # Simulate pipeline steps
    steps = [
        ('SID → SF2 Conversion', 1.2),
        ('Siddump Original', 15.0),
        ('Siddump Exported', 15.0),
        ('WAV Rendering', 60.0),  # This is the bottleneck!
        ('Disassembly', 20.0),
        ('SIDwinder Analysis', 10.0),
        ('MIDI Comparison', 15.0),
    ]

    for step_name, duration in steps:
        timer.start_step(step_name)
        time.sleep(duration / 100)  # Simulate work
        timer.end_step(step_name)

    # Generate report
    timer.generate_html_report('/tmp/pipeline_timing.html')
    print(f"Timing report generated: /tmp/pipeline_timing.html")

    # Print summary
    summary = timer.get_summary()
    print(f"\nTotal time: {summary['total_duration']:.1f}s")
    print("\nTop bottlenecks:")
    for step, duration in summary['steps'][:3]:
        percent = 100 * duration / summary['pipeline_duration']
        print(f"  {step:30} {duration:6.1f}s ({percent:5.1f}%)")
