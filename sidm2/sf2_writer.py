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
from .laxity_converter import LaxityConverter
from .sequence_extraction import (
    get_command_names,
    extract_command_parameters,
    build_command_index_map,
    build_sf2_command_table,
    extract_arpeggio_indices,
    find_arpeggio_table_in_memory,
    build_sf2_arp_table
)
from .instrument_transposition import transpose_instruments
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
                # Raw approach: embed song's own NP21 binary verbatim.
                # This supersedes the 40-patch Stinsen-template approach: it works
                # for any NP21 sub-version without hardcoded data-layout assumptions.
                if getattr(self.data, 'c64_data', None) is not None:
                    self._inject_laxity_raw_np21()
                else:
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

        # PACKED MODE: Pre-allocate enough space for sequences and orderlists
        # Calculate required size based on actual data
        sequence_space = sum(len(seq) * 4 for seq in (self.data.sequences or [])) + 2048  # 4 bytes per event + overhead
        orderlist_space = sum(len(ol) * 2 for ol in (self.data.orderlists or [])) + 1024  # 2 bytes per entry + overhead
        required_size = self._addr_to_offset(self.driver_info.sequence_start) + sequence_space + orderlist_space

        if len(self.output) < required_size:
            logger.debug(f"  Pre-allocating buffer: {required_size} bytes (sequences: {sequence_space}, orderlists: {orderlist_space})")
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

            # Ensure buffer is large enough for pointers
            if ptr_lo_offset + track >= len(self.output):
                self.output.extend(bytearray(ptr_lo_offset + track - len(self.output) + 1))
            if ptr_hi_offset + track >= len(self.output):
                self.output.extend(bytearray(ptr_hi_offset + track - len(self.output) + 1))

            self.output[ptr_lo_offset + track] = current_addr & 0xFF
            self.output[ptr_hi_offset + track] = (current_addr >> 8) & 0xFF

            ol_offset = self._addr_to_offset(current_addr)
            last_trans = -1

            # Pre-expand buffer for this orderlist
            estimated_ol_size = len(orderlist) * 2 + 10  # 2 bytes per entry + end marker
            if ol_offset + estimated_ol_size >= len(self.output):
                self.output.extend(bytearray(ol_offset + estimated_ol_size - len(self.output) + 1))

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
                    self.output[ol_offset] = sf2_trans
                    ol_offset += 1
                    last_trans = sf2_trans

                self.output[ol_offset] = seq_idx & 0x7F
                ol_offset += 1

            # Write end marker
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

        is_np20 = columns == 8

        # Get valid wave entry points for validation
        from .table_extraction import get_valid_wave_entry_points
        valid_wave_points = get_valid_wave_entry_points(wave_entries) if wave_entries else {0}
        wave_table_size = len(wave_entries) if wave_entries else 0

        # Use new instrument transposition for Driver 11 (6 columns)
        if not is_np20 and columns == 6:
            logger.info("    Using instrument transposition module (Track B3)")

            # Prepare Laxity 8-byte instruments for transposition
            laxity_instr_bytes = []
            for i, instr_bytes in enumerate(self.data.instruments[:32]):  # Up to 32 instruments
                if len(instr_bytes) >= 8:
                    # Process wave and pulse pointers
                    instr_copy = bytearray(instr_bytes)
                    wave_ptr = instr_copy[7]
                    pulse_ptr = instr_copy[6]

                    # Convert Laxity pulse_ptr from Y*4 indexing to direct index
                    if pulse_ptr != 0 and pulse_ptr % 4 == 0:
                        pulse_ptr = pulse_ptr // 4
                    instr_copy[3] = pulse_ptr  # LAXITY_PULSE = 3

                    # Validate and clamp wave pointer
                    if wave_table_size > 0 and wave_ptr >= wave_table_size:
                        valid_in_bounds = [p for p in valid_wave_points if p < wave_table_size]
                        if valid_in_bounds:
                            wave_ptr = min(valid_in_bounds, key=lambda p: abs(p - wave_ptr))
                        else:
                            wave_ptr = 0
                        logger.debug(f"    Clamped wave_ptr for instrument {i} to {wave_ptr}")
                    instr_copy[2] = wave_ptr  # LAXITY_WAVEFORM = 2

                    laxity_instr_bytes.append(bytes(instr_copy))

            # Transpose using B3 module (Laxity 8-byte → SF2 column-major 256-byte)
            sf2_table = transpose_instruments(laxity_instr_bytes, pad_to=rows)

            # Write transposed table directly
            base_offset = self._addr_to_offset(instr_addr)
            table_size = min(len(sf2_table), rows * columns)

            for i in range(table_size):
                offset = base_offset + i
                if offset < len(self.output):
                    self.output[offset] = sf2_table[i]

            instruments_written = len(laxity_instr_bytes)
            logger.info(f"    Written {instruments_written} instruments using transposition (B3)")

            # Log instrument details
            for i in range(min(instruments_written, 16)):
                if i < len(laxity_instruments):
                    lax_instr = laxity_instruments[i]
                    name = lax_instr.get('name', f'{i:02d} Instr')
                    logger.debug(f"      {i}: {name} (AD={lax_instr['ad']:02X} SR={lax_instr['sr']:02X})")

        else:
            # Legacy path for NP20 or non-standard column counts
            logger.info("    Using legacy instrument format (NP20 or non-standard)")
            sf2_instruments = []

            for lax_instr in laxity_instruments:
                wave_ptr = lax_instr.get('wave_ptr', 0)
                pulse_ptr = lax_instr.get('pulse_ptr', 0)
                filter_ptr = lax_instr.get('filter_ptr', 0)

                # Convert Laxity pulse_ptr from Y*4 indexing to direct index
                if pulse_ptr != 0 and pulse_ptr % 4 == 0:
                    pulse_ptr = pulse_ptr // 4

                if wave_ptr == 0:
                    wave_ptr = waveform_to_wave_index(lax_instr['wave_for_sf2'])

                # Validate wave pointer
                if wave_table_size > 0 and wave_ptr >= wave_table_size:
                    valid_in_bounds = [p for p in valid_wave_points if p < wave_table_size]
                    if valid_in_bounds:
                        wave_ptr = min(valid_in_bounds, key=lambda p: abs(p - wave_ptr))
                    else:
                        wave_ptr = 0
                    logger.debug(f"    Clamped wave_ptr for instrument {lax_instr['index']} to {wave_ptr}")

                if is_np20:
                    # NP20 instrument format (8 columns)
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
                    # Non-standard format fallback
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
                    wave_idx_pos = 4 if is_np20 else 5
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

            logger.info(f"    Written {instruments_written} instruments (legacy path)")

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
        laxity_filter_entries = laxity_tables.get('filter_table', [])

        if not laxity_filter_entries:
            laxity_filter_entries = [(0x40, 0x01, 0x20, 0x00)]

        # Convert Laxity filter format to SF2 filter format
        logger.info(f"    Converting {len(laxity_filter_entries)} Laxity filter entries to SF2 format...")
        filter_entries = LaxityConverter.convert_filter_table(laxity_filter_entries)
        logger.info(f"    Converted to {len(filter_entries)} SF2 filter entries")

        # Pad filter table to minimum size to avoid missing entry errors
        # Neutral entry: 0x00=no filter, 0x00=no modulation, 0x00=instant, 0x00=no chain
        MIN_FILTER_ENTRIES = 16
        neutral_entry = (0x00, 0x00, 0x00, 0x7F)  # SF2 format with end marker
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
        elif hasattr(self.data, 'sequences') and self.data.sequences:
            # Extract commands from parsed sequences (SequenceEvent format)
            sf2_commands = [(0, 0, 0)] * 64
            command_set = set()

            # Scan all sequences to find unique command combinations
            for seq in self.data.sequences:
                for event in seq:
                    if event.command > 0:  # Non-zero command
                        # For SF2 format, command is (type, param1, param2)
                        # SequenceEvent.command contains the command value
                        command_set.add((event.command, event.instrument, 0))

            # Assign command indices
            for idx, (cmd_type, param1, param2) in enumerate(sorted(command_set)):
                if idx < 64:
                    sf2_commands[idx] = (cmd_type, param1, param2)

            logger.info(f"    Extracted {len(command_set)} unique commands from parsed sequences")
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

    def _inject_laxity_raw_np21(self) -> None:
        """Build a valid SF2 file by embedding the song's own NP21 binary verbatim.

        Unlike the Stinsen-template approach (40 hardcoded pointer patches),
        this places the song's complete NP21 player + music data at its original
        C64 addresses ($1000+). A proper SF2 header sits at $0D7E-$0FFF.

        No pointer patches are required: the player reads its own music data from
        the same addresses it was assembled for. Works for any NP21 sub-version
        (Stinsen, Unboxed, etc.) without song-specific analysis.

        SF2 memory layout:
            $0D7E:       0x1337 magic (required for SF2 recognition)
            $0D80-$0EFF: SF2 header blocks (Descriptor, DriverCommon, DriverTables,
                         InstrumentDescriptor, MusicData, 0xFF end)
            $0F00:       INIT handler: JSR init_addr, RTS
            $0F04:       PLAY handler: JSR play_addr, RTS
            $0F08:       STOP handler: LDA #0, STA $D418, RTS
            $1000+:      Song's original NP21 binary (player + all music data)
        """
        logger.info("Building raw-NP21 SF2 (verbatim player embedding, valid SF2 headers)...")

        c64_data = getattr(self.data, 'c64_data', None)
        if not c64_data:
            logger.error("  No c64_data available; cannot build raw NP21 SF2")
            return

        sid_la    = getattr(self.data, 'load_address', 0x1000)
        header    = getattr(self.data, 'header', None)
        init_addr = getattr(header, 'init_address', sid_la)     if header else sid_la
        play_addr = getattr(header, 'play_address', sid_la + 3) if header else sid_la + 3

        LOAD_BASE    = 0x0D7E   # SF2 loads here; 0x1337 magic goes here
        HANDLER_BASE = 0x0F00   # Handler code — safely past all header blocks
        INIT_HANDLER = HANDLER_BASE + 0    # $0F00: JSR init_addr, RTS
        PLAY_HANDLER = HANDLER_BASE + 4    # $0F04: JSR play_addr, RTS
        STOP_HANDLER = HANDLER_BASE + 8    # $0F08: LDA #0, STA $D418, RTS

        # Generate SF2 header blocks with correct handler entry points.
        # generate_complete_headers() returns [37 13] + Block1..5 + [FF].
        # These bytes go at $0D7E; blocks start at $0D80 (= load_addr + 2) as
        # required by driver_info.cpp:313: block_address = m_TopAddress + 2.
        from sidm2.sf2_header_generator import SF2HeaderGenerator
        gen = SF2HeaderGenerator(driver_size=len(c64_data) + (sid_la - LOAD_BASE))
        gen.DRIVER_INIT = INIT_HANDLER
        gen.DRIVER_PLAY = PLAY_HANDLER
        gen.DRIVER_STOP = STOP_HANDLER
        header_bytes = gen.generate_complete_headers()

        # Safety check: headers must not overlap handler code
        headers_end_addr = LOAD_BASE + len(header_bytes)
        if headers_end_addr > HANDLER_BASE:
            logger.error(
                f"  Headers too large! End ${headers_end_addr:04X} > handler base ${HANDLER_BASE:04X}"
            )
            return

        # --- Extract NP21 patterns and build SF2 edit data area ---
        music_data_params, sf2_edit_data = self._build_np21_sf2_edit_area(c64_data, sid_la)

        # Update driver_size to include the full file extent (NP21 + edit area)
        gen.driver_size += len(sf2_edit_data)

        # Now regenerate headers with correct Block 5 addresses
        header_bytes = gen.generate_complete_headers(music_data_params)

        # Re-check header size hasn't grown past handler base
        headers_end_addr = LOAD_BASE + len(header_bytes)
        if headers_end_addr > HANDLER_BASE:
            logger.error(
                f"  Headers too large after music data update! End ${headers_end_addr:04X} > ${HANDLER_BASE:04X}"
            )
            return

        # Build the full PRG: [load_addr:2] + memory from $0D7E to end of NP21 + SF2 edit data
        gap = sid_la - LOAD_BASE
        file_size = 2 + gap + len(c64_data) + len(sf2_edit_data)
        file_data = bytearray(file_size)

        # PRG load address (2-byte little-endian header)
        file_data[0] = LOAD_BASE & 0xFF
        file_data[1] = LOAD_BASE >> 8

        # SF2 magic + header blocks at $0D7E (file offset 2)
        file_data[2:2 + len(header_bytes)] = header_bytes

        # Handler code at $0F00 (file offset 2 + ($0F00 - $0D7E))
        hnd_off = 2 + (HANDLER_BASE - LOAD_BASE)
        file_data[hnd_off:hnd_off + 4]  = bytes([0x20, init_addr & 0xFF, init_addr >> 8, 0x60])
        file_data[hnd_off + 4:hnd_off + 8]  = bytes([0x20, play_addr & 0xFF, play_addr >> 8, 0x60])
        file_data[hnd_off + 8:hnd_off + 14] = bytes([0xA9, 0x00, 0x8D, 0x18, 0xD4, 0x60])

        # NP21 binary verbatim at its original load address (file offset 2 + gap)
        np21_off = 2 + gap
        file_data[np21_off:np21_off + len(c64_data)] = c64_data

        # Fix zig64 auto-detection: it always calls init_addr+3 as PLAY.
        if play_addr != init_addr + 3:
            stub_off = np21_off + (init_addr + 3 - sid_la)
            if 0 <= stub_off and stub_off + 3 <= len(file_data):
                file_data[stub_off]     = 0x4C  # JMP
                file_data[stub_off + 1] = play_addr & 0xFF
                file_data[stub_off + 2] = (play_addr >> 8) & 0xFF
                logger.info(f"  Patched ${init_addr+3:04X} -> JMP ${play_addr:04X} (zig64 play redirect)")

        # SF2 edit data appended after NP21 binary
        if sf2_edit_data:
            edit_off = np21_off + len(c64_data)
            file_data[edit_off:edit_off + len(sf2_edit_data)] = sf2_edit_data

        self.output = file_data

        sf2_data_base = sid_la + len(c64_data)
        logger.info(f"  SF2 size: {len(self.output)} bytes")
        logger.info(f"  Magic + headers: ${LOAD_BASE:04X}-${headers_end_addr - 1:04X} ({len(header_bytes)} bytes)")
        logger.info(f"  Handlers: ${HANDLER_BASE:04X} (INIT=${INIT_HANDLER:04X}, PLAY=${PLAY_HANDLER:04X}, STOP=${STOP_HANDLER:04X})")
        logger.info(f"  NP21 binary: ${sid_la:04X}-${sid_la + len(c64_data) - 1:04X} ({len(c64_data)} bytes)")
        logger.info(f"  SF2 edit data: ${sf2_data_base:04X}-${sf2_data_base + len(sf2_edit_data) - 1:04X} ({len(sf2_edit_data)} bytes)")
        logger.info(f"  INIT: ${INIT_HANDLER:04X} -> JSR ${init_addr:04X}")
        logger.info(f"  PLAY: ${PLAY_HANDLER:04X} -> JSR ${play_addr:04X}")

    def _build_np21_sf2_edit_area(self, c64_data: bytes, sid_la: int):
        """Extract NP21 patterns/orderlists and build an SF2-format edit data area.

        Returns (music_data_params, sf2_edit_bytes).
        music_data_params is a dict for SF2HeaderGenerator.create_music_data_block().
        sf2_edit_bytes is the raw bytes to append after the NP21 binary in the file.

        EDITABLE-REPLAY GAP (do not "fix" by switching to NP21 format here):
          The bytes written here are read by the SF2 editor's DataSourceSequence::Unpack
          (datasource_sequence.cpp:197-267), which assumes the SF2 packed format:
            0x7F=end, 0xC0-0xFF=command, 0xA0-0xBF=instrument,
            0x80-0x9F=duration, <0x80=note (asserts), 0x00=gate-off, 0x7E=tie.
          NP21 format conflicts on every key byte (0x80=gate-off, 0xFF=loop,
          0-based notes), so storing NP21 bytes here would corrupt the editor view.
          The flip side: the laxity SF2 driver runs the original NP21 player code,
          which reads NP21-format sequences from inside the embedded NP21 binary at
          ch_seq_ptr ($0A1C/$0A1F) — NOT from this edit area. Therefore edits the
          user makes in the SF2 editor do NOT yet affect playback. Closing that gap
          requires either (a) a runtime SF2->NP21 translator added to the laxity
          driver, or (b) a full Driver-11-compatible re-encoding of the song. Both
          are out of scope for this function.

        The edit area layout (all offsets from sf2_data_base = sid_la + len(c64_data)):
          [0]          OL ptr lo table  (3 bytes, written by editor at runtime)
          [3]          OL ptr hi table  (3 bytes, written by editor at runtime)
          [6]          Seq ptr lo table (SEQ_PTR_SIZE bytes, written by editor at runtime)
          [6+N]        Seq ptr hi table (SEQ_PTR_SIZE bytes, written by editor at runtime)
          [6+2N]       Orderlists       (3 × OL_SIZE bytes)
          [6+2N+3*O]   Sequences        (num_patterns × SEQ_SIZE bytes, NP21-format)
        where N=SEQ_PTR_SIZE=128, O=OL_SIZE=256, SEQ_SIZE=256.
        """
        CH_SEQ_LO_OFF  = 0x0A1C   # Offset from sid_la to voice seq ptr lo table (3 bytes)
        CH_SEQ_HI_OFF  = 0x0A1F   # Offset from sid_la to voice seq ptr hi table (3 bytes)
        OL_SIZE  = 256
        SEQ_SIZE = 256
        SEQ_PTR_SIZE = 128         # Max sequences tracked in ptr tables

        def _extract_raw_seq(addr):
            """Read NP21 sequence bytes up to (not including) the loop/end terminator.

            NP21 uses 0xFF as an internal loop marker (not 0x7F).  Format:
              ...<body bytes>... 0xFF <loop_target_Y>
            where loop_target_Y is the Y index to jump to (usually 0x00 = loop from start).
            0x7F is a true end-of-data marker, but is typically unreachable in playback
            because each voice loops via 0xFF before ever reaching 0x7F.

            Returns (body_bytes, loop_target):
              body_bytes  — raw NP21 bytes before the terminator (excludes 0xFF/0x7F)
              loop_target — int Y target from 0xFF marker, or None if ended with 0x7F
            """
            off = addr - sid_la
            if off < 0 or off >= len(c64_data):
                return None, None
            raw = bytearray()
            j = 0
            while off + j < len(c64_data) and j < SEQ_SIZE:
                b = c64_data[off + j]
                if b == 0x7F:
                    # True end — sequence plays once (no loop)
                    return bytes(raw), None
                if b == 0xFF:
                    # Loop marker: next byte is the Y index to loop back to
                    loop_target = 0
                    if off + j + 1 < len(c64_data):
                        loop_target = c64_data[off + j + 1]
                    return bytes(raw), loop_target
                raw.append(b)
                j += 1
            return bytes(raw), None

        # --- 1. Extract the 3 main voice sequences from ch_seq_ptr ---
        # ch_seq_ptr ($0A1C/$0A1F) gives the actual voice sequence addresses.
        # These are the primary music data the editor needs to display.
        # The pattern ptr table at $0A22/$0A49 points to instrument sub-patterns, not
        # voice sequences — do NOT use that table for sequence extraction.
        addr_to_sf2_idx = {}
        raw_patterns = []    # list of (body_bytes, loop_target)

        for v in range(3):
            if CH_SEQ_LO_OFF + v < len(c64_data) and CH_SEQ_HI_OFF + v < len(c64_data):
                lo = c64_data[CH_SEQ_LO_OFF + v]
                hi = c64_data[CH_SEQ_HI_OFF + v]
                seq_addr = (hi << 8) | lo
                if seq_addr not in addr_to_sf2_idx:
                    body, loop_target = _extract_raw_seq(seq_addr)
                    if body is not None:
                        sf2_idx = len(raw_patterns)
                        addr_to_sf2_idx[seq_addr] = sf2_idx
                        raw_patterns.append((body, loop_target))
                        if loop_target is not None and loop_target > 0:
                            logger.warning(
                                f"  Voice seq at ${seq_addr:04X}: loop target={loop_target} "
                                f"(non-zero intro loop — only loop body extracted for SF2)"
                            )

        voice_init_idx = [0, 0, 0]
        for v in range(3):
            if CH_SEQ_LO_OFF + v < len(c64_data) and CH_SEQ_HI_OFF + v < len(c64_data):
                lo = c64_data[CH_SEQ_LO_OFF + v]
                hi = c64_data[CH_SEQ_HI_OFF + v]
                init_addr = (hi << 8) | lo
                voice_init_idx[v] = addr_to_sf2_idx.get(init_addr, 0)

        num_patterns = len(raw_patterns)
        if num_patterns == 0:
            logger.warning("  No NP21 patterns found; Block 5 will use placeholder addresses")
            return None, b''

        for i, (body, lt) in enumerate(raw_patterns):
            loop_str = f"loops from start" if lt == 0 else f"loops from Y={lt}" if lt is not None else "no loop"
            logger.info(f"  Pattern {i}: {len(body)} bytes, {loop_str}")

        # --- 2. Convert patterns to SF2 sequence format ---
        # SF2 packed sequence format (from datasource_sequence.cpp):
        #   0x00        = note off (gate off)
        #   0x01-0x6F   = notes  (0x01 = C-0, 0x02 = C#0, ..., chromatic)
        #   0x7E        = note on / tie
        #   0x7F        = end of sequence
        #   0x80-0x8F   = duration (0-15 ticks)
        #   0x90-0x9F   = duration + tie flag
        #   0xA0-0xBF   = set instrument
        #   0xC0-0xFF   = set command
        #
        # NP21 note format: 0x00-0x5D = notes, where 0x00 = C-0 (lowest).
        # SF2 note format:  0x01-0x6F = notes, where 0x01 = C-0.
        # Conversion: sf2_note = np21_note + 1  (NP21 notes are 0-based, SF2 are 1-based)
        # All other byte ranges (gate-on 0x7E, durations 0x80-0x9F, instrument, command)
        # are identical between NP21 and SF2.
        # Body bytes no longer contain 0x7F or 0xFF (stripped by _extract_raw_seq).
        sf2_sequences = []
        for body, loop_target in raw_patterns:
            seq = bytearray()
            for b in body:
                if b == 0x7E:           # gate on — same in SF2 (0x7E)
                    seq.append(0x7E)
                elif 0xA0 <= b <= 0xBF: # instrument — same encoding
                    seq.append(b)
                elif 0x80 <= b <= 0x9F: # duration — same encoding
                    seq.append(b)
                elif 0xC0 <= b <= 0xFF: # command index — pass through
                    seq.append(b)
                else:                   # note: NP21 is 0-based, SF2 is 1-based (+1 shift)
                    # NP21 note 0x00 = C-0, SF2 note 0x01 = C-0 (SF2 note 0x00 = gate off)
                    seq.append(min(0x6F, b + 1))
            seq.append(0x7F)  # SF2 end-of-sequence marker
            # Pad to fixed size
            while len(seq) < SEQ_SIZE:
                seq.append(0x7F)
            sf2_sequences.append(bytes(seq[:SEQ_SIZE]))

        orderlists = []
        for v in range(3):
            ol = bytearray([voice_init_idx[v] & 0x7F, 0xFE])  # single pattern + loop
            while len(ol) < OL_SIZE:
                ol.append(0xFF)
            orderlists.append(bytes(ol[:OL_SIZE]))

        # --- 4. Compute addresses in C64 memory ---
        sf2_data_base = sid_la + len(c64_data)

        ol_ptr_lo_addr  = sf2_data_base + 0
        ol_ptr_hi_addr  = sf2_data_base + 3
        seq_ptr_lo_addr = sf2_data_base + 6
        seq_ptr_hi_addr = sf2_data_base + 6 + SEQ_PTR_SIZE
        ol_track1_addr  = sf2_data_base + 6 + 2 * SEQ_PTR_SIZE
        seq00_addr      = ol_track1_addr + 3 * OL_SIZE

        music_data_params = {
            'track_count':     3,
            'ol_ptr_lo_addr':  ol_ptr_lo_addr,
            'ol_ptr_hi_addr':  ol_ptr_hi_addr,
            'seq_count':       min(num_patterns, SEQ_PTR_SIZE),
            'seq_ptr_lo_addr': seq_ptr_lo_addr,
            'seq_ptr_hi_addr': seq_ptr_hi_addr,
            'ol_size':         OL_SIZE,
            'ol_track1_addr':  ol_track1_addr,
            'seq_size':        SEQ_SIZE,
            'seq00_addr':      seq00_addr,
        }

        # --- 5. Build raw edit data bytes ---
        edit = bytearray()
        edit.extend(b'\x00' * 3)                  # OL ptr lo table (editor writes)
        edit.extend(b'\x00' * 3)                  # OL ptr hi table (editor writes)
        edit.extend(b'\x00' * SEQ_PTR_SIZE)       # Seq ptr lo table (editor writes)
        edit.extend(b'\x00' * SEQ_PTR_SIZE)       # Seq ptr hi table (editor writes)
        for ol in orderlists:
            edit.extend(ol)
        for seq in sf2_sequences:
            edit.extend(seq)

        logger.info(
            f"  SF2 edit area: base=${sf2_data_base:04X}, "
            f"OL=${ol_track1_addr:04X}, "
            f"Seq=${seq00_addr:04X} ({num_patterns} patterns × {SEQ_SIZE}B)"
        )

        return music_data_params, bytes(edit)

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
            logger.error(
                "  Output file too small to contain load address\n"
                "  Suggestion: Check if SF2 data was generated correctly\n"
                "  Check: Verify all required blocks were written\n"
                "  See: docs/guides/TROUBLESHOOTING.md#sf2-generation-failures"
            )
            return

        load_addr = struct.unpack('<H', self.output[0:2])[0]
        logger.debug(f"  Load address: ${load_addr:04X}")

        # Helper to convert memory address to file offset
        def addr_to_offset(addr: int) -> int:
            return addr - load_addr + 2  # +2 for PRG load address bytes

        # ===== INIT DISPATCH PATCH ($0E00) =====
        # The driver INIT at $0D89 calls JSR $0E00.  The dispatch table at $0E00 was:
        #   4C 92 14  JMP $1492   ← steals the return addr so $0E06 (full init) is never reached
        #   4C 9B 14  JMP $149B
        # Fix: change first entry to JSR $1492 and redirect second to JMP $0E06 so the
        # full init ($0E06: zero voices, set $1583=$02, set $1581=$80) runs during INIT.
        _off_0e00 = addr_to_offset(0x0E00)
        _off_0e03 = addr_to_offset(0x0E03)
        if (len(self.output) > _off_0e03 + 2
                and self.output[_off_0e00]     == 0x4C    # JMP $1492
                and self.output[_off_0e00 + 1] == 0x92
                and self.output[_off_0e00 + 2] == 0x14):
            self.output[_off_0e00] = 0x20                  # JSR $1492
            self.output[_off_0e03]     = 0x4C              # JMP $0E06
            self.output[_off_0e03 + 1] = 0x06
            self.output[_off_0e03 + 2] = 0x0E
            logger.debug("  INIT patch applied: $0E00 JMP->JSR $1492, $0E03 -> JMP $0E06")
        else:
            logger.warning(f"  INIT patch skipped: unexpected bytes at $0E00: "
                           f"{self.output[_off_0e00]:02X} {self.output[_off_0e00+1]:02X} {self.output[_off_0e00+2]:02X}")

        # ===== PLAY ENTRY PATCH ($0D97) =====
        # The PLAY wrapper at $0D91 calls JSR $0EA1, which is a mid-voice-loop entry
        # point that expects X=voice and FC set up — it never decrements the frame
        # counter ($1583) so the voice loop at $0E6D never runs and no SID writes occur.
        # Fix: redirect to JSR $0E06 (the real frame-tick routine) which decrements
        # $1583 and drives the full 3-voice loop + SID output on every PLAY call.
        _off_0d97 = addr_to_offset(0x0D97)
        if (len(self.output) > _off_0d97 + 2
                and self.output[_off_0d97]     == 0x20    # JSR
                and self.output[_off_0d97 + 1] == 0xA1    # lo: $A1
                and self.output[_off_0d97 + 2] == 0x0E):  # hi: $0E  → JSR $0EA1
            self.output[_off_0d97 + 1] = 0x06             # → JSR $0E06
            logger.debug("  PLAY patch applied: $0D97 JSR $0EA1 -> JSR $0E06")
        else:
            logger.warning(f"  PLAY patch skipped: unexpected bytes at $0D97: "
                           f"{self.output[_off_0d97]:02X} {self.output[_off_0d97+1]:02X} {self.output[_off_0d97+2]:02X}")

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

        # Read per-song NP21 voice orderlist start addresses from SID binary.
        # tbl_seq_ptr_lo/hi at load_addr+$0A1C / load_addr+$0A1F hold initial
        # orderlist positions for voices 0-2. These are used to redirect the
        # relocated NP21 player's orderlist pointer patches to the correct addresses.
        _c64 = getattr(self.data, 'c64_data', None)
        _sid_la = getattr(self.data, 'load_address', 0x1000)
        if _c64 and len(_c64) > 0x0A21:
            _v_ol_lo = [_c64[0x0A1C + v] for v in range(3)]
            _v_ol_hi = [_c64[0x0A1F + v] for v in range(3)]
        else:
            _v_ol_lo = [0x70, 0x9B, 0xB3]  # NP21 defaults (load $1000)
            _v_ol_hi = [0x1A, 0x1A, 0x1A]
        logger.info(f"  NP21 voice OL addrs: "
                    f"v0=${_v_ol_hi[0]:02X}{_v_ol_lo[0]:02X} "
                    f"v1=${_v_ol_hi[1]:02X}{_v_ol_lo[1]:02X} "
                    f"v2=${_v_ol_hi[2]:02X}{_v_ol_lo[2]:02X}")

        # Define all pointer patches (from trace_orderlist_access.py output)
        # Format: (file_offset, old_lo, old_hi, new_lo, new_hi)
        # NOTE: "old" addresses are AFTER -$0200 relocation (driver template is already relocated)
        pointer_patches = [
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
            # Voice orderlist pointers: patched to actual SID orderlist addresses per-song
            (0x057A, 0x3E, 0x17, _v_ol_lo[0], _v_ol_hi[0]),  # voice 0 OL (2 instances)
            (0x058D, 0x3E, 0x17, _v_ol_lo[0], _v_ol_hi[0]),
            (0x0581, 0x70, 0x17, _v_ol_lo[1], _v_ol_hi[1]),  # voice 1 OL (2 instances)
            (0x05B8, 0x70, 0x17, _v_ol_lo[1], _v_ol_hi[1]),
            (0x0595, 0x57, 0x17, _v_ol_lo[2], _v_ol_hi[2]),  # voice 2 OL (instance 1)
            (0x05A4, 0x57, 0x17, _v_ol_lo[2], _v_ol_hi[2]),  # voice 2 OL (instance 2)
            (0x05C8, 0xDA, 0x16, 0x42, 0x19),  # $16DA -> $1942 (2 instances)
            (0x05D6, 0xDA, 0x16, 0x42, 0x19),
            (0x05CF, 0x0C, 0x17, 0x74, 0x19),  # $170C -> $1974 (2 instances)
            (0x05DC, 0x0C, 0x17, 0x74, 0x19),
            (0x0684, 0x89, 0x17, 0xD0, 0x19),  # $1789 -> $19D0 (3 instances, filter_seq)
            (0x069D, 0x89, 0x17, 0xD0, 0x19),
            (0x06A7, 0x89, 0x17, 0xD0, 0x19),
            (0x068C, 0xBD, 0x17, 0x04, 0x1A),  # $17BD -> $1A04 (4 instances, filter_res)
            (0x0699, 0xBD, 0x17, 0x04, 0x1A),
            (0x06B5, 0xBD, 0x17, 0x04, 0x1A),
            (0x06BE, 0xBD, 0x17, 0x04, 0x1A),
            (0x06AF, 0xA3, 0x17, 0xEA, 0x19),  # $17A3 -> $19EA (filter_spd, step-advance path)
            # Sweep path: hold/accumulate code at $143F also references filter tables
            # but these instances were missing from the original patch set.
            # Sweep path: hold/accumulate code at $143F also references filter tables
            (0x06C8, 0xA3, 0x17, 0xEA, 0x19),  # $17A3 -> $19EA (filter_spd, sweep acc path)
            (0x06D1, 0x89, 0x17, 0xD0, 0x19),  # $1789 -> $19D0 (filter_seq, cutoff hi update)
            # Fix filter output: original NP21 uses LSR $FC for all 4 shifts;
            # SF2 template incorrectly uses LSR $EC for shifts 2-4, which corrupts
            # D416 with pattern-pointer LO bytes from voice processing.
            # Patch: 46 EC (LSR $EC) -> 46 FC (LSR $FC) at 3 locations.
            (0x06EA, 0x46, 0xEC, 0x46, 0xFC),  # $1466: LSR $EC -> LSR $FC
            (0x06ED, 0x46, 0xEC, 0x46, 0xFC),  # $1469: LSR $EC -> LSR $FC
            (0x06F0, 0x46, 0xEC, 0x46, 0xFC),  # $146C: LSR $EC -> LSR $FC
            (0x052A, 0xD7, 0x17, 0x3F, 0x1A),  # $17D7 -> $1A3F
            # Table references (after -$0200 relocation)
            (0x00DE, 0x19, 0x18, 0x81, 0x1A),  # $1819 -> $1A81 (3 instances - instrument table)
            (0x00E5, 0x19, 0x18, 0x81, 0x1A),
            (0x0394, 0x19, 0x18, 0x81, 0x1A),
            (0x0103, 0x1C, 0x18, 0x84, 0x1A),  # $181C -> $1A84
            (0x0108, 0x1F, 0x18, 0x87, 0x1A),  # $181F -> $1A87
            (0x038A, 0x1A, 0x18, 0x82, 0x1A),  # $181A -> $1A82
            (0x0141, 0x22, 0x18, (_sid_la + 0x0A22) & 0xFF, ((_sid_la + 0x0A22) >> 8) & 0xFF),  # $1822 -> $1A22 (pattern ptr lo table)
            (0x0146, 0x49, 0x18, (_sid_la + 0x0A49) & 0xFF, ((_sid_la + 0x0A49) >> 8) & 0xFF),  # $1849 -> $1A49 (pattern ptr hi table)
        ]

        # Apply the 40 working pointer patches from commit 08337f3
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

        # Prefer raw_sequences for Laxity driver: the NP21 player reads native sequence
        # bytes directly, so we must inject them verbatim. The translated self.data.sequences
        # only carries note events and silently drops all command bytes (filter triggers $C4/$CC,
        # portamento $81, etc.), causing 0% filter accuracy and other playback errors.
        raw_seqs = getattr(self.data, 'raw_sequences', None) or []
        seq_source = raw_seqs if raw_seqs else (self.data.sequences or [])
        seq_source_label = "raw" if raw_seqs else "translated"

        if seq_source:
            logger.info(f"  Injecting {len(seq_source)} sequences ({seq_source_label})...")
            current_offset = sequence_offset

            for seq_idx, sequence in enumerate(seq_source):
                if not sequence:
                    continue

                if isinstance(sequence, (bytes, bytearray)):
                    # Raw bytes — inject verbatim (preserves all NP21 commands)
                    seq_bytes = bytearray(sequence)
                    # Ensure terminated with $7F if not already
                    if not seq_bytes or seq_bytes[-1] != 0x7F:
                        seq_bytes.append(0x7F)
                else:
                    # Translated event list fallback
                    seq_bytes = bytearray()
                    for event in sequence:
                        if isinstance(event, dict):
                            note = event.get('note', 0)
                            gate = event.get('gate', False)
                            if gate:
                                seq_bytes.append(0x7E)
                            seq_bytes.append(note & 0x7F)
                        elif isinstance(event, int):
                            seq_bytes.append(event & 0xFF)
                    seq_bytes.append(0x7F)

                # Extend output if needed
                if current_offset + len(seq_bytes) > len(self.output):
                    self.output.extend(bytearray(
                        current_offset + len(seq_bytes) - len(self.output)))

                for i, byte in enumerate(seq_bytes):
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
        # Laxity NP21 filter uses three parallel tables (confirmed via Regenerator 2000).
        # Pointer patches redirect the player to read from these relocated addresses:
        #   tbl_filter_seq   : $1789 (orig $1989 - $0200) -> patched to $19D0
        #   tbl_filter_speed : $17A3 (orig $19A3 - $0200) -> patched to $19EA
        #   tbl_filter_res   : $17BD (orig $19BD - $0200) -> patched to $1A04
        # Tables packed at $19D0-$1A1D (before music block at $1A22).
        # Injection must match the patched pointer targets.
        # Filter tables must be entirely before the music block at $1A22.
        # Pack at $19D0/$19EA/$1A04 → all 78 bytes end at $1A1D (< $1A22).
        filter_seq_start  = 0x19D0   # tbl_filter_seq:       cutoff control + mode bits
        filter_spd_start  = 0x19EA   # tbl_filter_speed:     cutoff sweep delta
        filter_res_start  = 0x1A04   # tbl_filter_resonance: resonance per step

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

        # Inject filter tables (three parallel Laxity NP21 arrays)
        if hasattr(self.data, 'filtertable') and self.data.filtertable:
            filter_data = self.data.filtertable
            # filtertable is flat bytes: [seq, spd, res, next, seq, spd, res, next, ...]
            # Each 4-byte group maps to one filter step across the 3 parallel arrays.
            seq_bytes = bytearray()
            spd_bytes = bytearray()
            res_bytes = bytearray()
            raw = bytes(filter_data) if not isinstance(filter_data, (bytes, bytearray)) else filter_data
            for i in range(0, len(raw) - 3, 4):
                seq_bytes.append(raw[i])
                spd_bytes.append(raw[i + 1])
                res_bytes.append(raw[i + 2])

            for start_addr, table_bytes, label in (
                (filter_seq_start,  seq_bytes, 'filter_seq'),
                (filter_spd_start,  spd_bytes, 'filter_speed'),
                (filter_res_start,  res_bytes, 'filter_resonance'),
            ):
                if not table_bytes:
                    continue
                tbl_offset = addr_to_offset(start_addr)
                if len(self.output) < tbl_offset + len(table_bytes):
                    self.output.extend(bytearray(tbl_offset + len(table_bytes) - len(self.output)))
                for i, byte in enumerate(table_bytes):
                    self.output[tbl_offset + i] = byte
                logger.info(f"  Injected {label}: {len(table_bytes)} bytes at ${start_addr:04X}")

        # Inject raw NP21 music block verbatim at original SID addresses.
        # Block: pattern pointer lo table ($1A22) + hi table ($1A49) + orderlists + patterns.
        # This ensures the NP21 player finds all note patterns correctly, including filter
        # trigger commands ($C4/$CC) that activate the filter at the right song position.
        _NP21_MUSIC_OFF = _sid_la + 0x0A22 - _sid_la  # = 0x0A22 offset from SID c64_data start
        if _c64 and len(_c64) > _NP21_MUSIC_OFF:
            _music = bytes(_c64[_NP21_MUSIC_OFF:])
            _m_addr = _sid_la + _NP21_MUSIC_OFF   # $1A22 for NP21 at load $1000
            _m_off = addr_to_offset(_m_addr)
            if len(self.output) < _m_off + len(_music):
                self.output.extend(bytearray(_m_off + len(_music) - len(self.output)))
            for _i, _b in enumerate(_music):
                self.output[_m_off + _i] = _b
            logger.info(f"  Injected NP21 music block: {len(_music)} bytes at ${_m_addr:04X}")

        # Inject command table (NP21 indirect command dispatch table)
        # Each sequence command byte $C0+n references entry n in this table.
        # Entries are (cmd_byte, param_byte) pairs. Without this table, filter
        # commands ($C4/$CC) and portamento ($81) commands are all silently mis-fired.
        cmd_addrs = (getattr(self.data, 'extraction_addresses', None) or {}).get('commands')
        c64_data = getattr(self.data, 'c64_data', None)
        if cmd_addrs and c64_data:
            cmd_addr, cmd_end, cmd_size = cmd_addrs
            src_offset = cmd_addr - self.data.load_address
            if 0 <= src_offset and src_offset + cmd_size <= len(c64_data):
                cmd_bytes = bytes(c64_data[src_offset:src_offset + cmd_size])
                cmd_file_off = addr_to_offset(cmd_addr)
                if len(self.output) < cmd_file_off + cmd_size:
                    self.output.extend(bytearray(cmd_file_off + cmd_size - len(self.output)))
                for i, byte in enumerate(cmd_bytes):
                    self.output[cmd_file_off + i] = byte
                logger.info(f"  Injected command table: {cmd_size} bytes at ${cmd_addr:04X}")

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

        # Zero-init filter state variables.
        # The SF2 INIT routine ($1492) only clears $1581/$1582; it does NOT reset the
        # filter state machine variables $158A/$1589/$1586/$1587.
        # $158A ($E0 bug source): template has $10, causes D416=$E0 when inactive.
        # $1589 (sweep accumulator): template has $29, causes wrong sweep timing.
        # $1586 (mode_bits): template has $10 (LP bit set), causes D418=$1F not $0F.
        # $1587 (filter_res): template has $F2, causes D417=$F2 not $00 initially.
        # Setting all to $00 matches NP21 INIT behaviour (filter fully off at start).
        for _faddr, _flabel in [(0x158A, 'filter_lo'), (0x1589, 'filter_spd_acc'),
                                (0x1586, 'mode_bits'), (0x1587, 'filter_res')]:
            _foff = addr_to_offset(_faddr)
            if len(self.output) > _foff:
                self.output[_foff] = 0x00
                logger.debug(f"  Zeroed {_flabel} @ ${_faddr:04X}")

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
            logger.error(
                "  ERR Could not read file for validation\n"
                "  Suggestion: Check file permissions and path\n"
                "  Check: Ensure file exists and is accessible\n"
                "  See: docs/guides/TROUBLESHOOTING.md#file-access-errors"
            )
            return

        # Check minimum size
        if len(data) < 100:
            logger.error(
                f"  ERR File too small: {len(data)} bytes\n"
                f"  Suggestion: File appears corrupted or incomplete\n"
                f"  Check: Minimum valid SF2 file is ~8KB\n"
                f"  Try: Regenerate SF2 file from source SID\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#corrupted-sf2-files"
            )
            return

        # Check magic number
        if len(data) >= 4:
            magic = struct.unpack('<H', data[2:4])[0]
            if magic == 0x1337:
                logger.debug("  OK Valid magic number (0x1337)")
            else:
                logger.error(
                    f"  ERR Invalid magic number: 0x{magic:04X} (expected 0x1337)\n"
                    f"  Suggestion: File is not a valid SF2 format\n"
                    f"  Check: Ensure file was generated by SIDM2 converter\n"
                    f"  Try: Reconvert from original SID file\n"
                    f"  See: docs/SF2_FORMAT_SPEC.md#magic-number"
                )
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
                logger.error(
                    f"  ERR File truncated at block {block_id}\n"
                    f"  Suggestion: File was not written completely\n"
                    f"  Check: Verify disk space during conversion\n"
                    f"  Try: Regenerate SF2 file\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#truncated-files"
                )
                return

            block_size = data[offset + 1]
            block_end = offset + 2 + block_size

            if block_end > len(data):
                logger.error(
                    f"  ERR Block {block_id} extends beyond file (declares {block_size} bytes)\n"
                    f"  Suggestion: Block size header is corrupted\n"
                    f"  Check: File may have been modified after generation\n"
                    f"  Try: Regenerate SF2 file from source\n"
                    f"  See: docs/SF2_FORMAT_SPEC.md#block-structure"
                )
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
                logger.error(
                    "  ERR Too many blocks (possible corruption)\n"
                    "  Suggestion: File structure appears corrupted\n"
                    "  Check: Normal SF2 files have 3-5 blocks\n"
                    "  Try: Regenerate SF2 file from original SID\n"
                    "  See: docs/SF2_FORMAT_SPEC.md#block-limits"
                )
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
                logger.error(
                    "    ERR Instruments table (0x80) MISSING - file will be rejected!\n"
                    "    Suggestion: Critical metadata missing from SF2 file\n"
                    "    Check: Conversion may have failed partway through\n"
                    "    Try: Regenerate with --verbose to see where it failed\n"
                    "    See: docs/SF2_FORMAT_SPEC.md#required-tables"
                )

            if has_commands:
                logger.debug("    OK Commands table (0x81) found")
            else:
                logger.error(
                    "    ERR Commands table (0x81) MISSING - file will be rejected!\n"
                    "    Suggestion: Critical metadata missing from SF2 file\n"
                    "    Check: Conversion may have failed partway through\n"
                    "    Try: Regenerate with --verbose to see where it failed\n"
                    "    See: docs/SF2_FORMAT_SPEC.md#required-tables"
                )
        else:
            logger.error(
                "  ERR Block 3 (Driver Tables) missing\n"
                "  Suggestion: Critical driver tables not generated\n"
                "  Check: Conversion may have failed during table generation\n"
                "  Try: Regenerate SF2 file with different driver\n"
                "  See: docs/SF2_FORMAT_SPEC.md#driver-tables"
            )

        if has_block5:
            logger.debug("  OK Block 5 (Music Data) present")
        else:
            logger.warning("  WARN Block 5 (Music Data) missing")

        # Final verdict
        if has_instruments and has_commands and has_block1 and has_block2 and has_block3:
            logger.info("  OK SF2 FILE VALIDATION PASSED - file should load in SF2 Editor")
        else:
            logger.error(
                "  ERR SF2 FILE VALIDATION FAILED - file may be rejected by SF2 Editor\n"
                "  Suggestion: Review validation errors above for specific issues\n"
                "  Check: File may still work despite validation warnings\n"
                "  Try: Test file in SID Factory II to confirm\n"
                "  See: docs/guides/TROUBLESHOOTING.md#sf2-validation-failures"
            )

