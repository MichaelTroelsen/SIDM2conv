"""
AI-Based Music Table Detector for SID Players
Analyzes disassembled SID code to identify Wave, Pulse, Filter, and Instrument tables.
Works with any player type (Galway, Laxity, etc.)

Uses SID chip register knowledge from docs/reference/sid-registers.md
"""

import re
from typing import List, Dict, Tuple, Optional
from pathlib import Path


# SID Register Knowledge (from docs/reference/sid-registers.md)
# ============================================================

# Valid waveform control values (from SID control register bit layout)
WAVEFORM_VALUES = {
    0x01: 'gate_only',
    0x11: 'triangle',       # Triangle + gate
    0x21: 'sawtooth',       # Sawtooth + gate
    0x41: 'pulse',          # Pulse + gate
    0x81: 'noise',          # Noise + gate
    0x15: 'triangle_ring',  # Triangle + ring mod + gate
    0x31: 'tri_saw',        # Triangle + Sawtooth + gate
    0x51: 'tri_pulse',      # Triangle + Pulse + gate
    0x61: 'saw_pulse',      # Sawtooth + Pulse + gate
    0x71: 'tri_saw_pulse',  # All three + gate
    # Without gate
    0x10: 'triangle_no_gate',
    0x20: 'sawtooth_no_gate',
    0x40: 'pulse_no_gate',
    0x80: 'noise_no_gate',
}

# Note frequency table (PAL values from SID documentation)
# 16-bit frequency values for musical notes
NOTE_FREQ_TABLE_PAL = {
    'C-0': 0x0112, 'C-1': 0x0224, 'C-2': 0x0448, 'C-3': 0x0890,
    'C-4': 0x1120, 'C-5': 0x2240, 'C-6': 0x4480, 'C-7': 0x8900,
}

# ADSR valid ranges (from SID documentation)
ADSR_ATTACK_RANGE = (0, 15)   # 0-15 for attack nibble
ADSR_DECAY_RANGE = (0, 15)    # 0-15 for decay nibble
ADSR_SUSTAIN_RANGE = (0, 15)  # 0-15 for sustain nibble
ADSR_RELEASE_RANGE = (0, 15)  # 0-15 for release nibble

# SID register ranges
PULSE_WIDTH_RANGE = (0, 4095)   # 12-bit pulse width (0x000-0xFFF)
FILTER_CUTOFF_RANGE = (0, 2047) # 11-bit filter cutoff (0x000-0x7FF)
FREQUENCY_RANGE = (0, 65535)    # 16-bit frequency (0x0000-0xFFFF)

# SID register offsets
SID_FREQ_REGS = [0, 1, 7, 8, 14, 15]      # Frequency low/high for voice 1, 2, 3
SID_PW_REGS = [2, 3, 9, 10, 16, 17]       # Pulse width low/high for voice 1, 2, 3
SID_CTRL_REGS = [4, 11, 18]               # Control registers for voice 1, 2, 3
SID_AD_REGS = [5, 12, 19]                 # Attack/Decay for voice 1, 2, 3
SID_SR_REGS = [6, 13, 20]                 # Sustain/Release for voice 1, 2, 3
SID_FILTER_REGS = [21, 22, 23, 24]        # Filter cutoff, resonance, mode/volume


class TableCandidate:
    """Represents a potential music table found in the code"""
    def __init__(self, address: int, size: int, table_type: str, confidence: float, data: List[int]):
        self.address = address
        self.size = size
        self.table_type = table_type  # 'wave', 'pulse', 'filter', 'instrument', 'note_freq', 'arpeggio'
        self.confidence = confidence  # 0.0 to 1.0
        self.data = data
        self.reasons = []  # Why we think this is this type of table

    def add_reason(self, reason: str):
        self.reasons.append(reason)

    def __repr__(self):
        return f"TableCandidate(${self.address:04X}, {self.table_type}, {self.confidence:.0%}, {self.size} bytes)"


