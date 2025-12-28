"""
Laxity NewPlayer v21 Parser - Extract sequences and music data from Laxity player format.

Based on analysis in docs/LAXITY_PLAYER_ANALYSIS.md
"""

import logging
from typing import List, Tuple, NamedTuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Laxity player table offsets from load address (from docs/LAXITY_PLAYER_ANALYSIS.md)
# These are relative offsets, not absolute addresses
# For Angular (load $1000): SEQ_PTRS at $199F = $1000 + $099F
# For Broware (load $A000): SEQ_PTRS at $A99F = $A000 + $099F
LAXITY_SEQ_PTRS_OFFSET = 0x099F    # Sequence pointer table offset
LAXITY_INSTR_TABLE_OFFSET = 0x0A6B # Instrument table offset (8 × 8 bytes)
LAXITY_CMD_TABLE_OFFSET = 0x0ADB   # Command table offset


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

        # Calculate sequence pointer table location (offset $099F from load address)
        seq_ptr_addr = self.load_address + LAXITY_SEQ_PTRS_OFFSET

        if seq_ptr_addr < self.load_address or seq_ptr_addr >= self.load_address + len(self.data):
            logger.warning(f"Sequence pointer table at ${seq_ptr_addr:04X} is outside loaded data range")
            return sequences, orderlists

        # Calculate file offset
        seq_ptr_offset = seq_ptr_addr - self.load_address

        logger.debug(f"Sequence pointer table at ${seq_ptr_addr:04X} (file offset {seq_ptr_offset})")

        # Extract sequence pointers for 3 voices
        # The pointer table has pairs of bytes (lo, hi) for each voice's sequence
        sequence_addresses = set()  # Track unique sequence addresses

        for voice in range(3):
            # Read sequence pointer (2 bytes: lo, hi)
            ptr_offset = seq_ptr_offset + (voice * 2)

            if ptr_offset + 1 >= len(self.data):
                logger.warning(f"Voice {voice}: pointer offset {ptr_offset} out of range")
                continue

            seq_lo = self.data[ptr_offset]
            seq_hi = self.data[ptr_offset + 1]
            seq_addr = seq_lo | (seq_hi << 8)

            logger.debug(f"Voice {voice}: sequence at ${seq_addr:04X}")

            # The orderlist for Laxity is typically just one sequence per voice
            # (more complex songs might have multiple sequences chained)

            # Check if sequence address is valid (non-zero and within C64 addressable space)
            if seq_addr > 0 and seq_addr < 0x10000:
                # Try to extract sequence - it might be within loaded data at a different offset
                # Some SID files use relocated players where sequences are at unexpected addresses
                sequence_addresses.add(seq_addr)
                orderlists[voice].append(seq_addr)  # Store address for now
                logger.debug(f"Voice {voice}: sequence at ${seq_addr:04X}")
            else:
                logger.warning(f"Voice {voice}: invalid sequence address ${seq_addr:04X}")

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
