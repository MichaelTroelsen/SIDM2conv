"""Unit tests for sidm2.sf2_aux_bodies.

The two builders encode bodies for SF2II's auxiliary data chain:
  - build_description_data → AuxilaryDataSongs (id=5)
  - build_table_text_data → AuxilaryDataTableText (id=4)

These tests pin the BYTE-OUTPUT format, since the SF2II parser
(`auxilary_data_*.cpp:RestoreFromSaveData`) walks the bytes literally
and any formatting drift would silently break F10-load (or worse,
corrupt SF2II's heap by walking past the buffer end).
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import sf2_aux_bodies


# ---------------------------------------------------------------------------
# build_description_data (aux id=5 Songs body)
# ---------------------------------------------------------------------------

class TestBuildDescriptionData(unittest.TestCase):
    def test_default_main_when_no_name(self):
        out = sf2_aux_bodies.build_description_data()
        # [song_count=1][selected_song=0][len=4]["Main"]
        self.assertEqual(out, b"\x01\x00\x04Main")

    def test_empty_string_defaults_to_main(self):
        out = sf2_aux_bodies.build_description_data("")
        self.assertEqual(out, b"\x01\x00\x04Main")

    def test_whitespace_only_defaults_to_main(self):
        out = sf2_aux_bodies.build_description_data("   ")
        self.assertEqual(out, b"\x01\x00\x04Main")

    def test_normal_name_passes_through(self):
        out = sf2_aux_bodies.build_description_data("Stinsen")
        self.assertEqual(out[:3], b"\x01\x00\x07")
        self.assertEqual(out[3:], b"Stinsen")

    def test_name_truncated_to_16_chars(self):
        # Exactly 17-char name → truncated to 16
        out = sf2_aux_bodies.build_description_data("A" * 20)
        self.assertEqual(out[2], 16, "length byte should be 16")
        self.assertEqual(out[3:], b"A" * 16)

    def test_non_ascii_replaced(self):
        out = sf2_aux_bodies.build_description_data("Café")
        # latin-1 — 'é' = $E9, but 'Café' has 4 chars, encodes to 4 bytes
        self.assertEqual(out[:3], b"\x01\x00\x04")
        self.assertEqual(out[3:], "Café".encode('latin-1'))

    def test_unencodable_char_replaced(self):
        # Chinese chars aren't in latin-1 → '?' replacement
        out = sf2_aux_bodies.build_description_data("中国")
        self.assertEqual(out[:3], b"\x01\x00\x02")
        self.assertEqual(out[3:], b"??")


# ---------------------------------------------------------------------------
# build_table_text_data (aux id=4 TableText body)
# ---------------------------------------------------------------------------

class TestBuildTableTextData(unittest.TestCase):
    def test_empty_input_produces_correct_structure(self):
        out = sf2_aux_bodies.build_table_text_data([], [], instr_table_id=1, cmd_table_id=0)
        # [entry_count=3]
        self.assertEqual(out[0], 3)
        # Each entry:
        #   [u32 LE table_id][u16 LE layer_count=1][u16 LE text_count][per text: u8 len + bytes]
        # Entry 0: Commands (table_id=0), 64 empty texts
        pos = 1
        self.assertEqual(struct.unpack('<I', out[pos:pos + 4])[0], 0)        # table_id=0
        pos += 4
        self.assertEqual(struct.unpack('<H', out[pos:pos + 2])[0], 1)        # 1 layer
        pos += 2
        self.assertEqual(struct.unpack('<H', out[pos:pos + 2])[0], 64)       # 64 texts
        pos += 2
        # 64 empty strings = 64 zero bytes
        self.assertEqual(out[pos:pos + 64], b"\x00" * 64)

    def test_entry_count_is_always_3(self):
        out = sf2_aux_bodies.build_table_text_data(
            instrument_names=["Bass"] * 5,
            command_names=["Slide"] * 3,
        )
        self.assertEqual(out[0], 3, "TableText always has 3 entries")

    def test_instruments_padded_to_32(self):
        """Names are padded with empty strings to fill the 32 instrument slots."""
        out = sf2_aux_bodies.build_table_text_data(
            instrument_names=["Bass", "Lead", "Pad"],
            command_names=[],
            instr_table_id=1, cmd_table_id=0,
        )
        # Parse the 2nd entry (Instruments)
        # Skip entry 0: [table_id u32][layer_count u16][text_count u16=64] + 64 empty strings
        pos = 1 + 4 + 2 + 2 + 64
        # Entry 1: Instruments
        self.assertEqual(struct.unpack('<I', out[pos:pos + 4])[0], 1)        # instr_table_id
        pos += 4
        self.assertEqual(struct.unpack('<H', out[pos:pos + 2])[0], 1)        # 1 layer
        pos += 2
        self.assertEqual(struct.unpack('<H', out[pos:pos + 2])[0], 32)       # 32 slots
        pos += 2
        # First 3 names then 29 empty
        for name in ["Bass", "Lead", "Pad"]:
            self.assertEqual(out[pos], len(name))
            self.assertEqual(out[pos + 1:pos + 1 + len(name)],
                             name.encode('latin-1'))
            pos += 1 + len(name)
        # Remaining 29 = all zero-length
        self.assertEqual(out[pos:pos + 29], b"\x00" * 29)

    def test_extra_table_id_and_rows(self):
        """3rd entry is the "Mystery" table_id=64 with 256 empty rows."""
        out = sf2_aux_bodies.build_table_text_data([], [])
        # Find entry 2:
        # Entry 0: 1 + 4 + 2 + 2 + 64 (64 empty strings)
        # Entry 1: 4 + 2 + 2 + 32 (32 empty strings)
        pos = 1 + (4 + 2 + 2 + 64) + (4 + 2 + 2 + 32)
        self.assertEqual(struct.unpack('<I', out[pos:pos + 4])[0],
                         sf2_aux_bodies.EXTRA_TABLE_ID)
        pos += 4
        self.assertEqual(struct.unpack('<H', out[pos:pos + 2])[0], 1)
        pos += 2
        self.assertEqual(struct.unpack('<H', out[pos:pos + 2])[0], 256)

    def test_excess_names_truncated_to_target_count(self):
        """If caller passes 100 instrument names, only 32 land in the
        output (the rest discarded — text_count MUST stay at 32 or
        SF2II walks past the buffer)."""
        out = sf2_aux_bodies.build_table_text_data(
            instrument_names=["x" + str(i) for i in range(100)],
            command_names=[],
        )
        # Entry 1's text_count should be exactly 32
        pos = 1 + (4 + 2 + 2 + 64)  # past entry 0
        pos += 4 + 2  # past entry 1 table_id + layer_count
        text_count = struct.unpack('<H', out[pos:pos + 2])[0]
        self.assertEqual(text_count, 32)

    def test_custom_table_ids(self):
        out = sf2_aux_bodies.build_table_text_data(
            [], [], instr_table_id=42, cmd_table_id=17)
        # Entry 0 table_id should be 17 (Commands)
        self.assertEqual(struct.unpack('<I', out[1:5])[0], 17)
        # Entry 1 table_id should be 42 (Instruments)
        entry1_offset = 1 + (4 + 2 + 2 + 64)
        self.assertEqual(struct.unpack('<I', out[entry1_offset:entry1_offset + 4])[0], 42)

    def test_name_truncated_to_255_bytes(self):
        """Pascal-string length is 1 byte, so 255 max."""
        long_name = "A" * 300
        out = sf2_aux_bodies.build_table_text_data(
            instrument_names=[long_name],
            command_names=[],
        )
        # Find entry 1's first text length byte
        pos = 1 + (4 + 2 + 2 + 64) + 4 + 2 + 2
        self.assertEqual(out[pos], 255)
        # Followed by 255 bytes of 'A'
        self.assertEqual(out[pos + 1:pos + 256], b"A" * 255)


# ---------------------------------------------------------------------------
# Constants — pin them so any silent change breaks tests
# ---------------------------------------------------------------------------

class TestConstants(unittest.TestCase):
    def test_constants_match_block3_layout(self):
        # These are derived from SF2II's Block 3 — changing them would
        # break the parser walk and corrupt the heap.
        self.assertEqual(sf2_aux_bodies.COMMANDS_ROWS, 64)
        self.assertEqual(sf2_aux_bodies.INSTRUMENTS_ROWS, 32)
        self.assertEqual(sf2_aux_bodies.EXTRA_TABLE_ID, 64)
        self.assertEqual(sf2_aux_bodies.EXTRA_ROWS, 256)


class TestAssembleAuxChain(unittest.TestCase):
    """assemble_aux_chain wraps bodies in TLV frames and orders them
    [3, 2, 1, 4, 5, END] matching bundled SF2II reference files."""

    def test_chain_starts_with_block_3(self):
        out = sf2_aux_bodies.assemble_aux_chain(b"tt", b"dd")
        # First byte = block id 3 (PlayMarkers)
        self.assertEqual(out[0], 3)

    def test_chain_ends_with_5_zero_marker(self):
        out = sf2_aux_bodies.assemble_aux_chain(b"tt", b"dd")
        self.assertEqual(out[-5:], b"\x00\x00\x00\x00\x00")

    def test_chain_includes_all_5_blocks_when_desc_present(self):
        out = sf2_aux_bodies.assemble_aux_chain(b"tt", b"dd")
        # Find all distinct block id bytes at the chain framing positions.
        # Layout per block: [id:1][param:2 LE][length:2 LE][body...]
        block_ids = []
        pos = 0
        while pos < len(out) - 5:   # stop before the 5-zero terminator
            block_ids.append(out[pos])
            length = struct.unpack('<H', out[pos + 3:pos + 5])[0]
            pos += 5 + length
        self.assertEqual(block_ids, [3, 2, 1, 4, 5])

    def test_desc_omitted_when_none(self):
        """If desc_body is None, the id=5 block is NOT in the chain."""
        out = sf2_aux_bodies.assemble_aux_chain(b"tt", None)
        block_ids = []
        pos = 0
        while pos < len(out) - 5:
            block_ids.append(out[pos])
            length = struct.unpack('<H', out[pos + 3:pos + 5])[0]
            pos += 5 + length
        self.assertEqual(block_ids, [3, 2, 1, 4])

    def test_desc_omitted_when_empty_bytes(self):
        """Empty bytes (falsy) also omits the id=5 block."""
        out = sf2_aux_bodies.assemble_aux_chain(b"tt", b"")
        block_ids = []
        pos = 0
        while pos < len(out) - 5:
            block_ids.append(out[pos])
            length = struct.unpack('<H', out[pos + 3:pos + 5])[0]
            pos += 5 + length
        self.assertEqual(block_ids, [3, 2, 1, 4])

    def test_table_text_body_embedded_correctly(self):
        """The id=4 block's body equals the table_text_body passed in."""
        tt = b"\x12\x34\x56"
        out = sf2_aux_bodies.assemble_aux_chain(tt, None)
        # Walk to block id=4
        pos = 0
        while pos < len(out) and out[pos] != 4:
            length = struct.unpack('<H', out[pos + 3:pos + 5])[0]
            pos += 5 + length
        # block 4 body length should match len(tt)
        body_len = struct.unpack('<H', out[pos + 3:pos + 5])[0]
        self.assertEqual(body_len, len(tt))
        self.assertEqual(out[pos + 5:pos + 5 + body_len], tt)

    def test_block_3_default_body_is_2_zero_bytes(self):
        """The hardcoded PlayMarkers body is `01 00`."""
        out = sf2_aux_bodies.assemble_aux_chain(b"", None)
        # Block 3 starts at offset 0. Length is at offset 3-4.
        body_len = struct.unpack('<H', out[3:5])[0]
        self.assertEqual(body_len, 2)
        self.assertEqual(out[5:7], b"\x01\x00")


