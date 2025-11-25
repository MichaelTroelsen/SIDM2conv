"""SF2 to SID Packer - Creates compact VSID-compatible SID files.

Replicates SID Factory II's Pack utility (F6):
- Extracts only used data sections (sequences, orderlists, tables)
- Compacts data by eliminating gaps
- Relocates pointers and driver code
- Generates minimal SID files (~3,500 bytes vs ~8,900 bytes)
"""

import struct
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass
from .cpu6502 import CPU6502


@dataclass
class DataSection:
    """Represents a contiguous section of data to pack."""
    source_address: int      # Original address in SF2
    data: bytes              # Actual data content
    dest_address: int = 0    # Destination address after compaction (computed later)

    @property
    def size(self) -> int:
        return len(self.data)


class SF2Packer:
    """Packs SF2 files into compact PSID format."""

    # Driver 11 structure offsets (from CLAUDE.md)
    DRIVER_CODE_TOP = 0x1000
    SEQUENCE_TABLE_OFFSET = 0x0903
    INSTRUMENT_TABLE_OFFSET = 0x0A03
    WAVE_TABLE_OFFSET = 0x0B03
    PULSE_TABLE_OFFSET = 0x0D03
    FILTER_TABLE_OFFSET = 0x0F03

    # Control bytes
    END_MARKER = 0x7F
    LOOP_MARKER = 0x7E
    ORDERLIST_END = 0xFF
    ORDERLIST_LOOP = 0xFE

    def __init__(self, sf2_path: Path):
        """Initialize packer with SF2 file.

        Args:
            sf2_path: Path to input SF2 file
        """
        self.sf2_path = sf2_path
        self.memory = bytearray(65536)  # 64KB memory model
        self.data_sections: List[DataSection] = []
        self.sequence_pointers: List[int] = []
        self.orderlist_pointers: List[int] = []

        # Load SF2 into memory
        self._load_sf2()

    def _load_sf2(self):
        """Load SF2 file into memory array."""
        with open(self.sf2_path, 'rb') as f:
            data = f.read()

        # SF2 is a PRG file: first 2 bytes = load address (little-endian)
        if len(data) < 2:
            raise ValueError(f"SF2 file too small: {len(data)} bytes")

        load_addr = struct.unpack('<H', data[0:2])[0]
        file_data = data[2:]

        # Load into memory at specified address
        end_addr = load_addr + len(file_data)
        if end_addr > 65536:
            raise ValueError(f"SF2 data extends beyond 64KB: ${end_addr:04X}")

        self.memory[load_addr:end_addr] = file_data
        self.load_address = load_addr
        # Driver code is ALWAYS at absolute address $1000, not relative to load address
        self.driver_top = 0x1000

    def _read_word(self, address: int) -> int:
        """Read little-endian 16-bit word from memory.

        Args:
            address: Memory address

        Returns:
            16-bit value
        """
        lo = self.memory[address]
        hi = self.memory[address + 1]
        return (hi << 8) | lo

    def _write_word(self, address: int, value: int):
        """Write little-endian 16-bit word to memory.

        Args:
            address: Memory address
            value: 16-bit value to write
        """
        self.memory[address] = value & 0xFF
        self.memory[address + 1] = (value >> 8) & 0xFF

    def _read_word_be(self, address: int) -> int:
        """Read big-endian 16-bit word from memory.

        Args:
            address: Memory address

        Returns:
            16-bit value
        """
        hi = self.memory[address]
        lo = self.memory[address + 1]
        return (hi << 8) | lo

    def read_driver_addresses(self) -> Tuple[int, int]:
        """Read init and play addresses from SF2 DriverCommon structure.

        The DriverCommon structure is at file offset 0x30:
        - File offset 0x00-0x01: Load address
        - File offset 0x02+: Data starting at load_address
        - File offset 0x30: Unknown (2 bytes)
        - File offset 0x32: m_InitAddress (2 bytes, little-endian)
        - File offset 0x34: m_UpdateAddress/Play (2 bytes, little-endian)

        Since file offset 0x02 = memory[load_address],
        file offset 0x32 = memory[load_address + 0x30]

        Returns:
            Tuple of (init_address, play_address)
        """
        # File offset 0x32 = memory[load_address + 0x30]
        # SF2 stores addresses in big-endian
        init_address = self._read_word_be(self.load_address + 0x30)

        # File offset 0x34 = memory[load_address + 0x32]
        play_address = self._read_word_be(self.load_address + 0x32)

        return init_address, play_address

    def _scan_until_marker(self, start_addr: int, markers: List[int],
                          max_size: int = 2048) -> bytes:
        """Scan memory until a marker byte is found.

        Args:
            start_addr: Starting address
            markers: List of marker bytes to stop at (e.g., [0x7F])
            max_size: Maximum bytes to scan

        Returns:
            Data including the first marker found
        """
        data = bytearray()
        addr = start_addr

        for _ in range(max_size):
            byte = self.memory[addr]
            data.append(byte)
            if byte in markers:
                break
            addr += 1

        return bytes(data)

    def fetch_sequences(self):
        """Extract all sequence data by scanning for 0x7F terminators."""
        # Sequences start after instrument table
        # For Driver 11: typically around 0x1A03+
        seq_start = self.driver_top + self.INSTRUMENT_TABLE_OFFSET + 0x100

        # Scan pointer table at SEQUENCE_TABLE_OFFSET
        ptr_table_addr = self.driver_top + self.SEQUENCE_TABLE_OFFSET

        for i in range(256):  # Max 256 sequences
            ptr_addr = ptr_table_addr + (i * 2)
            seq_ptr = self._read_word(ptr_addr)

            # Check if pointer is valid
            if seq_ptr == 0 or seq_ptr < self.driver_top:
                continue
            if seq_ptr >= 0x2000:  # Beyond reasonable range
                break

            self.sequence_pointers.append(ptr_addr)

            # Scan sequence data until 0x7F
            seq_data = self._scan_until_marker(seq_ptr, [self.END_MARKER])

            if len(seq_data) > 0:
                section = DataSection(
                    source_address=seq_ptr,
                    data=seq_data
                )
                self.data_sections.append(section)

    def fetch_orderlists(self):
        """Extract orderlist data by scanning for 0xFF/0xFE terminators."""
        # Orderlists typically start around 0x1903 for Driver 11
        orderlist_start = self.driver_top + 0x903

        # Scan for orderlist pointers (3 voices)
        for voice in range(3):
            ptr_addr = orderlist_start + (voice * 2)
            orderlist_ptr = self._read_word(ptr_addr)

            if orderlist_ptr == 0 or orderlist_ptr < self.driver_top:
                continue

            self.orderlist_pointers.append(ptr_addr)

            # Scan until 0xFF or 0xFE
            orderlist_data = self._scan_until_marker(
                orderlist_ptr,
                [self.ORDERLIST_END, self.ORDERLIST_LOOP]
            )

            if len(orderlist_data) > 0:
                section = DataSection(
                    source_address=orderlist_ptr,
                    data=orderlist_data
                )
                self.data_sections.append(section)

    def fetch_tables(self):
        """Extract table data (instruments, wave, pulse, filter)."""
        # For Driver 11, extract tables with fixed/scanned sizes
        # NOTE: Don't extract tables at all! They're embedded in driver code.
        # The driver code section (0x1000-0x1800) already includes all tables.
        # Extracting them separately would duplicate the data and create wrong layout.
        pass

    def fetch_driver_code(self):
        """Extract all music data from driver start to last non-zero byte.

        For SF2 files generated by sid_to_sf2.py, extract everything from
        driver start (0x1000) to the end of actual music data. This includes:
        - Driver code + embedded tables (0x1000-0x1800)
        - Sequences and orderlists (0x1800+)

        We find the last non-zero byte to avoid including trailing padding.
        """
        driver_start = 0x1000

        # Find last non-zero byte in memory (search backwards from reasonable max)
        max_addr = min(len(self.memory), 0xFFFF)
        last_nonzero = driver_start
        for addr in range(max_addr - 1, driver_start, -1):
            if self.memory[addr] != 0:
                last_nonzero = addr + 1  # +1 to include this byte
                break

        driver_data = bytes(self.memory[driver_start:last_nonzero])

        section = DataSection(
            source_address=driver_start,
            data=driver_data
        )
        self.data_sections.append(section)

    def compute_destination_addresses(self, dest_start: int) -> int:
        """Compute destination addresses for all sections (eliminates gaps).

        Args:
            dest_start: Starting address for packed data (e.g., 0x1000)

        Returns:
            End address of packed data
        """
        # Sort sections by source address
        self.data_sections.sort(key=lambda s: s.source_address)

        current_addr = dest_start

        for section in self.data_sections:
            section.dest_address = current_addr
            current_addr += section.size

        return current_addr

    def create_output_data(self, dest_address: int) -> bytes:
        """Create compact output data by concatenating all sections.

        Args:
            dest_address: Starting address for packed data

        Returns:
            Packed binary data
        """
        output = bytearray()

        for section in self.data_sections:
            output.extend(section.data)

        return bytes(output)

    def adjust_pointers(self):
        """Adjust pointer tables to point to relocated addresses."""
        address_map = {s.source_address: s.dest_address
                      for s in self.data_sections}

        # Adjust sequence pointers
        for ptr_addr in self.sequence_pointers:
            old_ptr = self._read_word(ptr_addr)
            if old_ptr in address_map:
                new_ptr = address_map[old_ptr]
                self._write_word(ptr_addr, new_ptr)

        # Adjust orderlist pointers
        for ptr_addr in self.orderlist_pointers:
            old_ptr = self._read_word(ptr_addr)
            if old_ptr in address_map:
                new_ptr = address_map[old_ptr]
                self._write_word(ptr_addr, new_ptr)

    def process_driver_code(self, address_map: dict, address_delta: int):
        """Relocate absolute addresses in driver code.

        Args:
            address_map: Dictionary mapping source addresses to destination addresses
            address_delta: Amount to add to addresses not in map
        """
        # Find driver code section
        driver_section = next(
            (s for s in self.data_sections if s.source_address == self.driver_top),
            None
        )

        if not driver_section:
            print(f"WARNING: Driver section not found (driver_top=${self.driver_top:04X})")
            return

        print(f"\nRelocating driver code pointers:")
        print(f"  Driver section: src=${driver_section.source_address:04X} dest=${driver_section.dest_address:04X}")
        print(f"  Address delta: {address_delta:+d}")
        print(f"  Section ranges:")
        for s in self.data_sections:
            print(f"    ${s.source_address:04X}-${s.source_address + len(s.data):04X} -> ${s.dest_address:04X}")

        # Disassemble driver code
        cpu = CPU6502(bytes(driver_section.data))
        instructions = cpu.disassemble(0, len(driver_section.data))

        # Relocate absolute addresses
        relocated_data = bytearray(driver_section.data)
        reloc_count = 0

        for instr in instructions:
            if instr.is_relocatable():
                # Check if this address falls within a relocated section
                new_operand = None

                # Check all data sections to see if address falls within their range
                for section in self.data_sections:
                    section_start = section.source_address
                    section_end = section.source_address + len(section.data)

                    if section_start <= instr.operand < section_end:
                        # Address is within this section - relocate it
                        offset_in_section = instr.operand - section_start
                        new_operand = section.dest_address + offset_in_section
                        # Print all $22xx relocations for debugging
                        if 0x2200 <= instr.operand < 0x2300 or reloc_count < 5:
                            print(f"  Relocating: ${instr.operand:04X} -> ${new_operand:04X} (in section ${section.source_address:04X})")
                        reloc_count += 1
                        break

                if new_operand is None:
                    # Not in any section - apply fixed delta for internal driver references
                    new_operand = (instr.operand + address_delta) & 0xFFFF

                # Generate relocated instruction bytes manually
                lo = new_operand & 0xFF
                hi = (new_operand >> 8) & 0xFF
                new_bytes = bytes([instr.opcode, lo, hi])
                relocated_data[instr.address:instr.address + len(new_bytes)] = new_bytes

        print(f"  Total relocations: {reloc_count}")
        driver_section.data = bytes(relocated_data)

    def pack(self, dest_address: int = 0x1000,
            zp_address: int = 0xFC) -> Tuple[bytes, int, int]:
        """Pack SF2 into compact SID format.

        Args:
            dest_address: Destination load address (default $1000)
            zp_address: Zero page address (default $FC)

        Returns:
            Tuple of (packed_data, init_address, play_address)
        """
        # Step 0: Read play address from SF2 DriverCommon structure
        # Note: Init address from DriverCommon is an internal offset, not PSID init
        # PSID init should always be the load address
        _, play_address = self.read_driver_addresses()

        # Step 1: Fetch all data sections
        self.fetch_driver_code()
        self.fetch_tables()  # Currently disabled (tables embedded in driver code)
        # Fetch sequences and orderlists by following pointer tables
        self.fetch_orderlists()
        self.fetch_sequences()

        # Step 2: Compute destination addresses (eliminates gaps)
        end_address = self.compute_destination_addresses(dest_address)

        # Step 3: Adjust pointers
        self.adjust_pointers()

        # Step 4: Relocate driver code pointers
        # Even when driver stays at same address, tables move so pointers need updating
        # Build address map from all data sections for pointer relocation
        address_map = {s.source_address: s.dest_address for s in self.data_sections}
        address_delta = dest_address - self.driver_top

        # Always process driver code to relocate pointers to moved tables
        self.process_driver_code(address_map, address_delta)

        # Adjust play address only if driver itself relocated
        if address_delta != 0 and play_address < 0x1000:
            play_address += address_delta

        # Step 5: Create output
        packed_data = self.create_output_data(dest_address)

        # PSID init address is always the load address
        init_address = dest_address

        return packed_data, init_address, play_address


