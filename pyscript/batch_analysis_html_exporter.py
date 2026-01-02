#!/usr/bin/env python3
"""
Batch Analysis HTML Exporter - Generate interactive summary report

Exports batch analysis results to standalone HTML with:
- Sortable results table
- Accuracy distribution charts
- Best/worst highlights
- Links to individual heatmaps/comparisons

Version: 1.0.0
Date: 2026-01-01
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.batch_analysis_engine import PairAnalysisResult, BatchAnalysisSummary
from pyscript.html_components import HTMLComponents, ColorScheme


class BatchAnalysisHTMLExporter:
    """Generate interactive HTML summary report for batch analysis"""

    def __init__(self, results: List[PairAnalysisResult],
                 summary: BatchAnalysisSummary):
        """
        Initialize HTML exporter.

        Args:
            results: List of PairAnalysisResult from batch analysis
            summary: BatchAnalysisSummary with aggregate statistics
        """
        self.results = results
        self.summary = summary

    def export(self, output_path: str) -> bool:
        """
        Generate and save HTML summary report.

        Args:
            output_path: Path to save HTML file

        Returns:
            True if successful, False otherwise
        """
        try:
            html = self._generate_html()

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)

            return True

        except Exception as e:
            print(f"[ERROR] Failed to export HTML: {e}")
            return False

    def _generate_html(self) -> str:
        """Build complete HTML document"""
        html_parts = []

        # Header with Chart.js
        html_parts.append(HTMLComponents.get_document_header(
            title=f"Batch Analysis Summary - {self.summary.total_pairs} Pairs",
            include_chartjs=True
        ))

        # Custom CSS
        html_parts.append(self._create_custom_css())

        # Container
        html_parts.append('<div class="container">')

        # Sidebar
        html_parts.append(self._create_sidebar())

        # Main content
        html_parts.append('<div class="main-content">')

        # Overview section
        html_parts.append(self._create_overview_section())

        # Charts section
        html_parts.append(self._create_charts_section())

        # Results table
        html_parts.append(self._create_results_table())

        # Best/Worst section
        html_parts.append(self._create_best_worst_section())

        html_parts.append('</div>')  # End main-content
        html_parts.append('</div>')  # End container

        # JavaScript for sorting and charts
        html_parts.append('<script>')
        html_parts.append(self._add_javascript())
        html_parts.append('</script>')

        # Footer
        html_parts.append(HTMLComponents.get_document_footer())

        return ''.join(html_parts)

    def _create_custom_css(self) -> str:
        """Create custom CSS for batch analysis report"""
        return f"""
<style>
.container {{
    display: flex;
    min-height: 100vh;
}}

.sidebar {{
    width: 250px;
    background: {ColorScheme.BG_SECONDARY};
    border-right: 1px solid {ColorScheme.BORDER_PRIMARY};
    padding: 20px;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
}}

.main-content {{
    flex: 1;
    padding: 30px;
    overflow-y: auto;
}}

.section {{
    margin-bottom: 40px;
}}

.section-title {{
    color: {ColorScheme.TEXT_PRIMARY};
    font-size: 24px;
    font-weight: 600;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 2px solid {ColorScheme.ACCENT_TEAL};
}}

/* Stat Cards */
.stat-cards {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}}

.stat-card {{
    background: {ColorScheme.BG_SECONDARY};
    border-radius: 8px;
    padding: 20px;
    border-left: 4px solid {ColorScheme.ACCENT_TEAL};
}}

.stat-card.success {{
    border-left-color: {ColorScheme.SUCCESS};
}}

.stat-card.warning {{
    border-left-color: {ColorScheme.WARNING};
}}

.stat-card.error {{
    border-left-color: {ColorScheme.ERROR};
}}

.stat-label {{
    color: {ColorScheme.TEXT_SECONDARY};
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}}

.stat-value {{
    color: {ColorScheme.TEXT_PRIMARY};
    font-size: 32px;
    font-weight: 700;
}}

.stat-subtext {{
    color: {ColorScheme.TEXT_SECONDARY};
    font-size: 13px;
    margin-top: 5px;
}}

/* Results Table */
.results-table {{
    width: 100%;
    border-collapse: collapse;
    background: {ColorScheme.BG_SECONDARY};
    border-radius: 8px;
    overflow: hidden;
}}

