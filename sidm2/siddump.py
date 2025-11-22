"""
Siddump integration for extracting ADSR and waveform data.
"""

import logging
import os
import subprocess
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def extract_from_siddump(sid_path: str, playback_time: int = 60) -> Optional[Dict]:
    """
    Run siddump on a SID file and extract actual ADSR and waveform values.

    Returns dict with:
    - adsr_values: list of (AD, SR) tuples actually used
    - waveforms: list of waveform bytes actually used
    - pulse_range: (min, max) pulse width range
    - instruments: list of instrument dicts built from actual usage
    """
    siddump_exe = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools', 'siddump.exe')

    if not os.path.exists(siddump_exe):
        return None

    try:
        result = subprocess.run(
            [siddump_exe, sid_path, f'-t{playback_time}'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            return None

        # Parse siddump output
        adsr_set = set()
        waveform_set = set()
        pulse_values = set()

        for line in result.stdout.split('\n'):
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

    except subprocess.TimeoutExpired:
        logger.warning(f"siddump timed out after {playback_time}s")
        return None
    except FileNotFoundError:
        logger.warning(f"siddump.exe not found at {siddump_exe}")
        return None
    except Exception as e:
        logger.warning(f"siddump extraction failed: {e}")
        return None
