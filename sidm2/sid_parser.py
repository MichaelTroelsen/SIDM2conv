"""
SID file parser.
"""

import struct
from typing import Tuple

from .models import PSIDHeader
from .exceptions import SIDParseError, InvalidSIDFileError


class SIDParser:
    """Parser for PSID/RSID files"""

    def __init__(self, filepath: str):
        self.filepath = filepath
        try:
            with open(filepath, 'rb') as f:
                self.data = f.read()
        except FileNotFoundError:
            raise SIDParseError(f"SID file not found: {filepath}")
        except PermissionError:
            raise SIDParseError(f"Permission denied reading: {filepath}")
        except IOError as e:
            raise SIDParseError(f"Error reading SID file: {e}")

        if len(self.data) < 124:
            raise InvalidSIDFileError(f"File too small to be valid SID: {len(self.data)} bytes")

    def parse_header(self) -> PSIDHeader:
        """Parse the PSID/RSID header"""
        try:
            magic = self.data[0:4].decode('ascii')
        except UnicodeDecodeError:
            raise InvalidSIDFileError("Invalid magic bytes in SID file")

        if magic not in ('PSID', 'RSID'):
            raise InvalidSIDFileError(f"Invalid SID file magic: {magic}")

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
            raise InvalidSIDFileError(f"Data offset {header.data_offset} beyond file size")

        c64_data = self.data[header.data_offset:]

        # If load_address is 0, first two bytes are the actual load address
        if header.load_address == 0:
            if len(c64_data) < 2:
                raise InvalidSIDFileError("No load address in file")
            load_address = struct.unpack('<H', c64_data[0:2])[0]
            c64_data = c64_data[2:]
        else:
            load_address = header.load_address

        return c64_data, load_address
