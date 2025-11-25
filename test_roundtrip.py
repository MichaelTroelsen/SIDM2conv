#!/usr/bin/env python3
"""
Round-trip validation test: SID → SF2 → SID

Complete automated testing workflow:
1. Convert SID → SF2 (sid_to_sf2.py)
2. Pack SF2 → SID (sf2pack.exe)
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


class RoundtripValidator:
    def __init__(self, sid_file, output_dir="roundtrip_output", duration=30, verbose=False):
        self.sid_file = Path(sid_file)
        self.output_dir = Path(output_dir)
        self.duration = duration
        self.verbose = verbose
        self.base_name = self.sid_file.stem

        # Create output directory
        self.output_dir.mkdir(exist_ok=True)

        # Output files
        self.sf2_file = self.output_dir / f"{self.base_name}_converted.sf2"
        self.exported_sid = self.output_dir / f"{self.base_name}_exported.sid"
        self.original_wav = self.output_dir / f"{self.base_name}_original.wav"
        self.exported_wav = self.output_dir / f"{self.base_name}_exported.wav"
        self.original_dump = self.output_dir / f"{self.base_name}_original.dump"
        self.exported_dump = self.output_dir / f"{self.base_name}_exported.dump"
        self.report_file = self.output_dir / f"{self.base_name}_roundtrip_report.html"

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

    def step1_convert_sid_to_sf2(self):
        """Step 1: Convert SID -> SF2"""
        print("\n[1/7] Converting SID -> SF2...")

        cmd = [
            'python', 'sid_to_sf2.py',
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
        """Step 2: Pack SF2 -> SID using sf2pack"""
        print("\n[2/7] Packing SF2 -> SID (with relocation)...")

        cmd = [
            str(Path('tools/sf2pack/sf2pack.exe').absolute()),
            str(self.sf2_file),
            str(self.exported_sid),
            '--address', '0x1000',
            '--zp', '0x02',
            '--title', self.base_name,
            '--author', 'Roundtrip Test',
            '--copyright', datetime.now().strftime('%Y')
        ]

        if self.verbose:
            cmd.append('-v')

        success, output = self.run_command(cmd, "Running sf2pack.exe")

        self.results['steps']['sf2pack'] = {
            'success': success,
            'output_file': str(self.exported_sid),
            'exists': self.exported_sid.exists(),
            'size': self.exported_sid.stat().st_size if self.exported_sid.exists() else 0,
            'output': output
        }

        # Extract relocation stats from output
        if 'Relocations:' in output:
            for line in output.split('\n'):
                if 'Relocations:' in line:
                    self.results['steps']['sf2pack']['relocation_info'] = line.strip()
                    break

        if success and self.exported_sid.exists():
            print(f"  [OK] Created {self.exported_sid} ({self.exported_sid.stat().st_size} bytes)")
            if 'relocation_info' in self.results['steps']['sf2pack']:
                print(f"  {self.results['steps']['sf2pack']['relocation_info']}")
        else:
            print(f"  [FAIL] Failed to pack SF2")
            print(f"  Error: {output}")

        return success

    def step3_render_original_wav(self):
        """Step 3: Render original SID -> WAV"""
        print("\n[3/7] Rendering original SID -> WAV...")

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
        print("\n[4/7] Rendering exported SID -> WAV...")

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
        print("\n[5/7] Analyzing original SID with siddump...")

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
        print("\n[6/7] Analyzing exported SID with siddump...")

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
        print("\n[7/7] Generating detailed report...")

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

            # Add relocation info for sf2pack
            if step_key == 'sf2pack' and 'relocation_info' in step:
                output_info += f"<br><small>{step['relocation_info']}</small>"

            html += f"""
            <tr>
                <td><strong>{description}</strong></td>
                <td>{step.get('output_file', 'N/A')}</td>
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

        for file_path in [self.sf2_file, self.exported_sid, self.original_wav,
                         self.exported_wav, self.original_dump, self.exported_dump]:
            if file_path.exists():
                size = file_path.stat().st_size
                size_str = f"{size / 1024:.1f} KB" if size > 1024 else f"{size} bytes"
                html += f"            <li>{file_path.name} - {size_str}</li>\n"

        html += f"""
        </ul>

        <h2> Next Steps</h2>
        <ul>
            <li>Listen to <code>{self.original_wav.name}</code> and <code>{self.exported_wav.name}</code> to compare audio quality</li>
            <li>Review <code>{self.original_dump.name}</code> vs <code>{self.exported_dump.name}</code> for register differences</li>
            <li>Test <code>{self.exported_sid.name}</code> in a SID player (VICE, sidplayfp, etc.)</li>
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

    if not os.path.exists(args.sid_file):
        print(f"Error: File not found: {args.sid_file}")
        return 1

    validator = RoundtripValidator(
        args.sid_file,
        output_dir=args.output,
        duration=args.duration,
        verbose=args.verbose
    )

    success = validator.run_all()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
