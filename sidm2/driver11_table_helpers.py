"""Shared helpers for the driver11 template path's _inject_*_table methods.

Extracted from sf2_writer.py at the v3.5.44 refactor.

The driver11 template path has ~7 `_inject_*_table` methods
(Instruments, Pulse, Filter, Wave, Arp, Tempo, Init, HR, Commands)
that all share two repeated patterns:

# Pattern 1: Find table by name substring in driver_info.table_addresses

    table = None
    for name, info in self.driver_info.table_addresses.items():
        if 'Filter' in name or name == 'F':
            table = info
            break
    if not table:
        logger.debug("    Warning: No Filter table found in driver")
        return
    addr = table['addr']; columns = table['columns']; rows = table['rows']

# Pattern 2: Write tuple entries column-major into the SF2 buffer

    base_offset = self._addr_to_offset(addr)
    for col in range(min(columns, 4)):
        for i, entry in enumerate(entries):
            if i < rows:
                offset = base_offset + (col * rows) + i
                if offset < len(self.output) and col < len(entry):
                    self.output[offset] = entry[col]

Both patterns repeated across at least 6 methods. This module
consolidates them.

# API

  find_table(driver_info, name_substring, short_alias=None)
    -> Optional[Tuple[int, int, int]]
    Returns (addr, columns, rows) or None.

  write_column_major(output, base_offset, entries, columns, rows,
                     max_columns=4) -> None
    Writes column-major tuple data into a bytearray at base_offset.
"""
from __future__ import annotations
from typing import List, Optional, Sequence, Tuple


def find_table(
    driver_info,
    name_substring: str,
    short_alias: Optional[str] = None,
) -> Optional[Tuple[int, int, int]]:
    """Find a Block 3 table by name substring (e.g., 'Filter', 'Pulse').

    Searches driver_info.table_addresses (a dict populated by
    sf2_parser.parse_tables_block). Match conditions:
      - `name_substring` is a substring of the table key
      - OR the key equals `short_alias` (e.g., 'F' for Filter)

    Args:
        driver_info: The SF2DriverInfo dataclass populated by the parser.
        name_substring: Substring to match against table names
            (e.g., 'Filter', 'Pulse', 'Wave').
        short_alias: Optional 1-2 char alias (e.g., 'F', 'P', 'W').

    Returns:
        (addr, columns, rows) tuple on match, None otherwise.
    """
    for name, info in driver_info.table_addresses.items():
        if name_substring in name or (short_alias and name == short_alias):
            return info['addr'], info['columns'], info['rows']
    return None


def write_column_major(
    output: bytearray,
    base_offset: int,
    entries: Sequence[Sequence[int]],
    columns: int,
    rows: int,
    max_columns: int = 4,
) -> None:
    """Write a list of tuple-rows to a bytearray in column-major order.

    For each column c (up to min(columns, max_columns)):
      For each row i (up to len(entries) and < rows):
        output[base_offset + (c * rows) + i] = entries[i][c]

    Bounds-checks both:
      - offset < len(output)  (don't write past buffer)
      - c < len(entries[i])   (skip cols beyond the entry's tuple length)

    This shape matches SF2's Block 3 column storage — each column is
    a contiguous `rows`-byte slice; columns are placed sequentially.

    Args:
        output: The SF2 buffer to write into (mutated in place).
        base_offset: File offset where the table starts.
        entries: Iterable of tuple-rows. Each tuple is (col0, col1, ...).
        columns: Total columns in the SF2 table descriptor.
        rows: Total rows in the SF2 table descriptor.
        max_columns: Cap on columns written (default 4 — most NP21
            tables have <= 4 active columns).
    """
    for col in range(min(columns, max_columns)):
        for i, entry in enumerate(entries):
            if i < rows:
                offset = base_offset + (col * rows) + i
                if offset < len(output) and col < len(entry):
                    output[offset] = entry[col]
