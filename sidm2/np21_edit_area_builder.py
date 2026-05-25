"""Builder for the SF2 edit-data area (raw-NP21 path).

Extracted from sf2_writer.py at the v3.5.46 Phase 11 refactor — the
single largest extraction of the decomposition project. The function
was 761 lines and only read three fields from `self.data.header`:
copyright (for V20 / Wizax / Zetrex-YP detection), init_address and
play_address (inputs to the ch_seq_ptr scanner). Otherwise pure,
parameterised on c64_data + sid_la.

# What this builds

Given a Laxity-style NP21 binary at sid_la, this function:

  1. Extracts the 3 voice byte-streams from `ch_seq_ptr` (default
     offsets $0A1C/$0A1F, or relocated via Wizax-A / Zetrex-YP /
     ch_seq_ptr autodetect).
  2. Segments each voice's stream at instrument-prefix boundaries
     into per-voice "patterns" (Stage 2 multi-pattern segmentation).
  3. Converts NP21 byte format to SF2 packed-sequence format
     (close-to-identity except note clamping at 0x6F).
  4. Builds per-voice orderlists referencing the segmented patterns.
  5. Emits Driver-11-format Instruments / Wave / Pulse / Filter
     tables (Stages 3-4), using per-variant detectors when applicable
     (Stinsen / Beast / Angular).
  6. Computes the C64-memory layout of the SF2 edit area immediately
     past the NP21 binary at `sid_la + len(c64_data)`.

# When extraction fails

If no in-range ch_seq_ptr is found (Vibrants V20, or autodetect
falls through), the function emits a "safe placeholder" 3-track
1-sequence editor view so SF2II's ComponentTracks constructor
doesn't OOB-crash. Audio plays via the embedded-binary path either
way.

See `_inject_laxity_raw_np21` in sf2_writer for how this function's
output is consumed: the `raw_patterns` feed the shadow buffer, the
`voice_init_idx` patches `ch_seq_ptr` at the discovered table
location, and `music_data_params` configures Block 5.
"""
from __future__ import annotations
import logging
from typing import List, Optional, Tuple

from .table_extraction import extract_all_laxity_tables

logger = logging.getLogger(__name__)


