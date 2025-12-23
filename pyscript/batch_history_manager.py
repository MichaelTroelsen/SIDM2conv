#!/usr/bin/env python3
"""
Batch History Manager - Manages conversion batch history (last 10 batches)

Saves and loads batch configurations with timestamps, allowing users to
quickly recall and reuse previous conversion setups.

Version: 1.0.0
Date: 2025-12-23
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from pipeline_config import PipelineConfig


@dataclass
class BatchHistoryEntry:
    """Single batch history entry"""
    id: str  # Unique ID (timestamp-based: YYYYMMDD_HHMMSS)
    timestamp: str  # ISO format timestamp
    label: str  # User-friendly label (e.g., "Laxity Batch - 12/23")
    file_count: int  # Number of files in batch
    config: Dict[str, Any]  # Serialized PipelineConfig

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'label': self.label,
            'file_count': self.file_count,
            'config': self.config
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchHistoryEntry':
        """Create from dictionary (JSON deserialization)"""
        return cls(
            id=data['id'],
            timestamp=data['timestamp'],
            label=data['label'],
            file_count=data['file_count'],
            config=data['config']
        )


class BatchHistoryManager:
    """Manages batch history persistence and retrieval"""

    # Maximum number of batch entries to keep
    MAX_HISTORY = 10

    # History file location
    HISTORY_FILE = Path.home() / '.sidm2' / 'batch_history.json'

    def __init__(self):
        """Initialize history manager"""
        self.history_file = self.HISTORY_FILE
        self.entries: List[BatchHistoryEntry] = []
        self._ensure_history_dir()
        self.load_history()

    def _ensure_history_dir(self):
        """Ensure history directory exists"""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def _generate_id(self) -> str:
        """Generate unique ID from current timestamp"""
        return datetime.now().strftime('%Y%m%d_%H%M%S')

    def save_batch(self, config: PipelineConfig, file_count: int, label: Optional[str] = None) -> BatchHistoryEntry:
        """
        Save a batch configuration to history.

        Args:
            config: PipelineConfig object
            file_count: Number of files in this batch
            label: Optional user-friendly label

        Returns:
            BatchHistoryEntry that was saved
        """
        # Generate label if not provided
        if not label:
            mode = config.mode.capitalize()
            driver = config.primary_driver.capitalize()
            date_str = datetime.now().strftime('%m/%d')
            label = f"{driver} {mode} - {date_str}"

        # Create entry
        entry = BatchHistoryEntry(
            id=self._generate_id(),
            timestamp=datetime.now().isoformat(),
            label=label,
            file_count=file_count,
            config=self._serialize_config(config)
        )

        # Add to beginning of list (most recent first)
        self.entries.insert(0, entry)

        # Keep only MAX_HISTORY entries
        if len(self.entries) > self.MAX_HISTORY:
            self.entries = self.entries[:self.MAX_HISTORY]

        # Save to file
        self._write_history_file()

        return entry

    def load_history(self) -> List[BatchHistoryEntry]:
        """Load batch history from file"""
        if not self.history_file.exists():
            self.entries = []
            return []

        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.entries = [BatchHistoryEntry.from_dict(item) for item in data]
            return self.entries
        except Exception as e:
            print(f"Error loading batch history: {e}")
            self.entries = []
            return []

    def get_history(self) -> List[BatchHistoryEntry]:
        """Get all history entries (most recent first)"""
        return self.entries

    def get_entry(self, entry_id: str) -> Optional[BatchHistoryEntry]:
        """Get a specific history entry by ID"""
        for entry in self.entries:
            if entry.id == entry_id:
                return entry
        return None

    def delete_entry(self, entry_id: str) -> bool:
        """Delete a history entry"""
        original_len = len(self.entries)
        self.entries = [e for e in self.entries if e.id != entry_id]

        if len(self.entries) < original_len:
            self._write_history_file()
            return True
        return False

    def clear_history(self) -> None:
        """Clear all history entries"""
        self.entries = []
        self._write_history_file()

    def restore_config(self, entry_id: str) -> Optional[PipelineConfig]:
        """
        Restore a PipelineConfig from history.

        Args:
            entry_id: ID of the history entry to restore

        Returns:
            PipelineConfig if found, None otherwise
        """
        entry = self.get_entry(entry_id)
        if not entry:
            return None

        return self._deserialize_config(entry.config)

    def _serialize_config(self, config: PipelineConfig) -> Dict[str, Any]:
        """Convert PipelineConfig to dictionary"""
        # Convert to dict via dataclass asdict()
        config_dict = asdict(config)

        # Convert enabled_steps to serializable format
        config_dict['enabled_steps'] = dict(config_dict['enabled_steps'])

        return config_dict

    def _deserialize_config(self, config_dict: Dict[str, Any]) -> PipelineConfig:
        """Convert dictionary back to PipelineConfig"""
        # Create config with the stored data
        config = PipelineConfig(
            mode=config_dict.get('mode', 'simple'),
            primary_driver=config_dict.get('primary_driver', 'laxity'),
            generate_both=config_dict.get('generate_both', False),
            output_directory=config_dict.get('output_directory', 'output'),
            overwrite_existing=config_dict.get('overwrite_existing', False),
            create_nested_dirs=config_dict.get('create_nested_dirs', True),
            log_level=config_dict.get('log_level', 'INFO'),
            log_to_file=config_dict.get('log_to_file', False),
            log_file_path=config_dict.get('log_file_path', ''),
            log_json_format=config_dict.get('log_json_format', False),
            validation_duration=config_dict.get('validation_duration', 30),
            run_accuracy_validation=config_dict.get('run_accuracy_validation', True),
            stop_on_error=config_dict.get('stop_on_error', False),
            step_timeout_ms=config_dict.get('step_timeout_ms', 120000),
            concurrent_workers=config_dict.get('concurrent_workers', 2),
        )

        # Restore enabled_steps
        config.enabled_steps = config_dict.get('enabled_steps', {})

        return config

    def _write_history_file(self) -> None:
        """Write history to file"""
        try:
            data = [entry.to_dict() for entry in self.entries]
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error writing batch history: {e}")

    def format_entry_display(self, entry: BatchHistoryEntry) -> str:
        """Format entry for display in UI"""
        # Parse timestamp to get a readable time
        try:
            ts = datetime.fromisoformat(entry.timestamp)
            time_str = ts.strftime('%H:%M')
            date_str = ts.strftime('%m/%d')
        except:
            time_str = "??:??"
            date_str = "??/??"

        return f"{entry.label} ({entry.file_count} files, {date_str} {time_str})"


def main():
    """Test the batch history manager"""
    print("Batch History Manager Test")
    print("=" * 70)

    # Create manager
    manager = BatchHistoryManager()

    # Create a test config
    config = PipelineConfig()
    config.mode = "simple"
    config.primary_driver = "laxity"

    # Save a test batch
    print("\nSaving test batch...")
    entry = manager.save_batch(config, file_count=5, label="Test Batch 1")
    print(f"Saved: {manager.format_entry_display(entry)}")

    # Load and display history
    print("\nCurrent history:")
    for entry in manager.get_history():
        print(f"  - {manager.format_entry_display(entry)}")

    # Restore config
    print("\nRestoring config from history...")
    restored = manager.restore_config(entry.id)
    if restored:
        print(f"  Mode: {restored.mode}")
        print(f"  Driver: {restored.primary_driver}")
        print(f"  Output: {restored.output_directory}")

    print("\n" + "=" * 70)
    print(f"History file: {manager.history_file}")
    print(f"Total entries: {len(manager.entries)}")


if __name__ == '__main__':
    main()
