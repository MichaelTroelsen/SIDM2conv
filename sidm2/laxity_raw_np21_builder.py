"""Build a raw-NP21-embedded SF2 file (the Stinsen/Unboxed laxity path).

Extracted from sf2_writer.py at the v3.5.54 Phase 19 refactor.

The single biggest extraction of the entire decomposition project
(940 lines) — but interestingly NOT the hardest. AST analysis after
Phases 1-18 surfaced that of the 16 unique `self.*` references this
method had, 10 were calls to wrapper methods that already routed
into extracted modules (np21_codegen, low_load_layout,
np21_edit_area_builder). The actual class-bound state surface was
the 5 attr writes:

  - self.output                  → bytearray (the SF2 file bytes)
  - self._ch_seq_patches         → list of (offset, byte) tuples
  - self._ch_seq_patch_layout    → (lo_off, hi_off) tuple or None
  - self._np21_file_off          → int (offset of binary inside SF2)
  - self._wave_copy_jsr_offs     → list of int (JSR offsets for gate)

After parameterising those + replacing 10 self-method-call sites with
direct module-function calls, the function became a pure
`(data) → Optional[LaxityRawNp21Result]` builder. The result dataclass
carries all 5 pieces of state for SF2Writer to attach to itself.

# What this builds

The raw-NP21 SF2 layout for Stinsen-class binaries:

  - Embed the song's own NP21 binary verbatim at sid_la ($1000+).
  - Build the SF2 edit area past the binary (delegated to
    np21_edit_area_builder).
  - Append the 87-byte multi-pattern translator at $0F9E (delegated
    to np21_codegen.emit_multipat_translator).
  - Patch ch_seq_ptr at $0A1C/$0A1F (or the autodetected location)
    to point at shadow-buffer slots that the runtime translator
    pre-fills on each PLAY tick.
  - Emit Driver-11-format copy routines for the Stinsen/Beast/Angular
    instrument/wave/pulse/filter tables (the F2-F5 edit propagation
    plumbing — also delegated to np21_codegen).
  - Apply sub-$1000 low-load fallback via low_load_layout when needed.

# Why the C2 reference suite is the regression guard

This function exists in two patterns based on Phase 11's lesson —
synthetic test fixtures for a function this entangled with NP21 binary
layout + variant detectors + audio gate semantics would be a
months-long project. The 14-file C2 reference regression suite
verifies every byte of the SF2 output against pre-recorded byte
sequences known to round-trip via zig64 to byte-identical playback.
Any drift in this function fails the suite immediately.
"""
from __future__ import annotations
import logging
import struct
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from . import errors
from . import np21_codegen
from . import low_load_layout
from . import high_load_layout
from . import np21_edit_area_builder
from .table_extraction import extract_all_laxity_tables

logger = logging.getLogger(__name__)


@dataclass
class LaxityRawNp21Result:
    """Return type of build_laxity_raw_np21_sf2.

    Attributes:
        sf2_bytes: The complete SF2 file content.
        ch_seq_patches: List of (offset, original_byte) tuples — the
            ch_seq_ptr patches applied to the binary. Used by the
            audio gate at write-time to revert if the patch breaks
            audio.
        ch_seq_patch_layout: Optional (lo_off, hi_off) tuple — the
            file offsets where ch_seq_ptr_lo / ch_seq_ptr_hi live
            (different per variant after autodetect). None if no
            ch_seq_ptr patches were applied.
        np21_file_off: The file offset where the embedded NP21 binary
            starts. Used by the audio gate when re-tracing the SF2.
        wave_copy_jsr_offs: List of file offsets where wave-copy JSRs
            were emitted. Used by the audio gate to NOP them as a
            secondary revert strategy.
        skip_aux: True when the low-load fallback was used (binary
            spans $0FFB so aux injection must be skipped).
    """
    sf2_bytes: bytes
    ch_seq_patches: List[Tuple[int, int]] = field(default_factory=list)
    ch_seq_patch_layout: Optional[Tuple[int, int]] = None
    np21_file_off: int = 0
    wave_copy_jsr_offs: List[int] = field(default_factory=list)
    skip_aux: bool = False


