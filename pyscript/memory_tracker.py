"""
Memory Access Tracker for SID Analysis

Tracks READ/WRITE/EXECUTE access patterns during SID playback to identify
code regions, data regions, and tables. Uses cpu6502_emulator for accurate
6502 execution simulation.

Features:
- Memory access type tracking (READ/WRITE/EXECUTE/OPERAND)
- Region detection (CODE/DATA/MIXED)
- Integration with cpu6502_emulator
- SID-specific initialization and playback
"""

from enum import IntFlag
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
import sys
import os
import logging

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sidm2.cpu6502_emulator import CPU6502Emulator
from pyscript.disasm6502 import Disassembler6502, OPCODES

logger = logging.getLogger(__name__)


class MemAccessType(IntFlag):
    """Memory access type flags (can be combined)"""
    UNTOUCHED = 0x00    # Never accessed
    READ = 0x01         # Read as data
    WRITE = 0x02        # Written to
    EXECUTE = 0x04      # Executed as code
    OPERAND = 0x08      # Used as operand byte (part of instruction)


@dataclass
class MemoryAccessMap:
    """
    Tracks memory access patterns for the entire 64KB address space.

    Compatible with SIDdecompiler's MemAccessMap.
    """

    def __init__(self):
        """Initialize empty access map"""
        # Access type for each address (64KB)
        self.access_map: List[int] = [MemAccessType.UNTOUCHED] * 65536

        # Track specific addresses for quick lookup
        self.read_addresses: Set[int] = set()
        self.write_addresses: Set[int] = set()
        self.execute_addresses: Set[int] = set()
        self.operand_addresses: Set[int] = set()

    def mark_read(self, address: int):
        """Mark address as read"""
        if 0 <= address < 65536:
            self.access_map[address] |= MemAccessType.READ
            self.read_addresses.add(address)

    def mark_write(self, address: int):
        """Mark address as written"""
        if 0 <= address < 65536:
            self.access_map[address] |= MemAccessType.WRITE
            self.write_addresses.add(address)

    def mark_execute(self, address: int):
        """Mark address as executed (opcode byte)"""
        if 0 <= address < 65536:
            self.access_map[address] |= MemAccessType.EXECUTE
            self.execute_addresses.add(address)

    def mark_operand(self, address: int):
        """Mark address as operand (instruction data)"""
        if 0 <= address < 65536:
            self.access_map[address] |= MemAccessType.OPERAND
            self.operand_addresses.add(address)

    def get_access_type(self, address: int) -> int:
        """Get access type flags for address"""
        if 0 <= address < 65536:
            return self.access_map[address]
        return MemAccessType.UNTOUCHED

    def is_code(self, address: int) -> bool:
        """Check if address was executed as code"""
        return bool(self.get_access_type(address) & MemAccessType.EXECUTE)

    def is_data(self, address: int) -> bool:
        """Check if address was read (but not executed)"""
        access = self.get_access_type(address)
        return bool(access & MemAccessType.READ) and not bool(access & MemAccessType.EXECUTE)

    def is_untouched(self, address: int) -> bool:
        """Check if address was never accessed"""
        return self.get_access_type(address) == MemAccessType.UNTOUCHED

    def get_region_type(self, address: int) -> str:
        """
        Get region type for address (compatible with SIDdecompiler).

        Returns:
            "CODE", "DATA", or "UNKNOWN"
        """
        access = self.get_access_type(address)

        if access & (MemAccessType.EXECUTE | MemAccessType.OPERAND):
            return "CODE"
        elif access == MemAccessType.UNTOUCHED:
            return "UNKNOWN"
        else:
            return "DATA"

    def get_regions(self, start: int, end: int) -> List[Tuple[int, int, str]]:
        """
        Get contiguous memory regions in range.

        Args:
            start: Start address
            end: End address (exclusive)

        Returns:
            List of (start_addr, size, type) tuples
        """
        regions = []
        current_type = None
        current_start = None

        for addr in range(start, end):
            region_type = self.get_region_type(addr)

            if region_type != current_type:
                # Save previous region
                if current_type is not None:
                    size = addr - current_start
                    regions.append((current_start, size, current_type))

                # Start new region
                current_type = region_type
                current_start = addr

        # Save final region
        if current_type is not None:
            size = end - current_start
            regions.append((current_start, size, current_type))

        return regions

    def format_map_line(self, address: int, bytes_per_line: int = 64) -> str:
        """
        Format memory map line (compatible with SIDdecompiler output).

        Args:
            address: Starting address (should be multiple of bytes_per_line)
            bytes_per_line: Number of bytes per line

        Returns:
            Formatted line like: "$1000: xoo???xoxooxoxoxox..."
        """
        chars = []
        for i in range(bytes_per_line):
            addr = address + i
            if addr >= 65536:
                break

            access = self.get_access_type(addr)

            # Format: x=execute, r=read, w=write, +=read+write, o=operand, ?=untouched
            if access & MemAccessType.EXECUTE:
                chars.append('x')
            elif access & MemAccessType.OPERAND:
                chars.append('o')
            elif (access & MemAccessType.READ) and (access & MemAccessType.WRITE):
                chars.append('+')
            elif access & MemAccessType.WRITE:
                chars.append('w')
            elif access & MemAccessType.READ:
                chars.append('r')
            else:
                chars.append('?')

        return f"${address:04X}: {''.join(chars)}"


