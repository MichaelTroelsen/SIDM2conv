"""
Configuration system for SF2 conversion.

Provides a flexible configuration structure for customizing SID to SF2 conversion
with sensible defaults and validation.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path
import json


logger = logging.getLogger(__name__)


@dataclass
class DriverConfig:
    """Driver-specific configuration"""
    # Default driver to use
    default_driver: str = 'driver11'

    # Generate both driver versions
    generate_both: bool = False

    # Available driver types
    available_drivers: List[str] = field(default_factory=lambda: ['driver11', 'np20', 'laxity'])

    def validate(self):
        """Validate driver configuration"""
        if self.default_driver not in self.available_drivers:
            raise ValueError(f"Invalid default driver: {self.default_driver}. "
                           f"Must be one of {self.available_drivers}")


@dataclass
class OutputConfig:
    """Output file configuration"""
    # Output directory (None = same as input)
    output_dir: Optional[str] = None

    # File naming pattern: {name}_{driver}.sf2
    # Available placeholders: {name}, {driver}, {date}
    naming_pattern: str = '{name}_d11.sf2'

    # Overwrite existing files
    overwrite: bool = False

    # Create output directory if missing
    create_dirs: bool = True


@dataclass
class ExtractionConfig:
    """Data extraction configuration"""
    # Verbose extraction logging
    verbose: bool = False

    # Validation strictness: 'strict', 'normal', 'permissive'
    validation_level: str = 'normal'

    # Use siddump for register analysis
    use_siddump: bool = True

    # Siddump playback time (seconds)
    siddump_duration: int = 60

    # Maximum sequence length (events)
    max_sequence_length: int = 256

    # Maximum table sizes
    max_instruments: int = 32
    max_wave_entries: int = 128
    max_pulse_entries: int = 64
    max_filter_entries: int = 64

    def validate(self):
        """Validate extraction configuration"""
        if self.validation_level not in ['strict', 'normal', 'permissive']:
            raise ValueError(f"Invalid validation level: {self.validation_level}")

        if self.siddump_duration < 1 or self.siddump_duration > 300:
            raise ValueError(f"Siddump duration must be 1-300 seconds")


@dataclass
class LoggingConfig:
    """Logging configuration"""
    # Logging level: 'DEBUG', 'INFO', 'WARNING', 'ERROR'
    level: str = 'INFO'

    # Log file path (None = console only)
    log_file: Optional[str] = None

    # Log format
    log_format: str = '%(levelname)s: %(message)s'

    def validate(self):
        """Validate logging configuration"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.level not in valid_levels:
            raise ValueError(f"Invalid log level: {self.level}. Must be one of {valid_levels}")


@dataclass
class ConversionConfig:
    """Complete conversion configuration"""
    driver: DriverConfig = field(default_factory=DriverConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    def validate(self):
        """Validate all configuration sections"""
        self.driver.validate()
        self.extraction.validate()
        self.logging.validate()

    def to_dict(self) -> dict:
        """Convert configuration to dictionary"""
        return {
            'driver': {
                'default_driver': self.driver.default_driver,
                'generate_both': self.driver.generate_both,
                'available_drivers': self.driver.available_drivers,
            },
            'output': {
                'output_dir': self.output.output_dir,
                'naming_pattern': self.output.naming_pattern,
                'overwrite': self.output.overwrite,
                'create_dirs': self.output.create_dirs,
            },
            'extraction': {
                'verbose': self.extraction.verbose,
                'validation_level': self.extraction.validation_level,
                'use_siddump': self.extraction.use_siddump,
                'siddump_duration': self.extraction.siddump_duration,
                'max_sequence_length': self.extraction.max_sequence_length,
                'max_instruments': self.extraction.max_instruments,
                'max_wave_entries': self.extraction.max_wave_entries,
                'max_pulse_entries': self.extraction.max_pulse_entries,
                'max_filter_entries': self.extraction.max_filter_entries,
            },
            'logging': {
                'level': self.logging.level,
                'log_file': self.logging.log_file,
                'log_format': self.logging.log_format,
            }
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ConversionConfig':
        """Create configuration from dictionary"""
        config = cls()

        if 'driver' in data:
            config.driver = DriverConfig(**data['driver'])

        if 'output' in data:
            config.output = OutputConfig(**data['output'])

        if 'extraction' in data:
            config.extraction = ExtractionConfig(**data['extraction'])

        if 'logging' in data:
            config.logging = LoggingConfig(**data['logging'])

        config.validate()
        return config

    def save(self, path: str):
        """Save configuration to JSON file"""
        try:
            config_dict = self.to_dict()
            with open(path, 'w') as f:
                json.dump(config_dict, f, indent=2)
            logger.info(f"Configuration saved to {path}")
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise

    @classmethod
    def load(cls, path: str) -> 'ConversionConfig':
        """Load configuration from JSON file"""
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            config = cls.from_dict(data)
            logger.info(f"Configuration loaded from {path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Configuration file not found: {path}, using defaults")
            return cls()
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise


def get_default_config() -> ConversionConfig:
    """Get default configuration"""
    return ConversionConfig()


def create_example_config(path: str = 'sidm2_config.json'):
    """Create an example configuration file"""
    config = get_default_config()
    config.save(path)
    logger.info(f"Example configuration created at {path}")
