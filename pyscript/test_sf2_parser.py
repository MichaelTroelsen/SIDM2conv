"""Unit tests for sidm2.sf2_parser.

These functions populate an SF2DriverInfo from an SF2 file's block
chain. Tests use synthetic byte buffers to exercise:
  - parse_sf2_blocks (top-level walk; handles magic, terminator,
    dispatch)
  - parse_descriptor_block (Block 1: driver type + size + name)
  - parse_music_data_block (Block 5: track/sequence layout)
  - parse_tables_block (Block 3: Instruments/Commands/named tables)

Edge cases: truncated buffers, missing terminator, invalid magic,
all-zero data, malformed table descriptors.
"""
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import sf2_parser
from sidm2.models import SF2DriverInfo


# ---------------------------------------------------------------------------
# parse_sf2_blocks — top-level walk
# ---------------------------------------------------------------------------

class TestParseSf2Blocks(unittest.TestCase):
    def test_returns_none_on_tiny_buffer(self):
        di = SF2DriverInfo()
        result = sf2_parser.parse_sf2_blocks(b"\x00", di)
        self.assertIsNone(result)

    def test_returns_none_on_invalid_magic(self):
        # load=0x0D7E, magic=0xABCD (wrong)
        buf = b"\x7E\x0D\xCD\xAB" + b"\xFF"  # immediate end marker
        di = SF2DriverInfo()
        result = sf2_parser.parse_sf2_blocks(buf, di)
        self.assertIsNone(result)

    def test_reads_load_address_correctly(self):
        # Construct buffer: load=$0D7E, magic=$1337, end marker
        buf = b"\x7E\x0D\x37\x13" + b"\xFF"
        di = SF2DriverInfo()
        result = sf2_parser.parse_sf2_blocks(buf, di)
        self.assertEqual(result, 0x0D7E)

    def test_dispatches_to_descriptor_block(self):
        # Build: [load][magic][Block 1: id=1, size=4, body=[type=0,size_lo=0,size_hi=$10,'X','\0']][END]
        # Block 1 body: type(1) + size(2 LE) + name+NUL
        b1_body = bytes([0x00, 0x00, 0x10, ord('X'), 0x00])
        buf = (b"\x7E\x0D\x37\x13"
               + bytes([1, len(b1_body)]) + b1_body
               + b"\xFF")
        di = SF2DriverInfo()
        load = sf2_parser.parse_sf2_blocks(buf, di)
        self.assertEqual(load, 0x0D7E)
        self.assertEqual(di.driver_type, 0)
        self.assertEqual(di.driver_size, 0x1000)
        self.assertEqual(di.driver_name, "X")

    def test_terminator_stops_walk(self):
        """Bytes after the 0xFF terminator must NOT be parsed."""
        # Block 1 then terminator then a fake Block 5 — parser should stop at 0xFF
        b1_body = bytes([0x00, 0x00, 0x10, ord('A'), 0x00])
        # A fake "Block 5" after the terminator; if parser walks past
        # 0xFF, it'd populate sequence fields
        ghost_block5 = bytes([5, 18]) + b"\x99" * 18
        buf = (b"\x7E\x0D\x37\x13"
               + bytes([1, len(b1_body)]) + b1_body
               + b"\xFF"
               + ghost_block5)
        di = SF2DriverInfo()
        sf2_parser.parse_sf2_blocks(buf, di)
        self.assertEqual(di.driver_name, "A")
        # Ghost block should not have been parsed
        self.assertEqual(di.track_count, 3)         # default from __post_init__
        self.assertEqual(di.sequence_count, 0)      # default


# ---------------------------------------------------------------------------
# parse_descriptor_block
# ---------------------------------------------------------------------------

