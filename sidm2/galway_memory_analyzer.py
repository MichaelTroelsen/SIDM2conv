"""
Martin Galway Memory Structure Analyzer

Analyzes memory layout of Martin Galway SID files to identify:
- Player code boundaries
- Table locations (instruments, wave, pulse, filter, sequences)
- Memory access patterns
- Data structure boundaries

Phase 2 implementation: Memory pattern detection and heuristic analysis
"""

import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class MemoryPattern:
    """Represents a detected memory pattern"""
    address: int
    size: int
    pattern_type: str  # 'zero_run', 'code', 'table', 'data'
    confidence: float
    description: str


@dataclass
class TableCandidate:
    """Represents a potential table location"""
    address: int
    size: int
    table_type: str  # 'instrument', 'wave', 'pulse', 'filter', 'sequence', 'unknown'
    confidence: float
    reasoning: List[str]


class GalwayMemoryAnalyzer:
    """
    Analyze Martin Galway SID file memory structure.

    Martin Galway players vary significantly per game:
    - Player code: 2KB-12KB+ (variable)
    - Table locations: No standard addresses
    - Data layout: Game-specific organization

    Strategy: Use heuristics to identify likely table locations:
    1. Control byte patterns (0x7F, 0x7E markers)
    2. Memory density analysis (high zero density = data boundary)
    3. Pointer patterns (ascending sequences)
    4. Instruction patterns (6502 opcodes)
    5. Data frequency analysis
    """

    # Known control bytes in Galway tables
    CONTROL_BYTES = {
        0x7F: 'end_marker',      # End of table / sequence
        0x7E: 'gate_marker',     # Gate on/sustain marker
        0x80: 'gate_off',        # Gate off marker
        0xFF: 'padding',         # Often used for padding
    }

    # 6502 common opcodes
    COMMON_OPCODES = {
        0x60: 'RTS',    # Return
        0x40: 'RTI',    # Return from interrupt
        0x00: 'BRK',    # Break (or padding)
        0xEA: 'NOP',    # No operation
        0xA9: 'LDA',    # Load accumulator
        0x8D: 'STA',    # Store accumulator
        0xAD: 'LDA',    # Load accumulator absolute
    }

    def __init__(self, c64_data: bytes, load_address: int,
                 player_size_estimate: int = 0):
        """
        Initialize memory analyzer.

        Args:
            c64_data: Raw C64 binary data (without PSID header)
            load_address: Load address from PSID header
            player_size_estimate: Estimated player code size (from analyzer)
        """
        self.data = c64_data
        self.load_address = load_address
        self.player_size_estimate = player_size_estimate
        self.analysis_results = {}
        self.patterns = []
        self.table_candidates = []

    def analyze(self) -> Dict:
        """
        Perform complete memory analysis.

        Returns:
            Dictionary with analysis results
        """
        logger.debug(f"Galway Memory Analysis: {len(self.data):,} bytes at ${self.load_address:04X}")

        # Step 1: Scan for memory patterns
        self._scan_memory_patterns()

        # Step 2: Find likely table locations
        self._find_table_candidates()

        # Step 3: Detect code/data boundaries
        self._detect_boundaries()

        # Step 4: Build analysis report
        self._generate_report()

        return self.analysis_results

    def _scan_memory_patterns(self) -> None:
        """Scan for memory patterns to identify regions."""
        logger.debug("  Scanning memory patterns...")

        patterns = []
        i = 0

        while i < len(self.data):
            # Look for zero runs
            if self.data[i] == 0x00:
                start = i
                while i < len(self.data) and self.data[i] == 0x00:
                    i += 1
                size = i - start

                if size >= 16:  # Significant zero run
                    patterns.append(MemoryPattern(
                        address=self.load_address + start,
                        size=size,
                        pattern_type='zero_run',
                        confidence=0.9,
                        description=f'Zero block ({size} bytes)'
                    ))
            # Look for code patterns (RTS/RTI/BRK)
            elif self.data[i] in [0x60, 0x40]:  # RTS or RTI
                patterns.append(MemoryPattern(
                    address=self.load_address + i,
                    size=1,
                    pattern_type='code',
                    confidence=0.7,
                    description='Routine boundary (RTS/RTI)'
                ))
                i += 1
            else:
                i += 1

        self.patterns = patterns
        logger.debug(f"    Found {len(patterns)} patterns")

    def _find_table_candidates(self) -> None:
        """Find likely table locations using heuristics."""
        logger.debug("  Finding table candidates...")

        candidates = []
        data_len = len(self.data)

        # Heuristic 1: Look for sequences of identical bytes (tables)
        for i in range(data_len - 32):
            window = self.data[i:i+32]

            # High byte frequency = likely table
            byte_freq = Counter(window)
            most_common_byte, freq = byte_freq.most_common(1)[0]

            if freq >= 8:  # At least 8 occurrences in 32-byte window
                confidence = min(0.9, 0.5 + (freq / 32) * 0.4)
                candidates.append(TableCandidate(
                    address=self.load_address + i,
                    size=32,
                    table_type='potential_table',
                    confidence=confidence,
                    reasoning=[f'Byte 0x{most_common_byte:02X} appears {freq}/32 times']
                ))

        # Heuristic 2: Look for control byte patterns (0x7F end markers)
        for i in range(data_len):
            if self.data[i] == 0x7F:
                # Likely end of table - trace backwards to find start
                start = max(0, i - 64)  # Look back up to 64 bytes

                # Find previous control byte or zero boundary
                table_start = start
                for j in range(i - 1, start - 1, -1):
                    if self.data[j] in [0x7F, 0x7E, 0x00]:
                        table_start = j + 1
                        break

                size = i - table_start + 1
                if 4 <= size <= 256:  # Reasonable table size
                    candidates.append(TableCandidate(
                        address=self.load_address + table_start,
                        size=size,
                        table_type='bounded_table',
                        confidence=0.8,
                        reasoning=[f'Bounded by 0x7F marker (size {size} bytes)']
                    ))

        # Heuristic 3: Pointer patterns (ascending sequences)
        for i in range(data_len - 4):
            window = self.data[i:i+4]
            if len(set(window)) == 2 and window[0] < window[-1]:
                # Likely pointer or address table
                candidates.append(TableCandidate(
                    address=self.load_address + i,
                    size=4,
                    table_type='pointer_table',
                    confidence=0.6,
                    reasoning=['Ascending byte sequence (pointer pattern)']
                ))

        # Deduplicate and score
        self._deduplicate_candidates(candidates)

        logger.debug(f"    Found {len(self.table_candidates)} table candidates")

    def _deduplicate_candidates(self, candidates: List[TableCandidate]) -> None:
        """Remove duplicate/overlapping candidates, keep highest confidence."""
        if not candidates:
            self.table_candidates = []
            return

        # Sort by confidence descending
        sorted_cands = sorted(candidates, key=lambda x: x.confidence, reverse=True)

        # Keep unique addresses
        seen_ranges = []
        unique = []

        for cand in sorted_cands:
            # Check if overlaps with existing
            overlaps = False
            for seen_start, seen_end in seen_ranges:
                if (cand.address >= seen_start and cand.address < seen_end) or \
                   (seen_start >= cand.address and seen_start < cand.address + cand.size):
                    overlaps = True
                    break

            if not overlaps:
                unique.append(cand)
                seen_ranges.append((cand.address, cand.address + cand.size))

        self.table_candidates = unique[:20]  # Keep top 20

    def _detect_boundaries(self) -> None:
        """Detect code/data boundaries."""
        logger.debug("  Detecting memory boundaries...")

        # Find first large zero section (likely data boundary)
        longest_zero = 0
        longest_zero_addr = 0

        i = 0
        while i < len(self.data):
            if self.data[i] == 0x00:
                start = i
                while i < len(self.data) and self.data[i] == 0x00:
                    i += 1
                size = i - start
                if size > longest_zero:
                    longest_zero = size
                    longest_zero_addr = start
            else:
                i += 1

        if longest_zero >= 16:
            logger.debug(f"    Code/data boundary at ${self.load_address + longest_zero_addr:04X} "
                       f"({longest_zero} byte zero section)")

    def _generate_report(self) -> None:
        """Generate analysis report."""
        self.analysis_results = {
            'load_address': self.load_address,
            'data_size': len(self.data),
            'patterns_found': len(self.patterns),
            'table_candidates_count': len(self.table_candidates),
            'patterns': [
                {
                    'address': f'${p.address:04X}',
                    'size': p.size,
                    'type': p.pattern_type,
                    'confidence': f'{p.confidence:.0%}',
                    'description': p.description,
                }
                for p in self.patterns[:10]  # Top 10
            ],
            'table_candidates': [
                {
                    'address': f'${c.address:04X}',
                    'size': c.size,
                    'type': c.table_type,
                    'confidence': f'{c.confidence:.0%}',
                    'reasoning': ', '.join(c.reasoning),
                }
                for c in self.table_candidates[:10]  # Top 10
            ],
        }

    def get_summary(self) -> str:
        """Get human-readable summary of analysis."""
        if not self.analysis_results:
            return "No analysis performed"

        summary = [
            f"Memory Analysis Summary (${self.load_address:04X})",
            f"  Data size: {self.analysis_results['data_size']:,} bytes",
            f"  Patterns found: {self.analysis_results['patterns_found']}",
            f"  Table candidates: {self.analysis_results['table_candidates']}",
        ]

        if self.table_candidates:
            summary.append("  Top candidates:")
            for cand in self.table_candidates[:5]:
                summary.append(
                    f"    ${cand.address:04X}: {cand.table_type} ({cand.size} bytes, "
                    f"{cand.confidence:.0%} confidence)"
                )

        return '\n'.join(summary)


# Module initialization
logger.debug("galway_memory_analyzer module loaded")
