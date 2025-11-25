#!/usr/bin/env python3
"""
SID Accuracy Validation Tool

This tool plays a SID file and records all information needed to validate
100% accuracy with an SF2 file that is converted back to SID format.

It captures:
- All SID register writes (frame-by-frame)
- Memory state snapshots
- Voice parameters (ADSR, frequency, waveform, pulse width)
- Filter settings
- Timing information
- Pattern matching and anomalies

Usage:
    python validate_sid_accuracy.py original.sid exported.sid
    python validate_sid_accuracy.py original.sid exported.sid --duration 60 --output report.html
"""

__version__ = "0.1.0"
__date__ = "2025-11-25"

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import json


class SIDRegisterCapture:
    """Captures SID register writes frame by frame"""

    # SID register names
    REGISTER_NAMES = {
        0x00: "Voice1_FreqLo", 0x01: "Voice1_FreqHi",
        0x02: "Voice1_PulseLo", 0x03: "Voice1_PulseHi",
        0x04: "Voice1_Control", 0x05: "Voice1_Attack_Decay",
        0x06: "Voice1_Sustain_Release",
        0x07: "Voice2_FreqLo", 0x08: "Voice2_FreqHi",
        0x09: "Voice2_PulseLo", 0x0A: "Voice2_PulseHi",
        0x0B: "Voice2_Control", 0x0C: "Voice2_Attack_Decay",
        0x0D: "Voice2_Sustain_Release",
        0x0E: "Voice3_FreqLo", 0x0F: "Voice3_FreqHi",
        0x10: "Voice3_PulseLo", 0x11: "Voice3_PulseHi",
        0x12: "Voice3_Control", 0x13: "Voice3_Attack_Decay",
        0x14: "Voice3_Sustain_Release",
        0x15: "FilterCutoffLo", 0x16: "FilterCutoffHi",
        0x17: "FilterResonance_Routing", 0x18: "FilterMode_Volume"
    }

    def __init__(self, sid_path: str, duration: int = 30):
        self.sid_path = Path(sid_path)
        self.duration = duration
        self.frames = []
        self.register_history = {i: [] for i in range(0x19)}
        self.stats = {
            'total_frames': 0,
            'total_writes': 0,
            'unique_patterns': 0,
            'voice_activity': {1: 0, 2: 0, 3: 0}
        }

    def capture(self) -> bool:
        """Capture SID register writes using siddump"""
        siddump_exe = Path('tools/siddump.exe')
        if not siddump_exe.exists():
            print(f"ERROR: siddump.exe not found at {siddump_exe}")
            return False

        print(f"Capturing SID registers from: {self.sid_path.name}")
        print(f"Duration: {self.duration} seconds")

        try:
            result = subprocess.run(
                [str(siddump_exe.absolute()),
                 str(self.sid_path.absolute()),
                 '-z',  # Show cycle counts
                 f'-t{self.duration}'],
                capture_output=True,
                text=True,
                timeout=self.duration + 10
            )

            if result.returncode != 0:
                print(f"ERROR: siddump failed: {result.stderr}")
                return False

            # Parse siddump output
            self._parse_siddump_output(result.stdout)
            return True

        except subprocess.TimeoutExpired:
            print(f"ERROR: siddump timed out after {self.duration + 10} seconds")
            return False
        except Exception as e:
            print(f"ERROR: Failed to run siddump: {e}")
            return False

    def _parse_siddump_output(self, output: str):
        """Parse siddump output into frame-by-frame register data"""
        current_frame = {}
        frame_cycle = 0

        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Look for register writes: "D400: 01 02 03 ..."
            if line.startswith('D4'):
                parts = line.split(':')
                if len(parts) == 2:
                    addr_str = parts[0].strip()
                    values_str = parts[1].strip()

                    try:
                        base_addr = int(addr_str, 16)
                        values = [int(v, 16) for v in values_str.split() if v]

                        # Record each register value
                        for offset, value in enumerate(values):
                            reg = (base_addr - 0xD400 + offset) & 0xFF
                            if reg < 0x19:  # Valid SID register
                                current_frame[reg] = value
                                self.register_history[reg].append({
                                    'frame': self.stats['total_frames'],
                                    'cycle': frame_cycle,
                                    'value': value
                                })
                                self.stats['total_writes'] += 1
                    except ValueError:
                        continue

            # Check for frame boundaries (look for cycle counts)
            elif line.startswith('Cycle:') or line.startswith('Frame:'):
                if current_frame:
                    self.frames.append(current_frame.copy())
                    self.stats['total_frames'] += 1
                    current_frame = {}
                    frame_cycle = 0

        # Add last frame
        if current_frame:
            self.frames.append(current_frame)
            self.stats['total_frames'] += 1

        print(f"  Captured {self.stats['total_frames']} frames")
        print(f"  Total register writes: {self.stats['total_writes']}")

    def analyze_voice_activity(self):
        """Analyze which voices are active"""
        for frame in self.frames:
            # Check gate bits in control registers
            for voice in range(1, 4):
                control_reg = 0x04 + (voice - 1) * 7
                if control_reg in frame:
                    control = frame[control_reg]
                    if control & 0x01:  # Gate bit
                        self.stats['voice_activity'][voice] += 1

    def get_frequency_table(self, voice: int = 1) -> List[int]:
        """Extract frequency values for a voice"""
        freq_lo_reg = 0x00 + (voice - 1) * 7
        freq_hi_reg = 0x01 + (voice - 1) * 7

        frequencies = []
        for frame in self.frames:
            if freq_lo_reg in frame and freq_hi_reg in frame:
                freq = frame[freq_lo_reg] | (frame[freq_hi_reg] << 8)
                frequencies.append(freq)

        return frequencies

    def get_waveform_sequence(self, voice: int = 1) -> List[int]:
        """Extract waveform control byte sequence for a voice"""
        control_reg = 0x04 + (voice - 1) * 7

        waveforms = []
        for frame in self.frames:
            if control_reg in frame:
                waveforms.append(frame[control_reg])

        return waveforms

    def get_adsr_changes(self, voice: int = 1) -> List[Tuple[int, int, int]]:
        """Extract ADSR envelope changes for a voice"""
        ad_reg = 0x05 + (voice - 1) * 7
        sr_reg = 0x06 + (voice - 1) * 7

        adsr_changes = []
        for frame_idx, frame in enumerate(self.frames):
            if ad_reg in frame or sr_reg in frame:
                ad = frame.get(ad_reg, 0)
                sr = frame.get(sr_reg, 0)
                adsr_changes.append((frame_idx, ad, sr))

        return adsr_changes

    def get_pulse_width_sequence(self, voice: int = 1) -> List[int]:
        """Extract pulse width values for a voice"""
        pw_lo_reg = 0x02 + (voice - 1) * 7
        pw_hi_reg = 0x03 + (voice - 1) * 7

        pulse_widths = []
        for frame in self.frames:
            if pw_lo_reg in frame and pw_hi_reg in frame:
                pw = frame[pw_lo_reg] | ((frame[pw_hi_reg] & 0x0F) << 8)
                pulse_widths.append(pw)

        return pulse_widths

    def get_filter_sequence(self) -> List[Tuple[int, int, int]]:
        """Extract filter cutoff, resonance, and mode values"""
        filters = []
        for frame in self.frames:
            cutoff_lo = frame.get(0x15, 0)
            cutoff_hi = frame.get(0x16, 0)
            cutoff = cutoff_lo | ((cutoff_hi & 0x07) << 8)

            resonance = frame.get(0x17, 0)
            mode = frame.get(0x18, 0)

            if cutoff_lo in frame or cutoff_hi in frame or resonance in frame or mode in frame:
                filters.append((cutoff, resonance, mode))

        return filters

    def export_json(self, output_path: str):
        """Export captured data to JSON"""
        data = {
            'sid_file': str(self.sid_path),
            'duration': self.duration,
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'frames': self.frames,
            'register_history': {
                self.REGISTER_NAMES.get(reg, f"Reg_{reg:02X}"): history
                for reg, history in self.register_history.items()
                if history
            }
        }

        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"  Exported data to: {output_path}")


