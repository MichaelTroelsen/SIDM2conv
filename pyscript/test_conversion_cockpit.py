#!/usr/bin/env python3
"""
Unit Tests for Conversion Cockpit

Tests PipelineConfig, ConversionExecutor, and custom widgets.

Version: 1.0.0
Date: 2025-12-22
"""

import unittest
import sys
import os
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, MagicMock, patch

# Add pyscript directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import modules to test
from pipeline_config import PipelineConfig, PipelineStep


class TestPipelineConfig(unittest.TestCase):
    """Test PipelineConfig class"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = PipelineConfig()

    def test_default_configuration(self):
        """Test default configuration values"""
        self.assertEqual(self.config.mode, "simple")
        self.assertEqual(self.config.primary_driver, "laxity")
        self.assertFalse(self.config.generate_both)  # Default is False
        self.assertFalse(self.config.overwrite_existing)  # Default is False
        self.assertEqual(self.config.log_level, "INFO")

    def test_simple_preset(self):
        """Test simple mode preset"""
        preset = PipelineConfig.get_simple_preset()

        # Simple mode should have 7 essential steps enabled
        enabled_count = sum(1 for v in preset.values() if v)
        self.assertEqual(enabled_count, 7)

        # Check required steps are enabled
        self.assertTrue(preset["conversion"])
        self.assertTrue(preset["packing"])
        self.assertTrue(preset["validation"])

    def test_advanced_preset(self):
        """Test advanced mode preset"""
        preset = PipelineConfig.get_advanced_preset()

        # Advanced mode should have all 14 steps enabled
        enabled_count = sum(1 for v in preset.values() if v)
        self.assertEqual(enabled_count, 14)

    def test_apply_simple_preset(self):
        """Test applying simple preset"""
        self.config.set_mode("simple")

        self.assertEqual(self.config.mode, "simple")
        enabled_steps = self.config.get_enabled_steps()
        self.assertEqual(len(enabled_steps), 7)

    def test_apply_advanced_preset(self):
        """Test applying advanced preset"""
        self.config.set_mode("advanced")

        self.assertEqual(self.config.mode, "advanced")
        enabled_steps = self.config.get_enabled_steps()
        self.assertEqual(len(enabled_steps), 14)

    def test_get_enabled_steps(self):
        """Test getting list of enabled steps"""
        self.config.set_mode("simple")
        enabled = self.config.get_enabled_steps()

        # Should return list of step IDs
        self.assertIsInstance(enabled, list)
        self.assertIn("conversion", enabled)
        self.assertIn("validation", enabled)

    def test_driver_validation(self):
        """Test driver value validation"""
        # Valid drivers
        valid_drivers = ["laxity", "driver11", "np20"]
        for driver in valid_drivers:
            self.config.primary_driver = driver
            self.assertIn(self.config.primary_driver, valid_drivers)

    def test_mode_validation(self):
        """Test mode value validation"""
        # Valid modes
        valid_modes = ["simple", "advanced", "custom"]
        for mode in valid_modes:
            self.config.mode = mode
            self.assertIn(self.config.mode, valid_modes)

    def test_output_directory_default(self):
        """Test default output directory"""
        self.assertEqual(self.config.output_directory, "output")

    def test_log_level_options(self):
        """Test log level options"""
        valid_levels = ["DEBUG", "INFO", "WARN", "ERROR"]
        for level in valid_levels:
            self.config.log_level = level
            self.assertIn(self.config.log_level, valid_levels)

    def test_validation_duration_options(self):
        """Test validation duration options"""
        valid_durations = [10, 30, 60, 120]  # Integers in seconds
        for duration in valid_durations:
            self.config.validation_duration = duration
            self.assertIn(self.config.validation_duration, valid_durations)


class TestPipelineStep(unittest.TestCase):
    """Test PipelineStep enum"""

    def test_all_steps_exist(self):
        """Test that all 14 steps exist"""
        steps = list(PipelineStep)
        self.assertEqual(len(steps), 14)

    def test_step_properties(self):
        """Test step properties"""
        conversion_step = PipelineStep.CONVERSION

        self.assertEqual(conversion_step.step_id, "conversion")
        self.assertIn("Conversion", conversion_step.description)
        self.assertTrue(conversion_step.default_enabled)

    def test_required_steps(self):
        """Test that required steps are marked as default enabled"""
        # Conversion is the only truly required step
        self.assertTrue(PipelineStep.CONVERSION.default_enabled)

    def test_step_order(self):
        """Test that steps are in logical order"""
        steps = list(PipelineStep)

        # Conversion should be first
        self.assertEqual(steps[0], PipelineStep.CONVERSION)

        # Validation should be near the end
        validation_index = steps.index(PipelineStep.VALIDATION)
        self.assertGreater(validation_index, 10)


class TestConversionExecutorMocked(unittest.TestCase):
    """Test ConversionExecutor with mocked dependencies"""

    def setUp(self):
        """Set up test fixtures"""
        # Create mock config
        self.config = PipelineConfig()
        self.config.set_mode("simple")

        # We'll mock the GUI components since we can't import PyQt6 in tests
        # without it being installed

    @patch('conversion_executor.QProcess')
    def test_step_command_generation_conversion(self, mock_qprocess):
        """Test command generation for conversion step"""
        from conversion_executor import ConversionExecutor

        executor = ConversionExecutor(self.config)

        sid_file = "test.sid"
        command = executor._get_step_command("conversion", sid_file)

        # Should return list with python, script path, input, output, driver
        self.assertIsInstance(command, list)
        self.assertEqual(command[0], "python")
        self.assertIn("sid_to_sf2.py", command[1])
        self.assertIn("--driver", command)
        self.assertIn("laxity", command)

    @patch('conversion_executor.QProcess')
    def test_step_command_generation_siddump(self, mock_qprocess):
        """Test command generation for siddump step"""
        from conversion_executor import ConversionExecutor

        executor = ConversionExecutor(self.config)

        sid_file = "test.sid"
        command = executor._get_step_command("siddump_original", sid_file)

        # Should return list with siddump.exe path and arguments
        self.assertIsInstance(command, list)
        self.assertIn("siddump.exe", command[0])
        self.assertEqual(command[1], sid_file)
        self.assertEqual(command[2], "-t30")

    @patch('conversion_executor.QProcess')
    def test_output_file_generation(self, mock_qprocess):
        """Test output file path generation"""
        from conversion_executor import ConversionExecutor

        executor = ConversionExecutor(self.config)

        sid_file = "test.sid"

        # Test dump file generation
        output_file = executor._get_output_file_for_step("siddump_original", sid_file)
        self.assertIsNotNone(output_file)
        self.assertIn("test_original.dump", output_file)

        # Test trace file generation
        output_file = executor._get_output_file_for_step("sidwinder_trace", sid_file)
        self.assertIsNotNone(output_file)
        self.assertIn("analysis", output_file)
        self.assertIn("test_trace.txt", output_file)

    @patch('conversion_executor.QProcess')
    def test_collect_results_structure(self, mock_qprocess):
        """Test result collection structure"""
        from conversion_executor import ConversionExecutor, FileResult

        executor = ConversionExecutor(self.config)

        # Create a mock result
        result = FileResult(
            filename="test.sid",
            driver="laxity",
            steps_completed=7,
            total_steps=7,
            accuracy=99.93,
            status="passed",
            error_message="",
            start_time=100.0,
            end_time=110.5
        )

        # Verify structure
        self.assertEqual(result.filename, "test.sid")
        self.assertEqual(result.driver, "laxity")
        self.assertEqual(result.steps_completed, 7)
        self.assertEqual(result.accuracy, 99.93)
        self.assertEqual(result.status, "passed")
        self.assertEqual(result.error_message, "")

        # Verify duration calculation
        duration = result.end_time - result.start_time
        self.assertAlmostEqual(duration, 10.5, places=1)


class TestCockpitWidgetsLogic(unittest.TestCase):
    """Test custom widget logic (non-GUI parts)"""

    def test_stats_card_data_structure(self):
        """Test stats card data structure"""
        # Test the data structure used by StatsCard
        stats = [
            ("Total", "25"),
            ("Selected", "20"),
            ("Estimated", "10.5 minutes")
        ]

        # Verify structure
        self.assertEqual(len(stats), 3)
        self.assertIsInstance(stats[0], tuple)
        self.assertEqual(stats[0][0], "Total")
        self.assertEqual(stats[0][1], "25")

    def test_log_colors_mapping(self):
        """Test log color mapping"""
        # This tests the COLORS dict from LogStreamWidget
        COLORS = {
            "ERROR": "#d32f2f",
            "WARN": "#f57c00",
            "INFO": "#333333",
            "DEBUG": "#0288d1"
        }

        # Verify all levels have colors
        self.assertIn("ERROR", COLORS)
        self.assertIn("WARN", COLORS)
        self.assertIn("INFO", COLORS)
        self.assertIn("DEBUG", COLORS)

        # Verify colors are hex format
        for color in COLORS.values():
            self.assertTrue(color.startswith("#"))
            self.assertEqual(len(color), 7)

    def test_status_badge_styles(self):
        """Test status badge styles"""
        # This tests the BADGE_STYLES dict from StatusBadge
        BADGE_STYLES = {
            "pending": ("⏳", "#9e9e9e", "Pending"),
            "running": ("⏳", "#2196F3", "Running"),
            "passed": ("✅", "#4CAF50", "Passed"),
            "failed": ("❌", "#f44336", "Failed"),
            "warning": ("⚠️", "#FF9800", "Warning")
        }

        # Verify all statuses exist
        self.assertIn("pending", BADGE_STYLES)
        self.assertIn("running", BADGE_STYLES)
        self.assertIn("passed", BADGE_STYLES)
        self.assertIn("failed", BADGE_STYLES)
        self.assertIn("warning", BADGE_STYLES)

        # Verify structure (icon, color, text)
        for status, (icon, color, text) in BADGE_STYLES.items():
            self.assertIsInstance(icon, str)
            self.assertTrue(color.startswith("#"))
            self.assertIsInstance(text, str)


class TestFilePathGeneration(unittest.TestCase):
    """Test file path generation logic"""

    def test_output_directory_structure(self):
        """Test output directory structure"""
        base_name = "test_song"
        output_dir = Path("output") / base_name / "New"
        analysis_dir = output_dir / "analysis"

        # Verify structure
        self.assertEqual(output_dir.parts[-1], "New")
        self.assertEqual(output_dir.parts[-2], "test_song")
        self.assertEqual(analysis_dir.parts[-1], "analysis")

    def test_output_file_naming(self):
        """Test output file naming conventions"""
        base_name = "test_song"

        # Test various output file names
        original_dump = f"{base_name}_original.dump"
        exported_dump = f"{base_name}_exported.dump"
        trace_file = f"{base_name}_trace.txt"

        self.assertTrue(original_dump.endswith(".dump"))
        self.assertTrue(exported_dump.endswith(".dump"))
        self.assertTrue(trace_file.endswith(".txt"))

        self.assertIn("original", original_dump)
        self.assertIn("exported", exported_dump)
        self.assertIn("trace", trace_file)


class TestConfigurationPersistence(unittest.TestCase):
    """Test configuration save/load logic"""

    def test_config_to_dict(self):
        """Test configuration serialization to dict"""
        config = PipelineConfig()
        config.primary_driver = "laxity"
        config.mode = "advanced"

        # Test that config can be represented as dict
        config_dict = {
            "mode": config.mode,
            "primary_driver": config.primary_driver,
            "generate_both": config.generate_both,
            "output_directory": config.output_directory,
            "overwrite_existing": config.overwrite_existing,
            "log_level": config.log_level,
        }

        self.assertEqual(config_dict["mode"], "advanced")
        self.assertEqual(config_dict["primary_driver"], "laxity")

    def test_preset_switching(self):
        """Test switching between presets"""
        config = PipelineConfig()

        # Start with simple
        config.set_mode("simple")
        simple_steps = len(config.get_enabled_steps())

        # Switch to advanced
        config.set_mode("advanced")
        advanced_steps = len(config.get_enabled_steps())

        # Advanced should have more steps
        self.assertGreater(advanced_steps, simple_steps)
        self.assertEqual(advanced_steps, 14)
        self.assertEqual(simple_steps, 7)


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPipelineConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestPipelineStep))
    suite.addTests(loader.loadTestsFromTestCase(TestConversionExecutorMocked))
    suite.addTests(loader.loadTestsFromTestCase(TestCockpitWidgetsLogic))
    suite.addTests(loader.loadTestsFromTestCase(TestFilePathGeneration))
    suite.addTests(loader.loadTestsFromTestCase(TestConfigurationPersistence))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())

# ---------------------------------------------------------------------------
# PipelineConfig serialisation must be TOTAL.
#
# to_dict() hand-listed 15 of the dataclass's 16 fields and omitted
# concurrent_workers. from_dict is cls(**data), so the absent key did not
# raise -- the field just reverted to its default. That made the loss
# INVISIBLE whenever the value happened to equal the default, which is why a
# round trip checked at defaults reported success while dropping data.
# save_to_settings iterates to_dict().items(), so QSettings lost it too.
#
# The first test is the one that matters: it fails for a field that does not
# exist yet, so the next field added to PipelineConfig cannot be dropped the
# same silent way.
# ---------------------------------------------------------------------------

class TestPipelineConfigSerialisationIsTotal(unittest.TestCase):

    def test_to_dict_exports_every_dataclass_field(self):
        """THE MECHANISM GUARD. Not 'concurrent_workers is present' -- that
        would pass again the moment someone adds a seventeenth field."""
        import dataclasses
        cfg = PipelineConfig()
        fields = {f.name for f in dataclasses.fields(cfg)}
        exported = set(cfg.to_dict())
        self.assertEqual(fields - exported, set(),
                         "to_dict() drops dataclass field(s); from_dict is "
                         "cls(**data) so they revert to defaults SILENTLY")
        self.assertEqual(exported - fields, set(),
                         "to_dict() exports a key that is not a field; "
                         "from_dict would raise TypeError on it")

    def test_round_trip_at_NON_DEFAULT_values(self):
        """A round trip verified at DEFAULTS is vacuous -- the dropped field
        equalled its default, so nothing differed. Every field is moved off
        its default here before the trip."""
        import dataclasses
        import json
        cfg = PipelineConfig()
        for f in dataclasses.fields(cfg):
            cur = getattr(cfg, f.name)
            if isinstance(cur, bool):
                setattr(cfg, f.name, not cur)
            elif isinstance(cur, int):
                setattr(cfg, f.name, cur + 7)
            elif isinstance(cur, str):
                setattr(cfg, f.name, cur + "_x")
            elif isinstance(cur, dict):
                setattr(cfg, f.name, {"conversion": True, "sentinel": False})

        back = PipelineConfig.from_dict(json.loads(json.dumps(cfg.to_dict())))
        for f in dataclasses.fields(cfg):
            self.assertEqual(getattr(back, f.name), getattr(cfg, f.name),
                             "field %r did not survive the round trip" % f.name)

    def test_concurrent_workers_specifically(self):
        """The field that was actually lost, pinned by name as well as by the
        general rule -- a regression here should say WHICH field."""
        import json
        cfg = PipelineConfig()
        cfg.concurrent_workers = 8
        blob = json.dumps(cfg.to_dict())
        self.assertIn("concurrent_workers", json.loads(blob))
        self.assertEqual(PipelineConfig.from_dict(json.loads(blob)).concurrent_workers, 8)

# ---------------------------------------------------------------------------
# CC-7: exporting and importing a configuration file.
#
# The serialisation these rest on is `to_dict` == dataclasses.asdict, TOTAL by
# construction. That is load-bearing for an EXPORT specifically: the file is
# what a user carries between machines, so a field missing from it is a setting
# lost at the far end with nothing to notice it.
#
# Every round trip below moves fields OFF their defaults first. A round trip
# checked at defaults is vacuous -- to_dict dropped concurrent_workers for
# months and the check still reported "nothing differs", because the value it
# lost equalled the default it reverted to.
# ---------------------------------------------------------------------------

class TestConfigExportImport(unittest.TestCase):

    @staticmethod
    def _off_defaults():
        import dataclasses
        cfg = PipelineConfig()
        for f in dataclasses.fields(cfg):
            cur = getattr(cfg, f.name)
            if isinstance(cur, bool):
                setattr(cfg, f.name, not cur)
            elif isinstance(cur, int):
                setattr(cfg, f.name, cur + 13)
            elif isinstance(cur, str):
                setattr(cfg, f.name, cur + "_exported")
            elif isinstance(cur, dict):
                setattr(cfg, f.name, {"conversion": True, "marker": False})
        return cfg

    def test_every_field_survives_an_export_import_round_trip(self):
        import dataclasses
        cfg = self._off_defaults()
        back = PipelineConfig.from_json_text(cfg.to_json_text())
        for f in dataclasses.fields(cfg):
            self.assertEqual(getattr(back, f.name), getattr(cfg, f.name),
                             "field %r did not survive export/import" % f.name)

    def test_a_full_export_defaults_nothing(self):
        """If this ever reports a field, the export is incomplete -- which is
        the defect, not a curiosity."""
        cfg = self._off_defaults()
        self.assertEqual(PipelineConfig.defaulted_fields(cfg.to_json_text()), [])

    def test_an_unknown_key_is_REFUSED_and_named(self):
        """cls(**data) would raise a bare TypeError; ignoring it would drop a
        setting the file plainly asks for. Neither is acceptable."""
        import json
        blob = json.dumps({"mode": "simple", "not_a_real_setting": 1})
        with self.assertRaises(Exception) as ctx:
            PipelineConfig.from_json_text(blob)
        self.assertIn("not_a_real_setting", str(ctx.exception))

    def test_malformed_and_non_object_json_are_refused(self):
        for blob in ("{oops", "[1, 2]", '"a string"', "null"):
            with self.assertRaises(Exception):
                PipelineConfig.from_json_text(blob)

    def test_a_PARTIAL_file_loads_and_says_what_it_defaulted(self):
        """Deliberate asymmetry: missing keys are accepted so an older export
        still loads, but the caller can tell the user which fell back."""
        import json
        blob = json.dumps({"mode": "advanced"})
        cfg = PipelineConfig.from_json_text(blob)
        self.assertEqual(cfg.mode, "advanced")
        defaulted = PipelineConfig.defaulted_fields(blob)
        self.assertIn("concurrent_workers", defaulted)
        self.assertNotIn("mode", defaulted)

    def test_exported_text_is_stable_and_readable(self):
        """sort_keys + indent, so two exports of the same config diff cleanly
        and a human can edit one by hand."""
        cfg = self._off_defaults()
        a, b = cfg.to_json_text(), cfg.to_json_text()
        self.assertEqual(a, b)
        self.assertIn(chr(10), a)
        # TOP-LEVEL keys only -- enabled_steps is a nested dict whose inner
        # keys are also quoted lines, and they have no reason to be sorted
        # against the outer ones.
        keys = [ln.split('"')[1] for ln in a.splitlines()
                if ln.startswith('  "')]
        self.assertEqual(keys, sorted(keys), "keys should be sorted")
