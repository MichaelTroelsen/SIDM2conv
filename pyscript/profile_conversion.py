#!/usr/bin/env python3
"""
Profile Conversion Pipeline Performance

Measures execution time for each stage of the SID to SF2 conversion pipeline
to identify performance bottlenecks.

Usage:
    python pyscript/profile_conversion.py input.sid
    python pyscript/profile_conversion.py input.sid --iterations 10
    python pyscript/profile_conversion.py --batch directory/
"""

import os
import sys
import time
import cProfile
import pstats
import io
from pathlib import Path
from typing import Dict, List, Tuple
import argparse

# Add parent directory to path
script_dir = Path(__file__).parent
parent_dir = script_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

# Import conversion components
from sidm2 import (
    PSIDHeader,
    SIDParser,
    LaxityPlayerAnalyzer,
    SF2Writer,
    ExtractedData,
)
from sidm2.sf2_player_parser import SF2PlayerParser
from sidm2.config import get_default_config


class ConversionProfiler:
    """Profile the SID to SF2 conversion pipeline"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.timings: Dict[str, List[float]] = {}

    def _time_operation(self, name: str, func, *args, **kwargs):
        """Time a single operation and record the result"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start_time

        if name not in self.timings:
            self.timings[name] = []
        self.timings[name].append(elapsed)

        if self.verbose:
            print(f"  [{name}] {elapsed*1000:.2f} ms")

        return result

    def profile_file(self, input_path: Path, driver_type: str = 'laxity') -> Dict:
        """Profile a single file conversion

        Args:
            input_path: Path to SID file
            driver_type: Driver type to use

        Returns:
            Dict with profiling results
        """
        if self.verbose:
            print(f"\nProfiling: {input_path.name}")
            print("=" * 60)

        total_start = time.perf_counter()

        # Stage 1: Parse SID header
        parser = self._time_operation(
            "1. Create SIDParser",
            SIDParser, str(input_path)
        )

        header = self._time_operation(
            "2. Parse PSID header",
            parser.parse_header
        )

        # Stage 2: Extract C64 data
        c64_data, load_address = self._time_operation(
            "3. Extract C64 data",
            parser.get_c64_data, header
        )

        # Stage 3: Detect player type
        is_sf2_exported = b'\x37\x13' in c64_data

        # Stage 4: Analyze music data
        if is_sf2_exported:
            analyzer = self._time_operation(
                "4. Create SF2PlayerParser",
                SF2PlayerParser, str(input_path), None
            )
            extracted = self._time_operation(
                "5. Extract SF2 music data",
                analyzer.extract
            )
        else:
            analyzer = self._time_operation(
                "4. Create LaxityPlayerAnalyzer",
                LaxityPlayerAnalyzer, c64_data, load_address, header
            )
            extracted = self._time_operation(
                "5. Extract Laxity music data",
                analyzer.extract_music_data
            )

        # Stage 5: Write SF2 file
        output_path = input_path.parent / f"{input_path.stem}_profile.sf2"

        writer = self._time_operation(
            "6. Create SF2Writer",
            SF2Writer, extracted, driver_type
        )

        self._time_operation(
            "7. Write SF2 file",
            writer.write, str(output_path)
        )

        # Cleanup
        if output_path.exists():
            output_path.unlink()

        total_elapsed = time.perf_counter() - total_start

        if self.verbose:
            print("=" * 60)
            print(f"Total time: {total_elapsed*1000:.2f} ms")

        return {
            'total_time': total_elapsed,
            'stages': dict(self.timings),
            'file_size': len(c64_data),
            'is_sf2_exported': is_sf2_exported,
        }

    def profile_batch(self, files: List[Path], driver_type: str = 'laxity') -> Dict:
        """Profile batch conversion

        Args:
            files: List of SID files to profile
            driver_type: Driver type to use

        Returns:
            Dict with batch profiling results
        """
        print(f"\nBatch Profiling: {len(files)} files")
        print("=" * 60)

        batch_start = time.perf_counter()
        results = []

        for i, file_path in enumerate(files, 1):
            print(f"\n[{i}/{len(files)}] {file_path.name}")
            try:
                result = self.profile_file(file_path, driver_type)
                results.append({
                    'file': file_path.name,
                    'success': True,
                    **result
                })
            except Exception as e:
                print(f"  ERROR: {e}")
                results.append({
                    'file': file_path.name,
                    'success': False,
                    'error': str(e)
                })

        batch_elapsed = time.perf_counter() - batch_start

        # Calculate statistics
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]

        print("\n" + "=" * 60)
        print("BATCH PROFILING RESULTS")
        print("=" * 60)
        print(f"Total files:     {len(files)}")
        print(f"Successful:      {len(successful)}")
        print(f"Failed:          {len(failed)}")
        print(f"Batch time:      {batch_elapsed:.2f}s")
        print(f"Avg per file:    {batch_elapsed/len(files):.3f}s")

        if successful:
            avg_times = {}
            for stage in self.timings:
                avg_times[stage] = sum(self.timings[stage]) / len(self.timings[stage])

            print("\nAverage Stage Times:")
            total_stage_time = 0
            for stage, avg_time in sorted(avg_times.items()):
                print(f"  {stage:30s}: {avg_time*1000:8.2f} ms")
                total_stage_time += avg_time

            print(f"  {'Total measured':30s}: {total_stage_time*1000:8.2f} ms")

            # Identify bottlenecks
            print("\nBottleneck Analysis:")
            sorted_stages = sorted(avg_times.items(), key=lambda x: x[1], reverse=True)
            for i, (stage, avg_time) in enumerate(sorted_stages[:3], 1):
                percent = (avg_time / total_stage_time) * 100 if total_stage_time > 0 else 0
                print(f"  {i}. {stage}: {avg_time*1000:.2f} ms ({percent:.1f}%)")

        return {
            'batch_time': batch_elapsed,
            'total_files': len(files),
            'successful': len(successful),
            'failed': len(failed),
            'results': results,
            'stage_averages': avg_times if successful else {}
        }

    def profile_with_cprofile(self, input_path: Path, driver_type: str = 'laxity'):
        """Profile with cProfile for detailed function-level analysis

        Args:
            input_path: Path to SID file
            driver_type: Driver type to use
        """
        print(f"\nDetailed Function Profiling: {input_path.name}")
        print("=" * 60)

        profiler = cProfile.Profile()
        profiler.enable()

        # Run conversion
        self.profile_file(input_path, driver_type)

        profiler.disable()

        # Print results
        s = io.StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.strip_dirs()
        ps.sort_stats('cumulative')
        ps.print_stats(30)  # Top 30 functions

        print("\nTop 30 Functions by Cumulative Time:")
        print(s.getvalue())


