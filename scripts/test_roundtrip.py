#!/usr/bin/env python3
"""
Round-trip validation test: SID → SF2 → SID

Complete automated testing workflow:
1. Convert SID → SF2 (sid_to_sf2.py)
2. Pack SF2 → SID (Python sf2_packer)
3. Render original SID → WAV (SID2WAV.EXE)
4. Render exported SID → WAV (SID2WAV.EXE)
5. Compare with siddump analysis
6. Generate detailed HTML report

Usage:
    python test_roundtrip.py SID/Angular.sid
    python test_roundtrip.py SID/Angular.sid --duration 30 --verbose
"""

import subprocess
import sys
import os
import argparse
import json
from pathlib import Path
from datetime import datetime

# Setup Python path for imports - must be BEFORE sidm2 imports
# This allows the script to be run from any directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sidm2.sf2_packer import pack_sf2_to_sid

# Import custom error handling
try:
    from sidm2 import errors
except ImportError as e:
    print(f"Error importing sidm2: {e}")
    print(f"Project root: {project_root}")
    print(f"sys.path: {sys.path}")
    raise


class RoundtripValidator:
    def __init__(self, sid_file, output_dir="output", duration=30, verbose=False):
        self.sid_file = Path(sid_file)
        self.output_dir = Path(output_dir)
        self.duration = duration
        self.verbose = verbose
        self.base_name = self.sid_file.stem

        # Create nested directory structure: PlayerName/Original and PlayerName/New
        self.song_dir = self.output_dir / self.base_name
        self.original_dir = self.song_dir / "Original"
        self.new_dir = self.song_dir / "New"

        # Create all directories
        self.original_dir.mkdir(parents=True, exist_ok=True)
        self.new_dir.mkdir(parents=True, exist_ok=True)

        # Output files - organized by Original vs New
        # Original files
        self.original_sid_copy = self.original_dir / f"{self.base_name}.sid"
        self.original_wav = self.original_dir / f"{self.base_name}.wav"
        self.original_dump = self.original_dir / f"{self.base_name}.dump"
        self.original_info = self.original_dir / f"{self.base_name}_info.txt"

        # New files
        self.sf2_file = self.new_dir / f"{self.base_name}_converted.sf2"
        self.exported_sid = self.new_dir / f"{self.base_name}_exported.sid"
        self.exported_wav = self.new_dir / f"{self.base_name}_exported.wav"
        self.exported_dump = self.new_dir / f"{self.base_name}_exported.dump"
        self.exported_info = self.new_dir / f"{self.base_name}_info.txt"

        # Report at song level
        self.report_file = self.song_dir / f"{self.base_name}_roundtrip_report.html"

        self.results = {
            'sid_file': str(self.sid_file),
            'timestamp': datetime.now().isoformat(),
            'duration': duration,
            'steps': {}
        }

    def log(self, message):
        """Print message if verbose mode enabled"""
        if self.verbose:
            print(f"  {message}")

    def run_command(self, cmd, description, capture_output=True):
        """Run command and track result"""
        self.log(f"{description}...")
        try:
            if capture_output:
                result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
                success = result.returncode == 0
                output = result.stdout if success else result.stderr
            else:
                result = subprocess.run(cmd, shell=False)
                success = result.returncode == 0
                output = ""

            return success, output
        except Exception as e:
            return False, str(e)

    def step0_setup_original_files(self):
        """Step 0: Copy original SID and create info file"""
        print("\n[0/7] Setting up original files...")

        # Copy original SID to Original directory
        import shutil
        try:
            shutil.copy2(self.sid_file, self.original_sid_copy)
            print(f"  [OK] Copied {self.sid_file.name} to Original/")
        except Exception as e:
            print(f"  [FAIL] Failed to copy original SID: {e}")
            return False

        # Create original info file with SID metadata
        try:
            info_lines = []
            info_lines.append(f"Original SID File Information")
            info_lines.append(f"=" * 50)
            info_lines.append(f"Filename: {self.sid_file.name}")
            info_lines.append(f"Path: {self.sid_file}")
            info_lines.append(f"Size: {self.sid_file.stat().st_size} bytes")
            info_lines.append(f"Modified: {datetime.fromtimestamp(self.sid_file.stat().st_mtime)}")
            info_lines.append(f"")
            info_lines.append(f"Test Configuration")
            info_lines.append(f"-" * 50)
            info_lines.append(f"Test Date: {datetime.now()}")
            info_lines.append(f"Duration: {self.duration} seconds")
            info_lines.append(f"")

            # Try to extract PSID header info
            try:
                with open(self.sid_file, 'rb') as f:
                    header = f.read(128)
                    if header[:4] == b'PSID' or header[:4] == b'RSID':
                        magic = header[:4].decode('ascii')
                        version = int.from_bytes(header[4:6], 'big')
                        info_lines.append(f"SID Format")
                        info_lines.append(f"-" * 50)
                        info_lines.append(f"Type: {magic}")
                        info_lines.append(f"Version: {version}")

                        # Extract title, author, copyright (32 bytes each, starting at offset 0x16)
                        title = header[0x16:0x36].rstrip(b'\x00').decode('latin-1', errors='ignore')
                        author = header[0x36:0x56].rstrip(b'\x00').decode('latin-1', errors='ignore')
                        copyright_text = header[0x56:0x76].rstrip(b'\x00').decode('latin-1', errors='ignore')

                        if title:
                            info_lines.append(f"Title: {title}")
                        if author:
                            info_lines.append(f"Author: {author}")
                        if copyright_text:
                            info_lines.append(f"Copyright: {copyright_text}")
            except Exception as e:
                info_lines.append(f"Note: Could not extract SID header: {e}")

            self.original_info.write_text('\n'.join(info_lines), encoding='utf-8')
            print(f"  [OK] Created {self.original_info.name}")
        except Exception as e:
            print(f"  [WARN] Could not create info file: {e}")

        return True

    def step1_convert_sid_to_sf2(self):
        """Step 1: Convert SID -> SF2"""
        print("\n[1/8] Converting SID -> SF2...")

        # Use the scripts/sid_to_sf2.py path
        script_path = os.path.join(script_dir, 'sid_to_sf2.py')

        cmd = [
            sys.executable, script_path,
            str(self.sid_file),
            str(self.sf2_file),
            '--driver', 'driver11'
        ]

        success, output = self.run_command(cmd, "Running sid_to_sf2.py")

        self.results['steps']['sid_to_sf2'] = {
            'success': success,
            'output_file': str(self.sf2_file),
            'exists': self.sf2_file.exists(),
            'size': self.sf2_file.stat().st_size if self.sf2_file.exists() else 0
        }

        if success and self.sf2_file.exists():
            print(f"  [OK] Created {self.sf2_file} ({self.sf2_file.stat().st_size} bytes)")
        else:
            print(f"  [FAIL] Failed to create SF2 file")
            print(f"  Error: {output}")

        return success

    def step2_pack_sf2_to_sid(self):
        """Step 2: Pack SF2 -> SID using Python packer"""
        print("\n[2/8] Packing SF2 -> SID (with relocation)...")

        try:
            success = pack_sf2_to_sid(
                self.sf2_file,
                self.exported_sid,
                name=self.base_name,
                author='Roundtrip Test',
                copyright_str=datetime.now().strftime('%Y'),
                dest_address=0x1000,
                zp_address=0xFC
            )
        except Exception as e:
            success = False
            output = str(e)

        self.results['steps']['sf2pack'] = {
            'success': success,
            'output_file': str(self.exported_sid),
            'exists': self.exported_sid.exists(),
            'size': self.exported_sid.stat().st_size if self.exported_sid.exists() else 0,
            'output': 'Python packer (sidm2.sf2_packer)'
        }

        if success and self.exported_sid.exists():
            print(f"  [OK] Created {self.exported_sid} ({self.exported_sid.stat().st_size} bytes)")
        else:
            print(f"  [FAIL] Failed to pack SF2")

        return success

    def step3_render_original_wav(self):
        """Step 3: Render original SID -> WAV"""
        print("\n[3/8] Rendering original SID -> WAV...")

        cmd = [
            str(Path('tools/SID2WAV.EXE').absolute()),
            '-16',           # 16-bit
            '-s',            # Stereo
            '-f44100',       # 44.1kHz
            f'-t{self.duration}',  # Duration
            str(self.sid_file.absolute()),
            str(self.original_wav.absolute())
        ]

        success, output = self.run_command(cmd, "Running SID2WAV on original", capture_output=False)

        self.results['steps']['original_wav'] = {
            'success': success,
            'output_file': str(self.original_wav),
            'exists': self.original_wav.exists(),
            'size': self.original_wav.stat().st_size if self.original_wav.exists() else 0
        }

        if success and self.original_wav.exists():
            size_kb = self.original_wav.stat().st_size / 1024
            print(f"  [OK] Created {self.original_wav} ({size_kb:.1f} KB)")
        else:
            print(f"  [FAIL] Failed to render original WAV")

        return success

    def step4_render_exported_wav(self):
        """Step 4: Render exported SID -> WAV"""
        print("\n[4/8] Rendering exported SID -> WAV...")

        cmd = [
            str(Path('tools/SID2WAV.EXE').absolute()),
            '-16',           # 16-bit
            '-s',            # Stereo
            '-f44100',       # 44.1kHz
            f'-t{self.duration}',  # Duration
            str(self.exported_sid.absolute()),
            str(self.exported_wav.absolute())
        ]

        success, output = self.run_command(cmd, "Running SID2WAV on exported", capture_output=False)

        self.results['steps']['exported_wav'] = {
            'success': success,
            'output_file': str(self.exported_wav),
            'exists': self.exported_wav.exists(),
            'size': self.exported_wav.stat().st_size if self.exported_wav.exists() else 0
        }

        if success and self.exported_wav.exists():
            size_kb = self.exported_wav.stat().st_size / 1024
            print(f"  [OK] Created {self.exported_wav} ({size_kb:.1f} KB)")
        else:
            print(f"  [FAIL] Failed to render exported WAV")

        return success

    def step5_siddump_original(self):
        """Step 5: Analyze original SID with siddump"""
        print("\n[5/8] Analyzing original SID with siddump...")

        cmd = [
            str(Path('tools/siddump.exe').absolute()),
            str(self.sid_file.absolute()),
            f'-t{self.duration}'
        ]

        success, output = self.run_command(cmd, "Running siddump on original")

        if success:
            self.original_dump.write_text(output, encoding='utf-8')
            print(f"  [OK] Created {self.original_dump}")
        else:
            print(f"  [FAIL] Siddump failed on original")

        self.results['steps']['siddump_original'] = {
            'success': success,
            'output_file': str(self.original_dump),
            'lines': len(output.split('\n')) if success else 0
        }

        return success

    def step6_siddump_exported(self):
        """Step 6: Analyze exported SID with siddump"""
        print("\n[6/8] Analyzing exported SID with siddump...")

        cmd = [
            str(Path('tools/siddump.exe').absolute()),
            str(self.exported_sid.absolute()),
            f'-t{self.duration}'
        ]

        success, output = self.run_command(cmd, "Running siddump on exported")

        if success:
            self.exported_dump.write_text(output, encoding='utf-8')
            print(f"  [OK] Created {self.exported_dump}")
        else:
            print(f"  [FAIL] Siddump failed on exported")

        self.results['steps']['siddump_exported'] = {
            'success': success,
            'output_file': str(self.exported_dump),
            'lines': len(output.split('\n')) if success else 0
        }

        return success

    def step7_generate_report(self):
        """Step 7: Generate detailed HTML report"""
        print("\n[7/8] Generating detailed report...")

        # Compare file sizes
        comparison = self.compare_results()

        # Generate HTML report
        html = self.generate_html_report(comparison)

        self.report_file.write_text(html, encoding='utf-8')
        print(f"  [OK] Created {self.report_file}")

        return True

    def compare_results(self):
        """Compare original vs exported"""
        comparison = {
            'file_sizes': {},
            'wav_comparison': {},
            'siddump_comparison': {}
        }

        # File size comparison
        if self.sid_file.exists() and self.exported_sid.exists():
            orig_size = self.sid_file.stat().st_size
            export_size = self.exported_sid.stat().st_size
            comparison['file_sizes'] = {
                'original': orig_size,
                'exported': export_size,
                'diff': export_size - orig_size,
                'diff_percent': ((export_size - orig_size) / orig_size * 100) if orig_size > 0 else 0
            }

        # WAV file comparison
        if self.original_wav.exists() and self.exported_wav.exists():
            orig_wav_size = self.original_wav.stat().st_size
            export_wav_size = self.exported_wav.stat().st_size
            comparison['wav_comparison'] = {
                'original': orig_wav_size,
                'exported': export_wav_size,
                'diff': export_wav_size - orig_wav_size,
                'same_size': orig_wav_size == export_wav_size
            }

        # Siddump comparison
        if self.original_dump.exists() and self.exported_dump.exists():
            orig_lines = self.original_dump.read_text(encoding='utf-8').split('\n')
            export_lines = self.exported_dump.read_text(encoding='utf-8').split('\n')

            # Extract register writes (ignore header lines)
            orig_registers = [l for l in orig_lines if l.startswith('|') and not l.startswith('|---')]
            export_registers = [l for l in export_lines if l.startswith('|') and not l.startswith('|---')]

            # Count differences
            matching_lines = sum(1 for o, e in zip(orig_registers, export_registers) if o == e)

            comparison['siddump_comparison'] = {
                'original_lines': len(orig_registers),
                'exported_lines': len(export_registers),
                'matching_lines': matching_lines,
                'match_percent': (matching_lines / len(orig_registers) * 100) if orig_registers else 0
            }

        return comparison

    def generate_html_report(self, comparison):
        """Generate HTML report"""

        # Calculate overall success
        all_steps_success = all(
            step.get('success', False)
            for step in self.results['steps'].values()
        )

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Round-trip Validation Report - {self.base_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }}
        .success {{ color: #27ae60; font-weight: bold; }}
        .failure {{ color: #e74c3c; font-weight: bold; }}
        .warning {{ color: #f39c12; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #3498db; color: white; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-label {{ font-weight: bold; color: #7f8c8d; }}
        .metric-value {{ font-size: 1.2em; color: #2c3e50; }}
        .status-box {{ padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .status-success {{ background: #d4edda; border-left: 4px solid #28a745; }}
        .status-failure {{ background: #f8d7da; border-left: 4px solid #dc3545; }}
        pre {{ background: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; }}
        .file-list {{ list-style: none; padding: 0; }}
        .file-list li {{ padding: 8px; margin: 5px 0; background: #ecf0f1; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1> Round-trip Validation Report</h1>

        <div class="status-box {'status-success' if all_steps_success else 'status-failure'}">
            <h2>Overall Status: {'[OK] PASSED' if all_steps_success else '[FAIL] FAILED'}</h2>
            <p><strong>File:</strong> {self.sid_file}</p>
            <p><strong>Timestamp:</strong> {self.results['timestamp']}</p>
            <p><strong>Duration:</strong> {self.duration} seconds</p>
        </div>

        <h2> Processing Steps</h2>
        <table>
            <tr>
                <th>Step</th>
                <th>Description</th>
                <th>Status</th>
                <th>Output</th>
            </tr>
"""

        steps_info = [
            ('sid_to_sf2', '1. SID → SF2 Conversion', 'sf2_file'),
            ('sf2pack', '2. SF2 → SID Packing', 'exported_sid'),
            ('original_wav', '3. Original SID → WAV', 'original_wav'),
            ('exported_wav', '4. Exported SID → WAV', 'exported_wav'),
            ('siddump_original', '5. Siddump Analysis (Original)', 'original_dump'),
            ('siddump_exported', '6. Siddump Analysis (Exported)', 'exported_dump'),
        ]

        for step_key, description, file_key in steps_info:
            step = self.results['steps'].get(step_key, {})
            success = step.get('success', False)
            status_class = 'success' if success else 'failure'
            status_text = '[OK] Success' if success else '[FAIL] Failed'

            output_info = ''
            if step.get('exists'):
                size = step.get('size', 0)
                if size > 1024:
                    output_info = f"{size / 1024:.1f} KB"
                else:
                    output_info = f"{size} bytes"

            # Add packer info for sf2pack
            if step_key == 'sf2pack':
                output_info += f"<br><small>Python packer</small>"

            # Get relative path for display
            output_file = step.get('output_file', 'N/A')
            if output_file != 'N/A':
                file_path = Path(output_file)
                # Show relative path from song directory
                try:
                    rel_path = file_path.relative_to(self.song_dir)
                    output_file = str(rel_path).replace('\\', '/')
                except ValueError:
                    output_file = file_path.name

            html += f"""
            <tr>
                <td><strong>{description}</strong></td>
                <td>{output_file}</td>
                <td class="{status_class}">{status_text}</td>
                <td>{output_info}</td>
            </tr>
"""

        html += """
        </table>

        <h2> File Size Comparison</h2>
"""

        if comparison['file_sizes']:
            fs = comparison['file_sizes']
            html += f"""
        <div class="metric">
            <span class="metric-label">Original SID:</span>
            <span class="metric-value">{fs['original']} bytes</span>
        </div>
        <div class="metric">
            <span class="metric-label">Exported SID:</span>
            <span class="metric-value">{fs['exported']} bytes</span>
        </div>
        <div class="metric">
            <span class="metric-label">Difference:</span>
            <span class="metric-value">{fs['diff']:+d} bytes ({fs['diff_percent']:+.1f}%)</span>
        </div>
"""

        html += """
        <h2> WAV File Comparison</h2>
"""

        if comparison['wav_comparison']:
            wc = comparison['wav_comparison']
            html += f"""
        <div class="metric">
            <span class="metric-label">Original WAV:</span>
            <span class="metric-value">{wc['original'] / 1024:.1f} KB</span>
        </div>
        <div class="metric">
            <span class="metric-label">Exported WAV:</span>
            <span class="metric-value">{wc['exported'] / 1024:.1f} KB</span>
        </div>
        <div class="metric">
            <span class="metric-label">Same Size:</span>
            <span class="metric-value {'success' if wc['same_size'] else 'warning'}">{'Yes [OK]' if wc['same_size'] else 'No (differs by ' + str(wc['diff']) + ' bytes)'}</span>
        </div>
"""

        html += """
        <h2> Siddump Register Comparison</h2>
"""

        if comparison['siddump_comparison']:
            sc = comparison['siddump_comparison']
            match_class = 'success' if sc['match_percent'] > 95 else 'warning' if sc['match_percent'] > 80 else 'failure'
            html += f"""
        <div class="metric">
            <span class="metric-label">Original Frames:</span>
            <span class="metric-value">{sc['original_lines']}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Exported Frames:</span>
            <span class="metric-value">{sc['exported_lines']}</span>
        </div>
        <div class="metric">
            <span class="metric-label">Matching:</span>
            <span class="metric-value {match_class}">{sc['matching_lines']} ({sc['match_percent']:.1f}%)</span>
        </div>
"""

        html += """
        <h2> Generated Files</h2>
        <ul class="file-list">
"""

        for file_path in [self.original_sid_copy, self.sf2_file, self.exported_sid,
                         self.original_wav, self.exported_wav, self.original_dump,
                         self.exported_dump, self.original_info, self.exported_info]:
            if file_path.exists():
                size = file_path.stat().st_size
                size_str = f"{size / 1024:.1f} KB" if size > 1024 else f"{size} bytes"
                # Show relative path from song directory
                try:
                    rel_path = file_path.relative_to(self.song_dir)
                    display_path = str(rel_path).replace('\\', '/')
                except ValueError:
                    display_path = file_path.name
                html += f"            <li>{display_path} - {size_str}</li>\n"

        html += f"""
        </ul>

        <h2> Next Steps</h2>
        <ul>
            <li>Listen to <code>Original/{self.base_name}.wav</code> and <code>New/{self.base_name}_exported.wav</code> to compare audio quality</li>
            <li>Review <code>Original/{self.base_name}.dump</code> vs <code>New/{self.base_name}_exported.dump</code> for register differences</li>
            <li>Test <code>New/{self.base_name}_exported.sid</code> in a SID player (VICE, sidplayfp, etc.)</li>
            <li>Load <code>New/{self.base_name}_converted.sf2</code> in SID Factory II to verify it plays correctly</li>
        </ul>

        <p style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #7f8c8d;">
            Generated by Round-trip Validator | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>
"""

        return html

    def run_all(self):
        """Run complete validation workflow"""
        print("=" * 70)
        print(f"Round-trip Validation: {self.sid_file}")
        print("=" * 70)

        # Run all steps
        steps = [
            self.step0_setup_original_files,
            self.step1_convert_sid_to_sf2,
            self.step2_pack_sf2_to_sid,
            self.step3_render_original_wav,
            self.step4_render_exported_wav,
            self.step5_siddump_original,
            self.step6_siddump_exported,
            self.step7_generate_report
        ]

        for step_func in steps:
            if not step_func():
                print(f"\n[WARN] Warning: {step_func.__name__} failed, continuing anyway...")

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        all_success = all(step.get('success', False) for step in self.results['steps'].values())

        if all_success:
            print("[OK] All steps completed successfully!")
        else:
            print("[WARN] Some steps failed, check report for details")

        print(f"\n Report: {self.report_file}")
        print(f" Output directory: {self.output_dir}")

        return all_success


def main():
    parser = argparse.ArgumentParser(description='Round-trip SID validation test')
    parser.add_argument('sid_file', help='Input SID file')
    parser.add_argument('--duration', '-t', type=int, default=30, help='Playback duration in seconds (default: 30)')
    parser.add_argument('--output', '-o', default='roundtrip_output', help='Output directory (default: roundtrip_output)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    try:
        if not os.path.exists(args.sid_file):
            raise errors.FileNotFoundError(
                path=args.sid_file,
                context="input SID file",
                suggestions=[
                    f"Check the file path: {args.sid_file}",
                    "Use absolute path instead of relative",
                    "Verify the file extension is .sid"
                ],
                docs_link="guides/TROUBLESHOOTING.md#1-file-not-found-issues"
            )

        validator = RoundtripValidator(
            args.sid_file,
            output_dir=args.output,
            duration=args.duration,
            verbose=args.verbose
        )

        success = validator.run_all()
        return 0 if success else 1

    except errors.SIDMError as e:
        # Custom error - already has helpful formatting
        print(str(e))
        return 1
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
