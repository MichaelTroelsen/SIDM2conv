"""
Lightweight validation module for convert_all.py pipeline integration.

This module provides quick SID accuracy validation by comparing original
and exported SID files using siddump register capture.

Usage:
    from sidm2.validation import quick_validate, generate_accuracy_summary

    results = quick_validate('original.sid', 'exported.sid', duration=10)
    print(generate_accuracy_summary(results))
"""

import subprocess
import re
from pathlib import Path
from typing import Dict, Optional
from collections import defaultdict


def quick_validate(original_sid: str, exported_sid: str, duration: int = 10) -> Optional[Dict]:
    """
    Quick validation for pipeline (10 seconds default).

    Args:
        original_sid: Path to original SID file
        exported_sid: Path to exported SID file
        duration: Capture duration in seconds (default: 10)

    Returns:
        Dictionary with validation results or None if validation failed:
        {
            'overall_accuracy': float,       # 0-100
            'frame_accuracy': float,         # 0-100
            'voice_accuracy': float,         # 0-100 (average of all voices)
            'register_accuracy': float,      # 0-100 (average of all registers)
            'filter_accuracy': float,        # 0-100
            'frames_compared': int,
            'differences_found': int,
        }
    """
    try:
        # Capture both SID files
        orig_capture = _capture_sid_data(original_sid, duration)
        exp_capture = _capture_sid_data(exported_sid, duration)

        if not orig_capture or not exp_capture:
            return None

        # Compare captures
        comparison = _compare_captures(orig_capture, exp_capture)

        return comparison

    except Exception as e:
        # Silent failure for pipeline integration
        return None


def _capture_sid_data(sid_path: str, duration: int) -> Optional[Dict]:
    """Capture SID register data using siddump."""
    siddump_exe = Path('tools/siddump.exe')
    if not siddump_exe.exists():
        return None

    try:
        result = subprocess.run(
            [str(siddump_exe.absolute()), sid_path, '-z', f'-t{duration}'],
            capture_output=True,
            text=True,
            timeout=duration + 10
        )

        if result.returncode != 0:
            return None

        # Parse siddump table output
        frames = _parse_siddump_table(result.stdout)

        return {
            'frames': frames,
            'frame_count': len(frames)
        }

    except Exception:
        return None