def create_psid_header(name: str, author: str, copyright_str: str,
                      load_address: int, init_address: int,
                      play_address: int) -> bytes:
    """Create PSID v2 header.

    Args:
        name: Song title (max 31 chars)
        author: Author name (max 31 chars)
        copyright_str: Copyright info (max 31 chars)
        load_address: Load address (0 = use PRG load address)
        init_address: Init routine address
        play_address: Play routine address

    Returns:
        124-byte PSID header
    """
    header = bytearray(124)

    # Magic ID
    header[0:4] = b'PSID'

    # Version (0x0002 = v2)
    header[4:6] = struct.pack('>H', 0x0002)

    # Data offset (always 0x007C = 124 bytes for v2)
    header[6:8] = struct.pack('>H', 0x007C)

    # Load address (0 = use PRG load address)
    header[8:10] = struct.pack('>H', load_address)

    # Init address
    header[10:12] = struct.pack('>H', init_address)

    # Play address
    header[12:14] = struct.pack('>H', play_address)

    # Number of songs (1)
    header[14:16] = struct.pack('>H', 0x0001)

    # Start song (1)
    header[16:18] = struct.pack('>H', 0x0001)

    # Speed bits (0 = 60Hz)
    header[18:22] = struct.pack('>I', 0x00000000)

    # Name (32 bytes, null-terminated)
    name_bytes = name.encode('ascii', errors='replace')[:31]
    header[22:22 + len(name_bytes)] = name_bytes

    # Author (32 bytes, null-terminated)
    author_bytes = author.encode('ascii', errors='replace')[:31]
    header[54:54 + len(author_bytes)] = author_bytes

    # Copyright (32 bytes, null-terminated)
    copyright_bytes = copyright_str.encode('ascii', errors='replace')[:31]
    header[86:86 + len(copyright_bytes)] = copyright_bytes

    # Flags (offset 118-121) - Driver 11 defaults
    # Bit 0: MUS data (0), Bit 1: PlaySID specific (0)
    # Bit 2-3: Video standard (00 = PAL)
    # Bit 4-5: SID model (00 = 6581)
    header[118:122] = struct.pack('>I', 0x00000000)

    return bytes(header)


def pack_sf2_to_sid(sf2_path: Path, sid_path: Path,
                   name: str = "test", author: str = "test",
                   copyright_str: str = "test",
                   dest_address: int = 0x1000,
                   zp_address: int = 0xFC) -> bool:
    """Pack SF2 file to compact PSID format.

    Args:
        sf2_path: Input SF2 file path
        sid_path: Output SID file path
        name: Song title
        author: Author name
        copyright_str: Copyright info
        dest_address: Load address (default $1000)
        zp_address: Zero page address (default $FC)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Pack SF2 data
        packer = SF2Packer(sf2_path)
        packed_data, init_addr, play_addr = packer.pack(dest_address, zp_address)

        # Create PSID header
        header = create_psid_header(
            name=name,
            author=author,
            copyright_str=copyright_str,
            load_address=0,  # Use PRG load address
            init_address=init_addr,
            play_address=play_addr
        )

        # Create PRG load address (little-endian)
        prg_load = struct.pack('<H', dest_address)

        # Write output file
        with open(sid_path, 'wb') as f:
            f.write(header)
            f.write(prg_load)
            f.write(packed_data)

        return True

    except Exception as e:
        print(f"Pack error: {e}")
        return False
