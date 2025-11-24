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
    extract_hr_table,
    extract_init_table,
    extract_arp_table,
    extract_command_table,
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
        """Extract tempo/speed from the SID file.

        Laxity uses break speeds: first 4 bytes of filter table contain
        alternative speed lookup. Speed values 0-1 index into this table.
        """
        # Check filter table for break speeds (Laxity format)
        # Filter table is typically at $1A1E, first 4 bytes are break speeds
        filter_offset = 0x1A1E - self.load_address
        if 0 <= filter_offset < len(self.data) - 4:
            # Read first 4 bytes (break speed table)
            break_speeds = [self.data[filter_offset + i] for i in range(4)]
            # Filter out wrapping markers ($00) and invalid values
            valid_speeds = [s for s in break_speeds if 1 <= s <= 20]
            if valid_speeds:
                # Use the most common non-zero speed
                from collections import Counter
                speed_counts = Counter(valid_speeds)
                most_common_speed = speed_counts.most_common(1)[0][0]
                logger.debug(f"    Found break speeds in filter table: {break_speeds}")
                logger.debug(f"    Using most common speed: {most_common_speed}")
                return most_common_speed

        # Fallback to init routine search
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
        """Detect if this is a multi-speed tune.

        Multi-speed tunes call the play routine multiple times per frame.
        Detection methods:
        1. Check PSID speed flag (bit indicates CIA timer usage)
        2. Count JSR instructions to play address
        3. Look for CIA timer setup patterns

        Returns:
            1 = normal (1x per frame)
            2 = 2x per frame
            4 = 4x per frame
        """
        # Check PSID header speed flag
        # speed=0 means VBlank (50/60 Hz), speed=1 means CIA timer
        if hasattr(self.header, 'speed') and self.header.speed == 1:
            # CIA timer - likely multi-speed
            logger.debug("    PSID speed flag indicates CIA timer")

        play_addr = self.header.play_address
        play_lo = play_addr & 0xFF
        play_hi = (play_addr >> 8) & 0xFF

        # Count JSR instructions to play address
        jsr_count = 0
        for i in range(len(self.data) - 3):
            if self.data[i] == 0x20:  # JSR
                target_lo = self.data[i + 1]
                target_hi = self.data[i + 2]
                if target_lo == play_lo and target_hi == play_hi:
                    jsr_count += 1

        # Look for CIA timer setup patterns
        # Common pattern: LDA #$xx, STA $DC04 (timer low), LDA #$xx, STA $DC05 (timer high)
        cia_timer_detected = False
        for i in range(len(self.data) - 6):
            # Check for STA $DC04 or STA $DC05 (CIA timer registers)
            if (self.data[i] == 0x8D and
                self.data[i + 1] in (0x04, 0x05) and
                self.data[i + 2] == 0xDC):
                cia_timer_detected = True
                break

        # Determine multi-speed factor
        if jsr_count >= 4:
            return 4
        elif jsr_count >= 2:
            return 2
        elif cia_timer_detected and hasattr(self.header, 'speed') and self.header.speed == 1:
            # CIA timer but no multiple JSRs - assume 2x
            return 2

        return 1

    def extract_filter_table(self) -> bytes:
        """Extract filter modulation table from Laxity SID.

        Returns bytes in SF2 format: 4 bytes per entry (cutoff, step, duration, next).
        """
        addr, entries = find_and_extract_filter_table(self.data, self.load_address)

        if not entries:
            return b''

        # Convert list of (cutoff, step, duration, next) tuples to bytes
        filter_data = bytearray()
        for entry in entries:
            for byte_val in entry:
                filter_data.append(byte_val)

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

    def extract_wave_table(self) -> bytes:
        """Extract wave table from Laxity SID.

        Returns bytes in SF2 format: (note_offset, waveform) pairs.
        """
        from .table_extraction import find_and_extract_wave_table

        addr, entries = find_and_extract_wave_table(self.data, self.load_address)

        if not entries:
            return b''

        # Convert list of (waveform, note_offset) tuples to bytes
        # SF2 format is (note_offset, waveform) pairs
        wave_data = bytearray()
        for waveform, note_offset in entries:
            wave_data.append(note_offset)
            wave_data.append(waveform)

        return bytes(wave_data)

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
        wave_table = self.extract_wave_table()
        commands = self.extract_commands()

        # Extract HR and Init tables
        hr_table = extract_hr_table(self.data, self.load_address, self.header.init_address)
        init_table = extract_init_table(self.data, self.load_address, self.header.init_address,
                                        tempo, init_volume)

        # Extract arpeggio table
        arp_table = extract_arp_table(self.data, self.load_address)

        # Create extracted data structure
        extracted = ExtractedData(
            header=self.header,
            c64_data=self.data,
            load_address=self.load_address,
            sequences=[],
            orderlists=[],
            instruments=[],
            wavetable=wave_table,
            pulsetable=pulse_table,
            filtertable=filter_table,
            tempo=tempo,
            init_volume=init_volume,
            multi_speed=multi_speed,
            commands=commands,
            pointer_tables=tables,
            hr_table=hr_table,
            init_table=init_table,
            arp_table=arp_table
        )

        # Store raw sequences
        extracted.raw_sequences = laxity_data.sequences

        # Create SequenceEvent representation
        # Parse Laxity sequence format properly:
        # - 0xA0-0xBF: instrument change (instrument = byte - 0xA0 + 0xA0 for SF2)
        # - 0xC0-0xCF: command bytes (followed by parameter byte)
        # - 0x80-0x9F: duration/timing (number of frames)
        # - 0x00-0x6F: note values
        # - 0x7E: gate on (sustain)
        # - 0x7F: end marker
        for raw_seq in laxity_data.sequences:
            seq = []
            current_instr = 0x80  # No change
            current_cmd = 0x00    # No command
            current_cmd_param = 0x00  # Command parameter
            current_duration = 1  # Default duration (1 frame)
            i = 0

            while i < len(raw_seq):
                b = raw_seq[i]

                # Instrument change: 0xA0-0xBF
                if 0xA0 <= b <= 0xBF:
                    current_instr = b  # Keep as-is for SF2 format
                    i += 1
                    continue

                # Command: 0xC0-0xCF (followed by parameter byte)
                elif 0xC0 <= b <= 0xCF:
                    current_cmd = b
                    i += 1
                    # Extract parameter byte
                    if i < len(raw_seq):
                        current_cmd_param = raw_seq[i]
                        logger.debug(f"    Extracted command ${b:02X} with param ${current_cmd_param:02X}")
                        i += 1
                    continue

                # Duration/timing: 0x80-0x9F (Laxity uses full range)
                # 0x80 = 1 frame, 0x81 = 2 frames, ..., 0x9F = 32 frames
                elif 0x80 <= b <= 0x9F:
                    current_duration = b - 0x80 + 1
                    logger.debug(f"    Set duration to {current_duration} frames")
                    i += 1
                    continue

                # Note or control byte: 0x00-0x7F
                elif b <= 0x7F:
                    # Clamp high notes to SF2 max (0x5D = B-7), but keep control bytes
                    note = b
                    if note > 0x5D and note not in (0x7E, 0x7F):
                        note = 0x5D  # Clamp to B-7

                    # Add note event with current instrument/command
                    seq.append(SequenceEvent(current_instr, current_cmd, note))

                    # Expand duration: add gate-on events (0x7E) for sustain
                    # Skip expansion for control bytes (0x7E, 0x7F)
                    if note not in (0x7E, 0x7F) and current_duration > 1:
                        for _ in range(current_duration - 1):
                            # Gate on event: no instrument/command change, note = 0x7E (sustain)
                            seq.append(SequenceEvent(0x80, 0x00, 0x7E))

                    # Reset state after note
                    current_instr = 0x80  # Reset to "no change" after use
                    current_cmd = 0x00
                    current_cmd_param = 0x00
                    current_duration = 1  # Reset to default
                    i += 1
                    continue

                else:
                    # Unknown byte, skip
                    logger.debug(f"    Unknown byte ${b:02X} at offset {i}, skipping")
                    i += 1

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

        # Validate instrument table linkage
        # Laxity uses Y*4 indexing for pulse tables (64 entries = 256 bytes, ptrs 0-252)
        # Filter tables also use similar indexing
        wave_table_size = len(extracted.wavetable) // 2 if extracted.wavetable else 0
        # For pulse/filter, the raw table bytes divided by 4 gives entry count
        # But the pointers are pre-multiplied, so valid range is 0 to (entries-1)*4
        pulse_bytes = len(extracted.pulsetable) if extracted.pulsetable else 0
        filter_bytes = len(extracted.filtertable) if extracted.filtertable else 0

        for i, instr in enumerate(extracted.instruments):
            if len(instr) >= 8:
                # Laxity format: byte 4=filter_ptr, byte 5=pulse_ptr, byte 7=wave_ptr
                filter_ptr = instr[4]
                pulse_ptr = instr[5]
                wave_ptr = instr[7]

                # Check wave_ptr bounds (direct index)
                if wave_table_size > 0 and wave_ptr >= wave_table_size:
                    errors.append(f"Instrument {i}: wave_ptr {wave_ptr} exceeds wave table size {wave_table_size}")

                # Check pulse_ptr bounds (Laxity uses Y*4 indexing, so ptr must be < total bytes)
                if pulse_bytes > 0 and pulse_ptr >= pulse_bytes:
                    errors.append(f"Instrument {i}: pulse_ptr {pulse_ptr} exceeds pulse table bytes {pulse_bytes}")

                # Check filter_ptr bounds (similar to pulse)
                if filter_bytes > 0 and filter_ptr > 0 and filter_ptr >= filter_bytes:
                    errors.append(f"Instrument {i}: filter_ptr {filter_ptr} exceeds filter table bytes {filter_bytes}")

        extracted.validation_errors = errors
