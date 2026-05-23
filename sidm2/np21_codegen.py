"""6502 code generators for the NP21-embed SF2 wrapper layer.

Pure byte-stream emitters extracted from `sf2_writer.py` (v3.5.36
refactor). None of these functions hold state or reference `self.*` —
they assemble small 6502 routines (~15-160 bytes each) from
parameters and return the bytes.

The routines emit into the SF2 edit area to provide editor-to-player
data flow on every PLAY tick:

  emit_sf2_to_np21_translator   — single-pattern flat copy (legacy)
  emit_multipat_translator      — Stage 2.5 multi-pattern walker
                                  (called from $0F9E by the PLAY handler)
  emit_wave_copy_routine        — flat copy (kept as sanity utility)
  emit_wave_split_copy_routine  — Stage 7 F3: SF2 interleaved → NP21
                                  parallel waveform + note-offset arrays
  emit_pulse_copy_routine       — plumbing for variant-specific pulse
                                  (call sites disabled pending per-variant RE)
  emit_pulse_packed_copy_routine — Stage 7 F4 Beast/Angular: nibble-packed
                                  PW bytes (high=lo, low=hi)
  emit_pulse_split_copy_routine — Stage 7 F4 Stinsen: parallel PW lo/hi
  emit_instr_copy_routine       — generic instrument table copy
                                  (5 fields × n rows)
  emit_instr_column_copy_routine — Stage 7 F2 Stinsen: column-major
                                  AD/SR (NP21 stride 1)
  emit_filter_cutoff_only_routine — Stage 7 F5 Beast/Angular: copy
                                  only col 0 (cutoff_hi byte stream)
  emit_filter_split_copy_routine — Stage 7 F5 Stinsen: 3 parallel
                                  cmd/val/aux byte streams

All branches assert their relative offset fits in [-128, 127]; large
parameters that would overflow raise `RuntimeError`. Caller is
responsible for placing each routine at an address with at least
`len(returned_bytes)` of free space.
"""
from __future__ import annotations


def emit_sf2_to_np21_translator(num_patterns: int, seq00_addr: int,
                                  shadow_base: int, play_addr: int) -> bytes:
    """Single-pattern flat-copy SF2→NP21 translator (legacy, kept for
    sf2_to_np21.py output verification). For each of num_patterns
    256-byte slots starting at seq00_addr, copy bytes verbatim into
    the corresponding shadow slot until the first SF2 0x7F end marker
    is hit, then write NP21 `0xFF + 0x00` (loop-to-start). After all
    patterns are translated, `JSR play_addr; RTS`.

    Superseded by `emit_multipat_translator` (Stage 2.5) for the
    actual runtime PLAY handler. Returns 51 bytes regardless of
    num_patterns.
    """
    SRC_LO, SRC_HI = 0xFB, 0xFC
    DST_LO, DST_HI = 0xFD, 0xFE

    code = bytearray()

    # Setup: load src/dst pointers into zero page (16 bytes)
    code += bytes([0xA9,  seq00_addr        & 0xFF,
                   0x85,  SRC_LO,
                   0xA9, (seq00_addr  >> 8) & 0xFF,
                   0x85,  SRC_HI,
                   0xA9,  shadow_base       & 0xFF,
                   0x85,  DST_LO,
                   0xA9, (shadow_base >> 8) & 0xFF,
                   0x85,  DST_HI])

    code += bytes([0xA2, num_patterns])                # LDX #num_patterns

    pattern_loop_addr = len(code)
    code += bytes([0xA0, 0x00])                        # LDY #0

    byte_loop_addr = len(code)
    code += bytes([0xB1, SRC_LO,                       # LDA (src_zp),Y
                   0xC9, 0x7F])                        # CMP #$7F

    code += bytes([0xF0, 0])                           # BEQ end_of_seq (fixup)
    beq_off_pos = len(code) - 1

    code += bytes([0x91, DST_LO,                       # STA (dst_zp),Y
                   0xC8])                              # INY
    bne_target = byte_loop_addr - (len(code) + 2)
    code += bytes([0xD0, bne_target & 0xFF])           # BNE byte_loop

    end_of_seq_addr = len(code)
    code[beq_off_pos] = (end_of_seq_addr - (beq_off_pos + 1)) & 0xFF

    code += bytes([0xA9, 0xFF,                         # LDA #$FF
                   0x91, DST_LO,                       # STA (dst_zp),Y
                   0xC8,                               # INY
                   0xA9, 0x00,                         # LDA #$00
                   0x91, DST_LO])                      # STA (dst_zp),Y

    code += bytes([0xE6, SRC_HI,                       # INC src_zp+1
                   0xE6, DST_HI,                       # INC dst_zp+1
                   0xCA])                              # DEX

    bne_pat_target = pattern_loop_addr - (len(code) + 2)
    code += bytes([0xD0, bne_pat_target & 0xFF])       # BNE pattern_loop

    code += bytes([0x20, play_addr & 0xFF, (play_addr >> 8) & 0xFF,
                   0x60])                              # JSR play_addr; RTS

    return bytes(code)


