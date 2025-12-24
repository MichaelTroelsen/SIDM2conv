"""
Enhanced Comparison Tool for SID Accuracy Validation - Phase 1b

Extends scripts/validate_sid_accuracy.py with:
- JSON output for comparison results
- Detailed register-level diff reporting
- Voice-level difference tracking
- Machine-readable comparison data

Usage:
    from sidm2.comparison_tool import ComparisonJSONExporter

    exporter = ComparisonJSONExporter()
    exporter.export_comparison_results(
        original_capture,
        exported_capture,
        comparison_results,
        output_path="comparison.json"
    )
"""

__version__ = "1.0.0"
__date__ = "2025-12-24"

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class RegisterDiff:
    """Represents a difference in a single register write"""

    def __init__(self, frame: int, register: int, register_name: str,
                 original_value: int, exported_value: int):
        self.frame = frame
        self.register = register
        self.register_name = register_name
        self.original_value = original_value
        self.exported_value = exported_value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'frame': self.frame,
            'register': f"${self.register:02X}",
            'register_name': self.register_name,
            'original_value': f"${self.original_value:02X}",
            'exported_value': f"${self.exported_value:02X}",
            'original_decimal': self.original_value,
            'exported_decimal': self.exported_value,
            'difference': self.exported_value - self.original_value
        }


class VoiceDiff:
    """Tracks differences in a specific voice"""

    def __init__(self, voice: int):
        self.voice = voice
        self.frequency_diffs: List[Tuple[int, int, int]] = []  # (frame, orig, exp)
        self.waveform_diffs: List[Tuple[int, int, int]] = []   # (frame, orig, exp)
        self.pulse_width_diffs: List[Tuple[int, int, int]] = []  # (frame, orig, exp)
        self.adsr_diffs: List[Tuple[int, int, int]] = []       # (frame, orig, exp)

    def add_frequency_diff(self, frame: int, original: int, exported: int):
        """Record frequency difference"""
        if original != exported:
            self.frequency_diffs.append((frame, original, exported))

    def add_waveform_diff(self, frame: int, original: int, exported: int):
        """Record waveform difference"""
        if original != exported:
            self.waveform_diffs.append((frame, original, exported))

    def add_pulse_width_diff(self, frame: int, original: int, exported: int):
        """Record pulse width difference"""
        if original != exported:
            self.pulse_width_diffs.append((frame, original, exported))

    def add_adsr_diff(self, frame: int, original: int, exported: int):
        """Record ADSR difference"""
        if original != exported:
            self.adsr_diffs.append((frame, original, exported))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'voice': self.voice,
            'frequency': {
                'differences': len(self.frequency_diffs),
                'first_diff': {
                    'frame': self.frequency_diffs[0][0],
                    'original': f"${self.frequency_diffs[0][1]:04X}",
                    'exported': f"${self.frequency_diffs[0][2]:04X}"
                } if self.frequency_diffs else None,
                'samples': [
                    {
                        'frame': frame,
                        'original': f"${orig:04X}",
                        'exported': f"${exp:04X}"
                    }
                    for frame, orig, exp in self.frequency_diffs[:10]
                ]
            },
            'waveform': {
                'differences': len(self.waveform_diffs),
                'first_diff': {
                    'frame': self.waveform_diffs[0][0],
                    'original': f"${self.waveform_diffs[0][1]:02X}",
                    'exported': f"${self.waveform_diffs[0][2]:02X}"
                } if self.waveform_diffs else None,
                'samples': [
                    {
                        'frame': frame,
                        'original': f"${orig:02X}",
                        'exported': f"${exp:02X}"
                    }
                    for frame, orig, exp in self.waveform_diffs[:10]
                ]
            },
            'pulse_width': {
                'differences': len(self.pulse_width_diffs),
                'samples': [
                    {
                        'frame': frame,
                        'original': f"${orig:03X}",
                        'exported': f"${exp:03X}"
                    }
                    for frame, orig, exp in self.pulse_width_diffs[:10]
                ]
            },
            'adsr': {
                'differences': len(self.adsr_diffs),
                'samples': [
                    {
                        'frame': frame,
                        'original': f"${orig:02X}",
                        'exported': f"${exp:02X}"
                    }
                    for frame, orig, exp in self.adsr_diffs[:10]
                ]
            }
        }


