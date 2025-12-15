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

        # Display table with hex row numbers and no "0x" prefix
        self.table_widget.setRowCount(len(table_data))
        self.table_widget.setColumnCount(len(table_data[0]) if table_data else 0)

        for row_idx, row_data in enumerate(table_data):
            for col_idx, value in enumerate(row_data):
                # Display hex values without "0x" prefix
                item = QTableWidgetItem(f"{value:02X}")
                item.setFont(QFont("Courier", 9))
                self.table_widget.setItem(row_idx, col_idx, item)

        # Set headers - columns as C0, C1, etc. and rows as hex (00, 01, etc.)
        self.table_widget.setHorizontalHeaderLabels([f"C{i}" for i in range(len(table_data[0]))] if table_data else [])
        self.table_widget.setVerticalHeaderLabels([f"{i:02X}" for i in range(len(table_data))])

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

    def update_all_tables(self):
        """Update the all tables combined view with hex dump format"""
        if not self.parser or not self.parser.table_descriptors:
            self.all_tables_display.setText("No tables loaded")
            return

        # Build output with all tables side-by-side
        output_lines = []

        # Get all table data
        tables_data = {}
        for descriptor in self.parser.table_descriptors:
            table_data = self.parser.get_table_data(descriptor)
            tables_data[descriptor.name] = (descriptor, table_data)

        if not tables_data:
            self.all_tables_display.setText("No table data available")
            return

        # Determine how many rows to display (max of all tables)
        max_rows = max(len(data[1]) for data in tables_data.values())

        # Build header line with table names
        header = ""
        col_positions = {}
        pos = 0
        for table_name in tables_data.keys():
            col_positions[table_name] = pos
            # Each column is 20 chars wide (name + spacing)
            header += f"{table_name:20}"
            pos += 20

        output_lines.append(header)
        output_lines.append("=" * len(header))

        # Build data rows
        for row_idx in range(max_rows):
            row_str = ""
            for table_name in tables_data.keys():
                descriptor, table_data = tables_data[table_name]

                if row_idx < len(table_data):
                    # Format row as hex bytes
                    row_bytes = ' '.join(f"{val:02X}" for val in table_data[row_idx])
                    # Add row number at start
                    if row_idx == 0:
                        row_str += f"{row_idx:02X}: {row_bytes:16}"
                    else:
                        row_str += f"{row_idx:02X}: {row_bytes:16}"
                else:
                    row_str += " " * 20

                row_str += " "

            output_lines.append(row_str.rstrip())

        self.all_tables_display.setText('\n'.join(output_lines))

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

        # OrderList info
        info_layout = QHBoxLayout()
        self.orderlist_info = QLabel()
        info_layout.addWidget(self.orderlist_info)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # OrderList table
        self.orderlist_table = QTableWidget()
        self.orderlist_table.setColumnCount(3)
        self.orderlist_table.setHorizontalHeaderLabels(["Index", "Seq #", "Note"])
        self.orderlist_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.orderlist_table.setMaximumHeight(300)
        layout.addWidget(self.orderlist_table)

        # OrderList visualization
        self.orderlist_text = QTextEdit()
        self.orderlist_text.setReadOnly(True)
        self.orderlist_text.setFont(QFont("Courier", 9))
        layout.addWidget(self.orderlist_text)

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
        """Update the orderlist tab"""
        if not self.parser or not self.parser.music_data_info:
            self.orderlist_info.setText("No orderlist data available")
            return

        # Update info
        info = f"OrderList at ${self.parser.music_data_info.orderlist_address:04X} | {len(self.parser.orderlist)} entries"
        self.orderlist_info.setText(info)

        # Update table
        self.orderlist_table.setRowCount(len(self.parser.orderlist))
        for i, seq_idx in enumerate(self.parser.orderlist):
            self.orderlist_table.setItem(i, 0, QTableWidgetItem(f"{i}"))
            self.orderlist_table.setItem(i, 1, QTableWidgetItem(f"0x{seq_idx:02X}"))
            note = "END" if seq_idx == 0x7F else f"Seq {seq_idx}"
            self.orderlist_table.setItem(i, 2, QTableWidgetItem(note))

        # Update visualization
        ol_str = " ".join(f"{x:02X}" for x in self.parser.orderlist[:16])
        if len(self.parser.orderlist) > 16:
            ol_str += f" ... ({len(self.parser.orderlist)} total)"
        self.orderlist_text.setText(f"OrderList:\n{ol_str}\n\nStructure: Sequence indices separated by spaces, terminated by 7F (END)")

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