class TestInjectAuxChainIntoSf2(unittest.TestCase):
    """inject_aux_chain_into_sf2 appends the chain past the buffer and
    writes its C64 address to the $0FFB pointer slot."""

    def _make_buffer_with_load_addr(self, load_addr: int, size: int = 0x500) -> bytearray:
        """Synthetic SF2 buffer: [load:2 LE][zeros padding...]."""
        buf = bytearray(size)
        buf[0] = load_addr & 0xFF
        buf[1] = load_addr >> 8
        return buf

    def test_returns_none_when_buffer_too_small(self):
        result = sf2_aux_bodies.inject_aux_chain_into_sf2(bytearray(1), b"chain")
        self.assertIsNone(result)

    def test_appends_chain_past_buffer_end(self):
        buf = self._make_buffer_with_load_addr(0x0D7E, size=0x500)
        before_len = len(buf)
        chain = b"chain_payload"
        result = sf2_aux_bodies.inject_aux_chain_into_sf2(buf, chain)
        self.assertIsNotNone(result)
        # Buffer extended by chain length
        self.assertEqual(len(buf), before_len + len(chain))
        # Chain bytes match
        self.assertEqual(bytes(buf[-len(chain):]), chain)

    def test_writes_pointer_at_0ffb(self):
        load_addr = 0x0D7E
        buf = self._make_buffer_with_load_addr(load_addr, size=0x500)
        chain = b"abc"
        c64_addr = sf2_aux_bodies.inject_aux_chain_into_sf2(buf, chain)
        # Pointer at C64 $0FFB = file offset $0FFB - load_addr + 2
        ptr_off = 0x0FFB - load_addr + 2
        # The bytes at the pointer slot encode c64_addr in LE
        stored = buf[ptr_off] | (buf[ptr_off + 1] << 8)
        self.assertEqual(stored, c64_addr)
        # Returned c64_addr should be (load_addr + 500 - 2) before the
        # extension — i.e. where the chain was placed.
        self.assertEqual(c64_addr, load_addr + 0x500 - 2)

    def test_returns_none_when_pointer_slot_out_of_range(self):
        """A small buffer that doesn't reach $0FFB → no pointer written."""
        buf = self._make_buffer_with_load_addr(0x0D7E, size=0x200)
        # Buffer ends at $0D7E + $200 = $0F7E, well before $0FFB
        result = sf2_aux_bodies.inject_aux_chain_into_sf2(buf, b"chain")
        # The chain was NOT appended (we should NOT have extended).
        # But buffer end check: $0FFB - $0D7E + 2 = $27F, ptr+2 = $281 > $200.
        # So the function returns None and DOES NOT extend.
        self.assertIsNone(result)
        self.assertEqual(len(buf), 0x200, "buffer NOT extended on failure")


class TestAuxChainConstants(unittest.TestCase):
    def test_aux_pointer_c64_addr(self):
        self.assertEqual(sf2_aux_bodies.AUX_POINTER_C64_ADDR, 0x0FFB)


if __name__ == "__main__":
    unittest.main(verbosity=2)
