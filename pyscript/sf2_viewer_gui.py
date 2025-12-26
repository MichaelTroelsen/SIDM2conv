#!/usr/bin/env python3
"""
SF2 Viewer GUI - Professional SID Factory II file viewer
Display SF2 files with the same layout as the SID Factory II editor
"""

import sys
import os
import json
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
    from PyQt6.QtCore import Qt, QMimeData, QUrl, QSize, QTimer, QSettings
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

# Add path to sidm2 module
sys.path.insert(0, str(Path(__file__).parent.parent))
from sidm2.sf2_debug_logger import configure_sf2_logger, get_sf2_logger, SF2EventType

# Constants
MAX_RECENT_FILES = 10

# Configure ultra-verbose logging (can be toggled via environment variable)
import os
ULTRAVERBOSE = os.getenv('SF2_ULTRAVERBOSE', '').lower() in ('1', 'true', 'yes')
DEBUG_LOG_FILE = os.getenv('SF2_DEBUG_LOG', 'sf2_viewer_debug.log')
JSON_LOG = os.getenv('SF2_JSON_LOG', '').lower() in ('1', 'true', 'yes')

# Initialize SF2 debug logger
sf2_logger = configure_sf2_logger(
    level=1 if ULTRAVERBOSE else 10,  # ULTRAVERBOSE=1, DEBUG=10
    log_file=DEBUG_LOG_FILE if os.getenv('SF2_DEBUG_LOG') else None,
    json_log=JSON_LOG,
    ultraverbose=ULTRAVERBOSE
)


