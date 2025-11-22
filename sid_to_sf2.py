#!/usr/bin/env python3
"""
SID to SID Factory II (.sf2) Converter

This tool attempts to convert Commodore 64 .sid files into SID Factory II
project files. It's specifically designed for SID files using Laxity's player
routine, as used in the Unboxed_Ending_8580.sid file.

Note: This is a complex reverse-engineering task. Results may require manual
refinement in SID Factory II.
"""

import struct
import sys
import os
from dataclasses import dataclass
from typing import List, Optional, Tuple
from laxity_parser import LaxityParser


def find_sid_register_tables(data, load_addr):
    """
    Find table addresses for each SID register by tracing
    STA $D4xx,Y instructions back to their LDA source.
    Returns dict mapping SID register offset to table address.
    """
    tables = {}

    for i in range(len(data) - 3):
        # STA $D4xx,Y (99 lo hi)
        if data[i] == 0x99:
            addr = data[i + 1] | (data[i + 2] << 8)
            if not (0xD400 <= addr <= 0xD418):
                continue

            reg = addr - 0xD400

            # Look backwards for LDA table,X
            for j in range(1, 30):
                if i - j < 0:
                    break

                # LDA $xxxx,X (BD lo hi)
                if data[i - j] == 0xBD:
                    table = data[i - j + 1] | (data[i - j + 2] << 8)
                    tables[reg] = table
                    break

    return tables


def extract_laxity_instruments(data, load_addr):
    """
    Extract actual instrument data from Laxity SID file.
    Returns list of instrument dicts with ad, sr, ctrl, wave info.
    """
    tables = find_sid_register_tables(data, load_addr)

    instruments = []

    ad_table = tables.get(0x05)  # AD register
    sr_table = tables.get(0x06)  # SR register
    ctrl_table = tables.get(0x04)  # Control register

    if not ad_table:
        return instruments

    # Calculate number of instruments from table spacing
    if sr_table and ctrl_table:
        num_instr = sr_table - ad_table
    else:
        num_instr = 16

    for i in range(min(num_instr, 16)):
        ad_off = ad_table - load_addr + i
        sr_off = sr_table - load_addr + i if sr_table else ad_off
        ctrl_off = ctrl_table - load_addr + i if ctrl_table else ad_off

        if ad_off >= len(data) or sr_off >= len(data) or ctrl_off >= len(data):
            break

        ad = data[ad_off]
        sr = data[sr_off]
        ctrl = data[ctrl_off]

        # Decode waveform from control byte
        wave_for_sf2 = 0x21  # Default saw

        if ctrl & 0x80:
            wave_for_sf2 = 0x81  # noise
        elif ctrl & 0x40:
            wave_for_sf2 = 0x41  # pulse
        elif ctrl & 0x20:
            wave_for_sf2 = 0x21  # saw
        elif ctrl & 0x10:
            wave_for_sf2 = 0x11  # tri

        instruments.append({
            'index': i,
            'ad': ad,
            'sr': sr,
            'ctrl': ctrl,
            'wave_for_sf2': wave_for_sf2
        })

    return instruments


@dataclass
class PSIDHeader:
    """PSID/RSID file header structure"""
    magic: str
    version: int
    data_offset: int
    load_address: int
    init_address: int
    play_address: int
    songs: int
    start_song: int
    speed: int
    name: str
    author: str
    copyright: str
    # V2+ fields
    flags: int = 0
    start_page: int = 0
    page_length: int = 0
    second_sid_address: int = 0
    third_sid_address: int = 0


@dataclass
class SequenceEvent:
    """A single event in a sequence"""
    instrument: int
    command: int
    note: int


@dataclass
class ExtractedData:
    """Data extracted from SID file"""
    header: PSIDHeader
    c64_data: bytes
    load_address: int
    # Identified data regions
    sequences: List[List[SequenceEvent]]
    orderlists: List[List[Tuple[int, int]]]  # (transposition, sequence_index)
    instruments: List[bytes]
    wavetable: bytes
    pulsetable: bytes
    filtertable: bytes
    # New fields for improvements
    tempo: int = 6  # Default tempo (6 = ~7.5 rows per second at 50Hz)
    commands: List[bytes] = None  # Command/effect definitions
    pointer_tables: dict = None  # Parsed pointer table info
    validation_errors: List[str] = None  # Validation results
    raw_sequences: List[bytes] = None  # Raw sequence bytes for direct copy

    def __post_init__(self):
        if self.commands is None:
            self.commands = []
        if self.pointer_tables is None:
            self.pointer_tables = {}
        if self.validation_errors is None:
            self.validation_errors = []
        if self.raw_sequences is None:
            self.raw_sequences = []


@dataclass
class LaxityCommand:
    """Mapping of Laxity command to SF2 command"""
    laxity_cmd: int
    sf2_cmd: int
    name: str
    parameters: int = 0


