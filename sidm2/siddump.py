"""
Siddump integration for extracting ADSR and waveform data.

Updated to use Python siddump implementation by default (2025-12-22).
Falls back to siddump.exe if requested or if Python version unavailable.
"""

import logging
import os
import subprocess
import re
import sys
import io
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_from_siddump(sid_path: str, playback_time: int = 60, use_python: bool = True) -> Optional[Dict]:
    """
    Run siddump on a SID file and extract actual ADSR and waveform values.

    Args:
        sid_path: Path to SID file
        playback_time: Playback time in seconds (default: 60)
        use_python: Use Python siddump (default: True). Set False for C exe.

    Returns dict with:
    - adsr_values: list of (AD, SR) tuples actually used
    - waveforms: list of waveform bytes actually used
    - pulse_range: (min, max) pulse width range
    - instruments: list of instrument dicts built from actual usage
    """
    # Try Python version first (if requested)
    if use_python:
        output = _run_python_siddump(sid_path, playback_time)
        if output is None:
            logger.warning("Python siddump failed, falling back to .exe")
            use_python = False

    # Fallback to C exe version
    if not use_python:
        output = _run_exe_siddump(sid_path, playback_time)
        if output is None:
            return None

    # Parse siddump output (same format for both Python and C versions)
    adsr_set = set()
    waveform_set = set()
    pulse_values = set()

    if output:
        for line in output.split('\n'):
            if not line.startswith('|') or line.startswith('| Frame'):
                continue

            parts = line.split('|')
            if len(parts) < 5:
                continue

            # Parse each of 3 channels
            for ch in range(3):
                if ch + 2 >= len(parts):
                    break

                ch_data = parts[ch + 2].strip()

                # Extract ADSR (4 hex digits)
                adsr_match = re.search(r'([0-9A-Fa-f]{4})\s+[0-9A-Fa-f]{3}\s*$', ch_data)
                if not adsr_match:
                    adsr_match = re.search(r'\s([0-9A-Fa-f]{4})\s', ch_data)

                if adsr_match:
                    adsr = adsr_match.group(1)
                    if adsr != '....' and adsr != '0000':
                        adsr_val = int(adsr, 16)
                        ad = (adsr_val >> 8) & 0xFF
                        sr = adsr_val & 0xFF
                        # Filter out hard restart values
                        if ad != 0x0F or sr > 0x01:
                            adsr_set.add((ad, sr))

                # Extract waveform
                wf_match = re.search(r'\)\s*([0-9A-Fa-f]{2})\s', ch_data)
                if not wf_match:
                    wf_match = re.search(r'\s([0-9A-Fa-f]{2})\s+[0-9A-Fa-f\.]{4}', ch_data)

                if wf_match:
                    wf = wf_match.group(1)
                    if wf != '..':
                        wf_val = int(wf, 16)
                        if wf_val != 0:
                            waveform_set.add(wf_val)

            # Extract pulse width
            pulse_match = re.search(r'([0-9A-Fa-f]{3})\s*$', ch_data)
            if pulse_match:
                pulse = pulse_match.group(1)
                if pulse != '...':
                    pulse_val = int(pulse, 16)
                    if pulse_val != 0:
                        pulse_values.add(pulse_val)

    # Build instrument list from unique ADSR values
    instruments = []
    for i, (ad, sr) in enumerate(sorted(adsr_set)):
        # Determine waveform name based on common patterns
        if sr & 0xF0 >= 0xA0:
            char = "Lead"
        elif ad == 0 and (sr & 0x0F) <= 2:
            char = "Perc"
        elif ad >= 8:
            char = "Pad"
        elif (sr & 0x0F) <= 2:
            char = "Stab"
        else:
            char = ""

        instruments.append({
            'index': i,
            'ad': ad,
            'sr': sr,
            'name': f"{i:02d} {char} Instr".strip()
        })

    return {
        'adsr_values': list(adsr_set),
        'waveforms': list(waveform_set),
        'pulse_range': (min(pulse_values), max(pulse_values)) if pulse_values else (0, 0),
        'instruments': instruments
    }


def _run_python_siddump(sid_path: str, playback_time: int) -> Optional[str]:
    """
    Run Python siddump implementation.

    Returns:
        Siddump output as string, or None if failed
    """
    try:
        # Import Python siddump
        pyscript_path = Path(__file__).parent.parent / 'pyscript'
        if str(pyscript_path) not in sys.path:
            sys.path.insert(0, str(pyscript_path))

        from siddump_complete import main, parse_sid_file, run_siddump
        import argparse

        # Create argument namespace
        args = argparse.Namespace(
            sidfile=sid_path,
            subtune=0,
            basefreq=None,
            basenote=None,
            firstframe=0,
            lowres=False,
            spacing=0,
            oldnotefactor=1,
            pattspacing=0,
            timeseconds=False,
            seconds=playback_time,
            profiling=False
        )

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            # Parse SID file
            header, c64_data = parse_sid_file(sid_path)

            # Run siddump
            result = run_siddump(sid_path, args)

            # Get output
            output = sys.stdout.getvalue()

            if result != 0:
                logger.warning(f"Python siddump returned non-zero: {result}")
                return None

            return output

        finally:
            sys.stdout = old_stdout

    except ImportError as e:
        logger.debug(f"Python siddump not available: {e}")
        return None
    except Exception as e:
        logger.debug(f"Python siddump failed: {e}")
        return None


def _run_exe_siddump(sid_path: str, playback_time: int) -> Optional[str]:
    """
    Run C siddump.exe implementation (fallback).

    Returns:
        Siddump output as string, or None if failed
    """
    siddump_exe = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools', 'siddump.exe')

    if not os.path.exists(siddump_exe):
        logger.warning(f"siddump.exe not found at {siddump_exe}")
        return None

    try:
        result = subprocess.run(
            [siddump_exe, sid_path, f'-t{playback_time}'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.error(
                f"siddump.exe failed for {sid_path}: return code {result.returncode}\n"
                f"  Suggestion: SID file may be incompatible with siddump\n"
                f"  Check: Verify SID file has valid PSID/RSID header\n"
                f"  Try: Use Python siddump instead (use_python=True, default)\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#siddump-failures"
            )
            if result.stderr:
                logger.error(
                    f"siddump.exe stderr: {result.stderr}\n"
                    f"  Suggestion: Check stderr output for specific error details\n"
                    f"  Check: Verify siddump.exe is compatible with this SID format\n"
                    f"  Try: Use Python siddump as alternative (use_python=True)\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#siddump-stderr-errors"
                )
            return None

        return result.stdout

    except subprocess.TimeoutExpired:
        logger.warning(f"siddump.exe timed out after {playback_time}s for {sid_path}")
        return None
    except FileNotFoundError as e:
        logger.error(
            f"File not found during siddump.exe for {sid_path}: {e}\n"
            f"  Suggestion: siddump.exe not found in tools/ directory\n"
            f"  Check: Verify tools/siddump.exe exists\n"
            f"  Try: Use Python siddump instead (use_python=True, default)\n"
            f"  See: docs/guides/TROUBLESHOOTING.md#siddump-not-found"
        )
        return None
    except Exception as e:
        logger.error(
            f"siddump.exe failed for {sid_path}: {e}\n"
            f"  Suggestion: Unexpected error during siddump execution\n"
            f"  Check: Verify SID file is readable and valid\n"
            f"  Try: Use Python siddump instead (use_python=True, default)\n"
            f"  See: docs/guides/TROUBLESHOOTING.md#siddump-unexpected-errors"
        )
        return None
