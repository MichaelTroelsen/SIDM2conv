#!/usr/bin/env python3
"""
Accuracy Heatmap Tool - Visualize frame-by-frame register accuracy

Compares two SID files by executing them and generating an interactive
heatmap showing register-level accuracy across all frames. Supports 4
visualization modes with Canvas-based rendering.

Usage:
    python accuracy_heatmap_tool.py file_a.sid file_b.sid
    python accuracy_heatmap_tool.py file_a.sid file_b.sid --frames 1500
    python accuracy_heatmap_tool.py file_a.sid file_b.sid --output heatmap.html -v

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
from pyscript.accuracy_heatmap_generator import HeatmapGenerator
from pyscript.accuracy_heatmap_exporter import AccuracyHeatmapExporter


def setup_logging(verbose: int):
    """Setup logging based on verbosity level."""
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
        description="Generate accuracy heatmap comparing two SID files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s original.sid converted.sid
  %(prog)s a.sid b.sid --frames 1500
  %(prog)s a.sid b.sid --output heatmap.html -v

Visualization Modes:
  Mode 1: Binary Match/Mismatch (green=match, red=mismatch)
  Mode 2: Value Delta Magnitude (color intensity by difference)
  Mode 3: Register Group Highlighting (different colors for Voice 1/2/3/Filter)
  Mode 4: Frame Accuracy Summary (color by per-frame accuracy %)

Output:
  Generates interactive HTML with:
    - Canvas-based heatmap (frames × 29 registers)
    - 4 visualization modes (switchable)
    - Hover tooltips (show exact values)
    - Zoom controls
    - Accuracy statistics

Interpretation:
  - Green cells: Values match perfectly
  - Red cells: Values differ
  - Vertical lines: Consistent register differences across frames
  - Horizontal lines: Frame-specific issues affecting all registers
  - Clusters: Localized accuracy problems
        '''
    )

    parser.add_argument('file_a', help="First SID file to compare")
    parser.add_argument('file_b', help="Second SID file to compare")

    parser.add_argument('-f', '--frames', type=int, default=300,
                       help="Number of frames to trace (default: 300)")
    parser.add_argument('-o', '--output', default=None,
                       help="Output HTML file (default: heatmap_<timestamp>.html)")
    parser.add_argument('-m', '--mode', type=int, default=1, choices=[1,2,3,4],
                       help="Default visualization mode (1=Match/Mismatch, 2=Delta, 3=Groups, 4=Frame%%, default: 1)")
    parser.add_argument('-v', '--verbose', action='count', default=0,
                       help="Increase verbosity (-v, -vv)")

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

    # Generate heatmap data
    print("Generating heatmap data...")

    try:
        generator = HeatmapGenerator(
            trace_a, trace_b, comparison,
            filename_a=path_a.name,
            filename_b=path_b.name
        )
        heatmap_data = generator.generate()

        print(f"  Grid: {heatmap_data.frames} frames × {heatmap_data.registers} registers ({heatmap_data.total_comparisons:,} cells)")
        print(f"  Matches: {heatmap_data.total_matches:,} / {heatmap_data.total_comparisons:,} ({heatmap_data.overall_accuracy:.2f}%)")

    except Exception as e:
        print(f"[ERROR] Failed to generate heatmap data: {e}")
        if args.verbose >= 2:
            import traceback
            traceback.print_exc()
        return 1

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f"heatmap_{timestamp}.html"

    # Export to HTML
    print(f"\nGenerating HTML heatmap: {output_path}")

    try:
        exporter = AccuracyHeatmapExporter(heatmap_data)

        if exporter.export(output_path):
            file_size = Path(output_path).stat().st_size
            print(f"[OK] Heatmap generated: {output_path}")
            print(f"     Size: {file_size:,} bytes")
            print(f"\nOpen in browser to visualize accuracy patterns!")
            print(f"  - Mode 1: Binary Match/Mismatch")
            print(f"  - Mode 2: Value Delta Magnitude")
            print(f"  - Mode 3: Register Group Highlighting")
            print(f"  - Mode 4: Frame Accuracy Summary")
        else:
            print("[ERROR] Failed to generate HTML heatmap")
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
