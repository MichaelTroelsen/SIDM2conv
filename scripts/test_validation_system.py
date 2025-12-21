"""
Unit tests for Validation System.

Tests validation database, metrics collection, regression detection,
and dashboard generation.

Run: python scripts/test_validation_system.py
"""

import unittest
import tempfile
import sqlite3
import os
import json
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validation.database import ValidationDatabase
from scripts.validation.metrics import MetricsCollector
from scripts.validation.regression import RegressionDetector


class TestValidationDatabase(unittest.TestCase):
    """Test ValidationDatabase class."""

    def setUp(self):
        """Create temporary database for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / 'test_validation.db'
        self.db = ValidationDatabase(self.db_path)

    def tearDown(self):
        """Clean up temporary files."""
        if self.db.conn:
            self.db.conn.close()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_initialization(self):
        """Test database tables are created."""
        cursor = self.db.conn.cursor()

        # Check validation_runs table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='validation_runs'
        """)
        self.assertIsNotNone(cursor.fetchone())

        # Check file_results table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='file_results'
        """)
        self.assertIsNotNone(cursor.fetchone())

        # Check metric_trends table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='metric_trends'
        """)
        self.assertIsNotNone(cursor.fetchone())

    def test_create_run(self):
        """Test creating a validation run."""
        run_id = self.db.create_run(
            git_commit='abc123',
            pipeline_version='v1.0.0',
            notes='Test run'
        )

        self.assertIsInstance(run_id, int)
        self.assertGreater(run_id, 0)

        # Verify run was created
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM validation_runs WHERE run_id = ?', (run_id,))
        row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row['git_commit'], 'abc123')
        self.assertEqual(row['pipeline_version'], 'v1.0.0')
        self.assertEqual(row['notes'], 'Test run')

    def test_create_run_minimal(self):
        """Test creating a run with minimal parameters."""
        run_id = self.db.create_run()

        self.assertIsInstance(run_id, int)
        self.assertGreater(run_id, 0)

    def test_add_file_result(self):
        """Test adding a file result."""
        run_id = self.db.create_run()

        result_id = self.db.add_file_result(
            run_id=run_id,
            filename='test.sid',
            conversion_method='laxity',
            conversion_success=True,
            overall_accuracy=99.93,
            step1_conversion=True,
            step2_packing=True
        )

        self.assertIsInstance(result_id, int)
        self.assertGreater(result_id, 0)

        # Verify result was created
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT * FROM file_results WHERE result_id = ?', (result_id,))
        row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row['filename'], 'test.sid')
        self.assertEqual(row['conversion_method'], 'laxity')
        self.assertTrue(row['conversion_success'])
        self.assertAlmostEqual(row['overall_accuracy'], 99.93, places=2)

    def test_add_metric(self):
        """Test adding a metric to trends."""
        run_id = self.db.create_run()

        self.db.add_metric(run_id, 'avg_accuracy', 85.5)

        # Verify metric was added
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM metric_trends
            WHERE run_id = ? AND metric_name = ?
        """, (run_id, 'avg_accuracy'))
        row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row['metric_name'], 'avg_accuracy')
        self.assertAlmostEqual(row['metric_value'], 85.5, places=1)

    def test_multiple_runs(self):
        """Test creating multiple validation runs."""
        run1 = self.db.create_run(git_commit='abc123')
        run2 = self.db.create_run(git_commit='def456')
        run3 = self.db.create_run(git_commit='ghi789')

        self.assertNotEqual(run1, run2)
        self.assertNotEqual(run2, run3)
        self.assertNotEqual(run1, run3)

        # Verify all runs exist
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM validation_runs')
        count = cursor.fetchone()[0]

        self.assertEqual(count, 3)

    def test_multiple_file_results_per_run(self):
        """Test adding multiple file results to a run."""
        run_id = self.db.create_run()

        # Add 3 file results
        result1 = self.db.add_file_result(
            run_id=run_id,
            filename='file1.sid',
            overall_accuracy=90.0
        )
        result2 = self.db.add_file_result(
            run_id=run_id,
            filename='file2.sid',
            overall_accuracy=85.0
        )
        result3 = self.db.add_file_result(
            run_id=run_id,
            filename='file3.sid',
            overall_accuracy=95.0
        )

        # Verify all results exist for this run
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM file_results WHERE run_id = ?', (run_id,))
        count = cursor.fetchone()[0]

        self.assertEqual(count, 3)


class TestRegressionDetector(unittest.TestCase):
    """Test RegressionDetector class."""

    def setUp(self):
        """Create regression detector."""
        self.detector = RegressionDetector(threshold_accuracy=5.0, threshold_size=20.0)

    def test_init_with_thresholds(self):
        """Test RegressionDetector initialization with thresholds."""
        self.assertEqual(self.detector.threshold_accuracy, 5.0)
        self.assertEqual(self.detector.threshold_size, 20.0)

    def test_detect_regressions_no_changes(self):
        """Test no regressions when results are identical."""
        baseline = [
            {'filename': 'test.sid', 'overall_accuracy': 95.0, 'step1_conversion': True}
        ]
        current = [
            {'filename': 'test.sid', 'overall_accuracy': 95.0, 'step1_conversion': True}
        ]

        results = self.detector.detect_regressions(baseline, current)

        self.assertEqual(results['regression_count'], 0)
        self.assertEqual(results['improvement_count'], 0)
        self.assertEqual(results['warning_count'], 0)

    def test_detect_accuracy_regression(self):
        """Test detecting accuracy drop."""
        baseline = [
            {'filename': 'test.sid', 'overall_accuracy': 95.0}
        ]
        current = [
            {'filename': 'test.sid', 'overall_accuracy': 85.0}  # 10% drop (> 5% threshold)
        ]

        results = self.detector.detect_regressions(baseline, current)

        self.assertGreater(results['regression_count'], 0)
        self.assertIn('accuracy_drop', results['regressions'][0]['type'])

    def test_detect_step_failure(self):
        """Test detecting pipeline step failure."""
        baseline = [
            {'filename': 'test.sid', 'step1_conversion': True, 'step2_packing': True}
        ]
        current = [
            {'filename': 'test.sid', 'step1_conversion': True, 'step2_packing': False}
        ]

        results = self.detector.detect_regressions(baseline, current)

        self.assertGreater(results['regression_count'], 0)
        self.assertIn('step_failure', results['regressions'][0]['type'])

    def test_detect_improvement(self):
        """Test detecting accuracy improvement."""
        baseline = [
            {'filename': 'test.sid', 'overall_accuracy': 85.0}
        ]
        current = [
            {'filename': 'test.sid', 'overall_accuracy': 95.0}  # 10% improvement
        ]

        results = self.detector.detect_regressions(baseline, current)

        self.assertEqual(results['regression_count'], 0)
        self.assertGreater(results['improvement_count'], 0)

    def test_detect_new_files(self):
        """Test detecting newly added files."""
        baseline = [
            {'filename': 'old.sid'}
        ]
        current = [
            {'filename': 'old.sid'},
            {'filename': 'new.sid'}
        ]

        results = self.detector.detect_regressions(baseline, current)

        self.assertIn('new.sid', results['new_files'])

    def test_detect_removed_files(self):
        """Test detecting removed files."""
        baseline = [
            {'filename': 'old.sid'},
            {'filename': 'removed.sid'}
        ]
        current = [
            {'filename': 'old.sid'}
        ]

        results = self.detector.detect_regressions(baseline, current)

        self.assertIn('removed.sid', results['removed_files'])


class TestValidationDatabaseQueries(unittest.TestCase):
    """Test database query operations."""

    def setUp(self):
        """Create database with test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / 'test_validation.db'
        self.db = ValidationDatabase(self.db_path)

        # Create test runs
        self.run1 = self.db.create_run(git_commit='abc123')
        self.run2 = self.db.create_run(git_commit='def456')

        # Add file results to run1
        self.db.add_file_result(
            self.run1,
            filename='file1.sid',
            overall_accuracy=90.0,
            step1_conversion=True
        )
        self.db.add_file_result(
            self.run1,
            filename='file2.sid',
            overall_accuracy=85.0,
            step1_conversion=True
        )

    def tearDown(self):
        """Clean up."""
        if self.db.conn:
            self.db.conn.close()
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_get_run_results(self):
        """Test querying all results for a run."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM file_results WHERE run_id = ?
        """, (self.run1,))
        results = cursor.fetchall()

        self.assertEqual(len(results), 2)
        filenames = [r['filename'] for r in results]
        self.assertIn('file1.sid', filenames)
        self.assertIn('file2.sid', filenames)

    def test_get_latest_run(self):
        """Test getting the latest validation run."""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM validation_runs
            ORDER BY run_id DESC LIMIT 1
        """)
        latest = cursor.fetchone()

        self.assertEqual(latest['run_id'], self.run2)
        self.assertEqual(latest['git_commit'], 'def456')


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