class SF2ViewerWindow(QMainWindow):
    """Main window for SF2 viewer application"""

    def __init__(self, file_to_load: Optional[str] = None):
        super().__init__()
        self.setWindowTitle("SID Factory II SF2 Viewer v2.4")
        self.setGeometry(100, 100, 1600, 1000)

        self.parser: Optional[SF2Parser] = None
        self.current_file = None
        self.settings = QSettings("Anthropic", "SF2Viewer")
        self.recent_menu = None

        # Log initialization
        sf2_logger.log_action("SF2 Viewer GUI initialized", {
            'version': '2.4',
            'window_size': '1600x1000',
            'ultraverbose': ULTRAVERBOSE,
            'log_file': DEBUG_LOG_FILE if os.getenv('SF2_DEBUG_LOG') else None
        })

        self.init_ui()
        self.setup_drag_drop()
        self.update_recent_files_menu()

        # Load file if provided as argument
        if file_to_load and os.path.isfile(file_to_load):
            sf2_logger.log_action(f"Loading file from command line: {file_to_load}")
            self.load_file(file_to_load)

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

        # Tab 7: Track View (NEW - v2.4)
        self.track_view_tab = self.create_track_view_tab()
        self.tabs.addTab(self.track_view_tab, "Track View")

        # Tab 8: Visualization
        self.visualization_tab = self.create_visualization_tab()
        self.tabs.addTab(self.visualization_tab, "Visualization")

        # Tab 8: Playback
        self.playback_tab = self.create_playback_tab()
        self.tabs.addTab(self.playback_tab, "Playback")

        # Connect tab change signal for logging
        self.tabs.currentChanged.connect(self.on_tab_changed)

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

        # Recent Files submenu
        self.recent_menu = file_menu.addMenu("Recent Files")

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
                sf2_logger.log_action("File dropped", {
                    'file_path': file_path,
                    'drop_position': f'({event.position().x()}, {event.position().y()})'
                })
                self.load_file(file_path)

    def keyPressEvent(self, event):
        """Handle keyboard events and log them"""
        from PyQt6.QtCore import Qt

        # Get key name
        key = event.text() if event.text() else event.key()
        key_name = event.key()

        # Get modifiers
        modifiers = []
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            modifiers.append('Ctrl')
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append('Shift')
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            modifiers.append('Alt')

        # Special keys
        key_names = {
            Qt.Key.Key_Escape: 'Escape',
            Qt.Key.Key_Return: 'Return',
            Qt.Key.Key_Enter: 'Enter',
            Qt.Key.Key_Tab: 'Tab',
            Qt.Key.Key_Backspace: 'Backspace',
            Qt.Key.Key_Delete: 'Delete',
            Qt.Key.Key_Up: 'Up',
            Qt.Key.Key_Down: 'Down',
            Qt.Key.Key_Left: 'Left',
            Qt.Key.Key_Right: 'Right',
            Qt.Key.Key_F1: 'F1',
            Qt.Key.Key_F2: 'F2',
            Qt.Key.Key_F3: 'F3',
            Qt.Key.Key_F4: 'F4',
            Qt.Key.Key_F5: 'F5',
            Qt.Key.Key_F6: 'F6',
            Qt.Key.Key_F7: 'F7',
            Qt.Key.Key_F8: 'F8',
            Qt.Key.Key_F9: 'F9',
            Qt.Key.Key_F10: 'F10',
            Qt.Key.Key_F11: 'F11',
            Qt.Key.Key_F12: 'F12',
        }

        key_display = key_names.get(key_name, event.text() if event.text() else f'Key_{key_name}')

        # Log keypress
        sf2_logger.log_keypress(key_display, modifiers, self.__class__.__name__)

        # Pass to parent
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse press events and log them"""
        from PyQt6.QtCore import Qt

        # Get button name
        button_names = {
            Qt.MouseButton.LeftButton: 'Left',
            Qt.MouseButton.RightButton: 'Right',
            Qt.MouseButton.MiddleButton: 'Middle'
        }
        button = button_names.get(event.button(), 'Unknown')

        # Get widget under mouse
        widget = self.childAt(event.pos())
        widget_name = widget.__class__.__name__ if widget else 'Window'

        # Log mouse click
        sf2_logger.log_mouse_click(
            button,
            event.pos().x(),
            event.pos().y(),
            widget_name
        )

        # Pass to parent
        super().mousePressEvent(event)

    def on_tab_changed(self, index: int):
        """Handle tab change events"""
        if index >= 0 and index < self.tabs.count():
            tab_name = self.tabs.tabText(index)
            sf2_logger.log_event(SF2EventType.TAB_CHANGE, {
                'message': f'Tab changed to: {tab_name}',
                'tab_name': tab_name,
                'tab_index': index
            })

    def browse_file(self):
        """Browse for an SF2 file"""
        sf2_logger.log_action("Opening file browse dialog")

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open SF2 File",
            "",
            "SF2 Files (*.sf2);;All Files (*.*)"
        )

        if file_path:
            sf2_logger.log_action(f"File selected from dialog: {file_path}")
            self.load_file(file_path)
        else:
            sf2_logger.log_action("File browse dialog cancelled")

    def load_file(self, file_path: str):
        """Load and parse an SF2 file"""
        import time
        start_time = time.time()

        # Log file load start
        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
        sf2_logger.log_file_load(file_path, 'start', {
            'file_size_bytes': file_size,
            'file_size_kb': file_size / 1024
        })

        try:
            self.current_file = file_path
            self.file_label.setText(f"Loaded: {Path(file_path).name}")

            # Parse file
            parse_start = time.time()
            sf2_logger.log_action("Starting SF2 file parsing")
            self.parser = SF2Parser(file_path)
            parse_time = time.time() - parse_start

            if not self.parser.magic_id:
                sf2_logger.log_file_load(file_path, 'error', {
                    'error': 'Invalid magic ID',
                    'parse_time_ms': int(parse_time * 1000)
                })
                QMessageBox.critical(self, "Error", "Failed to parse SF2 file")
                return

            sf2_logger.log_action("SF2 file parsed successfully", {
                'parse_time_ms': int(parse_time * 1000),
                'magic_id': f'0x{self.parser.magic_id:04X}' if self.parser.magic_id else None,
                'blocks_found': len(self.parser.blocks) if hasattr(self.parser, 'blocks') else 0
            })

            # Update all tabs
            ui_update_start = time.time()
            sf2_logger.log_action("Updating UI tabs")

            self.update_overview()
            self.update_blocks()
            self.update_tables()
            self.update_all_tables()
            self.update_memory_map()
            self.update_orderlist()
            self.update_sequences()
            self.update_track_view()  # NEW - v2.4
            self.update_visualization()

            ui_update_time = time.time() - ui_update_start
            sf2_logger.log_action("UI tabs updated", {
                'update_time_ms': int(ui_update_time * 1000)
            })

            # Check if sequences have valid data and enable/disable tab
            has_valid_sequences = self._has_valid_sequences()
            seq_tab_index = self.tabs.indexOf(self.sequences_tab)
            if seq_tab_index >= 0:
                self.tabs.setTabEnabled(seq_tab_index, has_valid_sequences)

            # Enable playback
            if self.playback_engine:
                self.play_btn.setEnabled(True)
                self.playback_info.setText(f"Ready to play: {Path(file_path).name}")
                sf2_logger.log_action("Playback enabled")

            self.statusBar().showMessage(f"Loaded: {file_path}")
            self.add_recent_file(file_path)

            # Log successful load
            total_time = time.time() - start_time
            sf2_logger.log_file_load(file_path, 'complete', {
                'total_time_ms': int(total_time * 1000),
                'parse_time_ms': int(parse_time * 1000),
                'ui_update_time_ms': int(ui_update_time * 1000),
                'file_size_bytes': file_size,
                'has_sequences': has_valid_sequences
            })

        except Exception as e:
            sf2_logger.log_file_load(file_path, 'error', {
                'error': str(e),
                'exception_type': type(e).__name__,
                'elapsed_ms': int((time.time() - start_time) * 1000)
            })
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def load_recent_files(self) -> list:
        """Load recent files list from settings"""
        try:
            recent_json = self.settings.value("recent_files", "[]")
            recent = json.loads(recent_json) if isinstance(recent_json, str) else []

            # Filter out non-existent files
            recent = [f for f in recent if os.path.isfile(f)]

            # Return at most MAX_RECENT_FILES
            return recent[:MAX_RECENT_FILES]
        except (json.JSONDecodeError, TypeError):
            return []

    def save_recent_files(self, files: list):
        """Save recent files list to settings"""
        recent_json = json.dumps(files[:MAX_RECENT_FILES])
        self.settings.setValue("recent_files", recent_json)

    def add_recent_file(self, file_path: str):
        """Add file to recent files list"""
        recent = self.load_recent_files()

        # Remove if already exists (will move to top)
        if file_path in recent:
            recent.remove(file_path)

        # Insert at beginning
        recent.insert(0, file_path)

        # Trim to max size
        recent = recent[:MAX_RECENT_FILES]

        # Save and update menu
        self.save_recent_files(recent)
        self.update_recent_files_menu()

    def clear_recent_files(self):
        """Clear all recent files"""
        self.settings.remove("recent_files")
        self.update_recent_files_menu()

    def update_recent_files_menu(self):
        """Rebuild recent files submenu"""
        if not self.recent_menu:
            return

        # Clear existing actions
        self.recent_menu.clear()

        # Load recent files
        recent = self.load_recent_files()

        if not recent:
            # Show "No recent files" as disabled menu item
            no_recent = self.recent_menu.addAction("No recent files")
            no_recent.setEnabled(False)
        else:
            # Add action for each recent file
            for file_path in recent:
                action = self.recent_menu.addAction(Path(file_path).name)
                action.setToolTip(file_path)
                action.triggered.connect(lambda checked=False, fp=file_path: self.open_recent_file(fp))

            # Add separator and clear action
            self.recent_menu.addSeparator()
            clear_action = self.recent_menu.addAction("Clear Recent Files")
            clear_action.triggered.connect(self.clear_recent_files)

    def open_recent_file(self, file_path: str):
        """Open a file from recent files list"""
        if os.path.isfile(file_path):
            self.load_file(file_path)
        else:
            QMessageBox.warning(self, "File Not Found", f"File not found:\n{file_path}")
            # Remove from recent files
            recent = self.load_recent_files()
            if file_path in recent:
                recent.remove(file_path)
                self.save_recent_files(recent)
                self.update_recent_files_menu()

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

        # Top controls layout
        controls_layout = QHBoxLayout()

        # Sequence selector
        controls_layout.addWidget(QLabel("Select Sequence:"))
        self.sequence_combo = QComboBox()
        self.sequence_combo.currentIndexChanged.connect(self.on_sequence_selected)
        controls_layout.addWidget(self.sequence_combo)

        controls_layout.addSpacing(20)

        # View mode selector
        controls_layout.addWidget(QLabel("View Mode:"))
        self.sequence_view_combo = QComboBox()
        self.sequence_view_combo.addItem("Musician (Note Names)", "musician")
        self.sequence_view_combo.addItem("Hex (Raw Values)", "hex")
        self.sequence_view_combo.addItem("Both (Combined)", "both")
        self.sequence_view_combo.setCurrentIndex(2)  # Default to "Both"
        self.sequence_view_combo.currentIndexChanged.connect(self.on_sequence_view_changed)
        controls_layout.addWidget(self.sequence_view_combo)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Sequence info
        self.sequence_info = QLabel()
        layout.addWidget(self.sequence_info)

        # Sequence data text view (like OrderList for better performance with large sequences)
        self.sequence_text = QTextEdit()
        self.sequence_text.setReadOnly(True)
        self.sequence_text.setFont(QFont("Courier", 10))
        self.sequence_text.setStyleSheet("background-color: #000033; color: #FFFF00; border: 1px solid #0066FF;")
        layout.addWidget(self.sequence_text)

        return widget

    def create_track_view_tab(self) -> QWidget:
        """Create the track view tab - combines OrderList + Sequences with transpose"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Top controls layout
        controls_layout = QHBoxLayout()

        # Track selector
        controls_layout.addWidget(QLabel("Select Track:"))
        self.track_selector = QComboBox()
        self.track_selector.addItem("Track 1 (Voice 1)", 0)
        self.track_selector.addItem("Track 2 (Voice 2)", 1)
        self.track_selector.addItem("Track 3 (Voice 3)", 2)
        self.track_selector.currentIndexChanged.connect(self.on_track_selected)
        controls_layout.addWidget(self.track_selector)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Track info
        self.track_info = QLabel()
        layout.addWidget(self.track_info)

        # Track data text view
        self.track_text = QTextEdit()
        self.track_text.setReadOnly(True)
        self.track_text.setFont(QFont("Courier", 10))
        self.track_text.setStyleSheet("background-color: #000033; color: #FFFF00; border: 1px solid #0066FF;")
        layout.addWidget(self.track_text)

        return widget

    def _decode_transpose(self, transpose: int) -> tuple:
        """Decode transpose byte to signed semitones.

        Args:
            transpose: Transpose byte (0x80-0xBF)

        Returns:
            Tuple of (semitones: int, display: str)
            e.g., (0, "+0"), (2, "+2"), (-4, "-4")
        """
        # Extract lower nibble (4-bit signed value)
        transpose_nibble = transpose & 0x0F

        if transpose_nibble < 8:
            semitones = transpose_nibble  # 0-7 = +0 to +7
            display = f"+{semitones}"
        else:
            semitones = transpose_nibble - 16  # 8-15 = -8 to -1
            display = f"{semitones}"

        return semitones, display

    def _format_note(self, note_value: int) -> str:
        """Convert note value to musical notation (SF2 Editor format).

        Args:
            note_value: Note byte (0x00-0x7F)

        Returns:
            Musical notation string (e.g., "C-4", "F#-2", "+++", "---")
        """
        if note_value == 0x00:
            return "---"  # Gate off / silence
        elif note_value == 0x7E:
            return "+++"  # Gate on / sustain
        elif note_value == 0x7F:
            return "END"  # End marker
        elif note_value > 0x7F:
            return f"0x{note_value:02X}"  # Invalid
        else:
            # Valid note (0x01-0x7D)
            notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            octave = note_value // 12
            note_idx = note_value % 12
            return f"{notes[note_idx]}-{octave}"

    def _apply_transpose(self, note_value: int, transpose: int) -> int:
        """Apply transpose to note value.

        Args:
            note_value: Original note (0x00-0x7F)
            transpose: Transpose byte (0x80-0xBF)

        Returns:
            Transposed note value
        """
        # Special values not transposed
        if note_value in [0x00, 0x7E, 0x7F] or note_value >= 0x80:
            return note_value

        # Decode transpose (lower nibble)
        transpose_nibble = transpose & 0x0F
        if transpose_nibble < 8:
            semitones = transpose_nibble
        else:
            semitones = transpose_nibble - 16

        # Apply transpose
        transposed = note_value + semitones

        # Clamp to valid range
        if transposed < 0:
            transposed = 0
        elif transposed > 0x7D:
            transposed = 0x7D

        return transposed

    def update_orderlist(self):
        """Update the orderlist tab - display unpacked XXYY format (SF2 Editor format)"""
        if not self.parser or not self.parser.music_data_info:
            self.orderlist_info.setText("No orderlist data available")
            self.orderlist_text.setPlainText("No orderlist data available")
            return

        # Use unpacked orderlist if available (NEW - from Phase 1)
        if hasattr(self.parser, 'orderlist_unpacked') and self.parser.orderlist_unpacked:
            # Display unpacked XXYY format
            ol_text = ""
            ol_text += "ORDER LIST (SF2 Editor Format - Unpacked XXYY)\n"
            ol_text += "=" * 70 + "\n"
            ol_text += "Format: XXYY where XX=transpose, YY=sequence\n"
            ol_text += "  A0 = no transpose, A2 = +2 semitones, AC = -4 semitones, etc.\n"
            ol_text += "\n"
            ol_text += "Step  | Track 1      | Track 2      | Track 3      | Notes\n"
            ol_text += "------|--------------|--------------|--------------|------------------\n"

            # Get all 3 tracks
            tracks = self.parser.orderlist_unpacked

            # Find maximum length
            max_len = max(len(track) for track in tracks) if tracks else 0

            # Track sequence usage for validation
            sequence_usage = {}
            invalid_sequences = []
            available_sequences = set(self.parser.sequences.keys())

            # Display unpacked entries
            for pos in range(max_len):
                # Format row number
                ol_text += f"{pos:04X}  | "

                notes = []

                for track_idx, track in enumerate(tracks):
                    if pos < len(track):
                        entry = track[pos]
                        transpose = entry['transpose']
                        sequence = entry['sequence']

                        # Decode transpose
                        _, transpose_display = self._decode_transpose(transpose)

                        # Write in XXYY format with decoded transpose
                        ol_text += f"{transpose:02X}{sequence:02X} ({transpose_display:>3s}) | "

                        # Track usage
                        sequence_usage[sequence] = sequence_usage.get(sequence, 0) + 1

                        # Validate sequence exists
                        if sequence not in available_sequences:
                            invalid_sequences.append((pos, track_idx + 1, sequence))
                            notes.append(f"T{track_idx+1}:${sequence:02X}?")

                        # Note transpose changes
                        if pos > 0 and transpose != tracks[track_idx][pos-1]['transpose']:
                            _, new_transpose_display = self._decode_transpose(transpose)
                            notes.append(f"T{track_idx+1} transpose {new_transpose_display}")
                    else:
                        # Track ended
                        ol_text += "              | "

                # Add notes
                notes_str = " ".join(notes) if notes else ""
                ol_text += notes_str + "\n"

            # Add summary
            if sequence_usage:
                ol_text += "\n"
                ol_text += "SEQUENCE USAGE:\n"
                ol_text += "-" * 70 + "\n"
                for seq_num in sorted(sequence_usage.keys()):
                    count = sequence_usage[seq_num]
                    status = "OK" if seq_num in available_sequences else "MISSING"
                    seq_format = self.parser.sequence_formats.get(seq_num, 'unknown')
                    ol_text += f"  Sequence ${seq_num:02X}: {count:2d}x  [{status:7s}]  ({seq_format})\n"

            if invalid_sequences:
                ol_text += "\n"
                ol_text += "VALIDATION ERRORS:\n"
                ol_text += "-" * 70 + "\n"
                for pos, track, seq_num in invalid_sequences:
                    ol_text += f"  Step ${pos:04X} Track {track}: Sequence ${seq_num:02X} not found\n"

            self.orderlist_text.setPlainText(ol_text)

        else:
            # Fallback: Show raw bytes (old format)
            ol_text = ""
            ol_text += "ORDER LIST (Raw Format - Unpacked data not available)\n"
            ol_text += "=" * 60 + "\n\n"
            ol_text += "Step  | Track 1 | Track 2 | Track 3\n"
            ol_text += "------|---------|---------|----------\n"

            addr_col1 = self.parser.music_data_info.orderlist_address
            addr_col2 = getattr(self.parser, 'orderlist_col2_addr', addr_col1 + 0x100)
            addr_col3 = getattr(self.parser, 'orderlist_col3_addr', addr_col1 + 0x200)

            for row_idx in range(0, 256):
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
                    # Format display strings
                    col1_str = f"{bytes_in_row[0]:02X}" if bytes_in_row[0] != 0 else "  "
                    col2_str = f"{bytes_in_row[1]:02X}" if bytes_in_row[1] != 0 else "  "
                    col3_str = f"{bytes_in_row[2]:02X}" if bytes_in_row[2] != 0 else "  "

                    ol_text += f"{row_idx:04X}  | {col1_str:7s} | {col2_str:7s} | {col3_str:7s}\n"

                    # Stop at 0xFF marker (end marker)
                    if bytes_in_row[0] == 0xFF:
                        break

            self.orderlist_text.setPlainText(ol_text)

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
        """Handle sequence selection - display sequence data"""
        if index < 0 or not self.parser:
            return

        seq_idx = self.sequence_combo.itemData(index)
        if seq_idx not in self.parser.sequences:
            return

        seq_data = self.parser.sequences[seq_idx]

        # Check sequence format (single-track or 3-track interleaved)
        seq_format = self.parser.sequence_formats.get(seq_idx, 'interleaved')

        # Get current view mode
        view_mode = self.sequence_view_combo.currentData() if hasattr(self, 'sequence_view_combo') else 'both'

        if seq_format == 'single':
            # Display as single continuous track
            self._display_sequence_single_track(seq_idx, seq_data, view_mode)
        else:
            # Display in 3-track parallel format (matching SID Factory II)
            self._display_sequence_3track_parallel(seq_idx, seq_data, view_mode)

    def on_sequence_view_changed(self, index: int):
        """Handle view mode change - refresh current sequence display"""
        # Re-display the current sequence with the new view mode
        current_index = self.sequence_combo.currentIndex()
        if current_index >= 0:
            self.on_sequence_selected(current_index)

    def _display_sequence_single_track(self, seq_idx: int, seq_data: list, view_mode: str = 'both'):
        """Display sequence data as single continuous track (for Laxity single-track sequences)"""
        # Update info
        format_type = "Laxity driver (single-track)" if (hasattr(self.parser, 'is_laxity_driver') and self.parser.is_laxity_driver) else "Single-track"
        info = f"Sequence {seq_idx} (${seq_idx:02X}): {len(seq_data)} steps - {format_type}"
        self.sequence_info.setText(info)

        # Format sequence data as single track
        seq_text = ""

        # Header based on view mode
        if view_mode == 'musician':
            seq_text += "Step  Inst Cmd  Note\n"
            seq_text += "----  ---- ---  ----\n"
        elif view_mode == 'hex':
            seq_text += "Step  Inst Cmd  Note  [Hex]\n"
            seq_text += "----  ---- ---  ----  -----------\n"
        else:  # both
            seq_text += "Step  Inst Cmd  Note     [Hex]\n"
            seq_text += "----  ---- ---  -------  -----------\n"

        # Data rows
        for step, entry in enumerate(seq_data):
            # Get display values
            instr = entry.instrument_display()  # 2 chars
            cmd = entry.command_display()       # 2 chars
            note = entry.note_name()            # 3+ chars

            # Get hex values
            inst_hex = f"{entry.instrument:02X}" if entry.instrument else "00"
            cmd_hex = f"{entry.command:02X}" if entry.command else "00"
            note_hex = f"{entry.note:02X}" if hasattr(entry, 'note') and entry.note else "00"

            # Format based on view mode
            if view_mode == 'musician':
                seq_text += f"{step:04X}  {instr:2s}   {cmd:>2s}  {note:4s}\n"
            elif view_mode == 'hex':
                seq_text += f"{step:04X}  {inst_hex}   {cmd_hex}   {note_hex}    [{inst_hex} {cmd_hex} {note_hex}]\n"
            else:  # both
                seq_text += f"{step:04X}  {instr:2s}   {cmd:>2s}  {note:6s}   [{inst_hex} {cmd_hex} {note_hex}]\n"

        self.sequence_text.setText(seq_text)

    def _display_sequence_3track_parallel(self, seq_idx: int, seq_data: list, view_mode: str = 'both'):
        """Display sequence data in 3-track parallel format (matching SID Factory II editor)"""
        # Update info - calculate number of "steps" (groups of 3 entries for 3 tracks)
        num_steps = (len(seq_data) + 2) // 3  # Round up division
        format_type = "Laxity driver" if (hasattr(self.parser, 'is_laxity_driver') and self.parser.is_laxity_driver) else "Traditional"
        info = f"Sequence {seq_idx} (${seq_idx:02X}): {len(seq_data)} events ({num_steps} steps × 3 tracks) - {format_type}"
        self.sequence_info.setText(info)

        # Format sequence data like SID Factory II editor with 3 parallel tracks
        # Packed format stores sequences with 3 tracks interleaved:
        # Entry 0, 1, 2 = Track 1, 2, 3 at Step 0
        # Entry 3, 4, 5 = Track 1, 2, 3 at Step 1, etc.
        seq_text = ""

        # Header based on view mode
        if view_mode == 'musician':
            seq_text += "      Track 1           Track 2           Track 3\n"
            seq_text += "Step  In Cmd Note       In Cmd Note       In Cmd Note\n"
            seq_text += "----  -- --- ----       -- --- ----       -- --- ----\n"
        elif view_mode == 'hex':
            seq_text += "      Track 1                 Track 2                 Track 3\n"
            seq_text += "Step  In Cmd Note [Hex]      In Cmd Note [Hex]      In Cmd Note [Hex]\n"
            seq_text += "----  -- --- ---- --------   -- --- ---- --------   -- --- ---- --------\n"
        else:  # both
            seq_text += "      Track 1                  Track 2                  Track 3\n"
            seq_text += "Step  In Cmd Note   [Hex]     In Cmd Note   [Hex]     In Cmd Note   [Hex]\n"
            seq_text += "----  -- --- -----  --------  -- --- -----  --------  -- --- -----  --------\n"

        # Data rows - group by 3 for parallel track display
        step = 0
        for i in range(0, len(seq_data), 3):
            entry1 = seq_data[i]
            entry2 = seq_data[i + 1] if i + 1 < len(seq_data) else None
            entry3 = seq_data[i + 2] if i + 2 < len(seq_data) else None

            # Format each track's data based on view mode
            def format_entry(entry, view_mode):
                if entry is None:
                    if view_mode == 'hex':
                        return "-- --- ---- --------"
                    elif view_mode == 'both':
                        return "-- --- -----  --------"
                    else:
                        return "-- --- ----"

                instr = entry.instrument_display()
                cmd = entry.command_display()
                note = entry.note_name()

                if view_mode == 'musician':
                    return f"{instr:2s} {cmd:>2s} {note:4s}"
                else:
                    # Get hex values
                    inst_hex = f"{entry.instrument:02X}" if entry.instrument else "00"
                    cmd_hex = f"{entry.command:02X}" if entry.command else "00"
                    note_hex = f"{entry.note:02X}" if hasattr(entry, 'note') and entry.note else "00"

                    if view_mode == 'hex':
                        return f"{inst_hex} {cmd_hex}  {note_hex}   [{inst_hex} {cmd_hex} {note_hex}]"
                    else:  # both
                        return f"{instr:2s} {cmd:>2s} {note:5s}  [{inst_hex} {cmd_hex} {note_hex}]"

            track1_str = format_entry(entry1, view_mode)
            track2_str = format_entry(entry2, view_mode)
            track3_str = format_entry(entry3, view_mode)

            # Build the row with 3 tracks
            if view_mode == 'musician':
                seq_text += f"{step:04X}  {track1_str}       {track2_str}       {track3_str}\n"
            else:
                seq_text += f"{step:04X}  {track1_str}  {track2_str}  {track3_str}\n"
            step += 1

        self.sequence_text.setText(seq_text)

    def on_track_selected(self, index: int):
        """Handle track selection - display track data"""
        if index < 0 or not self.parser:
            return

        track_idx = self.track_selector.itemData(index)
        self.update_track_view(track_idx)

    def update_track_view(self, track_idx: int = 0):
        """Update the track view tab - combines OrderList + Sequences with transpose"""
        if not self.parser or not hasattr(self.parser, 'orderlist_unpacked') or not self.parser.orderlist_unpacked:
            self.track_info.setText("No track data available - OrderList unpacking required")
            self.track_text.setPlainText("No track data available")
            return

        if track_idx < 0 or track_idx >= len(self.parser.orderlist_unpacked):
            self.track_info.setText(f"Invalid track index: {track_idx}")
            self.track_text.setPlainText("Invalid track index")
            return

        # Get track OrderList
        track_orderlist = self.parser.orderlist_unpacked[track_idx]
        track_num = track_idx + 1

        # Update info
        self.track_info.setText(f"Track {track_num} - {len(track_orderlist)} OrderList positions")

        # Build track display
        track_text = f"# Track {track_num} - Unpacked Musical Notation\n"
        track_text += f"# Format: Position | OrderList | Sequence | Transpose | Step | Instrument | Command | Note\n"
        track_text += "# " + "-" * 77 + "\n\n"

        # Process each OrderList position
        for pos, entry in enumerate(track_orderlist):
            transpose = entry['transpose']
            sequence_idx = entry['sequence']

            # Decode transpose for display
            _, transpose_display = self._decode_transpose(transpose)

            # Write position header
            track_text += f"Position {pos:03d} | OrderList: {transpose:02X}{sequence_idx:02X} | "
            track_text += f"Sequence ${sequence_idx:02X} | Transpose {transpose_display}\n"

            # Get sequence data
            if sequence_idx not in self.parser.sequences:
                track_text += f"  ERROR: Sequence ${sequence_idx:02X} not found\n\n"
                continue

            sequence_data = self.parser.sequences[sequence_idx]
            seq_format = self.parser.sequence_formats.get(sequence_idx, 'interleaved')

            # Extract track entries (handle interleaved vs single)
            if seq_format == 'interleaved':
                # Interleaved format: entries at indices track_idx, track_idx+3, track_idx+6, ...
                track_entries = [sequence_data[i] for i in range(track_idx, len(sequence_data), 3)]
            else:
                # Single-track format: use all entries
                track_entries = sequence_data

            # Display sequence with transpose applied
            for step, seq_entry in enumerate(track_entries):
                # Get values
                inst_str = seq_entry.instrument_display() if hasattr(seq_entry, 'instrument_display') else f"{seq_entry.instrument:02X}"
                cmd_str = seq_entry.command_display() if hasattr(seq_entry, 'command_display') else f"{seq_entry.command:02X}"

                # Apply transpose to note
                note_value = seq_entry.note if hasattr(seq_entry, 'note') else 0
                transposed_note = self._apply_transpose(note_value, transpose)
                note_str = self._format_note(transposed_note)

                # Format instrument and command to fixed width
                inst_display = inst_str if inst_str != "00" else "--"
                cmd_display = cmd_str if cmd_str != "00" else "--"

                track_text += f"  {step:04X} | {inst_display:4s} | {cmd_display:4s} | {note_str:6s}\n"

            track_text += "  [End of sequence]\n\n"

        self.track_text.setPlainText(track_text)

    def _has_valid_sequences(self) -> bool:
        """Check if loaded SF2 file has valid sequence data

        Returns True if the SF2 file has usable sequences (either traditional format
        or packed format like Laxity driver files). Returns False if sequences are
        unavailable or invalid.
        """
        if not self.parser or not self.parser.sequences:
            return False

        # Count non-empty sequences with meaningful data
        non_empty_sequences = 0
        for seq_idx, seq_data in self.parser.sequences.items():
            if seq_data:  # Has sequence data
                # Check if it has any non-zero notes or commands
                has_meaningful_data = False
                for entry in seq_data:
                    if entry.note != 0 or entry.command != 0:
                        has_meaningful_data = True
                        break

                if has_meaningful_data:
                    non_empty_sequences += 1

        # If we found at least one sequence with meaningful data, enable the tab
        return non_empty_sequences > 0

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About SF2 Viewer",
            "SF2 Viewer v2.1\n\n"
            "Professional viewer for SID Factory II SF2 files\n"
            "Display driver information, tables, sequences, orderlists, and memory layout\n\n"
            "Features:\n"
            "• Drag and drop SF2 files to view\n"
            "• Recent Files menu for quick access\n"
            "• Audio playback and waveform visualization\n"
            "• Complete SF2 structure analysis"
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
    """Main entry point - accepts optional SF2 file path as argument"""
    app = QApplication(sys.argv)

    # Check if a file path was provided as argument
    file_to_load = None
    if len(sys.argv) > 1:
        file_to_load = sys.argv[1]

    window = SF2ViewerWindow(file_to_load)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
