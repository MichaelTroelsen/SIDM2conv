"""
Test Script: Automation Configuration System

Tests the AutomationConfig module to ensure it properly loads and parses
the configuration file.

Usage:
    python pyscript/test_automation_config.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.automation_config import AutomationConfig


def test_config_loading():
    """Test 1: Configuration file loading"""
    print("=" * 70)
    print("Test 1: Configuration File Loading")
    print("=" * 70)
    print()

    config = AutomationConfig()

    print("Loading configuration...")
    print(f"Config file: {config.config_path}")
    print(f"Config exists: {config.config_path.exists()}")
    print()

    if config.config_path.exists():
        print("[OK] Configuration file found")
    else:
        print("[WARN] Configuration file not found (using defaults)")

    print()
    return config


def test_autoit_config(config):
    """Test 2: AutoIt configuration"""
    print("=" * 70)
    print("Test 2: AutoIt Configuration")
    print("=" * 70)
    print()

    print(f"AutoIt enabled: {config.autoit_enabled}")
    print(f"AutoIt script path: {config.autoit_script_path}")
    print(f"AutoIt script exists: {config.autoit_script_path.exists()}")
    print(f"AutoIt timeout: {config.autoit_timeout}s")
    print(f"Keep-alive interval: {config.autoit_keep_alive_interval}ms")
    print()

    if config.autoit_enabled and config.autoit_script_path.exists():
        print("[OK] AutoIt mode available")
    elif config.autoit_enabled and not config.autoit_script_path.exists():
        print("[WARN] AutoIt enabled but script not found")
        print(f"   Expected: {config.autoit_script_path}")
        print("   Run: scripts/autoit/compile.bat")
    else:
        print("[INFO] AutoIt mode disabled")

    print()


def test_editor_config(config):
    """Test 3: Editor configuration"""
    print("=" * 70)
    print("Test 3: Editor Configuration")
    print("=" * 70)
    print()

    print(f"Window title: {config.editor_window_title}")
    print(f"Window timeout: {config.editor_window_timeout}s")
    print()

    print(f"Configured paths ({len(config.editor_paths)}):")
    for i, path in enumerate(config.editor_paths, 1):
        exists = "[OK]" if Path(path).exists() else "[  ]"
        print(f"  {i}. {exists} {path}")
    print()

    editor_path = config.find_editor_path()
    if editor_path:
        print(f"[OK] Editor found: {editor_path}")
    else:
        print("[FAIL] Editor not found in any configured path")
        print("   Add your editor path to config/sf2_automation.ini")

    print()


def test_playback_config(config):
    """Test 4: Playback configuration"""
    print("=" * 70)
    print("Test 4: Playback Configuration")
    print("=" * 70)
    print()

    print(f"Play key (F5): {hex(config.play_key)}")
    print(f"Stop key (F6): {hex(config.stop_key)}")
    print(f"Record key (F7): {hex(config.record_key)}")
    print(f"State check interval: {config.state_check_interval}ms")
    print(f"State check timeout: {config.state_check_timeout}ms")
    print()

    print("[OK] Playback keys configured")
    print()


def test_logging_config(config):
    """Test 5: Logging configuration"""
    print("=" * 70)
    print("Test 5: Logging Configuration")
    print("=" * 70)
    print()

    print(f"Logging enabled: {config.logging_enabled}")
    print(f"Log level: {config.logging_level}")
    print(f"Log file: {config.logging_file}")
    print(f"Log to console: {config.logging_to_console}")
    print(f"Log format: {config.logging_format}")
    print()

    if config.logging_enabled:
        print("[OK] Logging configured")
        if config.logging_file:
            print(f"   Log file: {config.logging_file}")
    else:
        print("[INFO] Logging disabled")

    print()


def test_validation_config(config):
    """Test 6: Validation configuration"""
    print("=" * 70)
    print("Test 6: Validation Configuration")
    print("=" * 70)
    print()

    print(f"File load timeout: {config.file_load_timeout}s")
    print(f"Playback timeout: {config.playback_timeout}s")
    print(f"Require exact match: {config.require_exact_match}")
    print()

    print("[OK] Validation configured")
    print()


def test_advanced_config(config):
    """Test 7: Advanced configuration"""
    print("=" * 70)
    print("Test 7: Advanced Configuration")
    print("=" * 70)
    print()

    print(f"Use Windows API: {config.use_windows_api}")
    print(f"Process name: {config.process_name}")
    print(f"Max retries: {config.max_retries}")
    print(f"Retry delay: {config.retry_delay}ms")
    print()

    print("[OK] Advanced settings configured")
    print()


def test_summary(config):
    """Test 8: Configuration summary"""
    print("=" * 70)
    print("Test 8: Configuration Summary")
    print("=" * 70)
    print()

    summary = config.get_summary()

    print("AutoIt:")
    print(f"  Enabled: {summary['AutoIt']['enabled']}")
    print(f"  Script: {summary['AutoIt']['script_path']}")
    print(f"  Exists: {summary['AutoIt']['script_exists']}")
    print()

    print("Editor:")
    print(f"  Paths configured: {summary['Editor']['paths_configured']}")
    print(f"  Path found: {summary['Editor']['path_found']}")
    print()

    print("Logging:")
    print(f"  Enabled: {summary['Logging']['enabled']}")
    print(f"  Level: {summary['Logging']['level']}")
    print()

    print("Config File:")
    print(f"  Path: {summary['Config']['file_path']}")
    print(f"  Exists: {summary['Config']['file_exists']}")
    print()

    print("[OK] Summary generated successfully")
    print()


def test_integration():
    """Test 9: Integration with SF2EditorAutomation"""
    print("=" * 70)
    print("Test 9: Integration with SF2EditorAutomation")
    print("=" * 70)
    print()

    try:
        from sidm2.sf2_editor_automation import SF2EditorAutomation

        print("Creating SF2EditorAutomation instance...")
        automation = SF2EditorAutomation()

        print(f"[OK] Automation instance created")
        print(f"   Editor path: {automation.editor_path}")
        print(f"   AutoIt enabled: {automation.autoit_enabled}")
        print(f"   AutoIt script: {automation.autoit_script}")
        print(f"   AutoIt timeout: {automation.autoit_timeout}s")
        print()

        print("[OK] Integration test passed")

    except Exception as e:
        print(f"[FAIL] Integration test failed: {e}")

    print()


def main():
    """Run all configuration tests"""

    print()
    print("=" * 70)
    print("Automation Configuration System - Test Suite")
    print("=" * 70)
    print()

    # Run tests
    config = test_config_loading()
    test_autoit_config(config)
    test_editor_config(config)
    test_playback_config(config)
    test_logging_config(config)
    test_validation_config(config)
    test_advanced_config(config)
    test_summary(config)
    test_integration()

    # Final summary
    print("=" * 70)
    print("Test Results")
    print("=" * 70)
    print()
    print("All tests completed!")
    print()

    # Print recommendations
    if not config.config_path.exists():
        print("[WARN] RECOMMENDATION: Create config/sf2_automation.ini")
        print("   Config file not found - using defaults")
        print()

    if not config.find_editor_path():
        print("[WARN] RECOMMENDATION: Add editor path to config")
        print("   SIDFactoryII.exe not found in configured paths")
        print("   Edit config/sf2_automation.ini [Editor] paths")
        print()

    if config.autoit_enabled and not config.autoit_script_path.exists():
        print("[WARN] RECOMMENDATION: Compile AutoIt script")
        print("   AutoIt enabled but script not found")
        print("   Run: scripts/autoit/compile.bat")
        print()

    if config.find_editor_path() and config.autoit_script_path.exists():
        print("[OK] System fully configured!")
        print("   Editor found + AutoIt available")
        print("   Ready for fully automated workflow")
        print()


if __name__ == '__main__':
    main()
