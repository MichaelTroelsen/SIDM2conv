#!/usr/bin/env python3
"""
SIDM2 Video Assets Setup Pipeline
Complete automation: SID -> WAV -> MP3 + Screenshot Capture

This script automates the entire process of setting up assets for the
enhanced SIDM2 demo video.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path


class VideoAssetsPipeline:
    """Pipeline for setting up all video assets."""

    def __init__(self):
        self.project_root = Path.cwd()
        self.video_dir = self.project_root / 'video-demo' / 'sidm2-demo'
        self.assets_dir = self.video_dir / 'public' / 'assets'
        self.temp_dir = self.video_dir / 'temp'

        # Create directories
        (self.assets_dir / 'audio').mkdir(parents=True, exist_ok=True)
        (self.assets_dir / 'screenshots').mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.results = {}

    def print_header(self, text):
        """Print a formatted header."""
        print("\n" + "="*70)
        print(f"  {text}")
        print("="*70)

    def print_step(self, step_num, text):
        """Print a step header."""
        print(f"\n{'='*70}")
        print(f"STEP {step_num}: {text}")
        print(f"{'='*70}")

    def find_sid_file(self):
        """Find a good SID file for background music."""
        self.print_step(1, "Finding SID file for background music")

        candidates = [
            "Laxity/Stinsens_Last_Night_of_89.sid",
            "learnings/Stinsens_Last_Night_of_89.sid",
            "SID/Stinsens_Last_Night_of_89.sid",
            "tools/Stinsens_Last_Night_of_89.sid",
        ]

        for candidate in candidates:
            path = self.project_root / candidate
            if path.exists():
                print(f"[OK] Found SID file: {path}")
                return path

        print("[X] Could not find Stinsens SID file")
        print("   Searching for any Laxity SID file...")

        laxity_dir = self.project_root / 'Laxity'
        if laxity_dir.exists():
            sid_files = list(laxity_dir.glob('*.sid'))
            if sid_files:
                print(f"[OK] Found alternative: {sid_files[0]}")
                return sid_files[0]

        return None

    def convert_sid_to_wav(self, sid_path):
        """Convert SID file to WAV using VSID (VICE SID player)."""
        self.print_step(2, "Converting SID to WAV (240 seconds)")

        wav_path = self.temp_dir / 'background-music.wav'

        try:
            # Try VSID from common locations
            vsid_paths = [
                Path(r'C:\winvice\bin\vsid.exe'),
                self.project_root / 'tools' / 'vice' / 'bin' / 'vsid.exe',
                self.project_root / 'tools' / 'vice' / 'vsid.exe',
            ]

            vsid_exe = None
            for path in vsid_paths:
                if path.exists():
                    vsid_exe = path
                    break

            if not vsid_exe:
                print(f"[X] VSID not found in any location:")
                for path in vsid_paths:
                    print(f"   - {path}")
                print(f"\n[i] Please install VICE:")
                print(f"   python pyscript/install_vice.py")
                return None

            print(f"[[music]] Input:  {sid_path}")
            print(f"[[music]] Output: {wav_path}")
            print(f"[t]  Duration: 240 seconds (4 minutes)")
            print(f"[V] Using VSID: {vsid_exe}")

            # Build VSID command
            # vsid -sounddev wav -soundarg output.wav input.sid
            # Note: VSID runs indefinitely, so we use timeout to stop it after 240 seconds
            cmd = [
                str(vsid_exe),
                '-sounddev', 'wav',
                '-soundarg', str(wav_path),
                str(sid_path)
            ]

            print(f"\n[>] Running: {' '.join(cmd)}")
            print(f"[t] Timeout: 250 seconds (240s playback + 10s buffer)")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=250  # 240 seconds + 10 second buffer
            )

            # Check if WAV was created (VSID may still be killed by timeout)
            if wav_path.exists() and wav_path.stat().st_size > 0:
                size_mb = wav_path.stat().st_size / (1024 * 1024)
                print(f"\n[OK] WAV file created successfully!")
                print(f"   File: {wav_path}")
                print(f"   Size: {size_mb:.2f} MB")
                return wav_path
            else:
                print(f"\n[X] VSID failed - no output file created")
                if result.stderr:
                    print(f"   Error: {result.stderr[:500]}")
                return None

        except subprocess.TimeoutExpired:
            # Timeout is expected - VSID runs indefinitely
            # Check if WAV file was created before timeout
            if wav_path.exists() and wav_path.stat().st_size > 0:
                size_mb = wav_path.stat().st_size / (1024 * 1024)
                print(f"\n[OK] WAV file created successfully (stopped after timeout)!")
                print(f"   File: {wav_path}")
                print(f"   Size: {size_mb:.2f} MB")
                return wav_path
            else:
                print("[X] VSID timed out without creating output file")
                return None
        except Exception as e:
            print(f"[X] Error: {e}")
            return None

    def convert_wav_to_mp3(self, wav_path):
        """Convert WAV to MP3 using wav_to_mp3.py."""
        self.print_step(3, "Converting WAV to MP3")

        mp3_path = self.assets_dir / 'audio' / 'background-music.mp3'

        try:
            wav_to_mp3_script = self.project_root / 'pyscript' / 'wav_to_mp3.py'

            print(f"[>] Running WAV to MP3 converter...")
            print(f"   Input:  {wav_path}")
            print(f"   Output: {mp3_path}")

            # Run the converter
            result = subprocess.run(
                [sys.executable, str(wav_to_mp3_script), str(wav_path), str(mp3_path)],
                capture_output=False,  # Show output in real-time
                text=True
            )

            if result.returncode == 0 and mp3_path.exists():
                size_mb = mp3_path.stat().st_size / (1024 * 1024)
                print(f"\n[OK] MP3 file created successfully!")
                print(f"   File: {mp3_path}")
                print(f"   Size: {size_mb:.2f} MB")
                return mp3_path
            else:
                print(f"\n[!]  Automatic conversion failed")
                print(f"\n[i] Manual conversion required:")
                print(f"   1. Go to: https://cloudconvert.com/wav-to-mp3")
                print(f"   2. Upload: {wav_path}")
                print(f"   3. Download and save as: {mp3_path}")
                return None

        except Exception as e:
            print(f"[X] Error: {e}")
            return None

    def capture_screenshots(self):
        """Capture screenshots using automated tool."""
        self.print_step(4, "Capturing Screenshots")

        try:
            capture_script = self.project_root / 'pyscript' / 'capture_screenshots.py'

            print("[>] Running screenshot capture automation...")

            result = subprocess.run(
                [sys.executable, str(capture_script)],
                capture_output=False,  # Show output in real-time
                text=True
            )

            screenshots_dir = self.assets_dir / 'screenshots'
            screenshot_count = len(list(screenshots_dir.glob('*.png')))

            if screenshot_count >= 3:
                print(f"\n[OK] Screenshots captured: {screenshot_count}/3")
                return True
            else:
                print(f"\n[!]  Only {screenshot_count}/3 screenshots captured")
                print("   You may need to capture some screenshots manually")
                return screenshot_count > 0

        except Exception as e:
            print(f"[X] Error: {e}")
            return False

    def verify_assets(self):
        """Verify all assets are in place."""
        self.print_step(5, "Verifying Assets")

        required_files = {
            'Audio': self.assets_dir / 'audio' / 'background-music.mp3',
            'SF2 Viewer Screenshot': self.assets_dir / 'screenshots' / 'sf2-viewer.png',
            'Conversion Cockpit Screenshot': self.assets_dir / 'screenshots' / 'conversion-cockpit.png',
            'SF2 Editor Screenshot': self.assets_dir / 'screenshots' / 'sf2-editor.png',
        }

        print("\n[i] Checking required files:\n")

        all_present = True
        for name, path in required_files.items():
            if path.exists():
                size_kb = path.stat().st_size / 1024
                print(f"[OK] {name}")
                print(f"   {path}")
                print(f"   {size_kb:.1f} KB\n")
            else:
                print(f"[X] {name}")
                print(f"   Missing: {path}\n")
                all_present = False

        return all_present

    def show_next_steps(self):
        """Show next steps to complete video."""
        self.print_header("Next Steps")

        print("\n[V] Your video assets are ready (or almost ready)!")

        print("\n[i] To preview your video:")
        print("   cd video-demo/sidm2-demo")
        print("   npm start")
        print("   Then open: http://localhost:3000")

        print("\n[V] To render final video:")
        print("   cd video-demo/sidm2-demo")
        print("   npx remotion render SIDM2Demo out/sidm2-demo-enhanced.mp4")

        print("\n[B] Documentation:")
        print("   - Setup Guide: video-demo/sidm2-demo/SETUP-ENHANCED-VIDEO.md")
        print("   - Quick Start: video-demo/sidm2-demo/QUICK-START.md")

    def run(self):
        """Run the complete pipeline."""
        self.print_header("SIDM2 Video Assets Setup Pipeline")

        print("\n[*] This pipeline will:")
        print("   1. Find a good SID file (Stinsens)")
        print("   2. Convert SID -> WAV (240 seconds / 4 minutes)")
        print("   3. Convert WAV -> MP3")
        print("   4. Capture tool screenshots automatically")
        print("   5. Verify all assets are ready")
        print("\n[i] Starting pipeline...")

        # Step 1: Find SID file
        sid_path = self.find_sid_file()
        if not sid_path:
            print("\n[X] Cannot proceed without SID file")
            return 1

        # Step 2: Convert to WAV
        wav_path = self.convert_sid_to_wav(sid_path)
        self.results['SID->WAV'] = wav_path is not None

        if not wav_path:
            print("\n[X] Cannot proceed without WAV file")
            return 1

        # Step 3: Convert to MP3
        mp3_path = self.convert_wav_to_mp3(wav_path)
        self.results['WAV->MP3'] = mp3_path is not None

        # Step 4: Capture screenshots
        screenshots_ok = self.capture_screenshots()
        self.results['Screenshots'] = screenshots_ok

        # Step 5: Verify
        all_assets_ready = self.verify_assets()

        # Summary
        self.print_header("Pipeline Complete!")

        print("\n[#] Results:")
        for task, success in self.results.items():
            status = "[OK]" if success else "[X]"
            print(f"   {status} {task}")

        if all_assets_ready:
            print("\n[*] All assets are ready! Your video is ready to render!")
            self.show_next_steps()
            return 0
        else:
            print("\n[!]  Some assets may need manual setup")
            print("   Check the verification results above")
            self.show_next_steps()
            return 0


def main():
    """Main entry point."""
    try:
        pipeline = VideoAssetsPipeline()
        return pipeline.run()
    except KeyboardInterrupt:
        print("\n\n[X] Pipeline cancelled by user")
        return 1
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
