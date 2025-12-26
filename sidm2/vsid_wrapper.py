"""
VSID Audio Export Integration for SID Conversion Pipeline

Integrates VSID (VICE SID player) into the conversion pipeline.
Exports SID files to WAV audio using VSID instead of SID2WAV.

VSID provides better accuracy and cross-platform support compared to SID2WAV.

Usage:
    from sidm2.vsid_wrapper import VSIDIntegration

    result = VSIDIntegration.export_to_wav(
        sid_file=Path("input.sid"),
        output_file=Path("output.wav"),
        duration=30,
        verbose=1
    )
"""

__version__ = "1.0.0"
__date__ = "2025-12-26"

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class VSIDIntegration:
    """Integration wrapper for VSID audio export in conversion pipeline"""

    # Default settings
    DEFAULT_DURATION = 30  # seconds
    DEFAULT_FREQUENCY = 44100  # Hz (VSID default)
    DEFAULT_BIT_DEPTH = 16  # bits (VSID default)

    @staticmethod
    def _find_vsid() -> Optional[Path]:
        """
        Locate vsid.exe in the tools directory or system PATH.

        Returns:
            Path to vsid.exe if found, None otherwise
        """
        # Check common VICE installation locations
        project_root = Path(__file__).parent.parent
        vice_paths = [
            Path(r'C:\winvice\bin\vsid.exe'),  # Common Windows installation
            project_root / 'tools' / 'vice' / 'bin' / 'vsid.exe',
            project_root / 'tools' / 'vice' / 'vsid.exe',
        ]

        for path in vice_paths:
            if path.exists():
                return path

        # Check system PATH
        vsid_path = shutil.which('vsid')
        if vsid_path:
            return Path(vsid_path)

        return None

    @staticmethod
    def _check_tool_available() -> bool:
        """
        Check if VSID is available.

        Returns:
            True if VSID exists, False otherwise
        """
        return VSIDIntegration._find_vsid() is not None

    @staticmethod
    def export_to_wav(
        sid_file: Path,
        output_file: Path,
        duration: int = DEFAULT_DURATION,
        frequency: int = DEFAULT_FREQUENCY,
        bit_depth: int = DEFAULT_BIT_DEPTH,
        stereo: bool = True,
        fade_out: int = 0,  # VSID doesn't support fade-out
        verbose: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Export SID file to WAV audio using VSID.

        Args:
            sid_file: Path to input SID file
            output_file: Path to output WAV file
            duration: Playback duration in seconds (default: 30)
            frequency: Sample rate in Hz (default: 44100) - VSID uses its own setting
            bit_depth: Bit depth - 8 or 16 (default: 16) - VSID uses its own setting
            stereo: Enable stereo output (default: True) - VSID uses its own setting
            fade_out: Fade-out time in seconds (ignored for VSID)
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
            Returns None if VSID not available.
        """
        vsid_exe = VSIDIntegration._find_vsid()
        if not vsid_exe:
            if verbose > 0:
                logger.warning("VSID not available. Install VICE emulator:")
                logger.warning("  python pyscript/install_vice.py")
                logger.warning("  OR install-vice.bat")
            return None

        if not sid_file.exists():
            if verbose > 0:
                logger.error(f"SID file not found: {sid_file}")
            return {
                'success': False,
                'error': f"SID file not found: {sid_file}"
            }

        try:
            # Create output directory if needed
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Build VSID command
            # vsid -sounddev wav -soundarg output.wav input.sid
            args = [
                str(vsid_exe),
                '-sounddev', 'wav',
                '-soundarg', str(output_file),
                str(sid_file)
            ]

            if verbose > 1:
                print(f"  Command: {' '.join(args)}")
                print(f"  Duration: {duration} seconds")

            # VSID runs indefinitely, so we use timeout to stop it
            timeout_value = duration + 10  # Add 10 seconds buffer

            # Execute VSID
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=timeout_value
            )

            # VSID runs indefinitely, so timeout is expected
            # Check if WAV file was created successfully
            if not output_file.exists():
                error_msg = "Output file not created"
                if result.returncode != 0 and result.stderr:
                    error_msg = result.stderr.strip()

                if verbose > 0:
                    logger.error(f"VSID export failed: {error_msg}")

                return {
                    'success': False,
                    'error': error_msg
                }

            file_size = output_file.stat().st_size
            if file_size == 0:
                if verbose > 0:
                    logger.error("Output file is empty")
                return {
                    'success': False,
                    'error': "Output file is empty"
                }

            if verbose > 0:
                print(f"  Audio export complete: {output_file.name}")
                print(f"    Duration: {duration}s")
                print(f"    Format: WAV (VSID default settings)")
                print(f"    Size: {file_size:,} bytes")

            return {
                'success': True,
                'output_file': output_file,
                'duration': duration,
                'frequency': frequency,  # VSID uses its own settings
                'bit_depth': bit_depth,  # VSID uses its own settings
                'stereo': stereo,  # VSID uses its own settings
                'file_size': file_size
            }

        except subprocess.TimeoutExpired:
            # This is expected - VSID runs indefinitely, timeout stops it
            # Check if WAV file was created
            if output_file.exists() and output_file.stat().st_size > 0:
                file_size = output_file.stat().st_size

                if verbose > 0:
                    print(f"  Audio export complete: {output_file.name}")
                    print(f"    Duration: {duration}s (stopped after timeout)")
                    print(f"    Format: WAV (VSID default settings)")
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
                error_msg = "Timeout but no output file created"
                if verbose > 0:
                    logger.error(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }

        except Exception as e:
            if verbose > 0:
                error_msg = str(e)
                logger.error(f"VSID export failed: {error_msg}")
            return {
                'success': False,
                'error': str(e)
            }


# Convenience function for simple usage
def export_to_wav(
    sid_file: Path,
    output_file: Path,
    duration: int = VSIDIntegration.DEFAULT_DURATION,
    verbose: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for exporting SID files to WAV audio using VSID.

    See VSIDIntegration.export_to_wav() for details.
    """
    return VSIDIntegration.export_to_wav(
        sid_file, output_file, duration=duration, verbose=verbose
    )
