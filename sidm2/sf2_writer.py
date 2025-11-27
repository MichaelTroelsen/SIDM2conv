"""
SF2 file writer - writes SID Factory II project files.
"""

import logging
import struct
import os
from typing import Optional

from .models import ExtractedData, SF2DriverInfo
from .table_extraction import find_and_extract_wave_table, extract_all_laxity_tables
from .instrument_extraction import extract_laxity_instruments, extract_laxity_wave_table
from .sequence_extraction import (
    get_command_names,
    extract_command_parameters,
    build_command_index_map,
    build_sf2_command_table,
    extract_arpeggio_indices,
    find_arpeggio_table_in_memory,
    build_sf2_arp_table
)
from .exceptions import SF2WriteError, TemplateNotFoundError

logger = logging.getLogger(__name__)


class SF2Writer:
    """Write SID Factory II .sf2 project files"""

    # SF2 file format constants
    SF2_FILE_ID = 0x1337
    SF2_DRIVER_VERSION = 11

    # Header block IDs
    BLOCK_DESCRIPTOR = 1
    BLOCK_DRIVER_COMMON = 2
    BLOCK_DRIVER_TABLES = 3
    BLOCK_INSTRUMENT_DESC = 4
    BLOCK_MUSIC_DATA = 5
    BLOCK_END = 0xFF

    def __init__(self, extracted_data: ExtractedData, driver_type: str = 'np20') -> None:
        self.data = extracted_data
        self.output = bytearray()
        self.template_path = None
        self.driver_info = SF2DriverInfo()
        self.load_address = 0
        self.driver_type = driver_type

    def write(self, filepath: str) -> None:
        """Write the SF2 file.

        Args:
            filepath: Output file path

        Raises:
            TemplateNotFoundError: If no template/driver is found
            SF2WriteError: If writing fails
        """
        template_path = self._find_template(self.driver_type)

        if template_path and os.path.exists(template_path):
            logger.info(f"Using template: {template_path}")
            try:
                with open(template_path, 'rb') as f:
                    template_data = f.read()
            except IOError as e:
                raise SF2WriteError(f"Failed to read template: {e}")

            self.output = bytearray(template_data)
            self._inject_music_data_into_template()
        else:
            driver_path = self._find_driver()

            if driver_path and os.path.exists(driver_path):
                logger.info(f"Using driver: {driver_path}")
                try:
                    with open(driver_path, 'rb') as f:
                        driver_data = f.read()
                except IOError as e:
                    raise SF2WriteError(f"Failed to read driver: {e}")

                self.output = bytearray(driver_data)
            else:
                logger.warning("No template or driver found, creating minimal structure")
                self._create_minimal_structure()

            self._inject_music_data()

        self._inject_auxiliary_data()

        try:
            with open(filepath, 'wb') as f:
                f.write(self.output)
        except IOError as e:
            raise SF2WriteError(f"Failed to write SF2 file: {e}")

        logger.info(f"Written SF2 file: {filepath}")
        logger.info(f"File size: {len(self.output)} bytes")

    def _find_template(self, driver_type: str = 'driver11') -> Optional[str]:
        """Find an SF2 template file to use as base

        Args:
            driver_type: Driver to use - 'driver11' (d11) or 'np20' (default)
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        driver_templates = {
            'driver11': [
                os.path.join(base_dir, 'G5', 'drivers', 'sf2driver11_05.prg'),
                os.path.join(base_dir, 'G5', 'drivers', 'sf2driver11_00.prg'),
                'template.sf2',
                r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\music\Driver 11 Test - Arpeggio.sf2',
            ],
            'np20': [
                os.path.join(base_dir, 'G5', 'drivers', 'sf2driver_np20_00.prg'),
                'template_np20.sf2',
                r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\drivers\sf2driver_np20_00.prg',
                r'C:\Users\mit\Downloads\SIDFactoryII_Win32_20231002\drivers\sf2driver_np20_00.prg',
            ],
        }

        # Support shorthand aliases
        if driver_type in ('d11', '11'):
            driver_type = 'driver11'

        search_paths = driver_templates.get(driver_type, driver_templates['driver11'])

        for path in search_paths:
            if os.path.isabs(path):
                if os.path.exists(path):
                    return path
            else:
                full_path = os.path.join(base_dir, path)
                if os.path.exists(full_path):
                    return full_path

        return None

    def _parse_sf2_header(self) -> bool:
        """Parse the SF2 driver header to find data locations"""
        if len(self.output) < 4:
            return False

        self.load_address = struct.unpack('<H', self.output[0:2])[0]

        file_id = struct.unpack('<H', self.output[2:4])[0]
        if file_id != self.SF2_FILE_ID:
            logger.warning(f" File ID {file_id:04X} != expected {self.SF2_FILE_ID:04X}")
            return False

        logger.debug(f"Parsing SF2 header (load address: ${self.load_address:04X})")

        offset = 4
        while offset < len(self.output) - 2:
            block_id = self.output[offset]
            if block_id == self.BLOCK_END:
                break

            block_size = self.output[offset + 1]
            block_data = self.output[offset + 2:offset + 2 + block_size]

            if block_id == self.BLOCK_DESCRIPTOR:
                self._parse_descriptor_block(block_data)
            elif block_id == self.BLOCK_MUSIC_DATA:
                self._parse_music_data_block(block_data)
            elif block_id == self.BLOCK_DRIVER_TABLES:
                self._parse_tables_block(block_data)

            offset += 2 + block_size

        return True

    def _parse_descriptor_block(self, data: bytes) -> None:
        """Parse descriptor block"""
        if len(data) < 3:
            return

        self.driver_info.driver_type = data[0]
        self.driver_info.driver_size = struct.unpack('<H', data[1:3])[0]

        name_end = 3
        while name_end < len(data) and data[name_end] != 0:
            name_end += 1

        self.driver_info.driver_name = data[3:name_end].decode('latin-1', errors='replace')
        logger.debug(f"  Driver: {self.driver_info.driver_name}")

    def _parse_music_data_block(self, data: bytes) -> None:
        """Parse music data block to find sequence/orderlist locations"""
        if len(data) < 18:
            return

        idx = 0
        self.driver_info.track_count = data[idx]
        idx += 1

        self.driver_info.orderlist_ptrs_lo = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        self.driver_info.orderlist_ptrs_hi = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2

        self.driver_info.sequence_count = data[idx]
        idx += 1

        self.driver_info.sequence_ptrs_lo = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        self.driver_info.sequence_ptrs_hi = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2

        self.driver_info.orderlist_size = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        self.driver_info.orderlist_start = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2

        self.driver_info.sequence_size = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        self.driver_info.sequence_start = struct.unpack('<H', data[idx:idx+2])[0]

        logger.debug(f"  Tracks: {self.driver_info.track_count}")
        logger.debug(f"  Sequences: {self.driver_info.sequence_count}")
        logger.debug(f"  Sequence start: ${self.driver_info.sequence_start:04X}")
        logger.debug(f"  Orderlist start: ${self.driver_info.orderlist_start:04X}")

    def _parse_tables_block(self, data: bytes) -> None:
        """Parse table definitions block to find table addresses"""
        idx = 0

        while idx < len(data):
            if idx >= len(data):
                break

            table_type = data[idx]
            if table_type == 0xFF:
                break

            if idx + 3 > len(data):
                break

            table_id = data[idx + 1]
            text_field_size = data[idx + 2]

            name_start = idx + 3
            name_end = name_start
            while name_end < len(data) and data[name_end] != 0:
                name_end += 1
            name = data[name_start:name_end].decode('latin-1', errors='replace')

            pos = name_end + 1
            if pos + 12 <= len(data):
                addr = struct.unpack('<H', data[pos+5:pos+7])[0]
                columns = struct.unpack('<H', data[pos+7:pos+9])[0]
                rows = struct.unpack('<H', data[pos+9:pos+11])[0]

                table_info = {
                    'type': table_type,
                    'id': table_id,
                    'addr': addr,
                    'columns': columns,
                    'rows': rows,
                    'name': name
                }

                if table_type == 0x80:
                    self.driver_info.table_addresses['Instruments'] = table_info
                    logger.debug(f"    Instruments table at ${addr:04X} ({columns}×{rows}) [ID={table_id}]")
                elif table_type == 0x81:
                    self.driver_info.table_addresses['Commands'] = table_info
                    logger.debug(f"    Commands table at ${addr:04X} ({columns}×{rows}) [ID={table_id}]")
                else:
                    if name:
                        self.driver_info.table_addresses[name] = table_info
                        first_char = name[0] if name else ''
                        if first_char in ['W', 'P', 'F', 'A', 'T']:
                            key_map = {'W': 'Wave', 'P': 'Pulse', 'F': 'Filter', 'A': 'Arp', 'T': 'Tempo'}
                            self.driver_info.table_addresses[key_map.get(first_char, first_char)] = table_info

                idx = pos + 12
            else:
                break

    def _addr_to_offset(self, addr: int) -> int:
        """Convert C64 address to file offset"""
        return addr - self.load_address + 2

    def _inject_music_data_into_template(self) -> None:
        """Inject extracted music data into a template SF2 file"""
        logger.info("Injecting music data into template...")
        logger.debug(f"Template size: {len(self.output)} bytes")

        if not self._parse_sf2_header():
            logger.warning(" Could not parse SF2 header, using fallback")
            self._print_extraction_summary()
            return

        required_size = self._addr_to_offset(self.driver_info.sequence_start) + (self.driver_info.sequence_count * 256)
        if len(self.output) < required_size:
            logger.debug(f"  Expanding file from {len(self.output)} to {required_size} bytes")
            self.output.extend(bytearray(required_size - len(self.output)))

        if self.data.instruments or self.data.raw_sequences:
            self._inject_instruments()

        if self.data.sequences and self.driver_info.sequence_start:
            self._inject_sequences()

        if self.data.orderlists and self.driver_info.orderlist_start:
            self._inject_orderlists()

        self._inject_wave_table()
        self._inject_pulse_table()
        self._inject_filter_table()
        self._inject_hr_table()
        self._inject_init_table()
        self._inject_tempo_table()
        self._inject_arp_table()
        self._inject_commands()

        self._print_extraction_summary()

    def _inject_sequences(self) -> None:
        """Inject sequence data into the SF2 file using packed format"""
        logger.debug("\n  Injecting sequences...")

        seq_start = self._addr_to_offset(self.driver_info.sequence_start)
        ptr_lo_offset = self._addr_to_offset(self.driver_info.sequence_ptrs_lo)
        ptr_hi_offset = self._addr_to_offset(self.driver_info.sequence_ptrs_hi)

        if seq_start >= len(self.output) or seq_start < 0:
            logger.warning(f"     Invalid sequence start offset {seq_start}")
            return

        SEQUENCE_SLOT_SIZE = 256
        sequences_written = 0

        for i, seq in enumerate(self.data.sequences[:127]):
            if i >= self.driver_info.sequence_count:
                break

            current_addr = self.driver_info.sequence_start + (i * SEQUENCE_SLOT_SIZE)

            if ptr_lo_offset + i < len(self.output):
                self.output[ptr_lo_offset + i] = current_addr & 0xFF
            if ptr_hi_offset + i < len(self.output):
                self.output[ptr_hi_offset + i] = (current_addr >> 8) & 0xFF

            seq_offset = self._addr_to_offset(current_addr)

            # SF2 sequences use packed format: only write instrument/command when they change
            # Format: [instr] [cmd] note [instr] [cmd] note ... 0x7F
            # Where instrument bytes are 0xA0-0xBF and command bytes are 0x01-0x3F
            #
            # Phase 1: Sequences now come pre-formatted from sequence_translator with:
            # - Proper SF2 command indices (0-63) from command_index_map
            # - Gate markers (0x7E sustain, 0x80 gate-off) already inserted
            # - Duration expansion already applied
            rows_written = 0
            for event in seq:
                # Skip duration bytes (0x80-0x9F) - shouldn't appear but be safe
                if 0x80 <= event.note <= 0x9F:
                    continue

                # Write instrument change if not "no change" (0x80)
                if event.instrument != 0x80 and seq_offset < len(self.output):
                    self.output[seq_offset] = event.instrument
                    seq_offset += 1

                # Write command index directly (Phase 1: already mapped to 0-63)
                # event.command is either 0x80 (no change) or 0-63 (command index)
                if event.command != 0x80 and seq_offset < len(self.output):
                    self.output[seq_offset] = event.command
                    seq_offset += 1

                # Always write note (including gate markers 0x7E, 0x80)
                if seq_offset < len(self.output):
                    self.output[seq_offset] = event.note
                    seq_offset += 1
                    rows_written += 1

                # Stop at end marker
                if event.note == 0x7F:
                    break

            # Ensure sequence ends with 0x7F
            if rows_written > 0 and seq_offset > 0:
                if self.output[seq_offset - 1] != 0x7F:
                    if seq_offset < len(self.output):
                        self.output[seq_offset] = 0x7F

            sequences_written += 1

        logger.info(f"    Written {sequences_written} sequences")

    def _inject_orderlists(self) -> None:
        """Inject orderlist data into the SF2 file using fixed 256-byte slots"""
        logger.info("  Injecting orderlists...")

        ol_start = self._addr_to_offset(self.driver_info.orderlist_start)
        ptr_lo_offset = self._addr_to_offset(self.driver_info.orderlist_ptrs_lo)
        ptr_hi_offset = self._addr_to_offset(self.driver_info.orderlist_ptrs_hi)

        if ol_start >= len(self.output) or ol_start < 0:
            logger.warning(f"     Invalid orderlist start offset {ol_start}")
            return

        ORDERLIST_SLOT_SIZE = 256
        tracks_written = 0

        for track, orderlist in enumerate(self.data.orderlists[:3]):
            current_addr = self.driver_info.orderlist_start + (track * ORDERLIST_SLOT_SIZE)

            if ptr_lo_offset + track < len(self.output):
                self.output[ptr_lo_offset + track] = current_addr & 0xFF
            if ptr_hi_offset + track < len(self.output):
                self.output[ptr_hi_offset + track] = (current_addr >> 8) & 0xFF

            ol_offset = self._addr_to_offset(current_addr)
            last_trans = -1

            for item in orderlist:
                # Handle both formats: simple int or (transposition, seq_idx) tuple
                if isinstance(item, tuple):
                    transposition, seq_idx = item
                else:
                    transposition = 0  # Default transposition
                    seq_idx = item

                sf2_trans = 0xA0 + (transposition if transposition < 32 else transposition - 256)
                sf2_trans = max(0x80, min(0xBF, sf2_trans))

                if sf2_trans != last_trans:
                    if ol_offset < len(self.output):
                        self.output[ol_offset] = sf2_trans
                        ol_offset += 1
                        last_trans = sf2_trans

                if ol_offset < len(self.output):
                    self.output[ol_offset] = seq_idx & 0x7F
                    ol_offset += 1

            if ol_offset + 1 < len(self.output):
                self.output[ol_offset] = 0xFF
                self.output[ol_offset + 1] = 0x00

            tracks_written += 1

        logger.info(f"    Written {tracks_written} orderlists")

    def _inject_instruments(self) -> None:
        """Inject instrument data into the SF2 file using extracted Laxity data"""
        logger.info("  Injecting instruments...")

        if 'Instruments' not in self.driver_info.table_addresses:
            logger.debug("    Warning: No instrument table found in driver")
            return

        instr_table = self.driver_info.table_addresses['Instruments']
        instr_addr = instr_table['addr']
        columns = instr_table['columns']
        rows = instr_table['rows']

        wave_addr, wave_entries = find_and_extract_wave_table(self.data.c64_data, self.data.load_address)

        # Use instruments from laxity_parser (already in self.data.instruments as raw bytes)
        # Convert them to the format expected by SF2
        laxity_instruments = []
        for i, instr_bytes in enumerate(self.data.instruments[:16]):
            if len(instr_bytes) >= 8:
                # Laxity instrument format (8 bytes):
                # 0: AD, 1: SR, 2-4: flags/unknown, 5: Pulse param, 6: Pulse Ptr, 7: Wave Ptr
                ad = instr_bytes[0]
                sr = instr_bytes[1]
                restart = instr_bytes[2]
                filter_setting = instr_bytes[4]
                pulse_ptr = instr_bytes[6]
                wave_ptr = instr_bytes[7]
                filter_ptr = 0  # Not directly in instrument table

                # Determine waveform from wave table
                wave_for_sf2 = 0x41  # Default pulse
                if wave_entries and wave_ptr < len(wave_entries):
                    waveform, _ = wave_entries[wave_ptr]
                    wave_for_sf2 = waveform

                laxity_instruments.append({
                    'index': i,
                    'ad': ad,
                    'sr': sr,
                    'restart': restart,
                    'filter_setting': filter_setting,
                    'filter_ptr': filter_ptr,
                    'pulse_ptr': pulse_ptr,
                    'pulse_property': 0,
                    'wave_ptr': wave_ptr,
                    'ctrl': 0x41,
                    'wave_for_sf2': wave_for_sf2,
                    'name': f"{i:02d} Instr"
                })

        # Fill remaining slots with defaults
        while len(laxity_instruments) < 16:
            i = len(laxity_instruments)
            laxity_instruments.append({
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

        self.data.laxity_instruments = laxity_instruments

        logger.info(f"    Converted {len(self.data.instruments)} Laxity instruments from parser")

        if hasattr(self.data, 'siddump_data') and self.data.siddump_data:
            siddump_adsr = set(self.data.siddump_data['adsr_values'])
            laxity_adsr = set((i['ad'], i['sr']) for i in laxity_instruments)
            matches = len(siddump_adsr & laxity_adsr)
            match_rate = matches / len(siddump_adsr) if siddump_adsr else 0
            logger.debug(f"    Validation: {match_rate*100:.0f}% of siddump ADSR values found in extraction")

        def waveform_to_wave_index(wave_for_sf2) -> int:
            if wave_for_sf2 == 0x21:
                return 0x00
            elif wave_for_sf2 == 0x41:
                return 0x02
            elif wave_for_sf2 == 0x11:
                return 0x04
            elif wave_for_sf2 == 0x81:
                return 0x06
            else:
                return 0x00

        sf2_instruments = []
        is_np20 = columns == 8

        # Get valid wave entry points for validation
        from .table_extraction import get_valid_wave_entry_points
        valid_wave_points = get_valid_wave_entry_points(wave_entries) if wave_entries else {0}
        wave_table_size = len(wave_entries) if wave_entries else 0

        for lax_instr in laxity_instruments:
            wave_ptr = lax_instr.get('wave_ptr', 0)
            pulse_ptr = lax_instr.get('pulse_ptr', 0)
            filter_ptr = lax_instr.get('filter_ptr', 0)

            # Convert Laxity pulse_ptr from Y*4 indexing to direct index
            if pulse_ptr != 0 and pulse_ptr % 4 == 0:
                pulse_ptr = pulse_ptr // 4

            if wave_ptr == 0:
                wave_ptr = waveform_to_wave_index(lax_instr['wave_for_sf2'])

            # Validate wave pointer - must be within wave table bounds and at valid entry point
            if wave_table_size > 0 and wave_ptr >= wave_table_size:
                # Find closest valid entry point that's within bounds
                valid_in_bounds = [p for p in valid_wave_points if p < wave_table_size]
                if valid_in_bounds:
                    # Find the closest valid entry point
                    wave_ptr = min(valid_in_bounds, key=lambda p: abs(p - wave_ptr))
                else:
                    wave_ptr = 0
                logger.debug(f"    Clamped wave_ptr for instrument {lax_instr['index']} to {wave_ptr}")

            if is_np20:
                # NP20 instrument format (8 columns):
                # 0: AD, 1: SR, 2: ???, 3: ???, 4: Wave, 5: Pulse, 6: Filter, 7: ???
                sf2_instr = [
                    lax_instr['ad'],
                    lax_instr['sr'],
                    0x00,
                    0x00,
                    wave_ptr,
                    pulse_ptr,
                    filter_ptr,
                    0x00
                ]
            else:
                restart = lax_instr.get('restart', 0)
                flags = 0x00
                if restart & 0x80:
                    flags |= 0x80
                if restart & 0x10:
                    flags |= 0x10
                if lax_instr.get('filter_setting', 0):
                    flags |= 0x40

                sf2_instr = [
                    lax_instr['ad'],
                    lax_instr['sr'],
                    flags,
                    filter_ptr,
                    pulse_ptr,
                    wave_ptr
                ]
            sf2_instruments.append(sf2_instr)

        while len(sf2_instruments) < 16:
            if is_np20:
                sf2_instruments.append([0x09, 0xA0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            else:
                sf2_instruments.append([0x09, 0xA0, 0x00, 0x00, 0x00, 0x00])

        for i, lax_instr in enumerate(laxity_instruments):
            if i < len(sf2_instruments):
                instr = sf2_instruments[i]
                wave_names = {0x00: 'saw', 0x02: 'pulse', 0x04: 'tri', 0x06: 'noise'}
                wave_idx_pos = 4 if is_np20 else 5  # Fixed: NP20 wave ptr is at col 4, not 2
                wave_name = wave_names.get(instr[wave_idx_pos], '?')
                name = lax_instr.get('name', f'{i:02d} {wave_name}')
                logger.debug(f"      {i}: {name} (AD={instr[0]:02X} SR={instr[1]:02X})")

        instruments_written = 0

        for col in range(columns):
            for row in range(rows):
                offset = self._addr_to_offset(instr_addr) + col * rows + row

                if offset >= len(self.output):
                    continue

                if row < len(sf2_instruments) and col < len(sf2_instruments[row]):
                    self.output[offset] = sf2_instruments[row][col]
                else:
                    self.output[offset] = 0

            if col == 0:
                instruments_written = min(len(sf2_instruments), rows)

        logger.info(f"    Written {instruments_written} instruments")

    def _inject_wave_table(self) -> None:
        """Inject wave table data extracted from Laxity SID"""
        logger.info("  Injecting wave table...")

        if 'Wave' not in self.driver_info.table_addresses:
            logger.debug("    Warning: No wave table found in driver")
            return

        wave_table = self.driver_info.table_addresses['Wave']
        wave_addr = wave_table['addr']
        columns = wave_table['columns']
        rows = wave_table['rows']

        extracted_waves = extract_laxity_wave_table(self.data.c64_data, self.data.load_address)

        if extracted_waves:
            wave_data = extracted_waves
            logger.info(f"    Extracted {len(extracted_waves)} wave entries from SID")
        else:
            # Default: (col0, col1) = (waveform, note) or (0x7F, target)
            wave_data = [
                (0x41, 0x00), (0x7F, 0x00),  # Pulse, jump to 0
                (0x21, 0x00), (0x7F, 0x02),  # Saw, jump to 2
                (0x11, 0x00), (0x7F, 0x04),  # Tri, jump to 4
                (0x81, 0x00), (0x7F, 0x06),  # Noise, jump to 6
            ]

        if hasattr(self.data, 'siddump_data') and self.data.siddump_data:
            siddump_waveforms = set(self.data.siddump_data['waveforms'])
            # Waveform is in column 0 (first element), except for $7F jump commands
            existing_waveforms = set(col0 for col0, _ in wave_data if col0 != 0x7F)
            missing = siddump_waveforms - existing_waveforms
            missing = {wf for wf in missing
                      if (wf | 0x01) not in existing_waveforms
                      and wf not in (0x01, 0x09, 0xF0)}
            if missing:
                logger.debug(f"    Validation: {len(missing)} waveforms from siddump not in wave table")

        base_offset = self._addr_to_offset(wave_addr)

        # SF2 wave table format is column-major:
        # Column 0: Waveform ($11=tri, $21=saw, $41=pulse, $81=noise) or $7F for jump
        # Column 1: Note offset or jump target
        # Extraction returns (col0, col1) tuples
        for i, (col0, col1) in enumerate(wave_data):
            if i < rows and base_offset + i < len(self.output):
                self.output[base_offset + i] = col0

        col1_offset = base_offset + rows
        for i, (col0, col1) in enumerate(wave_data):
            if i < rows and col1_offset + i < len(self.output):
                self.output[col1_offset + i] = col1

        logger.info(f"    Written {len(wave_data)} wave table entries")

    def _inject_hr_table(self) -> None:
        """Inject HR (Hard Restart) table data"""
        logger.info("  Injecting HR table...")

        hr_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'HR' in name:
                hr_table = info
                break

        if not hr_table:
            logger.debug("    Warning: No HR table found")
            return

        hr_addr = hr_table['addr']
        rows = hr_table['rows']

        # Use extracted HR table or default
        hr_entries = getattr(self.data, 'hr_table', None)
        if not hr_entries:
            hr_entries = [(0x0F, 0x00)]  # Default fallback

        base_offset = self._addr_to_offset(hr_addr)

        for i, (frames, wave) in enumerate(hr_entries):
            if i < rows and base_offset + i < len(self.output):
                self.output[base_offset + i] = frames

        col1_offset = base_offset + rows
        for i, (frames, wave) in enumerate(hr_entries):
            if i < rows and col1_offset + i < len(self.output):
                self.output[col1_offset + i] = wave

        logger.info(f"    Written {len(hr_entries)} HR table entries (frames={hr_entries[0][0]})")

    def _inject_pulse_table(self) -> None:
        """Inject pulse table data extracted from Laxity SID"""
        logger.info("  Injecting Pulse table...")

        pulse_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'Pulse' in name or name == 'P':
                pulse_table = info
                break

        if not pulse_table:
            logger.debug("    Warning: No Pulse table found in driver")
            return

        pulse_addr = pulse_table['addr']
        columns = pulse_table['columns']
        rows = pulse_table['rows']

        laxity_tables = extract_all_laxity_tables(self.data.c64_data, self.data.load_address)
        pulse_entries = laxity_tables.get('pulse_table', [])

        if not pulse_entries:
            pulse_entries = [(0x08, 0x01, 0x40, 0x00)]

        base_offset = self._addr_to_offset(pulse_addr)

        # Convert from Laxity format (Y*4 indexing) to SF2 format (direct indexing)
        # Laxity: (val, cnt, dur, next_y) where next_y is pre-multiplied by 4
        # SF2: (val, cnt, dur, next_idx) where next_idx is direct entry number
        for col in range(min(columns, 4)):
            for i, entry in enumerate(pulse_entries):
                if i < rows:
                    offset = base_offset + (col * rows) + i
                    if offset < len(self.output) and col < len(entry):
                        value = entry[col]
                        # Index already converted during extraction (Y*4 → direct)
                        self.output[offset] = value

        logger.info(f"    Written {len(pulse_entries)} Pulse table entries")

    def _inject_filter_table(self) -> None:
        """Inject filter table data extracted from Laxity SID"""
        logger.info("  Injecting Filter table...")

        filter_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'Filter' in name or name == 'F':
                filter_table = info
                break

        if not filter_table:
            logger.debug("    Warning: No Filter table found in driver")
            return

        filter_addr = filter_table['addr']
        columns = filter_table['columns']
        rows = filter_table['rows']

        laxity_tables = extract_all_laxity_tables(self.data.c64_data, self.data.load_address)
        filter_entries = laxity_tables.get('filter_table', [])

        if not filter_entries:
            filter_entries = [(0x40, 0x01, 0x20, 0x00)]

        base_offset = self._addr_to_offset(filter_addr)

        for col in range(min(columns, 4)):
            for i, entry in enumerate(filter_entries):
                if i < rows:
                    offset = base_offset + (col * rows) + i
                    if offset < len(self.output) and col < len(entry):
                        self.output[offset] = entry[col]

        logger.info(f"    Written {len(filter_entries)} Filter table entries")

    def _inject_init_table(self) -> None:
        """Inject Init table data"""
        logger.info("  Injecting Init table...")

        init_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'Init' in name:
                init_table = info
                break

        if not init_table:
            logger.debug("    Warning: No Init table found in driver")
            return

        init_addr = init_table['addr']
        columns = init_table['columns']
        rows = init_table['rows']

        # Use extracted init table or build from defaults
        init_entries = getattr(self.data, 'init_table', None)
        if not init_entries:
            # Fallback to building from init_volume
            init_volume = getattr(self.data, 'init_volume', 0x0F)
            init_entries = [0x00, init_volume, 0x00, 0x01, 0x02]

        base_offset = self._addr_to_offset(init_addr)

        for i, val in enumerate(init_entries):
            if i < rows * columns and base_offset + i < len(self.output):
                self.output[base_offset + i] = val

        init_volume = init_entries[1] if len(init_entries) > 1 else 0x0F
        logger.info(f"    Written {len(init_entries)} Init table entries (volume={init_volume})")

    def _inject_tempo_table(self) -> None:
        """Inject Tempo table data"""
        logger.info("  Injecting Tempo table...")

        tempo_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'Tempo' in name or name == 'T':
                tempo_table = info
                break

        if not tempo_table:
            logger.debug("    Warning: No Tempo table found in driver")
            return

        tempo_addr = tempo_table['addr']
        rows = tempo_table['rows']

        tempo = self.data.tempo if hasattr(self.data, 'tempo') else 6
        multi_speed = getattr(self.data, 'multi_speed', 1)

        # Adjust tempo for multi-speed tunes
        # Multi-speed tunes call the play routine multiple times per frame
        # To maintain correct playback speed, we divide tempo by multi-speed factor
        if multi_speed > 1:
            adjusted_tempo = max(1, tempo // multi_speed)
            logger.info(f"    Multi-speed tune detected ({multi_speed}x), adjusting tempo: {tempo} -> {adjusted_tempo}")
            tempo = adjusted_tempo

        tempo_entries = [tempo, 0x7F]

        base_offset = self._addr_to_offset(tempo_addr)

        for i, val in enumerate(tempo_entries):
            if i < rows and base_offset + i < len(self.output):
                self.output[base_offset + i] = val

        logger.info(f"    Written tempo: {tempo}")

    def _inject_arp_table(self) -> None:
        """Inject Arpeggio table data"""
        logger.info("  Injecting Arp table...")

        arp_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'Arp' in name or name == 'A':
                arp_table = info
                break

        if not arp_table:
            logger.debug("    Warning: No Arp table found in driver")
            return

        arp_addr = arp_table['addr']
        columns = arp_table['columns']
        rows = arp_table['rows']

        # Use extracted arpeggio table if available, otherwise try to extract
        if hasattr(self.data, 'arp_table') and self.data.arp_table:
            arp_entries = self.data.arp_table
            logger.info(f"    Using {len(arp_entries)} extracted arpeggio entries")
        elif hasattr(self.data, 'raw_sequences') and self.data.raw_sequences:
            # Try to extract arpeggio table from raw sequences
            arp_indices = extract_arpeggio_indices(self.data.raw_sequences)
            if arp_indices:
                logger.debug(f"    Found arpeggio indices: {sorted(arp_indices)}")
                _, extracted_entries = find_arpeggio_table_in_memory(
                    self.data.c64_data,
                    self.data.load_address,
                    arp_indices
                )
                if extracted_entries:
                    arp_entries = build_sf2_arp_table(extracted_entries)
                    logger.info(f"    Extracted {len(extracted_entries)} arpeggio patterns")
                else:
                    # Use defaults
                    arp_entries = [
                        (0x00, 0x04, 0x07, 0x7F),  # Major chord
                        (0x00, 0x03, 0x07, 0x7F),  # Minor chord
                        (0x00, 0x0C, 0x7F, 0x00),  # Octave
                    ]
                    logger.debug("    No arpeggio table found, using defaults")
            else:
                # No arpeggios used, use defaults
                arp_entries = [
                    (0x00, 0x04, 0x07, 0x7F),  # Major chord
                    (0x00, 0x03, 0x07, 0x7F),  # Minor chord
                    (0x00, 0x0C, 0x7F, 0x00),  # Octave
                ]
                logger.debug("    No arpeggio commands in sequences, using defaults")
        else:
            # Default arpeggio patterns
            arp_entries = [
                (0x00, 0x04, 0x07, 0x7F),  # Major chord
                (0x00, 0x03, 0x07, 0x7F),  # Minor chord
                (0x00, 0x0C, 0x7F, 0x00),  # Octave
            ]
            logger.debug("    Using default arpeggio patterns")

        base_offset = self._addr_to_offset(arp_addr)

        for col in range(min(columns, 4)):
            for i, entry in enumerate(arp_entries):
                if i < rows:
                    offset = base_offset + (col * rows) + i
                    if offset < len(self.output) and col < len(entry):
                        self.output[offset] = entry[col]

        logger.info(f"    Written {len(arp_entries)} Arp table entries")

    def _inject_commands(self) -> None:
        """Inject command table data extracted from Laxity sequences"""
        logger.info("  Injecting Commands table...")

        if 'Commands' not in self.driver_info.table_addresses:
            logger.debug("    Warning: No Commands table found in driver")
            return

        cmd_table = self.driver_info.table_addresses['Commands']
        cmd_addr = cmd_table['addr']
        columns = cmd_table['columns']
        rows = cmd_table['rows']

        # Extract command parameters from raw sequences
        # Phase 1: Use pre-built command_index_map if available (from sequence_translator)
        if hasattr(self.data, 'command_index_map') and self.data.command_index_map:
            # Convert command_index_map to SF2 command table format
            # command_index_map is {(type, param1, param2): index}
            # We need to build array where sf2_commands[index] = (type, param1, param2)
            sf2_commands = [(0, 0, 0)] * 64
            for (cmd_type, param1, param2), index in self.data.command_index_map.items():
                if 0 <= index < 64:
                    sf2_commands[index] = (cmd_type, param1, param2)

            logger.info(f"    Using pre-built command table with {len(self.data.command_index_map)} entries (Phase 1)")
        elif hasattr(self.data, 'raw_sequences') and self.data.raw_sequences:
            # Legacy path: extract from raw sequences
            command_params = extract_command_parameters(
                self.data.c64_data,
                self.data.load_address,
                self.data.raw_sequences
            )

            # Build the full 64-entry command table
            sf2_commands = build_sf2_command_table(command_params)

            logger.info(f"    Extracted {len(command_params)} unique commands from sequences (legacy)")
        else:
            # Default commands if no sequences available
            sf2_commands = [(0, 0, 0)] * 64
            logger.debug("    Using default command table (no sequences available)")

        # Write commands to SF2 file
        # SF2 command table: 3 columns (type, param1, param2), 64 rows
        # Format is column-major: all types first, then all param1s, then all param2s
        base_offset = self._addr_to_offset(cmd_addr)

        commands_written = 0
        for col in range(min(columns, 3)):
            for row in range(min(rows, 64)):
                offset = base_offset + (col * rows) + row
                if offset < len(self.output) and row < len(sf2_commands):
                    cmd_type, param1, param2 = sf2_commands[row]
                    if col == 0:
                        self.output[offset] = cmd_type
                    elif col == 1:
                        self.output[offset] = param1
                    else:
                        self.output[offset] = param2

                    if col == 0:
                        commands_written += 1

        logger.info(f"    Written {commands_written} command entries")

    def _inject_auxiliary_data(self) -> None:
        """Inject auxiliary data with instrument and command names"""
        logger.info("  Injecting auxiliary data (names)...")

        wave_addr, wave_entries = find_and_extract_wave_table(self.data.c64_data, self.data.load_address)
        laxity_instruments = extract_laxity_instruments(self.data.c64_data, self.data.load_address, wave_entries)
        instrument_names = [instr['name'] for instr in laxity_instruments]
        command_names = get_command_names()

        instr_table_id = 1
        cmd_table_id = 0
        if 'Instruments' in self.driver_info.table_addresses:
            instr_table_id = self.driver_info.table_addresses['Instruments']['id']
        if 'Commands' in self.driver_info.table_addresses:
            cmd_table_id = self.driver_info.table_addresses['Commands']['id']

        aux_data = bytearray()

        desc_data = self._build_description_data()
        if desc_data:
            aux_data.append(5)
            aux_data.extend(struct.pack('<H', 1))
            aux_data.extend(struct.pack('<H', len(desc_data)))
            aux_data.extend(desc_data)

        table_text_data = self._build_table_text_data(instrument_names, command_names, instr_table_id, cmd_table_id)

        aux_data.append(4)
        aux_data.extend(struct.pack('<H', 2))
        aux_data.extend(struct.pack('<H', len(table_text_data)))
        aux_data.extend(table_text_data)

        aux_data.append(0)
        aux_data.extend(struct.pack('<H', 0))
        aux_data.extend(struct.pack('<H', 0))

        aux_pointer_offset = 0x0FFB - self.load_address + 2

        if aux_pointer_offset < len(self.output):
            self.output.extend(aux_data)

            if hasattr(self.data, 'header') and self.data.header:
                logger.info(f"    Written metadata: {self.data.header.name} by {self.data.header.author}")
            logger.info(f"    Written {len(instrument_names)} instrument names")
            logger.info(f"    Written {len(command_names)} command names")
        else:
            logger.debug("    Warning: Could not find auxiliary data pointer location")

    def _build_description_data(self) -> Optional[bytearray]:
        """Build description data block with song metadata from SID header"""
        if not hasattr(self.data, 'header') or not self.data.header:
            return None

        header = self.data.header
        data = bytearray()

        name = header.name if header.name else ""
        name_bytes = name.encode('latin-1', errors='replace')[:255]
        data.append(len(name_bytes))
        data.extend(name_bytes)

        author = header.author if header.author else ""
        author_bytes = author.encode('latin-1', errors='replace')[:255]
        data.append(len(author_bytes))
        data.extend(author_bytes)

        copyright_str = header.copyright if header.copyright else ""
        copyright_bytes = copyright_str.encode('latin-1', errors='replace')[:255]
        data.append(len(copyright_bytes))
        data.extend(copyright_bytes)

        return data

    def _build_table_text_data(self, instrument_names, command_names, instr_table_id=1, cmd_table_id=0) -> bytearray:
        """Build the table text data block"""
        data = bytearray()

        num_tables = 2
        data.append(num_tables)

        data.extend(struct.pack('<i', instr_table_id))
        data.extend(struct.pack('<H', 1))
        data.extend(struct.pack('<H', len(instrument_names)))
        for name in instrument_names:
            name_bytes = name.encode('latin-1', errors='replace')[:255]
            data.append(len(name_bytes))
            data.extend(name_bytes)

        data.extend(struct.pack('<i', cmd_table_id))
        data.extend(struct.pack('<H', 1))
        data.extend(struct.pack('<H', len(command_names)))
        for name in command_names:
            name_bytes = name.encode('latin-1', errors='replace')[:255]
            data.append(len(name_bytes))
            data.extend(name_bytes)

        return data

    def _print_extraction_summary(self) -> None:
        """Print summary of extracted data"""
        if self.data.sequences:
            logger.debug(f"\n  Extracted {len(self.data.sequences)} sequences:")
            for i, seq in enumerate(self.data.sequences[:5]):
                logger.debug(f"    Sequence {i}: {len(seq)} events")
            if len(self.data.sequences) > 5:
                logger.debug(f"    ... and {len(self.data.sequences) - 5} more")

        if self.data.instruments:
            logger.debug(f"\n  Extracted {len(self.data.instruments)} instruments")

        if self.data.orderlists:
            logger.debug(f"\n  Created {len(self.data.orderlists)} orderlists")

        if hasattr(self.data, 'raw_sequences') and self.data.raw_sequences:
            from .sequence_extraction import analyze_sequence_commands
            cmd_analysis = analyze_sequence_commands(self.data.raw_sequences)
            if cmd_analysis['commands_used']:
                logger.debug(f"\n  Commands used in sequences:")
                cmd_names = get_command_names()
                for cmd in sorted(cmd_analysis['commands_used']):
                    count = cmd_analysis['command_counts'].get(cmd, 0)
                    name = cmd_names[cmd] if cmd < len(cmd_names) else f"Cmd {cmd}"
                    logger.debug(f"    {cmd:2d}: {name} ({count}x)")

    def _find_driver(self) -> Optional[str]:
        """Find SF2 driver file"""
        search_paths = [
            'sf2driver16_01.prg',
            'drivers/sf2driver16_01.prg',
            '../drivers/sf2driver16_01.prg',
        ]

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        for path in search_paths:
            full_path = os.path.join(base_dir, path)
            if os.path.exists(full_path):
                return full_path

        return None

    def _create_minimal_structure(self) -> None:
        """Create a minimal SF2-like structure"""
        self.output = bytearray(8192)

    def _inject_music_data(self) -> None:
        """Inject extracted music data into the SF2 structure"""
        logger.info(" Music data injection is a placeholder")
        logger.debug("The output file structure may need manual refinement")

