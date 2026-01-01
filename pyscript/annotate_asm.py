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
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass, field

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
                               all_subroutines: Optional[Dict[int, 'SubroutineInfo']] = None) -> str:
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


def annotate_asm_file(input_path: Path, output_path: Path, file_info: dict = None):
    """Annotate an ASM file with comprehensive comments"""

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

    # Create annotated version
    output_lines = []

    # Add comprehensive header
    output_lines.append(create_header(input_path.name, file_info))

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
            sub_header = generate_subroutine_header(subroutines[sub_addr], xrefs, subroutines)
            output_lines.append(sub_header)

        # Check if this line starts a code pattern
        if i in line_to_pattern:
            pattern = line_to_pattern[i]
            pattern_header = format_pattern_header(pattern)
            output_lines.append(pattern_header)

        # Annotate the line
        annotated = annotate_line(line)
        output_lines.append(annotated)

    # Write annotated file
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


def main():
    if len(sys.argv) < 2:
        print("Usage: python annotate_asm.py <input.asm> [output.asm]")
        print("   or: python annotate_asm.py <directory>")
        return 1

    input_path = Path(sys.argv[1])

    if input_path.is_dir():
        # Process all ASM files in directory
        for asm_file in input_path.glob('**/*.asm'):
            if '_ANNOTATED' not in asm_file.name:
                output_file = asm_file.parent / f"{asm_file.stem}_ANNOTATED.asm"
                annotate_asm_file(asm_file, output_file)
    else:
        # Process single file
        if len(sys.argv) > 2:
            output_path = Path(sys.argv[2])
        else:
            output_path = input_path.parent / f"{input_path.stem}_ANNOTATED.asm"

        annotate_asm_file(input_path, output_path)

    print("\nAnnotation complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
