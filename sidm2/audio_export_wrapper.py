"""
Audio Export Integration for SID Conversion Pipeline - Phase 2

Integrates SID2WAV.EXE into the conversion pipeline as Step 16.
Exports SID files to WAV audio for reference listening.

Usage:
    from sidm2.audio_export_wrapper import AudioExportIntegration

    result = AudioExportIntegration.export_to_wav(
        sid_file=Path("input.sid"),
        output_file=Path("output.wav"),
        duration=30,
        verbose=1
    )
"""

__version__ = "1.0.0"
__date__ = "2025-12-24"

import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AudioExportIntegration:
    """Integration wrapper for SID2WAV audio export in conversion pipeline"""

    # Tool configuration
    SID2WAV_EXE = "tools/SID2WAV.EXE"

    # Default settings
    DEFAULT_DURATION = 30  # seconds
    DEFAULT_FREQUENCY = 44100  # Hz
    DEFAULT_BIT_DEPTH = 16  # bits
    DEFAULT_FADE_OUT = 2  # seconds

    @staticmethod
    def _check_tool_available() -> bool:
        """
        Check if SID2WAV.EXE is available.

        Returns:
            True if tool exists, False otherwise
        """
        tool_path = Path(AudioExportIntegration.SID2WAV_EXE)
        return tool_path.exists()

    @staticmethod
    def export_to_wav(
        sid_file: Path,
        output_file: Path,
        duration: int = DEFAULT_DURATION,
        frequency: int = DEFAULT_FREQUENCY,
        bit_depth: int = DEFAULT_BIT_DEPTH,
        stereo: bool = True,
        fade_out: int = DEFAULT_FADE_OUT,
        verbose: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Export SID file to WAV audio.

        Args:
            sid_file: Path to input SID file
            output_file: Path to output WAV file
            duration: Playback duration in seconds (default: 30)
            frequency: Sample rate in Hz (default: 44100)
            bit_depth: Bit depth - 8 or 16 (default: 16)
            stereo: Enable stereo output (default: True)
            fade_out: Fade-out time in seconds (default: 2)
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)

        Returns:
            Dictionary with export results:
            {
                'success': True/False,
                'output_file': Path to WAV file,
                'duration': Duration in seconds,
                'frequency': Sample rate,
                'bit_depth': Bit depth,
                'stereo': Stereo enabled,
                'file_size': Output file size in bytes,
                'error': Error message (if failed)
            }
            Returns None if tool not available.
        """
        if not AudioExportIntegration._check_tool_available():
            if verbose > 0:
                logger.warning("SID2WAV.EXE not available (tools/SID2WAV.EXE not found)")
            return None

        if not sid_file.exists():
            if verbose > 0:
                logger.error(f"SID file not found: {sid_file}")
            return {
                'success': False,
                'error': f"SID file not found: {sid_file}"
            }

        try:
            # Build command line arguments
            args = [
                str(Path(AudioExportIntegration.SID2WAV_EXE)),
                f"-t{duration}",  # Duration
                f"-f{frequency}",  # Frequency
                f"-fout{fade_out}",  # Fade-out
            ]

            # Bit depth
            if bit_depth == 16:
                args.append("-16")

            # Stereo
            if stereo:
                args.append("-s")

            # Input and output files
            args.append(str(sid_file))
            args.append(str(output_file))

            if verbose > 1:
                print(f"  Command: {' '.join(args)}")

            # Execute SID2WAV
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=duration + 30  # Add buffer time
            )

            # Check if output file was created
            if output_file.exists():
                file_size = output_file.stat().st_size

                if verbose > 0:
                    print(f"  Audio export complete: {output_file.name}")
                    print(f"    Duration: {duration}s")
                    print(f"    Format: {frequency}Hz, {bit_depth}-bit, {'stereo' if stereo else 'mono'}")
                    print(f"    Size: {file_size:,} bytes")

                return {
                    'success': True,
                    'output_file': output_file,
                    'duration': duration,
                    'frequency': frequency,
                    'bit_depth': bit_depth,
                    'stereo': stereo,
                    'file_size': file_size
                }
            else:
                error_msg = "Output file not created"
                if result.stderr:
                    # Convert to ASCII-safe string
                    error_msg = result.stderr.strip().encode('ascii', 'replace').decode('ascii')

                if verbose > 0:
                    logger.error(f"Audio export failed: {error_msg}")

                return {
                    'success': False,
                    'error': error_msg
                }

        except subprocess.TimeoutExpired:
            error_msg = f"SID2WAV timeout (>{duration + 30}s)"
            if verbose > 0:
                logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

        except Exception as e:
            if verbose > 0:
                # Convert exception to ASCII-safe string
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                logger.error(f"Audio export failed: {error_msg}")
            return {
                'success': False,
                'error': str(e)
            }


# Convenience function for simple usage
def export_to_wav(
    sid_file: Path,
    output_file: Path,
    duration: int = AudioExportIntegration.DEFAULT_DURATION,
    verbose: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for exporting SID files to WAV audio.

    See AudioExportIntegration.export_to_wav() for details.
    """
    return AudioExportIntegration.export_to_wav(
        sid_file, output_file, duration=duration, verbose=verbose
    )
