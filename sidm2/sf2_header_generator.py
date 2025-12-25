#!/usr/bin/env python3
"""
SF2 Header Block Generator for Laxity Driver.

Generates complete SF2 header blocks (magic number + blocks 1-5)
for proper SID Factory II editor integration.

Based on LAXITY_TABLE_DESCRIPTOR_DESIGN.md specification.
"""

import struct
from typing import List, Optional


class TableDescriptor:
    """Single table descriptor for SF2 editor."""

    def __init__(
        self,
        name: str,
        table_id: int,
        address: int,
        columns: int,
        rows: int,
        table_type: int = 0x00,
        layout: int = 0x00,
        insert_delete: bool = False,
        color_rule: int = 0x00,
    ):
        """
        Initialize table descriptor.

        Args:
            name: Table name (will be null-terminated)
            table_id: Unique ID for this table (0-15)
            address: Memory address of table data
            columns: Number of columns per row
            rows: Number of rows
            table_type: 0x00=Generic, 0x80=Instruments
            layout: 0x00=Row-major, 0x01=Column-major
            insert_delete: Enable insert/delete operations
            color_rule: Color rule ID (3 for instruments, 0 for others)
        """
        self.name = name
        self.table_id = table_id
        self.address = address
        self.columns = columns
        self.rows = rows
        self.table_type = table_type
        self.layout = layout
        self.insert_delete = insert_delete
        self.color_rule = color_rule

    def to_bytes(self) -> bytes:
        """
        Generate table descriptor bytes for Block 3.

        Format:
        [Type:1][ID:1][NameLen:1][Name:Var][Layout:1][Flags:1]
        [Rules:3][Address:2LE][Columns:2LE][Rows:2LE]

        Returns:
            Binary representation of this descriptor
        """
        data = bytearray()

        # Type and ID
        data.append(self.table_type)
        data.append(self.table_id)

        # Name with null terminator
        name_bytes = self.name.encode("ascii") + b"\x00"
        data.append(len(name_bytes))
        data.extend(name_bytes)

        # Layout
        data.append(self.layout)

        # Flags byte (bit 0 = insert/delete)
        flags = 0x01 if self.insert_delete else 0x00
        data.append(flags)

        # Rule IDs
        data.append(0x00)  # Insert/Delete rule ID
        data.append(0xFF)  # Enter Action rule ID (0xFF = none)
        data.append(self.color_rule)  # Color rule ID

        # Address (little-endian)
        data.extend(struct.pack("<H", self.address))

        # Columns (little-endian)
        data.extend(struct.pack("<H", self.columns))

        # Rows (little-endian)
        data.extend(struct.pack("<H", self.rows))

        return bytes(data)


