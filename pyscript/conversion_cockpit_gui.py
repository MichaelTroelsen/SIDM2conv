#!/usr/bin/env python3
"""
Conversion Cockpit GUI - Mission control for batch SID conversion

Professional batch conversion interface with real-time monitoring,
configurable pipeline steps, and progressive disclosure (simple → advanced mode).

Version: 1.0.0
Date: 2025-12-22
"""

import sys
import os
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

# Try to import PyQt6, fallback instructions if not available
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QLabel, QPushButton, QFileDialog, QMessageBox,
        QStatusBar, QProgressBar, QTextEdit, QTableWidget, QTableWidgetItem,
        QCheckBox, QComboBox, QLineEdit, QGroupBox, QHeaderView, QListWidget,
        QSplitter, QFrame, QScrollArea
    )
    from PyQt6.QtCore import Qt, QSettings, QTimer, pyqtSignal, QObject, QUrl, QSize
    from PyQt6.QtGui import QFont, QColor, QIcon, QDragEnterEvent, QDropEvent
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    print("ERROR: PyQt6 is required for the Conversion Cockpit")
    print("\nInstall with: pip install PyQt6")
    sys.exit(1)

# Try to import QtWebEngineWidgets for embedded dashboard view (optional)
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    QWebEngineView = None  # For type checking

# Import cockpit modules
from conversion_executor import ConversionExecutor
from pipeline_config import PipelineConfig, PipelineStep
from cockpit_widgets import StatsCard, ProgressWidget, FileListWidget, LogStreamWidget
from cockpit_history_widgets import BatchHistorySectionWidget, HistoryControlWidget
from batch_history_manager import BatchHistoryManager
from cockpit_styles import ColorScheme, IconGenerator, StyleSheet
from report_generator import generate_batch_report


