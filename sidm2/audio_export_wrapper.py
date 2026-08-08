"""
Audio Export Integration for SID Conversion Pipeline - Phase 2

Exports SID files to WAV audio for reference listening.
Uses VSID (VICE emulator) as primary option with sidplayfp as fallback.

Usage:
    from sidm2.audio_export_wrapper import AudioExportIntegration

    result = AudioExportIntegration.export_to_wav(
        sid_file=Path("input.sid"),
        output_file=Path("output.wav"),
        duration=30,
        verbose=1
    )
"""

__version__ = "3.0.0"
__date__ = "2026-08-07"

from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Import VSID wrapper
try:
    from sidm2.vsid_wrapper import VSIDIntegration
    VSID_AVAILABLE = True
except ImportError:
    VSID_AVAILABLE = False

# Import sidplayfp wrapper (replaces SID2WAV.EXE, a 1997 build that hangs on
# some newer tunes -- see pyscript/audio_tightness_tool.py's choose_renderer)
try:
    from sidm2.sidplayfp_wrapper import SidplayfpIntegration
    SIDPLAYFP_AVAILABLE = True
except ImportError:
    SIDPLAYFP_AVAILABLE = False

logger = logging.getLogger(__name__)


class AudioExportIntegration:
    """
    Integration wrapper for audio export in conversion pipeline.

    Prefers VSID (VICE emulator) for better accuracy and cross-platform support.
    Falls back to sidplayfp if VSID is not available.
    """

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
        Check if sidplayfp is available.

        Returns:
            True if tool exists, False otherwise
        """
        return SIDPLAYFP_AVAILABLE and SidplayfpIntegration._check_tool_available()

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
        force_sidplayfp: bool = False,
        mute_voices: Optional[str] = None,
        subtune: Optional[int] = None,
        power_on_delay: Optional[int] = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Export SID file to WAV audio.

        Uses VSID (VICE emulator) by default for better accuracy.
        Falls back to sidplayfp if VSID is not available.

        Args:
            sid_file: Path to input SID file
            output_file: Path to output WAV file
            duration: Playback duration in seconds (default: 30)
            frequency: Sample rate in Hz (default: 44100)
            bit_depth: Bit depth - 16 or 32 (default: 16)
            stereo: Enable stereo output (default: True)
            fade_out: Fade-out time in seconds (default: 2). Currently unused
                by either renderer -- VSID has no fade-out, and sidplayfp's
                --fo is not wired up here.
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)
            force_sidplayfp: Force use of sidplayfp even if VSID is available
            mute_voices: sidplayfp -u<voice> digits (e.g. "23" mutes voices
                2+3). sidplayfp-only -- VSID has no equivalent, so this
                requires force_sidplayfp=True.
            subtune: Track/subtune number (sidplayfp -o<num>, 1-indexed same
                as VSID's -tune). sidplayfp-only, same force_sidplayfp=True
                requirement as mute_voices.
            power_on_delay: sidplayfp --delay=<cycles>, default 0 for
                REPRODUCIBLE renders; sidplayfp's own default is random. See
                SidplayfpIntegration.export_to_wav. Ignored by the VSID path.

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
                'tool': 'vsid' or 'sidplayfp',
                'error': Error message (if failed)
            }
            Returns None if no tool available.
        """
        if mute_voices is not None and not force_sidplayfp:
            raise ValueError(
                "mute_voices requires force_sidplayfp=True -- VSID has no "
                "voice-mute equivalent, so silently ignoring the flag would "
                "produce a misleading (unmuted) render."
            )
        if subtune is not None and not force_sidplayfp:
            raise ValueError(
                "subtune requires force_sidplayfp=True -- VSID export has no "
                "subtune-select equivalent in this wrapper."
            )

        # Try VSID first (preferred) unless forced to use sidplayfp
        if not force_sidplayfp and AudioExportIntegration.PREFER_VSID and VSID_AVAILABLE:
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

            # VSID failed, try sidplayfp fallback
            if verbose > 0:
                logger.warning("VSID export failed, trying sidplayfp fallback")

        # Use sidplayfp (fallback or forced)
        if not AudioExportIntegration._check_tool_available():
            if verbose > 0:
                logger.warning("sidplayfp not available (tools/sidplayfp/sidplayfp.exe not found)")
                if not VSID_AVAILABLE:
                    logger.warning("VSID also not available. Install VICE:")
                    logger.warning("  python pyscript/install_vice.py")
            return None

        if verbose > 1:
            print(f"  Using sidplayfp for audio export")

        result = SidplayfpIntegration.export_to_wav(
            sid_file=sid_file,
            output_file=output_file,
            duration=duration,
            frequency=frequency,
            bit_depth=bit_depth,
            stereo=stereo,
            verbose=verbose,
            mute_voices=mute_voices,
            power_on_delay=power_on_delay,
            subtune=subtune,
        )
        return result


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