class ComparisonDetailExtractor:
    """Extract detailed differences from SID captures"""

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

    @staticmethod
    def extract_register_diffs(original_frames: List[Dict],
                               exported_frames: List[Dict]) -> List[RegisterDiff]:
        """Extract all register-level differences"""
        diffs = []
        max_frames = min(len(original_frames), len(exported_frames))

        for frame_idx in range(max_frames):
            orig_frame = original_frames[frame_idx]
            exp_frame = exported_frames[frame_idx]

            all_regs = set(orig_frame.keys()) | set(exp_frame.keys())

            for reg in sorted(all_regs):
                orig_val = orig_frame.get(reg)
                exp_val = exp_frame.get(reg)

                if orig_val != exp_val:
                    orig_val = orig_val or 0
                    exp_val = exp_val or 0

                    reg_name = ComparisonDetailExtractor.REGISTER_NAMES.get(
                        reg, f"Reg_{reg:02X}"
                    )

                    diffs.append(RegisterDiff(
                        frame=frame_idx,
                        register=reg,
                        register_name=reg_name,
                        original_value=orig_val,
                        exported_value=exp_val
                    ))

        return diffs

    @staticmethod
    def extract_voice_diffs(original_frames: List[Dict],
                           exported_frames: List[Dict]) -> Dict[int, VoiceDiff]:
        """Extract voice-level differences"""
        voice_diffs = {1: VoiceDiff(1), 2: VoiceDiff(2), 3: VoiceDiff(3)}
        max_frames = min(len(original_frames), len(exported_frames))

        for frame_idx in range(max_frames):
            orig_frame = original_frames[frame_idx]
            exp_frame = exported_frames[frame_idx]

            for voice in range(1, 4):
                base_reg = (voice - 1) * 7

                # Frequency (16-bit)
                freq_lo_reg = base_reg + 0
                freq_hi_reg = base_reg + 1

                orig_freq = (orig_frame.get(freq_lo_reg, 0) |
                            (orig_frame.get(freq_hi_reg, 0) << 8))
                exp_freq = (exp_frame.get(freq_lo_reg, 0) |
                           (exp_frame.get(freq_hi_reg, 0) << 8))

                voice_diffs[voice].add_frequency_diff(
                    frame_idx, orig_freq, exp_freq
                )

                # Waveform
                wf_reg = base_reg + 4
                voice_diffs[voice].add_waveform_diff(
                    frame_idx,
                    orig_frame.get(wf_reg, 0),
                    exp_frame.get(wf_reg, 0)
                )

                # Pulse width
                pw_lo = base_reg + 2
                pw_hi = base_reg + 3
                orig_pw = (orig_frame.get(pw_lo, 0) |
                          ((orig_frame.get(pw_hi, 0) & 0x0F) << 8))
                exp_pw = (exp_frame.get(pw_lo, 0) |
                         ((exp_frame.get(pw_hi, 0) & 0x0F) << 8))

                voice_diffs[voice].add_pulse_width_diff(
                    frame_idx, orig_pw, exp_pw
                )

                # ADSR
                ad_reg = base_reg + 5
                voice_diffs[voice].add_adsr_diff(
                    frame_idx,
                    orig_frame.get(ad_reg, 0),
                    exp_frame.get(ad_reg, 0)
                )

        return voice_diffs


