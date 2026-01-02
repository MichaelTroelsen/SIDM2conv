#!/usr/bin/env python3
"""
SF2 Packed Format Reader

Reads SF2-packed SID files (which are actually complete SF2 PRG files)
and extracts the original music data by parsing header blocks and table definitions.

Based on SF2_FORMAT_SPEC.md and SF2_SOURCE_ANALYSIS.md
"""

import struct
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class TableDefinition:
    """Represents an SF2 table definition from Block 3."""

    def __init__(self, table_type: int, data_layout: int, address: int,
                 column_count: int, row_count: int):
        self.type = table_type  # 0x00=Generic, 0x80=Instruments, 0x81=Commands
        self.layout = data_layout  # 0=RowMajor, 1=ColumnMajor
        self.address = address
        self.columns = column_count
        self.rows = row_count

    @property
    def is_row_major(self) -> bool:
        return self.layout == 0

    @property
    def is_column_major(self) -> bool:
        return self.layout == 1

    @property
    def total_size(self) -> int:
        return self.columns * self.rows

    def __repr__(self):
        layout_str = "RowMajor" if self.is_row_major else "ColumnMajor"
        return (f"TableDef(type=${self.type:02X}, {layout_str}, "
                f"${self.address:04X}, {self.columns}x{self.rows})")