class AITableDetector:
    """AI-based detector for music tables in SID player code"""

    def __init__(self, asm_file: str):
        self.asm_file = Path(asm_file)
        self.asm_lines = []
        self.data_blocks = []  # List of (address, data_bytes, line_num)
        self.sid_writes = []  # List of (address, register, line_num)
        self.candidates = []

    def analyze(self) -> List[TableCandidate]:
        """Main analysis pipeline"""
        print(f"Analyzing {self.asm_file.name} for music tables...")

        # Step 1: Parse the assembly file
        self._parse_asm_file()
        print(f"   Found {len(self.data_blocks)} data blocks")
        print(f"   Found {len(self.sid_writes)} SID register writes")

        # Step 2: Identify table candidates
        self._identify_wave_tables()
        self._identify_pulse_tables()
        self._identify_filter_tables()
        self._identify_instrument_tables()
        self._identify_note_freq_tables()
        self._identify_arpeggio_tables()

        # Step 3: Sort by confidence
        self.candidates.sort(key=lambda c: c.confidence, reverse=True)

        print(f"   Found {len(self.candidates)} table candidates")
        return self.candidates

    def _parse_asm_file(self):
        """Parse the assembly file and extract data blocks and SID writes"""
        with open(self.asm_file, 'r', encoding='utf-8') as f:
            self.asm_lines = f.readlines()

        current_address = None

        for i, line in enumerate(self.asm_lines):
            # Extract data blocks (.byte directives)
            if '.byte' in line:
                # Extract address from comment (e.g., "//; $A000 - A002")
                addr_match = re.search(r'//;\s*\$([0-9A-F]{4})', line)
                if addr_match:
                    start_addr = int(addr_match.group(1), 16)

                    # Extract hex bytes
                    byte_match = re.findall(r'\$([0-9A-F]{2})', line)
                    if byte_match:
                        data_bytes = [int(b, 16) for b in byte_match]
                        self.data_blocks.append((start_addr, data_bytes, i))

            # Extract SID register writes
            if 'sta SID0' in line:
                # Extract SID register offset
                reg_match = re.search(r'sta SID0\+?(\d+)?', line)
                if reg_match:
                    reg_offset = int(reg_match.group(1)) if reg_match.group(1) else 0
                    addr_match = re.search(r'//;\s*\$([0-9A-F]{4})', line)
                    if addr_match:
                        code_addr = int(addr_match.group(1), 16)
                        self.sid_writes.append((code_addr, reg_offset, i))

    def _identify_wave_tables(self):
        """Identify waveform tables (patterns of $00-$FF representing waveforms)"""
        for addr, data, line_num in self.data_blocks:
            if len(data) < 8:  # Wave tables are usually longer
                continue

            # Check for waveform-like patterns
            confidence = 0.0
            reasons = []

            # Pattern 1: Repeated sequences (waveforms often repeat)
            if self._has_repetition(data):
                confidence += 0.3
                reasons.append("Has repetitive patterns")

            # Pattern 2: Smooth transitions (waveforms usually don't jump wildly)
            if self._has_smooth_transitions(data):
                confidence += 0.3
                reasons.append("Smooth value transitions")

            # Pattern 3: Full range usage ($00 to $FF for wave amplitude)
            value_range = max(data) - min(data)
            if value_range > 200:  # Wide range suggests waveform
                confidence += 0.2
                reasons.append(f"Wide value range (${min(data):02X} to ${max(data):02X})")

            # Pattern 4: Size is power of 2 (common for wave tables)
            if len(data) in [8, 16, 32, 64, 128, 256]:
                confidence += 0.2
                reasons.append(f"Power-of-2 size ({len(data)} bytes)")

            if confidence >= 0.5:
                candidate = TableCandidate(addr, len(data), 'wave', confidence, data)
                for reason in reasons:
                    candidate.add_reason(reason)
                self.candidates.append(candidate)

    def _identify_pulse_tables(self):
        """Identify pulse width modulation tables (12-bit values for SID pulse)
        Uses SID pulse width register range (0-4095) from sid-registers.md"""
        for addr, data, line_num in self.data_blocks:
            if len(data) < 4:  # Pulse tables need at least 2 entries (2 bytes each)
                continue

            confidence = 0.0
            reasons = []

            # Pattern 1: Values in SID pulse width range (0-4095, from $D402-$D403 spec)
            # Check if consecutive bytes form valid 12-bit values
            if len(data) % 2 == 0:  # Even number of bytes
                pulse_values = []
                for i in range(0, len(data), 2):
                    value = data[i] | (data[i+1] << 8)
                    pulse_values.append(value)

                # All values must be in valid SID pulse width range (0-4095)
                valid_pulse = sum(1 for v in pulse_values if PULSE_WIDTH_RANGE[0] <= v <= PULSE_WIDTH_RANGE[1])
                if valid_pulse == len(pulse_values):
                    confidence += 0.5
                    reasons.append(f"All {len(pulse_values)} values in SID pulse width range (0-4095)")

                    # Check for variation (pulse tables usually vary)
                    if len(set(pulse_values)) > len(pulse_values) // 2:
                        confidence += 0.2
                        reasons.append("Good value diversity")

            # Pattern 2: Size is even (pulse = 2 bytes)
            if len(data) % 2 == 0:
                confidence += 0.1
                reasons.append("Even size (16-bit values)")

            # Pattern 3: Referenced near SID pulse register writes (reg 2-3, 9-10, 16-17)
            if self._is_near_sid_pulse_writes(addr):
                confidence += 0.2
                reasons.append("Near SID pulse width register writes")

            if confidence >= 0.5:
                candidate = TableCandidate(addr, len(data), 'pulse', confidence, data)
                for reason in reasons:
                    candidate.add_reason(reason)
                self.candidates.append(candidate)

    def _identify_filter_tables(self):
        """Identify filter cutoff tables (11-bit values for SID filter)
        Uses SID filter cutoff range (0-2047) from sid-registers.md"""
        for addr, data, line_num in self.data_blocks:
            if len(data) < 2:
                continue

            confidence = 0.0
            reasons = []

            # Pattern 1: Values in SID filter cutoff range (0-2047, from $D415-$D416 spec)
            # Single byte values or 16-bit values that fit in 11-bit range
            if len(data) % 2 == 0:
                # Try as 16-bit values
                filter_values = []
                for i in range(0, len(data), 2):
                    value = data[i] | (data[i+1] << 8)
                    filter_values.append(value)

                valid_filter = sum(1 for v in filter_values if FILTER_CUTOFF_RANGE[0] <= v <= FILTER_CUTOFF_RANGE[1])
                if valid_filter == len(filter_values):
                    confidence += 0.5
                    reasons.append(f"All {len(filter_values)} values in SID filter cutoff range (0-2047)")
            else:
                # Single bytes
                valid_filter = sum(1 for v in data if v <= FILTER_CUTOFF_RANGE[1])
                if valid_filter == len(data):
                    confidence += 0.4
                    reasons.append(f"All values in filter cutoff range (max ${max(data):02X})")

            # Pattern 2: Referenced near SID filter writes (reg 21-22)
            if self._is_near_sid_filter_writes(addr):
                confidence += 0.4
                reasons.append("Near SID filter register writes ($D415-$D416)")

            # Pattern 3: Gradual changes (filter sweeps)
            if self._has_smooth_transitions(data, threshold=50):
                confidence += 0.2
                reasons.append("Smooth transitions (filter sweep)")

            if confidence >= 0.4:
                candidate = TableCandidate(addr, len(data), 'filter', confidence, data)
                for reason in reasons:
                    candidate.add_reason(reason)
                self.candidates.append(candidate)

    def _identify_instrument_tables(self):
        """Identify instrument definition tables (ADSR + waveform)
        Uses SID register knowledge from sid-registers.md"""
        for addr, data, line_num in self.data_blocks:
            if len(data) < 4:
                continue

            confidence = 0.0
            reasons = []

            # Pattern 1: Valid ADSR values (using SID documentation ranges)
            # ADSR format: Attack/Decay nibbles (0-15 each), Sustain/Release nibbles (0-15 each)
            if len(data) >= 2:
                valid_adsr = 0
                for i in range(0, min(len(data)-1, 8), 2):
                    # Check both bytes for valid ADSR nibbles
                    attack = data[i] >> 4
                    decay = data[i] & 0xF
                    if i+1 < len(data):
                        sustain = data[i+1] >> 4
                        release = data[i+1] & 0xF

                        # All nibbles must be in valid ADSR range (0-15)
                        if (ADSR_ATTACK_RANGE[0] <= attack <= ADSR_ATTACK_RANGE[1] and
                            ADSR_DECAY_RANGE[0] <= decay <= ADSR_DECAY_RANGE[1] and
                            ADSR_SUSTAIN_RANGE[0] <= sustain <= ADSR_SUSTAIN_RANGE[1] and
                            ADSR_RELEASE_RANGE[0] <= release <= ADSR_RELEASE_RANGE[1]):
                            valid_adsr += 1

                if valid_adsr >= 2:
                    confidence += 0.5
                    reasons.append(f"{valid_adsr} valid ADSR byte pairs (nibbles 0-15)")

            # Pattern 2: Structured chunks (instruments are often 4, 6, or 8 bytes each)
            if len(data) % 4 == 0 or len(data) % 6 == 0 or len(data) % 8 == 0:
                confidence += 0.2
                reasons.append(f"Structured size ({len(data)} bytes)")

            # Pattern 3: Valid SID waveform control values (from sid-registers.md)
            known_waveforms = [v for v in data if v in WAVEFORM_VALUES]
            if len(known_waveforms) >= len(data) // 8:
                confidence += 0.3
                waveform_names = ', '.join(set(WAVEFORM_VALUES[v] for v in known_waveforms[:3]))
                reasons.append(f"{len(known_waveforms)} valid SID waveform values ({waveform_names}...)")

            # Pattern 4: Near SID ADSR register writes
            if self._is_near_sid_adsr_writes(addr):
                confidence += 0.1
                reasons.append("Near SID ADSR register writes")

            if confidence >= 0.5:
                candidate = TableCandidate(addr, len(data), 'instrument', confidence, data)
                for reason in reasons:
                    candidate.add_reason(reason)
                self.candidates.append(candidate)

    def _identify_note_freq_tables(self):
        """Identify note frequency tables (16-bit SID frequency values)
        Uses SID frequency values from sid-registers.md"""
        for addr, data, line_num in self.data_blocks:
            if len(data) < 24:  # At least 12 notes (2 bytes each)
                continue

            confidence = 0.0
            reasons = []

            # Pattern 1: 16-bit values that increase logarithmically (musical notes)
            if len(data) % 2 == 0:
                freq_values = []
                for i in range(0, len(data), 2):
                    value = data[i] | (data[i+1] << 8)
                    freq_values.append(value)

                # Check if values are in valid SID frequency range (0-65535)
                valid_range = sum(1 for v in freq_values if FREQUENCY_RANGE[0] <= v <= FREQUENCY_RANGE[1])
                if valid_range == len(freq_values):
                    confidence += 0.2
                    reasons.append("All values in valid SID frequency range")

                # Check if values are monotonically increasing
                if freq_values == sorted(freq_values):
                    confidence += 0.3
                    reasons.append("Values increase monotonically")

                    # Check for musical interval ratios (each semitone is ~1.059x)
                    ratios = []
                    for i in range(len(freq_values) - 1):
                        if freq_values[i] > 0:
                            ratio = freq_values[i+1] / freq_values[i]
                            ratios.append(ratio)

                    # Musical semitones should have ratios around 1.059
                    musical_ratios = sum(1 for r in ratios if 1.04 < r < 1.08)
                    if musical_ratios >= len(ratios) * 0.7:
                        confidence += 0.4
                        reasons.append(f"{musical_ratios}/{len(ratios)} ratios match semitone intervals (~1.059x)")

                # Pattern 2: Compare against known note frequencies from SID documentation
                known_freqs = set(NOTE_FREQ_TABLE_PAL.values())
                matches = sum(1 for v in freq_values if v in known_freqs)
                if matches >= 3:
                    confidence += 0.3
                    reasons.append(f"{matches} values match documented SID note frequencies")

            # Pattern 3: Referenced near SID frequency writes (reg 0-1, 7-8, 14-15)
            if self._is_near_sid_freq_writes(addr):
                confidence += 0.2
                reasons.append("Near SID frequency register writes")

            if confidence >= 0.6:
                candidate = TableCandidate(addr, len(data), 'note_freq', confidence, data)
                for reason in reasons:
                    candidate.add_reason(reason)
                self.candidates.append(candidate)

    def _identify_arpeggio_tables(self):
        """Identify arpeggio/transpose tables (small offsets added to notes)"""
        for addr, data, line_num in self.data_blocks:
            if len(data) < 3 or len(data) > 64:  # Arpeggios are usually short
                continue

            confidence = 0.0
            reasons = []

            # Pattern 1: Small values (usually -12 to +12 semitones)
            small_values = sum(1 for v in data if v <= 24 or v >= 240)  # 240-255 = -16 to -1 in signed
            if small_values >= len(data) * 0.7:
                confidence += 0.4
                reasons.append(f"{small_values}/{len(data)} values are small offsets")

            # Pattern 2: Regular pattern (arpeggios often have patterns like 0, 3, 7, 12)
            if self._has_regular_pattern(data):
                confidence += 0.3
                reasons.append("Has regular pattern (musical intervals)")

            # Pattern 3: Musical intervals (0, 3, 4, 5, 7, 12 = common intervals)
            musical_intervals = [0, 3, 4, 5, 7, 12]
            interval_matches = sum(1 for v in data if v in musical_intervals)
            if interval_matches >= len(data) * 0.5:
                confidence += 0.3
                reasons.append(f"{interval_matches} musical interval values")

            if confidence >= 0.5:
                candidate = TableCandidate(addr, len(data), 'arpeggio', confidence, data)
                for reason in reasons:
                    candidate.add_reason(reason)
                self.candidates.append(candidate)

    # Helper methods

    def _has_repetition(self, data: List[int], min_repeat=2) -> bool:
        """Check if data has repeated patterns"""
        for pattern_len in [2, 4, 8, 16]:
            if len(data) < pattern_len * min_repeat:
                continue
            for i in range(len(data) - pattern_len * min_repeat + 1):
                pattern = data[i:i+pattern_len]
                next_pattern = data[i+pattern_len:i+pattern_len*2]
                if pattern == next_pattern:
                    return True
        return False

    def _has_smooth_transitions(self, data: List[int], threshold=40) -> bool:
        """Check if consecutive values don't jump too much"""
        if len(data) < 2:
            return False
        jumps = [abs(data[i+1] - data[i]) for i in range(len(data)-1)]
        smooth_count = sum(1 for j in jumps if j <= threshold)
        return smooth_count >= len(jumps) * 0.7

    def _has_regular_pattern(self, data: List[int]) -> bool:
        """Check if data has a regular arithmetic pattern"""
        if len(data) < 3:
            return False
        diffs = [data[i+1] - data[i] for i in range(len(data)-1)]
        # Check if differences are mostly the same
        if len(set(diffs)) <= len(diffs) // 2:
            return True
        return False

    def _is_near_sid_freq_writes(self, addr: int, distance=100) -> bool:
        """Check if address is near SID frequency register writes
        Uses SID_FREQ_REGS from sid-registers.md"""
        for code_addr, reg_offset, _ in self.sid_writes:
            if reg_offset in SID_FREQ_REGS and abs(code_addr - addr) < distance:
                return True
        return False

    def _is_near_sid_pulse_writes(self, addr: int, distance=100) -> bool:
        """Check if address is near SID pulse register writes
        Uses SID_PW_REGS from sid-registers.md"""
        for code_addr, reg_offset, _ in self.sid_writes:
            if reg_offset in SID_PW_REGS and abs(code_addr - addr) < distance:
                return True
        return False

    def _is_near_sid_filter_writes(self, addr: int, distance=100) -> bool:
        """Check if address is near SID filter register writes
        Uses SID_FILTER_REGS from sid-registers.md"""
        for code_addr, reg_offset, _ in self.sid_writes:
            if reg_offset in SID_FILTER_REGS and abs(code_addr - addr) < distance:
                return True
        return False

    def _is_near_sid_adsr_writes(self, addr: int, distance=100) -> bool:
        """Check if address is near SID ADSR register writes (5-6, 12-13, 19-20)
        Uses SID_AD_REGS and SID_SR_REGS from sid-registers.md"""
        adsr_regs = SID_AD_REGS + SID_SR_REGS  # [5, 12, 19, 6, 13, 20]
        for code_addr, reg_offset, _ in self.sid_writes:
            if reg_offset in adsr_regs and abs(code_addr - addr) < distance:
                return True
        return False

    def print_results(self):
        """Print detected tables in a nice format"""
        print("\n" + "="*80)
        print("AI TABLE DETECTION RESULTS")
        print("="*80)

        by_type = {}
        for candidate in self.candidates:
            if candidate.table_type not in by_type:
                by_type[candidate.table_type] = []
            by_type[candidate.table_type].append(candidate)

        for table_type in ['note_freq', 'wave', 'pulse', 'filter', 'instrument', 'arpeggio']:
            if table_type not in by_type:
                continue

            print(f"\n{table_type.upper()} TABLES:")
            print("-" * 80)

            for candidate in by_type[table_type]:
                print(f"  ${candidate.address:04X} - {candidate.size:3d} bytes - Confidence: {candidate.confidence:5.0%}")
                for reason in candidate.reasons:
                    print(f"    * {reason}")
                if candidate.size <= 32:
                    hex_str = ' '.join(f'${b:02X}' for b in candidate.data[:16])
                    if len(candidate.data) > 16:
                        hex_str += '...'
                    print(f"    Data: {hex_str}")
                print()


def main():
    """Test the detector on Ocean Loader 1"""
    import sys

    if len(sys.argv) > 1:
        asm_file = sys.argv[1]
    else:
        asm_file = "analysis/Ocean_Loader_1_temp.asm"

    detector = AITableDetector(asm_file)
    candidates = detector.analyze()
    detector.print_results()

    return candidates


if __name__ == "__main__":
    main()
