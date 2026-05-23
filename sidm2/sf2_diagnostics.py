"""Diagnostic helpers for SF2 file output (logging + validation).

Pure observers — none of these functions modify state or have side
effects beyond emitting log messages via the project logger. Extracted
from sf2_writer.py at the v3.5.36 Phase 3 refactor.

The two main entry points:

  log_sf2_structure(label, data)
    Walk the SF2 file's block chain and log everything. Useful for
    debugging at -v / -vv log levels. Calls log_block3_structure and
    log_block5_structure for the two blocks that need detailed
    interpretation.

  validate_sf2_file(filepath)
    Read a written SF2 file from disk and verify it has the structural
    invariants SF2II's parser requires (magic, all required blocks
    present, Instruments + Commands tables in Block 3, no truncation).
    Logs OK/WARN/ERR for each check.

These are called from SF2Writer.write() as the final diagnostic step.
SF2Writer keeps thin wrapper methods that forward to these functions.
"""
from __future__ import annotations
import logging
import struct

logger = logging.getLogger(__name__)


def log_sf2_structure(label: str, data: bytes) -> None:
    """Log detailed SF2 file structure for debugging.

    Args:
        label: Description label for this structure dump
        data: SF2 file data to analyze
    """
    logger.debug(f"=" * 70)
    logger.debug(f"{label}")
    logger.debug(f"=" * 70)
    logger.debug(f"Total size: {len(data)} bytes")

    if len(data) < 4:
        logger.debug("  File too small to analyze")
        return

    # Parse load address and magic number
    load_addr = struct.unpack('<H', data[0:2])[0]
    logger.debug(f"Load address: ${load_addr:04X}")

    offset = 2
    if len(data) < offset + 2:
        logger.debug("  No magic number found")
        return

    magic = struct.unpack('<H', data[offset:offset + 2])[0]
    logger.debug(f"Magic number: 0x{magic:04X} {'OK VALID' if magic == 0x1337 else 'ERR INVALID'}")
    offset += 2

    # Parse all blocks
    block_count = 0
    logger.debug("\nBlock Structure:")
    while offset < len(data) - 1:
        block_id = data[offset]

        # Check for end marker
        if block_id == 0xFF:
            logger.debug(f"\n  End marker (0xFF) at offset ${offset:04X}")
            break

        block_size = data[offset + 1]
        block_end = offset + 2 + block_size

        logger.debug(f"\n  Block {block_id}:")
        logger.debug(f"    Offset: ${offset:04X} - ${block_end:04X}")
        logger.debug(f"    Declared size: {block_size} bytes")
        logger.debug(f"    Actual size: {block_size + 2} bytes (with header)")

        # Special handling for Block 3 (Driver Tables)
        if block_id == 3 and block_size > 0:
            content = data[offset + 2:offset + 2 + block_size]
            log_block3_structure(content)

        # Special handling for Block 5 (Music Data)
        elif block_id == 5 and block_size >= 18:
            content = data[offset + 2:offset + 2 + block_size]
            log_block5_structure(content)

        offset = block_end
        block_count += 1

        if block_count > 20:  # Safety limit
            logger.debug("    ... (too many blocks, stopping)")
            break

    logger.debug(f"\nTotal blocks parsed: {block_count}")
    logger.debug(f"=" * 70)


def log_block3_structure(content: bytes) -> None:
    """Log detailed Block 3 (Driver Tables) structure.

    Args:
        content: Block 3 content bytes
    """
    logger.debug("    Block 3 (Driver Tables) details:")

    pos = 0
    table_count = 0
    while pos < len(content) and content[pos] != 0xFF:
        if pos + 3 > len(content):
            logger.debug(f"      ERR Truncated at table {table_count}")
            break

        table_type = content[pos]
        table_id = content[pos + 1]
        name_len = content[pos + 2]

        if pos + 3 + name_len > len(content):
            logger.debug(f"      ERR Truncated name at table {table_count}")
            break

        # Decode table name
        name_bytes = content[pos + 3:pos + 3 + name_len]
        try:
            name = name_bytes[:-1].decode('ascii')  # Skip null terminator
        except Exception:
            name = "<binary>"

        # Table type names
        type_names = {0x00: "Generic", 0x80: "Instruments", 0x81: "Commands"}
        type_name = type_names.get(table_type, f"Unknown(0x{table_type:02X})")

        logger.debug(f"      Table {table_count}: {type_name} (0x{table_type:02X})")
        logger.debug(f"        ID: {table_id}")
        logger.debug(f"        Name: \"{name}\"")

        # Calculate descriptor size including VisibleRows byte
        # Format: Type(1) + ID(1) + NameLen(1) + Name(var) + Layout(1) + Flags(1) +
        #         Rules(3) + Address(2) + Columns(2) + Rows(2) + VisibleRows(1)
        descriptor_size = 3 + name_len + 1 + 1 + 3 + 2 + 2 + 2 + 1

        if pos + descriptor_size > len(content):
            logger.debug(f"      ERR Truncated descriptor at table {table_count}")
            break

        pos += descriptor_size
        table_count += 1

    # Check for terminator
    if pos < len(content) and content[pos] == 0xFF:
        logger.debug(f"      OK Found 0xFF terminator at position {pos}")
        logger.debug(f"      OK Total tables: {table_count}")
    else:
        logger.debug(f"      ERR No 0xFF terminator found (stopped at position {pos})")


