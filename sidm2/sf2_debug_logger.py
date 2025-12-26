#!/usr/bin/env python3
"""
SF2 Debug Logger - Ultra-verbose logging for SF2 operations

Provides comprehensive logging for:
- SF2 Viewer GUI events (keypresses, mouse, actions)
- SF2 file operations (load, save, pack)
- Playback operations (start, stop, position)
- Music state tracking (playing, paused, stopped)
- Structure validation and debugging

Supports multiple output modes:
- Console (color-coded)
- File (rotating logs)
- JSON (structured data)
- Real-time streaming
"""

import logging
import sys
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SF2LogLevel(Enum):
    """SF2-specific log levels for ultra-verbose debugging"""
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    TRACE = 5      # Ultra-detailed function calls
    ULTRAVERBOSE = 1  # Every single operation


class SF2EventType(Enum):
    """Types of SF2 events to log"""
    # GUI Events
    KEYPRESS = "keypress"
    MOUSE_CLICK = "mouse_click"
    MOUSE_MOVE = "mouse_move"
    TAB_CHANGE = "tab_change"
    MENU_ACTION = "menu_action"
    BUTTON_CLICK = "button_click"

    # File Operations
    FILE_LOAD_START = "file_load_start"
    FILE_LOAD_COMPLETE = "file_load_complete"
    FILE_LOAD_ERROR = "file_load_error"
    FILE_SAVE_START = "file_save_start"
    FILE_SAVE_COMPLETE = "file_save_complete"
    FILE_SAVE_ERROR = "file_save_error"
    FILE_PACK_START = "file_pack_start"
    FILE_PACK_COMPLETE = "file_pack_complete"

    # Playback Events
    PLAYBACK_START = "playback_start"
    PLAYBACK_STOP = "playback_stop"
    PLAYBACK_PAUSE = "playback_pause"
    PLAYBACK_RESUME = "playback_resume"
    PLAYBACK_POSITION = "playback_position"
    PLAYBACK_ERROR = "playback_error"
    MUSIC_PLAYING = "music_playing"
    MUSIC_STOPPED = "music_stopped"

    # SF2 Editor Events (for automation)
    EDITOR_LAUNCH = "editor_launch"
    EDITOR_LOAD_START = "editor_load_start"
    EDITOR_LOAD_COMPLETE = "editor_load_complete"
    EDITOR_LOAD_ERROR = "editor_load_error"
    EDITOR_PLAYBACK_START = "editor_playback_start"
    EDITOR_PLAYBACK_STOP = "editor_playback_stop"
    EDITOR_PACK_START = "editor_pack_start"
    EDITOR_PACK_COMPLETE = "editor_pack_complete"
    EDITOR_PACK_ERROR = "editor_pack_error"
    EDITOR_EXIT = "editor_exit"
    EDITOR_ERROR = "editor_error"

    # Structure Events
    BLOCK_PARSE = "block_parse"
    TABLE_PARSE = "table_parse"
    VALIDATION_START = "validation_start"
    VALIDATION_COMPLETE = "validation_complete"

    # General Events
    STATE_CHANGE = "state_change"
    ACTION = "action"
    ERROR = "error"


