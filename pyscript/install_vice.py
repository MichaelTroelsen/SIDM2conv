#!/usr/bin/env python3
"""
Install VICE (Versatile Commodore Emulator) for Windows.
Downloads the latest VICE release and extracts vsid.exe.
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path

def download_file(url, dest_path):
    """Download a file with progress indication."""
    print(f"Downloading from {url}...")

    def report_progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, downloaded * 100 / total_size)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            print(f"\rProgress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end='')

    urllib.request.urlretrieve(url, dest_path, reporthook=report_progress)
    print()  # New line after progress

def extract_zip(zip_path, extract_to):
    """Extract a ZIP file."""
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print("Extraction complete!")

def install_vice():
    """Download and install VICE."""
    # Paths
    project_root = Path(__file__).parent.parent
    tools_dir = project_root / 'tools'
    vice_dir = tools_dir / 'vice'
    temp_dir = tools_dir / 'temp_vice'

    # Create directories
    tools_dir.mkdir(exist_ok=True)
    temp_dir.mkdir(exist_ok=True)

    # VICE download URL (Windows GTK3 version)
    # Using SourceForge direct download mirror (bypasses redirects)
    # Format: https://downloads.sourceforge.net/project/vice-emu/releases/vice-VERSION-win64.zip
    download_url = "https://downloads.sourceforge.net/project/vice-emu/releases/vice-3.7-win64.zip"
    zip_path = temp_dir / 'vice.zip'

    # Check if already installed
    vsid_exe = vice_dir / 'bin' / 'vsid.exe'
    if vsid_exe.exists():
        print(f"SUCCESS: VICE already installed at {vice_dir}")
        print(f"SUCCESS: vsid.exe found at {vsid_exe}")
        return str(vsid_exe)

    print("=" * 60)
    print("VICE Emulator Installation")
    print("=" * 60)

    try:
        # Download VICE
        if not zip_path.exists():
            print("\n1. Downloading VICE...")
            download_file(download_url, zip_path)
        else:
            print("\n1. Using existing download...")

        # Extract
        print("\n2. Extracting VICE...")
        extract_zip(zip_path, temp_dir)

        # Find extracted directory (it should be vice-3.8-win64 or similar)
        extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir() and 'vice' in d.name.lower()]
        if not extracted_dirs:
            raise Exception("Could not find extracted VICE directory")

        extracted_dir = extracted_dirs[0]

        # Move to final location
        print("\n3. Installing VICE...")
        if vice_dir.exists():
            shutil.rmtree(vice_dir)
        shutil.move(str(extracted_dir), str(vice_dir))

        # Verify installation
        vsid_exe = vice_dir / 'bin' / 'vsid.exe'
        x64_exe = vice_dir / 'bin' / 'x64sc.exe'

        if not vsid_exe.exists():
            # Try alternate structure
            vsid_exe = vice_dir / 'vsid.exe'
            x64_exe = vice_dir / 'x64sc.exe'

        if not vsid_exe.exists():
            raise Exception(f"vsid.exe not found in {vice_dir}")

        print("\n4. Testing installation...")
        import subprocess
        result = subprocess.run(
            [str(vsid_exe), '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )

        print(f"\nVICE Version: {result.stdout.strip()}")

        # Cleanup
        print("\n5. Cleaning up...")
        if zip_path.exists():
            zip_path.unlink()
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        print("\n" + "=" * 60)
        print("SUCCESS: VICE Installation Complete!")
        print("=" * 60)
        print(f"\nvsid.exe: {vsid_exe}")
        print(f"x64sc.exe: {x64_exe}")
        print("\nUsage:")
        print(f"  {vsid_exe} -sounddev wav -soundarg output.wav input.sid")

        return str(vsid_exe)

    except Exception as e:
        print(f"\nERROR during installation: {e}")

        # Cleanup on error
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

        sys.exit(1)

if __name__ == '__main__':
    install_vice()
