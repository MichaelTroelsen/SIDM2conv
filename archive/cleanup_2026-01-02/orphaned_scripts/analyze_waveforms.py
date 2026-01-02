#!/usr/bin/env python3
"""
Waveform Analysis Tool for SID to SF2 Conversion

Analyzes and compares WAV files generated from original and exported SID files.
Generates HTML reports with audio players, waveform data, and statistics.

Usage:
    python scripts/analyze_waveforms.py [output_dir]
"""

import wave
import struct
import os
import sys
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from datetime import datetime


class WaveformAnalyzer:
    """Analyzes WAV files and generates comparison reports."""

    def __init__(self, wav_path: str):
        """Initialize analyzer with a WAV file."""
        self.wav_path = Path(wav_path)
        self.params = None
        self.duration = 0
        self.sample_rate = 0
        self.channels = 0
        self.sample_width = 0
        self.num_frames = 0

        if self.wav_path.exists():
            self._read_metadata()

    def _read_metadata(self):
        """Read WAV file metadata."""
        try:
            with wave.open(str(self.wav_path), 'rb') as wav:
                self.params = wav.getparams()
                self.channels = wav.getnchannels()
                self.sample_width = wav.getsampwidth()
                self.sample_rate = wav.getframerate()
                self.num_frames = wav.getnframes()
                self.duration = self.num_frames / self.sample_rate
        except Exception as e:
            print(f"Error reading {self.wav_path}: {e}")

    def get_samples(self, start_second: float = 0, duration: float = 1.0,
                    num_samples: int = 1000) -> List[int]:
        """
        Extract sample values from WAV file.

        Args:
            start_second: Starting position in seconds
            duration: Duration to extract in seconds
            num_samples: Number of samples to extract

        Returns:
            List of sample values (averaged across channels)
        """
        if not self.wav_path.exists():
            return []

        try:
            with wave.open(str(self.wav_path), 'rb') as wav:
                # Calculate frame positions
                start_frame = int(start_second * self.sample_rate)
                end_frame = int((start_second + duration) * self.sample_rate)
                frames_to_read = min(end_frame - start_frame, self.num_frames - start_frame)

                # Position to start
                wav.setpos(start_frame)

                # Read frames
                frames = wav.readframes(frames_to_read)

                # Parse samples based on width
                if self.sample_width == 1:
                    fmt = f'{len(frames)}B'
                    samples = struct.unpack(fmt, frames)
                    samples = [s - 128 for s in samples]  # Convert to signed
                elif self.sample_width == 2:
                    fmt = f'{len(frames)//2}h'
                    samples = struct.unpack(fmt, frames)
                else:
                    return []

                # Average channels if stereo
                if self.channels == 2:
                    samples = [sum(samples[i:i+2])//2 for i in range(0, len(samples), 2)]

                # Downsample to num_samples points
                step = len(samples) // num_samples
                if step < 1:
                    step = 1
                downsampled = samples[::step][:num_samples]

                return downsampled
        except Exception as e:
            print(f"Error extracting samples from {self.wav_path}: {e}")
            return []

    def get_statistics(self) -> Dict:
        """Calculate basic statistics about the WAV file."""
        stats = {
            'file_size': self.wav_path.stat().st_size if self.wav_path.exists() else 0,
            'duration': self.duration,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'bit_depth': self.sample_width * 8,
            'num_frames': self.num_frames,
        }

        # Calculate peak amplitude
        try:
            samples = self.get_samples(duration=self.duration, num_samples=10000)
            if samples:
                stats['peak_amplitude'] = max(abs(min(samples)), abs(max(samples)))
                stats['avg_amplitude'] = sum(abs(s) for s in samples) // len(samples)
            else:
                stats['peak_amplitude'] = 0
                stats['avg_amplitude'] = 0
        except:
            stats['peak_amplitude'] = 0
            stats['avg_amplitude'] = 0

        return stats


def calculate_similarity(samples1: List[int], samples2: List[int]) -> Dict:
    """Calculate similarity metrics between two waveforms."""
    if not samples1 or not samples2:
        return {'correlation': 0.0, 'rmse': 0.0, 'match_rate': 0.0}

    # Ensure same length
    min_len = min(len(samples1), len(samples2))
    s1 = samples1[:min_len]
    s2 = samples2[:min_len]

    # Calculate RMSE (Root Mean Square Error)
    squared_diff = [(a - b) ** 2 for a, b in zip(s1, s2)]
    rmse = (sum(squared_diff) / len(squared_diff)) ** 0.5

    # Calculate simple correlation
    mean1 = sum(s1) / len(s1)
    mean2 = sum(s2) / len(s2)

    numerator = sum((a - mean1) * (b - mean2) for a, b in zip(s1, s2))
    denom1 = sum((a - mean1) ** 2 for a in s1) ** 0.5
    denom2 = sum((b - mean2) ** 2 for b in s2) ** 0.5

    correlation = numerator / (denom1 * denom2) if (denom1 * denom2) > 0 else 0.0

    # Calculate match rate (samples within 10% of each other)
    threshold = 3277  # ~10% of 16-bit range
    matches = sum(1 for a, b in zip(s1, s2) if abs(a - b) < threshold)
    match_rate = matches / len(s1)

    return {
        'correlation': correlation,
        'rmse': rmse,
        'match_rate': match_rate,
    }


def generate_html_report(song_name: str, original_wav: Path, exported_wav: Path,
                         output_path: Path) -> bool:
    """Generate HTML report comparing two WAV files."""

    # Analyze both files
    orig_analyzer = WaveformAnalyzer(str(original_wav))
    exp_analyzer = WaveformAnalyzer(str(exported_wav))

    # Get statistics
    orig_stats = orig_analyzer.get_statistics()
    exp_stats = exp_analyzer.get_statistics()

    # Get waveform samples (first 5 seconds)
    orig_samples = orig_analyzer.get_samples(start_second=0, duration=5.0, num_samples=500)
    exp_samples = exp_analyzer.get_samples(start_second=0, duration=5.0, num_samples=500)

    # Calculate similarity
    similarity = calculate_similarity(orig_samples, exp_samples)

    # Get relative paths for audio files
    orig_rel = os.path.relpath(original_wav, output_path.parent)
    exp_rel = os.path.relpath(exported_wav, output_path.parent)

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{song_name} - Waveform Analysis</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1200px;
            margin: 20px auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .section {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .audio-player {{
            margin: 15px 0;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        .stats-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .stats-table th {{
            background: #667eea;
            color: white;
            padding: 10px;
            text-align: left;
        }}
        .stats-table td {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }}
        .stats-table tr:hover {{
            background: #f8f9fa;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
            padding: 15px;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        canvas {{
            width: 100%;
            height: 200px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        .good {{ color: #28a745; }}
        .warning {{ color: #ffc107; }}
        .bad {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{song_name}</h1>
        <p>Waveform Analysis Report - Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="section">
        <h2>Audio Players</h2>
        <div class="audio-player">
            <h3>Original SID (Laxity NewPlayer)</h3>
            <audio controls style="width: 100%;">
                <source src="{orig_rel.replace(chr(92), '/')}" type="audio/wav">
                Your browser does not support the audio element.
            </audio>
        </div>
        <div class="audio-player">
            <h3>Exported SID (SF2 Driver 11)</h3>
            <audio controls style="width: 100%;">
                <source src="{exp_rel.replace(chr(92), '/')}" type="audio/wav">
                Your browser does not support the audio element.
            </audio>
        </div>
    </div>

    <div class="section">
        <h2>Similarity Metrics</h2>
        <div class="metric">
            <div class="metric-label">Correlation</div>
            <div class="metric-value">{similarity['correlation']:.3f}</div>
        </div>
        <div class="metric">
            <div class="metric-label">RMSE</div>
            <div class="metric-value">{similarity['rmse']:.0f}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Match Rate</div>
            <div class="metric-value">{similarity['match_rate']*100:.1f}%</div>
        </div>
        <p><strong>Note:</strong> Low similarity is expected when comparing different players (Laxity vs SF2).</p>
    </div>

    <div class="section">
        <h2>File Statistics</h2>
        <table class="stats-table">
            <tr>
                <th>Property</th>
                <th>Original</th>
                <th>Exported</th>
                <th>Match</th>
            </tr>
            <tr>
                <td>File Size</td>
                <td>{orig_stats['file_size']:,} bytes</td>
                <td>{exp_stats['file_size']:,} bytes</td>
                <td class="{'good' if orig_stats['file_size'] == exp_stats['file_size'] else 'warning'}">
                    {'\u2713' if orig_stats['file_size'] == exp_stats['file_size'] else '\u2717'}
                </td>
            </tr>
            <tr>
                <td>Duration</td>
                <td>{orig_stats['duration']:.2f}s</td>
                <td>{exp_stats['duration']:.2f}s</td>
                <td class="{'good' if abs(orig_stats['duration'] - exp_stats['duration']) < 0.1 else 'warning'}">
                    {'\u2713' if abs(orig_stats['duration'] - exp_stats['duration']) < 0.1 else '\u2717'}
                </td>
            </tr>
            <tr>
                <td>Sample Rate</td>
                <td>{orig_stats['sample_rate']} Hz</td>
                <td>{exp_stats['sample_rate']} Hz</td>
                <td class="{'good' if orig_stats['sample_rate'] == exp_stats['sample_rate'] else 'warning'}">
                    {'\u2713' if orig_stats['sample_rate'] == exp_stats['sample_rate'] else '\u2717'}
                </td>
            </tr>
            <tr>
                <td>Channels</td>
                <td>{orig_stats['channels']}</td>
                <td>{exp_stats['channels']}</td>
                <td class="{'good' if orig_stats['channels'] == exp_stats['channels'] else 'warning'}">
                    {'\u2713' if orig_stats['channels'] == exp_stats['channels'] else '\u2717'}
                </td>
            </tr>
            <tr>
                <td>Bit Depth</td>
                <td>{orig_stats['bit_depth']} bits</td>
                <td>{exp_stats['bit_depth']} bits</td>
                <td class="{'good' if orig_stats['bit_depth'] == exp_stats['bit_depth'] else 'warning'}">
                    {'\u2713' if orig_stats['bit_depth'] == exp_stats['bit_depth'] else '\u2717'}
                </td>
            </tr>
            <tr>
                <td>Peak Amplitude</td>
                <td>{orig_stats['peak_amplitude']:,}</td>
                <td>{exp_stats['peak_amplitude']:,}</td>
                <td class="{'good' if abs(orig_stats['peak_amplitude'] - exp_stats['peak_amplitude']) < 1000 else 'warning'}">
                    {abs(orig_stats['peak_amplitude'] - exp_stats['peak_amplitude']):,} diff
                </td>
            </tr>
            <tr>
                <td>Avg Amplitude</td>
                <td>{orig_stats['avg_amplitude']:,}</td>
                <td>{exp_stats['avg_amplitude']:,}</td>
                <td class="{'good' if abs(orig_stats['avg_amplitude'] - exp_stats['avg_amplitude']) < 500 else 'warning'}">
                    {abs(orig_stats['avg_amplitude'] - exp_stats['avg_amplitude']):,} diff
                </td>
            </tr>
        </table>
    </div>

    <div class="section">
        <h2>Waveform Comparison (First 5 seconds)</h2>
        <canvas id="waveform"></canvas>
        <script>
            const canvas = document.getElementById('waveform');
            const ctx = canvas.getContext('2d');
            canvas.width = canvas.offsetWidth;
            canvas.height = 400;

            const origSamples = {orig_samples};
            const expSamples = {exp_samples};

            // Draw original waveform (blue)
            ctx.strokeStyle = '#3498db';
            ctx.lineWidth = 1;
            ctx.beginPath();
            const xStep = canvas.width / origSamples.length;
            origSamples.forEach((sample, i) => {{
                const x = i * xStep;
                const y = canvas.height/4 + (sample / 32768) * canvas.height/4;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }});
            ctx.stroke();

            // Draw exported waveform (red)
            ctx.strokeStyle = '#e74c3c';
            ctx.lineWidth = 1;
            ctx.beginPath();
            expSamples.forEach((sample, i) => {{
                const x = i * xStep;
                const y = 3*canvas.height/4 + (sample / 32768) * canvas.height/4;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }});
            ctx.stroke();

            // Draw labels
            ctx.fillStyle = '#3498db';
            ctx.font = '14px Arial';
            ctx.fillText('Original (Laxity)', 10, 20);
            ctx.fillStyle = '#e74c3c';
            ctx.fillText('Exported (SF2)', 10, canvas.height/2 + 20);

            // Draw center lines
            ctx.strokeStyle = '#ddd';
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(0, canvas.height/4);
            ctx.lineTo(canvas.width, canvas.height/4);
            ctx.moveTo(0, 3*canvas.height/4);
            ctx.lineTo(canvas.width, 3*canvas.height/4);
            ctx.stroke();
        </script>
    </div>

    <div class="section">
        <h2>Analysis Notes</h2>
        <ul>
            <li><strong>Different Players:</strong> Original uses Laxity NewPlayer v21, Exported uses SF2 Driver 11</li>
            <li><strong>Expected Differences:</strong> Different timing, effects processing, filter implementation</li>
            <li><strong>What Matters:</strong> Both files should sound similar to human ears, even if waveforms differ</li>
            <li><strong>Register Accuracy:</strong> Check info.txt for SID register-level accuracy metrics</li>
        </ul>
    </div>
</body>
</html>
"""

    # Write HTML file
    try:
        output_path.write_text(html, encoding='utf-8')
        return True
    except Exception as e:
        print(f"Error writing HTML report: {e}")
        return False


def analyze_all_files(pipeline_dir: str):
    """Analyze all WAV files in pipeline output directory."""
    pipeline_path = Path(pipeline_dir)

    if not pipeline_path.exists():
        print(f"Error: Pipeline directory not found: {pipeline_dir}")
        return

    # Find all song directories
    song_dirs = [d for d in pipeline_path.iterdir() if d.is_dir()]

    print(f"Found {len(song_dirs)} song directories")
    print(f"Generating waveform analysis reports...\n")

    reports_generated = 0

    for song_dir in sorted(song_dirs):
        song_name = song_dir.name

        # Find WAV files
        original_wav = song_dir / "Original" / f"{song_name}_original.wav"
        exported_wav = song_dir / "New" / f"{song_name}_exported.wav"

        if not original_wav.exists() or not exported_wav.exists():
            print(f"[SKIP] {song_name}: Missing WAV files")
            continue

        # Generate report
        output_html = song_dir / f"{song_name}_waveform_analysis.html"

        print(f"[{reports_generated+1}] Analyzing: {song_name}")
        if generate_html_report(song_name, original_wav, exported_wav, output_html):
            print(f"    Generated: {output_html}")
            reports_generated += 1
        else:
            print(f"    [ERROR] Failed to generate report")

    print(f"\n{'='*70}")
    print(f"WAVEFORM ANALYSIS COMPLETE")
    print(f"{'='*70}")
    print(f"Reports generated: {reports_generated}/{len(song_dirs)}")
    print(f"Output directory: {pipeline_dir}")
    print(f"\nOpen any *_waveform_analysis.html file in your browser to view results.")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        pipeline_dir = sys.argv[1]
    else:
        pipeline_dir = "output/SIDSF2player_Complete_Pipeline"

    analyze_all_files(pipeline_dir)


if __name__ == "__main__":
    main()