def emit_wave_copy_routine(sf2_wave_addr: int, np21_wave_addr: int,
                            n_bytes: int = 64) -> bytes:
    """[KEPT for backwards compat — superseded by emit_wave_split_copy_routine]

    Simple byte-copy from sf2_wave_addr to np21_wave_addr (same layout
    in both). NP21 wave is actually parallel arrays (notes + waveforms
    at separate addresses), so this can't be used directly for Stage 7;
    see emit_wave_split_copy_routine instead. Kept as a sanity-test
    utility in case a future SF2/NP21 layout shares a flat 2-byte-row
    format.
    """
    if not (1 <= n_bytes <= 256):
        raise ValueError(f"wave_copy n_bytes must be 1..256, got {n_bytes}")
    code = bytearray()
    code += bytes([0xA2, (n_bytes - 1) & 0xFF])                                # LDX #n-1
    loop_start = len(code)
    code += bytes([0xBD, sf2_wave_addr & 0xFF, (sf2_wave_addr >> 8) & 0xFF])   # LDA sf2,X
    code += bytes([0x9D, np21_wave_addr & 0xFF, (np21_wave_addr >> 8) & 0xFF]) # STA np21,X
    code += bytes([0xCA])                                                       # DEX
    rel = loop_start - (len(code) + 2)
    if not -128 <= rel <= 127:
        raise RuntimeError(f"wave_copy back-branch out of range: {rel}")
    code += bytes([0x10, rel & 0xFF])                                          # BPL loop
    code += bytes([0x60])                                                       # RTS
    return bytes(code)


def emit_wave_split_copy_routine(sf2_wave_addr: int,
                                  np21_wave_data_addr: int,
                                  np21_note_addr: int,
                                  n_rows: int = 32) -> bytes:
    """Stage 7 Phase B.1: copy SF2-edit-area wave bytes back into
    NP21's PARALLEL waveform + note-offset arrays.

    NP21 stores wave programs as two parallel arrays at separate
    addresses (Stinsen layout: waveforms at $18DA, notes at $190C).
    The SF2 edit area emits them interleaved as 2-byte rows
    (waveform, note_offset) starting at sf2_wave_addr. So per row r:

        np21_wave_data[r] ← sf2[2r]      (waveform byte)
        np21_note[r]      ← sf2[2r + 1]  (note-offset byte)

    Routine size for n_rows=32 (typical Stage 4 emit): 31 bytes.
    """
    if not (1 <= n_rows <= 128):
        raise ValueError(f"wave_split_copy n_rows must be 1..128, got {n_rows}")
    code = bytearray()

    # ----- waveform pass -----
    code += bytes([0xA2, (n_rows - 1) & 0xFF])                                  # LDX #n-1
    wave_loop_start = len(code)
    code += bytes([0x8A, 0x0A, 0xA8])                                           # TXA; ASL; TAY
    code += bytes([0xB9, sf2_wave_addr & 0xFF, (sf2_wave_addr >> 8) & 0xFF])    # LDA sf2,Y
    code += bytes([0x9D, np21_wave_data_addr & 0xFF,
                   (np21_wave_data_addr >> 8) & 0xFF])                          # STA np21_wave,X
    code += bytes([0xCA])                                                        # DEX
    rel = wave_loop_start - (len(code) + 2)
    if not -128 <= rel <= 127:
        raise RuntimeError(f"wave_split_copy wave_loop out of range: {rel}")
    code += bytes([0x10, rel & 0xFF])                                           # BPL wave_loop

    # ----- note-offset pass -----
    code += bytes([0xA2, (n_rows - 1) & 0xFF])                                  # LDX #n-1
    note_loop_start = len(code)
    code += bytes([0x8A, 0x0A, 0xA8, 0xC8])                                     # TXA; ASL; TAY; INY
    code += bytes([0xB9, sf2_wave_addr & 0xFF, (sf2_wave_addr >> 8) & 0xFF])    # LDA sf2,Y
    code += bytes([0x9D, np21_note_addr & 0xFF,
                   (np21_note_addr >> 8) & 0xFF])                               # STA np21_note,X
    code += bytes([0xCA])                                                        # DEX
    rel = note_loop_start - (len(code) + 2)
    if not -128 <= rel <= 127:
        raise RuntimeError(f"wave_split_copy note_loop out of range: {rel}")
    code += bytes([0x10, rel & 0xFF])                                           # BPL note_loop

    code += bytes([0x60])                                                        # RTS
    return bytes(code)


