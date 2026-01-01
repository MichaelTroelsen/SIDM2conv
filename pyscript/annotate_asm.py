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


def generate_subroutine_header(info: SubroutineInfo) -> str:
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
    detector = SubroutineDetector(content)
    subroutines = detector.detect_all_subroutines()
    print(f"  Found {len(subroutines)} subroutine(s)")

    # Create annotated version
    output_lines = []

    # Add comprehensive header
    output_lines.append(create_header(input_path.name, file_info))

    # Build a mapping of line numbers to subroutine addresses
    line_to_subroutine = {}
    for addr, info in subroutines.items():
        line_num = detector._find_line_by_address(addr)
        if line_num is not None:
            line_to_subroutine[line_num] = addr

    # Process each line, inserting subroutine headers
    in_header = True
    lines = content.split('\n')

    for i, line in enumerate(lines):
        # Skip original SIDwinder header (first 10 lines)
        if in_header and line.startswith('//;'):
            continue
        elif in_header and not line.strip().startswith('//;'):
            in_header = False

        # Check if this line starts a subroutine (by line number)
        if i in line_to_subroutine:
            sub_addr = line_to_subroutine[i]
            sub_header = generate_subroutine_header(subroutines[sub_addr])
            output_lines.append(sub_header)

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
