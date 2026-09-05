#!/usr/bin/env python3
"""
Pipeline Configuration - Configuration management for conversion pipeline

Manages pipeline step configuration, presets, and persistence.

Version: 1.0.0
Date: 2025-12-22
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from sidm2.errors import ConfigurationError


class PipelineStep(Enum):
    """Available pipeline steps"""
    CONVERSION = ("conversion", "SID → SF2 Conversion", True)  # Required
    SIDDUMP_ORIGINAL = ("siddump_original", "Siddump (Original)", False)
    SIDDECOMPILER = ("siddecompiler", "SIDdecompiler Analysis", False)
    PACKING = ("packing", "SF2 → SID Packing", True)  # Recommended
    SIDDUMP_EXPORTED = ("siddump_exported", "Siddump (Exported)", False)
    WAV_ORIGINAL = ("wav_original", "WAV Rendering (Original)", False)
    WAV_EXPORTED = ("wav_exported", "WAV Rendering (Exported)", False)
    HEXDUMP = ("hexdump", "Hexdump Generation", False)
    SIDWINDER_TRACE = ("sidwinder_trace", "SIDwinder Trace", False)
    INFO_REPORT = ("info_report", "Info.txt Report", True)  # Recommended
    ANNOTATED_DISASSEMBLY = ("annotated_disasm", "Annotated Disassembly", False)
    SIDWINDER_DISASSEMBLY = ("sidwinder_disasm", "SIDwinder Disassembly", False)
    VALIDATION = ("validation", "File Validation", True)  # Recommended
    MIDI_COMPARISON = ("midi_comparison", "MIDI Comparison", False)

    def __init__(self, step_id: str, description: str, default_enabled: bool):
        self.step_id = step_id
        self.description = description
        self.default_enabled = default_enabled


@dataclass
class PipelineConfig:
    """Configuration for conversion pipeline"""

    # Mode
    mode: str = "simple"  # simple, advanced, custom

    # Driver configuration
    primary_driver: str = "laxity"  # laxity, driver11, np20
    generate_both: bool = False  # Generate both NP20 and Driver 11

    # Output configuration
    output_directory: str = "output"
    overwrite_existing: bool = False
    create_nested_dirs: bool = True

    # Pipeline steps (step_id: enabled)
    enabled_steps: Dict[str, bool] = field(default_factory=dict)

    # Logging configuration
    log_level: str = "INFO"  # ERROR, WARN, INFO, DEBUG
    log_to_file: bool = False
    log_file_path: str = ""
    log_json_format: bool = False

    # Validation configuration
    validation_duration: int = 30  # seconds
    run_accuracy_validation: bool = True

    # Execution configuration
    stop_on_error: bool = False
    step_timeout_ms: int = 120000  # 2 minutes per step
    concurrent_workers: int = 2  # Number of files to process simultaneously (1-4)

    def __post_init__(self):
        """Initialize enabled steps if not provided"""
        if not self.enabled_steps:
            self._apply_mode_preset()

    def _apply_mode_preset(self):
        """Apply preset based on mode"""
        if self.mode == "simple":
            self.enabled_steps = self.get_simple_preset()
        elif self.mode == "advanced":
            self.enabled_steps = self.get_advanced_preset()
        else:  # custom
            # Use defaults from enum
            self.enabled_steps = {
                step.step_id: step.default_enabled
                for step in PipelineStep
            }

    def get_enabled_steps(self) -> List[str]:
        """Get list of enabled step IDs in execution order"""
        return [
            step_id
            for step_id, enabled in self.enabled_steps.items()
            if enabled
        ]

    @staticmethod
    def get_simple_preset() -> Dict[str, bool]:
        """Simple mode: Essential steps only"""
        return {
            "conversion": True,
            "siddump_original": False,
            "siddecompiler": False,
            "packing": True,
            "siddump_exported": True,
            "wav_original": True,
            "wav_exported": True,
            "hexdump": False,
            "sidwinder_trace": False,
            "info_report": True,
            "annotated_disasm": False,
            "sidwinder_disasm": False,
            "validation": True,
            "midi_comparison": False
        }

    @staticmethod
    def get_advanced_preset() -> Dict[str, bool]:
        """Advanced mode: All 13 steps enabled"""
        return {
            step.step_id: True
            for step in PipelineStep
        }

    def set_mode(self, mode: str):
        """Change mode and apply corresponding preset"""
        if mode not in ["simple", "advanced", "custom"]:
            raise ConfigurationError(
                setting='pipeline_mode',
                value=mode,
                valid_options=['simple', 'advanced', 'custom'],
                example='mode: simple',
                docs_link='guides/TROUBLESHOOTING.md#pipeline-configuration'
            )

        self.mode = mode
        if mode != "custom":
            self._apply_mode_preset()

    def enable_step(self, step_id: str):
        """Enable a specific pipeline step"""
        if step_id in self.enabled_steps:
            self.enabled_steps[step_id] = True
            if self.mode != "custom":
                self.mode = "custom"  # Switch to custom mode

    def disable_step(self, step_id: str):
        """Disable a specific pipeline step"""
        if step_id in self.enabled_steps:
            self.enabled_steps[step_id] = False
            if self.mode != "custom":
                self.mode = "custom"  # Switch to custom mode

    def to_dict(self) -> Dict:
        """Every field, by construction -- NOT a hand-written list.

        THIS USED TO HAND-LIST 15 OF 16 FIELDS and silently omitted
        `concurrent_workers`. Because `from_dict` is `cls(**data)`, the missing
        key did not raise: it simply fell back to the default, so exporting a
        config with concurrent_workers=8 and re-importing it returned 2. The
        loss was invisible at the default value, which is why a round trip
        checked with defaults reported "no fields differ" while dropping data.

        IT WAS NEVER JUST AN IMPORT/EXPORT BUG. `save_to_settings` iterates
        `self.to_dict().items()`, so QSettings persisted the same 15 keys and
        the cockpit forgot the user's worker count between sessions.

        `asdict` is used rather than adding the sixteenth key BECAUSE THE
        MECHANISM WAS THE DEFECT: a hand-written list drops the NEXT field
        added to the dataclass in exactly the same silent way. This cannot.
        `test_to_dict_exports_every_dataclass_field` fails if anyone reverts it.

        One deliberate behaviour change: `asdict` deep-copies, so the returned
        `enabled_steps` is no longer the live dict. The only caller that takes
        it (`ConfigPanel.set_config`, via conversion_cockpit_gui) reads keys
        with `.get()` and never mutates, so nothing depended on the alias.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "PipelineConfig":
        """Create config from dictionary"""
        return cls(**data)

    def to_json_text(self, indent: int = 2) -> str:
        """This config as pretty JSON, ready to write to a file.

        Built on `to_dict`, which is `dataclasses.asdict` and therefore TOTAL --
        every field is exported by construction. That matters here more than
        anywhere else: an exported file is the thing a user carries between
        machines, so a field missing from it is a setting silently lost at the
        far end, with nothing to notice it. (to_dict hand-listed 15 of 16 fields
        until 2026-09-04 and dropped `concurrent_workers` exactly that way.)
        """
        import json
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json_text(cls, text: str) -> "PipelineConfig":
        """Parse an exported config, REFUSING anything it cannot honour.

        Three refusals, and each exists because the silent alternative loses a
        user's setting without telling them:

        * not a JSON object -> there is no config here at all;
        * an UNKNOWN key -> `cls(**data)` would raise a bare TypeError naming
          one key with no context; worse, ignoring it would drop a setting the
          file plainly asks for. Named explicitly instead.
        * a field of the wrong TYPE is left to the dataclass -- this does not
          coerce, because guessing that "8" meant 8 is how a config import
          starts inventing values.

        MISSING keys are ACCEPTED and take their defaults. That is deliberate
        and is the one asymmetry: an older export should still load, and a
        default is a defined value rather than a guess. Callers that need to
        know use `defaulted_fields`.
        """
        import dataclasses
        import json

        try:
            data = json.loads(text)
        except ValueError as exc:
            raise ConfigurationError(
                setting='config_file',
                value=str(exc),
                example='{"mode": "simple", "primary_driver": "laxity"}',
                docs_link='guides/CONVERSION_COCKPIT_USER_GUIDE.md'
            ) from exc

        if not isinstance(data, dict):
            raise ConfigurationError(
                setting='config_file',
                value=type(data).__name__,
                valid_options=['a JSON object'],
                example='{"mode": "simple"}',
                docs_link='guides/CONVERSION_COCKPIT_USER_GUIDE.md'
            )

        known = {f.name for f in dataclasses.fields(cls)}
        unknown = sorted(set(data) - known)
        if unknown:
            raise ConfigurationError(
                setting='config_file',
                value=', '.join(unknown),
                valid_options=sorted(known),
                example='remove the unrecognised key, or upgrade SIDM2',
                docs_link='guides/CONVERSION_COCKPIT_USER_GUIDE.md'
            )

        return cls.from_dict(data)

    @classmethod
    def defaulted_fields(cls, text: str) -> List[str]:
        """Which fields an exported config does NOT mention, so a caller can
        tell the user what fell back to a default rather than leaving them to
        discover it in the behaviour."""
        import dataclasses
        import json
        try:
            data = json.loads(text)
        except ValueError:
            return []
        if not isinstance(data, dict):
            return []
        return sorted({f.name for f in dataclasses.fields(cls)} - set(data))

    def save_to_settings(self, settings):
        """Save configuration to QSettings"""
        settings.beginGroup("Pipeline")
        for key, value in self.to_dict().items():
            if isinstance(value, dict):
                # Save dict as JSON string
                import json
                settings.setValue(key, json.dumps(value))
            else:
                settings.setValue(key, value)
        settings.endGroup()

    @classmethod
    def load_from_settings(cls, settings) -> "PipelineConfig":
        """Load configuration from QSettings"""
        import json

        settings.beginGroup("Pipeline")
        keys = settings.allKeys()

        data = {}
        for key in keys:
            value = settings.value(key)
            # Try to parse as JSON if it looks like a dict
            if isinstance(value, str) and value.startswith('{'):
                try:
                    value = json.loads(value)
                except:
                    pass
            data[key] = value

        settings.endGroup()

        # Return default config if no saved config
        if not data:
            return cls()

        return cls.from_dict(data)

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of warnings/errors.
        Returns empty list if configuration is valid.
        """
        warnings = []

        # Check required steps
        if not self.enabled_steps.get("conversion"):
            warnings.append("ERROR: Conversion step is required")

        # Check output directory
        if not self.output_directory:
            warnings.append("WARN: Output directory not set, using 'output'")
            self.output_directory = "output"

        # Check for dependency issues
        if self.enabled_steps.get("validation") and not self.enabled_steps.get("packing"):
            warnings.append("WARN: Validation requires packing step")

        if self.enabled_steps.get("midi_comparison") and not self.enabled_steps.get("packing"):
            warnings.append("WARN: MIDI comparison requires packing step")

        # Check log file path if logging enabled
        if self.log_to_file and not self.log_file_path:
            warnings.append("WARN: Log to file enabled but no path specified")

        # Check timeout
        if self.step_timeout_ms < 10000:
            warnings.append("WARN: Step timeout is very short (<10s)")

        return warnings

    def get_description(self) -> str:
        """Get human-readable description of configuration"""
        enabled_count = sum(1 for enabled in self.enabled_steps.values() if enabled)
        total_count = len(self.enabled_steps)

        mode_desc = {
            "simple": "Simple Mode (Essential steps)",
            "advanced": "Advanced Mode (All steps)",
            "custom": "Custom Mode"
        }

        return f"{mode_desc.get(self.mode, 'Unknown')} - {enabled_count}/{total_count} steps enabled"
