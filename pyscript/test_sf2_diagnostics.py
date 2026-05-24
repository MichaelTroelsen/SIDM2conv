"""Unit tests for sidm2.sf2_diagnostics.

These functions are pure observers — they walk SF2 byte buffers and
emit log messages but never modify state. Tests use synthetic buffers
+ a tempfile (for validate_sf2_file) and assert on log output via
`assertLogs`.

Coverage targets:
  - log_sf2_structure: tiny / valid / invalid-magic buffers
  - log_block3_structure: well-formed table descriptor, truncated, no terminator
  - log_block5_structure: well-formed 18-byte header, undersized
  - validate_sf2_file: missing file, too-small file, invalid magic,
                       valid file with all required blocks,
                       missing required tables (Instruments/Commands)
"""
import logging
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import sf2_diagnostics


# ---------------------------------------------------------------------------
# Synthetic SF2 buffer helpers
# ---------------------------------------------------------------------------

def _block3_table_descriptor(table_type: int, table_id: int, name: str) -> bytes:
    """Build one Block 3 table descriptor.

    Format: Type(1) + ID(1) + NameLen(1) + Name(var, NUL-terminated) +
            Layout(1) + Flags(1) + Rules(3) + Address(2) + Columns(2) +
            Rows(2) + VisibleRows(1)
    """
    name_bytes = name.encode('ascii') + b'\x00'
    name_len = len(name_bytes)
    return bytes([table_type, table_id, name_len]) + name_bytes + b'\x00' * (1 + 1 + 3 + 2 + 2 + 2 + 1)


def _build_valid_sf2(with_instruments: bool = True,
                      with_commands: bool = True,
                      with_block5: bool = True) -> bytes:
    """Build a minimal but structurally complete SF2 file in memory.
    Always includes Block 1 (Descriptor) + Block 2 (DriverCommon) +
    Block 3 (DriverTables) — flags above toggle the optional content.
    Returns bytes (immutable; ready for tempfile)."""
    # Header: load + magic
    out = bytearray()
    out += (0x0D7E).to_bytes(2, 'little')   # load
    out += (0x1337).to_bytes(2, 'little')   # magic

    # Block 1 (Descriptor) — 4-byte stub body
    b1_body = bytes([0x00, 0x01, 0x02, 0x03])
    out += bytes([1, len(b1_body)]) + b1_body

    # Block 2 (DriverCommon) — 12-byte body
    b2_body = bytes(12)
    out += bytes([2, len(b2_body)]) + b2_body

    # Block 3 (DriverTables) — N descriptors + terminator 0xFF
    b3 = bytearray()
    if with_instruments:
        b3 += _block3_table_descriptor(0x80, 1, "Instruments")
    if with_commands:
        b3 += _block3_table_descriptor(0x81, 2, "Commands")
    b3 += bytes([0xFF])  # terminator
    out += bytes([3, len(b3)]) + bytes(b3)

    # Block 5 (MusicData) — 18-byte body
    if with_block5:
        b5_body = bytes(18)
        out += bytes([5, len(b5_body)]) + b5_body

    # End marker
    out += bytes([0xFF])

    # Pad past the 100-byte minimum that validate_sf2_file requires
    if len(out) < 110:
        out += bytes(110 - len(out))

    return bytes(out)


# ---------------------------------------------------------------------------
# log_sf2_structure
# ---------------------------------------------------------------------------

class TestLogSf2Structure(unittest.TestCase):
    def test_tiny_buffer_logs_too_small(self):
        with self.assertLogs("sidm2.sf2_diagnostics", level="DEBUG") as cm:
            sf2_diagnostics.log_sf2_structure("Tiny", b"\x00")
        self.assertTrue(any("too small" in msg.lower() for msg in cm.output))

    def test_valid_buffer_logs_load_and_magic(self):
        data = _build_valid_sf2()
        with self.assertLogs("sidm2.sf2_diagnostics", level="DEBUG") as cm:
            sf2_diagnostics.log_sf2_structure("Valid", data)
        joined = "\n".join(cm.output)
        self.assertIn("$0D7E", joined)
        self.assertIn("0x1337", joined)
        self.assertIn("VALID", joined)

    def test_invalid_magic_logs_invalid(self):
        data = bytearray(_build_valid_sf2())
        data[2:4] = b"\xAB\xCD"  # corrupt magic
        with self.assertLogs("sidm2.sf2_diagnostics", level="DEBUG") as cm:
            sf2_diagnostics.log_sf2_structure("Invalid", bytes(data))
        joined = "\n".join(cm.output)
        self.assertIn("INVALID", joined)


# ---------------------------------------------------------------------------
# log_block3_structure
# ---------------------------------------------------------------------------

