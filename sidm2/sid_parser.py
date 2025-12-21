"""
SID file parser.

Version: 1.1.0 - Added custom error handling (v2.5.2)
"""

import struct
from typing import Tuple

from .models import PSIDHeader
from . import errors


class SIDParser:
    """Parser for PSID/RSID files"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        try:
            with open(filepath, 'rb') as f:
                self.data = f.read()
        except FileNotFoundError:
            raise errors.FileNotFoundError(
                path=filepath,
                context="SID file",
                suggestions=[
                    f"Check the file exists: ls {filepath}",
                    "Use absolute path instead of relative",
                    "Verify the file extension is .sid"
                ],
                docs_link="guides/TROUBLESHOOTING.md#1-file-not-found-issues"
            )
        except PermissionError:
            raise errors.PermissionError(
                operation="read",
                path=filepath,
                docs_link="guides/TROUBLESHOOTING.md#5-permission-problems"
            )
        except IOError as e:
            raise errors.ConversionError(
                stage="SID file loading",
                reason=f"I/O error: {e}",
                input_file=filepath,
                suggestions=[
                    "Check if file is locked by another program",
                    "Verify disk/network connection",
                    "Try copying file to a different location"
                ]
            )

        if len(self.data) < 124:
            raise errors.InvalidInputError(
                input_type="SID file",
                value=f"{len(self.data)} bytes",
                expected="at least 124 bytes (PSID header)",
                got=f"only {len(self.data)} bytes",
                suggestions=[
                    "Verify the file is a valid SID file",
                    "Check if the file was corrupted during download/transfer",
                    "Try re-downloading from the source"
                ],
                docs_link="guides/TROUBLESHOOTING.md#2-invalid-sid-files"
            )

    def parse_header(self) -> PSIDHeader:
        """Parse the PSID/RSID header"""
        try:
            magic = self.data[0:4].decode('ascii')
        except UnicodeDecodeError:
            raise errors.InvalidInputError(
                input_type="SID file header",
                value="corrupted magic bytes",
                expected="'PSID' or 'RSID' (ASCII)",
                got="non-ASCII bytes",
                suggestions=[
                    "Verify the file is a valid SID file",
                    "Check file integrity with a hex editor",
                    "Try re-downloading from the source"
                ],
                docs_link="guides/TROUBLESHOOTING.md#2-invalid-sid-files"
            )

        if magic not in ('PSID', 'RSID'):
            raise errors.InvalidInputError(
                input_type="SID file format",
                value=magic,
                expected="'PSID' or 'RSID'",
                got=f"'{magic}'",
                suggestions=[
                    "This may not be a SID file",
                    "File may be corrupted or in wrong format",
                    "Verify file extension is .sid"
                ],
                docs_link="reference/format-specification.md"
            )

        version = struct.unpack('>H', self.data[4:6])[0]
        data_offset = struct.unpack('>H', self.data[6:8])[0]
        load_address = struct.unpack('>H', self.data[8:10])[0]
        init_address = struct.unpack('>H', self.data[10:12])[0]
        play_address = struct.unpack('>H', self.data[12:14])[0]
        songs = struct.unpack('>H', self.data[14:16])[0]
        start_song = struct.unpack('>H', self.data[16:18])[0]
        speed = struct.unpack('>I', self.data[18:22])[0]

        # Strings are 32 bytes each, null-terminated
        name = self.data[22:54].split(b'\x00')[0].decode('latin-1')
        author = self.data[54:86].split(b'\x00')[0].decode('latin-1')
        copyright = self.data[86:118].split(b'\x00')[0].decode('latin-1')

        header = PSIDHeader(
            magic=magic,
            version=version,
            data_offset=data_offset,
            load_address=load_address,
            init_address=init_address,
            play_address=play_address,
            songs=songs,
            start_song=start_song,
            speed=speed,
            name=name,
            author=author,
            copyright=copyright
        )

        # Parse V2+ fields
        if version >= 2 and data_offset >= 0x7C:
            header.flags = struct.unpack('>H', self.data[118:120])[0]
            header.start_page = self.data[120]
            header.page_length = self.data[121]
            header.second_sid_address = self.data[122]
            header.third_sid_address = self.data[123]

        return header

    def get_c64_data(self, header: PSIDHeader) -> Tuple[bytes, int]:
        """Extract the C64 program data and determine load address"""
        if header.data_offset >= len(self.data):
            raise errors.InvalidInputError(
                input_type="SID file",
                value=f"data offset ${header.data_offset:04X}",
                expected=f"offset < ${len(self.data):04X} (file size)",
                got=f"offset ${header.data_offset:04X} (beyond end of file)",
                suggestions=[
                    "File may be corrupted or truncated",
                    "Header may contain invalid data offset",
                    "Try re-downloading from the source"
                ],
                docs_link="reference/format-specification.md"
            )

        c64_data = self.data[header.data_offset:]

        # If load_address is 0, first two bytes are the actual load address
        if header.load_address == 0:
            if len(c64_data) < 2:
                raise errors.InvalidInputError(
                    input_type="SID file",
                    value="missing load address",
                    expected="2-byte load address in file data",
                    got="insufficient data (< 2 bytes)",
                    suggestions=[
                        "File is corrupted or truncated",
                        "Data section is empty",
                        "Try re-downloading from the source"
                    ],
                    docs_link="reference/format-specification.md"
                )
            load_address = struct.unpack('<H', c64_data[0:2])[0]
            c64_data = c64_data[2:]
        else:
            load_address = header.load_address

        return c64_data, load_address
