"""
Confidence scoring system for SID to SF2 extraction quality.

Evaluates extraction quality for each component and provides percentage scores.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class ComponentScore:
    """Score for a single extraction component."""
    name: str
    score: float  # 0.0 to 100.0
    factors: Dict[str, float] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


@dataclass
class ExtractionConfidence:
    """Overall extraction confidence with per-component scores."""
    instruments: ComponentScore = None
    wave_table: ComponentScore = None
    pulse_table: ComponentScore = None
    filter_table: ComponentScore = None
    orderlist: ComponentScore = None
    commands: ComponentScore = None
    tempo: ComponentScore = None
    arp_table: ComponentScore = None
    notes: ComponentScore = None

    overall: float = 0.0  # Weighted average

    def __post_init__(self):
        if self.instruments is None:
            self.instruments = ComponentScore("Instruments", 0.0)
        if self.wave_table is None:
            self.wave_table = ComponentScore("Wave Table", 0.0)
        if self.pulse_table is None:
            self.pulse_table = ComponentScore("Pulse Table", 0.0)
        if self.filter_table is None:
            self.filter_table = ComponentScore("Filter Table", 0.0)
        if self.orderlist is None:
            self.orderlist = ComponentScore("Orderlist", 0.0)
        if self.commands is None:
            self.commands = ComponentScore("Commands", 0.0)
        if self.tempo is None:
            self.tempo = ComponentScore("Tempo", 0.0)
        if self.arp_table is None:
            self.arp_table = ComponentScore("Arpeggio", 0.0)
        if self.notes is None:
            self.notes = ComponentScore("Notes", 0.0)

    def calculate_overall(self) -> float:
        """Calculate weighted overall score."""
        # Weights for each component (total = 100)
        weights = {
            'instruments': 20,
            'wave_table': 15,
            'pulse_table': 10,
            'filter_table': 10,
            'orderlist': 15,
            'commands': 10,
            'tempo': 5,
            'arp_table': 5,
            'notes': 10,
        }

        total_weight = 0
        weighted_sum = 0

        for name, weight in weights.items():
            component = getattr(self, name)
            if component and component.score > 0:
                weighted_sum += component.score * weight
                total_weight += weight

        if total_weight > 0:
            self.overall = weighted_sum / total_weight
        else:
            self.overall = 0.0

        return self.overall

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'overall': round(self.overall, 1),
            'instruments': {
                'score': round(self.instruments.score, 1),
                'factors': self.instruments.factors,
                'notes': self.instruments.notes,
            },
            'wave_table': {
                'score': round(self.wave_table.score, 1),
                'factors': self.wave_table.factors,
                'notes': self.wave_table.notes,
            },
            'pulse_table': {
                'score': round(self.pulse_table.score, 1),
                'factors': self.pulse_table.factors,
                'notes': self.pulse_table.notes,
            },
            'filter_table': {
                'score': round(self.filter_table.score, 1),
                'factors': self.filter_table.factors,
                'notes': self.filter_table.notes,
            },
            'orderlist': {
                'score': round(self.orderlist.score, 1),
                'factors': self.orderlist.factors,
                'notes': self.orderlist.notes,
            },
            'commands': {
                'score': round(self.commands.score, 1),
                'factors': self.commands.factors,
                'notes': self.commands.notes,
            },
            'tempo': {
                'score': round(self.tempo.score, 1),
                'factors': self.tempo.factors,
                'notes': self.tempo.notes,
            },
            'arp_table': {
                'score': round(self.arp_table.score, 1),
                'factors': self.arp_table.factors,
                'notes': self.arp_table.notes,
            },
            'notes': {
                'score': round(self.notes.score, 1),
                'factors': self.notes.factors,
                'notes': self.notes.notes,
            },
        }

    def format_report(self) -> str:
        """Generate formatted confidence report."""
        lines = [
            "Extraction Confidence Scores",
            "-" * 50,
            f"Overall Score: {self.overall:.1f}%",
            "",
            "Component Breakdown:",
            f"  {'Component':<20} {'Score':>8} {'Status':<12}",
            f"  {'-' * 20} {'-' * 8} {'-' * 12}",
        ]

        components = [
            ('Instruments', self.instruments),
            ('Wave Table', self.wave_table),
            ('Pulse Table', self.pulse_table),
            ('Filter Table', self.filter_table),
            ('Orderlist', self.orderlist),
            ('Commands', self.commands),
            ('Tempo', self.tempo),
            ('Arpeggio', self.arp_table),
            ('Notes', self.notes),
        ]

        for name, comp in components:
            status = _get_status(comp.score)
            lines.append(f"  {name:<20} {comp.score:>7.1f}% {status}")

        # Add notes for components with issues
        issues = []
        for name, comp in components:
            if comp.notes:
                for note in comp.notes:
                    issues.append(f"  - {name}: {note}")

        if issues:
            lines.extend(["", "Notes:"] + issues)

        return "\n".join(lines)


def _get_status(score: float) -> str:
    """Get status label for a score."""
    if score >= 90:
        return "Excellent"
    elif score >= 75:
        return "Good"
    elif score >= 50:
        return "Fair"
    elif score >= 25:
        return "Low"
    else:
        return "Poor"


class ConfidenceCalculator:
    """Calculate confidence scores for extracted data."""

    def __init__(self, extracted_data, memory: bytes, load_address: int):
        """
        Args:
            extracted_data: ExtractedData object with extraction results
            memory: Full 64KB memory image
            load_address: Base load address of SID data
        """
        self.data = extracted_data
        self.memory = memory
        self.load_address = load_address
        self.confidence = ExtractionConfidence()

    def calculate_all(self) -> ExtractionConfidence:
        """Calculate confidence scores for all components."""
        self._score_instruments()
        self._score_wave_table()
        self._score_pulse_table()
        self._score_filter_table()
        self._score_orderlist()
        self._score_commands()
        self._score_tempo()
        self._score_arp_table()
        self._score_notes()

        self.confidence.calculate_overall()
        return self.confidence

    def _score_instruments(self):
        """Score instrument extraction quality."""
        score = 0.0
        factors = {}
        notes = []

        instruments = self.data.instruments
        if not instruments:
            notes.append("No instruments extracted")
            self.confidence.instruments = ComponentScore("Instruments", 0.0, factors, notes)
            return

        # Factor 1: Number of instruments (0-32 typical, max 50 points)
        num_instr = len(instruments)
        if num_instr > 0:
            count_score = min(50, num_instr * 5)
            if 8 <= num_instr <= 20:
                count_score = 50  # Optimal range
            factors['count'] = count_score
            score += count_score

        # Factor 2: Valid ADSR values (max 20 points)
        valid_adsr = 0
        for instr in instruments:
            if len(instr) >= 2:
                ad, sr = instr[0], instr[1]
                # Check for reasonable ADSR (not all 0 or all FF)
                if 0 < (ad | sr) < 0xFF:
                    valid_adsr += 1

        adsr_ratio = valid_adsr / num_instr if num_instr > 0 else 0
        adsr_score = adsr_ratio * 20
        factors['valid_adsr'] = adsr_score
        score += adsr_score

        # Factor 3: Valid table pointers (max 20 points)
        valid_ptrs = 0
        for instr in instruments:
            if len(instr) >= 7:
                wave_ptr = instr[6]
                # Check wave pointer is reasonable
                if 0 < wave_ptr < 128:
                    valid_ptrs += 1

        ptr_ratio = valid_ptrs / num_instr if num_instr > 0 else 0
        ptr_score = ptr_ratio * 20
        factors['valid_pointers'] = ptr_score
        score += ptr_score

        # Factor 4: Diversity (max 10 points)
        unique_ad = len(set(instr[0] for instr in instruments if len(instr) >= 1))
        diversity_score = min(10, unique_ad * 2)
        factors['diversity'] = diversity_score
        score += diversity_score

        if num_instr < 4:
            notes.append("Few instruments extracted")
        if adsr_ratio < 0.5:
            notes.append("Many instruments have invalid ADSR")

        self.confidence.instruments = ComponentScore("Instruments", min(100, score), factors, notes)

    def _score_wave_table(self):
        """Score wave table extraction quality."""
        score = 0.0
        factors = {}
        notes = []

        wavetable = self.data.wavetable
        if not wavetable or len(wavetable) == 0:
            notes.append("No wave table extracted")
            self.confidence.wave_table = ComponentScore("Wave Table", 0.0, factors, notes)
            return

        # Factor 1: Entry count (max 30 points)
        num_entries = len(wavetable) // 2
        if num_entries > 0:
            count_score = min(30, num_entries * 2)
            factors['count'] = count_score
            score += count_score

        # Factor 2: Valid waveforms (max 30 points)
        # Wave table format: (note_offset, waveform) pairs
        # Note offset is byte 0, waveform is byte 1
        valid_waveforms = 0
        valid_wave_values = {0x00, 0x01, 0x10, 0x11, 0x20, 0x21, 0x40, 0x41, 0x80, 0x81}

        for i in range(0, len(wavetable), 2):
            if i + 1 < len(wavetable):
                note_byte = wavetable[i]
                wave_byte = wavetable[i + 1]
                # Check for known waveform patterns in byte 1
                base_wave = wave_byte & 0xF1  # Ignore gate bit
                # Also check for control bytes in note position (0x7F jump, 0x7E hold)
                if base_wave in valid_wave_values or note_byte == 0x7F or note_byte == 0x7E:
                    valid_waveforms += 1

        wave_ratio = valid_waveforms / num_entries if num_entries > 0 else 0
        wave_score = wave_ratio * 30
        factors['valid_waveforms'] = wave_score
        score += wave_score

        # Factor 3: Jump/loop markers present (max 20 points)
        # Control bytes (0x7F jump, 0x7E hold) are in note_offset position (byte 0)
        has_jumps = any(wavetable[i] in (0x7E, 0x7F) for i in range(0, len(wavetable), 2))
        if has_jumps:
            factors['has_jumps'] = 20
            score += 20
        else:
            factors['has_jumps'] = 10
            score += 10
            notes.append("No jump/loop markers found")

        # Factor 4: Pattern validity (max 20 points)
        # Check for reasonable patterns (not all same values)
        # Check waveform variety (byte 1 of each pair)
        unique_waves = len(set(wavetable[i + 1] for i in range(0, len(wavetable) - 1, 2)))
        pattern_score = min(20, unique_waves * 4)
        factors['pattern_variety'] = pattern_score
        score += pattern_score

        if num_entries < 4:
            notes.append("Very small wave table")

        self.confidence.wave_table = ComponentScore("Wave Table", min(100, score), factors, notes)

    def _score_pulse_table(self):
        """Score pulse table extraction quality."""
        score = 0.0
        factors = {}
        notes = []

        pulsetable = self.data.pulsetable
        if not pulsetable or len(pulsetable) == 0:
            notes.append("No pulse table extracted")
            self.confidence.pulse_table = ComponentScore("Pulse Table", 30.0, factors, notes)
            return

        # Factor 1: Entry count (max 30 points)
        # Pulse entries are 4 bytes each
        num_entries = len(pulsetable) // 4
        if num_entries > 0:
            count_score = min(30, num_entries * 5)
            factors['count'] = count_score
            score += count_score

        # Factor 2: Valid pulse values (max 30 points)
        valid_pulses = 0
        for i in range(0, len(pulsetable), 4):
            if i + 3 < len(pulsetable):
                pulse_val = pulsetable[i]
                # Pulse values typically 0-127 or special values
                if pulse_val < 0x80 or pulse_val == 0xFF:
                    valid_pulses += 1

        pulse_ratio = valid_pulses / num_entries if num_entries > 0 else 0
        pulse_score = pulse_ratio * 30
        factors['valid_values'] = pulse_score
        score += pulse_score

        # Factor 3: Chain patterns (max 20 points)
        chain_count = 0
        for i in range(0, len(pulsetable), 4):
            if i + 3 < len(pulsetable):
                next_idx = pulsetable[i + 3]
                # Check for chain to another entry
                if next_idx < num_entries * 4 and next_idx != i // 4:
                    chain_count += 1

        chain_ratio = chain_count / num_entries if num_entries > 0 else 0
        chain_score = chain_ratio * 20
        factors['chains'] = chain_score
        score += chain_score

        # Factor 4: Not overlapping with other tables (max 20 points)
        # Assume valid if we got here
        factors['no_overlap'] = 20
        score += 20

        if num_entries < 2:
            notes.append("Very small pulse table")

        self.confidence.pulse_table = ComponentScore("Pulse Table", min(100, score), factors, notes)

    def _score_filter_table(self):
        """Score filter table extraction quality."""
        score = 0.0
        factors = {}
        notes = []

        filtertable = self.data.filtertable
        if not filtertable or len(filtertable) == 0:
            notes.append("No filter table extracted")
            self.confidence.filter_table = ComponentScore("Filter Table", 30.0, factors, notes)
            return

        # Factor 1: Entry count (max 30 points)
        num_entries = len(filtertable) // 4
        if num_entries > 0:
            count_score = min(30, num_entries * 5)
            factors['count'] = count_score
            score += count_score

        # Factor 2: Valid filter values (max 30 points)
        valid_filters = 0
        for i in range(0, len(filtertable), 4):
            if i + 3 < len(filtertable):
                filter_val = filtertable[i]
                # Filter cutoff 0-255 is valid
                if filter_val <= 0xFF:
                    valid_filters += 1

        filter_ratio = valid_filters / num_entries if num_entries > 0 else 0
        filter_score = filter_ratio * 30
        factors['valid_values'] = filter_score
        score += filter_score

        # Factor 3: Resonance patterns (max 20 points)
        # Check byte 1 for reasonable resonance/routing
        valid_res = 0
        for i in range(0, len(filtertable), 4):
            if i + 1 < len(filtertable):
                res_byte = filtertable[i + 1]
                # Resonance in upper nibble, routing in lower
                if (res_byte & 0x0F) <= 0x07:  # Valid routing
                    valid_res += 1

        res_ratio = valid_res / num_entries if num_entries > 0 else 0
        res_score = res_ratio * 20
        factors['valid_resonance'] = res_score
        score += res_score

        # Factor 4: Not all zeros (max 20 points)
        non_zero = sum(1 for b in filtertable if b != 0)
        if non_zero > len(filtertable) * 0.3:
            factors['non_zero'] = 20
            score += 20
        else:
            factors['non_zero'] = 5
            score += 5
            notes.append("Filter table mostly zeros")

        if num_entries < 2:
            notes.append("Very small filter table")

        self.confidence.filter_table = ComponentScore("Filter Table", min(100, score), factors, notes)

    def _score_orderlist(self):
        """Score orderlist extraction quality."""
        score = 0.0
        factors = {}
        notes = []

        orderlists = self.data.orderlists
        if not orderlists:
            notes.append("No orderlists extracted")
            self.confidence.orderlist = ComponentScore("Orderlist", 0.0, factors, notes)
            return

        # Factor 1: Track count (max 30 points)
        num_tracks = len(orderlists)
        if num_tracks == 3:
            factors['track_count'] = 30
            score += 30
        elif num_tracks > 0:
            factors['track_count'] = num_tracks * 10
            score += num_tracks * 10

        # Factor 2: Entry count per track (max 30 points)
        total_entries = sum(len(ol) for ol in orderlists)
        entry_score = min(30, total_entries * 2)
        factors['total_entries'] = entry_score
        score += entry_score

        # Factor 3: Valid sequence indices (max 20 points)
        sequences = self.data.sequences
        max_seq_idx = len(sequences) if sequences else 0

        valid_indices = 0
        total_indices = 0
        for orderlist in orderlists:
            for trans, seq_idx in orderlist:
                total_indices += 1
                if 0 <= seq_idx < max_seq_idx:
                    valid_indices += 1

        idx_ratio = valid_indices / total_indices if total_indices > 0 else 0
        idx_score = idx_ratio * 20
        factors['valid_indices'] = idx_score
        score += idx_score

        # Factor 4: Reasonable transpositions (max 20 points)
        valid_trans = 0
        for orderlist in orderlists:
            for trans, seq_idx in orderlist:
                # Transposition typically -24 to +24 semitones (in two's complement)
                if trans <= 24 or trans >= 232:  # 232 = -24 in unsigned
                    valid_trans += 1

        trans_ratio = valid_trans / total_indices if total_indices > 0 else 0
        trans_score = trans_ratio * 20
        factors['valid_transposition'] = trans_score
        score += trans_score

        if num_tracks < 3:
            notes.append(f"Only {num_tracks} tracks (expected 3)")
        if total_entries < 3:
            notes.append("Very short orderlists")

        self.confidence.orderlist = ComponentScore("Orderlist", min(100, score), factors, notes)

    def _score_commands(self):
        """Score command extraction quality."""
        score = 0.0
        factors = {}
        notes = []

        commands = self.data.commands
        if not commands:
            # Commands are optional, give partial score
            factors['default'] = 50
            score = 50
            notes.append("Using default command table")
            self.confidence.commands = ComponentScore("Commands", score, factors, notes)
            return

        # Factor 1: Number of commands defined (max 40 points)
        num_commands = len(commands)
        if 8 <= num_commands <= 16:
            factors['count'] = 40
            score += 40
        else:
            factors['count'] = min(40, num_commands * 3)
            score += min(40, num_commands * 3)

        # Factor 2: Commands with parameters (max 30 points)
        # Count sequences using commands
        cmd_usage = {}
        for seq in self.data.sequences:
            for event in seq:
                if event.command > 0:
                    cmd_usage[event.command] = cmd_usage.get(event.command, 0) + 1

        if cmd_usage:
            factors['usage'] = 30
            score += 30
        else:
            factors['usage'] = 10
            score += 10
            notes.append("No commands used in sequences")

        # Factor 3: Known command types (max 30 points)
        # Assume commands are valid if extracted
        factors['valid'] = 30
        score += 30

        self.confidence.commands = ComponentScore("Commands", min(100, score), factors, notes)

    def _score_tempo(self):
        """Score tempo extraction quality."""
        score = 0.0
        factors = {}
        notes = []

        tempo = self.data.tempo

        # Factor 1: Reasonable tempo value (max 50 points)
        if 1 <= tempo <= 31:
            factors['in_range'] = 50
            score += 50
        elif tempo > 0:
            factors['in_range'] = 30
            score += 30
            notes.append(f"Unusual tempo value: {tempo}")
        else:
            factors['in_range'] = 0
            notes.append("Invalid tempo (0)")

        # Factor 2: Not default value (max 30 points)
        if tempo != 6:  # 6 is default
            factors['not_default'] = 30
            score += 30
        else:
            factors['not_default'] = 15
            score += 15
            notes.append("Using default tempo (may be correct)")

        # Factor 3: Consistency check (max 20 points)
        # Check if tempo seems reasonable for the music
        factors['consistency'] = 20
        score += 20

        self.confidence.tempo = ComponentScore("Tempo", min(100, score), factors, notes)

    def _score_arp_table(self):
        """Score arpeggio table extraction quality."""
        score = 0.0
        factors = {}
        notes = []

        arp_table = self.data.arp_table
        if not arp_table:
            # Arpeggio is optional
            factors['optional'] = 40
            score = 40
            notes.append("No arpeggio table (may not be used)")
            self.confidence.arp_table = ComponentScore("Arpeggio", score, factors, notes)
            return

        # Factor 1: Entry count (max 40 points)
        num_entries = len(arp_table)
        count_score = min(40, num_entries * 8)
        factors['count'] = count_score
        score += count_score

        # Factor 2: Valid note offsets (max 30 points)
        valid_offsets = 0
        for entry in arp_table:
            if isinstance(entry, (tuple, list)) and len(entry) >= 3:
                # Check note offsets are reasonable
                for offset in entry[:3]:
                    if -24 <= offset <= 24 or offset == 0x7F:
                        valid_offsets += 1

        total_offsets = num_entries * 3
        offset_ratio = valid_offsets / total_offsets if total_offsets > 0 else 0
        offset_score = offset_ratio * 30
        factors['valid_offsets'] = offset_score
        score += offset_score

        # Factor 3: Variety (max 30 points)
        if num_entries > 1:
            factors['variety'] = 30
            score += 30
        else:
            factors['variety'] = 15
            score += 15

        self.confidence.arp_table = ComponentScore("Arpeggio", min(100, score), factors, notes)

    def _score_notes(self):
        """Score note extraction quality from sequences."""
        score = 0.0
        factors = {}
        notes_list = []

        sequences = self.data.sequences
        if not sequences:
            notes_list.append("No sequences extracted")
            self.confidence.notes = ComponentScore("Notes", 0.0, factors, notes_list)
            return

        # Factor 1: Total notes extracted (max 30 points)
        total_notes = 0
        for seq in sequences:
            total_notes += len([e for e in seq if e.note > 0])

        note_score = min(30, total_notes // 10)
        factors['count'] = note_score
        score += note_score

        # Factor 2: Note range (max 30 points)
        all_notes = [e.note for seq in sequences for e in seq if e.note > 0]
        if all_notes:
            min_note = min(all_notes)
            max_note = max(all_notes)

            # Check for reasonable range (C-0 to B-7, values 1-96)
            if 1 <= min_note <= 96 and 1 <= max_note <= 96:
                factors['valid_range'] = 30
                score += 30
            else:
                factors['valid_range'] = 15
                score += 15
                notes_list.append(f"Note range outside typical: {min_note}-{max_note}")

        # Factor 3: Instruments assigned (max 20 points)
        notes_with_instr = sum(
            1 for seq in sequences
            for e in seq
            if e.note > 0 and e.instrument > 0
        )
        instr_ratio = notes_with_instr / total_notes if total_notes > 0 else 0
        instr_score = instr_ratio * 20
        factors['instruments_assigned'] = instr_score
        score += instr_score

        # Factor 4: Sequence variety (max 20 points)
        non_empty_seqs = len([s for s in sequences if len(s) > 0])
        variety_score = min(20, non_empty_seqs)
        factors['variety'] = variety_score
        score += variety_score

        if total_notes < 10:
            notes_list.append("Very few notes extracted")

        self.confidence.notes = ComponentScore("Notes", min(100, score), factors, notes_list)


def calculate_extraction_confidence(extracted_data, memory: bytes, load_address: int) -> ExtractionConfidence:
    """
    Calculate confidence scores for extraction quality.

    Args:
        extracted_data: ExtractedData object with extraction results
        memory: Full 64KB memory image
        load_address: Base load address

    Returns:
        ExtractionConfidence with all scores calculated
    """
    calculator = ConfidenceCalculator(extracted_data, memory, load_address)
    return calculator.calculate_all()
