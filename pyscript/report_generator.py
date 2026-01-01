#!/usr/bin/env python3
"""
Batch Conversion Report Generator

Generates professional HTML reports from Conversion Cockpit batch results
using the HTML components library.

Version: 1.0.0
Date: 2026-01-01
"""

from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from collections import Counter
import json

from html_components import (
    HTMLComponents, StatCard, NavItem, StatCardType, ColorScheme
)


class BatchReportGenerator:
    """Generate HTML reports from batch conversion results"""

    def __init__(self, results: List[Dict], summary: Dict, config: Optional[Dict] = None):
        """
        Initialize report generator

        Args:
            results: List of file result dictionaries
            summary: Batch summary statistics
            config: Optional pipeline configuration
        """
        self.results = results
        self.summary = summary
        self.config = config or {}
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generate(self, output_path: str) -> bool:
        """
        Generate HTML report

        Args:
            output_path: Path to save HTML report

        Returns:
            True if successful, False otherwise
        """
        try:
            html = self._generate_html()
            Path(output_path).write_text(html, encoding='utf-8')
            return True
        except Exception as e:
            print(f"[ERROR] Failed to generate batch report: {e}")
            return False

    def _generate_html(self) -> str:
        """Generate complete HTML document"""
        html = HTMLComponents.get_document_header(
            title="Batch Conversion Report - SIDM2",
            include_chartjs=False
        )

        html += '<div class="container">'

        # Sidebar
        html += self._create_sidebar()

        # Main content
        html += '<div class="main-content">'
        html += self._create_header()
        html += self._create_overview_stats()
        html += self._create_summary_section()
        html += self._create_driver_breakdown()
        html += self._create_accuracy_distribution()
        html += self._create_performance_metrics()
        html += self._create_file_details()
        html += HTMLComponents.create_footer("3.0.1", self.timestamp)
        html += '</div>'  # main-content

        html += '</div>'  # container

        html += HTMLComponents.get_document_footer()

        return html

    def _create_sidebar(self) -> str:
        """Create navigation sidebar"""
        nav_items = [
            NavItem("Overview", "overview"),
            NavItem("Summary", "summary"),
            NavItem("Drivers", "drivers"),
            NavItem("Accuracy", "accuracy"),
            NavItem("Performance", "performance"),
            NavItem("File Details", "files", count=self.summary.get("total_files", 0))
        ]

        # Sidebar stats
        passed = self.summary.get("passed", 0)
        failed = self.summary.get("failed", 0)
        warnings = self.summary.get("warnings", 0)
        total = self.summary.get("total_files", 0)

        sidebar_stats = [
            StatCard("Total Files", str(total), StatCardType.INFO),
            StatCard("Success Rate", f"{self.summary.get('pass_rate', 0):.1f}%",
                    StatCardType.SUCCESS if self.summary.get('pass_rate', 0) >= 90 else StatCardType.WARNING)
        ]

        return HTMLComponents.create_sidebar(
            "Batch Report",
            nav_items,
            sidebar_stats
        )

    def _create_header(self) -> str:
        """Create report header"""
        return f'''
        <div id="overview" class="header">
            <h1>Batch Conversion Report</h1>
            <div class="subtitle">SIDM2 Conversion Cockpit - Generated {self.timestamp}</div>
        </div>
        '''

    def _create_overview_stats(self) -> str:
        """Create overview statistics grid"""
        total = self.summary.get("total_files", 0)
        passed = self.summary.get("passed", 0)
        failed = self.summary.get("failed", 0)
        warnings = self.summary.get("warnings", 0)
        avg_accuracy = self.summary.get("avg_accuracy", 0)
        duration = self.summary.get("duration", 0)

        cards = [
            StatCard("Total Files", str(total), StatCardType.PRIMARY),
            StatCard("Passed", str(passed), StatCardType.SUCCESS),
            StatCard("Failed", str(failed), StatCardType.ERROR if failed > 0 else StatCardType.SUCCESS),
            StatCard("Warnings", str(warnings), StatCardType.WARNING if warnings > 0 else StatCardType.SUCCESS),
            StatCard("Avg Accuracy", f"{avg_accuracy:.1f}%",
                    StatCardType.SUCCESS if avg_accuracy >= 90 else StatCardType.WARNING),
            StatCard("Total Time", f"{duration:.1f}s", StatCardType.INFO)
        ]

        return HTMLComponents.create_stat_grid(cards)

    def _create_summary_section(self) -> str:
        """Create summary section"""
        total = self.summary.get("total_files", 0)
        passed = self.summary.get("passed", 0)
        failed = self.summary.get("failed", 0)
        warnings = self.summary.get("warnings", 0)
        pass_rate = self.summary.get("pass_rate", 0)
        duration = self.summary.get("duration", 0)

        # Calculate average time per file
        avg_time = duration / total if total > 0 else 0

        content = f'''
        <div class="section">
            <h3>Batch Summary</h3>
            <table class="info-table">
                <tr>
                    <td><strong>Total Files Processed:</strong></td>
                    <td>{total}</td>
                </tr>
                <tr>
                    <td><strong>Successful Conversions:</strong></td>
                    <td>{passed} ({pass_rate:.1f}%)</td>
                </tr>
                <tr>
                    <td><strong>Failed Conversions:</strong></td>
                    <td>{failed}</td>
                </tr>
                <tr>
                    <td><strong>Warnings:</strong></td>
                    <td>{warnings}</td>
                </tr>
                <tr>
                    <td><strong>Total Processing Time:</strong></td>
                    <td>{duration:.2f} seconds</td>
                </tr>
                <tr>
                    <td><strong>Average Time per File:</strong></td>
                    <td>{avg_time:.2f} seconds</td>
                </tr>
            </table>
        </div>
        '''

        return HTMLComponents.create_collapsible(
            "summary",
            "Summary Statistics",
            content,
            collapsed=False
        )

    def _create_driver_breakdown(self) -> str:
        """Create driver usage breakdown"""
        # Count driver usage
        driver_counts = Counter(r.get("driver", "unknown") for r in self.results)

        # Create table rows
        rows = []
        for driver, count in sorted(driver_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(self.results) * 100) if self.results else 0
            rows.append([driver, str(count), f"{percentage:.1f}%"])

        table_html = HTMLComponents.create_table(
            headers=["Driver", "Files", "Percentage"],
            rows=rows
        )

        content = f'''
        <div class="section">
            <h3>Driver Usage</h3>
            <p>Breakdown of which drivers were used for conversion:</p>
            {table_html}
        </div>
        '''

        return HTMLComponents.create_collapsible(
            "drivers",
            f"Driver Breakdown ({len(driver_counts)} drivers)",
            content,
            collapsed=False
        )

    def _create_accuracy_distribution(self) -> str:
        """Create accuracy distribution section"""
        # Collect accuracies
        accuracies = [r.get("accuracy", 0) for r in self.results if r.get("accuracy", 0) > 0]

        if not accuracies:
            content = '<p class="warning">No accuracy data available.</p>'
        else:
            # Calculate distribution
            perfect = sum(1 for a in accuracies if a >= 99.0)
            high = sum(1 for a in accuracies if 90.0 <= a < 99.0)
            medium = sum(1 for a in accuracies if 70.0 <= a < 90.0)
            low = sum(1 for a in accuracies if a < 70.0)

            total_with_accuracy = len(accuracies)
            avg_accuracy = sum(accuracies) / total_with_accuracy
            min_accuracy = min(accuracies)
            max_accuracy = max(accuracies)

            rows = [
                ["Perfect (99-100%)", str(perfect), f"{perfect/total_with_accuracy*100:.1f}%"],
                ["High (90-99%)", str(high), f"{high/total_with_accuracy*100:.1f}%"],
                ["Medium (70-90%)", str(medium), f"{medium/total_with_accuracy*100:.1f}%"],
                ["Low (<70%)", str(low), f"{low/total_with_accuracy*100:.1f}%"]
            ]

            table_html = HTMLComponents.create_table(
                headers=["Accuracy Range", "Files", "Percentage"],
                rows=rows
            )

            content = f'''
            <div class="section">
                <h3>Accuracy Distribution</h3>
                <p><strong>Average:</strong> {avg_accuracy:.1f}% | <strong>Min:</strong> {min_accuracy:.1f}% | <strong>Max:</strong> {max_accuracy:.1f}%</p>
                {table_html}
            </div>
            '''

        return HTMLComponents.create_collapsible(
            "accuracy",
            f"Accuracy Distribution ({len(accuracies)} files with accuracy data)",
            content,
            collapsed=False
        )

    def _create_performance_metrics(self) -> str:
        """Create performance metrics section"""
        # Calculate timing statistics
        durations = [r.get("duration", 0) for r in self.results if r.get("duration", 0) > 0]

        if not durations:
            content = '<p class="warning">No timing data available.</p>'
        else:
            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            total_duration = self.summary.get("duration", sum(durations))

            # Find fastest and slowest files
            fastest_file = min(self.results, key=lambda r: r.get("duration", float('inf')))
            slowest_file = max(self.results, key=lambda r: r.get("duration", 0))

            content = f'''
            <div class="section">
                <h3>Performance Metrics</h3>

                <h4>Timing Statistics</h4>
                <table class="info-table">
                    <tr>
                        <td><strong>Total Processing Time:</strong></td>
                        <td>{total_duration:.2f} seconds</td>
                    </tr>
                    <tr>
                        <td><strong>Average Time per File:</strong></td>
                        <td>{avg_duration:.2f} seconds</td>
                    </tr>
                    <tr>
                        <td><strong>Fastest Conversion:</strong></td>
                        <td>{min_duration:.2f} seconds</td>
                    </tr>
                    <tr>
                        <td><strong>Slowest Conversion:</strong></td>
                        <td>{max_duration:.2f} seconds</td>
                    </tr>
                    <tr>
                        <td><strong>Throughput:</strong></td>
                        <td>{len(durations)/total_duration:.2f} files/second</td>
                    </tr>
                </table>

                <h4>Fastest File</h4>
                <p><code>{fastest_file.get("filename", "N/A")}</code> - {fastest_file.get("duration", 0):.2f}s</p>

                <h4>Slowest File</h4>
                <p><code>{slowest_file.get("filename", "N/A")}</code> - {slowest_file.get("duration", 0):.2f}s</p>
            </div>
            '''

        return HTMLComponents.create_collapsible(
            "performance",
            "Performance Metrics",
            content,
            collapsed=False
        )

    def _create_file_details(self) -> str:
        """Create per-file details section"""
        # Sort results by status (failed first, then warnings, then passed)
        status_priority = {"failed": 0, "warning": 1, "passed": 2, "pending": 3}
        sorted_results = sorted(
            self.results,
            key=lambda r: (status_priority.get(r.get("status", "pending"), 99), r.get("filename", ""))
        )

        # Create summary table (top 20 or all if fewer)
        summary_rows = []
        for result in sorted_results[:20]:
            filename = Path(result.get("filename", "N/A")).name
            driver = result.get("driver", "N/A")
            status = result.get("status", "pending")
            accuracy = result.get("accuracy", 0)
            duration = result.get("duration", 0)

            # Create status badge
            if status == "passed":
                status_badge = f'<span style="color: {ColorScheme.SUCCESS};">✓ Passed</span>'
            elif status == "failed":
                status_badge = f'<span style="color: {ColorScheme.ERROR};">✗ Failed</span>'
            elif status == "warning":
                status_badge = f'<span style="color: {ColorScheme.WARNING};">⚠ Warning</span>'
            else:
                status_badge = f'<span style="color: {ColorScheme.TEXT_SECONDARY};">○ Pending</span>'

            summary_rows.append([
                filename,
                driver,
                status_badge,
                f"{accuracy:.1f}%" if accuracy > 0 else "N/A",
                f"{duration:.2f}s" if duration > 0 else "N/A"
            ])

        summary_table = HTMLComponents.create_table(
            headers=["File", "Driver", "Status", "Accuracy", "Duration"],
            rows=summary_rows
        )

        # Create detailed expandable sections for each file
        details_html = ""
        for idx, result in enumerate(sorted_results):
            details_html += self._create_file_detail(result, idx)

        content = f'''
        <div class="section">
            <h3>File Summary</h3>
            <p>Showing {min(20, len(sorted_results))} of {len(sorted_results)} files (failed/warnings first):</p>
            {summary_table}

            <h3>Detailed Results</h3>
            <p>Click on any file below to view full details:</p>
            {details_html}
        </div>
        '''

        return HTMLComponents.create_collapsible(
            "files",
            f"File Details ({len(self.results)} files)",
            content,
            collapsed=True
        )

    def _create_file_detail(self, result: Dict, index: int) -> str:
        """Create detailed view for a single file"""
        filename = result.get("filename", "N/A")
        display_name = Path(filename).name
        driver = result.get("driver", "N/A")
        status = result.get("status", "pending")
        accuracy = result.get("accuracy", 0)
        duration = result.get("duration", 0)
        steps_completed = result.get("steps_completed", 0)
        total_steps = result.get("total_steps", 0)
        error_message = result.get("error_message", "")
        output_files = result.get("output_files", [])

        # Status indicator
        if status == "passed":
            status_class = "success"
            status_text = "✓ Passed"
        elif status == "failed":
            status_class = "error"
            status_text = "✗ Failed"
        elif status == "warning":
            status_class = "warning"
            status_text = "⚠ Warning"
        else:
            status_class = "info"
            status_text = "○ Pending"

        detail_content = f'''
        <div class="file-detail">
            <table class="info-table">
                <tr>
                    <td><strong>Filename:</strong></td>
                    <td><code>{filename}</code></td>
                </tr>
                <tr>
                    <td><strong>Driver:</strong></td>
                    <td>{driver}</td>
                </tr>
                <tr>
                    <td><strong>Status:</strong></td>
                    <td class="{status_class}">{status_text}</td>
                </tr>
                <tr>
                    <td><strong>Steps Completed:</strong></td>
                    <td>{steps_completed} / {total_steps}</td>
                </tr>
                <tr>
                    <td><strong>Accuracy:</strong></td>
                    <td>{accuracy:.1f}%</td>
                </tr>
                <tr>
                    <td><strong>Duration:</strong></td>
                    <td>{duration:.2f} seconds</td>
                </tr>
        '''

        if error_message:
            detail_content += f'''
                <tr>
                    <td><strong>Error:</strong></td>
                    <td class="error">{error_message}</td>
                </tr>
            '''

        if output_files:
            files_list = "<br>".join(f"<code>{Path(f).name}</code>" for f in output_files[:5])
            if len(output_files) > 5:
                files_list += f"<br><em>... and {len(output_files) - 5} more files</em>"
            detail_content += f'''
                <tr>
                    <td><strong>Output Files:</strong></td>
                    <td>{files_list}</td>
                </tr>
            '''

        detail_content += '''
            </table>
        </div>
        '''

        return HTMLComponents.create_collapsible(
            f"file-{index}",
            f"{display_name} - {status_text}",
            detail_content,
            collapsed=True
        )