def _parse_siddump_table(output: str) -> list:
    """Parse siddump table format output."""
    frames = []

    for line in output.split('\n'):
        line = line.strip()
        if not line or line.startswith('+') or '| Frame |' in line:
            continue

        if line.startswith('|'):
            parts = [p.strip() for p in line.split('|')[1:]]
            if len(parts) < 5:
                continue

            try:
                frame_data = {}

                # Parse 3 voices
                for voice_idx in range(3):
                    voice_data = parts[1 + voice_idx].split()
                    if len(voice_data) >= 5:
                        # Frequency
                        freq_str = voice_data[0]
                        if freq_str != '....':
                            try:
                                freq = int(freq_str, 16)
                                reg_base = voice_idx * 7
                                frame_data[reg_base + 0] = freq & 0xFF
                                frame_data[reg_base + 1] = (freq >> 8) & 0xFF
                            except ValueError:
                                pass

                        # Waveform
                        wf_idx = 2 if '(' in voice_data[1] else 1
                        if wf_idx < len(voice_data):
                            wf_str = voice_data[wf_idx]
                            if wf_str not in ('..', '....'):
                                try:
                                    frame_data[voice_idx * 7 + 4] = int(wf_str, 16)
                                except ValueError:
                                    pass

                        # ADSR
                        adsr_idx = wf_idx + 1
                        if adsr_idx < len(voice_data):
                            adsr_str = voice_data[adsr_idx]
                            if adsr_str != '....' and len(adsr_str) == 4:
                                try:
                                    ad = int(adsr_str[:2], 16)
                                    sr = int(adsr_str[2:], 16)
                                    frame_data[voice_idx * 7 + 5] = ad
                                    frame_data[voice_idx * 7 + 6] = sr
                                except ValueError:
                                    pass

                        # Pulse width
                        pw_idx = adsr_idx + 1
                        if pw_idx < len(voice_data):
                            pw_str = voice_data[pw_idx]
                            if pw_str not in ('...', '....'):
                                try:
                                    pw = int(pw_str, 16)
                                    frame_data[voice_idx * 7 + 2] = pw & 0xFF
                                    frame_data[voice_idx * 7 + 3] = (pw >> 8) & 0x0F
                                except ValueError:
                                    pass

                # Parse filter
                if len(parts) > 4:
                    filter_data = parts[4].split()
                    if len(filter_data) >= 4:
                        # Cutoff
                        fcut_str = filter_data[0]
                        if fcut_str != '....':
                            try:
                                fcut = int(fcut_str, 16)
                                frame_data[0x15] = fcut & 0xFF
                                frame_data[0x16] = (fcut >> 8) & 0x07
                            except ValueError:
                                pass

                        # Resonance
                        if len(filter_data) > 1:
                            rc_str = filter_data[1]
                            if rc_str != '..':
                                try:
                                    frame_data[0x17] = int(rc_str, 16)
                                except ValueError:
                                    pass

                        # Volume
                        if len(filter_data) > 3:
                            vol_str = filter_data[3]
                            if vol_str != '.':
                                try:
                                    frame_data[0x18] = int(vol_str, 16)
                                except ValueError:
                                    pass

                frames.append(frame_data)

            except (ValueError, IndexError):
                continue

    return frames


def _compare_captures(orig: Dict, exp: Dict) -> Dict:
    """Compare two SID captures and calculate accuracy metrics."""
    orig_frames = orig['frames']
    exp_frames = exp['frames']

    max_frames = min(len(orig_frames), len(exp_frames))

    if max_frames == 0:
        return {
            'overall_accuracy': 0.0,
            'frame_accuracy': 0.0,
            'voice_accuracy': 0.0,
            'register_accuracy': 0.0,
            'filter_accuracy': 0.0,
            'frames_compared': 0,
            'differences_found': 0
        }

    # Frame-level comparison
    matching_frames = 0
    total_differences = 0

    # Register-level tracking
    register_matches = defaultdict(int)
    register_totals = defaultdict(int)

    # Voice-level tracking (freq + waveform per voice)
    voice_freq_matches = [0, 0, 0]
    voice_freq_totals = [0, 0, 0]
    voice_wf_matches = [0, 0, 0]
    voice_wf_totals = [0, 0, 0]

    # Filter tracking
    filter_matches = 0
    filter_totals = 0

    for idx in range(max_frames):
        orig_frame = orig_frames[idx]
        exp_frame = exp_frames[idx]

        # Check frame match
        if orig_frame == exp_frame:
            matching_frames += 1
        else:
            total_differences += 1

        # Compare each register
        all_regs = set(orig_frame.keys()) | set(exp_frame.keys())
        for reg in all_regs:
            orig_val = orig_frame.get(reg, 0)
            exp_val = exp_frame.get(reg, 0)

            if orig_val == exp_val:
                register_matches[reg] += 1
            register_totals[reg] += 1

            # Voice tracking
            if reg < 21:  # SID registers 0x00-0x14
                voice_idx = reg // 7
                reg_offset = reg % 7

                if reg_offset in (0, 1):  # Frequency registers
                    if orig_val == exp_val:
                        voice_freq_matches[voice_idx] += 1
                    voice_freq_totals[voice_idx] += 1
                elif reg_offset == 4:  # Waveform/control register
                    if orig_val == exp_val:
                        voice_wf_matches[voice_idx] += 1
                    voice_wf_totals[voice_idx] += 1

            # Filter tracking (registers 0x15-0x18)
            if 0x15 <= reg <= 0x18:
                if orig_val == exp_val:
                    filter_matches += 1
                filter_totals += 1

    # Calculate accuracies
    frame_accuracy = (matching_frames / max_frames * 100) if max_frames > 0 else 0.0

    # Register accuracy (average across all registers)
    reg_accuracies = []
    for reg in register_totals:
        if register_totals[reg] > 0:
            reg_acc = register_matches[reg] / register_totals[reg] * 100
            reg_accuracies.append(reg_acc)
    register_accuracy = sum(reg_accuracies) / len(reg_accuracies) if reg_accuracies else 0.0

    # Voice accuracy (combined freq + waveform, averaged across voices)
    voice_accuracies = []
    for v in range(3):
        freq_acc = (voice_freq_matches[v] / voice_freq_totals[v] * 100) if voice_freq_totals[v] > 0 else 0.0
        wf_acc = (voice_wf_matches[v] / voice_wf_totals[v] * 100) if voice_wf_totals[v] > 0 else 0.0
        voice_accuracies.append((freq_acc + wf_acc) / 2)
    voice_accuracy = sum(voice_accuracies) / 3 if voice_accuracies else 0.0

    # Filter accuracy
    filter_accuracy = (filter_matches / filter_totals * 100) if filter_totals > 0 else 0.0

    # Overall accuracy (weighted)
    overall_accuracy = (
        frame_accuracy * 0.40 +
        voice_accuracy * 0.30 +
        register_accuracy * 0.20 +
        filter_accuracy * 0.10
    )

    return {
        'overall_accuracy': overall_accuracy,
        'frame_accuracy': frame_accuracy,
        'voice_accuracy': voice_accuracy,
        'register_accuracy': register_accuracy,
        'filter_accuracy': filter_accuracy,
        'frames_compared': max_frames,
        'differences_found': total_differences
    }


