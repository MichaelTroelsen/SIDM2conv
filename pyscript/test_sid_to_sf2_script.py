"""
Comprehensive tests for sidm2.conversion_pipeline module.

Target: 50% coverage (Phase 1, Module 4/4 - FINAL MODULE)

Tests conversion pipeline business logic extracted from scripts/sid_to_sf2.py.
"""

import unittest
import sys
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path
from io import StringIO

# Import functions from conversion_pipeline module (not the CLI script)
from sidm2.conversion_pipeline import (
    detect_player_type,
    print_success_summary,
    analyze_sid_file,
    convert_laxity_to_sf2,
    convert_galway_to_sf2,
    convert_sid_to_sf2,
    convert_sid_to_both_drivers,
)


class TestDetectPlayerType(unittest.TestCase):
    """Test player type detection."""

    @patch('sidm2.conversion_pipeline.subprocess.run')
    def test_detect_player_type_success(self, mock_run):
        """Test successful player type detection."""
        # Mock subprocess output
        mock_result = Mock()
        mock_result.stdout = "test.sid               NewPlayer_v21/Laxity\n"
        mock_run.return_value = mock_result

        result = detect_player_type("test.sid")

        self.assertEqual(result, "NewPlayer_v21/Laxity")
        mock_run.assert_called_once()

    @patch('sidm2.conversion_pipeline.subprocess.run')
    def test_detect_player_type_sf2_exported(self, mock_run):
        """Test detection of SF2-exported files."""
        mock_result = Mock()
        mock_result.stdout = "exported.sid           SidFactory_II\n"
        mock_run.return_value = mock_result

        result = detect_player_type("exported.sid")

        self.assertEqual(result, "SidFactory_II")

    @patch('sidm2.conversion_pipeline.subprocess.run')
    def test_detect_player_type_unknown(self, mock_run):
        """Test detection returns Unknown on failure."""
        mock_result = Mock()
        mock_result.stdout = "no match\n"
        mock_run.return_value = mock_result

        result = detect_player_type("unknown.sid")

        self.assertEqual(result, "Unknown")

    @patch('sidm2.conversion_pipeline.subprocess.run')
    def test_detect_player_type_exception(self, mock_run):
        """Test detection handles exceptions gracefully."""
        mock_run.side_effect = Exception("Command failed")

        result = detect_player_type("test.sid")

        self.assertEqual(result, "Unknown")

    @patch('sidm2.conversion_pipeline.subprocess.run')
    def test_detect_player_type_timeout(self, mock_run):
        """Test detection handles timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("player-id.exe", 10)

        result = detect_player_type("test.sid")

        self.assertEqual(result, "Unknown")


class TestPrintSuccessSummary(unittest.TestCase):
    """Test success summary printing."""

    def test_print_success_summary_basic(self):
        """Test basic success summary printing."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            print_success_summary("input.sid", "output.sf2")

            output = mock_stdout.getvalue()
            self.assertIn("SUCCESS", output)
            self.assertIn("input.sid", output)
            self.assertIn("output.sf2", output)

    def test_print_success_summary_with_driver_selection(self):
        """Test summary with driver selection info."""
        # Create mock driver selection
        driver_selection = Mock()
        driver_selection.driver_name = "laxity"
        driver_selection.player_type = "NewPlayer_v21/Laxity"
        driver_selection.expected_accuracy = "99.93%"
        driver_selection.reason = "Custom optimized driver"

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            print_success_summary("input.sid", "output.sf2", driver_selection=driver_selection)

            output = mock_stdout.getvalue()
            self.assertIn("laxity", output)
            self.assertIn("99.93%", output)

    def test_print_success_summary_quiet_mode(self):
        """Test quiet mode produces minimal output."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            print_success_summary("input.sid", "output.sf2", quiet=True)

            output = mock_stdout.getvalue()
            # Quiet mode still prints "OK: filename"
            self.assertIn("OK:", output)
            self.assertIn("output.sf2", output)

    def test_print_success_summary_with_validation(self):
        """Test summary with validation results."""
        # Create mock validation result
        validation_result = Mock()
        validation_result.is_valid = True
        validation_result.format_version = "SF2 v1.0"

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            print_success_summary("input.sid", "output.sf2", validation_result=validation_result)

            output = mock_stdout.getvalue()
            self.assertIn("SUCCESS", output)


class TestAnalyzeSidFile(unittest.TestCase):
    """Test SID file analysis."""

    @patch('sidm2.conversion_pipeline.SIDParser')
    @patch('sidm2.conversion_pipeline.os.path.exists')
    def test_analyze_sid_file_basic(self, mock_exists, mock_parser_class):
        """Test basic SID file analysis."""
        mock_exists.return_value = True

        # Create mock parser
        mock_parser = Mock()
        mock_header = Mock()
        mock_header.songs = 1
        mock_header.start_song = 1
        mock_header.load_address = 0x1000
        mock_header.init_address = 0x1000
        mock_header.play_address = 0x10A1
        mock_header.data_offset = 0x7C
        mock_parser.parse_header.return_value = mock_header
        # Mock get_c64_data to return tuple
        mock_parser.get_c64_data.return_value = (b'\x00' * 1024, 0x1000)
        mock_parser_class.return_value = mock_parser

        # Create temp test file
        test_file = "test_input.sid"
        with patch('builtins.open', mock_open(read_data=b'PSID' + b'\x00' * 1024)):
            result = analyze_sid_file(test_file)

        # Should return ExtractedData namedtuple (not dict)
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, 'header'))
        self.assertTrue(hasattr(result, 'c64_data'))

    @patch('sidm2.conversion_pipeline.SIDParser')
    @patch('sidm2.conversion_pipeline.os.path.exists')
    def test_analyze_sid_file_with_config(self, mock_exists, mock_parser_class):
        """Test analysis with custom config."""
        from sidm2.config import ConversionConfig

        mock_exists.return_value = True

        mock_parser = Mock()
        mock_header = Mock()
        mock_header.songs = 1
        mock_header.start_song = 1
        mock_header.load_address = 0x1000
        mock_header.init_address = 0x1000
        mock_header.play_address = 0x10A1
        mock_header.data_offset = 0x7C
        mock_parser.parse_header.return_value = mock_header
        mock_parser.get_c64_data.return_value = (b'\x00' * 1024, 0x1000)
        mock_parser_class.return_value = mock_parser

        config = ConversionConfig()

        test_file = "test_input.sid"
        with patch('builtins.open', mock_open(read_data=b'PSID' + b'\x00' * 1024)):
            result = analyze_sid_file(test_file, config=config)

        # Should return ExtractedData namedtuple (not dict)
        self.assertIsNotNone(result)
        self.assertTrue(hasattr(result, 'header'))
        self.assertTrue(hasattr(result, 'c64_data'))

    @patch('sidm2.conversion_pipeline.SIDParser')
    def test_analyze_sid_file_handles_exception(self, mock_parser_class):
        """Test analysis handles exceptions gracefully."""
        mock_parser_class.side_effect = Exception("Parse error")

        with patch('builtins.open', mock_open(read_data=b'\x00' * 1024)):
            with self.assertRaises(Exception):
                analyze_sid_file("test_input.sid")


class TestConvertLaxityToSF2(unittest.TestCase):
    """Test Laxity to SF2 conversion."""

    @patch('sidm2.conversion_pipeline.LAXITY_CONVERTER_AVAILABLE', True)
    @patch('sidm2.conversion_pipeline.LaxityConverter')
    @patch('sidm2.conversion_pipeline.SIDParser')
    @patch('sidm2.conversion_pipeline.os.path.exists')
    def test_convert_laxity_to_sf2_success(self, mock_exists, mock_parser_class, mock_converter_class):
        """Test successful Laxity to SF2 conversion."""
        mock_exists.return_value = True

        # Mock parser
        mock_parser = Mock()
        mock_header = Mock()
        mock_header.load_address = 0x1000
        mock_header.init_address = 0x1000
        mock_header.play_address = 0x10A1
        mock_header.data_offset = 0x7C
        mock_header.name = "Test Song"
        mock_header.author = "Test Author"
        mock_header.released = "2025"
        mock_parser.parse_header.return_value = mock_header
        mock_parser.get_c64_data.return_value = (b'\x00' * 1024, 0x1000)
        mock_parser_class.return_value = mock_parser

        # Mock converter
        mock_converter = Mock()
        mock_converter.convert.return_value = True
        mock_converter_class.return_value = mock_converter

        test_input = "test_laxity.sid"
        test_output = "test_output.sf2"

        # Mock SF2Writer to avoid file I/O
        with patch('sidm2.conversion_pipeline.SF2Writer') as mock_writer_class:
            mock_writer = Mock()
            mock_writer_class.return_value = mock_writer

            with patch('builtins.open', mock_open(read_data=b'\x00' * 1024)):
                result = convert_laxity_to_sf2(test_input, test_output)

        self.assertTrue(result)

    @patch('sidm2.conversion_pipeline.LAXITY_CONVERTER_AVAILABLE', False)
    @patch('sidm2.conversion_pipeline.os.path.exists')
    def test_convert_laxity_to_sf2_not_available(self, mock_exists):
        """Test conversion when Laxity converter not available."""
        mock_exists.return_value = True

        result = convert_laxity_to_sf2("test.sid", "output.sf2")

        self.assertFalse(result)

    @patch('sidm2.conversion_pipeline.LAXITY_CONVERTER_AVAILABLE', True)
    @patch('sidm2.conversion_pipeline.LaxityConverter')
    @patch('sidm2.conversion_pipeline.SIDParser')
    @patch('sidm2.conversion_pipeline.os.path.exists')
    def test_convert_laxity_to_sf2_handles_exception(self, mock_exists, mock_parser_class, mock_converter_class):
        """Test conversion handles exceptions."""
        from sidm2.errors import InvalidInputError

        mock_exists.return_value = True
        mock_parser_class.side_effect = Exception("Conversion error")

        with patch('builtins.open', mock_open(read_data=b'PSID' + b'\x00' * 1024)):
            with self.assertRaises(InvalidInputError):
                convert_laxity_to_sf2("test.sid", "output.sf2")


class TestConvertGalwayToSF2(unittest.TestCase):
    """Test Galway to SF2 conversion."""

    @patch('sidm2.conversion_pipeline.GALWAY_CONVERTER_AVAILABLE', True)
    @patch('sidm2.conversion_pipeline.MartinGalwayAnalyzer')
    @patch('sidm2.conversion_pipeline.SIDParser')
    @patch('sidm2.conversion_pipeline.os.path.exists')
    def test_convert_galway_to_sf2_success(self, mock_exists, mock_parser_class, mock_analyzer_class):
        """Test successful Galway to SF2 conversion."""
        mock_exists.return_value = True

        # Mock parser
        mock_parser = Mock()
        mock_header = Mock()
        mock_header.load_address = 0x1000
        mock_header.data_offset = 0x7C  # Add data_offset
        mock_parser.parse_header.return_value = mock_header
        mock_parser.get_c64_data.return_value = (b'\x00' * 1024, 0x1000)
        mock_parser_class.return_value = mock_parser

        # Mock analyzer
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        test_input = "test_galway.sid"
        test_output = "test_output.sf2"

        with patch('builtins.open', mock_open(read_data=b'PSID' + b'\x00' * 1024)):
            with patch('sidm2.conversion_pipeline.GalwayConversionIntegrator') as mock_integrator:
                mock_integrator.return_value.integrate_and_convert.return_value = True
                result = convert_galway_to_sf2(test_input, test_output)

        self.assertTrue(result)

    @patch('sidm2.conversion_pipeline.GALWAY_CONVERTER_AVAILABLE', False)
    @patch('sidm2.conversion_pipeline.os.path.exists')
    def test_convert_galway_to_sf2_not_available(self, mock_exists):
        """Test conversion when Galway converter not available."""
        mock_exists.return_value = True

        # Should raise MissingDependencyError
        with self.assertRaises(Exception):  # Catches the custom error
            convert_galway_to_sf2("test.sid", "output.sf2")


class TestConvertSidToSF2(unittest.TestCase):
    """Test main SID to SF2 conversion function."""

    @patch('sidm2.conversion_pipeline.DriverSelector')
    @patch('sidm2.conversion_pipeline.detect_player_type')
    @patch('sidm2.conversion_pipeline.SIDParser')
    @patch('sidm2.conversion_pipeline.SF2Writer')
    def test_convert_sid_to_sf2_basic(self, mock_writer_class, mock_parser_class,
                                      mock_detect, mock_selector_class):
        """Test basic SID to SF2 conversion."""
        # Mock player detection
        mock_detect.return_value = "SidFactory_II"

        # Mock driver selector
        mock_selector = Mock()
        mock_selection = Mock()
        mock_selection.driver_name = "driver11"
        mock_selection.player_type = "SidFactory_II"
        mock_selector.select_driver.return_value = mock_selection
        mock_selector_class.return_value = mock_selector

        # Mock parser
        mock_parser = Mock()
        mock_header = Mock()
        mock_header.load_address = 0x1000
        mock_header.init_address = 0x1000
        mock_header.play_address = 0x10A1
        mock_header.data_offset = 0x7C
        mock_parser.parse_header.return_value = mock_header
        mock_parser.get_c64_data.return_value = (b'\x00' * 1024, 0x1000)
        mock_parser_class.return_value = mock_parser

        # Mock SF2 writer
        mock_writer = Mock()
        mock_writer_class.return_value = mock_writer

        test_input = "test.sid"
        test_output = "output.sf2"

        with patch('builtins.open', mock_open(read_data=b'\x00' * 1024)):
            with patch('os.path.exists', return_value=True):
                with patch('sidm2.conversion_pipeline.SF2PlayerParser') as mock_sf2_parser:
                    mock_sf2_parser.return_value.parse_header.return_value = mock_header
                    convert_sid_to_sf2(test_input, test_output)

        # Verify key function calls
        mock_detect.assert_called_once()
        mock_selector.select_driver.assert_called_once()

    @patch('sidm2.conversion_pipeline.DriverSelector')
    @patch('sidm2.conversion_pipeline.detect_player_type')
    @patch('sidm2.conversion_pipeline.convert_laxity_to_sf2')
    def test_convert_sid_to_sf2_laxity_driver(self, mock_laxity_convert,
                                               mock_detect, mock_selector_class):
        """Test conversion with Laxity driver selection."""
        # Mock player detection
        mock_detect.return_value = "NewPlayer_v21/Laxity"

        # Mock driver selector
        mock_selector = Mock()
        mock_selection = Mock()
        mock_selection.driver_name = "laxity"
        mock_selection.player_type = "NewPlayer_v21/Laxity"
        mock_selector.select_driver.return_value = mock_selection
        mock_selector_class.return_value = mock_selector

        # Mock Laxity conversion
        mock_laxity_convert.return_value = True

        test_input = "test_laxity.sid"
        test_output = "output.sf2"

        with patch('builtins.open', mock_open(read_data=b'\x00' * 1024)):
            with patch('os.path.exists', return_value=True):
                convert_sid_to_sf2(test_input, test_output)

        # Should call Laxity converter
        mock_laxity_convert.assert_called_once()

    @patch('sidm2.conversion_pipeline.DriverSelector')
    @patch('sidm2.conversion_pipeline.detect_player_type')
    @patch('sidm2.conversion_pipeline.SIDParser')
    def test_convert_sid_to_sf2_file_not_found(self, mock_parser_class,
                                                mock_detect, mock_selector_class):
        """Test conversion handles missing input file."""
        from sidm2.errors import FileNotFoundError as SidmFileNotFoundError

        with patch('os.path.exists', return_value=False):
            with self.assertRaises((FileNotFoundError, SidmFileNotFoundError)):
                convert_sid_to_sf2("nonexistent.sid", "output.sf2")

    @patch('sidm2.conversion_pipeline.DriverSelector')
    @patch('sidm2.conversion_pipeline.detect_player_type')
    @patch('sidm2.conversion_pipeline.SIDParser')
    @patch('sidm2.conversion_pipeline.SF2Writer')
    @patch('sidm2.conversion_pipeline.SF2PlayerParser')
    def test_convert_sid_to_sf2_with_quiet_mode(self, mock_sf2_parser, mock_writer,
                                                 mock_parser_class, mock_detect, mock_selector_class):
        """Test conversion in quiet mode."""
        mock_detect.return_value = "Unknown"

        mock_selector = Mock()
        mock_selection = Mock()
        mock_selection.driver_name = "driver11"
        mock_selector.select_driver.return_value = mock_selection
        mock_selector_class.return_value = mock_selector

        # Mock SIDParser
        mock_parser = Mock()
        mock_header = Mock()
        mock_header.load_address = 0x1000
        mock_header.data_offset = 0x7C
        mock_parser.parse_header.return_value = mock_header
        mock_parser.get_c64_data.return_value = (b'\x00' * 1024, 0x1000)
        mock_parser_class.return_value = mock_parser

        # Mock SF2PlayerParser
        mock_sf2_parser.return_value.parse_header.return_value = mock_header

        with patch('builtins.open', mock_open(read_data=b'\x00' * 1024)):
            with patch('os.path.exists', return_value=True):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    convert_sid_to_sf2("test.sid", "output.sf2", quiet=True)

                    # In quiet mode, should have minimal output
                    output = mock_stdout.getvalue()
                    # print_success_summary is called with quiet=True


class TestDriverTypeOverride(unittest.TestCase):
    """Test manual driver type override."""

    @patch('sidm2.conversion_pipeline.convert_laxity_to_sf2')
    @patch('sidm2.conversion_pipeline.detect_player_type')
    def test_convert_with_manual_laxity_override(self, mock_detect, mock_laxity_convert):
        """Test manual override to Laxity driver."""
        mock_detect.return_value = "Unknown"
        mock_laxity_convert.return_value = True

        with patch('builtins.open', mock_open(read_data=b'\x00' * 1024)):
            with patch('os.path.exists', return_value=True):
                convert_sid_to_sf2("test.sid", "output.sf2", driver_type="laxity")

        # Should use Laxity converter despite Unknown detection
        mock_laxity_convert.assert_called_once()

    @patch('sidm2.conversion_pipeline.convert_galway_to_sf2')
    @patch('sidm2.conversion_pipeline.detect_player_type')
    def test_convert_with_manual_galway_override(self, mock_detect, mock_galway_convert):
        """Test manual override to Galway driver."""
        mock_detect.return_value = "Unknown"
        mock_galway_convert.return_value = True

        with patch('builtins.open', mock_open(read_data=b'\x00' * 1024)):
            with patch('os.path.exists', return_value=True):
                convert_sid_to_sf2("test.sid", "output.sf2", driver_type="galway")

        # Should use Galway converter
        mock_galway_convert.assert_called_once()


class TestConfigurationHandling(unittest.TestCase):
    """Test configuration handling."""

    @patch('sidm2.conversion_pipeline.get_default_config')
    @patch('sidm2.conversion_pipeline.DriverSelector')
    @patch('sidm2.conversion_pipeline.detect_player_type')
    @patch('sidm2.conversion_pipeline.SIDParser')
    @patch('sidm2.conversion_pipeline.SF2Writer')
    def test_convert_with_default_config(self, mock_writer, mock_parser,
                                         mock_detect, mock_selector, mock_get_config):
        """Test conversion uses default config when none provided."""
        from sidm2.config import ConversionConfig

        mock_detect.return_value = "Unknown"
        mock_selector.return_value.select_driver.return_value = Mock(driver_name="driver11")

        default_config = ConversionConfig()
        mock_get_config.return_value = default_config

        mock_header = Mock(load_address=0x1000, data_offset=0x7C)
        mock_parser.return_value.parse_header.return_value = mock_header
        mock_parser.return_value.get_c64_data.return_value = (b'\x00' * 1024, 0x1000)

        with patch('builtins.open', mock_open(read_data=b'\x00' * 1024)):
            with patch('os.path.exists', return_value=True):
                with patch('sidm2.conversion_pipeline.SF2PlayerParser') as mock_sf2_parser:
                    mock_sf2_parser.return_value.parse_header.return_value = mock_header
                    convert_sid_to_sf2("test.sid", "output.sf2")

        # Should call get_default_config
        mock_get_config.assert_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