def emit_filter_cutoff_only_routine(sf2_filter_addr: int,
                                     np21_cutoff_hi_addr: int,
                                     n_rows: int = 16) -> bytes:
    """Stage 7 Phase B.2 (F5 filter, Beast/Angular variants):
    propagate only col 0 (cutoff_hi byte stream) from SF2 edit area
    to NP21. Cols 1 + 2 (res_routing, mode_vol) are at fixed low
    addresses ($100A, $1009) that CANNOT be array-indexed safely.

    SF2 stride 3 (col0, col1, col2 per row), NP21 stride 1.
    """
    if not (1 <= n_rows <= 85):
        raise ValueError(f"filter_cutoff_only n_rows must be 1..85, got {n_rows}")
    code = bytearray()
    # Walk r = 0..n-1 with Y = 3*r maintained incrementally.
    code += bytes([0xA2, 0x00])                                                   # LDX #0
    code += bytes([0xA0, 0x00])                                                   # LDY #0
    loop_start = len(code)
    code += bytes([0xB9, sf2_filter_addr & 0xFF, (sf2_filter_addr >> 8) & 0xFF])  # LDA sf2,Y
    code += bytes([0x9D, np21_cutoff_hi_addr & 0xFF,
                   (np21_cutoff_hi_addr >> 8) & 0xFF])                             # STA np21,X
    code += bytes([0xC8, 0xC8, 0xC8])                                              # INY × 3
    code += bytes([0xE8])                                                          # INX
    code += bytes([0xE0, n_rows & 0xFF])                                           # CPX #n
    rel = loop_start - (len(code) + 2)
    if not -128 <= rel <= 127:
        raise RuntimeError(f"filter_cutoff_only loop out of range: {rel}")
    code += bytes([0xD0, rel & 0xFF])                                              # BNE loop
    code += bytes([0x60])                                                          # RTS
    return bytes(code)


