#!/usr/bin/env python3
"""
Pipeline Configuration - Configuration management for conversion pipeline

Manages pipeline step configuration, presets, and persistence.

Version: 1.0.0
Date: 2025-12-22
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional
from pathlib import Path


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
            raise ValueError(f"Invalid mode: {mode}")

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
        """Convert config to dictionary for serialization"""
        return {
            "mode": self.mode,
            "primary_driver": self.primary_driver,
            "generate_both": self.generate_both,
            "output_directory": self.output_directory,
            "overwrite_existing": self.overwrite_existing,
            "create_nested_dirs": self.create_nested_dirs,
            "enabled_steps": self.enabled_steps,
            "log_level": self.log_level,
            "log_to_file": self.log_to_file,
            "log_file_path": self.log_file_path,
            "log_json_format": self.log_json_format,
            "validation_duration": self.validation_duration,
            "run_accuracy_validation": self.run_accuracy_validation,
            "stop_on_error": self.stop_on_error,
            "step_timeout_ms": self.step_timeout_ms
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "PipelineConfig":
        """Create config from dictionary"""
        return cls(**data)

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
