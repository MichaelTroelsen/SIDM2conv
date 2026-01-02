#!/usr/bin/env python3
"""
WAV to MP3 Converter
Converts WAV audio files to MP3 format using available tools.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


def find_ffmpeg():
    """Try to find ffmpeg in common locations or PATH."""
    # Check if ffmpeg is in PATH
    if shutil.which('ffmpeg'):
        return 'ffmpeg'

    # Check project tools directory first (installed by install_ffmpeg.py)
    project_ffmpeg = Path.cwd() / 'tools' / 'ffmpeg' / 'bin' / 'ffmpeg.exe'
    if project_ffmpeg.exists():
        return str(project_ffmpeg)

    # Check common installation paths on Windows
    common_paths = [
        r'C:\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
        os.path.expanduser(r'~\ffmpeg\bin\ffmpeg.exe'),
    ]

    for path in common_paths:
        if os.path.exists(path):
            return path

    return None


def download_ffmpeg_portable():
    """Download portable ffmpeg for Windows."""
    import urllib.request
    import zipfile

    print("Downloading portable ffmpeg...")
    # This would download a portable version
    # For now, we'll provide instructions
    return None


def convert_with_ffmpeg(wav_path, mp3_path, ffmpeg_path='ffmpeg'):
    """Convert WAV to MP3 using ffmpeg."""
    try:
        cmd = [
            ffmpeg_path,
            '-i', wav_path,
            '-codec:a', 'libmp3lame',
            '-qscale:a', '2',  # High quality (0-9, lower is better)
            '-y',  # Overwrite output
            mp3_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"[OK] Successfully converted to MP3: {mp3_path}")
            return True
        else:
            print(f"[X] ffmpeg error: {result.stderr}")
            return False

    except Exception as e:
        print(f"[X] Error using ffmpeg: {e}")
        return False


def convert_with_pydub(wav_path, mp3_path):
    """Convert WAV to MP3 using pydub library."""
    try:
        from pydub import AudioSegment

        print("Converting with pydub...")
        audio = AudioSegment.from_wav(wav_path)
        audio.export(mp3_path, format='mp3', bitrate='192k')

        print(f"[OK] Successfully converted to MP3: {mp3_path}")
        return True

    except ImportError:
        print("[X] pydub not installed")
        return False
    except Exception as e:
        print(f"[X] Error with pydub: {e}")
        return False


def install_pydub():
    """Try to install pydub."""
    try:
        print("Attempting to install pydub...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pydub'],
                      capture_output=True, check=True)
        print("[OK] pydub installed successfully")
        return True
    except:
        print("[X] Could not install pydub")
        return False


def convert_wav_to_mp3(wav_path, mp3_path):
    """
    Convert WAV to MP3 using the best available method.

    Args:
        wav_path: Path to input WAV file
        mp3_path: Path to output MP3 file

    Returns:
        bool: True if conversion successful
    """
    wav_path = str(wav_path)
    mp3_path = str(mp3_path)

    if not os.path.exists(wav_path):
        print(f"[X] WAV file not found: {wav_path}")
        return False

    print(f"\n[music] Converting WAV to MP3...")
    print(f"   Input:  {wav_path}")
    print(f"   Output: {mp3_path}")

    # Method 1: Try ffmpeg
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        print(f"[OK] Found ffmpeg: {ffmpeg}")
        if convert_with_ffmpeg(wav_path, mp3_path, ffmpeg):
            return True
    else:
        print("[!]  ffmpeg not found in PATH or common locations")

    # Method 2: Try pydub
    if convert_with_pydub(wav_path, mp3_path):
        return True

    # Method 3: Try to install pydub and use it
    print("\n[>] Attempting to install pydub...")
    if install_pydub():
        if convert_with_pydub(wav_path, mp3_path):
            return True

    # All methods failed
    print("\n" + "="*60)
    print("[X] Could not convert WAV to MP3 automatically")
    print("="*60)
    print("\n[i] Manual conversion options:")
    print("\n1. Install ffmpeg:")
    print("   - Download: https://github.com/BtbN/FFmpeg-Builds/releases")
    print("   - Extract to C:\\ffmpeg")
    print("   - Add C:\\ffmpeg\\bin to PATH")
    print(f"\n2. Use online converter:")
    print("   - Go to: https://cloudconvert.com/wav-to-mp3")
    print(f"   - Upload: {wav_path}")
    print("   - Download and save as: {mp3_path}")
    print("\n3. Use VLC Media Player:")
    print("   - Media -> Convert/Save")
    print(f"   - Add: {wav_path}")
    print("   - Choose MP3 codec")
    print(f"   - Save as: {mp3_path}")

    return False


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: python wav_to_mp3.py <input.wav> <output.mp3>")
        return 1

    wav_path = sys.argv[1]
    mp3_path = sys.argv[2]

    # Ensure output directory exists
    os.makedirs(os.path.dirname(mp3_path) or '.', exist_ok=True)

    if convert_wav_to_mp3(wav_path, mp3_path):
        print("\n[OK] Conversion complete!")

        # Show file info
        if os.path.exists(mp3_path):
            size_mb = os.path.getsize(mp3_path) / (1024 * 1024)
            print(f"   MP3 file: {mp3_path}")
            print(f"   Size: {size_mb:.2f} MB")
        return 0
    else:
        print("\n[X] Conversion failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
