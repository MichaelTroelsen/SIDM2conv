#!/usr/bin/env python3
"""
Trace Comparison Tool - Compare two SID files trace-by-trace

Compares two SID files by executing them and comparing their SID register
writes frame-by-frame. Generates interactive HTML report with tabbed interface.

Usage:
    python trace_comparison_tool.py file_a.sid file_b.sid
    python trace_comparison_tool.py file_a.sid file_b.sid --frames 1500
    python trace_comparison_tool.py file_a.sid file_b.sid --output comparison.html -v

Version: 1.0.0
Date: 2026-01-01
"""

import argparse
import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.sidtracer import SIDTracer
from pyscript.trace_comparator import TraceComparator
from pyscript.trace_comparison_html_exporter import TraceComparisonHTMLExporter


def setup_logging(verbose: int):
    """Setup logging based on verbosity level"""
    if verbose >= 2:
        level = logging.DEBUG
    elif verbose >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format='[%(levelname)s] %(message)s'
    )


def main():
    parser = argparse.ArgumentParser(
        description="Compare SID execution traces and generate interactive HTML report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s original.sid converted.sid
  %(prog)s a.sid b.sid --frames 1500
  %(prog)s a.sid b.sid --output comparison.html -v
  %(prog)s a.sid b.sid --no-html  # Quick comparison, no HTML

Output:
  Generates interactive HTML with 3 tabs:
    - File A: Trace visualization for first file
    - File B: Trace visualization for second file
    - Differences: Side-by-side diff with color coding

Metrics displayed:
  - Frame Match %%: Percentage of identical frames
  - Register Accuracy: Per-register match percentage
  - Voice Accuracy: Per-voice frequency/waveform/ADSR accuracy
  - Total Diffs: Count of all register write differences
        '''
    )

    parser.add_argument('file_a', help="First SID file to compare")
    parser.add_argument('file_b', help="Second SID file to compare")

    parser.add_argument('-f', '--frames', type=int, default=300,
                       help="Number of frames to trace (default: 300)")
    parser.add_argument('-o', '--output', default=None,
                       help="Output HTML file (default: comparison_<timestamp>.html)")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                       help="Increase verbosity (-v, -vv)")
    parser.add_argument('--no-html', action='store_true',
                       help="Skip HTML generation (useful for quick comparisons)")

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Validate input files
    path_a = Path(args.file_a)
    path_b = Path(args.file_b)

    if not path_a.exists():
        print(f"[ERROR] File not found: {args.file_a}")
        return 1

    if not path_b.exists():
        print(f"[ERROR] File not found: {args.file_b}")
        return 1

    # Trace both files
    print(f"\nTracing File A: {args.file_a}")
    print(f"  Frames: {args.frames}")

    try:
        tracer_a = SIDTracer(path_a, verbose=args.verbose)
        trace_a = tracer_a.trace(frames=args.frames)
        print(f"  [OK] Traced {trace_a.frames} frames, {trace_a.cycles:,} cycles")
    except Exception as e:
        print(f"[ERROR] Failed to trace File A: {e}")
        if args.verbose >= 2:
            import traceback
            traceback.print_exc()
        return 1

    print(f"\nTracing File B: {args.file_b}")
    print(f"  Frames: {args.frames}")

    try:
        tracer_b = SIDTracer(path_b, verbose=args.verbose)
        trace_b = tracer_b.trace(frames=args.frames)
        print(f"  [OK] Traced {trace_b.frames} frames, {trace_b.cycles:,} cycles")
    except Exception as e:
        print(f"[ERROR] Failed to trace File B: {e}")
        if args.verbose >= 2:
            import traceback
            traceback.print_exc()
        return 1

    # Compare traces
    print("\nComparing traces...")

    try:
        comparator = TraceComparator(trace_a, trace_b)
        comparison = comparator.compare()
    except Exception as e:
        print(f"[ERROR] Failed to compare traces: {e}")
        if args.verbose >= 2:
            import traceback
            traceback.print_exc()
        return 1

    # Print summary
    print("\n" + "="*80)
    print("COMPARISON SUMMARY")
    print("="*80)
    print(f"Frame Match:        {comparison.frame_match_percent:.2f}% ({int(comparison.frame_match_percent * len(comparison.per_frame_accuracy) / 100)} / {len(comparison.per_frame_accuracy)} frames)")
    print(f"Register Accuracy:  {comparison.register_accuracy_overall:.2f}%")

    print(f"Voice Accuracies:")
    for voice in [1, 2, 3]:
        acc = comparison.voice_accuracy[voice]
        print(f"  Voice {voice}:        {acc['overall']:.2f}% (Freq:{acc['frequency']:.1f}%, Wave:{acc['waveform']:.1f}%, ADSR:{acc['adsr']:.1f}%, Pulse:{acc['pulse']:.1f}%)")

    print(f"\nTotal Differences:  {comparison.total_diff_count:,}")
    print(f"  Init phase:       {comparison.init_diff_count:,}")
    print(f"  Frame phase:      {comparison.frame_diff_count:,}")

    # Frame count match
    if not comparison.frame_count_match:
        print(f"\n[WARNING] Frame count mismatch: {trace_a.frames} vs {trace_b.frames}")

    # Interpretation hint
    print("\nInterpretation:")
    if comparison.frame_match_percent == 100.0 and comparison.total_diff_count == 0:
        print("  [PERFECT] Files are identical")
    elif comparison.frame_match_percent >= 95.0:
        print("  [EXCELLENT] Very high accuracy")
    elif comparison.frame_match_percent >= 90.0:
        print("  [GOOD] Minor differences")
    elif comparison.frame_match_percent >= 70.0:
        print("  [MODERATE] Some significant differences")
    else:
        print("  [POOR] Major differences detected")

    print("="*80)

    # Generate HTML
    if not args.no_html:
        # Determine output path
        if args.output:
            output_path = args.output
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"comparison_{timestamp}.html"

        print(f"\nGenerating HTML report: {output_path}")

        try:
            exporter = TraceComparisonHTMLExporter(
                trace_a, trace_b, comparison,
                path_a.name,
                path_b.name
            )

            if exporter.export(output_path):
                file_size = Path(output_path).stat().st_size
                print(f"[OK] HTML report generated: {output_path}")
                print(f"     Size: {file_size:,} bytes")
                print(f"\nOpen in browser to view interactive comparison!")
            else:
                print("[ERROR] Failed to generate HTML report")
                return 1

        except Exception as e:
            print(f"[ERROR] Failed to export HTML: {e}")
            if args.verbose >= 2:
                import traceback
                traceback.print_exc()
            return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
