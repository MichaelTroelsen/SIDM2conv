"""
6502 ASM Annotation Integration for SID Conversion Pipeline

Integrates pyscript/annotate_asm.py into the conversion pipeline as Step 8.7.
Provides comprehensive analysis of SID player code with symbol tables, call graphs,
loop detection, register tracking, and documentation cross-references.

This complements disasm_wrapper.py by adding advanced analysis on top of basic
disassembly. While disasm_wrapper provides raw assembly code, annotation_wrapper
adds semantic understanding with:
  - Symbol tables and memory maps
  - Call graphs and subroutine analysis
  - Loop detection and cycle counting
  - Register lifecycle tracking
  - Pattern recognition
  - Documentation links

Usage:
    from sidm2.annotation_wrapper import AnnotationIntegration

    result = AnnotationIntegration.annotate_sid(
        sid_file=Path("input.sid"),
        output_dir=Path("output/analysis"),
        output_format="text",
        config_path=None,  # Optional config file
        preset="educational",  # Or "minimal", "debug"
        verbose=1
    )

Returns:
    {
        'success': True/False,
        'annotated_file': Path to annotated .asm file,
        'load_addr': Load address,
        'init_addr': Init routine address,
        'play_addr': Play routine address,
        'symbols_found': Number of symbols detected,
        'subroutines_found': Number of subroutines,
        'loops_found': Number of loops,
        'patterns_found': Number of patterns detected,
        'output_format': Format used (text/html/markdown/json/csv/tsv)
    }
"""

__version__ = "1.0.0"
__date__ = "2026-01-01"

import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import subprocess

from .errors import InvalidInputError

# Add pyscript to path for annotate_asm import
pyscript_dir = Path(__file__).parent.parent / "pyscript"
if str(pyscript_dir) not in sys.path:
    sys.path.insert(0, str(pyscript_dir))

try:
    from annotate_asm import annotate_asm_file
    ASM_ANNOTATION_AVAILABLE = True
except ImportError:
    ASM_ANNOTATION_AVAILABLE = False

# Import disassembler for generating ASM from binary
try:
    from disasm6502 import Disassembler6502
    DISASM_AVAILABLE = True
except ImportError:
    DISASM_AVAILABLE = False

logger = logging.getLogger(__name__)