.results-table th {{
    background: {ColorScheme.BG_TERTIARY};
    color: {ColorScheme.TEXT_PRIMARY};
    font-weight: 600;
    text-align: left;
    padding: 15px;
    cursor: pointer;
    user-select: none;
    border-bottom: 2px solid {ColorScheme.BORDER_PRIMARY};
}}

.results-table th:hover {{
    background: {ColorScheme.BG_HOVER};
}}

.results-table th.sortable::after {{
    content: ' ↕';
    color: {ColorScheme.TEXT_SECONDARY};
}}

.results-table th.sort-asc::after {{
    content: ' ↑';
    color: {ColorScheme.ACCENT_TEAL};
}}

.results-table th.sort-desc::after {{
    content: ' ↓';
    color: {ColorScheme.ACCENT_TEAL};
}}

.results-table td {{
    padding: 12px 15px;
    border-bottom: 1px solid {ColorScheme.BORDER_PRIMARY};
    color: {ColorScheme.TEXT_PRIMARY};
}}

.results-table tr:hover {{
    background: {ColorScheme.BG_HOVER};
}}

/* Accuracy Bar */
.accuracy-bar {{
    height: 20px;
    background: {ColorScheme.BG_TERTIARY};
    border-radius: 10px;
    overflow: hidden;
    position: relative;
}}

.accuracy-fill {{
    height: 100%;
    border-radius: 10px;
    transition: width 0.3s ease;
}}

.accuracy-fill.excellent {{
    background: linear-gradient(90deg, {ColorScheme.SUCCESS_LIGHT}, {ColorScheme.SUCCESS});
}}

.accuracy-fill.good {{
    background: linear-gradient(90deg, {ColorScheme.WARNING_LIGHT}, {ColorScheme.WARNING});
}}

.accuracy-fill.poor {{
    background: linear-gradient(90deg, {ColorScheme.ERROR_LIGHT}, {ColorScheme.ERROR});
}}

.accuracy-text {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    color: {ColorScheme.TEXT_PRIMARY};
    font-size: 11px;
    font-weight: 600;
    text-shadow: 0 0 3px rgba(0,0,0,0.5);
}}

/* Status Badge */
.status-badge {{
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}}

.status-badge.success {{
    background: {ColorScheme.SUCCESS};
    color: white;
}}

.status-badge.partial {{
    background: {ColorScheme.WARNING};
    color: white;
}}

.status-badge.failed {{
    background: {ColorScheme.ERROR};
    color: white;
}}

/* Links */
.artifact-link {{
    color: {ColorScheme.ACCENT_TEAL};
    text-decoration: none;
    margin-right: 10px;
    font-size: 13px;
}}

.artifact-link:hover {{
    text-decoration: underline;
}}

/* Charts */
.chart-container {{
    background: {ColorScheme.BG_SECONDARY};
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
}}

.chart-wrapper {{
    position: relative;
    height: 300px;
}}

/* Search Box */
.search-box {{
    width: 100%;
    padding: 12px;
    background: {ColorScheme.BG_SECONDARY};
    border: 1px solid {ColorScheme.BORDER_PRIMARY};
    border-radius: 4px;
    color: {ColorScheme.TEXT_PRIMARY};
    font-size: 14px;
    margin-bottom: 20px;
}}

.search-box:focus {{
    outline: none;
    border-color: {ColorScheme.ACCENT_TEAL};
}}

/* Nav Links */
.nav-link {{
    display: block;
    padding: 10px 15px;
    color: {ColorScheme.TEXT_SECONDARY};
    text-decoration: none;
    border-radius: 4px;
    margin-bottom: 5px;
    transition: all 0.2s;
}}

.nav-link:hover {{
    background: {ColorScheme.BG_HOVER};
    color: {ColorScheme.TEXT_PRIMARY};
}}

.nav-link.active {{
    background: {ColorScheme.ACCENT_TEAL};
    color: white;
}}

/* Highlight Cards */
.highlight-cards {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
}}

.highlight-card {{
    background: {ColorScheme.BG_SECONDARY};
    border-radius: 8px;
    padding: 20px;
    border: 2px solid transparent;
}}

