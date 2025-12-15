#!/usr/bin/env python3
"""
SF2 Viewer GUI - Professional SID Factory II file viewer
Display SF2 files with the same layout as the SID Factory II editor
"""

import sys
import os
from pathlib import Path
from typing import Optional

# Try to import PyQt6, fallback instructions if not available
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
        QLabel, QPushButton, QFileDialog, QHeaderView, QTextEdit, QScrollArea,
        QStatusBar, QMenuBar, QMenu, QMessageBox
    )
    from PyQt6.QtCore import Qt, QMimeData, QUrl, QSize, QTimer
    from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QFont, QColor
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    print("ERROR: PyQt6 is required for the SF2 Viewer")
    print("\nInstall with: pip install PyQt6")
    sys.exit(1)

from sf2_viewer_core import SF2Parser, BlockType, TableDataLayout


class SF2ViewerWindow(QMainWindow):
    """Main window for SF2 viewer application"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SID Factory II SF2 Viewer")
        self.setGeometry(100, 100, 1600, 1000)

        self.parser: Optional[SF2Parser] = None
        self.current_file = None

        self.init_ui()
        self.setup_drag_drop()

    def init_ui(self):
        """Initialize the user interface"""
        # Central widget with main layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Top section: File controls
        top_layout = QHBoxLayout()
        self.file_label = QLabel("No file loaded - Drag and drop an SF2 file or use Browse")
        self.file_label.setStyleSheet("background-color: #f0f0f0; padding: 8px;")
        top_layout.addWidget(self.file_label)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_file)
        top_layout.addWidget(browse_btn)

        layout.addLayout(top_layout)

        # Main content area with tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Overview
        self.overview_tab = self.create_overview_tab()
        self.tabs.addTab(self.overview_tab, "Overview")

        # Tab 2: Header Blocks
        self.blocks_tab = self.create_blocks_tab()
        self.tabs.addTab(self.blocks_tab, "Header Blocks")

        # Tab 3: Tables
        self.tables_tab = self.create_tables_tab()
        self.tabs.addTab(self.tables_tab, "Tables")

        # Tab 4: Memory Map
        self.memory_tab = self.create_memory_tab()
        self.tabs.addTab(self.memory_tab, "Memory Map")

        # Status bar
        self.statusBar().showMessage("Ready")

        # Menu bar
        self.create_menu_bar()

    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        open_action = file_menu.addAction("Open SF2 File...")
        open_action.triggered.connect(self.browse_file)

        file_menu.addSeparator()

        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = help_menu.addAction("About SF2 Viewer")
        about_action.triggered.connect(self.show_about)

    def create_overview_tab(self) -> QWidget:
        """Create the overview tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Validation summary
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setFont(QFont("Courier", 10))
        layout.addWidget(QLabel("File Validation Summary:"))
        layout.addWidget(self.summary_text)

        # Quick info
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setFont(QFont("Courier", 9))
        layout.addWidget(QLabel("File Information:"))
        layout.addWidget(self.info_text)

        return widget

    def create_blocks_tab(self) -> QWidget:
        """Create the header blocks tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Header blocks tree
        self.blocks_tree = QTreeWidget()
        self.blocks_tree.setHeaderLabels(["Block", "Size", "Content"])
        self.blocks_tree.setColumnCount(3)
        layout.addWidget(QLabel("SF2 Header Blocks:"))
        layout.addWidget(self.blocks_tree)

        # Block details
        self.block_details = QTextEdit()
        self.block_details.setReadOnly(True)
        self.block_details.setFont(QFont("Courier", 9))
        self.blocks_tree.itemSelectionChanged.connect(self.on_block_selected)
        layout.addWidget(QLabel("Block Details:"))
        layout.addWidget(self.block_details)

        return widget

    def create_tables_tab(self) -> QWidget:
        """Create the tables tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Table selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Select Table:"))

        self.table_combo = self.create_table_combo()
        selector_layout.addWidget(self.table_combo)

        self.table_combo.currentIndexChanged.connect(self.on_table_selected)
        layout.addLayout(selector_layout)

        # Table display
        self.table_widget = QTableWidget()
        self.table_widget.setMaximumHeight(400)
        layout.addWidget(self.table_widget)

        # Table info
        self.table_info = QTextEdit()
        self.table_info.setReadOnly(True)
        self.table_info.setFont(QFont("Courier", 9))
        self.table_info.setMaximumHeight(100)
        layout.addWidget(self.table_info)

        # Add stretch
        layout.addStretch()

        return widget

    def create_table_combo(self) -> QWidget:
        """Create table selector combo box"""
        from PyQt6.QtWidgets import QComboBox
        combo = QComboBox()
        combo.addItem("Select a table...")
        return combo

    def create_memory_tab(self) -> QWidget:
        """Create the memory map tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.memory_text = QTextEdit()
        self.memory_text.setReadOnly(True)
        self.memory_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.memory_text)

        return widget

    def setup_drag_drop(self):
        """Setup drag and drop support"""
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle drop event"""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                self.load_file(file_path)

    def browse_file(self):
        """Browse for an SF2 file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open SF2 File",
            "",
            "SF2 Files (*.sf2);;All Files (*.*)"
        )

        if file_path:
            self.load_file(file_path)

    def load_file(self, file_path: str):
        """Load and parse an SF2 file"""
        try:
            self.current_file = file_path
            self.file_label.setText(f"Loaded: {Path(file_path).name}")

            # Parse file
            self.parser = SF2Parser(file_path)

            if not self.parser.magic_id:
                QMessageBox.critical(self, "Error", "Failed to parse SF2 file")
                return

            # Update all tabs
            self.update_overview()
            self.update_blocks()
            self.update_tables()
            self.update_memory_map()

            self.statusBar().showMessage(f"Loaded: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def update_overview(self):
        """Update the overview tab"""
        if not self.parser:
            return

        # Summary
        summary = self.parser.get_validation_summary()
        summary_lines = []
        for key, value in summary.items():
            summary_lines.append(f"{key:25s} {value}")

        self.summary_text.setText('\n'.join(summary_lines))

        # File info
        info_lines = [
            f"File: {Path(self.current_file).name}",
            f"Path: {self.current_file}",
            f"Size: {len(self.parser.data):,} bytes",
            f"Magic ID: 0x{self.parser.magic_id:04X}",
            f"Load Address: ${self.parser.load_address:04X}",
            f"",
            f"Driver Information:",
            f"  Name: {self.parser.driver_info.get('name', 'Unknown')}",
            f"  Size: {self.parser.driver_info.get('size_hex', 'Unknown')}",
            f"  Type: {self.parser.driver_info.get('type', 'Unknown')}",
        ]

        if self.parser.driver_common:
            info_lines.extend([
                f"",
                f"Driver Addresses:",
                f"  Init:   ${self.parser.driver_common.init_address:04X}",
                f"  Stop:   ${self.parser.driver_common.stop_address:04X}",
                f"  Play:   ${self.parser.driver_common.play_address:04X}",
            ])

        self.info_text.setText('\n'.join(info_lines))

    def update_blocks(self):
        """Update the header blocks tab"""
        if not self.parser:
            return

        self.blocks_tree.clear()

        for block_type, (offset, data) in self.parser.blocks.items():
            item = QTreeWidgetItem([block_type.name, str(len(data)), f"Offset: ${offset:04X}"])
            item.setData(0, Qt.ItemDataRole.UserRole, block_type)
            self.blocks_tree.addTopLevelItem(item)

        self.blocks_tree.resizeColumnToContents(0)
        self.blocks_tree.resizeColumnToContents(1)

    def on_block_selected(self):
        """Handle block selection"""
        items = self.blocks_tree.selectedItems()
        if not items:
            return

        item = items[0]
        block_type = item.data(0, Qt.ItemDataRole.UserRole)

        if not block_type or block_type not in self.parser.blocks:
            return

        offset, data = self.parser.blocks[block_type]

        details = []
        details.append(f"Block Type: {block_type.name} (0x{block_type.value:02X})")
        details.append(f"File Offset: ${offset:04X}")
        details.append(f"Data Size: {len(data)} bytes")
        details.append("")
        details.append("Hex Dump:")
        details.append(self.format_hex_dump(data))

        if block_type == BlockType.DESCRIPTOR and self.parser.driver_info:
            details.append("")
            details.append("Parsed Driver Info:")
            for key, value in self.parser.driver_info.items():
                details.append(f"  {key}: {value}")

        elif block_type == BlockType.DRIVER_COMMON and self.parser.driver_common:
            details.append("")
            details.append("Parsed Driver Addresses:")
            for key, value in self.parser.driver_common.to_dict().items():
                details.append(f"  {key}: ${value:04X}")

        self.block_details.setText('\n'.join(details))

    def update_tables(self):
        """Update the tables tab"""
        if not self.parser:
            return

        # Populate combo box
        self.table_combo.clear()
        self.table_combo.addItem("Select a table...")

        for desc in self.parser.table_descriptors:
            self.table_combo.addItem(f"{desc.name} ({desc.row_count}x{desc.column_count})", desc)

    def on_table_selected(self, index):
        """Handle table selection"""
        if index <= 0 or not self.parser:
            self.table_widget.clearContents()
            self.table_info.clear()
            return

        descriptor = self.table_combo.itemData(index)
        if not descriptor:
            return

        # Get table data
        table_data = self.parser.get_table_data(descriptor)

        # Display table
        self.table_widget.setRowCount(len(table_data))
        self.table_widget.setColumnCount(len(table_data[0]) if table_data else 0)

        for row_idx, row_data in enumerate(table_data):
            for col_idx, value in enumerate(row_data):
                item = QTableWidgetItem(f"0x{value:02X}")
                item.setFont(QFont("Courier", 9))
                self.table_widget.setItem(row_idx, col_idx, item)

        # Set headers
        self.table_widget.setHorizontalHeaderLabels([f"C{i}" for i in range(len(table_data[0]))] if table_data else [])
        self.table_widget.setVerticalHeaderLabels([f"R{i}" for i in range(len(table_data))])

        # Info
        info_lines = [
            f"Table: {descriptor.name}",
            f"Address: ${descriptor.address:04X}",
            f"Dimensions: {descriptor.row_count} rows × {descriptor.column_count} columns",
            f"Layout: {descriptor.data_layout.name}",
            f"Type: 0x{descriptor.type:02X}",
            f"ID: {descriptor.id}",
            f"Size: {descriptor.row_count * descriptor.column_count} bytes",
        ]

        self.table_info.setText('\n'.join(info_lines))

    def update_memory_map(self):
        """Update the memory map tab"""
        if not self.parser:
            return

        memory_map = self.parser.get_memory_map()
        self.memory_text.setText(memory_map)

    def format_hex_dump(self, data: bytes, width: int = 16) -> str:
        """Format data as hex dump"""
        lines = []
        for i in range(0, len(data), width):
            chunk = data[i:i+width]
            hex_part = ' '.join(f'{b:02x}' for b in chunk)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            lines.append(f"${i:04X}: {hex_part:<{width*3}} | {ascii_part}")

        return '\n'.join(lines)

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About SF2 Viewer",
            "SF2 Viewer v1.0\n\n"
            "Professional viewer for SID Factory II SF2 files\n"
            "Display driver information, tables, sequences, and memory layout\n\n"
            "Drag and drop an SF2 file to view its contents"
        )


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = SF2ViewerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
