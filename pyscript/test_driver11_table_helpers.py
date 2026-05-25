"""Unit tests for sidm2.driver11_table_helpers.

Two helpers used across the driver11 template path's _inject_*_table
methods:

  find_table(driver_info, name_substring, short_alias=None)
    - Substring match against table names
    - Alias match (e.g., 'F' for Filter)
    - Returns None when no match

  write_column_major(output, base_offset, entries, columns, rows)
    - Column-major write of tuple-rows into a bytearray
    - Bounds checks both buffer length and per-entry tuple length
    - Caps columns at max_columns (default 4)
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import driver11_table_helpers
from sidm2.models import SF2DriverInfo


# ---------------------------------------------------------------------------
# find_table
# ---------------------------------------------------------------------------

class TestFindTable(unittest.TestCase):
    def _make_driver_info(self, table_addresses):
        di = SF2DriverInfo()
        di.table_addresses = table_addresses
        return di

    def test_substring_match(self):
        di = self._make_driver_info({
            'Filter Table': {'addr': 0x1800, 'columns': 3, 'rows': 16},
        })
        result = driver11_table_helpers.find_table(di, 'Filter')
        self.assertEqual(result, (0x1800, 3, 16))

    def test_short_alias_match(self):
        di = self._make_driver_info({
            'F': {'addr': 0x2000, 'columns': 3, 'rows': 16},
        })
        result = driver11_table_helpers.find_table(di, 'Filter', 'F')
        self.assertEqual(result, (0x2000, 3, 16))

    def test_substring_preferred_over_alias_first_match(self):
        """First iteration order match wins (no ordering guarantee in dict
        but both possible matches should be valid)."""
        di = self._make_driver_info({
            'Filter Stuff': {'addr': 0x1800, 'columns': 3, 'rows': 16},
            'F': {'addr': 0x2000, 'columns': 4, 'rows': 32},
        })
        result = driver11_table_helpers.find_table(di, 'Filter', 'F')
        self.assertIsNotNone(result)
        # Result should be one of the two valid matches
        self.assertIn(result, [(0x1800, 3, 16), (0x2000, 4, 32)])

    def test_returns_none_when_no_match(self):
        di = self._make_driver_info({
            'Instruments': {'addr': 0x1800, 'columns': 6, 'rows': 32},
        })
        self.assertIsNone(
            driver11_table_helpers.find_table(di, 'Filter'))

    def test_returns_none_when_no_alias_match_and_no_substring(self):
        di = self._make_driver_info({
            'Instruments': {'addr': 0x1800, 'columns': 6, 'rows': 32},
        })
        self.assertIsNone(
            driver11_table_helpers.find_table(di, 'Filter', 'F'))

    def test_empty_table_addresses(self):
        di = self._make_driver_info({})
        self.assertIsNone(
            driver11_table_helpers.find_table(di, 'AnyTable'))

    def test_only_alias_when_substring_explicitly_none(self):
        """When name_substring is '' (empty), the substring check
        `'' in name` matches EVERY name. This documents that empty
        substring is treated as "match-all"."""
        di = self._make_driver_info({
            'Anything': {'addr': 0x1000, 'columns': 1, 'rows': 1},
        })
        result = driver11_table_helpers.find_table(di, '', None)
        self.assertEqual(result, (0x1000, 1, 1))


# ---------------------------------------------------------------------------
# write_column_major
# ---------------------------------------------------------------------------

class TestWriteColumnMajor(unittest.TestCase):
    def test_basic_4_col_3_row(self):
        """columns=4, rows=3: bytes laid out as col0 col0 col0 col1 col1 col1 …"""
        output = bytearray(20)
        entries = [
            (0x10, 0x20, 0x30, 0x40),    # row 0
            (0x11, 0x21, 0x31, 0x41),    # row 1
            (0x12, 0x22, 0x32, 0x42),    # row 2
        ]
        driver11_table_helpers.write_column_major(
            output, 0, entries, columns=4, rows=3)
        # Expected layout: col0 col0 col0 | col1 col1 col1 | col2 col2 col2 | col3 col3 col3
        expected = bytes([
            0x10, 0x11, 0x12,    # col 0
            0x20, 0x21, 0x22,    # col 1
            0x30, 0x31, 0x32,    # col 2
            0x40, 0x41, 0x42,    # col 3
        ])
        self.assertEqual(bytes(output[:12]), expected)

    def test_base_offset_respected(self):
        output = bytearray(20)
        entries = [(0xAA, 0xBB)]
        driver11_table_helpers.write_column_major(
            output, base_offset=5, entries=entries, columns=2, rows=1)
        self.assertEqual(output[5], 0xAA)
        self.assertEqual(output[5 + 1], 0xBB)
        # Bytes before base_offset untouched
        self.assertEqual(bytes(output[:5]), bytes(5))

    def test_columns_capped_at_max_columns(self):
        """A table with 6 columns but max_columns=4 only writes 4 cols."""
        output = bytearray(50)
        entries = [(0x10, 0x20, 0x30, 0x40, 0x50, 0x60)]
        driver11_table_helpers.write_column_major(
            output, 0, entries, columns=6, rows=1, max_columns=4)
        # Only 4 columns written
        self.assertEqual(bytes(output[:4]), b"\x10\x20\x30\x40")
        # Col 4 / 5 NOT written (still zero)
        self.assertEqual(output[4], 0x00)
        self.assertEqual(output[5], 0x00)

    def test_entries_capped_at_rows(self):
        """If entries has more rows than `rows`, only `rows` are written."""
        output = bytearray(20)
        entries = [(0x11,), (0x22,), (0x33,), (0x44,)]
        driver11_table_helpers.write_column_major(
            output, 0, entries, columns=1, rows=2)
        # Only first 2 rows of col 0 written
        self.assertEqual(output[0], 0x11)
        self.assertEqual(output[1], 0x22)
        # row 2 / row 3 NOT written
        self.assertEqual(output[2], 0x00)
        self.assertEqual(output[3], 0x00)

    def test_short_entry_tuple_skips_columns(self):
        """If an entry is (0x11,) but columns=3, only col 0 is written
        from that entry; cols 1 and 2 are untouched for that row."""
        output = bytearray(20)
        entries = [(0x11, 0x22)]   # only 2 columns of data
        driver11_table_helpers.write_column_major(
            output, 0, entries, columns=3, rows=1)
        self.assertEqual(output[0], 0x11)
        self.assertEqual(output[1], 0x22)
        # Col 2 was NOT written (entry too short)
        self.assertEqual(output[2], 0x00)

    def test_offset_past_buffer_skipped(self):
        """Writes past buffer end are silently skipped (not raised)."""
        output = bytearray(3)
        entries = [(0x10, 0x20, 0x30, 0x40, 0x50)]
        driver11_table_helpers.write_column_major(
            output, 0, entries, columns=5, rows=1)
        # Only cols 0/1/2 fit; cols 3+4 silently skipped
        self.assertEqual(bytes(output), b"\x10\x20\x30")

    def test_empty_entries(self):
        output = bytearray(10)
        driver11_table_helpers.write_column_major(
            output, 0, [], columns=4, rows=10)
        self.assertEqual(bytes(output), bytes(10), "buffer unchanged")


if __name__ == "__main__":
    unittest.main(verbosity=2)
