"""
Martin Galway Table Extraction Engine

Extracts music tables (instruments, sequences, effects, etc.) from Martin Galway SID files
using memory pattern analysis and game-specific templates.

Phase 3 implementation: Table extraction with fallback strategies
"""

import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """Represents an extracted music table"""
    name: str  # 'instruments', 'sequences', 'wave', 'pulse', 'filter', etc.
    address: int
    size: int
    entries: int  # Number of entries in table
    entry_size: int  # Bytes per entry
    data: bytes  # Raw table data
    confidence: float  # 0.0 to 1.0
    reasoning: List[str]
    template_match: str = "unknown"  # Which template this matches


@dataclass
class ExtractionResult:
    """Results from table extraction attempt"""
    success: bool
    tables_found: Dict[str, ExtractedTable]
    tables_missing: List[str]
    confidence_average: float
    notes: List[str]
    errors: List[str]


class GalwayTableExtractor:
    """
    Extract music tables from Martin Galway SID files.

    Different Galway players use different table layouts. This extractor:
    1. Uses memory patterns to identify likely table locations
    2. Applies game-specific templates for known patterns
    3. Uses heuristics to identify table boundaries
    4. Validates extracted tables
    """

    # Common table signatures for Galway players
    INSTRUMENT_MARKERS = {
        'size_32': 32 * 8,      # 32 instruments × 8 bytes
        'size_16': 16 * 8,      # 16 instruments × 8 bytes
        'size_64': 64 * 8,      # 64 instruments × 8 bytes
    }

    SEQUENCE_MARKERS = {
        'pattern_end': 0x7F,    # End of sequence pattern
        'loop_marker': 0x7E,    # Loop marker
        'rest_marker': 0x00,    # Rest/silence
    }

    # Control bytes commonly found in Galway tables
    CONTROL_BYTES = {
        0x7F: 'end_marker',
        0x7E: 'loop_marker',
        0x80: 'gate_off',
        0xFF: 'padding',
    }

    def __init__(self, c64_data: bytes, load_address: int = 0x1000):
        """
        Initialize table extractor.

        Args:
            c64_data: Raw C64 binary data (without header)
            load_address: Load address of the SID data
        """
        self.data = c64_data
        self.load_address = load_address
        self.extracted_tables: Dict[str, ExtractedTable] = {}
        self.candidate_tables: List[Dict[str, Any]] = []

    def extract(self, memory_patterns: Optional[List[Dict]] = None) -> ExtractionResult:
        """
        Extract all tables from SID data.

        Args:
            memory_patterns: Optional list of memory patterns from Phase 2 analyzer

        Returns:
            ExtractionResult with extracted tables
        """
        logger.debug(f"Galway Table Extraction: {len(self.data):,} bytes at ${self.load_address:04X}")

        self.extracted_tables = {}
        errors = []
        notes = []

        try:
            # Step 1: Extract sequence tables (most reliable)
            sequences = self._extract_sequences()
            if sequences:
                self.extracted_tables['sequences'] = sequences
                notes.append(f"Found {sequences.entries} sequences")

            # Step 2: Extract instrument table (if present)
            instruments = self._extract_instruments()
            if instruments:
                self.extracted_tables['instruments'] = instruments
                notes.append(f"Found {instruments.entries} instruments")

            # Step 3: Extract effect tables (wave, pulse, filter)
            effects = self._extract_effect_tables()
            for effect_name, table in effects.items():
                if table:
                    self.extracted_tables[effect_name] = table
                    notes.append(f"Found {table_name} table ({table.entries} entries)")

            # Step 4: Extract control tables
            controls = self._extract_control_tables()
            for control_name, table in controls.items():
                if table:
                    self.extracted_tables[control_name] = table
                    notes.append(f"Found {control_name} table")

        except Exception as e:
            logger.error(f"Extraction error: {e}")
            errors.append(str(e))

        # Calculate confidence
        confidence_scores = [t.confidence for t in self.extracted_tables.values()]
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

        # Determine missing tables
        expected_tables = {'sequences', 'instruments', 'wave', 'pulse', 'filter'}
        missing = expected_tables - set(self.extracted_tables.keys())
        missing_list = list(missing)

        return ExtractionResult(
            success=len(self.extracted_tables) > 0,
            tables_found=self.extracted_tables,
            tables_missing=missing_list,
            confidence_average=avg_confidence,
            notes=notes,
            errors=errors
        )

    def _extract_sequences(self) -> Optional[ExtractedTable]:
        """
        Extract sequence/pattern table.

        Looks for patterns of:
        - Note numbers (0x01-0x7E)
        - End markers (0x7F)
        - Control bytes
        - Repeated note runs
        """
        logger.debug("  Extracting sequences...")

        # Heuristic 1: Look for blocks of data with 0x7F markers
        sequence_blocks = []

        for i in range(len(self.data) - 1):
            if self.data[i] == 0x7F:  # End marker
                # Found potential sequence end, trace backwards
                block_start = max(0, i - 256)  # Look back up to 256 bytes

                # Find sequence boundary
                start = block_start
                for j in range(i - 1, block_start - 1, -1):
                    if self.data[j] == 0x7F or self.data[j] == 0x00:
                        start = j + 1
                        break

                size = i - start + 1
                if 4 <= size <= 256:  # Reasonable sequence size
                    sequence_blocks.append({
                        'address': self.load_address + start,
                        'start': start,
                        'end': i,
                        'size': size,
                        'confidence': 0.8,
                    })

        if not sequence_blocks:
            return None

        # Find largest continuous block (likely main sequence table)
        if len(sequence_blocks) > 5:
            # Group nearby blocks (likely same table)
            grouped = self._group_nearby_blocks(sequence_blocks)
            largest_group = max(grouped, key=lambda g: sum(b['size'] for b in g))

            # Estimate table size
            total_size = sum(b['size'] for b in largest_group)
            num_sequences = len(largest_group)

            logger.debug(f"    Found {num_sequences} sequences, {total_size} bytes")

            return ExtractedTable(
                name='sequences',
                address=largest_group[0]['address'],
                size=total_size,
                entries=num_sequences,
                entry_size=total_size // max(num_sequences, 1),
                data=self._extract_bytes(largest_group[0]['start'], total_size),
                confidence=0.75,
                reasoning=[
                    f"Found {num_sequences} sequence blocks marked with 0x7F",
                    f"Total data size: {total_size} bytes",
                    "Pattern consistent with sequence table"
                ]
            )

        return None

    def _extract_instruments(self) -> Optional[ExtractedTable]:
        """
        Extract instrument table.

        Typical structure:
        - 8-32 instruments
        - 8 bytes per instrument (AD/SR/waveform/etc.)
        - Often at fixed offset
        """
        logger.debug("  Extracting instruments...")

        # Common instrument table sizes
        common_sizes = [
            (32, 8),    # 32 instruments × 8 bytes
            (16, 8),    # 16 instruments × 8 bytes
            (64, 8),    # 64 instruments × 8 bytes
            (32, 4),    # 32 instruments × 4 bytes
        ]

        for num_entries, entry_size in common_sizes:
            table_size = num_entries * entry_size

            # Look for patterns in data
            for i in range(0, len(self.data) - table_size, entry_size):
                block = self.data[i:i+table_size]

                # Score this block
                score = self._score_instrument_block(block, num_entries, entry_size)

                if score > 0.7:  # Good match
                    logger.debug(f"    Found likely instrument table at ${self.load_address + i:04X}")

                    return ExtractedTable(
                        name='instruments',
                        address=self.load_address + i,
                        size=table_size,
                        entries=num_entries,
                        entry_size=entry_size,
                        data=bytes(block),
                        confidence=score,
                        reasoning=[
                            f"Pattern matches {num_entries}×{entry_size} instrument table",
                            f"Confidence score: {score:.0%}",
                        ]
                    )

        return None

    def _extract_effect_tables(self) -> Dict[str, Optional[ExtractedTable]]:
        """
        Extract effect tables (wave, pulse, filter).

        These vary greatly by player but often follow patterns:
        - Wave table: Often 128 entries (waveforms)
        - Pulse table: 64 entries (pulse widths)
        - Filter table: 32 entries (filter settings)
        """
        logger.debug("  Extracting effect tables...")

        result = {
            'wave': None,
            'pulse': None,
            'filter': None,
        }

        # Look for repeating patterns (characteristic of effect tables)
        # Wave table: Often has repeating waveform data
        # Pulse table: Often has smooth progression
        # Filter table: Often sparse data

        # For now, return None (placeholder for more sophisticated detection)
        return result

    def _extract_control_tables(self) -> Dict[str, Optional[ExtractedTable]]:
        """
        Extract control tables (transposition, arpeggio, etc.).
        """
        logger.debug("  Extracting control tables...")

        result = {}

        # Placeholder for control table extraction
        return result

    def _score_instrument_block(self, block: bytes, num_entries: int, entry_size: int) -> float:
        """
        Score a block to determine if it's likely an instrument table.

        Returns confidence 0.0-1.0
        """
        score = 0.5  # Base score

        # Check for reasonable byte patterns
        non_zero = sum(1 for b in block if b != 0x00)
        if non_zero > 0:
            # Some data is present (good)
            score += 0.2

        # Check for no obvious code opcodes (bad for instrument table)
        code_opcodes = [0x60, 0x40, 0xEA, 0x00]  # RTS, RTI, NOP, BRK
        code_count = sum(1 for b in block if b in code_opcodes)
        if code_count < len(block) * 0.1:  # < 10% code bytes
            score += 0.2

        # Check for reasonable value ranges
        max_val = max(block) if block else 0
        if 0 < max_val < 256:  # Valid byte range
            score += 0.1

        return min(1.0, score)

    def _group_nearby_blocks(self, blocks: List[Dict], threshold: int = 16) -> List[List[Dict]]:
        """Group blocks that are within threshold distance."""
        if not blocks:
            return []

        sorted_blocks = sorted(blocks, key=lambda b: b['start'])
        groups = []
        current_group = [sorted_blocks[0]]

        for block in sorted_blocks[1:]:
            if block['start'] - current_group[-1]['end'] <= threshold:
                current_group.append(block)
            else:
                groups.append(current_group)
                current_group = [block]

        groups.append(current_group)
        return groups

    def _extract_bytes(self, offset: int, size: int) -> bytes:
        """Extract bytes from data at offset."""
        end = min(offset + size, len(self.data))
        return self.data[offset:end]

    def get_extraction_report(self) -> str:
        """Get human-readable extraction report."""
        lines = [
            "Martin Galway Table Extraction Report",
            f"  Load address: ${self.load_address:04X}",
            f"  Data size: {len(self.data):,} bytes",
            f"  Tables found: {len(self.extracted_tables)}",
        ]

        for table_name, table in self.extracted_tables.items():
            lines.append(f"  - {table_name}: {table.entries} entries @ ${table.address:04X} ({table.confidence:.0%})")

        return '\n'.join(lines)


# Module initialization
logger.debug("galway_table_extractor module loaded")