class TestParseDescriptorBlock(unittest.TestCase):
    def test_too_short_silently_ignored(self):
        di = SF2DriverInfo()
        sf2_parser.parse_descriptor_block(b"\x00\x00", di)
        # No change from defaults
        self.assertEqual(di.driver_type, 0)
        self.assertEqual(di.driver_name, "")

    def test_extracts_type_size_name(self):
        di = SF2DriverInfo()
        # type=0x42, size=$1234, name="Laxity\0"
        data = bytes([0x42, 0x34, 0x12]) + b"Laxity\x00"
        sf2_parser.parse_descriptor_block(data, di)
        self.assertEqual(di.driver_type, 0x42)
        self.assertEqual(di.driver_size, 0x1234)
        self.assertEqual(di.driver_name, "Laxity")

    def test_name_without_null_terminator(self):
        di = SF2DriverInfo()
        # Name extends to end of buffer (no NUL found)
        data = bytes([0x00, 0x00, 0x10]) + b"NoNull"
        sf2_parser.parse_descriptor_block(data, di)
        self.assertEqual(di.driver_name, "NoNull")


# ---------------------------------------------------------------------------
# parse_music_data_block
# ---------------------------------------------------------------------------

class TestParseMusicDataBlock(unittest.TestCase):
    def test_undersized_body_ignored(self):
        di = SF2DriverInfo()
        sf2_parser.parse_music_data_block(b"\x00" * 10, di)   # < 18 bytes
        self.assertEqual(di.track_count, 3, "defaults preserved")

    def test_all_fields_populated(self):
        di = SF2DriverInfo()
        body = bytes([7])                          # track_count = 7
        body += struct.pack('<H', 0x1234)          # orderlist_ptrs_lo
        body += struct.pack('<H', 0x5678)          # orderlist_ptrs_hi
        body += bytes([16])                        # sequence_count
        body += struct.pack('<H', 0x2222)          # sequence_ptrs_lo
        body += struct.pack('<H', 0x3333)          # sequence_ptrs_hi
        body += struct.pack('<H', 0x0080)          # orderlist_size
        body += struct.pack('<H', 0xABCD)          # orderlist_start
        body += struct.pack('<H', 0x0100)          # sequence_size
        body += struct.pack('<H', 0xFEDC)          # sequence_start
        self.assertEqual(len(body), 18)
        sf2_parser.parse_music_data_block(body, di)
        self.assertEqual(di.track_count, 7)
        self.assertEqual(di.orderlist_ptrs_lo, 0x1234)
        self.assertEqual(di.orderlist_ptrs_hi, 0x5678)
        self.assertEqual(di.sequence_count, 16)
        self.assertEqual(di.sequence_ptrs_lo, 0x2222)
        self.assertEqual(di.sequence_ptrs_hi, 0x3333)
        self.assertEqual(di.orderlist_size, 0x0080)
        self.assertEqual(di.orderlist_start, 0xABCD)
        self.assertEqual(di.sequence_size, 0x0100)
        self.assertEqual(di.sequence_start, 0xFEDC)


# ---------------------------------------------------------------------------
# parse_tables_block
# ---------------------------------------------------------------------------

def _make_table_descriptor(table_type: int, table_id: int, name: str,
                            addr: int, columns: int, rows: int) -> bytes:
    """Build a single Block 3 table descriptor for testing.

    Layout: type(1) + id(1) + text_field_size(1) + name+NUL(var) +
            layout(1) + flags(1) + rules(3) + addr(2) + columns(2) +
            rows(2) + visible_rows(1) = 12 bytes AFTER the NUL.
    """
    out = bytearray()
    out.append(table_type)
    out.append(table_id)
    out.append(0)                         # text_field_size
    out.extend(name.encode('latin-1'))
    out.append(0)                         # NUL terminator
    out.extend([0, 0])                    # layout + flags
    out.extend([0, 0, 0])                 # rules
    out.extend(struct.pack('<H', addr))
    out.extend(struct.pack('<H', columns))
    out.extend(struct.pack('<H', rows))
    out.append(0)                         # visible_rows
    return bytes(out)


