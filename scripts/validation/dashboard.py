"""Dashboard HTML generation for validation results."""

from typing import Dict, List, Any
from datetime import datetime


class DashboardGenerator:
    """Generates HTML dashboard from validation data."""

    def generate_html(self, run_info: Dict[str, Any],
                     results: List[Dict[str, Any]],
                     aggregate: Dict[str, float],
                     trend_data: Dict[str, List] = None) -> str:
        """Generate complete HTML dashboard.

        Args:
            run_info: Validation run information
            results: List of file results
            aggregate: Aggregate metrics
            trend_data: Optional trend data for charts

        Returns:
            Complete HTML document string
        """
        html_parts = []

        # HTML header
        html_parts.append(self._generate_header())

        # Overview section
        html_parts.append(self._generate_overview(run_info, aggregate))

        # Trend charts (if data available)
        if trend_data:
            html_parts.append(self._generate_trend_section(trend_data))

        # File results table
        html_parts.append(self._generate_results_table(results))

        # HTML footer
        html_parts.append(self._generate_footer())

        return '\n'.join(html_parts)

    def _generate_header(self) -> str:
        """Generate HTML header with styles and scripts."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SIDM2 Validation Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            color: #333;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        h1 {
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 2.5em;
        }

        h2 {
            color: #34495e;
            margin-top: 30px;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
        }

        .run-info {
            background: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            font-size: 0.9em;
        }

        .run-info strong {
            color: #2c3e50;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .metric-card.success {
            background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%);
        }

        .metric-card.warning {
            background: linear-gradient(135deg, #f09819 0%, #edde5d 100%);
        }

        .metric-card.error {
            background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        }

        .metric-label {
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 5px;
        }

        .metric-value {
            font-size: 2.5em;
            font-weight: bold;
        }

        .chart-container {
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }

        canvas {
            max-height: 400px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.9em;
        }

        thead {
            background: #34495e;
            color: white;
        }

        th {
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }

        td {
            padding: 10px 12px;
            border-bottom: 1px solid #ecf0f1;
        }

        tbody tr:hover {
            background: #f8f9fa;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .status-pass {
            background: #d4edda;
            color: #155724;
        }

        .status-fail {
            background: #f8d7da;
            color: #721c24;
        }

        .accuracy-bar {
            display: inline-block;
            width: 100px;
            height: 20px;
            background: #ecf0f1;
            border-radius: 10px;
            overflow: hidden;
            position: relative;
        }

        .accuracy-fill {
            height: 100%;
            background: linear-gradient(90deg, #e74c3c 0%, #f39c12 50%, #2ecc71 100%);
            transition: width 0.3s ease;
        }

        .accuracy-text {
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            text-align: center;
            line-height: 20px;
            font-size: 0.75em;
            font-weight: bold;
            color: #2c3e50;
        }

        .step-indicator {
            display: inline-block;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            text-align: center;
            line-height: 20px;
            font-size: 0.7em;
            font-weight: bold;
        }

        .step-pass {
            background: #2ecc71;
            color: white;
        }

        .step-fail {
            background: #e74c3c;
            color: white;
        }

        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.85em;
        }
    </style>
</head>
<body>
    <div class="container">'''

    def _generate_overview(self, run_info: Dict[str, Any],
                          aggregate: Dict[str, float]) -> str:
        """Generate overview section with metrics cards."""
        timestamp = run_info.get('timestamp', 'Unknown')
        git_commit = run_info.get('git_commit', 'Unknown')
        pipeline_version = run_info.get('pipeline_version', 'Unknown')

        total = aggregate.get('total_files', 0)
        pass_rate = aggregate.get('pass_rate', 0) * 100
        avg_accuracy = aggregate.get('avg_overall_accuracy') or 0

        # Determine metric card classes
        pass_class = 'success' if pass_rate >= 90 else 'warning' if pass_rate >= 70 else 'error'
        acc_class = 'success' if avg_accuracy >= 80 else 'warning' if avg_accuracy >= 60 else 'error'

        html = f'''
        <h1>SIDM2 Validation Dashboard</h1>

        <div class="run-info">
            <strong>Run:</strong> {timestamp} |
            <strong>Commit:</strong> {git_commit} |
            <strong>Version:</strong> {pipeline_version}
        </div>

        <h2>Overall Metrics</h2>
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Files Tested</div>
                <div class="metric-value">{total}</div>
            </div>

            <div class="metric-card {pass_class}">
                <div class="metric-label">Pass Rate</div>
                <div class="metric-value">{pass_rate:.1f}%</div>
            </div>

            <div class="metric-card {acc_class}">
                <div class="metric-label">Avg Accuracy</div>
                <div class="metric-value">{avg_accuracy:.1f}%</div>
            </div>

            <div class="metric-card">
                <div class="metric-label">File Size</div>
                <div class="metric-value">{aggregate.get('avg_file_size_efficiency', 0) * 100:.0f}%</div>
            </div>
        </div>'''

        return html

    def _generate_trend_section(self, trend_data: Dict[str, List]) -> str:
        """Generate trend charts section."""
        html = '''
        <h2>Trends</h2>
        <div class="chart-container">
            <canvas id="accuracyTrendChart"></canvas>
        </div>

        <script>
            const ctx = document.getElementById('accuracyTrendChart').getContext('2d');
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ''' + str([d['timestamp'][:10] for d in trend_data.get('accuracy', [])]) + ''',
                    datasets: [{
                        label: 'Average Accuracy (%)',
                        data: ''' + str([d['metric_value'] for d in trend_data.get('accuracy', [])]) + ''',
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        </script>'''

        return html

    def _generate_results_table(self, results: List[Dict[str, Any]]) -> str:
        """Generate file results table."""
        html = '''
        <h2>File Results</h2>
        <table>
            <thead>
                <tr>
                    <th>File</th>
                    <th>Method</th>
                    <th>Accuracy</th>
                    <th>Steps</th>
                    <th>Size (bytes)</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>'''

        for result in sorted(results, key=lambda r: r.get('filename', '')):
            filename = result.get('filename', 'Unknown')
            method = result.get('conversion_method', 'N/A')
            accuracy = result.get('overall_accuracy') or 0
            exported_size = result.get('exported_size') or 0

            # Calculate steps passed
            steps_passed = sum([
                result.get('step1_conversion', False),
                result.get('step2_packing', False),
                result.get('step3_siddump', False),
                result.get('step4_wav', False),
                result.get('step5_hexdump', False),
                result.get('step6_trace', False),
                result.get('step7_info', False),
                result.get('step8_disasm_python', False),
                result.get('step9_disasm_sidwinder', False),
            ])

            status = 'PASS' if result.get('conversion_success', False) else 'FAIL'
            status_class = 'status-pass' if status == 'PASS' else 'status-fail'

            html += f'''
                <tr>
                    <td><strong>{filename}</strong></td>
                    <td>{method}</td>
                    <td>
                        <div class="accuracy-bar">
                            <div class="accuracy-fill" style="width: {accuracy}%"></div>
                            <div class="accuracy-text">{accuracy:.1f}%</div>
                        </div>
                    </td>
                    <td>{steps_passed}/9</td>
                    <td>{exported_size:,}</td>
                    <td><span class="status-badge {status_class}">{status}</span></td>
                </tr>'''

        html += '''
            </tbody>
        </table>'''

        return html

    def _generate_footer(self) -> str:
        """Generate HTML footer."""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return f'''
        <div class="footer">
            Generated by SIDM2 Validation System | {now}
        </div>
    </div>
</body>
</html>'''
