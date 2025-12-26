#!/usr/bin/env python3
"""
Install ffmpeg for Windows
Downloads and extracts ffmpeg to tools/ffmpeg directory
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path


def download_file(url, destination):
    """Download a file with progress indication."""
    print(f"[>] Downloading from: {url}")
    print(f"[>] Saving to: {destination}")

    try:
        # Download with progress
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0

            with open(destination, 'wb') as f:
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r[.] Progress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')

        print()  # New line after progress
        print(f"[OK] Download complete: {os.path.getsize(destination) / (1024*1024):.1f} MB")
        return True

    except Exception as e:
        print(f"\n[X] Download failed: {e}")
        return False


def extract_zip(zip_path, extract_to):
    """Extract ZIP file."""
    print(f"\n[>] Extracting: {zip_path}")
    print(f"[>] To: {extract_to}")

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get total files for progress
            total_files = len(zip_ref.namelist())

            for i, file in enumerate(zip_ref.namelist(), 1):
                zip_ref.extract(file, extract_to)
                if i % 10 == 0 or i == total_files:
                    print(f"\r[.] Extracting: {i}/{total_files} files", end='')

        print()  # New line
        print("[OK] Extraction complete")
        return True

    except Exception as e:
        print(f"\n[X] Extraction failed: {e}")
        return False


def find_ffmpeg_in_extracted(extract_dir):
    """Find ffmpeg.exe in the extracted directory."""
    for root, dirs, files in os.walk(extract_dir):
        if 'ffmpeg.exe' in files:
            return os.path.join(root, 'ffmpeg.exe')
    return None


def install_ffmpeg():
    """Download and install ffmpeg."""
    print("="*70)
    print("ffmpeg Installation for SIDM2")
    print("="*70)

    project_root = Path.cwd()
    tools_dir = project_root / 'tools'
    ffmpeg_dir = tools_dir / 'ffmpeg'
    temp_dir = project_root / 'temp_ffmpeg_install'

    # Create directories
    tools_dir.mkdir(exist_ok=True)
    temp_dir.mkdir(exist_ok=True)

    print(f"\n[i] Installation directory: {ffmpeg_dir}")

    # Check if already installed
    ffmpeg_exe = ffmpeg_dir / 'bin' / 'ffmpeg.exe'
    if ffmpeg_exe.exists():
        print(f"\n[!] ffmpeg is already installed at: {ffmpeg_exe}")
        response = input("[?] Reinstall? (y/N): ").strip().lower()
        if response != 'y':
            print("[i] Using existing installation")
            return str(ffmpeg_exe)
        print("[>] Removing old installation...")
        shutil.rmtree(ffmpeg_dir, ignore_errors=True)

    # Download URL for ffmpeg essentials build (Windows)
    # Using a smaller essentials build (~70 MB instead of ~150 MB full build)
    download_url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"

    zip_path = temp_dir / 'ffmpeg.zip'

    print(f"\n[*] Downloading ffmpeg (this may take a few minutes)...")
    print(f"[i] Size: Approximately 70-100 MB")

    # Download
    if not download_file(download_url, zip_path):
        print("\n[X] Failed to download ffmpeg")
        print("[i] Manual installation:")
        print("    1. Go to: https://github.com/BtbN/FFmpeg-Builds/releases")
        print("    2. Download: ffmpeg-master-latest-win64-gpl.zip")
        print(f"    3. Extract to: {ffmpeg_dir}")
        return None

    # Extract
    if not extract_zip(zip_path, temp_dir):
        print("\n[X] Failed to extract ffmpeg")
        return None

    # Find extracted ffmpeg directory (it has a version-specific name)
    extracted_dirs = [d for d in temp_dir.iterdir() if d.is_dir() and d.name.startswith('ffmpeg')]

    if not extracted_dirs:
        print("[X] Could not find extracted ffmpeg directory")
        return None

    extracted_dir = extracted_dirs[0]
    print(f"[i] Found extracted directory: {extracted_dir.name}")

    # Move to final location
    print(f"\n[>] Moving to: {ffmpeg_dir}")
    shutil.move(str(extracted_dir), str(ffmpeg_dir))

    # Find ffmpeg.exe
    ffmpeg_exe = ffmpeg_dir / 'bin' / 'ffmpeg.exe'

    if not ffmpeg_exe.exists():
        print(f"[X] ffmpeg.exe not found at expected location: {ffmpeg_exe}")
        return None

    # Cleanup
    print("\n[>] Cleaning up temporary files...")
    shutil.rmtree(temp_dir, ignore_errors=True)

    # Test ffmpeg
    print("\n[>] Testing ffmpeg installation...")
    import subprocess
    try:
        result = subprocess.run([str(ffmpeg_exe), '-version'],
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"[OK] {version_line}")
        else:
            print("[!] ffmpeg installed but version check failed")
    except Exception as e:
        print(f"[!] Could not test ffmpeg: {e}")

    print("\n" + "="*70)
    print("ffmpeg Installation Complete!")
    print("="*70)
    print(f"\n[F] ffmpeg location: {ffmpeg_exe}")
    print(f"[F] Size: {ffmpeg_exe.stat().st_size / (1024*1024):.1f} MB")

    return str(ffmpeg_exe)


def main():
    """Main entry point."""
    try:
        ffmpeg_path = install_ffmpeg()

        if ffmpeg_path:
            print("\n[OK] Installation successful!")
            print(f"[i] ffmpeg is ready at: {ffmpeg_path}")

            # Update wav_to_mp3.py to use this location
            print("\n[i] The pipeline will now use this ffmpeg installation")
            print("    automatically for WAV to MP3 conversion.")

            return 0
        else:
            print("\n[X] Installation failed")
            return 1

    except KeyboardInterrupt:
        print("\n\n[X] Installation cancelled by user")
        return 1
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
