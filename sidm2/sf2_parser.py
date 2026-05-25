"""Parser for SF2 file blocks (Descriptor + MusicData + DriverTables).

Extracted from sf2_writer.py at the v3.5.40 Phase 6 refactor.

The SF2 file format is a chain of TLV blocks (`[id:1][size:1][body]`)
terminated by `0xFF`. SIDM2's converter parses incoming SF2 templates
to learn:
  - Driver name, size, type (Block 1 / Descriptor)
  - Music data layout: track count, orderlist + sequence pointers,
    sizes, start addresses (Block 5 / MusicData)
  - Driver table addresses: Instruments + Commands + the dynamic
    Wave/Pulse/Filter/Arp/Tempo named tables (Block 3 / DriverTables)

# API

  parse_sf2_blocks(sf2_bytes, driver_info) -> Optional[int]
    Walks the entire block chain. Returns the PRG load address on
    success, None on missing/invalid magic. Mutates `driver_info`
    in place with the parsed fields.

  parse_descriptor_block(data, driver_info) -> None
  parse_music_data_block(data, driver_info) -> None
  parse_tables_block(data, driver_info) -> None
    Per-block parsers, exposed for unit testing in isolation.

All parsers are best-effort: malformed bodies are silently skipped
rather than raised. The caller (SF2Writer) keeps thin wrapper methods
forwarding to these functions for backwards-compat with the test
suite at `pyscript/test_sf2_writer.py`.
"""
from __future__ import annotations
import logging
import struct
from typing import Optional

from .models import SF2DriverInfo

logger = logging.getLogger(__name__)


# SF2 file format constants. These match SF2II's parser; changing any
# of them silently breaks F10-load.
SF2_FILE_ID = 0x1337            # magic number at file offset 2
BLOCK_DESCRIPTOR = 1            # Block 1 — driver name + size + type
BLOCK_DRIVER_TABLES = 3         # Block 3 — instruments + commands + named tables
BLOCK_MUSIC_DATA = 5            # Block 5 — orderlists + sequences layout
BLOCK_END = 0xFF                # block-chain terminator


def parse_sf2_blocks(
    sf2_bytes: bytes,
    driver_info: SF2DriverInfo,
) -> Optional[int]:
    """Walk the SF2 file's block chain and populate driver_info.

    Args:
        sf2_bytes: The raw SF2 file bytes (including the 2-byte PRG
            load address at offset 0).
        driver_info: The dataclass to populate (mutated in place).

    Returns:
        The PRG load address (the value at bytes 0-1, little-endian)
        on success. None if the file is too short or has an invalid
        magic number.
    """
    if len(sf2_bytes) < 4:
        return None

    load_address = struct.unpack('<H', sf2_bytes[0:2])[0]
    file_id = struct.unpack('<H', sf2_bytes[2:4])[0]
    if file_id != SF2_FILE_ID:
        logger.warning(
            f" File ID {file_id:04X} != expected {SF2_FILE_ID:04X}")
        return None

    logger.debug(f"Parsing SF2 header (load address: ${load_address:04X})")

    offset = 4
    while offset < len(sf2_bytes) - 2:
        block_id = sf2_bytes[offset]
        if block_id == BLOCK_END:
            break

        block_size = sf2_bytes[offset + 1]
        block_data = sf2_bytes[offset + 2:offset + 2 + block_size]

        if block_id == BLOCK_DESCRIPTOR:
            parse_descriptor_block(block_data, driver_info)
        elif block_id == BLOCK_MUSIC_DATA:
            parse_music_data_block(block_data, driver_info)
        elif block_id == BLOCK_DRIVER_TABLES:
            parse_tables_block(block_data, driver_info)

        offset += 2 + block_size

    return load_address


def parse_descriptor_block(data: bytes, driver_info: SF2DriverInfo) -> None:
    """Parse Block 1 (Descriptor) into driver_info.

    Body layout: [u8 type][u16 LE size][NUL-terminated driver name]...
    """
    if len(data) < 3:
        return

    driver_info.driver_type = data[0]
    driver_info.driver_size = struct.unpack('<H', data[1:3])[0]

    name_end = 3
    while name_end < len(data) and data[name_end] != 0:
        name_end += 1

    driver_info.driver_name = data[3:name_end].decode(
        'latin-1', errors='replace')
    logger.debug(f"  Driver: {driver_info.driver_name}")


