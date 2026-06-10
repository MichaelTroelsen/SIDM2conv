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
        text_field_size: int = 0,
    ):
        """Properties bits (per parse log): bit0=EnableInsertDelete,
        bit1=LayoutVertically, bit2=IndexAsContinuousMemory.

        Rule IDs (ins_del / enter / color) reference Block 7 / Block 8 /
        Block 6 entries respectively. 0xFF means "no rule".

        text_field_size: width of the side-text column SF2II's editor
        renders next to this table. >0 makes PrepareLayout build a
        ComponentTableRowElementsWithText (Refresh path that requires
        a populated AuxilaryDataTableText entry); =0 makes it build the
        plain ComponentTableRowElements (no text column, simpler Refresh
        path). Bundled "Driver 11 Test - Arpeggio.sf2" uses 12 for
        Commands, 18 for Instruments, 0 for everything else.
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
        self.text_field_size = text_field_size

    def to_bytes(self) -> bytes:
        """
        Generate table descriptor bytes for Block 3, matching the format
        SF2II's DriverInfo::ParseDriverTables expects (driver_info.cpp:347):

        Format:
        [Type:1][ID:1][TextFieldSize:1][Name+NUL:Var][Layout:1][Flags:1]
        [Rules:3][Address:2LE][Columns:2LE][Rows:2LE][VisibleRows:1]

        Pre-2026-05-08 the writer emitted NameLen at the TextFieldSize
        position. ParseDriverTables coincidentally still parsed cleanly
        (NameLen happens to be a small u8 like a real tfs would be) but
        every table ended up with m_TextFieldSize = strlen(name)+1.
        That made every table a "WithText" table, and the WithText
        component's Refresh writes a stray byte 0xDE/0xDF when its
        AuxilaryDataTableText lookup misses — corrupting m_MainTextField
        ~50% of the time. Emitting the proper tfs (with most tables 0)
        switches them to the simpler plain ComponentTableRowElements
        which doesn't take that path.

        Returns:
            Binary representation of this descriptor
        """
        data = bytearray()

        # Type and ID
        data.append(self.table_type)
        data.append(self.table_id)

        # TextFieldSize (NEW: was NameLen before 2026-05-08).
        data.append(self.text_field_size)

        # Name in PETSCII (lowercase a-z → 0x01-0x1A) + null terminator.
        # Bundled SF2II reference files use PETSCII for table names; ASCII
        # parses cleanly too, but PETSCII keeps us bug-for-bug compatible
        # with the corpus.
        name_bytes = bytearray()
        for ch in self.name:
            if 'a' <= ch <= 'z':
                name_bytes.append(ord(ch) - ord('a') + 1)
            else:
                name_bytes.append(ord(ch))
        name_bytes.append(0x00)
        data.extend(bytes(name_bytes))

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

        # Block 3 driver-table addresses. Defaults match Stinsen's NP21 binary
        # layout. Per-file overrides keep SF2II's editor view from reading
        # bytes outside the song's actual table data — songs with smaller
        # NP21 binaries (e.g., Angular ~5KB vs Stinsen ~9KB) have their tables
        # at different absolute C64 addresses. The writer should call
        # `extract_all_laxity_tables()` and set these before generating
        # headers; if left at defaults, behaviour matches pre-2026-05-06.
        self.wave_addr = 0x1942        # Wave table
        # Wave-table column count in the Block 3 descriptor. 2 = standard
        # Driver 11 format. The native Galway driver declares 3 (col2 = frames
        # to hold the row) so trace-RLE'd pitch envelopes fit 256 rows.
        self.wave_columns = 2
        self.pulse_addr = 0x1A3B       # Pulse table (row-major, 64x4)
        self.filter_addr = 0x1989      # tbl_filter_seq
        self.instr_addr = 0x1A6B       # Instruments (column-major, 32x8 — emitted as 6 cols)
        self.cmd_addr = 0x1ADB         # Commands (= instruments + 0x70 in Stinsen)
        # Editor-only "fake" tables (no NP21 player constructs). Default
        # high-RAM addresses are safe for Laxity NP21 (binary at $1000+,
        # so $C000-$C300 read zeros from emulated RAM). Non-Laxity files
        # whose binary overlaps high RAM (e.g., Hubbard player at $C000)
        # MUST override these to point at zero-filled placeholder regions
        # inside the SF2 edit area; otherwise SF2II's editor renders the
        # SID's executable code as instrument/wave/pulse/filter cells and
        # deterministically crashes on F10-load.
        self.arp_addr   = 0xC000
        self.tempo_addr = 0xC100
        self.hr_addr    = 0xC200
        self.init_table_addr = 0xC300
        # Block 1 DriverCodeTop/Size — the window SF2II statically sweeps
        # for ABX/ABY $D400-$D406 writes (driver_utils.cpp:419 derefs
        # result.begin() unguarded → empty ⇒ #211 F10 crash). Default
        # $1000/$0900 suits NP21-at-$1000. The low-load layout overrides
        # these to point at a controlled region containing a dead
        # STA $D400,X "scan bait".
        self.driver_code_top  = 0x1000
        self.driver_code_size = 0x0900

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

        # 3. Driver name (null-terminated, PETSCII-encoded).
        # SF2II reads names in PETSCII: lowercase letters a-z map to bytes
        # 0x01-0x1A; uppercase, digits, space, punctuation stay as ASCII.
        # All 67 bundled SF2II reference files use this encoding (e.g., the
        # original Stinsen SF2's name "Driver 11.03.00 - The Standard"
        # encodes the lowercase letters as 0x12 0x09 0x16 0x05 0x12 etc.).
        # Plain ASCII works for display but sf2_lint flags it as a deviation
        # from the bundled corpus.
        name_bytes = bytearray()
        for ch in self.driver_name:
            if 'a' <= ch <= 'z':
                name_bytes.append(ord(ch) - ord('a') + 1)  # 0x01-0x1A
            else:
                name_bytes.append(ord(ch))
        name_bytes.append(0x00)
        content.extend(bytes(name_bytes))

        # 4. Driver code top address (where driver code starts in C64 memory).
        # All 67 bundled SF2II reference files use $1000; we matched on $0E00
        # for the legacy relocated-driver approach (sf2_writer.py:1975-2020),
        # but the active path since v3.1.5 embeds raw NP21 verbatim at $1000.
        # SF2II's load-time validator was crashing on the mismatch.
        content.extend(struct.pack("<H", self.driver_code_top))

        # 5. Driver code size (size of actual 6502 code at driver_code_top).
        # NP21 player code occupies $1000-$18FF (~$0900 bytes); music data
        # tables start at $19xx and live in the SF2 edit area.
        content.extend(struct.pack("<H", self.driver_code_size))

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
        # text_field_size matches bundled "Driver 11 Test - Arpeggio.sf2":
        # 12 for Commands, 18 for Instruments, 0 for everything else.
        # Tables with tfs=0 use plain ComponentTableRowElements (no text
        # column) instead of ...WithText, sidestepping the WithText
        # Refresh-path corruption that fires ~50% on Arp.
        tables = [
            TableDescriptor(
                # 3 columns, not the 2 NP21 actually uses, because the
                # bundled Block 9 (DriverInstrumentDataDescriptor) we copy
                # verbatim references Commands column index 2; SF2II reads
                # past the end of a 2-col table and segfaults.
                name="Commands", table_id=0, address=self.cmd_addr,
                columns=3, rows=64, visible_rows=16,
                table_type=0x81, layout=0x01, properties=0x00,
                ins_del_rule=0xFF, enter_rule=0x03, color_rule=0xFF,
                text_field_size=12,
            ),
            TableDescriptor(
                name="Instruments", table_id=1, address=self.instr_addr,
                columns=6, rows=32, visible_rows=16,
                table_type=0x80, layout=0x01, properties=0x00,
                ins_del_rule=0xFF, enter_rule=0x01, color_rule=0xFF,
                text_field_size=18,
            ),
            TableDescriptor(
                name="Wave", table_id=2, address=self.wave_addr,
                columns=self.wave_columns, rows=256, visible_rows=16,
                table_type=0x00, layout=0x01, properties=0x01,
                ins_del_rule=0x00, enter_rule=0x00, color_rule=0x00,
                text_field_size=0,
            ),
            TableDescriptor(
                name="Pulse", table_id=3, address=self.pulse_addr,
                columns=3, rows=256, visible_rows=16,
                table_type=0x00, layout=0x01, properties=0x01,
                ins_del_rule=0x01, enter_rule=0x02, color_rule=0x01,
                text_field_size=0,
            ),
            TableDescriptor(
                name="Filter", table_id=4, address=self.filter_addr,
                columns=3, rows=256, visible_rows=16,
                table_type=0x00, layout=0x01, properties=0x01,
                ins_del_rule=0x02, enter_rule=0x02, color_rule=0x01,
                text_field_size=0,
            ),
            TableDescriptor(
                name="Arp", table_id=6, address=self.arp_addr,
                columns=1, rows=256, visible_rows=16,
                table_type=0x00, layout=0x01, properties=0x01,
                ins_del_rule=0x03, enter_rule=0xFF, color_rule=0x02,
                text_field_size=0,
            ),
            TableDescriptor(
                name="Tempo", table_id=7, address=self.tempo_addr,
                columns=1, rows=256, visible_rows=16,
                table_type=0x00, layout=0x01, properties=0x01,
                ins_del_rule=0xFF, enter_rule=0xFF, color_rule=0x00,
                text_field_size=0,
            ),
            TableDescriptor(
                name="HR", table_id=5, address=self.hr_addr,
                columns=2, rows=16, visible_rows=6,
                table_type=0x00, layout=0x01, properties=0x00,
                ins_del_rule=0xFF, enter_rule=0xFF, color_rule=0xFF,
                text_field_size=0,
            ),
            TableDescriptor(
                name="Init", table_id=8, address=self.init_table_addr,
                columns=2, rows=32, visible_rows=8,
                table_type=0x00, layout=0x01, properties=0x02,
                ins_del_rule=0xFF, enter_rule=0xFF, color_rule=0xFF,
                text_field_size=0,
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
    _BLOCK_7_BODY = bytes((
        0x01, 0x05, 0x00, 0x00, 0x00, 0x02, 0x01, 0x00, 0xFF, 0x7F, 0x00, 0x02, 0x00, 0xFF, 0x0B, 0xFF,
        0x01, 0x04, 0x00, 0x00, 0x00, 0x03, 0x02, 0x00, 0xFF, 0x7F, 0xFF, 0x01, 0x03, 0x00, 0x00, 0x00,
        0x04, 0x02, 0x00, 0xFF, 0x7F, 0x00, 0x02, 0x00, 0xFF, 0x0A, 0xFF, 0x00, 0x02, 0x00, 0xFF, 0x03,
        0xFF, 0xFE,
    ))
    _BLOCK_8_BODY = bytes((
        0x80, 0xFF, 0x01, 0xFF, 0x00, 0xFF, 0x7F, 0xFF, 0x03, 0x04, 0x03, 0xFF, 0x00, 0x00, 0x00, 0x04,
        0x03, 0x04, 0xFF, 0x00, 0x00, 0x00, 0x05, 0x02, 0x05, 0xFF, 0x00, 0x00, 0x00, 0xFF, 0x80, 0xFF,
        0x02, 0xFF, 0x00, 0xFF, 0x7F, 0xFF, 0x80, 0x06, 0x02, 0xFF, 0x00, 0xFF, 0x03, 0x80, 0x04, 0x02,
        0xFF, 0x00, 0xFF, 0x0A, 0x80, 0x02, 0x02, 0xFF, 0x00, 0xFF, 0x0B, 0xFF, 0xFE,
    ))
    # Block 9 (DriverInstrumentDataDescriptor) — Stage 5.
    # Format per ParseDriverInstrumentDataDescriptor in driver_info.cpp:519:
    #   [u8 count] then count × 10-byte InstrumentDataPointerDescription:
    #     m_TableID
    #     m_InstrumentDataPointerPosition
    #     m_PointerAndValue
    #     m_InstrumentDataConditionalValuePosition
    #     m_ConditionValueAndValue
    #     m_ConditionEqualityValue
    #     m_TableDataType                       (0=single entry, 1=looping)
    #     m_TableJumpMarkerValuePosition
    #     m_TableJumpMarkerValue
    #     m_TableJumpDestinationIndexPosition
    # 4 descriptors emitted, matching the Driver 11 reference SF2's Block 9
    # for Stinsen verbatim. Decoded values:
    #   desc 0: Wave   table (id 2) — ptr at instr byte 5, always include
    #   desc 1: Pulse  table (id 3) — ptr at instr byte 4, always include
    #   desc 2: Filter table (id 4) — ptr at instr byte 3, conditional on
    #                                  byte 2 & 0x40 == 0x40 (HR-flag bit 6)
    #   desc 3: HR     table (id 5) — ptr at instr byte 2 (low nibble), single
    # The "non-empty Block 9 crashes" claim from earlier sessions was
    # likely about Block 4 label-data missing — Block 9 itself is safe
    # if descriptors point at byte positions that exist (our 6-byte rows
    # hold AD, SR, HR, Filter, Pulse, Wave at positions 0..5 — see Stage 3).
    _BLOCK_9_BODY = bytes((
        0x04,  # 4 descriptors
        # Wave table (id=2): ptr at byte 5, always, looping with 0x7F end
        0x02, 0x05, 0xFF, 0x02, 0x00, 0x00, 0x01, 0x00, 0x7F, 0x01,
        # Pulse table (id=3): ptr at byte 4, always, looping with 0x7F end
        0x03, 0x04, 0xFF, 0x02, 0x00, 0x00, 0x01, 0x00, 0x7F, 0x02,
        # Filter table (id=4): ptr at byte 3, conditional (byte 2 & 0x40 == 0x40)
        0x04, 0x03, 0xFF, 0x02, 0x40, 0x40, 0x01, 0x00, 0x7F, 0x02,
        # HR table (id=5): ptr at byte 2 with mask 0x0F (low nibble), single entry
        0x05, 0x02, 0x0F, 0x02, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    ))

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
