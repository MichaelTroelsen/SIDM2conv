"""
SIDDUMP Integration for Pipeline Phase 5

Generates frame-by-frame SID register dumps for validation and analysis.
Integrated into conversion pipeline as optional analysis tool.

Usage:
    from sidm2.siddump_integration import SiddumpIntegration

    result = SiddumpIntegration.generate_dump(
        sid_file=Path("input.sid"),
        output_dir=Path("analysis"),
        duration=30
    )
"""

__version__ = "1.0.0"
__date__ = "2025-12-24"

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from sidm2.siddump import extract_from_siddump

logger = logging.getLogger(__name__)


class SiddumpIntegration:
    """Integration wrapper for siddump frame-by-frame analysis"""

    @staticmethod
    def generate_dump(
        sid_file: Path,
        output_dir: Path,
        duration: int = 30,
        use_python: bool = True,
        verbose: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Generate siddump output for SID file.

        Args:
            sid_file: Path to SID file
            output_dir: Directory for output files
            duration: Playback duration in seconds
            use_python: Use Python siddump (default: True)
            verbose: Verbosity level

        Returns:
            Dictionary with result information or None on failure
        """
        try:
            # Ensure output directory exists
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate dump filename
            dump_file = output_dir / f"{sid_file.stem}.dump"

            if verbose > 0:
                print(f"  Generating siddump: {dump_file.name}")
                print(f"    Duration: {duration}s")
                print(f"    Engine:   {'Python' if use_python else 'C exe'}")

            # Run siddump and capture output
            result_data = extract_from_siddump(
                str(sid_file),
                playback_time=duration,
                use_python=use_python
            )

            if not result_data:
                logger.warning(f"Siddump extraction failed for {sid_file.name}")
                return None

            # Write dump output to file
            # The dump format is: frame-by-frame SID register writes
            # We'll use the Python siddump to generate the output
            try:
                from pyscript.siddump_complete import main as siddump_main
                import sys
                import io

                # Capture stdout
                old_stdout = sys.stdout
                old_argv = sys.argv
                sys.stdout = captured_output = io.StringIO()

                try:
                    # Run siddump with output to stdout
                    sys.argv = ['siddump', str(sid_file), f'-t{duration}']
                    siddump_main()
                    dump_content = captured_output.getvalue()
                finally:
                    sys.stdout = old_stdout
                    sys.argv = old_argv

                # Write to file
                dump_file.write_text(dump_content, encoding='utf-8')
            except Exception as e:
                logger.error(
                    f"Failed to run Python siddump: {e}\n"
                    f"  Suggestion: Python siddump execution failed\n"
                    f"  Check: Verify SID file is valid and readable\n"
                    f"  Try: Test SID file in VICE emulator first\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#siddump-errors"
                )
                # Fallback: create minimal dump file
                dump_content = f"# Siddump failed: {e}\n"
                dump_file.write_text(dump_content, encoding='utf-8')
                return None

            # Count frames
            frame_count = dump_content.count('FRAME:')

            return {
                'success': True,
                'dump_file': dump_file,
                'duration': duration,
                'frames': frame_count,
                'file_size': dump_file.stat().st_size,
                'adsr_count': len(result_data.get('adsr_values', [])),
                'waveform_count': len(result_data.get('waveforms', []))
            }

        except Exception as e:
            logger.error(
                f"Siddump generation failed: {e}\n"
                f"  Suggestion: Failed to generate siddump output\n"
                f"  Check: Verify SID file is valid and readable\n"
                f"  Try: Check output directory is writable\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#siddump-generation-errors"
            )
            return None


def generate_siddump(sid_file: Path, output_dir: Path, duration: int = 30) -> Optional[Dict[str, Any]]:
    """
    Convenience function for generating siddump output.

    Args:
        sid_file: Path to SID file
        output_dir: Directory for output files
        duration: Playback duration in seconds

    Returns:
        Result dictionary or None on failure
    """
    return SiddumpIntegration.generate_dump(sid_file, output_dir, duration)
