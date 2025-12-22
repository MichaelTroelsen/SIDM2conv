#!/usr/bin/env python3
"""
Cockpit Widgets - Custom widgets for Conversion Cockpit

Custom PyQt6 widgets for stats cards, progress displays, file lists,
and log streaming.

Version: 1.0.0
Date: 2025-12-22
"""

from typing import List, Tuple, Optional

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
        QProgressBar, QListWidget, QListWidgetItem, QTextEdit,
        QCheckBox, QGroupBox
    )
    from PyQt6.QtCore import Qt, pyqtSignal
    from PyQt6.QtGui import QFont, QColor, QTextCursor, QDragEnterEvent, QDropEvent
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    print("ERROR: PyQt6 is required for cockpit widgets")
    import sys
    sys.exit(1)


class StatsCard(QGroupBox):
    """
    Statistics card widget for dashboard

    Displays a title and multiple key-value pairs in a card format.
    """

    def __init__(self, title: str, stats: List[Tuple[str, str]], parent=None):
        super().__init__(title, parent)
        self.stats_labels = {}
        self.init_ui(stats)

    def init_ui(self, stats: List[Tuple[str, str]]):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # Title styling
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #ccc;
                border-radius: 5px;
                margin-top: 10px;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                background-color: white;
            }
        """)

        # Add stat rows
        for key, value in stats:
            row_layout = QHBoxLayout()
            row_layout.setSpacing(5)

            key_label = QLabel(f"{key}:")
            key_label.setStyleSheet("font-weight: normal; color: #666;")
            row_layout.addWidget(key_label)

            value_label = QLabel(value)
            value_label.setStyleSheet("font-weight: bold; color: #000;")
            row_layout.addWidget(value_label)
            row_layout.addStretch()

            # Store reference to value label
            self.stats_labels[key] = value_label

            layout.addLayout(row_layout)

        layout.addStretch()
        self.setLayout(layout)

    def update_stat(self, key: str, value: str):
        """Update a stat value"""
        if key in self.stats_labels:
            self.stats_labels[key].setText(value)


class ProgressWidget(QWidget):
    """
    Progress widget with file and step progress bars

    Displays current file progress and overall step progress.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # File progress
        file_label = QLabel("File Progress:")
        file_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(file_label)

        self.file_progress = QProgressBar()
        self.file_progress.setMaximum(100)
        self.file_progress.setValue(0)
        self.file_progress.setFormat("%p% (%v/%m files)")
        layout.addWidget(self.file_progress)

        # Step progress
        step_label = QLabel("Step Progress:")
        step_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(step_label)

        self.step_progress = QProgressBar()
        self.step_progress.setMaximum(100)
        self.step_progress.setValue(0)
        self.step_progress.setFormat("%p% (Step %v/%m)")
        layout.addWidget(self.step_progress)

        self.setLayout(layout)

    def set_file_progress(self, current: int, total: int):
        """Update file progress"""
        self.file_progress.setMaximum(total)
        self.file_progress.setValue(current)

    def set_step_progress(self, current: int, total: int):
        """Update step progress"""
        self.step_progress.setMaximum(total)
        self.step_progress.setValue(current)

    def reset(self):
        """Reset both progress bars"""
        self.file_progress.setValue(0)
        self.step_progress.setValue(0)


class FileListWidget(QWidget):
    """
    File list widget with checkboxes for selection

    Displays a list of files with checkboxes for batch selection.
    Supports drag-and-drop for adding files.
    """

    files_changed = pyqtSignal(list)  # Emits list of selected files

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.setup_drag_drop()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;
                background-color: white;
            }
            QListWidget::item {
                padding: 5px;
            }
            QListWidget::item:hover {
                background-color: #e0e0e0;
            }
        """)
        layout.addWidget(self.list_widget)

        self.setLayout(layout)

    def setup_drag_drop(self):
        """Enable drag and drop"""
        self.setAcceptDrops(True)
        self.list_widget.setAcceptDrops(True)

    def add_file(self, file_path: str, checked: bool = True):
        """Add a file to the list"""
        item = QListWidgetItem(file_path)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        self.list_widget.addItem(item)
        self.files_changed.emit(self.get_selected_files())

    def add_files(self, file_paths: List[str], checked: bool = True):
        """Add multiple files to the list"""
        for file_path in file_paths:
            self.add_file(file_path, checked)

    def remove_selected(self):
        """Remove selected items from list"""
        for item in self.list_widget.selectedItems():
            self.list_widget.takeItem(self.list_widget.row(item))
        self.files_changed.emit(self.get_selected_files())

    def clear(self):
        """Clear all items"""
        self.list_widget.clear()
        self.files_changed.emit([])

    def select_all(self):
        """Check all items"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.CheckState.Checked)
        self.files_changed.emit(self.get_selected_files())

    def select_none(self):
        """Uncheck all items"""
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            item.setCheckState(Qt.CheckState.Unchecked)
        self.files_changed.emit(self.get_selected_files())

    def get_selected_files(self) -> List[str]:
        """Get list of checked files"""
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        return selected

    def get_all_files(self) -> List[str]:
        """Get list of all files"""
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter event"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        if event.mimeData().hasUrls():
            files = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith('.sid'):
                    files.append(file_path)

            if files:
                self.add_files(files)
                event.acceptProposedAction()


