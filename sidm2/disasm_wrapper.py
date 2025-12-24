"""
6502 Disassembler Integration for SID Conversion Pipeline - Phase 2

Integrates pyscript/disasm6502.py into the conversion pipeline as Step 8.5.
Disassembles SID init and play routines to .asm files for code analysis.

Usage:
    from sidm2.disasm_wrapper import DisassemblerIntegration

    result = DisassemblerIntegration.disassemble_sid(
        sid_file=Path("input.sid"),
        output_dir=Path("output"),
        verbose=1
    )
"""

__version__ = "1.0.0"
__date__ = "2025-12-24"

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Add pyscript to path for disasm6502 import
sys.path.insert(0, str(Path(__file__).parent.parent / "pyscript"))

try:
    from disasm6502 import Disassembler6502
    DISASM_AVAILABLE = True
except ImportError:
    DISASM_AVAILABLE = False

logger = logging.getLogger(__name__)


class DisassemblerIntegration:
    """Integration wrapper for 6502 disassembler in conversion pipeline"""

    @staticmethod
    def _read_sid_header(sid_file: Path) -> Dict[str, int]:
        """
        Read SID header to get init and play addresses.

        Args:
            sid_file: Path to SID file

        Returns:
            Dictionary with init_addr, play_addr, load_addr
        """
        with open(sid_file, 'rb') as f:
            header = f.read(0x7E)  # SID header is 126 bytes

        if len(header) < 0x7E:
            raise ValueError("SID file too small")

        # Parse header
        magic = header[0:4]
        if magic != b'PSID' and magic != b'RSID':
            raise ValueError(f"Invalid SID magic: {magic}")

        version = int.from_bytes(header[4:6], 'big')
        data_offset = int.from_bytes(header[6:8], 'big')
        load_addr = int.from_bytes(header[8:10], 'big')
        init_addr = int.from_bytes(header[10:12], 'big')
        play_addr = int.from_bytes(header[12:14], 'big')

        return {
            'load_addr': load_addr,
            'init_addr': init_addr,
            'play_addr': play_addr,
            'data_offset': data_offset
        }

    @staticmethod
    def _read_sid_data(sid_file: Path) -> tuple[bytes, int]:
        """
        Read SID music data.

        Args:
            sid_file: Path to SID file

        Returns:
            Tuple of (data bytes, load address)
        """
        header_info = DisassemblerIntegration._read_sid_header(sid_file)

        with open(sid_file, 'rb') as f:
            f.seek(header_info['data_offset'])
            data = f.read()

        load_addr = header_info['load_addr']
        if load_addr == 0:
            # Load address is in first 2 bytes of data
            load_addr = data[0] | (data[1] << 8)
            data = data[2:]  # Skip load address bytes

        return data, load_addr

    @staticmethod
    def disassemble_sid(
        sid_file: Path,
        output_dir: Path,
        verbose: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Disassemble SID init and play routines to .asm files.

        Args:
            sid_file: Path to input SID file
            output_dir: Directory to write .asm files
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)

        Returns:
            Dictionary with disassembly results:
            {
                'success': True/False,
                'init_file': Path to init.asm,
                'play_file': Path to play.asm,
                'init_addr': Init routine address,
                'play_addr': Play routine address,
                'init_size': Init disassembly size in bytes,
                'play_size': Play disassembly size in bytes,
                'init_lines': Number of disassembled instructions (init),
                'play_lines': Number of disassembled instructions (play)
            }
            Returns None on error.
        """
        if not DISASM_AVAILABLE:
            if verbose > 0:
                logger.warning("Disassembler not available (disasm6502.py not found)")
            return None

        if not sid_file.exists():
            if verbose > 0:
                logger.error(f"SID file not found: {sid_file}")
            return None

        try:
            # Read SID header
            header_info = DisassemblerIntegration._read_sid_header(sid_file)
            init_addr = header_info['init_addr']
            play_addr = header_info['play_addr']
            load_addr = header_info['load_addr']

            if verbose > 0:
                print(f"  Disassembling: {sid_file.name}")
                print(f"    Init: ${init_addr:04X}")
                print(f"    Play: ${play_addr:04X}")
                print(f"    Load: ${load_addr:04X}")

            # Read SID data
            data, actual_load_addr = DisassemblerIntegration._read_sid_data(sid_file)

            if load_addr == 0:
                load_addr = actual_load_addr

            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Disassemble init routine
            init_file = output_dir / f"{sid_file.stem}_init.asm"
            init_size = 200  # Estimate init routine size (will stop at RTS)

            disasm_init = Disassembler6502(data, load_addr, len(data))
            DisassemblerIntegration._disassemble_routine(
                disasm_init, init_addr, init_size, init_file, "Init Routine"
            )

            # Disassemble play routine
            play_file = output_dir / f"{sid_file.stem}_play.asm"
            play_size = 500  # Estimate play routine size (will stop at RTS)

            disasm_play = Disassembler6502(data, load_addr, len(data))
            DisassemblerIntegration._disassemble_routine(
                disasm_play, play_addr, play_size, play_file, "Play Routine"
            )

            if verbose > 0:
                print(f"    Init: {len(disasm_init.lines)} instructions -> {init_file.name}")
                print(f"    Play: {len(disasm_play.lines)} instructions -> {play_file.name}")

            return {
                'success': True,
                'init_file': init_file,
                'play_file': play_file,
                'init_addr': init_addr,
                'play_addr': play_addr,
                'init_size': sum(len(line.bytes) for line in disasm_init.lines.values()),
                'play_size': sum(len(line.bytes) for line in disasm_play.lines.values()),
                'init_lines': len(disasm_init.lines),
                'play_lines': len(disasm_play.lines)
            }

        except Exception as e:
            if verbose > 0:
                # Convert exception to ASCII-safe string
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                logger.error(f"Disassembly failed: {error_msg}")
            return None

    @staticmethod
    def _disassemble_routine(
        disasm: Disassembler6502,
        start_addr: int,
        max_size: int,
        output_file: Path,
        routine_name: str
    ):
        """
        Disassemble a routine and write to file.

        Args:
            disasm: Disassembler6502 instance
            start_addr: Starting address of routine
            max_size: Maximum size to disassemble
            output_file: Output .asm file path
            routine_name: Name for comment header
        """
        # Disassemble routine (will auto-stop at RTS)
        addr = start_addr
        end_addr = min(start_addr + max_size, disasm.end_addr)

        while addr < end_addr:
            line = disasm.disassemble_instruction(addr)
            if not line:
                break

            disasm.lines[addr] = line
            addr += len(line.bytes)

            # Stop at RTS
            if line.instruction == "RTS":
                break

        # Write output file (use ASCII-safe encoding for Windows compatibility)
        output_text = f"; {routine_name}\n"
        output_text += f"; Generated by SIDM2 6502 Disassembler\n"
        output_text += f"; Start: ${start_addr:04X}\n"
        output_text += f"; Size: {sum(len(line.bytes) for line in disasm.lines.values())} bytes\n"
        output_text += f"; Instructions: {len(disasm.lines)}\n"
        output_text += "\n"
        output_text += disasm.format_output()
        output_text += "\n"

        # Write with UTF-8 encoding
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_text)
        except UnicodeEncodeError:
            # Fallback to ASCII with errors replaced
            with open(output_file, 'w', encoding='ascii', errors='replace') as f:
                f.write(output_text)


# Convenience function for simple usage
def disassemble_sid(
    sid_file: Path,
    output_dir: Path,
    verbose: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for disassembling SID files.

    See DisassemblerIntegration.disassemble_sid() for details.
    """
    return DisassemblerIntegration.disassemble_sid(sid_file, output_dir, verbose)
