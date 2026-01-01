"""Improved Dashboard HTML generation using HTMLComponents library."""

from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
import sys

# Add pyscript to path for HTMLComponents
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'pyscript'))

from html_components import (
    HTMLComponents, StatCard, NavItem, StatCardType, ColorScheme
)


class DashboardGeneratorV2:
    """Generates improved HTML dashboard from validation data using HTMLComponents."""

    def generate_html(self, run_info: Dict[str, Any],
                     results: List[Dict[str, Any]],
                     aggregate: Dict[str, float],
                     trend_data: Dict[str, List] = None) -> str:
        """Generate complete HTML dashboard with HTMLComponents.

        Args:
            run_info: Validation run information
            results: List of file results
            aggregate: Aggregate metrics
            trend_data: Optional trend data for charts

        Returns:
            Complete HTML document string
        """
        html = HTMLComponents.get_document_header(
            title="SIDM2 Validation Dashboard",
            include_chartjs=True
        )

        html += '<div class="container">'

        # Sidebar
        html += self._create_sidebar(run_info, aggregate, len(results))

        # Main content
        html += '<div class="main-content">'
        html += self._create_header(run_info)
        html += self._create_stats_grid(aggregate)

        # Search box
        html += HTMLComponents.create_search_box(
            "Search files, statuses, or accuracy...",
            ".results-table tbody tr"
        )

        # Trend section (if data available)
        if trend_data:
            html += self._create_trend_section(trend_data)

        # Results table
        html += self._create_results_section(results)

        # Footer
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html += HTMLComponents.create_footer("3.0.1", timestamp)
        html += '</div>'  # main-content

        html += '</div>'  # container

        html += self._add_custom_javascript()
        html += HTMLComponents.get_document_footer()

        return html

    def _create_sidebar(self, run_info: Dict[str, Any], aggregate: Dict[str, float], total_files: int) -> str:
        """Create navigation sidebar"""
        nav_items = [
            NavItem("Overview", "overview"),
            NavItem("Statistics", "stats"),
            NavItem("Trends", "trends") if aggregate.get('total_files', 0) > 0 else None,
            NavItem("Results", "results", count=total_files)
        ]
        # Filter out None items
        nav_items = [item for item in nav_items if item is not None]

        # Sidebar stats
        pass_rate = aggregate.get('pass_rate', 0)
        avg_accuracy = aggregate.get('avg_overall_accuracy', 0)

        sidebar_stats = [
            StatCard("Pass Rate", f"{pass_rate:.1f}%",
                    StatCardType.SUCCESS if pass_rate >= 90 else StatCardType.WARNING),
            StatCard("Avg Accuracy", f"{avg_accuracy:.1f}%",
                    StatCardType.SUCCESS if avg_accuracy >= 90 else StatCardType.WARNING)
        ]

        return HTMLComponents.create_sidebar(
            "Validation",
            nav_items,
            sidebar_stats
        )

    def _create_header(self, run_info: Dict[str, Any]) -> str:
        """Create dashboard header"""
        run_id = run_info.get('run_id', 'N/A')
        timestamp = run_info.get('timestamp', 'N/A')
        driver = run_info.get('driver', 'N/A')

        return f'''
        <div id="overview" class="header">
            <h1>Validation Dashboard</h1>
            <div class="subtitle">SIDM2 Accuracy Validation - Run #{run_id}</div>
        </div>

        <div class="run-info-section">
            <h3>Run Information</h3>
            <table class="info-table">
                <tr>
                    <td><strong>Run ID:</strong></td>
                    <td>{run_id}</td>
                </tr>
                <tr>
                    <td><strong>Timestamp:</strong></td>
                    <td>{timestamp}</td>
                </tr>
                <tr>
                    <td><strong>Driver:</strong></td>
                    <td>{driver}</td>
                </tr>
            </table>
        </div>
        '''

    def _create_stats_grid(self, aggregate: Dict[str, float]) -> str:
        """Create statistics grid"""
        total_files = int(aggregate.get('total_files', 0))
        passed = int(aggregate.get('passed_files', 0))
        failed = int(aggregate.get('failed_files', 0))
        pass_rate = aggregate.get('pass_rate', 0)
        avg_accuracy = aggregate.get('avg_overall_accuracy', 0)
        avg_step1 = aggregate.get('avg_step1_accuracy', 0)

        cards = [
            StatCard("Total Files", str(total_files), StatCardType.PRIMARY),
            StatCard("Passed", str(passed), StatCardType.SUCCESS),
            StatCard("Failed", str(failed), StatCardType.ERROR if failed > 0 else StatCardType.SUCCESS),
            StatCard("Pass Rate", f"{pass_rate:.1f}%",
                    StatCardType.SUCCESS if pass_rate >= 90 else StatCardType.WARNING),
            StatCard("Avg Accuracy", f"{avg_accuracy:.1f}%",
                    StatCardType.SUCCESS if avg_accuracy >= 90 else StatCardType.WARNING),
            StatCard("Step 1 Avg", f"{avg_step1:.1f}%",
                    StatCardType.SUCCESS if avg_step1 >= 90 else StatCardType.WARNING)
        ]

        return f'<div id="stats">{HTMLComponents.create_stat_grid(cards)}</div>'

    def _create_trend_section(self, trend_data: Dict[str, List]) -> str:
        """Create trend chart section"""
        accuracy_data = trend_data.get('accuracy', [])

        if not accuracy_data:
            return ''

        # Prepare data for Chart.js
        # Handle both list of tuples and list of dicts
        if isinstance(accuracy_data[0], dict):
            labels = [str(item.get('run_id', i)) for i, item in enumerate(accuracy_data)]
            values = [item.get('value', 0) for item in accuracy_data]
        else:
            labels = [str(item[0]) for item in accuracy_data]  # run_ids
            values = [item[1] for item in accuracy_data]  # accuracy values

        chart_html = f'''
        <div id="trends" class="section">
            <h2>Accuracy Trends</h2>
            <div class="chart-container">
                <canvas id="accuracyTrendChart"></canvas>
            </div>
            <script>
                const ctx = document.getElementById('accuracyTrendChart').getContext('2d');
                new Chart(ctx, {{
                    type: 'line',
                    data: {{
                        labels: {labels},
                        datasets: [{{
                            label: 'Average Accuracy',
                            data: {values},
                            borderColor: '{ColorScheme.ACCENT_TEAL}',
                            backgroundColor: '{ColorScheme.ACCENT_TEAL}33',
                            tension: 0.4,
                            fill: true
                        }}]
                    }},
                    options: {{
                        responsive: true,
                        maintainAspectRatio: true,
                        scales: {{
                            y: {{
                                beginAtZero: false,
                                min: 0,
                                max: 100,
                                ticks: {{
                                    callback: function(value) {{
                                        return value + '%';
                                    }}
                                }},
                                grid: {{
                                    color: '{ColorScheme.BG_SECONDARY}'
                                }}
                            }},
                            x: {{
                                grid: {{
                                    color: '{ColorScheme.BG_SECONDARY}'
                                }}
                            }}
                        }},
                        plugins: {{
                            legend: {{
                                display: true,
                                labels: {{
                                    color: '{ColorScheme.TEXT_PRIMARY}'
                                }}
                            }},
                            tooltip: {{
                                callbacks: {{
                                    label: function(context) {{
                                        return 'Accuracy: ' + context.parsed.y.toFixed(1) + '%';
                                    }}
                                }}
                            }}
                        }}
                    }}
                }});
            </script>
        </div>
        '''

        return chart_html

    def _create_results_section(self, results: List[Dict[str, Any]]) -> str:
        """Create results table section"""
        if not results:
            return '<p class="warning">No validation results found.</p>'

        # Sort by status (failed first) and then by accuracy
        sorted_results = sorted(
            results,
            key=lambda r: (
                0 if r.get('status') == 'FAIL' else 1,
                -(r.get('overall_accuracy') or 0)
            )
        )

        # Create table rows
        rows = []
        for result in sorted_results:
            filename = Path(result.get('filename', 'N/A')).name
            status = result.get('status', 'UNKNOWN')
            overall_acc = result.get('overall_accuracy') or 0
            step1_acc = result.get('step1_accuracy') or 0
            step2_acc = result.get('step2_accuracy') or 0
            step3_acc = result.get('step3_accuracy') or 0

            # Status badge
            if status == 'PASS':
                status_html = f'<span style="color: {ColorScheme.SUCCESS};">✓ PASS</span>'
            elif status == 'FAIL':
                status_html = f'<span style="color: {ColorScheme.ERROR};">✗ FAIL</span>'
            else:
                status_html = f'<span style="color: {ColorScheme.TEXT_SECONDARY};">○ {status}</span>'

            # Accuracy bar
            def accuracy_bar(acc):
                acc = acc or 0  # Handle None
                color = ColorScheme.SUCCESS if acc >= 90 else (ColorScheme.WARNING if acc >= 70 else ColorScheme.ERROR)
                return f'''
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="flex: 1; max-width: 100px; height: 20px; background: {ColorScheme.BG_TERTIARY}; border-radius: 10px; overflow: hidden;">
                        <div style="width: {acc}%; height: 100%; background: {color}; transition: width 0.3s;"></div>
                    </div>
                    <span style="min-width: 45px; text-align: right;">{acc:.1f}%</span>
                </div>
                '''

            rows.append([
                f'<code>{filename}</code>',
                status_html,
                accuracy_bar(overall_acc),
                accuracy_bar(step1_acc),
                accuracy_bar(step2_acc),
                accuracy_bar(step3_acc)
            ])

        table_html = HTMLComponents.create_table(
            headers=["File", "Status", "Overall", "Step 1", "Step 2", "Step 3"],
            rows=rows,
            table_class="results-table"
        )

        content = f'''
        <div id="results" class="section">
            <h2>Validation Results ({len(results)} files)</h2>
            <p class="subtitle">Failed files shown first, sorted by accuracy</p>
            {table_html}
        </div>
        '''

        return content

    def _add_custom_javascript(self) -> str:
        """Add custom JavaScript for enhanced search functionality"""
        return f'''
        <script>
            // Enhanced search that includes accuracy values
            const searchBox = document.querySelector('input[placeholder*="Search"]');
            if (searchBox) {{
                searchBox.addEventListener('input', function(e) {{
                    const searchTerm = e.target.value.toLowerCase();
                    const rows = document.querySelectorAll('.results-table tbody tr');

                    rows.forEach(row => {{
                        const text = row.textContent.toLowerCase();
                        // Also search by accuracy ranges
                        const cells = row.querySelectorAll('td');
                        let matchesAccuracy = false;

                        // Check for accuracy range searches like ">90", "<70"
                        if (searchTerm.startsWith('>')) {{
                            const threshold = parseFloat(searchTerm.substring(1));
                            cells.forEach(cell => {{
                                const match = cell.textContent.match(/(\\d+\\.\\d+)%/);
                                if (match && parseFloat(match[1]) > threshold) {{
                                    matchesAccuracy = true;
                                }}
                            }});
                        }} else if (searchTerm.startsWith('<')) {{
                            const threshold = parseFloat(searchTerm.substring(1));
                            cells.forEach(cell => {{
                                const match = cell.textContent.match(/(\\d+\\.\\d+)%/);
                                if (match && parseFloat(match[1]) < threshold) {{
                                    matchesAccuracy = true;
                                }}
                            }});
                        }}

                        if (text.includes(searchTerm) || matchesAccuracy) {{
                            row.style.display = '';
                        }} else {{
                            row.style.display = 'none';
                        }}
                    }});
                }});
            }}
        </script>
        '''


def generate_html_v2(run_info: Dict[str, Any],
                     results: List[Dict[str, Any]],
                     aggregate: Dict[str, float],
                     trend_data: Dict[str, List] = None) -> str:
    """Convenience function to generate dashboard HTML."""
    generator = DashboardGeneratorV2()
    return generator.generate_html(run_info, results, aggregate, trend_data)
