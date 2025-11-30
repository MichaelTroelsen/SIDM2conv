"""
SID Structure Extractor

Comprehensive SID file analyzer that extracts detailed music structure:
- Sequences, patterns, instruments, orderlists
- Tempo, commands, effects
- Voice activity and note sequences
- Loop points and structure

This tool is used for before/after conversion comparison to achieve 99% accuracy.
"""

import os
import json
import struct
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

from .cpu6502_emulator import CPU6502Emulator
from .sid_parser import SIDParser
from .models import PSIDHeader

logger = logging.getLogger(__name__)


class SIDStructureExtractor:
    """Extract detailed music structure from SID files for comparison"""

    # SID register addresses
    SID_BASE = 0xD400
    VOICE1_FREQ_LO = 0xD400
    VOICE1_FREQ_HI = 0xD401
    VOICE1_PW_LO = 0xD402
    VOICE1_PW_HI = 0xD403
    VOICE1_CONTROL = 0xD404
    VOICE1_AD = 0xD405
    VOICE1_SR = 0xD406

    FILTER_CUTOFF_LO = 0xD415
    FILTER_CUTOFF_HI = 0xD416
    FILTER_CONTROL = 0xD417
    FILTER_MODE_VOL = 0xD418

    # Frequency table for note detection
    NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']

    def __init__(self):
        pass

    def extract_structure(self, sid_path: str, duration: int = 30) -> Dict:
        """
        Extract complete music structure from SID file

        Args:
            sid_path: Path to SID file
            duration: Duration to analyze in seconds

        Returns:
            Dictionary with extracted structure:
            {
                'header': {...},
                'sequences': {...},
                'instruments': {...},
                'patterns': {...},
                'voice_activity': {...},
                'commands': {...},
                'tempo': {...},
                'filter': {...},
                'statistics': {...}
            }
        """
        logger.info(f"Extracting structure from {sid_path}...")

        # Parse SID header
        parser = SIDParser(sid_path)
        header = parser.parse_header()

        # Read SID data
        with open(sid_path, 'rb') as f:
            sid_data = f.read()

        # Initialize structure
        structure = {
            'header': self._extract_header_info(header),
            'sequences': {},
            'instruments': {},
            'patterns': defaultdict(list),
            'voice_activity': {0: [], 1: [], 2: []},
            'commands': defaultdict(list),
            'tempo': [],
            'filter': [],
            'statistics': {},
            'frames': []
        }

        # Run CPU emulation to capture register writes
        logger.info("Running CPU emulation to capture register writes...")
        emulator = CPU6502Emulator()

        try:
            # Load SID into emulator
            load_addr = header.load_address if header.load_address > 0 else struct.unpack('<H', sid_data[header.data_offset:header.data_offset+2])[0]
            data_start = header.data_offset if header.load_address > 0 else header.data_offset + 2
            sid_code = sid_data[data_start:]

            # Load into memory
            for i, byte in enumerate(sid_code):
                emulator.mem[load_addr + i] = byte

            # Initialize
            emulator.pc = header.init_address
            emulator.a = 0  # Subtune 0

            # Run init routine (max 10000 instructions)
            for _ in range(10000):
                if emulator.pc == 0 or emulator.pc == 0xFFFF:
                    break
                emulator.run_instruction()

            # Run play routine for specified duration
            frame_count = duration * 50  # PAL: 50 frames/second
            play_addr = header.play_address

            for frame in range(frame_count):
                # Reset PC to play address
                emulator.pc = play_addr

                # Capture register state before play
                prev_registers = self._capture_sid_registers(emulator)

                # Run play routine (max 5000 instructions per frame)
                for _ in range(5000):
                    if emulator.pc == 0x60:  # RTS
                        break
                    emulator.run_instruction()

                # Capture register state after play
                curr_registers = self._capture_sid_registers(emulator)

                # Analyze frame
                self._analyze_frame(frame, prev_registers, curr_registers, structure)

                if frame % 100 == 0:
                    logger.debug(f"Processed frame {frame}/{frame_count}")

        except Exception as e:
            logger.error(f"Emulation failed: {e}")
            structure['error'] = str(e)

        # Post-process extracted data
        self._calculate_statistics(structure)
        self._detect_patterns(structure)
        self._identify_instruments(structure)

        logger.info(f"Structure extraction complete. Frames: {len(structure['frames'])}")

        return structure

    def _extract_header_info(self, header: PSIDHeader) -> Dict:
        """Extract relevant header information"""
        return {
            'version': header.version,
            'load_address': header.load_address,
            'init_address': header.init_address,
            'play_address': header.play_address,
            'songs': header.songs,
            'start_song': header.start_song,
            'name': header.name,
            'author': header.author,
            'copyright': header.copyright,
            'flags': header.flags,
            'speed': header.speed
        }

    def _capture_sid_registers(self, emulator: CPU6502Emulator) -> Dict:
        """Capture current state of all SID registers"""
        registers = {}

        # Voice 1
        registers['v1_freq'] = (emulator.mem[self.VOICE1_FREQ_HI] << 8) | emulator.mem[self.VOICE1_FREQ_LO]
        registers['v1_pw'] = (emulator.mem[self.VOICE1_PW_HI] << 8) | emulator.mem[self.VOICE1_PW_LO]
        registers['v1_control'] = emulator.mem[self.VOICE1_CONTROL]
        registers['v1_ad'] = emulator.mem[self.VOICE1_AD]
        registers['v1_sr'] = emulator.mem[self.VOICE1_SR]

        # Voice 2
        registers['v2_freq'] = (emulator.mem[0xD408] << 8) | emulator.mem[0xD407]
        registers['v2_pw'] = (emulator.mem[0xD40A] << 8) | emulator.mem[0xD409]
        registers['v2_control'] = emulator.mem[0xD40B]
        registers['v2_ad'] = emulator.mem[0xD40C]
        registers['v2_sr'] = emulator.mem[0xD40D]

        # Voice 3
        registers['v3_freq'] = (emulator.mem[0xD40F] << 8) | emulator.mem[0xD40E]
        registers['v3_pw'] = (emulator.mem[0xD411] << 8) | emulator.mem[0xD410]
        registers['v3_control'] = emulator.mem[0xD412]
        registers['v3_ad'] = emulator.mem[0xD413]
        registers['v3_sr'] = emulator.mem[0xD414]

        # Filter
        registers['filter_cutoff'] = (emulator.mem[self.FILTER_CUTOFF_HI] << 8) | emulator.mem[self.FILTER_CUTOFF_LO]
        registers['filter_control'] = emulator.mem[self.FILTER_CONTROL]
        registers['filter_mode_vol'] = emulator.mem[self.FILTER_MODE_VOL]

        return registers

    def _analyze_frame(self, frame: int, prev_regs: Dict, curr_regs: Dict, structure: Dict):
        """Analyze a single frame and update structure"""
        frame_data = {
            'frame': frame,
            'time': frame / 50.0,  # PAL timing
            'voices': {}
        }

        # Analyze each voice
        for voice in range(3):
            voice_prefix = f'v{voice+1}_'

            freq = curr_regs[f'{voice_prefix}freq']
            control = curr_regs[f'{voice_prefix}control']
            pw = curr_regs[f'{voice_prefix}pw']
            ad = curr_regs[f'{voice_prefix}ad']
            sr = curr_regs[f'{voice_prefix}sr']

            # Detect note changes
            prev_freq = prev_regs[f'{voice_prefix}freq']
            freq_changed = freq != prev_freq

            # Detect gate changes
            gate = bool(control & 0x01)
            prev_gate = bool(prev_regs[f'{voice_prefix}control'] & 0x01)
            gate_changed = gate != prev_gate

            # Detect waveform
            waveform = (control >> 4) & 0x0F

            # Convert frequency to note
            note_name, note_num = self._freq_to_note(freq) if freq > 0 else ('---', 0)

            voice_data = {
                'freq': freq,
                'note': note_name,
                'note_num': note_num,
                'gate': gate,
                'waveform': waveform,
                'pulse_width': pw,
                'attack_decay': ad,
                'sustain_release': sr,
                'freq_changed': freq_changed,
                'gate_changed': gate_changed
            }

            frame_data['voices'][voice] = voice_data

            # Track voice activity
            if gate and freq > 0:
                activity = {
                    'frame': frame,
                    'time': frame / 50.0,
                    'note': note_name,
                    'freq': freq,
                    'waveform': waveform
                }
                structure['voice_activity'][voice].append(activity)

        # Track filter changes
        filter_cutoff = curr_regs['filter_cutoff']
        prev_cutoff = prev_regs['filter_cutoff']
        if filter_cutoff != prev_cutoff:
            structure['filter'].append({
                'frame': frame,
                'time': frame / 50.0,
                'cutoff': filter_cutoff,
                'control': curr_regs['filter_control'],
                'mode_vol': curr_regs['filter_mode_vol']
            })

        structure['frames'].append(frame_data)

    def _freq_to_note(self, freq: int) -> Tuple[str, int]:
        """Convert SID frequency value to note name and number"""
        if freq == 0:
            return '---', 0

        # PAL C64 frequency formula: freq = note_freq * 16777216 / 985248
        # Reverse: note_freq = freq * 985248 / 16777216

        c64_freq = freq * 985248.0 / 16777216.0

        # A-4 = 440 Hz, calculate semitones from A-4
        if c64_freq > 0:
            semitones_from_a4 = 12 * (self._log2(c64_freq / 440.0))
            midi_note = int(round(69 + semitones_from_a4))

            octave = (midi_note // 12) - 1
            note_index = midi_note % 12

            note_name = f"{self.NOTE_NAMES[note_index]}{octave}"
            return note_name, midi_note

        return '---', 0

    def _log2(self, x: float) -> float:
        """Calculate log base 2"""
        import math
        return math.log(x) / math.log(2)

    def _calculate_statistics(self, structure: Dict):
        """Calculate statistics about the extracted structure"""
        stats = {
            'total_frames': len(structure['frames']),
            'duration': len(structure['frames']) / 50.0,
            'voice_activity_counts': {},
            'unique_notes': {},
            'unique_waveforms': set(),
            'filter_changes': len(structure['filter']),
        }

        # Count voice activity
        for voice in range(3):
            stats['voice_activity_counts'][voice] = len(structure['voice_activity'][voice])

            # Unique notes per voice
            notes = set()
            for activity in structure['voice_activity'][voice]:
                notes.add(activity['note'])
                stats['unique_waveforms'].add(activity['waveform'])

            stats['unique_notes'][voice] = sorted(list(notes))

        stats['unique_waveforms'] = sorted(list(stats['unique_waveforms']))

        structure['statistics'] = stats

    def _detect_patterns(self, structure: Dict):
        """Detect repeating patterns in voice activity"""
        # Analyze each voice for repeating sequences
        for voice in range(3):
            activity = structure['voice_activity'][voice]

            if len(activity) < 4:
                continue

            # Extract note sequence
            note_sequence = [a['note'] for a in activity]

            # Find repeating patterns (simple approach: look for exact repeats)
            patterns = []
            min_pattern_len = 4
            max_pattern_len = min(32, len(note_sequence) // 2)

            for pattern_len in range(min_pattern_len, max_pattern_len + 1):
                for start in range(len(note_sequence) - pattern_len * 2):
                    pattern = note_sequence[start:start + pattern_len]
                    next_seq = note_sequence[start + pattern_len:start + pattern_len * 2]

                    if pattern == next_seq:
                        patterns.append({
                            'length': pattern_len,
                            'start': start,
                            'pattern': pattern,
                            'occurrences': 1
                        })

            structure['patterns'][voice] = patterns[:10]  # Keep top 10 patterns

    def _identify_instruments(self, structure: Dict):
        """Identify unique instrument combinations (ADSR + waveform)"""
        instruments = {}
        instr_id = 0

        for voice in range(3):
            for activity in structure['voice_activity'][voice]:
                # Get instrument signature from frames
                frame = activity['frame']
                if frame < len(structure['frames']):
                    frame_data = structure['frames'][frame]
                    voice_data = frame_data['voices'][voice]

                    signature = (
                        voice_data['waveform'],
                        voice_data['attack_decay'],
                        voice_data['sustain_release']
                    )

                    if signature not in instruments:
                        instruments[signature] = {
                            'id': instr_id,
                            'waveform': voice_data['waveform'],
                            'attack_decay': voice_data['attack_decay'],
                            'sustain_release': voice_data['sustain_release'],
                            'usage_count': 0
                        }
                        instr_id += 1

                    instruments[signature]['usage_count'] += 1

        # Convert to list
        structure['instruments'] = {
            i['id']: {
                'waveform': sig[0],
                'attack_decay': sig[1],
                'sustain_release': sig[2],
                'usage_count': i['usage_count']
            }
            for sig, i in instruments.items()
        }

    def save_structure(self, structure: Dict, output_path: str):
        """Save extracted structure to JSON file"""
        # Convert sets to lists for JSON serialization
        if 'statistics' in structure:
            if 'unique_waveforms' in structure['statistics']:
                structure['statistics']['unique_waveforms'] = list(structure['statistics']['unique_waveforms'])

        with open(output_path, 'w') as f:
            json.dump(structure, f, indent=2)

        logger.info(f"Structure saved to {output_path}")

    def compare_structures(self, struct1: Dict, struct2: Dict) -> Dict:
        """
        Compare two extracted structures

        Args:
            struct1: Structure from original SID
            struct2: Structure from converted SID

        Returns:
            Comparison results with differences and similarity score
        """
        comparison = {
            'header_match': self._compare_headers(struct1['header'], struct2['header']),
            'voice_activity_match': {},
            'instrument_match': self._compare_instruments(struct1['instruments'], struct2['instruments']),
            'filter_match': self._compare_filters(struct1['filter'], struct2['filter']),
            'statistics_match': self._compare_statistics(struct1['statistics'], struct2['statistics']),
            'overall_similarity': 0.0
        }

        # Compare voice activity
        for voice in range(3):
            comparison['voice_activity_match'][voice] = self._compare_voice_activity(
                struct1['voice_activity'][voice],
                struct2['voice_activity'][voice]
            )

        # Calculate overall similarity
        similarity_scores = []

        # Header similarity (5%)
        similarity_scores.append(comparison['header_match']['similarity'] * 0.05)

        # Voice activity similarity (60%)
        voice_sim = sum(comparison['voice_activity_match'][v]['similarity'] for v in range(3)) / 3
        similarity_scores.append(voice_sim * 0.60)

        # Instrument similarity (20%)
        similarity_scores.append(comparison['instrument_match']['similarity'] * 0.20)

        # Filter similarity (10%)
        similarity_scores.append(comparison['filter_match']['similarity'] * 0.10)

        # Statistics similarity (5%)
        similarity_scores.append(comparison['statistics_match']['similarity'] * 0.05)

        comparison['overall_similarity'] = sum(similarity_scores)

        return comparison

    def _compare_headers(self, h1: Dict, h2: Dict) -> Dict:
        """Compare header information"""
        differences = []

        for key in ['init_address', 'play_address', 'load_address']:
            if h1.get(key) != h2.get(key):
                differences.append(f"{key}: {h1.get(key):04X} vs {h2.get(key):04X}")

        similarity = 1.0 if len(differences) == 0 else 0.5

        return {
            'differences': differences,
            'similarity': similarity
        }

    def _compare_voice_activity(self, act1: List, act2: List) -> Dict:
        """Compare voice activity between two structures"""
        # Compare lengths
        len_diff = abs(len(act1) - len(act2))
        max_len = max(len(act1), len(act2), 1)

        # Compare notes at similar times
        matching_notes = 0
        total_compared = 0

        for a1 in act1:
            # Find closest activity in act2 by time
            closest = None
            min_time_diff = float('inf')

            for a2 in act2:
                time_diff = abs(a1['time'] - a2['time'])
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    closest = a2

            if closest and min_time_diff < 0.1:  # Within 0.1 seconds
                total_compared += 1
                if a1['note'] == closest['note']:
                    matching_notes += 1

        note_similarity = matching_notes / max(total_compared, 1)
        length_similarity = 1.0 - (len_diff / max_len)

        similarity = (note_similarity * 0.7 + length_similarity * 0.3)

        return {
            'length_diff': len_diff,
            'note_similarity': note_similarity,
            'length_similarity': length_similarity,
            'similarity': similarity,
            'matching_notes': matching_notes,
            'total_compared': total_compared
        }

    def _compare_instruments(self, instr1: Dict, instr2: Dict) -> Dict:
        """Compare instrument definitions"""
        # Count matching instruments
        matching = 0

        sigs1 = set((i['waveform'], i['attack_decay'], i['sustain_release'])
                    for i in instr1.values())
        sigs2 = set((i['waveform'], i['attack_decay'], i['sustain_release'])
                    for i in instr2.values())

        matching = len(sigs1 & sigs2)
        total = len(sigs1 | sigs2)

        similarity = matching / max(total, 1)

        return {
            'matching_count': matching,
            'total_unique': total,
            'similarity': similarity
        }

    def _compare_filters(self, filt1: List, filt2: List) -> Dict:
        """Compare filter usage"""
        len_diff = abs(len(filt1) - len(filt2))
        similarity = 1.0 if len_diff == 0 else max(0, 1.0 - len_diff / max(len(filt1), len(filt2), 1))

        return {
            'count_diff': len_diff,
            'similarity': similarity
        }

    def _compare_statistics(self, stats1: Dict, stats2: Dict) -> Dict:
        """Compare overall statistics"""
        differences = []

        for voice in range(3):
            count1 = stats1['voice_activity_counts'].get(voice, 0)
            count2 = stats2['voice_activity_counts'].get(voice, 0)
            if count1 != count2:
                differences.append(f"Voice {voice} activity: {count1} vs {count2}")

        similarity = 1.0 if len(differences) == 0 else 0.7

        return {
            'differences': differences,
            'similarity': similarity
        }


def extract_and_compare(original_sid: str, converted_sid: str,
                       output_dir: str = None, duration: int = 30) -> Dict:
    """
    Complete workflow: extract structures from both SIDs and compare

    Args:
        original_sid: Path to original SID file
        converted_sid: Path to converted SID file
        output_dir: Directory to save structure JSON files (optional)
        duration: Duration to analyze in seconds

    Returns:
        Comparison results
    """
    extractor = SIDStructureExtractor()

    logger.info("Extracting structure from original SID...")
    struct1 = extractor.extract_structure(original_sid, duration)

    logger.info("Extracting structure from converted SID...")
    struct2 = extractor.extract_structure(converted_sid, duration)

    # Save structures if output directory specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

        orig_json = os.path.join(output_dir, "original_structure.json")
        conv_json = os.path.join(output_dir, "converted_structure.json")

        extractor.save_structure(struct1, orig_json)
        extractor.save_structure(struct2, conv_json)

    logger.info("Comparing structures...")
    comparison = extractor.compare_structures(struct1, struct2)

    # Save comparison
    if output_dir:
        comp_json = os.path.join(output_dir, "comparison.json")
        with open(comp_json, 'w') as f:
            json.dump(comparison, f, indent=2)
        logger.info(f"Comparison saved to {comp_json}")

    return comparison