def generate_batch_report(results: List[Dict], summary: Dict, output_path: str, config: Optional[Dict] = None) -> bool:
    """
    Generate HTML batch report (convenience function)

    Args:
        results: List of file result dictionaries
        summary: Batch summary statistics
        output_path: Path to save HTML report
        config: Optional pipeline configuration

    Returns:
        True if successful, False otherwise
    """
    generator = BatchReportGenerator(results, summary, config)
    return generator.generate(output_path)


# Demo usage
if __name__ == '__main__':
    # Sample data for demonstration
    sample_results = [
        {
            "filename": "test1.sid",
            "driver": "laxity",
            "steps_completed": 5,
            "total_steps": 5,
            "accuracy": 99.5,
            "status": "passed",
            "error_message": "",
            "duration": 0.5,
            "output_files": ["test1.sf2", "test1_analysis.txt"]
        },
        {
            "filename": "test2.sid",
            "driver": "driver11",
            "steps_completed": 5,
            "total_steps": 5,
            "accuracy": 95.2,
            "status": "passed",
            "error_message": "",
            "duration": 0.3,
            "output_files": ["test2.sf2"]
        },
        {
            "filename": "test3.sid",
            "driver": "laxity",
            "steps_completed": 3,
            "total_steps": 5,
            "accuracy": 0,
            "status": "failed",
            "error_message": "Conversion failed: Invalid format",
            "duration": 0.2,
            "output_files": []
        }
    ]

    sample_summary = {
        "total_files": 3,
        "passed": 2,
        "failed": 1,
        "warnings": 0,
        "avg_accuracy": 97.35,
        "duration": 1.0,
        "pass_rate": 66.7
    }

    output = Path("output/batch_report_demo.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    success = generate_batch_report(sample_results, sample_summary, str(output))

    if success:
        print(f"[OK] Demo batch report generated: {output}")
        print(f"     Open in browser to view")
    else:
        print("[ERROR] Failed to generate demo report")