def get_accuracy_grade(accuracy: float) -> str:
    """
    Return grade based on accuracy percentage.

    Args:
        accuracy: Accuracy percentage (0-100)

    Returns:
        Grade string: EXCELLENT/GOOD/FAIR/POOR
    """
    if accuracy >= 99.0:
        return "EXCELLENT"
    elif accuracy >= 95.0:
        return "GOOD"
    elif accuracy >= 80.0:
        return "FAIR"
    else:
        return "POOR"


def generate_accuracy_summary(validation: Dict) -> str:
    """
    Format accuracy results for info.txt files.

    Args:
        validation: Validation results from quick_validate()

    Returns:
        Multi-line formatted string with accuracy details
    """
    if not validation:
        return "Validation: N/A (validation failed)"

    overall = validation['overall_accuracy']
    grade = get_accuracy_grade(overall)

    lines = []
    lines.append(f"Overall Accuracy:      {overall:5.1f}%  [{grade}]")
    lines.append(f"Frame-Level:           {validation['frame_accuracy']:5.1f}%")
    lines.append(f"Voice Accuracy:        {validation['voice_accuracy']:5.1f}%")
    lines.append(f"Register Accuracy:     {validation['register_accuracy']:5.1f}%")
    lines.append(f"Filter Accuracy:       {validation['filter_accuracy']:5.1f}%")
    lines.append("")
    lines.append(f"Frames Compared:       {validation['frames_compared']}")
    lines.append(f"Differences Found:     {validation['differences_found']}")
    lines.append("")
    lines.append(f"Grade:                 {grade}")

    if grade == "EXCELLENT":
        lines.append("Recommendation:        Excellent! Minor tweaks may achieve 100%")
    elif grade == "GOOD":
        lines.append("Recommendation:        Very good, review differences for improvements")
    elif grade == "FAIR":
        lines.append("Recommendation:        Good start, focus on register sequences")
    else:
        lines.append("Recommendation:        Needs work, check table extraction and packing")

    return "\n".join(lines)
