"""Unit tests for sidm2.sf2_template_finder.

Both functions are read-only filesystem lookups, so tests use
monkeypatch to:
  (a) confirm they call os.path.exists with expected candidate paths
  (b) verify alias handling (`d11`, `11` → `driver11`)
  (c) verify the per-driver-type fallback order
  (d) verify None when no candidate exists

These tests stay deterministic regardless of which template/driver
files actually exist on the host filesystem.
"""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2 import sf2_template_finder as tf


class TestFindTemplate(unittest.TestCase):
    def test_unknown_driver_falls_back_to_driver11(self):
        """An unknown driver_type uses the driver11 search list."""
        seen_paths = []

        def fake_exists(p):
            seen_paths.append(p)
            return False

        with patch('os.path.exists', side_effect=fake_exists):
            result = tf.find_template('totally-unknown-driver')

        self.assertIsNone(result)
        # The seen paths should include "Driver 11 Test - Arpeggio.sf2"
        self.assertTrue(
            any('Driver 11 Test - Arpeggio.sf2' in p for p in seen_paths),
            "unknown driver_type should fall back to driver11 search list"
        )

    def test_d11_alias_maps_to_driver11(self):
        """`d11` alias = same search list as `driver11`."""
        d11_paths = []
        driver11_paths = []

        def collect(target_list):
            def fake_exists(p):
                target_list.append(p)
                return False
            return fake_exists

        with patch('os.path.exists', side_effect=collect(d11_paths)):
            tf.find_template('d11')

        with patch('os.path.exists', side_effect=collect(driver11_paths)):
            tf.find_template('driver11')

        self.assertEqual(d11_paths, driver11_paths,
                         "'d11' alias should match 'driver11' behavior")

    def test_11_alias_maps_to_driver11(self):
        paths_11 = []
        paths_driver11 = []

        with patch('os.path.exists', side_effect=lambda p: paths_11.append(p) or False):
            tf.find_template('11')

        with patch('os.path.exists', side_effect=lambda p: paths_driver11.append(p) or False):
            tf.find_template('driver11')

        self.assertEqual(paths_11, paths_driver11)

    def test_returns_first_existing_path(self):
        """When multiple candidates exist, the first one in the search
        order wins."""
        # Mock so that the SECOND path exists. find_template should
        # walk in order and return that path.
        call_count = [0]

        def fake_exists(p):
            call_count[0] += 1
            return call_count[0] == 2

        with patch('os.path.exists', side_effect=fake_exists):
            result = tf.find_template('driver11')

        self.assertIsNotNone(result, "second path exists → should return it")
        self.assertEqual(call_count[0], 2, "stops after finding first match")

    def test_returns_none_when_nothing_exists(self):
        with patch('os.path.exists', return_value=False):
            self.assertIsNone(tf.find_template('driver11'))
            self.assertIsNone(tf.find_template('np20'))
            self.assertIsNone(tf.find_template('laxity'))

    def test_driver11_search_includes_examples_first(self):
        """The bundled SF2 example file should be checked BEFORE any
        .prg driver file (the examples have correct table addresses,
        .prg drivers have wrong addresses)."""
        order = []

        def fake_exists(p):
            order.append(p)
            return False

        with patch('os.path.exists', side_effect=fake_exists):
            tf.find_template('driver11')

        # Find indices of the SF2 example and the first .prg driver
        sf2_indices = [i for i, p in enumerate(order)
                        if p.endswith('.sf2')]
        prg_indices = [i for i, p in enumerate(order)
                        if p.endswith('.prg')]
        if sf2_indices and prg_indices:
            self.assertLess(min(sf2_indices), min(prg_indices),
                            "SF2 examples must be checked before .prg drivers")

    def test_np20_search_uses_np20_specific_paths(self):
        seen = []
        with patch('os.path.exists', side_effect=lambda p: seen.append(p) or False):
            tf.find_template('np20')
        # All paths should mention np20 (case-insensitive) or template_np20
        for p in seen:
            self.assertIn('np20', p.lower())

    def test_laxity_search_uses_laxity_specific_paths(self):
        seen = []
        with patch('os.path.exists', side_effect=lambda p: seen.append(p) or False):
            tf.find_template('laxity')
        for p in seen:
            self.assertIn('laxity', p.lower())


class TestFindDriver(unittest.TestCase):
    def test_search_paths_for_v16_driver(self):
        """Checks expected three candidate paths for sf2driver16_01.prg."""
        seen = []
        with patch('os.path.exists', side_effect=lambda p: seen.append(p) or False):
            result = tf.find_driver()
        self.assertIsNone(result)
        # All paths should mention sf2driver16_01.prg
        for p in seen:
            self.assertIn('sf2driver16_01.prg', p)
        # Should have checked 3 candidates
        self.assertEqual(len(seen), 3)

    def test_returns_first_existing(self):
        call_count = [0]

        def fake_exists(p):
            call_count[0] += 1
            return call_count[0] == 1   # first path exists

        with patch('os.path.exists', side_effect=fake_exists):
            result = tf.find_driver()
        self.assertIsNotNone(result)
        self.assertEqual(call_count[0], 1, "stops on first match")

    def test_returns_none_when_no_drivers(self):
        with patch('os.path.exists', return_value=False):
            self.assertIsNone(tf.find_driver())


class TestBaseDir(unittest.TestCase):
    def test_base_dir_is_two_levels_up(self):
        """The internal _base_dir() helper resolves to the project root."""
        base = tf._base_dir()
        # The project root contains pyscript/, sidm2/, scripts/, etc.
        self.assertTrue(os.path.isdir(os.path.join(base, 'sidm2')),
                        f"base_dir={base} should contain sidm2/")


if __name__ == "__main__":
    unittest.main(verbosity=2)
