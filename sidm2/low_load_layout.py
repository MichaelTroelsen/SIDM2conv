"""Low-load SF2 layout — alternate PRG layout for binaries that load below $1000.

Extracted from sf2_writer.py at the v3.5.38 Phase 4 refactor.

# The problem

The normal SF2 PRG layout looks like this:

    [$0D7E header][$0F90 handlers][$0F9E translator][$1000 binary]...

But several Laxity-era SIDs load BELOW $1000 — e.g. $0F00, $0900, $0800,
even $0400. Their embedded binary would overlap the wrapper at $0F90
and silently corrupt either the player or the SF2 header. The converter
used to abort with "Translator overflow" → silent SF2 (C2=DIFF(*v0),
C1 crash). 7 files in 286-corpus.

# The fix (v3.5.20 series)

Move the header BELOW the binary and put minimal handlers AFTER it.
SF2II is fully TopAddress-relative (see driver_info.cpp:
`block_address = m_TopAddress + 2`; no lower bound on `m_TopAddress`),
so a low TopAddress parses fine.

    [LOAD_BASE header][binary at sid_la][HI handlers + bait + edit area]

No translator, no edit-area builds, no F1-F5 propagation (these files
have no working C3 anyway). Track view uses the same safe placeholder
as the minimal-embed path so SF2II's ComponentTracks constructor
doesn't OOB-crash on an empty editor view.

# The constraints

  - LOAD_BASE floor is $0500 (keeps the header clear of zeropage
    $00-$FF, stack $0100-$01FF, and the BASIC/KERNAL vector+buffer
    region $0200-$04FF — verified by py65 read-before-write analysis
    in `pyscript/find_rbw_scratch.py`).
  - $0500-$08FF is default C64 screen RAM but SF2II's player emulation
    never drives VIC, so it's free except where the embedded player
    has its own scratch. Laxity-class players either zero scratch at
    INIT before reading, or don't touch it at all in the header span.
  - File size must stay below 64K (16-bit address limit).
  - SF2II's #211 SID-write scan window is repointed at the handler+bait
    region (binary at $1000 has no usable stamp slot for low-load).
  - Aux-chain pointer at $0FFB is HARDCODED in driver_info.h; for
    low-load files the binary spans $0FFB so we MUST NOT write the
    pointer there. Caller is expected to honor `skip_aux=True`.

# Outputs

`build_low_load_sf2(...)` returns either:
  - `(bytes, skip_aux=True)` — the complete SF2 file
  - `None` — no room for the header below sid_la (caller falls back
    to legacy layout, which will raise its own architectural error)
"""
from __future__ import annotations
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def build_low_load_sf2(
    c64_data: bytes,
    sid_la: int,
    init_addr: int,
    play_addr: int,
) -> Optional[Tuple[bytes, bool]]:
    """Build an SF2 file using the low-load layout.

    Args:
        c64_data: The embedded NP21 binary bytes (verbatim).
        sid_la: The binary's native load address (must be < $1000).
        init_addr: The player's INIT entry point.
        play_addr: The player's PLAY entry point.

    Returns:
        (sf2_bytes, skip_aux) if the layout fits; None if the header
        won't fit below sid_la or the file would exceed 64K.

        The caller should:
          - assign sf2_bytes to self.output
          - set self._skip_aux = skip_aux (True for low-load — see
            the $0FFB aux-pointer note in the module docstring)
    """
    # Import inside the function to avoid a module-load cycle; SF2HeaderGenerator
    # is a sibling module that also imports from this package.
    from sidm2.sf2_header_generator import SF2HeaderGenerator

    OL_SIZE, SEQ_SIZE, SEQ_PTR_SIZE = 0x100, 0x100, 0x80
    clen = len(c64_data)

    # Handlers + edit-area placeholder go AFTER the binary, page-aligned.
    HI = (sid_la + clen + 0xFF) & ~0xFF
    INIT_H, PLAY_H, STOP_H = HI, HI + 4, HI + 8
    # #211 scan bait: SF2II statically sweeps [DriverCodeTop,+Size) for
    # an ABX/ABY $D400-$D406 write (driver_utils.cpp:419 derefs
    # result.begin() unguarded → empty ⇒ crash). For low-load files
    # $1000-$18FF is the embedded binary (no usable trampoline/stamp
    # slot), so point the scan window HERE instead: handler stubs are
    # 14B (HI..HI+13), then a dead `STA $D400,X; RTS` at HI+14 that
    # SF2II's linear sweep decodes after STOP's RTS. Never executed
    # (INIT/PLAY/STOP are JSR-stub entries; STOP ends RTS at HI+13).
    BAIT = HI + 14
    EDIT = HI + 0x20                       # past 14B stubs + 4B bait

    # Safe placeholder Block 5 + zero-filled Block 3 tables in the edit
    # area (identical shape to _inject_player_raw_minimal so SF2II's
    # editor model is valid even though it's empty).
    ol_ptr_lo  = EDIT + 0
    ol_ptr_hi  = EDIT + 3
    seq_ptr_lo = EDIT + 6
    seq_ptr_hi = EDIT + 6 + SEQ_PTR_SIZE
    ol_track1  = EDIT + 6 + 2 * SEQ_PTR_SIZE
    seq00      = ol_track1 + 3 * OL_SIZE
    music_data_params = {
        'track_count': 3, 'ol_ptr_lo_addr': ol_ptr_lo,
        'ol_ptr_hi_addr': ol_ptr_hi, 'seq_count': 1,
        'seq_ptr_lo_addr': seq_ptr_lo, 'seq_ptr_hi_addr': seq_ptr_hi,
        'ol_size': OL_SIZE, 'ol_track1_addr': ol_track1,
        'seq_size': SEQ_SIZE, 'seq00_addr': seq00,
    }

    edit = bytearray()
    for v in range(3): edit.append((ol_track1 + v * OL_SIZE) & 0xFF)
    for v in range(3): edit.append(((ol_track1 + v * OL_SIZE) >> 8) & 0xFF)
    seq_lo = bytearray(SEQ_PTR_SIZE); seq_hi = bytearray(SEQ_PTR_SIZE)
    seq_lo[0] = seq00 & 0xFF; seq_hi[0] = (seq00 >> 8) & 0xFF
    edit.extend(seq_lo); edit.extend(seq_hi)
    for _ in range(3):
        ol = bytearray([0xA0, 0x00, 0xFE])
        ol.extend([0xFF] * (OL_SIZE - 3)); edit.extend(ol)
    edit.extend(bytes([0x7F] * SEQ_SIZE))

    gen = SF2HeaderGenerator(driver_size=clen)
    gen.DRIVER_INIT, gen.DRIVER_PLAY, gen.DRIVER_STOP = INIT_H, PLAY_H, STOP_H
    # Point SF2II's #211 SID-write scan window at our handler+bait
    # region (binary at $1000 has no usable stamp slot for low-load).
    gen.driver_code_top  = HI
    gen.driver_code_size = 0x20
    gen.instr_addr = EDIT + len(edit); gen.cmd_addr = gen.instr_addr + 0x70
    edit.extend(bytes(32 * 6))
    gen.wave_addr = EDIT + len(edit);  edit.extend(bytes(32 * 2))
    gen.pulse_addr = EDIT + len(edit); edit.extend(bytes(16 * 3))
    gen.filter_addr = EDIT + len(edit); edit.extend(bytes(16 * 3))
    gen.arp_addr = EDIT + len(edit);   edit.extend(bytes(256))
    gen.tempo_addr = EDIT + len(edit); edit.extend(bytes(256))
    gen.hr_addr = EDIT + len(edit);    edit.extend(bytes(16 * 2))
    gen.init_table_addr = EDIT + len(edit); edit.extend(bytes(32 * 2))
    sf2_edit_data = bytes(edit)
    gen.driver_size += len(sf2_edit_data)

    header_bytes = gen.generate_complete_headers(music_data_params)
    H = len(header_bytes)

    # Place the header so it ends strictly below sid_la (header bytes
    # are LOAD_BASE-independent — all addresses inside are absolute).
    # Floor at $0500: keeps the header clear of zeropage ($00-$FF),
    # stack ($0100-$01FF), and the BASIC/KERNAL vector+buffer region
    # ($0200-$04FF — BASIC input $0200, tape buffer $033C, KERNAL
    # vectors $0314+). $0500-$08FF is default screen RAM on a real
    # C64 but SF2II's player emulation never drives VIC, so it's free
    # except where the embedded player has its own scratch — Laxity-
    # class players either zero scratch at INIT before reading, or
    # don't touch it at all in the header span (verified by py65
    # read-before-write analysis: `pyscript/find_rbw_scratch.py`).
    load_base = (sid_la - (2 + H) - 1) & ~0xFF
    if load_base < 0x0500:
        logger.info(
            f"  Low-load: no room for {2+H}B header below "
            f"${sid_la:04X} (would need LOAD_BASE ${load_base:04X} "
            f"< $0500 floor); cannot fix this file")
        return None

    edit_end = EDIT + len(sf2_edit_data)
    file_size = 2 + (edit_end - load_base)
    if file_size >= 0x10000:
        logger.info("  Low-load: file would exceed 64K; cannot fix")
        return None
    fd = bytearray(file_size)
    fd[0] = load_base & 0xFF
    fd[1] = load_base >> 8

    def off(addr): return addr - load_base + 2
    fd[off(load_base):off(load_base) + H] = header_bytes
    fd[off(sid_la):off(sid_la) + clen] = bytes(c64_data)
    # Minimal handler stubs after the binary.
    fd[off(INIT_H):off(INIT_H) + 4] = bytes([0x20, init_addr & 0xFF, init_addr >> 8, 0x60])
    fd[off(PLAY_H):off(PLAY_H) + 4] = bytes([0x20, play_addr & 0xFF, play_addr >> 8, 0x60])
    fd[off(STOP_H):off(STOP_H) + 6] = bytes([0xA9, 0x00, 0x8D, 0x18, 0xD4, 0x60])
    # #211 scan bait at HI+14 (after the 14B stubs): STA $D400,X; RTS.
    # Dead code — SF2II only static-sweeps it; nothing executes here.
    fd[off(BAIT):off(BAIT) + 4] = bytes([0x9D, 0x00, 0xD4, 0x60])
    fd[off(EDIT):off(EDIT) + len(sf2_edit_data)] = sf2_edit_data

    logger.info(
        f"  Low-load layout: LOAD_BASE=${load_base:04X} "
        f"header=${load_base:04X}-${load_base + H - 1:04X} "
        f"binary=${sid_la:04X}-${sid_la + clen - 1:04X} "
        f"handlers INIT=${INIT_H:04X} PLAY=${PLAY_H:04X} "
        f"STOP=${STOP_H:04X} (JSR ${init_addr:04X}/${play_addr:04X})")

    # SF2II reads the aux-chain pointer from a HARDCODED absolute
    # address $0FFB (driver_info.h: AuxilaryDataPointerAddress).
    # For low-load files the binary spans $0FFB, so writing our aux
    # pointer there corrupts live player data (verified: Slash/Broom
    # read a freq table at $0FFB → audio divergence). Caller MUST
    # skip aux injection entirely: SF2II then reads the binary's own
    # $0FFB-$0FFC bytes AS an address; for these files that points
    # below LOAD_BASE (unmapped → 0) so ParseAuxilaryData's
    # `if (addr == 0) return false` / immediate ID_End yields a clean
    # empty-aux skip — binary stays byte-intact, editor view is
    # empty-by-design anyway. (C4 metadata still works — the META
    # trailer is appended at file end, not via aux.)
    return bytes(fd), True
