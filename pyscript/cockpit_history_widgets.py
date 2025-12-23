#!/usr/bin/env python3
"""
Cockpit History Widgets - UI components for batch history management

Provides history dropdown, save/load buttons, and history browser widgets
for the Conversion Cockpit.

Version: 1.0.0
Date: 2025-12-23
"""

from typing import Optional, Callable
from batch_history_manager import BatchHistoryManager, BatchHistoryEntry

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton,
        QGroupBox, QLabel, QDialog, QListWidget, QListWidgetItem,
        QMessageBox, QAbstractItemView
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QObject
    from PyQt6.QtGui import QFont, QColor
except ImportError:
    raise ImportError("PyQt6 is required for Cockpit History Widgets")


class HistorySignals(QObject):
    """Signals for history operations"""
    history_loaded = pyqtSignal(str)  # entry_id
    history_saved = pyqtSignal(str, int)  # entry_id, file_count
    history_deleted = pyqtSignal(str)  # entry_id


class HistoryControlWidget(QWidget):
    """Widget for batch history controls (dropdown + buttons)"""

    signals = HistorySignals()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = BatchHistoryManager()
        self.on_load_callback: Optional[Callable[[str], None]] = None
        self.init_ui()
        self.refresh_history()

    def init_ui(self):
        """Initialize UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Label
        label = QLabel("Recent Batches:")
        layout.addWidget(label)

        # History dropdown
        self.history_combo = QComboBox()
        self.history_combo.addItem("-- No history --")
        self.history_combo.currentIndexChanged.connect(self.on_history_selected)
        layout.addWidget(self.history_combo, 1)

        # Load button
        self.load_btn = QPushButton("Load")
        self.load_btn.setMaximumWidth(80)
        self.load_btn.clicked.connect(self.on_load_clicked)
        self.load_btn.setEnabled(False)
        layout.addWidget(self.load_btn)

        # Browse button
        self.browse_btn = QPushButton("Browse All")
        self.browse_btn.setMaximumWidth(100)
        self.browse_btn.clicked.connect(self.on_browse_clicked)
        layout.addWidget(self.browse_btn)

        # Clear button
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setMaximumWidth(80)
        self.clear_btn.clicked.connect(self.on_clear_clicked)
        layout.addWidget(self.clear_btn)

    def refresh_history(self):
        """Refresh history dropdown from storage"""
        self.history_combo.blockSignals(True)
        self.history_combo.clear()

        history = self.manager.get_history()
        if not history:
            self.history_combo.addItem("-- No history --", None)
            self.load_btn.setEnabled(False)
        else:
            for entry in history:
                display_text = self.manager.format_entry_display(entry)
                self.history_combo.addItem(display_text, entry.id)
            self.load_btn.setEnabled(True)

        self.history_combo.blockSignals(False)

    def on_history_selected(self, index: int):
        """Handle history dropdown selection"""
        entry_id = self.history_combo.currentData()
        self.load_btn.setEnabled(entry_id is not None)

    def on_load_clicked(self):
        """Load selected history entry"""
        entry_id = self.history_combo.currentData()
        if entry_id and self.on_load_callback:
            try:
                self.on_load_callback(entry_id)
                self.signals.history_loaded.emit(entry_id)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load history: {e}")

    def on_browse_clicked(self):
        """Open history browser dialog"""
        dialog = HistoryBrowserDialog(self.manager, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_id = dialog.get_selected_entry_id()
            if selected_id and self.on_load_callback:
                try:
                    self.on_load_callback(selected_id)
                    self.signals.history_loaded.emit(selected_id)
                    self.refresh_history()
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to load history: {e}")

    def on_clear_clicked(self):
        """Clear all history with confirmation"""
        reply = QMessageBox.question(
            self,
            "Clear History",
            "Are you sure you want to clear all batch history?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.clear_history()
            self.refresh_history()

    def save_batch(self, file_count: int, label: str = "") -> Optional[str]:
        """Save current batch to history"""
        try:
            # Note: The actual config will be passed from the main window
            # This method is called from the main window with the current config
            return None  # Will be set by calling code
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save batch: {e}")
            return None

    def set_on_load_callback(self, callback: Callable[[str], None]):
        """Set callback for when history is loaded"""
        self.on_load_callback = callback


class HistoryBrowserDialog(QDialog):
    """Dialog for browsing and managing batch history"""

    def __init__(self, manager: BatchHistoryManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.selected_entry_id: Optional[str] = None
        self.init_ui()
        self.populate_list()

    def init_ui(self):
        """Initialize dialog UI"""
        self.setWindowTitle("Batch History Browser")
        self.setGeometry(200, 200, 600, 400)

        layout = QVBoxLayout(self)

        # Title
        title = QLabel("Browse Batch History (Last 10)")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title.setFont(title_font)
        layout.addWidget(title)

        # History list
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)

        # Buttons
        button_layout = QHBoxLayout()

        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.on_delete_clicked)
        button_layout.addWidget(delete_btn)

        button_layout.addStretch()

        load_btn = QPushButton("Load")
        load_btn.setDefault(True)
        load_btn.clicked.connect(self.on_load_clicked)
        button_layout.addWidget(load_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def populate_list(self):
        """Populate history list"""
        self.list_widget.clear()

        history = self.manager.get_history()
        if not history:
            item = QListWidgetItem("-- No history available --")
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.list_widget.addItem(item)
            return

        for entry in history:
            display_text = self.manager.format_entry_display(entry)
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, entry.id)

            # Style recent entries
            try:
                from datetime import datetime
                ts = datetime.fromisoformat(entry.timestamp)
                age_minutes = (datetime.now() - ts).total_seconds() / 60
                if age_minutes < 60:
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)
                    item.setBackground(QColor("#e8f4f8"))
            except:
                pass

            self.list_widget.addItem(item)

    def on_item_double_clicked(self, item):
        """Handle double-click to load"""
        self.on_load_clicked()

    def on_load_clicked(self):
        """Load selected entry"""
        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_entry_id = current_item.data(Qt.ItemDataRole.UserRole)
            self.accept()

    def on_delete_clicked(self):
        """Delete selected entry"""
        current_item = self.list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a batch to delete")
            return

        entry_id = current_item.data(Qt.ItemDataRole.UserRole)
        if not entry_id:
            return

        reply = QMessageBox.question(
            self,
            "Delete Batch",
            "Are you sure you want to delete this batch history?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.manager.delete_entry(entry_id)
            self.populate_list()

    def get_selected_entry_id(self) -> Optional[str]:
        """Get the selected entry ID"""
        return self.selected_entry_id


class BatchHistorySectionWidget(QWidget):
    """Complete section widget for batch history in config tab"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = BatchHistoryManager()
        self.history_control: Optional[HistoryControlWidget] = None
        self.init_ui()

    def init_ui(self):
        """Initialize UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # Group
        group = QGroupBox("Batch History")
        group_layout = QVBoxLayout()

        # History control widget
        self.history_control = HistoryControlWidget(self)
        group_layout.addWidget(self.history_control)

        # Save current batch button
        save_layout = QHBoxLayout()
        save_layout.addStretch()

        self.save_btn = QPushButton("Save Current Batch to History")
        self.save_btn.clicked.connect(self.on_save_batch_clicked)
        save_layout.addWidget(self.save_btn)

        group_layout.addLayout(save_layout)

        group.setLayout(group_layout)
        layout.addWidget(group)

    def on_save_batch_clicked(self):
        """Handle save batch button click"""
        # This will be connected to the main window's save handler
        pass

    def set_on_load_callback(self, callback: Callable[[str], None]):
        """Set callback for when history is loaded"""
        if self.history_control:
            self.history_control.set_on_load_callback(callback)

    def refresh_history(self):
        """Refresh history display"""
        if self.history_control:
            self.history_control.refresh_history()

    def get_manager(self) -> BatchHistoryManager:
        """Get the history manager"""
        return self.manager


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)

    # Test history control
    widget = HistoryControlWidget()
    widget.setWindowTitle("History Control Test")
    widget.show()

    sys.exit(app.exec())