class SIDComparator:
    """Compares two SID files for accuracy validation"""

    def __init__(self, original_capture: SIDRegisterCapture, exported_capture: SIDRegisterCapture):
        self.original = original_capture
        self.exported = exported_capture
        self.differences = []
        self.accuracy_score = 0.0

    def compare(self) -> Dict:
        """Compare original and exported SID captures"""
        print("\nComparing SID files...")

        results = {
            'frame_count_match': False,
            'frame_accuracy': 0.0,
            'register_accuracy': {},
            'voice_accuracy': {},
            'filter_accuracy': 0.0,
            'timing_drift': 0,
            'differences': []
        }

        # Compare frame counts
        orig_frames = len(self.original.frames)
        exp_frames = len(self.exported.frames)
        results['frame_count_match'] = (orig_frames == exp_frames)

        if not results['frame_count_match']:
            results['differences'].append(
                f"Frame count mismatch: original={orig_frames}, exported={exp_frames}"
            )

        # Compare frame-by-frame
        max_frames = min(orig_frames, exp_frames)
        matching_frames = 0

        for frame_idx in range(max_frames):
            orig_frame = self.original.frames[frame_idx]
            exp_frame = self.exported.frames[frame_idx]

            # Check if frames are identical
            if self._compare_frames(orig_frame, exp_frame):
                matching_frames += 1
            else:
                diff = self._get_frame_differences(frame_idx, orig_frame, exp_frame)
                if len(results['differences']) < 100:  # Limit stored differences
                    results['differences'].extend(diff)

        results['frame_accuracy'] = (matching_frames / max_frames * 100) if max_frames > 0 else 0.0

        # Compare per-register accuracy
        for reg in range(0x19):
            reg_name = SIDRegisterCapture.REGISTER_NAMES.get(reg, f"Reg_{reg:02X}")
            orig_history = self.original.register_history[reg]
            exp_history = self.exported.register_history[reg]

            if not orig_history and not exp_history:
                continue

            matches = 0
            total = max(len(orig_history), len(exp_history))

            for i in range(min(len(orig_history), len(exp_history))):
                if orig_history[i]['value'] == exp_history[i]['value']:
                    matches += 1

            accuracy = (matches / total * 100) if total > 0 else 0.0
            results['register_accuracy'][reg_name] = {
                'accuracy': accuracy,
                'orig_writes': len(orig_history),
                'exp_writes': len(exp_history),
                'matches': matches
            }

        # Compare voice activity
        for voice in range(1, 4):
            orig_freq = self.original.get_frequency_table(voice)
            exp_freq = self.exported.get_frequency_table(voice)

            orig_wave = self.original.get_waveform_sequence(voice)
            exp_wave = self.exported.get_waveform_sequence(voice)

            freq_matches = sum(1 for o, e in zip(orig_freq, exp_freq) if o == e)
            wave_matches = sum(1 for o, e in zip(orig_wave, exp_wave) if o == e)

            freq_accuracy = (freq_matches / len(orig_freq) * 100) if orig_freq else 0.0
            wave_accuracy = (wave_matches / len(orig_wave) * 100) if orig_wave else 0.0

            results['voice_accuracy'][f'Voice{voice}'] = {
                'frequency_accuracy': freq_accuracy,
                'waveform_accuracy': wave_accuracy,
                'freq_matches': f"{freq_matches}/{len(orig_freq)}",
                'wave_matches': f"{wave_matches}/{len(orig_wave)}"
            }

        # Compare filter settings
        orig_filter = self.original.get_filter_sequence()
        exp_filter = self.exported.get_filter_sequence()

        filter_matches = sum(1 for o, e in zip(orig_filter, exp_filter) if o == e)
        results['filter_accuracy'] = (filter_matches / len(orig_filter) * 100) if orig_filter else 0.0

        # Calculate overall accuracy
        self.accuracy_score = self._calculate_overall_accuracy(results)
        results['overall_accuracy'] = self.accuracy_score

        return results

    def _compare_frames(self, frame1: Dict, frame2: Dict) -> bool:
        """Compare two frames for exact match"""
        if len(frame1) != len(frame2):
            return False

        for reg, value in frame1.items():
            if frame2.get(reg) != value:
                return False

        return True

    def _get_frame_differences(self, frame_idx: int, orig: Dict, exp: Dict) -> List[str]:
        """Get detailed differences between two frames"""
        diffs = []

        all_regs = set(orig.keys()) | set(exp.keys())

        for reg in sorted(all_regs):
            orig_val = orig.get(reg, None)
            exp_val = exp.get(reg, None)

            if orig_val != exp_val:
                reg_name = SIDRegisterCapture.REGISTER_NAMES.get(reg, f"${reg:02X}")
                orig_str = f"${orig_val:02X}" if orig_val is not None else "---"
                exp_str = f"${exp_val:02X}" if exp_val is not None else "---"

                diffs.append(
                    f"Frame {frame_idx}, {reg_name}: original={orig_str}, exported={exp_str}"
                )

        return diffs

    def _calculate_overall_accuracy(self, results: Dict) -> float:
        """Calculate overall accuracy score (0-100%)"""
        scores = []

        # Frame accuracy (40% weight)
        scores.append(results['frame_accuracy'] * 0.4)

        # Voice accuracy (30% weight)
        voice_scores = []
        for voice_data in results['voice_accuracy'].values():
            voice_score = (voice_data['frequency_accuracy'] + voice_data['waveform_accuracy']) / 2
            voice_scores.append(voice_score)
        if voice_scores:
            scores.append(sum(voice_scores) / len(voice_scores) * 0.3)

        # Register accuracy (20% weight)
        reg_scores = [data['accuracy'] for data in results['register_accuracy'].values()]
        if reg_scores:
            scores.append(sum(reg_scores) / len(reg_scores) * 0.2)

        # Filter accuracy (10% weight)
        scores.append(results['filter_accuracy'] * 0.1)

        return sum(scores)