class CockpitMainWindow(QMainWindow):
    """Main window for Conversion Cockpit application"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SIDM2 Conversion Cockpit v1.0")
        self.setGeometry(100, 100, 1600, 1000)

        # State
        self.config = PipelineConfig()
        self.executor: Optional[ConversionExecutor] = None
        self.settings = QSettings("SIDM2", "ConversionCockpit")
        self.selected_files: List[str] = []
        self.is_running = False
        self.history_manager = BatchHistoryManager()

        # Initialize UI
        self.init_ui()
        self.setup_drag_drop()
        self.load_settings()

        # Create executor
        self.setup_executor()

    def init_ui(self):
        """Initialize the user interface"""
        # Apply stylesheet
        self.setStyleSheet(StyleSheet.get_main_stylesheet())

        # Set window icon
        app_icon = QIcon(IconGenerator.create_circular_icon(ColorScheme.PRIMARY, 64, "C"))
        self.setWindowIcon(app_icon)

        # Central widget with main layout
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Tab widget for main content
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Tab 1: Dashboard (Overview)
        self.dashboard_tab = self.create_dashboard_tab()
        self.tabs.addTab(self.dashboard_tab, "🏠 Dashboard")

        # Tab 2: Files
        self.files_tab = self.create_files_tab()
        self.tabs.addTab(self.files_tab, "📁 Files")

        # Tab 3: Configuration
        self.config_tab = self.create_config_tab()
        self.tabs.addTab(self.config_tab, "⚙️ Config")

        # Tab 4: Results
        self.results_tab = self.create_results_tab()
        self.tabs.addTab(self.results_tab, "📊 Results")

        # Tab 5: Logs
        self.logs_tab = self.create_logs_tab()
        self.tabs.addTab(self.logs_tab, "📝 Logs")

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.update_status_bar()

    def create_dashboard_tab(self) -> QWidget:
        """Create the Dashboard tab (main overview)"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title = QLabel("Conversion Dashboard")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Stats cards row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)

        # Files card
        self.files_card = StatsCard("FILES", [
            ("Total", "0"),
            ("Selected", "0"),
            ("Estimated", "0 minutes")
        ])
        stats_layout.addWidget(self.files_card)

        # Progress card
        self.progress_card = StatsCard("PROGRESS", [
            ("Current", "0/0"),
            ("Step", "0/0"),
            ("Time", "00:00 / 00:00")
        ])
        stats_layout.addWidget(self.progress_card)

        # Results card
        self.results_card = StatsCard("RESULTS", [
            ("Pass", "0"),
            ("Fail", "0"),
            ("Avg Accuracy", "0%")
        ])
        stats_layout.addWidget(self.results_card)

        layout.addLayout(stats_layout)

        # Control panel
        control_group = QGroupBox("Controls")
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)

        # Start button with play icon
        self.start_btn = QPushButton("START")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setIcon(QIcon(IconGenerator.create_play_icon(ColorScheme.SUCCESS, 48)))
        self.start_btn.setIconSize(QSize(24, 24))
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.start_conversion)
        control_layout.addWidget(self.start_btn)

        # Pause button with pause icon
        self.pause_btn = QPushButton("PAUSE")
        self.pause_btn.setObjectName("pauseBtn")
        self.pause_btn.setIcon(QIcon(IconGenerator.create_pause_icon(ColorScheme.WARNING, 48)))
        self.pause_btn.setIconSize(QSize(24, 24))
        self.pause_btn.setMinimumHeight(40)
        self.pause_btn.clicked.connect(self.pause_conversion)
        self.pause_btn.setEnabled(False)
        control_layout.addWidget(self.pause_btn)

        # Stop button with stop icon
        self.stop_btn = QPushButton("STOP")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setIcon(QIcon(IconGenerator.create_stop_icon(ColorScheme.ERROR, 48)))
        self.stop_btn.setIconSize(QSize(24, 24))
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.clicked.connect(self.stop_conversion)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)

        # Settings button
        settings_btn = QPushButton("SETTINGS")
        settings_btn.setIcon(QIcon(IconGenerator.create_settings_icon(ColorScheme.PRIMARY, 48)))
        settings_btn.setIconSize(QSize(24, 24))
        settings_btn.setMinimumHeight(40)
        settings_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))  # Switch to Config tab
        control_layout.addWidget(settings_btn)

        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # Current operation display
        operation_group = QGroupBox("Current Operation")
        operation_layout = QVBoxLayout()

        # Status row with icon and text
        status_layout = QHBoxLayout()
        self.status_icon_label = QLabel()
        self.status_icon_label.setPixmap(IconGenerator.create_checkmark_icon(ColorScheme.SUCCESS, 24))
        self.status_icon_label.setMaximumWidth(32)
        status_layout.addWidget(self.status_icon_label)

        self.current_file_label = QLabel("No operation in progress")
        self.current_file_label.setStyleSheet("font-size: 12px; padding: 5px;")
        status_layout.addWidget(self.current_file_label)
        status_layout.addStretch()

        operation_layout.addLayout(status_layout)

        self.current_step_label = QLabel("Waiting to start...")
        self.current_step_label.setStyleSheet("font-size: 11px; color: #666; padding: 5px;")
        operation_layout.addWidget(self.current_step_label)

        operation_group.setLayout(operation_layout)
        layout.addWidget(operation_group)

        # Progress bar
        self.main_progress = QProgressBar()
        self.main_progress.setMaximum(100)
        self.main_progress.setValue(0)
        self.main_progress.setTextVisible(True)
        layout.addWidget(self.main_progress)

        layout.addStretch()
        return widget

    def create_files_tab(self) -> QWidget:
        """Create the Files tab"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Left panel: Input directory controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Input directory section
        input_group = QGroupBox("Input Directory")
        input_layout = QVBoxLayout()

        dir_select_layout = QHBoxLayout()
        self.dir_path_label = QLabel("No directory selected")
        self.dir_path_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        dir_select_layout.addWidget(self.dir_path_label)

        browse_dir_btn = QPushButton("Browse...")
        browse_dir_btn.clicked.connect(self.browse_directory)
        dir_select_layout.addWidget(browse_dir_btn)

        scan_btn = QPushButton("Scan")
        scan_btn.clicked.connect(self.scan_directory)
        dir_select_layout.addWidget(scan_btn)

        input_layout.addLayout(dir_select_layout)

        self.include_subdir_cb = QCheckBox("Include subdirectories")
        self.include_subdir_cb.setChecked(True)
        input_layout.addWidget(self.include_subdir_cb)

        self.laxity_only_cb = QCheckBox("Laxity files only")
        input_layout.addWidget(self.laxity_only_cb)

        input_group.setLayout(input_layout)
        left_layout.addWidget(input_group)

        # Actions section
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_files)
        actions_layout.addWidget(select_all_btn)

        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self.select_no_files)
        actions_layout.addWidget(select_none_btn)

        add_files_btn = QPushButton("Add Files...")
        add_files_btn.clicked.connect(self.add_files_manually)
        actions_layout.addWidget(add_files_btn)

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_selected_files)
        actions_layout.addWidget(remove_btn)

        actions_group.setLayout(actions_layout)
        left_layout.addWidget(actions_group)

        left_layout.addStretch()
        left_panel.setMaximumWidth(250)

        # Right panel: File list
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        file_list_label = QLabel("File List")
        file_list_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        right_layout.addWidget(file_list_label)

        self.file_list_widget = FileListWidget()
        self.file_list_widget.files_changed.connect(self.on_files_changed)
        right_layout.addWidget(self.file_list_widget)

        self.selection_count_label = QLabel("0 files selected")
        self.selection_count_label.setStyleSheet("font-size: 11px; color: #666; padding: 5px;")
        right_layout.addWidget(self.selection_count_label)

        # Add panels to splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)
        return widget

    def create_config_tab(self) -> QWidget:
        """Create the Configuration tab"""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Create scroll area for configuration options
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(15)

        # === Mode Selection ===
        mode_group = QGroupBox("Mode")
        mode_layout = QVBoxLayout()

        mode_label = QLabel("Select conversion mode:")
        mode_layout.addWidget(mode_label)

        self.mode_simple_radio = QCheckBox("Simple Mode (Essential steps: conversion, packing, validation)")
        self.mode_simple_radio.setChecked(True)
        self.mode_simple_radio.toggled.connect(lambda: self.on_mode_changed("simple"))
        mode_layout.addWidget(self.mode_simple_radio)

        self.mode_advanced_radio = QCheckBox("Advanced Mode (All 14 pipeline steps)")
        self.mode_advanced_radio.toggled.connect(lambda: self.on_mode_changed("advanced"))
        mode_layout.addWidget(self.mode_advanced_radio)

        self.mode_custom_radio = QCheckBox("Custom Mode (Choose your own steps)")
        self.mode_custom_radio.toggled.connect(lambda: self.on_mode_changed("custom"))
        mode_layout.addWidget(self.mode_custom_radio)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # === Driver Configuration ===
        driver_group = QGroupBox("Driver Configuration")
        driver_layout = QVBoxLayout()

        # Primary driver selection
        driver_select_layout = QHBoxLayout()
        driver_select_layout.addWidget(QLabel("Primary Driver:"))

        self.driver_combo = QComboBox()
        self.driver_combo.addItems(["laxity", "driver11", "np20"])
        self.driver_combo.setCurrentText("laxity")
        self.driver_combo.currentTextChanged.connect(self.on_driver_changed)
        driver_select_layout.addWidget(self.driver_combo)
        driver_select_layout.addStretch()

        driver_layout.addLayout(driver_select_layout)

        # Generate both option
        self.generate_both_cb = QCheckBox("Generate both NP20 and Driver 11 versions")
        driver_layout.addWidget(self.generate_both_cb)

        # Output directory
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Directory:"))

        self.output_dir_label = QLabel(self.config.output_directory)
        self.output_dir_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        output_layout.addWidget(self.output_dir_label, 1)

        output_browse_btn = QPushButton("Browse...")
        output_browse_btn.clicked.connect(self.browse_output_directory)
        output_layout.addWidget(output_browse_btn)

        output_new_btn = QPushButton("New")
        output_new_btn.clicked.connect(self.create_new_output_directory)
        output_layout.addWidget(output_new_btn)

        driver_layout.addLayout(output_layout)

        # Options
        self.overwrite_cb = QCheckBox("Overwrite existing files")
        self.overwrite_cb.setChecked(self.config.overwrite_existing)
        driver_layout.addWidget(self.overwrite_cb)

        self.nested_dirs_cb = QCheckBox("Create nested directories")
        self.nested_dirs_cb.setChecked(self.config.create_nested_dirs)
        driver_layout.addWidget(self.nested_dirs_cb)

        driver_group.setLayout(driver_layout)
        layout.addWidget(driver_group)

        # === Pipeline Steps ===
        steps_group = QGroupBox("Pipeline Steps")
        steps_layout = QVBoxLayout()

        steps_label = QLabel("Select which steps to execute:")
        steps_label.setStyleSheet("font-weight: bold;")
        steps_layout.addWidget(steps_label)

        # Create checkboxes for each pipeline step
        self.step_checkboxes = {}
        from pipeline_config import PipelineStep

        for step in PipelineStep:
            cb = QCheckBox(f"{step.description} {'(Required)' if step.default_enabled else ''}")
            cb.setChecked(self.config.enabled_steps.get(step.step_id, step.default_enabled))
            cb.toggled.connect(lambda checked, s=step.step_id: self.on_step_toggled(s, checked))
            steps_layout.addWidget(cb)
            self.step_checkboxes[step.step_id] = cb

        # Presets buttons
        presets_layout = QHBoxLayout()
        presets_layout.addWidget(QLabel("Presets:"))

        simple_preset_btn = QPushButton("Simple")
        simple_preset_btn.clicked.connect(lambda: self.apply_preset("simple"))
        presets_layout.addWidget(simple_preset_btn)

        full_preset_btn = QPushButton("Full")
        full_preset_btn.clicked.connect(lambda: self.apply_preset("advanced"))
        presets_layout.addWidget(full_preset_btn)

        save_preset_btn = QPushButton("Save As...")
        save_preset_btn.clicked.connect(self.save_custom_preset)
        presets_layout.addWidget(save_preset_btn)

        presets_layout.addStretch()
        steps_layout.addLayout(presets_layout)

        steps_group.setLayout(steps_layout)
        layout.addWidget(steps_group)

        # === Logging & Validation ===
        logging_group = QGroupBox("Logging & Validation")
        logging_layout = QVBoxLayout()

        # Log level
        log_level_layout = QHBoxLayout()
        log_level_layout.addWidget(QLabel("Log Level:"))

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["ERROR", "WARN", "INFO", "DEBUG"])
        self.log_level_combo.setCurrentText(self.config.log_level)
        log_level_layout.addWidget(self.log_level_combo)
        log_level_layout.addStretch()

        logging_layout.addLayout(log_level_layout)

        # Log to file
        self.log_to_file_cb = QCheckBox("Log to file")
        self.log_to_file_cb.setChecked(self.config.log_to_file)
        logging_layout.addWidget(self.log_to_file_cb)

        self.log_json_cb = QCheckBox("JSON format (for analysis)")
        self.log_json_cb.setChecked(self.config.log_json_format)
        logging_layout.addWidget(self.log_json_cb)

        # Validation duration
        val_duration_layout = QHBoxLayout()
        val_duration_layout.addWidget(QLabel("Validation Duration:"))

        self.val_duration_combo = QComboBox()
        self.val_duration_combo.addItems(["10s", "30s", "60s", "120s"])
        self.val_duration_combo.setCurrentText(f"{self.config.validation_duration}s")
        val_duration_layout.addWidget(self.val_duration_combo)
        val_duration_layout.addStretch()

        logging_layout.addLayout(val_duration_layout)

        self.run_validation_cb = QCheckBox("Run accuracy validation")
        self.run_validation_cb.setChecked(self.config.run_accuracy_validation)
        logging_layout.addWidget(self.run_validation_cb)

        logging_group.setLayout(logging_layout)
        layout.addWidget(logging_group)

        # === Execution Options ===
        exec_group = QGroupBox("Execution Options")
        exec_layout = QVBoxLayout()

        self.stop_on_error_cb = QCheckBox("Stop batch on first error")
        self.stop_on_error_cb.setChecked(self.config.stop_on_error)
        exec_layout.addWidget(self.stop_on_error_cb)

        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Step Timeout:"))

        self.timeout_combo = QComboBox()
        self.timeout_combo.addItems(["30s", "60s", "120s", "300s"])
        self.timeout_combo.setCurrentText(f"{self.config.step_timeout_ms // 1000}s")
        timeout_layout.addWidget(self.timeout_combo)
        timeout_layout.addStretch()

        exec_layout.addLayout(timeout_layout)

        exec_group.setLayout(exec_layout)
        layout.addWidget(exec_group)

        # === Batch History ===
        self.history_section = BatchHistorySectionWidget()
        self.history_section.set_on_load_callback(self.on_history_load)
        self.history_section.history_control.save_btn = QPushButton("Save Current Batch to History")
        self.history_section.history_control.save_btn.clicked.connect(self.on_save_batch_to_history)
        layout.addWidget(self.history_section)

        # === Save/Load Configuration ===
        config_actions_layout = QHBoxLayout()
        config_actions_layout.addStretch()

        save_config_btn = QPushButton("Save Configuration")
        save_config_btn.clicked.connect(self.save_configuration)
        config_actions_layout.addWidget(save_config_btn)

        load_config_btn = QPushButton("Load Configuration")
        load_config_btn.clicked.connect(self.load_configuration)
        config_actions_layout.addWidget(load_config_btn)

        reset_config_btn = QPushButton("Reset to Defaults")
        reset_config_btn.clicked.connect(self.reset_configuration)
        config_actions_layout.addWidget(reset_config_btn)

        layout.addLayout(config_actions_layout)

        layout.addStretch()

        # Set scroll content
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

        return widget

    def create_results_tab(self) -> QWidget:
        """Create the Results tab with embedded dashboard view"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Create splitter for results table (top) and dashboard (bottom)
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Top section: Results table and stats
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "File", "Driver", "Steps", "Accuracy", "Status", "Action"
        ])
        self.results_table.horizontalHeader().setStretchLastSection(False)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        top_layout.addWidget(self.results_table)

        # Statistics section
        self.stats_label = QLabel("Statistics: Total: 0 | Passed: 0 (0%) | Failed: 0 (0%) | Avg Accuracy: 0%")
        self.stats_label.setStyleSheet("font-size: 11px; padding: 5px;")
        top_layout.addWidget(self.stats_label)

        # Export buttons
        export_layout = QHBoxLayout()
        export_layout.addStretch()

        export_csv_btn = QPushButton("Export CSV")
        export_layout.addWidget(export_csv_btn)

        export_json_btn = QPushButton("Export JSON")
        export_layout.addWidget(export_json_btn)

        export_html_btn = QPushButton("Export HTML Report")
        export_html_btn.clicked.connect(self.export_html_report)
        export_layout.addWidget(export_html_btn)

        self.export_dashboard_btn = QPushButton("Generate & View Dashboard")
        self.export_dashboard_btn.clicked.connect(self.generate_and_view_dashboard)
        export_layout.addWidget(self.export_dashboard_btn)

        refresh_dashboard_btn = QPushButton("Refresh Dashboard")
        refresh_dashboard_btn.clicked.connect(self.refresh_dashboard)
        export_layout.addWidget(refresh_dashboard_btn)

        top_layout.addLayout(export_layout)

        splitter.addWidget(top_widget)

        # Bottom section: Embedded dashboard view (if WebEngine available)
        if WEBENGINE_AVAILABLE:
            dashboard_widget = QWidget()
            dashboard_layout = QVBoxLayout(dashboard_widget)
            dashboard_layout.setContentsMargins(0, 0, 0, 0)

            dashboard_label = QLabel("📊 Validation Dashboard")
            dashboard_label.setStyleSheet("font-size: 12px; font-weight: bold; padding: 5px;")
            dashboard_layout.addWidget(dashboard_label)

            self.dashboard_view = QWebEngineView()
            dashboard_layout.addWidget(self.dashboard_view)

            splitter.addWidget(dashboard_widget)

            # Set initial splitter sizes (60% table, 40% dashboard)
            splitter.setSizes([600, 400])
        else:
            # If WebEngine not available, show info label
            info_label = QLabel("ℹ️  Install PyQt6-WebEngine to view dashboard here\n"
                               "Current: Dashboard will open in external browser")
            info_label.setStyleSheet("padding: 10px; background-color: #FFF3CD; border: 1px solid #FFEB3B;")
            info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            splitter.addWidget(info_label)
            splitter.setSizes([900, 100])
            self.dashboard_view = None

        layout.addWidget(splitter)

        return widget

    def create_logs_tab(self) -> QWidget:
        """Create the Logs tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Filter controls
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Level:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["ALL", "ERROR", "WARN", "INFO", "DEBUG"])
        self.log_level_combo.setCurrentText("ALL")
        filter_layout.addWidget(self.log_level_combo)

        filter_layout.addWidget(QLabel("Search:"))
        self.log_search_input = QLineEdit()
        filter_layout.addWidget(self.log_search_input)

        clear_search_btn = QPushButton("X")
        clear_search_btn.setMaximumWidth(30)
        clear_search_btn.clicked.connect(lambda: self.log_search_input.clear())
        filter_layout.addWidget(clear_search_btn)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Log display
        self.log_widget = LogStreamWidget()
        layout.addWidget(self.log_widget)

        # Log controls
        log_controls_layout = QHBoxLayout()

        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        log_controls_layout.addWidget(self.auto_scroll_cb)

        log_controls_layout.addStretch()

        clear_logs_btn = QPushButton("Clear Logs")
        clear_logs_btn.clicked.connect(self.clear_logs)
        log_controls_layout.addWidget(clear_logs_btn)

        export_logs_btn = QPushButton("Export...")
        log_controls_layout.addWidget(export_logs_btn)

        layout.addLayout(log_controls_layout)

        return widget

    def setup_drag_drop(self):
        """Enable drag and drop for files"""
        self.setAcceptDrops(True)

    def setup_executor(self):
        """Create and configure the conversion executor"""
        self.executor = ConversionExecutor(self.config)

        # Connect signals
        self.executor.batch_started.connect(self.on_batch_started)
        self.executor.file_started.connect(self.on_file_started)
        self.executor.step_started.connect(self.on_step_started)
        self.executor.step_completed.connect(self.on_step_completed)
        self.executor.file_completed.connect(self.on_file_completed)
        self.executor.batch_completed.connect(self.on_batch_completed)
        self.executor.progress_updated.connect(self.on_progress_updated)
        self.executor.log_message.connect(self.on_log_message)
        self.executor.error_occurred.connect(self.on_error_occurred)

    # =========================================================================
    # Control Methods
    # =========================================================================

    def start_conversion(self):
        """Start batch conversion"""
        if not self.selected_files:
            QMessageBox.warning(self, "No Files", "Please select files to convert first.")
            return

        self.is_running = True
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)

        # Update status icon to show running state
        self._update_status_icon("running")

        # Start executor
        self.executor.start_batch(self.selected_files)

    def pause_conversion(self):
        """Pause batch conversion"""
        if self.executor and self.is_running:
            self.executor.pause()
            self.pause_btn.setText("▶ RESUME")
            self.pause_btn.clicked.disconnect()
            self.pause_btn.clicked.connect(self.resume_conversion)
            # Update status icon to show paused state
            self._update_status_icon("paused")

    def resume_conversion(self):
        """Resume batch conversion"""
        if self.executor:
            self.executor.resume()
            self.pause_btn.setText("⏸ PAUSE")
            self.pause_btn.clicked.disconnect()
            self.pause_btn.clicked.connect(self.pause_conversion)
            # Update status icon to show running state
            self._update_status_icon("running")

    def stop_conversion(self):
        """Stop batch conversion"""
        if self.executor and self.is_running:
            reply = QMessageBox.question(
                self,
                "Stop Conversion",
                "Are you sure you want to stop the batch conversion?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.executor.stop()
                self.is_running = False
                self.start_btn.setEnabled(True)
                self.pause_btn.setEnabled(False)
                self.stop_btn.setEnabled(False)
                # Update status icon to show stopped state
                self._update_status_icon("stopped")

    # =========================================================================
    # UI Helper Methods
    # =========================================================================

    def _update_status_icon(self, state: str):
        """Update the status icon based on conversion state

        Args:
            state: One of 'idle', 'running', 'paused', 'stopped', 'completed', 'error'
        """
        if state == "running":
            pixmap = IconGenerator.create_play_icon(ColorScheme.INFO, 24)
        elif state == "paused":
            pixmap = IconGenerator.create_pause_icon(ColorScheme.WARNING, 24)
        elif state == "completed":
            pixmap = IconGenerator.create_checkmark_icon(ColorScheme.SUCCESS, 24)
        elif state == "error":
            pixmap = IconGenerator.create_error_icon(ColorScheme.ERROR, 24)
        else:  # idle, stopped, or unknown
            pixmap = IconGenerator.create_checkmark_icon(ColorScheme.SUCCESS, 24)

        self.status_icon_label.setPixmap(pixmap)

    # =========================================================================
    # Dashboard Methods
    # =========================================================================

    def generate_and_view_dashboard(self):
        """Generate validation dashboard HTML and display it in embedded view"""
        try:
            # Check if validation directory and database exist
            validation_dir = Path("validation")
            dashboard_html = validation_dir / "dashboard.html"
            database_file = validation_dir / "database.sqlite"

            if not database_file.exists():
                QMessageBox.information(
                    self,
                    "No Validation Data",
                    "No validation data found. Complete a batch conversion with validation enabled first.\n\n"
                    "Validation data is stored in: validation/database.sqlite"
                )
                return

            # Generate dashboard HTML using generate_dashboard.py
            self.update_status_bar("Generating validation dashboard...")

            # Import and run dashboard generator
            import subprocess
            result = subprocess.run(
                [sys.executable, "scripts/generate_dashboard.py"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                QMessageBox.warning(
                    self,
                    "Dashboard Generation Failed",
                    f"Failed to generate dashboard:\n\n{result.stderr}"
                )
                self.update_status_bar("Dashboard generation failed")
                return

            # Load dashboard in web view (if available) or open in browser
            if WEBENGINE_AVAILABLE and self.dashboard_view:
                if dashboard_html.exists():
                    url = QUrl.fromLocalFile(str(dashboard_html.absolute()))
                    self.dashboard_view.setUrl(url)
                    self.update_status_bar("Dashboard loaded in view")
                    QMessageBox.information(
                        self,
                        "Dashboard Generated",
                        "Validation dashboard generated and loaded successfully!\n\n"
                        "View it in the Results tab below."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Dashboard File Not Found",
                        f"Dashboard HTML file not found at: {dashboard_html}"
                    )
            else:
                # Fallback: Open in external browser
                import webbrowser
                webbrowser.open(f"file://{dashboard_html.absolute()}")
                self.update_status_bar("Dashboard opened in external browser")
                QMessageBox.information(
                    self,
                    "Dashboard Generated",
                    f"Dashboard generated and opened in your browser.\n\n"
                    f"Location: {dashboard_html}\n\n"
                    f"Install PyQt6-WebEngine to view dashboard within the app."
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to generate/view dashboard:\n\n{str(e)}"
            )
            self.update_status_bar("Error generating dashboard")

    def refresh_dashboard(self):
        """Refresh the embedded dashboard view"""
        try:
            validation_dir = Path("validation")
            dashboard_html = validation_dir / "dashboard.html"

            if not dashboard_html.exists():
                QMessageBox.information(
                    self,
                    "Dashboard Not Found",
                    "Dashboard has not been generated yet.\n\n"
                    "Click 'Generate & View Dashboard' first."
                )
                return

            if WEBENGINE_AVAILABLE and self.dashboard_view:
                # Reload the dashboard in the web view
                self.dashboard_view.reload()
                self.update_status_bar("Dashboard refreshed")
            else:
                # If no web view, just open in browser
                import webbrowser
                webbrowser.open(f"file://{dashboard_html.absolute()}")
                self.update_status_bar("Dashboard opened in browser")

        except Exception as e:
            QMessageBox.warning(
                self,
                "Refresh Failed",
                f"Failed to refresh dashboard:\n\n{str(e)}"
            )

    def export_html_report(self):
        """Export batch conversion results to HTML report"""
        try:
            # Check if there are results to export
            if not self.executor or not self.executor.results:
                QMessageBox.information(
                    self,
                    "No Results",
                    "No conversion results available to export.\n\n"
                    "Complete a batch conversion first."
                )
                return

            # Ask user for output file location
            default_filename = f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            output_file, _ = QFileDialog.getSaveFileName(
                self,
                "Export Batch Report",
                str(Path.home() / default_filename),
                "HTML Files (*.html);;All Files (*.*)"
            )

            if not output_file:
                # User cancelled
                return

            self.update_status_bar("Generating batch report...")

            # Collect results
            results_list = []
            for filename, result in self.executor.results.items():
                results_list.append(self.executor._result_to_dict(result))

            # Get summary statistics
            summary = self.executor._get_summary()

            # Get config (optional)
            config = {
                "primary_driver": self.executor.config.primary_driver,
                "enabled_steps": [step.name for step in self.executor.config.steps if step.enabled]
            }

            # Generate report
            success = generate_batch_report(
                results=results_list,
                summary=summary,
                output_path=output_file,
                config=config
            )

            if success:
                self.update_status_bar(f"Batch report exported: {Path(output_file).name}")

                # Ask if user wants to open the report
                reply = QMessageBox.question(
                    self,
                    "Report Exported",
                    f"Batch report exported successfully!\n\n"
                    f"Location: {output_file}\n\n"
                    f"Would you like to open it now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )

                if reply == QMessageBox.StandardButton.Yes:
                    import webbrowser
                    webbrowser.open(f"file://{Path(output_file).absolute()}")
            else:
                QMessageBox.warning(
                    self,
                    "Export Failed",
                    "Failed to generate batch report.\n\n"
                    "Check the console for error details."
                )
                self.update_status_bar("Report export failed")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export batch report:\n\n{str(e)}"
            )
            self.update_status_bar("Error exporting report")

    # =========================================================================
    # File Management Methods
    # =========================================================================

    def browse_directory(self):
        """Browse for input directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Input Directory",
            str(Path.home())
        )
        if directory:
            self.dir_path_label.setText(directory)

    def scan_directory(self):
        """Scan directory for SID files"""
        directory = self.dir_path_label.text()
        if directory == "No directory selected":
            QMessageBox.warning(self, "No Directory", "Please select a directory first.")
            return

        self.log_widget.append_log("INFO", f"Scanning directory: {directory}")

        # Scan for SID files
        dir_path = Path(directory)
        if not dir_path.exists():
            QMessageBox.warning(self, "Invalid Directory", f"Directory does not exist: {directory}")
            return

        # Find SID files
        pattern = "**/*.sid" if self.include_subdir_cb.isChecked() else "*.sid"
        sid_files = list(dir_path.glob(pattern))

        if not sid_files:
            QMessageBox.information(self, "No Files Found", "No SID files found in the selected directory.")
            return

        # Filter for Laxity only if checkbox is checked
        if self.laxity_only_cb.isChecked():
            # TODO: Filter by player type (requires player-id.exe integration)
            self.log_widget.append_log("WARN", "Laxity-only filtering not yet implemented")

        # Add files to list
        self.file_list_widget.clear()
        self.file_list_widget.add_files([str(f) for f in sid_files])

        self.log_widget.append_log("INFO", f"Found {len(sid_files)} SID files")

    def add_files_manually(self):
        """Add files manually via file dialog"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select SID Files",
            str(Path.home()),
            "SID Files (*.sid);;All Files (*)"
        )
        if files:
            self.file_list_widget.add_files(files)
            self.log_widget.append_log("INFO", f"Added {len(files)} files")

    def select_all_files(self):
        """Select all files in list"""
        self.file_list_widget.select_all()

    def select_no_files(self):
        """Deselect all files"""
        self.file_list_widget.select_none()

    def remove_selected_files(self):
        """Remove selected files from list"""
        self.file_list_widget.remove_selected()

    def on_files_changed(self, selected_files: List[str]):
        """Handle file selection changes"""
        self.selected_files = selected_files
        count = len(selected_files)
        total = len(self.file_list_widget.get_all_files())

        # Update selection count label
        self.selection_count_label.setText(f"{count} of {total} files selected")

        # Update dashboard stats
        self.files_card.update_stat("Selected", str(count))
        self.files_card.update_stat("Total", str(total))

        # Estimate time (assume 10 seconds per file with 6 steps)
        estimated_minutes = (count * 10 * 6) / 60
        self.files_card.update_stat("Estimated", f"{estimated_minutes:.1f} minutes")

    # =========================================================================
    # Configuration Methods
    # =========================================================================

    def on_mode_changed(self, mode: str):
        """Handle mode selection change"""
        # Uncheck other mode radios
        if mode == "simple":
            self.mode_advanced_radio.setChecked(False)
            self.mode_custom_radio.setChecked(False)
        elif mode == "advanced":
            self.mode_simple_radio.setChecked(False)
            self.mode_custom_radio.setChecked(False)
        elif mode == "custom":
            self.mode_simple_radio.setChecked(False)
            self.mode_advanced_radio.setChecked(False)

        # Apply preset
        self.config.set_mode(mode)
        self.apply_config_to_ui()
        self.update_status_bar()

    def on_driver_changed(self, driver: str):
        """Handle driver selection change"""
        self.config.primary_driver = driver
        self.update_status_bar()

    def on_step_toggled(self, step_id: str, checked: bool):
        """Handle pipeline step checkbox toggle"""
        if checked:
            self.config.enable_step(step_id)
        else:
            self.config.disable_step(step_id)

        # If mode was not custom, switch to custom
        if self.config.mode != "custom":
            self.mode_custom_radio.setChecked(True)

    def apply_preset(self, preset: str):
        """Apply a preset configuration"""
        self.config.set_mode(preset)
        self.apply_config_to_ui()

        # Update mode radio buttons
        if preset == "simple":
            self.mode_simple_radio.setChecked(True)
        elif preset == "advanced":
            self.mode_advanced_radio.setChecked(True)

        self.log_widget.append_log("INFO", f"Applied {preset} preset")

    def apply_config_to_ui(self):
        """Apply current config to UI controls"""
        # Update step checkboxes
        for step_id, checkbox in self.step_checkboxes.items():
            enabled = self.config.enabled_steps.get(step_id, False)
            checkbox.setChecked(enabled)

    def save_custom_preset(self):
        """Save current configuration as custom preset"""
        # TODO: Implement custom preset saving
        self.log_widget.append_log("INFO", "Custom preset saving not yet implemented")

    def browse_output_directory(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self.config.output_directory or str(Path.home())
        )
        if directory:
            self.config.output_directory = directory
            self.output_dir_label.setText(directory)
            self.update_status_bar()

    def create_new_output_directory(self):
        """Create a new output directory"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_dir = f"output_{timestamp}"

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Parent Directory for New Output Folder",
            str(Path.cwd())
        )

        if directory:
            new_path = Path(directory) / new_dir
            new_path.mkdir(exist_ok=True)
            self.config.output_directory = str(new_path)
            self.output_dir_label.setText(str(new_path))
            self.update_status_bar()
            self.log_widget.append_log("INFO", f"Created output directory: {new_path}")

    def save_configuration(self):
        """Save current configuration to QSettings"""
        # Update config from UI
        self.config.primary_driver = self.driver_combo.currentText()
        self.config.generate_both = self.generate_both_cb.isChecked()
        self.config.overwrite_existing = self.overwrite_cb.isChecked()
        self.config.create_nested_dirs = self.nested_dirs_cb.isChecked()
        self.config.log_level = self.log_level_combo.currentText()
        self.config.log_to_file = self.log_to_file_cb.isChecked()
        self.config.log_json_format = self.log_json_cb.isChecked()
        self.config.validation_duration = int(self.val_duration_combo.currentText().rstrip('s'))
        self.config.run_accuracy_validation = self.run_validation_cb.isChecked()
        self.config.stop_on_error = self.stop_on_error_cb.isChecked()
        self.config.step_timeout_ms = int(self.timeout_combo.currentText().rstrip('s')) * 1000

        # Save to QSettings
        self.config.save_to_settings(self.settings)

        self.log_widget.append_log("INFO", "Configuration saved")
        QMessageBox.information(self, "Configuration Saved", "Configuration has been saved successfully.")

    def load_configuration(self):
        """Load configuration from QSettings"""
        self.config = PipelineConfig.load_from_settings(self.settings)

        # Apply to UI
        self.driver_combo.setCurrentText(self.config.primary_driver)
        self.generate_both_cb.setChecked(self.config.generate_both)
        self.output_dir_label.setText(self.config.output_directory)
        self.overwrite_cb.setChecked(self.config.overwrite_existing)
        self.nested_dirs_cb.setChecked(self.config.create_nested_dirs)
        self.log_level_combo.setCurrentText(self.config.log_level)
        self.log_to_file_cb.setChecked(self.config.log_to_file)
        self.log_json_cb.setChecked(self.config.log_json_format)
        self.val_duration_combo.setCurrentText(f"{self.config.validation_duration}s")
        self.run_validation_cb.setChecked(self.config.run_accuracy_validation)
        self.stop_on_error_cb.setChecked(self.config.stop_on_error)
        self.timeout_combo.setCurrentText(f"{self.config.step_timeout_ms // 1000}s")

        # Apply mode
        if self.config.mode == "simple":
            self.mode_simple_radio.setChecked(True)
        elif self.config.mode == "advanced":
            self.mode_advanced_radio.setChecked(True)
        else:
            self.mode_custom_radio.setChecked(True)

        self.apply_config_to_ui()
        self.update_status_bar()

        # Update executor with new config
        if self.executor:
            self.executor.config = self.config

        self.log_widget.append_log("INFO", "Configuration loaded")
        QMessageBox.information(self, "Configuration Loaded", "Configuration has been loaded successfully.")

    def reset_configuration(self):
        """Reset configuration to defaults"""
        reply = QMessageBox.question(
            self,
            "Reset Configuration",
            "Are you sure you want to reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.config = PipelineConfig()  # Create new default config
            self.load_configuration()  # Apply to UI
            self.log_widget.append_log("INFO", "Configuration reset to defaults")

    # =========================================================================
    # Signal Handlers
    # =========================================================================

    def on_batch_started(self, total_files: int):
        """Handle batch started signal"""
        self.log_widget.append_log("INFO", f"Batch conversion started: {total_files} files")

        # Reset progress
        self.main_progress.setValue(0)

        # Update progress card
        self.progress_card.update_stat("Current", f"0/{total_files}")
        self.progress_card.update_stat("Step", "0/0")
        self.progress_card.update_stat("Time", "00:00 / --:--")

        # Reset results card
        self.results_card.update_stat("Pass", "0")
        self.results_card.update_stat("Fail", "0")
        self.results_card.update_stat("Avg Accuracy", "0%")

    def on_file_started(self, filename: str, index: int, total: int):
        """Handle file started signal"""
        # Extract just the filename from the path
        file_basename = Path(filename).name

        self.current_file_label.setText(f"Processing: {file_basename} ({index + 1}/{total})")
        self.log_widget.append_log("INFO", f"Started: {file_basename}")

        # Update progress card
        self.progress_card.update_stat("Current", f"{index + 1}/{total}")

    def on_step_started(self, step_name: str, step_num: int, total_steps: int):
        """Handle step started signal"""
        self.current_step_label.setText(f"Step {step_num}/{total_steps}: {step_name}")
        self.log_widget.append_log("DEBUG", f"Step {step_num}: {step_name}")

        # Update progress card
        self.progress_card.update_stat("Step", f"{step_num}/{total_steps}")

    def on_step_completed(self, step_name: str, success: bool, message: str):
        """Handle step completed signal"""
        status = "✅ OK" if success else "❌ FAIL"
        self.log_widget.append_log("INFO" if success else "ERROR", f"{step_name}: {status} - {message}")

    def on_file_completed(self, filename: str, results: Dict):
        """Handle file completed signal"""
        file_basename = Path(filename).name
        status = results.get("status", "unknown")
        accuracy = results.get("accuracy", 0.0)

        self.log_widget.append_log("INFO", f"Completed: {file_basename} - {status.upper()} ({accuracy:.2f}%)")

        # Update results table
        self._add_result_row(filename, results)

        # Update results card statistics
        self._update_results_stats()

    def on_batch_completed(self, summary: Dict):
        """Handle batch completed signal"""
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)

        # Log summary
        total = summary.get("total_files", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        avg_accuracy = summary.get("avg_accuracy", 0.0)
        duration = summary.get("duration", 0.0)

        self.log_widget.append_log("INFO", "=" * 60)
        self.log_widget.append_log("INFO", "BATCH CONVERSION COMPLETED")
        self.log_widget.append_log("INFO", f"Total: {total} | Passed: {passed} | Failed: {failed}")
        self.log_widget.append_log("INFO", f"Average Accuracy: {avg_accuracy:.2f}%")
        self.log_widget.append_log("INFO", f"Duration: {duration:.1f} seconds")
        self.log_widget.append_log("INFO", "=" * 60)

        # Update current operation display
        self.current_file_label.setText(f"Batch complete: {passed}/{total} files successful")
        self.current_step_label.setText(f"Finished in {duration:.1f} seconds")

        # Show completion message
        QMessageBox.information(
            self,
            "Conversion Complete",
            f"Batch conversion completed!\n\n"
            f"Total: {total} files\n"
            f"Passed: {passed} ({passed/total*100:.1f}%)\n"
            f"Failed: {failed}\n"
            f"Average Accuracy: {avg_accuracy:.2f}%"
        )

    def on_progress_updated(self, percentage: int):
        """Handle progress updated signal"""
        self.main_progress.setValue(percentage)

    def on_log_message(self, level: str, message: str):
        """Handle log message signal"""
        self.log_widget.append_log(level, message)

    def on_error_occurred(self, filename: str, error_message: str):
        """Handle error occurred signal"""
        self.log_widget.append_log("ERROR", f"{filename}: {error_message}")

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _add_result_row(self, filename: str, results: Dict):
        """Add a row to the results table"""
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)

        # File name
        file_item = QTableWidgetItem(Path(filename).name)
        self.results_table.setItem(row, 0, file_item)

        # Driver
        driver_item = QTableWidgetItem(results.get("driver", "unknown"))
        self.results_table.setItem(row, 1, driver_item)

        # Steps
        steps_completed = results.get("steps_completed", 0)
        total_steps = results.get("total_steps", 0)
        steps_item = QTableWidgetItem(f"{steps_completed}/{total_steps}")
        self.results_table.setItem(row, 2, steps_item)

        # Accuracy
        accuracy = results.get("accuracy", 0.0)
        accuracy_item = QTableWidgetItem(f"{accuracy:.2f}%")
        self.results_table.setItem(row, 3, accuracy_item)

        # Status
        status = results.get("status", "unknown")
        status_item = QTableWidgetItem(status.upper())

        # Color-code status
        if status == "passed":
            status_item.setForeground(QColor("#4CAF50"))  # Green
        elif status == "failed":
            status_item.setForeground(QColor("#f44336"))  # Red
        elif status == "warning":
            status_item.setForeground(QColor("#FF9800"))  # Orange

        self.results_table.setItem(row, 4, status_item)

        # Action button (View)
        view_btn = QPushButton("View")
        view_btn.clicked.connect(lambda: self._view_result_details(filename, results))
        self.results_table.setCellWidget(row, 5, view_btn)

    def _update_results_stats(self):
        """Update the results card statistics"""
        total = self.results_table.rowCount()
        passed = 0
        failed = 0
        accuracies = []

        for row in range(total):
            status_item = self.results_table.item(row, 4)
            if status_item:
                status = status_item.text().lower()
                if status == "passed":
                    passed += 1
                elif status == "failed":
                    failed += 1

            accuracy_item = self.results_table.item(row, 3)
            if accuracy_item:
                try:
                    acc = float(accuracy_item.text().rstrip('%'))
                    accuracies.append(acc)
                except:
                    pass

        # Calculate average accuracy
        avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.0

        # Update results card
        self.results_card.update_stat("Pass", str(passed))
        self.results_card.update_stat("Fail", str(failed))
        self.results_card.update_stat("Avg Accuracy", f"{avg_accuracy:.1f}%")

    def _view_result_details(self, filename: str, results: Dict):
        """View detailed results for a file"""
        # TODO: Show a dialog with detailed file information
        details = f"File: {Path(filename).name}\n\n"
        details += f"Status: {results.get('status', 'unknown').upper()}\n"
        details += f"Driver: {results.get('driver', 'unknown')}\n"
        details += f"Steps: {results.get('steps_completed')}/{results.get('total_steps')}\n"
        details += f"Accuracy: {results.get('accuracy', 0.0):.2f}%\n"
        details += f"Duration: {results.get('duration', 0.0):.2f}s\n"

        if results.get('error_message'):
            details += f"\nError: {results.get('error_message')}\n"

        output_files = results.get('output_files', [])
        if output_files:
            details += f"\nOutput Files ({len(output_files)}):\n"
            for f in output_files[:10]:  # Show first 10
                details += f"  - {Path(f).name}\n"
            if len(output_files) > 10:
                details += f"  ... and {len(output_files) - 10} more\n"

        QMessageBox.information(self, "File Details", details)

    def clear_logs(self):
        """Clear the log display"""
        self.log_widget.clear()

    def update_status_bar(self):
        """Update the status bar"""
        mode = "Simple" if self.config.mode == "simple" else "Advanced"
        output_dir = self.config.output_directory or "Not set"
        self.status_bar.showMessage(f"Ready | Output: {output_dir} | Mode: {mode}")

    # === Batch History Methods ===

    def on_save_batch_to_history(self):
        """Save current batch configuration to history"""
        if not self.selected_files:
            QMessageBox.warning(self, "No Files", "Please select files before saving batch history")
            return

        try:
            # Generate label
            mode = self.config.mode.capitalize()
            driver = self.config.primary_driver.capitalize()
            from datetime import datetime
            date_str = datetime.now().strftime('%m/%d')
            label = f"{driver} {mode} - {date_str}"

            # Save to history
            self.history_manager.save_batch(
                self.config,
                file_count=len(self.selected_files),
                label=label
            )

            # Refresh history display
            if hasattr(self, 'history_section'):
                self.history_section.refresh_history()

            QMessageBox.information(
                self,
                "Batch Saved",
                f"Batch configuration saved to history.\n"
                f"Files: {len(self.selected_files)}\n"
                f"Driver: {driver}\n"
                f"Mode: {mode}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save batch: {e}")

    def on_history_load(self, entry_id: str):
        """Load batch configuration from history"""
        try:
            config = self.history_manager.restore_config(entry_id)
            if not config:
                QMessageBox.warning(self, "Error", "Could not restore batch configuration")
                return

            # Apply loaded configuration
            self.config = config

            # Update UI to reflect new config
            self.mode_simple_radio.setChecked(config.mode == "simple")
            self.mode_advanced_radio.setChecked(config.mode == "advanced")
            self.mode_custom_radio.setChecked(config.mode == "custom")

            self.driver_combo.setCurrentText(config.primary_driver)
            self.generate_both_cb.setChecked(config.generate_both)
            self.output_dir_label.setText(config.output_directory)
            self.overwrite_cb.setChecked(config.overwrite_existing)
            self.create_nested_dirs_cb.setChecked(config.create_nested_dirs)
            self.stop_on_error_cb.setChecked(config.stop_on_error)
            self.concurrent_workers_spinbox.setValue(config.concurrent_workers)

            # Update step checkboxes via apply_config_to_ui
            self.apply_config_to_ui()

            QMessageBox.information(
                self,
                "Batch Loaded",
                f"Configuration restored from history.\n"
                f"Driver: {config.primary_driver}\n"
                f"Mode: {config.mode}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load batch: {e}")

    def load_settings(self):
        """Load saved settings from QSettings"""
        # TODO: Load window geometry, recent files, etc.
        pass

    def save_settings(self):
        """Save settings to QSettings"""
        # TODO: Save window geometry, recent files, etc.
        pass

    def closeEvent(self, event):
        """Handle window close event"""
        self.save_settings()
        event.accept()


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("SIDM2 Conversion Cockpit")
    app.setOrganizationName("SIDM2")

    window = CockpitMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