class SF2HeaderGenerator:
    """Generate complete SF2 header blocks for Laxity driver."""

    # Magic number for SF2 files
    MAGIC_NUMBER = 0x1337

    # Laxity driver memory layout
    DRIVER_INIT = 0x0D7E
    DRIVER_STOP = 0x0D84
    DRIVER_PLAY = 0x0D81

    # Laxity player state addresses (stubs - would need real values)
    PLAYER_ADDRESSES = {
        "sid_channel_offset": 0x16CC,
        "driver_state": 0x16D8,
        "tick_counter": 0x16DB,
        "orderlist_index": 0x16E1,
        "sequence_index": 0x16DE,
        "sequence_in_use": 0x16E4,
        "current_sequence": 0x16F9,
        "current_transpose": 0x16E7,
        "sequence_event_duration": 0x16F0,
        "next_instrument": 0x16F3,
        "next_command": 0x16ED,
        "next_note": 0x16EA,
        "next_note_tied": 0x16CE,
        "tempo_counter": 0x1641,
        "trigger_sync": 0x1702,
        "note_event_trigger_sync_value": 0x00,
        "reserved": 0x0000,
    }

    def __init__(self, driver_size: int = 8192):
        """
        Initialize header generator.

        Args:
            driver_size: Total Laxity driver size in bytes
        """
        self.driver_size = driver_size
        # Use short driver name to match Driver 11 format (max ~10 chars to avoid block overflow)
        self.driver_name = "Laxity"  # Short name to prevent block structure corruption

    def create_descriptor_block(self) -> bytes:
        """
        Create Block 1: Driver Descriptor.

        CRITICAL: Must include ALL 7 fields or editor will reject file!
        ParseDescriptor() expects exact structure (driver_info.cpp:300-316)

        Returns:
            Block bytes with ID and size prefix
        """
        content = bytearray()

        # 1. Driver type (0x00 = standard)
        content.append(0x00)

        # 2. Driver size (little-endian)
        content.extend(struct.pack("<H", self.driver_size))

        # 3. Driver name (null-terminated ASCII)
        name_bytes = self.driver_name.encode("ascii") + b"\x00"
        content.extend(name_bytes)

        # 4. Driver code top address (where driver code starts in C64 memory)
        # For Laxity: Code starts at $0E00 (after wrapper at $0D7E)
        content.extend(struct.pack("<H", 0x0E00))

        # 5. Driver code size (size of actual 6502 code)
        # For Laxity: Player code is ~2KB (relocated from $1000-$19FF to $0E00-$16FF)
        driver_code_size = 0x0900  # $16FF - $0E00 + 1 = 2304 bytes
        content.extend(struct.pack("<H", driver_code_size))

        # 6. Driver version major
        content.append(1)  # Version 1.x

        # 7. Driver version minor
        content.append(0)  # Version x.0

        # Optional 8. Driver version revision (not included for now)

        # Create block: [ID:1][Size:1][Data]
        block = bytearray([0x01, len(content)])
        block.extend(content)

        return bytes(block)

    def create_driver_common_block(self) -> bytes:
        """
        Create Block 2: Driver Common.

        Size is always 40 bytes (fixed format).

        Returns:
            Block bytes with ID and size prefix
        """
        content = bytearray()

        # 18 address fields (2 bytes each, little-endian)
        addresses = [
            self.DRIVER_INIT,  # Init
            self.DRIVER_STOP,  # Stop
            self.DRIVER_PLAY,  # Update/Play
            self.PLAYER_ADDRESSES["sid_channel_offset"],
            self.PLAYER_ADDRESSES["driver_state"],
            self.PLAYER_ADDRESSES["tick_counter"],
            self.PLAYER_ADDRESSES["orderlist_index"],
            self.PLAYER_ADDRESSES["sequence_index"],
            self.PLAYER_ADDRESSES["sequence_in_use"],
            self.PLAYER_ADDRESSES["current_sequence"],
            self.PLAYER_ADDRESSES["current_transpose"],
            self.PLAYER_ADDRESSES["sequence_event_duration"],
            self.PLAYER_ADDRESSES["next_instrument"],
            self.PLAYER_ADDRESSES["next_command"],
            self.PLAYER_ADDRESSES["next_note"],
            self.PLAYER_ADDRESSES["next_note_tied"],
            self.PLAYER_ADDRESSES["tempo_counter"],
            self.PLAYER_ADDRESSES["trigger_sync"],
        ]

        for addr in addresses:
            content.extend(struct.pack("<H", addr))

        # Note event trigger sync value
        content.append(self.PLAYER_ADDRESSES["note_event_trigger_sync_value"])

        # Reserved byte
        content.append(0x00)

        # Reserved word
        content.extend(struct.pack("<H", self.PLAYER_ADDRESSES["reserved"]))

        # Verify size is 40 bytes
        assert len(content) == 40, f"Driver Common block must be 40 bytes, got {len(content)}"

        # Create block: [ID:1][Size:1][Data]
        block = bytearray([0x02, len(content)])
        block.extend(content)

        return bytes(block)

    def create_tables_block(self) -> bytes:
        """
        Create Block 3: Driver Tables.

        Defines 5 Laxity tables with their memory addresses and sizes.

        Returns:
            Block bytes with ID and size prefix
        """
        # Define all 5 tables per specification
        tables = [
            TableDescriptor(
                name="Instruments",
                table_id=0,
                address=0x1A6B,
                columns=8,
                rows=32,
                table_type=0x80,  # Instruments type
                insert_delete=True,
                color_rule=0x03,  # Instruments color
            ),
            TableDescriptor(
                name="Wave",
                table_id=1,
                address=0x1ACB,
                columns=2,
                rows=128,
                table_type=0x00,  # Generic
                color_rule=0x00,
            ),
            TableDescriptor(
                name="Pulse",
                table_id=2,
                address=0x1A3B,
                columns=4,
                rows=64,
                table_type=0x00,  # Generic
                color_rule=0x00,
            ),
            TableDescriptor(
                name="Filter",
                table_id=3,
                address=0x1A1E,
                columns=4,
                rows=32,
                table_type=0x00,  # Generic
                color_rule=0x00,
            ),
            TableDescriptor(
                name="Sequences",
                table_id=4,
                address=0x1900,
                columns=1,
                rows=255,
                table_type=0x00,  # Generic
                layout=0x00,  # Will be marked continuous in implementation
                color_rule=0x00,
            ),
        ]

        # Generate all table descriptors
        content = bytearray()
        for table in tables:
            content.extend(table.to_bytes())

        # Create block: [ID:1][Size:1][Data]
        block = bytearray([0x03, len(content)])
        block.extend(content)

        return bytes(block)

    def create_music_data_block(self) -> bytes:
        """
        Create Block 5: Music Data (placeholder).

        This is a minimal block indicating where music data starts.

        Returns:
            Block bytes with ID and size prefix
        """
        # Minimal music data block
        content = bytes([0x00, 0x19])  # Address $1900 (little-endian)

        block = bytearray([0x05, len(content)])
        block.extend(content)

        return bytes(block)

    def create_optional_blocks(self) -> bytes:
        """
        Create optional blocks 4, 6-9 (minimal/empty).

        For now, these are minimal or empty. Can be enhanced later.

        Returns:
            Combined optional block bytes
        """
        blocks = bytearray()

        # Block 4: Instrument Descriptor (minimal)
        # For now, empty (just ID and size)
        blocks.extend(bytes([0x04, 0x01, 0x00]))

        # Blocks 6-9: Optional color/action rules
        # For now, skip these (can be added later if needed)

        return bytes(blocks)

    def generate_complete_headers(self) -> bytes:
        """
        Generate complete SF2 header block structure.

        Format:
        [Magic:2] [Descriptor:var] [DriverCommon:var] [DriverTables:var]
        [InstrumentDescriptor:var] [MusicData:var] [OptionalBlocks:var] [EndMarker:1]

        CRITICAL: Blocks MUST be in sequential order (1, 2, 3, 4, 5...)
        Editor rejects files with out-of-order blocks!

        Returns:
            Complete header bytes ready to prepend to driver
        """
        headers = bytearray()

        # Magic number (0x1337 in little-endian)
        headers.extend(struct.pack("<H", self.MAGIC_NUMBER))

        # Add all header blocks IN CORRECT ORDER (1, 2, 3, 4, 5...)
        headers.extend(self.create_descriptor_block())          # Block 1
        headers.extend(self.create_driver_common_block())       # Block 2
        headers.extend(self.create_tables_block())              # Block 3
        headers.extend(self.create_optional_blocks())           # Block 4 (InstrumentDescriptor)
        headers.extend(self.create_music_data_block())          # Block 5 (MusicData)

        # End marker
        headers.append(0xFF)

        return bytes(headers)

    def print_header_info(self) -> None:
        """Print diagnostic information about generated headers."""
        headers = self.generate_complete_headers()

        print(f"\nSF2 Header Generation Report")
        print(f"{'=' * 60}")
        print(f"Driver Name: {self.driver_name}")
        print(f"Driver Size: {self.driver_size} bytes")
        print(f"\nHeader Components:")
        print(f"  Magic Number:     2 bytes (0x1337)")
        print(f"  Block 1 (Descriptor): {len(self.create_descriptor_block())} bytes")
        print(f"  Block 2 (Common):     {len(self.create_driver_common_block())} bytes")
        print(f"  Block 3 (Tables):     {len(self.create_tables_block())} bytes")
        print(f"  Block 5 (Music):      {len(self.create_music_data_block())} bytes")
        print(f"  Optional blocks:      {len(self.create_optional_blocks())} bytes")
        print(f"  End marker:           1 byte (0xFF)")
        print(f"\nTotal Header Size: {len(headers)} bytes")
        print(f"\nHeader Hex (first 64 bytes):")

        hex_str = " ".join(f"{b:02X}" for b in headers[:64])
        print(f"  {hex_str}")

        if len(headers) > 64:
            print(f"  ... ({len(headers) - 64} more bytes)")

        print(f"\n{'=' * 60}")


def main():
    """Test header generator."""
    gen = SF2HeaderGenerator(driver_size=8192)
    headers = gen.generate_complete_headers()

    # Print info
    gen.print_header_info()

    # Verify structure
    print(f"\nVerification:")
    print(f"  Magic number: 0x{headers[0]:02X}{headers[1]:02X}")
    assert headers[0:2] == bytes([0x37, 0x13]), "Magic number incorrect!"
    print(f"  [OK] Magic number correct")

    # Find end marker
    end_pos = headers.rfind(0xFF)
    print(f"  End marker at offset: ${end_pos:04X}")
    print(f"  [OK] End marker found")

    # Save to file for inspection
    output_file = "sf2_headers_test.bin"
    with open(output_file, "wb") as f:
        f.write(headers)
    print(f"\n[OK] Headers saved to {output_file}")

    return headers


if __name__ == "__main__":
    headers = main()
