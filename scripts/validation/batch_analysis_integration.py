"""Validation pipeline integration for Batch Analysis Tool.

Integrates batch analysis results with the SIDM2 validation system,
storing results in the validation database and linking from the dashboard.

Usage:
    # Run batch analysis and store in validation DB
    python scripts/validation/batch_analysis_integration.py originals/ exported/

    # Run with custom options
    python scripts/validation/batch_analysis_integration.py originals/ exported/ --frames 500 --no-heatmaps

    # Use specific validation run
    python scripts/validation/batch_analysis_integration.py originals/ exported/ --run-id 5
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import asdict
import subprocess

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'pyscript'))

from scripts.validation.database import ValidationDatabase
from pyscript.batch_analysis_engine import BatchAnalysisEngine, BatchAnalysisConfig


class ValidationBatchAnalyzer:
    """Integrates batch analysis with validation pipeline."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize batch analyzer with validation database.

        Args:
            db_path: Path to validation database (default: validation/database.sqlite)
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'validation' / 'database.sqlite'

        self.db = ValidationDatabase(db_path)

    def run_batch_analysis(self,
                          dir_a: Path,
                          dir_b: Path,
                          output_dir: Optional[Path] = None,
                          frames: int = 300,
                          generate_heatmaps: bool = True,
                          generate_comparisons: bool = True,
                          run_id: Optional[int] = None,
                          git_commit: Optional[str] = None,
                          notes: Optional[str] = None,
                          verbose: int = 0) -> Dict[str, Any]:
        """Run batch analysis and store results in validation database.

        Args:
            dir_a: Directory with original SID files
            dir_b: Directory with converted/exported SID files
            output_dir: Output directory (default: batch_analysis_output)
            frames: Frames to trace per file
            generate_heatmaps: Generate heatmap HTMLs
            generate_comparisons: Generate comparison HTMLs
            run_id: Existing validation run ID (creates new if None)
            git_commit: Git commit hash
            notes: Notes about this batch analysis
            verbose: Verbosity level (0, 1, 2)

        Returns:
            Dictionary with batch_id, run_id, summary, output_paths
        """
        # Create validation run if needed
        if run_id is None:
            # Get current git commit if not provided
            if git_commit is None:
                try:
                    result = subprocess.run(
                        ['git', 'rev-parse', '--short', 'HEAD'],
                        capture_output=True,
                        text=True,
                        cwd=Path(__file__).parent.parent.parent
                    )
                    if result.returncode == 0:
                        git_commit = result.stdout.strip()
                except Exception:
                    git_commit = None

            run_id = self.db.create_run(
                git_commit=git_commit,
                pipeline_version="3.1.0",
                notes=notes or f"Batch analysis: {dir_a} vs {dir_b}"
            )
            print(f"Created validation run: {run_id}")
        else:
            print(f"Using existing validation run: {run_id}")

        # Set default output directory
        if output_dir is None:
            output_dir = Path('batch_analysis_output')

        # Create batch analysis config
        config = BatchAnalysisConfig(
            dir_a=dir_a,
            dir_b=dir_b,
            output_dir=output_dir,
            frames=frames,
            generate_heatmaps=generate_heatmaps,
            generate_comparisons=generate_comparisons,
            export_csv=True,
            export_json=True,
            export_html=True,
            verbose=verbose
        )

        # Run batch analysis
        print(f"\nRunning batch analysis...")
        print(f"  Directory A: {dir_a}")
        print(f"  Directory B: {dir_b}")
        print(f"  Output: {output_dir}")
        print(f"  Frames: {frames}")
        print()

        engine = BatchAnalysisEngine(config)
        summary = engine.run()

        # Convert summary to dictionary
        summary_dict = asdict(summary)

        # Store batch analysis in database
        config_dict = {
            'dir_a': str(dir_a),
            'dir_b': str(dir_b),
            'frames': frames
        }

        output_paths = {
            'html_report_path': str(summary.html_report_path) if summary.html_report_path else '',
            'csv_path': str(summary.csv_path) if summary.csv_path else '',
            'json_path': str(summary.json_path) if summary.json_path else ''
        }

        batch_id = self.db.add_batch_analysis(
            run_id=run_id,
            summary=summary_dict,
            config=config_dict,
            output_paths=output_paths
        )

        print(f"\nStored batch analysis in validation database:")
        print(f"  Batch ID: {batch_id}")
        print(f"  Run ID: {run_id}")

        # Store individual pair results
        print(f"\nStoring {len(engine.results)} pair results...")
        for result in engine.results:
            pair_dict = asdict(result)
            self.db.add_batch_pair_result(batch_id, pair_dict)

        print(f"  [OK] Stored {len(engine.results)} pair results")

        # Add aggregate metrics to trends
        self.db.add_metric(run_id, 'batch_avg_frame_match', summary.avg_frame_match)
        self.db.add_metric(run_id, 'batch_avg_register_accuracy', summary.avg_register_accuracy)
        self.db.add_metric(run_id, 'batch_success_rate',
                          (summary.successful / summary.total_pairs * 100) if summary.total_pairs > 0 else 0)

        return {
            'batch_id': batch_id,
            'run_id': run_id,
            'summary': summary_dict,
            'output_paths': output_paths,
            'total_pairs': len(engine.results)
        }

    def get_recent_batches(self, limit: int = 10) -> list:
        """Get recent batch analysis results from database.

        Args:
            limit: Maximum number of batches to return

        Returns:
            List of batch analysis results
        """
        return self.db.get_batch_analysis_results(limit)

    def get_batch_details(self, batch_id: int) -> Dict[str, Any]:
        """Get detailed results for a specific batch.

        Args:
            batch_id: ID of the batch analysis

        Returns:
            Dictionary with batch info and pair results
        """
        batches = self.db.get_batch_analysis_results(limit=1000)
        batch_info = next((b for b in batches if b['batch_id'] == batch_id), None)

        if batch_info is None:
            raise ValueError(f"Batch {batch_id} not found")

        pair_results = self.db.get_batch_pair_results(batch_id)

        return {
            'batch_info': batch_info,
            'pair_results': pair_results,
            'total_pairs': len(pair_results)
        }

    def close(self):
        """Close database connection."""
        self.db.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run batch analysis and store results in validation database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s originals/ exported/
  %(prog)s originals/ exported/ --frames 500
  %(prog)s originals/ exported/ --run-id 5 --notes "Testing new driver"
  %(prog)s originals/ exported/ --no-heatmaps --no-comparisons  # Fast mode
        '''
    )

    parser.add_argument('dir_a', help="Directory with original SID files")
    parser.add_argument('dir_b', help="Directory with converted/exported SID files")

    parser.add_argument('-o', '--output', help="Output directory")
    parser.add_argument('-f', '--frames', type=int, default=300,
                       help="Frames to trace per file (default: 300)")

    parser.add_argument('--run-id', type=int,
                       help="Use existing validation run ID")
    parser.add_argument('--git-commit',
                       help="Git commit hash (auto-detected if not provided)")
    parser.add_argument('--notes',
                       help="Notes about this batch analysis")

    parser.add_argument('--no-heatmaps', action='store_true',
                       help="Skip heatmap generation (faster)")
    parser.add_argument('--no-comparisons', action='store_true',
                       help="Skip comparison HTML generation (faster)")

    parser.add_argument('-v', '--verbose', action='count', default=0,
                       help="Increase verbosity (-v, -vv)")

    parser.add_argument('--db-path',
                       help="Path to validation database (default: validation/database.sqlite)")

    args = parser.parse_args()

    # Validate directories
    dir_a = Path(args.dir_a)
    dir_b = Path(args.dir_b)

    if not dir_a.exists():
        print(f"[ERROR] Directory A not found: {args.dir_a}")
        return 1

    if not dir_b.exists():
        print(f"[ERROR] Directory B not found: {args.dir_b}")
        return 1

    # Set output directory
    output_dir = Path(args.output) if args.output else None

    # Set database path
    db_path = Path(args.db_path) if args.db_path else None

    # Run batch analysis with validation integration
    try:
        with ValidationBatchAnalyzer(db_path) as analyzer:
            result = analyzer.run_batch_analysis(
                dir_a=dir_a,
                dir_b=dir_b,
                output_dir=output_dir,
                frames=args.frames,
                generate_heatmaps=not args.no_heatmaps,
                generate_comparisons=not args.no_comparisons,
                run_id=args.run_id,
                git_commit=args.git_commit,
                notes=args.notes,
                verbose=args.verbose
            )

        print("\n" + "="*80)
        print("VALIDATION INTEGRATION COMPLETE")
        print("="*80)
        print(f"Batch ID:       {result['batch_id']}")
        print(f"Run ID:         {result['run_id']}")
        print(f"Total Pairs:    {result['total_pairs']}")
        print(f"Avg Accuracy:   {result['summary']['avg_frame_match']:.2f}%")
        print()
        print("Results stored in validation database:")
        print(f"  - Batch summary: batch_analysis_results table")
        print(f"  - {result['total_pairs']} pair results: batch_analysis_pair_results table")
        print(f"  - Metrics added to trends")
        print()
        print("Output files:")
        if result['output_paths']['html_report_path']:
            print(f"  - HTML: {result['output_paths']['html_report_path']}")
        if result['output_paths']['csv_path']:
            print(f"  - CSV:  {result['output_paths']['csv_path']}")
        if result['output_paths']['json_path']:
            print(f"  - JSON: {result['output_paths']['json_path']}")
        print()
        print("Next steps:")
        print("  - Run 'validation-dashboard.bat' to view results in dashboard")
        print("  - Check batch_analysis_results table for aggregate metrics")
        print("  - Check batch_analysis_pair_results table for per-pair details")
        print("="*80)

        return 0

    except Exception as e:
        print(f"\n[ERROR] Batch analysis failed: {e}")
        if args.verbose >= 1:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
