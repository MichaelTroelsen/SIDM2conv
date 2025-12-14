"""
Memory Overlap Detection and Visualization Module

Provides:
- Detailed overlap detection and analysis
- Visual memory layout with overlap highlighting
- Overlap conflict resolution suggestions
- Memory fragmentation analysis
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum


@dataclass
class MemoryBlock:
    """Represents a block of memory"""
    name: str
    start: int
    end: int
    size: int
    block_type: str  # 'code', 'data', 'table', 'free'
    info: Optional[str] = None

    def overlaps_with(self, other: 'MemoryBlock') -> bool:
        """Check if this block overlaps with another"""
        return not (self.end < other.start or self.start > other.end)

    def overlap_size(self, other: 'MemoryBlock') -> int:
        """Calculate overlap size with another block"""
        if not self.overlaps_with(other):
            return 0
        overlap_start = max(self.start, other.start)
        overlap_end = min(self.end, other.end)
        return overlap_end - overlap_start + 1

    def __repr__(self):
        return f"{self.name:20} ${self.start:04X}-${self.end:04X} ({self.size:5} bytes)"


@dataclass
class OverlapConflict:
    """Information about an overlap conflict"""
    block_a: MemoryBlock
    block_b: MemoryBlock
    overlap_start: int
    overlap_end: int
    overlap_size: int
    severity: str  # 'critical', 'high', 'medium', 'low'

    def __str__(self):
        severity_marker = {
            'critical': '!!!',
            'high': '!!',
            'medium': '!',
            'low': '-'
        }
        marker = severity_marker.get(self.severity, '?')

        return (f"{marker} {self.block_a.name:15} <-> {self.block_b.name:15} "
                f"overlap at ${self.overlap_start:04X}-${self.overlap_end:04X} "
                f"({self.overlap_size} bytes)")


class MemoryOverlapDetector:
    """Detects and analyzes memory overlaps"""

    def __init__(self):
        """Initialize detector"""
        self.blocks: List[MemoryBlock] = []
        self.conflicts: List[OverlapConflict] = []

    def add_block(self, name: str, start: int, end: int, block_type: str = 'data',
                  info: Optional[str] = None) -> MemoryBlock:
        """Add a memory block to track"""
        size = end - start + 1
        block = MemoryBlock(
            name=name,
            start=start,
            end=end,
            size=size,
            block_type=block_type,
            info=info
        )
        self.blocks.append(block)
        return block

    def detect_overlaps(self) -> List[OverlapConflict]:
        """Detect all overlapping memory blocks"""
        self.conflicts = []

        for i, block_a in enumerate(self.blocks):
            for block_b in self.blocks[i+1:]:
                if block_a.overlaps_with(block_b):
                    overlap_start = max(block_a.start, block_b.start)
                    overlap_end = min(block_a.end, block_b.end)
                    overlap_size = overlap_end - overlap_start + 1

                    # Determine severity
                    severity = self._calculate_severity(block_a, block_b, overlap_size)

                    conflict = OverlapConflict(
                        block_a=block_a,
                        block_b=block_b,
                        overlap_start=overlap_start,
                        overlap_end=overlap_end,
                        overlap_size=overlap_size,
                        severity=severity
                    )
                    self.conflicts.append(conflict)

        return self.conflicts

    def _calculate_severity(self, block_a: MemoryBlock, block_b: MemoryBlock,
                           overlap_size: int) -> str:
        """Calculate severity of overlap based on block types"""

        # Code overlaps with anything are critical
        if block_a.block_type == 'code' or block_b.block_type == 'code':
            return 'critical'

        # Large overlaps are critical
        if overlap_size > 512:
            return 'critical'

        # Medium overlaps are high severity
        if overlap_size > 128:
            return 'high'

        # Small overlaps are medium severity
        if overlap_size > 32:
            return 'medium'

        return 'low'

    def generate_overlap_report(self) -> str:
        """Generate detailed overlap report"""
        lines = []

        lines.append("=" * 100)
        lines.append("MEMORY OVERLAP DETECTION REPORT")
        lines.append("=" * 100)
        lines.append("")

        # Summary
        num_blocks = len(self.blocks)
        num_conflicts = len(self.conflicts)

        lines.append(f"Total Memory Blocks: {num_blocks}")
        lines.append(f"Detected Overlaps: {num_conflicts}")
        lines.append("")

        if num_conflicts == 0:
            lines.append("No memory overlaps detected. Memory layout is clean.")
            lines.append("")
        else:
            # Categorize by severity
            critical = [c for c in self.conflicts if c.severity == 'critical']
            high = [c for c in self.conflicts if c.severity == 'high']
            medium = [c for c in self.conflicts if c.severity == 'medium']
            low = [c for c in self.conflicts if c.severity == 'low']

            if critical:
                lines.append(f"CRITICAL OVERLAPS: {len(critical)}")
                lines.append("-" * 100)
                for conflict in critical:
                    lines.append(f"  {conflict}")
                lines.append("")

            if high:
                lines.append(f"HIGH SEVERITY OVERLAPS: {len(high)}")
                lines.append("-" * 100)
                for conflict in high:
                    lines.append(f"  {conflict}")
                lines.append("")

            if medium:
                lines.append(f"MEDIUM SEVERITY OVERLAPS: {len(medium)}")
                lines.append("-" * 100)
                for conflict in medium:
                    lines.append(f"  {conflict}")
                lines.append("")

            if low:
                lines.append(f"LOW SEVERITY OVERLAPS: {len(low)}")
                lines.append("-" * 100)
                for conflict in low:
                    lines.append(f"  {conflict}")
                lines.append("")

        # Memory layout visualization
        lines.append("")
        lines.append("MEMORY LAYOUT (sorted by address):")
        lines.append("-" * 100)

        sorted_blocks = sorted(self.blocks, key=lambda b: b.start)
        for block in sorted_blocks:
            lines.append(f"  {block}")

        # Memory map visualization (ASCII art)
        lines.append("")
        lines.append("MEMORY MAP VISUALIZATION:")
        lines.append("-" * 100)

        lines.extend(self.generate_memory_map_ascii(64))

        lines.append("")
        lines.append("=" * 100)

        return "\n".join(lines)

    def generate_memory_map_ascii(self, width: int = 64) -> List[str]:
        """Generate ASCII memory map visualization"""
        lines = []

        # Create memory grid (16 rows × width columns)
        # Each cell represents 256 bytes (16 pages × 256 bytes)
        rows = 16
        cells_per_row = width
        bytes_per_cell = int(0x10000 / (rows * cells_per_row))

        # Create grid
        grid = [['.' for _ in range(cells_per_row)] for _ in range(rows)]

        # Mark blocks on grid
        block_chars = {}
        current_char = ord('A')

        for block in self.blocks:
            if current_char > ord('Z'):
                current_char = ord('0')

            char = chr(current_char)
            block_chars[block.name] = char

            # Mark all cells occupied by this block
            start_cell = block.start // bytes_per_cell
            end_cell = block.end // bytes_per_cell

            for cell in range(start_cell, min(end_cell + 1, rows * cells_per_row)):
                row = cell // cells_per_row
                col = cell % cells_per_row
                if row < rows:
                    grid[row][col] = char

            current_char += 1

        # Print grid with row labels
        for row_idx, row in enumerate(grid):
            addr_start = row_idx * cells_per_row * bytes_per_cell
            addr_end = addr_start + cells_per_row * bytes_per_cell - 1
            row_str = ''.join(row)
            lines.append(f"  ${addr_start:04X}-${addr_end:04X} | {row_str}")

        # Legend
        lines.append("")
        lines.append("Legend:")
        for block in sorted(self.blocks, key=lambda b: b.start):
            char = block_chars.get(block.name, '?')
            lines.append(f"  {char} = {block.name}")

        return lines

    def generate_suggestions(self) -> List[str]:
        """Generate suggestions for resolving overlaps"""
        suggestions = []

        if not self.conflicts:
            suggestions.append("No overlaps detected - memory layout is optimal.")
            return suggestions

        # Analyze patterns
        for conflict in self.conflicts:
            if conflict.severity == 'critical':
                suggestions.append(
                    f"CRITICAL: Move {conflict.block_b.name} to avoid overlap with "
                    f"{conflict.block_a.name}. {conflict.overlap_size} bytes overlap."
                )
            elif conflict.severity == 'high':
                suggestions.append(
                    f"Relocate {conflict.block_b.name} to ${conflict.overlap_end + 1:04X} "
                    f"to avoid {conflict.overlap_size} byte overlap with {conflict.block_a.name}"
                )

        # Memory fragmentation analysis
        occupied = sum(block.size for block in self.blocks)
        total = 0x10000
        free = total - occupied
        fragmentation = 100.0 * (1.0 - (occupied / total))

        suggestions.append("")
        suggestions.append(f"Memory Usage: {occupied} / {total} bytes ({100.0 * occupied / total:.1f}%)")
        suggestions.append(f"Free Space: {free} bytes")
        suggestions.append(f"Fragmentation: {fragmentation:.1f}%")

        return suggestions

    def validate_no_overlaps(self) -> Tuple[bool, List[str]]:
        """Validate that there are no overlaps"""
        overlaps = self.detect_overlaps()

        if not overlaps:
            return True, ["No overlaps detected - memory layout is valid."]

        messages = []
        for overlap in overlaps:
            messages.append(f"Overlap: {overlap.block_a.name} <-> {overlap.block_b.name}")

        return False, messages


def create_table_overlap_detector(tables: Dict) -> MemoryOverlapDetector:
    """Create overlap detector from table dictionary"""
    detector = MemoryOverlapDetector()

    for table_name, table_info in tables.items():
        if table_info.address and table_info.size:
            detector.add_block(
                name=table_name,
                start=table_info.address,
                end=table_info.address + table_info.size - 1,
                block_type='table',
                info=f"Type: {table_info.type}"
            )

    return detector