def emit_filter_split_copy_routine(sf2_filter_addr: int,
                                    np21_cmd_addr: int,
                                    np21_val_addr: int,
                                    np21_aux_addr: int,
                                    n_rows: int = 16) -> bytes:
    """Stage 7 Phase B.2 (F5 filter, Stinsen variant): copy
    SF2-edit-area filter bytes back into NP21's three parallel
    filter byte streams (cmd at $1989, val at $19A3, aux at $19BD).

    SF2 stride 3 (col0=cmd, col1=val, col2=aux), NP21 stride 1.
    """
    if not (1 <= n_rows <= 85):     # 85 * 3 = 255, fits in u8 Y
        raise ValueError(f"filter_split_copy n_rows must be 1..85, got {n_rows}")
    code = bytearray()

    code += bytes([0xA2, 0x00])                                                   # LDX #0
    code += bytes([0xA0, 0x00])                                                   # LDY #0
    loop_start = len(code)
    # col 0 (cmd)
    code += bytes([0xB9, sf2_filter_addr & 0xFF, (sf2_filter_addr >> 8) & 0xFF])  # LDA sf2,Y
    code += bytes([0x9D, np21_cmd_addr & 0xFF,
                   (np21_cmd_addr >> 8) & 0xFF])                                   # STA np21_cmd,X
    code += bytes([0xC8])                                                          # INY
    # col 1 (val)
    code += bytes([0xB9, sf2_filter_addr & 0xFF, (sf2_filter_addr >> 8) & 0xFF])  # LDA sf2,Y
    code += bytes([0x9D, np21_val_addr & 0xFF,
                   (np21_val_addr >> 8) & 0xFF])                                   # STA np21_val,X
    code += bytes([0xC8])                                                          # INY
    # col 2 (aux)
    code += bytes([0xB9, sf2_filter_addr & 0xFF, (sf2_filter_addr >> 8) & 0xFF])  # LDA sf2,Y
    code += bytes([0x9D, np21_aux_addr & 0xFF,
                   (np21_aux_addr >> 8) & 0xFF])                                   # STA np21_aux,X
    code += bytes([0xC8])                                                          # INY (→ next row col 0)
    code += bytes([0xE8])                                                          # INX
    code += bytes([0xE0, n_rows & 0xFF])                                           # CPX #n
    rel = loop_start - (len(code) + 2)
    if not -128 <= rel <= 127:
        raise RuntimeError(f"filter_split_copy loop out of range: {rel}")
    code += bytes([0xD0, rel & 0xFF])                                              # BNE loop
    code += bytes([0x60])                                                          # RTS
    return bytes(code)


def emit_pulse_packed_copy_routine(sf2_pulse_addr: int,
                                     np21_stream_addr: int,
                                     n_rows: int = 16) -> bytes:
    """Stage 7 Phase B.2 (F4 pulse, Beast/Angular variants):
    copy SF2-edit-area pulse bytes back to NP21's 4-byte stride
    step-record byte stream. SF2 cols 0/1/2 → NP21 bytes 0/1/2;
    NP21 byte 3 preserved.

    NP21 byte 0 is **nibble-packed**: high nibble = PW lo scratch,
    low nibble = PW hi scratch (verified for Beast at $1AC5 and
    Angular at $1A3B). SF2 emit splits it as a single byte column.
    """
    if not (1 <= n_rows <= 60):     # 60 * 4 = 240, fits u8 X
        raise ValueError(f"pulse_packed n_rows must be 1..60, got {n_rows}")
    np21_total = n_rows * 4
    code = bytearray()
    code += bytes([0xA2, 0x00, 0xA0, 0x00])                                       # LDX #0; LDY #0
    loop_start = len(code)
    # col 0
    code += bytes([0xB9, sf2_pulse_addr & 0xFF, (sf2_pulse_addr >> 8) & 0xFF])    # LDA sf2,Y
    code += bytes([0x9D, np21_stream_addr & 0xFF,
                   (np21_stream_addr >> 8) & 0xFF])                                # STA np21,X
    code += bytes([0xE8, 0xC8])                                                    # INX; INY
    # col 1
    code += bytes([0xB9, sf2_pulse_addr & 0xFF, (sf2_pulse_addr >> 8) & 0xFF])
    code += bytes([0x9D, np21_stream_addr & 0xFF,
                   (np21_stream_addr >> 8) & 0xFF])
    code += bytes([0xE8, 0xC8])
    # col 2
    code += bytes([0xB9, sf2_pulse_addr & 0xFF, (sf2_pulse_addr >> 8) & 0xFF])
    code += bytes([0x9D, np21_stream_addr & 0xFF,
                   (np21_stream_addr >> 8) & 0xFF])
    code += bytes([0xE8, 0xE8, 0xC8])                                              # INX; INX; INY
    code += bytes([0xE0, np21_total & 0xFF])                                       # CPX #n*4
    rel = loop_start - (len(code) + 2)
    if not -128 <= rel <= 127:
        raise RuntimeError(f"pulse_packed loop out of range: {rel}")
    code += bytes([0xD0, rel & 0xFF])                                              # BNE loop
    code += bytes([0x60])                                                          # RTS
    return bytes(code)


