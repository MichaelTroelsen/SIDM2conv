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
from . import np21_codegen
from . import audio_gate
from . import universal_211_workaround
from . import sf2_diagnostics
from . import low_load_layout
from . import sf2_aux_bodies
from . import sf2_parser
from . import sf2_metadata_trailer
from . import placeholder_edit_area
from . import sf2_template_finder
from . import driver11_table_helpers
from . import np21_edit_area_builder
from . import laxity_music_data_injector

logger = logging.getLogger(__name__)


class SF2Writer:
    """Write SID Factory II .sf2 project files.

    SF2 file format constants previously held as class attributes here
    (SF2_FILE_ID, BLOCK_*) were removed at v3.5.42 once the v3.5.40
    parser extraction made them orphaned. The single source of truth
    is now `sidm2.sf2_parser` (module-level constants). The remaining
    SF2_DRIVER_VERSION = 11 has no callers; SF2II reads the version
    from Block 1's body (`driver_info.driver_version_major`).
    """

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

            # Use Laxity-specific injection for Laxity driver, embed-binary
            # fallback for non-Laxity SIDs that have c64_data (Galway, Hubbard,
            # NP20, etc.), template-based for the rest.
            # Wizax-A redirect: files identified as non-Laxity by
            # player-id.exe but matching the Wizax-A signature can be
            # processed via the laxity F1 pipeline (their byte streams
            # are NP21-compatible). v3.5.15 enables this for 4 Wizax-A
            # files: 2000_A_D / Fight_TST_II / Hall_of_Fame / Min_Axel_F.
            # See `memory/wizax-a-byte-stream-re.md`.
            wizax_redirect = False
            if (self.driver_type != 'laxity'
                and getattr(self.data, 'c64_data', None) is not None):
                try:
                    from sidm2.wizax_a_detector import detect_wizax_a_layout
                    from sidm2.zetrex_yp_detector import detect_zetrex_yp_layout
                    sid_la_check = getattr(self.data, 'load_address', 0x1000)
                    cpyr = getattr(getattr(self.data, 'header', None),
                                   'copyright', '') or ''
                    if detect_wizax_a_layout(self.data.c64_data, sid_la_check, cpyr) is not None:
                        logger.info(
                            "  Wizax-A signature detected; redirecting "
                            "non-Laxity driver to the F1 pipeline."
                        )
                        wizax_redirect = True
                    elif detect_zetrex_yp_layout(self.data.c64_data, sid_la_check, cpyr) is not None:
                        logger.info(
                            "  Zetrex/YP signature detected; redirecting "
                            "non-Laxity driver to the F1 pipeline."
                        )
                        wizax_redirect = True
                except Exception:
                    pass

            if self.driver_type == 'laxity' or wizax_redirect:
                # Raw approach: embed song's own NP21 binary verbatim.
                # Works for any NP21 sub-version without hardcoded layout.
                if getattr(self.data, 'c64_data', None) is not None:
                    self._inject_laxity_raw_np21()
                else:
                    self._inject_laxity_music_data()
            elif getattr(self.data, 'c64_data', None) is not None:
                # Stage 8 Path A: minimal embed-binary for non-Laxity drivers.
                # Audio plays via the original player code; editor view is
                # mostly empty (table addresses point at high RAM, sequences
                # are placeholder 0x7F end markers).
                #
                # Known limitation (Stage 8.5, 2026-05-09): F10-load is only
                # 100% reliable when the SID's load_addr is roughly $0E00-$3000.
                # SIDs that load at $C000 (e.g., Hubbard Action_Biker), $7FF8
                # (Soundmonitor Byte_Bite), $5000 (Hubbard Commando), $BC00
                # (Hubbard Delta), $E000 (Hubbard ACE_II) trigger a heap-
                # layout-dependent crash inside SF2II's editor view setup
                # that's Heisenbug-masked under our diagnostic patched x86
                # SF2II build, so writer-side fixes can't be pinned without
                # admin-elevated AppVerifier/WER tooling. Conversion still
                # succeeds (the SF2 plays correctly outside the editor), but
                # users opening these files via F10 in SF2II will see a
                # crash. Workaround: route through Galway/dedicated converter
                # if applicable, or accept the editor crash and use other
                # tools (VICE, sidplayer) for audio.
                self._inject_player_raw_minimal()
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

        # Upstream #211 universal workaround. Every injection path
        # (laxity raw-NP21, minimal-embed, driver11) emits a valid SF2
        # whose Block 1 declares m_DriverCodeTop=$1000 and places a
        # 2-JMP trampoline at $1000. SF2II's GetSIDWriteInformationFromDriver
        # statically sweeps [$1000,$1900) for ABX/ABY $D400-$D406 writes
        # and then derefs result.begin() UNGUARDED (driver_utils.cpp:419)
        # — empty result ⇒ F10-load AV crash (upstream declined to fix).
        # Apply once here, after self.output is final, so it covers ALL
        # paths uniformly.
        self._ensure_sid_write_in_scan_window_universal()

        # v3.5.32 post-build zig64 audio gate. The py65 safety gate
        # (sidm2/ch_seq_safety_gate.py) catches most cases where a
        # ch_seq_ptr patch corrupts player code, but it can't simulate
        # CIA-IRQ-driven INIT correctly. For files like Edie_Ball
        # (Zetrex/YP cluster, CIA-timer-driven), py65 says SAFE while
        # cycle-accurate emulation diverges from the original SID. If
        # the patch is bad we revert the ch_seq_ptr bytes (preserves
        # everything else — translator, #211 stamp, META trailer, etc.).
        self._run_post_build_audio_gate()

        # v3.5.17: append a "META" trailer with PSID title/author/copyright
        # so SID -> SF2 -> SID round-trip preserves metadata. Trailer lives
        # past the shadow buffer; SF2II loads but never reads it (the C64
        # memory area where it lands isn't referenced by any handler).
        # Format: b"META" + 3 pascal strings (title, author, copyright).
        self._append_metadata_trailer()

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
        """v3.5.43 wrapper around sidm2.sf2_template_finder.find_template."""
        return sf2_template_finder.find_template(driver_type)

    def _parse_sf2_header(self) -> bool:
        """v3.5.40 wrapper around sidm2.sf2_parser.parse_sf2_blocks.

        Returns True on success (load address found + magic valid),
        False otherwise. Populates self.load_address and
        self.driver_info as a side effect (matching the original
        method's contract).
        """
        load_addr = sf2_parser.parse_sf2_blocks(self.output, self.driver_info)
        if load_addr is None:
            return False
        self.load_address = load_addr
        return True

    def _parse_descriptor_block(self, data: bytes) -> None:
        """v3.5.40 wrapper — see sidm2.sf2_parser.parse_descriptor_block."""
        sf2_parser.parse_descriptor_block(data, self.driver_info)

    def _parse_music_data_block(self, data: bytes) -> None:
        """v3.5.40 wrapper — see sidm2.sf2_parser.parse_music_data_block."""
        sf2_parser.parse_music_data_block(data, self.driver_info)

    def _parse_tables_block(self, data: bytes) -> None:
        """v3.5.40 wrapper — see sidm2.sf2_parser.parse_tables_block."""
        sf2_parser.parse_tables_block(data, self.driver_info)

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
        """Inject HR (Hard Restart) table data."""
        logger.info("  Injecting HR table...")

        result = driver11_table_helpers.find_table(self.driver_info, 'HR')
        if result is None:
            logger.debug("    Warning: No HR table found")
            return
        hr_addr, _columns, rows = result

        # Use extracted HR table or default
        hr_entries = getattr(self.data, 'hr_table', None)
        if not hr_entries:
            hr_entries = [(0x0F, 0x00)]  # Default fallback

        # HR table is 2-column (frames, wave). Each entry is a 2-tuple.
        driver11_table_helpers.write_column_major(
            self.output, self._addr_to_offset(hr_addr),
            hr_entries, columns=2, rows=rows)

        logger.info(f"    Written {len(hr_entries)} HR table entries (frames={hr_entries[0][0]})")

    def _inject_pulse_table(self) -> None:
        """Inject pulse table data extracted from Laxity SID"""
        logger.info("  Injecting Pulse table...")

        result = driver11_table_helpers.find_table(
            self.driver_info, 'Pulse', 'P')
        if result is None:
            logger.debug("    Warning: No Pulse table found in driver")
            return
        pulse_addr, columns, rows = result

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

        # Convert from Laxity format (Y*4 indexing) to SF2 format (direct indexing)
        # Laxity: (val, cnt, dur, next_y) where next_y is pre-multiplied by 4
        # SF2: (val, cnt, dur, next_idx) where next_idx is direct entry number
        # Index already converted during extraction (Y*4 → direct).
        driver11_table_helpers.write_column_major(
            self.output, self._addr_to_offset(pulse_addr),
            pulse_entries, columns, rows)

        logger.info(f"    Written {len(pulse_entries)} Pulse table entries (padded from {len(laxity_tables.get('pulse_table', []))})")

    def _inject_filter_table(self) -> None:
        """Inject filter table data extracted from Laxity SID."""
        logger.info("  Injecting Filter table...")

        result = driver11_table_helpers.find_table(
            self.driver_info, 'Filter', 'F')
        if result is None:
            logger.debug("    Warning: No Filter table found in driver")
            return
        filter_addr, columns, rows = result

        laxity_tables = extract_all_laxity_tables(self.data.c64_data, self.data.load_address)
        laxity_filter_entries = laxity_tables.get('filter_table', [])

        if not laxity_filter_entries:
            laxity_filter_entries = [(0x40, 0x01, 0x20, 0x00)]

        # Convert Laxity filter format to SF2 filter format.
        logger.info(f"    Converting {len(laxity_filter_entries)} Laxity filter entries to SF2 format...")
        filter_entries = LaxityConverter.convert_filter_table(laxity_filter_entries)
        logger.info(f"    Converted to {len(filter_entries)} SF2 filter entries")

        # Pad to minimum size with neutral entry: no filter, no modulation,
        # instant, end marker.
        MIN_FILTER_ENTRIES = 16
        neutral_entry = (0x00, 0x00, 0x00, 0x7F)
        while len(filter_entries) < MIN_FILTER_ENTRIES:
            filter_entries.append(neutral_entry)

        driver11_table_helpers.write_column_major(
            self.output, self._addr_to_offset(filter_addr),
            filter_entries, columns, rows)

        logger.info(f"    Written {len(filter_entries)} Filter table entries (padded from {len(laxity_tables.get('filter_table', []))})")

    def _inject_init_table(self) -> None:
        """Inject Init table data."""
        logger.info("  Injecting Init table...")

        result = driver11_table_helpers.find_table(self.driver_info, 'Init')
        if result is None:
            logger.debug("    Warning: No Init table found in driver")
            return
        init_addr, columns, rows = result

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
        """Inject Tempo table data."""
        logger.info("  Injecting Tempo table...")

        result = driver11_table_helpers.find_table(
            self.driver_info, 'Tempo', 'T')
        if result is None:
            logger.debug("    Warning: No Tempo table found in driver")
            return
        tempo_addr, _columns, rows = result

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
        """Inject Arpeggio table data."""
        logger.info("  Injecting Arp table...")

        result = driver11_table_helpers.find_table(
            self.driver_info, 'Arp', 'A')
        if result is None:
            logger.debug("    Warning: No Arp table found in driver")
            return
        arp_addr, columns, rows = result

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

    def _append_metadata_trailer(self) -> None:
        """v3.5.41 wrapper around
        sidm2.sf2_metadata_trailer.encode_metadata_trailer.

        Pulls title/author/copyright from self.data.header, encodes
        the trailer, and appends to self.output. See the module
        docstring for the trailer format spec.
        """
        if not hasattr(self.data, 'header') or not self.data.header:
            title = author = copyright = ""
        else:
            h = self.data.header
            title     = getattr(h, 'name', '')      or ''
            author    = getattr(h, 'author', '')    or ''
            copyright = getattr(h, 'copyright', '') or ''
        trailer = sf2_metadata_trailer.encode_metadata_trailer(
            title, author, copyright)
        self.output = bytes(self.output) + trailer
        logger.info(
            f"  Metadata trailer: title={title.strip()!r} "
            f"author={author.strip()!r} copyright={copyright.strip()!r} "
            f"({len(trailer)}B appended)"
        )

    def _inject_auxiliary_data(self) -> None:
        """Inject auxiliary data with instrument and command names"""
        # Low-load layout: the binary spans the hardcoded aux-pointer
        # address $0FFB, so writing the pointer there corrupts live
        # player data. Skip aux entirely (SF2II cleanly skips when it
        # reads the binary's bytes as an address into unmapped/zero RAM).
        if getattr(self, '_skip_aux', False):
            logger.info("  Skipping aux injection (low-load: $0FFB "
                        "overlaps embedded binary)")
            return
        logger.info("  Injecting auxiliary data (names)...")

        # Path A (non-Laxity SIDs): skip instrument-name extraction, which
        # would call Laxity-specific extractors on a Galway/Hubbard binary
        # and return garbage that corrupts the TableText body and crashes
        # F10-load. Empty names produce a clean (padded-with-empty-strings)
        # TableText that loads fine.
        if getattr(self, '_minimal_path', False):
            instrument_names = []
            command_names = []
        else:
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

        # Stage 6: emit the bundled-format aux chain
        # [id=3 param=2, id=2 param=1, id=1 param=1, id=4 param=2,
        #  id=5 param=2, END] — matches all 67 bundled SF2II reference
        # files we surveyed. TLV format: [u8 id][u16 LE param][u16 LE length]
        # [body]. The aux chain pointer at C64 $0FFB tells SF2II where to
        # find the chain. Without that pointer (the prior bug — aux_data
        # was appended but the pointer was never set), SF2II's
        # ParseAuxilaryData gets aux_pointer=0 and skips the chain entirely.
        #
        # Bodies for id=1, 2, 3 encode editor preferences / play-markers /
        # hardware prefs respectively. We emit minimal-but-valid bodies
        # taken from the reference SF2; exact field meanings aren't fully
        # decoded (a Stage 6.5 follow-up could expose them), but the
        # bundled values load cleanly across the corpus.

        def _make_aux_block(bid: int, param: int, body: bytes) -> bytes:
            return bytes([bid]) + struct.pack('<H', param) + struct.pack('<H', len(body)) + body

        # Aux body formats (decoded from auxilary_data_*.cpp:RestoreFromSaveData):
        # id=1 EditingPreferences (3B v1): [NotationMode][HighlightOffset][HighlightInterval]
        # id=2 HardwarePreferences (2B v1): [SIDModel][Region]
        # id=3 PlayMarkers v2:               [layer_count] then per-layer
        #                                    [marker_count][u32×marker_count event positions]
        # Defaults match reasonable editor state. Region/SIDModel could be
        # pulled from the PSID flags but defaulting to (8580, PAL) like the
        # reference is a safer bet because it matches more bundled files.
        body3 = bytes([0x01, 0x00])         # 1 layer, 0 markers (no song-position bookmarks)
        body2 = bytes([0x01, 0x00])         # SIDModel=8580 (1), Region=PAL (0)
        body1 = bytes([0x00, 0x00, 0x04])   # Sharp notation, highlight offset=0, interval=4

        # id=4 param=2 — Table text (instrument + command names).
        table_text_data = self._build_table_text_data(
            instrument_names, command_names, instr_table_id, cmd_table_id)

        # id=5 param=2 — Description / song metadata.
        desc_data = self._build_description_data()

        # Stage 6 first slice: emit [id=4 TableText, id=5 Songs, END].
        # Adding id=1/2/3 with verbatim reference bodies broke F10-load
        # because their bodies (PlayMarkers / HardwarePreferences /
        # EditingPreferences) reference addresses + states that don't
        # match our SF2 layout, so RestoreFromSaveData crashes. Decoding
        # those formats is a Stage 6.5 follow-up; for now we deliver the
        # missing aux-pointer fix without the full bundled chain — that
        # alone gives SF2II access to instrument names + song description
        # which the prior aux-pointer-zero made unreachable.
        # Stage 6.7: aux chain in bundled order [3, 2, 1, 4, 5, END]
        # matching all 67 bundled SF2II reference files.
        aux_data = bytearray()
        aux_data.extend(_make_aux_block(3, 2, body3))             # PlayMarkers (v2)
        aux_data.extend(_make_aux_block(2, 1, body2))             # HardwarePreferences
        aux_data.extend(_make_aux_block(1, 1, body1))             # EditingPreferences
        aux_data.extend(_make_aux_block(4, 2, bytes(table_text_data)))  # TableText
        if desc_data:
            aux_data.extend(_make_aux_block(5, 2, bytes(desc_data)))    # Songs
        aux_data.extend(bytes([0x00, 0x00, 0x00, 0x00, 0x00]))   # END marker

        # Place aux chain at end of file. C64 address of aux_chain_start
        # = LOAD_BASE + (file offset of aux start).
        # IMPORTANT: use the SF2 file's PRG load address ($0D7E) — read
        # back from the first two bytes of self.output — NOT the SID's
        # PSID load address (often $0000), which is what self.load_address
        # holds. Using PSID load address would compute aux_pointer_offset
        # at file offset 4093 instead of $027F, leaving the actual slot
        # at $0FFB-as-c64 still zero and SF2II skipping the chain.
        sf2_prg_load = self.output[0] | (self.output[1] << 8)
        aux_chain_offset_in_file = len(self.output)   # before extension
        aux_chain_c64_addr = sf2_prg_load + (aux_chain_offset_in_file - 2)

        # Write aux pointer at C64 $0FFB (file offset $0FFB - prg_load + 2)
        aux_pointer_offset = 0x0FFB - sf2_prg_load + 2
        if 0 <= aux_pointer_offset and aux_pointer_offset + 2 <= len(self.output):
            self.output[aux_pointer_offset]     = aux_chain_c64_addr & 0xFF
            self.output[aux_pointer_offset + 1] = (aux_chain_c64_addr >> 8) & 0xFF
            self.output.extend(aux_data)
            logger.info(f"    Aux chain @ ${aux_chain_c64_addr:04X} "
                        f"({len(aux_data)}B, [3,2,1,4,5,END] bundled order), "
                        f"pointer@$0FFB written at file offset ${aux_pointer_offset:04X}")
            if hasattr(self.data, 'header') and self.data.header:
                logger.info(f"    Written metadata: {self.data.header.name} by {self.data.header.author}")
            logger.info(f"    Written {len(instrument_names)} instrument names")
            logger.info(f"    Written {len(command_names)} command names")
        else:
            logger.debug("    Warning: Could not find auxiliary data pointer location")

    def _build_description_data(self) -> Optional[bytearray]:
        """v3.5.39 wrapper around sidm2.sf2_aux_bodies.build_description_data.

        Pulls the song name from self.data.header (PSID title) before
        delegating to the pure builder. Returns bytearray for
        backwards-compat with the _inject_auxiliary_data call site.
        """
        if not hasattr(self.data, 'header') or not self.data.header:
            song_name = None
        else:
            song_name = self.data.header.name
        return bytearray(sf2_aux_bodies.build_description_data(song_name))

    def _build_table_text_data(self, instrument_names, command_names,
                                instr_table_id=1, cmd_table_id=0) -> bytearray:
        """v3.5.39 wrapper around sidm2.sf2_aux_bodies.build_table_text_data.

        Returns bytearray for backwards-compat with the
        _inject_auxiliary_data call site.
        """
        return bytearray(sf2_aux_bodies.build_table_text_data(
            instrument_names, command_names, instr_table_id, cmd_table_id))

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
        """v3.5.43 wrapper around sidm2.sf2_template_finder.find_driver."""
        return sf2_template_finder.find_driver()

    def _create_minimal_structure(self) -> None:
        """Create a minimal SF2-like structure"""
        self.output = bytearray(8192)

    def _inject_music_data(self) -> None:
        """Inject extracted music data into the SF2 structure"""
        logger.info(" Music data injection is a placeholder")
        logger.debug("The output file structure may need manual refinement")

    def _run_post_build_audio_gate(self) -> None:
        """v3.5.36 wrapper around sidm2.audio_gate.run_post_build_audio_gate.

        Pulls per-instance state (output buffer, sid path, patch records)
        and forwards to the module-level function. Mutates self.output in
        place. Sets self._ch_seq_patches / self._wave_copy_jsr_offs to
        empty lists when the gate's respective revert step succeeded.
        """
        np21_off = getattr(self, '_np21_file_off', None)
        sid_path = getattr(self, '_sid_input_path', None)
        if np21_off is None or sid_path is None:
            return
        header = getattr(self.data, 'header', None)
        sid_init = getattr(header, 'init_address', None) if header else None
        sid_play = getattr(header, 'play_address', None) if header else None
        result = audio_gate.run_post_build_audio_gate(
            out=self.output,
            sid_path=sid_path,
            np21_off=np21_off,
            ch_seq_patches=getattr(self, '_ch_seq_patches', None) or [],
            wave_copy_jsr_offs=getattr(self, '_wave_copy_jsr_offs', None) or [],
            ch_seq_patch_layout=getattr(self, '_ch_seq_patch_layout', None),
            sid_init=sid_init,
            sid_play=sid_play,
        )
        if result.get('ch_seq_reverted'):
            self._ch_seq_patches = []
        if result.get('wave_copy_nopped'):
            self._wave_copy_jsr_offs = []

    def _ensure_sid_write_in_scan_window_universal(self) -> None:
        """v3.5.36 wrapper around
        sidm2.universal_211_workaround.ensure_sid_write_in_scan_window_universal.
        Forwards self.output; assigns back if the function returned a new
        buffer (Digidag-class case appends a stub at end of file).
        """
        result = universal_211_workaround.ensure_sid_write_in_scan_window_universal(
            self.output)
        if result is not None:
            self.output = result

    def _build_low_load_sf2(self, c64_data, sid_la, init_addr, play_addr) -> bool:
        """v3.5.38 wrapper around sidm2.low_load_layout.build_low_load_sf2.

        See `sidm2/low_load_layout.py` for the architecture writeup
        (why the alternate PRG layout exists, the constraints, and the
        $0FFB aux-pointer caveat). This wrapper preserves the original
        method signature (returns True on success, False on
        infeasibility) and handles the two self.* writes the pure
        function delegates back to the caller:

          - self.output  ← the built SF2 bytes
          - self._skip_aux ← True (REQUIRED for low-load — see
            module docstring on $0FFB)
        """
        result = low_load_layout.build_low_load_sf2(
            c64_data, sid_la, init_addr, play_addr)
        if result is None:
            return False
        sf2_bytes, skip_aux = result
        self.output = bytearray(sf2_bytes)
        self._skip_aux = skip_aux
        return True

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

        # Sub-$1000 wrapper-collision cluster: binaries loading below
        # $1000 overlap the normal SF2 wrapper ($0D7E header + $0F90
        # handlers + $0F9E translator) in the single contiguous PRG, so
        # the normal layout aborts ("Translator overflow") → silent SF2.
        # Use an alternate low-LOAD_BASE layout: header BELOW the binary,
        # handlers AFTER it. See memory/sub-1000-cluster-design.md.
        if 0 < sid_la < 0x1000:
            if self._build_low_load_sf2(c64_data, sid_la, init_addr, play_addr):
                return
            # Low-load returned False — header doesn't fit below sid_la
            # (Echo_Beat $0400 is the only file in this state: only
            # 512B of space below the load, but the 9-block SF2 header
            # needs 525B). Falling through to the legacy layout would
            # crash with a `struct.pack 'H' overflow` because handler
            # offsets go negative. Emit a clear architectural-limit
            # error and bail — the file genuinely cannot be converted
            # with the SF2 schema.
            logger.error(
                f"  Binary load address ${sid_la:04X} is too low: "
                f"no room for the 525B SF2 wrapper header below it "
                f"(stack + zeropage occupy $0000-$01FF; the lowest "
                f"safe LOAD_BASE is $0500). This is an architectural "
                f"limit of the SF2 format, not a converter bug.")
            raise errors.ConversionError(
                stage="raw-NP21 inject (low-load)",
                reason=f"sid_load=${sid_la:04X} below the $0500 LOAD_BASE floor "
                       f"(SF2 header doesn't fit below the binary)",
                input_file=getattr(self.data, 'filepath', None),
                docs_link="guides/LAXITY_DRIVER_USER_GUIDE.md#troubleshooting",
            )

        # v3.5.34 high-load architectural check: when the binary ends
        # within ~$300 bytes of $FFFF, there's no room for the SF2 edit
        # area (typically $400-$2000 bytes for orderlists + sequences +
        # F2/F3/F4/F5 tables + shadow buffer). Block 3 column addresses
        # would overflow the 16-bit space and produce a cryptic
        # `struct.pack 'H' overflow` deep in header generation.
        #
        # Canonical cases: Crosswords (1988 Starion, load=$F000, 3363B
        # → ends $FD23, only $2DD bytes left to $FFFF), Magic_Sound
        # (1987 Yield Point Music, load=$F000, 2613B → similar). Both
        # are documented "high-load architectural infeasibility" — the
        # SF2 format can't represent edit-area metadata for binaries
        # that fill nearly all 64KB.
        #
        # Threshold: we need ~$800 bytes minimum after the binary for
        # the smallest reasonable edit area + shadow + #211 stamp. If
        # less, raise a clean error instead of letting struct.pack
        # blow up several frames deep.
        MIN_POST_BINARY = 0x800
        if sid_la + len(c64_data) + MIN_POST_BINARY > 0x10000:
            logger.error(
                f"  Binary load address ${sid_la:04X} + size "
                f"${len(c64_data):04X} = ends at ${sid_la + len(c64_data):04X}: "
                f"insufficient room (<{MIN_POST_BINARY:#06x} bytes) below "
                f"$FFFF for the SF2 edit area + shadow buffer. This is an "
                f"architectural limit of the SF2 format — Block 3 column "
                f"addresses are 16-bit, so the edit area can't extend past "
                f"the C64 address space."
            )
            raise errors.ConversionError(
                stage="raw-NP21 inject (high-load)",
                reason=f"sid_load=${sid_la:04X} + size {len(c64_data)} leaves "
                       f"<{MIN_POST_BINARY:#06x} bytes below $FFFF for the "
                       f"edit area + shadow buffer",
                input_file=getattr(self.data, 'filepath', None),
                docs_link="guides/LAXITY_DRIVER_USER_GUIDE.md#troubleshooting",
            )

        LOAD_BASE      = 0x0D7E    # SF2 loads here; 0x1337 magic goes here
        # HANDLER_BASE history:
        #   $0F00 — original; only allowed 386B for the 9-block header set
        #   $0FA0 — moved to fit ~525B header set + 51-byte single-pattern
        #           translator at $0FAE (77B budget).
        #   $0F80 — Stage 2.5: multi-pattern translator needs ~87B; bumping
        #           HANDLER_BASE earlier gives translator a $0F8E..$0FFA
        #           window (109B).
        #   $0F90 — Stage 5: Block 9 grew from 1B placeholder to 41B
        #           (4 InstrumentDataPointerDescription entries).
        #           Stinsen+Unboxed headers now end ~$0F8B, leaving only
        #           ~5B slack to $0F90. Translator window $0F9E..$0FFA = 92B.
        HANDLER_BASE   = 0x0F90
        INIT_HANDLER   = HANDLER_BASE + 0
        PLAY_HANDLER   = HANDLER_BASE + 4
        STOP_HANDLER   = HANDLER_BASE + 8
        TRANSLATE_BASE = HANDLER_BASE + 0x0E

        # Generate SF2 header blocks with correct handler entry points.
        # generate_complete_headers() returns [37 13] + Block1..5 + [FF].
        # These bytes go at $0D7E; blocks start at $0D80 (= load_addr + 2) as
        # required by driver_info.cpp:313: block_address = m_TopAddress + 2.
        from sidm2.sf2_header_generator import SF2HeaderGenerator
        gen = SF2HeaderGenerator(driver_size=len(c64_data) + (sid_la - LOAD_BASE))
        gen.DRIVER_INIT = INIT_HANDLER
        gen.DRIVER_PLAY = PLAY_HANDLER
        gen.DRIVER_STOP = STOP_HANDLER

        # Detect per-file Block 3 table addresses from the actual NP21 binary,
        # rather than relying on Stinsen-derived defaults. Songs with smaller
        # binaries (e.g. Angular ~5KB vs Stinsen ~9KB) have their Wave/Pulse/
        # Filter/Instruments at different absolute C64 addresses; pointing
        # SF2II's editor view at the wrong addresses triggers a deterministic
        # editor-view crash on F10-load. See memory/project-status.md
        # (2026-05-06 Angular generalization finding) for context.
        # Stage 7 Phase B.1: capture the BINARY wave-table addresses before
        # gen.wave_addr gets overwritten with the SF2 edit area address
        # below (line ~1796). The wave-copy 6502 routine needs both the
        # NOTE address (where the player reads note offsets) AND the
        # WAVE-DATA address (where the player reads waveform values) —
        # NP21 stores them as PARALLEL arrays at separate addresses, e.g.
        # for Stinsen: note=$190C, wave-data=$18DA.
        np21_note_binary_addr = None
        np21_wave_data_binary_addr = None
        try:
            laxity_tables = extract_all_laxity_tables(c64_data, sid_la)
            if laxity_tables.get('wave_addr'):
                gen.wave_addr = laxity_tables['wave_addr']
                np21_note_binary_addr = laxity_tables['wave_addr']
            if laxity_tables.get('wave_data_addr'):
                np21_wave_data_binary_addr = laxity_tables['wave_data_addr']
            if laxity_tables.get('pulse_addr'):
                gen.pulse_addr = laxity_tables['pulse_addr']

            # Filter-address detection: extract_all_laxity_tables internally
            # falls back to Stinsen's $1989 when its strict stride-26 detector
            # fails. For files with interleaved 4-byte filter records
            # (Unboxed, Angular), the v2 loose detector finds the actual
            # base by clustering LDA targets near STA $D4xx sites.
            filter_addr = laxity_tables.get('filter_addr') or 0
            # The "extracted" address may be the $1989 fallback. Re-test
            # with the strict detector to see if dynamic detection actually
            # found it; if not, try the v2 loose detector.
            from sidm2.table_extraction import (
                detect_np21_filter_offsets,
                find_filter_table_np21_v2,
                find_instrument_table_np21_v2,
            )
            strict = detect_np21_filter_offsets(c64_data, sid_la)
            if strict:
                # Strict detection succeeded — trust the extracted addr
                gen.filter_addr = filter_addr or (sid_la + strict[0])
            else:
                # Strict failed; try v2 loose
                v2_filter = find_filter_table_np21_v2(c64_data, sid_la)
                if v2_filter:
                    gen.filter_addr = v2_filter
                    logger.info(f"  Filter table detected via v2 loose detector: ${gen.filter_addr:04X}")
                elif filter_addr:
                    gen.filter_addr = filter_addr  # fallback to whatever extract returned

            # Instrument-address detection: extract_all_laxity_tables uses
            # find_instrument_table whose scoring loop has an indentation bug
            # (returns 0 for Stinsen/Unboxed/Angular). Fall back to the v2
            # detector when the primary fails.
            instr_addr = laxity_tables.get('instr_addr') or 0
            if not instr_addr:
                wave_size = max(len(laxity_tables.get('wave_table') or []), 64)
                fallback = find_instrument_table_np21_v2(c64_data, sid_la, wave_size)
                if fallback:
                    instr_addr = fallback
                    logger.info(f"  Instrument table detected via v2 fallback: ${instr_addr:04X}")

            if instr_addr:
                gen.instr_addr = instr_addr
                # Commands sit a fixed 0x70 bytes past Instruments in Laxity NP21
                # (verified on Stinsen: instr=$1A6B, cmd=$1ADB). No separate
                # extractor; bias from Instruments is the simplest correct anchor.
                gen.cmd_addr = instr_addr + 0x70

            logger.info(
                f"  Block 3 table addresses: Wave=${gen.wave_addr:04X}, "
                f"Pulse=${gen.pulse_addr:04X}, Filter=${gen.filter_addr:04X}, "
                f"Instr=${gen.instr_addr:04X}, Cmd=${gen.cmd_addr:04X}"
            )
        except Exception as e:
            logger.warning(
                f"  Per-file table-address detection failed ({e!r}); "
                f"falling back to Stinsen-derived defaults"
            )

        header_bytes = gen.generate_complete_headers()

        # Safety check: headers must not overlap handler code
        headers_end_addr = LOAD_BASE + len(header_bytes)
        if headers_end_addr > HANDLER_BASE:
            logger.error(
                f"  Headers too large! End ${headers_end_addr:04X} > handler base ${HANDLER_BASE:04X}"
            )
            return

        # --- Extract NP21 patterns and build SF2 edit data area ---
        # Returns voice_init_idx so we can compute per-voice shadow slots,
        # raw_patterns (original NP21 sequence bytes for shadow pre-fill),
        # and voice_pat_counts (Stage 2.5: feeds the multi-pattern translator).
        music_data_params, sf2_edit_data, voice_init_idx, raw_patterns, voice_pat_counts = \
            self._build_np21_sf2_edit_area(c64_data, sid_la)

        # --- Shadow buffer: per-voice flat NP21 stream + ch_seq_ptr patch ---
        #
        # Stage 2 (segmentation) note: the shadow now holds ONE flat stream
        # per voice (= the original NP21 byte stream the song's player would
        # read), regardless of how many SF2 patterns we emit for the editor's
        # display. This decouples the editor's "many short patterns" view
        # from the player's "one continuous voice stream" model.
        #
        # The runtime translator at $0F0E (criterion-3 edit-propagation) is
        # DISABLED for now (PLAY = JSR play_addr; RTS, not JMP $0F0E),
        # because the existing translator's "SF2 pat N -> shadow slot N"
        # logic doesn't work for multi-pattern voices. Re-enabling requires
        # a multi-pattern translator that walks each voice's orderlist and
        # concatenates referenced patterns into the voice's shadow slot —
        # tracked as Stage 2.5 follow-up. Until then, edits in the editor
        # are visual only and don't propagate to playback.
        SEQ_SHADOW_SIZE = 256       # NP21 sequence max length the player can address
        SHADOW_VOICES = 3           # one slot per voice
        num_patterns = len(raw_patterns)
        # voice_streams: list[(body_bytes, loop_target)] of length 3, one per voice.
        # Built from raw_patterns + voice_init_idx (which voice maps to which
        # extracted stream — voices that share a stream share a slot in
        # voice_streams too, but each voice still gets its own shadow slot
        # so ch_seq_ptr per voice is unambiguous).
        voice_streams = []
        for v in range(3):
            if num_patterns > 0 and 0 <= voice_init_idx[v] < num_patterns:
                voice_streams.append(raw_patterns[voice_init_idx[v]])
            else:
                voice_streams.append((b"", None))

        shadow_buffer_size = SHADOW_VOICES * SEQ_SHADOW_SIZE
        sf2_data_base = sid_la + len(c64_data)

        # Stage 7 Phase B.1: append a wave SPLIT-copy 6502 routine to
        # the END of sf2_edit_data, so F3 (wave) edits propagate to
        # playback. The routine does a per-row split-copy from the
        # SF2 edit area's interleaved (waveform, note_offset) bytes
        # to the parallel NP21 arrays at np21_wave_data_addr and
        # np21_note_addr. ch_seq_ptr patch resolves correctly because
        # shadow_base is computed AFTER appending.
        #
        # Eligibility:
        #   - Class A extraction succeeded (np21_note_binary_addr set).
        #   - find_wave_table_from_player_code returned a wave-data
        #     addr distinct from the note addr (np21_wave_data_binary_addr).
        #   - Both addresses inside the embedded c64_data range.
        #   - music_data_params has an SF2 edit-area wave address.
        wave_copy_addr = None
        edit_wave_addr = music_data_params.get('edit_wave_addr')
        wave_n_rows = 32   # matches Stage 4 emit (32 rows × 2 cols)
        if (num_patterns > 0
            and np21_note_binary_addr is not None
            and np21_wave_data_binary_addr is not None
            and edit_wave_addr is not None
            and sid_la <= np21_note_binary_addr < sid_la + len(c64_data)
            and sid_la <= np21_wave_data_binary_addr < sid_la + len(c64_data)):
            wave_routine = self._emit_wave_split_copy_routine(
                sf2_wave_addr=edit_wave_addr,
                np21_wave_data_addr=np21_wave_data_binary_addr,
                np21_note_addr=np21_note_binary_addr,
                n_rows=wave_n_rows,
            )
            wave_copy_addr = sf2_data_base + len(sf2_edit_data)
            sf2_edit_data = bytes(sf2_edit_data) + wave_routine
            logger.info(
                f"  Stage 7 wave-split-copy routine @ ${wave_copy_addr:04X} "
                f"({len(wave_routine)}B); src=${edit_wave_addr:04X} "
                f"wave-dst=${np21_wave_data_binary_addr:04X} "
                f"note-dst=${np21_note_binary_addr:04X} "
                f"({wave_n_rows} rows per PLAY tick)"
            )

        # Stage 7 Phase B.2 (Stinsen variant): wire up the column-major
        # AD/SR copy routine when the binary matches Stinsen layout.
        # F2 (instruments) edits to AD/SR will then propagate to
        # playback. HR/Pulse/Wave columns NOT yet propagated — destination
        # addresses haven't been RE'd. See memory/stinsen-instr-layout.md.
        instr_copy_addr = None
        edit_instr_addr = music_data_params.get('edit_instr_addr')
        if num_patterns > 0 and edit_instr_addr is not None:
            from sidm2.stinsen_instr_detector import detect_stinsen_layout
            from sidm2.beast_instr_detector import detect_beast_layout
            from sidm2.angular_instr_detector import detect_angular_layout

            stinsen = detect_stinsen_layout(c64_data, sid_la)
            beast   = detect_beast_layout(c64_data, sid_la)
            angular = detect_angular_layout(c64_data, sid_la)

            if (stinsen is not None
                and sid_la <= stinsen.ad_col_addr < sid_la + len(c64_data)
                and sid_la <= stinsen.sr_col_addr < sid_la + len(c64_data)):
                instr_routine = self._emit_instr_column_copy_routine(
                    sf2_instr_addr=edit_instr_addr,
                    np21_ad_col_addr=stinsen.ad_col_addr,
                    np21_sr_col_addr=stinsen.sr_col_addr,
                    n_instruments=stinsen.n_instruments,
                )
                instr_copy_addr = sf2_data_base + len(sf2_edit_data)
                sf2_edit_data = bytes(sf2_edit_data) + instr_routine
                logger.info(
                    f"  Stage 7 instr-column-copy Stinsen (AD+SR) @ ${instr_copy_addr:04X} "
                    f"({len(instr_routine)}B); src=${edit_instr_addr:04X} "
                    f"AD-dst=${stinsen.ad_col_addr:04X} "
                    f"SR-dst=${stinsen.sr_col_addr:04X} "
                    f"({stinsen.n_instruments} instruments per PLAY tick)"
                )
            elif (beast is not None
                  and sid_la <= beast.table_addr < sid_la + len(c64_data)
                  and beast.n_instruments * 8 <= 256):
                # Beast: row-major, AD at byte 5, SR at byte 6 within
                # each 8-byte row. Reuse _emit_instr_copy_routine with
                # custom fields list. NP21-stride 8 / SF2-stride 6 are
                # the existing routine's defaults.
                instr_routine = self._emit_instr_copy_routine(
                    sf2_instr_addr=edit_instr_addr,
                    np21_instr_addr=beast.table_addr,
                    n_instruments=beast.n_instruments,
                    fields=[
                        (0, beast.ad_offset),   # SF2 col 0 (AD) → row+5
                        (1, beast.sr_offset),   # SF2 col 1 (SR) → row+6
                    ],
                )
                instr_copy_addr = sf2_data_base + len(sf2_edit_data)
                sf2_edit_data = bytes(sf2_edit_data) + instr_routine
                logger.info(
                    f"  Stage 7 instr-row-copy Beast (AD+SR) @ ${instr_copy_addr:04X} "
                    f"({len(instr_routine)}B); src=${edit_instr_addr:04X} "
                    f"table=${beast.table_addr:04X} "
                    f"({beast.n_instruments} instruments × 8B-row, "
                    f"AD@+{beast.ad_offset} SR@+{beast.sr_offset})"
                )
            elif (angular is not None
                  and sid_la <= angular.table_addr < sid_la + len(c64_data)
                  and angular.n_instruments * 2 <= 256):
                # Angular: row-major, 2 bytes per instrument (AD/SR
                # adjacent at offsets +0/+1). Use np21_stride=2.
                instr_routine = self._emit_instr_copy_routine(
                    sf2_instr_addr=edit_instr_addr,
                    np21_instr_addr=angular.table_addr,
                    n_instruments=angular.n_instruments,
                    fields=[
                        (0, angular.ad_offset),  # SF2 col 0 (AD) → row+0
                        (1, angular.sr_offset),  # SF2 col 1 (SR) → row+1
                    ],
                    np21_stride=2,
                )
                instr_copy_addr = sf2_data_base + len(sf2_edit_data)
                sf2_edit_data = bytes(sf2_edit_data) + instr_routine
                logger.info(
                    f"  Stage 7 instr-row-copy Angular (AD+SR) @ ${instr_copy_addr:04X} "
                    f"({len(instr_routine)}B); src=${edit_instr_addr:04X} "
                    f"table=${angular.table_addr:04X} "
                    f"({angular.n_instruments} instruments × 2B-row, "
                    f"AD@+{angular.ad_offset} SR@+{angular.sr_offset})"
                )

        # Stage 7 Phase B.2 (F4 pulse, Stinsen variant): wire up the
        # split-copy routine that propagates SF2-edit-area pulse edits
        # to NP21's parallel PW lo / PW hi byte streams at $1957/$193E.
        # Verified 2026-05-11 via py65 + direct-edit-patch (see
        # memory/stinsen-pulse-architecture.md).
        pulse_copy_addr = None
        edit_pulse_addr = music_data_params.get('edit_pulse_addr')
        if num_patterns > 0 and edit_pulse_addr is not None:
            from sidm2.stinsen_pulse_detector import detect_stinsen_pulse_layout
            from sidm2.beast_pulse_detector import detect_beast_pulse_layout
            from sidm2.angular_pulse_detector import detect_angular_pulse_layout

            sp_stinsen = detect_stinsen_pulse_layout(c64_data, sid_la)
            sp_beast   = detect_beast_pulse_layout(c64_data, sid_la)
            sp_angular = detect_angular_pulse_layout(c64_data, sid_la)

            if (sp_stinsen is not None
                and sid_la <= sp_stinsen.pw_lo_addr < sid_la + len(c64_data)
                and sid_la <= sp_stinsen.pw_hi_addr < sid_la + len(c64_data)):
                pulse_routine = self._emit_pulse_split_copy_routine(
                    sf2_pulse_addr=edit_pulse_addr,
                    np21_pulse_lo_addr=sp_stinsen.pw_lo_addr,
                    np21_pulse_hi_addr=sp_stinsen.pw_hi_addr,
                    n_rows=sp_stinsen.n_steps,
                )
                pulse_copy_addr = sf2_data_base + len(sf2_edit_data)
                sf2_edit_data = bytes(sf2_edit_data) + pulse_routine
                logger.info(
                    f"  Stage 7 pulse-split-copy Stinsen @ ${pulse_copy_addr:04X} "
                    f"({len(pulse_routine)}B); src=${edit_pulse_addr:04X} "
                    f"PW-lo-dst=${sp_stinsen.pw_lo_addr:04X} "
                    f"PW-hi-dst=${sp_stinsen.pw_hi_addr:04X} "
                    f"({sp_stinsen.n_steps} steps per PLAY tick)"
                )
            elif (sp_beast is not None
                  and sid_la <= sp_beast.stream_addr < sid_la + len(c64_data)):
                pulse_routine = self._emit_pulse_packed_copy_routine(
                    sf2_pulse_addr=edit_pulse_addr,
                    np21_stream_addr=sp_beast.stream_addr,
                    n_rows=sp_beast.n_steps,
                )
                pulse_copy_addr = sf2_data_base + len(sf2_edit_data)
                sf2_edit_data = bytes(sf2_edit_data) + pulse_routine
                logger.info(
                    f"  Stage 7 pulse-packed-copy Beast @ ${pulse_copy_addr:04X} "
                    f"({len(pulse_routine)}B); src=${edit_pulse_addr:04X} "
                    f"stream-dst=${sp_beast.stream_addr:04X} "
                    f"({sp_beast.n_steps} steps × 4B stride per PLAY tick)"
                )
            elif (sp_angular is not None
                  and sid_la <= sp_angular.stream_addr < sid_la + len(c64_data)):
                pulse_routine = self._emit_pulse_packed_copy_routine(
                    sf2_pulse_addr=edit_pulse_addr,
                    np21_stream_addr=sp_angular.stream_addr,
                    n_rows=sp_angular.n_steps,
                )
                pulse_copy_addr = sf2_data_base + len(sf2_edit_data)
                sf2_edit_data = bytes(sf2_edit_data) + pulse_routine
                logger.info(
                    f"  Stage 7 pulse-packed-copy Angular @ ${pulse_copy_addr:04X} "
                    f"({len(pulse_routine)}B); src=${edit_pulse_addr:04X} "
                    f"stream-dst=${sp_angular.stream_addr:04X} "
                    f"({sp_angular.n_steps} steps × 4B stride per PLAY tick)"
                )

        # Stage 7 Phase B.2 (F5 filter, Stinsen variant): wire up the
        # 3-array split-copy routine that propagates SF2-edit-area filter
        # edits to NP21's parallel byte streams at $1989/$19A3/$19BD.
        # The streams are a state machine internally (cmd/val/aux byte
        # patterns dispatch SET vs SWEEP behavior at runtime); we write
        # bytes back as-is, the player re-interprets on next step.
        # See memory/stinsen-filter-architecture.md.
        filter_copy_addr = None
        edit_filter_addr = music_data_params.get('edit_filter_addr')
        if num_patterns > 0 and edit_filter_addr is not None:
            from sidm2.stinsen_filter_detector import detect_stinsen_filter_layout
            from sidm2.beast_filter_detector import detect_beast_filter_layout
            from sidm2.angular_filter_detector import detect_angular_filter_layout

            sf_stinsen = detect_stinsen_filter_layout(c64_data, sid_la)
            sf_beast   = detect_beast_filter_layout(c64_data, sid_la)
            sf_angular = detect_angular_filter_layout(c64_data, sid_la)

            if (sf_stinsen is not None
                and sid_la <= sf_stinsen.cmd_addr < sid_la + len(c64_data)
                and sid_la <= sf_stinsen.val_addr < sid_la + len(c64_data)
                and sid_la <= sf_stinsen.aux_addr < sid_la + len(c64_data)):
                filter_routine = self._emit_filter_split_copy_routine(
                    sf2_filter_addr=edit_filter_addr,
                    np21_cmd_addr=sf_stinsen.cmd_addr,
                    np21_val_addr=sf_stinsen.val_addr,
                    np21_aux_addr=sf_stinsen.aux_addr,
                    n_rows=sf_stinsen.n_steps,
                )
                filter_copy_addr = sf2_data_base + len(sf2_edit_data)
                sf2_edit_data = bytes(sf2_edit_data) + filter_routine
                logger.info(
                    f"  Stage 7 filter-split-copy Stinsen @ ${filter_copy_addr:04X} "
                    f"({len(filter_routine)}B); src=${edit_filter_addr:04X} "
                    f"cmd-dst=${sf_stinsen.cmd_addr:04X} val-dst=${sf_stinsen.val_addr:04X} "
                    f"aux-dst=${sf_stinsen.aux_addr:04X} ({sf_stinsen.n_steps} steps per PLAY tick)"
                )
            elif (sf_beast is not None
                  and sid_la <= sf_beast.cutoff_hi_stream_addr < sid_la + len(c64_data)):
                filter_routine = self._emit_filter_cutoff_only_routine(
                    sf2_filter_addr=edit_filter_addr,
                    np21_cutoff_hi_addr=sf_beast.cutoff_hi_stream_addr,
                    n_rows=sf_beast.n_steps,
                )
                filter_copy_addr = sf2_data_base + len(sf2_edit_data)
                sf2_edit_data = bytes(sf2_edit_data) + filter_routine
                logger.info(
                    f"  Stage 7 filter-cutoff-only Beast @ ${filter_copy_addr:04X} "
                    f"({len(filter_routine)}B); src=${edit_filter_addr:04X} "
                    f"cutoff_hi-dst=${sf_beast.cutoff_hi_stream_addr:04X} "
                    f"({sf_beast.n_steps} steps per PLAY tick)"
                )
            elif (sf_angular is not None
                  and sid_la <= sf_angular.cutoff_hi_stream_addr < sid_la + len(c64_data)):
                filter_routine = self._emit_filter_cutoff_only_routine(
                    sf2_filter_addr=edit_filter_addr,
                    np21_cutoff_hi_addr=sf_angular.cutoff_hi_stream_addr,
                    n_rows=sf_angular.n_steps,
                )
                filter_copy_addr = sf2_data_base + len(sf2_edit_data)
                sf2_edit_data = bytes(sf2_edit_data) + filter_routine
                logger.info(
                    f"  Stage 7 filter-cutoff-only Angular @ ${filter_copy_addr:04X} "
                    f"({len(filter_routine)}B); src=${edit_filter_addr:04X} "
                    f"cutoff_hi-dst=${sf_angular.cutoff_hi_stream_addr:04X} "
                    f"({sf_angular.n_steps} steps per PLAY tick)"
                )

        # Stage 7 trampoline (v3.5.8): when 3+ copy routines are wired
        # (wave + instr + pulse + filter all fire for Stinsen), 4
        # inline JSRs in the translator + JSR play + RTS = 99B,
        # overflowing the $0F9E..$0FFA = 98B window. Consolidate the
        # tail (instr + pulse + filter) into a single trampoline
        # emitted at the end of sf2_edit_data. Translator JSRs (a)
        # wave_copy_addr inline, (b) the trampoline. Net translator
        # save: trampoline collapses 3 conditional JSRs into 1 (-6B).
        # Eligibility: at least 3 of the 4 copy_addrs are non-None.
        _wired = [a for a in (wave_copy_addr, instr_copy_addr,
                              pulse_copy_addr, filter_copy_addr) if a is not None]
        trampoline_or_wave_copy_addr = wave_copy_addr
        tr_instr_copy  = instr_copy_addr
        tr_pulse_copy  = pulse_copy_addr
        tr_filter_copy = filter_copy_addr
        if len(_wired) >= 4:
            # Consolidate instr + pulse + filter into a trampoline.
            # (Leave wave as a direct JSR so we always have at least one
            #  direct JSR for code-path coverage in tests + corpus.)
            _tail_addrs = [a for a in (instr_copy_addr, pulse_copy_addr,
                                       filter_copy_addr) if a is not None]
            tramp = bytearray()
            for a in _tail_addrs:
                tramp += bytes([0x20, a & 0xFF, (a >> 8) & 0xFF])  # JSR
            tramp += bytes([0x60])                                  # RTS
            _trampoline_addr = sf2_data_base + len(sf2_edit_data)
            sf2_edit_data = bytes(sf2_edit_data) + bytes(tramp)
            logger.info(
                f"  Stage 7 copy-trampoline @ ${_trampoline_addr:04X} "
                f"({len(tramp)}B); {len(_tail_addrs)} routines "
                f"({', '.join(f'${a:04X}' for a in _tail_addrs)})"
            )
            # Pass the trampoline as instr_copy_addr (one JSR slot in
            # the translator), suppress pulse + filter direct JSRs.
            tr_instr_copy  = _trampoline_addr
            tr_pulse_copy  = None
            tr_filter_copy = None

        shadow_base = sf2_data_base + len(sf2_edit_data)

        # Pre-fill shadow with each voice's full NP21 byte stream + loop terminator.
        shadow_buffer = bytearray(shadow_buffer_size)
        for v, (body, loop_target) in enumerate(voice_streams):
            slot = v * SEQ_SHADOW_SIZE
            n = min(len(body), SEQ_SHADOW_SIZE - 2)
            shadow_buffer[slot : slot + n] = body[:n]
            shadow_buffer[slot + n]     = 0xFF
            shadow_buffer[slot + n + 1] = loop_target & 0xFF if loop_target is not None else 0x00

        # Patch ch_seq_ptr in c64_data — each voice points to its own
        # shadow slot at shadow_base + v*256. Default offsets are NP21's
        # $0A1C/$0A1F. For Wizax-A files, override with the detected
        # ptr-table addresses (file-specific) so the redirected pipeline
        # actually patches the addresses the Wizax-A player reads from.
        # v3.5.17: skip the default $1A1C/$1A1F patch when the bytes
        # there don't actually contain valid ch_seq_ptrs (out-of-range
        # → those bytes are state-machine data, not pointers). Patching
        # them corrupts other code paths (e.g. Angular: LDA $1A1F,Y at
        # $10F7 reads state from there, causing 3 extra osc3 register
        # writes per active frame). Tradeoff: F1 edit propagation
        # disabled for these files; audio playback matches original.
        c64_data = bytearray(c64_data)
        CH_SEQ_LO_OFF = 0x0A1C
        CH_SEQ_HI_OFF = 0x0A1F
        skip_ch_seq_patch = False
        try:
            from sidm2.wizax_a_detector import detect_wizax_a_layout
            from sidm2.zetrex_yp_detector import detect_zetrex_yp_layout
            cpyr = getattr(getattr(self.data, 'header', None),
                           'copyright', '') or ''
            wzx_for_patch = detect_wizax_a_layout(c64_data, sid_la, cpyr)
            zyp_for_patch = detect_zetrex_yp_layout(c64_data, sid_la, cpyr)
        except Exception:
            wzx_for_patch = None
            zyp_for_patch = None
        patch_layout = wzx_for_patch or zyp_for_patch
        patch_layout_name = 'Wizax-A' if wzx_for_patch else ('Zetrex/YP' if zyp_for_patch else None)
        if patch_layout is not None:
            CH_SEQ_LO_OFF = patch_layout.ptr_lo_addr - sid_la
            CH_SEQ_HI_OFF = patch_layout.ptr_hi_addr - sid_la
            logger.info(
                f"  {patch_layout_name} ch_seq_ptr patching at "
                f"${patch_layout.ptr_lo_addr:04X}/${patch_layout.ptr_hi_addr:04X} "
                f"(NOT default $0A1C/$0A1F)"
            )
        else:
            # Check whether bytes at default $1A1C/$1A1F look like valid
            # ch_seq_ptrs (in-range, pointing inside the binary). If not,
            # those bytes are something else and patching them corrupts
            # the file. Skip the patch to preserve audio integrity.
            def _ptrs_in_range_check(lo_off, hi_off):
                if lo_off + 2 >= len(c64_data) or hi_off + 2 >= len(c64_data):
                    return False
                for v in range(3):
                    p = (c64_data[hi_off + v] << 8) | c64_data[lo_off + v]
                    if not (sid_la <= p < sid_la + len(c64_data)):
                        return False
                return True
            if not _ptrs_in_range_check(CH_SEQ_LO_OFF, CH_SEQ_HI_OFF):
                skip_ch_seq_patch = True
                logger.info(
                    f"  Default $1A1C/$1A1F ch_seq_ptr bytes are not "
                    f"in-range pointers for this file; skipping patch "
                    f"to preserve audio fidelity (F1 edit propagation "
                    f"disabled for this file)"
                )
            else:
                # v3.5.28 ch_seq_ptr safety gate: bytes look like in-range
                # pointers, but verify the player actually USES them as
                # ch_seq_ptr. Some files (Dark_Fun.sid, 2023 Genesis
                # Project, canonical example) have valid-looking pointer
                # bytes at $1A1C-$1A21 that are part of OTHER data tables;
                # patching them corrupts those tables → wrong audio.
                # The gate emulates the patch under py65 with the shadow
                # buffer mirroring the original byte streams; if the
                # patched audio diverges from the original, the player
                # doesn't use these bytes as ch_seq_ptr → skip patch.
                try:
                    from sidm2.ch_seq_safety_gate import is_ch_seq_patch_safe
                    init_addr_for_gate = getattr(
                        self.data.header, 'init_address', sid_la
                    ) if getattr(self, 'data', None) and getattr(
                        self.data, 'header', None
                    ) else sid_la
                    play_addr_for_gate = getattr(
                        self.data.header, 'play_address', sid_la + 3
                    ) if getattr(self, 'data', None) and getattr(
                        self.data, 'header', None
                    ) else sid_la + 3
                    if play_addr_for_gate == 0:
                        play_addr_for_gate = init_addr_for_gate + 3
                    if not is_ch_seq_patch_safe(
                        bytes(c64_data), sid_la,
                        init_addr_for_gate, play_addr_for_gate,
                        CH_SEQ_LO_OFF, CH_SEQ_HI_OFF,
                    ):
                        skip_ch_seq_patch = True
                        logger.info(
                            f"  ch_seq_ptr safety gate: patching "
                            f"$1A1C/$1A1F changes audio under py65 "
                            f"simulation (player uses these bytes for "
                            f"non-ch_seq_ptr data); skipping patch to "
                            f"preserve audio fidelity (F1 edit "
                            f"propagation disabled for this file)"
                        )
                except Exception as e:
                    # Safety gate failure (e.g., py65 import error) →
                    # fall through to apply patch as before. Logged at
                    # debug only since this is a soft fallback.
                    logger.debug(
                        f"  ch_seq_ptr safety gate skipped due to "
                        f"exception: {e}"
                    )
        # v3.5.32: track patched addresses + original bytes so the
        # post-build zig64 audio gate can revert if the patch corrupts
        # audio under cycle-accurate emulation (a case py65 can miss
        # for CIA-IRQ-driven players like Zetrex/YP — see Edie_Ball).
        ch_seq_patches: list[tuple[int, int]] = []
        if num_patterns > 0 and not skip_ch_seq_patch:
            for v in range(SHADOW_VOICES):
                voice_shadow_addr = shadow_base + v * SEQ_SHADOW_SIZE
                if CH_SEQ_LO_OFF + v < len(c64_data) and CH_SEQ_HI_OFF + v < len(c64_data):
                    ch_seq_patches.append((CH_SEQ_LO_OFF + v, c64_data[CH_SEQ_LO_OFF + v]))
                    ch_seq_patches.append((CH_SEQ_HI_OFF + v, c64_data[CH_SEQ_HI_OFF + v]))
                    c64_data[CH_SEQ_LO_OFF + v] = voice_shadow_addr & 0xFF
                    c64_data[CH_SEQ_HI_OFF + v] = (voice_shadow_addr >> 8) & 0xFF
        # Save for post-build verification (used in write() after the
        # universal #211 stamp).
        self._ch_seq_patches = ch_seq_patches
        self._ch_seq_patch_layout = patch_layout_name  # for log messages

        # Update driver_size to include the full file extent (NP21 + edit area + shadow)
        gen.driver_size += len(sf2_edit_data) + shadow_buffer_size

        # Stages 3 + 4: repoint Block 3 column addresses (Instruments,
        # Wave, Pulse, Filter) at the clean Driver-11-format tables we
        # emitted in the SF2 edit area instead of into the NP21 binary's
        # Laxity-format bytes. F2/F3/F4/F5 views will now show structured
        # rows in the editor instead of garbage.
        edit_instr_addr = music_data_params.get('edit_instr_addr')
        if edit_instr_addr:
            gen.instr_addr = edit_instr_addr
            # Commands table sits 0x70 past Instruments in NP21; keep that
            # bias against the new instr_addr.
            gen.cmd_addr = edit_instr_addr + 0x70
        if music_data_params.get('edit_wave_addr'):
            gen.wave_addr = music_data_params['edit_wave_addr']
        if music_data_params.get('edit_pulse_addr'):
            gen.pulse_addr = music_data_params['edit_pulse_addr']
        if music_data_params.get('edit_filter_addr'):
            gen.filter_addr = music_data_params['edit_filter_addr']

        # Now regenerate headers with correct Block 5 + Block 3 addresses
        header_bytes = gen.generate_complete_headers(music_data_params)

        # Re-check header size hasn't grown past handler base
        headers_end_addr = LOAD_BASE + len(header_bytes)
        if headers_end_addr > HANDLER_BASE:
            logger.error(
                f"  Headers too large after music data update! End ${headers_end_addr:04X} > ${HANDLER_BASE:04X}"
            )
            return

        # Build the full PRG: [load_addr:2] + memory from $0D7E through shadow buffer
        gap = sid_la - LOAD_BASE
        file_size = 2 + gap + len(c64_data) + len(sf2_edit_data) + shadow_buffer_size
        file_data = bytearray(file_size)

        # PRG load address (2-byte little-endian header)
        file_data[0] = LOAD_BASE & 0xFF
        file_data[1] = LOAD_BASE >> 8

        # SF2 magic + header blocks at $0D7E (file offset 2)
        file_data[2:2 + len(header_bytes)] = header_bytes

        # Handler code:
        #   INIT (HANDLER_BASE+0): JSR init_addr; RTS                (4 bytes)
        #   PLAY (HANDLER_BASE+4): JMP TRANSLATE_BASE + 1B NOP fill  (4 bytes)
        #     (translator does JSR play_addr internally on completion)
        #   STOP (HANDLER_BASE+8): LDA #0; STA $D418; RTS            (6 bytes)
        # Stage 2.5: PLAY rewires to JMP TRANSLATE_BASE again so editor edits
        # propagate through _emit_multipat_translator() to the per-voice
        # shadow slots. If num_patterns == 0 (no music data) PLAY stays as
        # plain JSR play_addr; RTS as a degenerate fallback.
        hnd_off = 2 + (HANDLER_BASE - LOAD_BASE)
        file_data[hnd_off:hnd_off + 4]  = bytes([0x20, init_addr & 0xFF, init_addr >> 8, 0x60])
        if num_patterns > 0:
            file_data[hnd_off + 4:hnd_off + 8]  = bytes([
                0x4C, TRANSLATE_BASE & 0xFF, (TRANSLATE_BASE >> 8) & 0xFF, 0xEA
            ])
        else:
            file_data[hnd_off + 4:hnd_off + 8]  = bytes([0x20, play_addr & 0xFF, play_addr >> 8, 0x60])
        file_data[hnd_off + 8:hnd_off + 14] = bytes([0xA9, 0x00, 0x8D, 0x18, 0xD4, 0x60])

        # NP21 binary (with patched ch_seq_ptr) at its original load address
        np21_off = 2 + gap
        file_data[np21_off:np21_off + len(c64_data)] = c64_data
        # Save for the post-build zig64 audio gate (used in write())
        # to know where the ch_seq_ptr patches landed in the output PRG.
        self._np21_file_off = np21_off

        # Stage 2.5: emit multi-pattern translator at TRANSLATE_BASE. Walks
        # each voice's segment range, concatenates pattern bytes into the
        # voice's shadow slot, terminates with 0xFF + 0x00. Audio fidelity
        # is preserved (build-time shadow has same content), and editor
        # edits to SF2 patterns propagate through here on every PLAY tick.
        # Stage 7 Phase B.1: if `wave_copy_addr` was set above (Class A
        # files where we know both the binary wave-table address and the
        # SF2 edit-area wave address), pass it to the translator so it
        # JSRs the wave-copy routine before JSR play_addr. F3 edits then
        # propagate to playback.
        if num_patterns > 0:
            # Pre-compute effective_play_addr (used by both the translator
            # JSR target below AND the trampoline patch later). For PSID
            # `play_addr == init+3`-with-JMP-indirection layouts (Beast,
            # Hubbard), the byte at init+3 is `4C lo hi`; the JMP target
            # is the real play handler. Translator must JSR the real
            # handler, NOT the trampoline (would infinite-loop after we
            # patch init+3 → JMP TRANSLATE_BASE below).
            effective_play_addr = play_addr
            if (play_addr == init_addr + 3
                and 0 <= (init_addr + 3 - sid_la) < len(c64_data) - 2):
                stub_lo = init_addr + 3 - sid_la
                if c64_data[stub_lo] == 0x4C:    # JMP abs
                    t = c64_data[stub_lo + 1] | (c64_data[stub_lo + 2] << 8)
                    if sid_la <= t < sid_la + len(c64_data):
                        effective_play_addr = t
            translator_bytes = self._emit_multipat_translator(
                voice_pat_counts=voice_pat_counts,
                seq00_addr=music_data_params['seq00_addr'],
                shadow_base=shadow_base,
                play_addr=effective_play_addr,
                translate_base=TRANSLATE_BASE,
                table_copy_addr=trampoline_or_wave_copy_addr,
                instr_copy_addr=tr_instr_copy,
                pulse_copy_addr=tr_pulse_copy,
                filter_copy_addr=tr_filter_copy,
            )
            tr_off = 2 + (TRANSLATE_BASE - LOAD_BASE)
            if tr_off + len(translator_bytes) > np21_off:
                logger.error(
                    f"  Translator overflow: {len(translator_bytes)}B at "
                    f"${TRANSLATE_BASE:04X} would overflow into $1000 (NP21 binary)"
                )
                return
            file_data[tr_off:tr_off + len(translator_bytes)] = translator_bytes

            # v3.5.33: scan the translator for the wave-copy JSR so the
            # post-build zig64 gate can NOP it if audio diverges.
            # Pattern: `20 lo hi` where (lo|hi<<8) == trampoline_or_wave_copy_addr.
            # The wave-copy routine writes to NP21 wave/note scratch
            # addresses (e.g. $190C/$18DA for Stinsen-class). For files
            # like Patterns where those addresses overlap an unrelated
            # data table inside the binary, the runtime copy stomps live
            # data → audio divergence.
            jsr_lo_off = []  # absolute file offsets of each JSR we may NOP
            if trampoline_or_wave_copy_addr is not None:
                tgt_lo = trampoline_or_wave_copy_addr & 0xFF
                tgt_hi = (trampoline_or_wave_copy_addr >> 8) & 0xFF
                for k in range(len(translator_bytes) - 2):
                    if (translator_bytes[k] == 0x20
                        and translator_bytes[k+1] == tgt_lo
                        and translator_bytes[k+2] == tgt_hi):
                        jsr_lo_off.append(tr_off + k)
                        break  # only first match — the wave-copy JSR
            self._wave_copy_jsr_offs = jsr_lo_off

        # Fix zig64 auto-detection: it always calls init_addr+3 as PLAY.
        # Determine effective play target — usually play_addr, but when
        # PSID play_addr == init+3 AND that location is a `JMP $XXXX`
        # (Beast/Hubbard layout: byte at init+3 is `4C lo hi`),
        # extracting the JMP target lets us safely patch init+3 to
        # JMP TRANSLATE_BASE without clobbering the original play entry.
        # The translator's JSR play_addr should target the JMP target,
        # not init+3 (would infinite-loop).
        effective_play_addr = play_addr
        # v3.5.31: init+3 patch safety. The patch overwrites 3 bytes at
        # init_addr+3 with `JMP TRANSLATE_BASE`. That's safe ONLY when
        # those 3 bytes are either:
        #   (A) `JMP $XXXX` (`$4C`) — typical NP21 trampoline; we
        #       extract the JMP target as effective_play_addr.
        #   (B) Inert gap (`$00 $00 $00` or `$EA $EA $EA`) — Twone_Five-
        #       class NP21 with no live code at init+3.
        # For files where init+3 is live player code (Joe_Gunn_Extras
        # init=$1900: byte 0=$19 is the high byte of an LDA abs,Y
        # operand from $1901's `B9 28` instruction), the patch CORRUPTS
        # init → player crashes → SF2 produces 0 SID writes. The old
        # `play_redirect_safe = (play_addr != init_addr + 3)` heuristic
        # had the safety check exactly backwards.
        play_redirect_safe = False
        stub_lo = init_addr + 3 - sid_la
        if 0 <= stub_lo and stub_lo + 2 < len(c64_data):
            b0, b1, b2 = c64_data[stub_lo], c64_data[stub_lo + 1], c64_data[stub_lo + 2]
            if b0 == 0x4C:    # Case A: JMP abs
                jmp_target = b1 | (b2 << 8)
                if sid_la <= jmp_target < sid_la + len(c64_data):
                    if play_addr == init_addr + 3:
                        effective_play_addr = jmp_target
                    play_redirect_safe = True
            elif (b0, b1, b2) in ((0x00, 0x00, 0x00),
                                   (0xEA, 0xEA, 0xEA)):
                # Case B: inert gap
                play_redirect_safe = True

        if play_redirect_safe:
            # The trampoline at init_addr+3 is what zig64 calls as PLAY
            # (it always uses init_addr+3 as the play entry). For runtime
            # translator + table-copy routines to fire on EVERY zig64
            # trace tick — not just SF2II's PLAY-handler path — point
            # the trampoline at TRANSLATE_BASE when patterns exist,
            # falling through to play_addr otherwise. Without this,
            # edits to the SF2 edit area would only propagate when SF2II
            # calls PLAY via $0F94, never under zig64 trace.
            stub_off = np21_off + (init_addr + 3 - sid_la)
            if 0 <= stub_off and stub_off + 3 <= len(file_data):
                if num_patterns > 0:
                    target = TRANSLATE_BASE
                    label = "translator"
                else:
                    target = effective_play_addr
                    label = "play"
                file_data[stub_off]     = 0x4C  # JMP
                file_data[stub_off + 1] = target & 0xFF
                file_data[stub_off + 2] = (target >> 8) & 0xFF
                logger.info(f"  Patched ${init_addr+3:04X} -> JMP ${target:04X} "
                            f"({label} — zig64 PLAY redirect)")

        # zig64 entry stub for non-$1000-loaded binaries:
        # zig64 always calls $1000 as INIT and $1003 as PLAY. For NP21
        # binaries loaded at $1000 the first 6 bytes are JMP init/JMP play
        # already, so zig64 works directly. For binaries loaded ELSEWHERE
        # (Zetrex/YP at $E000, Echo_Beat at $0400, etc.), $1000-$1003
        # is a gap in the SF2 file = zero bytes = no audio.
        # Write `JMP INIT_HANDLER; JMP PLAY_HANDLER` stubs there so zig64
        # finds the right entry points. INIT_HANDLER ($0F90) does
        # JSR psid_init then RTS; PLAY_HANDLER ($0F94) jumps to the
        # multipat translator. Both handlers are emitted unconditionally.
        binary_covers_1003 = sid_la <= 0x1000 < sid_la + len(c64_data)
        if not binary_covers_1003:
            stub_off_1000 = 2 + (0x1000 - LOAD_BASE)
            if 0 <= stub_off_1000 and stub_off_1000 + 6 <= len(file_data):
                # JMP INIT_HANDLER
                file_data[stub_off_1000]     = 0x4C
                file_data[stub_off_1000 + 1] = INIT_HANDLER & 0xFF
                file_data[stub_off_1000 + 2] = (INIT_HANDLER >> 8) & 0xFF
                # JMP PLAY_HANDLER
                file_data[stub_off_1000 + 3] = 0x4C
                file_data[stub_off_1000 + 4] = PLAY_HANDLER & 0xFF
                file_data[stub_off_1000 + 5] = (PLAY_HANDLER >> 8) & 0xFF
                logger.info(
                    f"  zig64 entry stub at $1000: "
                    f"JMP ${INIT_HANDLER:04X} / JMP ${PLAY_HANDLER:04X} "
                    f"(binary at ${sid_la:04X}-${sid_la + len(c64_data) - 1:04X} doesn't cover $1000-$1003)"
                )

        # SF2 edit data appended after NP21 binary
        if sf2_edit_data:
            edit_off = np21_off + len(c64_data)
            file_data[edit_off:edit_off + len(sf2_edit_data)] = sf2_edit_data

        # Shadow buffer appended after SF2 edit data
        if shadow_buffer_size > 0:
            shadow_off = np21_off + len(c64_data) + len(sf2_edit_data)
            file_data[shadow_off:shadow_off + shadow_buffer_size] = shadow_buffer

        # Upstream #211 workaround is applied universally in write()
        # (_ensure_sid_write_in_scan_window_universal) after all injection
        # paths converge, so nothing path-specific is needed here.
        self.output = file_data

        logger.info(f"  SF2 size: {len(self.output)} bytes")
        logger.info(f"  Magic + headers: ${LOAD_BASE:04X}-${headers_end_addr - 1:04X} ({len(header_bytes)} bytes)")
        logger.info(f"  Handlers: ${HANDLER_BASE:04X} (INIT=${INIT_HANDLER:04X}, PLAY=${PLAY_HANDLER:04X}, STOP=${STOP_HANDLER:04X})")
        logger.info(f"  NP21 binary: ${sid_la:04X}-${sid_la + len(c64_data) - 1:04X} ({len(c64_data)} bytes)")
        logger.info(f"  SF2 edit data: ${sf2_data_base:04X}-${sf2_data_base + len(sf2_edit_data) - 1:04X} ({len(sf2_edit_data)} bytes)")
        if shadow_buffer_size > 0:
            logger.info(f"  Shadow buffer: ${shadow_base:04X}-${shadow_base + shadow_buffer_size - 1:04X} "
                        f"({num_patterns} × {SEQ_SHADOW_SIZE}B = {shadow_buffer_size}B)")
            logger.info(f"  Translator: ${TRANSLATE_BASE:04X} (PLAY at ${PLAY_HANDLER:04X} JMPs here)")
        logger.info(f"  INIT: ${INIT_HANDLER:04X} -> JSR ${init_addr:04X}")
        logger.info(f"  PLAY: ${PLAY_HANDLER:04X} -> JSR ${play_addr:04X}")

    def _inject_player_raw_minimal(self) -> None:
        """Stage 8 Path A: minimal embed-binary fallback for non-Laxity SIDs.

        Galway, Hubbard, NP20, etc. don't share NP21's ch_seq_ptr / pattern-
        table layout, so the Laxity-specific extraction in
        _inject_laxity_raw_np21() yields garbage for them. This method
        delivers PLAYBACK fidelity at the cost of editor-view emptiness:

          - Embed the SID's compiled player + data binary verbatim at its
            PSID load address (no patches, no ch_seq_ptr rewrites).
          - INIT handler: JSR psid_init_addr; RTS
          - PLAY handler: JSR psid_play_addr; RTS  (no JMP into criterion-3
            translator — none exists for these drivers)
          - STOP handler: silence SID volume + RTS
          - Block 5 uses the safe-params placeholder (3 tracks × 1 pattern,
            all 0x7F end markers) so SF2II's ComponentTracks ctor sees a
            non-empty data source and doesn't OOB-crash.
          - Block 3 column addresses point at high RAM ($C000+) — outside
            the embedded binary — so editor reads zeros instead of garbage.
          - Aux chain (TableText with empty names, Songs, hardware/editing
            prefs, play markers) emitted in bundled [3,2,1,4,5,END] order.

        Editor will load (track view shows 1 placeholder pattern per voice;
        instrument/wave/pulse/filter views show empty rows) and audio plays
        correctly because the original player drives the SID registers.
        """
        logger.info("Building minimal-embed SF2 (non-Laxity driver — playback only)...")
        self._minimal_path = True

        c64_data = getattr(self.data, 'c64_data', None)
        if not c64_data:
            logger.error("  No c64_data available; cannot build minimal SF2")
            return

        sid_la    = getattr(self.data, 'load_address', 0x1000)

        # Vibrants V20 cluster advisory: even files routed through the
        # driver11 minimal-embed path (player-id="Rob_Hubbard" or similar)
        # may belong to our V20 inventory clusters (Jewels/Waste/Racer
        # use the Zetrex/YP player at load $E000). Log the cluster label
        # so users know which RE notes apply.
        v20_copyright = (getattr(self.data.header, 'copyright', '')
                         if getattr(self, 'data', None) and getattr(self.data, 'header', None)
                         else '')
        if v20_copyright:
            from sidm2.vibrants_v20_detector import detect_vibrants_v20
            v20_label = detect_vibrants_v20(c64_data, sid_la, v20_copyright)
            if v20_label:
                logger.info(
                    f"  Vibrants V20 (pre-NP21) detected: {v20_label}. "
                    f"Audio plays via embedded-binary path; editor view "
                    f"stays empty by design "
                    f"(see docs/ROADMAP.md → Vibrants V20 section)."
                )
        header    = getattr(self.data, 'header', None)
        init_addr = getattr(header, 'init_address', sid_la)     if header else sid_la
        play_addr = getattr(header, 'play_address', sid_la + 3) if header else sid_la + 3

        # Sub-$1000 wrapper-collision: same as the laxity path. The
        # minimal/driver11 path also places header+handlers in
        # $0D7E-$0FFF, which a sub-$1000 binary overlaps → silent SF2.
        # Reuse the self-contained low-LOAD_BASE builder.
        if 0 < sid_la < 0x1000:
            if self._build_low_load_sf2(c64_data, sid_la, init_addr, play_addr):
                return
            # else: unfixable (no header room below sid_la) → legacy.

        # v3.5.34 high-load architectural check: same as
        # _inject_laxity_raw_np21. Binary + edit area + shadow can't
        # overflow 16-bit C64 address space. Magic_Sound (load=$F000,
        # 2613 bytes) is the canonical case for this path.
        MIN_POST_BINARY = 0x800
        if sid_la + len(c64_data) + MIN_POST_BINARY > 0x10000:
            logger.error(
                f"  Binary load address ${sid_la:04X} + size "
                f"${len(c64_data):04X} = ends at ${sid_la + len(c64_data):04X}: "
                f"insufficient room (<{MIN_POST_BINARY:#06x} bytes) below "
                f"$FFFF for the SF2 edit area. Architectural limit of the "
                f"SF2 format (Block 3 column addresses are 16-bit)."
            )
            raise errors.ConversionError(
                stage="minimal-embed inject (high-load)",
                reason=f"sid_load=${sid_la:04X} + size {len(c64_data)} leaves "
                       f"<{MIN_POST_BINARY:#06x} bytes below $FFFF for edit area",
                input_file=getattr(self.data, 'filepath', None),
                docs_link="guides/LAXITY_DRIVER_USER_GUIDE.md#troubleshooting",
            )

        LOAD_BASE      = 0x0D7E
        HANDLER_BASE   = 0x0F90
        INIT_HANDLER   = HANDLER_BASE + 0
        PLAY_HANDLER   = HANDLER_BASE + 4
        STOP_HANDLER   = HANDLER_BASE + 8

        from sidm2.sf2_header_generator import SF2HeaderGenerator
        gen = SF2HeaderGenerator(driver_size=len(c64_data) + (sid_la - LOAD_BASE))
        gen.DRIVER_INIT = INIT_HANDLER
        gen.DRIVER_PLAY = PLAY_HANDLER
        gen.DRIVER_STOP = STOP_HANDLER

        # Block 3 column addresses will be filled in below to point at a
        # zero-filled placeholder region inside the SF2 edit area (rather
        # than high-RAM $C000+ which has unpredictable emulated-memory
        # contents that can crash the editor's renderer).

        # Zero-pad gap between binary end and edit area. Some SID players
        # (Twone_Five.sid is the canonical example, v3.5.28) declare a
        # data table just before the binary's last byte and read past the
        # binary end via absolute,Y indexing. In RAM this is naturally
        # zero (uninitialized DRAM); when the SF2 edit area lands at
        # sid_la+len(c64_data) the player picks up edit-area bytes
        # (orderlist-ptr lo, hi, seq-ptr-lo etc.) instead of zeros →
        # spurious SID-register writes. 256 bytes covers the 6502
        # absolute,Y addressing range (Y ∈ [0,255]).
        POST_BINARY_GUARD = 0x100
        sf2_data_base = sid_la + len(c64_data) + POST_BINARY_GUARD

        # Build placeholder Block 5 (3 tracks × 1 pattern) + zero-filled
        # F1-F5 + Arp/Tempo/HR/Init tables. Shared with the low-load path
        # via sidm2.placeholder_edit_area. Mutates gen with table addresses
        # (gen.instr_addr / cmd_addr / wave_addr / pulse_addr / filter_addr
        # / arp_addr / tempo_addr / hr_addr / init_table_addr).
        sf2_edit_data, music_data_params = (
            placeholder_edit_area.build_placeholder_edit_area(sf2_data_base, gen))
        gen.driver_size += POST_BINARY_GUARD + len(sf2_edit_data)

        header_bytes = gen.generate_complete_headers(music_data_params)
        headers_end_addr = LOAD_BASE + len(header_bytes)
        if headers_end_addr > HANDLER_BASE:
            logger.error(f"  Headers too large! End ${headers_end_addr:04X} > ${HANDLER_BASE:04X}")
            return

        # Build full PRG: [load:2] + headers + handler stubs + c64 binary
        # + post-binary zero guard + edit area
        gap = sid_la - LOAD_BASE
        file_size = 2 + gap + len(c64_data) + POST_BINARY_GUARD + len(sf2_edit_data)
        file_data = bytearray(file_size)  # bytearray() inits to 0x00 → guard is zero-filled

        file_data[0] = LOAD_BASE & 0xFF
        file_data[1] = LOAD_BASE >> 8
        file_data[2:2 + len(header_bytes)] = header_bytes

        # Handler stubs at HANDLER_BASE
        hnd_off = 2 + (HANDLER_BASE - LOAD_BASE)
        file_data[hnd_off:hnd_off + 4]      = bytes([0x20, init_addr & 0xFF, init_addr >> 8, 0x60])
        file_data[hnd_off + 4:hnd_off + 8]  = bytes([0x20, play_addr & 0xFF, play_addr >> 8, 0x60])
        file_data[hnd_off + 8:hnd_off + 14] = bytes([0xA9, 0x00, 0x8D, 0x18, 0xD4, 0x60])

        # Embed SID binary verbatim — NO ch_seq_ptr patch
        np21_off = 2 + gap
        file_data[np21_off:np21_off + len(c64_data)] = c64_data

        # Compatibility trampoline at $1000 for SID players that hardcode
        # $1000 as INIT (e.g., zig64 cycle-accurate tracer). Only placed
        # when the SID's load address is past $1006 — otherwise the binary
        # itself occupies $1000 and a trampoline would corrupt it.
        if sid_la >= 0x1007:
            tramp_off = 2 + (0x1000 - LOAD_BASE)
            file_data[tramp_off : tramp_off + 3] = bytes([
                0x4C, init_addr & 0xFF, (init_addr >> 8) & 0xFF
            ])
            file_data[tramp_off + 3 : tramp_off + 6] = bytes([
                0x4C, play_addr & 0xFF, (play_addr >> 8) & 0xFF
            ])
            logger.info(f"  Trampoline @ $1000: JMP ${init_addr:04X}; @ $1003: JMP ${play_addr:04X}")

        # SF2 edit area appended after binary + POST_BINARY_GUARD.
        # The guard region is already zero-filled by bytearray(file_size).
        edit_off = np21_off + len(c64_data) + POST_BINARY_GUARD
        file_data[edit_off:edit_off + len(sf2_edit_data)] = sf2_edit_data

        # Upstream #211 workaround applied universally in write().
        self.output = file_data

        logger.info(f"  SF2 size: {len(self.output)} bytes")
        logger.info(f"  Magic + headers: ${LOAD_BASE:04X}-${headers_end_addr - 1:04X} ({len(header_bytes)} bytes)")
        logger.info(f"  Handlers: ${HANDLER_BASE:04X} (INIT=${INIT_HANDLER:04X}, PLAY=${PLAY_HANDLER:04X}, STOP=${STOP_HANDLER:04X})")
        logger.info(f"  Binary: ${sid_la:04X}-${sid_la + len(c64_data) - 1:04X} ({len(c64_data)} bytes)")
        logger.info(f"  Edit area: ${sf2_data_base:04X}-${sf2_data_base + len(sf2_edit_data) - 1:04X} ({len(sf2_edit_data)} bytes)")
        logger.info(f"  INIT: ${INIT_HANDLER:04X} -> JSR ${init_addr:04X}")
        logger.info(f"  PLAY: ${PLAY_HANDLER:04X} -> JSR ${play_addr:04X}")

    def _inject_silent_stub(self) -> None:
        """[REMOVED v3.5.37 — failed approach; see git history for the
        ~120 line implementation.

        Originally attempted as a fallback for SIDs whose load_addr is
        outside the embed-binary safe window: a 3KB stub with valid
        Blocks 1-9 + bare-RTS handlers + placeholder edit area, hoping
        it would be structurally close enough to the bundled "Driver 11
        Test - Arpeggio.sf2" to load.

        DOES NOT load. Action_Biker silent-stub (3KB, no embedded
        binary, identical Block 3 layout to the working bundled file)
        crashed 5/5 in production SF2II while the byte-for-byte same
        layout converted via 13KB Stinsen file passed 5/5. The crash
        was heap-state-dependent, Heisenbug-masked under the patched
        diagnostic binary.

        Method body removed because it was never called from any code
        path in the converter. If future investigation needs the layout
        setup, recover it from git history at this method's removal
        commit.
        """
        raise NotImplementedError(
            "_inject_silent_stub was removed in v3.5.37 — see docstring "
            "and git history. The approach did not work in production "
            "SF2II and was never called from any code path.")

    # ──────────────────────────────────────────────────────────────────────
    # 6502 code generators (v3.5.36 — extracted to sidm2/np21_codegen.py).
    # These wrappers delegate to module-level functions for testability.
    # Each function in np21_codegen is pure (no self.*) so the extraction
    # is purely structural. Wrapper signatures preserved for stability.
    # ──────────────────────────────────────────────────────────────────────
    def _emit_sf2_to_np21_translator(self, num_patterns, seq00_addr, shadow_base, play_addr):
        return np21_codegen.emit_sf2_to_np21_translator(
            num_patterns, seq00_addr, shadow_base, play_addr)

    def _emit_wave_split_copy_routine(self, sf2_wave_addr: int,
                                     np21_wave_data_addr: int,
                                     np21_note_addr: int,
                                     n_rows: int = 32) -> bytes:
        return np21_codegen.emit_wave_split_copy_routine(
            sf2_wave_addr, np21_wave_data_addr, np21_note_addr, n_rows)

    def _emit_filter_cutoff_only_routine(self, sf2_filter_addr: int,
                                          np21_cutoff_hi_addr: int,
                                          n_rows: int = 16) -> bytes:
        return np21_codegen.emit_filter_cutoff_only_routine(
            sf2_filter_addr, np21_cutoff_hi_addr, n_rows)

    def _emit_filter_split_copy_routine(self, sf2_filter_addr: int,
                                        np21_cmd_addr: int,
                                        np21_val_addr: int,
                                        np21_aux_addr: int,
                                        n_rows: int = 16) -> bytes:
        return np21_codegen.emit_filter_split_copy_routine(
            sf2_filter_addr, np21_cmd_addr, np21_val_addr,
            np21_aux_addr, n_rows)

    def _emit_pulse_packed_copy_routine(self, sf2_pulse_addr: int,
                                         np21_stream_addr: int,
                                         n_rows: int = 16) -> bytes:
        return np21_codegen.emit_pulse_packed_copy_routine(
            sf2_pulse_addr, np21_stream_addr, n_rows)

    def _emit_pulse_split_copy_routine(self, sf2_pulse_addr: int,
                                       np21_pulse_lo_addr: int,
                                       np21_pulse_hi_addr: int,
                                       n_rows: int = 16) -> bytes:
        return np21_codegen.emit_pulse_split_copy_routine(
            sf2_pulse_addr, np21_pulse_lo_addr, np21_pulse_hi_addr, n_rows)

    def _emit_instr_copy_routine(self, sf2_instr_addr: int, np21_instr_addr: int,
                                  n_instruments: int = 16,
                                  fields: list[tuple[int, int]] | None = None,
                                  np21_stride: int = 8) -> bytes:
        return np21_codegen.emit_instr_copy_routine(
            sf2_instr_addr, np21_instr_addr, n_instruments, fields, np21_stride)

    def _emit_pulse_copy_routine(self, sf2_pulse_addr: int, np21_pulse_addr: int,
                                  n_rows: int = 16) -> bytes:
        return np21_codegen.emit_pulse_copy_routine(
            sf2_pulse_addr, np21_pulse_addr, n_rows)

    def _emit_instr_column_copy_routine(self, sf2_instr_addr: int,
                                         np21_ad_col_addr: int,
                                         np21_sr_col_addr: int,
                                         n_instruments: int) -> bytes:
        return np21_codegen.emit_instr_column_copy_routine(
            sf2_instr_addr, np21_ad_col_addr, np21_sr_col_addr, n_instruments)

    def _emit_multipat_translator(self, voice_pat_counts, seq00_addr, shadow_base,
                                  play_addr, translate_base, table_copy_addr=None,
                                  instr_copy_addr=None, pulse_copy_addr=None,
                                  filter_copy_addr=None):
        return np21_codegen.emit_multipat_translator(
            voice_pat_counts, seq00_addr, shadow_base, play_addr,
            translate_base, table_copy_addr=table_copy_addr,
            instr_copy_addr=instr_copy_addr,
            pulse_copy_addr=pulse_copy_addr,
            filter_copy_addr=filter_copy_addr)

    def _build_np21_sf2_edit_area(self, c64_data: bytes, sid_la: int):
        """v3.5.46 wrapper around
        sidm2.np21_edit_area_builder.build_np21_sf2_edit_area.

        Pulls psid_copyright / init_addr / play_addr from self.data.header
        and forwards to the pure builder. See the module docstring for
        full semantics, return value, and the empty-pattern fallback path.
        """
        psid_copyright = ''
        init_addr = None
        play_addr = None
        if getattr(self, 'data', None) and getattr(self.data, 'header', None):
            h = self.data.header
            psid_copyright = getattr(h, 'copyright', '') or ''
            init_addr = getattr(h, 'init_address', None)
            play_addr = getattr(h, 'play_address', None)
        return np21_edit_area_builder.build_np21_sf2_edit_area(
            c64_data, sid_la,
            psid_copyright=psid_copyright,
            init_addr=init_addr,
            play_addr=play_addr,
        )

    def _inject_laxity_music_data(self) -> None:
        """v3.5.47 wrapper around
        sidm2.laxity_music_data_injector.inject_laxity_music_data.

        See the module for the per-stage patch list and address layout.
        """
        laxity_music_data_injector.inject_laxity_music_data(
            self.output, self.data)

    def _log_sf2_structure(self, label: str, data: bytes) -> None:
        sf2_diagnostics.log_sf2_structure(label, data)

    def _log_block3_structure(self, content: bytes) -> None:
        sf2_diagnostics.log_block3_structure(content)

    def _log_block5_structure(self, content: bytes) -> None:
        sf2_diagnostics.log_block5_structure(content)

    def _validate_sf2_file(self, filepath: str) -> None:
        sf2_diagnostics.validate_sf2_file(filepath)
