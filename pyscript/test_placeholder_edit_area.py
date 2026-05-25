"""Unit tests for sidm2.placeholder_edit_area.

build_placeholder_edit_area is shared by `low_load_layout.py` and
`sf2_writer.py:_inject_player_raw_minimal`. Both paths use it to
produce the empty-editor-view edit area when SIDM2 can't populate
real F1-F5 data.

Tests pin:
  - Total layout size and byte breakdown matches expected SF2II shape
  - Music data params point at the correct C64 addresses inside the edit area
  - Table address fields on the SF2HeaderGenerator are populated correctly
  - The orderlist bytes are `[0xA0, 0x00, 0xFE, 0xFF...]` per voice
  - Sequence bytes are all 0x7F (end markers)
  - F1-F5 + Arp/Tempo/HR/Init tables are all zero
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import placeholder_edit_area
from sidm2.sf2_header_generator import SF2HeaderGenerator


class TestBuildPlaceholderEditArea(unittest.TestCase):
    def setUp(self):
        self.gen = SF2HeaderGenerator(driver_size=0x100)
        self.edit_base = 0x2000
        self.edit_bytes, self.music_params = (
            placeholder_edit_area.build_placeholder_edit_area(
                self.edit_base, self.gen))

    def test_total_size_matches_expected(self):
        """Sum of all section sizes."""
        OL_SIZE = placeholder_edit_area.OL_SIZE   # 0x100
        SEQ_SIZE = placeholder_edit_area.SEQ_SIZE  # 0x100
        SEQ_PTR_SIZE = placeholder_edit_area.SEQ_PTR_SIZE  # 0x80

        expected = (
            6                              # OL ptr lo/hi (3 voices × 2)
            + 2 * SEQ_PTR_SIZE             # Seq ptr lo + hi tables
            + 3 * OL_SIZE                  # 3 orderlists
            + SEQ_SIZE                     # 1 sequence
            + 32 * 6                       # Instruments
            + 32 * 2                       # Wave
            + 16 * 3                       # Pulse
            + 16 * 3                       # Filter
            + 256                          # Arp
            + 256                          # Tempo
            + 16 * 2                       # HR
            + 32 * 2                       # Init
        )
        self.assertEqual(len(self.edit_bytes), expected,
                         f"expected total {expected}, got {len(self.edit_bytes)}")

    def test_ol_ptr_lo_table_at_offset_0(self):
        """First 3 bytes are the OL ptr lo for voices 0/1/2."""
        # 3 voices, OL_SIZE=0x100, ol_track1 = edit_base + 6 + 256*2 = edit_base + 0x106
        ol_track1 = self.edit_base + 6 + 2 * placeholder_edit_area.SEQ_PTR_SIZE
        for v in range(3):
            expected_lo = (ol_track1 + v * placeholder_edit_area.OL_SIZE) & 0xFF
            self.assertEqual(self.edit_bytes[v], expected_lo)

    def test_orderlists_start_with_a0_00_fe(self):
        """Each of 3 orderlists begins with `[0xA0, 0x00, 0xFE]` then 0xFF padding."""
        # OL ptr tables: 6 bytes
        # Seq ptr tables: 2 × 0x80 = 0x100 bytes
        # ol_track1 offset in edit_bytes = 6 + 0x100 = 0x106
        ol_offset = 6 + 2 * placeholder_edit_area.SEQ_PTR_SIZE
        OL_SIZE = placeholder_edit_area.OL_SIZE
        for v in range(3):
            base = ol_offset + v * OL_SIZE
            self.assertEqual(self.edit_bytes[base], 0xA0,
                             f"voice {v} orderlist byte 0: expected 0xA0")
            self.assertEqual(self.edit_bytes[base + 1], 0x00,
                             f"voice {v} orderlist byte 1: expected 0x00")
            self.assertEqual(self.edit_bytes[base + 2], 0xFE,
                             f"voice {v} orderlist byte 2: expected 0xFE")
            # The rest (253 bytes) should be 0xFF padding
            self.assertEqual(
                self.edit_bytes[base + 3:base + OL_SIZE],
                bytes([0xFF] * (OL_SIZE - 3)),
                f"voice {v} orderlist tail should be 0xFF padding",
            )

    def test_sequence_all_0x7f(self):
        """The 1 sequence is all 0x7F end markers."""
        # Sequences come after: 6 + 0x100 + 3 × 0x100 = 0x406
        seq_offset = (6
                       + 2 * placeholder_edit_area.SEQ_PTR_SIZE
                       + 3 * placeholder_edit_area.OL_SIZE)
        seq_bytes = self.edit_bytes[
            seq_offset:seq_offset + placeholder_edit_area.SEQ_SIZE]
        self.assertEqual(seq_bytes,
                          bytes([0x7F] * placeholder_edit_area.SEQ_SIZE))

    def test_f_tables_all_zero(self):
        """Instruments + Wave + Pulse + Filter + Arp + Tempo + HR + Init
        are all zero bytes."""
        tables_offset = (6
                          + 2 * placeholder_edit_area.SEQ_PTR_SIZE
                          + 3 * placeholder_edit_area.OL_SIZE
                          + placeholder_edit_area.SEQ_SIZE)
        # All bytes from this offset to the end are zero
        tail = self.edit_bytes[tables_offset:]
        self.assertEqual(tail, bytes(len(tail)),
                         "all F1-F5 + editor tables should be zero")

    def test_gen_addresses_populated(self):
        """gen.instr_addr / wave_addr / etc. all set inside the edit area."""
        self.assertGreater(self.gen.instr_addr, self.edit_base)
        self.assertGreater(self.gen.wave_addr, self.gen.instr_addr)
        self.assertGreater(self.gen.pulse_addr, self.gen.wave_addr)
        self.assertGreater(self.gen.filter_addr, self.gen.pulse_addr)
        self.assertGreater(self.gen.arp_addr, self.gen.filter_addr)
        self.assertGreater(self.gen.tempo_addr, self.gen.arp_addr)
        self.assertGreater(self.gen.hr_addr, self.gen.tempo_addr)
        self.assertGreater(self.gen.init_table_addr, self.gen.hr_addr)
        # Last table end should fit within edit_base + len(edit_bytes)
        self.assertLessEqual(self.gen.init_table_addr + 32 * 2,
                              self.edit_base + len(self.edit_bytes))

    def test_cmd_addr_offset_from_instr(self):
        """cmd_addr = instr_addr + 0x70 (NP21-style bias)."""
        self.assertEqual(self.gen.cmd_addr, self.gen.instr_addr + 0x70)

    def test_music_data_params_shape(self):
        """The dict has all required keys for SF2HeaderGenerator."""
        required_keys = {
            'track_count', 'ol_ptr_lo_addr', 'ol_ptr_hi_addr',
            'seq_count', 'seq_ptr_lo_addr', 'seq_ptr_hi_addr',
            'ol_size', 'ol_track1_addr', 'seq_size', 'seq00_addr',
        }
        self.assertEqual(set(self.music_params.keys()), required_keys)
        self.assertEqual(self.music_params['track_count'], 3)
        self.assertEqual(self.music_params['seq_count'], 1)
        self.assertEqual(self.music_params['ol_size'],
                          placeholder_edit_area.OL_SIZE)
        self.assertEqual(self.music_params['seq_size'],
                          placeholder_edit_area.SEQ_SIZE)


class TestDifferentBaseAddresses(unittest.TestCase):
    """The function should work for different sf2_data_base values."""

    def test_base_at_2000(self):
        gen = SF2HeaderGenerator(driver_size=0x100)
        edit, params = placeholder_edit_area.build_placeholder_edit_area(0x2000, gen)
        self.assertEqual(params['ol_ptr_lo_addr'], 0x2000)
        self.assertEqual(params['ol_ptr_hi_addr'], 0x2003)
        self.assertEqual(params['seq_ptr_lo_addr'], 0x2006)

    def test_base_at_e000(self):
        gen = SF2HeaderGenerator(driver_size=0x100)
        edit, params = placeholder_edit_area.build_placeholder_edit_area(0xE000, gen)
        self.assertEqual(params['ol_ptr_lo_addr'], 0xE000)
        self.assertEqual(params['ol_track1_addr'],
                          0xE000 + 6 + 2 * placeholder_edit_area.SEQ_PTR_SIZE)


class TestConstants(unittest.TestCase):
    def test_constants_match_sf2ii_layout(self):
        self.assertEqual(placeholder_edit_area.OL_SIZE, 0x100)
        self.assertEqual(placeholder_edit_area.SEQ_SIZE, 0x100)
        self.assertEqual(placeholder_edit_area.SEQ_PTR_SIZE, 0x80)


if __name__ == "__main__":
    unittest.main(verbosity=2)