def log_block5_structure(content: bytes) -> None:
    """Log detailed Block 5 (Music Data) structure.

    Args:
        content: Block 5 content bytes
    """
    if len(content) < 18:
        logger.debug("    Block 5 (Music Data): Too small")
        return

    logger.debug("    Block 5 (Music Data) details:")

    # Parse music data fields
    offset = 0
    track_count = content[offset]
    offset += 1
    logger.debug(f"      Track count: {track_count}")

    track_ol_ptr_lo = struct.unpack('<H', content[offset:offset + 2])[0]
    offset += 2
    track_ol_ptr_hi = struct.unpack('<H', content[offset:offset + 2])[0]
    offset += 2
    logger.debug(f"      Track orderlist pointers: ${track_ol_ptr_lo:04X} / ${track_ol_ptr_hi:04X}")

    seq_count = content[offset]
    offset += 1
    logger.debug(f"      Sequence count: {seq_count}")

    seq_ptr_lo = struct.unpack('<H', content[offset:offset + 2])[0]
    offset += 2
    seq_ptr_hi = struct.unpack('<H', content[offset:offset + 2])[0]
    offset += 2
    logger.debug(f"      Sequence pointers: ${seq_ptr_lo:04X} / ${seq_ptr_hi:04X}")

    ol_size = struct.unpack('<H', content[offset:offset + 2])[0]
    offset += 2
    logger.debug(f"      Orderlist size: {ol_size}")

    ol_track1 = struct.unpack('<H', content[offset:offset + 2])[0]
    offset += 2
    logger.debug(f"      Orderlist track 1: ${ol_track1:04X}")

    seq_size = struct.unpack('<H', content[offset:offset + 2])[0]
    offset += 2
    logger.debug(f"      Sequence size: {seq_size}")

    seq00_addr = struct.unpack('<H', content[offset:offset + 2])[0]
    offset += 2
    logger.debug(f"      Sequence 00 address: ${seq00_addr:04X}")

    logger.debug(f"      OK All 18 bytes read correctly")


