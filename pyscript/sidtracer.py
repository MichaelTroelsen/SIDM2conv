"""
SID Tracer - Executes SID files and captures register writes

This module provides the SIDTracer class which uses the CPU6502Emulator
to execute SID files and capture SID register writes frame-by-frame.

Part of the Python SIDwinder replacement project (v2.8.0).
"""

from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sidm2.cpu6502_emulator import CPU6502Emulator, SIDRegisterWrite

logger = logging.getLogger(__name__)


@dataclass
class SIDHeader:
    """PSID/RSID header information."""
    version: int
    data_offset: int
    load_address: int
    init_address: int
    play_address: int
    songs: int
    start_song: int
    speed: int
    name: str
    author: str
    released: str
    flags: int
    start_page: int = 0
    page_length: int = 0
    sid_model: int = 0

    @property
    def is_rsid(self) -> bool:
        """Check if this is RSID format."""
        return self.version >= 2 and (self.flags & 0x02)

    @property
    def is_basic(self) -> bool:
        """Check if BASIC flag is set."""
        return bool(self.flags & 0x02)


@dataclass
class TraceData:
    """Complete trace output data."""
    init_writes: List[SIDRegisterWrite] = field(default_factory=list)
    frame_writes: List[List[SIDRegisterWrite]] = field(default_factory=list)
    frames: int = 0
    cycles: int = 0
    header: Optional[SIDHeader] = None