class TestLogBlock3Structure(unittest.TestCase):
    def test_well_formed_two_tables_with_terminator(self):
        content = (
            _block3_table_descriptor(0x80, 1, "Instruments") +
            _block3_table_descriptor(0x81, 2, "Commands") +
            bytes([0xFF])
        )
        with self.assertLogs("sidm2.sf2_diagnostics", level="DEBUG") as cm:
            sf2_diagnostics.log_block3_structure(content)
        joined = "\n".join(cm.output)
        self.assertIn("Instruments", joined)
        self.assertIn("Commands", joined)
        self.assertIn("0xFF terminator", joined)
        self.assertIn("Total tables: 2", joined)

    def test_missing_terminator_reports_error(self):
        # Single descriptor, no 0xFF after
        content = _block3_table_descriptor(0x80, 1, "Instruments")
        with self.assertLogs("sidm2.sf2_diagnostics", level="DEBUG") as cm:
            sf2_diagnostics.log_block3_structure(content)
        joined = "\n".join(cm.output)
        self.assertIn("No 0xFF terminator", joined)

    def test_unknown_table_type_labeled(self):
        content = _block3_table_descriptor(0x42, 1, "Custom") + bytes([0xFF])
        with self.assertLogs("sidm2.sf2_diagnostics", level="DEBUG") as cm:
            sf2_diagnostics.log_block3_structure(content)
        joined = "\n".join(cm.output)
        self.assertIn("Unknown(0x42)", joined)


# ---------------------------------------------------------------------------
# log_block5_structure
# ---------------------------------------------------------------------------

class TestLogBlock5Structure(unittest.TestCase):
    def test_too_small_logs_too_small(self):
        with self.assertLogs("sidm2.sf2_diagnostics", level="DEBUG") as cm:
            sf2_diagnostics.log_block5_structure(b"\x00" * 5)
        joined = "\n".join(cm.output)
        self.assertIn("Too small", joined)

    def test_full_18_byte_header_parsed(self):
        body = bytes([3])                              # track_count = 3
        body += (0x1234).to_bytes(2, 'little')         # track_ol_ptr_lo
        body += (0x5678).to_bytes(2, 'little')         # track_ol_ptr_hi
        body += bytes([16])                            # seq_count
        body += (0x2222).to_bytes(2, 'little')         # seq_ptr_lo
        body += (0x3333).to_bytes(2, 'little')         # seq_ptr_hi
        body += (0x0040).to_bytes(2, 'little')         # ol_size
        body += (0xABCD).to_bytes(2, 'little')         # ol_track1
        body += (0x0100).to_bytes(2, 'little')         # seq_size
        body += (0x4000).to_bytes(2, 'little')         # seq00_addr
        self.assertEqual(len(body), 18)
        with self.assertLogs("sidm2.sf2_diagnostics", level="DEBUG") as cm:
            sf2_diagnostics.log_block5_structure(body)
        joined = "\n".join(cm.output)
        self.assertIn("Track count: 3", joined)
        self.assertIn("$1234", joined)
        self.assertIn("$5678", joined)
        self.assertIn("Sequence count: 16", joined)
        self.assertIn("$ABCD", joined)
        self.assertIn("$4000", joined)


# ---------------------------------------------------------------------------
# validate_sf2_file
# ---------------------------------------------------------------------------

class TestValidateSf2File(unittest.TestCase):
    def _write_tempfile(self, data: bytes) -> str:
        # delete=False so Windows can re-open it via filepath
        f = tempfile.NamedTemporaryFile(suffix=".sf2", delete=False)
        f.write(data)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return f.name

    def test_missing_file_logs_error(self):
        with self.assertLogs("sidm2.sf2_diagnostics", level="ERROR") as cm:
            sf2_diagnostics.validate_sf2_file(
                "__nonexistent_xyz_123__.sf2")
        joined = "\n".join(cm.output)
        self.assertIn("Could not read", joined)

    def test_too_small_file_logs_error(self):
        path = self._write_tempfile(b"\x00" * 50)
        with self.assertLogs("sidm2.sf2_diagnostics", level="ERROR") as cm:
            sf2_diagnostics.validate_sf2_file(path)
        joined = "\n".join(cm.output)
        self.assertIn("File too small", joined)

    def test_invalid_magic_logs_error(self):
        data = bytearray(_build_valid_sf2())
        data[2:4] = b"\xAB\xCD"
        path = self._write_tempfile(bytes(data))
        with self.assertLogs("sidm2.sf2_diagnostics", level="ERROR") as cm:
            sf2_diagnostics.validate_sf2_file(path)
        joined = "\n".join(cm.output)
        self.assertIn("Invalid magic", joined)

    def test_valid_sf2_passes_validation(self):
        path = self._write_tempfile(_build_valid_sf2())
        with self.assertLogs("sidm2.sf2_diagnostics", level="INFO") as cm:
            sf2_diagnostics.validate_sf2_file(path)
        joined = "\n".join(cm.output)
        self.assertIn("VALIDATION PASSED", joined)

    def test_missing_instruments_table_logs_error(self):
        path = self._write_tempfile(_build_valid_sf2(with_instruments=False))
        with self.assertLogs("sidm2.sf2_diagnostics", level="ERROR") as cm:
            sf2_diagnostics.validate_sf2_file(path)
        joined = "\n".join(cm.output)
        self.assertIn("Instruments table (0x80) MISSING", joined)
        self.assertIn("VALIDATION FAILED", joined)

    def test_missing_commands_table_logs_error(self):
        path = self._write_tempfile(_build_valid_sf2(with_commands=False))
        with self.assertLogs("sidm2.sf2_diagnostics", level="ERROR") as cm:
            sf2_diagnostics.validate_sf2_file(path)
        joined = "\n".join(cm.output)
        self.assertIn("Commands table (0x81) MISSING", joined)


if __name__ == "__main__":
    unittest.main(verbosity=2)
