"""
Pattern Recognizer for SID Conversion Pipeline - Phase 3

Identifies repeating patterns and common structures in SID music data.
Integrated into the conversion pipeline as Step 17.

Usage:
    from sidm2.pattern_recognizer import PatternRecognizer

    recognizer = PatternRecognizer(sid_file=Path("input.sid"))
    patterns = recognizer.analyze()
    report = recognizer.generate_report(patterns, output_file)
"""

__version__ = "1.0.0"
__date__ = "2025-12-24"

from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class Pattern:
    """Represents a repeating pattern in the SID data"""

    def __init__(self, data: bytes, occurrences: List[int]):
        self.data = data
        self.occurrences = occurrences
        self.length = len(data)
        self.count = len(occurrences)

    def __repr__(self):
        return f"Pattern({self.length} bytes, {self.count} occurrences)"

    def bytes_saved(self) -> int:
        """Calculate potential bytes saved if pattern were shared"""
        if self.count <= 1:
            return 0
        # First occurrence stays, others could be replaced with pointers (2 bytes each)
        return (self.count - 1) * (self.length - 2)


class PatternRecognizer:
    """Identifies repeating patterns in SID files"""

    # Pattern search parameters
    MIN_PATTERN_LENGTH = 4  # Minimum bytes for a pattern
    MAX_PATTERN_LENGTH = 32  # Maximum bytes to search
    MIN_OCCURRENCES = 2  # Minimum times pattern must appear

    def __init__(self, sid_file: Path):
        """
        Initialize pattern recognizer.

        Args:
            sid_file: Path to SID file to analyze
        """
        self.sid_file = sid_file
        self.header = {}
        self.data = b''
        self.load_addr = 0
        self.patterns = []

    def _read_sid_header(self) -> Dict[str, Any]:
        """Read and parse SID file header"""
        with open(self.sid_file, 'rb') as f:
            header_bytes = f.read(0x7E)

        if len(header_bytes) < 0x7E:
            raise ValueError("SID file too small")

        magic = header_bytes[0:4]
        if magic not in (b'PSID', b'RSID'):
            raise ValueError(f"Invalid SID magic: {magic}")

        return {
            'magic': magic.decode('ascii'),
            'version': int.from_bytes(header_bytes[4:6], 'big'),
            'data_offset': int.from_bytes(header_bytes[6:8], 'big'),
            'load_addr': int.from_bytes(header_bytes[8:10], 'big'),
            'init_addr': int.from_bytes(header_bytes[10:12], 'big'),
            'play_addr': int.from_bytes(header_bytes[12:14], 'big'),
            'name': header_bytes[22:54].split(b'\x00')[0].decode('ascii', errors='ignore'),
            'author': header_bytes[54:86].split(b'\x00')[0].decode('ascii', errors='ignore'),
        }

    def _read_sid_data(self) -> Tuple[bytes, int]:
        """Read SID music data"""
        with open(self.sid_file, 'rb') as f:
            f.seek(self.header['data_offset'])
            data = f.read()

        load_addr = self.header['load_addr']
        if load_addr == 0:
            load_addr = data[0] | (data[1] << 8)
            data = data[2:]

        return data, load_addr

    def _find_patterns(self, min_length: int, max_length: int) -> List[Pattern]:
        """
        Find repeating byte patterns in the data.

        Args:
            min_length: Minimum pattern length
            max_length: Maximum pattern length

        Returns:
            List of Pattern objects
        """
        patterns_dict = defaultdict(list)

        # Search for patterns of each length
        for pattern_len in range(min_length, max_length + 1):
            # Scan through data looking for patterns
            for i in range(len(self.data) - pattern_len):
                pattern_bytes = self.data[i:i + pattern_len]
                patterns_dict[pattern_bytes].append(i)

        # Filter patterns that appear multiple times
        patterns = []
        for pattern_bytes, occurrences in patterns_dict.items():
            if len(occurrences) >= self.MIN_OCCURRENCES:
                # Check that occurrences don't overlap
                non_overlapping = []
                last_end = -1
                for pos in sorted(occurrences):
                    if pos >= last_end:
                        non_overlapping.append(pos)
                        last_end = pos + len(pattern_bytes)

                if len(non_overlapping) >= self.MIN_OCCURRENCES:
                    patterns.append(Pattern(pattern_bytes, non_overlapping))

        return patterns

    def _analyze_command_patterns(self) -> Dict[str, int]:
        """
        Analyze command byte patterns (common SID command values).

        Returns:
            Dictionary of command bytes and their frequencies
        """
        # Common SF2 command values
        COMMANDS = {
            0x7E: "GATE_ON",
            0x7F: "END",
            0x80: "GATE_OFF",
            0xA0: "TRANSPOSE",
        }

        command_freq = defaultdict(int)

        for byte in self.data:
            if byte in COMMANDS:
                command_freq[COMMANDS[byte]] += 1

        return dict(command_freq)

    def analyze(self, verbose: int = 0) -> Dict[str, Any]:
        """
        Analyze patterns in the SID file.

        Args:
            verbose: Verbosity level (0=quiet, 1=normal, 2=debug)

        Returns:
            Dictionary with analysis results
        """
        try:
            # Read header and data
            self.header = self._read_sid_header()
            self.data, self.load_addr = self._read_sid_data()

            # Find repeating patterns
            self.patterns = self._find_patterns(
                self.MIN_PATTERN_LENGTH,
                self.MAX_PATTERN_LENGTH
            )

            # Sort by potential savings (most valuable first)
            self.patterns.sort(key=lambda p: p.bytes_saved(), reverse=True)

            # Analyze command patterns
            command_freq = self._analyze_command_patterns()

            # Calculate statistics
            total_patterns = len(self.patterns)
            total_occurrences = sum(p.count for p in self.patterns)
            potential_savings = sum(p.bytes_saved() for p in self.patterns)

            # Get top patterns
            top_patterns = self.patterns[:10] if len(self.patterns) > 10 else self.patterns

            # Calculate compression ratio (percentage of bytes that could be saved)
            compression_ratio = (potential_savings / len(self.data)) * 100 if len(self.data) > 0 else 0
            # Cap at 100% to handle edge cases
            compression_ratio = min(compression_ratio, 100.0)

            result = {
                'success': True,
                'sid_file': self.sid_file,
                'header': self.header,
                'data_size': len(self.data),
                'total_patterns': total_patterns,
                'total_occurrences': total_occurrences,
                'potential_savings': potential_savings,
                'compression_ratio': compression_ratio,
                'top_patterns': top_patterns,
                'command_frequencies': command_freq,
                'all_patterns': self.patterns
            }

            if verbose > 0:
                print(f"  Pattern analysis complete")
                print(f"    Total patterns:     {total_patterns}")
                print(f"    Total occurrences:  {total_occurrences}")
                print(f"    Potential savings:  {potential_savings} bytes")
                if len(self.data) > 0:
                    savings_pct = (potential_savings * 100) // len(self.data)
                    print(f"    Compression ratio:  {savings_pct}%")

            return result

        except Exception as e:
            if verbose > 0:
                error_msg = str(e).encode('ascii', 'replace').decode('ascii')
                logger.error(f"Pattern analysis failed: {error_msg}")
            return {
                'success': False,
                'error': str(e)
            }

    def generate_report(self, analysis_result: Dict[str, Any], output_file: Path) -> bool:
        """
        Generate a text report of the pattern analysis.

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
                f.write("SID PATTERN ANALYSIS\n")
                f.write("=" * 70 + "\n\n")

                # File information
                f.write("FILE INFORMATION\n")
                f.write("-" * 70 + "\n")
                f.write(f"File:        {self.sid_file.name}\n")
                f.write(f"Format:      {analysis_result['header']['magic']}\n")
                f.write(f"Name:        {analysis_result['header']['name']}\n")
                f.write(f"Author:      {analysis_result['header']['author']}\n")
                f.write(f"Data size:   {analysis_result['data_size']} bytes\n")
                f.write("\n")

                # Pattern statistics
                f.write("PATTERN STATISTICS\n")
                f.write("-" * 70 + "\n")
                f.write(f"Total patterns:      {analysis_result['total_patterns']}\n")
                f.write(f"Total occurrences:   {analysis_result['total_occurrences']}\n")
                f.write(f"Potential savings:   {analysis_result['potential_savings']} bytes\n")
                f.write(f"Compression ratio:   {analysis_result['compression_ratio']:.1f}%\n")
                f.write("\n")

                # Command frequencies
                if analysis_result['command_frequencies']:
                    f.write("COMMAND FREQUENCIES\n")
                    f.write("-" * 70 + "\n")
                    for cmd, count in sorted(analysis_result['command_frequencies'].items(),
                                            key=lambda x: x[1], reverse=True):
                        f.write(f"{cmd:<15} {count:5d} times\n")
                    f.write("\n")

                # Top patterns
                f.write("TOP REPEATING PATTERNS (by potential savings)\n")
                f.write("-" * 70 + "\n")
                f.write(f"{'Length':<8} {'Count':<8} {'Savings':<10} {'Data (first 16 bytes)'}\n")
                f.write("-" * 70 + "\n")

                for pattern in analysis_result['top_patterns']:
                    # Format first 16 bytes of pattern data
                    data_preview = ' '.join(f'{b:02X}' for b in pattern.data[:16])
                    if len(pattern.data) > 16:
                        data_preview += "..."

                    f.write(f"{pattern.length:<8} {pattern.count:<8} {pattern.bytes_saved():<10} {data_preview}\n")

                    # Show first few occurrences
                    if len(pattern.occurrences) > 0:
                        occ_preview = ", ".join(f"${self.load_addr + pos:04X}" for pos in pattern.occurrences[:5])
                        if len(pattern.occurrences) > 5:
                            occ_preview += f", ... ({len(pattern.occurrences) - 5} more)"
                        f.write(f"         Positions: {occ_preview}\n")

                f.write("\n")

                f.write("=" * 70 + "\n")
                f.write("End of pattern analysis\n")
                f.write("=" * 70 + "\n")

            return True

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return False


# Convenience function
def analyze_patterns(
    sid_file: Path,
    output_file: Path,
    verbose: int = 0
) -> Optional[Dict[str, Any]]:
    """
    Convenience function for analyzing SID file patterns.

    Args:
        sid_file: Path to SID file
        output_file: Path to output report file
        verbose: Verbosity level

    Returns:
        Analysis result dictionary or None on error
    """
    recognizer = PatternRecognizer(sid_file)
    result = recognizer.analyze(verbose=verbose)

    if result['success']:
        recognizer.generate_report(result, output_file)

    return result
