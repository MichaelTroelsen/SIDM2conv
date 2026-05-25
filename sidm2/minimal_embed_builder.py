"""Minimal-embed SF2 builder for non-Laxity SIDs.

Extracted from sf2_writer.py at the v3.5.50 Phase 15 refactor.

# What this builds

Stage 8 Path A: a fallback SF2 layout for SIDs whose player isn't the
NP21 family (Galway, Hubbard, NP20, etc.). Those don't share Laxity's
ch_seq_ptr / pattern-table layout, so the laxity raw-NP21 path would
extract garbage. The minimal-embed path delivers PLAYBACK fidelity at
the cost of editor-view emptiness:

  - Embed the SID's compiled player + data binary verbatim at its
    PSID load address (no patches, no ch_seq_ptr rewrites).
  - INIT handler: JSR psid_init_addr; RTS
  - PLAY handler: JSR psid_play_addr; RTS  (no JMP into criterion-3
    translator — none exists for these drivers)
  - STOP handler: silence SID volume + RTS
  - Block 5 uses the safe-params placeholder (3 tracks x 1 pattern,
    all 0x7F end markers) so SF2II's ComponentTracks ctor sees a
    non-empty data source and doesn't OOB-crash.
  - Block 3 column addresses point inside the SF2 edit area (zero-
    filled placeholder regions) rather than high-RAM $C000+ which
    has unpredictable emulated-memory contents.
  - 256-byte POST_BINARY_GUARD between binary end and edit area
    (Twone_Five.sid v3.5.28 fix — players reading past binary end
    via abs,Y indexing get RAM-zero instead of edit-area bytes).
  - Compatibility trampoline at $1000 (JMP init / JMP play) for
    SID players that hardcode $1000 as INIT (e.g., zig64 cycle-
    accurate tracer). Only placed when sid_la >= $1007.

Editor will load (track view shows 1 placeholder pattern per voice;
instrument/wave/pulse/filter views show empty rows) and audio plays
correctly because the original player drives the SID registers.

# Sub-$1000 fallback

If `sid_la < 0x1000`, the binary overlaps the wrapper at $0F90. The
function delegates to `low_load_layout.build_low_load_sf2` which uses
an alternate PRG layout with the header placed BELOW the binary. That
path also sets `skip_aux=True` because the binary spans $0FFB (the
hardcoded aux-pointer address).

# High-load architectural error

If `sid_la + len(c64_data) + 0x800 > 0x10000`, there's insufficient
room below $FFFF for the SF2 edit area (Block 3 column addresses are
16-bit). Magic_Sound and Crosswords ($F000 load, 2-3KB) hit this. The
function raises `errors.ConversionError` with a diagnostic message.

# API

  build_minimal_embed_sf2(c64_data, sid_la, init_addr, play_addr, *,
                          psid_copyright='', psid_filepath=None)
      -> MinimalEmbedResult

A small dataclass result type carrying the SF2 bytes plus the
`skip_aux` flag needed by the caller (True for low-load paths, False
otherwise). Returns None if the function fails fatally (empty
c64_data, or a low-load layout that doesn't fit).
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional

from . import errors
from . import placeholder_edit_area
from . import low_load_layout

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MinimalEmbedResult:
    """Return type of build_minimal_embed_sf2.

    Attributes:
        sf2_bytes: The complete SF2 file content (bytes).
        skip_aux: Whether the caller MUST skip aux-chain injection.
            True for low-load layouts (the binary spans $0FFB, the
            hardcoded aux-pointer address); False for normal layouts.
    """
    sf2_bytes: bytes
    skip_aux: bool


def build_minimal_embed_sf2(
    c64_data: bytes,
    sid_la: int,
    init_addr: int,
    play_addr: int,
    *,
    psid_copyright: str = '',
    psid_filepath: Optional[str] = None,
) -> Optional[MinimalEmbedResult]:
    """Build a minimal-embed SF2 file for a non-Laxity SID.

    Args:
        c64_data: The SID's compiled player + data binary.
        sid_la: The binary's PSID load address.
        init_addr: PSID init address. Typically `sid_la` or close to it.
        play_addr: PSID play address.
        psid_copyright: For Vibrants V20 cluster advisory logging.
            Empty string skips the detector.
        psid_filepath: Source SID path, attached to ConversionError
            if the high-load architectural check fails.

    Returns:
        MinimalEmbedResult on success; None if c64_data is empty or
        the low-load fallback returns no fit.

    Raises:
        errors.ConversionError: when the high-load check fails (no
            room for SF2 edit area below $FFFF).
    """
    if not c64_data:
        logger.error("  No c64_data available; cannot build minimal SF2")
        return None

    logger.info("Building minimal-embed SF2 (non-Laxity driver — playback only)...")

    # Vibrants V20 cluster advisory: even files routed through the
    # driver11 minimal-embed path (player-id="Rob_Hubbard" or similar)
    # may belong to our V20 inventory clusters (Jewels/Waste/Racer
    # use the Zetrex/YP player at load $E000). Log the cluster label
    # so users know which RE notes apply.
    if psid_copyright:
        from sidm2.vibrants_v20_detector import detect_vibrants_v20
        v20_label = detect_vibrants_v20(c64_data, sid_la, psid_copyright)
        if v20_label:
            logger.info(
                f"  Vibrants V20 (pre-NP21) detected: {v20_label}. "
                f"Audio plays via embedded-binary path; editor view "
                f"stays empty by design "
                f"(see docs/ROADMAP.md → Vibrants V20 section)."
            )

    # Sub-$1000 wrapper-collision: the minimal/driver11 path places
    # header+handlers in $0D7E-$0FFF, which a sub-$1000 binary overlaps
    # → silent SF2. Reuse the low-load builder.
    if 0 < sid_la < 0x1000:
        ll_result = low_load_layout.build_low_load_sf2(
            c64_data, sid_la, init_addr, play_addr)
        if ll_result is not None:
            sf2_bytes, skip_aux = ll_result
            return MinimalEmbedResult(sf2_bytes=sf2_bytes, skip_aux=skip_aux)
        return None    # unfixable (no header room below sid_la)

    # v3.5.34 high-load architectural check: same as _inject_laxity_raw_np21.
    # Binary + edit area + shadow can't overflow 16-bit C64 address space.
    # Magic_Sound (load=$F000, 2613 bytes) is the canonical case for this path.
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
            input_file=psid_filepath,
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
    # zero-filled placeholder region inside the SF2 edit area.

    # Zero-pad gap between binary end and edit area (Twone_Five.sid
    # v3.5.28 fix — players reading past binary end via absolute,Y
    # indexing get RAM-zero instead of edit-area bytes). 256 bytes
    # covers the 6502 absolute,Y addressing range (Y in [0,255]).
    POST_BINARY_GUARD = 0x100
    sf2_data_base = sid_la + len(c64_data) + POST_BINARY_GUARD

    # Build placeholder Block 5 (3 tracks x 1 pattern) + zero-filled
    # F1-F5 + Arp/Tempo/HR/Init tables. Shared with the low-load path.
    sf2_edit_data, music_data_params = (
        placeholder_edit_area.build_placeholder_edit_area(sf2_data_base, gen))
    gen.driver_size += POST_BINARY_GUARD + len(sf2_edit_data)

    header_bytes = gen.generate_complete_headers(music_data_params)
    headers_end_addr = LOAD_BASE + len(header_bytes)
    if headers_end_addr > HANDLER_BASE:
        logger.error(f"  Headers too large! End ${headers_end_addr:04X} > ${HANDLER_BASE:04X}")
        return None

    # Build full PRG: [load:2] + headers + handler stubs + c64 binary
    # + post-binary zero guard + edit area
    gap = sid_la - LOAD_BASE
    file_size = 2 + gap + len(c64_data) + POST_BINARY_GUARD + len(sf2_edit_data)
    file_data = bytearray(file_size)   # bytearray() inits to 0x00 → guard is zero-filled

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

    logger.info(f"  SF2 size: {len(file_data)} bytes")
    logger.info(f"  Magic + headers: ${LOAD_BASE:04X}-${headers_end_addr - 1:04X} ({len(header_bytes)} bytes)")
    logger.info(f"  Handlers: ${HANDLER_BASE:04X} (INIT=${INIT_HANDLER:04X}, PLAY=${PLAY_HANDLER:04X}, STOP=${STOP_HANDLER:04X})")
    logger.info(f"  Binary: ${sid_la:04X}-${sid_la + len(c64_data) - 1:04X} ({len(c64_data)} bytes)")
    logger.info(f"  Edit area: ${sf2_data_base:04X}-${sf2_data_base + len(sf2_edit_data) - 1:04X} ({len(sf2_edit_data)} bytes)")
    logger.info(f"  INIT: ${INIT_HANDLER:04X} -> JSR ${init_addr:04X}")
    logger.info(f"  PLAY: ${PLAY_HANDLER:04X} -> JSR ${play_addr:04X}")

    return MinimalEmbedResult(sf2_bytes=bytes(file_data), skip_aux=False)
