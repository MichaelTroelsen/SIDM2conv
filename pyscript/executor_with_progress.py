#!/usr/bin/env python3
"""
Executor with Progress Estimation - Extends ConversionExecutor with progress tracking

Integrates the ProgressEstimator with ConversionExecutor to track execution times
and provide intelligent progress estimation for batch conversions.

Version: 1.0.0
Date: 2025-12-23
"""

from typing import Optional
from progress_estimator import ProgressEstimator
from conversion_executor import ConversionExecutor


class ExecutorWithProgress(ConversionExecutor):
    """ConversionExecutor extended with progress estimation"""

    def __init__(self, config, output_dir=None):
        """Initialize executor with progress estimation"""
        super().__init__(config, output_dir)
        self.progress_estimator = ProgressEstimator()

        # Connect signals to progress tracking
        self.step_started.connect(self._on_step_started)
        self.step_completed.connect(self._on_step_completed)

        # Store current step for tracking
        self._current_step_name: Optional[str] = None

    def _on_step_started(self, step_name: str, step_num: int, total_steps: int):
        """Handle step started signal"""
        self._current_step_name = step_name
        self.progress_estimator.record_step_start(step_name)

    def _on_step_completed(self, step_name: str, success: bool, message: str):
        """Handle step completed signal"""
        elapsed = self.progress_estimator.record_step_complete(step_name)
        self._current_step_name = None

    def get_batch_time_estimate(self, file_count: int) -> str:
        """
        Get estimated time for entire batch.

        Args:
            file_count: Number of files to process

        Returns:
            Formatted time string (e.g., "2h 15m 30s")
        """
        enabled_steps = self.config.get_enabled_steps()
        total_seconds, _ = self.progress_estimator.get_batch_estimate(enabled_steps, file_count)
        return self.progress_estimator.format_duration(total_seconds)

    def get_step_time_estimate(self, step_name: str) -> str:
        """
        Get estimated time for a single step.

        Args:
            step_name: Name of the step

        Returns:
            Formatted time string
        """
        seconds = self.progress_estimator.get_step_estimate(step_name)
        return self.progress_estimator.format_duration(seconds)

    def get_estimated_completion_time(self, total_seconds: float) -> str:
        """
        Get estimated completion time.

        Args:
            total_seconds: Total duration in seconds

        Returns:
            Formatted time string
        """
        # Get total duration for current batch
        enabled_steps = self.config.get_enabled_steps()
        if not hasattr(self, '_files_being_processed'):
            file_count = 1
        else:
            file_count = len(self._files_being_processed)

        total, _ = self.progress_estimator.get_batch_estimate(enabled_steps, file_count)
        return self.progress_estimator.get_estimated_completion_time(total)

    def reset_progress_data(self):
        """Reset all progress tracking data"""
        self.progress_estimator.reset_timings()

    def get_progress_stats(self):
        """Get all progress statistics"""
        return self.progress_estimator.get_all_statistics()


def main():
    """Test executor with progress"""
    print("Executor with Progress Test")
    print("=" * 70)

    # This would require actual executor setup
    print("Integration module created successfully")
    print("Use ExecutorWithProgress instead of ConversionExecutor")
    print("=" * 70)


if __name__ == '__main__':
    main()