.highlight-card.best {{
    border-color: {ColorScheme.SUCCESS};
}}

.highlight-card.worst {{
    border-color: {ColorScheme.ERROR};
}}

.highlight-title {{
    color: {ColorScheme.TEXT_SECONDARY};
    font-size: 12px;
    text-transform: uppercase;
    margin-bottom: 10px;
}}

.highlight-filename {{
    color: {ColorScheme.TEXT_PRIMARY};
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 5px;
}}

.highlight-accuracy {{
    color: {ColorScheme.ACCENT_TEAL};
    font-size: 32px;
    font-weight: 700;
}}
</style>
"""

    def _create_sidebar(self) -> str:
        """Create navigation sidebar"""
        return f"""
<div class="sidebar">
    <h2 style="color: {ColorScheme.TEXT_PRIMARY}; margin-bottom: 20px;">Batch Analysis</h2>
    <nav>
        <a href="#overview" class="nav-link active">Overview</a>
        <a href="#charts" class="nav-link">Charts</a>
        <a href="#results" class="nav-link">Results Table</a>
        <a href="#highlights" class="nav-link">Best/Worst</a>
    </nav>

    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid {ColorScheme.BORDER_PRIMARY};">
        <div style="color: {ColorScheme.TEXT_SECONDARY}; font-size: 11px; text-transform: uppercase; margin-bottom: 10px;">Quick Stats</div>
        <div style="color: {ColorScheme.TEXT_PRIMARY}; font-size: 24px; font-weight: 700; margin-bottom: 5px;">{self.summary.total_pairs}</div>
        <div style="color: {ColorScheme.TEXT_SECONDARY}; font-size: 13px;">Total Pairs</div>
    </div>

    <div style="margin-top: 20px;">
        <div style="color: {ColorScheme.TEXT_PRIMARY}; font-size: 24px; font-weight: 700; margin-bottom: 5px;">{self.summary.avg_frame_match:.1f}%</div>
        <div style="color: {ColorScheme.TEXT_SECONDARY}; font-size: 13px;">Avg Accuracy</div>
    </div>
</div>
"""

    def _create_overview_section(self) -> str:
        """Create overview section with stat cards"""

        # Determine success rate color
        success_rate = (self.summary.successful / self.summary.total_pairs * 100) if self.summary.total_pairs > 0 else 0
        success_class = "success" if success_rate >= 90 else "warning" if success_rate >= 70 else "error"

        return f"""
<div class="section" id="overview">
    <h1 class="section-title">Overview</h1>

    <div class="stat-cards">
        <div class="stat-card">
            <div class="stat-label">Total Pairs Analyzed</div>
            <div class="stat-value">{self.summary.total_pairs}</div>
        </div>

        <div class="stat-card {success_class}">
            <div class="stat-label">Successful</div>
            <div class="stat-value">{self.summary.successful}</div>
            <div class="stat-subtext">{success_rate:.1f}% success rate</div>
        </div>

        <div class="stat-card success">
            <div class="stat-label">Average Frame Match</div>
            <div class="stat-value">{self.summary.avg_frame_match:.1f}%</div>
        </div>

        <div class="stat-card">
            <div class="stat-label">Average Register Accuracy</div>
            <div class="stat-value">{self.summary.avg_register_accuracy:.1f}%</div>
        </div>

        <div class="stat-card">
            <div class="stat-label">Total Duration</div>
            <div class="stat-value">{self.summary.total_duration:.1f}s</div>
            <div class="stat-subtext">{self.summary.avg_duration_per_pair:.1f}s per pair</div>
        </div>

        <div class="stat-card">
            <div class="stat-label">Voice Accuracies</div>
            <div class="stat-value" style="font-size: 16px;">
                V1: {self.summary.avg_voice1_accuracy:.1f}%<br>
                V2: {self.summary.avg_voice2_accuracy:.1f}%<br>
                V3: {self.summary.avg_voice3_accuracy:.1f}%
            </div>
        </div>
    </div>
</div>
"""

    def _create_charts_section(self) -> str:
        """Create charts section with accuracy distribution"""
        return f"""
<div class="section" id="charts">
    <h2 class="section-title">Accuracy Distribution</h2>

    <div class="chart-container">
        <div class="chart-wrapper">
            <canvas id="accuracyChart"></canvas>
        </div>
    </div>
