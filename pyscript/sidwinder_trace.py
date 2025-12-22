"""
SIDwinder Trace - Command-line interface for SID tracing

This provides a command-line interface compatible with SIDwinder.exe
for generating SID register write traces.

Usage:
    python sidwinder_trace.py -trace=<output> -frames=<count> <input>
    python sidwinder_trace.py --trace <output> --frames <count> <input>

Part of the Python SIDwinder replacement project (v2.8.0).
"""

import argparse
import sys
import logging
from pathlib import Path

# Add parent directory to path
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pyscript.sidtracer import SIDTracer
from pyscript.trace_formatter import TraceFormatter


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Python SIDwinder - C64 SID Register Trace Tool',
        epilog='Part of SIDM2 - SID to SF2 Converter (v2.8.0)'
    )

    # Trace output
    parser.add_argument(
        '-trace', '--trace',
        dest='trace_output',
        metavar='FILE',
        help='Generate trace output to FILE'
    )

    # Frame count
    parser.add_argument(
        '-frames', '--frames',
        type=int,
        default=1500,
        help='Number of frames to trace (default: 1500 = 30s @ 50Hz PAL)'
    )

    # Input file
    parser.add_argument(
        'input',
        help='Input SID file'
    )

    # Verbosity
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='Increase verbosity (can be used multiple times: -v, -vv)'
    )

    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress all output except errors'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.trace_output:
        parser.error("Trace output file required (-trace=FILE or --trace FILE)")

    return args


def main():
    """Main entry point."""
    args = parse_arguments()

    # Setup logging
    if args.quiet:
        log_level = logging.ERROR
        verbose = 0
    elif args.verbose >= 2:
        log_level = logging.DEBUG
        verbose = 2
    elif args.verbose >= 1:
        log_level = logging.INFO
        verbose = 1
    else:
        log_level = logging.WARNING
        verbose = 0

    logging.basicConfig(
        level=log_level,
        format='%(message)s'
    )

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        return 1

    # Validate output path
    output_path = Path(args.trace_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if not args.quiet:
            print(f"Python SIDwinder v2.8.0 - Trace Mode")
            print(f"Input:  {input_path}")
            print(f"Output: {output_path}")
            print(f"Frames: {args.frames}")
            print()

        # Create tracer
        tracer = SIDTracer(input_path, verbose=verbose)

        if not args.quiet:
            print(f"SID: {tracer.header.name}")
            if tracer.header.author:
                print(f"Author: {tracer.header.author}")
            print()

        # Generate trace
        if not args.quiet:
            print(f"Tracing {args.frames} frames...")

        trace_data = tracer.trace(frames=args.frames)

        # Write output
        if not args.quiet:
            print(f"Writing trace to {output_path}...")

        TraceFormatter.write_trace_file(trace_data, output_path)

        # Print summary
        if not args.quiet:
            print()
            print(TraceFormatter.format_trace_summary(trace_data))
            print()
            print(f"Output: {output_path} ({output_path.stat().st_size:,} bytes)")
            print()
            print("Done!")

        return 0

    except KeyboardInterrupt:
        print("\nInterrupted!", file=sys.stderr)
        return 130

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose >= 2:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
