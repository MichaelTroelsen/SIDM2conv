#!/usr/bin/env python3
"""
Dedicated Laxity player parser for Angular.sid and similar SID files.

Based on reverse-engineering analysis, this parser finds the actual music data
structures instead of using heuristics.

Key findings about Laxity format:
- Init routine at $1000 references $199F for music data header
- Orderlists at $1AF3, $1B01, $1B0F (3 voices)
- Sequences start at $1B38 and end with 0x7F markers
- Sequence format is nearly identical to SF2 format

Sequence byte meanings:
- 0xA0-0xAF: Instrument change (instrument number = byte - 0xA0)
- 0x80-0x9F: Duration (duration value = byte - 0x80)
- 0xC0-0xCF: Commands
- 0x00-0x6F: Note values
- 0x7F: End marker
- 0x7E: Rest/tie
"""

import struct
import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LaxitySequence:
    """A parsed Laxity sequence"""
    start_addr: int
    end_addr: int
    data: bytes


@dataclass
class LaxityData:
    """Complete extracted Laxity music data"""
    orderlists: List[List[int]]  # 3 orderlists, each is list of sequence indices
    sequences: List[bytes]  # Raw sequence data (already in SF2-compatible format)
    instruments: List[bytes]  # Instrument definitions
    sequence_addrs: List[int]  # Addresses of each sequence
    command_table: List[Tuple[int, int]] = None  # Command table entries (cmd_byte, param_byte)