def find_test_files(directory: Path, pattern: str = "*.sid", limit: int = 10) -> List[Path]:
    """Find test SID files in a directory

    Args:
        directory: Directory to search
        pattern: File pattern (default: *.sid)
        limit: Maximum number of files to return

    Returns:
        List of Path objects
    """
    files = list(directory.glob(pattern))
    return files[:limit] if limit else files


def main():
    parser = argparse.ArgumentParser(
        description='Profile SID to SF2 conversion performance',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        'input',
        help='Input SID file or directory for batch profiling'
    )
    parser.add_argument(
        '--driver',
        choices=['laxity', 'driver11', 'np20'],
        default='laxity',
        help='Driver type to use (default: laxity)'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=1,
        help='Number of iterations to run (default: 1)'
    )
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Batch mode: profile all SID files in directory'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Limit number of files in batch mode (default: 10)'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Run detailed cProfile analysis'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode (less verbose output)'
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input not found: {input_path}")
        sys.exit(1)

    profiler = ConversionProfiler(verbose=not args.quiet)

    try:
        if args.batch or input_path.is_dir():
            # Batch profiling
            if input_path.is_dir():
                files = find_test_files(input_path, limit=args.limit)
            else:
                print(f"Error: {input_path} is not a directory")
                sys.exit(1)

            if not files:
                print(f"Error: No SID files found in {input_path}")
                sys.exit(1)

            profiler.profile_batch(files, driver_type=args.driver)

        else:
            # Single file profiling
            if args.detailed:
                profiler.profile_with_cprofile(input_path, driver_type=args.driver)
            else:
                for i in range(args.iterations):
                    if args.iterations > 1:
                        print(f"\n=== Iteration {i+1}/{args.iterations} ===")
                    profiler.profile_file(input_path, driver_type=args.driver)

                if args.iterations > 1:
                    # Print summary
                    print("\n" + "=" * 60)
                    print(f"SUMMARY ({args.iterations} iterations)")
                    print("=" * 60)
                    for stage, times in profiler.timings.items():
                        avg = sum(times) / len(times)
                        min_time = min(times)
                        max_time = max(times)
                        print(f"{stage:30s}: avg={avg*1000:6.2f}ms  min={min_time*1000:6.2f}ms  max={max_time*1000:6.2f}ms")

    except KeyboardInterrupt:
        print("\n\nProfiling interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError during profiling: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