def build_np21_sf2_edit_area(
    c64_data: bytes,
    sid_la: int,
    *,
    psid_copyright: str = '',
    init_addr: Optional[int] = None,
    play_addr: Optional[int] = None,
) -> Tuple[dict, bytes, List[int], List[Tuple[bytes, Optional[int]]], List[int]]:
    """Extract NP21 patterns/orderlists and build an SF2-format edit data area.

    See module docstring for full semantics.

    Args:
        c64_data: The embedded NP21 binary bytes.
        sid_la: The binary's C64 load address.
        psid_copyright: PSID copyright string. Empty skips V20 / Wizax /
            Zetrex-YP detection.
        init_addr: PSID init address (for ch_seq_ptr autodetect).
            Defaults to sid_la if None.
        play_addr: PSID play address (for ch_seq_ptr autodetect).
            Defaults to sid_la + 3 if None.

    Returns:
        5-tuple (music_data_params, sf2_edit_bytes, voice_init_idx,
        raw_patterns, voice_pat_counts).
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
    # The Stinsen/Unboxed convention places ch_seq_ptr at the binary's
    # $0A1C/$0A1F offsets ($1A1C/$1A1F absolute when sid_la=$1000).
    # Other NP21 variants put it elsewhere. Try the conventional offsets
    # first; if extraction yields no in-range pointers, run the
    # auto-detector (sidm2.ch_seq_ptr_scanner) which combines static
    # disasm of LDA-pair operands with runtime PLAY-read tracing.

    def _read_ptrs(lo_off, hi_off):
        ptrs = []
        for v in range(3):
            if lo_off + v >= len(c64_data) or hi_off + v >= len(c64_data):
                return None
            ptrs.append((c64_data[hi_off + v] << 8) | c64_data[lo_off + v])
        return ptrs

    def _ptrs_in_range(ptrs):
        return all(sid_la <= p < sid_la + len(c64_data) for p in ptrs)

    # Try conventional offsets first
    ptrs = _read_ptrs(CH_SEQ_LO_OFF, CH_SEQ_HI_OFF)
    if ptrs is None or not _ptrs_in_range(ptrs):
        # Wizax-A redirect: pre-NP21 Wizax-A files use a different
        # ptr-table layout than NP21's $0A1C/$0A1F but their byte
        # streams ARE NP21-compatible (notes $01-$6F, durations
        # $80-$9F, $FF loop). Redirect the ch_seq_ptr offsets at
        # Wizax-A's detected ptr-table addresses so the existing
        # F1 extraction + shadow buffer + multipat translator
        # pipeline can process them. v3.5.15 enables F1 (sequences)
        # display + edit propagation for the 4 Wizax-A files.
        # See `memory/wizax-a-byte-stream-re.md`.
        try:
            from sidm2.wizax_a_detector import detect_wizax_a_layout
            from sidm2.zetrex_yp_detector import detect_zetrex_yp_layout
            cpyr = psid_copyright
            wzx = detect_wizax_a_layout(c64_data, sid_la, cpyr)
            zyp = detect_zetrex_yp_layout(c64_data, sid_la, cpyr)
        except Exception:
            wzx = None
            zyp = None
        redirect = wzx or zyp
        redirect_name = 'Wizax-A' if wzx else ('Zetrex/YP' if zyp else None)
        if redirect is not None:
            CH_SEQ_LO_OFF = redirect.ptr_lo_addr - sid_la
            CH_SEQ_HI_OFF = redirect.ptr_hi_addr - sid_la
            ptrs = _read_ptrs(CH_SEQ_LO_OFF, CH_SEQ_HI_OFF)
            if ptrs is not None and _ptrs_in_range(ptrs):
                logger.info(
                    f"  {redirect_name} detected: ptr-table at "
                    f"${redirect.ptr_lo_addr:04X}/${redirect.ptr_hi_addr:04X} "
                    f"(ZP ${redirect.zp_lo:02X}/${redirect.zp_hi:02X}); "
                    f"voice ptrs = {[f'${p:04X}' for p in ptrs]}. "
                    f"Running NP21 F1 pipeline with {redirect_name} redirect."
                )

    if ptrs is None or not _ptrs_in_range(ptrs):
        # Vibrants V20 short-circuit: pre-NP21 player variants have
        # no NP21 ch_seq_ptr at all, and running the autodetect on
        # them yields garbage 2-14 byte "patterns" that mislead the
        # SF2 editor view. For these files, skip the autodetect
        # entirely and emit track_count=0 (honest empty editor view).
        # Audio playback is unaffected — it goes through the
        # embedded-binary path. See `memory/vibrants-v20-findings.md`.
        from sidm2.vibrants_v20_detector import detect_vibrants_v20
        v20_copyright = psid_copyright
        v20_label = detect_vibrants_v20(c64_data, sid_la, v20_copyright)
        if v20_label:
            logger.info(
                f"  Vibrants V20 (pre-NP21) detected: {v20_label}. "
                f"Skipping NP21 autodetect — these files use a different "
                f"player architecture. Audio plays via embedded-binary "
                f"path; editor view stays empty by design "
                f"(see docs/ROADMAP.md → Vibrants V20 section)."
            )
            # ptrs stays None → num_patterns=0 → track_count=0 path
        else:
            # Class B autodetect path (NP21 variant with relocated table)
            try:
                from sidm2.ch_seq_ptr_scanner import detect_ch_seq_ptr
                _init = init_addr if init_addr is not None else sid_la
                _play = play_addr if play_addr is not None else sid_la + 3
                detected = detect_ch_seq_ptr(c64_data, sid_la, _init,
                                             play_addr=_play, n_play_ticks=3)
            except Exception as e:
                logger.debug(f"  ch_seq_ptr autodetect failed: {e}")
                detected = None
            if detected is not None:
                lo_addr, hi_addr, det_ptrs, score = detected
                logger.info(
                    f"  ch_seq_ptr autodetect: lo=${lo_addr:04X} hi=${hi_addr:04X} "
                    f"score={score} ptrs={[f'${p:04X}' for p in det_ptrs]}"
                )
                # Convert absolute back to offsets
                CH_SEQ_LO_OFF = lo_addr - sid_la
                CH_SEQ_HI_OFF = hi_addr - sid_la
                ptrs = det_ptrs

    addr_to_sf2_idx = {}
    raw_patterns = []    # list of (body_bytes, loop_target)

    if ptrs is not None and _ptrs_in_range(ptrs):
        for seq_addr in ptrs:
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
    if ptrs is not None and _ptrs_in_range(ptrs):
        for v in range(3):
            voice_init_idx[v] = addr_to_sf2_idx.get(ptrs[v], 0)

    num_patterns = len(raw_patterns)
    if num_patterns == 0:
        # Pattern extraction failed (ch_seq_ptr at $0A1C/$0A1F doesn't
        # contain valid sequence pointers — happens for NP21 binaries
        # with a different player layout, e.g., Angular and Beast).
        # Returning music_data_params=None used to make
        # create_music_data_block() emit ALL-DEFAULT placeholder
        # addresses ($1900) with track_count=1 — SF2II's editor view
        # then iterates 1 track, reads OOB at $1900, and deterministically
        # crashes on F10-load. Documented 2026-05-06.
        #
        # Workaround: emit track_count=0 + seq_count=0 so the editor
        # iterates zero tracks/sequences and skips the crashing
        # track-display code path entirely. Playback is unaffected
        # because runtime SID emulation reads the embedded NP21 binary
        # via INIT/PLAY vectors, not Block 5 addresses.
        # The Vibrants V20 advisory was already logged at the
        # autodetect short-circuit (see above) for V20-class files.
        # Only emit the generic warning for non-V20 cases where the
        # autodetect genuinely failed.
        from sidm2.vibrants_v20_detector import detect_vibrants_v20
        v20_copy = psid_copyright
        if detect_vibrants_v20(c64_data, sid_la, v20_copy) is None:
            logger.warning(
                "  No NP21 patterns found (ch_seq_ptr at $0A1C/$0A1F "
                "doesn't contain valid sequence pointers); emitting "
                "track_count=0 to avoid SF2II editor-view OOB crash"
            )
        # SF2II's ComponentTracks constructor dereferences
        # `(*m_TracksDataSource)[0]->GetDimensions().m_Width` unconditionally
        # (component_tracks.cpp:47). With an empty data source it OOB-crashes.
        # So we MUST emit a non-empty track structure even when we can't
        # extract real patterns.
        #
        # Build a minimal "1 track + 1 sequence" placeholder block with
        # real SF2-format bytes (0x7F end-of-sequence markers) so the
        # editor's iteration sees valid data. Point all Block 5 addresses
        # at this minimal edit area, appended after the NP21 binary like
        # the normal path.
        OL_SIZE  = 0x100
        SEQ_SIZE = 0x100
        sf2_data_base = sid_la + len(c64_data)
        # Layout (mimicking the normal path for editor-compat):
        #   [0..2]    OL ptr lo table  (3 bytes — for 3 voices)
        #   [3..5]    OL ptr hi table  (3 bytes)
        #   [6..7]    Seq ptr lo table (2 bytes — for 1 sequence × 2 fields? actually used as varint)
        #   [...]     ...
        # Simplest: keep 3-track layout per editor expectations but with
        # all tracks pointing at the same single orderlist + single seq.
        ol_ptr_lo_addr  = sf2_data_base + 0
        ol_ptr_hi_addr  = sf2_data_base + 3
        seq_ptr_lo_addr = sf2_data_base + 6
        seq_ptr_hi_addr = sf2_data_base + 6 + 0x80
        ol_track1_addr  = sf2_data_base + 6 + 2 * 0x80
        seq00_addr      = ol_track1_addr + 3 * OL_SIZE
        safe_params = {
            'track_count':     3,
            'ol_ptr_lo_addr':  ol_ptr_lo_addr,
            'ol_ptr_hi_addr':  ol_ptr_hi_addr,
            'seq_count':       1,
            'seq_ptr_lo_addr': seq_ptr_lo_addr,
            'seq_ptr_hi_addr': seq_ptr_hi_addr,
            'ol_size':         OL_SIZE,
            'ol_track1_addr':  ol_track1_addr,
            'seq_size':        SEQ_SIZE,
            'seq00_addr':      seq00_addr,
        }
        # Build the minimal edit data:
        #   pointer tables: zeros (editor will fill)
        #   3 orderlists × 256 bytes: [0x00, 0xFE, 0xFF*254] each (single
        #     pattern, loop marker, then padded with 0xFF end-markers)
        #   1 sequence × 256 bytes: 0x7F repeated (end-of-sequence)
        edit = bytearray()
        edit.extend(b'\x00' * 3)          # OL ptr lo
        edit.extend(b'\x00' * 3)          # OL ptr hi
        edit.extend(b'\x00' * 0x80)       # Seq ptr lo
        edit.extend(b'\x00' * 0x80)       # Seq ptr hi
        for _ in range(3):                # 3 orderlists, each 256 bytes
            ol = bytearray([0x00, 0xFE])  # single pattern + loop
            while len(ol) < OL_SIZE:
                ol.append(0xFF)
            edit.extend(ol)
        seq = bytearray()                  # single sequence, 256 bytes
        while len(seq) < SEQ_SIZE:
            seq.append(0x7F)               # SF2 end-of-sequence marker
        edit.extend(seq)
        # voice_pat_counts: each voice points at the single placeholder
        # pattern (index 0). Stage 2.5 multi-pattern translator path is
        # not used for empty-pattern files anyway, but the caller unpacks
        # 5 values, so return a 5-tuple to keep arity consistent.
        return safe_params, bytes(edit), [0, 0, 0], [(b'', None)], [1, 1, 1]

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
    # NP21 note byte semantics (verified against player code at $10C9-$1108
    # in drivers/laxity/laxity_player_disassembly.asm:111-156):
    #   0x00         = "no new note this tick" — gate stays in current state.
    #                  At $10F4 the byte is stored to the active-note slot;
    #                  $10F7 BEQ branches to Label_13 which only increments
    #                  the tick counter. NOT "C-0" as v3.1.9 changelog claimed.
    #   0x01 - 0x7D  = playable notes (0x01 = lowest; chromatic).
    #   0x7E         = tie / note-on (Label_14, copies last active note).
    #   0x7F         = true end-of-data (rare; loops use 0xFF/Y-target instead).
    #   0x80 - 0x9F  = duration byte (low nibble = ticks; bit 4 = tie flag).
    #   0xA0 - 0xBF  = set-instrument prefix.
    #   0xC0 - 0xFF  = command prefix (then a payload byte follows).
    #
    # SF2 packed sequence format (DataSourceSequence::Unpack lines 197-267):
    #   0x00         = gate off
    #   0x01 - 0x6F  = notes (0x01 = C-0; SF2 has FEWER pitches than NP21)
    #   0x7E         = tie/note-on (same as NP21)
    #   0x7F         = end of sequence
    #   0x80 - 0x9F  = duration (same encoding as NP21)
    #   0xA0 - 0xBF  = instrument (same)
    #   0xC0 - 0xFF  = command (same)
    #
    # Correct conversion (identity for compatible ranges; map for note 0):
    #   NP21 0x00       → SF2 0x00 (no event / gate off — closest equivalent)
    #   NP21 0x01-0x6F  → SF2 0x01-0x6F (identity)
    #   NP21 0x70-0x7D  → SF2 0x6F (clamp; SF2's pitch range is shorter)
    #   NP21 0x7E       → SF2 0x7E
    #   NP21 0x80+      → SF2 same (identity for all control bytes)
    # The previous +1 shift (v3.1.9 fix) was based on the wrong assumption
    # that NP21 0x00 = C-0 (lowest pitch); fixed in v3.2.2 after verifying
    # against the player disassembly directly. Body bytes no longer contain
    # 0x7F or 0xFF (stripped by _extract_raw_seq).
    # --- Stage 2: per-voice pattern segmentation ---
    # Replace today's "1 SF2 pattern = 1 voice's flat stream" with
    # "N SF2 patterns = N segments of the voice", split at instrument-
    # prefix ($A0-$BF) boundaries. Each voice's segments concatenate
    # back to its original byte stream (round-trip property), so the
    # build-time shadow pre-fill in the outer function can still
    # reconstruct identical flat streams per voice.
    from sidm2.np21_pattern_segmenter import segment_voice_stream

    sf2_sequences = []
    orderlists = []
    # Track which SF2 pattern indices belong to each voice (for orderlists)
    per_voice_pat_indices: list[list[int]] = [[], [], []]
    next_pat_idx = 0

    for v in range(3):
        # Voice v's flat byte stream comes from raw_patterns[voice_init_idx[v]]
        if num_patterns > 0 and 0 <= voice_init_idx[v] < num_patterns:
            voice_body, _loop = raw_patterns[voice_init_idx[v]]
        else:
            voice_body = b""
        segments = segment_voice_stream(voice_body)
        for seg in segments:
            seq = bytearray()
            for b in seg.bytes_:
                # Byte format is identical (NP21 == SF2 packed) for all
                # ranges except 0x7F (we strip those during extraction)
                # and 0x70-0x7D (clamp to SF2 max pitch 0x6F).
                if b == 0x00:
                    seq.append(0x00)
                elif 0x01 <= b <= 0x6F:
                    seq.append(b)
                elif 0x70 <= b <= 0x7D:
                    seq.append(0x6F)
                else:  # 0x7E (tie) and 0x80-0xFF (controls): identity
                    seq.append(b)
            seq.append(0x7F)
            while len(seq) < SEQ_SIZE:
                seq.append(0x7F)
            sf2_sequences.append(bytes(seq[:SEQ_SIZE]))
            per_voice_pat_indices[v].append(next_pat_idx)
            next_pat_idx += 1

    # If a voice produced zero segments (empty stream), give it a
    # placeholder pattern so its orderlist can still terminate cleanly.
    for v in range(3):
        if not per_voice_pat_indices[v]:
            placeholder = bytearray(b'\x7F' * SEQ_SIZE)
            sf2_sequences.append(bytes(placeholder))
            per_voice_pat_indices[v].append(next_pat_idx)
            next_pat_idx += 1

    # Replace num_patterns with the segmented count (defines seq_count
    # in Block 5 + size of seq ptr table population below).
    num_patterns = len(sf2_sequences)

    # Build per-voice orderlists. Each entry: 0xA0 transpose marker
    # (= zero transposition; renderer subtracts 0xA0) followed by the
    # SF2 pattern index. Terminate with 0xFE (no loop).
    # Orderlist parser (datasource_orderlist.cpp:290-365):
    #   - 0x80+ updates current_transposition
    #   - 0x00..0x7F = pattern index (stored with current transposition)
    #   - 0xFE = end (no loop), 0xFF = end-with-loop (next byte = loop idx)
    for v in range(3):
        ol = bytearray()
        for pat_idx in per_voice_pat_indices[v]:
            ol.append(0xA0)              # transpose 0 (re-asserted per entry)
            ol.append(pat_idx & 0x7F)
        ol.append(0xFE)                  # end (no loop)
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
    # The OL ptr and Seq ptr tables MUST be populated at conversion time:
    # SF2II reads them on F10-load to find the orderlists and sequences.
    # The previous "editor writes" comment was wrong — leaving these as
    # zeros made every voice's OL ptr decode to $00xx (zero page), which
    # is why the editor's track view showed empty sequences even though
    # the sequence/OL data was present in the file.
    ol_lo_table = bytearray(b'\x00' * 3)
    ol_hi_table = bytearray(b'\x00' * 3)
    for v in range(3):
        ol_addr = ol_track1_addr + v * OL_SIZE
        ol_lo_table[v] = ol_addr & 0xFF
        ol_hi_table[v] = (ol_addr >> 8) & 0xFF

    seq_lo_table = bytearray(b'\x00' * SEQ_PTR_SIZE)
    seq_hi_table = bytearray(b'\x00' * SEQ_PTR_SIZE)
    for s in range(min(num_patterns, SEQ_PTR_SIZE)):
        seq_addr = seq00_addr + s * SEQ_SIZE
        seq_lo_table[s] = seq_addr & 0xFF
        seq_hi_table[s] = (seq_addr >> 8) & 0xFF

    edit = bytearray()
    edit.extend(ol_lo_table)
    edit.extend(ol_hi_table)
    edit.extend(seq_lo_table)
    edit.extend(seq_hi_table)
    for ol in orderlists:
        edit.extend(ol)
    for seq in sf2_sequences:
        edit.extend(seq)

    # --- Stages 3 + 4: clean Driver-11-format tables in edit area ---
    # The NP21 binary at $1000 has Laxity-specific table formats that
    # look like garbage when SF2II's editor reads them through its
    # Driver-11 column interpretation (Block 3 column counts: Instr=6,
    # Wave=2, Pulse=3, Filter=3). Stages 3-4 emit clean Driver-11
    # tables in the SF2 edit area and repoint Block 3 column addresses
    # at them. Display only: F2/F3/F4/F5 edits don't propagate to
    # playback because the NP21 binary keeps reading its own table data.
    from sidm2.instrument_extraction import extract_laxity_instruments
    from sidm2.stinsen_instr_detector import extract_stinsen_instruments
    from sidm2.beast_instr_detector import extract_beast_instruments
    from sidm2.angular_instr_detector import extract_angular_instruments

    # Stage 3 — Instruments (6 bytes per row)
    instr_table_offset = len(edit)
    instr_table_addr   = sf2_data_base + instr_table_offset

    # Stage 7 Phase B.2: when the binary matches a known per-variant
    # layout, extract REAL AD/SR values into the SF2 view so F2 edits
    # have something meaningful to alter. Stinsen-class column-major
    # at $1808/$181C; Beast-class row-major 8B/instr at $1B38
    # (AD@+5, SR@+6); Angular-class row-major 2B/instr at $1ADB.
    # Other variants fall through to extract_laxity_instruments.
    try:
        laxity_instrs = extract_stinsen_instruments(c64_data, sid_la)
        if laxity_instrs is not None:
            logger.info(
                f"  Stage 3: Stinsen layout detected — "
                f"{len(laxity_instrs)} instruments from column-major "
                f"table (AD@${sid_la + 0x808:04X} SR@${sid_la + 0x81C:04X})"
            )
        elif (beast_i := extract_beast_instruments(c64_data, sid_la)) is not None:
            laxity_instrs = beast_i
            logger.info(
                f"  Stage 3: Beast layout detected — "
                f"{len(laxity_instrs)} instruments from row-major "
                f"table (AD@+5 SR@+6 from ${sid_la + 0xB38:04X})"
            )
        elif (ang_i := extract_angular_instruments(c64_data, sid_la)) is not None:
            laxity_instrs = ang_i
            logger.info(
                f"  Stage 3: Angular layout detected — "
                f"{len(laxity_instrs)} instruments from row-major "
                f"2B-row table at ${sid_la + 0xADB:04X}"
            )
        else:
            laxity_instrs = extract_laxity_instruments(c64_data, sid_la)
    except Exception as e:
        logger.warning(f"  Stage 3 instrument extract failed: {e!r}; "
                       f"falling back to NP21 instr_addr (garbled F2 view)")
        laxity_instrs = []

    # Stage 5: instrument byte order matches Driver 11 reference layout
    # (matters for Block 9 DriverInstrumentDataDescriptor below — Block 9
    # tells SF2II which byte position holds which table-program index):
    #   byte 0: AD          (Attack/Decay)
    #   byte 1: SR          (Sustain/Release)
    #   byte 2: HR          (Hard-Restart flags; bit 0x40 enables filter)
    #   byte 3: Filter      (filter program index; only used when HR bit 6 set)
    #   byte 4: Pulse       (pulse program index)
    #   byte 5: Wave        (wave program index)
    # The "waveform character" byte (0x41/Pulse, 0x21/Saw, etc.) is NOT
    # stored in the instrument row — it's derived from wave_table[wave][1]
    # at runtime.
    instr_count = 0
    for instr in laxity_instrs:
        ad      = instr.get('ad', 0) & 0xFF
        sr      = instr.get('sr', 0) & 0xFF
        hr      = instr.get('restart', 0) & 0xFF
        # extract_laxity_instruments doesn't expose a per-instrument
        # filter program ptr (NP21's filter selection is global per
        # song, not per instrument). Emit 0; Block 9 makes filter
        # column conditional on HR bit 0x40 anyway, so 0 = "no filter".
        filt    = 0
        pulse   = instr.get('pulse_ptr', 0) & 0xFF
        wave    = instr.get('wave_ptr', 0) & 0xFF
        edit.extend(bytes([ad, sr, hr, filt, pulse, wave]))
        instr_count += 1

    MIN_INSTR_ROWS = 16
    while instr_count < MIN_INSTR_ROWS:
        edit.extend(bytes([0x00, 0x00, 0x00, 0x00, 0x00, 0x00]))
        instr_count += 1

    # Stage 4 — Wave / Pulse / Filter tables.
    # extract_all_laxity_tables returns the player's tables in their
    # native NP21 layouts; we re-pack them to Driver 11 column counts.
    try:
        laxity_tables = extract_all_laxity_tables(c64_data, sid_la)
    except Exception as e:
        logger.warning(f"  Stage 4 table extract failed: {e!r}")
        laxity_tables = {}

    # Wave: NP21 wave_table is already (note_offset, waveform) pairs
    # — exactly Driver 11's 2-byte row layout. Direct copy.
    wave_table_offset = len(edit)
    wave_table_addr   = sf2_data_base + wave_table_offset
    wave_entries = laxity_tables.get('wave_table', []) or []
    wave_rows = 0
    for note_off, waveform in wave_entries:
        edit.extend(bytes([note_off & 0xFF, waveform & 0xFF]))
        wave_rows += 1
    # Pad to a useful editor view (32 visible rows minimum)
    while wave_rows < 32:
        edit.extend(bytes([0x7F, 0x00]))   # 0x7F = end-of-program
        wave_rows += 1

    # Pulse: NP21 pulse rows are 4-byte tuples; Block 3 declares Pulse
    # with 3 columns. Emit (b0, b1, b2) — drop the last byte, which is
    # the "next-program" pointer in NP21 internals and not part of
    # Driver 11's 3-column display anyway.
    #
    # Stage 7 Phase B.2 (F4 Stinsen override): when the binary matches
    # Stinsen-class pulse layout, replace the 4-byte-tuple
    # interpretation with the ACTUAL PW lo / PW hi bytes from
    # $1957 / $193E. This gives the editor a coherent semantics
    # ("col 0 = PW lo, col 1 = PW hi") that matches what
    # _emit_pulse_split_copy_routine writes back. Verified
    # 2026-05-11; see memory/stinsen-pulse-architecture.md.
    pulse_table_offset = len(edit)
    pulse_table_addr   = sf2_data_base + pulse_table_offset
    pulse_rows = 0
    used_variant_pulse = False
    try:
        from sidm2.stinsen_pulse_detector import detect_stinsen_pulse_layout
        from sidm2.beast_pulse_detector import detect_beast_pulse_layout
        from sidm2.angular_pulse_detector import detect_angular_pulse_layout
        sp_stinsen = detect_stinsen_pulse_layout(c64_data, sid_la)
        sp_beast   = detect_beast_pulse_layout(c64_data, sid_la)
        sp_angular = detect_angular_pulse_layout(c64_data, sid_la)
    except Exception:
        sp_stinsen = sp_beast = sp_angular = None
    if sp_stinsen is not None:
        lo_off = sp_stinsen.pw_lo_addr - sid_la
        hi_off = sp_stinsen.pw_hi_addr - sid_la
        for r in range(sp_stinsen.n_steps):
            if lo_off + r >= len(c64_data) or hi_off + r >= len(c64_data):
                break
            edit.extend(bytes([c64_data[lo_off + r], c64_data[hi_off + r], 0x00]))
            pulse_rows += 1
        used_variant_pulse = pulse_rows > 0
    elif sp_beast is not None or sp_angular is not None:
        # Beast / Angular: 4-byte step records starting at stream_addr.
        # SF2 cols 0/1/2 ← np21 bytes 0/1/2 (byte 3 preserved).
        sp = sp_beast if sp_beast is not None else sp_angular
        base_off = sp.stream_addr - sid_la
        for r in range(sp.n_steps):
            if base_off + r * 4 + 3 > len(c64_data):
                break
            edit.extend(bytes([c64_data[base_off + r * 4 + 0],
                               c64_data[base_off + r * 4 + 1],
                               c64_data[base_off + r * 4 + 2]]))
            pulse_rows += 1
        used_variant_pulse = pulse_rows > 0
    if not used_variant_pulse:
        pulse_entries = laxity_tables.get('pulse_table', []) or []
        for entry in pulse_entries:
            row = bytes(entry)[:3]
            if len(row) < 3:
                row = row + bytes(3 - len(row))
            edit.extend(row)
            pulse_rows += 1
    while pulse_rows < 16:
        edit.extend(bytes([0x7F, 0x00, 0x00]))
        pulse_rows += 1

    # Filter: NP21 stores three parallel arrays (cmd/val/aux) that
    # form a state machine. Block 3 declares Filter as a 3-column
    # table for the editor view.
    #
    # Stage 7 Phase B.2 (F5 Stinsen override): when the binary
    # matches Stinsen-class filter layout, populate cols 0/1/2 from
    # the actual byte streams at $1989/$19A3/$19BD — the addresses
    # that `_emit_filter_split_copy_routine` writes back to. This
    # gives a coherent edit→playback path. The state-machine
    # interpretation lives in the player ($15F6-$167F handler), so
    # the SF2 view shows raw bytes; users editing need to know the
    # cmd-byte bit-7 dispatch (SET vs SWEEP). Verified 2026-05-11;
    # see memory/stinsen-filter-architecture.md.
    filter_table_offset = len(edit)
    filter_table_addr   = sf2_data_base + filter_table_offset
    filter_rows = 0
    used_variant_filter = False
    try:
        from sidm2.stinsen_filter_detector import detect_stinsen_filter_layout
        from sidm2.beast_filter_detector import detect_beast_filter_layout
        from sidm2.angular_filter_detector import detect_angular_filter_layout
        sf_stinsen = detect_stinsen_filter_layout(c64_data, sid_la)
        sf_beast   = detect_beast_filter_layout(c64_data, sid_la)
        sf_angular = detect_angular_filter_layout(c64_data, sid_la)
    except Exception:
        sf_stinsen = sf_beast = sf_angular = None
    if sf_stinsen is not None:
        cmd_off = sf_stinsen.cmd_addr - sid_la
        val_off = sf_stinsen.val_addr - sid_la
        aux_off = sf_stinsen.aux_addr - sid_la
        for r in range(sf_stinsen.n_steps):
            if cmd_off + r >= len(c64_data) or val_off + r >= len(c64_data) or aux_off + r >= len(c64_data):
                break
            edit.extend(bytes([c64_data[cmd_off + r],
                               c64_data[val_off + r],
                               c64_data[aux_off + r]]))
            filter_rows += 1
        used_variant_filter = filter_rows > 0
    elif sf_beast is not None:
        # Beast/Angular: only cutoff_hi byte stream propagates;
        # cols 1+2 emit the binary's current $100A/$1009 bytes for
        # editor-view consistency (edits to cols 1+2 won't propagate
        # but the displayed values match what plays).
        cutoff_off = sf_beast.cutoff_hi_stream_addr - sid_la
        for r in range(sf_beast.n_steps):
            if cutoff_off + r >= len(c64_data):
                break
            edit.extend(bytes([c64_data[cutoff_off + r],
                               c64_data[0x000A] if 0x000A < len(c64_data) else 0,   # $100A res_routing
                               c64_data[0x0009] if 0x0009 < len(c64_data) else 0]))  # $1009 mode_vol
            filter_rows += 1
        used_variant_filter = filter_rows > 0
    elif sf_angular is not None:
        cutoff_off = sf_angular.cutoff_hi_stream_addr - sid_la
        for r in range(sf_angular.n_steps):
            if cutoff_off + r >= len(c64_data):
                break
            edit.extend(bytes([c64_data[cutoff_off + r],
                               c64_data[0x000A] if 0x000A < len(c64_data) else 0,
                               c64_data[0x0009] if 0x0009 < len(c64_data) else 0]))
            filter_rows += 1
        used_variant_filter = filter_rows > 0
    if not used_variant_filter:
        # Fallback: existing extract-based 3-byte interpretation
        filter_entries = laxity_tables.get('filter_table', []) or []
        for entry in filter_entries:
            row = bytes(entry) if isinstance(entry, (bytes, bytearray)) else bytes(entry[:3])
            if len(row) < 3:
                row = row + bytes(3 - len(row))
            elif len(row) > 3:
                row = row[:3]
            edit.extend(row)
            filter_rows += 1
    while filter_rows < 16:
        edit.extend(bytes([0x7F, 0x00, 0x00]))
        filter_rows += 1

    logger.info(
        f"  SF2 edit area: base=${sf2_data_base:04X}, "
        f"OL=${ol_track1_addr:04X}, Seq=${seq00_addr:04X} "
        f"({num_patterns} pat×{SEQ_SIZE}B), Instr=${instr_table_addr:04X} "
        f"({instr_count}×6B), Wave=${wave_table_addr:04X} ({wave_rows}×2B), "
        f"Pulse=${pulse_table_addr:04X} ({pulse_rows}×3B), "
        f"Filter=${filter_table_addr:04X} ({filter_rows}×3B)"
    )

    # Stage 2.5: per-voice segment counts feed the multi-pattern
    # translator at $0F0E. Total of voice_pat_counts == num_patterns.
    voice_pat_counts = [len(per_voice_pat_indices[v]) for v in range(3)]

    # Stages 3 + 4: report new table addresses so caller can update
    # gen.instr_addr / wave_addr / pulse_addr / filter_addr before
    # regenerating Block 3.
    music_data_params['edit_instr_addr']  = instr_table_addr
    music_data_params['edit_instr_count'] = instr_count
    music_data_params['edit_wave_addr']   = wave_table_addr
    music_data_params['edit_pulse_addr']  = pulse_table_addr
    music_data_params['edit_filter_addr'] = filter_table_addr

    # v3.5.17 fix: expose the (possibly autodetected, possibly redirected)
    # ch_seq_ptr table absolute addresses so _inject_laxity_raw_np21 can
    # patch at the SAME location we extracted pointers from. Without
    # this, the injector defaults to $0A1C/$0A1F and clobbers
    # non-ch_seq_ptr data on files whose actual table is elsewhere
    # (e.g. Angular: ch_seq_ptr at $1B2C/$1B2F, but $1A1F-$1A22 is
    # state-machine data the player reads via LDA $1A1F,Y at $10F7).
    # Only set when the table was successfully located (ptrs in range).
    if ptrs is not None and _ptrs_in_range(ptrs):
        music_data_params['ch_seq_lo_addr'] = sid_la + CH_SEQ_LO_OFF
        music_data_params['ch_seq_hi_addr'] = sid_la + CH_SEQ_HI_OFF

    return music_data_params, bytes(edit), voice_init_idx, raw_patterns, voice_pat_counts
