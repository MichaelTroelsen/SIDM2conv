"""
Memory Map Analyzer for SID Conversion Pipeline - Phase 3

Analyzes memory layout of SID files to visualize code, data, and table regions.
Integrated into the conversion pipeline as Step 12.5.

Usage:
    from sidm2.memmap_analyzer import MemoryMapAnalyzer

    analyzer = MemoryMapAnalyzer(sid_file=Path("input.sid"))
    memory_map = analyzer.analyze()
    report = analyzer.generate_report(memory_map)
"""

__version__ = "1.0.0"
__date__ = "2025-12-24"

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import logging

from .errors import InvalidInputError

logger = logging.getLogger(__name__)


class MemoryRegion:
    """Represents a region of memory in the SID file"""

    def __init__(self, start: int, end: int, region_type: str, description: str = ""):
        self.start = start
        self.end = end
        self.region_type = region_type
        self.description = description

    @property
    def size(self) -> int:
        """Size of the region in bytes"""
        return self.end - self.start + 1

    def overlaps(self, other: 'MemoryRegion') -> bool:
        """Check if this region overlaps with another"""
        return not (self.end < other.start or self.start > other.end)

    def __repr__(self):
        return f"MemoryRegion(${self.start:04X}-${self.end:04X}, {self.region_type}, {self.size} bytes)"


