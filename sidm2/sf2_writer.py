"""
SF2 file writer - writes SID Factory II project files.

Version: 1.1.0 - Added custom error handling (v2.5.2)
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
from . import errors

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
            errors.FileNotFoundError: If no template/driver is found
            errors.PermissionError: If file read/write fails
            errors.ConversionError: If conversion fails
        """
        template_path = self._find_template(self.driver_type)

        if template_path and os.path.exists(template_path):
            logger.info(f"Using template: {template_path}")
            try:
                with open(template_path, 'rb') as f:
                    template_data = f.read()
            except IOError as e:
                raise errors.PermissionError(
                    operation="read",
                    path=template_path,
                    docs_link="guides/TROUBLESHOOTING.md#5-permission-problems"
                )

            logger.info(f"  Template size: {len(template_data)} bytes")
            self.output = bytearray(template_data)

            # Log detailed template structure
            self._log_sf2_structure("TEMPLATE LOADED", template_data)

            # Use Laxity-specific injection for Laxity driver
            if self.driver_type == 'laxity':
                self._inject_laxity_music_data()
            else:
                self._inject_music_data_into_template()
        else:
            driver_path = self._find_driver()

            if driver_path and os.path.exists(driver_path):
                logger.info(f"Using driver: {driver_path}")
                try:
                    with open(driver_path, 'rb') as f:
                        driver_data = f.read()
                except IOError as e:
                    raise errors.PermissionError(
                        operation="read",
                        path=driver_path,
                        docs_link="guides/TROUBLESHOOTING.md#5-permission-problems"
                    )

                logger.info(f"  Driver size: {len(driver_data)} bytes")
                self.output = bytearray(driver_data)
            else:
                logger.warning("No template or driver found, creating minimal structure")
                self._create_minimal_structure()

            self._inject_music_data()
            self._update_table_definitions()

        self._inject_auxiliary_data()

        # Log final structure before writing
        self._log_sf2_structure("FINAL FILE STRUCTURE", self.output)

        try:
            with open(filepath, 'wb') as f:
                f.write(self.output)
        except IOError as e:
            raise errors.PermissionError(
                operation="write",
                path=filepath,
                docs_link="guides/TROUBLESHOOTING.md#5-permission-problems"
            )

        logger.info(f"Written SF2 file: {filepath}")
        logger.info(f"File size: {len(self.output)} bytes")

        # Validate written file structure
        self._validate_sf2_file(filepath)

    def _find_template(self, driver_type: str = 'driver11') -> Optional[str]:
        """Find an SF2 template file to use as base

        Args:
            driver_type: Driver to use - 'driver11' (d11) or 'np20' (default)
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        driver_templates = {
            'driver11': [
                # PREFER SF2 EXAMPLE FILES - they have correct table addresses!
                os.path.join(base_dir, 'G5', 'examples', 'Driver 11 Test - Arpeggio.sf2'),
                r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\music\Driver 11 Test - Arpeggio.sf2',
                'template.sf2',
                # .prg driver files have WRONG table addresses - use as fallback only
                os.path.join(base_dir, 'G5', 'drivers', 'sf2driver11_03.prg'),
                os.path.join(base_dir, 'G5', 'drivers', 'sf2driver11_05.prg'),
                os.path.join(base_dir, 'G5', 'drivers', 'sf2driver11_00.prg'),
            ],
            'np20': [
                os.path.join(base_dir, 'G5', 'drivers', 'sf2driver_np20_00.prg'),
                'template_np20.sf2',
                r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\drivers\sf2driver_np20_00.prg',
                r'C:\Users\mit\Downloads\SIDFactoryII_Win32_20231002\drivers\sf2driver_np20_00.prg',
            ],
            'laxity': [
                os.path.join(base_dir, 'drivers', 'laxity', 'sf2driver_laxity_00.prg'),
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
                    logger.info(f"    Instruments table at ${addr:04X} ({columns}×{rows}) [ID={table_id}]")
                elif table_type == 0x81:
                    self.driver_info.table_addresses['Commands'] = table_info
                    logger.info(f"    Commands table at ${addr:04X} ({columns}×{rows}) [ID={table_id}]")
                else:
                    if name:
                        self.driver_info.table_addresses[name] = table_info
                        first_char = name[0] if name else ''
                        if first_char in ['W', 'P', 'F', 'A', 'T']:
                            key_map = {'W': 'Wave', 'P': 'Pulse', 'F': 'Filter', 'A': 'Arp', 'T': 'Tempo'}
                            mapped_name = key_map.get(first_char, first_char)
                            self.driver_info.table_addresses[mapped_name] = table_info
                            logger.info(f"    {mapped_name} table (\"{name}\") at ${addr:04X} ({columns}×{rows}) [type=${table_type:02X}, ID={table_id}]")

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

        # PACKED MODE: Don't pre-allocate fixed 256-byte slots
        # Sequences will dynamically extend the buffer as needed during injection
        # Just ensure we have space up to the sequence start address
        required_size = self._addr_to_offset(self.driver_info.sequence_start) + 256  # Small initial buffer
        if len(self.output) < required_size:
            logger.debug(f"  Ensuring minimum file size: {required_size} bytes")
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
        """Inject sequence data into the SF2 file using packed variable-length format (Tetris-style)"""
        logger.debug("\n  Injecting sequences...")

        seq_start = self._addr_to_offset(self.driver_info.sequence_start)
        ptr_lo_offset = self._addr_to_offset(self.driver_info.sequence_ptrs_lo)
        ptr_hi_offset = self._addr_to_offset(self.driver_info.sequence_ptrs_hi)

        if seq_start >= len(self.output) or seq_start < 0:
            logger.warning(f"     Invalid sequence start offset {seq_start}")
            return

        # PACKED MODE: Calculate actual size needed for each sequence
        # Sequences are written contiguously (Tetris-style stacking)
        # Only write sequences with actual data (skip empty placeholders)
        sequences_written = 0
        current_offset = seq_start  # Track current write position
        current_addr = self.driver_info.sequence_start  # Current address in C64 memory

        # Determine max sequence to write (up to driver limit or actual sequences)
        max_sequences = min(len(self.data.sequences), 256)

        for i in range(max_sequences):
            if i >= len(self.data.sequences):
                break

            seq = self.data.sequences[i]

            # Skip empty placeholder sequences (just end marker with 0x80 persistence)
            if len(seq) == 1 and seq[0].note == 0x7F and seq[0].instrument == 0x80 and seq[0].command == 0x80:
                # Write null pointer for empty sequence
                if ptr_lo_offset + i < len(self.output):
                    self.output[ptr_lo_offset + i] = 0x00
                if ptr_hi_offset + i < len(self.output):
                    self.output[ptr_hi_offset + i] = 0x00
                continue

            # Write sequence pointer (points to where this sequence will be written)
            if ptr_lo_offset + i < len(self.output):
                self.output[ptr_lo_offset + i] = current_addr & 0xFF
            if ptr_hi_offset + i < len(self.output):
                self.output[ptr_hi_offset + i] = (current_addr >> 8) & 0xFF

            seq_offset = current_offset  # Write at current packed position

            # SF2 sequences use packed format: only write instrument/command when they change
            # Format: [instr] [cmd] note [instr] [cmd] note ... 0x7F
            # Where instrument bytes are 0xA0-0xBF and command bytes are 0x01-0x3F
            #
            # Phase 1: Sequences now come pre-formatted from sequence_translator with:
            # - Proper SF2 command indices (0-63) from command_index_map
            # - Gate markers (0x7E sustain, 0x80 gate-off) already inserted
            # - Duration expansion already applied

            sequence_start_offset = seq_offset  # Remember where this sequence started
            rows_written = 0

            # Ensure we have enough space - resize output buffer if needed
            estimated_size = len(seq) * 3 + 10  # Conservative estimate
            if seq_offset + estimated_size > len(self.output):
                self.output.extend(bytearray(seq_offset + estimated_size - len(self.output)))

            # SF2 format requires DURATION byte (0x80-0x9F) before each note
            # Format: [instrument?] [command?] [DURATION] [note]
            # For now, use default duration of 0x80 (duration=0, no tie)
            # TODO: Add proper duration tracking to SequenceEvent structure
            DEFAULT_DURATION = 0x80

            for event in seq:
                # Skip duration bytes (0x80-0x9F) - shouldn't appear but be safe
                if 0x80 <= event.note <= 0x9F:
                    continue

                # Write instrument change if not "no change" (0x80)
                if event.instrument != 0x80:
                    self.output[seq_offset] = event.instrument
                    seq_offset += 1

                # Write command index directly (Phase 1: already mapped to 0-63)
                # event.command is either 0x80 (no change) or 0-63 (command index)
                if event.command != 0x80:
                    self.output[seq_offset] = event.command
                    seq_offset += 1

                # *** CRITICAL FIX: Write duration byte (REQUIRED by SF2 format) ***
                # Duration bytes are 0x80-0x9F where lower 4 bits = ticks, bit 4 = tie flag
                self.output[seq_offset] = DEFAULT_DURATION
                seq_offset += 1

                # Write note (including gate markers 0x7E, 0x80)
                self.output[seq_offset] = event.note
                seq_offset += 1
                rows_written += 1

                # Stop at end marker
                if event.note == 0x7F:
                    break

            # Ensure sequence ends with 0x7F
            if rows_written > 0 and seq_offset > 0:
                if self.output[seq_offset - 1] != 0x7F:
                    self.output[seq_offset] = 0x7F
                    seq_offset += 1

            # Calculate actual bytes written for this sequence
            bytes_written = seq_offset - sequence_start_offset

            # Update position for next sequence (pack them tightly)
            current_offset = seq_offset
            current_addr += bytes_written

            sequences_written += 1

        logger.info(f"    Written {sequences_written} sequences (packed, total {current_offset - seq_start} bytes)")

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

        logger.info(f"    Wave table address: ${wave_addr:04X}, columns={columns}, rows={rows}")
        logger.info(f"    Extracting from c64_data (len={len(self.data.c64_data)}), load_address=${self.data.load_address:04X}")
        logger.info(f"    First 16 bytes of c64_data: {self.data.c64_data[:16].hex(' ').upper()}")

        extracted_waves = extract_laxity_wave_table(self.data.c64_data, self.data.load_address)

        if extracted_waves:
            wave_data = extracted_waves
            logger.info(f"    Extracted {len(extracted_waves)} wave entries from SID")
            logger.info(f"    First 5 entries: {extracted_waves[:5]}")
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

        logger.info(f"    Base offset: ${base_offset:04X} ({base_offset}), load_addr=${self.load_address:04X}")

        # SF2 wave table format is column-major storage:
        # Bytes 0-255 (Column 0): Waveforms ($11=tri, $21=saw, $41=pulse, $81=noise) or $7F for jump
        # Bytes 256-511 (Column 1): Note offsets
        # Extraction returns (waveform, note) tuples - write waveforms first, then notes

        # Write Column 0: Waveforms (bytes 0-255)
        logger.info(f"    Writing waveforms: rows={rows}, base_offset=${base_offset:04X}, file_size={len(self.output)}, wave_data_len={len(wave_data)}")
        waveforms_written = 0
        for i, (waveform, note) in enumerate(wave_data):
            if i < rows and base_offset + i < len(self.output):
                old_val = self.output[base_offset + i]  # Capture old value
                self.output[base_offset + i] = waveform
                waveforms_written += 1
                if i < 3:  # Log first 3 for debugging
                    logger.info(f"      [{i}] Wrote waveform ${waveform:02X} at offset ${base_offset+i:04X} (was ${old_val:02X})")
            elif i < rows:
                logger.warning(f"    Skipping wave entry {i}: offset ${base_offset+i:04X} out of bounds (file size {len(self.output)})")
        logger.info(f"    Wrote {waveforms_written} waveforms")

        # Write Column 1: Note offsets (bytes 256-511)
        note_offset = base_offset + rows
        logger.debug(f"    Writing notes: note_offset=${note_offset:04X}")
        notes_written = 0
        for i, (waveform, note) in enumerate(wave_data):
            if i < rows and note_offset + i < len(self.output):
                self.output[note_offset + i] = note
                notes_written += 1
                if i < 5:  # Log first 5 for debugging
                    logger.debug(f"      [{i}] Writing note ${note:02X} at offset ${note_offset+i:04X}")
        logger.debug(f"    Wrote {notes_written} note offsets")

        logger.info(f"    Written {len(wave_data)} wave table entries (column-major: waveforms first, then notes)")

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

        # Pad pulse table to minimum size to avoid missing entry errors
        # Neutral entry: 0xFF=keep value, 0x00=no modulation, 0x00=instant, 0x00=no chain
        MIN_PULSE_ENTRIES = 16
        neutral_entry = (0xFF, 0x00, 0x00, 0x00)
        while len(pulse_entries) < MIN_PULSE_ENTRIES:
            pulse_entries.append(neutral_entry)

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

        logger.info(f"    Written {len(pulse_entries)} Pulse table entries (padded from {len(laxity_tables.get('pulse_table', []))})")

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

        # Pad filter table to minimum size to avoid missing entry errors
        # Neutral entry: 0x00=no filter, 0x00=no modulation, 0x00=instant, 0x00=no chain
        MIN_FILTER_ENTRIES = 16
        neutral_entry = (0x00, 0x00, 0x00, 0x00)
        while len(filter_entries) < MIN_FILTER_ENTRIES:
            filter_entries.append(neutral_entry)

        base_offset = self._addr_to_offset(filter_addr)

        for col in range(min(columns, 4)):
            for i, entry in enumerate(filter_entries):
                if i < rows:
                    offset = base_offset + (col * rows) + i
                    if offset < len(self.output) and col < len(entry):
                        self.output[offset] = entry[col]

        logger.info(f"    Written {len(filter_entries)} Filter table entries (padded from {len(laxity_tables.get('filter_table', []))})")

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

    def _update_table_definitions(self) -> None:
        """Update table definition headers with actual data sizes"""
        logger.info("  Updating table definitions...")

        # Table definitions start at offset 0x31 from load address
        table_defs_offset = 0x31
        idx = table_defs_offset

        while idx < len(self.output):
            if idx >= len(self.output):
                break

            table_type = self.output[idx]
            if table_type == 0xFF:  # End marker
                break

            if idx + 3 > len(self.output):
                break

            table_id = self.output[idx + 1]

            # Find null-terminated name
            name_start = idx + 3
            name_end = name_start
            while name_end < len(self.output) and self.output[name_end] != 0:
                name_end += 1

            if name_end >= len(self.output):
                break

            name = bytes(self.output[name_start:name_end]).decode('latin-1', errors='replace')

            # Table header is after null terminator
            pos = name_end + 1
            if pos + 12 > len(self.output):
                break

            # Update Instruments table (type 0x80)
            if table_type == 0x80:
                # Get actual dimensions from driver_info
                if 'Instruments' in self.driver_info.table_addresses:
                    table_info = self.driver_info.table_addresses['Instruments']
                    actual_cols = table_info['columns']
                    actual_rows = table_info['rows']

                    # Update columns at pos+7, pos+8 (little-endian word)
                    struct.pack_into('<H', self.output, pos + 7, actual_cols)
                    # Update rows at pos+9, pos+10 (little-endian word)
                    struct.pack_into('<H', self.output, pos + 9, actual_rows)

                    logger.info(f"    Updated Instruments table definition: {actual_cols}x{actual_rows}")

            # Update Commands table (type 0x81)
            elif table_type == 0x81:
                if 'Commands' in self.driver_info.table_addresses:
                    table_info = self.driver_info.table_addresses['Commands']
                    actual_cols = table_info['columns']
                    actual_rows = table_info['rows']

                    struct.pack_into('<H', self.output, pos + 7, actual_cols)
                    struct.pack_into('<H', self.output, pos + 9, actual_rows)

                    logger.info(f"    Updated Commands table definition: {actual_cols}x{actual_rows}")

            idx = pos + 12

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

    def _inject_laxity_music_data(self) -> None:
        """Inject music data into Laxity driver (native format, no conversion)

        Laxity Driver Memory Layout:
            $0D7E-$0DFF: SF2 Wrapper
            $0E00-$16FF: Relocated Laxity Player (with embedded default tables)
            $1700-$18FF: SF2 Header Blocks
            $1900+:      Music Data (orderlists, sequences)

        Tables are already in the relocated player, so we only inject:
            - Orderlists at $1900 (3 tracks × 256 bytes max)
            - Sequences after orderlists
        """
        logger.info("Injecting Laxity music data (native format)...")

        # Get load address from PRG file (first 2 bytes)
        if len(self.output) < 2:
            logger.error("  Output file too small to contain load address")
            return

        load_addr = struct.unpack('<H', self.output[0:2])[0]
        logger.debug(f"  Load address: ${load_addr:04X}")

        # Helper to convert memory address to file offset
        def addr_to_offset(addr: int) -> int:
            return addr - load_addr + 2  # +2 for PRG load address bytes

        #  ===== POINTER PATCHING FOR RELOCATED LAXITY PLAYER =====
        # The relocated Laxity player contains hardcoded pointers to orderlist/sequence locations
        # Original addresses after -$0200 relocation: $1698-$1898
        # We need to inject at $1900-$1B00 (to avoid SF2 header conflict at $1700)
        # So we must patch all instructions that reference $1698-$1A98 to point to $1900-$1B00

        logger.info("  Patching orderlist pointers in relocated player...")

        # CRITICAL NOTE (v2.9.1): Pointer patches commented out because they're outdated
        # for the current driver version. The Laxity driver binary has been pre-patched
        # during creation with pointers that already point to the correct locations.
        # Testing if music injection alone works without additional patching.

        # Define all pointer patches (from trace_orderlist_access.py output)
        # Format: (file_offset, old_lo, old_hi, new_lo, new_hi)
        # NOTE: "old" addresses are AFTER -$0200 relocation (driver template is already relocated)
        pointer_patches_DISABLED = [
            # Sequence/data references (after -$0200 relocation)
            (0x01C6, 0xD8, 0x16, 0x40, 0x19),  # $16D8 -> $1940
            (0x01CC, 0xD9, 0x16, 0x41, 0x19),  # $16D9 -> $1941
            (0x02AD, 0xB7, 0x16, 0x1F, 0x19),  # $16B7 -> $191F (11 instances)
            (0x02BE, 0xB7, 0x16, 0x1F, 0x19),
            (0x02D4, 0xB7, 0x16, 0x1F, 0x19),
            (0x02ED, 0xB7, 0x16, 0x1F, 0x19),
            (0x0300, 0xB7, 0x16, 0x1F, 0x19),
            (0x030E, 0xB7, 0x16, 0x1F, 0x19),
            (0x0335, 0xB7, 0x16, 0x1F, 0x19),
            (0x0347, 0xB7, 0x16, 0x1F, 0x19),
            (0x0353, 0xB7, 0x16, 0x1F, 0x19),
            (0x0361, 0xB7, 0x16, 0x1F, 0x19),
            (0x0372, 0xB7, 0x16, 0x1F, 0x19),
            (0x0380, 0xB7, 0x16, 0x1F, 0x19),
            (0x057A, 0x3E, 0x17, 0xA6, 0x19),  # $173E -> $19A6 (2 instances)
            (0x058D, 0x3E, 0x17, 0xA6, 0x19),
            (0x0581, 0x70, 0x17, 0xD8, 0x19),  # $1770 -> $19D8 (2 instances)
            (0x05B8, 0x70, 0x17, 0xD8, 0x19),
            (0x0595, 0x57, 0x17, 0xBF, 0x19),  # $1757 -> $19BF
            (0x05C8, 0xDA, 0x16, 0x42, 0x19),  # $16DA -> $1942 (2 instances)
            (0x05D6, 0xDA, 0x16, 0x42, 0x19),
            (0x05CF, 0x0C, 0x17, 0x74, 0x19),  # $170C -> $1974 (2 instances)
            (0x05DC, 0x0C, 0x17, 0x74, 0x19),
            (0x0684, 0x89, 0x17, 0xF1, 0x19),  # $1789 -> $19F1 (3 instances)
            (0x069D, 0x89, 0x17, 0xF1, 0x19),
            (0x06A7, 0x89, 0x17, 0xF1, 0x19),
            (0x068C, 0xBD, 0x17, 0x25, 0x1A),  # $17BD -> $1A25 (4 instances)
            (0x0699, 0xBD, 0x17, 0x25, 0x1A),
            (0x06B5, 0xBD, 0x17, 0x25, 0x1A),
            (0x06BE, 0xBD, 0x17, 0x25, 0x1A),
            (0x06AF, 0xA3, 0x17, 0x0B, 0x1A),  # $17A3 -> $1A0B
            (0x052A, 0xD7, 0x17, 0x3F, 0x1A),  # $17D7 -> $1A3F
            # Table references (after -$0200 relocation)
            (0x00DE, 0x19, 0x18, 0x81, 0x1A),  # $1819 -> $1A81 (3 instances - instrument table)
            (0x00E5, 0x19, 0x18, 0x81, 0x1A),
            (0x0394, 0x19, 0x18, 0x81, 0x1A),
            (0x0103, 0x1C, 0x18, 0x84, 0x1A),  # $181C -> $1A84
            (0x0108, 0x1F, 0x18, 0x87, 0x1A),  # $181F -> $1A87
            (0x038A, 0x1A, 0x18, 0x82, 0x1A),  # $181A -> $1A82
            (0x0141, 0x22, 0x18, 0x8A, 0x1A),  # $1822 -> $1A8A
            (0x0146, 0x49, 0x18, 0xB1, 0x1A),  # $1849 -> $1AB1
        ]

        # Apply patches - Instrument table pointers need redirection to $1A81
        pointer_patches = [
            # Instrument Table Area patches - redirect to $1A81
            (0x02C3, 0x83, 0x1A, 0x81, 0x1A),  # $103F: $1A83 -> $1A81
            (0x02E1, 0x91, 0x1A, 0x81, 0x1A),  # $105D: $1A91 -> $1A81
            (0x04F8, 0x91, 0x1A, 0x81, 0x1A),  # $1274: $1A91 -> $1A81
            (0x069F, 0x9F, 0x1A, 0x81, 0x1A),  # $141B: $1A9F -> $1A81
            (0x0793, 0xA1, 0x1A, 0x81, 0x1A),  # $150F: $1AA1 -> $1A81
            (0x079F, 0x80, 0x1A, 0x81, 0x1A),  # $151B: $1A80 -> $1A81
            (0x07A3, 0x83, 0x1A, 0x81, 0x1A),  # $151F: $1A83 -> $1A81
            (0x07F1, 0x91, 0x1A, 0x81, 0x1A),  # $156D: $1A91 -> $1A81
        ]
        patches_applied = 0
        for file_offset, old_lo, old_hi, new_lo, new_hi in pointer_patches:
            if file_offset + 1 < len(self.output):
                # Verify old values match (safety check)
                current_lo = self.output[file_offset]
                current_hi = self.output[file_offset + 1]

                if current_lo == old_lo and current_hi == old_hi:
                    self.output[file_offset] = new_lo
                    self.output[file_offset + 1] = new_hi
                    patches_applied += 1
                else:
                    logger.warning(f"    Patch mismatch at ${file_offset:04X}: expected {old_lo:02X} {old_hi:02X}, found {current_lo:02X} {current_hi:02X}")

        logger.info(f"  Applied {patches_applied} pointer patches")

        # Now inject orderlists at the safe location $1900-$1B00
        orderlist_start = 0x1900

        # Calculate file offsets
        orderlist_offset = addr_to_offset(orderlist_start)

        # Ensure file is large enough
        min_size = orderlist_offset + (3 * 256) + 1024  # Orderlists + sequences
        if len(self.output) < min_size:
            logger.debug(f"  Extending file to {min_size} bytes")
            self.output.extend(bytearray(min_size - len(self.output)))

        logger.info(f"  Orderlist offset: ${orderlist_offset:04X} (mem: ${orderlist_start:04X})")

        # Inject orderlists (3 tracks, native Laxity format)
        if self.data.orderlists and len(self.data.orderlists) > 0:
            logger.info(f"  Injecting {len(self.data.orderlists)} orderlists...")

            for track_idx, orderlist in enumerate(self.data.orderlists[:3]):  # Max 3 tracks
                track_offset = orderlist_offset + (track_idx * 256)

                # Initialize full 256-byte block with $00
                for i in range(256):
                    self.output[track_offset + i] = 0x00

                # Write orderlist entries (native Laxity format)
                for i, entry in enumerate(orderlist[:256]):  # Max 256 entries
                    if isinstance(entry, dict):
                        # Extract sequence index and transpose
                        seq_idx = entry.get('sequence', 0)
                        transpose = entry.get('transpose', 0xA0)  # Default no transpose

                        # Laxity orderlist format: [sequence_idx, transpose]
                        self.output[track_offset + i] = seq_idx & 0xFF
                    elif isinstance(entry, tuple) and len(entry) >= 2:
                        # Tuple format: (transpose, seq_idx)
                        seq_idx = entry[1]
                        self.output[track_offset + i] = seq_idx & 0xFF
                    elif isinstance(entry, int):
                        # Direct sequence index
                        self.output[track_offset + i] = entry & 0xFF
                    else:
                        self.output[track_offset + i] = 0x00

                # Mark end with 0xFF
                if len(orderlist) < 256:
                    self.output[track_offset + len(orderlist)] = 0xFF

                logger.debug(f"    Track {track_idx+1}: {len(orderlist)} entries at ${track_offset:04X}")

        # Inject sequences after orderlists
        sequence_start = orderlist_start + (3 * 256)  # After 3 orderlist tracks
        sequence_offset = addr_to_offset(sequence_start)

        if self.data.sequences and len(self.data.sequences) > 0:
            logger.info(f"  Injecting {len(self.data.sequences)} sequences...")
            current_offset = sequence_offset

            for seq_idx, sequence in enumerate(self.data.sequences):
                if not sequence:
                    continue

                # Write sequence data (native Laxity format)
                seq_bytes = bytearray()

                for event in sequence:
                    if isinstance(event, dict):
                        # Extract note/command
                        note = event.get('note', 0)
                        duration = event.get('duration', 1)
                        gate = event.get('gate', False)

                        # Laxity sequence format varies, use simple note encoding
                        if gate:
                            seq_bytes.append(0x7E)  # Gate on marker
                        seq_bytes.append(note & 0x7F)

                    elif isinstance(event, int):
                        seq_bytes.append(event & 0xFF)

                # Write sequence end marker
                seq_bytes.append(0x7F)

                # Copy to output
                for i, byte in enumerate(seq_bytes):
                    if current_offset + i < len(self.output):
                        self.output[current_offset + i] = byte

                logger.debug(f"    Sequence {seq_idx}: {len(seq_bytes)} bytes at ${current_offset:04X}")
                current_offset += len(seq_bytes)

        # Inject tables after sequences
        # Memory layout: $1900-$1B00 (orderlists), $1B00+ (sequences), then tables

        # Calculate table injection addresses based on pointer patches
        # All patches add +$0268 offset to relocated addresses
        # Instrument table: original $1A19, relocated $1819, patched -> $1A81
        # So inject at $1A81 (not $1A00!)
        instrument_table_start = 0x1A81  # Matches patched pointer $1819 -> $1A81
        wave_table_start = 0x1942        # Matches patched pointer $16DA -> $1942
        pulse_table_start = 0x1E00       # Estimated (no specific patches found yet)
        filter_table_start = 0x1F00      # Estimated (no specific patches found yet)

        # Inject wave table - FIXED: Laxity uses TWO SEPARATE ARRAYS, not interleaved pairs
        if hasattr(self.data, 'wavetable') and self.data.wavetable:
            # De-interleave SF2 format (waveform, note_offset pairs) into two arrays
            wave_data = self.data.wavetable

            # Extract waveforms and note offsets from interleaved pairs
            waveforms = bytearray()
            note_offsets = bytearray()

            for i in range(0, len(wave_data), 2):
                if i + 1 < len(wave_data):
                    waveform = wave_data[i] if isinstance(wave_data[i], int) else wave_data[i][0]
                    note_offset = wave_data[i+1] if isinstance(wave_data[i+1], int) else wave_data[i+1][0]
                    waveforms.append(waveform)
                    note_offsets.append(note_offset)

            # Laxity format: Two separate arrays with 50-byte offset
            # Based on pointer patches: waveforms at $1942, note offsets at $1974
            waveform_addr = wave_table_start  # $1942
            note_offset_addr = wave_table_start + 0x32  # $1974 ($1942 + 50 bytes)

            # Calculate file offsets
            waveform_file_offset = addr_to_offset(waveform_addr)
            note_offset_file_offset = addr_to_offset(note_offset_addr)

            # Ensure file is large enough
            max_offset = max(waveform_file_offset + len(waveforms),
                           note_offset_file_offset + len(note_offsets))
            if len(self.output) < max_offset:
                self.output.extend(bytearray(max_offset - len(self.output)))

            # Write waveforms array
            for i, byte in enumerate(waveforms):
                self.output[waveform_file_offset + i] = byte

            # Write note offsets array
            for i, byte in enumerate(note_offsets):
                self.output[note_offset_file_offset + i] = byte

            logger.info(f"  Injected wave table (Laxity format):")
            logger.info(f"    Waveforms: {len(waveforms)} bytes at ${waveform_addr:04X}")
            logger.info(f"    Note offsets: {len(note_offsets)} bytes at ${note_offset_addr:04X}")

        # Inject pulse table
        if hasattr(self.data, 'pulsetable') and self.data.pulsetable:  # RE-ENABLED after wave fix
            pulse_offset = addr_to_offset(pulse_table_start)
            pulse_data = self.data.pulsetable

            # Ensure file is large enough
            if len(self.output) < pulse_offset + len(pulse_data):
                self.output.extend(bytearray(pulse_offset + len(pulse_data) - len(self.output)))

            # Write pulse table
            for i, byte in enumerate(pulse_data):
                if isinstance(byte, (int, bytes)):
                    self.output[pulse_offset + i] = byte if isinstance(byte, int) else byte[0]

            logger.info(f"  Injected pulse table: {len(pulse_data)} bytes at ${pulse_table_start:04X}")

        # Inject filter table
        if hasattr(self.data, 'filtertable') and self.data.filtertable:  # RE-ENABLED after wave fix
            filter_offset = addr_to_offset(filter_table_start)
            filter_data = self.data.filtertable

            # Ensure file is large enough
            if len(self.output) < filter_offset + len(filter_data):
                self.output.extend(bytearray(filter_offset + len(filter_data) - len(self.output)))

            # Write filter table
            for i, byte in enumerate(filter_data):
                if isinstance(byte, (int, bytes)):
                    self.output[filter_offset + i] = byte if isinstance(byte, int) else byte[0]

            logger.info(f"  Injected filter table: {len(filter_data)} bytes at ${filter_table_start:04X}")

        # Inject instrument table
        if self.data.instruments and len(self.data.instruments) > 0:  # RE-ENABLED for testing
            instr_offset = addr_to_offset(instrument_table_start)

            # Laxity instruments are 8 bytes each
            instr_data = bytearray()
            for instr in self.data.instruments:
                if isinstance(instr, (list, tuple)):
                    for byte in instr[:8]:  # 8 bytes per instrument
                        instr_data.append(byte if isinstance(byte, int) else ord(byte))
                elif isinstance(instr, bytes):
                    instr_data.extend(instr[:8])

            # Ensure file is large enough
            if len(self.output) < instr_offset + len(instr_data):
                self.output.extend(bytearray(instr_offset + len(instr_data) - len(self.output)))

            # Write instrument table
            for i, byte in enumerate(instr_data):
                self.output[instr_offset + i] = byte

            logger.info(f"  Injected instrument table: {len(instr_data)} bytes ({len(self.data.instruments)} instruments) at ${instrument_table_start:04X}")

        logger.info(f"  Laxity music data injection complete (with tables)")
        logger.info(f"  Total file size: {len(self.output)} bytes")

    def _log_sf2_structure(self, label: str, data: bytes) -> None:
        """Log detailed SF2 file structure for debugging.

        Args:
            label: Description label for this structure dump
            data: SF2 file data to analyze
        """
        logger.debug(f"=" * 70)
        logger.debug(f"{label}")
        logger.debug(f"=" * 70)
        logger.debug(f"Total size: {len(data)} bytes")

        if len(data) < 4:
            logger.debug("  File too small to analyze")
            return

        # Parse load address and magic number
        load_addr = struct.unpack('<H', data[0:2])[0]
        logger.debug(f"Load address: ${load_addr:04X}")

        offset = 2
        if len(data) < offset + 2:
            logger.debug("  No magic number found")
            return

        magic = struct.unpack('<H', data[offset:offset+2])[0]
        logger.debug(f"Magic number: 0x{magic:04X} {'OK VALID' if magic == 0x1337 else 'ERR INVALID'}")
        offset += 2

        # Parse all blocks
        block_count = 0
        logger.debug("\nBlock Structure:")
        while offset < len(data) - 1:
            block_id = data[offset]

            # Check for end marker
            if block_id == 0xFF:
                logger.debug(f"\n  End marker (0xFF) at offset ${offset:04X}")
                break

            block_size = data[offset + 1]
            block_end = offset + 2 + block_size

            logger.debug(f"\n  Block {block_id}:")
            logger.debug(f"    Offset: ${offset:04X} - ${block_end:04X}")
            logger.debug(f"    Declared size: {block_size} bytes")
            logger.debug(f"    Actual size: {block_size + 2} bytes (with header)")

            # Special handling for Block 3 (Driver Tables)
            if block_id == 3 and block_size > 0:
                content = data[offset+2:offset+2+block_size]
                self._log_block3_structure(content)

            # Special handling for Block 5 (Music Data)
            elif block_id == 5 and block_size >= 18:
                content = data[offset+2:offset+2+block_size]
                self._log_block5_structure(content)

            offset = block_end
            block_count += 1

            if block_count > 20:  # Safety limit
                logger.debug("    ... (too many blocks, stopping)")
                break

        logger.debug(f"\nTotal blocks parsed: {block_count}")
        logger.debug(f"=" * 70)

    def _log_block3_structure(self, content: bytes) -> None:
        """Log detailed Block 3 (Driver Tables) structure.

        Args:
            content: Block 3 content bytes
        """
        logger.debug("    Block 3 (Driver Tables) details:")

        pos = 0
        table_count = 0
        while pos < len(content) and content[pos] != 0xFF:
            if pos + 3 > len(content):
                logger.debug(f"      ERR Truncated at table {table_count}")
                break

            table_type = content[pos]
            table_id = content[pos+1]
            name_len = content[pos+2]

            if pos + 3 + name_len > len(content):
                logger.debug(f"      ERR Truncated name at table {table_count}")
                break

            # Decode table name
            name_bytes = content[pos+3:pos+3+name_len]
            try:
                name = name_bytes[:-1].decode('ascii')  # Skip null terminator
            except:
                name = "<binary>"

            # Table type names
            type_names = {0x00: "Generic", 0x80: "Instruments", 0x81: "Commands"}
            type_name = type_names.get(table_type, f"Unknown(0x{table_type:02X})")

            logger.debug(f"      Table {table_count}: {type_name} (0x{table_type:02X})")
            logger.debug(f"        ID: {table_id}")
            logger.debug(f"        Name: \"{name}\"")

            # Calculate descriptor size including VisibleRows byte
            # Format: Type(1) + ID(1) + NameLen(1) + Name(var) + Layout(1) + Flags(1) +
            #         Rules(3) + Address(2) + Columns(2) + Rows(2) + VisibleRows(1)
            descriptor_size = 3 + name_len + 1 + 1 + 3 + 2 + 2 + 2 + 1

            if pos + descriptor_size > len(content):
                logger.debug(f"      ERR Truncated descriptor at table {table_count}")
                break

            pos += descriptor_size
            table_count += 1

        # Check for terminator
        if pos < len(content) and content[pos] == 0xFF:
            logger.debug(f"      OK Found 0xFF terminator at position {pos}")
            logger.debug(f"      OK Total tables: {table_count}")
        else:
            logger.debug(f"      ERR No 0xFF terminator found (stopped at position {pos})")

    def _log_block5_structure(self, content: bytes) -> None:
        """Log detailed Block 5 (Music Data) structure.

        Args:
            content: Block 5 content bytes
        """
        if len(content) < 18:
            logger.debug("    Block 5 (Music Data): Too small")
            return

        logger.debug("    Block 5 (Music Data) details:")

        # Parse music data fields
        offset = 0
        track_count = content[offset]
        offset += 1
        logger.debug(f"      Track count: {track_count}")

        track_ol_ptr_lo = struct.unpack('<H', content[offset:offset+2])[0]
        offset += 2
        track_ol_ptr_hi = struct.unpack('<H', content[offset:offset+2])[0]
        offset += 2
        logger.debug(f"      Track orderlist pointers: ${track_ol_ptr_lo:04X} / ${track_ol_ptr_hi:04X}")

        seq_count = content[offset]
        offset += 1
        logger.debug(f"      Sequence count: {seq_count}")

        seq_ptr_lo = struct.unpack('<H', content[offset:offset+2])[0]
        offset += 2
        seq_ptr_hi = struct.unpack('<H', content[offset:offset+2])[0]
        offset += 2
        logger.debug(f"      Sequence pointers: ${seq_ptr_lo:04X} / ${seq_ptr_hi:04X}")

        ol_size = struct.unpack('<H', content[offset:offset+2])[0]
        offset += 2
        logger.debug(f"      Orderlist size: {ol_size}")

        ol_track1 = struct.unpack('<H', content[offset:offset+2])[0]
        offset += 2
        logger.debug(f"      Orderlist track 1: ${ol_track1:04X}")

        seq_size = struct.unpack('<H', content[offset:offset+2])[0]
        offset += 2
        logger.debug(f"      Sequence size: {seq_size}")

        seq00_addr = struct.unpack('<H', content[offset:offset+2])[0]
        offset += 2
        logger.debug(f"      Sequence 00 address: ${seq00_addr:04X}")

        logger.debug(f"      OK All 18 bytes read correctly")

    def _validate_sf2_file(self, filepath: str) -> None:
        """Validate written SF2 file structure.

        Args:
            filepath: Path to SF2 file to validate
        """
        logger.debug(f"\nValidating SF2 file: {filepath}")

        try:
            with open(filepath, 'rb') as f:
                data = f.read()
        except IOError:
            logger.error("  ERR Could not read file for validation")
            return

        # Check minimum size
        if len(data) < 100:
            logger.error(f"  ERR File too small: {len(data)} bytes")
            return

        # Check magic number
        if len(data) >= 4:
            magic = struct.unpack('<H', data[2:4])[0]
            if magic == 0x1337:
                logger.debug("  OK Valid magic number (0x1337)")
            else:
                logger.error(f"  ERR Invalid magic number: 0x{magic:04X} (expected 0x1337)")
                return

        # Parse and validate blocks
        offset = 4  # After load address and magic
        block_count = 0
        has_block1 = False
        has_block2 = False
        has_block3 = False
        has_block5 = False
        has_instruments = False
        has_commands = False

        while offset < len(data) - 1:
            block_id = data[offset]

            if block_id == 0xFF:
                logger.debug(f"  OK Found end marker at offset ${offset:04X}")
                break

            if offset + 1 >= len(data):
                logger.error(f"  ERR File truncated at block {block_id}")
                return

            block_size = data[offset + 1]
            block_end = offset + 2 + block_size

            if block_end > len(data):
                logger.error(f"  ERR Block {block_id} extends beyond file (declares {block_size} bytes)")
                return

            # Track which blocks we found
            if block_id == 1:
                has_block1 = True
            elif block_id == 2:
                has_block2 = True
            elif block_id == 3:
                has_block3 = True
                # Check for required tables
                content = data[offset+2:block_end]
                pos = 0
                while pos < len(content) and content[pos] != 0xFF:
                    if pos + 3 <= len(content):
                        table_type = content[pos]
                        name_len = content[pos+2] if pos + 2 < len(content) else 0
                        if table_type == 0x80:
                            has_instruments = True
                        elif table_type == 0x81:
                            has_commands = True
                        # Skip to next descriptor
                        desc_size = 3 + name_len + 1 + 1 + 3 + 2 + 2 + 2 + 1
                        pos += desc_size
                    else:
                        break
            elif block_id == 5:
                has_block5 = True

            offset = block_end
            block_count += 1

            if block_count > 20:
                logger.error("  ERR Too many blocks (possible corruption)")
                return

        # Report validation results
        logger.debug(f"  OK Parsed {block_count} blocks successfully")

        if has_block1:
            logger.debug("  OK Block 1 (Descriptor) present")
        else:
            logger.warning("  WARN Block 1 (Descriptor) missing")

        if has_block2:
            logger.debug("  OK Block 2 (Driver Common) present")
        else:
            logger.warning("  WARN Block 2 (Driver Common) missing")

        if has_block3:
            logger.debug("  OK Block 3 (Driver Tables) present")
            if has_instruments:
                logger.debug("    OK Instruments table (0x80) found")
            else:
                logger.error("    ERR Instruments table (0x80) MISSING - file will be rejected!")

            if has_commands:
                logger.debug("    OK Commands table (0x81) found")
            else:
                logger.error("    ERR Commands table (0x81) MISSING - file will be rejected!")
        else:
            logger.error("  ERR Block 3 (Driver Tables) missing")

        if has_block5:
            logger.debug("  OK Block 5 (Music Data) present")
        else:
            logger.warning("  WARN Block 5 (Music Data) missing")

        # Final verdict
        if has_instruments and has_commands and has_block1 and has_block2 and has_block3:
            logger.info("  OK SF2 FILE VALIDATION PASSED - file should load in SF2 Editor")
        else:
            logger.error("  ERR SF2 FILE VALIDATION FAILED - file may be rejected by SF2 Editor")

