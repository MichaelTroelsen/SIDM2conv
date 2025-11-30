"""
WAV Comparison Module

Compare WAV files generated from SID files to validate audio accuracy.
Provides multiple comparison methods: byte-level, RMS difference, and waveform analysis.
"""

import os
import subprocess
import struct
import math
from pathlib import Path
from typing import Tuple, Optional, Dict
import logging

logger = logging.getLogger(__name__)


class WAVComparator:
    """Compare two WAV files for audio accuracy validation"""

    def __init__(self, sid2wav_path: str = "tools/SID2WAV.EXE"):
        self.sid2wav_path = Path(sid2wav_path)
        if not self.sid2wav_path.exists():
            raise FileNotFoundError(f"SID2WAV.EXE not found at {sid2wav_path}")

    def generate_wav(self, sid_path: str, wav_path: str, duration: int = 30) -> bool:
        """
        Generate WAV file from SID using SID2WAV.EXE

        Args:
            sid_path: Input SID file path
            wav_path: Output WAV file path
            duration: Duration in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # SID2WAV.EXE usage: sid2wav [-t<seconds>] <sidfile> [outputfile]
            result = subprocess.run(
                [str(self.sid2wav_path.absolute()),
                 f'-t{duration}',
                 '-16',  # 16-bit output for better quality
                 sid_path,
                 wav_path],
                capture_output=True,
                text=True,
                timeout=duration + 30
            )

            if result.returncode == 0 and Path(wav_path).exists():
                logger.info(f"Generated WAV: {wav_path}")
                return True
            else:
                logger.error(f"SID2WAV failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"SID2WAV timed out after {duration + 30} seconds")
            return False
        except Exception as e:
            logger.error(f"WAV generation failed: {e}")
            return False

    def compare_wavs(self, wav1_path: str, wav2_path: str) -> Dict[str, float]:
        """
        Compare two WAV files using multiple methods

        Args:
            wav1_path: First WAV file (original)
            wav2_path: Second WAV file (converted)

        Returns:
            Dictionary with comparison metrics:
            - byte_match: Percentage of matching bytes (0-100%)
            - rms_difference: RMS difference between waveforms (0-1, lower is better)
            - size_match: Whether file sizes match
            - audio_accuracy: Overall audio accuracy score (0-100%)
        """
        results = {
            'byte_match': 0.0,
            'rms_difference': 1.0,
            'size_match': False,
            'audio_accuracy': 0.0,
            'error': None
        }

        try:
            # Read both WAV files
            with open(wav1_path, 'rb') as f1, open(wav2_path, 'rb') as f2:
                data1 = f1.read()
                data2 = f2.read()

            # Check file sizes
            results['size_match'] = (len(data1) == len(data2))

            if not results['size_match']:
                logger.warning(f"WAV file sizes differ: {len(data1)} vs {len(data2)} bytes")
                # Truncate to smaller size for comparison
                min_len = min(len(data1), len(data2))
                data1 = data1[:min_len]
                data2 = data2[:min_len]

            # Byte-level comparison
            matching_bytes = sum(1 for b1, b2 in zip(data1, data2) if b1 == b2)
            results['byte_match'] = (matching_bytes / len(data1) * 100) if len(data1) > 0 else 0.0

            # Parse WAV headers and extract audio data
            audio1 = self._extract_audio_data(data1)
            audio2 = self._extract_audio_data(data2)

            if audio1 and audio2:
                # Calculate RMS difference
                results['rms_difference'] = self._calculate_rms_difference(audio1, audio2)

                # Calculate overall audio accuracy
                # Lower RMS = higher accuracy
                # Convert RMS (0-1) to accuracy (0-100%)
                rms_accuracy = max(0, (1.0 - results['rms_difference']) * 100)

                # Combine byte match and RMS accuracy
                results['audio_accuracy'] = (results['byte_match'] * 0.3 + rms_accuracy * 0.7)
            else:
                # Fall back to byte match only
                results['audio_accuracy'] = results['byte_match']
                logger.warning("Could not extract audio data, using byte comparison only")

            logger.info(f"WAV Comparison: {results['audio_accuracy']:.2f}% accuracy, "
                       f"RMS diff: {results['rms_difference']:.4f}")

        except Exception as e:
            logger.error(f"WAV comparison failed: {e}")
            results['error'] = str(e)

        return results

    def _extract_audio_data(self, wav_data: bytes) -> Optional[bytes]:
        """
        Extract raw audio data from WAV file (skip header)

        WAV format:
        - RIFF header (12 bytes)
        - fmt chunk (24+ bytes)
        - data chunk (8 bytes + audio data)
        """
        try:
            # Simple WAV parser - find 'data' chunk
            data_marker = b'data'
            data_pos = wav_data.find(data_marker)

            if data_pos == -1:
                logger.warning("Could not find 'data' chunk in WAV file")
                return None

            # Data chunk size is 4 bytes after 'data' marker
            chunk_size_pos = data_pos + 4
            chunk_size = struct.unpack('<I', wav_data[chunk_size_pos:chunk_size_pos + 4])[0]

            # Audio data starts after chunk size
            audio_start = chunk_size_pos + 4
            audio_data = wav_data[audio_start:audio_start + chunk_size]

            return audio_data

        except Exception as e:
            logger.error(f"Failed to extract audio data: {e}")
            return None

    def _calculate_rms_difference(self, audio1: bytes, audio2: bytes) -> float:
        """
        Calculate RMS (Root Mean Square) difference between two audio streams

        Args:
            audio1: First audio stream
            audio2: Second audio stream

        Returns:
            RMS difference (0.0 = identical, 1.0 = maximum difference)
        """
        try:
            # Ensure same length
            min_len = min(len(audio1), len(audio2))
            audio1 = audio1[:min_len]
            audio2 = audio2[:min_len]

            # Convert bytes to 16-bit signed integers (assuming 16-bit PCM WAV)
            samples1 = struct.unpack(f'<{min_len//2}h', audio1[:min_len - (min_len % 2)])
            samples2 = struct.unpack(f'<{min_len//2}h', audio2[:min_len - (min_len % 2)])

            # Calculate RMS difference
            sum_sq_diff = sum((s1 - s2) ** 2 for s1, s2 in zip(samples1, samples2))
            rms = math.sqrt(sum_sq_diff / len(samples1))

            # Normalize to 0-1 range (assuming 16-bit audio: max value = 32768)
            normalized_rms = min(1.0, rms / 32768.0)

            return normalized_rms

        except Exception as e:
            logger.error(f"RMS calculation failed: {e}")
            return 1.0  # Return maximum difference on error

    def compare_sids_with_wav(self, sid1_path: str, sid2_path: str,
                              duration: int = 30,
                              cleanup: bool = True) -> Dict[str, any]:
        """
        Complete SID comparison workflow with WAV generation and comparison

        Args:
            sid1_path: Original SID file
            sid2_path: Converted SID file
            duration: Playback duration in seconds
            cleanup: Remove WAV files after comparison

        Returns:
            Dictionary with comparison results
        """
        results = {
            'wav1_generated': False,
            'wav2_generated': False,
            'comparison': None,
            'error': None
        }

        # Generate temporary WAV file paths
        wav1_path = str(Path(sid1_path).with_suffix('.wav'))
        wav2_path = str(Path(sid2_path).with_suffix('.wav'))

        try:
            # Generate WAV files
            logger.info(f"Generating WAV from {sid1_path}...")
            results['wav1_generated'] = self.generate_wav(sid1_path, wav1_path, duration)

            logger.info(f"Generating WAV from {sid2_path}...")
            results['wav2_generated'] = self.generate_wav(sid2_path, wav2_path, duration)

            if results['wav1_generated'] and results['wav2_generated']:
                # Compare WAV files
                logger.info("Comparing WAV files...")
                results['comparison'] = self.compare_wavs(wav1_path, wav2_path)
            else:
                results['error'] = "Failed to generate one or both WAV files"

        except Exception as e:
            logger.error(f"SID-to-WAV comparison failed: {e}")
            results['error'] = str(e)

        finally:
            # Cleanup WAV files if requested
            if cleanup:
                for wav_path in [wav1_path, wav2_path]:
                    try:
                        if Path(wav_path).exists():
                            os.remove(wav_path)
                            logger.debug(f"Removed temporary WAV: {wav_path}")
                    except Exception as e:
                        logger.warning(f"Could not remove {wav_path}: {e}")

        return results


def quick_wav_compare(sid1_path: str, sid2_path: str, duration: int = 10) -> float:
    """
    Quick WAV comparison for batch processing

    Args:
        sid1_path: Original SID file
        sid2_path: Converted SID file
        duration: Duration in seconds (default: 10 for speed)

    Returns:
        Audio accuracy percentage (0-100%)
    """
    try:
        comparator = WAVComparator()
        results = comparator.compare_sids_with_wav(sid1_path, sid2_path,
                                                   duration=duration,
                                                   cleanup=True)

        if results['comparison']:
            return results['comparison']['audio_accuracy']
        else:
            logger.error(f"WAV comparison failed: {results.get('error', 'Unknown error')}")
            return 0.0

    except Exception as e:
        logger.error(f"Quick WAV compare failed: {e}")
        return 0.0