def generate_html_report(original: SIDRegisterCapture, exported: SIDRegisterCapture,
                         comparison: Dict, output_path: str):
    """Generate comprehensive HTML report"""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>SID Accuracy Validation Report</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
        }}
        .score {{
            font-size: 48px;
            font-weight: bold;
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            border-radius: 8px;
        }}
        .score.excellent {{ color: #27ae60; background: #e8f8f5; }}
        .score.good {{ color: #f39c12; background: #fef5e7; }}
        .score.poor {{ color: #e74c3c; background: #fadbd8; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #ecf0f1;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #3498db;
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 14px;
            text-transform: uppercase;
        }}
        .stat-card .value {{
            font-size: 24px;
            font-weight: bold;
            color: #34495e;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #3498db;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
        .diff-list {{
            max-height: 400px;
            overflow-y: auto;
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }}
        .diff-item {{
            padding: 4px 0;
            border-bottom: 1px solid #e9ecef;
        }}
        .metadata {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #ecf0f1;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
        }}
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #3498db, #2ecc71);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎵 SID Accuracy Validation Report</h1>

        <div class="metadata">
            <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            <strong>Original SID:</strong> {original.sid_path.name}<br>
            <strong>Exported SID:</strong> {exported.sid_path.name}<br>
            <strong>Duration:</strong> {original.duration} seconds
        </div>

        <h2>Overall Accuracy Score</h2>
        <div class="score {'excellent' if comparison['overall_accuracy'] >= 95 else 'good' if comparison['overall_accuracy'] >= 80 else 'poor'}">
            {comparison['overall_accuracy']:.2f}%
        </div>

        <div class="progress-bar">
            <div class="progress-fill" style="width: {comparison['overall_accuracy']:.1f}%">
                {comparison['overall_accuracy']:.1f}%
            </div>
        </div>

        <h2>Summary Statistics</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Frame Accuracy</h3>
                <div class="value">{comparison['frame_accuracy']:.1f}%</div>
            </div>
            <div class="stat-card">
                <h3>Filter Accuracy</h3>
                <div class="value">{comparison['filter_accuracy']:.1f}%</div>
            </div>
            <div class="stat-card">
                <h3>Total Frames</h3>
                <div class="value">{original.stats['total_frames']}</div>
            </div>
            <div class="stat-card">
                <h3>Total Writes</h3>
                <div class="value">{original.stats['total_writes']}</div>
            </div>
        </div>

        <h2>Voice Accuracy</h2>
        <table>
            <tr>
                <th>Voice</th>
                <th>Frequency Accuracy</th>
                <th>Waveform Accuracy</th>
                <th>Frequency Matches</th>
                <th>Waveform Matches</th>
            </tr>
"""

    for voice_name, voice_data in comparison['voice_accuracy'].items():
        html += f"""
            <tr>
                <td><strong>{voice_name}</strong></td>
                <td>{voice_data['frequency_accuracy']:.2f}%</td>
                <td>{voice_data['waveform_accuracy']:.2f}%</td>
                <td>{voice_data['freq_matches']}</td>
                <td>{voice_data['wave_matches']}</td>
            </tr>
"""

    html += """
        </table>

        <h2>Register-Level Accuracy</h2>
        <table>
            <tr>
                <th>Register</th>
                <th>Accuracy</th>
                <th>Original Writes</th>
                <th>Exported Writes</th>
                <th>Matches</th>
            </tr>
"""

    for reg_name, reg_data in sorted(comparison['register_accuracy'].items()):
        html += f"""
            <tr>
                <td><strong>{reg_name}</strong></td>
                <td>{reg_data['accuracy']:.2f}%</td>
                <td>{reg_data['orig_writes']}</td>
                <td>{reg_data['exp_writes']}</td>
                <td>{reg_data['matches']}</td>
            </tr>
"""

    html += """
        </table>
"""

    # Add differences section if there are any
    if comparison['differences']:
        html += f"""
        <h2>Differences Found ({len(comparison['differences'])} items)</h2>
        <div class="diff-list">
"""
        for diff in comparison['differences'][:500]:  # Limit to first 500
            html += f'            <div class="diff-item">{diff}</div>\n'

        if len(comparison['differences']) > 500:
            html += f'            <div class="diff-item"><em>... and {len(comparison["differences"]) - 500} more differences</em></div>\n'

        html += """
        </div>
"""

    html += """
        <h2>Recommendations</h2>
        <ul>
"""

    # Generate recommendations based on accuracy
    if comparison['overall_accuracy'] >= 99:
        html += "            <li>✅ <strong>Excellent!</strong> Conversion is nearly perfect. Minor tweaks may achieve 100% accuracy.</li>\n"
    elif comparison['overall_accuracy'] >= 95:
        html += "            <li>⚠️ Very good accuracy. Review the differences list to identify remaining issues.</li>\n"
    elif comparison['overall_accuracy'] >= 80:
        html += "            <li>⚠️ Good accuracy but significant differences remain. Focus on register write sequences.</li>\n"
    else:
        html += "            <li>❌ Low accuracy. Major issues in conversion pipeline. Review SF2 table extraction and packing logic.</li>\n"

    # Specific recommendations
    if comparison['frame_accuracy'] < 90:
        html += "            <li>🔍 Frame-level accuracy is low. Check timing and frame synchronization.</li>\n"

    if comparison['filter_accuracy'] < 90:
        html += "            <li>🔍 Filter accuracy is low. Review filter table extraction and cutoff/resonance values.</li>\n"

    for voice_name, voice_data in comparison['voice_accuracy'].items():
        if voice_data['frequency_accuracy'] < 90:
            html += f"            <li>🔍 {voice_name} frequency accuracy is low. Check note frequency calculation.</li>\n"
        if voice_data['waveform_accuracy'] < 90:
            html += f"            <li>🔍 {voice_name} waveform accuracy is low. Check wave table and control register handling.</li>\n"

    html += """
        </ul>
    </div>
</body>
</html>
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ HTML report generated: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='SID Accuracy Validation Tool - Compare original and exported SID files'
    )
    parser.add_argument('original', help='Original SID file')
    parser.add_argument('exported', help='Exported SID file (from SF2 conversion)')
    parser.add_argument('--duration', '-d', type=int, default=30,
                        help='Playback duration in seconds (default: 30)')
    parser.add_argument('--output', '-o', help='Output HTML report path (default: auto-generated)')
    parser.add_argument('--json', help='Export raw JSON data')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')

    args = parser.parse_args()

    # Validate input files
    if not os.path.exists(args.original):
        print(f"ERROR: Original SID file not found: {args.original}")
        return 1

    if not os.path.exists(args.exported):
        print(f"ERROR: Exported SID file not found: {args.exported}")
        return 1

    print("=" * 70)
    print("SID Accuracy Validation Tool")
    print("=" * 70)
    print()

    # Capture original SID
    print("[1/3] Capturing original SID...")
    original_capture = SIDRegisterCapture(args.original, args.duration)
    if not original_capture.capture():
        return 1
    original_capture.analyze_voice_activity()

    # Capture exported SID
    print("\n[2/3] Capturing exported SID...")
    exported_capture = SIDRegisterCapture(args.exported, args.duration)
    if not exported_capture.capture():
        return 1
    exported_capture.analyze_voice_activity()

    # Compare captures
    print("\n[3/3] Comparing captures...")
    comparator = SIDComparator(original_capture, exported_capture)
    comparison_results = comparator.compare()

    # Display results
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)
    print(f"\nOverall Accuracy: {comparison_results['overall_accuracy']:.2f}%")
    print(f"Frame Accuracy:   {comparison_results['frame_accuracy']:.2f}%")
    print(f"Filter Accuracy:  {comparison_results['filter_accuracy']:.2f}%")
    print(f"\nVoice Accuracy:")
    for voice_name, voice_data in comparison_results['voice_accuracy'].items():
        print(f"  {voice_name}:")
        print(f"    Frequency: {voice_data['frequency_accuracy']:.2f}%")
        print(f"    Waveform:  {voice_data['waveform_accuracy']:.2f}%")

    print(f"\nDifferences found: {len(comparison_results['differences'])}")

    if args.verbose and comparison_results['differences']:
        print("\nFirst 20 differences:")
        for diff in comparison_results['differences'][:20]:
            print(f"  {diff}")

    # Export JSON if requested
    if args.json:
        print(f"\nExporting JSON data...")
        original_capture.export_json(args.json.replace('.json', '_original.json'))
        exported_capture.export_json(args.json.replace('.json', '_exported.json'))

    # Generate HTML report
    if args.output:
        output_path = args.output
    else:
        base_name = Path(args.original).stem
        output_path = f"validation_{base_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    generate_html_report(original_capture, exported_capture, comparison_results, output_path)

    print("\n" + "=" * 70)

    # Return exit code based on accuracy
    if comparison_results['overall_accuracy'] >= 99:
        print("✅ SUCCESS: 99%+ accuracy achieved!")
        return 0
    elif comparison_results['overall_accuracy'] >= 95:
        print("⚠️  GOOD: 95%+ accuracy achieved")
        return 0
    else:
        print("❌ NEEDS WORK: Accuracy below 95%")
        return 1


if __name__ == '__main__':
    sys.exit(main())