class ComparisonJSONExporter:
    """Export comparison results to machine-readable JSON format"""

    @staticmethod
    def export_comparison_results(
        original_capture,
        exported_capture,
        comparison_results: Dict,
        output_path: str
    ) -> bool:
        """Export detailed comparison results to JSON

        Args:
            original_capture: SIDRegisterCapture object for original SID
            exported_capture: SIDRegisterCapture object for exported SID
            comparison_results: Dictionary with comparison data from SIDComparator
            output_path: Path to write JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Extract detailed diffs
            register_diffs = ComparisonDetailExtractor.extract_register_diffs(
                original_capture.frames,
                exported_capture.frames
            )

            voice_diffs = ComparisonDetailExtractor.extract_voice_diffs(
                original_capture.frames,
                exported_capture.frames
            )

            # Build comprehensive comparison data
            comparison_data = {
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'original_sid': str(original_capture.sid_path),
                    'exported_sid': str(exported_capture.sid_path),
                    'duration': original_capture.duration
                },
                'summary': {
                    'overall_accuracy': comparison_results.get('overall_accuracy', 0),
                    'frame_accuracy': comparison_results.get('frame_accuracy', 0),
                    'filter_accuracy': comparison_results.get('filter_accuracy', 0),
                    'frame_count_match': comparison_results.get('frame_count_match', False),
                    'total_register_differences': len(register_diffs)
                },
                'voice_accuracy': comparison_results.get('voice_accuracy', {}),
                'register_accuracy': ComparisonJSONExporter._format_register_accuracy(
                    comparison_results.get('register_accuracy', {})
                ),
                'register_diffs': {
                    'count': len(register_diffs),
                    'samples': [d.to_dict() for d in register_diffs[:100]]
                },
                'voice_diffs': {
                    voice_num: voice_diff.to_dict()
                    for voice_num, voice_diff in voice_diffs.items()
                },
                'recommendations': ComparisonJSONExporter._generate_recommendations(
                    comparison_results
                )
            }

            # Write to JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(comparison_data, f, indent=2)

            return True

        except Exception as e:
            print(f"ERROR: Failed to export comparison JSON: {e}")
            return False

    @staticmethod
    def _format_register_accuracy(register_accuracy: Dict) -> Dict:
        """Format register accuracy data for JSON"""
        formatted = {}
        for reg_name, data in register_accuracy.items():
            formatted[reg_name] = {
                'accuracy_percent': round(data.get('accuracy', 0), 2),
                'original_writes': data.get('orig_writes', 0),
                'exported_writes': data.get('exp_writes', 0),
                'matching_writes': data.get('matches', 0)
            }
        return formatted

    @staticmethod
    def _generate_recommendations(comparison_results: Dict) -> List[str]:
        """Generate human-readable recommendations"""
        recommendations = []

        accuracy = comparison_results.get('overall_accuracy', 0)

        if accuracy >= 99:
            recommendations.append("EXCELLENT: Conversion is nearly perfect (99%+ accuracy)")
        elif accuracy >= 95:
            recommendations.append("VERY GOOD: Conversion is quite accurate (95%+ accuracy)")
        elif accuracy >= 80:
            recommendations.append("GOOD: Conversion has reasonable accuracy (80%+ accuracy)")
        else:
            recommendations.append("NEEDS WORK: Conversion accuracy is below 80%")

        if comparison_results.get('frame_accuracy', 0) < 90:
            recommendations.append("Check timing and frame synchronization")

        if comparison_results.get('filter_accuracy', 0) < 90:
            recommendations.append("Review filter table extraction and cutoff values")

        voice_acc = comparison_results.get('voice_accuracy', {})
        for voice_name, voice_data in voice_acc.items():
            if voice_data.get('frequency_accuracy', 0) < 90:
                recommendations.append(f"{voice_name}: Check frequency calculation")
            if voice_data.get('waveform_accuracy', 0) < 90:
                recommendations.append(f"{voice_name}: Check waveform table handling")

        return recommendations


class ComparisonDiffReporter:
    """Generate human-readable diff reports"""

    @staticmethod
    def generate_text_report(
        original_capture,
        exported_capture,
        comparison_results: Dict,
        output_path: str,
        max_diffs: int = 100
    ) -> bool:
        """Generate detailed text report of differences

        Args:
            original_capture: SIDRegisterCapture object for original SID
            exported_capture: SIDRegisterCapture object for exported SID
            comparison_results: Dictionary with comparison data
            output_path: Path to write text report
            max_diffs: Maximum number of differences to include

        Returns:
            True if successful, False otherwise
        """
        try:
            register_diffs = ComparisonDetailExtractor.extract_register_diffs(
                original_capture.frames,
                exported_capture.frames
            )

            voice_diffs = ComparisonDetailExtractor.extract_voice_diffs(
                original_capture.frames,
                exported_capture.frames
            )

            report_lines = [
                "=" * 80,
                "SID ACCURACY COMPARISON - DETAILED DIFF REPORT",
                "=" * 80,
                "",
                f"Original SID: {original_capture.sid_path.name}",
                f"Exported SID: {exported_capture.sid_path.name}",
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "ACCURACY SUMMARY",
                "-" * 80,
                f"Overall Accuracy: {comparison_results.get('overall_accuracy', 0):.2f}%",
                f"Frame Accuracy: {comparison_results.get('frame_accuracy', 0):.2f}%",
                f"Filter Accuracy: {comparison_results.get('filter_accuracy', 0):.2f}%",
                f"Total Register Differences: {len(register_diffs)}",
                "",
                "REGISTER-LEVEL DIFFERENCES",
                "-" * 80,
            ]

            for i, diff in enumerate(register_diffs[:max_diffs], 1):
                d = diff.to_dict()
                report_lines.append(
                    f"{i:3d}. Frame {d['frame']:4d}: {d['register_name']:25s} "
                    f"{d['original_value']} -> {d['exported_value']} "
                    f"(delta: {d['difference']:+d})"
                )

            if len(register_diffs) > max_diffs:
                report_lines.append(f"... and {len(register_diffs) - max_diffs} more differences")

            report_lines.extend([
                "",
                "VOICE-LEVEL DIFFERENCES",
                "-" * 80,
            ])

            for voice_num in range(1, 4):
                voice_diff = voice_diffs[voice_num]
                report_lines.extend([
                    f"\nVOICE {voice_num}:",
                    f"  Frequency differences: {len(voice_diff.frequency_diffs)}",
                    f"  Waveform differences: {len(voice_diff.waveform_diffs)}",
                    f"  Pulse width differences: {len(voice_diff.pulse_width_diffs)}",
                    f"  ADSR differences: {len(voice_diff.adsr_diffs)}",
                ])

                if voice_diff.frequency_diffs:
                    report_lines.append("    First frequency diff: Frame {}, {} -> {}".format(
                        voice_diff.frequency_diffs[0][0],
                        f"${voice_diff.frequency_diffs[0][1]:04X}",
                        f"${voice_diff.frequency_diffs[0][2]:04X}"
                    ))

            report_lines.extend([
                "",
                "=" * 80,
            ])

            # Write report
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))

            return True

        except Exception as e:
            print(f"ERROR: Failed to generate diff report: {e}")
            return False
