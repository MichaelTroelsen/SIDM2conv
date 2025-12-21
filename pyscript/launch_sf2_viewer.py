#!/usr/bin/env python3
"""
SF2 Viewer Launcher
Provides quick-start and installation guidance
"""

import sys
import os
import subprocess
from pathlib import Path


def check_pyqt6():
    """Check if PyQt6 is installed"""
    try:
        import PyQt6
        return True
    except ImportError:
        return False


def install_pyqt6():
    """Install PyQt6"""
    print("Installing PyQt6...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyQt6"])
        print("✓ PyQt6 installed successfully")
        return True
    except subprocess.CalledProcessError:
        print("✗ Failed to install PyQt6")
        return False


def launch_viewer():
    """Launch the SF2 viewer"""
    try:
        from sf2_viewer_gui import main
        main()
    except Exception as e:
        print(f"✗ Error launching viewer: {e}")
        sys.exit(1)


def main():
    """Main launcher logic"""
    print("=" * 60)
    print("SF2 Viewer - SID Factory II File Viewer")
    print("=" * 60)

    # Check PyQt6
    if not check_pyqt6():
        print("\n⚠ PyQt6 is not installed")
        print("PyQt6 is required to run the SF2 Viewer\n")

        response = input("Would you like to install PyQt6 now? (y/n): ").strip().lower()
        if response == 'y':
            if install_pyqt6():
                print("\n✓ Installation complete. Starting viewer...")
                launch_viewer()
            else:
                print("\n✗ Installation failed.")
                print("Please install manually with: pip install PyQt6")
                sys.exit(1)
        else:
            print("\nTo install PyQt6, run:")
            print("  pip install PyQt6")
            sys.exit(1)
    else:
        print("✓ PyQt6 is installed")
        print("\nStarting SF2 Viewer...\n")
        launch_viewer()


if __name__ == '__main__':
    main()
