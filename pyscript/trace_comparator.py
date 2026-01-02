#!/usr/bin/env python3
"""
Trace Comparator - Compare two SID execution traces

Compares two TraceData objects (from SIDTracer) and calculates comprehensive
comparison metrics including frame-level accuracy, register-level accuracy,
voice-level accuracy, and detailed diffs.

Usage:
    from trace_comparator import TraceComparator

    comparator = TraceComparator(trace_a, trace_b)
    metrics = comparator.compare()

    print(f"Frame Match: {metrics.frame_match_percent:.2f}%")
    print(f"Total Diffs: {metrics.total_diff_count}")

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
from sidm2.comparison_tool import ComparisonDetailExtractor, RegisterDiff, VoiceDiff


@dataclass
class TraceComparisonMetrics:
    """Comprehensive trace comparison metrics"""

    # Overall metrics
    frame_match_percent: float = 0.0       # % of frames with identical writes
    total_diff_count: int = 0              # Total register write differences
    frame_count_match: bool = False        # Do both traces have same frame count?

    # Per-phase breakdowns
    init_diff_count: int = 0               # Differences in init phase
    frame_diff_count: int = 0              # Differences in frame phase

    # Per-frame accuracy (for timeline visualization)
    per_frame_accuracy: List[float] = field(default_factory=list)  # [100.0, 98.5, ...]

    # Register-level accuracy
    register_accuracy: Dict[str, float] = field(default_factory=dict)  # Per-register match %
    register_accuracy_overall: float = 0.0

    # Voice-level accuracy (frequency, waveform, ADSR, pulse)
    voice_accuracy: Dict[int, Dict[str, float]] = field(default_factory=dict)  # Voice 1/2/3

    # Detailed diffs (reuse existing classes)
    register_diffs: List[RegisterDiff] = field(default_factory=list)
    voice_diffs: Dict[int, VoiceDiff] = field(default_factory=dict)


class TraceComparator:
    """Compare two TraceData objects and calculate comprehensive metrics"""

    def __init__(self, trace_a: TraceData, trace_b: TraceData):
        """
        Initialize comparator with two traces.

        Args:
            trace_a: First trace (e.g., original SID)
            trace_b: Second trace (e.g., converted SID)
        """
        self.trace_a = trace_a
        self.trace_b = trace_b

    def compare(self) -> TraceComparisonMetrics:
        """
        Execute full comparison and return comprehensive metrics.

        Returns:
            TraceComparisonMetrics with all comparison data
        """
        metrics = TraceComparisonMetrics()

        # Check frame count match
        metrics.frame_count_match = (self.trace_a.frames == self.trace_b.frames)

        # Compare init writes
        init_diffs = self._compare_init_writes()
        metrics.init_diff_count = len(init_diffs)

        # Convert traces to frame format for comparison
        frames_a = self._convert_trace_to_frame_format(self.trace_a)
        frames_b = self._convert_trace_to_frame_format(self.trace_b)

        # Compare frame writes
        per_frame_acc, frame_diffs = self._compare_frame_writes(frames_a, frames_b)
        metrics.per_frame_accuracy = per_frame_acc
        metrics.frame_diff_count = len(frame_diffs)

        # Calculate frame match percentage
        if per_frame_acc:
            perfect_frames = sum(1 for acc in per_frame_acc if acc == 100.0)
            metrics.frame_match_percent = (perfect_frames / len(per_frame_acc)) * 100.0
        else:
            metrics.frame_match_percent = 100.0

        # Total diffs
        metrics.total_diff_count = metrics.init_diff_count + metrics.frame_diff_count

        # Extract detailed diffs using existing infrastructure
        metrics.register_diffs = ComparisonDetailExtractor.extract_register_diffs(
            frames_a, frames_b
        )
        metrics.voice_diffs = ComparisonDetailExtractor.extract_voice_diffs(
            frames_a, frames_b
        )

        # Calculate register-level accuracy
        metrics.register_accuracy = self._calculate_register_accuracy(frames_a, frames_b)
        if metrics.register_accuracy:
            # Overall register accuracy = average of all registers
            accuracies = [acc for acc in metrics.register_accuracy.values() if acc is not None]
            metrics.register_accuracy_overall = sum(accuracies) / len(accuracies) if accuracies else 0.0

        # Calculate voice-level accuracy
        metrics.voice_accuracy = self._calculate_voice_accuracy(frames_a, frames_b)

        return metrics

    def _compare_init_writes(self) -> List[RegisterDiff]:
        """
        Compare initialization phase writes.

        Returns:
            List of RegisterDiff for init phase differences
        """
        # Convert init writes to dict format
        init_a = {}
        for write in self.trace_a.init_writes:
            reg_offset = write.address - 0xD400
            init_a[reg_offset] = write.value

        init_b = {}
        for write in self.trace_b.init_writes:
            reg_offset = write.address - 0xD400
            init_b[reg_offset] = write.value

        # Find differences
        diffs = []
        all_regs = set(init_a.keys()) | set(init_b.keys())

        for reg in sorted(all_regs):
            val_a = init_a.get(reg, 0)
            val_b = init_b.get(reg, 0)

            if val_a != val_b:
                reg_name = ComparisonDetailExtractor.REGISTER_NAMES.get(
                    reg, f"Reg_{reg:02X}"
                )
                diffs.append(RegisterDiff(
                    frame=-1,  # -1 indicates init phase
                    register=reg,
                    register_name=reg_name,
                    original_value=val_a,
                    exported_value=val_b
                ))

        return diffs

    def _compare_frame_writes(self, frames_a: List[Dict], frames_b: List[Dict]) -> Tuple[List[float], List[RegisterDiff]]:
        """
        Compare frame-by-frame writes and calculate per-frame accuracy.

        Args:
            frames_a: List of frames for trace A (each frame is Dict[reg_offset, value])
            frames_b: List of frames for trace B

        Returns:
            Tuple of (per_frame_accuracy list, all register diffs)
        """
        max_frames = min(len(frames_a), len(frames_b))
        per_frame_accuracy = []
        all_diffs = []

        for frame_idx in range(max_frames):
            frame_a = frames_a[frame_idx]
            frame_b = frames_b[frame_idx]

            # Calculate this frame's accuracy
            accuracy = self._calculate_frame_accuracy(frame_a, frame_b)
            per_frame_accuracy.append(accuracy)

            # Extract diffs for this frame
            all_regs = set(frame_a.keys()) | set(frame_b.keys())
            for reg in sorted(all_regs):
                val_a = frame_a.get(reg, 0)
                val_b = frame_b.get(reg, 0)

                if val_a != val_b:
                    reg_name = ComparisonDetailExtractor.REGISTER_NAMES.get(
                        reg, f"Reg_{reg:02X}"
                    )
                    all_diffs.append(RegisterDiff(
                        frame=frame_idx,
                        register=reg,
                        register_name=reg_name,
                        original_value=val_a,
                        exported_value=val_b
                    ))

        return per_frame_accuracy, all_diffs

    def _calculate_frame_accuracy(self, frame_a: Dict[int, int], frame_b: Dict[int, int]) -> float:
        """
        Calculate percentage of matching registers in a single frame.

        Args:
            frame_a: Frame from trace A (Dict[reg_offset, value])
            frame_b: Frame from trace B

        Returns:
            Accuracy percentage (0.0 - 100.0)
        """
        all_regs = set(frame_a.keys()) | set(frame_b.keys())

        if not all_regs:
            return 100.0  # Both empty = perfect match

        matches = sum(1 for reg in all_regs if frame_a.get(reg) == frame_b.get(reg))
        return (matches / len(all_regs)) * 100.0

    def _convert_trace_to_frame_format(self, trace: TraceData) -> List[Dict[int, int]]:
        """
        Convert TraceData.frame_writes to format expected by ComparisonDetailExtractor.

        Args:
            trace: TraceData object with frame_writes

        Returns:
            List of frame dicts (each dict maps register offset to value)
        """
        frames = []

        for frame_writes in trace.frame_writes:
            frame_dict = {}
            for write in frame_writes:
                reg_offset = write.address - 0xD400
                frame_dict[reg_offset] = write.value
            frames.append(frame_dict)

        return frames

    def _calculate_register_accuracy(self, frames_a: List[Dict], frames_b: List[Dict]) -> Dict[str, float]:
        """
        Calculate per-register accuracy across all frames.

        Args:
            frames_a: Frames from trace A
            frames_b: Frames from trace B

        Returns:
            Dict mapping register name to accuracy percentage
        """
        register_stats = {}  # reg_offset -> {matches: int, total: int}
        max_frames = min(len(frames_a), len(frames_b))

        for frame_idx in range(max_frames):
            frame_a = frames_a[frame_idx]
            frame_b = frames_b[frame_idx]

            all_regs = set(frame_a.keys()) | set(frame_b.keys())

            for reg in all_regs:
                if reg not in register_stats:
                    register_stats[reg] = {'matches': 0, 'total': 0}

                val_a = frame_a.get(reg)
                val_b = frame_b.get(reg)

                if val_a == val_b:
                    register_stats[reg]['matches'] += 1

                register_stats[reg]['total'] += 1

        # Calculate accuracy percentages
        register_accuracy = {}
        for reg, stats in register_stats.items():
            reg_name = ComparisonDetailExtractor.REGISTER_NAMES.get(reg, f"Reg_{reg:02X}")
            accuracy = (stats['matches'] / stats['total']) * 100.0 if stats['total'] > 0 else 100.0
            register_accuracy[reg_name] = accuracy

        return register_accuracy

    def _calculate_voice_accuracy(self, frames_a: List[Dict], frames_b: List[Dict]) -> Dict[int, Dict[str, float]]:
        """
        Calculate per-voice accuracy (frequency, waveform, ADSR, pulse).

        Args:
            frames_a: Frames from trace A
            frames_b: Frames from trace B

        Returns:
            Dict mapping voice (1/2/3) to accuracy metrics
        """
        voice_accuracy = {
            1: {'frequency': 0.0, 'waveform': 0.0, 'adsr': 0.0, 'pulse': 0.0, 'overall': 0.0},
            2: {'frequency': 0.0, 'waveform': 0.0, 'adsr': 0.0, 'pulse': 0.0, 'overall': 0.0},
            3: {'frequency': 0.0, 'waveform': 0.0, 'adsr': 0.0, 'pulse': 0.0, 'overall': 0.0}
        }

        # Voice register offsets
        voice_regs = {
            1: {'freq': [0x00, 0x01], 'pulse': [0x02, 0x03], 'control': [0x04], 'adsr': [0x05, 0x06]},
            2: {'freq': [0x07, 0x08], 'pulse': [0x09, 0x0A], 'control': [0x0B], 'adsr': [0x0C, 0x0D]},
            3: {'freq': [0x0E, 0x0F], 'pulse': [0x10, 0x11], 'control': [0x12], 'adsr': [0x13, 0x14]}
        }

        max_frames = min(len(frames_a), len(frames_b))

        for voice in [1, 2, 3]:
            regs = voice_regs[voice]

            # Calculate accuracy for each component
            for component in ['freq', 'pulse', 'control', 'adsr']:
                reg_list = regs[component]
                matches = 0
                total = 0

                for frame_idx in range(max_frames):
                    frame_a = frames_a[frame_idx]
                    frame_b = frames_b[frame_idx]

                    for reg in reg_list:
                        if reg in frame_a or reg in frame_b:
                            total += 1
                            if frame_a.get(reg) == frame_b.get(reg):
                                matches += 1

                accuracy = (matches / total) * 100.0 if total > 0 else 100.0

                if component == 'freq':
                    voice_accuracy[voice]['frequency'] = accuracy
                elif component == 'pulse':
                    voice_accuracy[voice]['pulse'] = accuracy
                elif component == 'control':
                    voice_accuracy[voice]['waveform'] = accuracy
                elif component == 'adsr':
                    voice_accuracy[voice]['adsr'] = accuracy

            # Overall voice accuracy (average of components)
            components = ['frequency', 'waveform', 'adsr', 'pulse']
            overall = sum(voice_accuracy[voice][c] for c in components) / len(components)
            voice_accuracy[voice]['overall'] = overall

        return voice_accuracy


def main():
    """Test the comparator with sample data"""
    print("TraceComparator module loaded successfully")
    print(f"Classes available: {TraceComparisonMetrics.__name__}, {TraceComparator.__name__}")


if __name__ == '__main__':
    main()