class LogStreamWidget(QTextEdit):
    """
    Log streaming widget with color-coded output

    Displays log messages with color coding based on log level.
    Supports auto-scrolling and line limits.
    """

    # Color scheme
    COLORS = {
        "ERROR": "#d32f2f",   # Red
        "WARN": "#f57c00",    # Orange
        "INFO": "#333333",    # Dark gray
        "DEBUG": "#0288d1"    # Blue
    }

    def __init__(self, max_lines: int = 10000, parent=None):
        super().__init__(parent)
        self.max_lines = max_lines
        self.line_count = 0
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #ccc;
            }
        """)

        # Set fixed-width font
        font = QFont("Consolas", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)

    def append_log(self, level: str, message: str):
        """Append a log message with color coding"""
        # Get color for level
        color = self.COLORS.get(level.upper(), self.COLORS["INFO"])

        # Format message with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")

        # Create HTML formatted message
        html = f'<span style="color: #888;">[{timestamp}]</span> '
        html += f'<span style="color: {color}; font-weight: bold;">[{level:5s}]</span> '
        html += f'<span style="color: #d4d4d4;">{self._escape_html(message)}</span>'

        # Append to text edit
        self.append(html)

        # Limit line count
        self.line_count += 1
        if self.line_count > self.max_lines:
            # Remove old lines
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            cursor.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor,
                              self.line_count - self.max_lines)
            cursor.removeSelectedText()
            self.line_count = self.max_lines

        # Auto-scroll to bottom
        self.moveCursor(QTextCursor.MoveOperation.End)

    def clear(self):
        """Clear the log display"""
        super().clear()
        self.line_count = 0

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters"""
        return (text.replace("&", "&amp;")
                   .replace("<", "&lt;")
                   .replace(">", "&gt;")
                   .replace('"', "&quot;")
                   .replace("'", "&#39;"))


class ConfigPanel(QWidget):
    """
    Configuration panel widget

    Provides controls for configuring pipeline parameters.
    """

    config_changed = pyqtSignal(dict)  # Emits configuration dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Mode selection
        mode_group = QGroupBox("Mode")
        mode_layout = QVBoxLayout()

        # TODO: Add radio buttons for Simple/Advanced/Custom

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Driver configuration
        driver_group = QGroupBox("Driver Configuration")
        driver_layout = QVBoxLayout()

        # TODO: Add driver dropdown, output directory selection, etc.

        driver_group.setLayout(driver_layout)
        layout.addWidget(driver_group)

        # Pipeline steps
        steps_group = QGroupBox("Pipeline Steps")
        steps_layout = QVBoxLayout()

        # TODO: Add checkboxes for each pipeline step

        steps_group.setLayout(steps_layout)
        layout.addWidget(steps_group)

        layout.addStretch()
        self.setLayout(layout)


class StatusBadge(QLabel):
    """
    Status badge widget

    Displays a colored status indicator with icon and text.
    """

    BADGE_STYLES = {
        "pending": ("⏳", "#9e9e9e", "Pending"),
        "running": ("⏳", "#2196F3", "Running"),
        "passed": ("✅", "#4CAF50", "Passed"),
        "failed": ("❌", "#f44336", "Failed"),
        "warning": ("⚠️", "#FF9800", "Warning")
    }

    def __init__(self, status: str = "pending", parent=None):
        super().__init__(parent)
        self.set_status(status)

    def set_status(self, status: str):
        """Update the badge status"""
        icon, color, text = self.BADGE_STYLES.get(status, self.BADGE_STYLES["pending"])
        self.setText(f"{icon} {text}")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                color: white;
                padding: 3px 8px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }}
        """)
