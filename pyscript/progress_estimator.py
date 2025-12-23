#!/usr/bin/env python3
"""
Progress Estimator - Estimates conversion progress based on historical performance

Tracks per-step execution times, calculates statistics, and provides intelligent
time estimates for conversions based on actual historical data.

Version: 1.0.0
Date: 2025-12-23
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from statistics import mean, median, stdev
import time


@dataclass
class StepTimingStats:
    """Statistics for a single pipeline step"""
    step_id: str
    execution_count: int = 0
    total_time: float = 0.0  # seconds
    timings: List[float] = field(default_factory=list)  # Individual timings
    min_time: float = 0.0
    max_time: float = 0.0
    mean_time: float = 0.0
    median_time: float = 0.0
    std_dev: float = 0.0

    def add_timing(self, seconds: float):
        """Add a new timing measurement"""
        self.timings.append(seconds)
        self.execution_count += 1
        self.total_time += seconds
        self._calculate_stats()

    def _calculate_stats(self):
        """Calculate statistics from timings"""
        if not self.timings:
            return

        # Basic stats
        self.min_time = min(self.timings)
        self.max_time = max(self.timings)
        self.mean_time = mean(self.timings)
        self.median_time = median(self.timings)

        # Standard deviation (only if we have enough samples)
        if len(self.timings) > 1:
            self.std_dev = stdev(self.timings)
        else:
            self.std_dev = 0.0

    def get_estimated_time(self) -> float:
        """Get estimated time for next execution (median with outlier handling)"""
        if not self.timings:
            return 0.0

        # Use median for robustness against outliers
        if len(self.timings) >= 3:
            # Filter extreme outliers (>3 std devs)
            filtered = [t for t in self.timings if abs(t - self.mean_time) <= 3 * self.std_dev]
            if filtered:
                return median(filtered)

        # Fallback to median of all timings
        return self.median_time

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'step_id': self.step_id,
            'execution_count': self.execution_count,
            'total_time': self.total_time,
            'timings': self.timings,
            'min_time': self.min_time,
            'max_time': self.max_time,
            'mean_time': self.mean_time,
            'median_time': self.median_time,
            'std_dev': self.std_dev
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'StepTimingStats':
        """Create from dictionary"""
        stats = cls(step_id=data['step_id'])
        stats.execution_count = data.get('execution_count', 0)
        stats.total_time = data.get('total_time', 0.0)
        stats.timings = data.get('timings', [])
        stats.min_time = data.get('min_time', 0.0)
        stats.max_time = data.get('max_time', 0.0)
        stats.mean_time = data.get('mean_time', 0.0)
        stats.median_time = data.get('median_time', 0.0)
        stats.std_dev = data.get('std_dev', 0.0)
        return stats


class ProgressEstimator:
    """Tracks execution times and estimates progress"""

    # File for storing timing data
    TIMING_FILE = Path.home() / '.sidm2' / 'step_timings.json'

    # Keep last 20 timings per step (for statistics)
    MAX_TIMINGS_PER_STEP = 20

    def __init__(self):
        """Initialize progress estimator"""
        self.step_stats: Dict[str, StepTimingStats] = {}
        self._current_step_name: Optional[str] = None
        self._step_start_time: Optional[float] = None
        self._ensure_data_dir()
        self.load_timings()

    def _ensure_data_dir(self):
        """Ensure data directory exists"""
        self.TIMING_FILE.parent.mkdir(parents=True, exist_ok=True)

    def record_step_start(self, step_name: str):
        """Record that a step has started"""
        self._current_step_name = step_name
        self._step_start_time = time.time()

    def record_step_complete(self, step_name: str) -> float:
        """
        Record that a step has completed.

        Args:
            step_name: Name of the completed step

        Returns:
            Elapsed time in seconds
        """
        if not self._step_start_time:
            return 0.0

        elapsed = time.time() - self._step_start_time

        # Get or create stats for this step
        if step_name not in self.step_stats:
            self.step_stats[step_name] = StepTimingStats(step_id=step_name)

        # Add timing
        stats = self.step_stats[step_name]
        stats.add_timing(elapsed)

        # Keep only last MAX_TIMINGS_PER_STEP
        if len(stats.timings) > self.MAX_TIMINGS_PER_STEP:
            removed = stats.timings.pop(0)
            stats.total_time -= removed
            stats.execution_count = len(stats.timings)

        # Save timings
        self.save_timings()

        # Reset
        self._current_step_name = None
        self._step_start_time = None

        return elapsed

    def get_step_estimate(self, step_name: str) -> float:
        """
        Get estimated time for a step.

        Args:
            step_name: Name of the step

        Returns:
            Estimated time in seconds
        """
        if step_name not in self.step_stats:
            # Default estimate for unknown steps
            return 10.0

        return self.step_stats[step_name].get_estimated_time()

    def get_batch_estimate(self, step_names: List[str], file_count: int) -> Tuple[float, Dict]:
        """
        Get estimated time for entire batch.

        Args:
            step_names: List of enabled pipeline steps
            file_count: Number of files to process

        Returns:
            Tuple of (total_seconds, per_step_breakdown)
        """
        breakdown = {}
        total_seconds = 0.0

        for step in step_names:
            step_estimate = self.get_step_estimate(step)
            breakdown[step] = step_estimate
            total_seconds += step_estimate

        # Total is per-file time * file count
        total_seconds *= file_count

        return total_seconds, breakdown

    def format_duration(self, seconds: float) -> str:
        """
        Format seconds as human-readable duration.

        Args:
            seconds: Duration in seconds

        Returns:
            Formatted string (e.g., "2h 15m 30s")
        """
        if seconds < 0:
            return "unknown"

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)

    def get_estimated_completion_time(self, total_seconds: float) -> str:
        """
        Get estimated completion time.

        Args:
            total_seconds: Total duration in seconds

        Returns:
            Formatted completion time string
        """
        from datetime import datetime, timedelta
        completion = datetime.now() + timedelta(seconds=total_seconds)
        return completion.strftime("%H:%M:%S")

    def get_confidence_level(self, step_name: str) -> str:
        """
        Get confidence level for estimate.

        Args:
            step_name: Name of the step

        Returns:
            Confidence level: "high", "medium", "low", or "none"
        """
        if step_name not in self.step_stats:
            return "none"

        stats = self.step_stats[step_name]

        if stats.execution_count >= 10:
            return "high"
        elif stats.execution_count >= 5:
            return "medium"
        elif stats.execution_count >= 2:
            return "low"
        else:
            return "none"

    def save_timings(self):
        """Save timing data to file"""
        try:
            data = {
                step_name: stats.to_dict()
                for step_name, stats in self.step_stats.items()
            }
            with open(self.TIMING_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving timing data: {e}")

    def load_timings(self):
        """Load timing data from file"""
        if not self.TIMING_FILE.exists():
            self.step_stats = {}
            return

        try:
            with open(self.TIMING_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.step_stats = {
                    step_name: StepTimingStats.from_dict(stats_data)
                    for step_name, stats_data in data.items()
                }
        except Exception as e:
            print(f"Error loading timing data: {e}")
            self.step_stats = {}

    def reset_timings(self):
        """Reset all timing data"""
        self.step_stats = {}
        if self.TIMING_FILE.exists():
            self.TIMING_FILE.unlink()

    def get_all_statistics(self) -> Dict:
        """Get all statistics for display"""
        return {
            step_name: {
                'count': stats.execution_count,
                'mean': stats.mean_time,
                'median': stats.median_time,
                'min': stats.min_time,
                'max': stats.max_time,
                'std_dev': stats.std_dev,
                'estimate': stats.get_estimated_time(),
                'confidence': self.get_confidence_level(step_name)
            }
            for step_name, stats in self.step_stats.items()
        }

    def __repr__(self) -> str:
        """String representation"""
        tracked = len(self.step_stats)
        total_measurements = sum(s.execution_count for s in self.step_stats.values())
        return f"ProgressEstimator({tracked} steps, {total_measurements} measurements)"


def main():
    """Test the progress estimator"""
    print("Progress Estimator Test")
    print("=" * 70)

    estimator = ProgressEstimator()

    # Simulate some step executions
    print("\nSimulating step executions...")
    steps = ["conversion", "packing", "validation", "siddump_original"]

    import random
    for i in range(5):
        for step in steps:
            estimator.record_step_start(step)
            # Simulate execution time (10-30 seconds)
            time.sleep(0.01)  # Simulate work
            elapsed = estimator.record_step_complete(step)
            print(f"  {step}: {elapsed:.2f}s")

    # Print statistics
    print("\nEstimated times per step:")
    for step_name, stats in estimator.step_stats.items():
        estimate = estimator.get_step_estimate(step_name)
        confidence = estimator.get_confidence_level(step_name)
        print(f"  {step_name}: {estimate:.1f}s (confidence: {confidence})")

    # Estimate batch
    print("\nBatch estimation (5 files, all steps):")
    total, breakdown = estimator.get_batch_estimate(steps, 5)
    print(f"  Estimated total: {estimator.format_duration(total)}")
    print(f"  Per step:")
    for step, time_per_file in breakdown.items():
        print(f"    {step}: {estimator.format_duration(time_per_file)} per file")

    print("\n" + "=" * 70)
    print(f"Timing file: {estimator.TIMING_FILE}")
    print(f"Estimator: {estimator}")


if __name__ == '__main__':
    main()