class SF2DebugLogger:
    """Comprehensive debug logger for SF2 operations"""

    def __init__(
        self,
        name: str = "SF2Debug",
        level: int = logging.DEBUG,
        log_file: Optional[str] = None,
        json_log: bool = False,
        console_output: bool = True,
        ultraverbose: bool = False
    ):
        """Initialize SF2 debug logger

        Args:
            name: Logger name
            level: Base logging level
            log_file: Optional file path for log output
            json_log: Enable JSON-formatted logging
            console_output: Enable console output
            ultraverbose: Enable ultra-verbose mode (logs everything)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(SF2LogLevel.ULTRAVERBOSE.value if ultraverbose else level)
        self.logger.handlers.clear()  # Remove existing handlers

        self.json_log = json_log
        self.ultraverbose = ultraverbose
        self.event_count = 0
        self.start_time = time.time()
        self.event_history: List[Dict[str, Any]] = []

        # Console handler with color coding
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)

            if ultraverbose:
                console_formatter = logging.Formatter(
                    '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s::%(funcName)s:%(lineno)d - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
            else:
                console_formatter = logging.Formatter(
                    '%(asctime)s [%(levelname)s] %(name)s - %(message)s',
                    datefmt='%H:%M:%S'
                )

            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        # File handler
        if log_file:
            file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)

            file_formatter = logging.Formatter(
                '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s::%(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

        # JSON handler
        if json_log:
            json_file = log_file.replace('.log', '.json') if log_file else 'sf2_debug.json'
            self.json_handler = open(json_file, 'a', encoding='utf-8')
        else:
            self.json_handler = None

        self.log_event(SF2EventType.STATE_CHANGE, {
            'message': 'SF2 Debug Logger initialized',
            'ultraverbose': ultraverbose,
            'level': logging.getLevelName(level)
        })

    def log_event(
        self,
        event_type: SF2EventType,
        data: Dict[str, Any],
        level: int = logging.DEBUG
    ):
        """Log an SF2 event with structured data

        Args:
            event_type: Type of event
            data: Event data dictionary
            level: Logging level
        """
        self.event_count += 1
        timestamp = time.time()
        elapsed = timestamp - self.start_time

        event = {
            'event_id': self.event_count,
            'timestamp': datetime.now().isoformat(),
            'elapsed_ms': int(elapsed * 1000),
            'event_type': event_type.value,
            'data': data
        }

        # Store in history (limit to last 1000 events)
        self.event_history.append(event)
        if len(self.event_history) > 1000:
            self.event_history.pop(0)

        # Format message
        message = f"[{event_type.value}] {data.get('message', '')}"
        if self.ultraverbose and 'details' in data:
            message += f" | Details: {data['details']}"

        # Log to standard logger
        self.logger.log(level, message)

        # Log to JSON if enabled
        if self.json_handler:
            self.json_handler.write(json.dumps(event) + '\n')
            self.json_handler.flush()

    def log_keypress(self, key: str, modifiers: List[str] = None, widget: str = None):
        """Log a keypress event

        Args:
            key: Key that was pressed
            modifiers: List of modifier keys (Ctrl, Shift, Alt)
            widget: Widget that received the keypress
        """
        self.log_event(SF2EventType.KEYPRESS, {
            'message': f'Key pressed: {key}',
            'key': key,
            'modifiers': modifiers or [],
            'widget': widget or 'unknown'
        }, logging.DEBUG)

    def log_mouse_click(self, button: str, x: int, y: int, widget: str = None):
        """Log a mouse click event

        Args:
            button: Mouse button (left, right, middle)
            x: X coordinate
            y: Y coordinate
            widget: Widget that was clicked
        """
        self.log_event(SF2EventType.MOUSE_CLICK, {
            'message': f'Mouse click: {button} at ({x}, {y})',
            'button': button,
            'x': x,
            'y': y,
            'widget': widget or 'unknown'
        }, logging.DEBUG if not self.ultraverbose else logging.INFO)

    def log_file_load(self, filepath: str, stage: str = 'start', details: Dict = None):
        """Log file load operation

        Args:
            filepath: Path to file being loaded
            stage: Stage of loading (start, complete, error)
            details: Additional details (size, parse time, etc.)
        """
        event_types = {
            'start': SF2EventType.FILE_LOAD_START,
            'complete': SF2EventType.FILE_LOAD_COMPLETE,
            'error': SF2EventType.FILE_LOAD_ERROR
        }

        data = {
            'message': f'File load {stage}: {Path(filepath).name}',
            'filepath': filepath,
            'stage': stage
        }

        if details:
            data.update(details)

        level = logging.ERROR if stage == 'error' else logging.INFO
        self.log_event(event_types.get(stage, SF2EventType.ACTION), data, level)

    def log_playback(
        self,
        action: str,
        position_ms: Optional[int] = None,
        duration_ms: Optional[int] = None,
        details: Dict = None
    ):
        """Log playback operation

        Args:
            action: Playback action (start, stop, pause, resume, position)
            position_ms: Current position in milliseconds
            duration_ms: Total duration in milliseconds
            details: Additional details
        """
        event_types = {
            'start': SF2EventType.PLAYBACK_START,
            'stop': SF2EventType.PLAYBACK_STOP,
            'pause': SF2EventType.PLAYBACK_PAUSE,
            'resume': SF2EventType.PLAYBACK_RESUME,
            'position': SF2EventType.PLAYBACK_POSITION,
            'error': SF2EventType.PLAYBACK_ERROR
        }

        data = {'message': f'Playback {action}', 'action': action}

        if position_ms is not None:
            data['position_ms'] = position_ms
            data['position_s'] = position_ms / 1000

        if duration_ms is not None:
            data['duration_ms'] = duration_ms
            data['duration_s'] = duration_ms / 1000

            if position_ms is not None:
                data['progress_percent'] = (position_ms / duration_ms * 100) if duration_ms > 0 else 0

        if details:
            data.update(details)

        level = logging.ERROR if action == 'error' else logging.INFO
        self.log_event(event_types.get(action, SF2EventType.ACTION), data, level)

    def log_music_state(self, playing: bool, details: Dict = None):
        """Log music playing state

        Args:
            playing: Whether music is currently playing
            details: Additional state details
        """
        event_type = SF2EventType.MUSIC_PLAYING if playing else SF2EventType.MUSIC_STOPPED

        data = {
            'message': f'Music state: {"PLAYING" if playing else "STOPPED"}',
            'playing': playing
        }

        if details:
            data.update(details)

        self.log_event(event_type, data, logging.INFO)

    def log_action(self, action: str, details: Dict = None):
        """Log a general action

        Args:
            action: Action description
            details: Action details
        """
        data = {'message': action}
        if details:
            data.update(details)

        self.log_event(SF2EventType.ACTION, data, logging.INFO)

    def log_editor_launch(self, editor_path: str, sf2_file: Optional[str] = None, details: Dict = None):
        """Log SF2 editor launch

        Args:
            editor_path: Path to editor executable
            sf2_file: SF2 file being loaded (if any)
            details: Additional launch details
        """
        data = {
            'message': f'Launching SF2 Editor: {Path(editor_path).name}',
            'editor_path': editor_path,
            'sf2_file': sf2_file
        }
        if details:
            data.update(details)

        self.log_event(SF2EventType.EDITOR_LAUNCH, data, logging.INFO)

    def log_editor_load(self, stage: str, sf2_file: str, details: Dict = None):
        """Log editor file load operation

        Args:
            stage: Load stage (start, complete, error)
            sf2_file: SF2 file being loaded
            details: Additional load details
        """
        event_types = {
            'start': SF2EventType.EDITOR_LOAD_START,
            'complete': SF2EventType.EDITOR_LOAD_COMPLETE,
            'error': SF2EventType.EDITOR_LOAD_ERROR
        }

        data = {
            'message': f'Editor file load {stage}: {Path(sf2_file).name}',
            'sf2_file': sf2_file,
            'stage': stage
        }
        if details:
            data.update(details)

        level = logging.ERROR if stage == 'error' else logging.INFO
        self.log_event(event_types.get(stage, SF2EventType.ACTION), data, level)

    def log_editor_playback(self, action: str, details: Dict = None):
        """Log editor playback operation

        Args:
            action: Playback action (start, stop)
            details: Additional playback details
        """
        event_types = {
            'start': SF2EventType.EDITOR_PLAYBACK_START,
            'stop': SF2EventType.EDITOR_PLAYBACK_STOP
        }

        data = {'message': f'Editor playback {action}', 'action': action}
        if details:
            data.update(details)

        self.log_event(event_types.get(action, SF2EventType.ACTION), data, logging.INFO)

    def log_editor_pack(self, stage: str, output_path: Optional[str] = None, details: Dict = None):
        """Log editor SF2 packing operation

        Args:
            stage: Pack stage (start, complete, error)
            output_path: Output SID file path
            details: Additional packing details
        """
        event_types = {
            'start': SF2EventType.EDITOR_PACK_START,
            'complete': SF2EventType.EDITOR_PACK_COMPLETE,
            'error': SF2EventType.EDITOR_PACK_ERROR
        }

        data = {
            'message': f'Editor pack {stage}',
            'stage': stage,
            'output_path': output_path
        }
        if details:
            data.update(details)

        level = logging.ERROR if stage == 'error' else logging.INFO
        self.log_event(event_types.get(stage, SF2EventType.ACTION), data, level)

    def log_editor_exit(self, details: Dict = None):
        """Log editor exit

        Args:
            details: Additional exit details
        """
        data = {'message': 'SF2 Editor exited'}
        if details:
            data.update(details)

        self.log_event(SF2EventType.EDITOR_EXIT, data, logging.INFO)

    def log_editor_error(self, error: str, details: Dict = None):
        """Log editor error

        Args:
            error: Error message
            details: Additional error details
        """
        data = {'message': f'Editor error: {error}', 'error': error}
        if details:
            data.update(details)

        self.log_event(SF2EventType.EDITOR_ERROR, data, logging.ERROR)

    def log_block_parse(self, block_id: int, block_size: int, block_type: str, details: Dict = None):
        """Log SF2 block parsing

        Args:
            block_id: Block ID
            block_size: Block size in bytes
            block_type: Block type description
            details: Additional parsing details
        """
        data = {
            'message': f'Parsing block {block_id}: {block_type} ({block_size} bytes)',
            'block_id': block_id,
            'block_size': block_size,
            'block_type': block_type
        }

        if details:
            data.update(details)

        self.log_event(SF2EventType.BLOCK_PARSE, data, logging.DEBUG)

    def log_table_parse(self, table_name: str, rows: int, columns: int, details: Dict = None):
        """Log SF2 table parsing

        Args:
            table_name: Table name
            rows: Number of rows
            columns: Number of columns
            details: Additional parsing details
        """
        data = {
            'message': f'Parsing table {table_name}: {rows} rows × {columns} columns',
            'table_name': table_name,
            'rows': rows,
            'columns': columns
        }

        if details:
            data.update(details)

        self.log_event(SF2EventType.TABLE_PARSE, data, logging.DEBUG)

    def get_event_summary(self) -> Dict[str, Any]:
        """Get summary of logged events

        Returns:
            Summary dictionary with event counts and timing
        """
        event_type_counts = {}
        for event in self.event_history:
            event_type = event['event_type']
            event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1

        return {
            'total_events': self.event_count,
            'elapsed_seconds': time.time() - self.start_time,
            'events_per_second': self.event_count / (time.time() - self.start_time),
            'event_types': event_type_counts,
            'recent_events': self.event_history[-10:] if self.event_history else []
        }

    def dump_event_history(self, filepath: str):
        """Dump complete event history to JSON file

        Args:
            filepath: Output file path
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'summary': self.get_event_summary(),
                'events': self.event_history
            }, f, indent=2)

        self.log_action(f'Event history dumped to {filepath}', {
            'filepath': filepath,
            'event_count': len(self.event_history)
        })

    def __del__(self):
        """Cleanup on deletion"""
        if self.json_handler:
            self.json_handler.close()