def build_laxity_raw_np21_sf2(data) -> Optional[LaxityRawNp21Result]:
    """Build the raw-NP21 SF2 file for a laxity-class SID.

    See module docstring for the full architecture writeup.

    Args:
        data: ExtractedData providing c64_data, load_address, header,
            and the various NP21 binary fields needed to identify
            ch_seq_ptr / Wizax-A / Zetrex-YP / Vibrants V20 layouts.

    Returns:
        LaxityRawNp21Result with the SF2 bytes + the 5 state values
        the caller needs to attach to SF2Writer for audio-gate
        consumption. None if c64_data is missing.
    """
    # Initialize the 5 mutated state values that will be returned.
    output: bytearray = bytearray()
    ch_seq_patches: List[Tuple[int, int]] = []
    ch_seq_patch_layout: Optional[Tuple[int, int]] = None
    np21_file_off: int = 0
    wave_copy_jsr_offs: List[int] = []
    skip_aux: bool = False

    logger.info("Building raw-NP21 SF2 (verbatim player embedding, valid SF2 headers)...")

    c64_data = getattr(data, 'c64_data', None)
    if not c64_data:
        logger.error("  No c64_data available; cannot build raw NP21 SF2")
        return None

    sid_la    = getattr(data, 'load_address', 0x1000)
    header    = getattr(data, 'header', None)
    init_addr = getattr(header, 'init_address', sid_la)     if header else sid_la
    play_addr = getattr(header, 'play_address', sid_la + 3) if header else sid_la + 3

    # Sub-$1000 wrapper-collision cluster: binaries loading below
    # $1000 overlap the normal SF2 wrapper ($0D7E header + $0F90
    # handlers + $0F9E translator) in the single contiguous PRG, so
    # the normal layout aborts ("Translator overflow") → silent SF2.
    # Use an alternate low-LOAD_BASE layout: header BELOW the binary,
    # handlers AFTER it. See memory/sub-1000-cluster-design.md.
    if 0 < sid_la < 0x1000:
        psid_copyright = (getattr(header, 'copyright', '') or '') if header else ''
        ll_result = low_load_layout.build_low_load_sf2(
            c64_data, sid_la, init_addr, play_addr,
            psid_copyright=psid_copyright)
        if ll_result is not None:
            ll_bytes, ll_skip_aux = ll_result
            return LaxityRawNp21Result(
                sf2_bytes=ll_bytes, skip_aux=ll_skip_aux)
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
            input_file=getattr(data, 'filepath', None),
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
    # v3.5.55: try the high-load alternate layout BEFORE raising the
    # architectural error. The alternate layout places the SF2 edit area
    # BEFORE the binary (in the 50+ KB gap between handlers at $0FA0 and
    # binary at $F000+), giving Crosswords and Magic_Sound a working
    # SF2 output instead of the previous CONV_FAIL. Editor view is the
    # placeholder (no F1-F5 edit propagation for these files) but audio
    # plays correctly via the embedded binary.
    MIN_POST_BINARY = 0x800
    if sid_la + len(c64_data) + MIN_POST_BINARY > 0x10000:
        hl_result = high_load_layout.build_high_load_sf2(
            c64_data, sid_la, init_addr, play_addr)
        if hl_result is not None:
            hl_bytes, hl_skip_aux = hl_result
            # np21_file_off: where the embedded binary starts in the file.
            # The audio gate uses this to re-trace the SF2.
            file_np21_off = 2 + sid_la - 0x0D7E   # LOAD_BASE = $0D7E
            return LaxityRawNp21Result(
                sf2_bytes=hl_bytes,
                np21_file_off=file_np21_off,
                skip_aux=hl_skip_aux,
            )
        logger.error(
            f"  Binary load address ${sid_la:04X} + size "
            f"${len(c64_data):04X} = ends at ${sid_la + len(c64_data):04X}: "
            f"insufficient room (<{MIN_POST_BINARY:#06x} bytes) below "
            f"$FFFF for the SF2 edit area + shadow buffer, and the "
            f"high-load alternate layout doesn't fit either."
        )
        raise errors.ConversionError(
            stage="raw-NP21 inject (high-load)",
            reason=f"sid_load=${sid_la:04X} + size {len(c64_data)} doesn't "
                   f"fit either the normal or high-load layouts",
            input_file=getattr(data, 'filepath', None),
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
    except (ValueError, IndexError, KeyError, struct.error) as e:
        # Catch only data-format problems from the binary-parsing path;
        # let NameError / ImportError / AttributeError propagate so
        # structural bugs (like the v3.5.54 missing-import regression
        # this except block silently swallowed for 9 releases — see
        # memory/v3.5.63-import-fix.md) surface immediately at the
        # first conversion rather than masquerading as a benign
        # "falling back to defaults" warning.
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
        return None

    # --- Extract NP21 patterns and build SF2 edit data area ---
    # Returns voice_init_idx so we can compute per-voice shadow slots,
    # raw_patterns (original NP21 sequence bytes for shadow pre-fill),
    # and voice_pat_counts (Stage 2.5: feeds the multi-pattern translator).
    music_data_params, sf2_edit_data, voice_init_idx, raw_patterns, voice_pat_counts = \
        np21_edit_area_builder.build_np21_sf2_edit_area(
            c64_data, sid_la,
            psid_copyright=(getattr(data.header, 'copyright', '') or '') if data.header else '',
            init_addr=getattr(data.header, 'init_address', None) if data.header else None,
            play_addr=getattr(data.header, 'play_address', None) if data.header else None,
        )

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
        wave_routine = np21_codegen.emit_wave_split_copy_routine(
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
            instr_routine = np21_codegen.emit_instr_column_copy_routine(
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
            instr_routine = np21_codegen.emit_instr_copy_routine(
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
            instr_routine = np21_codegen.emit_instr_copy_routine(
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
            pulse_routine = np21_codegen.emit_pulse_split_copy_routine(
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
            pulse_routine = np21_codegen.emit_pulse_packed_copy_routine(
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
            pulse_routine = np21_codegen.emit_pulse_packed_copy_routine(
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
            filter_routine = np21_codegen.emit_filter_split_copy_routine(
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
            filter_routine = np21_codegen.emit_filter_cutoff_only_routine(
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
            filter_routine = np21_codegen.emit_filter_cutoff_only_routine(
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
        cpyr = getattr(getattr(data, 'header', None),
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
                # v3.5.65: replaced two stray `self.data` references the
                # v3.5.54 refactor missed. `data` is a function parameter
                # here, not an instance attribute. Pyflakes caught these
                # as undefined names; the bare `except Exception` below
                # had been silently swallowing the NameError, causing
                # the ch_seq_ptr safety gate to never run.
                if getattr(data, 'header', None) is not None:
                    init_addr_for_gate = getattr(
                        data.header, 'init_address', sid_la)
                    play_addr_for_gate = getattr(
                        data.header, 'play_address', sid_la + 3)
                else:
                    init_addr_for_gate = sid_la
                    play_addr_for_gate = sid_la + 3
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
    ch_seq_patches = ch_seq_patches
    ch_seq_patch_layout = patch_layout_name  # for log messages

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
        return None

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
    np21_file_off = np21_off

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
        translator_bytes = np21_codegen.emit_multipat_translator(
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
            return None
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
        wave_copy_jsr_offs = jsr_lo_off

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
    output = file_data

    logger.info(f"  SF2 size: {len(output)} bytes")
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

    return LaxityRawNp21Result(sf2_bytes=bytes(output), ch_seq_patches=ch_seq_patches, ch_seq_patch_layout=ch_seq_patch_layout, np21_file_off=np21_file_off, wave_copy_jsr_offs=wave_copy_jsr_offs, skip_aux=skip_aux)