def emit_pulse_split_copy_routine(sf2_pulse_addr: int,
                                   np21_pulse_lo_addr: int,
                                   np21_pulse_hi_addr: int,
                                   n_rows: int = 16) -> bytes:
    """Stage 7 Phase B.2 (F4 pulse, Stinsen variant): copy
    SF2-edit-area pulse bytes back into NP21's PARALLEL
    pulse-program byte streams (PW lo at $1957, PW hi at $193E).
    SF2 col 0 → PW lo, col 1 → PW hi, col 2 ignored.
    """
    if not (1 <= n_rows <= 85):     # 85 × 3 = 255, fits in u8 Y
        raise ValueError(f"pulse_split_copy n_rows must be 1..85, got {n_rows}")
    code = bytearray()

    code += bytes([0xA2, 0x00])                                                 # LDX #0
    code += bytes([0xA0, 0x00])                                                 # LDY #0
    loop_start = len(code)
    code += bytes([0xB9, sf2_pulse_addr & 0xFF, (sf2_pulse_addr >> 8) & 0xFF])  # LDA sf2,Y
    code += bytes([0x9D, np21_pulse_lo_addr & 0xFF,
                   (np21_pulse_lo_addr >> 8) & 0xFF])                            # STA np21_lo,X
    code += bytes([0xC8])                                                        # INY (→ col 1)
    code += bytes([0xB9, sf2_pulse_addr & 0xFF, (sf2_pulse_addr >> 8) & 0xFF])  # LDA sf2,Y
    code += bytes([0x9D, np21_pulse_hi_addr & 0xFF,
                   (np21_pulse_hi_addr >> 8) & 0xFF])                            # STA np21_hi,X
    code += bytes([0xC8, 0xC8])                                                  # INY; INY (skip col 2)
    code += bytes([0xE8])                                                        # INX
    code += bytes([0xE0, n_rows & 0xFF])                                         # CPX #n
    rel = loop_start - (len(code) + 2)
    if not -128 <= rel <= 127:
        raise RuntimeError(f"pulse_split_copy loop out of range: {rel}")
    code += bytes([0xD0, rel & 0xFF])                                            # BNE loop
    code += bytes([0x60])                                                        # RTS
    return bytes(code)


