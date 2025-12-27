"""
Audio Export Integration for SID Conversion Pipeline - Phase 2

Exports SID files to WAV audio for reference listening.
Uses VSID (VICE emulator) as primary option with SID2WAV.EXE as fallback.

Usage:
    from sidm2.audio_export_wrapper import AudioExportIntegration

    result = AudioExportIntegration.export_to_wav(
        sid_file=Path("input.sid"),
        output_file=Path("output.wav"),
        duration=30,
        verbose=1
    )
"""

__version__ = "2.0.0"
__date__ = "2025-12-26"

import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Import VSID wrapper
try:
    from sidm2.vsid_wrapper import VSIDIntegration
    VSID_AVAILABLE = True
except ImportError:
    VSID_AVAILABLE = False

logger = logging.getLogger(__name__)


class AudioExportIntegration:
    """
    Integration wrapper for audio export in conversion pipeline.

    Prefers VSID (VICE emulator) for better accuracy and cross-platform support.
    Falls back to SID2WAV.EXE if VSID is not available.
    """

    # Tool configuration
    SID2WAV_EXE = "tools/SID2WAV.EXE"

    # Default settings
    DEFAULT_DURATION = 30  # seconds
    DEFAULT_FREQUENCY = 44100  # Hz
    DEFAULT_BIT_DEPTH = 16  # bits
    DEFAULT_FADE_OUT = 2  # seconds

    # Preferred tool order
    PREFER_VSID = True  # Use VSID by default if available

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
        verbose: int = 0,
        force_sid2wav: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Export SID file to WAV audio.

        Uses VSID (VICE emulator) by default for better accuracy.
        Falls back to SID2WAV.EXE if VSID is not available.

        Args:
            sid_file: Path to input SID file
            output_file: Path to output WAV file
            duration: Playback duration in seconds (default: 30)
            frequency: Sample rate in Hz (default: 44100)
            bit_depth: Bit depth - 8 or 16 (default: 16)
            stereo: Enable stereo output (default: True)
            fade_out: Fade-out time in seconds (default: 2, SID2WAV only)
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)
            force_sid2wav: Force use of SID2WAV even if VSID is available

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
                'tool': 'vsid' or 'sid2wav',
                'error': Error message (if failed)
            }
            Returns None if no tool available.
        """
        # Try VSID first (preferred) unless forced to use SID2WAV
        if not force_sid2wav and AudioExportIntegration.PREFER_VSID and VSID_AVAILABLE:
            if verbose > 1:
                print(f"  Using VSID for audio export (preferred)")

            result = VSIDIntegration.export_to_wav(
                sid_file=sid_file,
                output_file=output_file,
                duration=duration,
                frequency=frequency,
                bit_depth=bit_depth,
                stereo=stereo,
                fade_out=fade_out,
                verbose=verbose
            )

            if result and result.get('success'):
                result['tool'] = 'vsid'
                return result

            # VSID failed, try SID2WAV fallback
            if verbose > 0:
                logger.warning("VSID export failed, trying SID2WAV fallback")

        # Use SID2WAV (fallback or forced)
        if not AudioExportIntegration._check_tool_available():
            if verbose > 0:
                logger.warning("SID2WAV.EXE not available (tools/SID2WAV.EXE not found)")
                if not VSID_AVAILABLE:
                    logger.warning("VSID also not available. Install VICE:")
                    logger.warning("  python pyscript/install_vice.py")
            return None

        if verbose > 1:
            print(f"  Using SID2WAV for audio export")

        if not sid_file.exists():
            if verbose > 0:
                logger.error(
                    f"SID file not found: {sid_file}\n"
                    f"  Suggestion: Verify file path is correct\n"
                    f"  Check: Ensure file was generated successfully\n"
                    f"  Try: Use absolute path instead of relative path\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#file-not-found-issues"
                )
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
                    'file_size': file_size,
                    'tool': 'sid2wav'
                }
            else:
                error_msg = "Output file not created"
                if result.stderr:
                    # Convert to ASCII-safe string
                    error_msg = result.stderr.strip().encode('ascii', 'replace').decode('ascii')

                if verbose > 0:
                    logger.error(
                        f"Audio export failed: {error_msg}\n"
                        f"  Suggestion: Verify SID2WAV is installed correctly\n"
                        f"  Check: Ensure SID file is valid and playable\n"
                        f"  Try: Test SID file in VICE emulator first\n"
                        f"  See: docs/guides/TROUBLESHOOTING.md#audio-export-failures"
                    )

                return {
                    'success': False,
                    'error': error_msg
                }

        except subprocess.TimeoutExpired:
            error_msg = f"SID2WAV timeout (>{duration + 30}s)"
            if verbose > 0:
                logger.error(
                    f"{error_msg}\n"
                    f"  Suggestion: Reduce duration with -t flag (e.g., -t30)\n"
                    f"  Check: SID file may have infinite loop\n"
                    f"  Try: Test with shorter duration first\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#audio-export-timeout"
                )
            return {
                'success': False,
                'error': error_msg
            }

        except Exception as e:
            if verbose > 0:
                # Convert exception to ASCII-safe string
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                logger.error(
                    f"Audio export failed: {error_msg}\n"
                    f"  Suggestion: Check if SID2WAV.EXE is available in tools/ directory\n"
                    f"  Check: Verify SID file format is valid\n"
                    f"  Try: Run SID2WAV manually to diagnose issue\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#audio-export-failures"
                )
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
