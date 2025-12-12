"""SID accuracy calculation module.

This module provides reusable accuracy calculation for comparing
original and exported SID files based on register-level comparison.

Can work with:
- Pre-generated siddump output files (for pipeline integration)
- Live SID files (runs siddump automatically)

Version: 1.4.1
Date: 2025-12-12

Usage:
    # From existing dump files (pipeline integration)
    accuracy = calculate_accuracy_from_dumps(
        'output/file_original.dump',
        'output/file_exported.dump'
    )

    # From SID files directly
    accuracy = calculate_accuracy_from_sids(
        'original.sid',
        'exported.sid',
        duration=30
    )
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess


class SIDRegisterCapture:
    """Captures SID register writes frame by frame.

    Can capture from:
    - Siddump output text (for reusing existing dumps)
    - SID file directly (runs siddump)
    """

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

    def __init__(self, sid_path: Optional[str] = None,
                 siddump_text: Optional[str] = None,
                 duration: int = 30):
        """Initialize register capture.

        Args:
            sid_path: Path to SID file (for live capture)
            siddump_text: Pre-generated siddump output text
            duration: Duration in seconds for live capture
        """
        self.sid_path = Path(sid_path) if sid_path else None
        self.duration = duration
        self.frames = []
        self.register_history = {i: [] for i in range(0x19)}
        self.stats = {
            'total_frames': 0,
            'total_writes': 0,
            'voice_activity': {1: 0, 2: 0, 3: 0}
        }

        # If siddump text provided, parse it immediately
        if siddump_text:
            self._parse_siddump_output(siddump_text)

    def capture_from_file(self, dump_path: str) -> bool:
        """Capture from existing siddump file.

        Args:
            dump_path: Path to .dump file

        Returns:
            True if successful
        """
        try:
            dump_file = Path(dump_path)
            if not dump_file.exists():
                return False

            siddump_text = dump_file.read_text(encoding='utf-8', errors='ignore')
            self._parse_siddump_output(siddump_text)
            return True
        except Exception:
            return False

    def capture_from_sid(self) -> bool:
        """Capture by running siddump on SID file.

        Returns:
            True if successful
        """
        if not self.sid_path or not self.sid_path.exists():
            return False

        siddump_exe = Path('tools/siddump.exe')
        if not siddump_exe.exists():
            return False

        try:
            result = subprocess.run(
                [str(siddump_exe.absolute()),
                 str(self.sid_path.absolute()),
                 '-z',
                 f'-t{self.duration}'],
                capture_output=True,
                text=True,
                timeout=self.duration + 10
            )

            if result.returncode != 0:
                return False

            self._parse_siddump_output(result.stdout)
            return True
        except Exception:
            return False

    def _parse_siddump_output(self, output: str):
        """Parse siddump table format into frame data."""
        for line in output.split('\n'):
            line = line.strip()
            if not line or line.startswith('+') or '| Frame |' in line:
                continue

            if line.startswith('|'):
                parts = [p.strip() for p in line.split('|')[1:]]
                if len(parts) < 5:
                    continue

                try:
                    frame_num = int(parts[0])
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

                            # Waveform, ADSR, Pulse width
                            wf_idx, adsr_idx, pw_idx = 3, 4, 5

                            if wf_idx < len(voice_data):
                                wf_str = voice_data[wf_idx]
                                if wf_str not in ('.', '..', '....'):
                                    try:
                                        wf = int(wf_str, 16)
                                        frame_data[voice_idx * 7 + 4] = wf
                                    except ValueError:
                                        pass

                            if adsr_idx < len(voice_data):
                                adsr_str = voice_data[adsr_idx]
                                if adsr_str != '....':
                                    try:
                                        if len(adsr_str) == 4:
                                            ad = int(adsr_str[:2], 16)
                                            sr = int(adsr_str[2:], 16)
                                            frame_data[voice_idx * 7 + 5] = ad
                                            frame_data[voice_idx * 7 + 6] = sr
                                    except ValueError:
                                        pass

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

                    # Store frame
                    self.frames.append(frame_data)
                    self.stats['total_frames'] += 1

                    # Update register history
                    for reg, value in frame_data.items():
                        self.register_history[reg].append({
                            'frame': frame_num,
                            'value': value
                        })
                        self.stats['total_writes'] += 1

                except (ValueError, IndexError):
                    continue


class SIDComparator:
    """Compares two SID register captures for accuracy."""

    def __init__(self, original: SIDRegisterCapture, exported: SIDRegisterCapture):
        self.original = original
        self.exported = exported

    def compare(self) -> Dict:
        """Compare captures and calculate accuracy metrics.

        Returns:
            Dict with accuracy percentages and detailed results
        """
        results = {
            'frame_accuracy': 0.0,
            'voice_accuracy': {},
            'register_accuracy': {},
            'filter_accuracy': 0.0,
            'overall_accuracy': 0.0
        }

        # Frame-by-frame comparison
        max_frames = min(len(self.original.frames), len(self.exported.frames))
        if max_frames == 0:
            return results

        matching_frames = sum(
            1 for i in range(max_frames)
            if self._frames_match(self.original.frames[i], self.exported.frames[i])
        )
        results['frame_accuracy'] = (matching_frames / max_frames * 100)

        # Voice accuracy
        for voice in range(1, 4):
            orig_freq = self._get_frequencies(self.original, voice)
            exp_freq = self._get_frequencies(self.exported, voice)
            orig_wave = self._get_waveforms(self.original, voice)
            exp_wave = self._get_waveforms(self.exported, voice)

            freq_matches = sum(1 for o, e in zip(orig_freq, exp_freq) if o == e)
            wave_matches = sum(1 for o, e in zip(orig_wave, exp_wave) if o == e)

            freq_acc = (freq_matches / len(orig_freq) * 100) if orig_freq else 0
            wave_acc = (wave_matches / len(orig_wave) * 100) if orig_wave else 0

            results['voice_accuracy'][f'voice{voice}'] = {
                'frequency': freq_acc,
                'waveform': wave_acc
            }

        # Register accuracy
        for reg in range(0x19):
            orig_hist = self.original.register_history[reg]
            exp_hist = self.exported.register_history[reg]

            if not orig_hist and not exp_hist:
                continue

            matches = sum(
                1 for i in range(min(len(orig_hist), len(exp_hist)))
                if orig_hist[i]['value'] == exp_hist[i]['value']
            )
            total = max(len(orig_hist), len(exp_hist))

            if total > 0:
                reg_name = SIDRegisterCapture.REGISTER_NAMES.get(reg, f"Reg_{reg:02X}")
                results['register_accuracy'][reg_name] = (matches / total * 100)

        # Filter accuracy
        orig_filter = self._get_filter_values(self.original)
        exp_filter = self._get_filter_values(self.exported)
        filter_matches = sum(1 for o, e in zip(orig_filter, exp_filter) if o == e)
        if orig_filter:
            results['filter_accuracy'] = (filter_matches / len(orig_filter) * 100)

        # Overall accuracy (weighted)
        frame_weight = 0.4
        voice_weight = 0.3
        register_weight = 0.2
        filter_weight = 0.1

        voice_scores = [
            (v['frequency'] + v['waveform']) / 2
            for v in results['voice_accuracy'].values()
        ]
        avg_voice = sum(voice_scores) / len(voice_scores) if voice_scores else 0

        reg_scores = list(results['register_accuracy'].values())
        avg_register = sum(reg_scores) / len(reg_scores) if reg_scores else 0

        results['overall_accuracy'] = (
            results['frame_accuracy'] * frame_weight +
            avg_voice * voice_weight +
            avg_register * register_weight +
            results['filter_accuracy'] * filter_weight
        )

        return results

    def _frames_match(self, frame1: Dict, frame2: Dict) -> bool:
        """Check if two frames are identical."""
        if len(frame1) != len(frame2):
            return False
        return all(frame2.get(reg) == val for reg, val in frame1.items())

    def _get_frequencies(self, capture: SIDRegisterCapture, voice: int) -> List[int]:
        """Extract frequency values for a voice."""
        freq_lo = 0x00 + (voice - 1) * 7
        freq_hi = 0x01 + (voice - 1) * 7

        frequencies = []
        for frame in capture.frames:
            if freq_lo in frame and freq_hi in frame:
                freq = frame[freq_lo] | (frame[freq_hi] << 8)
                frequencies.append(freq)
        return frequencies

    def _get_waveforms(self, capture: SIDRegisterCapture, voice: int) -> List[int]:
        """Extract waveform control bytes for a voice."""
        control_reg = 0x04 + (voice - 1) * 7
        return [frame[control_reg] for frame in capture.frames if control_reg in frame]

    def _get_filter_values(self, capture: SIDRegisterCapture) -> List[Tuple]:
        """Extract filter cutoff/resonance/mode tuples."""
        filters = []
        for frame in capture.frames:
            cutoff_lo = frame.get(0x15, 0)
            cutoff_hi = frame.get(0x16, 0)
            cutoff = cutoff_lo | ((cutoff_hi & 0x07) << 8)
            resonance = frame.get(0x17, 0)
            mode = frame.get(0x18, 0)

            if 0x15 in frame or 0x16 in frame or 0x17 in frame or 0x18 in frame:
                filters.append((cutoff, resonance, mode))
        return filters


def calculate_accuracy_from_dumps(original_dump: str, exported_dump: str) -> Optional[Dict]:
    """Calculate accuracy from existing siddump files.

    Args:
        original_dump: Path to original SID dump file
        exported_dump: Path to exported SID dump file

    Returns:
        Dict with accuracy metrics, or None if failed
    """
    try:
        original_capture = SIDRegisterCapture()
        if not original_capture.capture_from_file(original_dump):
            return None

        exported_capture = SIDRegisterCapture()
        if not exported_capture.capture_from_file(exported_dump):
            return None

        comparator = SIDComparator(original_capture, exported_capture)
        return comparator.compare()

    except Exception:
        return None


def calculate_accuracy_from_sids(original_sid: str, exported_sid: str,
                                 duration: int = 30) -> Optional[Dict]:
    """Calculate accuracy by running siddump on SID files.

    Args:
        original_sid: Path to original SID file
        exported_sid: Path to exported SID file
        duration: Capture duration in seconds

    Returns:
        Dict with accuracy metrics, or None if failed
    """
    try:
        original_capture = SIDRegisterCapture(sid_path=original_sid, duration=duration)
        if not original_capture.capture_from_sid():
            return None

        exported_capture = SIDRegisterCapture(sid_path=exported_sid, duration=duration)
        if not exported_capture.capture_from_sid():
            return None

        comparator = SIDComparator(original_capture, exported_capture)
        return comparator.compare()

    except Exception:
        return None
