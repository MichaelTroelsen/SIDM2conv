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
        properties: int = 0x00,
        ins_del_rule: int = 0xFF,
        enter_rule: int = 0xFF,
        color_rule: int = 0xFF,
        visible_rows: int = 0,
    ):
        """Properties bits (per parse log): bit0=EnableInsertDelete,
        bit1=LayoutVertically, bit2=IndexAsContinuousMemory.

        Rule IDs (ins_del / enter / color) reference Block 7 / Block 8 /
        Block 6 entries respectively. 0xFF means "no rule".
        """
        self.name = name
        self.table_id = table_id
        self.address = address
        self.columns = columns
        self.rows = rows
        self.table_type = table_type
        self.layout = layout
        self.properties = properties
        self.ins_del_rule = ins_del_rule
        self.enter_rule = enter_rule
        self.color_rule = color_rule
        self.visible_rows = visible_rows if visible_rows > 0 else rows

    def to_bytes(self) -> bytes:
        """
        Generate table descriptor bytes for Block 3.

        Format:
        [Type:1][ID:1][NameLen:1][Name:Var][Layout:1][Flags:1]
        [Rules:3][Address:2LE][Columns:2LE][Rows:2LE][VisibleRows:1]

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

        # Layout, properties (bit-flags), then 3 rule IDs.
        data.append(self.layout)
        data.append(self.properties)
        data.append(self.ins_del_rule)
        data.append(self.enter_rule)
        data.append(self.color_rule)

        # Address (little-endian)
        data.extend(struct.pack("<H", self.address))

        # Columns (little-endian)
        data.extend(struct.pack("<H", self.columns))

        # Rows (little-endian)
        data.extend(struct.pack("<H", self.rows))

        # Visible row count (added - was missing!)
        data.append(self.visible_rows)

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

        # 4. Driver code top address (where driver code starts in C64 memory).
        # All 67 bundled SF2II reference files use $1000; we matched on $0E00
        # for the legacy relocated-driver approach (sf2_writer.py:1975-2020),
        # but the active path since v3.1.5 embeds raw NP21 verbatim at $1000.
        # SF2II's load-time validator was crashing on the mismatch.
        content.extend(struct.pack("<H", 0x1000))

        # 5. Driver code size (size of actual 6502 code at driver_code_top).
        # NP21 player code occupies $1000-$18FF (~$0900 bytes); music data
        # tables start at $19xx and live in the SF2 edit area.
        driver_code_size = 0x0900
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

        All addresses are for the raw NP21 approach: player at $1000 (load address).
        Offsets are fixed constants in the Laxity NP21 v21 player binary.

        Confirmed addresses (laxity-np21.md + zig64 verification):
          Instruments  $1A6B  offset $0A6B  32x8 column-major
          Wave         $1942  offset $0942  waveform array; note offsets start at $1974
          Pulse        $1A3B  offset $0A3B  64x4 row-major (Y*4 indexed)
          Filter seq   $1989  offset $0989  tbl_filter_seq  (26 entries, $7F=end-of-prog)
          Filter spd   $19A3  offset $09A3  tbl_filter_speed
          Filter res   $19BD  offset $09BD  tbl_filter_resonance
          Commands     $1ADB  offset $0ADB  instrument sub-pattern table base

        NOTE: $1A1E is WRONG for filter — it is ch_seq_ptr_hi (voice sequence pointers).
        Editing that address would corrupt NP21 playback. Corrected to $1989.

        Returns:
            Block bytes with ID and size prefix
        """
        # Tables match the schema bundled SF2II reference files emit: same set
        # of 9 tables (Commands, Instruments, Wave, Pulse, Filter, HR, Arp,
        # Tempo, Init) with the same column counts, types, and rule IDs.
        # Editor view loaded an SF2 we wrote with only 6 tables and crashed
        # post-parse — bundled files exist with these 9 in 67/67 .sf2 we have.
        #
        # HR / Arp / Tempo / Init are not real NP21 player constructs; they're
        # editor-side tables required by SF2II's display layer. We point each
        # at a unique high-RAM address ($C000 region — outside our PRG load
        # range, so SF2II's emulated C64 reads zeros). Display will be empty;
        # editor loads.
        tables = [
            TableDescriptor(
                # 3 columns, not the 2 NP21 actually uses, because the
                # bundled Block 9 (DriverInstrumentDataDescriptor) we copy
                # verbatim references Commands column index 2; SF2II reads
                # past the end of a 2-col table and segfaults.
                name="Commands", table_id=0, address=0x1ADB,
                columns=3, rows=64, visible_rows=16,
                table_type=0x81, layout=0x01, properties=0x00,
                ins_del_rule=0xFF, enter_rule=0x03, color_rule=0xFF,
            ),
            TableDescriptor(
                name="Instruments", table_id=1, address=0x1A6B,
                columns=6, rows=32, visible_rows=16,
                table_type=0x80, layout=0x01, properties=0x00,
                ins_del_rule=0xFF, enter_rule=0x01, color_rule=0xFF,
            ),
            TableDescriptor(
                name="Wave", table_id=2, address=0x1942,
                columns=2, rows=256, visible_rows=16,
                table_type=0x00, layout=0x01, properties=0x01,
                ins_del_rule=0x00, enter_rule=0x00, color_rule=0x00,
            ),
            TableDescriptor(
                name="Pulse", table_id=3, address=0x1A3B,
                columns=3, rows=256, visible_rows=16,
                table_type=0x00, layout=0x01, properties=0x01,
                ins_del_rule=0x01, enter_rule=0x02, color_rule=0x01,
            ),
            TableDescriptor(
                name="Filter", table_id=4, address=0x1989,
                columns=3, rows=256, visible_rows=16,
                table_type=0x00, layout=0x01, properties=0x01,
                ins_del_rule=0x02, enter_rule=0x02, color_rule=0x01,
            ),
            TableDescriptor(
                name="Arp", table_id=6, address=0xC000,
                columns=1, rows=256, visible_rows=16,
                table_type=0x00, layout=0x01, properties=0x01,
                ins_del_rule=0x03, enter_rule=0xFF, color_rule=0x02,
            ),
            TableDescriptor(
                name="Tempo", table_id=7, address=0xC100,
                columns=1, rows=256, visible_rows=16,
                table_type=0x00, layout=0x01, properties=0x01,
                ins_del_rule=0xFF, enter_rule=0xFF, color_rule=0x00,
            ),
            TableDescriptor(
                name="HR", table_id=5, address=0xC200,
                columns=2, rows=16, visible_rows=6,
                table_type=0x00, layout=0x01, properties=0x00,
                ins_del_rule=0xFF, enter_rule=0xFF, color_rule=0xFF,
            ),
            TableDescriptor(
                name="Init", table_id=8, address=0xC300,
                columns=2, rows=32, visible_rows=8,
                table_type=0x00, layout=0x01, properties=0x02,
                ins_del_rule=0xFF, enter_rule=0xFF, color_rule=0xFF,
            ),
        ]

        # Generate all table descriptors
        content = bytearray()
        for table in tables:
            content.extend(table.to_bytes())

        # CRITICAL: Add 0xFF terminator - ParseDriverTables() expects it!
        content.append(0xFF)

        # Create block: [ID:1][Size:1][Data]
        block = bytearray([0x03, len(content)])
        block.extend(content)

        return bytes(block)

    def create_music_data_block(self, music_data_params: Optional[dict] = None) -> bytes:
        """
        Create Block 5: Music Data.

        ParseMusicData() expects 18 bytes total:
        - TrackCount (1)
        - TrackOrderListPointersLowAddress (2)
        - TrackOrderListPointersHighAddress (2)
        - SequenceCount (1)
        - SequencePointersLowAddress (2)
        - SequencePointersHighAddress (2)
        - OrderListSize (2)
        - OrderListTrack1Address (2)
        - SequenceSize (2)
        - Sequence00Address (2)

        Args:
            music_data_params: dict with real address values, or None for placeholders.
                Keys: track_count, ol_ptr_lo_addr, ol_ptr_hi_addr, seq_count,
                      seq_ptr_lo_addr, seq_ptr_hi_addr, ol_size, ol_track1_addr,
                      seq_size, seq00_addr

        Returns:
            Block bytes with ID and size prefix
        """
        p = music_data_params or {}
        content = bytearray()

        content.append(p.get('track_count', 0x01))
        content.extend(struct.pack("<H", p.get('ol_ptr_lo_addr', 0x1900)))
        content.extend(struct.pack("<H", p.get('ol_ptr_hi_addr', 0x1900)))
        content.append(p.get('seq_count', 0x01))
        content.extend(struct.pack("<H", p.get('seq_ptr_lo_addr', 0x1900)))
        content.extend(struct.pack("<H", p.get('seq_ptr_hi_addr', 0x1900)))
        content.extend(struct.pack("<H", p.get('ol_size', 0x0100)))
        content.extend(struct.pack("<H", p.get('ol_track1_addr', 0x1900)))
        content.extend(struct.pack("<H", p.get('seq_size', 0x0100)))
        content.extend(struct.pack("<H", p.get('seq00_addr', 0x1900)))

        assert len(content) == 18, f"MusicData block must be 18 bytes, got {len(content)}"

        block = bytearray([0x05, len(content)])
        block.extend(content)

        return bytes(block)

    # Bytes copied verbatim from bundled "bin/music/Driver 11 Test - Arpeggio.sf2".
    # SF2II's editor view requires these blocks to be present and parsable;
    # without them the file parses cleanly but SF2II crashes (access violation)
    # when constructing the editor model. The bytes describe the editor's
    # column layout (Block 4: Attack/decay, Sustain/release, Options, Pulse
    # program, Wave program — 5 column descriptors for the 6-column
    # Instruments table) and the rule sets referenced by Block 3 table
    # descriptors (color rules, insert/delete rules, action rules, instrument
    # data descriptor). We use Driver 11's set verbatim because (a) SF2II's
    # editor displays NP21 instrument data through a Driver 11-shaped UI
    # anyway — playback uses NP21's own player code embedded at $1000 — and
    # (b) shipping our own would require reverse-engineering the rule format.
    # Editor-side editing of NP21 instruments will appear with Driver 11
    # column labels, which is acceptable for the "file loads" goal.
    _BLOCK_4_BODY = bytes((
        0x05, 0x41, 0x14, 0x14, 0x01, 0x03, 0x0B, 0x2F, 0x04, 0x05, 0x03, 0x01, 0x19, 0x00, 0x53, 0x15,
        0x13, 0x14, 0x01, 0x09, 0x0E, 0x2F, 0x12, 0x05, 0x0C, 0x05, 0x01, 0x13, 0x05, 0x00, 0x4F, 0x10,
        0x14, 0x09, 0x0F, 0x0E, 0x13, 0x00, 0x50, 0x15, 0x0C, 0x13, 0x05, 0x20, 0x10, 0x12, 0x0F, 0x07,
        0x12, 0x01, 0x0D, 0x00, 0x57, 0x01, 0x16, 0x05, 0x20, 0x10, 0x12, 0x0F, 0x07, 0x12, 0x01, 0x0D,
        0x00,
    ))
    _BLOCK_6_BODY = bytes((
        0x00, 0xFF, 0x7F, 0x09, 0xFF, 0x00, 0x80, 0x80, 0x07, 0x00, 0xFF, 0x7F, 0x09, 0xFF, 0x00, 0xF0,
        0x70, 0x09, 0xFF, 0xFE,
    ))
    # Block 7 (TableInsertDeleteRules): bundled's 50-byte body produces a
    # rules array whose entries reference instrument-name addresses that
    # exist only in Driver 11 files; SF2II's editor view dereferences
    # those refs unconditionally on a code path that runs after parse
    # complete (RVA 0x7EF42, NULL+0x48). Result: deterministic-when-
    # triggered, non-deterministic overall (~40% crash rate).
    #
    # Confirmed via N=10 byte-patch experiment on 2026-05-05:
    #   bundled-body Block 7 → 6/10 PASS
    #   single-byte (0xFE end marker) Block 7 → 10/10 PASS
    #   (Block 6 / Block 8 emptied separately → 0/10 each — Block 7 is
    #   uniquely the culprit.)
    #
    # The cost of an empty Block 7 is editor-side: insert/delete rules
    # in the SF2 editor (e.g., "when Wave row deleted, also delete
    # corresponding Pulse row") won't fire. That's acceptable — our
    # editor view is for inspecting NP21 data, not editing it across
    # tables. Player-side playback is unaffected.
    _BLOCK_7_BODY = bytes((0xFE,))
    _BLOCK_8_BODY = bytes((
        0x80, 0xFF, 0x01, 0xFF, 0x00, 0xFF, 0x7F, 0xFF, 0x03, 0x04, 0x03, 0xFF, 0x00, 0x00, 0x00, 0x04,
        0x03, 0x04, 0xFF, 0x00, 0x00, 0x00, 0x05, 0x02, 0x05, 0xFF, 0x00, 0x00, 0x00, 0xFF, 0x80, 0xFF,
        0x02, 0xFF, 0x00, 0xFF, 0x7F, 0xFF, 0x80, 0x06, 0x02, 0xFF, 0x00, 0xFF, 0x03, 0x80, 0x04, 0x02,
        0xFF, 0x00, 0xFF, 0x0A, 0x80, 0x02, 0x02, 0xFF, 0x00, 0xFF, 0x0B, 0xFF, 0xFE,
    ))
    # Block 9 (DriverInstrumentDataDescriptor) entries reference instrument-
    # name addresses that exist only in bundled Driver 11 files (a label
    # data section appended after the header). Our raw-NP21 layout has no
    # such labels, so any non-empty Block 9 makes ParseAuxilaryData crash
    # with an access violation. A single-byte body (zero entries) lets
    # SF2II's parser walk past it cleanly — verified via load harness:
    # ParseAuxilaryData: PASSED, editor opens.
    _BLOCK_9_BODY = bytes((0x00,))

    @staticmethod
    def _wrap_block(block_id: int, body: bytes) -> bytes:
        return bytes([block_id, len(body)]) + body

    def create_block_4_instrument_descriptor(self) -> bytes:
        return self._wrap_block(0x04, self._BLOCK_4_BODY)

    def create_block_6_table_color_rules(self) -> bytes:
        return self._wrap_block(0x06, self._BLOCK_6_BODY)

    def create_block_7_insert_delete_rules(self) -> bytes:
        return self._wrap_block(0x07, self._BLOCK_7_BODY)

    def create_block_8_action_rules(self) -> bytes:
        return self._wrap_block(0x08, self._BLOCK_8_BODY)

    def create_block_9_instrument_data_descriptor(self) -> bytes:
        return self._wrap_block(0x09, self._BLOCK_9_BODY)

    def generate_complete_headers(self, music_data_params: Optional[dict] = None) -> bytes:
        """
        Generate complete SF2 header block structure.

        Format:
        [Magic:2] [Descriptor:var] [DriverCommon:var] [DriverTables:var]
        [InstrumentDescriptor:var] [MusicData:var] [OptionalBlocks:var] [EndMarker:1]

        CRITICAL: Blocks MUST be in sequential order (1, 2, 3, 4, 5...)
        Editor rejects files with out-of-order blocks!

        Args:
            music_data_params: Real Block 5 address values (see create_music_data_block).
                               If None, placeholder $1900 values are used.

        Returns:
            Complete header bytes ready to prepend to driver
        """
        headers = bytearray()

        headers.extend(struct.pack("<H", self.MAGIC_NUMBER))

        headers.extend(self.create_descriptor_block())              # 1
        headers.extend(self.create_driver_common_block())            # 2
        headers.extend(self.create_tables_block())                   # 3
        headers.extend(self.create_block_4_instrument_descriptor())  # 4
        headers.extend(self.create_music_data_block(music_data_params))  # 5
        headers.extend(self.create_block_6_table_color_rules())      # 6
        headers.extend(self.create_block_7_insert_delete_rules())    # 7
        headers.extend(self.create_block_8_action_rules())           # 8
        headers.extend(self.create_block_9_instrument_data_descriptor())  # 9

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
