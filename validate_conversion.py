#!/usr/bin/env python3
"""
Automated SID to SF2 Conversion Validation Script

This script validates the quality of SID to SF2 conversion by:
1. Analyzing original SID file register writes using siddump
2. Converting SID to SF2
3. Rendering original SID to WAV for audio reference
4. Comparing extracted data (instruments, waveforms, ADSR values)
5. Generating detailed HTML report

Usage:
    python validate_conversion.py SID/Angular.sid
    python validate_conversion.py SID/Angular.sid --duration 30 --verbose
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Optional
from collections import Counter

# Import SIDM2 components
from sidm2 import (
    SIDParser,
    LaxityPlayerAnalyzer,
    SF2Writer,
    extract_from_siddump
)

__version__ = "1.0.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


class ConversionValidator:
    """Validates SID to SF2 conversion quality"""

    def __init__(self, tools_dir: str = "tools"):
        self.tools_dir = Path(tools_dir)
        self.sid2wav = self.tools_dir / "SID2WAV.EXE"
        self.siddump = self.tools_dir / "siddump.exe"

        if not self.sid2wav.exists():
            logger.warning(f"SID2WAV.EXE not found in {tools_dir}")
        if not self.siddump.exists():
            logger.warning(f"siddump.exe not found in {tools_dir}")

    def render_to_wav(self, sid_file: str, output_wav: str, duration: int = 60) -> bool:
        """Render SID file to WAV using SID2WAV"""
        if not self.sid2wav.exists():
            logger.warning("  Cannot render WAV - SID2WAV.EXE not found")
            return False

        import subprocess

        cmd = [
            str(self.sid2wav),
            "-16",           # 16-bit
            "-s",            # Stereo
            f"-f44100",      # 44.1kHz
            f"-t{duration}", # Duration
            sid_file,
            output_wav
        ]

        logger.debug(f"Rendering: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=duration + 10
            )

            if result.returncode == 0 and os.path.exists(output_wav):
                logger.info(f"  Created: {output_wav} ({os.path.getsize(output_wav):,} bytes)")
                return True
            else:
                logger.error(f"  Failed to render: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error(f"  Timeout rendering {sid_file}")
            return False
        except Exception as e:
            logger.error(f"  Error rendering: {e}")
            return False

    def validate_conversion(
        self,
        sid_file: str,
        output_dir: str = "validation_output",
        duration: int = 30
    ) -> Dict:
        """
        Complete validation pipeline

        Args:
            sid_file: Original SID file
            output_dir: Directory for output files
            duration: Playback duration in seconds for WAV/siddump

        Returns:
            Dictionary with validation results
        """
        logger.info("="*60)
        logger.info("SID to SF2 Conversion Validation")
        logger.info("="*60)
        logger.info(f"Original SID: {sid_file}")
        logger.info("")

        os.makedirs(output_dir, exist_ok=True)
        base_name = Path(sid_file).stem

        # Step 1: Analyze original SID with siddump
        logger.info("Step 1: Analyzing original SID with siddump...")
        siddump_data = extract_from_siddump(sid_file, playback_time=duration)

        if siddump_data:
            logger.info(f"  Found {len(siddump_data['adsr_values'])} unique ADSR values")
            logger.info(f"  Found {len(siddump_data['waveforms'])} unique waveforms")
            logger.info(f"  Pulse width range: ${siddump_data['pulse_range'][0]:03X} - ${siddump_data['pulse_range'][1]:03X}")
        else:
            logger.warning("  Siddump analysis failed - continuing anyway")
            siddump_data = {'adsr_values': [], 'waveforms': [], 'pulse_range': (0, 0), 'instruments': []}

        # Step 2: Parse SID file
        logger.info("Step 2: Parsing SID file structure...")
        parser = SIDParser(sid_file)
        header = parser.parse_header()
        c64_data, load_address = parser.get_c64_data(header)

        logger.info(f"  Format: {header.magic} v{header.version}")
        logger.info(f"  Name: {header.name}")
        logger.info(f"  Author: {header.author}")
        logger.info(f"  Load: ${load_address:04X}, Size: {len(c64_data)} bytes")

        # Step 3: Extract music data
        logger.info("Step 3: Extracting music data from SID...")
        analyzer = LaxityPlayerAnalyzer(c64_data, load_address, header)
        extracted = analyzer.extract_music_data()

        logger.info(f"  Sequences: {len(extracted.sequences)}")
        logger.info(f"  Instruments: {len(extracted.instruments)}")
        logger.info(f"  Wave entries: {len(extracted.wavetable)}")
        logger.info(f"  Pulse entries: {len(extracted.pulsetable)}")
        logger.info(f"  Filter entries: {len(extracted.filtertable)}")
        logger.info(f"  Tempo: {extracted.tempo}")

        # Attach siddump data
        extracted.siddump_data = siddump_data

        # Step 4: Generate SF2 file
        logger.info("Step 4: Generating SF2 file...")
        sf2_file = os.path.join(output_dir, f"{base_name}_validated.sf2")

        writer = SF2Writer(extracted, driver_type='driver11')
        writer.write(sf2_file)

        logger.info(f"  Created: {sf2_file} ({os.path.getsize(sf2_file):,} bytes)")

        # Step 5: Render original to WAV
        logger.info("Step 5: Rendering original SID to WAV...")
        wav_file = os.path.join(output_dir, f"{base_name}_reference.wav")
        wav_created = self.render_to_wav(sid_file, wav_file, duration)

        # Step 6: Compare extracted data
        logger.info("Step 6: Comparing extracted vs. actual data...")
        comparison = self._compare_data(extracted, siddump_data)

        for msg in comparison['messages']:
            logger.info(f"  {msg}")

        # Step 7: Generate report
        logger.info("Step 7: Generating HTML report...")
        report_file = os.path.join(output_dir, f"{base_name}_validation_report.html")
        self._generate_report({
            'sid_file': sid_file,
            'sf2_file': sf2_file,
            'wav_file': wav_file if wav_created else None,
            'header': header,
            'extracted': extracted,
            'siddump': siddump_data,
            'comparison': comparison
        }, report_file)

        logger.info(f"  Report: {report_file}")
        logger.info("")
        logger.info("="*60)
        logger.info("Validation complete!")
        logger.info("="*60)

        return {
            'sf2_file': sf2_file,
            'wav_file': wav_file if wav_created else None,
            'report_file': report_file,
            'comparison': comparison
        }

    def _compare_data(self, extracted, siddump_data) -> Dict:
        """Compare extracted data against siddump actual data"""
        messages = []
        issues = []

        # Compare ADSR values
        if siddump_data['adsr_values']:
            extracted_adsr = set()
            for instr_bytes in extracted.instruments[:16]:
                if len(instr_bytes) >= 2:
                    ad = instr_bytes[0]
                    sr = instr_bytes[1]
                    extracted_adsr.add((ad, sr))

            actual_adsr = set(siddump_data['adsr_values'])

            matching = extracted_adsr & actual_adsr
            missing = actual_adsr - extracted_adsr
            extra = extracted_adsr - actual_adsr

            messages.append(f"ADSR: {len(matching)}/{len(actual_adsr)} matching")
            if missing:
                issues.append(f"Missing ADSR values: {missing}")
            if extra:
                issues.append(f"Extra ADSR values: {extra}")

        # Compare waveforms
        if siddump_data['waveforms']:
            # Extract waveforms from wavetable bytes (alternating waveform/note pairs)
            extracted_waves = set()
            for i in range(0, len(extracted.wavetable), 2):
                if i < len(extracted.wavetable):
                    wave = extracted.wavetable[i]
                    if wave not in (0x7F, 0x7E):  # Exclude end/loop markers
                        extracted_waves.add(wave)

            actual_waves = set(siddump_data['waveforms'])

            matching_waves = extracted_waves & actual_waves
            missing_waves = actual_waves - extracted_waves
            extra_waves = extracted_waves - actual_waves

            messages.append(f"Waveforms: {len(matching_waves)}/{len(actual_waves)} matching")
            if missing_waves:
                issues.append(f"Missing waveforms: {[f'${w:02X}' for w in missing_waves]}")
            if extra_waves:
                issues.append(f"Extra waveforms: {[f'${w:02X}' for w in extra_waves]}")

        # Tempo check
        messages.append(f"Tempo: {extracted.tempo} frames/row")

        return {
            'messages': messages,
            'issues': issues
        }

    def _generate_report(self, data: Dict, report_file: str):
        """Generate HTML validation report"""

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Validation Report: {Path(data['sid_file']).stem}</title>
    <style>
        body {{ font-family: monospace; margin: 20px; background: #1e1e1e; color: #d4d4d4; }}
        h1 {{ color: #4ec9b0; }}
        h2 {{ color: #569cd6; margin-top: 30px; }}
        table {{ border-collapse: collapse; margin: 10px 0; }}
        th, td {{ border: 1px solid #555; padding: 8px; text-align: left; }}
        th {{ background: #2d2d30; color: #4ec9b0; }}
        .stat {{ background: #252526; padding: 10px; margin: 10px 0; border-left: 3px solid #4ec9b0; }}
        .good {{ color: #4ec9b0; }}
        .warning {{ color: #ce9178; }}
        .error {{ color: #f48771; }}
        .code {{ background: #1e1e1e; padding: 2px 5px; border: 1px solid #555; }}
    </style>
</head>
<body>
    <h1>SID to SF2 Conversion Validation Report</h1>

    <div class="stat">
        <strong>Original SID:</strong> {data['sid_file']}<br>
        <strong>Generated SF2:</strong> {data['sf2_file']}<br>
        <strong>Reference WAV:</strong> {data['wav_file'] or 'N/A'}<br>
    </div>

    <h2>SID File Information</h2>
    <div class="stat">
        <strong>Format:</strong> {data['header'].magic} v{data['header'].version}<br>
        <strong>Name:</strong> {data['header'].name}<br>
        <strong>Author:</strong> {data['header'].author}<br>
        <strong>Copyright:</strong> {data['header'].copyright}<br>
    </div>

    <h2>Extracted Data Summary</h2>
    <div class="stat">
        <strong>Sequences:</strong> {len(data['extracted'].sequences)}<br>
        <strong>Instruments:</strong> {len(data['extracted'].instruments)}<br>
        <strong>Wave entries:</strong> {len(data['extracted'].wavetable)}<br>
        <strong>Pulse entries:</strong> {len(data['extracted'].pulsetable)}<br>
        <strong>Filter entries:</strong> {len(data['extracted'].filtertable)}<br>
        <strong>Tempo:</strong> {data['extracted'].tempo} frames/row<br>
    </div>

    <h2>Siddump Analysis (Actual Runtime Behavior)</h2>
"""

        if data['siddump']['adsr_values']:
            html += f"""    <div class="stat">
        <strong>Unique ADSR values:</strong> {len(data['siddump']['adsr_values'])}<br>
        <strong>Unique waveforms:</strong> {len(data['siddump']['waveforms'])}<br>
        <strong>Pulse width range:</strong> ${data['siddump']['pulse_range'][0]:03X} - ${data['siddump']['pulse_range'][1]:03X}<br>
    </div>

    <h3>ADSR Values Found During Playback</h3>
    <table>
        <tr>
            <th>Index</th>
            <th>Attack/Decay</th>
            <th>Sustain/Release</th>
            <th>Hex</th>
        </tr>
"""
            for i, (ad, sr) in enumerate(sorted(data['siddump']['adsr_values'])):
                html += f"        <tr><td>{i}</td><td>${ad:02X}</td><td>${sr:02X}</td><td>${ad:02X}{sr:02X}</td></tr>\n"

            html += """    </table>

    <h3>Waveforms Found During Playback</h3>
    <table>
        <tr>
            <th>Waveform</th>
            <th>Binary</th>
            <th>Description</th>
        </tr>
"""
            wave_names = {
                0x01: "Triangle",
                0x10: "Triangle + Gate",
                0x11: "Pulse (Tri gate)",
                0x15: "Pulse + Noise + Gate",
                0x20: "Sawtooth",
                0x21: "Sawtooth + Triangle",
                0x40: "Pulse",
                0x41: "Pulse + Gate",
                0x80: "Noise",
                0x81: "Noise + Gate"
            }

            for wf in sorted(data['siddump']['waveforms']):
                binary = f"{wf:08b}"
                name = wave_names.get(wf, "Unknown")
                html += f"        <tr><td>${wf:02X}</td><td>{binary}</td><td>{name}</td></tr>\n"

            html += "    </table>\n"
        else:
            html += """    <div class="stat warning">
        Siddump analysis not available
    </div>
"""

        # Comparison results
        html += """
    <h2>Extraction Quality</h2>
"""

        if data['comparison']['messages']:
            html += """    <ul>
"""
            for msg in data['comparison']['messages']:
                html += f"        <li>{msg}</li>\n"
            html += """    </ul>
"""

        if data['comparison']['issues']:
            html += """    <h3 class="error">Issues Found</h3>
    <ul>
"""
            for issue in data['comparison']['issues']:
                html += f"        <li class='error'>{issue}</li>\n"
            html += """    </ul>
"""
        else:
            html += """    <div class="stat good">
        No major issues detected
    </div>
"""

        # Instruments table
        html += """
    <h2>Extracted Instruments</h2>
    <table>
        <tr>
            <th>Index</th>
            <th>AD</th>
            <th>SR</th>
            <th>Restart</th>
            <th>Filter</th>
            <th>Pulse Ptr</th>
            <th>Wave Ptr</th>
        </tr>
"""

        for i, instr_bytes in enumerate(data['extracted'].instruments[:16]):
            if len(instr_bytes) >= 8:
                ad = instr_bytes[0]
                sr = instr_bytes[1]
                restart = instr_bytes[2]
                filter_setting = instr_bytes[4]
                pulse_ptr = instr_bytes[6]
                wave_ptr = instr_bytes[7]

                html += f"        <tr><td>{i:02d}</td><td>${ad:02X}</td><td>${sr:02X}</td><td>${restart:02X}</td><td>${filter_setting:02X}</td><td>${pulse_ptr:02X}</td><td>${wave_ptr:02X}</td></tr>\n"

        html += """    </table>

    <h2>Testing Instructions</h2>
    <div class="stat">
        <ol>
            <li>Open the generated SF2 file in SID Factory II</li>
            <li>Play the song and compare to the reference WAV file</li>
            <li>Check that tempo, rhythm, and effects sound correct</li>
            <li>Verify instrument sounds match the original</li>
        </ol>
    </div>

    <h2>Files Generated</h2>
    <ul>
        <li><strong>SF2:</strong> <span class='code'>{os.path.basename(data['sf2_file'])}</span></li>
"""

        if data['wav_file']:
            html += f"        <li><strong>Reference WAV:</strong> <span class='code'>{os.path.basename(data['wav_file'])}</span></li>\n"

        html += """    </ul>
</body>
</html>
"""

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Validate SID to SF2 conversion quality'
    )
    parser.add_argument('sid_file', help='Original SID file to validate')
    parser.add_argument(
        '--output-dir', '-o',
        default='validation_output',
        help='Output directory (default: validation_output)'
    )
    parser.add_argument(
        '--duration', '-t',
        type=int,
        default=30,
        help='Playback duration in seconds (default: 30)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if not os.path.exists(args.sid_file):
        logger.error(f"SID file not found: {args.sid_file}")
        sys.exit(1)

    validator = ConversionValidator()
    result = validator.validate_conversion(
        args.sid_file,
        args.output_dir,
        args.duration
    )

    logger.info(f"SF2 file: {result['sf2_file']}")
    if result['wav_file']:
        logger.info(f"WAV file: {result['wav_file']}")
    logger.info(f"Report: {result['report_file']}")


if __name__ == '__main__':
    main()
