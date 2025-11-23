"""
Laxity player analyzer for extracting music data.
"""

import logging
from typing import List, Tuple
from .models import PSIDHeader, SequenceEvent, ExtractedData

logger = logging.getLogger(__name__)
from .table_extraction import (
    extract_all_laxity_tables,
    find_and_extract_wave_table,
    find_and_extract_pulse_table,
    find_and_extract_filter_table,
)
from .instrument_extraction import extract_laxity_instruments, extract_laxity_wave_table
from .sequence_extraction import get_command_names, analyze_sequence_commands

# Import LaxityParser from the existing module
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from laxity_parser import LaxityParser


class LaxityPlayerAnalyzer:
    """Analyze Laxity player format to extract music data"""

    def __init__(self, c64_data: bytes, load_address: int, header: PSIDHeader):
        self.data = c64_data
        self.load_address = load_address
        self.header = header
        self.memory = bytearray(65536)

        # Load data into virtual memory
        end_address = min(load_address + len(c64_data), 65536)
        self.memory[load_address:end_address] = c64_data[:end_address - load_address]

        self.sequence_regions = []
        self.instrument_data = []

    def get_byte(self, addr: int) -> int:
        """Get byte from virtual memory"""
        return self.memory[addr & 0xFFFF]

    def get_word(self, addr: int) -> int:
        """Get little-endian word from virtual memory"""
        return self.get_byte(addr) | (self.get_byte(addr + 1) << 8)

    def extract_tempo(self) -> int:
        """Extract tempo/speed from the SID file"""
        init_offset = self.header.init_address - self.load_address

        for i in range(init_offset, min(init_offset + 200, len(self.data) - 5)):
            if self.data[i] == 0xA9:  # LDA immediate
                value = self.data[i + 1]
                if 1 <= value <= 20:
                    if self.data[i + 2] in (0x85, 0x8D):
                        return value

        return 6

    def extract_init_volume(self) -> int:
        """Extract initial master volume from the SID init routine.

        Searches for patterns like:
        - LDA #$0F; STA $D418 (volume 15)
        - LDA #$xF; STA $D418 (volume x)

        Returns:
            Initial volume (0-15), defaults to 15 if not found
        """
        init_offset = self.header.init_address - self.load_address

        # Search for STA $D418 pattern (8D 18 D4) in init routine
        for i in range(init_offset, min(init_offset + 300, len(self.data) - 5)):
            # Check for STA $D418
            if (self.data[i] == 0x8D and
                self.data[i + 1] == 0x18 and
                self.data[i + 2] == 0xD4):

                # Look backwards for LDA immediate
                for j in range(i - 1, max(i - 10, init_offset), -1):
                    if self.data[j] == 0xA9:  # LDA immediate
                        value = self.data[j + 1]
                        # Volume is low nibble
                        volume = value & 0x0F
                        logger.debug(f"    Found init volume: ${value:02X} -> volume {volume}")
                        return volume

        # Alternative: search for LDA #$xF followed by STA to any address
        # Some players store volume in a variable first
        for i in range(init_offset, min(init_offset + 200, len(self.data) - 3)):
            if self.data[i] == 0xA9:  # LDA immediate
                value = self.data[i + 1]
                # Check if this looks like a volume value (low nibble)
                if (value & 0xF0) == 0 and value > 0:
                    # Check if next instruction is a store
                    if self.data[i + 2] in (0x85, 0x8D):  # STA
                        return value & 0x0F

        return 0x0F  # Default to max volume

    def detect_multi_speed(self) -> int:
        """Detect if this is a multi-speed tune"""
        play_addr = self.header.play_address
        play_lo = play_addr & 0xFF
        play_hi = (play_addr >> 8) & 0xFF

        jsr_count = 0
        for i in range(len(self.data) - 3):
            if self.data[i] == 0x20:  # JSR
                target_lo = self.data[i + 1]
                target_hi = self.data[i + 2]
                if target_lo == play_lo and target_hi == play_hi:
                    jsr_count += 1

        if jsr_count >= 4:
            return 4
        elif jsr_count >= 2:
            return 2

        return 1

    def extract_filter_table(self) -> bytes:
        """Extract filter modulation table"""
        filter_data = bytearray()

        for addr in range(0x1A00, 0x1C00):
            offset = addr - self.load_address
            if offset < 0 or offset >= len(self.data) - 64:
                continue

            is_filter = True
            prev_val = None
            for i in range(32):
                val = self.get_byte(addr + i)
                if prev_val is not None:
                    if abs(val - prev_val) > 32:
                        is_filter = False
                        break
                prev_val = val

            if is_filter:
                filter_data = bytes([self.get_byte(addr + i) for i in range(64)])
                break

        return bytes(filter_data)

    def extract_pulse_table(self) -> bytes:
        """Extract pulse width modulation table"""
        pulse_data = bytearray()

        for addr in range(0x1A00, 0x1C00):
            offset = addr - self.load_address
            if offset < 0 or offset >= len(self.data) - 64:
                continue

            oscillation_count = 0
            prev_val = self.get_byte(addr)
            direction = 0

            for i in range(1, 32):
                val = self.get_byte(addr + i)
                new_dir = 1 if val > prev_val else (-1 if val < prev_val else 0)
                if new_dir != 0 and new_dir != direction:
                    oscillation_count += 1
                    direction = new_dir
                prev_val = val

            if oscillation_count >= 4:
                pulse_data = bytes([self.get_byte(addr + i) for i in range(64)])
                break

        return bytes(pulse_data)

    def extract_commands(self) -> List[bytes]:
        """Extract command/effect definitions"""
        commands = []

        for addr in range(0x1A60, 0x1C00):
            offset = addr - self.load_address
            if offset < 0 or offset >= len(self.data) - 32:
                continue

            cmd_data = bytes([self.get_byte(addr + i) for i in range(8)])

            if cmd_data[0] in range(0x00, 0x10):
                commands.append(cmd_data)

                if len(commands) >= 32:
                    break

        return commands

    def extract_instruments(self) -> List[bytes]:
        """Extract instrument data from the SID file.

        Returns list of 8-byte instrument definitions in SF2 format:
        [AD, SR, Wave, Pulse Lo, Pulse Hi, Filter, unused, unused]
        """
        instruments = []

        # Try to find instrument table
        from .table_extraction import find_instrument_table
        instr_addr = find_instrument_table(self.data, self.load_address)

        if instr_addr:
            instr_offset = instr_addr - self.load_address

            # Extract up to 32 instruments (8 bytes each in Laxity format)
            for i in range(32):
                off = instr_offset + (i * 8)
                if off + 8 <= len(self.data):
                    # Read Laxity 8-byte format
                    laxity_instr = self.data[off:off + 8]
                    ad = laxity_instr[0]
                    sr = laxity_instr[1]

                    # Stop if we hit empty instrument
                    if ad == 0 and sr == 0 and laxity_instr[7] == 0 and i > 0:
                        break

                    # Convert to SF2 8-byte format
                    # [AD, SR, Wave, Pulse Lo, Pulse Hi, Filter, unused, unused]
                    wave = 0x41  # Default pulse
                    sf2_instr = bytes([ad, sr, wave, 0x00, 0x08, 0x00, 0x00, 0x00])
                    instruments.append(sf2_instr)
                else:
                    break

        # Return at least one default instrument
        if not instruments:
            instruments.append(bytes([0x09, 0x00, 0x41, 0x00, 0x08, 0x00, 0x00, 0x00]))

        return instruments

    def map_command(self, cmd_byte: int) -> Tuple[int, str]:
        """Map a command byte to its command number and name.

        Args:
            cmd_byte: Command byte from sequence data

        Returns:
            Tuple of (command_number, command_name)
        """
        # Command names from Laxity/JCH format
        command_names = {
            0xC0: "Set duration",
            0xC1: "Slide up",
            0xC2: "Slide down",
            0xC3: "Set ADSR",
            0xC4: "Set wave",
            0xC5: "Vibrato",
            0xC6: "Portamento",
            0xC7: "Set filter",
            0xC8: "Set pulse",
            0xC9: "Arpeggio",
            0xCA: "Note delay",
            0xCB: "Note cut",
            0xCC: "Legato on",
            0xCD: "Legato off",
            0xCE: "Set tempo",
            0xCF: "End",
        }

        # Duration commands (0x80-0xBF)
        if 0x80 <= cmd_byte <= 0xBF:
            return (cmd_byte, "Duration")

        # Super commands (0xC0-0xCF)
        if cmd_byte in command_names:
            return (cmd_byte, command_names[cmd_byte])

        return (cmd_byte, f"Unknown ${cmd_byte:02X}")

    def find_data_tables(self) -> dict:
        """Attempt to identify data tables in the Laxity player format."""
        tables = {}

        init_addr = self.header.init_address
        play_addr = self.header.play_address

        logger.debug(f"Init address: ${init_addr:04X}")
        logger.debug(f"Play address: ${play_addr:04X}")
        logger.debug(f"Load address: ${self.load_address:04X}")
        logger.debug(f"Data size: {len(self.data)} bytes")

        self._find_pointer_tables(tables)
        self._find_sequence_data(tables)

        return tables

    def _find_pointer_tables(self, tables: dict):
        """Find low/high byte pointer tables"""
        data_start = self.load_address
        data_end = self.load_address + len(self.data)

        candidates = []

        for addr in range(data_start, data_end - 32):
            values = [self.get_byte(addr + i) for i in range(16)]

            is_potential_table = True
            for v in values:
                if v == 0xFF:
                    break

            if is_potential_table:
                for offset in range(1, 256):
                    hi_addr = addr + offset
                    if hi_addr >= data_end - 16:
                        break

                    hi_values = [self.get_byte(hi_addr + i) for i in range(16)]

                    valid_pointers = 0
                    resolved_ptrs = []
                    for i in range(16):
                        ptr = values[i] | (hi_values[i] << 8)
                        if data_start <= ptr < data_end:
                            valid_pointers += 1
                            resolved_ptrs.append(ptr)

                    if valid_pointers >= 8:
                        candidates.append((addr, hi_addr, valid_pointers, resolved_ptrs))

        candidates.sort(key=lambda x: x[2], reverse=True)

        if candidates:
            tables['pointer_tables'] = candidates[:5]
            if candidates:
                best = candidates[0]
                tables['resolved_pointers'] = best[3]
                tables['ptr_lo_addr'] = best[0]
                tables['ptr_hi_addr'] = best[1]
            logger.debug(f"Found {len(candidates)} potential pointer table pairs")

    def _find_sequence_data(self, tables: dict):
        """Find sequence data patterns"""
        data_start = self.load_address
        data_end = self.load_address + len(self.data)

        sequence_candidates = []

        for addr in range(data_start, data_end - 32):
            score = 0
            for i in range(32):
                byte = self.get_byte(addr + i)

                if 0x00 <= byte <= 0x60:
                    score += 1
                elif byte in (0x7E, 0x7F):
                    score += 2
                elif 0xC0 <= byte <= 0xFF:
                    score += 1
                elif 0xA0 <= byte <= 0xBF:
                    score += 1

            if score >= 20:
                sequence_candidates.append((addr, score))

        if sequence_candidates:
            tables['sequence_regions'] = sequence_candidates[:20]
            logger.debug(f"Found {len(sequence_candidates)} potential sequence regions")

    def extract_music_data(self) -> ExtractedData:
        """Extract music data from the SID file using Laxity parser"""

        # Use the dedicated Laxity parser for accurate extraction
        laxity = LaxityParser(self.data, self.load_address)
        laxity_data = laxity.parse()

        # Extract other data
        tables = self.find_data_tables()
        tempo = self.extract_tempo()
        init_volume = self.extract_init_volume()
        multi_speed = self.detect_multi_speed()
        filter_table = self.extract_filter_table()
        pulse_table = self.extract_pulse_table()
        commands = self.extract_commands()

        # Create extracted data structure
        extracted = ExtractedData(
            header=self.header,
            c64_data=self.data,
            load_address=self.load_address,
            sequences=[],
            orderlists=[],
            instruments=[],
            wavetable=b'',
            pulsetable=pulse_table,
            filtertable=filter_table,
            tempo=tempo,
            init_volume=init_volume,
            multi_speed=multi_speed,
            commands=commands,
            pointer_tables=tables
        )

        # Store raw sequences
        extracted.raw_sequences = laxity_data.sequences

        # Create SequenceEvent representation
        for raw_seq in laxity_data.sequences:
            seq = []
            for b in raw_seq:
                if b <= 0x70 or b == 0x7E or b == 0x7F:
                    seq.append(SequenceEvent(0x80, 0x00, b))
            if seq:
                extracted.sequences.append(seq)

        # Convert orderlists
        for orderlist_indices in laxity_data.orderlists:
            orderlist = []
            for seq_idx in orderlist_indices:
                orderlist.append((0, seq_idx))
            if not orderlist:
                orderlist.append((0, 0))
            extracted.orderlists.append(orderlist)

        # Use Laxity-extracted instruments
        for instr_data in laxity_data.instruments:
            extracted.instruments.append(instr_data)

        # Validate
        self._validate_extracted_data(extracted)

        logger.info(f"Extracted {len(extracted.sequences)} sequences (via Laxity parser)")
        logger.info(f"Extracted {len(extracted.instruments)} instruments")
        logger.info(f"Created {len(extracted.orderlists)} orderlists")
        for i, ol in enumerate(extracted.orderlists):
            seq_indices = [idx for _, idx in ol]
            logger.debug(f"  Voice {i+1}: sequences {seq_indices}")
        logger.info(f"Tempo: {extracted.tempo}")
        if extracted.multi_speed > 1:
            logger.info(f"Multi-speed: {extracted.multi_speed}x")
        logger.debug(f"Filter table: {len(extracted.filtertable)} bytes")
        logger.debug(f"Pulse table: {len(extracted.pulsetable)} bytes")

        if extracted.validation_errors:
            logger.warning(f"Validation warnings: {len(extracted.validation_errors)}")
            for err in extracted.validation_errors[:5]:
                logger.warning(f"  - {err}")

        return extracted

    def _validate_extracted_data(self, extracted: ExtractedData):
        """Validate extracted data for integrity"""
        errors = []

        # Validate sequences
        for i, seq in enumerate(extracted.sequences):
            if len(seq) == 0:
                errors.append(f"Sequence {i} is empty")
            elif len(seq) > 256:
                errors.append(f"Sequence {i} too long ({len(seq)} events)")

            for j, event in enumerate(seq):
                if event.note > 0x5D and event.note not in (0x7E, 0x7F):
                    if event.note <= 0x70:
                        errors.append(f"Seq {i} event {j}: note ${event.note:02X} out of range")
                    elif event.note > 0x7F:
                        errors.append(f"Seq {i} event {j}: invalid note ${event.note:02X}")

        # Validate instruments
        for i, instr in enumerate(extracted.instruments):
            if len(instr) < 6:
                errors.append(f"Instrument {i} too short ({len(instr)} bytes)")

        # Validate orderlists
        for i, orderlist in enumerate(extracted.orderlists):
            if len(orderlist) == 0:
                errors.append(f"Orderlist {i} is empty")

            for j, (trans, seq_idx) in enumerate(orderlist):
                if seq_idx >= len(extracted.sequences):
                    errors.append(f"Orderlist {i} entry {j}: invalid seq index {seq_idx}")

        # Validate tempo
        if extracted.tempo < 1 or extracted.tempo > 31:
            errors.append(f"Unusual tempo value: {extracted.tempo}")

        extracted.validation_errors = errors