class MemoryTracker:
    """
    Tracks memory access during SID execution using CPU emulation.

    Integrates with cpu6502_emulator to monitor all memory operations.
    """

    def __init__(self, cpu: CPU6502Emulator):
        """
        Initialize memory tracker with CPU emulator.

        Args:
            cpu: CPU6502 emulator instance
        """
        self.cpu = cpu
        self.access_map = MemoryAccessMap()
        self.last_pc = 0

    def track_instruction(self):
        """
        Track current instruction execution.

        Should be called before each instruction execution.
        Marks PC as execute and operand bytes as operand.
        """
        pc = self.cpu.pc

        # Get opcode
        if pc < len(self.cpu.mem):
            opcode_byte = self.cpu.mem[pc]

            # Mark opcode as executed
            self.access_map.mark_execute(pc)

            # Get instruction length
            if opcode_byte in OPCODES:
                opcode = OPCODES[opcode_byte]

                # Mark operand bytes
                for i in range(1, opcode.bytes):
                    if pc + i < 65536:
                        self.access_map.mark_operand(pc + i)

        self.last_pc = pc

    def track_read(self, address: int):
        """Track memory read"""
        self.access_map.mark_read(address)

    def track_write(self, address: int):
        """Track memory write"""
        self.access_map.mark_write(address)

    def get_map(self) -> MemoryAccessMap:
        """Get access map"""
        return self.access_map


class SIDMemoryAnalyzer:
    """
    Analyzes SID file by executing and tracking memory access.

    High-level interface for SID memory analysis compatible with SIDdecompiler.
    """

    def __init__(self):
        """Initialize analyzer"""
        self.cpu = None
        self.tracker = None

    def analyze_sid(self,
                   sid_data: bytes,
                   init_addr: int,
                   play_addr: int,
                   load_addr: int,
                   data_size: int,
                   ticks: int = 3000) -> MemoryAccessMap:
        """
        Analyze SID file by executing init and play routines.

        Args:
            sid_data: Raw SID music data (after header)
            init_addr: Init routine address
            play_addr: Play routine address
            load_addr: Load address for data
            data_size: Size of data
            ticks: Number of play() calls (default: 3000 = 60s at 50Hz)

        Returns:
            MemoryAccessMap with access patterns
        """
        # Create CPU emulator
        self.cpu = CPU6502Emulator()

        # Load SID data into memory
        for i in range(min(data_size, len(sid_data))):
            if load_addr + i < 65536:
                self.cpu.mem[load_addr + i] = sid_data[i]

        # Create tracker
        self.tracker = MemoryTracker(self.cpu)

        # Execute init routine
        logger.info(f"Calling init routine at ${init_addr:04X}")
        self._execute_routine(init_addr, max_cycles=100000)

        # Execute play routine multiple times
        logger.info(f"Calling play routine {ticks} times at ${play_addr:04X}")
        for tick in range(ticks):
            self._execute_routine(play_addr, max_cycles=10000)

            # Progress reporting
            if tick % 500 == 0 and tick > 0:
                logger.debug(f"Progress: {tick}/{ticks} ticks")

        logger.info(f"Analysis complete: {ticks} ticks executed")

        return self.tracker.get_map()

    def _execute_routine(self, address: int, max_cycles: int = 100000):
        """
        Execute subroutine at address until RTS.

        Args:
            address: Routine entry point
            max_cycles: Maximum cycles to execute
        """
        # Set up for JSR
        self.cpu.pc = address
        self.cpu.sp = 0xFF  # Reset stack

        # Push return address (0x0000) for RTS
        self.cpu.push(0x00)  # High byte
        self.cpu.push(0x00)  # Low byte

        cycles = 0
        while cycles < max_cycles:
            # Track instruction before execution
            self.tracker.track_instruction()

            # Get current opcode
            if self.cpu.pc >= len(self.cpu.mem):
                logger.warning(f"PC out of range: ${self.cpu.pc:04X}")
                break

            opcode = self.cpu.mem[self.cpu.pc]

            # Check for RTS to return address 0x0000 (we're done)
            if opcode == 0x60:  # RTS
                # Execute the RTS
                self.cpu.run_instruction()

                # Check if we returned to our sentinel (0x0000)
                if self.cpu.pc == 0x0000 or self.cpu.pc == 0x0001:
                    break

            # Execute instruction
            try:
                self.cpu.run_instruction()
                cycles += 1
            except Exception as e:
                logger.error(
                    f"Execution error at ${self.cpu.pc:04X}: {e}\n"
                    f"  Suggestion: 6502 emulation error during routine execution\n"
                    f"  Check: May be invalid opcode or illegal instruction\n"
                    f"  Try: Enable debug logging to see instruction trace\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#emulation-errors"
                )
                break

        if cycles >= max_cycles:
            logger.warning(f"Routine at ${address:04X} hit max cycles ({max_cycles})")


def main():
    """Test memory tracker"""
    # Simple test: track a few instructions
    cpu = CPU6502Emulator()

    # Load simple program: LDA #$00, STA $D400, RTS
    program = bytes([0xA9, 0x00, 0x8D, 0x00, 0xD4, 0x60])
    for i, byte in enumerate(program):
        cpu.mem[0x1000 + i] = byte

    tracker = MemoryTracker(cpu)
    cpu.pc = 0x1000

    # Execute instructions
    for _ in range(10):
        tracker.track_instruction()

        # Check for RTS
        if cpu.mem[cpu.pc] == 0x60:
            break

        cpu.run_instruction()

    # Show results
    access_map = tracker.get_map()

    print("Memory Access Map:")
    print(access_map.format_map_line(0x1000, 16))
    print(access_map.format_map_line(0xD400, 16))

    print("\nRegions:")
    regions = access_map.get_regions(0x1000, 0x1010)
    for start, size, rtype in regions:
        print(f"  ${start:04X}-${start+size-1:04X}: {rtype} ({size} bytes)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    main()
