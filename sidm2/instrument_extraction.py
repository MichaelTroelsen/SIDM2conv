"""
Instrument extraction functions for Laxity SID files.
"""

import logging
from typing import Dict, List, Optional, Tuple

from .table_extraction import find_instrument_table, find_and_extract_wave_table
from .exceptions import TableExtractionError

logger = logging.getLogger(__name__)


def extract_laxity_instruments(data: bytes, load_addr: int, wave_table: Optional[List[Tuple[int, int]]] = None) -> List[Dict]:
    """
    Extract actual instrument data from Laxity SID file.

    Args:
        data: C64 program data
        load_addr: Memory load address
        wave_table: Optional wave table entries

    Returns:
        List of instrument dicts with full 8-byte Laxity format (empty list for small data)

    Raises:
        TableExtractionError: If data is invalid (but not for size constraints)
    """
    if not data or len(data) < 128:
        logger.warning(f"Data too small for instrument extraction: {len(data) if data else 0} bytes, returning empty list")
        return []

    instruments = []

    try:
        instr_addr = find_instrument_table(data, load_addr, wave_table=wave_table)
    except TableExtractionError:
        # If table extraction fails, return default instruments
        instr_addr = None

    if not instr_addr:
        # Return 16 default instruments
        for i in range(16):
            instruments.append({
                'index': i,
                'ad': 0x09,
                'sr': 0x00,
                'restart': 0x00,
                'filter_setting': 0x00,
                'filter_ptr': 0x00,
                'pulse_ptr': 0x00,
                'pulse_property': 0x00,
                'wave_ptr': 0x00,
                'ctrl': 0x41,
                'wave_for_sf2': 0x41,
                'name': f"Instr {i:02d} Pulse"
            })
        return instruments

    instr_offset = instr_addr - load_addr

    if instr_offset < 0 or instr_offset >= len(data):
        raise TableExtractionError(f"Invalid instrument table offset: {instr_offset}")

    real_instr_count = 0
    try:
        for i in range(32):
            off = instr_offset + (i * 8)
            if off + 8 > len(data):
                break

            instr_data = data[off:off + 8]
            if len(instr_data) < 8:
                raise TableExtractionError(f"Insufficient data for instrument {i} at offset {off}")

            ad = instr_data[0]
            sr = instr_data[1]

            if ad == 0 and sr == 0 and instr_data[7] == 0 and i > 0:
                break

            real_instr_count = i + 1

            # Laxity instrument format (8 bytes):
            # 0: AD, 1: SR, 2-4: flags/unknown, 5: Pulse param, 6: Pulse Ptr, 7: Wave Ptr
            pulse_param = instr_data[5]
            pulse_ptr = instr_data[6]
            wave_ptr = instr_data[7]
            filter_ptr = 0  # Filter pointer not directly in instrument table

            # Flags/control bytes (bytes 2-4)
            flags1 = instr_data[2]
            flags2 = instr_data[3]
            flags3 = instr_data[4]

            # Keep compatibility fields
            restart = flags1  # Use first flag byte as restart value
            filter_setting = flags3  # Use third flag byte as filter setting
            pulse_property = 0

            wave_name = "Wave"
            wave_for_sf2 = 0x41

            if wave_table and wave_ptr < len(wave_table):
                _, waveform = wave_table[wave_ptr]
                wf_base = waveform & 0xF0
                if wf_base == 0x80:
                    wave_name = "Noise"
                elif wf_base == 0x40:
                    wave_name = "Pulse"
                elif wf_base == 0x20:
                    wave_name = "Saw"
                elif wf_base == 0x10:
                    wave_name = "Tri"
                else:
                    wave_name = "Wave"
                wave_for_sf2 = waveform

            attack = (ad >> 4) & 0x0F
            decay = ad & 0x0F
            sustain = (sr >> 4) & 0x0F
            release = sr & 0x0F

            # Determine sound character from ADSR
            if attack == 0 and decay <= 3 and release <= 8:
                char = "Perc"
            elif attack >= 10:
                char = "Pad"
            elif sustain <= 6 and release >= 4 and release <= 10 and attack <= 1:
                char = "Bass"
            elif sustain >= 12:
                char = "Lead"
            elif release <= 3 and attack <= 2:
                char = "Stab"
            elif attack >= 3 and attack <= 6 and release <= 6:
                char = "Pluck"
            elif sustain >= 8:
                char = "Lead"
            else:
                char = ""

            if char:
                name = f"{i:02d} {char} {wave_name}"
            else:
                name = f"{i:02d} {wave_name}"

            instruments.append({
                'index': i,
                'ad': ad,
                'sr': sr,
                'restart': restart,
                'filter_setting': filter_setting,
                'filter_ptr': filter_ptr,
                'pulse_ptr': pulse_ptr,
                'pulse_property': pulse_property,
                'wave_ptr': wave_ptr,
                'ctrl': 0x41,
                'wave_for_sf2': wave_for_sf2,
                'name': name
            })

    except IndexError as e:
        raise TableExtractionError(f"Index error while extracting instruments: {e}")

    # Fill remaining slots with defaults
    for i in range(real_instr_count, 16):
        instruments.append({
            'index': i,
            'ad': 0x09,
            'sr': 0x00,
            'restart': 0x00,
            'filter_setting': 0x00,
            'filter_ptr': 0x00,
            'pulse_ptr': 0x00,
            'pulse_property': 0x00,
            'wave_ptr': 0x00,
            'ctrl': 0x41,
            'wave_for_sf2': 0x41,
            'name': f"{i:02d} Pulse"
        })

    return instruments


def extract_laxity_wave_table(data: bytes, load_addr: int, siddump_waveforms: Optional[List[int]] = None) -> List[Tuple[int, int]]:
    """
    Extract wave table data from Laxity SID file.

    Args:
        data: C64 program data
        load_addr: Memory load address
        siddump_waveforms: Optional list of waveforms from siddump

    Returns:
        List of (waveform, note_offset) tuples from editor display format
        These will be converted to column-major format when written to SF2

    Raises:
        TableExtractionError: If data is invalid or wave table extraction fails
    """
    if not data or len(data) < 64:
        raise TableExtractionError(f"Data too small for wave table extraction: {len(data) if data else 0} bytes")

    try:
        wave_addr, wave_entries = find_and_extract_wave_table(data, load_addr, siddump_waveforms=siddump_waveforms)
    except TableExtractionError:
        # Fall back to default entries if extraction fails
        wave_entries = []

    if wave_entries and len(wave_entries) >= 4:
        return wave_entries

    # Default entries for basic waveforms
    # Format: (col0, col1) where col0=waveform or $7F, col1=note or target
    if not wave_entries or len(wave_entries) < 4:
        wave_entries = [
            (0x41, 0x00),  # Pulse, note=0
            (0x7F, 0x00),  # Jump to 0
            (0x21, 0x00),  # Saw, note=0
            (0x7F, 0x02),  # Jump to 2
            (0x11, 0x00),  # Triangle, note=0
            (0x7F, 0x04),  # Jump to 4
            (0x81, 0x00),  # Noise, note=0
            (0x7F, 0x06),  # Jump to 6
        ]

    return wave_entries