def emit_instr_copy_routine(sf2_instr_addr: int, np21_instr_addr: int,
                             n_instruments: int = 16,
                             fields: list[tuple[int, int]] | None = None,
                             np21_stride: int = 8) -> bytes:
    """Stage 7 Phase B.2: copy SF2-edit-area instrument bytes back
    into the NP21 binary's instrument table on every PLAY tick.

    Default field mapping (full Driver-11 row-major, 5 fields):
        NP21 byte 0 (AD)        ← SF2 col 0
        NP21 byte 1 (SR)        ← SF2 col 1
        NP21 byte 2 (HR)        ← SF2 col 2
        NP21 byte 6 (pulse_ptr) ← SF2 col 4
        NP21 byte 7 (wave_ptr)  ← SF2 col 5
        (col 3 Filter and bytes 3-5 NP21 flags2/flags3/pulse_pm
         intentionally NOT copied.)

    Caller can pass a variant-specific subset via `fields`, e.g.
    Beast uses [(0, 5), (1, 6)] (AD/SR at NP21 offsets 5/6 in an
    8-byte row). `np21_stride` defaults to 8 (Driver 11 stride).
    """
    if not (1 <= n_instruments <= 32):
        raise ValueError(f"instr_copy n_instruments must be 1..32, got {n_instruments}")

    if fields is not None:
        FIELDS = list(fields)
    else:
        FIELDS = [
            (0, 0),   # AD
            (1, 1),   # SR
            (2, 2),   # HR / restart
            (4, 6),   # Pulse ptr
            (5, 7),   # Wave ptr
        ]
    if not (1 <= np21_stride <= 16):
        raise ValueError(f"instr_copy np21_stride must be 1..16, got {np21_stride}")
    np21_total = n_instruments * np21_stride
    if np21_total > 256:
        raise ValueError(f"instr_copy NP21 stride×rows exceeds 256: {np21_total}")

    code = bytearray()
    for sf2_col, np21_byte in FIELDS:
        sf2_field_addr = (sf2_instr_addr + sf2_col) & 0xFFFF
        np21_field_addr = (np21_instr_addr + np21_byte) & 0xFFFF
        code += bytes([0xA2, 0x00])                                              # LDX #0
        code += bytes([0xA0, 0x00])                                              # LDY #0
        loop_start = len(code)
        code += bytes([0xB9, sf2_field_addr & 0xFF,
                       (sf2_field_addr >> 8) & 0xFF])                            # LDA sf2,Y
        code += bytes([0x9D, np21_field_addr & 0xFF,
                       (np21_field_addr >> 8) & 0xFF])                           # STA np21,X
        # X += stride
        code += bytes([0x8A, 0x18, 0x69, np21_stride & 0xFF, 0xAA])              # TXA; CLC; ADC #stride; TAX
        # Y += 6 (SF2 stride)
        code += bytes([0x98, 0x18, 0x69, 0x06, 0xA8])                            # TYA; CLC; ADC #6; TAY
        code += bytes([0xE0, np21_total & 0xFF])                                 # CPX #n*stride
        rel = loop_start - (len(code) + 2)
        if not -128 <= rel <= 127:
            raise RuntimeError(f"instr_copy back-branch out of range: {rel}")
        code += bytes([0xD0, rel & 0xFF])                                        # BNE loop
    code += bytes([0x60])                                                         # RTS
    return bytes(code)


def emit_pulse_copy_routine(sf2_pulse_addr: int, np21_pulse_addr: int,
                             n_rows: int = 16) -> bytes:
    """[plumbing only — wire-up disabled pending per-variant address RE]

    Stage 7 Phase B.2 generic pulse table copy: 3 fields × n_rows
    rows. NP21 stride 4, SF2 stride 3.
    """
    if not (1 <= n_rows <= 32):
        raise ValueError(f"pulse_copy n_rows must be 1..32, got {n_rows}")

    np21_total = n_rows * 4
    if np21_total > 256:
        raise ValueError(f"pulse_copy NP21 stride×rows exceeds 256: {np21_total}")

    code = bytearray()
    for col in range(3):  # SF2 cols 0, 1, 2 → NP21 bytes 0, 1, 2
        sf2_field_addr = (sf2_pulse_addr + col) & 0xFFFF
        np21_field_addr = (np21_pulse_addr + col) & 0xFFFF
        code += bytes([0xA2, 0x00])                                              # LDX #0
        code += bytes([0xA0, 0x00])                                              # LDY #0
        loop_start = len(code)
        code += bytes([0xB9, sf2_field_addr & 0xFF,
                       (sf2_field_addr >> 8) & 0xFF])                            # LDA sf2,Y
        code += bytes([0x9D, np21_field_addr & 0xFF,
                       (np21_field_addr >> 8) & 0xFF])                           # STA np21,X
        code += bytes([0x8A, 0x18, 0x69, 0x04, 0xAA])                            # TXA; CLC; ADC #4; TAX
        code += bytes([0x98, 0x18, 0x69, 0x03, 0xA8])                            # TYA; CLC; ADC #3; TAY
        code += bytes([0xE0, np21_total & 0xFF])                                 # CPX #n*4
        rel = loop_start - (len(code) + 2)
        if not -128 <= rel <= 127:
            raise RuntimeError(f"pulse_copy back-branch out of range: {rel}")
        code += bytes([0xD0, rel & 0xFF])                                        # BNE loop
    code += bytes([0x60])                                                         # RTS
    return bytes(code)


