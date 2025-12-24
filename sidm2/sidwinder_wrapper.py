"""
SIDwinder Integration Wrapper - Integrates SIDwinder tracing into conversion pipeline

This module provides a clean interface to integrate SIDwinder tracing as an optional
step (Step 7.5) in the conversion pipeline.

Part of SIDM2 Enhanced Pipeline (v2.0.0).
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from pyscript.sidtracer import SIDTracer, TraceData
from pyscript.trace_formatter import TraceFormatter

logger = logging.getLogger(__name__)


class SIDwinderIntegration:
    """Integration layer for SIDwinder tracing in conversion pipeline."""

    @staticmethod
    def trace_sid(
        sid_file: Path,
        output_dir: Path,
        frames: int = 1500,
        verbose: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Generate SIDwinder trace for a SID file.

        This is Step 7.5 in the enhanced pipeline - optional detailed tracing.

        Args:
            sid_file: Path to input SID file
            output_dir: Output directory for trace file
            frames: Number of frames to trace (default 1500 = 30s @ 50Hz)
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)

        Returns:
            Dictionary with trace results:
            {
                'success': True/False,
                'trace_file': Path to output trace file,
                'frames': Number of frames traced,
                'writes': Total SID register writes,
                'cycles': CPU cycles processed,
                'file_size': Bytes in trace file
            }
            Returns None on error.

        Example:
            result = SIDwinderIntegration.trace_sid(
                Path('input.sid'),
                Path('output'),
                frames=1500,
                verbose=1
            )
            if result['success']:
                print(f"Traced {result['writes']} register writes")
        """
        try:
            sid_file = Path(sid_file)
            output_dir = Path(output_dir)

            # Validate input file
            if not sid_file.exists():
                logger.error(f"SID file not found: {sid_file}")
                return None

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate output filename
            trace_file = output_dir / f"{sid_file.stem}_trace.txt"

            if verbose >= 1:
                logger.info(f"[Step 7.5] SIDwinder Trace - Starting")
                logger.info(f"  Input:  {sid_file}")
                logger.info(f"  Output: {trace_file}")
                logger.info(f"  Frames: {frames}")

            # Create tracer
            tracer = SIDTracer(sid_file, verbose=verbose - 1 if verbose > 0 else 0)

            # Generate trace
            if verbose >= 1:
                logger.info(f"  Tracing {frames} frames...")

            trace_data = tracer.trace(frames=frames)

            # Write trace to file
            if verbose >= 1:
                logger.info(f"  Writing trace to {trace_file.name}...")

            TraceFormatter.write_trace_file(trace_data, trace_file)

            # Get file size
            file_size = trace_file.stat().st_size

            if verbose >= 1:
                logger.info(f"[Step 7.5] Complete - {len(trace_data.init_writes)} init + "
                           f"{sum(len(fw) for fw in trace_data.frame_writes)} frame writes "
                           f"({file_size:,} bytes)")

            return {
                'success': True,
                'trace_file': trace_file,
                'frames': trace_data.frames,
                'cycles': trace_data.cycles,
                'writes': len(trace_data.init_writes) + sum(len(fw) for fw in trace_data.frame_writes),
                'file_size': file_size
            }

        except Exception as e:
            logger.error(f"SIDwinder trace failed: {e}")
            if verbose >= 2:
                import traceback
                traceback.print_exc()
            return None


def trace_sid(
    sid_file: Path,
    output_dir: Path,
    frames: int = 1500,
    verbose: int = 0
) -> Optional[Dict[str, Any]]:
    """Convenience function to trace a SID file.

    Args:
        sid_file: Path to input SID file
        output_dir: Output directory for trace file
        frames: Number of frames to trace (default 1500)
        verbose: Verbosity level (0=quiet, 1=normal, 2=debug)

    Returns:
        Dictionary with trace results or None on error
    """
    return SIDwinderIntegration.trace_sid(sid_file, output_dir, frames, verbose)


__all__ = ['SIDwinderIntegration', 'trace_sid']
