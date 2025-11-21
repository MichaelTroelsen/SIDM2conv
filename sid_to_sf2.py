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
        """Extract instrument definitions"""
        instruments = []

        # Look for instrument table patterns around $19E0-$1A30
        # Based on analysis, instruments appear to be 6 bytes each
        for addr in range(0x19E0, 0x1A30):
            # Try to identify instrument entries
            wave = self.get_byte(self.load_address - 0x1000 + addr + 2)
            if wave in (0x11, 0x21, 0x41, 0x81, 0x10, 0x20, 0x40, 0x80):
                instr = bytes([
                    self.get_byte(self.load_address - 0x1000 + addr + i)
                    for i in range(6)
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
        """Find low/high byte pointer tables"""
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
                    for i in range(16):
                        ptr = values[i] | (hi_values[i] << 8)
                        if data_start <= ptr < data_end:
                            valid_pointers += 1

                    if valid_pointers >= 8:
                        candidates.append((addr, hi_addr, valid_pointers))

        # Sort by number of valid pointers
        candidates.sort(key=lambda x: x[2], reverse=True)

        if candidates:
            tables['pointer_tables'] = candidates[:5]
            print(f"Found {len(candidates)} potential pointer table pairs")

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
        """Extract music data from the SID file"""
        tables = self.find_data_tables()

        # Find sequence data
        raw_sequences = self.find_sequence_data()
        print(f"Found {len(raw_sequences)} potential sequences")

        # Extract instruments
        raw_instruments = self.extract_instruments()
        print(f"Found {len(raw_instruments)} potential instruments")

        # Create extracted data structure
        extracted = ExtractedData(
            header=self.header,
            c64_data=self.data,
            load_address=self.load_address,
            sequences=[],
            orderlists=[],
            instruments=[],
            wavetable=b'',
            pulsetable=b'',
            filtertable=b''
        )

        # Convert raw sequences to SF2 format
        for addr, events in raw_sequences[:50]:  # Limit to 50 sequences
            seq = []
            for cmd, instr, note in events:
                # Convert Laxity format to SF2 format
                # Laxity: cmd, instr, note
                # SF2: instrument, command, note

                # Map instrument byte
                if 0x80 <= instr <= 0x9F:
                    sf2_instr = instr  # Keep as-is for now
                else:
                    sf2_instr = 0x80  # No instrument change

                # Map command byte
                if 0xC0 <= cmd <= 0xCF:
                    sf2_cmd = cmd  # Duration/command
                else:
                    sf2_cmd = 0x80  # No command

                # Note stays the same
                sf2_note = note

                seq.append(SequenceEvent(sf2_instr, sf2_cmd, sf2_note))

            if seq:
                extracted.sequences.append(seq)

        # Add instruments
        for instr_data in raw_instruments[:32]:  # Limit to 32 instruments
            extracted.instruments.append(instr_data)

        # Create basic orderlists (3 voices)
        for voice in range(3):
            orderlist = []
            # Distribute sequences across voices
            start = voice * (len(extracted.sequences) // 3)
            for i in range(min(8, len(extracted.sequences) // 3)):
                seq_idx = start + i
                if seq_idx < len(extracted.sequences):
                    orderlist.append((0, seq_idx))  # No transposition
            if not orderlist:
                orderlist.append((0, 0))
            extracted.orderlists.append(orderlist)

        print(f"Extracted {len(extracted.sequences)} sequences")
        print(f"Extracted {len(extracted.instruments)} instruments")
        print(f"Created {len(extracted.orderlists)} orderlists")

        return extracted

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
        """Parse table definitions block"""
        # Tables block contains multiple table definitions
        # Each has type, ID, name, address, dimensions, etc.
        pass  # Simplified for now

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

        # Inject sequence data
        if self.data.sequences and self.driver_info.sequence_start:
            self._inject_sequences()

        # Inject orderlist data
        if self.data.orderlists and self.driver_info.orderlist_start:
            self._inject_orderlists()

        # Print summary
        self._print_extraction_summary()

    def _inject_sequences(self):
        """Inject sequence data into the SF2 file"""
        print("\n  Injecting sequences...")

        seq_start = self._addr_to_offset(self.driver_info.sequence_start)
        ptr_lo_offset = self._addr_to_offset(self.driver_info.sequence_ptrs_lo)
        ptr_hi_offset = self._addr_to_offset(self.driver_info.sequence_ptrs_hi)

        if seq_start >= len(self.output) or seq_start < 0:
            print(f"    Warning: Invalid sequence start offset {seq_start}")
            return

        # Write sequence data
        current_addr = self.driver_info.sequence_start
        sequences_written = 0

        for i, seq in enumerate(self.data.sequences[:127]):  # Max 127 sequences
            if i >= self.driver_info.sequence_count:
                break

            # Update pointer table
            if ptr_lo_offset + i < len(self.output):
                self.output[ptr_lo_offset + i] = current_addr & 0xFF
            if ptr_hi_offset + i < len(self.output):
                self.output[ptr_hi_offset + i] = (current_addr >> 8) & 0xFF

            # Write sequence events
            seq_offset = self._addr_to_offset(current_addr)
            for event in seq:
                if seq_offset + 2 < len(self.output):
                    self.output[seq_offset] = event.instrument
                    self.output[seq_offset + 1] = event.command
                    self.output[seq_offset + 2] = event.note
                    seq_offset += 3
                    current_addr += 3

            # Add end marker
            if seq_offset < len(self.output):
                self.output[seq_offset] = 0x7F
                current_addr += 1

            sequences_written += 1

        print(f"    Written {sequences_written} sequences")

    def _inject_orderlists(self):
        """Inject orderlist data into the SF2 file"""
        print("  Injecting orderlists...")

        ol_start = self._addr_to_offset(self.driver_info.orderlist_start)
        ptr_lo_offset = self._addr_to_offset(self.driver_info.orderlist_ptrs_lo)
        ptr_hi_offset = self._addr_to_offset(self.driver_info.orderlist_ptrs_hi)

        if ol_start >= len(self.output) or ol_start < 0:
            print(f"    Warning: Invalid orderlist start offset {ol_start}")
            return

        current_addr = self.driver_info.orderlist_start
        tracks_written = 0

        for track, orderlist in enumerate(self.data.orderlists[:3]):  # Max 3 tracks
            # Update pointer table
            if ptr_lo_offset + track < len(self.output):
                self.output[ptr_lo_offset + track] = current_addr & 0xFF
            if ptr_hi_offset + track < len(self.output):
                self.output[ptr_hi_offset + track] = (current_addr >> 8) & 0xFF

            # Write orderlist entries
            ol_offset = self._addr_to_offset(current_addr)
            for transposition, seq_idx in orderlist:
                if ol_offset + 1 < len(self.output):
                    self.output[ol_offset] = transposition
                    self.output[ol_offset + 1] = seq_idx
                    ol_offset += 2
                    current_addr += 2

            # Add loop marker (loop to start)
            if ol_offset + 1 < len(self.output):
                self.output[ol_offset] = 0xFF  # Loop marker
                self.output[ol_offset + 1] = 0x00  # Loop to position 0
                current_addr += 2

            tracks_written += 1

        print(f"    Written {tracks_written} orderlists")

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
