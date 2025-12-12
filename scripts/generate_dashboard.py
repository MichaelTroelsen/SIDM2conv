"""Generate HTML dashboard from validation database."""

import argparse
import sys
from pathlib import Path
import io

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validation.database import ValidationDatabase
from scripts.validation.dashboard import DashboardGenerator
from scripts.validation.metrics import MetricsCollector


def generate_dashboard(db_path: Path, output_path: Path, run_id: int = None):
    """Generate HTML dashboard from validation data.

    Args:
        db_path: Path to validation database
        output_path: Output HTML file path
        run_id: Optional specific run ID (default: latest)
    """
    print(f"Generating dashboard from {db_path}...")

    with ValidationDatabase(db_path) as db:
        # Get run info
        if run_id:
            # Use specified run
            run_info = None
            cursor = db.conn.cursor()
            cursor.execute("SELECT * FROM validation_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            if row:
                run_info = dict(row)
        else:
            # Use latest run
            run_info = db.get_latest_run()
            run_id = run_info['run_id'] if run_info else None

        if not run_info:
            print("ERROR: No validation runs found in database")
            return False

        print(f"Using run {run_id}: {run_info['timestamp']}")

        # Get results
        results = db.get_run_results(run_id)

        if not results:
            print("WARNING: No file results found for this run")

        # Calculate aggregate metrics
        collector = MetricsCollector(Path('.'))  # Path not used for aggregates
        aggregate = collector.collect_aggregate_metrics(results)

        # Get trend data
        trend_data = {
            'accuracy': db.get_metric_trend('avg_overall_accuracy', limit=20)
        }

        # Generate HTML
        generator = DashboardGenerator()
        html = generator.generate_html(
            run_info=run_info,
            results=results,
            aggregate=aggregate,
            trend_data=trend_data if trend_data['accuracy'] else None
        )

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding='utf-8')

        print(f"✅ Dashboard generated: {output_path}")
        print(f"   Open in browser: file://{output_path.absolute()}")

        return True


def generate_summary_markdown(db_path: Path, output_path: Path, run_id: int = None):
    """Generate markdown summary from validation data.

    Args:
        db_path: Path to validation database
        output_path: Output markdown file path
        run_id: Optional specific run ID (default: latest)
    """
    print(f"Generating markdown summary...")

    with ValidationDatabase(db_path) as db:
        # Get run info
        if run_id:
            cursor = db.conn.cursor()
            cursor.execute("SELECT * FROM validation_runs WHERE run_id = ?", (run_id,))
            row = cursor.fetchone()
            run_info = dict(row) if row else None
        else:
            run_info = db.get_latest_run()
            run_id = run_info['run_id'] if run_info else None

        if not run_info:
            print("ERROR: No validation runs found in database")
            return False

        # Get results
        results = db.get_run_results(run_id)

        # Calculate aggregate
        collector = MetricsCollector(Path('.'))
        aggregate = collector.collect_aggregate_metrics(results)

        # Generate markdown
        lines = []
        lines.append("# SIDM2 Validation Summary")
        lines.append("")
        lines.append(f"**Run ID**: {run_id}")
        lines.append(f"**Timestamp**: {run_info['timestamp']}")
        lines.append(f"**Git Commit**: {run_info['git_commit']}")
        lines.append(f"**Pipeline Version**: {run_info['pipeline_version']}")
        lines.append("")

        lines.append("## Overall Metrics")
        lines.append("")
        lines.append(f"- **Files Tested**: {aggregate['total_files']}")
        lines.append(f"- **Pass Rate**: {aggregate['pass_rate'] * 100:.1f}%")
        if aggregate.get('avg_overall_accuracy'):
            lines.append(f"- **Avg Accuracy**: {aggregate['avg_overall_accuracy']:.1f}%")
        lines.append("")

        lines.append("## File Results")
        lines.append("")
        lines.append("| File | Method | Accuracy | Steps | Status |")
        lines.append("|------|--------|----------|-------|--------|")

        for result in sorted(results, key=lambda r: r.get('filename', '')):
            filename = result.get('filename', 'Unknown')
            method = result.get('conversion_method', 'N/A')
            accuracy = result.get('overall_accuracy') or 0

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

            status = '✅ PASS' if result.get('conversion_success', False) else '❌ FAIL'

            lines.append(f"| {filename} | {method} | {accuracy:.1f}% | {steps_passed}/9 | {status} |")

        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append(f"*Generated: {run_info['timestamp']}*")
        lines.append("")

        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text('\n'.join(lines), encoding='utf-8')

        print(f"✅ Summary generated: {output_path}")

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate validation dashboard from database'
    )

    parser.add_argument(
        '--db',
        type=Path,
        default=Path('validation/database.sqlite'),
        help='Validation database path (default: validation/database.sqlite)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=Path('validation/dashboard.html'),
        help='Output HTML file (default: validation/dashboard.html)'
    )

    parser.add_argument(
        '--run',
        type=int,
        metavar='RUN_ID',
        help='Specific run ID to generate dashboard for (default: latest)'
    )

    parser.add_argument(
        '--markdown',
        type=Path,
        metavar='MD_FILE',
        help='Also generate markdown summary to specified file'
    )

    args = parser.parse_args()

    # Check database exists
    if not args.db.exists():
        print(f"ERROR: Database not found: {args.db}")
        print("Run 'python scripts/run_validation.py' first to create validation data")
        return 1

    # Generate HTML dashboard
    success = generate_dashboard(args.db, args.output, args.run)

    if not success:
        return 1

    # Generate markdown if requested
    if args.markdown:
        generate_summary_markdown(args.db, args.markdown, args.run)

    return 0


if __name__ == '__main__':
    sys.exit(main())
