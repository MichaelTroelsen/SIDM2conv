"""Run validation on pipeline outputs and track results."""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import io

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from scripts.validation.database import ValidationDatabase
from scripts.validation.metrics import MetricsCollector
from scripts.validation.regression import RegressionDetector


def get_git_commit() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return 'unknown'


def get_pipeline_version() -> str:
    """Get pipeline version from STATUS.md."""
    try:
        status_path = Path(__file__).parent.parent / 'STATUS.md'
        content = status_path.read_text(encoding='utf-8')
        # Extract version from "**Current Version**: vX.Y.Z"
        for line in content.split('\n'):
            if '**Current Version**' in line:
                version = line.split('**Current Version**:')[1].strip()
                return version
    except Exception:
        pass
    return 'unknown'


def find_test_files(output_base: Path, quick: bool = False) -> list:
    """Find all test files in output directory.

    Args:
        output_base: Base output directory
        quick: If True, return subset for quick validation

    Returns:
        List of test file names (without extensions)
    """
    # Look for folders in output directory
    if not output_base.exists():
        return []

    test_files = []
    for item in output_base.iterdir():
        if item.is_dir():
            # Check if it has New/ subdirectory with .sf2 file
            new_dir = item / 'New'
            if new_dir.exists():
                # Find .sf2 file
                sf2_files = list(new_dir.glob('*.sf2'))
                if sf2_files:
                    test_files.append(item.name)

    test_files.sort()

    if quick and len(test_files) > 5:
        # Return subset for quick validation
        return test_files[::len(test_files)//5][:5]

    return test_files


def run_validation(output_base: Path, db_path: Path,
                  quick: bool = False,
                  baseline_run: int = None,
                  notes: str = None) -> int:
    """Run validation on all test files.

    Args:
        output_base: Base directory for pipeline outputs
        db_path: Path to validation database
        quick: If True, run quick validation on subset
        baseline_run: Optional baseline run ID for comparison
        notes: Optional notes for this run

    Returns:
        run_id of the created validation run
    """
    print("=" * 70)
    print("SIDM2 VALIDATION RUNNER")
    print("=" * 70)
    print()

    # Get git info
    git_commit = get_git_commit()
    pipeline_version = get_pipeline_version()

    print(f"Git Commit: {git_commit}")
    print(f"Pipeline Version: {pipeline_version}")
    print(f"Output Base: {output_base}")
    print(f"Database: {db_path}")
    print()

    # Find test files
    test_files = find_test_files(output_base, quick=quick)

    if not test_files:
        print("ERROR: No test files found in output directory")
        print(f"Expected structure: {output_base}/{{filename}}/New/{{filename}}.sf2")
        return None

    print(f"Found {len(test_files)} test file(s)")
    if quick:
        print("(Quick mode: testing subset)")
    print()

    # Initialize database
    with ValidationDatabase(db_path) as db:
        # Create validation run
        run_id = db.create_run(
            git_commit=git_commit,
            pipeline_version=pipeline_version,
            notes=notes
        )

        print(f"Created validation run: {run_id}")
        print()

        # Collect metrics for each file
        collector = MetricsCollector(output_base)
        all_results = []

        print("Collecting metrics...")
        print("-" * 70)

        for i, filename in enumerate(test_files, 1):
            print(f"[{i}/{len(test_files)}] {filename}...", end=" ")

            try:
                metrics = collector.collect_file_metrics(filename)
                all_results.append(metrics)

                # Add to database
                db.add_file_result(run_id, **metrics)

                # Show status
                if metrics['conversion_success']:
                    print("✅ PASS")
                else:
                    print("❌ FAIL")

            except Exception as e:
                print(f"❌ ERROR: {e}")
                # Add minimal result
                db.add_file_result(run_id, filename=filename, conversion_success=False)

        print("-" * 70)
        print()

        # Calculate aggregate metrics
        aggregate = collector.collect_aggregate_metrics(all_results)

        # Store aggregate metrics
        for metric_name, metric_value in aggregate.items():
            if metric_name != 'total_files':
                db.add_metric(run_id, metric_name, metric_value)

        # Display summary
        print("SUMMARY")
        print("-" * 70)
        print(f"Total Files: {aggregate['total_files']}")
        print(f"Pass Rate: {aggregate['pass_rate'] * 100:.1f}%")
        if aggregate.get('avg_overall_accuracy'):
            print(f"Avg Accuracy: {aggregate['avg_overall_accuracy']:.1f}%")
        print()

        # Check for regressions if baseline provided
        if baseline_run:
            print("REGRESSION DETECTION")
            print("-" * 70)

            baseline_results = db.get_run_results(baseline_run)
            current_results = all_results

            detector = RegressionDetector()
            regression_results = detector.detect_regressions(baseline_results, current_results)

            # Display summary
            print(detector.format_regression_report(regression_results))
            print()

            # Store regression count as metric
            db.add_metric(run_id, 'regression_count', regression_results['regression_count'])
            db.add_metric(run_id, 'improvement_count', regression_results['improvement_count'])

        print("=" * 70)
        print(f"Validation complete! Run ID: {run_id}")
        print("=" * 70)

        return run_id


def export_results(db_path: Path, run_id: int, output_path: Path):
    """Export validation results to JSON.

    Args:
        db_path: Path to validation database
        run_id: Run ID to export
        output_path: Output JSON file path
    """
    print(f"Exporting run {run_id} to {output_path}...")

    with ValidationDatabase(db_path) as db:
        db.export_to_json(run_id, output_path)

    print(f"✅ Exported to {output_path}")


def compare_runs(db_path: Path, run_id1: int, run_id2: int):
    """Compare two validation runs.

    Args:
        db_path: Path to validation database
        run_id1: First run ID
        run_id2: Second run ID
    """
    print(f"Comparing run {run_id1} vs run {run_id2}...")
    print()

    with ValidationDatabase(db_path) as db:
        results1 = db.get_run_results(run_id1)
        results2 = db.get_run_results(run_id2)

        detector = RegressionDetector()
        comparison = detector.detect_regressions(results1, results2)

        print(detector.format_regression_report(comparison))


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Run SIDM2 pipeline validation and track results'
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=Path('output/SIDSF2player_Complete_Pipeline'),
        help='Pipeline output directory (default: output/SIDSF2player_Complete_Pipeline)'
    )

    parser.add_argument(
        '--db',
        type=Path,
        default=Path('validation/database.sqlite'),
        help='Validation database path (default: validation/database.sqlite)'
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='Quick validation (subset of files)'
    )

    parser.add_argument(
        '--baseline',
        type=int,
        metavar='RUN_ID',
        help='Baseline run ID for regression detection'
    )

    parser.add_argument(
        '--notes',
        type=str,
        help='Notes about this validation run'
    )

    parser.add_argument(
        '--export',
        type=Path,
        metavar='JSON_FILE',
        help='Export results to JSON file'
    )

    parser.add_argument(
        '--compare',
        type=int,
        nargs=2,
        metavar=('RUN_ID1', 'RUN_ID2'),
        help='Compare two validation runs'
    )

    args = parser.parse_args()

    # Ensure validation directory exists
    args.db.parent.mkdir(parents=True, exist_ok=True)

    # Compare mode
    if args.compare:
        compare_runs(args.db, args.compare[0], args.compare[1])
        return 0

    # Run validation
    run_id = run_validation(
        output_base=args.output,
        db_path=args.db,
        quick=args.quick,
        baseline_run=args.baseline,
        notes=args.notes
    )

    if run_id is None:
        return 1

    # Export if requested
    if args.export:
        export_results(args.db, run_id, args.export)

    return 0


if __name__ == '__main__':
    sys.exit(main())
