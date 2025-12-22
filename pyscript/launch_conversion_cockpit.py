#!/usr/bin/env python3
"""
Conversion Cockpit Launcher - Auto-installer and launcher

Checks for PyQt6 dependency and launches the Conversion Cockpit GUI.
Automatically installs PyQt6 if not available.

Usage:
    python launch_conversion_cockpit.py

Version: 1.0.0
Date: 2025-12-22
"""

import sys
import subprocess
import os
from pathlib import Path


def check_pyqt6():
    """Check if PyQt6 is installed"""
    try:
        import PyQt6
        return True
    except ImportError:
        return False


def install_pyqt6():
    """Install PyQt6 using pip"""
    print("=" * 70)
    print("PyQt6 NOT FOUND")
    print("=" * 70)
    print("\nThe Conversion Cockpit requires PyQt6 to run.")
    print("PyQt6 is a Python library for creating graphical user interfaces.")
    print("\nWould you like to install it now? (It will take about 1 minute)")
    print("\nOptions:")
    print("  Y - Yes, install PyQt6 now")
    print("  N - No, exit without installing")
    print("=" * 70)

    choice = input("\nYour choice (Y/N): ").strip().upper()

    if choice != 'Y':
        print("\nInstallation cancelled. Exiting.")
        return False

    print("\n" + "=" * 70)
    print("INSTALLING PyQt6")
    print("=" * 70)
    print("\nThis will run: pip install PyQt6")
    print("Please wait...\n")

    try:
        # Run pip install
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "PyQt6"],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print("\n" + "=" * 70)
            print("INSTALLATION SUCCESSFUL")
            print("=" * 70)
            print("\nPyQt6 has been installed successfully!")
            print("The Conversion Cockpit will now launch...\n")
            return True
        else:
            print("\n" + "=" * 70)
            print("INSTALLATION FAILED")
            print("=" * 70)
            print("\nError installing PyQt6:")
            print(result.stderr)
            print("\nPlease install manually with: pip install PyQt6")
            return False

    except Exception as e:
        print("\n" + "=" * 70)
        print("INSTALLATION ERROR")
        print("=" * 70)
        print(f"\nAn error occurred: {e}")
        print("\nPlease install manually with: pip install PyQt6")
        return False


def launch_cockpit():
    """Launch the Conversion Cockpit GUI"""
    # Add pyscript directory to path
    script_dir = Path(__file__).parent
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    # Import and run the GUI
    try:
        from conversion_cockpit_gui import main
        main()
    except ImportError as e:
        print("\n" + "=" * 70)
        print("ERROR: Missing module")
        print("=" * 70)
        print(f"\nCould not import Conversion Cockpit GUI: {e}")
        print("\nPlease ensure all required files are present in pyscript/:")
        print("  - conversion_cockpit_gui.py")
        print("  - conversion_executor.py")
        print("  - pipeline_config.py")
        print("  - cockpit_widgets.py")
        print("\n")
        return False
    except Exception as e:
        print("\n" + "=" * 70)
        print("ERROR: Launch failed")
        print("=" * 70)
        print(f"\nFailed to launch Conversion Cockpit: {e}")
        print("\n")
        return False

    return True


def main():
    """Main entry point"""
    print("\n" + "=" * 70)
    print("SIDM2 CONVERSION COCKPIT LAUNCHER")
    print("=" * 70)
    print("\nVersion: 1.0.0")
    print("Mission control for batch SID conversion")
    print("=" * 70)

    # Check for PyQt6
    if not check_pyqt6():
        print("\nChecking dependencies...")
        if not install_pyqt6():
            print("\nExiting.")
            return 1
        print("\nDependencies installed. Launching...\n")
    else:
        print("\nAll dependencies found. Launching...\n")

    # Launch the GUI
    if not launch_cockpit():
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
