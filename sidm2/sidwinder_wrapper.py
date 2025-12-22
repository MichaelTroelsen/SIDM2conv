"""
SIDwinder Wrapper Module

Provides Python interface to SIDwinder (Python or .exe) for SID register
tracing and validation.

Now uses native Python SIDwinder with automatic fallback to .exe.

Based on SIDwinder 0.2.6 by Stein Pedersen/Prosonix
Python implementation: 100% compatible cross-platform version (v2.8.0)
"""

import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Add parent directory and pyscript to path for importing Python SIDwinder components
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(parent_dir / "pyscript"))

logger = logging.getLogger(__name__)


class SIDwinderWrapper:
    """
    Wrapper for SIDwinder (Python or .exe) for SID register tracing

    Provides:
    - Frame-by-frame SID register write tracing
    - SIDwinder-compatible text format output
    - Cross-platform support (Python) or Windows .exe fallback
    - Automated error handling and reporting

    By default, uses the Python SIDwinder implementation for cross-platform
    compatibility. Falls back to .exe if Python version fails or if explicitly
    requested via use_python=False.
    """

    def __init__(self,
                 sidwinder_path: str = "tools/SIDwinder.exe",
                 use_python: bool = True):
        """
        Initialize SIDwinder wrapper

        Args:
            sidwinder_path: Path to SIDwinder.exe (fallback)
            use_python: Use Python SIDwinder (default: True)
        """
        self.exe = Path(sidwinder_path)
        self.use_python = use_python
        self.python_available = False

        # Try to import Python SIDwinder components
        if use_python:
            try:
                from pyscript.sidtracer import SIDTracer
                from pyscript.trace_formatter import TraceFormatter
                self.SIDTracer = SIDTracer
                self.TraceFormatter = TraceFormatter
                self.python_available = True
                logger.debug("Python SIDwinder loaded successfully")
            except ImportError as e:
                logger.warning(f"Python SIDwinder not available: {e}")
                self.python_available = False

        # Check if at least one method is available
        if not self.exe.exists() and not self.python_available:
            raise FileNotFoundError(
                f"Neither Python SIDwinder nor .exe found at {self.exe}"
            )

    def trace(self,
              sid_file: Path,
              output_file: Path,
              frames: int = 1500,
              verbose: int = 0) -> Dict[str, Any]:
        """
        Generate SID register trace

        Args:
            sid_file: Path to input SID file
            output_file: Path to output trace file (.txt)
            frames: Number of frames to trace (default: 1500 = 30s @ 50Hz)
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)

        Returns:
            Dict with:
                'success': bool - Whether trace succeeded
                'method': str - 'python' or 'exe'
                'output': Path - Output file path
                'frames': int - Number of frames traced
                'writes': int - Total SID register writes
                'error': str - Error message if failed
        """
        sid_file = Path(sid_file)
        output_file = Path(output_file)

        # Validate input
        if not sid_file.exists():
            return {
                'success': False,
                'method': None,
                'output': output_file,
                'error': f"Input file not found: {sid_file}"
            }

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Try Python version first
        if self.use_python and self.python_available:
            try:
                return self._trace_python(sid_file, output_file, frames, verbose)
            except Exception as e:
                logger.warning(f"Python SIDwinder failed: {e}, trying .exe")
                # Fall through to .exe

        # Fall back to .exe
        if self.exe.exists():
            return self._trace_exe(sid_file, output_file, frames, verbose)
        else:
            return {
                'success': False,
                'method': None,
                'output': output_file,
                'error': "No working SIDwinder implementation available"
            }

    def _trace_python(self,
                     sid_file: Path,
                     output_file: Path,
                     frames: int,
                     verbose: int) -> Dict[str, Any]:
        """
        Generate trace using Python SIDwinder

        Returns:
            Result dictionary
        """
        try:
            # Create tracer
            tracer = self.SIDTracer(sid_file, verbose=verbose)

            # Generate trace
            trace_data = tracer.trace(frames=frames)

            # Write output
            self.TraceFormatter.write_trace_file(trace_data, output_file)

            # Calculate total writes
            total_writes = len(trace_data.init_writes) + sum(
                len(fw) for fw in trace_data.frame_writes
            )

            return {
                'success': True,
                'method': 'python',
                'output': output_file,
                'frames': trace_data.frames,
                'cycles': trace_data.cycles,
                'writes': total_writes,
                'sid_name': trace_data.header.name if trace_data.header else None,
                'error': None
            }

        except Exception as e:
            logger.error(f"Python SIDwinder trace failed: {e}")
            raise

    def _trace_exe(self,
                  sid_file: Path,
                  output_file: Path,
                  frames: int,
                  verbose: int) -> Dict[str, Any]:
        """
        Generate trace using SIDwinder.exe

        Returns:
            Result dictionary
        """
        try:
            # Build command
            cmd = [
                str(self.exe.absolute()),
                f'-trace={output_file.absolute()}',
                f'-frames={frames}',
                str(sid_file.absolute())
            ]

            if verbose >= 2:
                logger.debug(f"Running: {' '.join(cmd)}")

            # Run SIDwinder.exe
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes max
            )

            # Check if output file was created
            # Note: SIDwinder.exe may return non-zero even on success
            if output_file.exists() and output_file.stat().st_size > 0:
                # Count frames in output
                with open(output_file, 'r') as f:
                    frame_count = sum(1 for line in f if line.startswith('FRAME:'))

                return {
                    'success': True,
                    'method': 'exe',
                    'output': output_file,
                    'frames': frame_count,
                    'writes': None,  # Can't easily count from .exe output
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'method': 'exe',
                    'output': output_file,
                    'error': f"SIDwinder.exe failed: {result.stderr or 'No output generated'}"
                }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'method': 'exe',
                'output': output_file,
                'error': "SIDwinder.exe timed out (>120s)"
            }
        except Exception as e:
            return {
                'success': False,
                'method': 'exe',
                'output': output_file,
                'error': f"SIDwinder.exe execution failed: {e}"
            }


# Convenience function for direct usage
def trace_sid(sid_file: Path,
              output_file: Path,
              frames: int = 1500,
              use_python: bool = True,
              verbose: int = 0) -> Dict[str, Any]:
    """
    Convenience function to trace a SID file

    Args:
        sid_file: Path to input SID file
        output_file: Path to output trace file
        frames: Number of frames to trace (default: 1500)
        use_python: Use Python implementation (default: True)
        verbose: Verbosity level (0-2)

    Returns:
        Result dictionary with success status and details
    """
    wrapper = SIDwinderWrapper(use_python=use_python)
    return wrapper.trace(sid_file, output_file, frames, verbose)


if __name__ == "__main__":
    # Simple test
    import sys

    if len(sys.argv) < 3:
        print("Usage: python sidwinder_wrapper.py <input.sid> <output.txt> [frames]")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    sid_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    frames = int(sys.argv[3]) if len(sys.argv) > 3 else 100

    result = trace_sid(sid_file, output_file, frames, use_python=True, verbose=1)

    if result['success']:
        print(f"\n[OK] Success ({result['method']})")
        print(f"  Output: {result['output']}")
        print(f"  Frames: {result.get('frames', 'N/A')}")
        if result.get('writes'):
            print(f"  Writes: {result['writes']}")
    else:
        print(f"\n[FAIL] Failed: {result['error']}")
        sys.exit(1)