def validate_sf2_file(filepath: str) -> None:
    """Validate written SF2 file structure.

    Reads the file from disk, walks its block chain, and reports
    per-block OK/WARN/ERR status. Catches: missing magic, truncated
    blocks, missing required blocks (1, 2, 3, 5), missing
    Instruments/Commands tables in Block 3.

    Args:
        filepath: Path to SF2 file to validate
    """
    logger.debug(f"\nValidating SF2 file: {filepath}")

    try:
        with open(filepath, 'rb') as f:
            data = f.read()
    except IOError:
        logger.error(
            "  ERR Could not read file for validation\n"
            "  Suggestion: Check file permissions and path\n"
            "  Check: Ensure file exists and is accessible\n"
            "  See: docs/guides/TROUBLESHOOTING.md#file-access-errors"
        )
        return

    # Check minimum size
    if len(data) < 100:
        logger.error(
            f"  ERR File too small: {len(data)} bytes\n"
            f"  Suggestion: File appears corrupted or incomplete\n"
            f"  Check: Minimum valid SF2 file is ~8KB\n"
            f"  Try: Regenerate SF2 file from source SID\n"
            f"  See: docs/guides/TROUBLESHOOTING.md#corrupted-sf2-files"
        )
        return

    # Check magic number
    if len(data) >= 4:
        magic = struct.unpack('<H', data[2:4])[0]
        if magic == 0x1337:
            logger.debug("  OK Valid magic number (0x1337)")
        else:
            logger.error(
                f"  ERR Invalid magic number: 0x{magic:04X} (expected 0x1337)\n"
                f"  Suggestion: File is not a valid SF2 format\n"
                f"  Check: Ensure file was generated by SIDM2 converter\n"
                f"  Try: Reconvert from original SID file\n"
                f"  See: docs/SF2_FORMAT_SPEC.md#magic-number"
            )
            return

    # Parse and validate blocks
    offset = 4  # After load address and magic
    block_count = 0
    has_block1 = False
    has_block2 = False
    has_block3 = False
    has_block5 = False
    has_instruments = False
    has_commands = False

    while offset < len(data) - 1:
        block_id = data[offset]

        if block_id == 0xFF:
            logger.debug(f"  OK Found end marker at offset ${offset:04X}")
            break

        if offset + 1 >= len(data):
            logger.error(
                f"  ERR File truncated at block {block_id}\n"
                f"  Suggestion: File was not written completely\n"
                f"  Check: Verify disk space during conversion\n"
                f"  Try: Regenerate SF2 file\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#truncated-files"
            )
            return

        block_size = data[offset + 1]
        block_end = offset + 2 + block_size

        if block_end > len(data):
            logger.error(
                f"  ERR Block {block_id} extends beyond file (declares {block_size} bytes)\n"
                f"  Suggestion: Block size header is corrupted\n"
                f"  Check: File may have been modified after generation\n"
                f"  Try: Regenerate SF2 file from source\n"
                f"  See: docs/SF2_FORMAT_SPEC.md#block-structure"
            )
            return

        # Track which blocks we found
        if block_id == 1:
            has_block1 = True
        elif block_id == 2:
            has_block2 = True
        elif block_id == 3:
            has_block3 = True
            # Check for required tables
            content = data[offset + 2:block_end]
            pos = 0
            while pos < len(content) and content[pos] != 0xFF:
                if pos + 3 <= len(content):
                    table_type = content[pos]
                    name_len = content[pos + 2] if pos + 2 < len(content) else 0
                    if table_type == 0x80:
                        has_instruments = True
                    elif table_type == 0x81:
                        has_commands = True
                    # Skip to next descriptor
                    desc_size = 3 + name_len + 1 + 1 + 3 + 2 + 2 + 2 + 1
                    pos += desc_size
                else:
                    break
        elif block_id == 5:
            has_block5 = True

        offset = block_end
        block_count += 1

        if block_count > 20:
            logger.error(
                "  ERR Too many blocks (possible corruption)\n"
                "  Suggestion: File structure appears corrupted\n"
                "  Check: Normal SF2 files have 3-5 blocks\n"
                "  Try: Regenerate SF2 file from original SID\n"
                "  See: docs/SF2_FORMAT_SPEC.md#block-limits"
            )
            return

    # Report validation results
    logger.debug(f"  OK Parsed {block_count} blocks successfully")

    if has_block1:
        logger.debug("  OK Block 1 (Descriptor) present")
    else:
        logger.warning("  WARN Block 1 (Descriptor) missing")

    if has_block2:
        logger.debug("  OK Block 2 (Driver Common) present")
    else:
        logger.warning("  WARN Block 2 (Driver Common) missing")

    if has_block3:
        logger.debug("  OK Block 3 (Driver Tables) present")
        if has_instruments:
            logger.debug("    OK Instruments table (0x80) found")
        else:
            logger.error(
                "    ERR Instruments table (0x80) MISSING - file will be rejected!\n"
                "    Suggestion: Critical metadata missing from SF2 file\n"
                "    Check: Conversion may have failed partway through\n"
                "    Try: Regenerate with --verbose to see where it failed\n"
                "    See: docs/SF2_FORMAT_SPEC.md#required-tables"
            )

        if has_commands:
            logger.debug("    OK Commands table (0x81) found")
        else:
            logger.error(
                "    ERR Commands table (0x81) MISSING - file will be rejected!\n"
                "    Suggestion: Critical metadata missing from SF2 file\n"
                "    Check: Conversion may have failed partway through\n"
                "    Try: Regenerate with --verbose to see where it failed\n"
                "    See: docs/SF2_FORMAT_SPEC.md#required-tables"
            )
    else:
        logger.error(
            "  ERR Block 3 (Driver Tables) missing\n"
            "  Suggestion: Critical driver tables not generated\n"
            "  Check: Conversion may have failed during table generation\n"
            "  Try: Regenerate SF2 file with different driver\n"
            "  See: docs/SF2_FORMAT_SPEC.md#driver-tables"
        )

    if has_block5:
        logger.debug("  OK Block 5 (Music Data) present")
    else:
        logger.warning("  WARN Block 5 (Music Data) missing")

    # Final verdict
    if has_instruments and has_commands and has_block1 and has_block2 and has_block3:
        logger.info("  OK SF2 FILE VALIDATION PASSED - file should load in SF2 Editor")
    else:
        logger.error(
            "  ERR SF2 FILE VALIDATION FAILED - file may be rejected by SF2 Editor\n"
            "  Suggestion: Review validation errors above for specific issues\n"
            "  Check: File may still work despite validation warnings\n"
            "  Try: Test file in SID Factory II to confirm\n"
            "  See: docs/guides/TROUBLESHOOTING.md#sf2-validation-failures"
        )
