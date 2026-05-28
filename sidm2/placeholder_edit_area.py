"""Empty-or-populated editor-view edit area builder.

Extracted from `low_load_layout.py` and `sf2_writer.py:_inject_player_raw_minimal`
at the v3.5.42 refactor. Both functions had ~40 lines of identical
placeholder-edit-area construction — same OL ptr / seq ptr / orderlists
/ F1-F5 tables — sitting in separate files.

v3.5.60 added the populated-stream path so the low-load 2000 A.D. file
(Echo_Beat) can show real F1 patterns in the editor view instead of
the empty placeholder.

# What this builds

By default, the "empty editor view" — what SF2II's editor sees when
SIDM2 can't populate real F1-F5 data (the laxity raw-NP21 path is the
only one that does; everything else uses this placeholder):

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

When `voice_streams` is provided, the orderlists + sequence area instead
hold real F1 data: each voice's NP21-shape stream gets segmented at
`$A0` boundaries into one SF2 sub-pattern per segment, with each voice's
orderlist referencing only its own segments. F2-F5 + arp/tempo/hr/init
tables stay zero — the populated path is meant for cases like the 2000
A.D. cluster where F1 patterns can be synthesized but instrument/wave
data can't.

This shape is the safe minimum that lets SF2II's ComponentTracks
constructor see a non-empty data source (3 tracks × N patterns), the
editor render zero rows for the unpopulated tables, and the file load
without crashing.

# When to use

  - Low-load layout (`low_load_layout.py`): sub-$1000 binaries, no
    room for real edit area. Passes `voice_streams` when 2000 A.D.
    is detected (v3.5.60); otherwise placeholder.
  - Minimal embed (`sf2_writer.py:_inject_player_raw_minimal`):
    Galway/Hubbard/NP20 — drivers we can't decode editor-side, but
    can embed verbatim for playback. Always placeholder.

The laxity raw-NP21 path builds its own real edit area via
`np21_edit_area_builder`; it does NOT use this module.
"""
from __future__ import annotations
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .sf2_header_generator import SF2HeaderGenerator


# Block 5 sizes — these match SF2II's reference Stinsen layout and the
# pre-extraction implementations in low_load_layout.py and
# _inject_player_raw_minimal. Changing any one of them changes the
# editor's reported track/pattern counts.
OL_SIZE = 0x100             # orderlist slot size (bytes)
SEQ_SIZE = 0x100            # sequence slot size (bytes)
SEQ_PTR_SIZE = 0x80         # sequence-pointer table size (entries; 1 byte each)


def _build_populated_orderlists(
    voice_streams: List[bytes],
) -> Tuple[List[bytes], List[bytes]]:
    """Segment NP21-shape streams into SF2 orderlists + sequences.

    Mirrors the per-voice segmentation logic in `np21_edit_area_builder`
    so the editor sees the same orderlist+pattern shape whether the
    file goes through the standard path or the low-load path.

    Args:
        voice_streams: Exactly 3 NP21-shape byte streams (V0/V1/V2).
            Shorter lists are padded with empty streams.

    Returns:
        (orderlists, sf2_sequences):
          - orderlists: 3 byte strings, each OL_SIZE bytes
                        (`0xA0 idx 0xA0 idx ... 0xFE 0xFF...`)
          - sf2_sequences: N byte strings, each SEQ_SIZE bytes
                           (one per segment across all voices)
    """
    from .np21_pattern_segmenter import segment_voice_stream

    sf2_sequences: List[bytes] = []
    per_voice_pat_indices: List[List[int]] = [[], [], []]
    next_pat_idx = 0

    for v in range(3):
        voice_body = voice_streams[v] if v < len(voice_streams) else b''
        for seg in segment_voice_stream(voice_body):
            # v3.5.66 fix #3+#7: bound total segments at SEQ_PTR_SIZE
            # (the seq_ptr table caps at 128 entries; emitting beyond
            # would silently alias via `pat_idx & 0x7F`); also strip the
            # leading $A0-$BF synthesizer marker that the v2k extractor
            # emits — see np21_edit_area_builder.py for the rationale.
            if next_pat_idx >= SEQ_PTR_SIZE:
                break
            seq = bytearray()
            seg_bytes = seg.bytes_
            if seg_bytes and 0xA0 <= seg_bytes[0] <= 0xBF:
                seg_bytes = seg_bytes[1:]
            for b in seg_bytes:
                # NP21 ↔ SF2 packed byte conversion:
                # $00 (no event), $01-$6F (notes), and $7E-$FF (controls)
                # pass through identity; $70-$7D clamp to SF2 max pitch $6F.
                if 0x70 <= b <= 0x7D:
                    seq.append(0x6F)
                else:
                    seq.append(b)
            seq.append(0x7F)
            while len(seq) < SEQ_SIZE:
                seq.append(0x7F)
            sf2_sequences.append(bytes(seq[:SEQ_SIZE]))
            per_voice_pat_indices[v].append(next_pat_idx)
            next_pat_idx += 1
        if next_pat_idx >= SEQ_PTR_SIZE:
            break

    # Voices with zero segments still need a pattern to terminate their
    # orderlist; emit a single all-$7F sequence as a placeholder.
    for v in range(3):
        if not per_voice_pat_indices[v]:
            sf2_sequences.append(bytes([0x7F] * SEQ_SIZE))
            per_voice_pat_indices[v].append(next_pat_idx)
            next_pat_idx += 1

    orderlists: List[bytes] = []
    for v in range(3):
        ol = bytearray()
        for pat_idx in per_voice_pat_indices[v]:
            ol.append(0xA0)              # transpose 0 marker
            ol.append(pat_idx & 0x7F)
        ol.append(0xFE)                  # end (no loop)
        while len(ol) < OL_SIZE:
            ol.append(0xFF)
        orderlists.append(bytes(ol[:OL_SIZE]))

    return orderlists, sf2_sequences


