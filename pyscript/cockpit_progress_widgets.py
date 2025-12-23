#!/usr/bin/env python3
"""
Cockpit Progress Widgets - UI components for progress estimation display

Provides widgets to display estimated times and progress predictions
in the Conversion Cockpit.

Version: 1.0.0
Date: 2025-12-23
"""

from typing import Optional, Dict
from progress_estimator import ProgressEstimator

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
        QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
        QFrame
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
    from PyQt6.QtGui import QFont, QColor
except ImportError:
    raise ImportError("PyQt6 is required for Progress Widgets")


class ProgressEstimateSignals(QObject):
    """Signals for progress updates"""
    time_estimate_updated = pyqtSignal(str, str)  # estimated_time, completion_time


class BatchProgressEstimateWidget(QWidget):
    """Widget for displaying batch progress estimation"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.estimator = ProgressEstimator()
        self.init_ui()
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self.update_estimates)

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Group
        group = QGroupBox("Time Estimation")
        group_layout = QVBoxLayout()

        # Estimated time row
        time_layout = QHBoxLayout()
        time_label = QLabel("Estimated Duration:")
        time_font = QFont()
        time_font.setBold(True)
        time_label.setFont(time_font)
        time_layout.addWidget(time_label)

        self.estimated_time_label = QLabel("-- (building history)")
        self.estimated_time_label.setStyleSheet("color: #0066cc; font-weight: bold; font-size: 14pt;")
        time_layout.addWidget(self.estimated_time_label)

        time_layout.addStretch()
        group_layout.addLayout(time_layout)

        # Completion time row
        completion_layout = QHBoxLayout()
        completion_label = QLabel("Estimated Completion:")
        completion_label.setFont(time_font)
        completion_layout.addWidget(completion_label)

        self.completion_time_label = QLabel("-- (building history)")
        self.completion_time_label.setStyleSheet("color: #006600; font-weight: bold; font-size: 12pt;")
        completion_layout.addWidget(self.completion_time_label)

        completion_layout.addStretch()
        group_layout.addLayout(completion_layout)

        # Confidence note
        confidence_label = QLabel("(Accuracy improves as more batches are processed)")
        confidence_label.setStyleSheet("color: #666666; font-size: 9pt; font-style: italic;")
        group_layout.addWidget(confidence_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        group_layout.addWidget(separator)

        # Per-step breakdown label
        breakdown_label = QLabel("Per-Step Estimates:")
        breakdown_label.setFont(time_font)
        group_layout.addWidget(breakdown_label)

        # Step breakdown table
        self.breakdown_table = QTableWidget()
        self.breakdown_table.setColumnCount(4)
        self.breakdown_table.setHorizontalHeaderLabels([
            "Step", "Per File", "Samples", "Confidence"
        ])

        # Configure header
        header = self.breakdown_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.breakdown_table.setMaximumHeight(150)
        self.breakdown_table.setAlternatingRowColors(True)
        group_layout.addWidget(self.breakdown_table)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def update_estimates(self, file_count: int = 0, step_names: list = None):
        """
        Update progress estimates.

        Args:
            file_count: Number of files to process
            step_names: List of enabled steps
        """
        if file_count <= 0:
            self.estimated_time_label.setText("-- (need file count)")
            self.completion_time_label.setText("-- (need file count)")
            return

        if not step_names:
            step_names = []

        # Get batch estimate
        total_seconds, breakdown = self.estimator.get_batch_estimate(step_names, file_count)
        estimated_duration = self.estimator.format_duration(total_seconds)
        completion_time = self.estimator.get_estimated_completion_time(total_seconds)

        # Update displays
        self.estimated_time_label.setText(estimated_duration)
        self.completion_time_label.setText(completion_time)

        # Update per-step breakdown table
        self._update_breakdown_table(step_names)

    def _update_breakdown_table(self, step_names: list):
        """Update the per-step breakdown table"""
        self.breakdown_table.setRowCount(0)

        stats = self.estimator.get_all_statistics()

        for step in step_names:
            if step not in stats:
                continue

            step_stat = stats[step]
            row = self.breakdown_table.rowCount()
            self.breakdown_table.insertRow(row)

            # Step name
            name_item = QTableWidgetItem(step)
            self.breakdown_table.setItem(row, 0, name_item)

            # Per-file time
            time_str = self.estimator.format_duration(step_stat['estimate'])
            time_item = QTableWidgetItem(time_str)
            time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.breakdown_table.setItem(row, 1, time_item)

            # Sample count
            count_item = QTableWidgetItem(str(step_stat['count']))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.breakdown_table.setItem(row, 2, count_item)

            # Confidence
            confidence = step_stat['confidence']
            confidence_item = QTableWidgetItem(confidence)
            confidence_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Color code confidence
            if confidence == "high":
                confidence_item.setBackground(QColor("#ccffcc"))
            elif confidence == "medium":
                confidence_item.setBackground(QColor("#ffffcc"))
            elif confidence == "low":
                confidence_item.setBackground(QColor("#ffcccc"))
            else:
                confidence_item.setBackground(QColor("#f0f0f0"))

            self.breakdown_table.setItem(row, 3, confidence_item)

    def get_estimator(self) -> ProgressEstimator:
        """Get the underlying estimator"""
        return self.estimator

    def reset_estimates(self):
        """Reset all estimates"""
        self.estimator.reset_timings()
        self.estimated_time_label.setText("-- (cleared)")
        self.completion_time_label.setText("-- (cleared)")
        self.breakdown_table.setRowCount(0)


class ProgressInfoPanel(QWidget):
    """Compact panel showing time estimation during conversion"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.estimator = ProgressEstimator()
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(20)

        # Estimated time
        layout.addWidget(QLabel("Est. Duration:"))
        self.time_label = QLabel("--")
        self.time_label.setStyleSheet("font-weight: bold; font-size: 12pt; color: #0066cc;")
        layout.addWidget(self.time_label)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        separator.setMaximumWidth(20)
        layout.addWidget(separator)

        # Completion time
        layout.addWidget(QLabel("Completion:"))
        self.completion_label = QLabel("--")
        self.completion_label.setStyleSheet("font-weight: bold; font-size: 11pt; color: #006600;")
        layout.addWidget(self.completion_label)

        layout.addStretch()

    def update_estimate(self, file_count: int, step_names: list):
        """Update estimate display"""
        if file_count <= 0 or not step_names:
            self.time_label.setText("--")
            self.completion_label.setText("--")
            return

        total_seconds, _ = self.estimator.get_batch_estimate(step_names, file_count)
        time_str = self.estimator.format_duration(total_seconds)
        completion_str = self.estimator.get_estimated_completion_time(total_seconds)

        self.time_label.setText(time_str)
        self.completion_label.setText(completion_str)

    def get_estimator(self) -> ProgressEstimator:
        """Get the underlying estimator"""
        return self.estimator


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # Test progress estimate widget
    widget = BatchProgressEstimateWidget()
    widget.setWindowTitle("Progress Estimate Widget Test")
    widget.update_estimates(
        file_count=10,
        step_names=["conversion", "packing", "validation"]
    )
    widget.show()

    sys.exit(app.exec())