</div>
"""

    def _create_results_table(self) -> str:
        """Create sortable results table"""
        table_rows = []

        for r in self.results:
            # Accuracy bar styling
            accuracy_class = "excellent" if r.frame_match_percent >= 90 else "good" if r.frame_match_percent >= 70 else "poor"

            # Status badge
            status_html = f'<span class="status-badge {r.status}">{r.status}</span>'

            # Artifact links
            artifacts_html = []
            if r.heatmap_path:
                artifacts_html.append(f'<a href="{r.heatmap_path}" class="artifact-link" target="_blank">Heatmap</a>')
            if r.comparison_path:
                artifacts_html.append(f'<a href="{r.comparison_path}" class="artifact-link" target="_blank">Comparison</a>')
            artifacts_str = ''.join(artifacts_html) if artifacts_html else '-'

            table_rows.append(f"""
            <tr data-filename="{r.filename_a.lower()}" data-accuracy="{r.frame_match_percent}">
                <td>{r.filename_a}</td>
                <td>
                    <div class="accuracy-bar">
                        <div class="accuracy-fill {accuracy_class}" style="width: {r.frame_match_percent}%"></div>
                        <div class="accuracy-text">{r.frame_match_percent:.1f}%</div>
                    </div>
                </td>
                <td>{r.register_accuracy_overall:.1f}%</td>
                <td>{r.total_diff_count:,}</td>
                <td>{status_html}</td>
                <td>{r.duration:.1f}s</td>
                <td>{artifacts_str}</td>
            </tr>
            """)

        return f"""
<div class="section" id="results">
    <h2 class="section-title">Results Table</h2>

    <input type="text" id="searchBox" class="search-box" placeholder="Search filenames..." onkeyup="filterTable()">

    <table class="results-table" id="resultsTable">
        <thead>
            <tr>
                <th class="sortable" onclick="sortTable(0)">Filename</th>
                <th class="sortable" onclick="sortTable(1)">Frame Match</th>
                <th class="sortable" onclick="sortTable(2)">Register Accuracy</th>
                <th class="sortable" onclick="sortTable(3)">Total Diffs</th>
                <th class="sortable" onclick="sortTable(4)">Status</th>
                <th class="sortable" onclick="sortTable(5)">Duration</th>
                <th>Artifacts</th>
            </tr>
        </thead>
        <tbody>
            {''.join(table_rows)}
        </tbody>
    </table>
</div>
"""

    def _create_best_worst_section(self) -> str:
        """Create best/worst match highlights"""
        if not self.summary.best_match_filename:
            return ""

        return f"""
<div class="section" id="highlights">
    <h2 class="section-title">Best & Worst Matches</h2>

    <div class="highlight-cards">
        <div class="highlight-card best">
            <div class="highlight-title">Best Match</div>
            <div class="highlight-filename">{self.summary.best_match_filename}</div>
            <div class="highlight-accuracy">{self.summary.best_match_accuracy:.1f}%</div>
        </div>

        <div class="highlight-card worst">
            <div class="highlight-title">Worst Match</div>
            <div class="highlight-filename">{self.summary.worst_match_filename}</div>
            <div class="highlight-accuracy">{self.summary.worst_match_accuracy:.1f}%</div>
        </div>
    </div>
</div>
"""

    def _add_javascript(self) -> str:
        """Add JavaScript for sorting, filtering, and charts"""

        # Build accuracy data for chart
        accuracy_bins = [0, 0, 0, 0, 0]  # 0-20, 20-40, 40-60, 60-80, 80-100
        for r in self.results:
            if r.status in ("success", "partial"):
                bin_index = min(int(r.frame_match_percent / 20), 4)
                accuracy_bins[bin_index] += 1

        return f"""