def emit_instr_column_copy_routine(sf2_instr_addr: int,
                                    np21_ad_col_addr: int,
                                    np21_sr_col_addr: int,
                                    n_instruments: int) -> bytes:
    """Stage 7 Phase B.2 (Stinsen variant): copy SF2-edit-area
    instrument AD/SR columns back into NP21's COLUMN-MAJOR table.

    Stinsen-class layout:
        AD column: NP21 contiguous bytes [np21_ad_col_addr .. +n-1]
        SR column: NP21 contiguous bytes [np21_sr_col_addr .. +n-1]

    SF2 edit area is row-major (6B/instr). Per row r:
        np21_ad_col[r] ← sf2[6r + 0]
        np21_sr_col[r] ← sf2[6r + 1]
    """
    if not (1 <= n_instruments <= 42):
        raise ValueError(
            f"instr_column_copy n_instruments must be 1..42, got {n_instruments}"
        )

    code = bytearray()
    for col_offset_in_row, np21_col_addr in (
        (0, np21_ad_col_addr),    # AD
        (1, np21_sr_col_addr),    # SR
    ):
        sf2_field_addr = (sf2_instr_addr + col_offset_in_row) & 0xFFFF
        code += bytes([0xA2, 0x00])                                              # LDX #0
        code += bytes([0xA0, 0x00])                                              # LDY #0
        loop_start = len(code)
        code += bytes([0xB9, sf2_field_addr & 0xFF,
                       (sf2_field_addr >> 8) & 0xFF])                            # LDA sf2,Y
        code += bytes([0x9D, np21_col_addr & 0xFF,
                       (np21_col_addr >> 8) & 0xFF])                             # STA np21_col,X
        code += bytes([0xE8])                                                     # INX
        code += bytes([0x98, 0x18, 0x69, 0x06, 0xA8])                            # TYA; CLC; ADC #6; TAY
        code += bytes([0xE0, n_instruments & 0xFF])                              # CPX #n
        rel = loop_start - (len(code) + 2)
        if not -128 <= rel <= 127:
            raise RuntimeError(
                f"instr_column_copy back-branch out of range: {rel}"
            )
        code += bytes([0xD0, rel & 0xFF])                                        # BNE loop
    code += bytes([0x60])                                                         # RTS
    return bytes(code)


