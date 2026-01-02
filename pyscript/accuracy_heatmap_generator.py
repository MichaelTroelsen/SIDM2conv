#!/usr/bin/env python3
"""
Accuracy Heatmap Generator - Generate heatmap data from trace comparison

Generates a frame-by-frame, register-by-register heatmap visualization data
structure for comparing two SID traces. Produces grids showing matches,
values, and deltas for all 29 SID registers across all frames.

Usage:
    from accuracy_heatmap_generator import HeatmapGenerator

    generator = HeatmapGenerator(trace_a, trace_b, comparison)
    heatmap_data = generator.generate()

    print(f"Heatmap: {heatmap_data.frames} frames × {heatmap_data.registers} registers")
    print(f"Overall accuracy: {heatmap_data.overall_accuracy:.2f}%")

Version: 1.0.0
Date: 2026-01-01
"""

import sys
import os
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyscript.sidtracer import TraceData, SIDRegisterWrite
from pyscript.trace_comparator import TraceComparisonMetrics


# SID register offsets (0x00-0x1C, 29 registers total)
SID_REGISTERS = 29

# Register names for reference
REGISTER_NAMES = [
    "V1_FREQ_LO", "V1_FREQ_HI", "V1_PW_LO", "V1_PW_HI", "V1_CTRL", "V1_AD", "V1_SR",
    "V2_FREQ_LO", "V2_FREQ_HI", "V2_PW_LO", "V2_PW_HI", "V2_CTRL", "V2_AD", "V2_SR",
    "V3_FREQ_LO", "V3_FREQ_HI", "V3_PW_LO", "V3_PW_HI", "V3_CTRL", "V3_AD", "V3_SR",
    "FC_LO", "FC_HI", "RES_FILT", "MODE_VOL",
    "POT_X", "POT_Y", "OSC3_RAND", "ENV3"
]


@dataclass
class HeatmapData:
    """Heatmap visualization data structure.

    Contains all data needed to render an interactive heatmap showing
    frame-by-frame register-level accuracy between two SID traces.
    """

    # Dimensions
    frames: int = 0
    registers: int = SID_REGISTERS

    # Per-frame, per-register data (2D grids)
    match_grid: List[List[bool]] = field(default_factory=list)     # [frame][register] -> match/mismatch
    value_grid_a: List[List[int]] = field(default_factory=list)    # [frame][register] -> value in file A
    value_grid_b: List[List[int]] = field(default_factory=list)    # [frame][register] -> value in file B
    delta_grid: List[List[int]] = field(default_factory=list)      # [frame][register] -> abs(value_a - value_b)

    # Per-frame summary
    frame_accuracy: List[float] = field(default_factory=list)      # [frame] -> accuracy %

    # Per-register summary
    register_accuracy: List[float] = field(default_factory=list)   # [register] -> accuracy %

    # Metadata
    filename_a: str = ""
    filename_b: str = ""
    total_comparisons: int = 0
    total_matches: int = 0
    overall_accuracy: float = 0.0


