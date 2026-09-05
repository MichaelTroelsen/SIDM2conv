"""
Laxity NewPlayer v21 Parser - Extract sequences and music data from Laxity player format.

Based on analysis in docs/LAXITY_PLAYER_ANALYSIS.md
"""

import logging
from typing import List, Tuple, NamedTuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Laxity player table offsets from load address (confirmed via Regenerator 2000 symbol table,
# Stinsens_Last_Night_of_89 NP21 v21 disassembly)
# ch_seq_ptr_lo at load+$0A1C (3 bytes: lo of seq ptr for ch0, ch1, ch2)
# ch_seq_ptr_hi at load+$0A1F (3 bytes: hi of seq ptr for ch0, ch1, ch2)
# Format: SEPARATE lo/hi arrays, NOT interleaved pairs.
# Old value 0x099F was wrong for Stinsen (pointed into filter speed table).
LAXITY_SEQ_PTRS_LO_OFFSET = 0x0A1C  # ch_seq_ptr_lo[0..2]
LAXITY_SEQ_PTRS_HI_OFFSET = 0x0A1F  # ch_seq_ptr_hi[0..2]
LAXITY_SEQ_PTRS_OFFSET = 0x0A1C     # Legacy alias (lo offset)
LAXITY_INSTR_TABLE_OFFSET = 0x0A6B # Instrument table offset (8 × 8 bytes)
LAXITY_CMD_TABLE_OFFSET = 0x0ADB   # Command table offset


# How far apart the two `LDA abs,X` reads may sit for the pair to count.
_LOCATE_WINDOW = 24
# A sequence longer than this is not a sequence.
_MAX_SEQ_SCAN = 256


def locate_seq_ptr_table(data: bytes, load_address: int):
    """Find ch_seq_ptr by CODE SIGNATURE. Returns (lo_base, hi_base) or None.

    THE CONSTANTS ABOVE ARE WRONG FOR MOST FILES AND ALWAYS WERE. $0A1C serves
    Stinsen and Unboxed; $099F serves Angular and Omniphunk; neither serves the
    other 13 files in SID/. Seven cycles were spent asking which constant was
    right. The question was wrong: the LAYOUT is uniform -- split lo/hi, stride
    1, gap 3 -- and only the OFFSET moves, because the player is assembled per
    song. So locate it, exactly as HardTrack's vib_depth had to be after the
    last such constant turned out wrong on 15 files.

    THE SIGNATURE. The player reads the table as two `LDA abs,X` ($BD) whose
    absolute operands are exactly 3 apart -- one per voice, lo then hi. That
    shape appears in 17 of 17 files (Angular at $1171/$1177, Stinsen at
    $107E/$1083), but so do ~20 neighbours, because the player keeps several
    parallel 3-byte per-voice tables side by side.

    THE DISCRIMINATOR, and two that failed first, recorded so they are not
    retried. (a) "a sequence start is preceded by $FF": scores the correct
    answer 2/3 on Angular but 0/3 on STINSEN'S, so it rejects a correct result.
    (b) "the table INIT writes": eliminates Stinsen's correct answer outright --
    $1A1C has LDA sites and no STA. What works is looking FORWARD at the data:
    keep only candidates whose three pointers are in-image, distinct, and each
    terminate in $FF within _MAX_SEQ_SCAN, then take the one whose sequences are
    LONGEST in total. That is not a fitted rule -- the losing candidate points a
    few bytes INTO the same sequences, so it necessarily runs shorter to the
    same terminator.

    IT REFUSES RATHER THAN GUESSES. No surviving candidate, or a tie on the top
    score, returns None and the caller falls back to the constants. On SID/ that
    is 3 of 17 (Blue ties; Clarencio_extended and Ocean_Reloaded have no valid
    candidate).

    VERIFIED on the three files whose sequence addresses are independently
    known: Angular $1907, Omniphunk $1907, Stinsen $1A1C -- 3 of 3. The other 11
    are PLAUSIBLE, not verified: they satisfy the validity filter, but no ground
    truth exists for them.
    """
    n = len(data)
    hi_limit = load_address + n

    cands = set()
    for i in range(n - 3):
        if data[i] != 0xBD:
            continue
        a1 = data[i + 1] | (data[i + 2] << 8)
        for j in range(i + 3, min(i + 3 + _LOCATE_WINDOW, n - 3)):
            if data[j] != 0xBD:
                continue
            a2 = data[j + 1] | (data[j + 2] << 8)
            if a2 == a1 + 3 and load_address <= a1 and a1 + 6 <= hi_limit:
                cands.add((a1, a2))

    def seq_len(addr):
        if not (load_address <= addr < hi_limit):
            return None
        off = addr - load_address
        for k in range(off, min(off + _MAX_SEQ_SCAN, n)):
            if data[k] == 0xFF:
                return k - off + 1
        return None

    scored = []
    for lo, hi in cands:
        off = lo - load_address
        ptrs = [data[off + v] | (data[off + 3 + v] << 8) for v in range(3)]
        if len(set(ptrs)) != 3:
            continue
        lens = [seq_len(a) for a in ptrs]
        if any(l is None or l < 4 for l in lens):
            continue
        scored.append((sum(lens), lo, hi))

    if not scored:
        logger.debug("locate_seq_ptr_table: no candidate survived the validity filter")
        return None
    scored.sort(key=lambda t: (-t[0], t[1]))
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        logger.debug(
            "locate_seq_ptr_table: tie on top score between $%04X and $%04X -- refusing",
            scored[0][1], scored[1][1])
        return None
    return scored[0][1], scored[0][2]


def locate_seq_table(data: bytes, load_address: int, min_n=4, max_n=64):
    """(table_addr, N, ptrs) for the split lo[N]/hi[N] SEQUENCE table, or None.

    PORTED VERBATIM from pyscript/sf2_viewer_core.py's
    SF2Parser.laxity_locate_seq_table (81e4e94), which is where this shape was
    first measured -- 22 locate / 25 refuse / 0 tie over the 47 Laxity SF2s.
    It is repeated here rather than imported because sidm2/ is the lower layer:
    the viewer already imports this module, so importing back would be a cycle.
    The two copies should converge on THIS one; see
    laxity-locate-seq-table-exists-in-two-copies.

    WHY A SEARCH AND NOT A CONSTANT. The table sits immediately below the
    orderlists on Angular ($1B1C, N=14) but not on Stinsen, whose three
    orderlists are $100 apart -- so "just past the last orderlist" is an
    Angular-shaped guess, and this area has been wrong twice already by
    generalising from one file.

    THE SHAPE IS SELF-VERIFYING, which is what makes an exhaustive scan safe:
    the bodies start immediately after the table, so entry 0 MUST equal
    table + 2N. With "every entry inside the image" and "entries strictly
    ascending" that is strong enough to be unique, and this REFUSES on a tie
    rather than picking -- a wrong table would silently renumber every
    sequence.

    Measured here over SID/Laxity/*.sid (286 files): 21 locate, 265 refuse,
    worst single-file scan 0.004s.
    """
    n = len(data)
    lim = load_address + n
    hits = []
    for off in range(0, n - 2 * min_n):
        # bodies begin at table + 2N, so lo[0] pins N modulo 128
        delta = (data[off] - (load_address + off)) & 0xFF
        if delta & 1:
            continue
        for cand in range(delta >> 1, max_n + 1, 128):
            if cand < min_n or off + 2 * cand >= n:
                break
            tbl = load_address + off
            if data[off + cand] != ((tbl + 2 * cand) >> 8) & 0xFF:
                continue
            ptrs = [data[off + i] | (data[off + cand + i] << 8) for i in range(cand)]
            if ptrs[0] != tbl + 2 * cand:
                continue
            if not all(load_address <= p < lim for p in ptrs):
                continue
            if not all(ptrs[i] < ptrs[i + 1] for i in range(cand - 1)):
                continue
            hits.append((tbl, cand, ptrs))
    if len(hits) != 1:
        logger.debug("locate_seq_table: %d candidates -- refusing", len(hits))
        return None
    return hits[0]


def read_orderlist_numbers(data: bytes, load_address: int, lo_base: int,
                           hi_base: int, max_len=256):
    """The three per-voice orderlists as SEQUENCE NUMBERS, or None if unreadable.

    ch_seq_ptr points at an ORDERLIST: a byte stream terminated by $FF whose
    entries are sequence numbers, with TRANSPOSE bytes interleaved. Bit 7 is
    the discriminator -- measured over the 21 SID/Laxity files whose sequence
    table locates: dropping bit-7-set bytes takes the out-of-range entry count
    from 361 to 213, and every one of the 213 that remains comes from a single
    file (Rudolph_in_the_Kitchen), not from a scatter across the corpus.

    Angular's voice 0 reads `87 01 01 01 01 01 01 08 08 08 08 08 08 FF`: $87 is
    the transpose, then twelve sequence numbers. Voice 2 is
    `87 05 06 03 04 03 07 0A 0A 0B 0C 0B 0D`. The numbers index the sequence
    table DIRECTLY (0-based) -- confirmed against the editor, where sequence 07
    rows 7..14 are T3's 'A-4 G-4 B-4 G-4 D-4 C-5 B-4 G-4'.
    """
    lim = load_address + len(data)
    out = []
    for voice in range(3):
        try:
            addr = (data[lo_base - load_address + voice]
                    | (data[hi_base - load_address + voice] << 8))
        except IndexError:
            return None
        if not load_address <= addr < lim:
            return None
        numbers = []
        pos = addr
        seen = 0
        while pos < lim and data[pos - load_address] != 0xFF and seen < max_len:
            byte = data[pos - load_address]
            if not byte & 0x80:          # bit 7 set -> transpose, not a number
                numbers.append(byte)
            pos += 1
            seen += 1
        out.append(numbers)
    return out


@dataclass
class LaxityData:
    """Extracted data from Laxity player"""
    sequences: List[bytes] = field(default_factory=list)
    orderlists: List[List[int]] = field(default_factory=list)
    instruments: List[bytes] = field(default_factory=list)
    command_table: List[bytes] = field(default_factory=list)


class LaxityParser:
    """
    Parser for Laxity NewPlayer v21 format.

    Extracts sequences, orderlists, instruments, and command data from
    the Laxity player stored in SID file memory.
    """

    def __init__(self, data: bytes, load_address: int):
        """
        Initialize parser.

        Args:
            data: C64 memory data (64KB)
            load_address: Load address of the SID data
        """
        self.data = data
        self.load_address = load_address

    def parse(self) -> LaxityData:
        """
        Parse Laxity player data and extract all music elements.

        Returns:
            LaxityData with sequences, orderlists, instruments, commands
        """
        result = LaxityData()

        # Extract sequence pointers and orderlists (3 voices)
        logger.info("Extracting Laxity sequences and orderlists")
        sequences, orderlists = self._extract_sequences_and_orderlists()
        result.sequences = sequences
        result.orderlists = orderlists

        # Extract instruments
        result.instruments = self._extract_instruments()

        # Extract command table
        result.command_table = self._extract_command_table()

        logger.info(f"Extracted {len(sequences)} sequences, {len(result.instruments)} instruments, {len(result.command_table)} commands")

        return result

    def _extract_sequences_and_orderlists(self) -> Tuple[List[bytes], List[List[int]]]:
        """
        Extract sequences and orderlists from Laxity player.

        The Laxity player has a sequence pointer table at $199F that contains
        pointers to sequence data for each voice. We need to:
        1. Read the sequence pointer table
        2. Follow each pointer to extract sequence data
        3. Build the orderlist (which sequences each voice plays)

        Returns:
            Tuple of (sequences, orderlists)
        """
        sequences = []
        orderlists = [[], [], []]  # 3 voices

        # STAGE 1: THE REAL SEQUENCE TABLE, if this file has a locatable one.
        #
        # ch_seq_ptr does NOT point at sequences -- it points at ORDERLISTS, and
        # the two have different grammars and different terminators. An orderlist
        # ends on $FF; _extract_sequence_at_address below terminates on $7F, so it
        # runs straight past the end and keeps going. That is where Angular's
        # 197/174/139 "events" came from, and why scripts/test_converter.py has
        # been printing "Sequence 0 too long (429 events)" as a warning rather
        # than an error. Those counts are not a row count of anything.
        #
        # The real sequences live in a split lo[N]/hi[N] pointer table located by
        # locate_seq_table(). Bodies are cut at the NEXT POINTER, so their lengths
        # are STRUCTURAL rather than scanned -- which is the whole reason this
        # stage is worth having: the $7F scan below is unbounded and the table is
        # not. Derivation and ground truth: docs/players/LAXITY.md (34ed351).
        #
        # WHEN IT REFUSES, NOTHING CHANGES. 265 of the 286 files in SID/Laxity/
        # yield no unique table and fall through to the reader below, byte for
        # byte as before. This stage only ever ADDS a better answer; it never
        # replaces a working one with a worse one.
        located = locate_seq_table(self.data, self.load_address)
        if located is not None:
            real = self._sequences_from_table(*located)
            if real is not None:
                return real

        # ch_seq_ptr stored as two separate 3-byte arrays:
        #   lo bytes at load+$0A1C: [ch0_lo, ch1_lo, ch2_lo]
        #   hi bytes at load+$0A1F: [ch0_hi, ch1_hi, ch2_hi]
        # (Confirmed via Regenerator 2000 symbol table for Stinsen NP21 v21)
        # Locate by code signature; fall back to the constants when it refuses.
        located = locate_seq_ptr_table(self.data, self.load_address)
        if located is not None:
            lo_base, hi_base = located
            logger.debug(f"ch_seq_ptr LOCATED at ${lo_base:04X}/${hi_base:04X}")
        else:
            lo_base = self.load_address + LAXITY_SEQ_PTRS_LO_OFFSET
            hi_base = self.load_address + LAXITY_SEQ_PTRS_HI_OFFSET
            logger.debug(
                f"ch_seq_ptr locate refused; falling back to the constants "
                f"${lo_base:04X}/${hi_base:04X}")

        if hi_base + 2 >= self.load_address + len(self.data):
            logger.warning(f"ch_seq_ptr table at ${lo_base:04X} is outside loaded data range")
            return sequences, orderlists

        lo_off = lo_base - self.load_address
        hi_off = hi_base - self.load_address

        logger.debug(f"ch_seq_ptr_lo at ${lo_base:04X}, ch_seq_ptr_hi at ${hi_base:04X}")

        # Extract sequence pointers for 3 voices (separate lo/hi arrays)
        sequence_addresses = set()  # Track unique sequence addresses

        for voice in range(3):
            seq_lo = self.data[lo_off + voice]
            seq_hi = self.data[hi_off + voice]
            seq_addr = seq_lo | (seq_hi << 8)

            logger.debug(f"Voice {voice}: sequence at ${seq_addr:04X}")

            # The orderlist for Laxity is typically just one sequence per voice
            # (more complex songs might have multiple sequences chained)

            # The address must lie INSIDE THE LOADED IMAGE, not merely inside the
            # 64K address space. The old test was `seq_addr > 0 and seq_addr <
            # 0x10000`, which accepts anything at all: measured across the named
            # corpus (docs/players/LAXITY.md:8, SID/Laxity/, 286 files) this
            # constant produces a usable locate on SEVEN of them, and the other
            # 279 were fed values like $007F, $4141, $0000 and, on Angular,
            # $0334/$0341/$0336 -- all three BELOW the $1000 load address.
            # Nothing noticed, because nothing checked.
            #
            # This is a REFUSAL, not a locate: it does not find the right
            # sequences, it stops the wrong ones being returned as though they
            # were right. Failing honestly is this repo's convention -- zig64
            # prints FAILED: and exits non-zero rather than emitting an empty
            # trace as a silent tune, and fidelity_common.score_pct returns None
            # rather than 100.0 when there is nothing to score.
            lo_bound = self.load_address
            hi_bound = self.load_address + len(self.data)
            if lo_bound <= seq_addr < hi_bound:
                sequence_addresses.add(seq_addr)
                orderlists[voice].append(seq_addr)  # Store address for now
                logger.debug(f"Voice {voice}: sequence at ${seq_addr:04X}")
            else:
                logger.warning(
                    f"Voice {voice}: ch_seq_ptr ${seq_addr:04X} is outside the "
                    f"loaded image ${lo_bound:04X}-${hi_bound - 1:04X} -- "
                    f"refusing it rather than extracting from it"
                )

        # Extract each unique sequence
        addr_to_index = {}
        for seq_addr in sorted(sequence_addresses):
            seq_data = self._extract_sequence_at_address(seq_addr)
            if seq_data:
                addr_to_index[seq_addr] = len(sequences)
                sequences.append(seq_data)
                logger.debug(f"Sequence {len(sequences)-1}: ${seq_addr:04X}, {len(seq_data)} bytes")

        # Convert orderlists from addresses to indices
        for voice in range(3):
            orderlist_indices = []
            for seq_addr in orderlists[voice]:
                if seq_addr in addr_to_index:
                    orderlist_indices.append(addr_to_index[seq_addr])
            orderlists[voice] = orderlist_indices

        # Handle case where some voices have no sequences but we found at least one
        # Some Laxity files share the same sequence across all voices
        if sequences and any(not ol for ol in orderlists):
            logger.info(f"Found {len(sequences)} sequence(s), assigning to voices with missing sequences")
            for voice in range(3):
                if not orderlists[voice]:
                    # Use first available sequence
                    orderlists[voice] = [0]
                    logger.debug(f"Voice {voice}: using shared sequence 0")

        return sequences, orderlists

    def _sequences_from_table(self, tbl: int, count: int, ptrs):
        """(sequences, orderlists) from a located sequence table, or None to decline.

        THE ORDERLISTS ARE A CROSS-CHECK, NOT JUST AN OUTPUT. A located table
        says how many sequences exist; the orderlists say which numbers the song
        actually plays. If a voice names a sequence the table does not contain,
        the table is not the whole table and everything built on it would be
        silently wrong -- so this declines and lets the older reader answer.
        That fires on exactly one file in SID/Laxity/ (286 files, 21 locates):
        Rudolph_in_the_Kitchen names sequence $22 against a located N=13.
        Refusing there is the same convention as locate_seq_table's tie refusal.
        """
        end_of_image = self.load_address + len(self.data)
        sequences = []
        for idx, start in enumerate(ptrs):
            if idx + 1 < count:
                stop = ptrs[idx + 1]
            else:
                # The last body has no successor to bound it. Cut it at the
                # grammar's own END marker instead of running to end-of-image.
                stop = start
                while (stop < end_of_image
                       and self.data[stop - self.load_address] != 0x7F):
                    stop += 1
                stop = min(stop + 1, end_of_image)
            sequences.append(bytes(
                self.data[start - self.load_address:stop - self.load_address]))

        located_ptr = locate_seq_ptr_table(self.data, self.load_address)
        if located_ptr is None:
            lo_base = self.load_address + LAXITY_SEQ_PTRS_LO_OFFSET
            hi_base = self.load_address + LAXITY_SEQ_PTRS_HI_OFFSET
        else:
            lo_base, hi_base = located_ptr
        if hi_base + 2 >= end_of_image:
            numbers = None
        else:
            numbers = read_orderlist_numbers(
                self.data, self.load_address, lo_base, hi_base)

        if numbers is None:
            # The bodies are still structurally sound -- the locate is unique and
            # self-verifying -- but with no readable orderlist there is nothing to
            # say which sequence each voice plays, and inventing one would be a
            # guess. Emit the sequences and leave the orderlists empty.
            logger.info(
                "Laxity sequence table at $%04X: %d sequences, orderlists "
                "unreadable", tbl, count)
            return sequences, [[], [], []]

        outside = [n for voice in numbers for n in voice if n >= count]
        if outside:
            logger.warning(
                "Laxity sequence table at $%04X declares %d sequences but the "
                "orderlists name %s -- declining it rather than truncating",
                tbl, count, sorted(set(outside))[:8])
            return None

        logger.info("Laxity sequence table at $%04X: %d sequences, orderlists "
                    "%s", tbl, count, [len(v) for v in numbers])
        return sequences, numbers

    def _extract_sequence_at_address(self, address: int) -> bytes:
        """
        Extract a single sequence starting at the given address.

        Sequences are terminated by $7F (end marker).

        Format (from docs):
        - $00: Rest
        - $01-$5F: Note value
        - $7E: Gate continue
        - $7F: End of sequence
        - $80-$8F: Rest with duration
        - $90-$9F: Duration with gate
        - $A0-$BF: Instrument
        - $C0-$FF: Command

        Args:
            address: C64 address of sequence start

        Returns:
            Sequence data as bytes
        """
        # Try multiple strategies to locate the sequence data

        # Strategy 1: Address is within loaded data range (standard case)
        if address >= self.load_address and address < self.load_address + len(self.data):
            offset = address - self.load_address
            return self._extract_sequence_from_offset(offset, address)

        # Strategy 2: Address might be a direct offset into the data (relocated player)
        # Some SID files store sequences using offsets that appear to be low addresses
        if address < len(self.data):
            logger.debug(f"Trying sequence at ${address:04X} as direct data offset")
            return self._extract_sequence_from_offset(address, address)

        # Strategy 3: Address might be relative to a different base
        # Try interpreting as offset from start of data
        if address < 0x2000:  # Reasonable offset range
            logger.debug(f"Trying sequence at ${address:04X} as relative offset")
            return self._extract_sequence_from_offset(address, address)

        # Sequence not found - this is logged at debug level since some Laxity files
        # share sequences between voices and may have invalid pointers for some voices
        logger.debug(f"Could not locate sequence at ${address:04X} (may be shared with another voice)")
        return b''

    def _extract_sequence_from_offset(self, offset: int, address: int) -> bytes:
        """Extract sequence data from a specific offset in the loaded data"""
        sequence = bytearray()
        max_length = 10000  # Safety limit

        while offset < len(self.data) and len(sequence) < max_length:
            byte = self.data[offset]
            sequence.append(byte)
            offset += 1

            # End of sequence
            if byte == 0x7F:
                break

        if len(sequence) >= max_length:
            logger.warning(f"Sequence at ${address:04X} exceeded max length, truncating")

        if len(sequence) > 0 and sequence[-1] == 0x7F:
            logger.debug(f"Successfully extracted {len(sequence)} byte sequence from ${address:04X}")
            return bytes(sequence)
        else:
            logger.debug(f"No valid sequence found at ${address:04X} (no end marker)")
            return b''

    def _extract_instruments(self) -> List[bytes]:
        """
        Extract instrument table from Laxity player.

        Located at $1A6B, 8 bytes per instrument (column-major layout).
        Typically 8 instruments.

        Format:
        - Byte 0: AD (Attack/Decay)
        - Byte 1: SR (Sustain/Release)
        - Byte 2: Pulse pointer
        - Byte 3: Filter byte
        - Byte 4: (unused)
        - Byte 5: (unused)
        - Byte 6: Flags
        - Byte 7: Wave table pointer

        Returns:
            List of 8-byte instrument data
        """
        instruments = []
        # Calculate instrument table location (offset $0A6B from load address)
        instr_addr = self.load_address + LAXITY_INSTR_TABLE_OFFSET

        if instr_addr < self.load_address or instr_addr >= self.load_address + len(self.data):
            logger.warning(f"Instrument table at ${instr_addr:04X} is outside loaded data range")
            return instruments

        offset = instr_addr - self.load_address

        # Extract 8 instruments (8 bytes each, column-major)
        # Column-major means first 8 bytes are AD values for all instruments,
        # next 8 bytes are SR values, etc.
        num_instruments = 8

        if offset + (num_instruments * 8) > len(self.data):
            logger.warning("Not enough data for full instrument table")
            return instruments

        # Convert from column-major to row-major (one instrument at a time)
        for i in range(num_instruments):
            instr = bytearray(8)
            for byte_idx in range(8):
                column_offset = offset + (byte_idx * num_instruments) + i
                if column_offset < len(self.data):
                    instr[byte_idx] = self.data[column_offset]

            instruments.append(bytes(instr))

        logger.debug(f"Extracted {len(instruments)} instruments from ${instr_addr:04X}")
        return instruments

    def _extract_command_table(self) -> List[bytes]:
        """
        Extract command table from Laxity player.

        Located at $1ADB, variable number of entries.
        Each command is 3 bytes (command type + 2 parameter bytes).

        We scan until we hit invalid data or reach the sequence data area.

        Returns:
            List of 3-byte command entries
        """
        commands = []
        # Calculate command table location (offset $0ADB from load address)
        cmd_addr = self.load_address + LAXITY_CMD_TABLE_OFFSET

        if cmd_addr < self.load_address or cmd_addr >= self.load_address + len(self.data):
            logger.warning(f"Command table at ${cmd_addr:04X} is outside loaded data range")
            return commands

        offset = cmd_addr - self.load_address
        max_commands = 64  # Typical limit

        # Extract commands (3 bytes each)
        for i in range(max_commands):
            if offset + 2 >= len(self.data):
                break

            cmd_byte0 = self.data[offset]
            cmd_byte1 = self.data[offset + 1]
            cmd_byte2 = self.data[offset + 2]

            # Stop if we hit obviously invalid command data
            # (this is heuristic - could be improved)
            if cmd_byte0 == 0 and cmd_byte1 == 0 and cmd_byte2 == 0:
                break

            commands.append(bytes([cmd_byte0, cmd_byte1, cmd_byte2]))
            offset += 3

        logger.debug(f"Extracted {len(commands)} commands from ${cmd_addr:04X}")
        return commands
