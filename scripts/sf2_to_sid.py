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

# Import custom error handling
try:
    from sidm2 import errors
    from sidm2.logging_config import setup_logging, get_logger, configure_from_args, PerformanceLogger
except ImportError:
    # Fallback if running standalone
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
    from sidm2 import errors
    from sidm2.logging_config import setup_logging, get_logger, configure_from_args, PerformanceLogger

__version__ = "1.1.0"

# Get module logger (configured via configure_from_args in main)
logger = get_logger(__name__)


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
            raise errors.InvalidInputError(
                input_type="SF2 file",
                value=f"{len(self.data)} bytes",
                expected="at least 2 bytes (PRG load address)",
                got=f"only {len(self.data)} bytes",
                suggestions=[
                    "Verify the file is a valid SF2 file",
                    "Check if the file was corrupted during download/transfer",
                    "Try re-exporting from SID Factory II"
                ]
            )

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
        """Parse SF2 header blocks to extract init/play addresses.

        SF2 files use a block-based header system after the magic number (0x1337).
        Block 2 (DriverCommon, ID=2) contains the init/play/stop addresses.

        File structure:
          Offset 0-1: Load address (little-endian)
          Offset 2-3: Magic number 0x1337 (0x37 0x13)
          Offset 4+:  Header blocks (ID, size, data)

        Block 2 (DriverCommon) format:
          Offset 0-1: Init address
          Offset 2-3: Stop address
          Offset 4-5: Play address
          (+ 34 more bytes of driver state addresses)
        """
        # Method 1: Parse Block 2 (DriverCommon) header - most reliable
        try:
            # Check magic number at offset 2
            if len(self.data) >= 4:
                magic = struct.unpack('<H', self.data[2:4])[0]
                if magic == 0x1337:
                    # Valid SF2 file - parse header blocks
                    offset = 4
                    while offset + 2 < len(self.data):
                        block_id = self.data[offset]
                        if block_id == 0xFF:  # End marker
                            break

                        block_size = self.data[offset + 1]
                        block_data_offset = offset + 2

                        if block_id == 2:  # DriverCommon block
                            if block_data_offset + 6 <= len(self.data):
                                self.init_address = struct.unpack('<H', self.data[block_data_offset:block_data_offset+2])[0]
                                # Skip stop address at +2/+3
                                self.play_address = struct.unpack('<H', self.data[block_data_offset+4:block_data_offset+6])[0]
                                logger.debug(f"  Parsed Block 2 (DriverCommon): init=${self.init_address:04X}, play=${self.play_address:04X}")
                                return

                        offset += 2 + block_size
        except Exception as e:
            logger.warning(f"  Failed to parse SF2 header blocks: {e}")

        # Method 2: Fallback - Check load address (OLD LOGIC)
        # This is kept for compatibility with files that don't have proper headers
        logger.debug(f"  No Block 2 found, using fallback address detection")

        if self.load_address == 0x0D7E:
            # Laxity driver detected via load address
            self.init_address = 0x0D7E
            self.play_address = 0x0D81
            logger.debug(f"  Detected Laxity driver (load=$0D7E): init=$0D7E, play=$0D81")
            return

        # Check for "Laxity" string in header (backup method)
        if len(self.data) >= 20:
            header_text = self.data[2:50]
            if b'Laxity' in header_text:
                self.init_address = 0x0D80
                self.play_address = 0x0D83
                logger.debug(f"  Detected Laxity driver (string match): init=$0D80, play=$0D83")
                return

        # Default: Driver 11 entry points
        self.init_address = 0x1000
        self.play_address = 0x1006
        logger.debug(f"  Using Driver 11 default entry points: init=$1000, play=$1006")

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
    if not os.path.exists(sf2_path):
        raise errors.FileNotFoundError(
            path=sf2_path,
            context="input SF2 file",
            suggestions=[
                f"Check the file path: {sf2_path}",
                "Use absolute path instead of relative",
                "Verify the file extension is .sf2"
            ],
            docs_link="guides/TROUBLESHOOTING.md#1-file-not-found-issues"
        )

    try:
        with open(sf2_path, 'rb') as f:
            sf2_data = f.read()
    except IOError as e:
        raise errors.PermissionError(
            operation="read",
            path=sf2_path,
            suggestions=[
                "Check file permissions",
                "Ensure the file is not open in another program",
                "Try running with administrator privileges (Windows)"
            ]
        )

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
    c64_data = sf2.get_c64_data()
    psid_data = header.to_bytes() + c64_data

    # Debug: Show first bytes of data
    logger.info(f"  DEBUG: SF2 file size: {len(sf2.data):,} bytes")
    logger.info(f"  DEBUG: SF2 first 16 bytes: {' '.join(f'{b:02x}' for b in sf2.data[:16])}")
    logger.info(f"  DEBUG: C64 data size: {len(c64_data):,} bytes")
    logger.info(f"  DEBUG: C64 first 16 bytes: {' '.join(f'{b:02x}' for b in c64_data[:16])}")

    # Write PSID file
    try:
        # Create output directory if needed
        output_dir = os.path.dirname(sid_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        with open(sid_path, 'wb') as f:
            f.write(psid_data)
    except IOError as e:
        raise errors.PermissionError(
            operation="write",
            path=sid_path,
            suggestions=[
                "Check if you have write permissions for the output directory",
                "Ensure the output file is not open in another program",
                "Try a different output location"
            ]
        )

    logger.info(f"  Created: {sid_path} ({len(psid_data):,} bytes)")
    logger.info(f"  Header: 124 bytes")
    logger.info(f"  Data: {len(c64_data):,} bytes")
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

    # Enhanced logging arguments (v2.0.0)
    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=2,
        help='Increase verbosity (-v=INFO, -vv=DEBUG). Default: INFO level'
    )
    parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Quiet mode (errors only)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Debug mode (maximum verbosity, same as -vv)'
    )
    parser.add_argument(
        '--log-file',
        type=str,
        help='Write logs to file (with automatic rotation)'
    )
    parser.add_argument(
        '--log-json',
        action='store_true',
        help='Use JSON log format (for log aggregation tools)'
    )

    args = parser.parse_args()

    # Configure enhanced logging system (v2.0.0)
    configure_from_args(args)

    try:
        with PerformanceLogger(logger, f"SF2 to SID conversion: {args.input_sf2}"):
            success = convert_sf2_to_sid(args.input_sf2, args.output_sid)

        if success:
            logger.info("Conversion complete!")
        else:
            logger.error(
                "Conversion failed\n"
                "  Suggestion: SF2 to SID conversion did not complete successfully\n"
                "  Check: Review error messages above for specific failures\n"
                "  Try: Verify SF2 file format is valid and complete\n"
                "  See: docs/guides/TROUBLESHOOTING.md#conversion-failures"
            )
            sys.exit(1)
    except errors.SIDMError as e:
        # Custom error - already has helpful formatting
        print(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(
            f"Unexpected error: {e}\n"
            f"  Suggestion: SF2 to SID conversion encountered unexpected error\n"
            f"  Check: Review error trace for specific issue\n"
            f"  Try: Enable debug mode (--debug) for detailed logging\n"
            f"  See: docs/guides/TROUBLESHOOTING.md#unexpected-errors"
        )
        if args.debug or (hasattr(args, 'verbose') and args.verbose >= 3):
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
