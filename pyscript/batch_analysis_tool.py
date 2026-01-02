#!/usr/bin/env python3
"""
Batch Analysis Tool - Compare multiple SID file pairs

Compares SID file pairs from two directories, generating:
- Individual heatmaps and comparison HTMLs
- Aggregate summary report (HTML + CSV + JSON)

Usage:
    python batch_analysis_tool.py dir_a/ dir_b/
    python batch_analysis_tool.py dir_a/ dir_b/ -o results/ --frames 500
    python batch_analysis_tool.py dir_a/ dir_b/ --no-heatmaps --no-comparisons

Version: 1.0.0
Date: 2026-01-01
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.batch_analysis_engine import BatchAnalysisEngine, BatchAnalysisConfig
from pyscript.batch_analysis_html_exporter import BatchAnalysisHTMLExporter


def main():
    parser = argparse.ArgumentParser(
        description="Batch analyze multiple SID file pairs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s originals/ exported/
  %(prog)s dir_a/ dir_b/ -o results/ --frames 500
  %(prog)s dir_a/ dir_b/ --no-heatmaps --no-comparisons  # Fast, metrics only

Output:
  - batch_summary.html (interactive report)
  - batch_results.csv (spreadsheet export)
  - batch_results.json (machine-readable)
  - heatmaps/ (individual heatmap HTMLs)
  - comparisons/ (individual comparison HTMLs)

File Pairing:
  Auto-pairs files by matching basenames:
  - song.sid <-> song_exported.sid
  - song.sid <-> song_laxity_exported.sid
  - song.sid <-> song.sf2_exported.sid
        '''
    )

    parser.add_argument('dir_a', help="Directory with original SID files")
    parser.add_argument('dir_b', help="Directory with converted/exported SID files")

    parser.add_argument('-o', '--output', default="batch_analysis_output",
                       help="Output directory (default: batch_analysis_output)")
    parser.add_argument('-f', '--frames', type=int, default=300,
                       help="Frames to trace per file (default: 300)")

    parser.add_argument('--no-heatmaps', action='store_true',
                       help="Skip heatmap generation (faster)")
    parser.add_argument('--no-comparisons', action='store_true',
                       help="Skip comparison HTML generation (faster)")
    parser.add_argument('--no-html', action='store_true',
                       help="Skip HTML summary report")
    parser.add_argument('--no-csv', action='store_true',
                       help="Skip CSV export")
    parser.add_argument('--no-json', action='store_true',
                       help="Skip JSON export")

    parser.add_argument('-v', '--verbose', action='count', default=0,
                       help="Increase verbosity (-v, -vv)")

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

    # Create config
    config = BatchAnalysisConfig(
        dir_a=dir_a,
        dir_b=dir_b,
        output_dir=Path(args.output),
        frames=args.frames,
        generate_heatmaps=not args.no_heatmaps,
        generate_comparisons=not args.no_comparisons,
        export_csv=not args.no_csv,
        export_json=not args.no_json,
        export_html=not args.no_html,
        verbose=args.verbose
    )

    # Print configuration
    print("\n" + "="*80)
    print("BATCH SID ANALYSIS")
    print("="*80)

    # Run batch analysis
    try:
        engine = BatchAnalysisEngine(config)
        summary = engine.run()

    except Exception as e:
        print(f"\n[ERROR] Batch analysis failed: {e}")
        if args.verbose >= 1:
            import traceback
            traceback.print_exc()
        return 1

    # Generate HTML summary report
    if config.export_html and summary.total_pairs > 0:
        print(f"\nGenerating HTML summary report...")

        html_path = config.output_dir / "batch_summary.html"

        try:
            exporter = BatchAnalysisHTMLExporter(engine.results, summary)
            if exporter.export(str(html_path)):
                summary.html_report_path = str(html_path.absolute())
                file_size = html_path.stat().st_size
                print(f"  [OK] HTML report generated: {html_path}")
                print(f"       Size: {file_size:,} bytes")
            else:
                print(f"  [ERROR] HTML report generation failed")

        except Exception as e:
            print(f"  [ERROR] HTML export failed: {e}")
            if args.verbose >= 1:
                import traceback
                traceback.print_exc()

    # Print summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    if summary.total_pairs == 0:
        print("No pairs analyzed.")
        return 0

    print(f"Total Pairs:        {summary.total_pairs}")
    print(f"Successful:         {summary.successful} ({summary.successful / summary.total_pairs * 100:.1f}%)")
    print(f"Failed:             {summary.failed}")
    if summary.partial > 0:
        print(f"Partial:            {summary.partial} (some outputs failed)")

    print(f"\nAccuracy:")
    print(f"  Avg Frame Match:  {summary.avg_frame_match:.2f}%")
    print(f"  Avg Register:     {summary.avg_register_accuracy:.2f}%")

    if summary.best_match_filename:
        print(f"  Best:             {summary.best_match_filename} ({summary.best_match_accuracy:.2f}%)")
        print(f"  Worst:            {summary.worst_match_filename} ({summary.worst_match_accuracy:.2f}%)")

    print(f"\nVoice Accuracy:")
    print(f"  Voice 1:          {summary.avg_voice1_accuracy:.2f}%")
    print(f"  Voice 2:          {summary.avg_voice2_accuracy:.2f}%")
    print(f"  Voice 3:          {summary.avg_voice3_accuracy:.2f}%")

    print(f"\nDuration:           {summary.total_duration:.1f} seconds ({summary.avg_duration_per_pair:.1f}s per pair)")

    print(f"\nOutput:")
    if summary.html_report_path:
        print(f"  HTML Report:      {summary.html_report_path}")
    if summary.csv_path:
        print(f"  CSV Export:       {summary.csv_path}")
    if summary.json_path:
        print(f"  JSON Export:      {summary.json_path}")

    if config.generate_heatmaps:
        heatmap_count = sum(1 for r in engine.results if r.heatmap_path)
        print(f"  Heatmaps:         {config.output_dir / 'heatmaps'} ({heatmap_count} files)")

    if config.generate_comparisons:
        comparison_count = sum(1 for r in engine.results if r.comparison_path)
        print(f"  Comparisons:      {config.output_dir / 'comparisons'} ({comparison_count} files)")

    # Interpretation
    print(f"\nInterpretation:")
    if summary.avg_frame_match >= 95.0:
        print("  [EXCELLENT] Very high accuracy across all pairs")
    elif summary.avg_frame_match >= 80.0:
        print("  [GOOD] Good accuracy, minor differences")
    elif summary.avg_frame_match >= 60.0:
        print("  [MODERATE] Some significant differences detected")
    else:
        print("  [POOR] Major differences, review individual reports")

    print("="*80)

    if summary.html_report_path:
        print(f"\nOpen {config.output_dir / 'batch_summary.html'} in browser to view interactive report!")

    return 0


if __name__ == '__main__':
    sys.exit(main())
