"""
Logging configuration for SIDM2 package.
"""

import logging
import sys

# Create package logger
logger = logging.getLogger('sidm2')

def setup_logging(level: int = logging.INFO, log_file: str = None):
    """Configure logging for the SIDM2 package.

    Args:
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        log_file: Optional file path to write logs to
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(name)s - %(levelname)s - %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Configure root logger for sidm2
    logger.setLevel(level)
    logger.addHandler(console_handler)

    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f'sidm2.{name}')