class MemoryMapAnalyzer:
    """Analyzes memory layout of SID files"""

    # C64 memory ranges
    C64_RAM_START = 0x0000
    C64_RAM_END = 0xFFFF
    SID_CHIP_START = 0xD400
    SID_CHIP_END = 0xD7FF

    def __init__(self, sid_file: Path):
        """
        Initialize memory map analyzer.

        Args:
            sid_file: Path to SID file to analyze
        """
        self.sid_file = sid_file
        self.header = {}
        self.data = b''
        self.load_addr = 0
        self.regions = []

    def _read_sid_header(self) -> Dict[str, Any]:
        """
        Read and parse SID file header.

        Returns:
            Dictionary with header information
        """
        with open(self.sid_file, 'rb') as f:
            header_bytes = f.read(0x7E)  # 126 bytes

        if len(header_bytes) < 0x7E:
            raise InvalidInputError(
                input_type='SID file',
                value=str(self.sid_file),
                expected='At least 126 bytes for SID header',
                got=f'Only {len(header_bytes)} bytes available',
                suggestions=[
                    'Verify file is a complete SID file (not truncated)',
                    'Check if file was fully downloaded',
                    f'File size: {self.sid_file.stat().st_size if self.sid_file.exists() else 0} bytes',
                    'SID files should be at least 126 bytes + music data',
                    'Try re-downloading or re-exporting the file'
                ],
                docs_link='guides/TROUBLESHOOTING.md#invalid-sid-files'
            )

        magic = header_bytes[0:4]
        if magic not in (b'PSID', b'RSID'):
            raise InvalidInputError(
                input_type='SID file',
                value=str(self.sid_file),
                expected='PSID or RSID magic bytes at file start',
                got=f'Magic bytes: {repr(magic)}',
                suggestions=[
                    'Verify file is a valid SID file (not corrupted)',
                    'Check file extension is .sid',
                    'Try opening file in a SID player (e.g., VICE) to verify',
                    f'Inspect file header: hexdump -C {self.sid_file} | head -5',
                    'Re-download file if obtained from internet'
                ],
                docs_link='guides/TROUBLESHOOTING.md#invalid-sid-files'
            )

        header = {
            'magic': magic.decode('ascii'),
            'version': int.from_bytes(header_bytes[4:6], 'big'),
            'data_offset': int.from_bytes(header_bytes[6:8], 'big'),
            'load_addr': int.from_bytes(header_bytes[8:10], 'big'),
            'init_addr': int.from_bytes(header_bytes[10:12], 'big'),
            'play_addr': int.from_bytes(header_bytes[12:14], 'big'),
            'songs': int.from_bytes(header_bytes[14:16], 'big'),
            'start_song': int.from_bytes(header_bytes[16:18], 'big'),
            'speed': int.from_bytes(header_bytes[18:22], 'big'),
        }

        # Extract name, author, copyright (null-terminated strings)
        header['name'] = header_bytes[22:54].split(b'\x00')[0].decode('ascii', errors='ignore')
        header['author'] = header_bytes[54:86].split(b'\x00')[0].decode('ascii', errors='ignore')
        header['copyright'] = header_bytes[86:118].split(b'\x00')[0].decode('ascii', errors='ignore')

        return header

    def _read_sid_data(self) -> Tuple[bytes, int]:
        """
        Read SID music data.

        Returns:
            Tuple of (data bytes, actual load address)
        """
        with open(self.sid_file, 'rb') as f:
            f.seek(self.header['data_offset'])
            data = f.read()

        load_addr = self.header['load_addr']
        if load_addr == 0:
            # Load address is in first 2 bytes of data
            load_addr = data[0] | (data[1] << 8)
            data = data[2:]

        return data, load_addr

    def _identify_regions(self) -> List[MemoryRegion]:
        """
        Identify memory regions in the SID file.

        Returns:
            List of MemoryRegion objects
        """
        regions = []

        # Calculate end address
        end_addr = self.load_addr + len(self.data) - 1

        # Add main data region
        regions.append(MemoryRegion(
            self.load_addr,
            end_addr,
            "DATA",
            f"Total SID data ({len(self.data)} bytes)"
        ))

        # Add init routine region (estimate ~200 bytes)
        if self.header['init_addr'] > 0:
            init_end = min(self.header['init_addr'] + 199, end_addr)
            regions.append(MemoryRegion(
                self.header['init_addr'],
                init_end,
                "CODE",
                "Init routine (estimated)"
            ))

        # Add play routine region (estimate ~500 bytes)
        if self.header['play_addr'] > 0:
            play_end = min(self.header['play_addr'] + 499, end_addr)
            regions.append(MemoryRegion(
                self.header['play_addr'],
                play_end,
                "CODE",
                "Play routine (estimated)"
            ))

        # Check for SID chip register access
        if self.SID_CHIP_START <= end_addr:
            regions.append(MemoryRegion(
                self.SID_CHIP_START,
                self.SID_CHIP_END,
                "HARDWARE",
                "SID chip registers"
            ))

        return regions

    def analyze(self, verbose: int = 0) -> Dict[str, Any]:
        """
        Analyze memory layout of the SID file.

        Args:
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)

        Returns:
            Dictionary with analysis results
        """
        try:
            # Read header
            self.header = self._read_sid_header()

            # Read data
            self.data, self.load_addr = self._read_sid_data()

            # Identify regions
            self.regions = self._identify_regions()

            # Calculate statistics
            total_size = len(self.data)
            code_size = sum(r.size for r in self.regions if r.region_type == "CODE")
            data_size = total_size - code_size

            result = {
                'success': True,
                'sid_file': self.sid_file,
                'header': self.header,
                'load_addr': self.load_addr,
                'end_addr': self.load_addr + total_size - 1,
                'total_size': total_size,
                'code_size': code_size,
                'data_size': data_size,
                'regions': self.regions,
                'region_count': len(self.regions)
            }

            if verbose > 0:
                print(f"  Memory map analysis complete")
                print(f"    Load address: ${self.load_addr:04X}")
                print(f"    End address:  ${self.load_addr + total_size - 1:04X}")
                print(f"    Total size:   {total_size} bytes")
                print(f"    Code:         {code_size} bytes ({code_size*100//total_size if total_size > 0 else 0}%)")
                print(f"    Data:         {data_size} bytes ({data_size*100//total_size if total_size > 0 else 0}%)")
                print(f"    Regions:      {len(self.regions)}")

            return result

        except Exception as e:
            if verbose > 0:
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                logger.error(
                    f"Memory map analysis failed: {error_msg}\n"
                    f"  Suggestion: Cannot analyze SID memory layout\n"
                    f"  Check: Verify SID file has valid structure\n"
                    f"  Try: Use simpler analysis or different tool\n"
                    f"  See: docs/guides/TROUBLESHOOTING.md#memory-map-errors"
                )
            return {
                'success': False,
                'error': str(e)
            }

    def generate_report(self, analysis_result: Dict[str, Any], output_file: Path) -> bool:
        """
        Generate a text report of the memory map analysis.

        Args:
            analysis_result: Result from analyze()
            output_file: Output file path for the report

        Returns:
            True if successful, False otherwise
        """
        try:
            if not analysis_result.get('success'):
                return False

            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("SID MEMORY MAP ANALYSIS\n")
                f.write("=" * 70 + "\n\n")

                # Header information
                f.write("FILE INFORMATION\n")
                f.write("-" * 70 + "\n")
                f.write(f"File:        {self.sid_file.name}\n")
                f.write(f"Format:      {analysis_result['header']['magic']}\n")
                f.write(f"Name:        {analysis_result['header']['name']}\n")
                f.write(f"Author:      {analysis_result['header']['author']}\n")
                f.write(f"Copyright:   {analysis_result['header']['copyright']}\n")
                f.write(f"Version:     {analysis_result['header']['version']}\n")
                f.write(f"Songs:       {analysis_result['header']['songs']}\n")
                f.write("\n")

                # Memory layout
                f.write("MEMORY LAYOUT\n")
                f.write("-" * 70 + "\n")
                f.write(f"Load address:  ${analysis_result['load_addr']:04X}\n")
                f.write(f"End address:   ${analysis_result['end_addr']:04X}\n")
                f.write(f"Init address:  ${analysis_result['header']['init_addr']:04X}\n")
                f.write(f"Play address:  ${analysis_result['header']['play_addr']:04X}\n")
                f.write("\n")

                # Memory regions
                f.write("MEMORY REGIONS\n")
                f.write("-" * 70 + "\n")
                f.write(f"{'Start':<8} {'End':<8} {'Size':<8} {'Type':<10} {'Description'}\n")
                f.write("-" * 70 + "\n")

                for region in analysis_result['regions']:
                    f.write(f"${region.start:04X}    ${region.end:04X}    "
                           f"{region.size:5d}    {region.region_type:<10} {region.description}\n")

                f.write("\n")

                # Statistics
                f.write("STATISTICS\n")
                f.write("-" * 70 + "\n")
                total = analysis_result['total_size']
                code = analysis_result['code_size']
                data = analysis_result['data_size']

                f.write(f"Total size:    {total:5d} bytes (100%)\n")
                f.write(f"Code regions:  {code:5d} bytes ({code*100//total if total > 0 else 0}%)\n")
                f.write(f"Data regions:  {data:5d} bytes ({data*100//total if total > 0 else 0}%)\n")
                f.write("\n")

                # Visual memory map
                f.write("VISUAL MEMORY MAP\n")
                f.write("-" * 70 + "\n")
                self._write_visual_map(f, analysis_result)
                f.write("\n")

                f.write("=" * 70 + "\n")
                f.write("End of memory map analysis\n")
                f.write("=" * 70 + "\n")

            return True

        except Exception as e:
            logger.error(
                f"Failed to generate report: {e}\n"
                f"  Suggestion: Cannot write memory map report\n"
                f"  Check: Verify output directory is writable\n"
                f"  Try: Check disk space and file permissions\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#report-generation-errors"
            )
            return False

    def _write_visual_map(self, f, analysis_result: Dict[str, Any]):
        """
        Write a visual ASCII representation of the memory map.

        Args:
            f: File handle to write to
            analysis_result: Analysis results
        """
        # Create a simple bar chart representation
        total_size = analysis_result['total_size']
        bar_width = 60

        # Calculate bar segments
        code_width = (analysis_result['code_size'] * bar_width) // total_size if total_size > 0 else 0
        data_width = bar_width - code_width

        f.write(f"${analysis_result['load_addr']:04X} ")
        f.write("C" * code_width)
        f.write("D" * data_width)
        f.write(f" ${analysis_result['end_addr']:04X}\n")
        f.write(" " * 7)
        f.write("-" * bar_width)
        f.write("\n")
        f.write(f"       C = Code ({analysis_result['code_size']} bytes)\n")
        f.write(f"       D = Data ({analysis_result['data_size']} bytes)\n")


# Convenience function
def analyze_memory_map(
    sid_file: Path,
    output_file: Path,
    verbose: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for analyzing SID file memory map.

    Args:
        sid_file: Path to SID file
        output_file: Path to output report file
        verbose: Verbosity level

    Returns:
        Analysis result dictionary or None on error
    """
    analyzer = MemoryMapAnalyzer(sid_file)
    result = analyzer.analyze(verbose=verbose)

    if result['success']:
        analyzer.generate_report(result, output_file)

    return result
