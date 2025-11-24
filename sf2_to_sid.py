#!/usr/bin/env python3
"""
SF2 to PSID Converter

Converts SID Factory II (.sf2) project files to Commodore 64 PSID format.
This enables round-trip testing: SID → SF2 → SID → WAV comparison.

The SF2 file contains:
- Driver code (6502 assembly for playback)
- Music data (sequences, instruments, tables)
- Metadata (title, author, copyright)

The PSID file format wraps this into a playable SID file with header.

Usage:
    python sf2_to_sid.py input.sf2 output.sid
    python sf2_to_sid.py SF2/Angular_d11_final.sf2 SID/Angular_converted.sid
"""

import os
import sys
import struct
import logging
from pathlib import Path
from typing import Tuple, Optional

__version__ = "1.0.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class PSIDHeader:
    """PSID v2 file header structure"""

    def __init__(
        self,
        load_address: int,
        init_address: int,
        play_address: int,
        songs: int = 1,
        start_song: int = 1,
        title: str = "",
        author: str = "",
        copyright: str = "",
        speed: int = 0,  # 0 = 50Hz (PAL)
        sid_model: int = 0,  # 0 = 6581, 1 = 8580
    ):
        self.magic = b'PSID'
        self.version = 2
        self.data_offset = 0x007C  # Header is 124 bytes
        self.load_address = load_address
        self.init_address = init_address
        self.play_address = play_address
        self.songs = songs
        self.start_song = start_song
        self.speed = speed
        self.title = title[:32].ljust(32, '\x00')
        self.author = author[:32].ljust(32, '\x00')
        self.copyright = copyright[:32].ljust(32, '\x00')

        # Flags (bits for SID model, video standard, etc.)
        # Bit 0-1: SID model (0=6581, 1=8580, 2=both, 3=both)
        # Bit 2-3: Video standard (0=unknown, 1=PAL, 2=NTSC, 3=both)
        self.flags = sid_model | (1 << 2)  # PAL

        self.start_page = 0
        self.page_length = 0
        self.second_sid_address = 0
        self.third_sid_address = 0

    def to_bytes(self) -> bytes:
        """Convert header to binary format"""
        header = bytearray(124)

        # Magic number and version
        header[0:4] = self.magic
        struct.pack_into('>H', header, 0x04, self.version)
        struct.pack_into('>H', header, 0x06, self.data_offset)

        # Addresses
        struct.pack_into('>H', header, 0x08, self.load_address)
        struct.pack_into('>H', header, 0x0A, self.init_address)
        struct.pack_into('>H', header, 0x0C, self.play_address)

        # Song info
        struct.pack_into('>H', header, 0x0E, self.songs)
        struct.pack_into('>H', header, 0x10, self.start_song)

        # Speed flags (1 bit per song, 0=60Hz, 1=50Hz)
        struct.pack_into('>I', header, 0x12, self.speed)

        # Strings (32 bytes each, null-padded)
        header[0x16:0x36] = self.title.encode('latin-1', errors='replace')[:32].ljust(32, b'\x00')
        header[0x36:0x56] = self.author.encode('latin-1', errors='replace')[:32].ljust(32, b'\x00')
        header[0x56:0x76] = self.copyright.encode('latin-1', errors='replace')[:32].ljust(32, b'\x00')

        # Flags and SID addresses
        struct.pack_into('>H', header, 0x76, self.flags)
        header[0x78] = self.start_page
        header[0x79] = self.page_length
        header[0x7A] = self.second_sid_address
        header[0x7B] = self.third_sid_address

        return bytes(header)


