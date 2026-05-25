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


if __name__ == "__main__":
    unittest.main(verbosity=2)
