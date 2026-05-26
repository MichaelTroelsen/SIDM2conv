"""High-load SF2 layout — for binaries that load near $F000 with insufficient
post-binary space for the SF2 edit area.

Added at the v3.5.55 refactor. Mirror image of `low_load_layout.py`:

# The problem

The normal SF2 PRG layout looks like:

    [$0D7E header][$0F90 handlers][$1000 binary]...[edit area past binary]

For binaries that load near `$F000` and have only a few hundred bytes
between binary-end and `$FFFF`, the edit area doesn't fit AFTER the
binary. Crosswords ($F000, 3363B) has only 733 bytes post-binary;
Magic_Sound ($F000, 2613B) has only 1483 bytes — both under the
~$800 minimum needed for the SF2 edit area + Block 3 tables.

Pre-v3.5.55 these files raised `errors.ConversionError(stage="...
inject (high-load)")` and produced no SF2 output.

# The fix

There's TONS of free space BEFORE the binary: the gap between the
handler region ($0FA0) and the binary ($F000) is ~57KB. The edit
area can go there:

    [$0D7E header][$0F90 handlers][$1000 edit area][zero pad][$F000 binary]

Block 3 column addresses point at $1000+ instead of high RAM. SF2II
doesn't care WHERE the edit area lives in 16-bit address space — it
just reads bytes at the configured addresses. The 16-bit overflow
concern from v3.5.34 was based on the assumption that edit area must
follow the binary; lifting that assumption makes the file fit.

# What this doesn't fix

Echo_Beat ($0400) — its binary loads BELOW the SF2 wrapper at $0D7E.
No layout can rescue that; it's a genuine architectural infeasibility.

# Public API

  build_high_load_sf2(c64_data, sid_la, init_addr, play_addr)
      -> Optional[Tuple[bytes, bool]]

Returns `(sf2_bytes, skip_aux=False)` on success, None when the file
would exceed 64K or the layout doesn't apply (sid_la too low to need
this path).
"""
from __future__ import annotations
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


# Trigger threshold: this layout is needed when there are fewer than
# `MIN_POST_BINARY` bytes between binary-end and $FFFF for the SF2 edit
# area. Matches the threshold used by minimal_embed_builder /
# laxity_raw_np21_builder for the architectural-error gate.
MIN_POST_BINARY = 0x800

# Fixed SF2 file constants — match the normal-path layout.
LOAD_BASE       = 0x0D7E
HANDLER_BASE    = 0x0F90
INIT_HANDLER    = HANDLER_BASE + 0
PLAY_HANDLER    = HANDLER_BASE + 4
STOP_HANDLER    = HANDLER_BASE + 8
BAIT_ADDR       = HANDLER_BASE + 14    # #211 scan bait stub
EDIT_AREA_BASE  = 0x1000               # SF2 edit area starts at $1000
                                        # (well before any high-load binary)