def parse_music_data_block(data: bytes, driver_info: SF2DriverInfo) -> None:
    """Parse Block 5 (MusicData) into driver_info.

    Body layout (18 bytes):
      [u8 track_count]
      [u16 LE orderlist_ptrs_lo][u16 LE orderlist_ptrs_hi]
      [u8 sequence_count]
      [u16 LE sequence_ptrs_lo][u16 LE sequence_ptrs_hi]
      [u16 LE orderlist_size][u16 LE orderlist_start]
      [u16 LE sequence_size][u16 LE sequence_start]
    """
    if len(data) < 18:
        return

    idx = 0
    driver_info.track_count = data[idx]
    idx += 1

    driver_info.orderlist_ptrs_lo = struct.unpack('<H', data[idx:idx + 2])[0]
    idx += 2
    driver_info.orderlist_ptrs_hi = struct.unpack('<H', data[idx:idx + 2])[0]
    idx += 2

    driver_info.sequence_count = data[idx]
    idx += 1

    driver_info.sequence_ptrs_lo = struct.unpack('<H', data[idx:idx + 2])[0]
    idx += 2
    driver_info.sequence_ptrs_hi = struct.unpack('<H', data[idx:idx + 2])[0]
    idx += 2

    driver_info.orderlist_size = struct.unpack('<H', data[idx:idx + 2])[0]
    idx += 2
    driver_info.orderlist_start = struct.unpack('<H', data[idx:idx + 2])[0]
    idx += 2

    driver_info.sequence_size = struct.unpack('<H', data[idx:idx + 2])[0]
    idx += 2
    driver_info.sequence_start = struct.unpack('<H', data[idx:idx + 2])[0]

    logger.debug(f"  Tracks: {driver_info.track_count}")
    logger.debug(f"  Sequences: {driver_info.sequence_count}")
    logger.debug(f"  Sequence start: ${driver_info.sequence_start:04X}")
    logger.debug(f"  Orderlist start: ${driver_info.orderlist_start:04X}")


def parse_tables_block(data: bytes, driver_info: SF2DriverInfo) -> None:
    """Parse Block 3 (DriverTables) into driver_info.table_addresses.

    Body is a chain of per-table descriptors, terminated by `0xFF`.
    Each descriptor:
      [u8 type][u8 id][u8 text_field_size]
      [NUL-terminated name]
      [u8 layout][u8 flags][3B rules]
      [u16 LE addr][u16 LE columns][u16 LE rows]
      [u8 visible_rows]    ← total descriptor span is 12 bytes
                              after the NUL terminator

    Type-to-name mapping:
      0x80 → "Instruments"
      0x81 → "Commands"
      other → use the first char of the name to identify
              (W→Wave, P→Pulse, F→Filter, A→Arp, T→Tempo).
    """
    idx = 0
    while idx < len(data):
        if idx >= len(data):
            break

        table_type = data[idx]
        if table_type == 0xFF:
            break

        if idx + 3 > len(data):
            break

        table_id = data[idx + 1]
        # text_field_size = data[idx + 2]  # currently unused

        name_start = idx + 3
        name_end = name_start
        while name_end < len(data) and data[name_end] != 0:
            name_end += 1
        name = data[name_start:name_end].decode('latin-1', errors='replace')

        pos = name_end + 1
        if pos + 12 <= len(data):
            addr = struct.unpack('<H', data[pos + 5:pos + 7])[0]
            columns = struct.unpack('<H', data[pos + 7:pos + 9])[0]
            rows = struct.unpack('<H', data[pos + 9:pos + 11])[0]

            table_info = {
                'type': table_type,
                'id': table_id,
                'addr': addr,
                'columns': columns,
                'rows': rows,
                'name': name,
            }

            if table_type == 0x80:
                driver_info.table_addresses['Instruments'] = table_info
                logger.info(
                    f"    Instruments table at ${addr:04X} "
                    f"({columns}×{rows}) [ID={table_id}]")
            elif table_type == 0x81:
                driver_info.table_addresses['Commands'] = table_info
                logger.info(
                    f"    Commands table at ${addr:04X} "
                    f"({columns}×{rows}) [ID={table_id}]")
            else:
                if name:
                    driver_info.table_addresses[name] = table_info
                    first_char = name[0] if name else ''
                    if first_char in ['W', 'P', 'F', 'A', 'T']:
                        key_map = {
                            'W': 'Wave', 'P': 'Pulse', 'F': 'Filter',
                            'A': 'Arp', 'T': 'Tempo',
                        }
                        mapped_name = key_map.get(first_char, first_char)
                        driver_info.table_addresses[mapped_name] = table_info
                        logger.info(
                            f"    {mapped_name} table (\"{name}\") "
                            f"at ${addr:04X} ({columns}×{rows}) "
                            f"[type=${table_type:02X}, ID={table_id}]")

            idx = pos + 12
        else:
            break