class AnnotationIntegration:
    """Integration wrapper for ASM annotation in conversion pipeline"""

    @staticmethod
    def _read_sid_header(sid_file: Path) -> Dict[str, int]:
        """
        Read SID header to get addresses and metadata.

        Args:
            sid_file: Path to SID file

        Returns:
            Dictionary with load_addr, init_addr, play_addr, data_offset, title, author
        """
        with open(sid_file, 'rb') as f:
            header = f.read(0x7E)  # SID header is 126 bytes

        if len(header) < 0x7E:
            raise InvalidInputError(
                input_type='SID file',
                value=str(sid_file),
                expected='At least 126 bytes for SID header',
                got=f'Only {len(header)} bytes available',
                suggestions=[
                    'Verify file is a complete SID file (not truncated)',
                    'Check if file was fully downloaded',
                    f'File size: {sid_file.stat().st_size if sid_file.exists() else 0} bytes',
                    'SID files should be at least 126 bytes + music data',
                    'Try re-downloading or re-exporting the file'
                ],
                docs_link='guides/TROUBLESHOOTING.md#invalid-sid-files'
            )

        # Parse header
        magic = header[0:4]
        if magic != b'PSID' and magic != b'RSID':
            raise InvalidInputError(
                input_type='SID file',
                value=str(sid_file),
                expected='PSID or RSID magic bytes at file start',
                got=f'Magic bytes: {repr(magic)}',
                suggestions=[
                    'Verify file is a valid SID file (not corrupted)',
                    'Check file extension is .sid',
                    'Try opening file in a SID player (e.g., VICE) to verify',
                    f'Inspect file header with hex viewer',
                    'Re-download file if obtained from internet'
                ],
                docs_link='guides/TROUBLESHOOTING.md#invalid-sid-files'
            )

        version = int.from_bytes(header[4:6], 'big')
        data_offset = int.from_bytes(header[6:8], 'big')
        load_addr = int.from_bytes(header[8:10], 'big')
        init_addr = int.from_bytes(header[10:12], 'big')
        play_addr = int.from_bytes(header[12:14], 'big')

        # Extract metadata
        title = header[0x16:0x36].decode('ascii', errors='ignore').rstrip('\x00')
        author = header[0x36:0x56].decode('ascii', errors='ignore').rstrip('\x00')

        return {
            'load_addr': load_addr,
            'init_addr': init_addr,
            'play_addr': play_addr,
            'data_offset': data_offset,
            'title': title,
            'author': author,
            'version': version
        }

    @staticmethod
    def _disassemble_sid(sid_file: Path, output_dir: Path) -> Optional[Path]:
        """
        Disassemble SID file to ASM for annotation.

        Args:
            sid_file: Path to SID file
            output_dir: Directory to write .asm file

        Returns:
            Path to disassembled .asm file, or None on error
        """
        if not DISASM_AVAILABLE:
            logger.error("Disassembler not available (disasm6502.py not found)")
            return None

        try:
            header_info = AnnotationIntegration._read_sid_header(sid_file)

            with open(sid_file, 'rb') as f:
                f.seek(header_info['data_offset'])
                data = f.read()

            load_addr = header_info['load_addr']
            if load_addr == 0:
                # Load address is in first 2 bytes of data
                load_addr = data[0] | (data[1] << 8)
                data = data[2:]  # Skip load address bytes

            # Disassemble the code
            output_dir.mkdir(parents=True, exist_ok=True)
            asm_file = output_dir / f"{sid_file.stem}_disasm.asm"

            disasm = Disassembler6502(data, load_addr, len(data))

            # Disassemble full code section (up to 8KB or end of data)
            max_bytes = min(8192, len(data))
            addr = load_addr
            end_addr = load_addr + max_bytes

            while addr < end_addr and (addr - load_addr) < len(data):
                line = disasm.disassemble_instruction(addr)
                if not line:
                    break
                disasm.lines[addr] = line
                addr += len(line.bytes)

            # Write disassembly to file
            with open(asm_file, 'w', encoding='utf-8') as f:
                f.write(f"; Disassembly of {sid_file.name}\n")
                f.write(f"; Generated by SIDM2 for ASM annotation\n")
                if header_info['title']:
                    f.write(f"; Title: {header_info['title']}\n")
                if header_info['author']:
                    f.write(f"; Author: {header_info['author']}\n")
                f.write(f"; Load: ${load_addr:04X}\n")
                f.write(f"; Init: ${header_info['init_addr']:04X}\n")
                f.write(f"; Play: ${header_info['play_addr']:04X}\n")
                f.write("\n")
                f.write(disasm.format_output())

            return asm_file

        except Exception as e:
            logger.error(f"Failed to disassemble SID: {e}")
            return None

    @staticmethod
    def annotate_sid(
        sid_file: Path,
        output_dir: Path,
        output_format: str = "text",
        verbose: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Generate comprehensive annotated analysis of SID player code.

        Args:
            sid_file: Path to input SID file
            output_dir: Directory to write annotated files
            output_format: Output format (text/html/markdown/json/csv/tsv)
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)

        Returns:
            Dictionary with annotation results:
            {
                'success': True/False,
                'annotated_file': Path to annotated output file,
                'disasm_file': Path to intermediate disassembly file,
                'load_addr': Load address,
                'init_addr': Init routine address,
                'play_addr': Play routine address,
                'title': SID title,
                'author': SID author,
                'output_format': Format used,
                'file_size': Size of annotated output in bytes
            }
            Returns None on error.
        """
        if not ASM_ANNOTATION_AVAILABLE:
            if verbose > 0:
                logger.warning("ASM annotation not available (annotate_asm.py not found)")
            return None

        if not DISASM_AVAILABLE:
            if verbose > 0:
                logger.warning("Disassembler not available (disasm6502.py not found)")
            return None

        if not sid_file.exists():
            if verbose > 0:
                logger.error(
                    f"SID file not found: {sid_file}\n"
                    f"  Suggestion: Cannot annotate missing SID file\n"
                    f"  Check: Verify file path is correct\n"
                    f"  Try: Use absolute path instead of relative path\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#file-not-found-issues"
                )
            return None

        try:
            # Read SID header
            header_info = AnnotationIntegration._read_sid_header(sid_file)

            if verbose > 0:
                print(f"  Annotating: {sid_file.name}")
                if header_info['title']:
                    print(f"    Title: {header_info['title']}")
                if header_info['author']:
                    print(f"    Author: {header_info['author']}")
                print(f"    Init: ${header_info['init_addr']:04X}")
                print(f"    Play: ${header_info['play_addr']:04X}")
                print(f"    Load: ${header_info['load_addr']:04X}")

            # Step 1: Disassemble SID to ASM
            if verbose > 0:
                print(f"    Step 1: Disassembling...")

            asm_file = AnnotationIntegration._disassemble_sid(sid_file, output_dir)
            if not asm_file:
                if verbose > 0:
                    logger.error("Failed to disassemble SID")
                return None

            if verbose > 0:
                print(f"    Disassembly: {asm_file.name} ({asm_file.stat().st_size:,} bytes)")

            # Step 2: Annotate the disassembly
            if verbose > 0:
                print(f"    Step 2: Annotating disassembly...")

            # Determine output extension
            ext_map = {
                'text': '.asm',
                'html': '.html',
                'markdown': '.md',
                'json': '.json',
                'csv': '.csv',
                'tsv': '.tsv'
            }
            ext = ext_map.get(output_format, '.asm')

            # Generate annotated output
            output_file = output_dir / f"{sid_file.stem}_annotated{ext}"

            # Prepare file_info for annotator
            file_info = {
                'title': header_info['title'],
                'author': header_info['author'],
                'init_addr': header_info['init_addr'],
                'play_addr': header_info['play_addr'],
                'load_address': header_info['load_addr']
            }

            # Call annotate_asm_file (it prints its own progress)
            # Silence stdout if not verbose
            if verbose == 0:
                import contextlib
                import io
                with contextlib.redirect_stdout(io.StringIO()):
                    annotate_asm_file(asm_file, output_file, file_info, output_format)
            else:
                annotate_asm_file(asm_file, output_file, file_info, output_format)

            if verbose > 0:
                print(f"    Annotated: {output_file.name} ({output_file.stat().st_size:,} bytes)")

            return {
                'success': True,
                'annotated_file': output_file,
                'disasm_file': asm_file,
                'load_addr': header_info['load_addr'],
                'init_addr': header_info['init_addr'],
                'play_addr': header_info['play_addr'],
                'title': header_info['title'],
                'author': header_info['author'],
                'output_format': output_format,
                'file_size': output_file.stat().st_size
            }

        except Exception as e:
            if verbose > 0:
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                logger.error(
                    f"Annotation failed: {error_msg}\n"
                    f"  Suggestion: Annotator could not process SID file\n"
                    f"  Check: Verify SID file has valid executable code\n"
                    f"  Try: Run quick_disasm.py first to verify SID structure\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#annotation-failures"
                )
            return None


# Convenience function for simple usage
def annotate_sid(
    sid_file: Path,
    output_dir: Path,
    output_format: str = "text",
    verbose: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for annotating SID files.

    See AnnotationIntegration.annotate_sid() for details.
    """
    return AnnotationIntegration.annotate_sid(
        sid_file, output_dir, output_format, verbose
    )
