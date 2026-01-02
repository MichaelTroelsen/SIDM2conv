#!/usr/bin/env python3
"""
Automated Screenshot Capture for SIDM2 Tools
Launches each tool and captures screenshots automatically.
"""

import os
import sys
import time
import subprocess
from pathlib import Path


def install_required_packages():
    """Install required packages for screenshot capture."""
    required = ['pillow', 'pyautogui']

    for package in required:
        try:
            __import__(package.replace('pillow', 'PIL'))
        except ImportError:
            print(f"Installing {package}...")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', package],
                             capture_output=True, check=True)
                print(f"[OK] {package} installed")
            except:
                print(f"[X] Could not install {package}")
                return False
    return True


def capture_window_screenshot(window_title, output_path, wait_time=2):
    """
    Capture screenshot of a specific window.

    Args:
        window_title: Title of window to capture
        output_path: Path to save screenshot
        wait_time: Seconds to wait before capture
    """
    try:
        import pyautogui
        from PIL import Image

        print(f"[.] Waiting {wait_time}s for window to load...")
        time.sleep(wait_time)

        # Take screenshot
        screenshot = pyautogui.screenshot()

        # Save
        screenshot.save(output_path)
        print(f"[OK] Screenshot saved: {output_path}")

        return True

    except Exception as e:
        print(f"[X] Error capturing screenshot: {e}")
        return False


def capture_sf2_viewer(output_dir):
    """Launch SF2 Viewer and capture screenshot."""
    print("\n[C] Capturing SF2 Viewer...")

    # Find a good SF2 file to display
    sf2_files = [
        "output/keep_Stinsens_Last_Night_of_89/Stinsens_Last_Night_of_89/New/Stinsens_Last_Night_of_89.sf2",
        "learnings/Laxity - Stinsen - Last Night Of 89.sf2",
    ]

    sf2_file = None
    for f in sf2_files:
        if os.path.exists(f):
            sf2_file = f
            break

    if not sf2_file:
        print("[X] No SF2 file found to display")
        return False

    try:
        # Launch SF2 Viewer
        print(f"[>] Launching SF2 Viewer with: {sf2_file}")
        process = subprocess.Popen(
            [sys.executable, 'pyscript/sf2_viewer_gui.py', sf2_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for window to appear and settle
        time.sleep(3)

        # Capture screenshot
        output_path = os.path.join(output_dir, 'sf2-viewer.png')
        capture_window_screenshot('SF2 Viewer', output_path, wait_time=2)

        # Close the viewer
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()

        return os.path.exists(output_path)

    except Exception as e:
        print(f"[X] Error: {e}")
        return False


def capture_conversion_cockpit(output_dir):
    """Launch Conversion Cockpit and capture screenshot."""
    print("\n[C] Capturing Conversion Cockpit...")

    try:
        # Launch Conversion Cockpit
        print("[>] Launching Conversion Cockpit...")
        process = subprocess.Popen(
            [sys.executable, 'pyscript/conversion_cockpit_gui.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        # Wait for window to appear and settle
        time.sleep(4)

        # Capture screenshot
        output_path = os.path.join(output_dir, 'conversion-cockpit.png')
        capture_window_screenshot('Conversion Cockpit', output_path, wait_time=2)

        # Close the cockpit
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()

        return os.path.exists(output_path)

    except Exception as e:
        print(f"[X] Error: {e}")
        return False


def create_sf2_editor_placeholder(output_dir):
    """Create a placeholder for SF2 Editor screenshot."""
    print("\n[C] Creating SF2 Editor placeholder...")

    try:
        from PIL import Image, ImageDraw, ImageFont

        # Create a placeholder image
        img = Image.new('RGB', (1280, 720), color='#1a1a2e')
        draw = ImageDraw.Draw(img)

        # Add text
        text = "SID Factory II Editor\n\n(Screenshot placeholder)\n\nReplace with actual screenshot"

        # Try to use a font, fall back to default
        try:
            font = ImageFont.truetype("arial.ttf", 40)
            small_font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
            small_font = font

        # Calculate text position
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        x = (1280 - text_width) // 2
        y = (720 - text_height) // 2

        # Draw text
        draw.text((x, y), text, fill='#00ff88', font=font)

        # Add instructions
        instructions = "To replace: Capture SID Factory II editor screenshot\nand save as 'sf2-editor.png' in this folder"
        draw.text((50, 650), instructions, fill='#aaaaaa', font=small_font)

        # Save
        output_path = os.path.join(output_dir, 'sf2-editor.png')
        img.save(output_path)

        print(f"[OK] Placeholder created: {output_path}")
        print("   [!]  Replace this with actual SF2 Editor screenshot when available")

        return True

    except Exception as e:
        print(f"[X] Error creating placeholder: {e}")
        return False


def main():
    """Main entry point."""
    # Output directory
    output_dir = 'video-demo/sidm2-demo/public/assets/screenshots'
    os.makedirs(output_dir, exist_ok=True)

    print("="*60)
    print("SIDM2 Screenshot Capture Automation")
    print("="*60)

    # Install required packages
    print("\n[+] Checking requirements...")
    if not install_required_packages():
        print("\n[X] Could not install required packages")
        print("   Manual installation: pip install pillow pyautogui")
        return 1

    results = {}

    # Capture screenshots
    results['SF2 Viewer'] = capture_sf2_viewer(output_dir)
    time.sleep(1)

    results['Conversion Cockpit'] = capture_conversion_cockpit(output_dir)
    time.sleep(1)

    results['SF2 Editor'] = create_sf2_editor_placeholder(output_dir)

    # Summary
    print("\n" + "="*60)
    print("Screenshot Capture Summary")
    print("="*60)

    for tool, success in results.items():
        status = "[OK]" if success else "[X]"
        print(f"{status} {tool}")

    print(f"\n[F] Screenshots saved to: {output_dir}")

    # List files
    print("\n[i] Files created:")
    for file in os.listdir(output_dir):
        if file.endswith('.png'):
            path = os.path.join(output_dir, file)
            size_kb = os.path.getsize(path) / 1024
            print(f"   - {file} ({size_kb:.1f} KB)")

    success_count = sum(results.values())
    total_count = len(results)

    if success_count == total_count:
        print(f"\n[OK] All {total_count} screenshots captured successfully!")
        return 0
    else:
        print(f"\n[!]  Captured {success_count}/{total_count} screenshots")
        print("   Some screenshots may need manual capture")
        return 0


if __name__ == '__main__':
    sys.exit(main())
