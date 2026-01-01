"""
Automatic ASM File Annotator

Adds comprehensive annotations to 6502 assembly files with:
- Memory map
- SID register documentation
- Laxity format reference
- Inline comments for known patterns
- Label identification
- Subroutine detection and documentation
"""

import sys
import re
import json
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass, field, asdict

# Import HTML export module
try:
    from html_export import generate_html_export
    HTML_EXPORT_AVAILABLE = True
except ImportError:
    HTML_EXPORT_AVAILABLE = False

# Documentation mapping: Address ranges and topics to documentation files
DOCUMENTATION_MAP = {
    # Memory address ranges to documentation
    'addresses': {
        # SID chip registers
        (0xD400, 0xD418): {
            'title': 'SID Chip Registers',
            'docs': [
                'docs/reference/SID_REGISTERS.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'Complete SID sound chip register reference'
        },
        # Laxity NewPlayer v21 tables
        (0x18DA, 0x18F9): {
            'title': 'Laxity Wave Table - Waveforms',
            'docs': [
                'docs/reference/LAXITY_WAVE_TABLE.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'Laxity NewPlayer v21 waveform table (32 bytes)'
        },
        (0x190C, 0x192B): {
            'title': 'Laxity Wave Table - Note Offsets',
            'docs': [
                'docs/reference/LAXITY_WAVE_TABLE.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'Laxity NewPlayer v21 note offset table (32 bytes)'
        },
        (0x1837, 0x1A1D): {
            'title': 'Laxity Pulse Table',
            'docs': [
                'docs/reference/LAXITY_TABLES.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'Laxity NewPlayer v21 pulse width table (4-byte entries)'
        },
        (0x1A1E, 0x1A6A): {
            'title': 'Laxity Filter Table',
            'docs': [
                'docs/reference/LAXITY_TABLES.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'Laxity NewPlayer v21 filter table (4-byte entries)'
        },
        (0x1A6B, 0x1AAA): {
            'title': 'Laxity Instrument Table',
            'docs': [
                'docs/reference/LAXITY_INSTRUMENTS.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'Laxity NewPlayer v21 instrument table (8×8 bytes, column-major)'
        },
        (0x199F, 0x19A4): {
            'title': 'Laxity Sequence Pointers',
            'docs': [
                'docs/reference/LAXITY_SEQUENCES.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'Laxity NewPlayer v21 sequence pointers (3 voices × 2 bytes)'
        },
        # SF2 Driver tables
        (0x0903, 0x0A02): {
            'title': 'SF2 Sequence Data',
            'docs': [
                'docs/reference/SF2_FORMAT_SPEC.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'SF2 Driver 11 sequence data area'
        },
        (0x0A03, 0x0B02): {
            'title': 'SF2 Instrument Table',
            'docs': [
                'docs/reference/SF2_FORMAT_SPEC.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'SF2 Driver 11 instrument table'
        },
        (0x0B03, 0x0D02): {
            'title': 'SF2 Wave Table',
            'docs': [
                'docs/reference/SF2_FORMAT_SPEC.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'SF2 Driver 11 wave table'
        },
        (0x0D03, 0x0F02): {
            'title': 'SF2 Pulse Table',
            'docs': [
                'docs/reference/SF2_FORMAT_SPEC.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'SF2 Driver 11 pulse table'
        },
        (0x0F03, 0x1102): {
            'title': 'SF2 Filter Table',
            'docs': [
                'docs/reference/SF2_FORMAT_SPEC.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'SF2 Driver 11 filter table'
        },
    },
    # Topics to documentation
    'topics': {
        'laxity': {
            'title': 'Laxity NewPlayer v21',
            'docs': [
                'docs/LAXITY_DRIVER_USER_GUIDE.md',
                'docs/implementation/LAXITY_DRIVER_IMPLEMENTATION.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'Laxity music player format and driver'
        },
        'sf2': {
            'title': 'SID Factory II Format',
            'docs': [
                'docs/reference/SF2_FORMAT_SPEC.md',
                'docs/guides/SF2_VIEWER_GUIDE.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'SF2 file format and drivers'
        },
        'conversion': {
            'title': 'SID to SF2 Conversion',
            'docs': [
                'docs/guides/TUTORIALS.md',
                'docs/guides/BEST_PRACTICES.md',
                'README.md'
            ],
            'description': 'How SID files are converted to SF2 format'
        },
        'validation': {
            'title': 'Accuracy Validation',
            'docs': [
                'docs/guides/VALIDATION_GUIDE.md',
                'docs/ARCHITECTURE.md'
            ],
            'description': 'How conversion accuracy is measured and validated'
        },
        'driver_selection': {
            'title': 'Driver Selection',
            'docs': [
                'docs/ARCHITECTURE.md',
                'docs/guides/BEST_PRACTICES.md'
            ],
            'description': 'How the correct driver is automatically selected'
        },
    }
}

# Common 6502 opcodes with descriptions
OPCODES = {
    'LDA': 'Load Accumulator',
    'LDX': 'Load X Register',
    'LDY': 'Load Y Register',
    'STA': 'Store Accumulator',
    'STX': 'Store X Register',
    'STY': 'Store Y Register',
    'TAX': 'Transfer A to X',
    'TAY': 'Transfer A to Y',
    'TXA': 'Transfer X to A',
    'TYA': 'Transfer Y to A',
    'INX': 'Increment X',
    'INY': 'Increment Y',
    'DEX': 'Decrement X',
    'DEY': 'Decrement Y',
    'INC': 'Increment Memory',
    'DEC': 'Decrement Memory',
    'CMP': 'Compare with A',
    'CPX': 'Compare with X',
    'CPY': 'Compare with Y',
    'BEQ': 'Branch if Equal',
    'BNE': 'Branch if Not Equal',
    'BPL': 'Branch if Plus',
    'BMI': 'Branch if Minus',
    'BCC': 'Branch if Carry Clear',
    'BCS': 'Branch if Carry Set',
    'BVC': 'Branch if Overflow Clear',
    'BVS': 'Branch if Overflow Set',
    'JMP': 'Jump',
    'JSR': 'Jump to Subroutine',
    'RTS': 'Return from Subroutine',
    'AND': 'Logical AND',
    'ORA': 'Logical OR',
    'EOR': 'Logical XOR',
    'SEC': 'Set Carry',
    'CLC': 'Clear Carry',
    'SEI': 'Set Interrupt Disable',
    'CLI': 'Clear Interrupt Disable',
}

# Known memory regions
MEMORY_REGIONS = {
    (0xD400, 0xD418): 'SID Chip Registers',
    (0x0000, 0x00FF): 'Zero Page',
    (0x0100, 0x01FF): 'Stack',
    (0x1000, 0x1FFF): 'Laxity Player Code/Data',
    (0xA000, 0xBFFF): 'BASIC ROM / RAM',
    (0xE000, 0xFFFF): 'Kernal ROM',
}

# SID registers
SID_REGISTERS = {
    0xD400: 'Voice 1 Frequency Low',
    0xD401: 'Voice 1 Frequency High',
    0xD402: 'Voice 1 Pulse Width Low',
    0xD403: 'Voice 1 Pulse Width High',
    0xD404: 'Voice 1 Control Register',
    0xD405: 'Voice 1 Attack/Decay',
    0xD406: 'Voice 1 Sustain/Release',
    0xD407: 'Voice 2 Frequency Low',
    0xD408: 'Voice 2 Frequency High',
    0xD409: 'Voice 2 Pulse Width Low',
    0xD40A: 'Voice 2 Pulse Width High',
    0xD40B: 'Voice 2 Control Register',
    0xD40C: 'Voice 2 Attack/Decay',
    0xD40D: 'Voice 2 Sustain/Release',
    0xD40E: 'Voice 3 Frequency Low',
    0xD40F: 'Voice 3 Frequency High',
    0xD410: 'Voice 3 Pulse Width Low',
    0xD411: 'Voice 3 Pulse Width High',
    0xD412: 'Voice 3 Control Register',
    0xD413: 'Voice 3 Attack/Decay',
    0xD414: 'Voice 3 Sustain/Release',
    0xD415: 'Filter Cutoff Low',
    0xD416: 'Filter Cutoff High',
    0xD417: 'Filter Resonance/Routing',
    0xD418: 'Volume/Filter Mode',
}

# Known Laxity table addresses for Stinsens
LAXITY_TABLES = {
    0x18DA: 'Wave Table - Waveforms (32 bytes)',
    0x190C: 'Wave Table - Note Offsets (32 bytes)',
    0x1837: 'Pulse Table (4-byte entries)',
    0x1A1E: 'Filter Table (4-byte entries)',
    0x1A6B: 'Instrument Table (8×8 bytes, column-major)',
    0x199F: 'Sequence Pointers (3 voices × 2 bytes)',
}


# ==============================================================================
# Section Detection (Data vs Code)
# ==============================================================================

from enum import Enum

class SectionType(Enum):
    """Type of section in assembly code"""
    CODE = "code"
    DATA = "data"
    WAVE_TABLE = "wave_table"
    PULSE_TABLE = "pulse_table"
    FILTER_TABLE = "filter_table"
    INSTRUMENT_TABLE = "instrument_table"
    SEQUENCE_DATA = "sequence_data"
    UNKNOWN = "unknown"


@dataclass
class Section:
    """Represents a section of assembly code"""
    start_address: Optional[int]
    end_address: Optional[int]
    start_line: int
    end_line: int
    section_type: SectionType
    name: str = ""
    size: int = 0

    def __post_init__(self):
        if self.start_address and self.end_address:
            self.size = self.end_address - self.start_address + 1


class SectionDetector:
    """Detect code vs data sections in assembly"""

    def __init__(self, lines: List[str], subroutines: Dict[int, 'SubroutineInfo']):
        self.lines = lines
        self.subroutines = subroutines
        self.sections: List[Section] = []

    def detect_sections(self) -> List[Section]:
        """Detect and classify all sections"""
        current_section = None

        for i, line in enumerate(self.lines):
            # Skip comments and empty lines
            if line.strip().startswith(';') or not line.strip():
                continue

            address = self._extract_address(line)

            # Check if this line starts a known data table
            if address:
                table_type = self._identify_table_type(address)
                if table_type != SectionType.UNKNOWN:
                    # Start new data section
                    if current_section:
                        current_section.end_line = i - 1
                        self.sections.append(current_section)

                    current_section = Section(
                        start_address=address,
                        end_address=None,
                        start_line=i,
                        end_line=i,
                        section_type=table_type,
                        name=table_type.value.replace('_', ' ').title()
                    )
                    continue

            # Check if this is a subroutine (code section)
            if address and address in self.subroutines:
                # Start new code section
                if current_section and current_section.section_type != SectionType.CODE:
                    current_section.end_line = i - 1
                    self.sections.append(current_section)
                    current_section = None

                if not current_section or current_section.section_type != SectionType.CODE:
                    current_section = Section(
                        start_address=address,
                        end_address=None,
                        start_line=i,
                        end_line=i,
                        section_type=SectionType.CODE,
                        name="Code"
                    )
                continue

            # Extend current section
            if current_section:
                current_section.end_line = i
                if address:
                    current_section.end_address = address

        # Add final section
        if current_section:
            self.sections.append(current_section)

        return self.sections

    def _extract_address(self, line: str) -> Optional[int]:
        """Extract address from line"""
        match = re.match(r'^\s*\$?([0-9A-Fa-f]{4}):', line)
        if match:
            return int(match.group(1), 16)
        return None

    def _identify_table_type(self, address: int) -> SectionType:
        """Identify if address is a known table type"""
        # Check Laxity tables
        if address == 0x18DA or address == 0x190C:
            return SectionType.WAVE_TABLE
        elif address == 0x1837:
            return SectionType.PULSE_TABLE
        elif address == 0x1A1E:
            return SectionType.FILTER_TABLE
        elif address == 0x1A6B:
            return SectionType.INSTRUMENT_TABLE
        elif address >= 0x1900 and address < 0x1A00:
            return SectionType.SEQUENCE_DATA

        return SectionType.UNKNOWN


def format_data_section(section: Section, lines: List[str],
                        xrefs: Optional[Dict[int, List[Reference]]] = None,
                        subroutines: Optional[Dict[int, 'SubroutineInfo']] = None) -> str:
    """Format a data section with appropriate header and formatting"""
    sep = ";" + "=" * 78
    header = f"{sep}\n"
    header += f"; DATA SECTION: {section.name}\n"

    if section.start_address:
        header += f"; Address: ${section.start_address:04X}"
        if section.end_address:
            header += f" - ${section.end_address:04X}\n"
        else:
            header += "\n"

    if section.size:
        header += f"; Size: {section.size} bytes\n"

    # Add format-specific information
    if section.section_type == SectionType.WAVE_TABLE:
        header += "; Format: SID waveform bytes or note offsets (1 byte per instrument)\n"
        header += "; Values: $01=triangle, $10=sawtooth, $20=pulse, $40=noise, $80=gate\n"
    elif section.section_type == SectionType.PULSE_TABLE:
        header += "; Format: 4-byte entries (pulse_lo, pulse_hi, duration, next_index)\n"
    elif section.section_type == SectionType.FILTER_TABLE:
        header += "; Format: 4-byte entries (cutoff, resonance, duration, next_index)\n"
    elif section.section_type == SectionType.INSTRUMENT_TABLE:
        header += "; Format: 8 bytes × 8 instruments (column-major layout)\n"
        header += "; Bytes: AD, SR, Pulse ptr, Filter, unused, unused, Flags, Wave ptr\n"
    elif section.section_type == SectionType.SEQUENCE_DATA:
        header += "; Format: Sequence bytes terminated by $7F\n"
        header += "; $00=rest, $01-$5F=note, $7E=gate continue, $7F=end\n"

    # Add cross-references if available
    if xrefs and subroutines and section.start_address:
        xref_header = format_cross_references(section.start_address, xrefs, subroutines)
        if xref_header:
            header += xref_header

    header += f"{sep}\n"

    return header


# ==============================================================================
# Cross-Reference Generation
# ==============================================================================

class ReferenceType(Enum):
    """Type of reference to an address"""
    CALL = "call"           # JSR instruction
    JUMP = "jump"           # JMP instruction
    BRANCH = "branch"       # BEQ, BNE, etc.
    READ = "read"           # LDA, LDX, LDY, CMP, etc.
    WRITE = "write"         # STA, STX, STY
    READ_MODIFY = "r/w"     # INC, DEC, ASL, LSR, ROL, ROR


@dataclass
class Reference:
    """A reference to an address in the code"""
    source_address: Optional[int]  # Address where reference occurs
    source_line: int               # Line number where reference occurs
    target_address: int            # Address being referenced
    ref_type: ReferenceType        # Type of reference
    instruction: str = ""          # The actual instruction


class CrossReferenceDetector:
    """Generate cross-references for addresses in assembly code"""

    def __init__(self, lines: List[str], subroutines: Dict[int, 'SubroutineInfo']):
        self.lines = lines
        self.subroutines = subroutines
        # Map from target address to list of references
        self.xrefs: Dict[int, List[Reference]] = {}

    def generate_cross_references(self) -> Dict[int, List[Reference]]:
        """Build complete cross-reference table"""
        from collections import defaultdict
        self.xrefs = defaultdict(list)

        for line_num, line in enumerate(self.lines):
            # Skip comments and empty lines
            if line.strip().startswith(';') or not line.strip():
                continue

            # Extract source address
            source_addr = self._extract_address(line)

            # Check for different reference types
            self._check_jsr(line, line_num, source_addr)
            self._check_jmp(line, line_num, source_addr)
            self._check_branch(line, line_num, source_addr)
            self._check_read(line, line_num, source_addr)
            self._check_write(line, line_num, source_addr)
            self._check_read_modify(line, line_num, source_addr)

        return dict(self.xrefs)

    def _extract_address(self, line: str) -> Optional[int]:
        """Extract address from line"""
        match = re.match(r'^\s*\$?([0-9A-Fa-f]{4}):', line)
        if match:
            return int(match.group(1), 16)
        return None

    def _extract_target_address(self, operand: str) -> Optional[int]:
        """Extract target address from operand"""
        # Match $XXXX or XXXX (with optional ,X or ,Y)
        match = re.match(r'\$?([0-9A-Fa-f]{4})', operand)
        if match:
            return int(match.group(1), 16)
        return None

    def _check_jsr(self, line: str, line_num: int, source_addr: Optional[int]):
        """Check for JSR (call) instruction"""
        match = re.search(r'JSR\s+\$?([0-9A-Fa-f]{4})', line, re.IGNORECASE)
        if match:
            target = int(match.group(1), 16)
            self.xrefs[target].append(Reference(
                source_address=source_addr,
                source_line=line_num,
                target_address=target,
                ref_type=ReferenceType.CALL,
                instruction=line.strip()
            ))

    def _check_jmp(self, line: str, line_num: int, source_addr: Optional[int]):
        """Check for JMP instruction"""
        match = re.search(r'JMP\s+\$?([0-9A-Fa-f]{4})', line, re.IGNORECASE)
        if match:
            target = int(match.group(1), 16)
            self.xrefs[target].append(Reference(
                source_address=source_addr,
                source_line=line_num,
                target_address=target,
                ref_type=ReferenceType.JUMP,
                instruction=line.strip()
            ))

    def _check_branch(self, line: str, line_num: int, source_addr: Optional[int]):
        """Check for branch instructions (BEQ, BNE, etc.)"""
        match = re.search(r'(BEQ|BNE|BPL|BMI|BCC|BCS|BVC|BVS)\s+\$?([0-9A-Fa-f]{4})', line, re.IGNORECASE)
        if match:
            target = int(match.group(2), 16)
            self.xrefs[target].append(Reference(
                source_address=source_addr,
                source_line=line_num,
                target_address=target,
                ref_type=ReferenceType.BRANCH,
                instruction=line.strip()
            ))

    def _check_read(self, line: str, line_num: int, source_addr: Optional[int]):
        """Check for read instructions (LDA, LDX, LDY, CMP, etc.)"""
        # Match load and compare instructions with absolute addressing
        match = re.search(r'(LDA|LDX|LDY|CMP|CPX|CPY|BIT|AND|ORA|EOR|ADC|SBC)\s+\$?([0-9A-Fa-f]{4})(,X|,Y)?', line, re.IGNORECASE)
        if match:
            target = int(match.group(2), 16)
            # Only track if it's not a SID register (those are tracked separately)
            if target < 0xD400 or target > 0xD418:
                self.xrefs[target].append(Reference(
                    source_address=source_addr,
                    source_line=line_num,
                    target_address=target,
                    ref_type=ReferenceType.READ,
                    instruction=line.strip()
                ))

    def _check_write(self, line: str, line_num: int, source_addr: Optional[int]):
        """Check for write instructions (STA, STX, STY)"""
        match = re.search(r'(STA|STX|STY)\s+\$?([0-9A-Fa-f]{4})(,X|,Y)?', line, re.IGNORECASE)
        if match:
            target = int(match.group(2), 16)
            # Only track if it's not a SID register
            if target < 0xD400 or target > 0xD418:
                self.xrefs[target].append(Reference(
                    source_address=source_addr,
                    source_line=line_num,
                    target_address=target,
                    ref_type=ReferenceType.WRITE,
                    instruction=line.strip()
                ))

    def _check_read_modify(self, line: str, line_num: int, source_addr: Optional[int]):
        """Check for read-modify-write instructions (INC, DEC, etc.)"""
        match = re.search(r'(INC|DEC|ASL|LSR|ROL|ROR)\s+\$?([0-9A-Fa-f]{4})', line, re.IGNORECASE)
        if match:
            target = int(match.group(2), 16)
            # Only track if it's not a SID register
            if target < 0xD400 or target > 0xD418:
                self.xrefs[target].append(Reference(
                    source_address=source_addr,
                    source_line=line_num,
                    target_address=target,
                    ref_type=ReferenceType.READ_MODIFY,
                    instruction=line.strip()
                ))


def format_cross_references(address: int, xrefs: Dict[int, List[Reference]],
                            subroutines: Dict[int, 'SubroutineInfo']) -> str:
    """Format cross-references for an address"""
    if address not in xrefs or not xrefs[address]:
        return ""

    refs = xrefs[address]
    header = "; Cross-References:\n"

    # Group by reference type
    calls = [r for r in refs if r.ref_type == ReferenceType.CALL]
    jumps = [r for r in refs if r.ref_type == ReferenceType.JUMP]
    branches = [r for r in refs if r.ref_type == ReferenceType.BRANCH]
    reads = [r for r in refs if r.ref_type == ReferenceType.READ]
    writes = [r for r in refs if r.ref_type == ReferenceType.WRITE]
    read_modifies = [r for r in refs if r.ref_type == ReferenceType.READ_MODIFY]

    # Format calls
    if calls:
        header += ";   Called by:\n"
        for ref in calls[:5]:  # Limit to 5 for brevity
            name = ""
            if ref.source_address and ref.source_address in subroutines:
                name = f" ({subroutines[ref.source_address].name})"
            header += f";     - ${ref.source_address:04X}{name}\n" if ref.source_address else f";     - Line {ref.source_line}\n"
        if len(calls) > 5:
            header += f";     - ... ({len(calls) - 5} more)\n"

    # Format jumps
    if jumps:
        header += ";   Jumped to by:\n"
        for ref in jumps[:5]:
            name = ""
            if ref.source_address and ref.source_address in subroutines:
                name = f" ({subroutines[ref.source_address].name})"
            header += f";     - ${ref.source_address:04X}{name}\n" if ref.source_address else f";     - Line {ref.source_line}\n"
        if len(jumps) > 5:
            header += f";     - ... ({len(jumps) - 5} more)\n"

    # Format branches
    if branches:
        header += ";   Branched to by:\n"
        for ref in branches[:5]:
            header += f";     - ${ref.source_address:04X}\n" if ref.source_address else f";     - Line {ref.source_line}\n"
        if len(branches) > 5:
            header += f";     - ... ({len(branches) - 5} more)\n"

    # Format reads
    if reads:
        header += ";   Read by:\n"
        for ref in reads[:5]:
            name = ""
            if ref.source_address and ref.source_address in subroutines:
                name = f" ({subroutines[ref.source_address].name})"
            header += f";     - ${ref.source_address:04X}{name}\n" if ref.source_address else f";     - Line {ref.source_line}\n"
        if len(reads) > 5:
            header += f";     - ... ({len(reads) - 5} more)\n"

    # Format writes
    if writes:
        header += ";   Written by:\n"
        for ref in writes[:5]:
            name = ""
            if ref.source_address and ref.source_address in subroutines:
                name = f" ({subroutines[ref.source_address].name})"
            header += f";     - ${ref.source_address:04X}{name}\n" if ref.source_address else f";     - Line {ref.source_line}\n"
        if len(writes) > 5:
            header += f";     - ... ({len(writes) - 5} more)\n"

    # Format read-modify-write
    if read_modifies:
        header += ";   Modified by:\n"
        for ref in read_modifies[:5]:
            name = ""
            if ref.source_address and ref.source_address in subroutines:
                name = f" ({subroutines[ref.source_address].name})"
            header += f";     - ${ref.source_address:04X}{name}\n" if ref.source_address else f";     - Line {ref.source_line}\n"
        if len(read_modifies) > 5:
            header += f";     - ... ({len(read_modifies) - 5} more)\n"

    return header


# ==============================================================================
# Pattern Recognition
# ==============================================================================

class PatternType(Enum):
    """Type of recognized code pattern"""
    ADD_16BIT = "16bit_add"
    SUB_16BIT = "16bit_sub"
    LOOP_COUNT = "loop_count"
    LOOP_MEMORY_COPY = "loop_memory_copy"
    LOOP_MEMORY_FILL = "loop_memory_fill"
    DELAY_LOOP = "delay_loop"
    BIT_SHIFT_LEFT = "bit_shift_left"
    BIT_SHIFT_RIGHT = "bit_shift_right"
    CLEAR_MEMORY = "clear_memory"
    COMPARE_16BIT = "16bit_compare"


@dataclass
class Pattern:
    """Represents a recognized code pattern"""
    pattern_type: PatternType
    start_line: int
    end_line: int
    description: str = ""
    variables: Dict[str, str] = field(default_factory=dict)
    result: str = ""


class PatternDetector:
    """Detect common 6502 code patterns"""

    def __init__(self, lines: List[str]):
        self.lines = lines
        self.patterns: List[Pattern] = []

    def detect_all_patterns(self) -> List[Pattern]:
        """Main entry point: detect all patterns in the code"""
        # Detect different pattern types
        self._detect_16bit_addition()
        self._detect_16bit_subtraction()
        self._detect_memory_copy_loops()
        self._detect_memory_fill_loops()
        self._detect_delay_loops()
        self._detect_bit_shifts()
        self._detect_clear_memory()

        # Sort patterns by start line
        self.patterns.sort(key=lambda p: p.start_line)

        return self.patterns

    def _extract_instruction(self, line: str) -> Optional[Tuple[str, str]]:
        """Extract opcode and operand from a line"""
        # Match pattern like: $1000:  LDA #$00  ; comment
        # or just: LDA #$00  ; comment
        match = re.search(r'(?:\$[0-9A-Fa-f]{4}:)?\s*([A-Z]{3})\s+([^;]+)', line, re.IGNORECASE)
        if match:
            opcode = match.group(1).upper()
            operand = match.group(2).strip()
            return (opcode, operand)
        return None

    def _detect_16bit_addition(self):
        """Detect 16-bit addition pattern: CLC; ADC; STA; LDA; ADC; STA"""
        for i in range(len(self.lines) - 5):
            # Look for CLC
            instr0 = self._extract_instruction(self.lines[i])
            if not instr0 or instr0[0] != 'CLC':
                continue

            # Look for ADC (low byte)
            instr1 = self._extract_instruction(self.lines[i + 1])
            if not instr1 or instr1[0] != 'ADC':
                continue

            # Look for STA (store low result)
            instr2 = self._extract_instruction(self.lines[i + 2])
            if not instr2 or instr2[0] != 'STA':
                continue

            # Look for LDA (high byte)
            instr3 = self._extract_instruction(self.lines[i + 3])
            if not instr3 or instr3[0] != 'LDA':
                continue

            # Look for ADC (add carry to high byte)
            instr4 = self._extract_instruction(self.lines[i + 4])
            if not instr4 or instr4[0] != 'ADC':
                continue

            # Look for STA (store high result)
            instr5 = self._extract_instruction(self.lines[i + 5])
            if not instr5 or instr5[0] != 'STA':
                continue

            # Found 16-bit addition pattern!
            self.patterns.append(Pattern(
                pattern_type=PatternType.ADD_16BIT,
                start_line=i,
                end_line=i + 5,
                description="16-bit addition with carry propagation",
                variables={
                    'addend': instr1[1],
                    'result_lo': instr2[1],
                    'high_byte': instr3[1],
                    'result_hi': instr5[1]
                },
                result=f"{instr2[1]}/{instr5[1]} = {instr3[1]} + {instr1[1]} (with carry)"
            ))

    def _detect_16bit_subtraction(self):
        """Detect 16-bit subtraction pattern: SEC; SBC; STA; LDA; SBC; STA"""
        for i in range(len(self.lines) - 5):
            # Look for SEC
            instr0 = self._extract_instruction(self.lines[i])
            if not instr0 or instr0[0] != 'SEC':
                continue

            # Look for SBC (low byte)
            instr1 = self._extract_instruction(self.lines[i + 1])
            if not instr1 or instr1[0] != 'SBC':
                continue

            # Look for STA (store low result)
            instr2 = self._extract_instruction(self.lines[i + 2])
            if not instr2 or instr2[0] != 'STA':
                continue

            # Look for LDA (high byte)
            instr3 = self._extract_instruction(self.lines[i + 3])
            if not instr3 or instr3[0] != 'LDA':
                continue

            # Look for SBC (subtract borrow from high byte)
            instr4 = self._extract_instruction(self.lines[i + 4])
            if not instr4 or instr4[0] != 'SBC':
                continue

            # Look for STA (store high result)
            instr5 = self._extract_instruction(self.lines[i + 5])
            if not instr5 or instr5[0] != 'STA':
                continue

            # Found 16-bit subtraction pattern!
            self.patterns.append(Pattern(
                pattern_type=PatternType.SUB_16BIT,
                start_line=i,
                end_line=i + 5,
                description="16-bit subtraction with borrow propagation",
                variables={
                    'subtrahend': instr1[1],
                    'result_lo': instr2[1],
                    'high_byte': instr3[1],
                    'result_hi': instr5[1]
                },
                result=f"{instr2[1]}/{instr5[1]} = {instr3[1]} - {instr1[1]} (with borrow)"
            ))

    def _detect_memory_copy_loops(self):
        """Detect memory copy loop: LDA source,X; STA dest,X; INX/DEX; BNE"""
        for i in range(len(self.lines) - 3):
            # Look for LDA with indexed addressing
            instr0 = self._extract_instruction(self.lines[i])
            if not instr0 or instr0[0] != 'LDA' or ',X' not in instr0[1] and ',Y' not in instr0[1]:
                continue

            # Look for STA with indexed addressing
            instr1 = self._extract_instruction(self.lines[i + 1])
            if not instr1 or instr1[0] != 'STA' or ',X' not in instr1[1] and ',Y' not in instr1[1]:
                continue

            # Look for INX/INY/DEX/DEY
            instr2 = self._extract_instruction(self.lines[i + 2])
            if not instr2 or instr2[0] not in ['INX', 'INY', 'DEX', 'DEY']:
                continue

            # Look for BNE (or CPX/CPY followed by BNE)
            instr3 = self._extract_instruction(self.lines[i + 3])
            if not instr3:
                continue

            # Check if it's a direct BNE or a compare followed by BNE
            is_loop = False
            end_line = i + 3
            if instr3[0] == 'BNE':
                is_loop = True
            elif instr3[0] in ['CPX', 'CPY'] and i + 4 < len(self.lines):
                instr4 = self._extract_instruction(self.lines[i + 4])
                if instr4 and instr4[0] == 'BNE':
                    is_loop = True
                    end_line = i + 4

            if is_loop:
                source = instr0[1].replace(',X', '').replace(',Y', '')
                dest = instr1[1].replace(',X', '').replace(',Y', '')
                index_reg = 'X' if ',X' in instr0[1] else 'Y'

                self.patterns.append(Pattern(
                    pattern_type=PatternType.LOOP_MEMORY_COPY,
                    start_line=i,
                    end_line=end_line,
                    description=f"Memory copy loop using {index_reg} register",
                    variables={
                        'source': source,
                        'dest': dest,
                        'index': index_reg
                    },
                    result=f"Copy bytes from {source} to {dest}"
                ))

    def _detect_memory_fill_loops(self):
        """Detect memory fill loop: LDA #value; STA dest,X; INX/DEX; BNE"""
        for i in range(len(self.lines) - 3):
            # Look for LDA immediate
            instr0 = self._extract_instruction(self.lines[i])
            if not instr0 or instr0[0] != 'LDA' or not instr0[1].startswith('#'):
                continue

            # Look for STA with indexed addressing
            instr1 = self._extract_instruction(self.lines[i + 1])
            if not instr1 or instr1[0] != 'STA' or ',X' not in instr1[1] and ',Y' not in instr1[1]:
                continue

            # Look for INX/INY/DEX/DEY
            instr2 = self._extract_instruction(self.lines[i + 2])
            if not instr2 or instr2[0] not in ['INX', 'INY', 'DEX', 'DEY']:
                continue

            # Look for BNE or compare+BNE
            instr3 = self._extract_instruction(self.lines[i + 3])
            if not instr3:
                continue

            is_loop = False
            end_line = i + 3
            if instr3[0] == 'BNE':
                is_loop = True
            elif instr3[0] in ['CPX', 'CPY'] and i + 4 < len(self.lines):
                instr4 = self._extract_instruction(self.lines[i + 4])
                if instr4 and instr4[0] == 'BNE':
                    is_loop = True
                    end_line = i + 4

            if is_loop:
                value = instr0[1]
                dest = instr1[1].replace(',X', '').replace(',Y', '')
                index_reg = 'X' if ',X' in instr1[1] else 'Y'

                self.patterns.append(Pattern(
                    pattern_type=PatternType.LOOP_MEMORY_FILL,
                    start_line=i,
                    end_line=end_line,
                    description=f"Memory fill loop using {index_reg} register",
                    variables={
                        'value': value,
                        'dest': dest,
                        'index': index_reg
                    },
                    result=f"Fill memory at {dest} with {value}"
                ))

    def _detect_delay_loops(self):
        """Detect delay loop: LDX/LDY #n; DEX/DEY; BNE (simple counting loop with no body)"""
        for i in range(len(self.lines) - 2):
            # Look for LDX/LDY immediate
            instr0 = self._extract_instruction(self.lines[i])
            if not instr0 or instr0[0] not in ['LDX', 'LDY'] or not instr0[1].startswith('#'):
                continue

            # Look for DEX/DEY (matching register)
            instr1 = self._extract_instruction(self.lines[i + 1])
            expected_dec = 'DEX' if instr0[0] == 'LDX' else 'DEY'
            if not instr1 or instr1[0] != expected_dec:
                continue

            # Look for BNE (branch back to DEX/DEY)
            instr2 = self._extract_instruction(self.lines[i + 2])
            if not instr2 or instr2[0] != 'BNE':
                continue

            # This is a simple delay loop
            count = instr0[1]
            register = 'X' if instr0[0] == 'LDX' else 'Y'

            self.patterns.append(Pattern(
                pattern_type=PatternType.DELAY_LOOP,
                start_line=i,
                end_line=i + 2,
                description=f"Delay loop counting down from {count}",
                variables={
                    'count': count,
                    'register': register
                },
                result=f"Delay for {count} iterations"
            ))

    def _detect_bit_shifts(self):
        """Detect bit shift sequences: ASL/LSR/ROL/ROR chains"""
        for i in range(len(self.lines) - 1):
            # Look for shift instruction
            instr0 = self._extract_instruction(self.lines[i])
            if not instr0 or instr0[0] not in ['ASL', 'LSR', 'ROL', 'ROR']:
                continue

            # Count consecutive shifts on same operand
            shift_op = instr0[0]
            operand = instr0[1]
            shift_count = 1
            j = i + 1

            while j < len(self.lines):
                instr = self._extract_instruction(self.lines[j])
                if instr and instr[0] == shift_op and instr[1] == operand:
                    shift_count += 1
                    j += 1
                else:
                    break

            # Only create pattern if multiple shifts detected
            if shift_count > 1:
                direction = "left" if shift_op in ['ASL', 'ROL'] else "right"
                pattern_type = PatternType.BIT_SHIFT_LEFT if shift_op in ['ASL', 'ROL'] else PatternType.BIT_SHIFT_RIGHT
                with_carry = "with carry" if shift_op in ['ROL', 'ROR'] else "without carry"

                self.patterns.append(Pattern(
                    pattern_type=pattern_type,
                    start_line=i,
                    end_line=j - 1,
                    description=f"Bit shift {direction} by {shift_count} ({with_carry})",
                    variables={
                        'operand': operand,
                        'shifts': str(shift_count),
                        'operation': shift_op
                    },
                    result=f"{operand} shifted {direction} by {shift_count} bits"
                ))

    def _detect_clear_memory(self):
        """Detect clear memory pattern: LDA #$00; STA addr1; STA addr2; ..."""
        for i in range(len(self.lines) - 2):
            # Look for LDA #$00
            instr0 = self._extract_instruction(self.lines[i])
            if not instr0 or instr0[0] != 'LDA' or instr0[1] not in ['#$00', '#0', '#$0']:
                continue

            # Count consecutive STA instructions
            addresses = []
            j = i + 1
            while j < len(self.lines):
                instr = self._extract_instruction(self.lines[j])
                if instr and instr[0] == 'STA':
                    addresses.append(instr[1])
                    j += 1
                else:
                    break

            # Only create pattern if clearing multiple addresses
            if len(addresses) >= 3:
                self.patterns.append(Pattern(
                    pattern_type=PatternType.CLEAR_MEMORY,
                    start_line=i,
                    end_line=j - 1,
                    description=f"Clear {len(addresses)} memory locations",
                    variables={
                        'count': str(len(addresses)),
                        'addresses': ', '.join(addresses[:5]) + ('...' if len(addresses) > 5 else '')
                    },
                    result=f"Zero out {len(addresses)} memory location(s)"
                ))


def format_pattern_header(pattern: Pattern) -> str:
    """Format a header comment for a detected pattern"""
    sep = ";" + "~" * 78
    header = f"{sep}\n"
    header += f"; PATTERN DETECTED: {pattern.description}\n"

    if pattern.pattern_type == PatternType.ADD_16BIT:
        header += f"; Type: 16-bit Addition\n"
        header += f"; Result: {pattern.result}\n"
    elif pattern.pattern_type == PatternType.SUB_16BIT:
        header += f"; Type: 16-bit Subtraction\n"
        header += f"; Result: {pattern.result}\n"
    elif pattern.pattern_type == PatternType.LOOP_MEMORY_COPY:
        header += f"; Type: Memory Copy Loop\n"
        header += f"; Operation: {pattern.result}\n"
    elif pattern.pattern_type == PatternType.LOOP_MEMORY_FILL:
        header += f"; Type: Memory Fill Loop\n"
        header += f"; Operation: {pattern.result}\n"
    elif pattern.pattern_type == PatternType.DELAY_LOOP:
        header += f"; Type: Delay/Timing Loop\n"
        header += f"; Iterations: {pattern.variables.get('count', 'unknown')}\n"
    elif pattern.pattern_type == PatternType.BIT_SHIFT_LEFT:
        header += f"; Type: Bit Shift Left\n"
        header += f"; Result: {pattern.result}\n"
    elif pattern.pattern_type == PatternType.BIT_SHIFT_RIGHT:
        header += f"; Type: Bit Shift Right\n"
        header += f"; Result: {pattern.result}\n"
    elif pattern.pattern_type == PatternType.CLEAR_MEMORY:
        header += f"; Type: Memory Clear\n"
        header += f"; Addresses: {pattern.variables.get('addresses', '')}\n"

    header += f"{sep}\n"

    return header


# ==============================================================================
# Subroutine Detection
# ==============================================================================

@dataclass
class RegisterUsage:
    """Track register usage within a subroutine"""
    a_input: bool = False      # A used before written
    x_input: bool = False      # X used before written
    y_input: bool = False      # Y used before written
    a_output: bool = False     # A written and used after
    x_output: bool = False     # X written and used after
    y_output: bool = False     # Y written and used after
    a_modified: bool = False   # A modified at all
    x_modified: bool = False   # X modified at all
    y_modified: bool = False   # Y modified at all


@dataclass
class SubroutineInfo:
    """Information about a detected subroutine"""
    address: int
    end_address: Optional[int] = None
    name: str = ""
    purpose: str = ""
    calls: List[int] = field(default_factory=list)
    called_by: List[int] = field(default_factory=list)
    register_usage: RegisterUsage = field(default_factory=RegisterUsage)
    accesses_sid: bool = False
    accesses_tables: List[str] = field(default_factory=list)


class SubroutineDetector:
    """Detect and analyze subroutines in 6502 assembly code"""

    def __init__(self, content: str):
        self.content = content
        self.lines = content.split('\n')
        self.subroutines: Dict[int, SubroutineInfo] = {}
        self.jsr_targets: Set[int] = set()

    def detect_all_subroutines(self) -> Dict[int, SubroutineInfo]:
        """Main entry point: detect all subroutines in the code"""
        # Step 1: Find all JSR targets
        self._find_jsr_targets()

        # Step 2: Find entry points (init, play, stop)
        self._find_entry_points()

        # Step 3: Create subroutine info for each target
        for address in self.jsr_targets:
            self._analyze_subroutine(address)

        # Step 4: Build call graph
        self._build_call_graph()

        # Step 5: Infer purposes
        self._infer_purposes()

        return self.subroutines

    def _find_jsr_targets(self):
        """Find all JSR instruction targets"""
        jsr_pattern = re.compile(r'JSR\s+\$([0-9A-Fa-f]{4})', re.IGNORECASE)

        for line in self.lines:
            match = jsr_pattern.search(line)
            if match:
                target = int(match.group(1), 16)
                self.jsr_targets.add(target)

    def _find_entry_points(self):
        """Find known entry points (init, play, stop addresses)"""
        # Look for common entry point patterns
        init_pattern = re.compile(r'[Ii]nit.*\$([0-9A-Fa-f]{4})')
        play_pattern = re.compile(r'[Pp]lay.*\$([0-9A-Fa-f]{4})')

        for line in self.lines[:50]:  # Check first 50 lines for headers
            init_match = init_pattern.search(line)
            play_match = play_pattern.search(line)

            if init_match:
                self.jsr_targets.add(int(init_match.group(1), 16))
            if play_match:
                self.jsr_targets.add(int(play_match.group(1), 16))

    def _analyze_subroutine(self, address: int):
        """Analyze a single subroutine starting at address"""
        info = SubroutineInfo(address=address)

        # Find the subroutine boundaries (address to RTS)
        start_line = self._find_line_by_address(address)
        if start_line is None:
            return

        end_line = self._find_rts_after(start_line)
        if end_line is not None:
            end_addr = self._extract_address_from_line(self.lines[end_line])
            info.end_address = end_addr

        # Analyze instructions within subroutine
        for i in range(start_line, end_line + 1 if end_line else start_line + 50):
            if i >= len(self.lines):
                break

            line = self.lines[i]

            # Check for JSR calls
            jsr_match = re.search(r'JSR\s+\$([0-9A-Fa-f]{4})', line, re.IGNORECASE)
            if jsr_match:
                called_addr = int(jsr_match.group(1), 16)
                info.calls.append(called_addr)

            # Check for SID access
            if re.search(r'\$D4[0-1][0-9A-F]', line, re.IGNORECASE):
                info.accesses_sid = True

            # Check for table access
            for table_addr, table_name in LAXITY_TABLES.items():
                if f'${table_addr:04X}' in line.upper():
                    if table_name not in info.accesses_tables:
                        info.accesses_tables.append(table_name)

            # Track register usage
            self._analyze_register_usage(line, info.register_usage)

        self.subroutines[address] = info

    def _find_line_by_address(self, address: int) -> Optional[int]:
        """Find line number containing the given address"""
        addr_pattern = re.compile(r'\$?' + f'{address:04X}', re.IGNORECASE)

        for i, line in enumerate(self.lines):
            # Look for address at start of line (common format: $1000: or 1000:)
            if line.strip().startswith(f'${address:04X}:') or \
               line.strip().startswith(f'{address:04X}:'):
                return i
            # Also check for hex addresses in various formats
            if addr_pattern.match(line.strip().split(':')[0] if ':' in line else ''):
                return i
            # Check for comments that indicate the address (like "; Init routine ($0D7E)")
            if f'(${address:04X})' in line.upper():
                # This might be a comment before the label, search next few lines for label
                for j in range(i, min(i+3, len(self.lines))):
                    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:', self.lines[j].strip()):
                        return j
            # Check for label immediately after address definition (like "*=$0D7E" followed by label)
            if re.match(r'^\s*\*\s*=\s*\$' + f'{address:04X}', line, re.IGNORECASE):
                # Search next few lines for a label
                for j in range(i+1, min(i+5, len(self.lines))):
                    next_line = self.lines[j].strip()
                    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:', next_line):
                        return j

        return None

    def _find_rts_after(self, start_line: int) -> Optional[int]:
        """Find the next RTS instruction after start_line"""
        rts_pattern = re.compile(r'\bRTS\b', re.IGNORECASE)

        for i in range(start_line, min(start_line + 200, len(self.lines))):
            if rts_pattern.search(self.lines[i]):
                return i

        return None

    def _extract_address_from_line(self, line: str) -> Optional[int]:
        """Extract address from a line like '$1234: RTS'"""
        match = re.match(r'\$?([0-9A-Fa-f]{4}):', line.strip())
        if match:
            return int(match.group(1), 16)
        return None

    def _analyze_register_usage(self, line: str, usage: RegisterUsage):
        """Analyze how registers are used in a line"""
        upper_line = line.upper()

        # Check A register
        if re.search(r'\bLDA\b', upper_line):
            usage.a_modified = True
            usage.a_output = True
        elif re.search(r'\bSTA\b', upper_line):
            usage.a_input = True
        elif re.search(r'\bADC\b|\bSBC\b|\bAND\b|\bORA\b|\bEOR\b|\bCMP\b', upper_line):
            usage.a_input = True
            usage.a_modified = True
            usage.a_output = True

        # Check X register
        if re.search(r'\bLDX\b', upper_line):
            usage.x_modified = True
            usage.x_output = True
        elif re.search(r'\bSTX\b', upper_line):
            usage.x_input = True
        elif re.search(r'\bINX\b|\bDEX\b|\bCPX\b', upper_line):
            usage.x_input = True
            usage.x_modified = True
            usage.x_output = True

        # Check Y register
        if re.search(r'\bLDY\b', upper_line):
            usage.y_modified = True
            usage.y_output = True
        elif re.search(r'\bSTY\b', upper_line):
            usage.y_input = True
        elif re.search(r'\bINY\b|\bDEY\b|\bCPY\b', upper_line):
            usage.y_input = True
            usage.y_modified = True
            usage.y_output = True

        # Check indexed addressing (uses X or Y as input)
        if re.search(r',X\b', upper_line):
            usage.x_input = True
        if re.search(r',Y\b', upper_line):
            usage.y_input = True

    def _build_call_graph(self):
        """Build bidirectional call graph"""
        for addr, info in self.subroutines.items():
            for called_addr in info.calls:
                if called_addr in self.subroutines:
                    self.subroutines[called_addr].called_by.append(addr)

    def _infer_purposes(self):
        """Infer subroutine purposes from their behavior"""
        for addr, info in self.subroutines.items():
            # Infer name from address (common patterns)
            if info.accesses_sid and not info.calls:
                info.purpose = "Initialize or control SID chip"
                info.name = "SID Control"
            elif info.accesses_sid:
                info.purpose = "Update SID registers (music playback)"
                info.name = "SID Update"
            elif len(info.accesses_tables) > 0:
                table_names = ", ".join([t.split(' - ')[0] for t in info.accesses_tables[:2]])
                info.purpose = f"Access music data ({table_names})"
                info.name = "Music Data Access"
            elif len(info.calls) > 2:
                info.purpose = "Coordinate multiple operations"
                info.name = "Main Coordinator"
            elif not info.calls and not info.accesses_sid:
                info.purpose = "Utility or helper function"
                info.name = "Utility"
            else:
                info.purpose = "Subroutine"
                info.name = "Subroutine"


def generate_subroutine_header(info: SubroutineInfo,
                               xrefs: Optional[Dict[int, List[Reference]]] = None,
                               all_subroutines: Optional[Dict[int, 'SubroutineInfo']] = None,
                               cycle_counter: Optional['CycleCounter'] = None) -> str:
    """Generate a detailed header comment for a subroutine"""
    sep = ";" + "-" * 78
    header = f"{sep}\n"
    header += f"; Subroutine: {info.name}\n"
    header += f"; Address: ${info.address:04X}"

    if info.end_address:
        header += f" - ${info.end_address:04X}\n"
    else:
        header += "\n"

    if info.purpose:
        header += f"; Purpose: {info.purpose}\n"

    # Add cycle count information if available
    if cycle_counter:
        min_c, max_c, typ_c = cycle_counter.count_subroutine_cycles(info)
        if typ_c > 0:
            cycle_summary = format_cycle_summary(min_c, max_c, typ_c, 'NTSC')
            header += cycle_summary

    # Document register inputs
    inputs = []
    if info.register_usage.a_input and not info.register_usage.a_modified:
        inputs.append("A")
    if info.register_usage.x_input and not info.register_usage.x_modified:
        inputs.append("X")
    if info.register_usage.y_input and not info.register_usage.y_modified:
        inputs.append("Y")

    if inputs:
        header += f"; Inputs: {', '.join(inputs)}\n"
    else:
        header += "; Inputs: None\n"

    # Document register outputs
    outputs = []
    if info.register_usage.a_output:
        outputs.append("A")
    if info.register_usage.x_output:
        outputs.append("X")
    if info.register_usage.y_output:
        outputs.append("Y")

    if outputs:
        header += f"; Outputs: {', '.join(outputs)}\n"

    # Document modified registers
    modified = []
    if info.register_usage.a_modified:
        modified.append("A")
    if info.register_usage.x_modified:
        modified.append("X")
    if info.register_usage.y_modified:
        modified.append("Y")

    if modified:
        header += f"; Modifies: {', '.join(modified)}\n"

    # Document calls
    if info.calls:
        header += f"; Calls: "
        call_strs = [f"${addr:04X}" for addr in info.calls[:3]]
        if len(info.calls) > 3:
            call_strs.append(f"... ({len(info.calls)} total)")
        header += ", ".join(call_strs) + "\n"

    # Document callers
    if info.called_by:
        header += f"; Called by: "
        caller_strs = [f"${addr:04X}" for addr in info.called_by[:3]]
        if len(info.called_by) > 3:
            caller_strs.append(f"... ({len(info.called_by)} total)")
        header += ", ".join(caller_strs) + "\n"

    # Add enhanced cross-references if available
    if xrefs and all_subroutines:
        xref_header = format_cross_references(info.address, xrefs, all_subroutines)
        if xref_header:
            header += xref_header

    # Document SID access
    if info.accesses_sid:
        header += "; Accesses: SID chip registers\n"

    # Document table access
    if info.accesses_tables:
        tables_str = ", ".join([t.split(' - ')[0] for t in info.accesses_tables])
        header += f"; Tables: {tables_str}\n"

    header += f"{sep}\n"

    return header


# ==============================================================================
# Cycle Counting
# ==============================================================================

# Frame timing constants
NTSC_CYCLES_PER_FRAME = 19656  # 60 Hz
PAL_CYCLES_PER_FRAME = 19705   # 50 Hz

# 6502 Cycle counts by opcode and addressing mode
# Format: (opcode, addressing_mode): cycles
# Addressing modes: IMM (immediate), ZP (zero page), ZPX/ZPY (zero page indexed),
#                   ABS (absolute), ABSX/ABSY (absolute indexed), IND (indirect),
#                   INDX (indexed indirect), INDY (indirect indexed), IMP (implied)
#
# Note: Some instructions have variable timing (marked with +1 for page crossing)
CYCLE_COUNTS = {
    # Load/Store
    ('LDA', 'IMM'): 2, ('LDA', 'ZP'): 3, ('LDA', 'ZPX'): 4,
    ('LDA', 'ABS'): 4, ('LDA', 'ABSX'): 4, ('LDA', 'ABSY'): 4,  # +1 if page crossed
    ('LDA', 'INDX'): 6, ('LDA', 'INDY'): 5,  # +1 if page crossed on INDY

    ('LDX', 'IMM'): 2, ('LDX', 'ZP'): 3, ('LDX', 'ZPY'): 4,
    ('LDX', 'ABS'): 4, ('LDX', 'ABSY'): 4,  # +1 if page crossed

    ('LDY', 'IMM'): 2, ('LDY', 'ZP'): 3, ('LDY', 'ZPX'): 4,
    ('LDY', 'ABS'): 4, ('LDY', 'ABSX'): 4,  # +1 if page crossed

    ('STA', 'ZP'): 3, ('STA', 'ZPX'): 4,
    ('STA', 'ABS'): 4, ('STA', 'ABSX'): 5, ('STA', 'ABSY'): 5,
    ('STA', 'INDX'): 6, ('STA', 'INDY'): 6,

    ('STX', 'ZP'): 3, ('STX', 'ZPY'): 4, ('STX', 'ABS'): 4,
    ('STY', 'ZP'): 3, ('STY', 'ZPX'): 4, ('STY', 'ABS'): 4,

    # Transfer
    ('TAX', 'IMP'): 2, ('TAY', 'IMP'): 2, ('TXA', 'IMP'): 2, ('TYA', 'IMP'): 2,
    ('TSX', 'IMP'): 2, ('TXS', 'IMP'): 2,

    # Stack
    ('PHA', 'IMP'): 3, ('PHP', 'IMP'): 3, ('PLA', 'IMP'): 4, ('PLP', 'IMP'): 4,

    # Increment/Decrement
    ('INC', 'ZP'): 5, ('INC', 'ZPX'): 6, ('INC', 'ABS'): 6, ('INC', 'ABSX'): 7,
    ('DEC', 'ZP'): 5, ('DEC', 'ZPX'): 6, ('DEC', 'ABS'): 6, ('DEC', 'ABSX'): 7,
    ('INX', 'IMP'): 2, ('INY', 'IMP'): 2, ('DEX', 'IMP'): 2, ('DEY', 'IMP'): 2,

    # Arithmetic
    ('ADC', 'IMM'): 2, ('ADC', 'ZP'): 3, ('ADC', 'ZPX'): 4,
    ('ADC', 'ABS'): 4, ('ADC', 'ABSX'): 4, ('ADC', 'ABSY'): 4,  # +1 if page crossed
    ('ADC', 'INDX'): 6, ('ADC', 'INDY'): 5,  # +1 if page crossed on INDY

    ('SBC', 'IMM'): 2, ('SBC', 'ZP'): 3, ('SBC', 'ZPX'): 4,
    ('SBC', 'ABS'): 4, ('SBC', 'ABSX'): 4, ('SBC', 'ABSY'): 4,  # +1 if page crossed
    ('SBC', 'INDX'): 6, ('SBC', 'INDY'): 5,  # +1 if page crossed on INDY

    # Logical
    ('AND', 'IMM'): 2, ('AND', 'ZP'): 3, ('AND', 'ZPX'): 4,
    ('AND', 'ABS'): 4, ('AND', 'ABSX'): 4, ('AND', 'ABSY'): 4,  # +1 if page crossed
    ('AND', 'INDX'): 6, ('AND', 'INDY'): 5,  # +1 if page crossed on INDY

    ('ORA', 'IMM'): 2, ('ORA', 'ZP'): 3, ('ORA', 'ZPX'): 4,
    ('ORA', 'ABS'): 4, ('ORA', 'ABSX'): 4, ('ORA', 'ABSY'): 4,  # +1 if page crossed
    ('ORA', 'INDX'): 6, ('ORA', 'INDY'): 5,  # +1 if page crossed on INDY

    ('EOR', 'IMM'): 2, ('EOR', 'ZP'): 3, ('EOR', 'ZPX'): 4,
    ('EOR', 'ABS'): 4, ('EOR', 'ABSX'): 4, ('EOR', 'ABSY'): 4,  # +1 if page crossed
    ('EOR', 'INDX'): 6, ('EOR', 'INDY'): 5,  # +1 if page crossed on INDY

    # Compare
    ('CMP', 'IMM'): 2, ('CMP', 'ZP'): 3, ('CMP', 'ZPX'): 4,
    ('CMP', 'ABS'): 4, ('CMP', 'ABSX'): 4, ('CMP', 'ABSY'): 4,  # +1 if page crossed
    ('CMP', 'INDX'): 6, ('CMP', 'INDY'): 5,  # +1 if page crossed on INDY

    ('CPX', 'IMM'): 2, ('CPX', 'ZP'): 3, ('CPX', 'ABS'): 4,
    ('CPY', 'IMM'): 2, ('CPY', 'ZP'): 3, ('CPY', 'ABS'): 4,

    # Shifts/Rotates
    ('ASL', 'ACC'): 2, ('ASL', 'ZP'): 5, ('ASL', 'ZPX'): 6, ('ASL', 'ABS'): 6, ('ASL', 'ABSX'): 7,
    ('LSR', 'ACC'): 2, ('LSR', 'ZP'): 5, ('LSR', 'ZPX'): 6, ('LSR', 'ABS'): 6, ('LSR', 'ABSX'): 7,
    ('ROL', 'ACC'): 2, ('ROL', 'ZP'): 5, ('ROL', 'ZPX'): 6, ('ROL', 'ABS'): 6, ('ROL', 'ABSX'): 7,
    ('ROR', 'ACC'): 2, ('ROR', 'ZP'): 5, ('ROR', 'ZPX'): 6, ('ROR', 'ABS'): 6, ('ROR', 'ABSX'): 7,

    # Branches (2 cycles if not taken, 3 if taken, 4 if page crossed)
    ('BCC', 'REL'): 2, ('BCS', 'REL'): 2, ('BEQ', 'REL'): 2, ('BNE', 'REL'): 2,
    ('BMI', 'REL'): 2, ('BPL', 'REL'): 2, ('BVC', 'REL'): 2, ('BVS', 'REL'): 2,

    # Jumps/Calls
    ('JMP', 'ABS'): 3, ('JMP', 'IND'): 5,
    ('JSR', 'ABS'): 6,
    ('RTS', 'IMP'): 6,
    ('RTI', 'IMP'): 6,

    # Flags
    ('CLC', 'IMP'): 2, ('SEC', 'IMP'): 2, ('CLI', 'IMP'): 2, ('SEI', 'IMP'): 2,
    ('CLV', 'IMP'): 2, ('CLD', 'IMP'): 2, ('SED', 'IMP'): 2,

    # Misc
    ('BIT', 'ZP'): 3, ('BIT', 'ABS'): 4,
    ('NOP', 'IMP'): 2,
    ('BRK', 'IMP'): 7,
}


@dataclass
class CycleInfo:
    """Information about cycle count for an instruction"""
    min_cycles: int
    max_cycles: int
    typical_cycles: int
    notes: str = ""

    @property
    def is_variable(self) -> bool:
        """Returns True if cycle count varies"""
        return self.min_cycles != self.max_cycles


class CycleCounter:
    """Count CPU cycles for 6502 assembly instructions"""

    def __init__(self, lines: List[str], subroutines: Dict[int, 'SubroutineInfo']):
        self.lines = lines
        self.subroutines = subroutines
        self.cycle_counts: Dict[int, CycleInfo] = {}  # address -> cycle info

    def count_all_cycles(self) -> Dict[int, CycleInfo]:
        """Count cycles for all instructions in the file"""
        for i, line in enumerate(self.lines):
            addr = self._extract_address(line)
            if addr is not None:
                cycle_info = self._count_instruction_cycles(line)
                if cycle_info:
                    self.cycle_counts[addr] = cycle_info

        return self.cycle_counts

    def count_subroutine_cycles(self, subroutine: 'SubroutineInfo') -> Tuple[int, int, int]:
        """
        Count total cycles for a subroutine

        Returns:
            (min_cycles, max_cycles, typical_cycles)
        """
        min_total = 0
        max_total = 0
        typical_total = 0

        # Find all instructions in this subroutine
        start_addr = subroutine.address
        end_addr = subroutine.end_address or (start_addr + 1000)  # Default range

        for addr in range(start_addr, end_addr):
            if addr in self.cycle_counts:
                info = self.cycle_counts[addr]
                min_total += info.min_cycles
                max_total += info.max_cycles
                typical_total += info.typical_cycles

                # Stop at RTS
                line = self._find_line_by_address(addr)
                if line and 'RTS' in line:
                    break

        return (min_total, max_total, typical_total)

    def _count_instruction_cycles(self, line: str) -> Optional[CycleInfo]:
        """Count cycles for a single instruction"""
        # Extract opcode and operand
        parts = self._parse_instruction(line)
        if not parts:
            return None

        opcode, operand = parts

        # Determine addressing mode
        addr_mode = self._detect_addressing_mode(opcode, operand)
        if not addr_mode:
            return None

        # Look up base cycle count
        key = (opcode, addr_mode)
        if key not in CYCLE_COUNTS:
            return None

        base_cycles = CYCLE_COUNTS[key]

        # Determine if variable (page crossing or branch taken)
        min_cycles = base_cycles
        max_cycles = base_cycles
        typical_cycles = base_cycles
        notes = ""

        # Check for page crossing possibility
        if addr_mode in ['ABSX', 'ABSY', 'INDY']:
            if opcode in ['LDA', 'LDX', 'LDY', 'ADC', 'SBC', 'AND', 'ORA', 'EOR', 'CMP']:
                max_cycles = base_cycles + 1
                typical_cycles = base_cycles  # Assume same page typically
                notes = "+1 if page crossed"

        # Branches have variable timing
        if addr_mode == 'REL':
            max_cycles = 4  # Taken + page crossed
            typical_cycles = 3  # Assume taken, same page
            notes = "+1 if taken, +2 if page crossed"

        return CycleInfo(
            min_cycles=min_cycles,
            max_cycles=max_cycles,
            typical_cycles=typical_cycles,
            notes=notes
        )

    def _parse_instruction(self, line: str) -> Optional[Tuple[str, str]]:
        """Parse instruction line into (opcode, operand)"""
        # Match pattern: $ADDR: BYTES  OPCODE OPERAND  ; comment
        # Example: $1000: A9 00    LDA  #$00         ; comment
        match = re.search(r'([A-Z]{3})\s+(.+?)(?:\s*;|$)', line)
        if match:
            opcode = match.group(1).strip()
            operand = match.group(2).strip()
            return (opcode, operand)

        # Try simpler pattern: OPCODE OPERAND
        match = re.search(r'^[^;]*\s([A-Z]{3})(?:\s+(.+?))?(?:\s*;|$)', line)
        if match:
            opcode = match.group(1).strip()
            operand = match.group(2).strip() if match.group(2) else ""
            return (opcode, operand)

        return None

    def _detect_addressing_mode(self, opcode: str, operand: str) -> Optional[str]:
        """Detect addressing mode from operand"""
        if not operand:
            # Implied or Accumulator
            if opcode in ['ASL', 'LSR', 'ROL', 'ROR']:
                return 'ACC'  # Accumulator
            return 'IMP'  # Implied

        operand = operand.upper().strip()

        # Immediate: #$00
        if operand.startswith('#'):
            return 'IMM'

        # Indirect indexed: ($00),Y
        if '(' in operand and '),Y' in operand:
            return 'INDY'

        # Indexed indirect: ($00,X)
        if '(' in operand and ',X)' in operand:
            return 'INDX'

        # Indirect: ($0000)
        if operand.startswith('(') and operand.endswith(')'):
            return 'IND'

        # Indexed: $00,X or $0000,X
        if ',X' in operand:
            # Check if zero page or absolute
            addr_part = operand.split(',')[0].strip()
            if addr_part.startswith('$'):
                addr_hex = addr_part[1:]
                if len(addr_hex) <= 2:
                    return 'ZPX'
                else:
                    return 'ABSX'
            return 'ABSX'  # Default to absolute

        if ',Y' in operand:
            # Check if zero page or absolute
            addr_part = operand.split(',')[0].strip()
            if addr_part.startswith('$'):
                addr_hex = addr_part[1:]
                if len(addr_hex) <= 2:
                    return 'ZPY'
                else:
                    return 'ABSY'
            return 'ABSY'  # Default to absolute

        # Relative (for branches)
        if opcode in ['BCC', 'BCS', 'BEQ', 'BNE', 'BMI', 'BPL', 'BVC', 'BVS']:
            return 'REL'

        # Absolute or Zero Page
        if operand.startswith('$'):
            addr_hex = operand[1:]
            if len(addr_hex) <= 2:
                return 'ZP'
            else:
                return 'ABS'

        return 'ABS'  # Default

    def _extract_address(self, line: str) -> Optional[int]:
        """Extract address from line"""
        match = re.match(r'^\s*\$?([0-9A-Fa-f]{4}):', line)
        if match:
            return int(match.group(1), 16)
        return None

    def _find_line_by_address(self, address: int) -> Optional[str]:
        """Find line by address"""
        for line in self.lines:
            addr = self._extract_address(line)
            if addr == address:
                return line
        return None


def format_cycle_summary(min_cycles: int, max_cycles: int, typical_cycles: int,
                         system: str = 'NTSC') -> str:
    """Format cycle count summary with frame budget"""
    frame_cycles = NTSC_CYCLES_PER_FRAME if system == 'NTSC' else PAL_CYCLES_PER_FRAME

    # Calculate percentages
    min_pct = (min_cycles / frame_cycles) * 100
    max_pct = (max_cycles / frame_cycles) * 100
    typical_pct = (typical_cycles / frame_cycles) * 100

    output = ""

    if min_cycles == max_cycles:
        # Fixed cycle count
        output += f"; Cycles: {typical_cycles} ({typical_pct:.1f}% of {system} frame)\n"
    else:
        # Variable cycle count
        output += f"; Cycles: {min_cycles}-{max_cycles} (typically {typical_cycles})\n"
        output += f"; Frame %: {min_pct:.1f}%-{max_pct:.1f}% (typically {typical_pct:.1f}% of {system} frame)\n"

    # Calculate remaining budget
    remaining = frame_cycles - typical_cycles
    remaining_pct = (remaining / frame_cycles) * 100
    output += f"; Budget remaining: {remaining} cycles ({remaining_pct:.1f}%)\n"

    # Warning if over budget
    if typical_cycles > frame_cycles:
        output += f"; ⚠ WARNING: Exceeds frame budget by {typical_cycles - frame_cycles} cycles!\n"

    return output


# ==============================================================================
# Control Flow Visualization
# ==============================================================================

@dataclass
class CallGraphNode:
    """Node in the call graph representing a subroutine"""
    address: int
    name: str
    calls: List[int] = field(default_factory=list)
    called_by: List[int] = field(default_factory=list)
    cycles_min: int = 0
    cycles_max: int = 0
    cycles_typical: int = 0


@dataclass
class LoopInfo:
    """Information about a detected loop"""
    start_address: int
    end_address: int
    loop_type: str  # "counted", "conditional", "infinite"
    counter_register: str = ""  # X, Y, or memory address
    iterations_min: int = 0
    iterations_max: int = 0
    iterations_typical: int = 0
    cycles_per_iteration: int = 0
    description: str = ""


@dataclass
class BranchInfo:
    """Information about a conditional branch"""
    address: int
    opcode: str
    target: int
    is_backward: bool  # True if branch goes backward (likely a loop)
    is_forward: bool   # True if branch goes forward (likely a conditional)


class ControlFlowAnalyzer:
    """Analyze control flow: calls, branches, loops"""

    def __init__(self,
                 lines: List[str],
                 subroutines: Dict[int, 'SubroutineInfo'],
                 cycle_counter: Optional['CycleCounter'] = None):
        self.lines = lines
        self.subroutines = subroutines
        self.cycle_counter = cycle_counter
        self.call_graph: Dict[int, CallGraphNode] = {}
        self.branches: List[BranchInfo] = []
        self.loops: List[LoopInfo] = []

    def analyze_all(self) -> Tuple[Dict[int, CallGraphNode], List[LoopInfo], List[BranchInfo]]:
        """Main entry point: analyze all control flow"""
        self._build_call_graph()
        self._detect_branches()
        self._detect_loops()
        return (self.call_graph, self.loops, self.branches)

    def _build_call_graph(self):
        """Build call graph from JSR instructions"""
        # Create nodes for all subroutines
        for addr, info in self.subroutines.items():
            cycles_min = 0
            cycles_max = 0
            cycles_typical = 0

            if self.cycle_counter:
                cycles_min, cycles_max, cycles_typical = self.cycle_counter.count_subroutine_cycles(info)

            self.call_graph[addr] = CallGraphNode(
                address=addr,
                name=info.name,
                calls=list(info.calls),
                called_by=list(info.called_by),
                cycles_min=cycles_min,
                cycles_max=cycles_max,
                cycles_typical=cycles_typical
            )

    def _detect_branches(self):
        """Detect all conditional branches"""
        branch_opcodes = {'BEQ', 'BNE', 'BPL', 'BMI', 'BCC', 'BCS', 'BVC', 'BVS'}

        for line in self.lines:
            # Extract address and instruction
            addr = self._extract_address(line)
            if addr is None:
                continue

            # Check for branch instruction - handle both $ADDR and label formats
            # Pattern: BNE  $a051 or BNE  la051
            match = re.search(r'([A-Z]{3})\s+(?:\$?([0-9A-Fa-f]{4})|l?a?([0-9A-Fa-f]{3,4}))', line)
            if match:
                opcode = match.group(1)
                if opcode in branch_opcodes:
                    # Try to extract target address from either hex or label
                    target_hex = match.group(2) or match.group(3)
                    if target_hex:
                        target = int(target_hex, 16)
                        is_backward = target < addr
                        is_forward = target > addr

                        self.branches.append(BranchInfo(
                            address=addr,
                            opcode=opcode,
                            target=target,
                            is_backward=is_backward,
                            is_forward=is_forward
                        ))

    def _detect_loops(self):
        """Detect loops (backward branches and counted loops)"""
        # Group backward branches as potential loops
        backward_branches = [b for b in self.branches if b.is_backward]

        for branch in backward_branches:
            # Look for counted loop pattern: LDX/LDY #n ... DEX/DEY ... BNE
            loop_info = self._analyze_loop(branch.target, branch.address)
            if loop_info:
                self.loops.append(loop_info)

    def _analyze_loop(self, start_addr: int, end_addr: int) -> Optional[LoopInfo]:
        """Analyze a potential loop between start and end addresses"""
        # Find lines in loop body
        loop_lines = []
        for line in self.lines:
            addr = self._extract_address(line)
            if addr and start_addr <= addr <= end_addr:
                loop_lines.append(line)

        if not loop_lines:
            return None

        # Check for counted loop pattern (LDX/LDY #n)
        counter_reg = None
        initial_count = None

        for line in loop_lines[:3]:  # Check first few lines
            match = re.search(r'(LDX|LDY)\s+#\$?([0-9A-Fa-f]+)', line)
            if match:
                counter_reg = match.group(1)[2]  # 'X' or 'Y'
                initial_count = int(match.group(2), 16)
                break

        # Check for decrement (DEX/DEY)
        has_decrement = any(f'DE{counter_reg}' in line if counter_reg else False
                           for line in loop_lines)

        # Calculate cycles per iteration
        cycles_per_iter = 0
        if self.cycle_counter:
            for line in loop_lines:
                addr = self._extract_address(line)
                if addr and addr in self.cycle_counter.cycle_counts:
                    info = self.cycle_counter.cycle_counts[addr]
                    cycles_per_iter += info.typical_cycles

        # Determine loop type
        if counter_reg and has_decrement and initial_count:
            # Counted loop
            return LoopInfo(
                start_address=start_addr,
                end_address=end_addr,
                loop_type="counted",
                counter_register=counter_reg,
                iterations_min=initial_count,
                iterations_max=initial_count,
                iterations_typical=initial_count,
                cycles_per_iteration=cycles_per_iter,
                description=f"Counted loop (register {counter_reg}, {initial_count} iterations)"
            )
        else:
            # Conditional loop (unknown iteration count)
            return LoopInfo(
                start_address=start_addr,
                end_address=end_addr,
                loop_type="conditional",
                counter_register="",
                iterations_min=1,
                iterations_max=100,  # Estimate
                iterations_typical=10,  # Estimate
                cycles_per_iteration=cycles_per_iter,
                description="Conditional loop (variable iterations)"
            )

    def _extract_address(self, line: str) -> Optional[int]:
        """Extract address from line"""
        match = re.match(r'^\s*\$?([0-9A-Fa-f]{4}):', line)
        if match:
            return int(match.group(1), 16)
        return None


def format_call_graph(call_graph: Dict[int, CallGraphNode],
                      subroutines: Dict[int, 'SubroutineInfo'],
                      max_depth: int = 10) -> str:
    """Format call graph as ASCII art tree"""
    if not call_graph:
        return ""

    sep = "=" * 78
    output = f";{sep}\n"
    output += f"; CALL GRAPH\n"
    output += f";{sep}\n"
    output += ";\n"

    # Find entry points (not called by anyone, or called by few)
    entry_points = []
    for addr, node in call_graph.items():
        if not node.called_by or len(node.called_by) <= 1:
            entry_points.append(addr)

    # Limit to first few entry points
    entry_points = sorted(entry_points)[:5]

    if entry_points:
        output += f"; Entry Points ({len(entry_points)}):\n"
        for addr in entry_points:
            node = call_graph[addr]
            cycles_str = ""
            if node.cycles_typical > 0:
                pct = (node.cycles_typical / NTSC_CYCLES_PER_FRAME) * 100
                cycles_str = f" ({node.cycles_typical} cycles, {pct:.1f}% frame)"
            output += f";   - {node.name} [${addr:04X}]{cycles_str}\n"
        output += ";\n"

    # Build call hierarchy for each entry point
    output += "; Call Hierarchy:\n;\n"

    for entry_addr in entry_points:
        output += _format_call_tree(entry_addr, call_graph, subroutines, "", set(), 0, max_depth)
        output += ";\n"

    # Statistics
    total_subs = len(call_graph)
    max_call_depth = _calculate_max_depth(call_graph)
    recursive_calls = sum(1 for node in call_graph.values() if node.address in node.calls)

    output += "; Statistics:\n"
    output += f";   - Total subroutines: {total_subs}\n"
    output += f";   - Maximum call depth: {max_call_depth} levels\n"
    output += f";   - Recursive calls: {recursive_calls}\n"

    # Find hottest path
    hottest = max(call_graph.values(), key=lambda n: n.cycles_typical, default=None)
    if hottest and hottest.cycles_typical > 0:
        pct = (hottest.cycles_typical / NTSC_CYCLES_PER_FRAME) * 100
        output += f";   - Hottest subroutine: {hottest.name} ({hottest.cycles_typical} cycles, {pct:.1f}%)\n"

    output += f";{sep}\n"
    output += ";\n"

    return output


def _format_call_tree(addr: int,
                     call_graph: Dict[int, CallGraphNode],
                     subroutines: Dict[int, 'SubroutineInfo'],
                     prefix: str,
                     visited: Set[int],
                     depth: int,
                     max_depth: int) -> str:
    """Recursively format call tree (helper for format_call_graph)"""
    if depth >= max_depth or addr in visited:
        return ""

    visited.add(addr)
    node = call_graph.get(addr)
    if not node:
        return ""

    output = ""

    # Format this node
    cycles_str = ""
    if node.cycles_typical > 0:
        cycles_str = f" ({node.cycles_typical} cycles)"

    output += f"; {prefix}{node.name} [${addr:04X}]{cycles_str}\n"

    # Format children
    if node.calls:
        for i, callee_addr in enumerate(node.calls[:5]):  # Limit to first 5 calls
            is_last = (i == len(node.calls) - 1) or (i == 4)
            child_prefix = prefix + ("└─> " if is_last else "├─> ")
            next_prefix = prefix + ("    " if is_last else "│   ")

            output += f"; {child_prefix}JSR ${callee_addr:04X}"

            # Add callee name if known
            if callee_addr in call_graph:
                callee_node = call_graph[callee_addr]
                cycles_str = ""
                if callee_node.cycles_typical > 0:
                    cycles_str = f" ({callee_node.cycles_typical} cycles)"
                output += f" - {callee_node.name}{cycles_str}"

            output += "\n"

            # Recurse (only for first few to avoid deep trees)
            if i < 3 and callee_addr in call_graph:
                child_output = _format_call_tree(callee_addr, call_graph, subroutines,
                                                 next_prefix, visited.copy(), depth + 1, max_depth)
                if child_output:
                    output += child_output

        if len(node.calls) > 5:
            output += f"; {prefix}    ... and {len(node.calls) - 5} more call(s)\n"

    return output


def _calculate_max_depth(call_graph: Dict[int, CallGraphNode]) -> int:
    """Calculate maximum call depth in the call graph"""
    def depth_from(addr: int, visited: Set[int]) -> int:
        if addr in visited or addr not in call_graph:
            return 0
        visited.add(addr)
        node = call_graph[addr]
        if not node.calls:
            return 1
        max_child_depth = max((depth_from(c, visited.copy()) for c in node.calls), default=0)
        return 1 + max_child_depth

    # Start from entry points
    entry_points = [addr for addr, node in call_graph.items() if not node.called_by]
    if not entry_points:
        entry_points = list(call_graph.keys())[:1]

    return max((depth_from(addr, set()) for addr in entry_points), default=0)


def format_loop_analysis(loops: List[LoopInfo]) -> str:
    """Format loop analysis"""
    if not loops:
        return ""

    sep = "=" * 78
    output = f";{sep}\n"
    output += f"; LOOP ANALYSIS\n"
    output += f";{sep}\n"
    output += ";\n"

    output += f"; Detected Loops: {len(loops)}\n"
    output += ";\n"

    for i, loop in enumerate(loops, 1):
        output += f"; Loop #{i}: [${loop.start_address:04X}-${loop.end_address:04X}]\n"
        output += f";   Type: {loop.loop_type}\n"

        if loop.counter_register:
            output += f";   Counter: Register {loop.counter_register}\n"

        if loop.iterations_typical > 0:
            if loop.iterations_min == loop.iterations_max:
                output += f";   Iterations: {loop.iterations_typical} (fixed)\n"
            else:
                output += f";   Iterations: {loop.iterations_min}-{loop.iterations_max} (typically {loop.iterations_typical})\n"

        if loop.cycles_per_iteration > 0:
            total_cycles = loop.cycles_per_iteration * loop.iterations_typical
            output += f";   Per iteration: {loop.cycles_per_iteration} cycles\n"
            output += f";   Total: {total_cycles} cycles (typically)\n"

            # Calculate percentage of frame
            pct = (total_cycles / NTSC_CYCLES_PER_FRAME) * 100
            output += f";   Frame %: {pct:.1f}%\n"

        if loop.description:
            output += f";   Description: {loop.description}\n"

        output += ";\n"

    output += f";{sep}\n"
    output += ";\n"

    return output


# ==============================================================================
# Symbol Table Generation
# ==============================================================================

class SymbolType(Enum):
    """Type of symbol in the symbol table"""
    SUBROUTINE = "subroutine"
    DATA = "data"
    HARDWARE = "hardware"
    UNKNOWN = "unknown"


@dataclass
class Symbol:
    """Represents a symbol in the symbol table"""
    address: int
    symbol_type: SymbolType
    name: str = ""
    description: str = ""
    ref_count: int = 0
    call_count: int = 0
    read_count: int = 0
    write_count: int = 0
    size_bytes: Optional[int] = None


class SymbolTableGenerator:
    """Generate a comprehensive symbol table from detected features"""

    def __init__(self,
                 subroutines: Dict[int, 'SubroutineInfo'],
                 xrefs: Dict[int, List['Reference']],
                 sections: List['SectionInfo']):
        self.subroutines = subroutines
        self.xrefs = xrefs
        self.sections = sections
        self.symbols: Dict[int, Symbol] = {}

    def generate_symbol_table(self) -> Dict[int, Symbol]:
        """Main entry point: generate complete symbol table"""
        # Add subroutines
        self._add_subroutines()

        # Add data sections
        self._add_data_sections()

        # Add hardware registers (SID)
        self._add_hardware_registers()

        # Add referenced addresses that aren't classified yet
        self._add_unknown_references()

        # Count references for all symbols
        self._count_references()

        return self.symbols

    def _add_subroutines(self):
        """Add all detected subroutines to symbol table"""
        for addr, info in self.subroutines.items():
            self.symbols[addr] = Symbol(
                address=addr,
                symbol_type=SymbolType.SUBROUTINE,
                name=info.name if info.name else f"sub_{addr:04x}",
                description=info.purpose,
                size_bytes=info.end_address - addr if info.end_address else None
            )

    def _add_data_sections(self):
        """Add data sections to symbol table"""
        for section in self.sections:
            if section.section_type == SectionType.CODE or section.section_type == SectionType.UNKNOWN:
                continue

            addr = section.address
            if addr and addr not in self.symbols:
                # Determine description from section type
                desc = ""
                if section.section_type == SectionType.FREQUENCY_TABLE:
                    desc = "Note frequency lookup table"
                elif section.section_type == SectionType.WAVE_TABLE:
                    desc = "Waveform data table"
                elif section.section_type == SectionType.INSTRUMENT_TABLE:
                    desc = "Instrument definitions"
                elif section.section_type == SectionType.PULSE_TABLE:
                    desc = "Pulse width modulation table"
                elif section.section_type == SectionType.FILTER_TABLE:
                    desc = "Filter parameter table"
                elif section.section_type == SectionType.SEQUENCE_DATA:
                    desc = "Music sequence data"
                else:
                    desc = section.section_type.value.replace('_', ' ').title()

                self.symbols[addr] = Symbol(
                    address=addr,
                    symbol_type=SymbolType.DATA,
                    name=section.section_type.value.lower(),
                    description=desc,
                    size_bytes=section.size
                )

    def _add_hardware_registers(self):
        """Add SID hardware registers to symbol table"""
        # Add the main SID register range
        for addr, desc in SID_REGISTERS.items():
            if addr not in self.symbols:
                # Generate short name from description
                name = desc.lower().replace(' ', '_')
                self.symbols[addr] = Symbol(
                    address=addr,
                    symbol_type=SymbolType.HARDWARE,
                    name=name,
                    description=desc,
                    size_bytes=1
                )

    def _add_unknown_references(self):
        """Add referenced addresses that aren't classified yet"""
        for addr in self.xrefs.keys():
            if addr not in self.symbols:
                # Determine if this looks like zero page, stack, or other
                desc = ""
                if 0x0000 <= addr <= 0x00FF:
                    desc = "Zero page variable"
                elif 0x0100 <= addr <= 0x01FF:
                    desc = "Stack location"
                elif 0xD400 <= addr <= 0xD7FF:
                    desc = "I/O register"
                else:
                    desc = "Referenced address"

                self.symbols[addr] = Symbol(
                    address=addr,
                    symbol_type=SymbolType.UNKNOWN,
                    name=f"addr_{addr:04x}",
                    description=desc
                )

    def _count_references(self):
        """Count all types of references for each symbol"""
        from collections import defaultdict

        for addr, refs in self.xrefs.items():
            if addr not in self.symbols:
                continue

            symbol = self.symbols[addr]

            for ref in refs:
                symbol.ref_count += 1

                if ref.ref_type == ReferenceType.CALL:
                    symbol.call_count += 1
                elif ref.ref_type == ReferenceType.READ:
                    symbol.read_count += 1
                elif ref.ref_type == ReferenceType.WRITE:
                    symbol.write_count += 1
                elif ref.ref_type == ReferenceType.READ_MODIFY:
                    symbol.read_count += 1
                    symbol.write_count += 1


def format_symbol_table(symbols: Dict[int, Symbol],
                        max_entries: int = 0,
                        filter_type: Optional[SymbolType] = None) -> str:
    """
    Format the symbol table as a readable text table

    Args:
        symbols: Dictionary of address -> Symbol
        max_entries: Maximum entries to show (0 = show all)
        filter_type: Only show symbols of this type (None = show all)

    Returns:
        Formatted symbol table as string
    """
    if not symbols:
        return ""

    sep = "=" * 78

    # Filter symbols if requested
    filtered_symbols = symbols
    if filter_type:
        filtered_symbols = {addr: sym for addr, sym in symbols.items()
                          if sym.symbol_type == filter_type}

    # Sort by address
    sorted_symbols = sorted(filtered_symbols.items(), key=lambda x: x[0])

    # Limit entries if requested
    if max_entries > 0:
        sorted_symbols = sorted_symbols[:max_entries]

    # Build header
    output = f";{sep}\n"
    output += f"; SYMBOL TABLE\n"
    output += f";{sep}\n"
    output += ";\n"

    if filter_type:
        output += f"; Showing: {filter_type.value.upper()} symbols only\n"
    else:
        output += f"; Total Symbols: {len(filtered_symbols)}\n"

    # Count by type
    type_counts = {}
    for sym in symbols.values():
        type_counts[sym.symbol_type] = type_counts.get(sym.symbol_type, 0) + 1

    output += "; Breakdown: "
    output += ", ".join([f"{count} {stype.value}" for stype, count in sorted(type_counts.items(), key=lambda x: x[0].value)])
    output += "\n;\n"

    # Table header
    output += f"; {'Address':<10} {'Type':<12} {'Name':<24} {'Refs':<8} {'Description'}\n"
    output += f"; {'-'*10} {'-'*12} {'-'*24} {'-'*8} {'-'*20}\n"

    # Table rows
    for addr, symbol in sorted_symbols:
        addr_str = f"${addr:04X}"
        type_str = symbol.symbol_type.value.capitalize()
        name_str = symbol.name[:24] if symbol.name else "-"

        # Format reference counts
        refs_parts = []
        if symbol.call_count > 0:
            refs_parts.append(f"{symbol.call_count}c")
        if symbol.read_count > 0:
            refs_parts.append(f"{symbol.read_count}r")
        if symbol.write_count > 0:
            refs_parts.append(f"{symbol.write_count}w")

        refs_str = ",".join(refs_parts) if refs_parts else "-"

        desc_str = symbol.description[:40] if symbol.description else "-"

        output += f"; {addr_str:<10} {type_str:<12} {name_str:<24} {refs_str:<8} {desc_str}\n"

    output += f";{sep}\n"
    output += ";\n"

    # Add legend
    output += "; Legend:\n"
    output += ";   Refs: c=calls, r=reads, w=writes\n"
    output += ";   Types: subroutine, data, hardware, unknown\n"
    output += f";{sep}\n"
    output += ";\n"

    return output


# ==============================================================================
# Enhanced Register Usage Tracking
# ==============================================================================

@dataclass
class RegisterLifecycle:
    """Track the complete lifecycle of a register value"""
    register: str  # 'A', 'X', or 'Y'
    load_address: int
    load_instruction: str
    uses: List[int] = field(default_factory=list)  # Addresses where value is used
    modifications: List[int] = field(default_factory=list)  # Where modified (but not killed)
    death_address: Optional[int] = None  # Where value is overwritten/killed
    is_dead_code: bool = False  # True if loaded but never used before being killed


@dataclass
class RegisterState:
    """State of all registers at a specific instruction"""
    address: int
    a_live: bool = False  # A contains a value that will be used later
    x_live: bool = False  # X contains a value that will be used later
    y_live: bool = False  # Y contains a value that will be used later
    a_source: Optional[int] = None  # Address where current A value was set
    x_source: Optional[int] = None  # Address where current X value was set
    y_source: Optional[int] = None  # Address where current Y value was set


@dataclass
class RegisterDependency:
    """Track register dependencies for a single instruction"""
    address: int
    instruction: str
    reads_a: bool = False  # Instruction reads A
    reads_x: bool = False  # Instruction reads X
    reads_y: bool = False  # Instruction reads Y
    writes_a: bool = False  # Instruction writes A
    writes_x: bool = False  # Instruction writes X
    writes_y: bool = False  # Instruction writes Y
    depends_on_a: Optional[int] = None  # Address that produced current A value
    depends_on_x: Optional[int] = None  # Address that produced current X value
    depends_on_y: Optional[int] = None  # Address that produced current Y value


class EnhancedRegisterTracker:
    """Enhanced register usage analysis with detailed lifecycle tracking"""

    def __init__(self, lines: List[str], subroutines: Dict[int, 'SubroutineInfo']):
        self.lines = lines
        self.subroutines = subroutines
        self.lifecycles: Dict[str, List[RegisterLifecycle]] = {
            'A': [],
            'X': [],
            'Y': []
        }
        self.dependencies: Dict[int, RegisterDependency] = {}
        self.register_states: Dict[int, RegisterState] = {}
        self.dead_code: List[Tuple[int, str, str]] = []  # (address, register, reason)
        self.optimizations: List[str] = []

    def analyze_all(self) -> Tuple[
        Dict[str, List[RegisterLifecycle]],
        Dict[int, RegisterDependency],
        List[Tuple[int, str, str]],
        List[str]
    ]:
        """Main entry point: analyze all register usage"""
        # Analyze each subroutine
        for addr, info in self.subroutines.items():
            self._analyze_subroutine_registers(addr, info)

        # Detect dead code
        self._detect_dead_code()

        # Generate optimization suggestions
        self._suggest_optimizations()

        return self.lifecycles, self.dependencies, self.dead_code, self.optimizations

    def _analyze_subroutine_registers(self, start_addr: int, info: 'SubroutineInfo'):
        """Analyze register usage within a single subroutine"""
        # Find subroutine boundaries
        start_line = self._find_line_by_address(start_addr)
        if start_line is None:
            return

        end_line = self._find_rts_after(start_line)
        if end_line is None:
            end_line = min(start_line + 200, len(self.lines))

        # Track current state (where was each register last set?)
        current_a_source: Optional[int] = None
        current_x_source: Optional[int] = None
        current_y_source: Optional[int] = None

        # Active lifecycles (one per register, if any)
        active_lifecycle_a: Optional[RegisterLifecycle] = None
        active_lifecycle_x: Optional[RegisterLifecycle] = None
        active_lifecycle_y: Optional[RegisterLifecycle] = None

        # Analyze each instruction in the subroutine
        for i in range(start_line, end_line + 1):
            if i >= len(self.lines):
                break

            line = self.lines[i]
            addr = self._extract_address(line)
            if addr is None:
                continue

            # Determine what this instruction does to registers
            dep = self._analyze_instruction_registers(line, addr)
            if dep is None:
                continue

            # Track dependencies (what does this instruction depend on?)
            dep.depends_on_a = current_a_source if dep.reads_a else None
            dep.depends_on_x = current_x_source if dep.reads_x else None
            dep.depends_on_y = current_y_source if dep.reads_y else None

            self.dependencies[addr] = dep

            # Handle A register lifecycle
            if dep.reads_a and active_lifecycle_a:
                active_lifecycle_a.uses.append(addr)

            if dep.writes_a:
                # Kill previous lifecycle if any
                if active_lifecycle_a:
                    active_lifecycle_a.death_address = addr
                    self.lifecycles['A'].append(active_lifecycle_a)

                # Start new lifecycle
                active_lifecycle_a = RegisterLifecycle(
                    register='A',
                    load_address=addr,
                    load_instruction=line.strip()
                )
                current_a_source = addr

            # Handle X register lifecycle
            if dep.reads_x and active_lifecycle_x:
                active_lifecycle_x.uses.append(addr)

            if dep.writes_x:
                # Kill previous lifecycle if any
                if active_lifecycle_x:
                    active_lifecycle_x.death_address = addr
                    self.lifecycles['X'].append(active_lifecycle_x)

                # Start new lifecycle
                active_lifecycle_x = RegisterLifecycle(
                    register='X',
                    load_address=addr,
                    load_instruction=line.strip()
                )
                current_x_source = addr

            # Handle Y register lifecycle
            if dep.reads_y and active_lifecycle_y:
                active_lifecycle_y.uses.append(addr)

            if dep.writes_y:
                # Kill previous lifecycle if any
                if active_lifecycle_y:
                    active_lifecycle_y.death_address = addr
                    self.lifecycles['Y'].append(active_lifecycle_y)

                # Start new lifecycle
                active_lifecycle_y = RegisterLifecycle(
                    register='Y',
                    load_address=addr,
                    load_instruction=line.strip()
                )
                current_y_source = addr

        # Close any remaining lifecycles at subroutine end
        if active_lifecycle_a:
            active_lifecycle_a.death_address = info.end_address
            self.lifecycles['A'].append(active_lifecycle_a)

        if active_lifecycle_x:
            active_lifecycle_x.death_address = info.end_address
            self.lifecycles['X'].append(active_lifecycle_x)

        if active_lifecycle_y:
            active_lifecycle_y.death_address = info.end_address
            self.lifecycles['Y'].append(active_lifecycle_y)

    def _analyze_instruction_registers(self, line: str, addr: int) -> Optional[RegisterDependency]:
        """Analyze what registers an instruction reads/writes"""
        upper_line = line.upper()
        dep = RegisterDependency(address=addr, instruction=line.strip())

        # Instructions that read and write A
        if re.search(r'\bADC\b|\bSBC\b|\bAND\b|\bORA\b|\bEOR\b|\bASL\s*$|\bLSR\s*$|\bROL\s*$|\bROR\s*$', upper_line):
            dep.reads_a = True
            dep.writes_a = True

        # Instructions that only read A
        elif re.search(r'\bSTA\b|\bCMP\b', upper_line):
            dep.reads_a = True

        # Instructions that only write A
        elif re.search(r'\bLDA\b', upper_line):
            dep.writes_a = True

        # Transfer instructions affecting A
        elif re.search(r'\bTXA\b|\bTYA\b', upper_line):
            dep.reads_x = 'TXA' in upper_line
            dep.reads_y = 'TYA' in upper_line
            dep.writes_a = True
        elif re.search(r'\bTAX\b', upper_line):
            dep.reads_a = True
            dep.writes_x = True
        elif re.search(r'\bTAY\b', upper_line):
            dep.reads_a = True
            dep.writes_y = True

        # Instructions that read and write X
        if re.search(r'\bINX\b|\bDEX\b', upper_line):
            dep.reads_x = True
            dep.writes_x = True

        # Instructions that only read X
        elif re.search(r'\bSTX\b|\bCPX\b', upper_line):
            dep.reads_x = True

        # Instructions that only write X
        elif re.search(r'\bLDX\b', upper_line):
            dep.writes_x = True

        # Instructions that read and write Y
        if re.search(r'\bINY\b|\bDEY\b', upper_line):
            dep.reads_y = True
            dep.writes_y = True

        # Instructions that only read Y
        elif re.search(r'\bSTY\b|\bCPY\b', upper_line):
            dep.reads_y = True

        # Instructions that only write Y
        elif re.search(r'\bLDY\b', upper_line):
            dep.writes_y = True

        # Indexed addressing modes also read the index register
        if re.search(r',\s*X\b', upper_line):
            dep.reads_x = True
        if re.search(r',\s*Y\b', upper_line):
            dep.reads_y = True

        # Only return if this instruction does something with registers
        if dep.reads_a or dep.reads_x or dep.reads_y or dep.writes_a or dep.writes_x or dep.writes_y:
            return dep

        return None

    def _detect_dead_code(self):
        """Detect register loads that are never used (dead code)"""
        for reg_name, lifecycles in self.lifecycles.items():
            for lifecycle in lifecycles:
                # Dead code: loaded but never used before being killed
                if not lifecycle.uses and lifecycle.death_address is not None:
                    lifecycle.is_dead_code = True
                    reason = f"Value loaded at ${lifecycle.load_address:04X} but never used before overwritten at ${lifecycle.death_address:04X}"
                    self.dead_code.append((lifecycle.load_address, reg_name, reason))

    def _suggest_optimizations(self):
        """Generate optimization suggestions based on register usage patterns"""
        # Suggestion 1: Dead code elimination
        if self.dead_code:
            self.optimizations.append(
                f"Dead Code: Found {len(self.dead_code)} register load(s) that are never used. "
                f"Consider removing these instructions."
            )

        # Suggestion 2: Register reuse opportunities
        for reg_name, lifecycles in self.lifecycles.items():
            short_lives = [lc for lc in lifecycles if len(lc.uses) == 1]
            if len(short_lives) > 3:
                self.optimizations.append(
                    f"Register {reg_name}: Found {len(short_lives)} single-use loads. "
                    f"Consider caching values for reuse."
                )

        # Suggestion 3: Long dependency chains
        for addr, dep in self.dependencies.items():
            chain_length = 0
            current_addr = addr

            # Trace back dependency chain for A register
            if dep.depends_on_a:
                visited = set()
                while current_addr and current_addr not in visited:
                    visited.add(current_addr)
                    chain_length += 1
                    if current_addr in self.dependencies:
                        current_addr = self.dependencies[current_addr].depends_on_a
                    else:
                        break

                if chain_length > 5:
                    self.optimizations.append(
                        f"Long Dependency Chain: Instruction at ${addr:04X} has a dependency "
                        f"chain of {chain_length} steps. Consider breaking into smaller operations."
                    )

    def _extract_address(self, line: str) -> Optional[int]:
        """Extract address from a line"""
        # Try various address formats
        match = re.match(r'\s*\$?([0-9A-Fa-f]{4}):', line)
        if match:
            return int(match.group(1), 16)
        return None

    def _find_line_by_address(self, address: int) -> Optional[int]:
        """Find line number containing the given address"""
        # Support both uppercase and lowercase hex
        addr_upper = f'${address:04X}:'
        addr_lower = f'${address:04x}:'
        for i, line in enumerate(self.lines):
            stripped = line.strip()
            if stripped.startswith(addr_upper) or stripped.startswith(addr_lower) or \
               stripped.startswith(f'{address:04X}:') or stripped.startswith(f'{address:04x}:'):
                return i
        return None

    def _find_rts_after(self, start_line: int) -> Optional[int]:
        """Find the next RTS instruction after start_line"""
        rts_pattern = re.compile(r'\bRTS\b', re.IGNORECASE)
        for i in range(start_line, min(start_line + 200, len(self.lines))):
            if rts_pattern.search(self.lines[i]):
                return i
        return None


def format_register_analysis(
    lifecycles: Dict[str, List[RegisterLifecycle]],
    dependencies: Dict[int, RegisterDependency],
    dead_code: List[Tuple[int, str, str]],
    optimizations: List[str]
) -> str:
    """Format enhanced register analysis as readable output"""
    sep = "=" * 78
    output = f";{sep}\n"
    output += f"; ENHANCED REGISTER ANALYSIS\n"
    output += f";{sep}\n"
    output += ";\n"

    # Summary statistics
    total_lifecycles = sum(len(lc) for lc in lifecycles.values())
    total_dependencies = len(dependencies)

    output += f"; Total Register Lifecycles: {total_lifecycles}\n"
    output += f"; Total Dependencies Tracked: {total_dependencies}\n"
    output += f"; Dead Code Instances: {len(dead_code)}\n"
    output += ";\n"

    # Register lifecycles summary
    output += f"; Register Lifecycles by Register:\n"
    for reg_name in ['A', 'X', 'Y']:
        lifecycles_list = lifecycles[reg_name]
        output += f";   {reg_name}: {len(lifecycles_list)} lifecycle(s)\n"

        # Statistics
        if lifecycles_list:
            avg_uses = sum(len(lc.uses) for lc in lifecycles_list) / len(lifecycles_list)
            max_uses = max(len(lc.uses) for lc in lifecycles_list)
            dead_count = sum(1 for lc in lifecycles_list if lc.is_dead_code)

            output += f";      Average uses per load: {avg_uses:.1f}\n"
            output += f";      Maximum uses: {max_uses}\n"
            output += f";      Dead loads: {dead_count}\n"

    output += ";\n"

    # Dead code warnings
    if dead_code:
        output += f"; DEAD CODE WARNINGS\n"
        output += f"; {'-' * 76}\n"
        for addr, reg, reason in dead_code:
            output += f"; ${addr:04X} - Register {reg}: {reason}\n"
        output += ";\n"

    # Optimization suggestions
    if optimizations:
        output += f"; OPTIMIZATION SUGGESTIONS\n"
        output += f"; {'-' * 76}\n"
        for i, suggestion in enumerate(optimizations, 1):
            output += f"; {i}. {suggestion}\n"
        output += ";\n"

    # Detailed lifecycle table (show first 20)
    output += f"; REGISTER LIFECYCLE DETAILS (First 20)\n"
    output += f"; {'-' * 76}\n"
    output += f"; {'Reg':<3} {'Load@':<8} {'Uses':<6} {'Death@':<8} {'Status':<10} {'Instruction'}\n"

    all_lifecycles = []
    for reg_name, lc_list in lifecycles.items():
        for lc in lc_list:
            all_lifecycles.append((reg_name, lc))

    # Sort by load address
    all_lifecycles.sort(key=lambda x: x[1].load_address)

    for reg_name, lc in all_lifecycles[:20]:
        load_str = f"${lc.load_address:04X}"
        uses_str = str(len(lc.uses))
        death_str = f"${lc.death_address:04X}" if lc.death_address else "end"
        status_str = "DEAD" if lc.is_dead_code else "live"
        instr_str = lc.load_instruction[:40] if lc.load_instruction else ""

        output += f"; {reg_name:<3} {load_str:<8} {uses_str:<6} {death_str:<8} {status_str:<10} {instr_str}\n"

    if len(all_lifecycles) > 20:
        output += f"; ... ({len(all_lifecycles) - 20} more lifecycles not shown)\n"

    output += ";\n"
    output += f";{sep}\n"
    output += ";\n"

    return output


def find_documentation_for_address(address: int) -> Optional[dict]:
    """Find documentation links for a given memory address"""
    for (start, end), doc_info in DOCUMENTATION_MAP['addresses'].items():
        if start <= address <= end:
            return doc_info
    return None


def find_documentation_for_topic(topic: str) -> Optional[dict]:
    """Find documentation links for a given topic"""
    return DOCUMENTATION_MAP['topics'].get(topic.lower())


def format_documentation_link(doc_path: str, base_path: Path = None) -> str:
    """Format a documentation link (check if file exists)"""
    if base_path:
        full_path = base_path / doc_path
        if full_path.exists():
            return f"{doc_path} ✓"
        else:
            return f"{doc_path} (not found)"
    return doc_path


def generate_documentation_references(address: int, player_type: str = None) -> List[str]:
    """Generate documentation reference lines for an address"""
    refs = []

    # Check for address-specific documentation
    doc_info = find_documentation_for_address(address)
    if doc_info:
        refs.append(f"; See also: {doc_info['title']}")
        for doc in doc_info['docs'][:2]:  # Limit to 2 most relevant
            refs.append(f";   - {doc}")

    # Check for player-type documentation
    if player_type:
        topic_info = find_documentation_for_topic(player_type)
        if topic_info and not doc_info:  # Only if we don't already have address docs
            refs.append(f"; See also: {topic_info['title']}")
            for doc in topic_info['docs'][:2]:
                refs.append(f";   - {doc}")

    return refs


def create_reverse_documentation_index(symbols: Dict[int, 'Symbol'],
                                       file_info: dict = None) -> Dict[str, List[int]]:
    """Create reverse index: documentation file -> addresses that reference it"""
    index = {}

    # Scan all symbols for addresses that have documentation
    for addr, symbol in symbols.items():
        doc_info = find_documentation_for_address(addr)
        if doc_info:
            for doc in doc_info['docs']:
                if doc not in index:
                    index[doc] = []
                index[doc].append(addr)

    return index


def format_documentation_section(reverse_index: Dict[str, List[int]]) -> str:
    """Format documentation cross-reference section"""
    if not reverse_index:
        return ""

    output = []
    output.append(";==============================================================================")
    output.append("; DOCUMENTATION CROSS-REFERENCES")
    output.append(";==============================================================================")
    output.append(";")
    output.append("; This section shows which documentation files are relevant to this code.")
    output.append(";")

    for doc_path in sorted(reverse_index.keys()):
        addresses = reverse_index[doc_path]
        output.append(f"; {doc_path}")

        # Show first 5 addresses
        addr_strs = [f"${a:04X}" for a in sorted(addresses)[:5]]
        addr_list = ", ".join(addr_strs)
        if len(addresses) > 5:
            output.append(f";   Referenced by {len(addresses)} address(es): {addr_list}, ... ({len(addresses) - 5} more)")
        else:
            output.append(f";   Referenced by {len(addresses)} address(es): {addr_list}")
        output.append(";")

    output.append(";==============================================================================")
    output.append("")

    return "\n".join(output)


def create_header(filename: str, info: dict) -> str:
    """Create comprehensive header for ASM file"""
    sep = ";" + "=" * 78
    header = f"""{sep}
; {filename}
; Annotated 6502 Assembly Disassembly
{sep}
;
"""

    if info.get('title'):
        header += f"; TITLE: {info['title']}\n"
    if info.get('author'):
        header += f"; AUTHOR: {info['author']}\n"
    if info.get('copyright'):
        header += f"; COPYRIGHT: {info['copyright']}\n"
    if info.get('player'):
        header += f"; PLAYER: {info['player']}\n"
    if info.get('load_address'):
        header += f"; LOAD ADDRESS: ${info['load_address']:04X}\n"
    if info.get('init_address'):
        header += f"; INIT ADDRESS: ${info['init_address']:04X}\n"
    if info.get('play_address'):
        header += f"; PLAY ADDRESS: ${info['play_address']:04X}\n"

    header += f""";
{sep}
; MEMORY MAP
{sep}
"""

    # Add Laxity table addresses if this is a Laxity file
    if info.get('player') and 'Laxity' in info['player']:
        header += """;
; LAXITY NEWPLAYER V21 TABLE ADDRESSES (Verified):
; $18DA   Wave Table - Waveforms (32 bytes)
; $190C   Wave Table - Note Offsets (32 bytes)
; $1837   Pulse Table (4-byte entries)
; $1A1E   Filter Table (4-byte entries)
; $1A6B   Instrument Table (8×8 bytes, column-major)
; $199F   Sequence Pointers (3 voices × 2 bytes)
;
"""

    header += f"""{sep}
; SID REGISTER REFERENCE
{sep}
; $D400-$D406   Voice 1 (Frequency, Pulse, Control, ADSR)
; $D407-$D40D   Voice 2 (Frequency, Pulse, Control, ADSR)
; $D40E-$D414   Voice 3 (Frequency, Pulse, Control, ADSR)
; $D415-$D416   Filter Cutoff (11-bit)
; $D417         Filter Resonance/Routing
; $D418         Volume/Filter Mode
;
{sep}
; CODE
{sep}

"""
    return header


def parse_address(addr_str: str) -> Optional[int]:
    """Parse address string to integer"""
    try:
        if addr_str.startswith('$'):
            return int(addr_str[1:], 16)
        elif addr_str.startswith('0x'):
            return int(addr_str, 16)
        else:
            return int(addr_str)
    except:
        return None


def annotate_line(line: str) -> str:
    """Add inline annotation to a line if possible"""
    # Skip already commented lines
    if line.strip().startswith(';'):
        return line

    # Look for SID register accesses
    for addr, desc in SID_REGISTERS.items():
        if f'${addr:04X}' in line.upper() or f'$D{addr & 0xFF:02X}' in line.upper():
            if ';' not in line:
                line = line.rstrip() + f'  ; {desc}\n'
            break

    # Look for Laxity table accesses
    for addr, desc in LAXITY_TABLES.items():
        if f'${addr:04X}' in line.upper():
            if '; Wave Table' not in line and '; Pulse Table' not in line:
                if ';' not in line:
                    line = line.rstrip() + f'  ; {desc}\n'
            break

    # Look for known opcodes
    for opcode, desc in OPCODES.items():
        if line.strip().upper().startswith(opcode):
            # Don't add if already has detailed comment
            if ';' not in line or line.count(';') < 2:
                parts = line.split(';', 1)
                code_part = parts[0].rstrip()
                comment_part = parts[1] if len(parts) > 1 else ''
                if not comment_part:
                    line = code_part + f'  ; {desc}\n'
            break

    return line


def extract_info_from_sidwinder(content: str) -> dict:
    """Extract file info from SIDwinder-generated header"""
    info = {}

    # Look for SIDwinder header
    for line in content.split('\n')[:20]:
        if 'Name:' in line:
            info['title'] = line.split('Name:', 1)[1].strip()
        elif 'Author:' in line:
            info['author'] = line.split('Author:', 1)[1].strip()
        elif 'Copyright:' in line:
            info['copyright'] = line.split('Copyright:', 1)[1].strip()
        elif 'SIDLoad' in line:
            match = re.search(r'\$([0-9A-Fa-f]+)', line)
            if match:
                info['load_address'] = int(match.group(1), 16)

    return info


def annotate_asm_file(input_path: Path, output_path: Path, file_info: dict = None, output_format: str = 'text'):
    """Annotate an ASM file with comprehensive comments

    Args:
        input_path: Path to input ASM file
        output_path: Path to output file
        file_info: Optional file metadata dict
        output_format: Output format - 'text' (default), 'json', or 'markdown'
    """

    print(f"Annotating: {input_path.name}")

    # Read original file
    with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Extract info if not provided
    if not file_info:
        file_info = extract_info_from_sidwinder(content)

    # Detect if this is a Laxity file
    if 'Laxity' in content or 'laxity' in str(input_path).lower():
        file_info['player'] = 'Laxity NewPlayer v21'

    # Detect subroutines
    print(f"  Detecting subroutines...")
    sub_detector = SubroutineDetector(content)
    subroutines = sub_detector.detect_all_subroutines()
    print(f"  Found {len(subroutines)} subroutine(s)")

    # Detect sections (data vs code)
    print(f"  Detecting sections...")
    lines = content.split('\n')
    section_detector = SectionDetector(lines, subroutines)
    sections = section_detector.detect_sections()
    data_sections = [s for s in sections if s.section_type != SectionType.CODE and s.section_type != SectionType.UNKNOWN]
    print(f"  Found {len(data_sections)} data section(s)")

    # Generate cross-references
    print(f"  Generating cross-references...")
    xref_detector = CrossReferenceDetector(lines, subroutines)
    xrefs = xref_detector.generate_cross_references()
    total_refs = sum(len(refs) for refs in xrefs.values())
    print(f"  Found {total_refs} reference(s) to {len(xrefs)} address(es)")

    # Detect code patterns
    print(f"  Detecting code patterns...")
    pattern_detector = PatternDetector(lines)
    patterns = pattern_detector.detect_all_patterns()
    print(f"  Found {len(patterns)} code pattern(s)")

    # Count CPU cycles
    print(f"  Counting CPU cycles...")
    cycle_counter = CycleCounter(lines, subroutines)
    cycle_counts = cycle_counter.count_all_cycles()
    print(f"  Counted cycles for {len(cycle_counts)} instruction(s)")

    # Analyze control flow
    print(f"  Analyzing control flow...")
    flow_analyzer = ControlFlowAnalyzer(lines, subroutines, cycle_counter)
    call_graph, loops, branches = flow_analyzer.analyze_all()
    print(f"  Found {len(loops)} loop(s), {len(branches)} branch(es)")

    # Generate symbol table
    print(f"  Generating symbol table...")
    symbol_generator = SymbolTableGenerator(subroutines, xrefs, sections)
    symbols = symbol_generator.generate_symbol_table()
    print(f"  Found {len(symbols)} symbol(s)")

    # Analyze enhanced register usage
    print(f"  Analyzing enhanced register usage...")
    register_tracker = EnhancedRegisterTracker(lines, subroutines)
    lifecycles, dependencies, dead_code, optimizations = register_tracker.analyze_all()
    total_lifecycles = sum(len(lc) for lc in lifecycles.values())
    print(f"  Tracked {total_lifecycles} register lifecycle(s), {len(dead_code)} dead code instance(s)")

    # Create annotated version
    output_lines = []

    # Add comprehensive header
    output_lines.append(create_header(input_path.name, file_info))

    # Add symbol table
    symbol_table = format_symbol_table(symbols)
    if symbol_table:
        output_lines.append(symbol_table)

    # Add call graph
    call_graph_output = format_call_graph(call_graph, subroutines)
    if call_graph_output:
        output_lines.append(call_graph_output)

    # Add loop analysis
    loop_analysis = format_loop_analysis(loops)
    if loop_analysis:
        output_lines.append(loop_analysis)

    # Add enhanced register analysis
    register_analysis = format_register_analysis(lifecycles, dependencies, dead_code, optimizations)
    if register_analysis:
        output_lines.append(register_analysis)

    # Add documentation cross-references
    reverse_doc_index = create_reverse_documentation_index(symbols, file_info)
    doc_section = format_documentation_section(reverse_doc_index)
    if doc_section:
        output_lines.append(doc_section)

    # Build a mapping of line numbers to subroutine addresses
    line_to_subroutine = {}
    for addr, info in subroutines.items():
        line_num = sub_detector._find_line_by_address(addr)
        if line_num is not None:
            line_to_subroutine[line_num] = addr

    # Build a mapping of line numbers to data sections
    line_to_section = {}
    for section in data_sections:
        line_to_section[section.start_line] = section

    # Build a mapping of line numbers to patterns
    line_to_pattern = {}
    for pattern in patterns:
        line_to_pattern[pattern.start_line] = pattern

    # Process each line, inserting subroutine and section headers
    in_header = True

    for i, line in enumerate(lines):
        # Skip original SIDwinder header (first 10 lines)
        if in_header and line.startswith('//;'):
            continue
        elif in_header and not line.strip().startswith('//;'):
            in_header = False

        # Check if this line starts a data section
        if i in line_to_section:
            section = line_to_section[i]
            section_header = format_data_section(section, lines, xrefs, subroutines)
            output_lines.append(section_header)

        # Check if this line starts a subroutine (by line number)
        if i in line_to_subroutine:
            sub_addr = line_to_subroutine[i]
            sub_header = generate_subroutine_header(subroutines[sub_addr], xrefs, subroutines, cycle_counter)
            output_lines.append(sub_header)

        # Check if this line starts a code pattern
        if i in line_to_pattern:
            pattern = line_to_pattern[i]
            pattern_header = format_pattern_header(pattern)
            output_lines.append(pattern_header)

        # Check if this line references a documented address
        line_addr = _extract_line_address(line)
        if line_addr:
            doc_refs = generate_documentation_references(line_addr, file_info.get('player'))
            if doc_refs:
                for ref in doc_refs:
                    output_lines.append(ref)

        # Annotate the line
        annotated = annotate_line(line)
        output_lines.append(annotated)

    # Export in requested format
    if output_format == 'json':
        # Export comprehensive analysis data to JSON
        json_output = export_to_json(
            file_info, subroutines, sections, xrefs, patterns, symbols,
            cycle_counts, call_graph, loops, branches, lifecycles,
            dependencies, dead_code, optimizations
        )
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"  Created JSON: {output_path.name}")

    elif output_format == 'markdown':
        # Export analysis summary to Markdown
        md_output = export_to_markdown(
            input_path, file_info, subroutines, sections, symbols,
            patterns, loops, dead_code, optimizations
        )
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_output)
        print(f"  Created Markdown: {output_path.name}")

    elif output_format == 'html':
        # Export interactive HTML
        if not HTML_EXPORT_AVAILABLE:
            print("  WARNING: HTML export module not available, falling back to text format")
            output_format = 'text'
        else:
            html_output = generate_html_export(
                input_path, file_info, subroutines, sections, symbols,
                xrefs, patterns, loops, branches, cycle_counts, call_graph,
                lifecycles, dependencies, dead_code, optimizations, lines
            )
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_output)
            print(f"  Created HTML: {output_path.name}")
            return

    elif output_format == 'csv':
        # Export to CSV format (diff-friendly)
        csv_output = export_to_csv(
            input_path, file_info, subroutines, symbols, xrefs,
            patterns, loops, cycle_counts, lifecycles, dead_code, lines
        )
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            f.write(csv_output)
        print(f"  Created CSV: {output_path.name}")
        return

    elif output_format == 'tsv':
        # Export to TSV format (tab-separated, diff-friendly)
        tsv_output = export_to_tsv(
            input_path, file_info, subroutines, symbols, xrefs,
            patterns, loops, cycle_counts, lifecycles, dead_code, lines
        )
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(tsv_output)
        print(f"  Created TSV: {output_path.name}")
        return

    if output_format == 'text':
        # Default: Write annotated text file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(output_lines))
        print(f"  Created: {output_path.name}")


def _extract_line_address(line: str) -> Optional[int]:
    """Extract address from the start of a line if present"""
    # Match patterns like: $1000:, 1000:, etc.
    match = re.match(r'^\s*\$?([0-9A-Fa-f]{4}):', line)
    if match:
        return int(match.group(1), 16)

    # Check if this is a label, search for address in nearby comment
    # Pattern: label_name:
    if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*:\s*$', line.strip()):
        # This is a label, but we don't know its address yet
        # Will be handled by the subroutine detector finding the label
        return None

    return None


# ==============================================================================
# Export Formats (JSON, Markdown, HTML)
# ==============================================================================

def export_to_json(
    file_info: dict,
    subroutines: Dict[int, 'SubroutineInfo'],
    sections: List['SectionInfo'],
    xrefs: Dict[int, List['Reference']],
    patterns: List['Pattern'],
    symbols: Dict[int, 'Symbol'],
    cycle_counts: Dict[int, 'CycleInfo'],
    call_graph: Dict[int, 'CallGraphNode'],
    loops: List['LoopInfo'],
    branches: List['BranchInfo'],
    lifecycles: Dict[str, List['RegisterLifecycle']],
    dependencies: Dict[int, 'RegisterDependency'],
    dead_code: List[Tuple[int, str, str]],
    optimizations: List[str]
) -> str:
    """Export all analysis data to JSON format"""

    # Convert dataclasses to dictionaries
    def to_dict(obj):
        """Convert dataclass to dict, handling nested structures"""
        if hasattr(obj, '__dataclass_fields__'):
            result = {}
            for field_name, field_value in asdict(obj).items():
                if isinstance(field_value, list):
                    result[field_name] = [to_dict(item) if hasattr(item, '__dataclass_fields__') else item
                                         for item in field_value]
                elif hasattr(field_value, '__dataclass_fields__'):
                    result[field_name] = to_dict(field_value)
                elif hasattr(field_value, 'value'):  # Enum
                    result[field_name] = field_value.value
                else:
                    result[field_name] = field_value
            return result
        return obj

    # Build JSON structure
    data = {
        "metadata": file_info,
        "statistics": {
            "subroutines": len(subroutines),
            "data_sections": len([s for s in sections if s.section_type.value != 'CODE']),
            "cross_references": sum(len(refs) for refs in xrefs.values()),
            "patterns": len(patterns),
            "symbols": len(symbols),
            "instructions_analyzed": len(cycle_counts),
            "loops": len(loops),
            "branches": len(branches),
            "register_lifecycles": sum(len(lc) for lc in lifecycles.values()),
            "dead_code_instances": len(dead_code)
        },
        "subroutines": {
            f"${addr:04X}": {
                "address": addr,
                "end_address": info.end_address,
                "name": info.name,
                "purpose": info.purpose,
                "calls": [f"${c:04X}" for c in info.calls],
                "called_by": [f"${c:04X}" for c in info.called_by],
                "accesses_sid": info.accesses_sid,
                "accesses_tables": info.accesses_tables,
                "register_usage": {
                    "a_input": info.register_usage.a_input,
                    "x_input": info.register_usage.x_input,
                    "y_input": info.register_usage.y_input,
                    "a_output": info.register_usage.a_output,
                    "x_output": info.register_usage.x_output,
                    "y_output": info.register_usage.y_output,
                    "a_modified": info.register_usage.a_modified,
                    "x_modified": info.register_usage.x_modified,
                    "y_modified": info.register_usage.y_modified
                }
            }
            for addr, info in subroutines.items()
        },
        "data_sections": [
            {
                "start_address": f"${s.start_address:04X}" if s.start_address else None,
                "end_address": f"${s.end_address:04X}" if s.end_address else None,
                "section_type": s.section_type.value,
                "start_line": s.start_line,
                "end_line": s.end_line,
                "size": s.size,
                "name": s.name
            }
            for s in sections if s.section_type.value != 'CODE'
        ],
        "cross_references": {
            f"${addr:04X}": [
                {
                    "source_address": f"${ref.source_address:04X}" if ref.source_address else None,
                    "source_line": ref.source_line,
                    "ref_type": ref.ref_type.value,
                    "instruction": ref.instruction
                }
                for ref in refs
            ]
            for addr, refs in xrefs.items()
        },
        "patterns": [
            {
                "type": p.pattern_type.value,
                "start_line": p.start_line,
                "end_line": p.end_line,
                "description": p.description,
                "variables": p.variables,
                "result": p.result
            }
            for p in patterns
        ],
        "symbols": {
            f"${addr:04X}": {
                "address": addr,
                "type": sym.symbol_type.value,
                "name": sym.name,
                "description": sym.description,
                "ref_count": sym.ref_count,
                "call_count": sym.call_count,
                "read_count": sym.read_count,
                "write_count": sym.write_count,
                "size_bytes": sym.size_bytes
            }
            for addr, sym in symbols.items()
        },
        "cycles": {
            f"${addr:04X}": {
                "min": info.min_cycles,
                "max": info.max_cycles,
                "typical": info.typical_cycles,
                "notes": info.notes
            }
            for addr, info in cycle_counts.items()
        },
        "call_graph": {
            f"${addr:04X}": {
                "name": node.name,
                "calls": [f"${c:04X}" for c in node.calls],
                "called_by": [f"${c:04X}" for c in node.called_by],
                "cycles_min": node.cycles_min,
                "cycles_max": node.cycles_max,
                "cycles_typical": node.cycles_typical
            }
            for addr, node in call_graph.items()
        },
        "loops": [
            {
                "start_address": f"${loop.start_address:04X}",
                "end_address": f"${loop.end_address:04X}",
                "type": loop.loop_type,
                "counter_register": loop.counter_register,
                "iterations_min": loop.iterations_min,
                "iterations_max": loop.iterations_max,
                "iterations_typical": loop.iterations_typical,
                "cycles_per_iteration": loop.cycles_per_iteration,
                "description": loop.description
            }
            for loop in loops
        ],
        "branches": [
            {
                "address": f"${branch.address:04X}",
                "opcode": branch.opcode,
                "target": f"${branch.target:04X}",
                "is_backward": branch.is_backward,
                "is_forward": branch.is_forward
            }
            for branch in branches
        ],
        "register_lifecycles": {
            reg: [
                {
                    "load_address": f"${lc.load_address:04X}",
                    "load_instruction": lc.load_instruction,
                    "uses": [f"${addr:04X}" for addr in lc.uses],
                    "death_address": f"${lc.death_address:04X}" if lc.death_address else None,
                    "is_dead_code": lc.is_dead_code
                }
                for lc in lifecycles_list
            ]
            for reg, lifecycles_list in lifecycles.items()
        },
        "dependencies": {
            f"${addr:04X}": {
                "instruction": dep.instruction,
                "reads_a": dep.reads_a,
                "reads_x": dep.reads_x,
                "reads_y": dep.reads_y,
                "writes_a": dep.writes_a,
                "writes_x": dep.writes_x,
                "writes_y": dep.writes_y,
                "depends_on_a": f"${dep.depends_on_a:04X}" if dep.depends_on_a else None,
                "depends_on_x": f"${dep.depends_on_x:04X}" if dep.depends_on_x else None,
                "depends_on_y": f"${dep.depends_on_y:04X}" if dep.depends_on_y else None
            }
            for addr, dep in dependencies.items()
        },
        "dead_code": [
            {
                "address": f"${addr:04X}",
                "register": reg,
                "reason": reason
            }
            for addr, reg, reason in dead_code
        ],
        "optimizations": optimizations
    }

    return json.dumps(data, indent=2)


def export_to_markdown(
    input_path: Path,
    file_info: dict,
    subroutines: Dict[int, 'SubroutineInfo'],
    sections: List['SectionInfo'],
    symbols: Dict[int, 'Symbol'],
    patterns: List['Pattern'],
    loops: List['LoopInfo'],
    dead_code: List[Tuple[int, str, str]],
    optimizations: List[str]
) -> str:
    """Export annotated assembly to Markdown format"""

    md = []

    # Header
    md.append(f"# {input_path.name} - Assembly Analysis\n")
    md.append(f"**Auto-generated by ASM Annotation System**\n")

    if file_info.get('title'):
        md.append(f"- **Title**: {file_info['title']}")
    if file_info.get('author'):
        md.append(f"- **Author**: {file_info['author']}")
    if file_info.get('player'):
        md.append(f"- **Player**: {file_info['player']}")

    md.append("\n---\n")

    # Statistics
    md.append("## Statistics\n")
    md.append(f"- **Subroutines**: {len(subroutines)}")
    md.append(f"- **Data Sections**: {len([s for s in sections if s.section_type.value != 'CODE'])}")
    md.append(f"- **Symbols**: {len(symbols)}")
    md.append(f"- **Patterns**: {len(patterns)}")
    md.append(f"- **Loops**: {len(loops)}")
    md.append(f"- **Dead Code**: {len(dead_code)} instances")
    md.append("\n---\n")

    # Subroutines
    if subroutines:
        md.append("## Subroutines\n")
        for addr, info in sorted(subroutines.items()):
            md.append(f"### {info.name or f'sub_{addr:04x}'} (`${addr:04X}`)\n")
            if info.purpose:
                md.append(f"**Purpose**: {info.purpose}\n")
            if info.calls:
                calls_str = ", ".join([f"`${c:04X}`" for c in info.calls])
                md.append(f"**Calls**: {calls_str}\n")
            if info.called_by:
                callers_str = ", ".join([f"`${c:04X}`" for c in info.called_by])
                md.append(f"**Called by**: {callers_str}\n")

            # Register usage
            inputs = []
            outputs = []
            if info.register_usage.a_input:
                inputs.append("A")
            if info.register_usage.x_input:
                inputs.append("X")
            if info.register_usage.y_input:
                inputs.append("Y")
            if info.register_usage.a_output:
                outputs.append("A")
            if info.register_usage.x_output:
                outputs.append("X")
            if info.register_usage.y_output:
                outputs.append("Y")

            if inputs:
                md.append(f"**Inputs**: {', '.join(inputs)}\n")
            if outputs:
                md.append(f"**Outputs**: {', '.join(outputs)}\n")

            md.append("")
        md.append("\n---\n")

    # Symbols
    if symbols:
        md.append("## Symbol Table\n")
        md.append("| Address | Type | Name | Refs | Description |")
        md.append("|---------|------|------|------|-------------|")
        for addr, sym in sorted(symbols.items())[:50]:  # Limit to 50
            addr_str = f"`${addr:04X}`"
            type_str = sym.symbol_type.value
            name_str = sym.name or "-"

            # Format refs
            refs_parts = []
            if sym.call_count > 0:
                refs_parts.append(f"{sym.call_count}c")
            if sym.read_count > 0:
                refs_parts.append(f"{sym.read_count}r")
            if sym.write_count > 0:
                refs_parts.append(f"{sym.write_count}w")
            refs_str = ",".join(refs_parts) if refs_parts else "-"

            desc_str = sym.description[:40] if sym.description else "-"

            md.append(f"| {addr_str} | {type_str} | {name_str} | {refs_str} | {desc_str} |")

        if len(symbols) > 50:
            md.append(f"\n*({len(symbols) - 50} more symbols not shown)*\n")
        md.append("\n---\n")

    # Loops
    if loops:
        md.append("## Loop Analysis\n")
        for i, loop in enumerate(loops[:20], 1):  # Show first 20
            md.append(f"### Loop #{i}: `${loop.start_address:04X}` - `${loop.end_address:04X}`\n")
            md.append(f"- **Type**: {loop.loop_type}")
            if loop.counter_register:
                md.append(f"- **Counter**: Register {loop.counter_register}")
            md.append(f"- **Iterations**: {loop.iterations_min}-{loop.iterations_max} (typically {loop.iterations_typical})")
            md.append(f"- **Cycles/iteration**: {loop.cycles_per_iteration}")
            total_cycles = loop.cycles_per_iteration * loop.iterations_typical
            md.append(f"- **Total cycles**: {total_cycles} ({total_cycles * 100 // NTSC_CYCLES_PER_FRAME:.1f}% of frame)")
            md.append("")

        if len(loops) > 20:
            md.append(f"\n*({len(loops) - 20} more loops not shown)*\n")
        md.append("\n---\n")

    # Dead code
    if dead_code:
        md.append("## Dead Code Warnings\n")
        for addr, reg, reason in dead_code:
            md.append(f"- **`${addr:04X}`** - Register {reg}: {reason}")
        md.append("\n---\n")

    # Optimizations
    if optimizations:
        md.append("## Optimization Suggestions\n")
        for i, opt in enumerate(optimizations, 1):
            md.append(f"{i}. {opt}")
        md.append("\n---\n")

    md.append("\n*Generated by ASM Annotation System*")

    return "\n".join(md)


def export_to_csv(
    input_path: Path,
    file_info: dict,
    subroutines: Dict[int, 'SubroutineInfo'],
    symbols: Dict[int, 'Symbol'],
    xrefs: Dict[int, List['Reference']],
    patterns: List['Pattern'],
    loops: List['LoopInfo'],
    cycle_counts: Dict[int, 'CycleInfo'],
    lifecycles: Dict[str, List['RegisterLifecycle']],
    dead_code: List[Tuple[int, str, str]],
    lines: List[str]
) -> str:
    """Export assembly analysis to CSV format (diff-friendly)"""
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([
        'Address',
        'Type',
        'Opcode',
        'Operand',
        'Cycles_Min',
        'Cycles_Max',
        'Description',
        'Reads',
        'Writes',
        'Calls',
        'In_Loop',
        'In_Subroutine',
        'Dead_Code',
        'Pattern'
    ])

    # Build lookup maps
    addr_to_subroutine = {}
    for addr, info in subroutines.items():
        # Map all addresses in subroutine range
        if info.end_address:
            for a in range(addr, info.end_address + 1):
                addr_to_subroutine[a] = info.name or f"sub_{addr:04x}"

    addr_to_loop = {}
    for loop in loops:
        for a in range(loop.start_address, loop.end_address + 1):
            addr_to_loop[a] = True

    dead_code_addrs = {addr for addr, _, _ in dead_code}

    # Parse each line
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(';'):
            continue

        # Try to extract address and instruction
        if ':' in stripped:
            parts = stripped.split(':', 1)
            try:
                addr = int(parts[0].strip().replace('$', ''), 16)
            except ValueError:
                continue

            # Get symbol type
            symbol_type = symbols[addr].symbol_type.value if addr in symbols else 'CODE'

            # Parse instruction
            instruction_part = parts[1].strip() if len(parts) > 1 else ''
            opcode = ''
            operand = ''
            description = ''

            if instruction_part:
                # Split on comment
                if ';' in instruction_part:
                    inst, desc = instruction_part.split(';', 1)
                    description = desc.strip()
                else:
                    inst = instruction_part

                # Parse opcode and operand
                inst_parts = inst.strip().split(None, 1)
                if inst_parts:
                    opcode = inst_parts[0]
                    operand = inst_parts[1] if len(inst_parts) > 1 else ''

            # Get cycle counts
            cycles_min = cycle_counts[addr].min_cycles if addr in cycle_counts else ''
            cycles_max = cycle_counts[addr].max_cycles if addr in cycle_counts else ''

            # Get reads/writes from symbols
            reads = ''
            writes = ''
            calls = ''
            if addr in symbols:
                sym = symbols[addr]
                if sym.read_count > 0:
                    reads = f"{sym.read_count}r"
                if sym.write_count > 0:
                    writes = f"{sym.write_count}w"
                if sym.call_count > 0:
                    calls = f"{sym.call_count}c"

            # Check if in loop
            in_loop = 'YES' if addr in addr_to_loop else 'NO'

            # Check which subroutine
            in_subroutine = addr_to_subroutine.get(addr, '')

            # Check if dead code
            is_dead_code = 'YES' if addr in dead_code_addrs else 'NO'

            # Check for patterns
            pattern_match = ''
            for pattern in patterns:
                if hasattr(pattern, 'start_address') and pattern.start_address == addr:
                    pattern_match = pattern.pattern_type.value
                    break

            # Write row
            writer.writerow([
                f"${addr:04X}",
                symbol_type,
                opcode,
                operand,
                cycles_min,
                cycles_max,
                description,
                reads,
                writes,
                calls,
                in_loop,
                in_subroutine,
                is_dead_code,
                pattern_match
            ])

    return output.getvalue()


def export_to_tsv(
    input_path: Path,
    file_info: dict,
    subroutines: Dict[int, 'SubroutineInfo'],
    symbols: Dict[int, 'Symbol'],
    xrefs: Dict[int, List['Reference']],
    patterns: List['Pattern'],
    loops: List['LoopInfo'],
    cycle_counts: Dict[int, 'CycleInfo'],
    lifecycles: Dict[str, List['RegisterLifecycle']],
    dead_code: List[Tuple[int, str, str]],
    lines: List[str]
) -> str:
    """Export assembly analysis to TSV format (tab-separated, diff-friendly)"""
    # Use same logic as CSV but with tab delimiter
    csv_output = export_to_csv(
        input_path, file_info, subroutines, symbols, xrefs,
        patterns, loops, cycle_counts, lifecycles, dead_code, lines
    )

    # Convert CSV to TSV
    lines_out = []
    for line in csv_output.splitlines():
        # Simple CSV to TSV conversion (assumes no commas in quoted fields for now)
        # For proper conversion, we'd need to parse CSV properly
        import csv
        from io import StringIO
        reader = csv.reader(StringIO(line))
        for row in reader:
            lines_out.append('\t'.join(row))

    return '\n'.join(lines_out)


def main():
    if len(sys.argv) < 2:
        print("Usage: python annotate_asm.py <input.asm> [output] [--format FORMAT]")
        print("   or: python annotate_asm.py <directory> [--format FORMAT]")
        print("")
        print("Formats:")
        print("  text     - Annotated ASM text (default)")
        print("  json     - Machine-readable JSON with all analysis data")
        print("  markdown - Human-readable Markdown summary")
        print("  html     - Interactive HTML with collapsible sections, search, syntax highlighting")
        print("  csv      - Comma-separated values (diff-friendly, version control)")
        print("  tsv      - Tab-separated values (diff-friendly, version control)")
        print("")
        print("Examples:")
        print("  python annotate_asm.py input.asm                           # Text output")
        print("  python annotate_asm.py input.asm output.json --format json")
        print("  python annotate_asm.py input.asm output.md --format markdown")
        print("  python annotate_asm.py input.asm output.html --format html")
        print("  python annotate_asm.py input.asm output.csv --format csv   # Diff-friendly")
        print("  python annotate_asm.py input.asm output.tsv --format tsv   # Tab-separated")
        return 1

    # Parse arguments
    input_path = Path(sys.argv[1])
    output_format = 'text'  # default
    output_path = None

    # Check for --format argument
    if '--format' in sys.argv:
        format_index = sys.argv.index('--format')
        if format_index + 1 < len(sys.argv):
            output_format = sys.argv[format_index + 1]
            if output_format not in ['text', 'json', 'markdown', 'html', 'csv', 'tsv']:
                print(f"Error: Invalid format '{output_format}'. Use: text, json, markdown, html, csv, or tsv")
                return 1

    # Determine output path
    if len(sys.argv) > 2 and not sys.argv[2].startswith('--'):
        output_path = Path(sys.argv[2])

    if input_path.is_dir():
        # Process all ASM files in directory
        for asm_file in input_path.glob('**/*.asm'):
            if '_ANNOTATED' not in asm_file.name:
                # Determine extension based on format
                if output_format == 'json':
                    ext = '.json'
                elif output_format == 'markdown':
                    ext = '.md'
                elif output_format == 'html':
                    ext = '.html'
                elif output_format == 'csv':
                    ext = '.csv'
                elif output_format == 'tsv':
                    ext = '.tsv'
                else:
                    ext = '.asm'

                output_file = asm_file.parent / f"{asm_file.stem}_ANNOTATED{ext}"
                annotate_asm_file(asm_file, output_file, output_format=output_format)
    else:
        # Process single file
        if not output_path:
            # Auto-generate output path based on format
            if output_format == 'json':
                output_path = input_path.parent / f"{input_path.stem}_ANALYSIS.json"
            elif output_format == 'markdown':
                output_path = input_path.parent / f"{input_path.stem}_ANALYSIS.md"
            elif output_format == 'html':
                output_path = input_path.parent / f"{input_path.stem}_ANALYSIS.html"
            elif output_format == 'csv':
                output_path = input_path.parent / f"{input_path.stem}_ANALYSIS.csv"
            elif output_format == 'tsv':
                output_path = input_path.parent / f"{input_path.stem}_ANALYSIS.tsv"
            else:
                output_path = input_path.parent / f"{input_path.stem}_ANNOTATED.asm"

        annotate_asm_file(input_path, output_path, output_format=output_format)

    print("\nAnnotation complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
