"""
sidplayfp Audio Export Integration for SID Conversion Pipeline

Replaces SID2WAV.EXE (a 1997 build) as the secondary/voice-isolating renderer.
sidplayfp (https://github.com/libsidplayfp/sidplayfp) is the actively
maintained reference SID player, built on libsidplayfp + libresidfp (a reSID
fork with more accurate filter emulation). Unlike SID2WAV it renders duration
natively via -t<seconds> (no hang-on-unsupported-tune failure mode), and its
-u<voice> flag replaces SID2WAV's -m<digits> for voice muting.

Usage:
    from sidm2.sidplayfp_wrapper import SidplayfpIntegration

    result = SidplayfpIntegration.export_to_wav(
        sid_file=Path("input.sid"),
        output_file=Path("output.wav"),
        duration=30,
        verbose=1
    )
"""

__version__ = "1.0.0"
__date__ = "2026-08-07"

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SidplayfpIntegration:
    """Integration wrapper for sidplayfp audio export in conversion pipeline"""

    # Default settings
    DEFAULT_DURATION = 30  # seconds
    DEFAULT_FREQUENCY = 44100  # Hz
    DEFAULT_BIT_DEPTH = 16  # bits (sidplayfp supports 16 or 32-bit float only)

    @staticmethod
    def _find_sidplayfp() -> Optional[Path]:
        """
        Locate sidplayfp.exe in the bundled tools directory or system PATH.

        Returns:
            Path to sidplayfp.exe if found, None otherwise
        """
        project_root = Path(__file__).parent.parent
        bundled = project_root / 'tools' / 'sidplayfp' / 'sidplayfp.exe'
        if bundled.exists():
            return bundled

        found = shutil.which('sidplayfp')
        if found:
            return Path(found)

        return None

    @staticmethod
    def _check_tool_available() -> bool:
        """
        Check if sidplayfp is available.

        Returns:
            True if sidplayfp exists, False otherwise
        """
        return SidplayfpIntegration._find_sidplayfp() is not None

    @staticmethod
    def export_to_wav(
        sid_file: Path,
        output_file: Path,
        duration: int = DEFAULT_DURATION,
        frequency: int = DEFAULT_FREQUENCY,
        bit_depth: int = DEFAULT_BIT_DEPTH,
        stereo: bool = True,
        verbose: int = 0,
        mute_voices: Optional[str] = None,
        subtune: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Export SID file to WAV audio using sidplayfp.

        Args:
            sid_file: Path to input SID file
            output_file: Path to output WAV file
            duration: Playback duration in seconds (default: 30)
            frequency: Sample rate in Hz (default: 44100)
            bit_depth: Bit depth - 16 or 32 (default: 16). sidplayfp has no
                8-bit output mode; anything other than 32 renders 16-bit.
            stereo: Enable stereo output (default: True)
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)
            mute_voices: Digits of voices to mute, e.g. "23" mutes voices 2+3
                (isolates voice 1). Maps to sidplayfp's -u<num> per voice.
            subtune: Track/subtune number, 1-indexed same as VSID's -tune.
                Maps to sidplayfp's -o<num>.

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
                'tool': 'sidplayfp',
                'error': Error message (if failed)
            }
            Returns None if sidplayfp not available.
        """
        sidplayfp_exe = SidplayfpIntegration._find_sidplayfp()
        if not sidplayfp_exe:
            if verbose > 0:
                logger.warning(
                    "sidplayfp not available (looked in tools/sidplayfp/sidplayfp.exe, PATH). "
                    "Install via MSYS2: pacman -S mingw-w64-x86_64-sidplayfp"
                )
            return None

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
            output_file.parent.mkdir(parents=True, exist_ok=True)
            if output_file.exists():
                output_file.unlink()

            args = [
                str(sidplayfp_exe),
                f"-t{duration}",
                f"-f{frequency}",
                "-p32" if bit_depth == 32 else "-p16",
            ]

            args.append("-s" if stereo else "-m")

            if mute_voices:
                for digit in mute_voices:
                    args.append(f"-u{digit}")

            if subtune is not None:
                args.append(f"-o{subtune}")

            args.append(f"-w{output_file}")
            args.append(str(sid_file))

            if verbose > 1:
                print(f"  Command: {' '.join(args)}")

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=duration + 30  # Add buffer time
            )

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
                    'tool': 'sidplayfp'
                }
            else:
                error_msg = "Output file not created"
                if result.stderr:
                    error_msg = result.stderr.strip().encode('ascii', 'replace').decode('ascii')

                if verbose > 0:
                    logger.error(
                        f"Audio export failed: {error_msg}\n"
                        f"  Suggestion: Verify sidplayfp is installed correctly\n"
                        f"  Check: Ensure SID file is valid and playable\n"
                        f"  Try: Run sidplayfp manually to diagnose issue\n"
                        f"  See: docs/guides/TROUBLESHOOTING.md#audio-export-failures"
                    )

                return {
                    'success': False,
                    'error': error_msg
                }

        except subprocess.TimeoutExpired:
            error_msg = f"sidplayfp timeout (>{duration + 30}s)"
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
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                logger.error(
                    f"Audio export failed: {error_msg}\n"
                    f"  Suggestion: Check if sidplayfp.exe is available in tools/sidplayfp/\n"
                    f"  Check: Verify SID file format is valid\n"
                    f"  Try: Run sidplayfp manually to diagnose issue\n"
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
    duration: int = SidplayfpIntegration.DEFAULT_DURATION,
    verbose: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for exporting SID files to WAV audio using sidplayfp.

    See SidplayfpIntegration.export_to_wav() for details.
    """
    return SidplayfpIntegration.export_to_wav(
        sid_file, output_file, duration=duration, verbose=verbose
    )
