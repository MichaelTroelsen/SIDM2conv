"""
Enhanced logging configuration for SIDM2 package.

This module provides comprehensive logging with:
- Verbosity levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured logging (JSON format option)
- Color-coded console output
- File logging with rotation
- Performance/metrics logging
- Module-specific loggers

Example usage:
    from sidm2.logging_config import setup_logging, get_logger

    # Setup logging with verbosity
    setup_logging(verbosity=2)  # 0=ERROR, 1=WARNING, 2=INFO, 3=DEBUG

    # Get module logger
    logger = get_logger(__name__)
    logger.info("Processing file", extra={'file': 'test.sid', 'size': 1024})

Version: 2.0.0
"""

import logging
import logging.handlers
import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


# Verbosity level mapping
VERBOSITY_LEVELS = {
    0: logging.ERROR,      # Quiet - only errors
    1: logging.WARNING,    # Normal - warnings and errors
    2: logging.INFO,       # Verbose - info, warnings, errors
    3: logging.DEBUG,      # Debug - everything
}


# Color codes for terminal output
class Colors:
    """ANSI color codes for terminal output."""
    GREY = '\033[90m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD_RED = '\033[1;91m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

    # Level-specific colors
    LEVEL_COLORS = {
        'DEBUG': GREY,
        'INFO': CYAN,
        'WARNING': YELLOW,
        'ERROR': RED,
        'CRITICAL': BOLD_RED,
    }

    @staticmethod
    def is_enabled() -> bool:
        """Check if colors should be enabled."""
        # Enable if stdout is a terminal (not redirected)
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


class ColoredFormatter(logging.Formatter):
    """
    Formatter that adds color codes to log levels.

    Format: [TIMESTAMP] LEVEL - module:line - message
    """

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and Colors.is_enabled()

        # Format template
        self.fmt_template = "%(asctime)s [%(levelname)8s] %(name)s:%(lineno)d - %(message)s"
        self.datefmt = "%Y-%m-%d %H:%M:%S"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Create a copy to avoid modifying the original
        record_copy = logging.makeLogRecord(record.__dict__)

        if self.use_colors:
            # Colorize level name
            level_color = Colors.LEVEL_COLORS.get(record.levelname, '')
            record_copy.levelname = f"{level_color}{record.levelname}{Colors.RESET}"

            # Colorize module:line
            record_copy.name = f"{Colors.GREY}{record.name}{Colors.RESET}"

        # Use standard formatter
        formatter = logging.Formatter(self.fmt_template, datefmt=self.datefmt)
        return formatter.format(record_copy)


class StructuredFormatter(logging.Formatter):
    """
    Formatter that outputs JSON-structured logs.

    Format: {"timestamp": "...", "level": "...", "logger": "...", "message": "...", ...}
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'line': record.lineno,
            'function': record.funcName,
            'message': record.getMessage(),
        }

        # Add extra fields from record
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                              'levelname', 'levelno', 'lineno', 'module', 'msecs',
                              'message', 'pathname', 'process', 'processName',
                              'relativeCreated', 'thread', 'threadName', 'exc_info',
                              'exc_text', 'stack_info']:
                    log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)


class PerformanceLogger:
    """
    Context manager for performance logging.

    Example:
        with PerformanceLogger(logger, "SID conversion"):
            convert_sid_to_sf2(input_file, output_file)
    """

    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.start_time = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        self.logger.log(self.level, f"Starting: {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """End timing and log duration."""
        duration = time.time() - self.start_time

        if exc_type is None:
            self.logger.log(
                self.level,
                f"Completed: {self.operation}",
                extra={'duration_seconds': duration, 'status': 'success'}
            )
        else:
            self.logger.error(
                f"Failed: {self.operation}\n"
                f"  Suggestion: Operation failed during execution\n"
                f"  Check: Review exception details for specific cause\n"
                f"  Try: Enable debug logging for more information\n"
                f"  See: docs/guides/TROUBLESHOOTING.md#operation-failures",
                extra={'duration_seconds': duration, 'status': 'failed', 'exception': str(exc_val)}
            )

        return False  # Don't suppress exceptions


# Global logger registry
_loggers: Dict[str, logging.Logger] = {}
_logging_config: Dict[str, Any] = {
    'verbosity': 2,  # Default to INFO
    'log_file': None,
    'structured': False,
    'use_colors': True,
    'max_file_size': 10 * 1024 * 1024,  # 10 MB
    'backup_count': 3,
}


def setup_logging(
    verbosity: int = 2,
    log_file: Optional[str] = None,
    structured: bool = False,
    use_colors: bool = True,
    max_file_size: int = 10 * 1024 * 1024,
    backup_count: int = 3,
    quiet: bool = False,
    debug: bool = False
) -> logging.Logger:
    """
    Configure logging for the SIDM2 package.

    Args:
        verbosity: Logging verbosity level
            0 = ERROR only (quiet mode)
            1 = WARNING + ERROR
            2 = INFO + WARNING + ERROR (default)
            3 = DEBUG + INFO + WARNING + ERROR (debug mode)
        log_file: Optional file path to write logs to
        structured: If True, use JSON-structured logging (overrides colors)
        use_colors: If True, use colored console output (ignored if structured=True)
        max_file_size: Maximum log file size before rotation (bytes)
        backup_count: Number of rotated log files to keep
        quiet: If True, set verbosity to 0 (ERROR only)
        debug: If True, set verbosity to 3 (DEBUG)

    Returns:
        Main logger instance for 'sidm2' package

    Example:
        # Normal mode (INFO level)
        setup_logging(verbosity=2)

        # Debug mode (DEBUG level)
        setup_logging(debug=True)

        # Quiet mode (ERROR only)
        setup_logging(quiet=True)

        # With file logging and rotation
        setup_logging(verbosity=2, log_file='logs/sidm2.log', max_file_size=5*1024*1024)

        # Structured JSON logging
        setup_logging(verbosity=2, structured=True, log_file='logs/sidm2.jsonl')
    """
    # Handle convenience flags
    if quiet:
        verbosity = 0
    elif debug:
        verbosity = 3

    # Clamp verbosity to valid range
    verbosity = max(0, min(3, verbosity))
    level = VERBOSITY_LEVELS[verbosity]

    # Update global config
    _logging_config.update({
        'verbosity': verbosity,
        'log_file': log_file,
        'structured': structured,
        'use_colors': use_colors and not structured,
        'max_file_size': max_file_size,
        'backup_count': backup_count,
    })

    # Get or create root logger for sidm2
    logger = logging.getLogger('sidm2')
    logger.setLevel(logging.DEBUG)  # Always capture all levels, handlers will filter

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if structured:
        console_formatter = StructuredFormatter()
    else:
        console_formatter = ColoredFormatter(use_colors=use_colors)

    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler with rotation if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        if max_file_size > 0:
            # Rotating file handler
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count
            )
        else:
            # Regular file handler (no rotation)
            file_handler = logging.FileHandler(log_file)

        file_handler.setLevel(level)

        if structured:
            file_formatter = StructuredFormatter()
        else:
            # File logs never use colors
            file_formatter = ColoredFormatter(use_colors=False)

        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    # Log initial message
    logger.debug(
        f"Logging initialized",
        extra={
            'verbosity': verbosity,
            'level': logging.getLevelName(level),
            'structured': structured,
            'log_file': log_file or 'console only'
        }
    )

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get or create a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance configured for the module

    Example:
        logger = get_logger(__name__)
        logger.info("Processing started")
        logger.debug("Debug details", extra={'variable': value})
    """
    # Ensure name is under 'sidm2' namespace
    if not name.startswith('sidm2'):
        name = f'sidm2.{name}'

    if name not in _loggers:
        _loggers[name] = logging.getLogger(name)

    return _loggers[name]


def log_performance(operation: str, level: int = logging.INFO):
    """
    Decorator for performance logging.

    Args:
        operation: Description of the operation
        level: Logging level to use

    Example:
        @log_performance("SID file parsing")
        def parse_sid_file(path: str):
            # ... parsing code ...
            return sid_data
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            with PerformanceLogger(logger, operation, level):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def get_verbosity() -> int:
    """Get current verbosity level (0-3)."""
    return _logging_config['verbosity']


def set_verbosity(verbosity: int):
    """
    Change verbosity level dynamically.

    Args:
        verbosity: New verbosity level (0-3)
    """
    verbosity = max(0, min(3, verbosity))
    level = VERBOSITY_LEVELS[verbosity]

    _logging_config['verbosity'] = verbosity

    # Update all handlers
    logger = logging.getLogger('sidm2')
    for handler in logger.handlers:
        handler.setLevel(level)


def add_file_handler(
    log_file: str,
    level: Optional[int] = None,
    structured: bool = False,
    max_file_size: int = 10 * 1024 * 1024,
    backup_count: int = 3
):
    """
    Add an additional file handler to existing logger.

    Args:
        log_file: Path to log file
        level: Optional logging level (defaults to current verbosity)
        structured: If True, use JSON format
        max_file_size: Maximum file size before rotation
        backup_count: Number of backup files to keep

    Example:
        # Add error-only log file
        add_file_handler('logs/errors.log', level=logging.ERROR)

        # Add JSON debug log
        add_file_handler('logs/debug.jsonl', level=logging.DEBUG, structured=True)
    """
    if level is None:
        level = VERBOSITY_LEVELS[_logging_config['verbosity']]

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    if max_file_size > 0:
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count
        )
    else:
        handler = logging.FileHandler(log_file)

    handler.setLevel(level)

    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = ColoredFormatter(use_colors=False)

    handler.setFormatter(formatter)

    logger = logging.getLogger('sidm2')
    logger.addHandler(handler)


# Convenience function for CLI usage
def configure_from_args(args):
    """
    Configure logging from argparse arguments.

    Expected args attributes:
        - verbose: int (verbosity level 0-3)
        - quiet: bool
        - debug: bool
        - log_file: str (optional)
        - log_json: bool (optional)

    Example:
        parser = argparse.ArgumentParser()
        parser.add_argument('-v', '--verbose', action='count', default=2)
        parser.add_argument('-q', '--quiet', action='store_true')
        parser.add_argument('--debug', action='store_true')
        parser.add_argument('--log-file', type=str)
        parser.add_argument('--log-json', action='store_true')
        args = parser.parse_args()

        from sidm2.logging_config import configure_from_args
        configure_from_args(args)
    """
    verbosity = getattr(args, 'verbose', 2)
    quiet = getattr(args, 'quiet', False)
    debug = getattr(args, 'debug', False)
    log_file = getattr(args, 'log_file', None)
    structured = getattr(args, 'log_json', False)

    return setup_logging(
        verbosity=verbosity,
        quiet=quiet,
        debug=debug,
        log_file=log_file,
        structured=structured
    )