class SIDTracer:
    """Executes SID and captures register writes frame-by-frame."""

    def __init__(self, sid_path: Path, verbose: int = 0):
        """Initialize tracer with SID file.

        Args:
            sid_path: Path to SID file
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)
        """
        self.sid_path = Path(sid_path)
        self.verbose = verbose
        self.header: Optional[SIDHeader] = None
        self.sid_data: Optional[bytes] = None
        self.cpu: Optional[CPU6502Emulator] = None

        # Parse SID file
        if not self._parse_sid_file():
            raise ValueError(f"Failed to parse SID file: {sid_path}")

    def _parse_sid_file(self) -> bool:
        """Parse SID file header and data.

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(self.sid_path, 'rb') as f:
                data = f.read()

            # Check magic bytes
            if data[:4] not in (b'PSID', b'RSID'):
                logger.error(
                    f"Invalid SID file: {self.sid_path}\n"
                    f"  Suggestion: File does not have PSID or RSID magic bytes\n"
                    f"  Check: Verify file is valid SID format\n"
                    f"  Try: Download from HVSC or csdb.dk if corrupted\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#invalid-sid-files"
                )
                return False

            # Parse header
            version = (data[4] << 8) | data[5]
            data_offset = (data[6] << 8) | data[7]
            load_address = (data[8] << 8) | data[9]
            init_address = (data[10] << 8) | data[11]
            play_address = (data[12] << 8) | data[13]
            songs = (data[14] << 8) | data[15]
            start_song = (data[16] << 8) | data[17]
            speed = (data[18] << 24) | (data[19] << 16) | (data[20] << 8) | data[21]

            # Extract strings (null-terminated, max 32 bytes)
            name = data[22:54].split(b'\x00')[0].decode('latin-1', errors='replace')
            author = data[54:86].split(b'\x00')[0].decode('latin-1', errors='replace')
            released = data[86:118].split(b'\x00')[0].decode('latin-1', errors='replace')

            # Additional fields for v2+
            flags = 0
            start_page = 0
            page_length = 0
            sid_model = 0

            if version >= 2 and len(data) >= 124:
                flags = (data[118] << 8) | data[119]
                start_page = data[120]
                page_length = data[121]
                sid_model = data[123]

            self.header = SIDHeader(
                version=version,
                data_offset=data_offset,
                load_address=load_address,
                init_address=init_address,
                play_address=play_address,
                songs=songs,
                start_song=start_song,
                speed=speed,
                name=name.strip(),
                author=author.strip(),
                released=released.strip(),
                flags=flags,
                start_page=start_page,
                page_length=page_length,
                sid_model=sid_model
            )

            # Extract music data
            self.sid_data = data[data_offset:]

            # If load address is 0, get it from first two bytes of data
            if self.header.load_address == 0:
                if len(self.sid_data) < 2:
                    logger.error(
                        "SID data too short\n"
                        "  Suggestion: SID data section is missing embedded load address\n"
                        "  Check: File may be truncated or corrupted\n"
                        "  Try: Re-download file or verify integrity\n"
                        "  See: docs/guides/TROUBLESHOOTING.md#sid-data-too-short"
                    )
                    return False
                self.header.load_address = self.sid_data[0] | (self.sid_data[1] << 8)
                self.sid_data = self.sid_data[2:]  # Skip load address bytes

            if self.verbose >= 1:
                logger.info(f"Parsed SID: {self.header.name}")
                logger.info(f"  Author: {self.header.author}")
                logger.info(f"  Load: ${self.header.load_address:04X}")
                logger.info(f"  Init: ${self.header.init_address:04X}")
                logger.info(f"  Play: ${self.header.play_address:04X}")

            return True

        except Exception as e:
            logger.error(f"Error parsing SID file: {e}")
            return False

    def _load_sid_data(self):
        """Load SID data into CPU memory."""
        if not self.sid_data or not self.header:
            raise ValueError("SID not parsed")

        addr = self.header.load_address
        for byte in self.sid_data:
            self.cpu.mem[addr] = byte
            addr += 1
            if addr > 0xFFFF:
                break

        if self.verbose >= 2:
            logger.debug(f"Loaded {len(self.sid_data)} bytes at ${self.header.load_address:04X}")

    def _execute_init(self) -> List[SIDRegisterWrite]:
        """Execute init routine and capture SID writes.

        Returns:
            List of SID register writes during init
        """
        if not self.header:
            raise ValueError("SID not parsed")

        # Set up init call
        init_addr = self.header.init_address
        song = self.header.start_song - 1  # Convert to 0-based

        # Reset CPU
        self.cpu.reset(pc=init_addr, a=song, x=0, y=0)
        self.cpu.current_frame = 0
        self.cpu.sid_writes.clear()

        # Execute init routine (with timeout)
        max_instructions = 100000  # Reasonable limit
        instruction_count = 0

        try:
            # Use CPU's run_until_return for cleaner execution
            instruction_count = self.cpu.run_until_return()
        except Exception as e:
            logger.error(f"Error during init: {e}")
            raise

        if instruction_count >= max_instructions:
            logger.warning(f"Init routine timeout after {max_instructions} instructions")

        # Return captured writes
        init_writes = list(self.cpu.sid_writes)

        if self.verbose >= 2:
            logger.debug(f"Init executed: {instruction_count} instructions, {len(init_writes)} SID writes")

        return init_writes

    def _execute_frame(self, frame_num: int) -> List[SIDRegisterWrite]:
        """Execute play routine for one frame and capture SID writes.

        Args:
            frame_num: Frame number (for tracking)

        Returns:
            List of SID register writes during this frame
        """
        if not self.header:
            raise ValueError("SID not parsed")

        # Clear previous frame's writes
        self.cpu.sid_writes.clear()
        self.cpu.current_frame = frame_num

        # Set up play call
        play_addr = self.header.play_address

        # Save current PC
        saved_pc = self.cpu.pc

        # Call play routine
        self.cpu.pc = play_addr

        # Execute play routine (with timeout)
        try:
            # Use CPU's run_until_return for cleaner execution
            instruction_count = self.cpu.run_until_return()
        except Exception as e:
            logger.error(f"Error during play frame {frame_num}: {e}")
            raise

        # Restore PC
        self.cpu.pc = saved_pc

        # Return captured writes for this frame
        frame_writes = list(self.cpu.sid_writes)

        if self.verbose >= 2 and frame_num % 100 == 0:
            logger.debug(f"Frame {frame_num}: {instruction_count} instructions, {len(frame_writes)} SID writes")

        return frame_writes

    def trace(self, frames: int = 1500) -> TraceData:
        """Execute SID for N frames and return trace data.

        Args:
            frames: Number of frames to execute (default: 1500 = 30 sec @ 50Hz)

        Returns:
            TraceData with init writes + per-frame writes
        """
        if not self.header or not self.sid_data:
            raise ValueError("SID not parsed")

        # Create CPU emulator with write capture enabled
        self.cpu = CPU6502Emulator(capture_writes=True)

        # Load SID data into memory
        self._load_sid_data()

        if self.verbose >= 1:
            logger.info(f"Executing init routine...")

        # Execute init and capture writes
        init_writes = self._execute_init()

        if self.verbose >= 1:
            logger.info(f"  Init: {len(init_writes)} SID register writes")
            logger.info(f"Executing {frames} frames...")

        # Execute frames and capture writes
        frame_writes = []
        for frame_num in range(1, frames + 1):
            writes = self._execute_frame(frame_num)
            frame_writes.append(writes)

            if self.verbose >= 1 and frame_num % 500 == 0:
                logger.info(f"  Frame {frame_num}/{frames}")

        if self.verbose >= 1:
            total_writes = sum(len(fw) for fw in frame_writes)
            logger.info(f"Complete: {frames} frames, {total_writes} total SID writes")

        return TraceData(
            init_writes=init_writes,
            frame_writes=frame_writes,
            frames=frames,
            cycles=self.cpu.cycles,
            header=self.header
        )


if __name__ == "__main__":
    # Simple test
    import sys

    if len(sys.argv) < 2:
        print("Usage: python sidtracer.py <sid_file> [frames]")
        sys.exit(1)

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    sid_path = Path(sys.argv[1])
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    tracer = SIDTracer(sid_path, verbose=1)
    trace_data = tracer.trace(frames)

    print(f"\nInit writes: {len(trace_data.init_writes)}")
    print(f"Frame writes: {len(trace_data.frame_writes)}")
    print(f"Total cycles: {trace_data.cycles}")
