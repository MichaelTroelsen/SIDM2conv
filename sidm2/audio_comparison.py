#!/usr/bin/env python3
"""
Audio Comparison Module

Compares WAV files to measure conversion accuracy based on actual sound output
rather than SID register writes. This is more meaningful for conversions that
change the player code (e.g., Laxity → SF2 Driver 11).

Version: 1.0.0
Author: SIDM2 Project
Date: 2025-12-12
"""

import struct
import math
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class WAVComparisonError(Exception):
    """Raised when WAV comparison fails"""
    pass


def read_wav_header(data: bytes) -> dict:
    """
    Parse WAV file header.

    Args:
        data: WAV file bytes

    Returns:
        Dictionary with WAV parameters

    Raises:
        WAVComparisonError: If not a valid WAV file
    """
    if len(data) < 44:
        raise WAVComparisonError("File too small to be a valid WAV")

    # Check RIFF header
    if data[0:4] != b'RIFF':
        raise WAVComparisonError("Not a WAV file (missing RIFF header)")

    # Check WAVE format
    if data[8:12] != b'WAVE':
        raise WAVComparisonError("Not a WAV file (missing WAVE format)")

    # Find fmt chunk
    if data[12:16] != b'fmt ':
        raise WAVComparisonError("Missing fmt chunk")

    fmt_size = struct.unpack('<I', data[16:20])[0]
    audio_format = struct.unpack('<H', data[20:22])[0]
    num_channels = struct.unpack('<H', data[22:24])[0]
    sample_rate = struct.unpack('<I', data[24:28])[0]
    bits_per_sample = struct.unpack('<H', data[34:36])[0]

    # Find data chunk
    pos = 20 + fmt_size
    while pos < len(data) - 8:
        chunk_id = data[pos:pos+4]
        chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]

        if chunk_id == b'data':
            data_offset = pos + 8
            data_size = chunk_size
            break

        pos += 8 + chunk_size
    else:
        raise WAVComparisonError("Missing data chunk")

    return {
        'audio_format': audio_format,
        'num_channels': num_channels,
        'sample_rate': sample_rate,
        'bits_per_sample': bits_per_sample,
        'data_offset': data_offset,
        'data_size': data_size
    }


def read_wav_samples(filepath: str) -> Tuple[list, dict]:
    """
    Read WAV file and extract sample data.

    Args:
        filepath: Path to WAV file

    Returns:
        (samples, header_info) tuple where samples is list of normalized floats [-1.0, 1.0]

    Raises:
        WAVComparisonError: If file cannot be read or parsed
    """
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
    except IOError as e:
        raise WAVComparisonError(f"Cannot read file {filepath}: {e}")

    header = read_wav_header(data)

    # Extract sample data
    data_offset = header['data_offset']
    data_size = header['data_size']
    bits = header['bits_per_sample']
    channels = header['num_channels']

    samples = []

    if bits == 8:
        # 8-bit samples are unsigned (0-255, center at 128)
        for i in range(data_size):
            if data_offset + i < len(data):
                value = data[data_offset + i]
                # Convert to signed and normalize to [-1.0, 1.0]
                normalized = (value - 128) / 128.0
                samples.append(normalized)

    elif bits == 16:
        # 16-bit samples are signed (-32768 to 32767)
        num_samples = data_size // 2
        for i in range(num_samples):
            offset = data_offset + i * 2
            if offset + 1 < len(data):
                value = struct.unpack('<h', data[offset:offset+2])[0]
                # Normalize to [-1.0, 1.0]
                normalized = value / 32768.0
                samples.append(normalized)

    else:
        raise WAVComparisonError(f"Unsupported bit depth: {bits}")

    # If stereo, average channels to mono for comparison
    if channels == 2:
        mono_samples = []
        for i in range(0, len(samples), 2):
            if i + 1 < len(samples):
                mono_samples.append((samples[i] + samples[i+1]) / 2.0)
        samples = mono_samples

    return samples, header