class SF2File:
    """Represents a SID Factory II (.sf2) file"""

    def __init__(self, data: bytes):
        self.data = data
        self.load_address = None
        self.init_address = None
        self.play_address = None
        self.title = ""
        self.author = ""
        self.copyright = ""

        self._parse()

    def _parse(self):
        """Parse SF2 file structure"""
        if len(self.data) < 2:
            raise ValueError("SF2 file too short")

        # SF2 files are PRG format: first 2 bytes are load address (little-endian)
        self.load_address = struct.unpack('<H', self.data[0:2])[0]

        # Extract metadata from auxiliary data section if present
        # Look for metadata marker (null-terminated strings at end of file)
        self._extract_metadata()

        # Determine init and play addresses from driver
        self._detect_driver_addresses()

        logger.debug(f"  Load address: ${self.load_address:04X}")
        logger.debug(f"  Init address: ${self.init_address:04X}")
        logger.debug(f"  Play address: ${self.play_address:04X}")
        logger.debug(f"  Data size: {len(self.data) - 2} bytes")

    def _extract_metadata(self):
        """Extract title, author, copyright from SF2 auxiliary data"""
        # SF2 files store metadata as null-terminated strings near the end
        # Format: [title\0][author\0][copyright\0]
        # Look for string data in last 256 bytes

        search_start = max(0, len(self.data) - 512)
        search_data = self.data[search_start:]

        strings = []
        current_str = bytearray()

        for i, byte in enumerate(search_data):
            if byte == 0:
                if current_str:
                    try:
                        # Try to decode as ASCII/Latin-1
                        decoded = current_str.decode('latin-1', errors='ignore').strip()
                        if decoded and len(decoded) > 3:  # Reasonable string
                            strings.append(decoded)
                    except:
                        pass
                    current_str = bytearray()
            elif 0x20 <= byte <= 0x7E:  # Printable ASCII
                current_str.append(byte)
            else:
                current_str = bytearray()  # Reset on non-printable

        # Take last 3 strings as title/author/copyright
        if len(strings) >= 3:
            self.title = strings[-3]
            self.author = strings[-2]
            self.copyright = strings[-1]
            logger.debug(f"  Found metadata: {self.title} / {self.author} / {self.copyright}")
        elif len(strings) >= 2:
            self.title = strings[-2]
            self.author = strings[-1]
        elif len(strings) >= 1:
            self.title = strings[-1]

    def _detect_driver_addresses(self):
        """Detect init and play addresses from driver code"""
        # SF2 drivers follow standard patterns:
        # - Driver 11: Init at offset +0, Play at offset +3
        # - NP20: Init at offset +0, Play at offset +0xA1

        # The SF2 file format stores the driver starting at load_address
        # For PSID export, init/play offsets are added to the driver address

        # Default: Driver 11 style (most common)
        init_offset = 0
        play_offset = 3

        # Try to detect NP20 by looking for specific code patterns
        if len(self.data) > 0xA3:
            # Check if there's a JSR or JMP around offset +0xA1
            offset = 0xA1 + 2  # Account for load address bytes
            if offset < len(self.data):
                opcode = self.data[offset]
                if opcode in (0x20, 0x4C):  # JSR or JMP
                    play_offset = 0xA1
                    logger.debug("  Detected NP20-style driver")

        self.init_address = self.load_address + init_offset
        self.play_address = self.load_address + play_offset

    def get_prg_data(self) -> bytes:
        """Get raw PRG data (including load address)"""
        return self.data

    def get_c64_data(self) -> bytes:
        """Get C64 memory data (without load address bytes)"""
        return self.data[2:]


def convert_sf2_to_sid(sf2_path: str, sid_path: str) -> bool:
    """
    Convert SF2 file to PSID format

    Args:
        sf2_path: Path to input .sf2 file
        sid_path: Path to output .sid file

    Returns:
        True if conversion successful
    """
    logger.info(f"Converting SF2 to PSID...")
    logger.info(f"  Input: {sf2_path}")
    logger.info(f"  Output: {sid_path}")

    # Read SF2 file
    with open(sf2_path, 'rb') as f:
        sf2_data = f.read()

    sf2 = SF2File(sf2_data)

    # Create PSID header
    header = PSIDHeader(
        load_address=sf2.load_address,
        init_address=sf2.init_address,
        play_address=sf2.play_address,
        title=sf2.title,
        author=sf2.author,
        copyright=sf2.copyright
    )

    # Build PSID file: [PSID header][C64 data]
    psid_data = header.to_bytes() + sf2.get_c64_data()

    # Write PSID file
    with open(sid_path, 'wb') as f:
        f.write(psid_data)

    logger.info(f"  Created: {sid_path} ({len(psid_data):,} bytes)")
    logger.info(f"  Header: 124 bytes")
    logger.info(f"  Data: {len(sf2.get_c64_data()):,} bytes")
    logger.info(f"  Load: ${sf2.load_address:04X}")
    logger.info(f"  Init: ${sf2.init_address:04X}")
    logger.info(f"  Play: ${sf2.play_address:04X}")

    if sf2.title:
        logger.info(f"  Title: {sf2.title}")
    if sf2.author:
        logger.info(f"  Author: {sf2.author}")

    return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert SID Factory II (.sf2) to PSID (.sid) format'
    )
    parser.add_argument('input_sf2', help='Input SF2 file')
    parser.add_argument('output_sid', help='Output SID file')
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not os.path.exists(args.input_sf2):
        logger.error(f"Input file not found: {args.input_sf2}")
        sys.exit(1)

    try:
        success = convert_sf2_to_sid(args.input_sf2, args.output_sid)
        if success:
            logger.info("Conversion complete!")
        else:
            logger.error("Conversion failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