class LaxityParser:
    """Parser for Laxity player format SID files"""

    def __init__(self, c64_data: bytes, load_address: int):
        self.data = c64_data
        self.load_address = load_address
        self.data_end = load_address + len(c64_data)

    def get_byte(self, addr: int) -> int:
        """Get byte at C64 address.

        Args:
            addr: C64 memory address

        Returns:
            Byte value at address, or 0 if out of bounds
        """
        offset = addr - self.load_address
        if 0 <= offset < len(self.data):
            return self.data[offset]
        return 0

    def get_word(self, addr: int) -> int:
        """Get word (little-endian) at C64 address.

        Args:
            addr: C64 memory address

        Returns:
            16-bit word value (little-endian)
        """
        if addr < self.load_address or addr + 1 >= self.data_end:
            return 0
        return self.get_byte(addr) | (self.get_byte(addr + 1) << 8)

    def get_bytes(self, addr: int, count: int) -> bytes:
        """Get multiple bytes at C64 address.

        Args:
            addr: C64 memory address
            count: Number of bytes to read

        Returns:
            Bytes read, or zero-filled bytes if out of bounds
        """
        if count < 0:
            raise ValueError(f"Invalid byte count: {count}")

        offset = addr - self.load_address
        if 0 <= offset < len(self.data):
            end_offset = min(offset + count, len(self.data))
            result = self.data[offset:end_offset]
            # Pad with zeros if we couldn't read all requested bytes
            if len(result) < count:
                result = result + bytes(count - len(result))
            return result
        return bytes(count)

    def find_orderlists(self) -> List[List[int]]:
        """
        Find the 3 orderlists for the 3 voices.

        Based on analysis, Angular.sid has orderlists at:
        - Voice 1: $1AF3 (01 01 01 01 01 01 08 08 08 08 08 08 FF)
        - Voice 2: $1B01 (02 02 02 02 02 02 09 09 09 09 09 09 FF)
        - Voice 3: $1B0F (05 06 03 04 03 07 0A 0A 0B 0C 0B 0D FF)
        """
        orderlists = []

        # Search for orderlist patterns
        # Orderlists contain small values (sequence indices) and end with 0xFF

        orderlist_addrs = []

        for addr in range(self.load_address + 0x900, self.data_end - 32):
            # Read potential orderlist
            seq = []
            for i in range(64):
                b = self.get_byte(addr + i)
                if b == 0xFF:
                    seq.append(b)
                    break
                seq.append(b)

            if len(seq) < 4 or seq[-1] != 0xFF:
                continue

            # Check if all values before FF are small (sequence indices <= 0x20)
            values = seq[:-1]
            if all(v <= 0x20 for v in values) and any(v > 0 for v in values):
                # Good candidate - check it's not a subset of another
                is_subset = False
                for existing_addr, existing_len in orderlist_addrs:
                    if existing_addr <= addr < existing_addr + existing_len:
                        is_subset = True
                        break

                if not is_subset:
                    orderlist_addrs.append((addr, len(seq)))

        # Take the first 3 longest orderlists
        orderlist_addrs.sort(key=lambda x: -x[1])

        # Filter to get 3 distinct orderlists
        selected = []
        for addr, length in orderlist_addrs:
            # Check not overlapping with already selected
            overlaps = False
            for sel_addr, sel_len in selected:
                if not (addr + length <= sel_addr or addr >= sel_addr + sel_len):
                    overlaps = True
                    break
            if not overlaps and length >= 4:
                selected.append((addr, length))
                if len(selected) >= 3:
                    break

        # Sort by address order
        selected.sort(key=lambda x: x[0])

        # Extract orderlist data
        for addr, length in selected:
            orderlist = []
            for i in range(length - 1):  # Exclude FF terminator
                orderlist.append(self.get_byte(addr + i))
            orderlists.append(orderlist)
            logger.debug(f"Found orderlist at ${addr:04X}: {' '.join(f'{v:02X}' for v in orderlist)}")

        # Ensure we have 3 orderlists
        while len(orderlists) < 3:
            orderlists.append([0])  # Default to seq 0

        return orderlists

    def find_sequences(self) -> Tuple[List[bytes], List[int]]:
        """
        Find all sequences in the music data area.

        Returns:
            Tuple of (sequence_list, address_list) where:
            - sequence_list: List of raw sequence bytes
            - address_list: List of sequence start addresses

        Sequences end with 0x7F and contain:
        - 0xA0-0xAF: Instrument changes
        - 0x80-0x9F: Durations
        - 0xC0-0xCF: Commands
        - 0x00-0x6F: Notes
        """
        # First, find all 0x7F end markers in the likely music data area
        markers = []
        for addr in range(self.load_address + 0xB00, self.data_end):
            if self.get_byte(addr) == 0x7F:
                markers.append(addr)

        if not markers:
            logger.warning("No sequence end markers found")
            return [], []

        logger.info(f"Found {len(markers)} end markers (0x7F)")

        # The key insight: sequences start right after orderlists
        # Orderlists end with 0xFF at $1B1B (05 06 03 04 03 07 0A 0A 0B 0C 0B 0D FF)
        # Then there's pointer table data, then sequences start

        # Find the start of actual sequence data by looking for:
        # - A byte in range 0x80-0xAF (instrument or duration, which starts most sequences)
        # - Preceded by 0x7F (end of previous data) or non-sequence data

        sequences = []
        sequence_addrs = []

        # Simple approach: use gaps between consecutive 0x7F markers
        # Each sequence is the data BETWEEN two 0x7F markers

        for i, end_addr in enumerate(markers):
            if i == 0:
                # First sequence - need to find its start
                # Look backwards from end for instrument (0xA0-0xAF) or duration (0x80-0x9F)
                # that isn't preceded by valid sequence bytes

                # Better approach: scan forward to find first proper sequence start
                # Sequences typically start with 0x80 (duration) or 0xA0 (instrument)
                start = end_addr

                # Search backwards, but be conservative
                # The first marker is at $1B3A
                # Looking at data: ... 1E 1E 1E 80 00 7F
                # So the sequence is: 80 00 7F (just 3 bytes)
                # Previous byte (1E) is in pointer table

                for check_addr in range(end_addr - 1, end_addr - 16, -1):
                    b = self.get_byte(check_addr)
                    prev_b = self.get_byte(check_addr - 1)

                    # Look for duration or instrument byte preceded by non-sequence data
                    if 0x80 <= b <= 0x9F or 0xA0 <= b <= 0xAF:
                        # Check if previous byte looks like end of other data
                        # Pointer table bytes at this location are typically 0x1B-0x1F
                        # (high byte of addresses in $1Bxx-$1Fxx range)
                        # Valid sequence note bytes would be in range 0x00-0x70
                        # So if prev_b is > 0x17 and < 0x80, it's likely pointer table

                        # Key: sequence notes are typically 0x00-0x60 (C-0 to B-7)
                        # Pointer table bytes here are 0x1B, 0x1C, 0x1D, 0x1E (hi bytes of $1Bxx-$1Exx)
                        if 0x1A <= prev_b <= 0x1F:  # High byte of pointer to $1Axx-$1Fxx
                            start = check_addr
                            break
                        # Also check if prev is clearly out of note range
                        if prev_b > 0x60 and prev_b < 0x80:  # Not a note, not a command
                            start = check_addr
                            break
                    elif b == 0x7F:
                        start = check_addr + 1
                        break

            else:
                # Subsequent sequences start right after previous end
                start = markers[i - 1] + 1

            # Extract sequence data
            length = end_addr - start + 1
            if length > 0 and length < 256:
                seq_data = self.get_bytes(start, length)
                sequences.append(seq_data)
                sequence_addrs.append(start)

        # The orderlists reference sequences starting from index 1 (not 0)
        # So we need to prepend a placeholder sequence 0 (empty/silent)
        # Check if minimum index in orderlists is > 0

        logger.info(f"Extracted {len(sequences)} sequences")
        for i, (seq, addr) in enumerate(zip(sequences[:5], sequence_addrs[:5])):
            hex_str = ' '.join(f'{b:02X}' for b in seq[:16])
            if len(seq) > 16:
                hex_str += ' ...'
            logger.debug(f"  Seq {i} at ${addr:04X} ({len(seq)} bytes): {hex_str}")

        return sequences, sequence_addrs

    def find_instrument_table_from_code(self) -> Optional[int]:
        """Find instrument table by analyzing player code LDA patterns.

        Laxity player reads instrument data using LDA $xxxx,Y instructions
        for bytes 0-7 of the instrument structure. This finds addresses
        where multiple bytes in an 8-byte structure are accessed.

        Returns:
            Address of instrument table, or None if not found
        """
        # Look for LDA abs,Y (0xB9) instructions accessing consecutive addresses
        lda_targets = {}
        for i in range(len(self.data) - 3):
            if self.data[i] == 0xB9:  # LDA abs,Y
                addr = (self.data[i+2] << 8) | self.data[i+1]
                if 0x1900 <= addr <= 0x1C00:  # Data region
                    lda_targets[addr] = lda_targets.get(addr, 0) + 1

        # Find addresses that are part of an 8-byte structure
        best_addr = None
        best_score = 0
        for base in range(0x1900, 0x1B00):
            # Check how many bytes in the 8-byte structure are accessed
            accessed = sum(1 for offset in range(8) if (base + offset) in lda_targets)
            if accessed > best_score:
                best_score = accessed
                best_addr = base

        # Only return if we have high confidence (7+ of 8 bytes accessed)
        if best_score >= 7 and best_addr:
            return best_addr
        return None

    def find_instruments(self) -> List[bytes]:
        """
        Find instrument definitions.

        Laxity instruments are 8-byte structures with format:
        - Byte 0: AD (Attack/Decay)
        - Byte 1: SR (Sustain/Release)
        - Byte 2-6: Flags/params
        - Byte 7: Wave table pointer
        """
        instruments = []

        # Method 1: Analyze player code to find instrument table address
        instr_addr = self.find_instrument_table_from_code()

        if instr_addr:
            logger.info(f"Found instrument table at ${instr_addr:04X} (via code analysis)")
            instr_offset = instr_addr - self.load_address

            # Extract instruments until we hit empty/invalid data
            for i in range(32):
                off = instr_offset + (i * 8)
                if off + 8 > len(self.data):
                    break

                instr = self.get_bytes(self.load_address + off, 8)
                ad = instr[0]
                sr = instr[1]
                wave_ptr = instr[7]

                # Stop if we hit empty instrument (but not for first one)
                if i > 0 and ad == 0 and sr == 0 and wave_ptr == 0:
                    break

                # Validate: reasonable ADSR and wave pointer
                sustain = (sr >> 4) & 0xF
                if ad < 0x40 and wave_ptr < 64:  # Reasonable values
                    instruments.append(instr)
                elif i == 0:  # Keep first instrument even if unusual
                    instruments.append(instr)
                else:
                    break

            if instruments:
                logger.info(f"Extracted {len(instruments)} instruments")
                return instruments

        # Method 2: Fallback - search for instrument-like patterns
        logger.info("Falling back to pattern-based instrument search")
        for addr in range(self.load_address + 0xA00, self.load_address + 0xB00):
            count = 0
            for i in range(8):
                instr_addr = addr + i * 8
                if instr_addr + 8 > self.data_end:
                    break

                instr = self.get_bytes(instr_addr, 8)
                ad = instr[0]
                sr = instr[1]
                wave_ptr = instr[7]

                # Better validation: check ADSR and wave pointer
                sustain = (sr >> 4) & 0xF
                if ad < 0x20 and sustain >= 0x04 and wave_ptr < 64:
                    count += 1
                elif count == 0 and ad != 0:  # First instrument can be unusual
                    count += 1
                else:
                    break

            if count >= 3:
                logger.info(f"Found instrument table at ${addr:04X} with {count} instruments")
                for i in range(count):
                    instr = self.get_bytes(addr + i * 8, 8)
                    instruments.append(instr)
                break

        # If no instruments found, create defaults
        if not instruments:
            logger.info("Creating default instruments")
            instruments.append(bytes([0x09, 0x00, 0x41, 0x00, 0x08, 0x00, 0x00, 0x00]))
            instruments.append(bytes([0x0A, 0x0A, 0x11, 0x00, 0x00, 0x00, 0x00, 0x00]))
            instruments.append(bytes([0x0F, 0x0F, 0x81, 0x00, 0x00, 0x00, 0x00, 0x00]))

        return instruments

    def find_command_table(self, sequences: List[bytes]) -> List[Tuple[int, int]]:
        """
        Extract command table from Laxity player at $1ADB.

        Laxity sequences use $C0-$FF bytes as command INDICES into this table.
        Each command entry is 2 bytes: (command_byte, param_byte).

        The command_byte format depends on the command type:
        - $0x = Slide up, speed hi nibble
        - $2x = Slide down, speed hi nibble
        - $60 = Vibrato, param = freq|amp
        - $8x = Portamento, speed hi nibble
        - $9x = Set ADSR persistent
        - $Ax = Set ADSR local
        - $C0 = Set wave pointer
        - $Dx = Filter/pulse control
        - $E0 = Set speed
        - $F0 = Set volume

        Args:
            sequences: List of raw sequences to determine which commands are used

        Returns:
            List of (cmd_byte, param_byte) tuples, indexed by command index
        """
        # Command table is at $1ADB in Laxity NewPlayer v21
        CMD_TABLE_ADDR = 0x1ADB
        MAX_COMMANDS = 64  # Up to 64 command entries

        # Find which command indices are used in sequences
        used_indices = set()
        for seq in sequences:
            for b in seq:
                if 0xC0 <= b <= 0xFF:
                    cmd_idx = (b & 0x3F)  # Index calculation
                    used_indices.add(cmd_idx)

        if not used_indices:
            logger.info("No commands found in sequences")
            return []

        max_idx = max(used_indices)
        logger.info(f"Found command indices in sequences: {sorted(used_indices)}")
        logger.debug(f"Command table at ${CMD_TABLE_ADDR:04X}, reading {max_idx + 1} entries")

        # Read command table entries
        command_table = []
        for i in range(max_idx + 1):
            entry_addr = CMD_TABLE_ADDR + (i * 2)
            cmd_byte = self.get_byte(entry_addr)
            param_byte = self.get_byte(entry_addr + 1)
            command_table.append((cmd_byte, param_byte))

            if i in used_indices:
                logger.debug(f"  Cmd {i}: ${cmd_byte:02X} ${param_byte:02X}")

        return command_table

    def parse(self) -> LaxityData:
        """Parse the SID file and extract all music data

        Returns:
            LaxityData with extracted music components

        Raises:
            ValueError: If data is too small or invalid format
            RuntimeError: If extraction fails
        """
        try:
            # Validate data size
            if len(self.data) < 256:
                raise ValueError(f"Data too small: {len(self.data)} bytes (minimum 256 bytes required)")

            logger.debug("=" * 60)
            logger.info("LAXITY PARSER")
            logger.debug("=" * 60)
            logger.info(f"Load address: ${self.load_address:04X}")
            logger.debug(f"Data size: {len(self.data)} bytes")
            logger.debug(f"Data end: ${self.data_end - 1:04X}")

            # Find orderlists
            logger.info("Finding orderlists...")
            try:
                orderlists = self.find_orderlists()
            except Exception as e:
                logger.error(f"Failed to find orderlists: {e}")
                # Provide default orderlists
                orderlists = [[0], [0], [0]]
                logger.warning("Using default orderlists")

            # Find sequences
            logger.info("Finding sequences...")
            try:
                sequences, sequence_addrs = self.find_sequences()
            except Exception as e:
                logger.error(f"Failed to find sequences: {e}")
                # Provide minimal default sequences
                sequences = [bytes([0x7F])]  # Empty sequence
                sequence_addrs = [self.load_address]
                logger.warning("Using default sequences")

            # Find instruments
            logger.info("Finding instruments...")
            try:
                instruments = self.find_instruments()
            except Exception as e:
                logger.error(f"Failed to find instruments: {e}")
                # Provide default instruments
                instruments = [bytes([0x09, 0x00, 0x41, 0x00, 0x08, 0x00, 0x00, 0x00])]
                logger.warning("Using default instruments")

            # Find command table
            logger.info("Finding command table...")
            try:
                command_table = self.find_command_table(sequences)
            except Exception as e:
                logger.error(f"Failed to find command table: {e}")
                command_table = []
                logger.warning("Using empty command table")

            return LaxityData(
                orderlists=orderlists,
                sequences=sequences,
                instruments=instruments,
                sequence_addrs=sequence_addrs,
                command_table=command_table
            )

        except ValueError:
            # Re-raise validation errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during parsing: {e}")
            raise RuntimeError(f"Failed to parse Laxity data: {e}")


def main():
    """Test the parser with Angular.sid"""
    import struct

    # Load SID file
    with open('SID/Angular.sid', 'rb') as f:
        data = f.read()

    # Parse PSID header
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_address = struct.unpack('>H', data[8:10])[0]

    c64_data = data[data_offset:]
    if load_address == 0:
        load_address = struct.unpack('<H', c64_data[0:2])[0]
        c64_data = c64_data[2:]

    # Parse
    parser = LaxityParser(c64_data, load_address)
    laxity_data = parser.parse()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Orderlists: {len(laxity_data.orderlists)}")
    for i, ol in enumerate(laxity_data.orderlists):
        print(f"  Voice {i+1}: {ol}")
    print(f"Sequences: {len(laxity_data.sequences)}")
    print(f"Instruments: {len(laxity_data.instruments)}")


if __name__ == '__main__':
    main()