def build_placeholder_edit_area(
    sf2_data_base: int,
    gen: "SF2HeaderGenerator",
    voice_streams: Optional[List[bytes]] = None,
    instruments: Optional[List] = None,
) -> Tuple[bytes, dict]:
    """Build the editor-view edit area and populate gen with addresses.

    Args:
        sf2_data_base: The C64 address where the edit area starts.
        gen: SF2HeaderGenerator to populate with table addresses
             (mutated in place — sets instr_addr / cmd_addr / wave_addr
              / pulse_addr / filter_addr / arp_addr / tempo_addr
              / hr_addr / init_table_addr).
        voice_streams: When None (default), emits the empty
             placeholder (3 tracks × 1 zero sequence). When a 3-entry
             list of NP21-shape byte streams is provided, each stream
             gets segmented at $A0 instrument-set boundaries and
             becomes a chain of orderlist + per-segment sequences in
             the edit area. F2-F5 + arp/tempo/hr/init tables remain
             zero-filled either way.

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

    if voice_streams is not None:
        orderlists, sf2_sequences = _build_populated_orderlists(voice_streams)
    else:
        # Placeholder: 3 identical orderlists (each pointing at pattern 0),
        # 1 empty sequence
        orderlists = [
            bytes([0xA0, 0x00, 0xFE] + [0xFF] * (OL_SIZE - 3))
            for _ in range(3)
        ]
        sf2_sequences = [bytes([0x7F] * SEQ_SIZE)]

    num_seqs = len(sf2_sequences)

    music_data_params = {
        'track_count': 3,
        'ol_ptr_lo_addr':  ol_ptr_lo,
        'ol_ptr_hi_addr':  ol_ptr_hi,
        'seq_count':       min(num_seqs, SEQ_PTR_SIZE),
        'seq_ptr_lo_addr': seq_ptr_lo,
        'seq_ptr_hi_addr': seq_ptr_hi,
        'ol_size':         OL_SIZE,
        'ol_track1_addr':  ol_track1,
        'seq_size':        SEQ_SIZE,
        'seq00_addr':      seq00,
    }

    edit = bytearray()
    # OL ptr lo / hi tables (3 voices each, pointing at their own
    # 256-byte orderlist slot)
    for v in range(3):
        edit.append((ol_track1 + v * OL_SIZE) & 0xFF)
    for v in range(3):
        edit.append(((ol_track1 + v * OL_SIZE) >> 8) & 0xFF)
    # Seq ptr lo / hi tables — populated entries point at consecutive
    # SEQ_SIZE slots starting at seq00
    seq_lo = bytearray(SEQ_PTR_SIZE)
    seq_hi = bytearray(SEQ_PTR_SIZE)
    for s in range(min(num_seqs, SEQ_PTR_SIZE)):
        addr = seq00 + s * SEQ_SIZE
        seq_lo[s] = addr & 0xFF
        seq_hi[s] = (addr >> 8) & 0xFF
    edit.extend(seq_lo)
    edit.extend(seq_hi)
    # 3 orderlists × 256 bytes
    for ol in orderlists:
        edit.extend(ol)
    # N sequences × 256 bytes
    for seq in sf2_sequences:
        edit.extend(seq)

    # F1-F5 placeholder tables (zero-filled) + editor-only Arp/Tempo/HR/Init
    # tables. Block 3 column addresses point HERE (inside the edit area)
    # rather than into high-RAM, so the editor's renderer reads real file
    # bytes (zeros) instead of unpredictable emulated $C000+ contents that
    # may collide with a non-Laxity binary loaded there.
    # Instruments: 32 rows × 6 cols [AD, SR, HR, Filter, Pulse, Wave]. When
    # `instruments` is provided (e.g. the Galway extractor), populate AD/SR
    # per instrument and point its Wave column at a matching wave-table row,
    # so the editor's F2 view shows real instruments instead of empty rows.
    # (For embedded-player files this is a display only — audio comes from
    # the embedded player, not these tables.)
    gen.instr_addr = sf2_data_base + len(edit)
    gen.cmd_addr   = gen.instr_addr + 0x70    # NP21-style bias retained
    instr_tbl = bytearray(32 * 6)
    if instruments:
        for i, ins in enumerate(instruments[:32]):
            ad = getattr(ins, 'ad', 0) & 0xFF
            sr = getattr(ins, 'sr', 0) & 0xFF
            instr_tbl[i * 6:i * 6 + 6] = bytes([ad, sr, 0, 0, 0, i])
    edit.extend(instr_tbl)

    gen.wave_addr  = sf2_data_base + len(edit)
    wave_tbl = bytearray(32 * 2)              # 32 rows × 2 cols [note_off, waveform]
    if instruments:
        for i, ins in enumerate(instruments[:32]):
            ctrl = getattr(ins, 'ctrl', 0) & 0xFF
            wave_tbl[i * 2:i * 2 + 2] = bytes([0x00, ctrl])
    edit.extend(wave_tbl)

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
