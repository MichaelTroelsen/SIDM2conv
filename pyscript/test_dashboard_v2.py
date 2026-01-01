"""
Unit Tests for Validation Dashboard v2.0

Tests for dashboard_v2.py - improved HTML dashboard generator
with enhanced features and professional styling.

Tests cover:
- Dashboard HTML generation
- Stats grid creation
- Trend chart rendering
- Results table generation
- Search functionality
- Sidebar navigation
- None/null value handling
- Empty data scenarios

Usage:
    python pyscript/test_dashboard_v2.py
    python pyscript/test_dashboard_v2.py -v
"""

import unittest
import sys
import os
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scripts.validation.dashboard_v2 import DashboardGeneratorV2


class TestDashboardGeneratorV2(unittest.TestCase):
    """Test dashboard v2 HTML generation."""

    def setUp(self):
        """Set up test fixtures."""
        self.generator = DashboardGeneratorV2()

        # Sample run info
        self.run_info = {
            'run_id': 42,
            'timestamp': '2026-01-01 12:00:00',
            'driver': 'laxity'
        }

        # Sample aggregate data
        self.aggregate = {
            'total_files': 10,
            'passed_files': 8,
            'failed_files': 2,
            'pass_rate': 80.0,
            'avg_overall_accuracy': 85.5,
            'avg_step1_accuracy': 90.0
        }

        # Sample results
        self.results = [
            {
                'filename': 'test1.sid',
                'status': 'PASS',
                'overall_accuracy': 95.5,
                'step1_accuracy': 98.0,
                'step2_accuracy': 92.0,
                'step3_accuracy': 96.0
            },
            {
                'filename': 'test2.sid',
                'status': 'FAIL',
                'overall_accuracy': 45.0,
                'step1_accuracy': 50.0,
                'step2_accuracy': 40.0,
                'step3_accuracy': 45.0
            }
        ]

        # Sample trend data
        self.trend_data = {
            'accuracy': [
                {'run_id': 1, 'value': 85.0},
                {'run_id': 2, 'value': 87.5},
                {'run_id': 3, 'value': 90.0}
            ]
        }

    def test_generate_html_basic(self):
        """Test basic HTML generation."""
        html = self.generator.generate_html(
            self.run_info,
            self.results,
            self.aggregate,
            self.trend_data
        )

        self.assertIsInstance(html, str)
        self.assertGreater(len(html), 1000)
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('</html>', html)
        self.assertIn('Validation Dashboard', html)

    def test_generate_html_without_trends(self):
        """Test HTML generation without trend data."""
        html = self.generator.generate_html(
            self.run_info,
            self.results,
            self.aggregate,
            None
        )

        self.assertIsInstance(html, str)
        self.assertIn('<!DOCTYPE html>', html)
        # Should not include trend chart
        self.assertNotIn('accuracyTrendChart', html)

    def test_stats_grid_creation(self):
        """Test statistics grid generation."""
        html = self.generator._create_stats_grid(self.aggregate)

        self.assertIn('Total Files', html)
        self.assertIn('10', html)  # total files
        self.assertIn('8', html)   # passed
        self.assertIn('2', html)   # failed
        self.assertIn('80.0%', html)  # pass rate
        self.assertIn('85.5%', html)  # avg accuracy

    def test_results_section_creation(self):
        """Test results table generation."""
        html = self.generator._create_results_section(self.results)

        self.assertIn('test1.sid', html)
        self.assertIn('test2.sid', html)
        self.assertIn('PASS', html)
        self.assertIn('FAIL', html)
        self.assertIn('95.5%', html)
        self.assertIn('45.0%', html)

    def test_results_sorting(self):
        """Test that failed files appear first."""
        html = self.generator._create_results_section(self.results)

        # Find positions of filenames
        pos_fail = html.find('test2.sid')  # Failed file
        pos_pass = html.find('test1.sid')  # Passed file

        # Failed should come before passed
        self.assertLess(pos_fail, pos_pass)

    def test_trend_section_with_dict_data(self):
        """Test trend chart with dict-formatted data."""
        html = self.generator._create_trend_section(self.trend_data)

        self.assertIn('accuracyTrendChart', html)
        self.assertIn('canvas', html)
        self.assertIn('Chart', html)
        # Check labels and data
        self.assertIn('[\'1\', \'2\', \'3\']', html)  # run_ids
        self.assertIn('[85.0, 87.5, 90.0]', html)  # accuracy values

    def test_trend_section_with_tuple_data(self):
        """Test trend chart with tuple-formatted data."""
        tuple_trend = {
            'accuracy': [
                (1, 85.0),
                (2, 87.5),
                (3, 90.0)
            ]
        }

        html = self.generator._create_trend_section(tuple_trend)

        self.assertIn('accuracyTrendChart', html)
        self.assertIn('[\'1\', \'2\', \'3\']', html)
        self.assertIn('[85.0, 87.5, 90.0]', html)

    def test_trend_section_empty_data(self):
        """Test trend chart with empty data."""
        empty_trend = {'accuracy': []}
        html = self.generator._create_trend_section(empty_trend)

        self.assertEqual(html, '')

    def test_sidebar_creation(self):
        """Test sidebar navigation generation."""
        html = self.generator._create_sidebar(
            self.run_info,
            self.aggregate,
            len(self.results)
        )

        self.assertIn('sidebar', html)
        self.assertIn('Overview', html)
        self.assertIn('Statistics', html)
        self.assertIn('Results', html)
        self.assertIn('80.0%', html)  # Pass rate in sidebar

    def test_header_creation(self):
        """Test header section generation."""
        html = self.generator._create_header(self.run_info)

        self.assertIn('Validation Dashboard', html)
        self.assertIn('42', html)  # run_id
        self.assertIn('2026-01-01 12:00:00', html)  # timestamp
        self.assertIn('laxity', html)  # driver

    def test_custom_javascript(self):
        """Test custom JavaScript generation."""
        html = self.generator._add_custom_javascript()

        self.assertIn('<script>', html)
        self.assertIn('searchBox', html)
        self.assertIn('addEventListener', html)
        # Check for accuracy filter logic
        self.assertIn('>', html)  # Greater than filter
        self.assertIn('<', html)  # Less than filter
        self.assertIn('parseFloat', html)

    def test_handle_none_accuracies(self):
        """Test handling of None accuracy values."""
        results_with_none = [
            {
                'filename': 'test3.sid',
                'status': 'FAIL',
                'overall_accuracy': None,
                'step1_accuracy': None,
                'step2_accuracy': 50.0,
                'step3_accuracy': None
            }
        ]

        html = self.generator._create_results_section(results_with_none)

        self.assertIn('test3.sid', html)
        self.assertIn('0.0%', html)  # None should be converted to 0

    def test_empty_results(self):
        """Test with no results."""
        html = self.generator._create_results_section([])

        self.assertIn('No validation results found', html)

    def test_full_generation_integration(self):
        """Test full dashboard generation integration."""
        html = self.generator.generate_html(
            self.run_info,
            self.results,
            self.aggregate,
            self.trend_data
        )

        # Check all major sections present
        self.assertIn('Validation Dashboard', html)
        self.assertIn('Total Files', html)
        self.assertIn('accuracyTrendChart', html)
        self.assertIn('test1.sid', html)
        self.assertIn('test2.sid', html)
        self.assertIn('sidebar', html)
        self.assertIn('search', html.lower())

    def test_color_scheme_in_output(self):
        """Test that ColorScheme values are used."""
        html = self.generator.generate_html(
            self.run_info,
            self.results,
            self.aggregate,
            self.trend_data
        )

        # Should contain color scheme colors (hex codes)
        self.assertIn('#', html)  # Hex color codes present

    def test_accuracy_bar_colors(self):
        """Test accuracy bar color coding."""
        html = self.generator._create_results_section(self.results)

        # High accuracy (>90%) should use success color
        # Low accuracy (<70%) should use error color
        # Check that progress bars are present
        self.assertIn('width:', html)
        self.assertIn('95.5%', html)  # High accuracy
        self.assertIn('45.0%', html)  # Low accuracy


class TestDashboardV2ConvenienceFunction(unittest.TestCase):
    """Test convenience function for dashboard generation."""

    def test_generate_html_v2_function(self):
        """Test generate_html_v2 convenience function."""
        from scripts.validation.dashboard_v2 import generate_html_v2

        run_info = {'run_id': 1, 'timestamp': '2026-01-01', 'driver': 'test'}
        results = []
        aggregate = {
            'total_files': 0,
            'passed_files': 0,
            'failed_files': 0,
            'pass_rate': 0,
            'avg_overall_accuracy': 0,
            'avg_step1_accuracy': 0
        }

        html = generate_html_v2(run_info, results, aggregate, None)

        self.assertIsInstance(html, str)
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('Validation Dashboard', html)


if __name__ == '__main__':
    unittest.main()
