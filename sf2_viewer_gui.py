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
        QStatusBar, QMenuBar, QMenu, QMessageBox, QComboBox, QSlider
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
from sf2_visualization_widgets import WaveformWidget, FilterResponseWidget, EnvelopeWidget
from sf2_playback import SF2PlaybackEngine


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

        # Tab 3.5: All Tables Combined
        self.all_tables_tab = self.create_all_tables_tab()
        self.tabs.addTab(self.all_tables_tab, "All Tables")

        # Tab 4: Memory Map
        self.memory_tab = self.create_memory_tab()
        self.tabs.addTab(self.memory_tab, "Memory Map")

        # Tab 5: OrderList
        self.orderlist_tab = self.create_orderlist_tab()
        self.tabs.addTab(self.orderlist_tab, "OrderList")

        # Tab 6: Sequences
        self.sequences_tab = self.create_sequences_tab()
        self.tabs.addTab(self.sequences_tab, "Sequences")

        # Tab 7: Visualization
        self.visualization_tab = self.create_visualization_tab()
        self.tabs.addTab(self.visualization_tab, "Visualization")

        # Tab 8: Playback
        self.playback_tab = self.create_playback_tab()
        self.tabs.addTab(self.playback_tab, "Playback")

        # Create playback engine
        try:
            self.playback_engine = SF2PlaybackEngine()
            self.playback_engine.playback_error.connect(self.on_playback_error)
            self.playback_engine.position_changed.connect(self.on_playback_position)
        except RuntimeError as e:
            print(f"Playback disabled: {e}")
            self.playback_engine = None

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
        """Create the tables tab with split layout - data on left, info on right"""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)

        # Table selector at top
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Select Table:"))

        self.table_combo = self.create_table_combo()
        selector_layout.addWidget(self.table_combo)
        selector_layout.addStretch()

        self.table_combo.currentIndexChanged.connect(self.on_table_selected)
        main_layout.addLayout(selector_layout)

        # Horizontal split layout - left: data, right: info
        split_layout = QHBoxLayout()

        # Left side: Table data display (in All Tables format)
        self.table_display = QTextEdit()
        self.table_display.setReadOnly(True)
        self.table_display.setFont(QFont("Courier New", 10))
        split_layout.addWidget(self.table_display, 2)  # 2/3 of width

        # Right side: Table info metadata
        self.table_info = QTextEdit()
        self.table_info.setReadOnly(True)
        self.table_info.setFont(QFont("Courier", 9))
        split_layout.addWidget(self.table_info, 1)  # 1/3 of width

        main_layout.addLayout(split_layout)

        return widget

    def create_table_combo(self) -> QWidget:
        """Create table selector combo box"""
        from PyQt6.QtWidgets import QComboBox
        combo = QComboBox()
        combo.addItem("Select a table...")
        return combo

    def create_all_tables_tab(self) -> QWidget:
        """Create tab showing all tables combined in hex dump format"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Text display for all tables
        self.all_tables_display = QTextEdit()
        self.all_tables_display.setReadOnly(True)
        self.all_tables_display.setFont(QFont("Courier New", 9))
        layout.addWidget(self.all_tables_display)

        return widget

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
            self.update_all_tables()
            self.update_memory_map()
            self.update_orderlist()
            self.update_sequences()
            self.update_visualization()

            # Check if sequences have valid data and enable/disable tab
            has_valid_sequences = self._has_valid_sequences()
            seq_tab_index = self.tabs.indexOf(self.sequences_tab)
            if seq_tab_index >= 0:
                self.tabs.setTabEnabled(seq_tab_index, has_valid_sequences)

            # Enable playback
            if self.playback_engine:
                self.play_btn.setEnabled(True)
                self.playback_info.setText(f"Ready to play: {Path(file_path).name}")

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
        """Handle table selection - display in All Tables format"""
        if index <= 0 or not self.parser:
            self.table_display.clear()
            self.table_info.clear()
            return

        descriptor = self.table_combo.itemData(index)
        if not descriptor:
            return

        # Get table data
        table_data = self.parser.get_table_data(descriptor)

        # Create formatted document like All Tables view
        from PyQt6.QtGui import QTextDocument, QTextCursor, QTextCharFormat, QBrush, QColor

        doc = QTextDocument()
        cursor = QTextCursor(doc)

        # Define colors and formatting
        font_color = QColor(0, 0, 0)  # Black text
        header_color = QColor(100, 150, 255)  # Light blue for headers

        # Add title with table name
        title_format = QTextCharFormat()
        title_format.setFontWeight(75)
        title_format.setForeground(QBrush(header_color))
        title_format.setFontFamily("Courier New")
        title_format.setFontPointSize(11)
        cursor.setCharFormat(title_format)
        cursor.insertText(f"{descriptor.name}\n")

        # Add separator
        separator_format = QTextCharFormat()
        separator_format.setForeground(QBrush(font_color))
        separator_format.setFontFamily("Courier New")
        separator_format.setFontPointSize(10)
        cursor.setCharFormat(separator_format)
        cursor.insertText("=" * 60 + "\n")

        # Add data rows with row numbers
        data_format = QTextCharFormat()
        data_format.setForeground(QBrush(font_color))
        data_format.setFontFamily("Courier New")
        data_format.setFontPointSize(10)
        cursor.setCharFormat(data_format)

        for row_idx, row_data in enumerate(table_data):
            # Check if all values in row are zero
            if all(val == 0 for val in row_data):
                continue  # Skip all-zero rows

            # Format row with row number and hex values
            row_bytes = ' '.join(f"{val:02X}" for val in row_data)
            row_line = f"{row_idx:02X}: {row_bytes}\n"
            cursor.insertText(row_line)

        self.table_display.setDocument(doc)

        # Display table info on the right
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

    def update_all_tables(self):
        """Update the all tables combined view with proper grid layout and spacing"""
        if not self.parser or not self.parser.table_descriptors:
            self.all_tables_display.setPlainText("No tables loaded")
            return

        # Get all table data - preserve order and handle duplicate names
        tables_data = []
        table_names = []
        for descriptor in self.parser.table_descriptors:
            table_data = self.parser.get_table_data(descriptor)
            tables_data.append((descriptor, table_data))
            table_names.append(descriptor.name)

        if not tables_data:
            self.all_tables_display.setPlainText("No table data available")
            return

        # Define table order preference and grouping
        order_preference = ["Commands", "Instruments", "Wave", "Pulse", "Filter", "Arpeggio", "Tempo", "HR", "Init"]

        # Create list of (index, name) tuples sorted by preference
        indexed_tables = [(i, name) for i, name in enumerate(table_names)]

        # Sort by preference order, then by index for ties
        def sort_key(item):
            idx, name = item
            try:
                pref_order = order_preference.index(name)
            except ValueError:
                pref_order = len(order_preference)
            return (pref_order, idx)

        sorted_indices = sorted(indexed_tables, key=sort_key)
        sorted_tables = [(idx, table_names[idx]) for idx, _ in sorted_indices]

        # Create formatted document
        from PyQt6.QtGui import QTextDocument, QTextCursor, QTextCharFormat, QBrush, QColor

        doc = QTextDocument()
        cursor = QTextCursor(doc)

        # Define colors and formatting
        font_color = QColor(0, 0, 0)  # Black text
        header_color = QColor(100, 150, 255)  # Light blue for headers

        # Calculate column width based on table data - ensure columns are wide enough
        # For Commands (32x6): "00: 05 3A 80 00 09 00" = 21 chars
        # For Instruments (64x3): "00: 02 01 00" = 13 chars
        col_width_large = 26  # For Commands/Instruments
        col_width_small = 18  # For other tables
        spacing = "  "  # Spacing between columns

        # Group tables: Commands/Instruments pair (large), then others in grid
        groups = [
            (sorted_tables[0:2], "Commands & Instruments", col_width_large),  # First 2 tables
            (sorted_tables[2:], "All Tables", col_width_small)  # Remaining tables
        ]

        for group_idx, (group_tables, group_title, col_w) in enumerate(groups):
            if not group_tables:
                continue

            # Add spacing before section (skip for first section)
            if group_idx > 0:
                cursor.insertText("\n")

            # Add header line with table names
            header_format = QTextCharFormat()
            header_format.setFontWeight(75)
            header_format.setForeground(QBrush(header_color))
            header_format.setFontFamily("Courier New")
            header_format.setFontPointSize(10)
            cursor.setCharFormat(header_format)

            header_line = ""
            for table_idx, table_name in group_tables:
                header_line += f"{table_name:<{col_w}}{spacing}"
            cursor.insertText(header_line + "\n")

            # Add separator
            separator_format = QTextCharFormat()
            separator_format.setForeground(QBrush(font_color))
            separator_format.setFontFamily("Courier New")
            separator_format.setFontPointSize(10)
            cursor.setCharFormat(separator_format)
            separator_line = "=" * (col_w * len(group_tables) + len(spacing) * (len(group_tables) - 1))
            cursor.insertText(separator_line + "\n")

            # Determine max rows for this group
            max_rows = 0
            for table_idx, _ in group_tables:
                descriptor, table_data = tables_data[table_idx]
                max_rows = max(max_rows, len(table_data))

            # Add data rows
            data_format = QTextCharFormat()
            data_format.setForeground(QBrush(font_color))
            data_format.setFontFamily("Courier New")
            data_format.setFontPointSize(10)
            cursor.setCharFormat(data_format)

            for row_idx in range(max_rows):
                row_parts = []
                all_zero = True  # Track if all columns have all-zero data

                for table_idx, table_name in group_tables:
                    descriptor, table_data = tables_data[table_idx]

                    if row_idx < len(table_data):
                        # Check if this row is all zeros
                        row_is_zero = all(val == 0 for val in table_data[row_idx])
                        if not row_is_zero:
                            all_zero = False

                        row_bytes = ' '.join(f"{val:02X}" for val in table_data[row_idx])
                        row_text = f"{row_idx:02X}: {row_bytes}"
                    else:
                        row_text = ""

                    row_parts.append(f"{row_text:<{col_w}}")

                # Skip rows where all columns have all-zero data
                if not all_zero:
                    row_line = spacing.join(row_parts) + "\n"
                    cursor.insertText(row_line)

        self.all_tables_display.setDocument(doc)

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

    def create_orderlist_tab(self) -> QWidget:
        """Create the orderlist viewer tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # OrderList data display (moved to top)
        self.orderlist_text = QTextEdit()
        self.orderlist_text.setReadOnly(True)
        self.orderlist_text.setFont(QFont("Courier", 9))
        layout.addWidget(self.orderlist_text)

        # OrderList info (hidden, but available for internal use)
        self.orderlist_info = QLabel()
        self.orderlist_info.setVisible(False)

        return widget

    def create_sequences_tab(self) -> QWidget:
        """Create the sequences viewer tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Sequence selector
        seq_layout = QHBoxLayout()
        seq_layout.addWidget(QLabel("Select Sequence:"))
        self.sequence_combo = QComboBox()
        self.sequence_combo.currentIndexChanged.connect(self.on_sequence_selected)
        seq_layout.addWidget(self.sequence_combo)
        seq_layout.addStretch()
        layout.addLayout(seq_layout)

        # Sequence info
        self.sequence_info = QLabel()
        layout.addWidget(self.sequence_info)

        # Sequence data table
        self.sequence_table = QTableWidget()
        self.sequence_table.setColumnCount(6)
        self.sequence_table.setHorizontalHeaderLabels(["Step", "Note", "Cmd", "Param1", "Param2", "Duration"])
        self.sequence_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.sequence_table)

        return widget

    def update_orderlist(self):
        """Update the orderlist tab - display 3-column OrderList structure (SID Factory II format)"""
        if not self.parser or not self.parser.music_data_info:
            self.orderlist_info.setText("No orderlist data available")
            return

        # Get orderlist addresses (3 columns stored separately)
        addr_col1 = self.parser.music_data_info.orderlist_address
        addr_col2 = getattr(self.parser, 'orderlist_col2_addr', addr_col1 + 0x100)
        addr_col3 = getattr(self.parser, 'orderlist_col3_addr', addr_col1 + 0x200)

        # Update info (hidden)
        info = f"OrderList (3 columns): Col1=${addr_col1:04X} Col2=${addr_col2:04X} Col3=${addr_col3:04X}"
        self.orderlist_info.setText(info)

        # Read orderlist columns from memory
        # Skip first 2 rows (padding/metadata), start from row 2
        # Each column contains one byte per entry (256 bytes max = 256 entries)
        # Format matches SID Factory II editor: row numbers increment by 0x20
        ol_text = ""
        display_row = 0

        for row_idx in range(2, 256):  # Start from row 2 (skip padding rows 0-1)
            # Get one byte from each column
            bytes_in_row = []

            # Column 1
            if addr_col1 + row_idx < len(self.parser.memory):
                bytes_in_row.append(self.parser.memory[addr_col1 + row_idx])
            else:
                break

            # Column 2
            if addr_col2 + row_idx < len(self.parser.memory):
                bytes_in_row.append(self.parser.memory[addr_col2 + row_idx])
            else:
                bytes_in_row.append(0)

            # Column 3
            if addr_col3 + row_idx < len(self.parser.memory):
                bytes_in_row.append(self.parser.memory[addr_col3 + row_idx])
            else:
                bytes_in_row.append(0)

            if len(bytes_in_row) == 3:
                # Format as: XXXX: YY YY YY (row numbers increment by 0x20 like SID Factory II editor)
                hex_bytes = ' '.join(f'{b:02X}' for b in bytes_in_row)
                row_display = display_row * 0x20  # Match editor row numbering
                ol_text += f"{row_display:04X}: {hex_bytes}\n"
                display_row += 1

                # Stop at 0xFF marker (end marker)
                if bytes_in_row[0] == 0xFF:
                    break

        self.orderlist_text.setText(ol_text if ol_text else "OrderList is empty or contains only zeros")

    def update_sequences(self):
        """Update the sequences tab"""
        if not self.parser or not self.parser.sequences:
            self.sequence_combo.clear()
            self.sequence_info.setText("No sequence data available")
            return

        # Update sequence selector
        self.sequence_combo.blockSignals(True)
        self.sequence_combo.clear()
        for seq_idx in sorted(self.parser.sequences.keys()):
            seq = self.parser.sequences[seq_idx]
            self.sequence_combo.addItem(f"Sequence {seq_idx} ({len(seq)} steps)", seq_idx)
        self.sequence_combo.blockSignals(False)

        # Select first sequence
        if self.sequence_combo.count() > 0:
            self.sequence_combo.setCurrentIndex(0)

    def on_sequence_selected(self, index: int):
        """Handle sequence selection"""
        if index < 0 or not self.parser:
            return

        seq_idx = self.sequence_combo.itemData(index)
        if seq_idx not in self.parser.sequences:
            return

        seq_data = self.parser.sequences[seq_idx]

        # Update info
        info = f"Sequence {seq_idx}: {len(seq_data)} steps"
        self.sequence_info.setText(info)

        # Update table
        self.sequence_table.setRowCount(len(seq_data))
        for step, entry in enumerate(seq_data):
            self.sequence_table.setItem(step, 0, QTableWidgetItem(f"{step}"))
            self.sequence_table.setItem(step, 1, QTableWidgetItem(entry.note_name()))
            self.sequence_table.setItem(step, 2, QTableWidgetItem(entry.command_name()))
            self.sequence_table.setItem(step, 3, QTableWidgetItem(f"0x{entry.param1:02X}"))
            self.sequence_table.setItem(step, 4, QTableWidgetItem(f"0x{entry.param2:02X}"))
            self.sequence_table.setItem(step, 5, QTableWidgetItem(f"{entry.duration}"))

    def _has_valid_sequences(self) -> bool:
        """Check if loaded SF2 file has valid sequence data

        For Laxity driver files, sequences are not properly stored in the SF2 format.
        Sequences are disabled for Laxity files since they cannot be reliably extracted.
        Returns False for Laxity drivers to disable the sequences tab.
        """
        if not self.parser or not self.parser.sequences:
            return False

        # Check if this is a Laxity driver file
        # Laxity driver files don't store real sequences in SF2 format
        # Musical information is stored in: OrderList, Commands, Wave, Filter, etc.
        if self.parser.music_data_info:
            # For Laxity files, sequences are not available
            # Check if we have mostly empty sequences (typical for Laxity)
            total_entries = 0
            empty_entries = 0

            for seq_idx, seq_data in self.parser.sequences.items():
                for entry in seq_data:
                    total_entries += 1
                    if entry.note == 0 and entry.command == 0 and entry.duration == 0:
                        empty_entries += 1

            # If more than 90% of entries are empty, it's likely a Laxity file
            if total_entries > 0 and empty_entries / total_entries > 0.90:
                return False

        return False  # Default: sequences not available

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About SF2 Viewer",
            "SF2 Viewer v2.0\n\n"
            "Professional viewer for SID Factory II SF2 files\n"
            "Display driver information, tables, sequences, orderlists, and memory layout\n\n"
            "Drag and drop an SF2 file to view its contents"
        )

    def create_visualization_tab(self) -> QWidget:
        """Create the visualization tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Table selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Select Table:"))
        self.viz_table_combo = QComboBox()
        self.viz_table_combo.currentIndexChanged.connect(self.on_viz_table_selected)
        selector_layout.addWidget(self.viz_table_combo)
        selector_layout.addStretch()
        layout.addLayout(selector_layout)

        # Waveform display
        layout.addWidget(QLabel("Waveform:"))
        self.waveform_widget = WaveformWidget()
        layout.addWidget(self.waveform_widget)

        # Filter display
        layout.addWidget(QLabel("Filter Response:"))
        self.filter_widget = FilterResponseWidget()
        layout.addWidget(self.filter_widget)

        # Envelope display
        layout.addWidget(QLabel("ADSR Envelope:"))
        self.envelope_widget = EnvelopeWidget()
        layout.addWidget(self.envelope_widget)

        return widget

    def update_visualization(self):
        """Update the visualization tab"""
        if not self.parser:
            return

        # Populate table selector with wave/filter/pulse/instrument tables
        self.viz_table_combo.blockSignals(True)
        self.viz_table_combo.clear()

        for desc in self.parser.table_descriptors:
            if desc.name in ["Wave", "Filter", "Pulse", "Instruments"]:
                self.viz_table_combo.addItem(f"{desc.name} Table", desc)

        self.viz_table_combo.blockSignals(False)

        # Select first table
        if self.viz_table_combo.count() > 0:
            self.viz_table_combo.setCurrentIndex(0)

    def on_viz_table_selected(self, index: int):
        """Handle visualization table selection"""
        if index < 0 or not self.parser:
            return

        descriptor = self.viz_table_combo.itemData(index)
        if not descriptor:
            return

        table_data = self.parser.get_table_data(descriptor)

        if descriptor.name == "Wave":
            # Show first row as waveform
            if table_data:
                self.waveform_widget.set_data(table_data[0])

        elif descriptor.name == "Filter":
            # Extract cutoff values (column 0)
            cutoff_data = [row[0] if row else 0 for row in table_data]
            self.filter_widget.set_data(cutoff_data)

        elif descriptor.name == "Pulse":
            # Show pulse width progression (column 0)
            pulse_data = [row[0] if row else 0 for row in table_data]
            self.waveform_widget.set_data(pulse_data)

        elif descriptor.name == "Instruments":
            # Show first instrument envelope
            if table_data and len(table_data[0]) >= 2:
                ad_byte = table_data[0][0]
                sr_byte = table_data[0][1]
                attack = (ad_byte >> 4) & 0x0F
                decay = ad_byte & 0x0F
                sustain = (sr_byte >> 4) & 0x0F
                release = sr_byte & 0x0F
                self.envelope_widget.set_envelope(attack, decay, sustain, release)

    def create_playback_tab(self) -> QWidget:
        """Create the playback tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Info label
        self.playback_info = QLabel("Load an SF2 file to enable playback")
        layout.addWidget(self.playback_info)

        # Playback controls
        controls_layout = QHBoxLayout()

        self.play_btn = QPushButton("Play Full Song")
        self.play_btn.clicked.connect(self.on_play_clicked)
        self.play_btn.setEnabled(False)
        controls_layout.addWidget(self.play_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self.on_pause_clicked)
        self.pause_btn.setEnabled(False)
        controls_layout.addWidget(self.pause_btn)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.on_stop_clicked)
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Volume control
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(QLabel("Volume:"))
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setMaximumWidth(200)
        self.volume_slider.valueChanged.connect(self.on_volume_changed)
        volume_layout.addWidget(self.volume_slider)
        self.volume_label = QLabel("70%")
        volume_layout.addWidget(self.volume_label)
        volume_layout.addStretch()
        layout.addLayout(volume_layout)

        # Position display
        self.position_label = QLabel("Position: 00:00 / 00:30")
        layout.addWidget(self.position_label)

        # Status
        self.playback_status = QTextEdit()
        self.playback_status.setReadOnly(True)
        self.playback_status.setMaximumHeight(150)
        self.playback_status.setFont(QFont("Courier", 9))
        layout.addWidget(QLabel("Status:"))
        layout.addWidget(self.playback_status)

        layout.addStretch()
        return widget

    def on_play_clicked(self):
        """Handle play button click"""
        if not self.current_file or not self.playback_engine:
            self.playback_status.append("ERROR: No file loaded or playback engine unavailable")
            return

        self.playback_status.clear()
        self.playback_status.append("Converting SF2 to audio...\n")
        self.playback_status.append("Step 1: Exporting SF2 to SID format...")
        self.playback_status.append("Step 2: Converting SID to WAV audio...")
        self.playback_status.append("Step 3: Loading audio player...\n")

        success = self.playback_engine.play_sf2(self.current_file)

        if success:
            self.playback_status.append("✓ Playback started!")
            self.play_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
        else:
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)

    def on_pause_clicked(self):
        """Handle pause button click"""
        if self.playback_engine:
            if self.playback_engine.is_playing():
                self.playback_engine.pause()
                self.playback_status.append("Playback paused.")
                self.play_btn.setText("Resume")
                self.play_btn.setEnabled(True)
                self.pause_btn.setEnabled(False)
            else:
                self.playback_engine.resume()
                self.playback_status.append("Playback resumed.")
                self.play_btn.setText("Play Full Song")
                self.play_btn.setEnabled(False)
                self.pause_btn.setEnabled(True)

    def on_stop_clicked(self):
        """Handle stop button click"""
        if self.playback_engine:
            self.playback_engine.stop()
            self.play_btn.setText("Play Full Song")
            self.play_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            self.stop_btn.setEnabled(False)
            self.playback_status.append("Playback stopped.")

    def on_volume_changed(self, value: int):
        """Handle volume slider change"""
        if self.playback_engine:
            self.playback_engine.set_volume(value)
            self.volume_label.setText(f"{value}%")

    def on_playback_error(self, error: str):
        """Handle playback errors"""
        self.playback_status.append(f"ERROR: {error}")
        self.play_btn.setEnabled(True)
        self.play_btn.setText("Play Full Song")
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

    def on_playback_position(self, position_ms: int):
        """Update position display"""
        duration_ms = self.playback_engine.get_duration() if self.playback_engine else 30000
        seconds = position_ms // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        total_seconds = duration_ms // 1000
        total_minutes = total_seconds // 60
        total_seconds = total_seconds % 60
        self.position_label.setText(
            f"Position: {minutes:02d}:{seconds:02d} / {total_minutes:02d}:{total_seconds:02d}"
        )


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    window = SF2ViewerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
