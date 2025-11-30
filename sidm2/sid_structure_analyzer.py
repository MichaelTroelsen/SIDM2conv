"""
SID Structure Analyzer

Analyzes SID music structure using existing validated tools:
- siddump for register-level analysis
- Heuristics to detect patterns, sequences, instruments
- Comparison capabilities for before/after conversion

This uses proven tools instead of reimplementing CPU emulation.
"""

import os
import re
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class SIDStructureAnalyzer:
    """Analyze SID file structure using siddump output"""

    SID_REGISTERS = [
        'FREQ_LO_1', 'FREQ_HI_1', 'PW_LO_1', 'PW_HI_1', 'CONTROL_1', 'ATTACK_DECAY_1', 'SUSTAIN_RELEASE_1',
        'FREQ_LO_2', 'FREQ_HI_2', 'PW_LO_2', 'PW_HI_2', 'CONTROL_2', 'ATTACK_DECAY_2', 'SUSTAIN_RELEASE_2',
        'FREQ_LO_3', 'FREQ_HI_3', 'PW_LO_3', 'PW_HI_3', 'CONTROL_3', 'ATTACK_DECAY_3', 'SUSTAIN_RELEASE_3',
        'FILTER_CUTOFF_LO', 'FILTER_CUTOFF_HI', 'FILTER_CONTROL', 'FILTER_MODE_VOL'
    ]

    NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']

    def __init__(self, siddump_path: str = "tools/siddump.exe"):
        self.siddump_path = Path(siddump_path)
        if not self.siddump_path.exists():
            raise FileNotFoundError(f"siddump not found at {siddump_path}")

    def analyze_structure(self, sid_path: str, duration: int = 30) -> Dict:
        """
        Analyze SID file structure using siddump

        Args:
            sid_path: Path to SID file
            duration: Duration to analyze in seconds

        Returns:
            Structure dictionary with extracted information
        """
        logger.info(f"Analyzing structure of {sid_path}...")

        # Run siddump to get register dumps
        dump_data = self._run_siddump(sid_path, duration)

        if not dump_data:
            logger.error("Failed to get siddump output")
            return self._empty_structure()

        # Parse siddump output
        frames = self._parse_siddump(dump_data)

        # Analyze structure
        structure = {
            'file': os.path.basename(sid_path),
            'duration': duration,
            'total_frames': len(frames),
            'voices': self._analyze_voices(frames),
            'instruments': self._detect_instruments(frames),
            'patterns': self._detect_patterns(frames),
            'filter_usage': self._analyze_filter(frames),
            'statistics': {}
        }

        # Calculate statistics
        structure['statistics'] = self._calculate_statistics(structure)

        logger.info(f"Structure analysis complete. Frames: {len(frames)}")

        return structure

    def _run_siddump(self, sid_path: str, duration: int) -> str:
        """Run siddump and capture output"""
        try:
            result = subprocess.run(
                [str(self.siddump_path.absolute()), sid_path, f'-t{duration}'],
                capture_output=True,
                text=True,
                timeout=duration + 30
            )

            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"siddump failed: {result.stderr}")
                return ""

        except subprocess.TimeoutExpired:
            logger.error(f"siddump timed out after {duration + 30} seconds")
            return ""
        except Exception as e:
            logger.error(f"siddump execution failed: {e}")
            return ""

    def _parse_siddump(self, dump_data: str) -> List[Dict]:
        """Parse siddump output into frame data"""
        frames = []
        current_frame = None

        for line in dump_data.split('\n'):
            line = line.strip()

            # Frame marker (cycle count)
            if line.startswith('$'):
                # New frame - save previous if exists
                if current_frame:
                    frames.append(current_frame)

                current_frame = {
                    'registers': [0] * 25,  # 25 SID registers
                    'voice1': {},
                    'voice2': {},
                    'voice3': {},
                    'filter': {}
                }

            # Register write: D400 01 (address value)
            elif current_frame and len(line) >= 7:
                parts = line.split()
                if len(parts) >= 2:
                    addr_str = parts[0]
                    val_str = parts[1]

                    if addr_str.startswith('D4') or addr_str.startswith('d4'):
                        try:
                            addr = int(addr_str, 16)
                            value = int(val_str, 16)

                            # Store in register array
                            reg_offset = addr - 0xD400
                            if 0 <= reg_offset < 25:
                                current_frame['registers'][reg_offset] = value
                        except ValueError:
                            pass

        # Add last frame
        if current_frame:
            frames.append(current_frame)

        # Post-process frames to extract voice/filter data
        for frame in frames:
            self._extract_frame_data(frame)

        return frames

    def _extract_frame_data(self, frame: Dict):
        """Extract voice and filter data from raw registers"""
        regs = frame['registers']

        # Voice 1
        frame['voice1'] = {
            'freq': (regs[1] << 8) | regs[0],
            'pw': (regs[3] << 8) | regs[2],
            'control': regs[4],
            'gate': bool(regs[4] & 0x01),
            'waveform': (regs[4] >> 4) & 0x0F,
            'ad': regs[5],
            'sr': regs[6]
        }

        # Voice 2
        frame['voice2'] = {
            'freq': (regs[8] << 8) | regs[7],
            'pw': (regs[10] << 8) | regs[9],
            'control': regs[11],
            'gate': bool(regs[11] & 0x01),
            'waveform': (regs[11] >> 4) & 0x0F,
            'ad': regs[12],
            'sr': regs[13]
        }

        # Voice 3
        frame['voice3'] = {
            'freq': (regs[15] << 8) | regs[14],
            'pw': (regs[17] << 8) | regs[16],
            'control': regs[18],
            'gate': bool(regs[18] & 0x01),
            'waveform': (regs[18] >> 4) & 0x0F,
            'ad': regs[19],
            'sr': regs[20]
        }

        # Filter
        frame['filter'] = {
            'cutoff': (regs[22] << 8) | regs[21],
            'control': regs[23],
            'mode_vol': regs[24]
        }

    def _analyze_voices(self, frames: List[Dict]) -> Dict:
        """Analyze voice activity across all frames"""
        voices = {}

        for voice_num in range(1, 4):
            voice_key = f'voice{voice_num}'
            activity = []
            note_events = []

            prev_gate = False
            prev_freq = 0

            for frame_num, frame in enumerate(frames):
                voice = frame[voice_key]

                # Detect note events (gate on with frequency change)
                if voice['gate'] and voice['freq'] > 0:
                    if not prev_gate or voice['freq'] != prev_freq:
                        # New note
                        note_name, note_num = self._freq_to_note(voice['freq'])

                        event = {
                            'frame': frame_num,
                            'time': frame_num / 50.0,  # PAL timing
                            'note': note_name,
                            'note_num': note_num,
                            'freq': voice['freq'],
                            'waveform': voice['waveform'],
                            'pw': voice['pw'],
                            'ad': voice['ad'],
                            'sr': voice['sr']
                        }

                        note_events.append(event)

                        activity.append({
                            'frame': frame_num,
                            'active': True,
                            'note': note_name
                        })

                prev_gate = voice['gate']
                prev_freq = voice['freq']

            voices[voice_num] = {
                'note_events': note_events,
                'activity': activity,
                'unique_notes': len(set(e['note'] for e in note_events)),
                'total_notes': len(note_events)
            }

        return voices

    def _detect_instruments(self, frames: List[Dict]) -> Dict:
        """Detect unique instrument combinations (ADSR + waveform)"""
        instruments = {}
        instr_signatures = {}

        for frame in frames:
            for voice_num in range(1, 4):
                voice_key = f'voice{voice_num}'
                voice = frame[voice_key]

                if voice['gate']:
                    signature = (voice['waveform'], voice['ad'], voice['sr'])

                    if signature not in instr_signatures:
                        instr_id = len(instr_signatures)
                        instr_signatures[signature] = {
                            'id': instr_id,
                            'waveform': voice['waveform'],
                            'ad': voice['ad'],
                            'sr': voice['sr'],
                            'usage_count': 0
                        }

                    instr_signatures[signature]['usage_count'] += 1

        return {i['id']: {
            'waveform': sig[0],
            'attack_decay': sig[1],
            'sustain_release': sig[2],
            'usage_count': i['usage_count']
        } for sig, i in instr_signatures.items()}

    def _detect_patterns(self, frames: List[Dict]) -> Dict:
        """Detect repeating patterns in each voice"""
        patterns = {}

        for voice_num in range(1, 4):
            # Extract note sequence for this voice
            notes = []
            for frame in frames:
                voice = frame[f'voice{voice_num}']
                if voice['gate'] and voice['freq'] > 0:
                    note_name, _ = self._freq_to_note(voice['freq'])
                    notes.append(note_name)

            # Find repeating sequences
            voice_patterns = []
            min_len = 4
            max_len = min(16, len(notes) // 2)

            for pattern_len in range(min_len, max_len + 1):
                for start in range(len(notes) - pattern_len * 2):
                    pattern = notes[start:start + pattern_len]
                    next_seq = notes[start + pattern_len:start + pattern_len * 2]

                    if pattern == next_seq:
                        voice_patterns.append({
                            'length': pattern_len,
                            'start': start,
                            'pattern': pattern
                        })
                        break  # Found one pattern of this length

            patterns[voice_num] = voice_patterns[:5]  # Keep top 5

        return patterns

    def _analyze_filter(self, frames: List[Dict]) -> Dict:
        """Analyze filter usage"""
        filter_changes = []
        prev_cutoff = 0

        for frame_num, frame in enumerate(frames):
            filt = frame['filter']
            if filt['cutoff'] != prev_cutoff:
                filter_changes.append({
                    'frame': frame_num,
                    'time': frame_num / 50.0,
                    'cutoff': filt['cutoff'],
                    'control': filt['control'],
                    'mode_vol': filt['mode_vol']
                })
                prev_cutoff = filt['cutoff']

        return {
            'total_changes': len(filter_changes),
            'changes': filter_changes[:20]  # Keep first 20 for summary
        }

    def _calculate_statistics(self, structure: Dict) -> Dict:
        """Calculate overall statistics"""
        stats = {
            'total_frames': structure['total_frames'],
            'duration': structure['duration'],
            'voices': {}
        }

        for voice_num in range(1, 4):
            voice = structure['voices'][voice_num]
            stats['voices'][voice_num] = {
                'total_notes': voice['total_notes'],
                'unique_notes': voice['unique_notes'],
                'activity_percentage': (len(voice['activity']) / max(structure['total_frames'], 1)) * 100
            }

        stats['total_instruments'] = len(structure['instruments'])
        stats['filter_changes'] = structure['filter_usage']['total_changes']

        return stats

    def _freq_to_note(self, freq: int) -> Tuple[str, int]:
        """Convert SID frequency to note name and MIDI number"""
        if freq == 0:
            return '---', 0

        # PAL C64 frequency formula
        c64_freq = freq * 985248.0 / 16777216.0

        # Calculate MIDI note
        if c64_freq > 0:
            import math
            semitones_from_a4 = 12 * (math.log2(c64_freq / 440.0))
            midi_note = int(round(69 + semitones_from_a4))

            octave = (midi_note // 12) - 1
            note_index = midi_note % 12

            note_name = f"{self.NOTE_NAMES[note_index]}{octave}"
            return note_name, midi_note

        return '---', 0

    def _empty_structure(self) -> Dict:
        """Return empty structure template"""
        return {
            'file': '',
            'duration': 0,
            'total_frames': 0,
            'voices': {i: {'note_events': [], 'activity': [], 'unique_notes': 0, 'total_notes': 0} for i in range(1, 4)},
            'instruments': {},
            'patterns': {i: [] for i in range(1, 4)},
            'filter_usage': {'total_changes': 0, 'changes': []},
            'statistics': {}
        }

    def save_structure(self, structure: Dict, output_path: str):
        """Save structure to JSON file"""
        with open(output_path, 'w') as f:
            json.dump(structure, f, indent=2)
        logger.info(f"Structure saved to {output_path}")

    def compare_structures(self, struct1: Dict, struct2: Dict) -> Dict:
        """
        Compare two structures

        Returns:
            Comparison results with similarity scores
        """
        comparison = {
            'voice_comparison': {},
            'instrument_comparison': {},
            'overall_similarity': 0.0
        }

        # Compare voices
        voice_similarities = []
        for voice_num in range(1, 4):
            v1 = struct1['voices'][voice_num]
            v2 = struct2['voices'][voice_num]

            # Compare note counts
            count_sim = 1.0 - abs(v1['total_notes'] - v2['total_notes']) / max(v1['total_notes'], v2['total_notes'], 1)

            # Compare unique notes
            unique_sim = 1.0 - abs(v1['unique_notes'] - v2['unique_notes']) / max(v1['unique_notes'], v2['unique_notes'], 1)

            # Compare note sequences
            notes1 = [e['note'] for e in v1['note_events']]
            notes2 = [e['note'] for e in v2['note_events']]

            matching_notes = 0
            total_compared = 0
            for i in range(min(len(notes1), len(notes2))):
                total_compared += 1
                if notes1[i] == notes2[i]:
                    matching_notes += 1

            note_seq_sim = matching_notes / max(total_compared, 1)

            voice_sim = (count_sim * 0.3 + unique_sim * 0.3 + note_seq_sim * 0.4)
            voice_similarities.append(voice_sim)

            comparison['voice_comparison'][voice_num] = {
                'similarity': voice_sim * 100,
                'note_count_diff': abs(v1['total_notes'] - v2['total_notes']),
                'unique_notes_diff': abs(v1['unique_notes'] - v2['unique_notes']),
                'matching_notes': matching_notes,
                'total_compared': total_compared
            }

        # Compare instruments
        instr1_sigs = set((i['waveform'], i['attack_decay'], i['sustain_release'])
                         for i in struct1['instruments'].values())
        instr2_sigs = set((i['waveform'], i['attack_decay'], i['sustain_release'])
                         for i in struct2['instruments'].values())

        matching_instr = len(instr1_sigs & instr2_sigs)
        total_instr = len(instr1_sigs | instr2_sigs)

        instr_sim = matching_instr / max(total_instr, 1)

        comparison['instrument_comparison'] = {
            'similarity': instr_sim * 100,
            'matching': matching_instr,
            'total_unique': total_instr
        }

        # Overall similarity (voices 70%, instruments 30%)
        overall = (sum(voice_similarities) / 3) * 0.70 + instr_sim * 0.30
        comparison['overall_similarity'] = overall * 100

        return comparison


def analyze_and_compare(original_sid: str, converted_sid: str,
                        output_dir: str = None, duration: int = 30) -> Dict:
    """
    Complete workflow: analyze both SIDs and compare

    Args:
        original_sid: Path to original SID
        converted_sid: Path to converted SID
        output_dir: Output directory for results
        duration: Duration to analyze

    Returns:
        Comparison results
    """
    analyzer = SIDStructureAnalyzer()

    logger.info("Analyzing original SID...")
    struct1 = analyzer.analyze_structure(original_sid, duration)

    logger.info("Analyzing converted SID...")
    struct2 = analyzer.analyze_structure(converted_sid, duration)

    # Save structures
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        analyzer.save_structure(struct1, os.path.join(output_dir, "original_structure.json"))
        analyzer.save_structure(struct2, os.path.join(output_dir, "converted_structure.json"))

    logger.info("Comparing structures...")
    comparison = analyzer.compare_structures(struct1, struct2)

    # Save comparison
    if output_dir:
        with open(os.path.join(output_dir, "structure_comparison.json"), 'w') as f:
            json.dump(comparison, f, indent=2)

    return comparison