class HeatmapGenerator:
    """Generate heatmap data from trace comparison.

    Takes two SID traces and comparison metrics, builds complete heatmap
    data structure with match/value/delta grids for visualization.
    """

    def __init__(self, trace_a: TraceData, trace_b: TraceData,
                 comparison: TraceComparisonMetrics,
                 filename_a: str = "File A",
                 filename_b: str = "File B"):
        """
        Initialize heatmap generator.

        Args:
            trace_a: First trace (original)
            trace_b: Second trace (converted)
            comparison: Comparison metrics from TraceComparator
            filename_a: Display name for first file
            filename_b: Display name for second file
        """
        self.trace_a = trace_a
        self.trace_b = trace_b
        self.comparison = comparison
        self.filename_a = filename_a
        self.filename_b = filename_b

    def generate(self) -> HeatmapData:
        """
        Generate complete heatmap data structure.

        Process:
        1. Build grid: frames × 29 registers
        2. For each (frame, register) cell:
           - Get value from trace_a
           - Get value from trace_b
           - Calculate match (bool)
           - Calculate delta (abs difference)
        3. Calculate per-frame accuracy
        4. Calculate per-register accuracy
        5. Return HeatmapData

        Returns:
            Complete HeatmapData structure ready for visualization
        """

        # Determine frame count (use minimum if they differ)
        frames = min(self.trace_a.frames, self.trace_b.frames)

        # Initialize heatmap data
        heatmap = HeatmapData(
            frames=frames,
            registers=SID_REGISTERS,
            filename_a=self.filename_a,
            filename_b=self.filename_b
        )

        # Build grids
        heatmap.match_grid = self._build_match_grid(frames)
        heatmap.value_grid_a, heatmap.value_grid_b = self._build_value_grids(frames)
        heatmap.delta_grid = self._build_delta_grid(heatmap.value_grid_a, heatmap.value_grid_b)

        # Calculate summary statistics
        heatmap.frame_accuracy = self._calculate_frame_accuracy(heatmap.match_grid)
        heatmap.register_accuracy = self._calculate_register_accuracy(heatmap.match_grid)

        # Calculate overall stats
        total_cells = frames * SID_REGISTERS
        total_matches = sum(sum(1 for match in row if match) for row in heatmap.match_grid)

        heatmap.total_comparisons = total_cells
        heatmap.total_matches = total_matches
        heatmap.overall_accuracy = (total_matches / total_cells * 100.0) if total_cells > 0 else 0.0

        return heatmap

    def _build_match_grid(self, frames: int) -> List[List[bool]]:
        """
        Build binary match/mismatch grid.

        For each (frame, register) cell, determine if the register value
        matches between trace_a and trace_b.

        Args:
            frames: Number of frames to process

        Returns:
            2D grid [frame][register] -> bool (True = match, False = mismatch)
        """
        match_grid = []

        for frame_idx in range(frames):
            frame_row = []

            # Get register values for this frame from both traces
            values_a = self._get_frame_register_values(self.trace_a, frame_idx)
            values_b = self._get_frame_register_values(self.trace_b, frame_idx)

            # Compare each register
            for reg_offset in range(SID_REGISTERS):
                value_a = values_a.get(reg_offset, 0)
                value_b = values_b.get(reg_offset, 0)
                match = (value_a == value_b)
                frame_row.append(match)

            match_grid.append(frame_row)

        return match_grid

    def _build_value_grids(self, frames: int) -> Tuple[List[List[int]], List[List[int]]]:
        """
        Build value grids for both traces.

        For each (frame, register) cell, store the actual register value
        from each trace.

        Args:
            frames: Number of frames to process

        Returns:
            Tuple of (value_grid_a, value_grid_b), each [frame][register] -> int (0-255)
        """
        value_grid_a = []
        value_grid_b = []

        for frame_idx in range(frames):
            # Get register values for this frame from both traces
            values_a = self._get_frame_register_values(self.trace_a, frame_idx)
            values_b = self._get_frame_register_values(self.trace_b, frame_idx)

            # Build row for trace_a
            row_a = [values_a.get(reg_offset, 0) for reg_offset in range(SID_REGISTERS)]
            value_grid_a.append(row_a)

            # Build row for trace_b
            row_b = [values_b.get(reg_offset, 0) for reg_offset in range(SID_REGISTERS)]
            value_grid_b.append(row_b)

        return value_grid_a, value_grid_b

    def _build_delta_grid(self, value_grid_a: List[List[int]],
                          value_grid_b: List[List[int]]) -> List[List[int]]:
        """
        Build delta (difference) grid.

        For each (frame, register) cell, calculate the absolute difference
        between trace_a and trace_b values.

        Args:
            value_grid_a: Value grid for trace_a
            value_grid_b: Value grid for trace_b

        Returns:
            2D grid [frame][register] -> int (0-255, absolute difference)
        """
        delta_grid = []

        for frame_idx in range(len(value_grid_a)):
            row = []
            for reg_offset in range(SID_REGISTERS):
                value_a = value_grid_a[frame_idx][reg_offset]
                value_b = value_grid_b[frame_idx][reg_offset]
                delta = abs(value_a - value_b)
                row.append(delta)
            delta_grid.append(row)

        return delta_grid

    def _calculate_frame_accuracy(self, match_grid: List[List[bool]]) -> List[float]:
        """
        Calculate per-frame accuracy percentages.

        For each frame, calculate what % of registers match.

        Args:
            match_grid: Binary match/mismatch grid

        Returns:
            List of accuracy percentages [100.0, 98.5, ...], one per frame
        """
        frame_accuracy = []

        for frame_row in match_grid:
            matches = sum(1 for match in frame_row if match)
            total = len(frame_row)
            accuracy = (matches / total * 100.0) if total > 0 else 0.0
            frame_accuracy.append(accuracy)

        return frame_accuracy

    def _calculate_register_accuracy(self, match_grid: List[List[bool]]) -> List[float]:
        """
        Calculate per-register accuracy percentages.

        For each register, calculate what % of frames match.

        Args:
            match_grid: Binary match/mismatch grid

        Returns:
            List of accuracy percentages [95.0, 100.0, ...], one per register
        """
        register_accuracy = []

        for reg_offset in range(SID_REGISTERS):
            matches = 0
            total = 0

            for frame_row in match_grid:
                if frame_row[reg_offset]:
                    matches += 1
                total += 1

            accuracy = (matches / total * 100.0) if total > 0 else 0.0
            register_accuracy.append(accuracy)

        return register_accuracy

    def _get_frame_register_values(self, trace: TraceData, frame_idx: int) -> Dict[int, int]:
        """
        Get all register values for a specific frame.

        Extracts register writes from the trace for the given frame and
        returns them as a dictionary mapping register offset -> value.

        Args:
            trace: TraceData to extract from
            frame_idx: Frame index (0-based)

        Returns:
            Dictionary of {register_offset: value} for this frame
            Empty dict if frame doesn't exist
        """
        if frame_idx >= len(trace.frame_writes):
            return {}

        frame_writes = trace.frame_writes[frame_idx]
        register_values = {}

        for write in frame_writes:
            # Convert absolute address to register offset
            reg_offset = write.address - 0xD400

            # Only process valid SID register offsets
            if 0 <= reg_offset < SID_REGISTERS:
                register_values[reg_offset] = write.value

        return register_values


def main():
    """Test heatmap generator with sample data."""
    print("Accuracy Heatmap Generator - Test Mode")
    print("This module is meant to be imported, not run directly.")
    print()
    print("Usage:")
    print("  from accuracy_heatmap_generator import HeatmapGenerator")
    print("  generator = HeatmapGenerator(trace_a, trace_b, comparison)")
    print("  heatmap_data = generator.generate()")
    print()
    print("See accuracy_heatmap_tool.py for complete CLI usage.")


if __name__ == '__main__':
    main()