class SIDParser:
    """Parser for PSID/RSID files"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        with open(filepath, 'rb') as f:
            self.data = f.read()

    def parse_header(self) -> PSIDHeader:
        """Parse the PSID/RSID header"""
        magic = self.data[0:4].decode('ascii')
        if magic not in ('PSID', 'RSID'):
            raise ValueError(f"Invalid SID file magic: {magic}")

        version = struct.unpack('>H', self.data[4:6])[0]
        data_offset = struct.unpack('>H', self.data[6:8])[0]
        load_address = struct.unpack('>H', self.data[8:10])[0]
        init_address = struct.unpack('>H', self.data[10:12])[0]
        play_address = struct.unpack('>H', self.data[12:14])[0]
        songs = struct.unpack('>H', self.data[14:16])[0]
        start_song = struct.unpack('>H', self.data[16:18])[0]
        speed = struct.unpack('>I', self.data[18:22])[0]

        # Strings are 32 bytes each, null-terminated
        name = self.data[22:54].split(b'\x00')[0].decode('latin-1')
        author = self.data[54:86].split(b'\x00')[0].decode('latin-1')
        copyright = self.data[86:118].split(b'\x00')[0].decode('latin-1')

        header = PSIDHeader(
            magic=magic,
            version=version,
            data_offset=data_offset,
            load_address=load_address,
            init_address=init_address,
            play_address=play_address,
            songs=songs,
            start_song=start_song,
            speed=speed,
            name=name,
            author=author,
            copyright=copyright
        )

        # Parse V2+ fields
        if version >= 2 and data_offset >= 0x7C:
            header.flags = struct.unpack('>H', self.data[118:120])[0]
            header.start_page = self.data[120]
            header.page_length = self.data[121]
            header.second_sid_address = self.data[122]
            header.third_sid_address = self.data[123]

        return header

    def get_c64_data(self, header: PSIDHeader) -> Tuple[bytes, int]:
        """Extract the C64 program data and determine load address"""
        c64_data = self.data[header.data_offset:]

        # If load_address is 0, first two bytes are the actual load address
        if header.load_address == 0:
            load_address = struct.unpack('<H', c64_data[0:2])[0]
            c64_data = c64_data[2:]
        else:
            load_address = header.load_address

        return c64_data, load_address


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

        # Key addresses from analysis
        # These are specific to the Laxity player in Unboxed_Ending_8580.sid
        self.sequence_regions = []
        self.instrument_data = []

    def get_byte(self, addr: int) -> int:
        """Get byte from virtual memory"""
        return self.memory[addr & 0xFFFF]

    def get_word(self, addr: int) -> int:
        """Get little-endian word from virtual memory"""
        return self.get_byte(addr) | (self.get_byte(addr + 1) << 8)

    def find_sequence_data(self) -> List[Tuple[int, List[bytes]]]:
        """
        Find and extract sequence data from the SID file.

        Based on analysis, Laxity player sequence data appears to use format:
        - Command/duration byte (0xC0-0xCF range, or 0x80-0x9F)
        - Instrument byte (0x80=none, 0x81-0x9F=instrument, or note continuation)
        - Note byte (0x00-0x60, 0x7E=rest/tie, 0x7F=end)

        The detection uses a scoring system to identify high-quality sequences.
        """
        sequences = []

        # Scan for high-scoring sequence regions
        data_start = self.load_address
        data_end = self.load_address + len(self.data)

        checked = set()

        # First pass: identify potential sequence start points
        candidates = []

        for addr in range(data_start + 0x800, data_end - 32):
            if addr in checked:
                continue

            score = 0
            confidence = 0
            events = []

            # Try to read sequence events
            pos = addr
            consecutive_valid = 0
            max_consecutive = 0

            while pos < data_end - 3:
                b1 = self.get_byte(pos)
                b2 = self.get_byte(pos + 1)
                b3 = self.get_byte(pos + 2)

                # Scoring criteria for valid triplets
                triplet_score = 0

                # Check note byte (most reliable indicator)
                if b3 <= 0x60:  # Valid note
                    triplet_score += 3
                elif b3 == 0x7E:  # Rest/tie
                    triplet_score += 4
                elif b3 == 0x7F:  # End marker
                    triplet_score += 5
                else:
                    triplet_score -= 5

                # Check command/duration byte
                if 0xC0 <= b1 <= 0xCF:  # Command range
                    triplet_score += 2
                elif 0x80 <= b1 <= 0x9F:  # Instrument/duration
                    triplet_score += 2
                elif b1 <= 0x60:  # Could be note (different format)
                    triplet_score += 1

                # Check instrument byte
                if b2 == 0x80:  # No instrument change
                    triplet_score += 1
                elif 0x81 <= b2 <= 0x9F:  # Instrument change
                    triplet_score += 2
                elif 0x90 <= b2 <= 0x97:  # Tie note
                    triplet_score += 2

                # Valid triplet threshold
                if triplet_score >= 4:
                    score += triplet_score
                    consecutive_valid += 1
                    max_consecutive = max(max_consecutive, consecutive_valid)
                    events.append((b1, b2, b3))

                    # Mark as checked
                    for i in range(3):
                        checked.add(pos + i)

                    if b3 == 0x7F:  # End marker found
                        confidence += 10
                        break

                    pos += 3
                else:
                    consecutive_valid = 0
                    # Allow one bad triplet before giving up
                    if len(events) > 0 and events[-1][2] != 0x7F:
                        break
                    pos += 1

            # Calculate overall confidence
            if events:
                confidence += min(len(events), 20)  # More events = more confident
                confidence += max_consecutive * 2  # Consecutive valid = good
                confidence += score // 10

                # Bonus for ending with end marker
                if events and events[-1][2] == 0x7F:
                    confidence += 5

            # Only keep sequences with sufficient confidence
            if confidence >= 15 and len(events) >= 4:
                candidates.append((addr, events, confidence))

        # Sort by confidence and take best sequences
        candidates.sort(key=lambda x: x[2], reverse=True)

        # Remove overlapping sequences (keep higher confidence ones)
        used_ranges = set()
        for addr, events, confidence in candidates:
            # Check if this range overlaps with already selected sequence
            seq_range = set(range(addr, addr + len(events) * 3))
            if not seq_range & used_ranges:
                sequences.append((addr, events))
                used_ranges.update(seq_range)

                if len(sequences) >= 50:  # Limit total sequences
                    break

        return sequences

    def extract_instruments(self) -> List[bytes]:
        """Extract instrument definitions with improved detection"""
        instruments = []

        # Look for instrument table patterns around $19E0-$1A60
        # Based on analysis, instruments are typically 8 bytes each in SF2
        # Laxity format: AD, SR, Wave, PulseLo, PulseHi, ...

        # First, try to find the instrument table by looking for waveform patterns
        best_addr = None
        best_count = 0

        for start_addr in range(0x19C0, 0x1A40):
            count = 0
            for i in range(32):  # Check up to 32 instruments
                addr = start_addr + i * 6  # 6 bytes per instrument in Laxity
                offset = addr - self.load_address
                if offset < 0 or offset >= len(self.data) - 6:
                    break

                # Check waveform byte (byte 2)
                wave = self.get_byte(addr + 2)
                if wave in (0x11, 0x21, 0x41, 0x81, 0x10, 0x20, 0x40, 0x80,
                           0x12, 0x22, 0x42, 0x82, 0x14, 0x24, 0x44, 0x84):
                    # Verify ADSR values are reasonable
                    ad = self.get_byte(addr)
                    sr = self.get_byte(addr + 1)
                    if ad <= 0xFF and sr <= 0xFF:
                        count += 1
                else:
                    break

            if count > best_count:
                best_count = count
                best_addr = start_addr

        # Extract instruments from best location
        if best_addr and best_count >= 1:
            for i in range(best_count):
                addr = best_addr + i * 6
                # Convert 6-byte Laxity to 8-byte SF2 format
                instr = bytes([
                    self.get_byte(addr),      # Attack/Decay
                    self.get_byte(addr + 1),  # Sustain/Release
                    self.get_byte(addr + 2),  # Waveform
                    self.get_byte(addr + 3),  # Pulse Lo
                    self.get_byte(addr + 4),  # Pulse Hi
                    self.get_byte(addr + 5) if addr + 5 - self.load_address < len(self.data) else 0,
                    0x00,  # Padding
                    0x00   # Padding
                ])
                instruments.append(instr)

        return instruments

    def find_data_tables(self) -> dict:
        """
        Attempt to identify data tables in the Laxity player format.

        Laxity's player typically has:
        - Sequence pointers (low/high byte tables)
        - Order lists for each voice
        - Instrument definitions
        - Wave/Pulse/Filter tables
        """
        tables = {}

        # The init address often points to initialization code
        # Data tables are usually after the player code
        init_addr = self.header.init_address
        play_addr = self.header.play_address

        print(f"Init address: ${init_addr:04X}")
        print(f"Play address: ${play_addr:04X}")
        print(f"Load address: ${self.load_address:04X}")
        print(f"Data size: {len(self.data)} bytes")

        # Scan for potential pointer tables
        # Looking for patterns like sequential addresses
        self._find_pointer_tables(tables)

        # Look for sequence data patterns
        self._find_sequence_data(tables)

        return tables

    def _find_pointer_tables(self, tables: dict):
        """Find low/high byte pointer tables with improved analysis"""
        # Scan through memory looking for potential pointer tables
        # These usually appear as pairs of tables with related values

        data_start = self.load_address
        data_end = self.load_address + len(self.data)

        candidates = []

        for addr in range(data_start, data_end - 32):
            # Check if this could be a low-byte table
            # Look for incrementing or related values
            values = [self.get_byte(addr + i) for i in range(16)]

            # Check for pattern of sequence pointers
            # They often point to addresses within the data
            is_potential_table = True
            for v in values:
                if v == 0xFF:  # End marker
                    break

            if is_potential_table:
                # Try to find corresponding high-byte table
                for offset in range(1, 256):
                    hi_addr = addr + offset
                    if hi_addr >= data_end - 16:
                        break

                    hi_values = [self.get_byte(hi_addr + i) for i in range(16)]

                    # Check if these form valid pointers
                    valid_pointers = 0
                    resolved_ptrs = []
                    for i in range(16):
                        ptr = values[i] | (hi_values[i] << 8)
                        if data_start <= ptr < data_end:
                            valid_pointers += 1
                            resolved_ptrs.append(ptr)

                    if valid_pointers >= 8:
                        candidates.append((addr, hi_addr, valid_pointers, resolved_ptrs))

        # Sort by number of valid pointers
        candidates.sort(key=lambda x: x[2], reverse=True)

        if candidates:
            tables['pointer_tables'] = candidates[:5]
            # Store resolved pointers for use in extraction
            if candidates:
                best = candidates[0]
                tables['resolved_pointers'] = best[3]
                tables['ptr_lo_addr'] = best[0]
                tables['ptr_hi_addr'] = best[1]
            print(f"Found {len(candidates)} potential pointer table pairs")

    def extract_tempo(self) -> int:
        """Extract tempo/speed from the SID file"""
        # Laxity player typically stores tempo in a specific location
        # Common tempo values: 3-12 (lower = faster)

        # Search for tempo patterns near init routine
        init_offset = self.header.init_address - self.load_address

        # Look for LDA #$xx, STA tempo_addr pattern
        for i in range(init_offset, min(init_offset + 200, len(self.data) - 5)):
            if self.data[i] == 0xA9:  # LDA immediate
                value = self.data[i + 1]
                # Reasonable tempo range
                if 1 <= value <= 20:
                    # Check if followed by STA
                    if self.data[i + 2] in (0x85, 0x8D):  # STA zp or STA abs
                        return value

        # Default tempo
        return 6

    def extract_filter_table(self) -> bytes:
        """Extract filter modulation table"""
        # Filter tables typically contain cutoff frequency patterns
        # Look for patterns with values in filter range (0-2047 split across bytes)

        filter_data = bytearray()

        # Search for filter table patterns
        for addr in range(0x1A00, 0x1C00):
            offset = addr - self.load_address
            if offset < 0 or offset >= len(self.data) - 64:
                continue

            # Check for filter-like patterns
            # Filter tables often have smoothly changing values
            is_filter = True
            prev_val = None
            for i in range(32):
                val = self.get_byte(addr + i)
                if prev_val is not None:
                    # Filter values typically change gradually
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
        # Pulse tables contain PWM patterns (0-4095 range)

        pulse_data = bytearray()

        # Search for pulse table patterns
        for addr in range(0x1A00, 0x1C00):
            offset = addr - self.load_address
            if offset < 0 or offset >= len(self.data) - 64:
                continue

            # Check for pulse-like patterns
            # Pulse tables often have oscillating values for PWM effect
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

            # Good pulse table has multiple oscillations
            if oscillation_count >= 4:
                pulse_data = bytes([self.get_byte(addr + i) for i in range(64)])
                break

        return bytes(pulse_data)

    def map_command(self, laxity_cmd: int) -> Tuple[int, str]:
        """Map Laxity command byte to SF2 command"""
        # Command mapping table based on Laxity player analysis
        command_map = {
            0xC0: (0xC0, "Set duration"),
            0xC1: (0xC1, "Set instrument"),
            0xC2: (0xC2, "Gate control"),
            0xC3: (0xC3, "Slide up"),
            0xC4: (0xC4, "Slide down"),
            0xC5: (0xC5, "Vibrato"),
            0xC6: (0xC6, "Portamento"),
            0xC7: (0xC7, "Arpeggio"),
            0xC8: (0xC8, "Filter on"),
            0xC9: (0xC9, "Filter off"),
            0xCA: (0xCA, "Pulse program"),
            0xCB: (0xCB, "Wave program"),
            0xCC: (0xCC, "ADSR change"),
            0xCD: (0xCD, "Tempo change"),
            0xCE: (0xCE, "Pattern break"),
            0xCF: (0xCF, "Loop/Jump"),
        }

        if laxity_cmd in command_map:
            return command_map[laxity_cmd]
        elif 0x80 <= laxity_cmd <= 0x9F:
            # Duration/gate commands
            return (0x80 + (laxity_cmd & 0x1F), "Duration")
        else:
            return (0x80, "None")

    def extract_commands(self) -> List[bytes]:
        """Extract command/effect definitions"""
        commands = []

        # Look for command table patterns
        # Commands typically follow instrument table
        for addr in range(0x1A60, 0x1C00):
            offset = addr - self.load_address
            if offset < 0 or offset >= len(self.data) - 32:
                continue

            # Check for command-like patterns
            # Commands often have specific byte patterns
            cmd_data = bytes([self.get_byte(addr + i) for i in range(8)])

            # Simple heuristic: commands often start with specific values
            if cmd_data[0] in range(0x00, 0x10):
                commands.append(cmd_data)

                if len(commands) >= 32:
                    break

        return commands

    def _find_sequence_data(self, tables: dict):
        """Find sequence data patterns"""
        # Sequence data in Laxity format typically has:
        # - Note values (usually in range 0x00-0x60)
        # - Command bytes (0xC0-0xFF range)
        # - Instrument changes

        data_start = self.load_address
        data_end = self.load_address + len(self.data)

        sequence_candidates = []

        for addr in range(data_start, data_end - 32):
            # Look for patterns that look like sequence data
            score = 0
            for i in range(32):
                byte = self.get_byte(addr + i)

                # Note values
                if 0x00 <= byte <= 0x60:
                    score += 1
                # Rest/tie values
                elif byte in (0x7E, 0x7F):
                    score += 2
                # Command bytes
                elif 0xC0 <= byte <= 0xFF:
                    score += 1
                # Instrument bytes (0xA0-0xBF in SF2 format)
                elif 0xA0 <= byte <= 0xBF:
                    score += 1

            if score >= 20:
                sequence_candidates.append((addr, score))

        # Group adjacent high-scoring regions
        if sequence_candidates:
            tables['sequence_regions'] = sequence_candidates[:20]
            print(f"Found {len(sequence_candidates)} potential sequence regions")

    def extract_music_data(self) -> ExtractedData:
        """Extract music data from the SID file using Laxity parser"""

        # Use the dedicated Laxity parser for accurate extraction
        laxity = LaxityParser(self.data, self.load_address)
        laxity_data = laxity.parse()

        # Extract other data using existing methods
        tables = self.find_data_tables()
        tempo = self.extract_tempo()
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
            commands=commands,
            pointer_tables=tables
        )

        # Store raw sequences directly - Laxity format is compatible with SF2!
        # Both use the same byte ranges:
        # - 0xA0-0xAF: instrument
        # - 0x80-0x9F: duration
        # - 0xC0-0xCF: command
        # - 0x00-0x6F: note
        # - 0x7F: end marker
        #
        # We'll convert to SequenceEvent format for the data structure,
        # but the SF2Writer will write the raw bytes.

        # Store raw sequence bytes for direct copying to SF2
        extracted.raw_sequences = laxity_data.sequences

        # Also create SequenceEvent representation for compatibility
        for raw_seq in laxity_data.sequences:
            seq = []
            # Count actual notes for event count (control bytes don't need events)
            for b in raw_seq:
                if b <= 0x70 or b == 0x7E or b == 0x7F:
                    # This is a note, rest, or end marker - create event
                    seq.append(SequenceEvent(0x80, 0x00, b))
            if seq:
                extracted.sequences.append(seq)

        # Convert Laxity orderlists to expected format
        # Laxity orderlist is just sequence indices
        # SF2 orderlist is (transposition, sequence_index)
        for orderlist_indices in laxity_data.orderlists:
            orderlist = []
            for seq_idx in orderlist_indices:
                orderlist.append((0, seq_idx))  # No transposition
            if not orderlist:
                orderlist.append((0, 0))
            extracted.orderlists.append(orderlist)

        # Use Laxity-extracted instruments
        for instr_data in laxity_data.instruments:
            extracted.instruments.append(instr_data)

        # Validate extracted data
        self._validate_extracted_data(extracted)

        print(f"Extracted {len(extracted.sequences)} sequences (via Laxity parser)")
        print(f"Extracted {len(extracted.instruments)} instruments")
        print(f"Created {len(extracted.orderlists)} orderlists")
        for i, ol in enumerate(extracted.orderlists):
            seq_indices = [idx for _, idx in ol]
            print(f"  Voice {i+1}: sequences {seq_indices}")
        print(f"Tempo: {extracted.tempo}")
        print(f"Filter table: {len(extracted.filtertable)} bytes")
        print(f"Pulse table: {len(extracted.pulsetable)} bytes")

        if extracted.validation_errors:
            print(f"Validation warnings: {len(extracted.validation_errors)}")
            for err in extracted.validation_errors[:5]:
                print(f"  - {err}")

        return extracted

    def _validate_extracted_data(self, extracted: ExtractedData):
        """Validate extracted data for integrity (#7)"""
        errors = []

        # Validate sequences
        for i, seq in enumerate(extracted.sequences):
            if len(seq) == 0:
                errors.append(f"Sequence {i} is empty")
            elif len(seq) > 256:
                errors.append(f"Sequence {i} too long ({len(seq)} events)")

            for j, event in enumerate(seq):
                # Check note range
                if event.note > 0x7F and event.note not in (0x7E, 0x7F):
                    errors.append(f"Seq {i} event {j}: invalid note ${event.note:02X}")

        # Validate instruments
        for i, instr in enumerate(extracted.instruments):
            if len(instr) < 6:
                errors.append(f"Instrument {i} too short ({len(instr)} bytes)")

            # Check waveform
            if len(instr) >= 3:
                wave = instr[2]
                valid_waves = (0x00, 0x10, 0x11, 0x20, 0x21, 0x40, 0x41, 0x80, 0x81,
                              0x12, 0x14, 0x22, 0x24, 0x42, 0x44, 0x82, 0x84)
                if wave not in valid_waves and wave != 0:
                    errors.append(f"Instrument {i}: unusual waveform ${wave:02X}")

        # Validate orderlists
        for i, orderlist in enumerate(extracted.orderlists):
            if len(orderlist) == 0:
                errors.append(f"Orderlist {i} is empty")

            for j, (trans, seq_idx) in enumerate(orderlist):
                if seq_idx >= len(extracted.sequences):
                    errors.append(f"Orderlist {i} entry {j}: invalid seq index {seq_idx}")
                if trans > 127:
                    errors.append(f"Orderlist {i} entry {j}: invalid transposition {trans}")

        # Validate tempo
        if extracted.tempo < 1 or extracted.tempo > 31:
            errors.append(f"Unusual tempo value: {extracted.tempo}")

        extracted.validation_errors = errors

    def _extract_with_heuristics(self, extracted: ExtractedData, tables: dict):
        """Use heuristics to extract music data"""
        # Create some basic sequences as placeholders
        # These will need to be refined

        # For a typical 3-voice SID tune:
        for voice in range(3):
            # Create empty orderlist
            extracted.orderlists.append([(0, 0)])

        # Create a simple test sequence
        test_sequence = [
            SequenceEvent(0, 0, 0x30),  # Note C-4
            SequenceEvent(0, 0, 0x34),  # Note E-4
            SequenceEvent(0, 0, 0x37),  # Note G-4
        ]
        extracted.sequences.append(test_sequence)

        # Create basic instrument data
        # Format: AD, SR, Wave, Pulse Lo, Pulse Hi, additional bytes
        basic_instrument = bytes([
            0x09,  # Attack/Decay
            0x00,  # Sustain/Release
            0x41,  # Waveform (pulse + gate)
            0x00, 0x08,  # Pulse width
            0x00, 0x00, 0x00  # Additional
        ])
        extracted.instruments.append(basic_instrument)


@dataclass
class SF2DriverInfo:
    """Parsed SF2 driver header information"""
    # Descriptor
    driver_type: int = 0
    driver_size: int = 0
    driver_name: str = ""
    driver_version_major: int = 0
    driver_version_minor: int = 0

    # Music data pointers
    track_count: int = 3
    orderlist_ptrs_lo: int = 0
    orderlist_ptrs_hi: int = 0
    sequence_count: int = 0
    sequence_ptrs_lo: int = 0
    sequence_ptrs_hi: int = 0
    orderlist_size: int = 0
    orderlist_start: int = 0
    sequence_size: int = 0
    sequence_start: int = 0

    # Table addresses (for instruments, commands, etc.)
    table_addresses: dict = None

    def __post_init__(self):
        if self.table_addresses is None:
            self.table_addresses = {}


class SF2Writer:
    """Write SID Factory II .sf2 project files"""

    # SF2 file format constants
    SF2_FILE_ID = 0x1337
    SF2_DRIVER_VERSION = 11  # Use driver version 11

    # Header block IDs
    BLOCK_DESCRIPTOR = 1
    BLOCK_DRIVER_COMMON = 2
    BLOCK_DRIVER_TABLES = 3
    BLOCK_INSTRUMENT_DESC = 4
    BLOCK_MUSIC_DATA = 5
    BLOCK_END = 0xFF

    def __init__(self, extracted_data: ExtractedData):
        self.data = extracted_data
        self.output = bytearray()
        self.template_path = None
        self.driver_info = SF2DriverInfo()
        self.load_address = 0

    def write(self, filepath: str):
        """Write the SF2 file"""
        # Try to find and use a template SF2 file
        template_path = self._find_template()

        if template_path and os.path.exists(template_path):
            print(f"Using template: {template_path}")
            with open(template_path, 'rb') as f:
                template_data = f.read()

            # Copy template as base
            self.output = bytearray(template_data)

            # Inject our extracted music data
            self._inject_music_data_into_template()
        else:
            # Fallback to driver-only approach
            driver_path = self._find_driver()

            if driver_path and os.path.exists(driver_path):
                print(f"Using driver: {driver_path}")
                with open(driver_path, 'rb') as f:
                    driver_data = f.read()

                self.output = bytearray(driver_data)
            else:
                # Create minimal structure
                print("Warning: No template or driver found, creating minimal structure")
                self._create_minimal_structure()

            # Inject music data
            self._inject_music_data()

        # Write output file
        with open(filepath, 'wb') as f:
            f.write(self.output)

        print(f"Written SF2 file: {filepath}")
        print(f"File size: {len(self.output)} bytes")

    def _find_template(self) -> Optional[str]:
        """Find an SF2 template file to use as base"""
        # Look for template files in common locations
        search_paths = [
            # Check for existing SF2 files in the project
            'template.sf2',
            # Check SID Factory II installation paths
            r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\music\Driver 11 Test - Arpeggio.sf2',
        ]

        base_dir = os.path.dirname(os.path.abspath(__file__))

        for path in search_paths:
            if os.path.isabs(path):
                if os.path.exists(path):
                    return path
            else:
                full_path = os.path.join(base_dir, path)
                if os.path.exists(full_path):
                    return full_path

        return None

    def _parse_sf2_header(self):
        """Parse the SF2 driver header to find data locations"""
        if len(self.output) < 4:
            return False

        # Get load address (first 2 bytes)
        self.load_address = struct.unpack('<H', self.output[0:2])[0]

        # Check for SF2 file ID at load address
        file_id = struct.unpack('<H', self.output[2:4])[0]
        if file_id != self.SF2_FILE_ID:
            print(f"Warning: File ID {file_id:04X} != expected {self.SF2_FILE_ID:04X}")
            return False

        print(f"Parsing SF2 header (load address: ${self.load_address:04X})")

        # Parse header blocks starting at offset 4
        offset = 4
        while offset < len(self.output) - 2:
            block_id = self.output[offset]
            if block_id == self.BLOCK_END:
                break

            block_size = self.output[offset + 1]
            block_data = self.output[offset + 2:offset + 2 + block_size]

            if block_id == self.BLOCK_DESCRIPTOR:
                self._parse_descriptor_block(block_data)
            elif block_id == self.BLOCK_MUSIC_DATA:
                self._parse_music_data_block(block_data)
            elif block_id == self.BLOCK_DRIVER_TABLES:
                self._parse_tables_block(block_data)

            offset += 2 + block_size

        return True

    def _parse_descriptor_block(self, data: bytes):
        """Parse descriptor block"""
        if len(data) < 3:
            return

        self.driver_info.driver_type = data[0]
        self.driver_info.driver_size = struct.unpack('<H', data[1:3])[0]

        # Find null-terminated driver name
        name_end = 3
        while name_end < len(data) and data[name_end] != 0:
            name_end += 1

        self.driver_info.driver_name = data[3:name_end].decode('latin-1', errors='replace')

        print(f"  Driver: {self.driver_info.driver_name}")

    def _parse_music_data_block(self, data: bytes):
        """Parse music data block to find sequence/orderlist locations"""
        if len(data) < 18:
            return

        idx = 0

        # Track count
        self.driver_info.track_count = data[idx]
        idx += 1

        # Order list pointers
        self.driver_info.orderlist_ptrs_lo = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        self.driver_info.orderlist_ptrs_hi = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2

        # Sequence count
        self.driver_info.sequence_count = data[idx]
        idx += 1

        # Sequence pointers
        self.driver_info.sequence_ptrs_lo = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        self.driver_info.sequence_ptrs_hi = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2

        # Order list size and start
        self.driver_info.orderlist_size = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        self.driver_info.orderlist_start = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2

        # Sequence size and start
        self.driver_info.sequence_size = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        self.driver_info.sequence_start = struct.unpack('<H', data[idx:idx+2])[0]

        print(f"  Tracks: {self.driver_info.track_count}")
        print(f"  Sequences: {self.driver_info.sequence_count}")
        print(f"  Sequence start: ${self.driver_info.sequence_start:04X}")
        print(f"  Orderlist start: ${self.driver_info.orderlist_start:04X}")

    def _parse_tables_block(self, data: bytes):
        """Parse table definitions block to find table addresses"""
        idx = 0

        while idx < len(data):
            if idx >= len(data):
                break

            table_type = data[idx]
            if table_type == 0xFF:
                break

            # Format: type(1), id(1), textfieldsize(1), name(null-terminated),
            # datalayout(1), properties(1), insertdeleteruleid(1),
            # enteractionruleid(1), colorruleid(1),
            # address(2), columns(2), rows(2), visiblerowcount(1)

            if idx + 3 > len(data):
                break

            table_id = data[idx + 1]
            text_field_size = data[idx + 2]

            # Find null-terminated name
            name_start = idx + 3
            name_end = name_start
            while name_end < len(data) and data[name_end] != 0:
                name_end += 1
            name = data[name_start:name_end].decode('latin-1', errors='replace')

            # Parse remaining fields after null terminator
            pos = name_end + 1
            if pos + 12 <= len(data):
                addr = struct.unpack('<H', data[pos+5:pos+7])[0]
                columns = struct.unpack('<H', data[pos+7:pos+9])[0]
                rows = struct.unpack('<H', data[pos+9:pos+11])[0]

                # Store table info
                table_info = {
                    'type': table_type,
                    'id': table_id,
                    'addr': addr,
                    'columns': columns,
                    'rows': rows,
                    'name': name
                }

                # Store by type and name
                if table_type == 0x80:  # Instruments
                    self.driver_info.table_addresses['Instruments'] = table_info
                    print(f"    Instruments table at ${addr:04X} ({columns}×{rows})")
                elif table_type == 0x81:  # Commands
                    self.driver_info.table_addresses['Commands'] = table_info
                    print(f"    Commands table at ${addr:04X} ({columns}×{rows})")
                else:
                    # Generic table - store by name (first letter only for common tables)
                    if name:
                        self.driver_info.table_addresses[name] = table_info
                        # Also store by first letter for common tables
                        first_char = name[0] if name else ''
                        if first_char in ['W', 'P', 'F', 'A', 'T']:
                            # Wave, Pulse, Filter, Arp, Tempo
                            key_map = {'W': 'Wave', 'P': 'Pulse', 'F': 'Filter', 'A': 'Arp', 'T': 'Tempo'}
                            self.driver_info.table_addresses[key_map.get(first_char, first_char)] = table_info

                idx = pos + 12
            else:
                break

    def _addr_to_offset(self, addr: int) -> int:
        """Convert C64 address to file offset"""
        return addr - self.load_address + 2  # +2 for load address header

    def _inject_music_data_into_template(self):
        """Inject extracted music data into a template SF2 file"""
        print("Injecting music data into template...")
        print(f"Template size: {len(self.output)} bytes")

        # Parse the SF2 header to find data locations
        if not self._parse_sf2_header():
            print("Warning: Could not parse SF2 header, using fallback")
            self._print_extraction_summary()
            return

        # Ensure file is large enough for all sequences (128 * 256 bytes = 32KB for sequences)
        # Sequence area starts at sequence_start, needs space for sequence_count slots
        required_size = self._addr_to_offset(self.driver_info.sequence_start) + (self.driver_info.sequence_count * 256)
        if len(self.output) < required_size:
            print(f"  Expanding file from {len(self.output)} to {required_size} bytes")
            self.output.extend(bytearray(required_size - len(self.output)))

        # Inject sequence data
        if self.data.sequences and self.driver_info.sequence_start:
            self._inject_sequences()

        # Inject orderlist data
        if self.data.orderlists and self.driver_info.orderlist_start:
            self._inject_orderlists()

        # Inject instruments
        if self.data.instruments or self.data.raw_sequences:
            self._inject_instruments()

        # Inject wave table
        self._inject_wave_table()

        # Inject HR table (defines waveforms for instruments)
        self._inject_hr_table()

        # Print summary
        self._print_extraction_summary()

    def _inject_sequences(self):
        """Inject sequence data into the SF2 file using packed format"""
        print("\n  Injecting sequences...")

        seq_start = self._addr_to_offset(self.driver_info.sequence_start)
        ptr_lo_offset = self._addr_to_offset(self.driver_info.sequence_ptrs_lo)
        ptr_hi_offset = self._addr_to_offset(self.driver_info.sequence_ptrs_hi)

        if seq_start >= len(self.output) or seq_start < 0:
            print(f"    Warning: Invalid sequence start offset {seq_start}")
            return

        # SF2 uses FIXED 256-byte slots for each sequence
        SEQUENCE_SLOT_SIZE = 256
        sequences_written = 0

        for i, seq in enumerate(self.data.sequences[:127]):  # Max 127 sequences
            if i >= self.driver_info.sequence_count:
                break

            # Each sequence goes in its own 256-byte slot
            current_addr = self.driver_info.sequence_start + (i * SEQUENCE_SLOT_SIZE)

            # Update pointer table
            if ptr_lo_offset + i < len(self.output):
                self.output[ptr_lo_offset + i] = current_addr & 0xFF
            if ptr_hi_offset + i < len(self.output):
                self.output[ptr_hi_offset + i] = (current_addr >> 8) & 0xFF

            # Pack sequence data
            # SF2 format: [CMD] [INSTR] [DURATION] NOTE NOTE NOTE ... 0x7F
            # - 0xC0-0xFF: Command (only when changed)
            # - 0xA0-0xBF: Instrument (only when changed)
            # - 0x80-0x9F: Duration (only when changed, applies to all following notes)
            # - 0x00-0x6F: Note values
            # - 0x7E: Note on (retrigger)
            # - 0x7F: End marker

            seq_offset = self._addr_to_offset(current_addr)

            # Write raw sequence bytes directly - they're already in SF2 format!
            # Laxity format uses same byte ranges as SF2:
            # - 0xA0-0xAF: Instrument
            # - 0x80-0x9F: Duration
            # - 0xC0-0xCF: Command
            # - 0x00-0x6F: Note
            # - 0x7E: Rest/tie
            # - 0x7F: End marker

            if hasattr(self.data, 'raw_sequences') and i < len(self.data.raw_sequences):
                # Use raw sequence bytes directly
                raw_seq = self.data.raw_sequences[i]
                for b in raw_seq:
                    if seq_offset < len(self.output):
                        self.output[seq_offset] = b
                        seq_offset += 1
            else:
                # Fallback: write from SequenceEvent (legacy code)
                for event in seq:
                    if event.instrument != 0x80 and seq_offset < len(self.output):
                        self.output[seq_offset] = event.instrument
                        seq_offset += 1

                    if event.command != 0x00 and seq_offset < len(self.output):
                        self.output[seq_offset] = event.command
                        seq_offset += 1

                    if seq_offset < len(self.output):
                        self.output[seq_offset] = event.note
                        seq_offset += 1

                    if event.note == 0x7F:
                        break

                # Ensure end marker
                if seq_offset > 0 and seq_offset < len(self.output):
                    if self.output[seq_offset - 1] != 0x7F:
                        self.output[seq_offset] = 0x7F
                        seq_offset += 1

            sequences_written += 1

        print(f"    Written {sequences_written} sequences")

    def _inject_orderlists(self):
        """Inject orderlist data into the SF2 file using fixed 256-byte slots"""
        print("  Injecting orderlists...")

        ol_start = self._addr_to_offset(self.driver_info.orderlist_start)
        ptr_lo_offset = self._addr_to_offset(self.driver_info.orderlist_ptrs_lo)
        ptr_hi_offset = self._addr_to_offset(self.driver_info.orderlist_ptrs_hi)

        if ol_start >= len(self.output) or ol_start < 0:
            print(f"    Warning: Invalid orderlist start offset {ol_start}")
            return

        # SF2 uses FIXED 256-byte slots for each orderlist
        ORDERLIST_SLOT_SIZE = 256
        tracks_written = 0

        for track, orderlist in enumerate(self.data.orderlists[:3]):  # Max 3 tracks
            # Each orderlist goes in its own 256-byte slot
            current_addr = self.driver_info.orderlist_start + (track * ORDERLIST_SLOT_SIZE)

            # Update pointer table
            if ptr_lo_offset + track < len(self.output):
                self.output[ptr_lo_offset + track] = current_addr & 0xFF
            if ptr_hi_offset + track < len(self.output):
                self.output[ptr_hi_offset + track] = (current_addr >> 8) & 0xFF

            # Write orderlist in PACKED format
            # SF2 format: Only write transposition when it changes
            # - 0x80-0xBF: Transposition (0xA0 = center/no transpose)
            # - 0x00-0x7F: Sequence index
            # - 0xFE: End marker (no loop)
            # - 0xFF + byte: End with loop to packed index

            ol_offset = self._addr_to_offset(current_addr)
            last_trans = -1

            for transposition, seq_idx in orderlist:
                # Convert transposition to SF2 format (0xA0 = center)
                # transposition 0 -> 0xA0, -31 -> 0x81, +31 -> 0xBF
                sf2_trans = 0xA0 + (transposition if transposition < 32 else transposition - 256)
                sf2_trans = max(0x80, min(0xBF, sf2_trans))

                # Write transposition only if changed
                if sf2_trans != last_trans:
                    if ol_offset < len(self.output):
                        self.output[ol_offset] = sf2_trans
                        ol_offset += 1
                        last_trans = sf2_trans

                # Write sequence index
                if ol_offset < len(self.output):
                    self.output[ol_offset] = seq_idx & 0x7F  # Ensure valid range
                    ol_offset += 1

            # Add loop marker (0xFF + loop index in packed data)
            if ol_offset + 1 < len(self.output):
                self.output[ol_offset] = 0xFF  # Loop marker
                self.output[ol_offset + 1] = 0x00  # Loop to byte 0 (start of packed data)

            tracks_written += 1

        print(f"    Written {tracks_written} orderlists")

    def _inject_instruments(self):
        """Inject instrument data into the SF2 file using extracted Laxity data"""
        print("  Injecting instruments...")

        if 'Instruments' not in self.driver_info.table_addresses:
            print("    Warning: No instrument table found in driver")
            return

        instr_table = self.driver_info.table_addresses['Instruments']
        instr_addr = instr_table['addr']
        columns = instr_table['columns']  # Should be 6 for Driver 11
        rows = instr_table['rows']  # Should be 32

        # SF2 Driver 11 instrument format (6 bytes per instrument, column-major):
        # Byte 0: AD (Attack/Decay)
        # Byte 1: SR (Sustain/Release)
        # Byte 2: Wave table index (0x00 = use table 0, 0x80 = no wave table)
        # Byte 3: Pulse table index
        # Byte 4: Filter table index
        # Byte 5: HR (Hard Restart) table index

        # Extract actual instruments from the Laxity SID data
        laxity_instruments = extract_laxity_instruments(self.data.c64_data, self.data.load_address)

        print(f"    Extracted {len(laxity_instruments)} instruments from Laxity format")

        # Map waveform values to wave table indices
        # Our wave table: 0=saw, 2=pulse, 4=tri, 6=noise
        def waveform_to_wave_index(wave_for_sf2):
            if wave_for_sf2 == 0x21:  # saw
                return 0x00
            elif wave_for_sf2 == 0x41:  # pulse
                return 0x02
            elif wave_for_sf2 == 0x11:  # tri
                return 0x04
            elif wave_for_sf2 == 0x81:  # noise
                return 0x06
            else:
                return 0x00  # default saw

        # Build instrument list from extracted data
        sf2_instruments = []
        for lax_instr in laxity_instruments:
            wave_idx = waveform_to_wave_index(lax_instr['wave_for_sf2'])

            # Format: AD, SR, Wave index, Pulse index, Filter index, HR index
            sf2_instr = [
                lax_instr['ad'],
                lax_instr['sr'],
                wave_idx,
                0x00,  # Pulse index
                0x00,  # Filter index
                0x00   # HR index
            ]
            sf2_instruments.append(sf2_instr)

        # Fill remaining slots with defaults
        while len(sf2_instruments) < 16:
            sf2_instruments.append([0x09, 0xA0, 0x00, 0x00, 0x00, 0x00])

        # Print extracted instruments
        for i, instr in enumerate(sf2_instruments[:len(laxity_instruments)]):
            wave_names = {0x00: 'saw', 0x02: 'pulse', 0x04: 'tri', 0x06: 'noise'}
            wave_name = wave_names.get(instr[2], '?')
            print(f"      {i}: AD={instr[0]:02X} SR={instr[1]:02X} Wave={wave_name}")

        # Write instruments in column-major format
        # Column 0 (all AD bytes), then Column 1 (all SR bytes), etc.
        instruments_written = 0

        for col in range(columns):
            for row in range(rows):
                offset = self._addr_to_offset(instr_addr) + col * rows + row

                if offset >= len(self.output):
                    continue

                if row < len(sf2_instruments) and col < len(sf2_instruments[row]):
                    self.output[offset] = sf2_instruments[row][col]
                else:
                    self.output[offset] = 0

            if col == 0:
                instruments_written = min(len(sf2_instruments), rows)

        print(f"    Written {instruments_written} instruments")

    def _inject_wave_table(self):
        """Inject wave table data"""
        print("  Injecting wave table...")

        if 'Wave' not in self.driver_info.table_addresses:
            print("    Warning: No wave table found")
            return

        wave_table = self.driver_info.table_addresses['Wave']
        wave_addr = wave_table['addr']
        columns = wave_table['columns']  # Should be 2
        rows = wave_table['rows']  # Should be 256

        # Wave table format (2 columns, column-major):
        # Column 0: Waveform (11=tri, 21=saw, 41=pulse, 81=noise) or 7F=end
        # Column 1: Note offset/command (80=no offset, 00=standard, 7F=loop marker)
        #
        # Based on working SF2 analysis:
        # - Entry starts at index, ends with 7F marker
        # - Second byte of 7F row is loop-back index

        # Create wave table entries based on working SF2 patterns
        wave_data = [
            # Entry 0: Saw (similar to working SF2)
            (0x21, 0x80),  # Row 0: Saw wave
            (0x7F, 0x00),  # Row 1: End, no loop
            # Entry 2: Pulse
            (0x41, 0x00),  # Row 2: Pulse wave
            (0x7F, 0x02),  # Row 3: End, loop to row 2
            # Entry 4: Triangle
            (0x11, 0x00),  # Row 4: Triangle wave
            (0x7F, 0x04),  # Row 5: End, loop to row 4
            # Entry 6: Noise
            (0x81, 0x00),  # Row 6: Noise wave
            (0x7F, 0x06),  # Row 7: End, loop to row 6
        ]

        # Write wave table in column-major format
        base_offset = self._addr_to_offset(wave_addr)

        # Write column 0 (waveforms)
        for i, (wave, note) in enumerate(wave_data):
            if i < rows and base_offset + i < len(self.output):
                self.output[base_offset + i] = wave

        # Write column 1 (note offsets)
        col1_offset = base_offset + rows
        for i, (wave, note) in enumerate(wave_data):
            if i < rows and col1_offset + i < len(self.output):
                self.output[col1_offset + i] = note

        print(f"    Written {len(wave_data)//2} wave table entries")

    def _inject_hr_table(self):
        """Inject HR (Hard Restart) table data - this defines the actual waveforms"""
        print("  Injecting HR table...")

        # HR table is named 'HR' in the template
        hr_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'HR' in name:
                hr_table = info
                break

        if not hr_table:
            print("    Warning: No HR table found")
            return

        hr_addr = hr_table['addr']
        columns = hr_table['columns']  # Should be 2
        rows = hr_table['rows']  # Should be 16

        # HR table format (2 columns):
        # Column 0: Frame count / settings
        # Column 1: Waveform or other setting
        # Based on working SF2, HR entry 0 is just "0F 00"

        # Create HR entries - simple version like working SF2
        hr_entries = [
            # HR 0: Default (used by instruments with Wave=0x80)
            (0x0F, 0x00),
        ]

        base_offset = self._addr_to_offset(hr_addr)

        # Write column 0 (frame counts)
        for i, (frames, wave) in enumerate(hr_entries):
            if i < rows and base_offset + i < len(self.output):
                self.output[base_offset + i] = frames

        # Write column 1 (waveforms)
        col1_offset = base_offset + rows
        for i, (frames, wave) in enumerate(hr_entries):
            if i < rows and col1_offset + i < len(self.output):
                self.output[col1_offset + i] = wave

        print(f"    Written {len(hr_entries)} HR table entries")

    def _print_extraction_summary(self):
        """Print summary of extracted data"""
        if self.data.sequences:
            print(f"\n  Extracted {len(self.data.sequences)} sequences:")
            for i, seq in enumerate(self.data.sequences[:5]):
                print(f"    Sequence {i}: {len(seq)} events")
            if len(self.data.sequences) > 5:
                print(f"    ... and {len(self.data.sequences) - 5} more")

        if self.data.instruments:
            print(f"\n  Extracted {len(self.data.instruments)} instruments")

        if self.data.orderlists:
            print(f"\n  Created {len(self.data.orderlists)} orderlists")

    def _find_driver(self) -> Optional[str]:
        """Find SF2 driver file"""
        # Look for driver in common locations
        search_paths = [
            'sf2driver16_01.prg',
            'drivers/sf2driver16_01.prg',
            '../drivers/sf2driver16_01.prg',
        ]

        base_dir = os.path.dirname(os.path.abspath(__file__))

        for path in search_paths:
            full_path = os.path.join(base_dir, path)
            if os.path.exists(full_path):
                return full_path

        return None

    def _create_minimal_structure(self):
        """Create a minimal SF2-like structure"""
        # This creates a basic structure that SF2 can potentially load
        # It won't be playable without proper driver code

        # Allocate space for basic structure
        self.output = bytearray(8192)

        # Set some basic pointers (these would need proper driver)
        # This is a placeholder structure

    def _inject_music_data(self):
        """Inject extracted music data into the SF2 structure"""
        # This would modify the driver data to include:
        # - Order lists
        # - Sequence data
        # - Instrument definitions
        # - Tables (wave, pulse, filter)

        # For now, this is a placeholder that shows the concept
        # Full implementation requires detailed knowledge of the
        # specific driver version's memory layout

        print("Note: Music data injection is a placeholder")
        print("The output file structure may need manual refinement")


def analyze_sid_file(filepath: str):
    """Analyze a SID file and print detailed information"""
    parser = SIDParser(filepath)
    header = parser.parse_header()
    c64_data, load_address = parser.get_c64_data(header)

    print("=" * 60)
    print("SID File Analysis")
    print("=" * 60)
    print(f"File: {filepath}")
    print(f"Format: {header.magic} v{header.version}")
    print(f"Name: {header.name}")
    print(f"Author: {header.author}")
    print(f"Copyright: {header.copyright}")
    print(f"Songs: {header.songs}")
    print(f"Start song: {header.start_song}")
    print(f"Load address: ${load_address:04X}")
    print(f"Init address: ${header.init_address:04X}")
    print(f"Play address: ${header.play_address:04X}")
    print(f"Data size: {len(c64_data)} bytes")
    print(f"End address: ${load_address + len(c64_data) - 1:04X}")
    print("=" * 60)

    # Analyze the data
    analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
    extracted = analyzer.extract_music_data()

    return extracted


def convert_sid_to_sf2(input_path: str, output_path: str):
    """Convert a SID file to SF2 format"""
    print(f"Converting: {input_path}")
    print(f"Output: {output_path}")
    print()

    # Analyze the SID file
    extracted = analyze_sid_file(input_path)

    # Write the SF2 file
    writer = SF2Writer(extracted)
    writer.write(output_path)

    print()
    print("Conversion complete!")
    print()
    print("IMPORTANT NOTES:")
    print("- This is an experimental converter")
    print("- The output file may need manual editing in SID Factory II")
    print("- Complex music data extraction is still in development")
    print("- Consider this a starting point for further refinement")


def main():
    if len(sys.argv) < 2:
        print("SID to SF2 Converter")
        print("Usage: python sid_to_sf2.py <input.sid> [output.sf2]")
        print()
        print("Example:")
        print("  python sid_to_sf2.py Unboxed_Ending_8580.sid output.sf2")
        sys.exit(1)

    input_file = sys.argv[1]

    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        # Generate output filename
        base = os.path.splitext(input_file)[0]
        output_file = base + ".sf2"

    if not os.path.exists(input_file):
        print(f"Error: Input file not found: {input_file}")
        sys.exit(1)

    convert_sid_to_sf2(input_file, output_file)


if __name__ == '__main__':
    main()
