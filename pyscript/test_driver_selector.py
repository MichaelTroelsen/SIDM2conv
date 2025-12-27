#!/usr/bin/env python3
"""
Unit tests for driver selection system.

Tests the DriverSelector class and automatic driver selection logic.
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.driver_selector import DriverSelector, DriverSelection


class TestDriverSelector(unittest.TestCase):
    """Test cases for DriverSelector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.selector = DriverSelector()

    def test_laxity_variants(self):
        """Test that all Laxity variants map to laxity driver."""
        laxity_variants = [
            'Laxity_NewPlayer_V21',
            'Vibrants/Laxity',
            'SidFactory_II/Laxity',
            'SidFactory/Laxity',
            '256bytes/Laxity',
        ]

        for player_type in laxity_variants:
            result = self.selector._select_best_driver(player_type)
            self.assertEqual(result, 'laxity',
                           f"Player type '{player_type}' should map to laxity driver")

    def test_newplayer20_variants(self):
        """Test that NewPlayer 20 variants map to np20 driver."""
        np20_variants = [
            'NewPlayer_20',
            'NewPlayer_20.G4',
            'NP20',
        ]

        for player_type in np20_variants:
            result = self.selector._select_best_driver(player_type)
            self.assertEqual(result, 'np20',
                           f"Player type '{player_type}' should map to np20 driver")

    def test_sf2_exported_variants(self):
        """Test that SF2-exported files map to driver11."""
        sf2_variants = [
            'SF2_Exported',
            'Driver_11',
        ]

        for player_type in sf2_variants:
            result = self.selector._select_best_driver(player_type)
            self.assertEqual(result, 'driver11',
                           f"Player type '{player_type}' should map to driver11")

    def test_unknown_player_defaults_to_driver11(self):
        """Test that unknown player types default to driver11."""
        unknown_types = [
            'Unknown',
            'Rob_Hubbard',
            'Martin_Galway',
            'UNIDENTIFIED',
            '',
        ]

        for player_type in unknown_types:
            result = self.selector._select_best_driver(player_type)
            self.assertEqual(result, 'driver11',
                           f"Unknown player type '{player_type}' should default to driver11")

    def test_partial_match_laxity(self):
        """Test partial matching for laxity in player name."""
        partial_laxity = [
            'laxity_custom',
            'NEW_laxity_player',
            'Laxity_Modified',
        ]

        for player_type in partial_laxity:
            result = self.selector._select_best_driver(player_type)
            self.assertEqual(result, 'laxity',
                           f"Player type '{player_type}' should partially match laxity")

    def test_partial_match_newplayer20(self):
        """Test partial matching for NewPlayer 20."""
        partial_np20 = [
            'newplayer 20 custom',
            'NewPlayer_20_Modified',
        ]

        for player_type in partial_np20:
            result = self.selector._select_best_driver(player_type)
            self.assertEqual(result, 'np20',
                           f"Player type '{player_type}' should partially match np20")

        # "NP20" alone without "newplayer" should use exact mapping from PLAYER_MAPPINGS
        # If it's a variant like "NP20_variant", it falls back to driver11
        result = self.selector._select_best_driver('NP20')
        self.assertEqual(result, 'np20', "Exact 'NP20' should match via PLAYER_MAPPINGS")

    def test_build_selection_result_laxity(self):
        """Test building selection result for Laxity driver."""
        result = self.selector._build_selection_result('laxity', 'SidFactory_II/Laxity')

        self.assertEqual(result.driver_name, 'laxity')
        self.assertEqual(result.driver_file, 'sf2driver_laxity_00.prg')
        self.assertEqual(result.expected_accuracy, '99.93%')
        self.assertEqual(result.player_type, 'SidFactory_II/Laxity')
        self.assertEqual(result.alternative_driver, 'Driver 11')
        self.assertEqual(result.alternative_accuracy, '1-8%')
        self.assertIn('Laxity-specific', result.selection_reason)

    def test_build_selection_result_np20(self):
        """Test building selection result for NP20 driver."""
        result = self.selector._build_selection_result('np20', 'NewPlayer_20.G4')

        self.assertEqual(result.driver_name, 'np20')
        self.assertEqual(result.driver_file, 'sf2driver_np20.prg')
        self.assertEqual(result.expected_accuracy, '70-90%')
        self.assertEqual(result.player_type, 'NewPlayer_20.G4')
        self.assertEqual(result.alternative_driver, 'Driver 11')
        self.assertEqual(result.alternative_accuracy, '~10-20%')

    def test_build_selection_result_driver11_sf2(self):
        """Test building selection result for SF2-exported files."""
        result = self.selector._build_selection_result('driver11', 'SF2_Exported')

        self.assertEqual(result.driver_name, 'driver11')
        self.assertEqual(result.driver_file, 'sf2driver_11.prg')
        self.assertEqual(result.expected_accuracy, '100%')
        self.assertEqual(result.player_type, 'SF2_Exported')
        self.assertIn('SF2-exported', result.selection_reason)
        self.assertEqual(result.alternative_driver, '')

    def test_build_selection_result_driver11_default(self):
        """Test building selection result for unknown files (Driver 11 default)."""
        result = self.selector._build_selection_result('driver11', 'Unknown')

        self.assertEqual(result.driver_name, 'driver11')
        self.assertEqual(result.driver_file, 'sf2driver_11.prg')
        self.assertEqual(result.expected_accuracy, 'Safe default')
        self.assertEqual(result.player_type, 'Unknown')
        self.assertIn('compatibility', result.selection_reason)
        self.assertEqual(result.alternative_driver, '')

    def test_handle_forced_driver(self):
        """Test forced driver override."""
        result = self.selector._handle_forced_driver('laxity', 'Unknown')

        self.assertEqual(result.driver_name, 'laxity')
        self.assertEqual(result.expected_accuracy, 'User override')
        self.assertIn('Manual override', result.selection_reason)
        self.assertEqual(result.player_type, 'Unknown')

    def test_format_selection_output(self):
        """Test formatting selection output for console."""
        selection = DriverSelection(
            driver_name='laxity',
            driver_file='sf2driver_laxity_00.prg',
            expected_accuracy='99.93%',
            selection_reason='Test reason',
            player_type='Test_Player',
            alternative_driver='Driver 11',
            alternative_accuracy='1-8%'
        )

        output = self.selector.format_selection_output(selection)

        self.assertIn('Driver Selection:', output)
        self.assertIn('Test_Player', output)
        self.assertIn('LAXITY', output)
        self.assertIn('99.93%', output)
        self.assertIn('Test reason', output)
        self.assertIn('Driver 11', output)
        self.assertIn('1-8%', output)
        self.assertIn('not recommended', output)

    def test_format_info_file_section(self):
        """Test formatting selection for info file."""
        selection = DriverSelection(
            driver_name='np20',
            driver_file='sf2driver_np20.prg',
            expected_accuracy='70-90%',
            selection_reason='NP20 specific',
            player_type='NewPlayer_20',
        )

        output = self.selector.format_info_file_section(selection)

        self.assertIn('Driver Selection:', output)
        self.assertIn('NP20', output)
        self.assertIn('70-90%', output)
        self.assertIn('NP20 specific', output)

    def test_create_conversion_info(self):
        """Test creating complete conversion info file."""
        selection = DriverSelection(
            driver_name='laxity',
            driver_file='sf2driver_laxity_00.prg',
            expected_accuracy='99.93%',
            selection_reason='Laxity driver',
            player_type='SidFactory_II/Laxity'
        )

        sid_metadata = {
            'title': 'Test Song',
            'author': 'Test Author',
            'copyright': '2025',
            'format': 'PSID v2',
            'load_addr': 0x1000,
            'init_addr': 0x1000,
            'play_addr': 0x1003,
            'songs': 1
        }

        # Mock output file
        output_file = Mock()
        output_file.name = 'test.sf2'
        output_file.exists.return_value = True
        output_file.stat.return_value.st_size = 10000

        info = self.selector.create_conversion_info(
            selection,
            Path('test.sid'),
            output_file,
            sid_metadata
        )

        self.assertIn('Conversion Information', info)
        self.assertIn('Test Song', info)
        self.assertIn('Test Author', info)
        self.assertIn('2025', info)
        self.assertIn('SidFactory_II/Laxity', info)
        self.assertIn('LAXITY', info)
        self.assertIn('99.93%', info)
        self.assertIn('SUCCESS', info)
        self.assertIn('10,000 bytes', info)

    @patch('subprocess.run')
    def test_identify_player_success(self, mock_run):
        """Test successful player identification."""
        # Mock player-id.exe output
        mock_run.return_value.stdout = "test.sid  SidFactory_II/Laxity\n"

        result = self.selector.identify_player(Path('test.sid'))

        self.assertEqual(result, 'SidFactory_II/Laxity')
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_identify_player_unidentified(self, mock_run):
        """Test unidentified file."""
        mock_run.return_value.stdout = "test.sid  UNIDENTIFIED\n"

        result = self.selector.identify_player(Path('test.sid'))

        self.assertEqual(result, 'Unknown')

    @patch('subprocess.run')
    def test_identify_player_exception(self, mock_run):
        """Test exception during player identification."""
        mock_run.side_effect = Exception("Test error")

        result = self.selector.identify_player(Path('test.sid'))

        self.assertEqual(result, 'Unknown')

    @patch('subprocess.run')
    def test_identify_player_no_exe(self, mock_run):
        """Test when player-id.exe doesn't exist."""
        selector = DriverSelector(player_id_exe=Path('nonexistent.exe'))

        result = selector.identify_player(Path('test.sid'))

        self.assertEqual(result, 'Unknown')
        mock_run.assert_not_called()

    @patch.object(DriverSelector, 'identify_player')
    def test_select_driver_auto_detection(self, mock_identify):
        """Test automatic driver selection."""
        mock_identify.return_value = 'SidFactory_II/Laxity'

        result = self.selector.select_driver(Path('test.sid'))

        self.assertEqual(result.driver_name, 'laxity')
        self.assertEqual(result.player_type, 'SidFactory_II/Laxity')
        mock_identify.assert_called_once()

    def test_select_driver_with_player_type(self):
        """Test driver selection with pre-identified player type."""
        result = self.selector.select_driver(
            Path('test.sid'),
            player_type='NewPlayer_20'
        )

        self.assertEqual(result.driver_name, 'np20')
        self.assertEqual(result.player_type, 'NewPlayer_20')

    def test_select_driver_forced(self):
        """Test forced driver override."""
        result = self.selector.select_driver(
            Path('test.sid'),
            player_type='SidFactory_II/Laxity',
            force_driver='driver11'
        )

        self.assertEqual(result.driver_name, 'driver11')
        self.assertIn('Manual override', result.selection_reason)


class TestDriverSelectionEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""

    def setUp(self):
        """Set up test fixtures."""
        self.selector = DriverSelector()

    def test_empty_player_type(self):
        """Test handling of empty player type."""
        result = self.selector._select_best_driver('')
        self.assertEqual(result, 'driver11')

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        test_cases = [
            'LAXITY_PLAYER',
            'laxity_player',
            'LaxItY_PlAyEr',
        ]

        for player_type in test_cases:
            result = self.selector._select_best_driver(player_type)
            self.assertEqual(result, 'laxity')

    def test_whitespace_handling(self):
        """Test handling of whitespace in player names."""
        test_cases = [
            ' Laxity ',
            'Laxity\t',
            '\nLaxity\n',
        ]

        for player_type in test_cases:
            result = self.selector._select_best_driver(player_type)
            self.assertEqual(result, 'laxity')

    def test_special_characters_in_player_name(self):
        """Test handling of special characters."""
        player_type = 'Laxity/NewPlayer!@#$%'

        # Should still match laxity
        result = self.selector._select_best_driver(player_type)
        self.assertEqual(result, 'laxity')

    def test_very_long_player_name(self):
        """Test handling of very long player names."""
        player_type = 'Laxity' + ('_extra' * 100)

        result = self.selector._select_best_driver(player_type)
        self.assertEqual(result, 'laxity')

    def test_driver_file_mapping(self):
        """Test that all drivers have file mappings."""
        for driver in ['laxity', 'driver11', 'np20']:
            self.assertIn(driver, self.selector.DRIVER_FILES)
            self.assertTrue(self.selector.DRIVER_FILES[driver])

    def test_accuracy_mappings_complete(self):
        """Test that all accuracy types are mapped."""
        required_keys = ['laxity', 'driver11_sf2', 'driver11_default', 'np20']

        for key in required_keys:
            self.assertIn(key, self.selector.EXPECTED_ACCURACY)
            self.assertTrue(self.selector.EXPECTED_ACCURACY[key])


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDriverSelector))
    suite.addTests(loader.loadTestsFromTestCase(TestDriverSelectionEdgeCases))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
