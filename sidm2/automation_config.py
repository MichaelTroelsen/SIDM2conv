"""
SF2 Editor Automation Configuration

Reads and provides access to automation configuration from config/sf2_automation.ini
Provides default values if config file is missing or incomplete.

Usage:
    from sidm2.automation_config import AutomationConfig

    config = AutomationConfig()
    if config.autoit_enabled:
        script = config.autoit_script_path
        timeout = config.autoit_timeout
"""

import configparser
from pathlib import Path
from typing import List, Optional
import logging


class AutomationConfig:
    """SF2 Editor Automation Configuration Manager"""

    # Default configuration file path
    DEFAULT_CONFIG_PATH = Path("config/sf2_automation.ini")

    # Default values (used if config file missing or incomplete)
    DEFAULTS = {
        'AutoIt': {
            'enabled': 'false',
            'script_path': 'scripts/autoit/sf2_loader.exe',
            'timeout': '60',
            'keep_alive_interval': '500'
        },
        'PyAutoGUI': {
            'enabled': 'true',
            'skip_intro': 'true',
            'window_timeout': '10',
            'failsafe': 'true'
        },
        'Editor': {
            'paths': '''bin/SIDFactoryII.exe
C:/Program Files/SIDFactoryII/SIDFactoryII.exe
C:/Program Files (x86)/SIDFactoryII/SIDFactoryII.exe''',
            'window_title': 'SID Factory II',
            'window_timeout': '10'
        },
        'Playback': {
            'play_key': '0x74',
            'stop_key': '0x75',
            'record_key': '0x76',
            'state_check_interval': '100',
            'state_check_timeout': '5000'
        },
        'Logging': {
            'enabled': 'true',
            'level': 'INFO',
            'log_file': 'logs/sf2_automation.log',
            'log_to_console': 'true',
            'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'Validation': {
            'file_load_timeout': '30',
            'playback_timeout': '5',
            'require_exact_match': 'false'
        },
        'Advanced': {
            'use_windows_api': 'true',
            'process_name': 'SIDFactoryII.exe',
            'max_retries': '3',
            'retry_delay': '500'
        }
    }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration

        Args:
            config_path: Path to config file (default: config/sf2_automation.ini)
        """
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        # Use RawConfigParser to avoid interpolation of % in format strings
        self.config = configparser.RawConfigParser()

        # Load defaults first
        self.config.read_dict(self.DEFAULTS)

        # Override with config file if it exists
        if self.config_path.exists():
            try:
                self.config.read(self.config_path)
            except Exception as e:
                logging.warning(f"Failed to read config file {self.config_path}: {e}")
                logging.warning("Using default configuration")

    # ========================================================================
    # AutoIt Configuration
    # ========================================================================

    @property
    def autoit_enabled(self) -> bool:
        """Whether AutoIt mode is enabled by default"""
        return self.config.getboolean('AutoIt', 'enabled')

    @property
    def autoit_script_path(self) -> Path:
        """Path to sf2_loader.exe (relative to project root)"""
        return Path(self.config.get('AutoIt', 'script_path'))

    @property
    def autoit_timeout(self) -> int:
        """Timeout for AutoIt file loading (seconds)"""
        return self.config.getint('AutoIt', 'timeout')

    @property
    def autoit_keep_alive_interval(self) -> int:
        """Keep-alive interval (milliseconds)"""
        return self.config.getint('AutoIt', 'keep_alive_interval')

    # ========================================================================
    # PyAutoGUI Configuration
    # ========================================================================

    @property
    def pyautogui_enabled(self) -> bool:
        """Whether PyAutoGUI mode is enabled by default"""
        return self.config.getboolean('PyAutoGUI', 'enabled', fallback=True)

    @property
    def pyautogui_skip_intro(self) -> bool:
        """Whether to use --skip-intro CLI flag"""
        return self.config.getboolean('PyAutoGUI', 'skip_intro', fallback=True)

    @property
    def pyautogui_window_timeout(self) -> int:
        """Timeout for window detection (seconds)"""
        return self.config.getint('PyAutoGUI', 'window_timeout', fallback=10)

    @property
    def pyautogui_failsafe(self) -> bool:
        """Whether to enable PyAutoGUI failsafe (move mouse to corner to abort)"""
        return self.config.getboolean('PyAutoGUI', 'failsafe', fallback=True)

    # ========================================================================
    # Editor Configuration
    # ========================================================================

    @property
    def editor_paths(self) -> List[str]:
        """List of editor paths to search (in order)"""
        paths_str = self.config.get('Editor', 'paths')
        # Split by newlines and strip whitespace
        return [p.strip() for p in paths_str.split('\n') if p.strip()]

    @property
    def editor_window_title(self) -> str:
        """Expected window title pattern"""
        return self.config.get('Editor', 'window_title')

    @property
    def editor_window_timeout(self) -> int:
        """Window detection timeout (seconds)"""
        return self.config.getint('Editor', 'window_timeout')

    def find_editor_path(self) -> Optional[Path]:
        """Find first existing editor path from configured list

        Returns:
            Path to editor executable, or None if not found
        """
        for path_str in self.editor_paths:
            path = Path(path_str)
            if path.exists():
                return path.resolve()
        return None

    # ========================================================================
    # Playback Configuration
    # ========================================================================

    @property
    def play_key(self) -> int:
        """Virtual key code for Play (F5)"""
        return int(self.config.get('Playback', 'play_key'), 0)

    @property
    def stop_key(self) -> int:
        """Virtual key code for Stop (F6)"""
        return int(self.config.get('Playback', 'stop_key'), 0)

    @property
    def record_key(self) -> int:
        """Virtual key code for Record (F7)"""
        return int(self.config.get('Playback', 'record_key'), 0)

    @property
    def state_check_interval(self) -> int:
        """State check interval (milliseconds)"""
        return self.config.getint('Playback', 'state_check_interval')

    @property
    def state_check_timeout(self) -> int:
        """State check timeout (milliseconds)"""
        return self.config.getint('Playback', 'state_check_timeout')

    # ========================================================================
    # Logging Configuration
    # ========================================================================

    @property
    def logging_enabled(self) -> bool:
        """Whether logging is enabled"""
        return self.config.getboolean('Logging', 'enabled')

    @property
    def logging_level(self) -> str:
        """Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"""
        return self.config.get('Logging', 'level')

    @property
    def logging_file(self) -> Optional[Path]:
        """Log file path (None if disabled)"""
        file_path = self.config.get('Logging', 'log_file').strip()
        return Path(file_path) if file_path else None

    @property
    def logging_to_console(self) -> bool:
        """Whether to log to console"""
        return self.config.getboolean('Logging', 'log_to_console')

    @property
    def logging_format(self) -> str:
        """Log message format"""
        return self.config.get('Logging', 'log_format')

    # ========================================================================
    # Validation Configuration
    # ========================================================================

    @property
    def file_load_timeout(self) -> int:
        """File load validation timeout (seconds)"""
        return self.config.getint('Validation', 'file_load_timeout')

    @property
    def playback_timeout(self) -> int:
        """Playback validation timeout (seconds)"""
        return self.config.getint('Validation', 'playback_timeout')

    @property
    def require_exact_match(self) -> bool:
        """Whether to require exact file name match in window title"""
        return self.config.getboolean('Validation', 'require_exact_match')

    # ========================================================================
    # Advanced Configuration
    # ========================================================================

    @property
    def use_windows_api(self) -> bool:
        """Whether to use Windows API for window management"""
        return self.config.getboolean('Advanced', 'use_windows_api')

    @property
    def process_name(self) -> str:
        """Process name for finding running instances"""
        return self.config.get('Advanced', 'process_name')

    @property
    def max_retries(self) -> int:
        """Maximum retries for window operations"""
        return self.config.getint('Advanced', 'max_retries')

    @property
    def retry_delay(self) -> int:
        """Retry delay (milliseconds)"""
        return self.config.getint('Advanced', 'retry_delay')

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_summary(self) -> dict:
        """Get configuration summary as dictionary

        Returns:
            Dictionary with configuration values
        """
        return {
            'AutoIt': {
                'enabled': self.autoit_enabled,
                'script_path': str(self.autoit_script_path),
                'script_exists': self.autoit_script_path.exists(),
                'timeout': self.autoit_timeout
            },
            'PyAutoGUI': {
                'enabled': self.pyautogui_enabled,
                'skip_intro': self.pyautogui_skip_intro,
                'window_timeout': self.pyautogui_window_timeout,
                'failsafe': self.pyautogui_failsafe
            },
            'Editor': {
                'paths_configured': len(self.editor_paths),
                'path_found': str(self.find_editor_path()) if self.find_editor_path() else None,
                'window_title': self.editor_window_title
            },
            'Logging': {
                'enabled': self.logging_enabled,
                'level': self.logging_level,
                'log_file': str(self.logging_file) if self.logging_file else None
            },
            'Config': {
                'file_path': str(self.config_path),
                'file_exists': self.config_path.exists()
            }
        }

    def print_summary(self):
        """Print configuration summary to console"""
        print()
        print("=" * 70)
        print("SF2 Editor Automation Configuration")
        print("=" * 70)
        print()

        summary = self.get_summary()

        print("AutoIt Configuration:")
        print(f"  Enabled: {summary['AutoIt']['enabled']}")
        print(f"  Script Path: {summary['AutoIt']['script_path']}")
        print(f"  Script Exists: {summary['AutoIt']['script_exists']}")
        print(f"  Timeout: {summary['AutoIt']['timeout']}s")
        print()

        print("Editor Configuration:")
        print(f"  Paths Configured: {summary['Editor']['paths_configured']}")
        print(f"  Path Found: {summary['Editor']['path_found']}")
        print(f"  Window Title: {summary['Editor']['window_title']}")
        print()

        print("Logging Configuration:")
        print(f"  Enabled: {summary['Logging']['enabled']}")
        print(f"  Level: {summary['Logging']['level']}")
        print(f"  Log File: {summary['Logging']['log_file']}")
        print()

        print("Config File:")
        print(f"  Path: {summary['Config']['file_path']}")
        print(f"  Exists: {summary['Config']['file_exists']}")
        print()
        print("=" * 70)
        print()


# Singleton instance for convenient access
_config_instance = None

def get_config(config_path: Optional[str] = None) -> AutomationConfig:
    """Get singleton configuration instance

    Args:
        config_path: Path to config file (default: config/sf2_automation.ini)

    Returns:
        AutomationConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = AutomationConfig(config_path)
    return _config_instance


if __name__ == '__main__':
    # Test configuration loading
    config = AutomationConfig()
    config.print_summary()
