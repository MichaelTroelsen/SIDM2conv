"""Laxity driver template-path music data injector.

Extracted from sf2_writer.py at the v3.5.47 Phase 12 refactor.

The Laxity driver template (v1.6, `sf2driver_laxity_00.prg`) ships a
relocated Laxity player at $0E00-$16FF with embedded default tables,
SF2 header blocks at $1700-$18FF, and a music data area starting at
$1900. This function patches that template:

  - INIT dispatch fix at $0E00 (steals-return-addr bug)
  - 40 hardcoded pointer patches throughout the player
  - Orderlist injection at $1900 (3 tracks x 256 bytes max)
  - Sequence injection after orderlists
  - Tempo / arp / filter / wave / pulse / instrument tables
  - Per-voice scratch initialization

Operates entirely on `output: bytearray` + reads from `data: ExtractedData`.
No SF2Writer state required beyond those two.

# Public API

  inject_laxity_music_data(output, data) -> None

Mutates `output` in place. No return value.
"""
from __future__ import annotations
import logging
import struct

logger = logging.getLogger(__name__)


def inject_laxity_music_data(output: bytearray, data) -> None:
    """Inject music data into the Laxity driver template (native format).

    Args:
        output: The SF2 file's PRG buffer (mutated in place). Must
            already contain the Laxity driver template at $0D7E with
            the load-address bytes at offset 0-1.
        data: An ExtractedData instance providing sequences, orderlists,
            instruments, tempo, arp_table, hr_table, filter_table,
            wave_table, pulse_table, c64_data, load_address, etc.

    Side effects:
        - Patches the driver INIT dispatch at $0E00.
        - Writes 40 hardcoded pointer patches throughout the relocated
          player.
        - Populates orderlists at $1900, sequences after, and the
          Driver-11-format tables.
    """
    logger.info("Injecting Laxity music data (native format)...")

    # Get load address from PRG file (first 2 bytes)
    if len(output) < 2:
        logger.error(
            "  Output file too small to contain load address\n"
            "  Suggestion: Check if SF2 data was generated correctly\n"
            "  Check: Verify all required blocks were written\n"
            "  See: docs/guides/TROUBLESHOOTING.md#sf2-generation-failures"
        )
        return

    load_addr = struct.unpack('<H', output[0:2])[0]
    logger.debug(f"  Load address: ${load_addr:04X}")

    # Helper to convert memory address to file offset
    def addr_to_offset(addr: int) -> int:
        return addr - load_addr + 2  # +2 for PRG load address bytes

    # ===== INIT DISPATCH PATCH ($0E00) =====
    # The driver INIT at $0D89 calls JSR $0E00.  The dispatch table at $0E00 was:
    #   4C 92 14  JMP $1492   ← steals the return addr so $0E06 (full init) is never reached
    #   4C 9B 14  JMP $149B
    # Fix: change first entry to JSR $1492 and redirect second to JMP $0E06 so the
    # full init ($0E06: zero voices, set $1583=$02, set $1581=$80) runs during INIT.
    _off_0e00 = addr_to_offset(0x0E00)
    _off_0e03 = addr_to_offset(0x0E03)
    if (len(output) > _off_0e03 + 2
            and output[_off_0e00]     == 0x4C    # JMP $1492
            and output[_off_0e00 + 1] == 0x92
            and output[_off_0e00 + 2] == 0x14):
        output[_off_0e00] = 0x20                  # JSR $1492
        output[_off_0e03]     = 0x4C              # JMP $0E06
        output[_off_0e03 + 1] = 0x06
        output[_off_0e03 + 2] = 0x0E
        logger.debug("  INIT patch applied: $0E00 JMP->JSR $1492, $0E03 -> JMP $0E06")
    else:
        logger.warning(f"  INIT patch skipped: unexpected bytes at $0E00: "
                       f"{output[_off_0e00]:02X} {output[_off_0e00+1]:02X} {output[_off_0e00+2]:02X}")

    # ===== PLAY ENTRY PATCH ($0D97) =====
    # The PLAY wrapper at $0D91 calls JSR $0EA1, which is a mid-voice-loop entry
    # point that expects X=voice and FC set up — it never decrements the frame
    # counter ($1583) so the voice loop at $0E6D never runs and no SID writes occur.
    # Fix: redirect to JSR $0E06 (the real frame-tick routine) which decrements
    # $1583 and drives the full 3-voice loop + SID output on every PLAY call.
    _off_0d97 = addr_to_offset(0x0D97)
    if (len(output) > _off_0d97 + 2
            and output[_off_0d97]     == 0x20    # JSR
            and output[_off_0d97 + 1] == 0xA1    # lo: $A1
            and output[_off_0d97 + 2] == 0x0E):  # hi: $0E  → JSR $0EA1
        output[_off_0d97 + 1] = 0x06             # → JSR $0E06
        logger.debug("  PLAY patch applied: $0D97 JSR $0EA1 -> JSR $0E06")
    else:
        logger.warning(f"  PLAY patch skipped: unexpected bytes at $0D97: "
                       f"{output[_off_0d97]:02X} {output[_off_0d97+1]:02X} {output[_off_0d97+2]:02X}")

    #  ===== POINTER PATCHING FOR RELOCATED LAXITY PLAYER =====
    # The relocated Laxity player contains hardcoded pointers to orderlist/sequence locations
    # Original addresses after -$0200 relocation: $1698-$1898
    # We need to inject at $1900-$1B00 (to avoid SF2 header conflict at $1700)
    # So we must patch all instructions that reference $1698-$1A98 to point to $1900-$1B00

    logger.info("  Patching orderlist pointers in relocated player...")

    # CRITICAL NOTE (v2.9.1): Pointer patches commented out because they're outdated
    # for the current driver version. The Laxity driver binary has been pre-patched
    # during creation with pointers that already point to the correct locations.
    # Testing if music injection alone works without additional patching.

    # Read per-song NP21 voice orderlist start addresses from SID binary.
    # tbl_seq_ptr_lo/hi at load_addr+$0A1C / load_addr+$0A1F hold initial
    # orderlist positions for voices 0-2. These are used to redirect the
    # relocated NP21 player's orderlist pointer patches to the correct addresses.
    _c64 = getattr(data, 'c64_data', None)
    _sid_la = getattr(data, 'load_address', 0x1000)
    if _c64 and len(_c64) > 0x0A21:
        _v_ol_lo = [_c64[0x0A1C + v] for v in range(3)]
        _v_ol_hi = [_c64[0x0A1F + v] for v in range(3)]
    else:
        _v_ol_lo = [0x70, 0x9B, 0xB3]  # NP21 defaults (load $1000)
        _v_ol_hi = [0x1A, 0x1A, 0x1A]
    logger.info(f"  NP21 voice OL addrs: "
                f"v0=${_v_ol_hi[0]:02X}{_v_ol_lo[0]:02X} "
                f"v1=${_v_ol_hi[1]:02X}{_v_ol_lo[1]:02X} "
                f"v2=${_v_ol_hi[2]:02X}{_v_ol_lo[2]:02X}")

    # Define all pointer patches (from trace_orderlist_access.py output)
    # Format: (file_offset, old_lo, old_hi, new_lo, new_hi)
    # NOTE: "old" addresses are AFTER -$0200 relocation (driver template is already relocated)
    pointer_patches = [
        # Sequence/data references (after -$0200 relocation)
        (0x01C6, 0xD8, 0x16, 0x40, 0x19),  # $16D8 -> $1940
        (0x01CC, 0xD9, 0x16, 0x41, 0x19),  # $16D9 -> $1941
        (0x02AD, 0xB7, 0x16, 0x1F, 0x19),  # $16B7 -> $191F (11 instances)
        (0x02BE, 0xB7, 0x16, 0x1F, 0x19),
        (0x02D4, 0xB7, 0x16, 0x1F, 0x19),
        (0x02ED, 0xB7, 0x16, 0x1F, 0x19),
        (0x0300, 0xB7, 0x16, 0x1F, 0x19),
        (0x030E, 0xB7, 0x16, 0x1F, 0x19),
        (0x0335, 0xB7, 0x16, 0x1F, 0x19),
        (0x0347, 0xB7, 0x16, 0x1F, 0x19),
        (0x0353, 0xB7, 0x16, 0x1F, 0x19),
        (0x0361, 0xB7, 0x16, 0x1F, 0x19),
        (0x0372, 0xB7, 0x16, 0x1F, 0x19),
        (0x0380, 0xB7, 0x16, 0x1F, 0x19),
        # Voice orderlist pointers: patched to actual SID orderlist addresses per-song
        (0x057A, 0x3E, 0x17, _v_ol_lo[0], _v_ol_hi[0]),  # voice 0 OL (2 instances)
        (0x058D, 0x3E, 0x17, _v_ol_lo[0], _v_ol_hi[0]),
        (0x0581, 0x70, 0x17, _v_ol_lo[1], _v_ol_hi[1]),  # voice 1 OL (2 instances)
        (0x05B8, 0x70, 0x17, _v_ol_lo[1], _v_ol_hi[1]),
        (0x0595, 0x57, 0x17, _v_ol_lo[2], _v_ol_hi[2]),  # voice 2 OL (instance 1)
        (0x05A4, 0x57, 0x17, _v_ol_lo[2], _v_ol_hi[2]),  # voice 2 OL (instance 2)
        (0x05C8, 0xDA, 0x16, 0x42, 0x19),  # $16DA -> $1942 (2 instances)
        (0x05D6, 0xDA, 0x16, 0x42, 0x19),
        (0x05CF, 0x0C, 0x17, 0x74, 0x19),  # $170C -> $1974 (2 instances)
        (0x05DC, 0x0C, 0x17, 0x74, 0x19),
        (0x0684, 0x89, 0x17, 0xD0, 0x19),  # $1789 -> $19D0 (3 instances, filter_seq)
        (0x069D, 0x89, 0x17, 0xD0, 0x19),
        (0x06A7, 0x89, 0x17, 0xD0, 0x19),
        (0x068C, 0xBD, 0x17, 0x04, 0x1A),  # $17BD -> $1A04 (4 instances, filter_res)
        (0x0699, 0xBD, 0x17, 0x04, 0x1A),
        (0x06B5, 0xBD, 0x17, 0x04, 0x1A),
        (0x06BE, 0xBD, 0x17, 0x04, 0x1A),
        (0x06AF, 0xA3, 0x17, 0xEA, 0x19),  # $17A3 -> $19EA (filter_spd, step-advance path)
        # Sweep path: hold/accumulate code at $143F also references filter tables
        # but these instances were missing from the original patch set.
        # Sweep path: hold/accumulate code at $143F also references filter tables
        (0x06C8, 0xA3, 0x17, 0xEA, 0x19),  # $17A3 -> $19EA (filter_spd, sweep acc path)
        (0x06D1, 0x89, 0x17, 0xD0, 0x19),  # $1789 -> $19D0 (filter_seq, cutoff hi update)
        # Fix filter output: original NP21 uses LSR $FC for all 4 shifts;
        # SF2 template incorrectly uses LSR $EC for shifts 2-4, which corrupts
        # D416 with pattern-pointer LO bytes from voice processing.
        # Patch: 46 EC (LSR $EC) -> 46 FC (LSR $FC) at 3 locations.
        (0x06EA, 0x46, 0xEC, 0x46, 0xFC),  # $1466: LSR $EC -> LSR $FC
        (0x06ED, 0x46, 0xEC, 0x46, 0xFC),  # $1469: LSR $EC -> LSR $FC
        (0x06F0, 0x46, 0xEC, 0x46, 0xFC),  # $146C: LSR $EC -> LSR $FC
        (0x052A, 0xD7, 0x17, 0x3F, 0x1A),  # $17D7 -> $1A3F
        # Table references (after -$0200 relocation)
        (0x00DE, 0x19, 0x18, 0x81, 0x1A),  # $1819 -> $1A81 (3 instances - instrument table)
        (0x00E5, 0x19, 0x18, 0x81, 0x1A),
        (0x0394, 0x19, 0x18, 0x81, 0x1A),
        (0x0103, 0x1C, 0x18, 0x84, 0x1A),  # $181C -> $1A84
        (0x0108, 0x1F, 0x18, 0x87, 0x1A),  # $181F -> $1A87
        (0x038A, 0x1A, 0x18, 0x82, 0x1A),  # $181A -> $1A82
        (0x0141, 0x22, 0x18, (_sid_la + 0x0A22) & 0xFF, ((_sid_la + 0x0A22) >> 8) & 0xFF),  # $1822 -> $1A22 (pattern ptr lo table)
        (0x0146, 0x49, 0x18, (_sid_la + 0x0A49) & 0xFF, ((_sid_la + 0x0A49) >> 8) & 0xFF),  # $1849 -> $1A49 (pattern ptr hi table)
    ]

    # Apply the 40 working pointer patches from commit 08337f3
    patches_applied = 0
    for file_offset, old_lo, old_hi, new_lo, new_hi in pointer_patches:
        if file_offset + 1 < len(output):
            # Verify old values match (safety check)
            current_lo = output[file_offset]
            current_hi = output[file_offset + 1]

            if current_lo == old_lo and current_hi == old_hi:
                output[file_offset] = new_lo
                output[file_offset + 1] = new_hi
                patches_applied += 1
            else:
                logger.warning(f"    Patch mismatch at ${file_offset:04X}: expected {old_lo:02X} {old_hi:02X}, found {current_lo:02X} {current_hi:02X}")

    logger.info(f"  Applied {patches_applied} pointer patches")

    # Now inject orderlists at the safe location $1900-$1B00
    orderlist_start = 0x1900

    # Calculate file offsets
    orderlist_offset = addr_to_offset(orderlist_start)

    # Ensure file is large enough
    min_size = orderlist_offset + (3 * 256) + 1024  # Orderlists + sequences
    if len(output) < min_size:
        logger.debug(f"  Extending file to {min_size} bytes")
        output.extend(bytearray(min_size - len(output)))

    logger.info(f"  Orderlist offset: ${orderlist_offset:04X} (mem: ${orderlist_start:04X})")

    # Inject orderlists (3 tracks, native Laxity format)
    if data.orderlists and len(data.orderlists) > 0:
        logger.info(f"  Injecting {len(data.orderlists)} orderlists...")

        for track_idx, orderlist in enumerate(data.orderlists[:3]):  # Max 3 tracks
            track_offset = orderlist_offset + (track_idx * 256)

            # Initialize full 256-byte block with $00
            for i in range(256):
                output[track_offset + i] = 0x00

            # Write orderlist entries (native Laxity format)
            for i, entry in enumerate(orderlist[:256]):  # Max 256 entries
                if isinstance(entry, dict):
                    # Extract sequence index and transpose
                    seq_idx = entry.get('sequence', 0)
                    transpose = entry.get('transpose', 0xA0)  # Default no transpose

                    # Laxity orderlist format: [sequence_idx, transpose]
                    output[track_offset + i] = seq_idx & 0xFF
                elif isinstance(entry, tuple) and len(entry) >= 2:
                    # Tuple format: (transpose, seq_idx)
                    seq_idx = entry[1]
                    output[track_offset + i] = seq_idx & 0xFF
                elif isinstance(entry, int):
                    # Direct sequence index
                    output[track_offset + i] = entry & 0xFF
                else:
                    output[track_offset + i] = 0x00

            # Mark end with 0xFF
            if len(orderlist) < 256:
                output[track_offset + len(orderlist)] = 0xFF

            logger.debug(f"    Track {track_idx+1}: {len(orderlist)} entries at ${track_offset:04X}")

    # Inject sequences after orderlists
    sequence_start = orderlist_start + (3 * 256)  # After 3 orderlist tracks
    sequence_offset = addr_to_offset(sequence_start)

    # Prefer raw_sequences for Laxity driver: the NP21 player reads native sequence
    # bytes directly, so we must inject them verbatim. The translated data.sequences
    # only carries note events and silently drops all command bytes (filter triggers $C4/$CC,
    # portamento $81, etc.), causing 0% filter accuracy and other playback errors.
    raw_seqs = getattr(data, 'raw_sequences', None) or []
    seq_source = raw_seqs if raw_seqs else (data.sequences or [])
    seq_source_label = "raw" if raw_seqs else "translated"

    if seq_source:
        logger.info(f"  Injecting {len(seq_source)} sequences ({seq_source_label})...")
        current_offset = sequence_offset

        for seq_idx, sequence in enumerate(seq_source):
            if not sequence:
                continue

            if isinstance(sequence, (bytes, bytearray)):
                # Raw bytes — inject verbatim (preserves all NP21 commands)
                seq_bytes = bytearray(sequence)
                # Ensure terminated with $7F if not already
                if not seq_bytes or seq_bytes[-1] != 0x7F:
                    seq_bytes.append(0x7F)
            else:
                # Translated event list fallback
                seq_bytes = bytearray()
                for event in sequence:
                    if isinstance(event, dict):
                        note = event.get('note', 0)
                        gate = event.get('gate', False)
                        if gate:
                            seq_bytes.append(0x7E)
                        seq_bytes.append(note & 0x7F)
                    elif isinstance(event, int):
                        seq_bytes.append(event & 0xFF)
                seq_bytes.append(0x7F)

            # Extend output if needed
            if current_offset + len(seq_bytes) > len(output):
                output.extend(bytearray(
                    current_offset + len(seq_bytes) - len(output)))

            for i, byte in enumerate(seq_bytes):
                output[current_offset + i] = byte

            logger.debug(f"    Sequence {seq_idx}: {len(seq_bytes)} bytes at ${current_offset:04X}")
            current_offset += len(seq_bytes)

    # Inject tables after sequences
    # Memory layout: $1900-$1B00 (orderlists), $1B00+ (sequences), then tables

    # Calculate table injection addresses based on pointer patches
    # All patches add +$0268 offset to relocated addresses
    # Instrument table: original $1A19, relocated $1819, patched -> $1A81
    # So inject at $1A81 (not $1A00!)
    instrument_table_start = 0x1A81  # Matches patched pointer $1819 -> $1A81
    wave_table_start = 0x1942        # Matches patched pointer $16DA -> $1942
    pulse_table_start = 0x1E00       # Estimated (no specific patches found yet)
    # Laxity NP21 filter uses three parallel tables (confirmed via Regenerator 2000).
    # Pointer patches redirect the player to read from these relocated addresses:
    #   tbl_filter_seq   : $1789 (orig $1989 - $0200) -> patched to $19D0
    #   tbl_filter_speed : $17A3 (orig $19A3 - $0200) -> patched to $19EA
    #   tbl_filter_res   : $17BD (orig $19BD - $0200) -> patched to $1A04
    # Tables packed at $19D0-$1A1D (before music block at $1A22).
    # Injection must match the patched pointer targets.
    # Filter tables must be entirely before the music block at $1A22.
    # Pack at $19D0/$19EA/$1A04 → all 78 bytes end at $1A1D (< $1A22).
    filter_seq_start  = 0x19D0   # tbl_filter_seq:       cutoff control + mode bits
    filter_spd_start  = 0x19EA   # tbl_filter_speed:     cutoff sweep delta
    filter_res_start  = 0x1A04   # tbl_filter_resonance: resonance per step

    # Inject wave table - FIXED: Laxity uses TWO SEPARATE ARRAYS, not interleaved pairs
    if hasattr(data, 'wavetable') and data.wavetable:
        # De-interleave SF2 format (waveform, note_offset pairs) into two arrays
        wave_data = data.wavetable

        # Extract waveforms and note offsets from interleaved pairs
        waveforms = bytearray()
        note_offsets = bytearray()

        for i in range(0, len(wave_data), 2):
            if i + 1 < len(wave_data):
                waveform = wave_data[i] if isinstance(wave_data[i], int) else wave_data[i][0]
                note_offset = wave_data[i+1] if isinstance(wave_data[i+1], int) else wave_data[i+1][0]
                waveforms.append(waveform)
                note_offsets.append(note_offset)

        # Laxity format: Two separate arrays with 50-byte offset
        # Based on pointer patches: waveforms at $1942, note offsets at $1974
        waveform_addr = wave_table_start  # $1942
        note_offset_addr = wave_table_start + 0x32  # $1974 ($1942 + 50 bytes)

        # Calculate file offsets
        waveform_file_offset = addr_to_offset(waveform_addr)
        note_offset_file_offset = addr_to_offset(note_offset_addr)

        # Ensure file is large enough
        max_offset = max(waveform_file_offset + len(waveforms),
                       note_offset_file_offset + len(note_offsets))
        if len(output) < max_offset:
            output.extend(bytearray(max_offset - len(output)))

        # Write waveforms array
        for i, byte in enumerate(waveforms):
            output[waveform_file_offset + i] = byte

        # Write note offsets array
        for i, byte in enumerate(note_offsets):
            output[note_offset_file_offset + i] = byte

        logger.info(f"  Injected wave table (Laxity format):")
        logger.info(f"    Waveforms: {len(waveforms)} bytes at ${waveform_addr:04X}")
        logger.info(f"    Note offsets: {len(note_offsets)} bytes at ${note_offset_addr:04X}")

    # Inject pulse table
    if hasattr(data, 'pulsetable') and data.pulsetable:  # RE-ENABLED after wave fix
        pulse_offset = addr_to_offset(pulse_table_start)
        pulse_data = data.pulsetable

        # Ensure file is large enough
        if len(output) < pulse_offset + len(pulse_data):
            output.extend(bytearray(pulse_offset + len(pulse_data) - len(output)))

        # Write pulse table
        for i, byte in enumerate(pulse_data):
            if isinstance(byte, (int, bytes)):
                output[pulse_offset + i] = byte if isinstance(byte, int) else byte[0]

        logger.info(f"  Injected pulse table: {len(pulse_data)} bytes at ${pulse_table_start:04X}")

    # Inject filter tables (three parallel Laxity NP21 arrays)
    if hasattr(data, 'filtertable') and data.filtertable:
        filter_data = data.filtertable
        # filtertable is flat bytes: [seq, spd, res, next, seq, spd, res, next, ...]
        # Each 4-byte group maps to one filter step across the 3 parallel arrays.
        seq_bytes = bytearray()
        spd_bytes = bytearray()
        res_bytes = bytearray()
        raw = bytes(filter_data) if not isinstance(filter_data, (bytes, bytearray)) else filter_data
        for i in range(0, len(raw) - 3, 4):
            seq_bytes.append(raw[i])
            spd_bytes.append(raw[i + 1])
            res_bytes.append(raw[i + 2])

        for start_addr, table_bytes, label in (
            (filter_seq_start,  seq_bytes, 'filter_seq'),
            (filter_spd_start,  spd_bytes, 'filter_speed'),
            (filter_res_start,  res_bytes, 'filter_resonance'),
        ):
            if not table_bytes:
                continue
            tbl_offset = addr_to_offset(start_addr)
            if len(output) < tbl_offset + len(table_bytes):
                output.extend(bytearray(tbl_offset + len(table_bytes) - len(output)))
            for i, byte in enumerate(table_bytes):
                output[tbl_offset + i] = byte
            logger.info(f"  Injected {label}: {len(table_bytes)} bytes at ${start_addr:04X}")

    # Inject raw NP21 music block verbatim at original SID addresses.
    # Block: pattern pointer lo table ($1A22) + hi table ($1A49) + orderlists + patterns.
    # This ensures the NP21 player finds all note patterns correctly, including filter
    # trigger commands ($C4/$CC) that activate the filter at the right song position.
    _NP21_MUSIC_OFF = _sid_la + 0x0A22 - _sid_la  # = 0x0A22 offset from SID c64_data start
    if _c64 and len(_c64) > _NP21_MUSIC_OFF:
        _music = bytes(_c64[_NP21_MUSIC_OFF:])
        _m_addr = _sid_la + _NP21_MUSIC_OFF   # $1A22 for NP21 at load $1000
        _m_off = addr_to_offset(_m_addr)
        if len(output) < _m_off + len(_music):
            output.extend(bytearray(_m_off + len(_music) - len(output)))
        for _i, _b in enumerate(_music):
            output[_m_off + _i] = _b
        logger.info(f"  Injected NP21 music block: {len(_music)} bytes at ${_m_addr:04X}")

    # Inject command table (NP21 indirect command dispatch table)
    # Each sequence command byte $C0+n references entry n in this table.
    # Entries are (cmd_byte, param_byte) pairs. Without this table, filter
    # commands ($C4/$CC) and portamento ($81) commands are all silently mis-fired.
    cmd_addrs = (getattr(data, 'extraction_addresses', None) or {}).get('commands')
    c64_data = getattr(data, 'c64_data', None)
    if cmd_addrs and c64_data:
        cmd_addr, cmd_end, cmd_size = cmd_addrs
        src_offset = cmd_addr - data.load_address
        if 0 <= src_offset and src_offset + cmd_size <= len(c64_data):
            cmd_bytes = bytes(c64_data[src_offset:src_offset + cmd_size])
            cmd_file_off = addr_to_offset(cmd_addr)
            if len(output) < cmd_file_off + cmd_size:
                output.extend(bytearray(cmd_file_off + cmd_size - len(output)))
            for i, byte in enumerate(cmd_bytes):
                output[cmd_file_off + i] = byte
            logger.info(f"  Injected command table: {cmd_size} bytes at ${cmd_addr:04X}")

    # Inject instrument table
    if data.instruments and len(data.instruments) > 0:  # RE-ENABLED for testing
        instr_offset = addr_to_offset(instrument_table_start)

        # Laxity instruments are 8 bytes each
        instr_data = bytearray()
        for instr in data.instruments:
            if isinstance(instr, (list, tuple)):
                for byte in instr[:8]:  # 8 bytes per instrument
                    instr_data.append(byte if isinstance(byte, int) else ord(byte))
            elif isinstance(instr, bytes):
                instr_data.extend(instr[:8])

        # Ensure file is large enough
        if len(output) < instr_offset + len(instr_data):
            output.extend(bytearray(instr_offset + len(instr_data) - len(output)))

        # Write instrument table
        for i, byte in enumerate(instr_data):
            output[instr_offset + i] = byte

        logger.info(f"  Injected instrument table: {len(instr_data)} bytes ({len(data.instruments)} instruments) at ${instrument_table_start:04X}")

    # Zero-init filter state variables.
    # The SF2 INIT routine ($1492) only clears $1581/$1582; it does NOT reset the
    # filter state machine variables $158A/$1589/$1586/$1587.
    # $158A ($E0 bug source): template has $10, causes D416=$E0 when inactive.
    # $1589 (sweep accumulator): template has $29, causes wrong sweep timing.
    # $1586 (mode_bits): template has $10 (LP bit set), causes D418=$1F not $0F.
    # $1587 (filter_res): template has $F2, causes D417=$F2 not $00 initially.
    # Setting all to $00 matches NP21 INIT behaviour (filter fully off at start).
    for _faddr, _flabel in [(0x158A, 'filter_lo'), (0x1589, 'filter_spd_acc'),
                            (0x1586, 'mode_bits'), (0x1587, 'filter_res')]:
        _foff = addr_to_offset(_faddr)
        if len(output) > _foff:
            output[_foff] = 0x00
            logger.debug(f"  Zeroed {_flabel} @ ${_faddr:04X}")

    logger.info(f"  Laxity music data injection complete (with tables)")
    logger.info(f"  Total file size: {len(output)} bytes")