class TestParseTablesBlock(unittest.TestCase):
    def test_instruments_table(self):
        di = SF2DriverInfo()
        data = _make_table_descriptor(0x80, 1, "Instruments",
                                       0x1800, 6, 32) + b"\xFF"
        sf2_parser.parse_tables_block(data, di)
        self.assertIn('Instruments', di.table_addresses)
        info = di.table_addresses['Instruments']
        self.assertEqual(info['type'], 0x80)
        self.assertEqual(info['id'], 1)
        self.assertEqual(info['addr'], 0x1800)
        self.assertEqual(info['columns'], 6)
        self.assertEqual(info['rows'], 32)

    def test_commands_table(self):
        di = SF2DriverInfo()
        data = _make_table_descriptor(0x81, 0, "Commands",
                                       0x1900, 3, 64) + b"\xFF"
        sf2_parser.parse_tables_block(data, di)
        info = di.table_addresses['Commands']
        self.assertEqual(info['type'], 0x81)
        self.assertEqual(info['id'], 0)

    def test_wave_table_mapped_by_first_letter(self):
        """A named table 'WaveStuff' should be aliased to 'Wave'."""
        di = SF2DriverInfo()
        data = _make_table_descriptor(0x00, 5, "WaveStuff",
                                       0x1B00, 2, 32) + b"\xFF"
        sf2_parser.parse_tables_block(data, di)
        self.assertIn('Wave', di.table_addresses)
        self.assertIn('WaveStuff', di.table_addresses)
        # Both entries should point to the same info dict
        self.assertEqual(di.table_addresses['Wave'],
                          di.table_addresses['WaveStuff'])

    def test_first_letter_mappings(self):
        """All 5 letter mappings (W, P, F, A, T) work."""
        for first_letter, mapped in [
            ('W', 'Wave'), ('P', 'Pulse'), ('F', 'Filter'),
            ('A', 'Arp'), ('T', 'Tempo'),
        ]:
            di = SF2DriverInfo()
            name = first_letter + "Generic"
            data = _make_table_descriptor(0x00, 1, name,
                                           0x2000, 1, 16) + b"\xFF"
            sf2_parser.parse_tables_block(data, di)
            self.assertIn(mapped, di.table_addresses,
                          f"missing {mapped} alias for {name}")

    def test_multiple_tables_in_one_block(self):
        di = SF2DriverInfo()
        data = (_make_table_descriptor(0x80, 1, "Instruments", 0x1800, 6, 32)
                + _make_table_descriptor(0x81, 0, "Commands", 0x1900, 3, 64)
                + _make_table_descriptor(0x00, 5, "Wave1", 0x1A00, 2, 32)
                + b"\xFF")
        sf2_parser.parse_tables_block(data, di)
        self.assertIn('Instruments', di.table_addresses)
        self.assertIn('Commands', di.table_addresses)
        self.assertIn('Wave', di.table_addresses)
        self.assertIn('Wave1', di.table_addresses)

    def test_terminator_stops_walk(self):
        di = SF2DriverInfo()
        data = (_make_table_descriptor(0x80, 1, "Instruments", 0x1800, 6, 32)
                + b"\xFF"
                + _make_table_descriptor(0x81, 0, "Ghost", 0x9999, 1, 1))
        sf2_parser.parse_tables_block(data, di)
        self.assertIn('Instruments', di.table_addresses)
        self.assertNotIn('Commands', di.table_addresses,
                         "ghost block past terminator must not be parsed")

    def test_empty_data_ignored(self):
        di = SF2DriverInfo()
        sf2_parser.parse_tables_block(b"", di)
        self.assertEqual(di.table_addresses, {})


# ---------------------------------------------------------------------------
# Constants — pin them so any silent change breaks tests
# ---------------------------------------------------------------------------

class TestConstants(unittest.TestCase):
    def test_constants_match_sf2ii(self):
        self.assertEqual(sf2_parser.SF2_FILE_ID, 0x1337)
        self.assertEqual(sf2_parser.BLOCK_DESCRIPTOR, 1)
        self.assertEqual(sf2_parser.BLOCK_DRIVER_TABLES, 3)
        self.assertEqual(sf2_parser.BLOCK_MUSIC_DATA, 5)
        self.assertEqual(sf2_parser.BLOCK_END, 0xFF)


if __name__ == "__main__":
    unittest.main(verbosity=2)