def calculate_correlation(samples1: list, samples2: list) -> float:
    """
    Calculate Pearson correlation coefficient between two waveforms.

    Args:
        samples1: First waveform samples
        samples2: Second waveform samples

    Returns:
        Correlation coefficient [0.0, 1.0] where 1.0 = perfect match
    """
    # Use shorter length
    n = min(len(samples1), len(samples2))

    if n == 0:
        return 0.0

    # Calculate means
    mean1 = sum(samples1[:n]) / n
    mean2 = sum(samples2[:n]) / n

    # Calculate correlation
    numerator = sum((samples1[i] - mean1) * (samples2[i] - mean2) for i in range(n))

    sum_sq1 = sum((samples1[i] - mean1) ** 2 for i in range(n))
    sum_sq2 = sum((samples2[i] - mean2) ** 2 for i in range(n))

    denominator = math.sqrt(sum_sq1 * sum_sq2)

    if denominator == 0:
        return 0.0

    correlation = numerator / denominator

    # Return absolute value (phase doesn't matter) clamped to [0, 1]
    return max(0.0, min(1.0, abs(correlation)))


def calculate_rmse(samples1: list, samples2: list) -> float:
    """
    Calculate Root Mean Square Error between two waveforms.

    Args:
        samples1: First waveform samples
        samples2: Second waveform samples

    Returns:
        RMSE value [0.0, 2.0] where 0.0 = perfect match
    """
    n = min(len(samples1), len(samples2))

    if n == 0:
        return 2.0

    mse = sum((samples1[i] - samples2[i]) ** 2 for i in range(n)) / n
    return math.sqrt(mse)


def compare_wav_files(file1: str, file2: str) -> dict:
    """
    Compare two WAV files and return similarity metrics.

    Args:
        file1: Path to first WAV file (original)
        file2: Path to second WAV file (converted)

    Returns:
        Dictionary with comparison results:
        - 'correlation': Pearson correlation [0.0, 1.0]
        - 'rmse': Root mean square error [0.0, 2.0]
        - 'accuracy': Overall accuracy percentage [0.0, 100.0]
        - 'samples_compared': Number of samples compared
        - 'compatible': Whether files have compatible formats

    Raises:
        WAVComparisonError: If comparison fails
    """
    try:
        samples1, header1 = read_wav_samples(file1)
        samples2, header2 = read_wav_samples(file2)
    except Exception as e:
        raise WAVComparisonError(f"Failed to read WAV files: {e}")

    # Check format compatibility
    compatible = (
        header1['sample_rate'] == header2['sample_rate'] and
        header1['bits_per_sample'] == header2['bits_per_sample']
    )

    if not compatible:
        logger.warning(f"WAV format mismatch: "
                      f"{header1['sample_rate']}Hz/{header1['bits_per_sample']}bit vs "
                      f"{header2['sample_rate']}Hz/{header2['bits_per_sample']}bit")

    # Calculate metrics
    correlation = calculate_correlation(samples1, samples2)
    rmse = calculate_rmse(samples1, samples2)

    # Convert correlation to accuracy percentage
    # Correlation of 1.0 = 100%, 0.0 = 0%
    accuracy = correlation * 100.0

    # Alternative: Use RMSE-based accuracy
    # RMSE of 0.0 = 100%, 2.0 = 0%
    # rmse_accuracy = max(0.0, (1.0 - rmse / 2.0) * 100.0)

    return {
        'correlation': correlation,
        'rmse': rmse,
        'accuracy': accuracy,
        'samples_compared': min(len(samples1), len(samples2)),
        'compatible': compatible,
        'duration_samples': (len(samples1), len(samples2))
    }


def calculate_audio_accuracy(original_wav: str, exported_wav: str, verbose: bool = False) -> Optional[float]:
    """
    Calculate audio accuracy between original and exported WAV files.

    This is the main entry point for the pipeline.

    Args:
        original_wav: Path to original WAV file
        exported_wav: Path to exported/converted WAV file
        verbose: If True, log detailed comparison info

    Returns:
        Accuracy percentage [0.0, 100.0] or None if comparison fails
    """
    try:
        result = compare_wav_files(original_wav, exported_wav)

        if verbose:
            logger.info(f"  Audio Comparison:")
            logger.info(f"    Correlation: {result['correlation']:.4f}")
            logger.info(f"    RMSE: {result['rmse']:.4f}")
            logger.info(f"    Samples compared: {result['samples_compared']:,}")
            logger.info(f"    Accuracy: {result['accuracy']:.2f}%")

        return result['accuracy']

    except WAVComparisonError as e:
        logger.warning(f"  Audio comparison failed: {e}")
        return None
    except Exception as e:
        logger.error(f"  Audio comparison error: {e}")
        return None
