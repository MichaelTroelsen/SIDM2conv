#!/usr/bin/env python3
"""Tests for configuration system"""

import unittest
import os
import tempfile
import json
from pathlib import Path

from sidm2.config import (
    ConversionConfig, DriverConfig, OutputConfig,
    ExtractionConfig, LoggingConfig,
    get_default_config, create_example_config
)


class TestDriverConfig(unittest.TestCase):
    """Tests for DriverConfig"""

    def test_default_values(self):
        """Test default driver configuration"""
        config = DriverConfig()
        self.assertEqual(config.default_driver, 'driver11')
        self.assertFalse(config.generate_both)
        self.assertIn('driver11', config.available_drivers)
        self.assertIn('np20', config.available_drivers)

    def test_validation_valid(self):
        """Test validation passes for valid config"""
        config = DriverConfig(default_driver='driver11')
        config.validate()  # Should not raise

    def test_validation_invalid_driver(self):
        """Test validation fails for invalid driver"""
        config = DriverConfig(default_driver='invalid')
        with self.assertRaises(ValueError) as cm:
            config.validate()
        self.assertIn('Invalid default driver', str(cm.exception))


class TestOutputConfig(unittest.TestCase):
    """Tests for OutputConfig"""

    def test_default_values(self):
        """Test default output configuration"""
        config = OutputConfig()
        self.assertIsNone(config.output_dir)
        self.assertEqual(config.naming_pattern, '{name}_d11.sf2')
        self.assertFalse(config.overwrite)
        self.assertTrue(config.create_dirs)


class TestExtractionConfig(unittest.TestCase):
    """Tests for ExtractionConfig"""

    def test_default_values(self):
        """Test default extraction configuration"""
        config = ExtractionConfig()
        self.assertFalse(config.verbose)
        self.assertEqual(config.validation_level, 'normal')
        self.assertTrue(config.use_siddump)
        self.assertEqual(config.siddump_duration, 60)
        self.assertEqual(config.max_sequence_length, 256)
        self.assertEqual(config.max_instruments, 32)

    def test_validation_valid(self):
        """Test validation passes for valid config"""
        config = ExtractionConfig(validation_level='strict')
        config.validate()  # Should not raise

    def test_validation_invalid_level(self):
        """Test validation fails for invalid level"""
        config = ExtractionConfig(validation_level='invalid')
        with self.assertRaises(ValueError) as cm:
            config.validate()
        self.assertIn('Invalid validation level', str(cm.exception))

    def test_validation_invalid_duration(self):
        """Test validation fails for invalid siddump duration"""
        config = ExtractionConfig(siddump_duration=0)
        with self.assertRaises(ValueError) as cm:
            config.validate()
        self.assertIn('duration must be', str(cm.exception))


class TestLoggingConfig(unittest.TestCase):
    """Tests for LoggingConfig"""

    def test_default_values(self):
        """Test default logging configuration"""
        config = LoggingConfig()
        self.assertEqual(config.level, 'INFO')
        self.assertIsNone(config.log_file)
        self.assertIn('levelname', config.log_format)

    def test_validation_valid(self):
        """Test validation passes for valid config"""
        config = LoggingConfig(level='DEBUG')
        config.validate()  # Should not raise

    def test_validation_invalid_level(self):
        """Test validation fails for invalid log level"""
        config = LoggingConfig(level='INVALID')
        with self.assertRaises(ValueError) as cm:
            config.validate()
        self.assertIn('Invalid log level', str(cm.exception))


class TestConversionConfig(unittest.TestCase):
    """Tests for ConversionConfig"""

    def test_default_config(self):
        """Test creating default configuration"""
        config = ConversionConfig()
        self.assertIsInstance(config.driver, DriverConfig)
        self.assertIsInstance(config.output, OutputConfig)
        self.assertIsInstance(config.extraction, ExtractionConfig)
        self.assertIsInstance(config.logging, LoggingConfig)

    def test_validate(self):
        """Test validation of complete configuration"""
        config = ConversionConfig()
        config.validate()  # Should not raise

    def test_to_dict(self):
        """Test conversion to dictionary"""
        config = ConversionConfig()
        data = config.to_dict()

        self.assertIn('driver', data)
        self.assertIn('output', data)
        self.assertIn('extraction', data)
        self.assertIn('logging', data)

        self.assertEqual(data['driver']['default_driver'], 'driver11')
        self.assertEqual(data['logging']['level'], 'INFO')

    def test_from_dict(self):
        """Test creation from dictionary"""
        data = {
            'driver': {
                'default_driver': 'np20',
                'generate_both': True,
                'available_drivers': ['driver11', 'np20']
            },
            'extraction': {
                'verbose': True,
                'validation_level': 'strict',
                'use_siddump': False,
                'siddump_duration': 30,
                'max_sequence_length': 512,
                'max_instruments': 64,
                'max_wave_entries': 256,
                'max_pulse_entries': 128,
                'max_filter_entries': 128,
            },
            'logging': {
                'level': 'DEBUG',
                'log_file': 'debug.log',
                'log_format': '%(message)s'
            }
        }

        config = ConversionConfig.from_dict(data)

        self.assertEqual(config.driver.default_driver, 'np20')
        self.assertTrue(config.driver.generate_both)
        self.assertTrue(config.extraction.verbose)
        self.assertEqual(config.extraction.validation_level, 'strict')
        self.assertEqual(config.logging.level, 'DEBUG')

    def test_save_and_load(self):
        """Test saving and loading configuration"""
        # Create config with custom values
        config = ConversionConfig()
        config.driver.default_driver = 'np20'
        config.extraction.verbose = True
        config.logging.level = 'DEBUG'

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            config.save(temp_path)

            # Verify file exists and contains JSON
            self.assertTrue(os.path.exists(temp_path))

            with open(temp_path, 'r') as f:
                data = json.load(f)
                self.assertEqual(data['driver']['default_driver'], 'np20')

            # Load configuration
            loaded_config = ConversionConfig.load(temp_path)

            self.assertEqual(loaded_config.driver.default_driver, 'np20')
            self.assertTrue(loaded_config.extraction.verbose)
            self.assertEqual(loaded_config.logging.level, 'DEBUG')

        finally:
            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file returns defaults"""
        config = ConversionConfig.load('nonexistent_config.json')

        # Should return default config without raising
        self.assertEqual(config.driver.default_driver, 'driver11')
        self.assertEqual(config.logging.level, 'INFO')


class TestConfigUtilities(unittest.TestCase):
    """Tests for configuration utility functions"""

    def test_get_default_config(self):
        """Test getting default configuration"""
        config = get_default_config()

        self.assertIsInstance(config, ConversionConfig)
        self.assertEqual(config.driver.default_driver, 'driver11')

    def test_create_example_config(self):
        """Test creating example configuration file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name

        try:
            create_example_config(temp_path)

            self.assertTrue(os.path.exists(temp_path))

            # Verify it's valid JSON with correct structure
            with open(temp_path, 'r') as f:
                data = json.load(f)

            self.assertIn('driver', data)
            self.assertIn('output', data)
            self.assertIn('extraction', data)
            self.assertIn('logging', data)

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