def build_high_load_sf2(
    c64_data: bytes,
    sid_la: int,
    init_addr: int,
    play_addr: int,
) -> Optional[Tuple[bytes, bool]]:
    """Build an SF2 file using the high-load layout.

    Args:
        c64_data: The embedded SID binary bytes.
        sid_la: The binary's PSID load address. Must be high enough
            that the binary doesn't overlap the edit area at $1000+
            (typically $E000+ in practice).
        init_addr: The player's INIT entry point.
        play_addr: The player's PLAY entry point.

    Returns:
        `(sf2_bytes, skip_aux=False)` on success.
        `None` when:
          - sid_la is too low for this layout (binary would overlap
            edit area at $1000)
          - PRG file size would exceed 64K
    """
    from sidm2.sf2_header_generator import SF2HeaderGenerator
    from sidm2 import placeholder_edit_area

    clen = len(c64_data)

    # Sanity: this layout only applies when binary loads near the top
    # of memory. Require sid_la to be past where the edit area + some
    # margin would land. The edit area is ~1414 bytes (placeholder),
    # starting at $1000 — so binary must start past $2000 at minimum.
    if sid_la < 0x2000:
        logger.debug(
            f"  High-load: sid_la ${sid_la:04X} too low for this layout "
            f"(needs >= $2000 to clear the edit area at $1000)")
        return None

    # Build the SF2 header generator with handlers pointing at HANDLER_BASE.
    # `driver_size` is the span from LOAD_BASE through the END of the
    # placeholder edit area — SF2II uses this to bound its parser walks.
    gen = SF2HeaderGenerator(driver_size=EDIT_AREA_BASE - LOAD_BASE)
    gen.DRIVER_INIT = INIT_HANDLER
    gen.DRIVER_PLAY = PLAY_HANDLER
    gen.DRIVER_STOP = STOP_HANDLER

    # Point SF2II's #211 SID-write scan window at our handler+bait
    # region (binary at $F000+ is too far away for the default scan).
    # The bait stub at HANDLER_BASE + 14 makes the static `STA
    # $D400,X; RTS` opcode visible.
    gen.driver_code_top  = HANDLER_BASE
    gen.driver_code_size = 0x20

    # Build placeholder Block 5 + zero-filled F1-F5 tables in the edit
    # area at $1000. The placeholder builder mutates gen with all
    # table addresses (instr_addr / cmd_addr / wave_addr / etc.).
    sf2_edit_data, music_data_params = (
        placeholder_edit_area.build_placeholder_edit_area(
            EDIT_AREA_BASE, gen))
    gen.driver_size = (EDIT_AREA_BASE - LOAD_BASE) + len(sf2_edit_data)

    header_bytes = gen.generate_complete_headers(music_data_params)
    headers_end = LOAD_BASE + len(header_bytes)
    if headers_end > HANDLER_BASE:
        logger.error(
            f"  High-load: headers extend past HANDLER_BASE "
            f"(${headers_end:04X} > ${HANDLER_BASE:04X})")
        return None

    edit_end = EDIT_AREA_BASE + len(sf2_edit_data)
    if edit_end > sid_la:
        logger.debug(
            f"  High-load: edit area end ${edit_end:04X} would overlap "
            f"binary at ${sid_la:04X}")
        return None

    # File span: from LOAD_BASE through the end of the embedded binary
    # at sid_la + clen - 1. File size = 2 (PRG load) + binary_end - LOAD_BASE.
    file_size = 2 + (sid_la + clen - LOAD_BASE)
    if file_size > 0x10000:
        logger.info(
            f"  High-load: file size {file_size} > 64K; cannot fix")
        return None

    fd = bytearray(file_size)
    fd[0] = LOAD_BASE & 0xFF
    fd[1] = LOAD_BASE >> 8

    # Headers at LOAD_BASE+2 through HANDLER_BASE
    fd[2:2 + len(header_bytes)] = header_bytes

    # Handlers at HANDLER_BASE (file offset = 2 + HANDLER_BASE - LOAD_BASE)
    hnd_off = 2 + HANDLER_BASE - LOAD_BASE
    fd[hnd_off:hnd_off + 4]     = bytes([
        0x20, init_addr & 0xFF, init_addr >> 8, 0x60])   # JSR init; RTS
    fd[hnd_off + 4:hnd_off + 8] = bytes([
        0x20, play_addr & 0xFF, play_addr >> 8, 0x60])   # JSR play; RTS
    fd[hnd_off + 8:hnd_off + 14] = bytes([
        0xA9, 0x00, 0x8D, 0x18, 0xD4, 0x60])             # STOP: silence

    # #211 scan bait at HANDLER_BASE + 14 (after stop handler):
    # STA $D400,X; RTS — SF2II's static sweep decodes this and finds
    # the ABX $D40x write it needs to avoid the driver_utils.cpp:419 crash.
    bait_off = 2 + BAIT_ADDR - LOAD_BASE
    fd[bait_off:bait_off + 4] = bytes([0x9D, 0x00, 0xD4, 0x60])

    # Edit area at $1000. Block 3 column addresses already point here
    # because placeholder_edit_area set them up that way.
    edit_off = 2 + EDIT_AREA_BASE - LOAD_BASE
    fd[edit_off:edit_off + len(sf2_edit_data)] = sf2_edit_data

    # Embedded binary at sid_la. The gap between edit_end and sid_la
    # is zero-filled by bytearray(file_size).
    bin_off = 2 + sid_la - LOAD_BASE
    fd[bin_off:bin_off + clen] = bytes(c64_data)

    logger.info(
        f"  High-load layout: header=${LOAD_BASE:04X}-${headers_end - 1:04X} "
        f"handlers=${HANDLER_BASE:04X}-${BAIT_ADDR + 3:04X} "
        f"edit=${EDIT_AREA_BASE:04X}-${edit_end - 1:04X} "
        f"binary=${sid_la:04X}-${sid_la + clen - 1:04X} "
        f"file_size={file_size}")

    # skip_aux=True: the high-load layout uses a placeholder edit area
    # (no real F1-F5 data, no per-instrument names). Including the aux
    # chain would just pad the file with empty TableText entries and
    # could push it past 64K (Crosswords v3.5.57 fix — the 779-byte
    # aux chain was overflowing past $FFFF for binaries ending near
    # $FD22, panicking zig64's tracer at "index out of bounds" even
    # though SF2II loaded the file fine). The META trailer at file
    # end is still appended (carries title/author/copyright for SID
    # round-trip recovery via sf2_to_sid.py).
    return bytes(fd), True