def emit_multipat_translator(voice_pat_counts, seq00_addr: int,
                              shadow_base: int, play_addr: int,
                              translate_base: int, table_copy_addr=None,
                              instr_copy_addr=None, pulse_copy_addr=None,
                              filter_copy_addr=None) -> bytes:
    """Stage 2.5: Multi-pattern runtime translator. Called from the
    SF2 PLAY handler at $0F94 (JMP $0F9E). Regenerates the shadow
    buffer from the SF2 edit area on every PLAY tick.

    For each voice 0..2:
      1. Reset DST to shadow_base + voice*256, DST_Y to 0.
      2. Load voice's pattern count from inline data table.
      3. For each pattern: copy bytes from src (SF2 edit area) until
         0x7F into the voice's shadow slot at DST_Y, advance DST_Y
         per byte, advance src by 256 (next SF2 pattern) per pattern.
      4. After all voice's patterns: write 0xFF + 0x00 to dst (loop
         terminator the NP21 player needs).
    After all 3 voices: optionally JSR each of (table_copy_addr,
    instr_copy_addr, pulse_copy_addr, filter_copy_addr), then
    JSR play_addr; RTS.

    ZP usage:
      $F7      = src_y_save (temp)
      $F8      = dst_y (current write offset within voice slot)
      $F9      = pat_remaining (patterns left in current voice)
      $FA      = voice_idx (0..2)
      $FB/$FC  = src_lo/src_hi (current SF2 pattern start)
      $FD/$FE  = dst_lo/dst_hi (voice shadow slot base)

    Caller emits the returned bytes at `translate_base` (an absolute
    c64 address). The patcher computes the inline data table's
    absolute address using `translate_base + table_offset`.
    """
    SRC_LO, SRC_HI = 0xFB, 0xFC
    DST_LO, DST_HI = 0xFD, 0xFE
    DST_Y          = 0xF8
    PAT_REM        = 0xF9
    VOICE_IDX      = 0xFA
    SRC_Y_TMP      = 0xF7

    SHADOW_LO = shadow_base & 0xFF
    SHADOW_HI = (shadow_base >> 8) & 0xFF

    c = bytearray()

    # ------ Setup: src = seq00_addr, voice = 0
    c += bytes([0xA9, seq00_addr & 0xFF, 0x85, SRC_LO,
                0xA9, (seq00_addr >> 8) & 0xFF, 0x85, SRC_HI,
                0xA9, 0x00, 0x85, VOICE_IDX])

    # ------ voice_loop:
    voice_loop = len(c)

    # DST = shadow_base + voice_idx*256 (10 bytes)
    c += bytes([0xA9, SHADOW_LO, 0x85, DST_LO,
                0xA5, VOICE_IDX,
                0x18,
                0x69, SHADOW_HI,
                0x85, DST_HI])

    # DST_Y = 0; PAT_REM = pat_count_table[voice_idx]
    c += bytes([0xA9, 0x00, 0x85, DST_Y,
                0xA6, VOICE_IDX,
                0xBD, 0x00, 0x00,
                0x85, PAT_REM])
    table_load_operand = len(c) - 4

    # ------ pat_loop:
    pat_loop = len(c)
    c += bytes([0xA0, 0x00])

    # ------ copy_loop:
    copy_loop = len(c)
    c += bytes([0xB1, SRC_LO,
                0xC9, 0x7F,
                0xF0, 0])
    beq_pat_end_pos = len(c) - 1

    c += bytes([0x84, SRC_Y_TMP,
                0xA4, DST_Y,
                0x91, DST_LO,
                0xE6, DST_Y,
                0xA4, SRC_Y_TMP,
                0xC8])

    rel_back = copy_loop - (len(c) + 2)
    if not -128 <= rel_back <= 127:
        raise RuntimeError(f"copy_loop back-branch out of range: {rel_back}")
    c += bytes([0xD0, rel_back & 0xFF])

    # ------ pat_end:
    pat_end = len(c)
    c[beq_pat_end_pos] = (pat_end - beq_pat_end_pos - 1) & 0xFF

    c += bytes([0xE6, SRC_HI,
                0xC6, PAT_REM])
    rel_back2 = pat_loop - (len(c) + 2)
    if not -128 <= rel_back2 <= 127:
        raise RuntimeError(f"pat_loop back-branch out of range: {rel_back2}")
    c += bytes([0xD0, rel_back2 & 0xFF])

    # ------ voice_done: write 0xFF, 0x00 terminator
    c += bytes([0xA9, 0xFF,
                0xA4, DST_Y,
                0x91, DST_LO,
                0xC8,
                0xA9, 0x00,
                0x91, DST_LO])

    # Advance voice; if < 3, loop
    c += bytes([0xE6, VOICE_IDX,
                0xA5, VOICE_IDX,
                0xC9, 0x03])
    rel_voice_back = voice_loop - (len(c) + 2)
    if -128 <= rel_voice_back <= 127:
        c += bytes([0x90, rel_voice_back & 0xFF])
    else:
        c += bytes([0xB0, 0x03,
                    0x4C,
                    (translate_base + voice_loop) & 0xFF,
                    ((translate_base + voice_loop) >> 8) & 0xFF])

    # ------ all voices done: optionally JSR copy routines, then
    # JSR play_addr; RTS.
    for addr in (table_copy_addr, instr_copy_addr, pulse_copy_addr,
                 filter_copy_addr):
        if addr is not None:
            c += bytes([0x20, addr & 0xFF, (addr >> 8) & 0xFF])
    c += bytes([0x20, play_addr & 0xFF, (play_addr >> 8) & 0xFF, 0x60])

    # ------ Inline data: voice_pat_counts table (3 bytes)
    table_offset = len(c)
    if len(voice_pat_counts) != 3:
        raise ValueError("voice_pat_counts must have 3 entries")
    for n in voice_pat_counts:
        c.append(n & 0xFF)

    # Patch the LDA absolute,X table operand to point at the table
    table_abs = translate_base + table_offset
    c[table_load_operand]     = table_abs & 0xFF
    c[table_load_operand + 1] = (table_abs >> 8) & 0xFF

    return bytes(c)