// Accuracy distribution chart
const ctx = document.getElementById('accuracyChart').getContext('2d');
new Chart(ctx, {{
    type: 'bar',
    data: {{
        labels: ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'],
        datasets: [{{
            label: 'Number of Pairs',
            data: {accuracy_bins},
            backgroundColor: [
                '{ColorScheme.ERROR}',
                '{ColorScheme.WARNING}',
                '{ColorScheme.WARNING_LIGHT}',
                '{ColorScheme.SUCCESS_LIGHT}',
                '{ColorScheme.SUCCESS}'
            ]
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{
                display: false
            }},
            title: {{
                display: true,
                text: 'Frame Match Accuracy Distribution',
                color: '{ColorScheme.TEXT_PRIMARY}'
            }}
        }},
        scales: {{
            y: {{
                beginAtZero: true,
                ticks: {{
                    color: '{ColorScheme.TEXT_SECONDARY}'
                }},
                grid: {{
                    color: '{ColorScheme.BORDER_PRIMARY}'
                }}
            }},
            x: {{
                ticks: {{
                    color: '{ColorScheme.TEXT_SECONDARY}'
                }},
                grid: {{
                    color: '{ColorScheme.BORDER_PRIMARY}'
                }}
            }}
        }}
    }}
}});

// Table sorting
let sortDirection = {{}};

function sortTable(columnIndex) {{
    const table = document.getElementById('resultsTable');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    // Toggle sort direction
    if (!sortDirection[columnIndex]) {{
        sortDirection[columnIndex] = 'asc';
    }} else if (sortDirection[columnIndex] === 'asc') {{
        sortDirection[columnIndex] = 'desc';
    }} else {{
        sortDirection[columnIndex] = 'asc';
    }}

    // Update header classes
    table.querySelectorAll('th').forEach((th, idx) => {{
        th.classList.remove('sort-asc', 'sort-desc');
        if (idx === columnIndex) {{
            th.classList.add('sort-' + sortDirection[columnIndex]);
        }}
    }});

    // Sort rows
    rows.sort((a, b) => {{
        let aVal, bVal;

        if (columnIndex === 0) {{
            // Filename
            aVal = a.dataset.filename;
            bVal = b.dataset.filename;
        }} else if (columnIndex === 1 || columnIndex === 2) {{
            // Accuracy columns (use data-accuracy)
            aVal = parseFloat(a.dataset.accuracy);
            bVal = parseFloat(b.dataset.accuracy);
        }} else if (columnIndex === 3) {{
            // Total diffs (parse number with commas)
            aVal = parseInt(a.cells[columnIndex].textContent.replace(/,/g, ''));
            bVal = parseInt(b.cells[columnIndex].textContent.replace(/,/g, ''));
        }} else if (columnIndex === 5) {{
            // Duration (parse seconds)
            aVal = parseFloat(a.cells[columnIndex].textContent);
            bVal = parseFloat(b.cells[columnIndex].textContent);
        }} else {{
            // Text comparison
            aVal = a.cells[columnIndex].textContent;
            bVal = b.cells[columnIndex].textContent;
        }}

        if (sortDirection[columnIndex] === 'asc') {{
            return aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
        }} else {{
            return aVal > bVal ? -1 : aVal < bVal ? 1 : 0;
        }}
    }});

    // Re-append sorted rows
    rows.forEach(row => tbody.appendChild(row));
}}

// Table filtering
function filterTable() {{
    const searchBox = document.getElementById('searchBox');
    const filter = searchBox.value.toLowerCase();
    const table = document.getElementById('resultsTable');
    const rows = table.querySelector('tbody').querySelectorAll('tr');

    rows.forEach(row => {{
        const filename = row.dataset.filename;
        if (filename.includes(filter)) {{
            row.style.display = '';
        }} else {{
            row.style.display = 'none';
        }}
    }});
}}

// Smooth scrolling for nav links
document.querySelectorAll('.nav-link').forEach(link => {{
    link.addEventListener('click', function(e) {{
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {{
            target.scrollIntoView({{ behavior: 'smooth' }});

            // Update active link
            document.querySelectorAll('.nav-link').forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        }}
    }});
}});
"""


def main():
    """Test HTML exporter."""
    print("Batch Analysis HTML Exporter - Test Mode")
    print("This module is meant to be imported, not run directly.")
    print()
    print("Usage:")
    print("  from batch_analysis_html_exporter import BatchAnalysisHTMLExporter")
    print("  exporter = BatchAnalysisHTMLExporter(results, summary)")
    print("  exporter.export('batch_summary.html')")
    print()
    print("See batch_analysis_tool.py for complete CLI usage.")


if __name__ == '__main__':
    main()
