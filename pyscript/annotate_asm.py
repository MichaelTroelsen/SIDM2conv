"""
Automatic ASM File Annotator

Adds comprehensive annotations to 6502 assembly files with:
- Memory map
- SID register documentation
- Laxity format reference
- Inline comments for known patterns
- Label identification
"""

import sys
import re
from pathlib import Path
from typing import List, Tuple, Optional

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

    # Create annotated version
    output_lines = []

    # Add comprehensive header
    output_lines.append(create_header(input_path.name, file_info))

    # Process each line
    in_header = True
    for line in content.split('\n'):
        # Skip original SIDwinder header (first 10 lines)
        if in_header and line.startswith('//;'):
            continue
        elif in_header and not line.strip().startswith('//;'):
            in_header = False

        # Annotate the line
        annotated = annotate_line(line)
        output_lines.append(annotated)

    # Write annotated file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(''.join(output_lines))

    print(f"  Created: {output_path.name}")


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