class SF2PackedReader:
    """Reads SF2-packed SID files and extracts music data."""

    # Header block IDs
    BLOCK_DESCRIPTOR = 1
    BLOCK_DRIVER_COMMON = 2
    BLOCK_DRIVER_TABLES = 3
    BLOCK_INSTRUMENT_DESC = 4
    BLOCK_MUSIC_DATA = 5
    BLOCK_COLOR_RULES = 6
    BLOCK_INSERT_DELETE = 7
    BLOCK_ACTION_RULES = 8
    BLOCK_INSTRUMENT_DATA = 9
    BLOCK_END = 255

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.data = None
        self.load_address = 0
        self.header_blocks = {}
        self.tables = {}  # table_id -> TableDefinition
        self.table_names = {
            0: "Commands",
            1: "Instruments",
            2: "Wave",
            3: "Pulse",
            4: "Filter",
            5: "Unknown5",
            6: "Arpeggio",
            7: "Tempo",
            8: "HR",
            9: "Init"
        }

        # Music data block attributes (populated by parse_header_blocks)
        self.orderlist_pointers = []
        self.sequence_data_pointer = None
        self.music_data_block = None

        self._load_file()

    def _load_file(self):
        """Load SF2-packed file."""
        with open(self.file_path, 'rb') as f:
            self.data = f.read()

        # Check if this is a PSID file or raw PRG
        magic = self.data[0:4]
        if magic == b'PSID' or magic == b'RSID':
            # PSID format - has header
            version = struct.unpack('>H', self.data[4:6])[0]
            load_addr = struct.unpack('>H', self.data[8:10])[0]
            header_size = 0x7C if version == 2 else 0x76

            if load_addr == 0:
                # Load address in data
                self.load_address = struct.unpack('<H', self.data[header_size:header_size+2])[0]
                self.music_data = self.data[header_size+2:]
            else:
                self.load_address = load_addr
                self.music_data = self.data[header_size:]

            print(f"Loaded SF2-packed file (PSID): {self.file_path}")
            print(f"  Total size: {len(self.data):,} bytes")
            print(f"  Header size: {header_size} bytes")
            print(f"  Music data size: {len(self.music_data):,} bytes")
            print(f"  Load address: ${self.load_address:04X}")

            # Replace self.data with just music data for easier addressing
            self.data = self.music_data
        else:
            # Raw PRG format
            self.load_address = struct.unpack('<H', self.data[0:2])[0]
            self.music_data = self.data[2:]
            self.data = self.music_data

            print(f"Loaded SF2-packed file (PRG): {self.file_path}")
            print(f"  Size: {len(self.data):,} bytes")
            print(f"  Load address: ${self.load_address:04X}")

    def get_byte(self, address: int) -> int:
        """Get byte at memory address."""
        offset = address - self.load_address
        if 0 <= offset < len(self.data):
            return self.data[offset]
        return 0

    def get_word(self, address: int) -> int:
        """Get little-endian word at memory address."""
        return self.get_byte(address) | (self.get_byte(address + 1) << 8)

    def get_bytes(self, address: int, count: int) -> bytes:
        """Get bytes starting at memory address."""
        offset = address - self.load_address
        if 0 <= offset < len(self.data):
            return self.data[offset:offset + count]
        return b''

    def parse_header_blocks(self):
        """Parse SF2 header blocks starting at $0800+."""
        # Start after driver code (typically around $0800-$0900)
        # Look for block structure
        search_start = 0x0800
        current = search_start

        print("\nParsing header blocks...")

        while current < 0x1000:  # Search first 4KB
            block_id = self.get_byte(current)

            if block_id == self.BLOCK_END:
                print(f"  Found END marker at ${current:04X}")
                break

            if block_id in [self.BLOCK_DESCRIPTOR, self.BLOCK_DRIVER_COMMON,
                           self.BLOCK_DRIVER_TABLES, self.BLOCK_MUSIC_DATA]:
                block_size = self.get_word(current + 1)
                print(f"  Block {block_id}: ${current:04X}, size={block_size}")

                self.header_blocks[block_id] = {
                    'address': current,
                    'size': block_size,
                    'data': self.get_bytes(current + 3, block_size - 3)
                }

                # Parse specific blocks
                if block_id == self.BLOCK_DRIVER_TABLES:
                    self._parse_driver_tables_block(current)
                elif block_id == self.BLOCK_MUSIC_DATA:
                    self._parse_music_data_block(current)

                current += block_size
            else:
                current += 1

    def _parse_driver_tables_block(self, block_addr: int):
        """Parse Block 3 (Driver Tables) to get table definitions."""
        block_size = self.get_word(block_addr + 1)
        data_start = block_addr + 3

        print("\n  Parsing Driver Tables block...")

        # Read table count
        table_count = self.get_byte(data_start)
        print(f"    Table count: {table_count}")

        offset = data_start + 1
        for i in range(table_count):
            # Each table definition is 6 bytes:
            # byte 0: type (0x00=Generic, 0x80=Instruments, 0x81=Commands)
            # byte 1: layout (0=RowMajor, 1=ColumnMajor)
            # bytes 2-3: address (little-endian word)
            # byte 4: column count
            # byte 5: row count

            table_type = self.get_byte(offset)
            layout = self.get_byte(offset + 1)
            address = self.get_word(offset + 2)
            columns = self.get_byte(offset + 4)
            rows = self.get_byte(offset + 5)

            table_def = TableDefinition(table_type, layout, address, columns, rows)
            self.tables[i] = table_def

            table_name = self.table_names.get(i, f"Table{i}")
            layout_str = "ColMajor" if table_def.is_column_major else "RowMajor"
            print(f"    [{i}] {table_name}: ${address:04X}, "
                  f"{columns}x{rows} ({layout_str})")

            offset += 6

    def _parse_music_data_block(self, block_addr: int):
        """
        Parse Block 5 (Music Data) to extract sequence pointers.

        Block 5 contains pointers to:
        - Orderlists (3 tracks, one per voice)
        - Sequences (variable number of note/instrument/command data)

        Format (typical Driver 11 layout):
          Byte 0-1: Voice 1 orderlist pointer (address, little-endian)
          Byte 2-3: Voice 2 orderlist pointer
          Byte 4-5: Voice 3 orderlist pointer
          Byte 6-7: Sequence data start pointer
          Byte 8+:  Additional metadata (varies by driver)
        """
        block_size = self.get_word(block_addr + 1)
        data_start = block_addr + 3

        print("\n  Parsing Music Data block...")

        # Extract orderlist pointers (3 voices × 2 bytes each)
        self.orderlist_pointers = []
        for voice in range(3):
            offset = data_start + (voice * 2)
            pointer = self.get_word(offset)
            self.orderlist_pointers.append(pointer)
            print(f"    Voice {voice + 1} orderlist: ${pointer:04X}")

        # Extract sequence data pointer (if present)
        sequence_data_offset = data_start + 6
        if sequence_data_offset < block_addr + block_size:
            self.sequence_data_pointer = self.get_word(sequence_data_offset)
            print(f"    Sequence data start: ${self.sequence_data_pointer:04X}")
        else:
            self.sequence_data_pointer = None
            print("    No sequence data pointer found")

        # Store raw block data for further analysis
        self.music_data_block = self.get_bytes(data_start, block_size - 3)

    def extract_table(self, table_id: int) -> Optional[List[List[int]]]:
        """Extract table data using its definition."""
        if table_id not in self.tables:
            return None

        table_def = self.tables[table_id]
        result = []

        if table_def.is_row_major:
            # Row-major: read row by row
            for row in range(table_def.rows):
                row_data = []
                for col in range(table_def.columns):
                    addr = table_def.address + (row * table_def.columns) + col
                    row_data.append(self.get_byte(addr))
                result.append(row_data)
        else:
            # Column-major: read column by column, then transpose
            columns_data = []
            for col in range(table_def.columns):
                col_data = []
                for row in range(table_def.rows):
                    addr = table_def.address + (col * table_def.rows) + row
                    col_data.append(self.get_byte(addr))
                columns_data.append(col_data)

            # Transpose to get rows
            for row in range(table_def.rows):
                row_data = [columns_data[col][row] for col in range(table_def.columns)]
                result.append(row_data)

        return result

    def extract_all_tables(self) -> Dict[str, List[List[int]]]:
        """Extract all tables."""
        result = {}

        print("\nExtracting tables...")
        for table_id, table_def in self.tables.items():
            table_name = self.table_names.get(table_id, f"Table{table_id}")
            table_data = self.extract_table(table_id)

            if table_data:
                # Count non-empty rows
                non_empty = sum(1 for row in table_data if any(b != 0 for b in row))
                print(f"  {table_name}: {len(table_data)} rows "
                      f"({non_empty} non-empty)")
                result[table_name] = table_data

        return result

    def extract_sequences(self) -> Dict[int, bytes]:
        """
        Extract sequence data from Block 5 (Music Data).

        Sequences in SF2 are packed event streams with format:
          Byte 0: Instrument ($80 = no change, $A0-$BF = instrument+$A0)
          Byte 1: Command ($80 = no change, $C0+ = command+$C0)
          Byte 2: Note ($00-$5D = notes, $7E = gate on, $7F = end, $80 = gate off)

        Returns:
            Dictionary mapping sequence index to raw sequence bytes
        """
        sequences = {}

        if not self.orderlist_pointers:
            print("  No orderlist pointers found - Block 5 may not have been parsed")
            return sequences

        print("\nExtracting sequences...")

        # Parse orderlists to find sequence indices referenced
        sequence_indices = set()
        for voice_idx, orderlist_ptr in enumerate(self.orderlist_pointers):
            if orderlist_ptr == 0:
                continue

            # Read orderlist entries (each is 2 bytes: transpose + sequence_idx)
            current = orderlist_ptr
            entry_count = 0
            max_entries = 256  # Safety limit

            while entry_count < max_entries:
                transpose = self.get_byte(current)
                seq_idx = self.get_byte(current + 1)

                # Check for end of orderlist (various termination markers)
                if transpose == 0xFF or seq_idx == 0xFF:
                    break

                # Valid sequence index
                if seq_idx != 0x80:  # 0x80 = empty/no sequence
                    sequence_indices.add(seq_idx)

                current += 2
                entry_count += 1

            print(f"  Voice {voice_idx + 1} orderlist: {entry_count} entries")

        # Now extract the actual sequence data
        # Sequences are typically stored contiguously after orderlists
        # Each sequence is terminated by 0x7F (end marker)
        if self.sequence_data_pointer and sequence_indices:
            print(f"  Found {len(sequence_indices)} unique sequence indices: {sorted(sequence_indices)}")

            # Try to extract sequences by scanning from sequence_data_pointer
            # This is a heuristic approach - sequences stack like Tetris blocks
            current = self.sequence_data_pointer
            seq_idx = 0
            max_sequences = max(sequence_indices) + 1 if sequence_indices else 256

            for seq_idx in range(max_sequences):
                if current >= self.load_address + len(self.data):
                    break  # Reached end of data

                sequence_bytes = []
                max_bytes = 1024  # Safety limit per sequence
                byte_count = 0

                # Read sequence until end marker (0x7F in note column)
                while byte_count < max_bytes:
                    # Read 3 bytes per event (instrument, command, note)
                    instrument = self.get_byte(current)
                    command = self.get_byte(current + 1)
                    note = self.get_byte(current + 2)

                    sequence_bytes.extend([instrument, command, note])
                    current += 3
                    byte_count += 3

                    # Check for end marker (0x7F in note position)
                    if note == 0x7F:
                        break

                    # Additional safety check - if we hit all zeros, likely past data
                    if instrument == 0 and command == 0 and note == 0:
                        break

                # Store sequence if it's referenced in orderlists
                if seq_idx in sequence_indices and len(sequence_bytes) > 0:
                    sequences[seq_idx] = bytes(sequence_bytes)
                    print(f"    Sequence {seq_idx}: {len(sequence_bytes)} bytes")

        print(f"  Extracted {len(sequences)} sequences")
        return sequences

    def compare_with_original(self, original_sf2_path: str):
        """Compare extracted data with original SF2 file."""
        print(f"\n{'='*80}")
        print(f"COMPARING WITH ORIGINAL SF2")
        print(f"{'='*80}")

        # Read original SF2
        with open(original_sf2_path, 'rb') as f:
            orig_data = f.read()

        orig_load = struct.unpack('<H', orig_data[0:2])[0]

        print(f"\nOriginal SF2:      {original_sf2_path}")
        print(f"  Size:            {len(orig_data):,} bytes")
        print(f"  Load address:    ${orig_load:04X}")

        print(f"\nSF2-packed SID:    {self.file_path}")
        print(f"  Size:            {len(self.data):,} bytes")
        print(f"  Load address:    ${self.load_address:04X}")

        # Compare sizes
        size_diff = len(orig_data) - len(self.data)
        size_pct = (size_diff / len(orig_data)) * 100 if len(orig_data) > 0 else 0
        print(f"\nSize difference:   {size_diff:,} bytes ({size_pct:.1f}%)")

        # Byte-by-byte comparison
        matches = 0
        total = min(len(orig_data), len(self.data))
        for i in range(total):
            if orig_data[i] == self.data[i]:
                matches += 1

        match_pct = (matches / total) * 100 if total > 0 else 0
        print(f"Byte match:        {matches}/{total} ({match_pct:.1f}%)")


def main():
    """Example usage."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python sf2_packed_reader.py <sf2_packed_file> [original_sf2]")
        sys.exit(1)

    packed_file = sys.argv[1]
    original_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Read SF2-packed file
    reader = SF2PackedReader(packed_file)

    # Parse header blocks
    reader.parse_header_blocks()

    # Extract tables
    tables = reader.extract_all_tables()

    # Compare with original if provided
    if original_file:
        reader.compare_with_original(original_file)

    print(f"\n{'='*80}")
    print("EXTRACTION COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    main()
