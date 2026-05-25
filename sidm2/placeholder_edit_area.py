"""Empty-editor-view edit area builder.

Extracted from `low_load_layout.py` and `sf2_writer.py:_inject_player_raw_minimal`
at the v3.5.42 refactor. Both functions had ~40 lines of identical
placeholder-edit-area construction — same OL ptr / seq ptr / orderlists
/ F1-F5 tables — sitting in separate files.

# What this builds

The "empty editor view" — what SF2II's editor sees when SIDM2 can't
populate real F1-F5 data (the laxity raw-NP21 path is the only one that
does; everything else uses this placeholder):

  - 6 bytes: OL ptr lo/hi tables (3 voices × 2 bytes)
  - 256 bytes: Seq ptr lo table
  - 256 bytes: Seq ptr hi table
  - 768 bytes: 3 orderlists × 256 bytes — each is
              `[0xA0 (transpose 0)][0x00 (pattern 0)][0xFE (end)][0xFF...]`
  - 256 bytes: 1 sequence — all `0x7F` end-of-sequence markers
  - 192 bytes: Instruments (32×6) — all 0
  - 64 bytes:  Wave (32×2) — all 0
  - 48 bytes:  Pulse (16×3) — all 0
  - 48 bytes:  Filter (16×3) — all 0
  - 256 bytes: Arp (256×1) — all 0
  - 256 bytes: Tempo (256×1) — all 0
  - 32 bytes:  HR (16×2) — all 0
  - 64 bytes:  Init (32×2) — all 0

This shape is the safe minimum that lets SF2II's ComponentTracks
constructor see a non-empty data source (3 tracks × 1 pattern), the
editor render zero rows for each table, and the file load without
crashing — at the cost of "you can't see real instruments / waves /
patterns in the editor."

# When to use

  - Low-load layout (`low_load_layout.py`): sub-$1000 binaries, no
    room for real edit area.
  - Minimal embed (`sf2_writer.py:_inject_player_raw_minimal`):
    Galway/Hubbard/NP20 — drivers we can't decode editor-side, but
    can embed verbatim for playback.

The laxity raw-NP21 path builds a real edit area instead; it does
NOT use this module.
"""
from __future__ import annotations
from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .sf2_header_generator import SF2HeaderGenerator


# Block 5 sizes — these match SF2II's reference Stinsen layout and the
# pre-extraction implementations in low_load_layout.py and
# _inject_player_raw_minimal. Changing any one of them changes the
# editor's reported track/pattern counts.
OL_SIZE = 0x100             # orderlist slot size (bytes)
SEQ_SIZE = 0x100            # sequence slot size (bytes)
SEQ_PTR_SIZE = 0x80         # sequence-pointer table size (entries; 1 byte each)


def build_placeholder_edit_area(
    sf2_data_base: int,
    gen: "SF2HeaderGenerator",
) -> Tuple[bytes, dict]:
    """Build the empty-editor-view edit area and populate gen with addresses.

    Args:
        sf2_data_base: The C64 address where the edit area starts.
        gen: SF2HeaderGenerator to populate with table addresses
             (mutated in place — sets instr_addr / cmd_addr / wave_addr
              / pulse_addr / filter_addr / arp_addr / tempo_addr
              / hr_addr / init_table_addr).

    Returns:
        (edit_bytes, music_data_params) tuple.
          - edit_bytes: ready to be embedded in the SF2 file at sf2_data_base
          - music_data_params: dict to pass to
            `gen.generate_complete_headers(music_data_params)`
    """
    ol_ptr_lo  = sf2_data_base + 0
    ol_ptr_hi  = sf2_data_base + 3
    seq_ptr_lo = sf2_data_base + 6
    seq_ptr_hi = sf2_data_base + 6 + SEQ_PTR_SIZE
    ol_track1  = sf2_data_base + 6 + 2 * SEQ_PTR_SIZE
    seq00      = ol_track1 + 3 * OL_SIZE

    music_data_params = {
        'track_count': 3,
        'ol_ptr_lo_addr':  ol_ptr_lo,
        'ol_ptr_hi_addr':  ol_ptr_hi,
        'seq_count': 1,
        'seq_ptr_lo_addr': seq_ptr_lo,
        'seq_ptr_hi_addr': seq_ptr_hi,
        'ol_size':         OL_SIZE,
        'ol_track1_addr':  ol_track1,
        'seq_size':        SEQ_SIZE,
        'seq00_addr':      seq00,
    }

    edit = bytearray()
    # OL ptr lo / hi tables (3 voices each, all pointing at their own
    # 256-byte orderlist slot)
    for v in range(3):
        edit.append((ol_track1 + v * OL_SIZE) & 0xFF)
    for v in range(3):
        edit.append(((ol_track1 + v * OL_SIZE) >> 8) & 0xFF)
    # Seq ptr lo / hi tables (only entry 0 populated, pointing at seq00)
    seq_lo = bytearray(SEQ_PTR_SIZE)
    seq_hi = bytearray(SEQ_PTR_SIZE)
    seq_lo[0] = seq00 & 0xFF
    seq_hi[0] = (seq00 >> 8) & 0xFF
    edit.extend(seq_lo)
    edit.extend(seq_hi)
    # 3 orderlists × 256 bytes — each: [0xA0 (transpose 0)][0x00 (pattern 0)]
    # [0xFE (end)][0xFF...padding]
    for _ in range(3):
        ol = bytearray([0xA0, 0x00, 0xFE])
        ol.extend([0xFF] * (OL_SIZE - 3))
        edit.extend(ol)
    # 1 sequence × 256 bytes of 0x7F (end-of-sequence marker)
    edit.extend(bytes([0x7F] * SEQ_SIZE))

    # F1-F5 placeholder tables (zero-filled) + editor-only Arp/Tempo/HR/Init
    # tables. Block 3 column addresses point HERE (inside the edit area)
    # rather than into high-RAM, so the editor's renderer reads real file
    # bytes (zeros) instead of unpredictable emulated $C000+ contents that
    # may collide with a non-Laxity binary loaded there.
    gen.instr_addr = sf2_data_base + len(edit)
    gen.cmd_addr   = gen.instr_addr + 0x70    # NP21-style bias retained
    edit.extend(bytes(32 * 6))                # 32 rows × 6 cols Instruments

    gen.wave_addr  = sf2_data_base + len(edit)
    edit.extend(bytes(32 * 2))                # 32 rows × 2 cols Wave

    gen.pulse_addr = sf2_data_base + len(edit)
    edit.extend(bytes(16 * 3))                # 16 rows × 3 cols Pulse

    gen.filter_addr = sf2_data_base + len(edit)
    edit.extend(bytes(16 * 3))                # 16 rows × 3 cols Filter

    gen.arp_addr   = sf2_data_base + len(edit)
    edit.extend(bytes(256))                   # Arp: 256 rows × 1 col

    gen.tempo_addr = sf2_data_base + len(edit)
    edit.extend(bytes(256))                   # Tempo: 256 rows × 1 col

    gen.hr_addr    = sf2_data_base + len(edit)
    edit.extend(bytes(16 * 2))                # HR: 16 rows × 2 cols

    gen.init_table_addr = sf2_data_base + len(edit)
    edit.extend(bytes(32 * 2))                # Init: 32 rows × 2 cols

    return bytes(edit), music_data_params
