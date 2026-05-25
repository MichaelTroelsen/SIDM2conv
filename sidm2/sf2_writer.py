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
from . import driver11_section_injectors
from . import minimal_embed_builder
from . import laxity_raw_np21_builder

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
        """v3.5.53 wrapper around
        sidm2.driver11_section_injectors.inject_music_data_into_template.
        """
        load_address = driver11_section_injectors.inject_music_data_into_template(
            self.output, self.data, self.driver_info)
        if load_address is not None:
            self.load_address = load_address

    def _inject_sequences(self) -> None:
        """v3.5.48 wrapper around
        sidm2.driver11_section_injectors.inject_sequences."""
        driver11_section_injectors.inject_sequences(
            self.output, self.data, self.driver_info, self.load_address)

    def _inject_orderlists(self) -> None:
        """v3.5.48 wrapper around
        sidm2.driver11_section_injectors.inject_orderlists."""
        driver11_section_injectors.inject_orderlists(
            self.output, self.data, self.driver_info, self.load_address)

    def _inject_instruments(self) -> None:
        """v3.5.48 wrapper around
        sidm2.driver11_section_injectors.inject_instruments."""
        driver11_section_injectors.inject_instruments(
            self.output, self.data, self.driver_info, self.load_address)

    def _inject_wave_table(self) -> None:
        """v3.5.52 wrapper around
        sidm2.driver11_section_injectors.inject_wave_table."""
        driver11_section_injectors.inject_wave_table(
            self.output, self.data, self.driver_info, self.load_address)

    def _inject_hr_table(self) -> None:
        """v3.5.52 wrapper around
        sidm2.driver11_section_injectors.inject_hr_table."""
        driver11_section_injectors.inject_hr_table(
            self.output, self.data, self.driver_info, self.load_address)

    def _inject_pulse_table(self) -> None:
        """v3.5.52 wrapper around
        sidm2.driver11_section_injectors.inject_pulse_table."""
        driver11_section_injectors.inject_pulse_table(
            self.output, self.data, self.driver_info, self.load_address)

    def _inject_filter_table(self) -> None:
        """v3.5.52 wrapper around
        sidm2.driver11_section_injectors.inject_filter_table."""
        driver11_section_injectors.inject_filter_table(
            self.output, self.data, self.driver_info, self.load_address)

    def _inject_init_table(self) -> None:
        """v3.5.52 wrapper around
        sidm2.driver11_section_injectors.inject_init_table."""
        driver11_section_injectors.inject_init_table(
            self.output, self.data, self.driver_info, self.load_address)

    def _inject_tempo_table(self) -> None:
        """v3.5.52 wrapper around
        sidm2.driver11_section_injectors.inject_tempo_table."""
        driver11_section_injectors.inject_tempo_table(
            self.output, self.data, self.driver_info, self.load_address)

    def _inject_arp_table(self) -> None:
        """v3.5.52 wrapper around
        sidm2.driver11_section_injectors.inject_arp_table."""
        driver11_section_injectors.inject_arp_table(
            self.output, self.data, self.driver_info, self.load_address)

    def _inject_commands(self) -> None:
        """v3.5.48 wrapper around
        sidm2.driver11_section_injectors.inject_commands."""
        driver11_section_injectors.inject_commands(
            self.output, self.data, self.driver_info, self.load_address)

    def _update_table_definitions(self) -> None:
        """v3.5.49 wrapper around
        sidm2.driver11_table_helpers.update_table_dimensions.
        """
        driver11_table_helpers.update_table_dimensions(
            self.output, self.driver_info)

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
        """Inject the SF2 auxiliary data chain.

        v3.5.51: chain assembly + $0FFB pointer-injection moved to
        sidm2.sf2_aux_bodies. This wrapper handles the orchestration:
          - skip when self._skip_aux is True (low-load layout)
          - choose name extraction by path (laxity vs minimal embed)
          - delegate to sf2_aux_bodies.assemble_aux_chain
          - delegate to sf2_aux_bodies.inject_aux_chain_into_sf2
        """
        # Low-load layout: the binary spans the hardcoded aux-pointer
        # address $0FFB, so writing the pointer there corrupts live
        # player data. Skip aux entirely.
        if getattr(self, '_skip_aux', False):
            logger.info("  Skipping aux injection (low-load: $0FFB "
                        "overlaps embedded binary)")
            return
        logger.info("  Injecting auxiliary data (names)...")

        # Path A (non-Laxity SIDs): skip instrument-name extraction
        # (would call Laxity-specific extractors on a Galway/Hubbard
        # binary and return garbage). Empty names produce a clean
        # TableText that loads fine.
        if getattr(self, '_minimal_path', False):
            instrument_names = []
            command_names = []
        else:
            wave_addr, wave_entries = find_and_extract_wave_table(
                self.data.c64_data, self.data.load_address)
            laxity_instruments = extract_laxity_instruments(
                self.data.c64_data, self.data.load_address, wave_entries)
            instrument_names = [instr['name'] for instr in laxity_instruments]
            command_names = get_command_names()

        instr_table_id = 1
        cmd_table_id = 0
        if 'Instruments' in self.driver_info.table_addresses:
            instr_table_id = self.driver_info.table_addresses['Instruments']['id']
        if 'Commands' in self.driver_info.table_addresses:
            cmd_table_id = self.driver_info.table_addresses['Commands']['id']

        # Build the two converter-derived bodies + assemble the chain.
        table_text = sf2_aux_bodies.build_table_text_data(
            instrument_names, command_names, instr_table_id, cmd_table_id)
        desc_body = sf2_aux_bodies.build_description_data(
            self.data.header.name if (hasattr(self.data, 'header')
                                       and self.data.header) else None)
        aux_chain = sf2_aux_bodies.assemble_aux_chain(table_text, desc_body)

        aux_addr = sf2_aux_bodies.inject_aux_chain_into_sf2(
            self.output, aux_chain)
        if aux_addr is not None:
            logger.info(f"    Aux chain @ ${aux_addr:04X} "
                        f"({len(aux_chain)}B, [3,2,1,4,5,END] bundled order)")
            if hasattr(self.data, 'header') and self.data.header:
                logger.info(f"    Written metadata: {self.data.header.name} "
                            f"by {self.data.header.author}")
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
        """v3.5.53 wrapper around
        sidm2.driver11_section_injectors.print_extraction_summary.
        """
        driver11_section_injectors.print_extraction_summary(self.data)

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
        """v3.5.54 wrapper around
        sidm2.laxity_raw_np21_builder.build_laxity_raw_np21_sf2.

        Builds the raw-NP21 SF2 (the Stinsen/Unboxed laxity path).
        See the module docstring for the full architecture writeup.
        """
        result = laxity_raw_np21_builder.build_laxity_raw_np21_sf2(self.data)
        if result is None:
            return
        self.output = bytearray(result.sf2_bytes)
        self._ch_seq_patches = result.ch_seq_patches
        self._ch_seq_patch_layout = result.ch_seq_patch_layout
        self._np21_file_off = result.np21_file_off
        self._wave_copy_jsr_offs = result.wave_copy_jsr_offs
        if result.skip_aux:
            self._skip_aux = True

    def _inject_player_raw_minimal(self) -> None:
        """v3.5.50 wrapper around
        sidm2.minimal_embed_builder.build_minimal_embed_sf2.

        See the module docstring for the full Stage 8 Path A semantics
        (non-Laxity playback-fidelity-only layout, low-load fallback,
        high-load architectural error).
        """
        self._minimal_path = True
        c64_data = getattr(self.data, 'c64_data', None)
        sid_la = getattr(self.data, 'load_address', 0x1000)
        header = getattr(self.data, 'header', None)
        init_addr = getattr(header, 'init_address', sid_la) if header else sid_la
        play_addr = getattr(header, 'play_address', sid_la + 3) if header else sid_la + 3
        psid_copyright = (getattr(header, 'copyright', '') or '') if header else ''
        psid_filepath = getattr(self.data, 'filepath', None)
        result = minimal_embed_builder.build_minimal_embed_sf2(
            c64_data, sid_la, init_addr, play_addr,
            psid_copyright=psid_copyright,
            psid_filepath=psid_filepath,
        )
        if result is not None:
            self.output = bytearray(result.sf2_bytes)
            if result.skip_aux:
                self._skip_aux = True

    # `_inject_silent_stub` was a NotImplementedError stub kept since
    # v3.5.37 as documentation for a failed approach (3KB silent SF2
    # for unsafe load_addr files — never loaded in production SF2II).
    # Removed at v3.5.53: zero callers, no external references, docs
    # still pinned in CHANGELOG / STORY / git history at the removal
    # commit. If future investigation needs the layout setup, recover
    # from `git show <v3.5.37>^:sidm2/sf2_writer.py | grep -A 120 _inject_silent_stub`.

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