# Global logger instance (can be configured at startup)
_global_logger: Optional[SF2DebugLogger] = None


def get_sf2_logger() -> SF2DebugLogger:
    """Get or create global SF2 debug logger

    Returns:
        Global SF2DebugLogger instance
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = SF2DebugLogger(
            name="SF2Debug",
            level=logging.INFO,
            ultraverbose=False
        )
    return _global_logger


def configure_sf2_logger(
    level: int = logging.DEBUG,
    log_file: Optional[str] = None,
    json_log: bool = False,
    ultraverbose: bool = False
) -> SF2DebugLogger:
    """Configure global SF2 debug logger

    Args:
        level: Logging level
        log_file: Optional log file path
        json_log: Enable JSON logging
        ultraverbose: Enable ultra-verbose mode

    Returns:
        Configured SF2DebugLogger instance
    """
    global _global_logger
    _global_logger = SF2DebugLogger(
        name="SF2Debug",
        level=level,
        log_file=log_file,
        json_log=json_log,
        ultraverbose=ultraverbose
    )
    return _global_logger


# Convenience logging functions
def log_keypress(key: str, modifiers: List[str] = None, widget: str = None):
    """Convenience function for logging keypresses"""
    get_sf2_logger().log_keypress(key, modifiers, widget)


def log_file_load(filepath: str, stage: str = 'start', details: Dict = None):
    """Convenience function for logging file loads"""
    get_sf2_logger().log_file_load(filepath, stage, details)


def log_playback(action: str, position_ms: Optional[int] = None, duration_ms: Optional[int] = None, details: Dict = None):
    """Convenience function for logging playback"""
    get_sf2_logger().log_playback(action, position_ms, duration_ms, details)


def log_music_state(playing: bool, details: Dict = None):
    """Convenience function for logging music state"""
    get_sf2_logger().log_music_state(playing, details)


def log_action(action: str, details: Dict = None):
    """Convenience function for logging actions"""
    get_sf2_logger().log_action(action, details)
