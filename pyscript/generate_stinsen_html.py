#!/usr/bin/env python3
"""
Generate fully annotated HTML for Stinsen's Last Night of '89
Extracts real data from the SID file
"""

import sys
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sidm2.sid_parser import SIDParser
from pyscript.html_export import generate_html_export
from pyscript.annotate_asm import SectionType

@dataclass
class DataSection:
    """Data section with raw bytes"""
    start_address: int
    end_address: int
    section_type: SectionType
    data: bytes
    annotations: List[str] = None
    start_line: int = 0
    end_line: int = 0
    name: str = ""
    size: int = 0

    def __post_init__(self):
        """Calculate size from addresses"""
        if self.size == 0 and self.start_address and self.end_address:
            self.size = self.end_address - self.start_address + 1

def annotate_wave_table(data: bytes) -> List[str]:
    """Generate annotations for wave table (waveform values)"""
    waveform_names = {
        0x00: "None",
        0x01: "Triangle",
        0x02: "Sawtooth",
        0x03: "Tri+Saw",
        0x04: "Pulse",
        0x05: "Tri+Pls",
        0x06: "Saw+Pls",
        0x07: "Tri+Saw+Pls",
        0x08: "Noise",
        0x09: "Tri+Noise",
        0x0A: "Saw+Noise",
        0x0B: "Tri+Saw+Noise",
        0x0C: "Pls+Noise",
        0x0D: "Tri+Pls+Noise",
        0x0E: "Saw+Pls+Noise",
        0x0F: "All"
    }

    annotations = []
    for i, byte in enumerate(data):
        waveform = waveform_names.get(byte & 0x0F, f"Unknown({byte:02X})")
        annotations.append(f"Wave:{waveform}")
    return annotations

def annotate_wave_note_offsets(data: bytes) -> List[str]:
    """Generate annotations for wave note offset table"""
    annotations = []
    for i, byte in enumerate(data):
        if byte == 0:
            annotations.append("Note+0")
        elif byte < 0x80:
            annotations.append(f"Note+{byte}")
        else:
            # Negative offset (two's complement)
            offset = byte - 256
            annotations.append(f"Note{offset}")
    return annotations

def annotate_pulse_table(data: bytes) -> List[str]:
    """Generate annotations for pulse width table (4-byte entries)"""
    annotations = []
    for i in range(0, len(data), 4):
        if i + 3 < len(data):
            # 4-byte pulse entry
            pw_lo = data[i]
            pw_hi = data[i+1]
            pw_value = (pw_hi << 8) | pw_lo

            # Annotate each of the 4 bytes
            annotations.append(f"PW.Lo=${pw_lo:02X}")
            annotations.append(f"PW.Hi=${pw_hi:02X}")
            annotations.append(f"Byte2=${data[i+2]:02X}")
            annotations.append(f"Byte3=${data[i+3]:02X}")
        else:
            # Handle incomplete entry
            for j in range(i, len(data)):
                annotations.append(f"Data=${data[j]:02X}")
    return annotations

def annotate_filter_table(data: bytes) -> List[str]:
    """Generate annotations for filter table (4-byte entries)"""
    annotations = []
    for i in range(0, len(data), 4):
        if i + 3 < len(data):
            # 4-byte filter entry
            cutoff = data[i]
            resonance = data[i+1]

            annotations.append(f"Cutoff=${cutoff:02X}")
            annotations.append(f"Reson=${resonance:02X}")
            annotations.append(f"Ctrl=${data[i+2]:02X}")
            annotations.append(f"Mode=${data[i+3]:02X}")
        else:
            for j in range(i, len(data)):
                annotations.append(f"Data=${data[j]:02X}")
    return annotations

def annotate_instrument_table(data: bytes) -> List[str]:
    """Generate annotations for instrument table"""
    annotations = []

    # Laxity instrument commands
    commands = {
        0xA0: "Cmd:Loop",
        0xA1: "Cmd:Note",
        0xA2: "Cmd:Wait",
        0xA3: "Cmd:Vib",
        0xA4: "Cmd:Port",
        0xA5: "Cmd:ADSR",
        0xA6: "Cmd:Wave",
        0xA7: "Cmd:PW",
        0xA8: "Cmd:Filt",
        0xA9: "Cmd:Jump",
        0xAA: "Cmd:Arp1",
        0xAB: "Cmd:Arp2",
        0xAC: "Cmd:Bend",
        0xAD: "Cmd:Sld",
        0xAE: "Cmd:Vol",
        0xAF: "Cmd:Spd",
        0xFF: "End"
    }

    waveform_names = {
        0x00: "None", 0x01: "Tri", 0x02: "Saw", 0x03: "T+S",
        0x04: "Pls", 0x05: "T+P", 0x06: "S+P", 0x07: "All",
        0x08: "Noi", 0x09: "T+N", 0x0A: "S+N", 0x0B: "TSN",
        0x0C: "P+N", 0x0D: "TPN", 0x0E: "SPN", 0x0F: "Full"
    }

    for i, byte in enumerate(data):
        if byte in commands:
            annotations.append(commands[byte])
        elif byte <= 0x0F:
            waveform = waveform_names.get(byte, f"W:{byte:02X}")
            annotations.append(f"Wave:{waveform}")
        elif byte < 0x80:
            # Note or parameter
            annotations.append(f"Val:${byte:02X}")
        else:
            # High byte value
            annotations.append(f"Data:${byte:02X}")

    return annotations

def annotate_sequence_data(data: bytes) -> List[str]:
    """Generate annotations for sequence/arpeggio data

    Laxity sequence format uses various control bytes:
    - 0x00: Rest/Empty
    - 0x01-0x5F: Note values (C-0 to B-7)
    - 0x7E: Gate On
    - 0x7F: End of sequence
    - 0x80: Gate Off
    - 0x81-0x9F: Extended commands/durations
    - 0xA0-0xBF: Transpose commands (0xA0 = transpose +0, 0xA1 = +1, etc.)
    - 0xC0-0xFF: Various commands and control bytes
    """
    annotations = []

    # Note names for MIDI-style note numbering
    note_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']

    # Control commands
    commands = {
        0x00: "Rest",
        0x7E: "Gate:ON",
        0x7F: "END",
        0x80: "Gate:OFF",
        0x8F: "Ctrl:$8F",
        0xFF: "Mark:$FF"
    }

    for i, byte in enumerate(data):
        if byte in commands:
            # Known control command
            annotations.append(commands[byte])
        elif 0x01 <= byte <= 0x5F:
            # Note value (C-0 = 0x0C, C-1 = 0x18, etc.)
            # Approximate note name
            octave = (byte - 1) // 12
            note_idx = (byte - 1) % 12
            note_name = note_names[note_idx]
            annotations.append(f"Note:{note_name}{octave}")
        elif 0x81 <= byte <= 0x8E:
            # Extended control/duration
            annotations.append(f"Dur:${byte:02X}")
        elif 0xA0 <= byte <= 0xBF:
            # Transpose command (0xA0 = +0, 0xA1 = +1, etc.)
            transpose = byte - 0xA0
            if transpose <= 15:
                annotations.append(f"Trans:+{transpose}")
            else:
                # Negative transpose (two's complement style)
                transpose_val = transpose - 32
                annotations.append(f"Trans:{transpose_val:+d}")
        elif 0xC0 <= byte <= 0xCF:
            # Command bytes
            annotations.append(f"Cmd:${byte:02X}")
        else:
            # Other data
            annotations.append(f"Data:${byte:02X}")

    return annotations

def annotate_voice_control(data: bytes) -> List[str]:
    """Generate annotations for Voice/Channel Control section

    This section contains control data for the three SID voices.
    Structure (approximate 406 bytes total):
    - Voice state flags and counters
    - Current note/frequency data
    - Sequence pointers (lo/hi bytes)
    - Instrument assignments
    - Timing/duration counters
    - Transpose values
    - Various control parameters

    The data is organized in arrays indexed by voice (0, 1, 2)
    """
    annotations = []

    # Waveform names for quick reference
    waveform_names = {
        0x00: "Off", 0x01: "Tri", 0x02: "Saw", 0x03: "T+S",
        0x04: "Pls", 0x05: "T+P", 0x06: "S+P", 0x07: "All",
        0x08: "Noi", 0x09: "T+N", 0x0A: "S+N", 0x0B: "TSN",
        0x0C: "P+N", 0x0D: "TPN", 0x0E: "SPN", 0x0F: "Full",
        0x11: "Tri", 0x21: "Tri", 0x41: "Tri", 0x7F: "All", 0x81: "Tri"
    }

    for i, byte in enumerate(data):
        # Try to identify the type of data based on position and value

        if byte == 0x00:
            annotations.append("Empty")
        elif byte == 0x01:
            annotations.append("Flag:1")
        elif byte == 0x02:
            annotations.append("Flag:2")
        elif byte == 0x03:
            annotations.append("Flag:3")
        elif byte == 0xFF:
            annotations.append("Max:$FF")
        elif byte == 0x80:
            annotations.append("Flag:$80")
        elif byte in waveform_names:
            # Waveform value
            annotations.append(f"Wave:{waveform_names[byte]}")
        elif 0x04 <= byte <= 0x0F:
            # Small values - likely indices, counters, or flags
            annotations.append(f"Idx:{byte}")
        elif 0x10 <= byte <= 0x3F:
            # Medium values - could be durations, offsets, or note values
            annotations.append(f"Val:${byte:02X}")
        elif 0x40 <= byte <= 0x7F:
            # Higher values - could be flags, pointers (lo byte), or data
            annotations.append(f"Data:${byte:02X}")
        elif 0xA0 <= byte <= 0xBF:
            # Transpose or command range
            transpose = byte - 0xA0
            if transpose <= 15:
                annotations.append(f"Trans:+{transpose}")
            else:
                annotations.append(f"Cmd:${byte:02X}")
        else:
            # Other data - pointers, addresses, or control values
            annotations.append(f"Byte:${byte:02X}")

    return annotations

def extract_laxity_data_sections(sid_file: Path) -> Tuple[List[DataSection], 'PSIDHeader']:
    """Extract data sections from Laxity SID file"""

    # Parse SID file and extract full metadata
    parser = SIDParser(str(sid_file))
    header = parser.parse_header()
    music_data, load_addr = parser.get_c64_data(header)

    print(f"\nSID File Metadata:")
    print(f"  Name: {header.name}")
    print(f"  Author: {header.author}")
    print(f"  Copyright: {header.copyright}")
    print(f"  Load Address: ${header.load_address or load_addr:04X}")
    print(f"  Init Address: ${header.init_address:04X}")
    print(f"  Play Address: ${header.play_address:04X}")
    print(f"  Songs: {header.songs}, Start Song: {header.start_song}")

    # Known Laxity NewPlayer v21 table addresses (relative to load address)
    # Load address is typically $1000, tables start around $18DA

    # Calculate offsets from load address
    wave_table_addr = 0x18DA
    wave_note_addr = 0x190C
    pulse_table_addr = 0x1837
    filter_table_addr = 0x1A1E
    instrument_table_addr = 0x1A6B

    # Extract data sections
    sections = []

    try:
        # Wave Table - 32 bytes
        offset = wave_table_addr - load_addr
        if 0 <= offset < len(music_data) - 32:
            wave_data = music_data[offset:offset+32]
            annotations = annotate_wave_table(wave_data)
            sections.append(DataSection(
                start_address=wave_table_addr,
                end_address=wave_table_addr + 31,
                section_type=SectionType.WAVE_TABLE,
                data=wave_data,
                annotations=annotations,
                name="Wave Table",
                size=32
            ))
            print(f"Extracted Wave Table: ${wave_table_addr:04X}, {len(wave_data)} bytes, {len(annotations)} annotations")

        # Wave Note Offsets - 32 bytes
        offset = wave_note_addr - load_addr
        if 0 <= offset < len(music_data) - 32:
            wave_note_data = music_data[offset:offset+32]
            annotations = annotate_wave_note_offsets(wave_note_data)
            sections.append(DataSection(
                start_address=wave_note_addr,
                end_address=wave_note_addr + 31,
                section_type=SectionType.WAVE_TABLE,
                data=wave_note_data,
                annotations=annotations,
                name="Wave Note Offsets",
                size=32
            ))
            print(f"Extracted Wave Note Offsets: ${wave_note_addr:04X}, {len(wave_note_data)} bytes, {len(annotations)} annotations")

        # Pulse Table - 64 bytes (4-byte entries)
        offset = pulse_table_addr - load_addr
        if 0 <= offset < len(music_data) - 64:
            pulse_data = music_data[offset:offset+64]
            annotations = annotate_pulse_table(pulse_data)
            sections.append(DataSection(
                start_address=pulse_table_addr,
                end_address=pulse_table_addr + 63,
                section_type=SectionType.PULSE_TABLE,
                data=pulse_data,
                annotations=annotations,
                name="Pulse Table",
                size=64
            ))
            print(f"Extracted Pulse Table: ${pulse_table_addr:04X}, {len(pulse_data)} bytes, {len(annotations)} annotations")

        # Filter Table - 64 bytes
        offset = filter_table_addr - load_addr
        if 0 <= offset < len(music_data) - 64:
            filter_data = music_data[offset:offset+64]
            annotations = annotate_filter_table(filter_data)
            sections.append(DataSection(
                start_address=filter_table_addr,
                end_address=filter_table_addr + 63,
                section_type=SectionType.FILTER_TABLE,
                data=filter_data,
                annotations=annotations,
                name="Filter Table",
                size=64
            ))
            print(f"Extracted Filter Table: ${filter_table_addr:04X}, {len(filter_data)} bytes, {len(annotations)} annotations")

        # Instrument Table - 96 bytes (8 bytes × 12 instruments)
        offset = instrument_table_addr - load_addr
        if 0 <= offset < len(music_data) - 96:
            inst_data = music_data[offset:offset+96]
            annotations = annotate_instrument_table(inst_data)
            sections.append(DataSection(
                start_address=instrument_table_addr,
                end_address=instrument_table_addr + 95,
                section_type=SectionType.INSTRUMENT_TABLE,
                data=inst_data,
                annotations=annotations,
                name="Instrument Table",
                size=96
            ))
            print(f"Extracted Instrument Table: ${instrument_table_addr:04X}, {len(inst_data)} bytes, {len(annotations)} annotations")

    except Exception as e:
        print(f"Warning: Error extracting section: {e}")

    # Add all DataBlock_6 subsections for complete memory map
    try:
        # Define all DataBlock_6 sections with their addresses and sizes
        datablock6_sections = [
            (0x16A1, 0x1836, "Voice/Channel Control", SectionType.DATA),
            (0x1837, 0x1876, "Pulse Table", SectionType.PULSE_TABLE),  # Already added above
            (0x1877, 0x18D9, "Arpeggio Pointers", SectionType.DATA),
            (0x18DA, 0x18F9, "Wave Table", SectionType.WAVE_TABLE),  # Already added above
            (0x18FA, 0x190B, "Wave Control", SectionType.DATA),
            (0x190C, 0x192B, "Wave Note Offsets", SectionType.WAVE_TABLE),  # Already added above
            (0x192C, 0x1A1D, "Filter Control", SectionType.DATA),
            (0x1A1E, 0x1A5D, "Filter Table", SectionType.FILTER_TABLE),  # Already added above
            (0x1A5E, 0x1A6A, "Reserved", SectionType.DATA),
            (0x1A6B, 0x1ACA, "Instrument Table", SectionType.INSTRUMENT_TABLE),  # Already added above
            (0x1ACB, 0x27BA, "Sequence/Arpeggio Data", SectionType.DATA),
        ]

        # Add sections that weren't already extracted
        existing_addrs = {s.start_address for s in sections}
        for start, end, name, sect_type in datablock6_sections:
            if start not in existing_addrs:
                offset = start - load_addr
                size = end - start + 1
                if 0 <= offset < len(music_data) and offset + size <= len(music_data):
                    data = music_data[offset:offset+size]

                    # Generate annotations based on section type
                    annotations = []
                    if name == "Sequence/Arpeggio Data":
                        annotations = annotate_sequence_data(data)
                        print(f"Added DataBlock_6 section: {name} ${start:04X}-${end:04X} ({size} bytes, {len(annotations)} annotations)")
                    elif name == "Voice/Channel Control":
                        annotations = annotate_voice_control(data)
                        print(f"Added DataBlock_6 section: {name} ${start:04X}-${end:04X} ({size} bytes, {len(annotations)} annotations)")
                    else:
                        print(f"Added DataBlock_6 section: {name} ${start:04X}-${end:04X} ({size} bytes)")

                    sections.append(DataSection(
                        start_address=start,
                        end_address=end,
                        section_type=sect_type,
                        data=data,
                        annotations=annotations,
                        name=name,  # Store descriptive name
                        size=size
                    ))

    except Exception as e:
        print(f"Warning: Error adding DataBlock_6 sections: {e}")

    print(f"\nTotal sections extracted: {len(sections)}")
    return sections, header

def main():
    """Generate annotated HTML for SID file"""
    import sys

    # Accept SID file as command-line argument
    if len(sys.argv) > 1:
        sid_file = Path(sys.argv[1])
    else:
        sid_file = Path("Laxity/Stinsens_Last_Night_of_89.sid")

    # Generate output filename based on input
    base_name = sid_file.stem
    output_file = Path(f"analysis/{base_name}_ANNOTATED.html")

    if not sid_file.exists():
        print(f"Error: SID file not found: {sid_file}")
        return 1

    print(f"Processing: {sid_file}")
    print(f"Output: {output_file}")
    print()

    # Extract data sections and header metadata
    sections, header = extract_laxity_data_sections(sid_file)

    # Detect player type
    print("\nDetecting player type...")
    from sidm2.enhanced_player_detection import EnhancedPlayerDetector
    detector = EnhancedPlayerDetector()
    player_type, confidence = detector.detect_player(sid_file)
    print(f"  Detected: {player_type} (confidence: {confidence:.1%})")

    # Disassemble with SIDwinder to get assembly code
    print("\nDisassembling with SIDwinder...")
    import subprocess
    import os

    asm_file = Path(f"analysis/{base_name}_temp.asm")
    sidwinder_path = Path("tools/SIDwinder.exe").absolute()

    try:
        # Use full absolute paths
        result = subprocess.run(
            [str(sidwinder_path), "-disassemble", str(sid_file.absolute()), str(asm_file.absolute())],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.getcwd()
        )

        if result.returncode != 0:
            print(f"Warning: SIDwinder error (code {result.returncode}):")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
        else:
            print(f"Disassembly complete: {asm_file}")

    except Exception as e:
        print(f"Warning: Could not run SIDwinder: {e}")
        import traceback
        traceback.print_exc()

    # Read assembly lines
    lines = []
    if asm_file.exists():
        with open(asm_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f"Read {len(lines)} lines of assembly")

    # Get actual load address (for PSID files, header.load_address might be 0)
    parser = SIDParser(str(sid_file))
    _, actual_load_addr = parser.get_c64_data(header)

    # Create file info dict for HTML generation (use actual header data)
    file_info = {
        'name': header.name or sid_file.name,
        'author': header.author or "Unknown",
        'copyright': header.copyright or "",
        'load_address': header.load_address or actual_load_addr,  # Use actual if header is 0
        'init_address': header.init_address,
        'play_address': header.play_address,
        'songs': header.songs,
        'start_song': header.start_song,
        'player': player_type,  # HTML template expects 'player'
        'player_type': player_type,  # Also keep this for compatibility
        'player_confidence': confidence,
        'format': header.magic,
        'version': header.version
    }

    # Generate HTML using existing export function
    print("\nGenerating HTML...")

    # We'll need to call the annotate_asm functions directly
    # For now, let's use the demo approach and inject our real data

    # Actually, let me just update the demo to use the extracted sections
    html = generate_annotated_html_with_sections(
        input_path=sid_file,
        file_info=file_info,
        sections=sections,
        lines=lines
    )

    # Write HTML
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\nGenerated: {output_file}")
    print(f"Sections: {len(sections)}")
    print(f"Lines: {len(lines)}")

    # Open in browser
    import os
    os.system(f'start {output_file}')

    return 0

def generate_meaningful_labels(lines: List[str], init_addr: int, play_addr: int) -> Dict[str, str]:
    """Analyze code and generate meaningful label names instead of Label_0, Label_1, etc."""
    import re

    label_mapping = {}  # Map from "Label_52" to "Loop_ClearMemory"
    label_info = {}     # Collect info about each label

    # First pass: Find all labels and collect information
    for i, line in enumerate(lines):
        # Find label definitions (e.g., "Label_52:")
        label_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*):\s*$', line.strip())
        if label_match:
            label_name = label_match.group(1)
            if label_name.startswith('Label_'):
                # Extract address if available in next line
                addr = None
                if i + 1 < len(lines):
                    addr_match = re.search(r'//;\s*\$([0-9A-Fa-f]{4})', lines[i + 1])
                    if addr_match:
                        addr = int(addr_match.group(1), 16)

                # Collect context: next 5 instructions
                context_lines = []
                for j in range(i + 1, min(i + 6, len(lines))):
                    if lines[j].strip() and not lines[j].strip().startswith('//'):
                        context_lines.append(lines[j].strip())

                label_info[label_name] = {
                    'line_num': i,
                    'address': addr,
                    'context': context_lines,
                    'is_jsr_target': False,
                    'is_jmp_target': False,
                    'is_branch_target': False,
                    'branch_directions': []  # 'forward' or 'backward'
                }

    # Second pass: Find what references each label
    for i, line in enumerate(lines):
        # Find JSR, JMP, and branch instructions
        jsr_match = re.search(r'\bjsr\s+([A-Za-z_][A-Za-z0-9_]*)', line, re.IGNORECASE)
        jmp_match = re.search(r'\bjmp\s+([A-Za-z_][A-Za-z0-9_]*)', line, re.IGNORECASE)
        branch_match = re.search(r'\b(bne|beq|bpl|bmi|bcc|bcs|bvc|bvs)\s+([A-Za-z_][A-Za-z0-9_]*)', line, re.IGNORECASE)

        if jsr_match and jsr_match.group(1) in label_info:
            label_info[jsr_match.group(1)]['is_jsr_target'] = True

        if jmp_match and jmp_match.group(1) in label_info:
            label_info[jmp_match.group(1)]['is_jmp_target'] = True

        if branch_match and branch_match.group(2) in label_info:
            label_name = branch_match.group(2)
            label_info[label_name]['is_branch_target'] = True
            # Determine if branch is forward or backward
            target_line = label_info[label_name]['line_num']
            direction = 'backward' if target_line < i else 'forward'
            label_info[label_name]['branch_directions'].append(direction)

    # Third pass: Generate meaningful names
    for label_name, info in label_info.items():
        addr = info['address']
        context = info['context']

        # Special addresses
        if addr == init_addr:
            label_mapping[label_name] = 'Init'
            continue
        elif addr == play_addr:
            label_mapping[label_name] = 'Play'
            continue

        # Analyze context to determine purpose
        context_str = ' '.join(context).lower()
        new_name = None

        # JSR targets are subroutines
        if info['is_jsr_target']:
            # Analyze subroutine purpose from context
            if 'sid' in context_str or '$d4' in context_str:
                if 'sta' in context_str:
                    new_name = 'Subroutine_SetSID'
                else:
                    new_name = 'Subroutine_ReadSID'
            elif 'rts' in context_str and context.index('rts') <= 1:
                new_name = 'Subroutine_Return'
            elif any(x in context_str for x in ['lda', 'ldx', 'ldy']) and 'sta' in context_str:
                new_name = 'Subroutine_LoadStore'
            else:
                # Generic subroutine
                new_name = f'Subroutine_{label_name.replace("Label_", "")}'

        # Backward branches are loops
        elif 'backward' in info['branch_directions']:
            if 'dex' in context_str or 'dey' in context_str:
                new_name = 'Loop_Countdown'
            elif 'inx' in context_str or 'iny' in context_str:
                new_name = 'Loop_Countup'
            elif 'sta' in context_str and ('$00' in context_str or 'zp' in context_str):
                new_name = 'Loop_ClearMemory'
            else:
                new_name = f'Loop_{label_name.replace("Label_", "")}'

        # Forward branches are conditional skips
        elif 'forward' in info['branch_directions']:
            if 'rts' in context_str:
                new_name = 'ExitEarly'
            elif 'jmp' in context_str:
                new_name = 'BranchToJump'
            else:
                new_name = f'Skip_{label_name.replace("Label_", "")}'

        # JMP targets
        elif info['is_jmp_target']:
            new_name = f'JumpTarget_{label_name.replace("Label_", "")}'

        # Data blocks or unknown
        else:
            if 'byte' in context_str:
                new_name = f'DataBlock_{label_name.replace("Label_", "")}'
            else:
                new_name = f'Code_{label_name.replace("Label_", "")}'

        if new_name:
            label_mapping[label_name] = new_name

    return label_mapping


def apply_label_mapping(line: str, label_mapping: Dict[str, str]) -> str:
    """Replace generic labels with meaningful names in a line"""
    import re

    # Replace label references in instructions (jsr, jmp, branches)
    for old_label, new_label in label_mapping.items():
        # Match whole word only (not part of another word)
        line = re.sub(r'\b' + re.escape(old_label) + r'\b', new_label, line)

    return line


def annotate_sid_registers(line: str) -> str:
    """Add SID register names to instructions that access SID registers"""
    import re

    # SID base address
    SID0_BASE = 0xD400

    # SID register map
    SID_REGISTERS = {
        0: 'Voice 1: Freq Lo',
        1: 'Voice 1: Freq Hi',
        2: 'Voice 1: PW Lo',
        3: 'Voice 1: PW Hi',
        4: 'Voice 1: Control',
        5: 'Voice 1: Attack/Decay',
        6: 'Voice 1: Sustain/Release',
        7: 'Voice 2: Freq Lo',
        8: 'Voice 2: Freq Hi',
        9: 'Voice 2: PW Lo',
        10: 'Voice 2: PW Hi',
        11: 'Voice 2: Control',
        12: 'Voice 2: Attack/Decay',
        13: 'Voice 2: Sustain/Release',
        14: 'Voice 3: Freq Lo',
        15: 'Voice 3: Freq Hi',
        16: 'Voice 3: PW Lo',
        17: 'Voice 3: PW Hi',
        18: 'Voice 3: Control',
        19: 'Voice 3: Attack/Decay',
        20: 'Voice 3: Sustain/Release',
        21: 'Filter: Cutoff Lo',
        22: 'Filter: Cutoff Hi',
        23: 'Filter: Resonance/Routing',
        24: 'Filter: Mode/Volume'
    }

    # Pattern to match SID0, SID0+offset, SID0+offset,Y, SID0,Y, etc.
    # Examples: SID0, SID0+1, SID0+6,Y, SID0,Y

    # First, handle SID0+offset,X/Y (with index register)
    pattern1 = r'SID0\+(\d+),([XY])'
    def replace_indexed(match):
        offset = int(match.group(1))
        index_reg = match.group(2)
        if offset in SID_REGISTERS:
            reg_name = SID_REGISTERS[offset]
            return f'SID0+{offset},{index_reg}  ; [{reg_name}]'
        else:
            return f'SID0+{offset},{index_reg}'

    # Second, handle SID0,X/Y (no offset, with index register)
    pattern2 = r'SID0,([XY])'
    def replace_sid0_indexed(match):
        index_reg = match.group(1)
        return f'SID0,{index_reg}  ; [Voice register, dynamic]'

    # Third, handle SID0+offset (no index register)
    pattern3 = r'SID0\+(\d+)(?![,XY])'
    def replace_offset_only(match):
        offset = int(match.group(1))
        if offset in SID_REGISTERS:
            reg_name = SID_REGISTERS[offset]
            return f'SID0+{offset}  ; [{reg_name}]'
        else:
            return f'SID0+{offset}'

    # Fourth, handle plain SID0 (no offset, no index)
    pattern4 = r'\bSID0\b(?!\+)(?!,)'
    def replace_sid0_direct(match):
        return 'SID0  ; [Voice 1: Freq Lo]'

    line = re.sub(pattern1, replace_indexed, line)
    line = re.sub(pattern2, replace_sid0_indexed, line)
    line = re.sub(pattern3, replace_offset_only, line)
    line = re.sub(pattern4, replace_sid0_direct, line)

    return line


def replace_datablock6_with_table_names(line: str) -> str:
    """Replace DataBlock_6 + $offset with meaningful table names"""
    import re

    # DataBlock_6 base address is $16A1
    DATABLOCK_6_BASE = 0x16A1

    # Find all instances of DataBlock_6 + $XX or DataBlock_6 + $XXX
    pattern = r'DataBlock_6\s*\+\s*\$([0-9A-Fa-f]+)'

    def replace_with_table_name(match):
        offset_str = match.group(1)
        offset = int(offset_str, 16)
        absolute_addr = DATABLOCK_6_BASE + offset

        # Map absolute addresses to table names
        # Based on the section boundaries
        if 0x16A1 <= absolute_addr <= 0x1836:
            return f'VoiceControl + ${offset_str}'
        elif 0x1837 <= absolute_addr <= 0x1876:
            pulse_offset = absolute_addr - 0x1837
            return f'PulseTable + ${pulse_offset:02X}'
        elif 0x1877 <= absolute_addr <= 0x18D9:
            arp_offset = absolute_addr - 0x1877
            return f'ArpeggioPointers + ${arp_offset:02X}'
        elif 0x18DA <= absolute_addr <= 0x18F9:
            wave_offset = absolute_addr - 0x18DA
            return f'WaveTable + ${wave_offset:02X}'
        elif 0x18FA <= absolute_addr <= 0x190B:
            wave_ctrl_offset = absolute_addr - 0x18FA
            return f'WaveControl + ${wave_ctrl_offset:02X}'
        elif 0x190C <= absolute_addr <= 0x192B:
            wave_note_offset = absolute_addr - 0x190C
            return f'WaveNoteOffsets + ${wave_note_offset:02X}'
        elif 0x192C <= absolute_addr <= 0x1A1D:
            filter_ctrl_offset = absolute_addr - 0x192C
            return f'FilterControl + ${filter_ctrl_offset:02X}'
        elif 0x1A1E <= absolute_addr <= 0x1A5D:
            filter_offset = absolute_addr - 0x1A1E
            return f'FilterTable + ${filter_offset:02X}'
        elif 0x1A5E <= absolute_addr <= 0x1A6A:
            return f'Reserved + ${offset_str}'
        elif 0x1A6B <= absolute_addr <= 0x1ACA:
            inst_offset = absolute_addr - 0x1A6B
            # Calculate instrument number (8 bytes per instrument)
            inst_num = inst_offset // 8
            byte_in_inst = inst_offset % 8
            return f'Instrument{inst_num} + ${byte_in_inst:X}'
        elif 0x1ACB <= absolute_addr <= 0x27BA:
            seq_offset = absolute_addr - 0x1ACB
            return f'SequenceData + ${seq_offset:04X}'
        else:
            # Outside known ranges, keep as DataBlock_6
            return f'DataBlock_6 + ${offset_str}'

    return re.sub(pattern, replace_with_table_name, line)


def add_table_name_hyperlinks(line: str) -> str:
    """Add hyperlinks to table names so they jump to their sections"""
    import re

    # List of table names to make clickable
    table_names = [
        'VoiceControl',
        'PulseTable',
        'ArpeggioPointers',
        'SequenceData',
        'WaveTable',
        'WaveControl',
        'WaveNoteOffsets',
        'FilterControl',
        'FilterTable',
        'InstrumentTable',
        'Reserved'
    ]

    # Also handle Instrument0-11
    for i in range(12):
        table_names.append(f'Instrument{i}')

    # Replace table names with hyperlink markers
    for table_name in table_names:
        # Match the table name when it appears before a + or space
        # But not when it's in a section header
        if '┌─' not in line and '├─' not in line and '└─' not in line:
            pattern = r'\b(' + re.escape(table_name) + r')(\s*\+)'
            line = re.sub(pattern, r'[[TABLELINK:\1]]\2', line)

    return line


def add_label_hyperlinks(line: str, all_labels: set) -> str:
    """Add special markers for label hyperlinks (to be converted to HTML after escaping)"""
    import re

    stripped = line.strip()

    # Check if this line is a label definition (e.g., "Loop_Countdown:")
    label_def_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*):\s*$', stripped)
    if label_def_match:
        label_name = label_def_match.group(1)
        # Add special marker for label definition (will be converted to anchor after HTML escaping)
        return line.replace(f'{label_name}:', f'[[LABELDEF:{label_name}]]')

    # Not a label definition - check for label references
    # Find all potential label references (identifiers that are in our label set)
    result = line
    for label in sorted(all_labels, key=len, reverse=True):  # Longest first to avoid partial matches
        # Match label as whole word (not part of another identifier)
        pattern = r'\b(' + re.escape(label) + r')\b'

        def make_marker(match):
            label_text = match.group(1)
            # Add special marker (will be converted to link after HTML escaping)
            return f'[[LABELREF:{label_text}]]'

        result = re.sub(pattern, make_marker, result)

    return result


def build_memory_map(load_address: int) -> dict:
    """
    Build C64 memory map, treating ROM areas as RAM if SID loads there.

    When a SID file loads at $A000-$BFFF or $E000-$FFFF, those ROM areas
    are actually being used as RAM (ROM is banked out).

    Args:
        load_address: SID file load address

    Returns:
        Dictionary mapping (start, end) ranges to region names
    """
    # Determine if ROM areas should be treated as RAM
    basic_rom_is_ram = 0xA000 <= load_address <= 0xBFFF
    kernal_rom_is_ram = 0xE000 <= load_address <= 0xFFFF

    return {
        (0x0000, 0x00FF): 'Zero Page',
        (0x0100, 0x01FF): 'Stack',
        (0x0200, 0x03FF): 'BASIC/KERNAL Variables',
        (0x0400, 0x07FF): 'Screen RAM',
        (0x0800, 0x0FFF): 'BASIC Program',
        (0x1000, 0x1FFF): 'Program Memory',
        (0x2000, 0x3FFF): 'Program Memory',
        (0x4000, 0x7FFF): 'Program Memory',
        (0x8000, 0x9FFF): 'Cartridge ROM',
        (0xA000, 0xBFFF): 'RAM (BASIC ROM banked out)' if basic_rom_is_ram else 'BASIC ROM',
        (0xC000, 0xCFFF): 'Program Memory',
        (0xD000, 0xD3FF): 'VIC-II',
        (0xD400, 0xD7FF): 'SID',
        (0xD800, 0xDBFF): 'Color RAM',
        (0xDC00, 0xDCFF): 'CIA #1',
        (0xDD00, 0xDDFF): 'CIA #2',
        (0xDE00, 0xDFFF): 'I/O',
        (0xE000, 0xFFFF): 'RAM (KERNAL ROM banked out)' if kernal_rom_is_ram else 'KERNAL ROM'
    }


def annotate_sidwinder_line(line: str, load_address: int = 0x1000) -> str:
    """Add inline annotations to SIDwinder disassembly lines with memory map info

    Args:
        line: Assembly line to annotate
        load_address: SID file load address (for correct ROM/RAM mapping)
    """
    import re

    # Strip ALL lines of their newlines first - we'll add exactly one back at the end
    line = line.rstrip('\r\n')

    # Skip completely empty lines - return empty string so they can be filtered
    if not line.strip():
        return ''

    # Skip comment-only lines that have no real content (just //; and whitespace)
    stripped = line.strip()
    if stripped.startswith('//;'):
        # Check if there's actual content after the //;
        content_after = stripped[3:].strip()
        if not content_after or content_after == '-' * len(content_after):
            # Just whitespace or just dashes - return empty string to filter
            return ''

    # Lines with directives (.const, .byte, etc.) - ensure consistent alignment
    if stripped.startswith('.'):
        # For .byte lines, ensure comments are aligned at column 100
        if '//' in line:
            parts = line.split('//', 1)
            code_part = parts[0].rstrip()
            comment_part = parts[1].lstrip()
            # Expand tabs for accurate length
            code_part_expanded = code_part.expandtabs(8)
            # Align comment at column 100 for .byte lines (they're longer with table names)
            target_column = 100
            current_length = len(code_part_expanded)
            padding = ' ' * max(2, target_column - current_length)
            return f'{code_part}{padding}//;  {comment_part}\n'
        return line + '\n'

    # C64 Memory Map (dynamic based on SID load address)
    MEMORY_MAP = build_memory_map(load_address)

    # SID Chip Register Map ($D400-$D41F)
    SID_REGISTERS = {
        0xD400: 'Voice 1: Freq Lo',
        0xD401: 'Voice 1: Freq Hi',
        0xD402: 'Voice 1: PW Lo',
        0xD403: 'Voice 1: PW Hi',
        0xD404: 'Voice 1: Control',
        0xD405: 'Voice 1: Attack/Decay',
        0xD406: 'Voice 1: Sustain/Release',
        0xD407: 'Voice 2: Freq Lo',
        0xD408: 'Voice 2: Freq Hi',
        0xD409: 'Voice 2: PW Lo',
        0xD40A: 'Voice 2: PW Hi',
        0xD40B: 'Voice 2: Control',
        0xD40C: 'Voice 2: Attack/Decay',
        0xD40D: 'Voice 2: Sustain/Release',
        0xD40E: 'Voice 3: Freq Lo',
        0xD40F: 'Voice 3: Freq Hi',
        0xD410: 'Voice 3: PW Lo',
        0xD411: 'Voice 3: PW Hi',
        0xD412: 'Voice 3: Control',
        0xD413: 'Voice 3: Attack/Decay',
        0xD414: 'Voice 3: Sustain/Release',
        0xD415: 'Filter: Cutoff Lo',
        0xD416: 'Filter: Cutoff Hi',
        0xD417: 'Filter: Resonance/Routing',
        0xD418: 'Filter: Mode/Volume'
    }

    def get_memory_info(addr: int) -> str:
        """Get memory map info for an address"""
        # Check SID registers first
        if addr in SID_REGISTERS:
            return f'SID: {SID_REGISTERS[addr]}'

        # Check memory map ranges
        for (start, end), region in MEMORY_MAP.items():
            if start <= addr <= end:
                return region

        return 'Unknown'

    # Common 6502 instruction annotations (complete set)
    INSTRUCTION_DOCS = {
        # Arithmetic
        'ADC': 'Add with Carry',
        'SBC': 'Subtract with Carry',
        'INC': 'Increment Memory',
        'DEC': 'Decrement Memory',
        'INX': 'Increment X',
        'INY': 'Increment Y',
        'DEX': 'Decrement X',
        'DEY': 'Decrement Y',
        # Logic
        'AND': 'Logical AND',
        'ORA': 'Logical OR',
        'EOR': 'Exclusive OR',
        'BIT': 'Bit Test',
        # Shifts & Rotates
        'ASL': 'Arithmetic Shift Left',
        'LSR': 'Logical Shift Right',
        'ROL': 'Rotate Left',
        'ROL': 'Rotate Right',
        # Loads
        'LDA': 'Load Accumulator',
        'LDX': 'Load X Register',
        'LDY': 'Load Y Register',
        # Stores
        'STA': 'Store Accumulator',
        'STX': 'Store X Register',
        'STY': 'Store Y Register',
        # Transfers
        'TAX': 'Transfer A to X',
        'TAY': 'Transfer A to Y',
        'TXA': 'Transfer X to A',
        'TYA': 'Transfer Y to A',
        'TSX': 'Transfer Stack Pointer to X',
        'TXS': 'Transfer X to Stack Pointer',
        # Stack
        'PHA': 'Push Accumulator',
        'PLA': 'Pull Accumulator',
        'PHP': 'Push Processor Status',
        'PLP': 'Pull Processor Status',
        # Jumps & Branches
        'JMP': 'Jump',
        'JSR': 'Jump to Subroutine',
        'RTS': 'Return from Subroutine',
        'RTI': 'Return from Interrupt',
        'BNE': 'Branch if Not Equal',
        'BEQ': 'Branch if Equal',
        'BPL': 'Branch if Plus',
        'BMI': 'Branch if Minus',
        'BCC': 'Branch if Carry Clear',
        'BCS': 'Branch if Carry Set',
        'BVC': 'Branch if Overflow Clear',
        'BVS': 'Branch if Overflow Set',
        # Compares
        'CMP': 'Compare with Accumulator',
        'CPX': 'Compare with X',
        'CPY': 'Compare with Y',
        # Flags
        'CLC': 'Clear Carry Flag',
        'SEC': 'Set Carry Flag',
        'CLI': 'Clear Interrupt Disable',
        'SEI': 'Set Interrupt Disable',
        'CLV': 'Clear Overflow Flag',
        'CLD': 'Clear Decimal Mode',
        'SED': 'Set Decimal Mode',
        # System
        'NOP': 'No Operation',
        'BRK': 'Break'
    }

    # Process SIDwinder comments: remove duplicates, add memory map info
    # Format: "instruction //; $1046 - 1046 //; $1046 - 1046"
    # Should become: "instruction ; Description //; $1046 [Memory Map]"

    # Extract address from SIDwinder comments
    addr_match = re.search(r'//;\s*\$?([0-9A-Fa-f]{4})', line)
    memory_info = ''
    if addr_match:
        addr = int(addr_match.group(1), 16)
        memory_info = get_memory_info(addr)

    # Extract instruction from line (lowercase in SIDwinder output)
    instruction_match = re.match(r'\s*([a-z]{3})\s', line, re.IGNORECASE)
    if instruction_match:
        instruction = instruction_match.group(1).upper()
        instruction_doc = INSTRUCTION_DOCS.get(instruction, '')

        # Remove duplicate SIDwinder comments and rebuild
        # Original: "    rts                          //; $1046 - 1046 //; $1046 - 1046"
        # New:      "    rts ; Return from Subroutine //; $1046 [Program Memory]"

        if '//' in line:
            # Split at first //
            parts = line.split('//', 1)
            code_part = parts[0].rstrip()

            # Expand tabs to spaces (8-space tab stops) for accurate length calculation AND display
            code_part_expanded = code_part.expandtabs(8)

            # Extract just the first address from comments
            addr_str = ''
            if addr_match:
                addr_str = f'${addr_match.group(1)}'

            # Rebuild line with instruction doc and single address + memory map
            # Align comments at column 100 for better spacing with long table names
            target_column = 100
            current_length = len(code_part_expanded)
            padding = ' ' * max(2, target_column - current_length)

            # Use expanded code_part for consistent alignment (no tabs)
            if instruction_doc and addr_str:
                line = f'{code_part_expanded}{padding};  {instruction_doc} //; {addr_str} [{memory_info}]'
            elif instruction_doc:
                line = f'{code_part_expanded}{padding};  {instruction_doc}'
            elif addr_str:
                line = f'{code_part_expanded}{padding}//; {addr_str} [{memory_info}]'
        else:
            # No SIDwinder comment, just add instruction doc
            if instruction_doc:
                line = line.rstrip() + f' ; {instruction_doc}'

    # Always return with exactly one newline
    return line + '\n'

def generate_annotated_html_with_sections(input_path, file_info, sections, lines):
    """Generate HTML with our extracted sections"""

    # Import all analyzer classes from annotate_asm
    from pyscript.annotate_asm import (
        SubroutineDetector,
        SectionDetector,
        CrossReferenceDetector,
        PatternDetector,
        CycleCounter,
        ControlFlowAnalyzer,
        SymbolTableGenerator,
        EnhancedRegisterTracker
    )

    print("\n=== Running Full Analysis Pipeline ===")

    # Convert lines list to string content for SubroutineDetector
    content = '\n'.join(lines)

    # 1. Detect subroutines
    print("  Detecting subroutines...")
    sub_detector = SubroutineDetector(content)
    subroutines = sub_detector.detect_all_subroutines()
    print(f"  Found {len(subroutines)} subroutine(s)")

    # 2. Generate cross-references
    print("  Generating cross-references...")
    xref_detector = CrossReferenceDetector(lines, subroutines)
    xrefs = xref_detector.generate_cross_references()
    total_refs = sum(len(refs) for refs in xrefs.values())
    print(f"  Found {total_refs} reference(s) to {len(xrefs)} address(es)")

    # 3. Detect code patterns
    print("  Detecting code patterns...")
    pattern_detector = PatternDetector(lines)
    patterns = pattern_detector.detect_all_patterns()
    print(f"  Found {len(patterns)} code pattern(s)")

    # 4. Count CPU cycles
    print("  Counting CPU cycles...")
    cycle_counter = CycleCounter(lines, subroutines)
    cycle_counts = cycle_counter.count_all_cycles()
    print(f"  Counted cycles for {len(cycle_counts)} instruction(s)")

    # 5. Analyze control flow
    print("  Analyzing control flow...")
    flow_analyzer = ControlFlowAnalyzer(lines, subroutines, cycle_counter)
    call_graph, loops, branches = flow_analyzer.analyze_all()
    print(f"  Found {len(loops)} loop(s), {len(branches)} branch(es)")

    # 6. Generate symbol table
    print("  Generating symbol table...")
    symbol_generator = SymbolTableGenerator(subroutines, xrefs, sections)
    symbols = symbol_generator.generate_symbol_table()
    print(f"  Found {len(symbols)} symbol(s)")

    # 7. Analyze enhanced register usage
    print("  Analyzing enhanced register usage...")
    register_tracker = EnhancedRegisterTracker(lines, subroutines)
    lifecycles, dependencies, dead_code, optimizations = register_tracker.analyze_all()
    total_lifecycles = sum(len(lc) for lc in lifecycles.values())
    print(f"  Tracked {total_lifecycles} register lifecycle(s), {len(dead_code)} dead code instance(s)")

    print("=== Analysis Complete ===\n")

    # 8. Generate meaningful label names
    print("  Generating meaningful label names...")
    label_mapping = generate_meaningful_labels(lines, file_info['init_address'], file_info['play_address'])
    print(f"  Renamed {len(label_mapping)} labels (e.g., Label_52 -> Loop_ClearMemory)")

    # 8b. Collect all labels for hyperlink generation
    import re
    all_labels = set()
    for line in lines:
        # Find label definitions
        label_match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*):\s*$', line.strip())
        if label_match:
            label_name = label_match.group(1)
            # Use the mapped name if it was renamed
            if label_name in label_mapping:
                all_labels.add(label_mapping[label_name])
            else:
                all_labels.add(label_name)

    # Also add common data blocks that appear in expressions
    for line in lines:
        # Find identifiers like DataBlock_6, DataBlock_0, etc.
        for match in re.finditer(r'\b(DataBlock_\d+|Code_\d+|JumpTarget_\d+|Loop_\w+|Skip_\d+|Subroutine_\w+)\b', line):
            all_labels.add(match.group(1))

    print(f"  Found {len(all_labels)} unique labels for hyperlinking")

    # 9. Annotate each assembly line with inline comments (SIDwinder-compatible)
    print("  Annotating assembly lines...")
    annotated_lines = []

    # Memory map helper function (uses the same build_memory_map logic)
    def get_memory_region(addr: int) -> str:
        """Get the memory region name for an address

        Priority:
        1. Specific data sections (Wave Table, Pulse Table, etc.)
        2. General memory map (RAM/ROM/Program Memory, etc.)
        """
        # First, check if address is within any extracted data section
        # These take precedence over general memory regions
        for section in sections:
            if section.start_address <= addr <= section.end_address:
                return section.name

        # Fall back to general memory map based on load address
        load_addr = file_info.get('load_address', 0x1000)
        memory_map = build_memory_map(load_addr)
        for (start, end), region in memory_map.items():
            if start <= addr <= end:
                return region
        return 'Unknown'

    for i, line in enumerate(lines):
        # Skip completely blank lines
        if not line.strip():
            continue

        # Skip quasi-blank lines (just comment markers with no content)
        stripped = line.strip()
        if stripped.startswith('//;'):
            content_after = stripped[3:].strip()
            # Skip if it's just whitespace, dashes, or empty
            if not content_after or content_after == '-' * len(content_after):
                continue

        # Apply label mapping first (replace generic labels with meaningful names)
        line = apply_label_mapping(line, label_mapping)

        # Replace DataBlock_6 references with meaningful table names
        line = replace_datablock6_with_table_names(line)

        # Annotate SID register accesses with register names
        line = annotate_sid_registers(line)

        # Add hyperlinks to table names
        line = add_table_name_hyperlinks(line)

        # Add hyperlinks to labels (both definitions and references)
        line = add_label_hyperlinks(line, all_labels)

        # Then annotate the line (with correct ROM/RAM mapping based on load address)
        annotated_line = annotate_sidwinder_line(line, file_info.get('load_address', 0x1000))

        # Skip if annotation returned empty string (filtered blank line)
        if not annotated_line or not annotated_line.strip():
            continue

        # Check if we need to add a section header BEFORE this line (for DataBlock_6 .byte lines)
        section_header_to_add = None
        if '.byte' in stripped and i > 0:
            # Check if we're inside DataBlock_6
            # Look back to find if we're between DataBlock_6: and the next label
            in_datablock_6 = False
            for j in range(i - 1, max(0, i - 100), -1):
                prev_line = lines[j].strip()
                if re.match(r'^DataBlock_6:', prev_line):
                    in_datablock_6 = True
                    break
                elif re.match(r'^[A-Za-z_][A-Za-z0-9_]*:', prev_line) and not prev_line.startswith('DataBlock_6'):
                    break

            if in_datablock_6:
                # Extract address from this .byte line
                byte_addr_match = re.search(r'//;\s*\$([0-9A-Fa-f]+)', stripped)
                if byte_addr_match:
                    byte_addr = int(byte_addr_match.group(1), 16)

                    # Define DataBlock_6 memory sections (complete layout)
                    sections_map = [
                        (0x16A1, 0x1836, 'Voice/Channel Control Data'),
                        (0x1837, 0x1876, 'Pulse Table (64 bytes)'),
                        (0x1877, 0x18D9, 'Arpeggio Table Pointers'),
                        (0x18DA, 0x18F9, 'Wave Table (32 bytes)'),
                        (0x18FA, 0x190B, 'Wave Control Parameters'),
                        (0x190C, 0x192B, 'Wave Note Offsets (32 bytes)'),
                        (0x192C, 0x1A1D, 'Filter/Effect Control Data'),
                        (0x1A1E, 0x1A5D, 'Filter Table (64 bytes)'),
                        (0x1A5E, 0x1A6A, 'Reserved/Padding'),
                        (0x1A6B, 0x1ACA, 'Instrument Table (12 instruments × 8 bytes)'),
                        (0x1ACB, 0x27BA, 'Sequence/Arpeggio Data (3,312 bytes)'),
                    ]

                    # Find which section this byte address belongs to
                    for start, end, desc in sections_map:
                        if start <= byte_addr <= end:
                            # Check if this is the first line of a new section
                            prev_byte_addr = None
                            if i > 0:
                                prev_addr_match = re.search(r'//;\s*\$([0-9A-Fa-f]+)', lines[i-1])
                                if prev_addr_match:
                                    prev_byte_addr = int(prev_addr_match.group(1), 16)

                            # Add section header if we're entering a new section
                            if prev_byte_addr is None or prev_byte_addr < start or prev_byte_addr > end:
                                # Determine the anchor ID based on the section description
                                anchor_id = None
                                if 'Pulse Table' in desc:
                                    anchor_id = 'PulseTable'
                                elif 'Wave Table' in desc and 'Note Offsets' not in desc:
                                    anchor_id = 'WaveTable'
                                elif 'Wave Note Offsets' in desc:
                                    anchor_id = 'WaveNoteOffsets'
                                elif 'Wave Control' in desc:
                                    anchor_id = 'WaveControl'
                                elif 'Filter Table' in desc:
                                    anchor_id = 'FilterTable'
                                elif 'Filter/Effect Control' in desc:
                                    anchor_id = 'FilterControl'
                                elif 'Instrument Table' in desc:
                                    anchor_id = 'InstrumentTable'
                                elif 'Voice/Channel' in desc:
                                    anchor_id = 'VoiceControl'
                                elif 'Sequence/Arpeggio Data' in desc:
                                    anchor_id = 'SequenceData'
                                elif 'Arpeggio Table Pointers' in desc:
                                    anchor_id = 'ArpeggioPointers'
                                elif 'Reserved' in desc:
                                    anchor_id = 'Reserved'

                                if anchor_id:
                                    section_header_to_add = f';   [[ANCHOR:{anchor_id}]]┌─ [{desc}] (${start:04X}-${end:04X})\n'
                                else:
                                    section_header_to_add = f';   ┌─ [{desc}] (${start:04X}-${end:04X})\n'
                            break

        # Add the annotated line (with optional section header before it)
        if section_header_to_add:
            annotated_lines.append(section_header_to_add)
        annotated_lines.append(annotated_line)

        # Check if this is a DataBlock label - if so, add memory map annotation
        if re.match(r'^DataBlock_\d+:', stripped):
            # Look ahead to next line to get address range
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                # Extract address from comment like "//; $1047 - 1050"
                addr_match = re.search(r'//;\s*\$([0-9A-Fa-f]+)\s*-\s*([0-9A-Fa-f]+)', next_line)
                if addr_match:
                    start_addr = int(addr_match.group(1), 16)
                    end_addr = int(addr_match.group(2), 16)
                    region = get_memory_region(start_addr)
                    size = end_addr - start_addr + 1

                    # Add memory map annotation comment
                    annotation = f';   ├─ Location: ${start_addr:04X}-${end_addr:04X} ({size} bytes)\n'
                    annotation += f';   └─ Memory Region: {region}\n'
                    annotated_lines.append(annotation)

    # Add prominent EOF marker at the end (make it very visible with version info)
    from datetime import datetime
    annotated_lines.append('\n')  # Blank line before EOF
    annotated_lines.append(';' + '=' * 78 + '\n')
    annotated_lines.append(';' + '=' * 78 + '\n')
    annotated_lines.append(';\n')
    annotated_lines.append(';   END OF FILE - Stinsen\'s Last Night of \'89\n')
    annotated_lines.append(';\n')
    annotated_lines.append(';   SIDM2 Version: 3.0.1\n')
    annotated_lines.append(';   Generated: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + '\n')
    annotated_lines.append(';   Total Lines: ' + str(len(annotated_lines) + 5) + '\n')
    annotated_lines.append(';\n')
    annotated_lines.append(';   Tools Used:\n')
    annotated_lines.append(';     - SIDwinder 0.2.6 (Disassembler)\n')
    annotated_lines.append(';     - Python SID Parser (Metadata Extraction)\n')
    annotated_lines.append(';     - Enhanced Player Detector (Player Identification)\n')
    annotated_lines.append(';     - Python Assembly Annotator (Instruction Comments)\n')
    annotated_lines.append(';     - 6502 Register Tracker (Data Flow Analysis)\n')
    annotated_lines.append(';     - Label Name Generator (Semantic Naming)\n')
    annotated_lines.append(';\n')
    annotated_lines.append(';' + '=' * 78 + '\n')
    annotated_lines.append(';' + '=' * 78 + '\n')

    print(f"  Annotated {len(annotated_lines)} lines (+ EOF marker)")

    # Generate HTML using the existing function (with annotated lines)
    html = generate_html_export(
        input_path=input_path,
        file_info=file_info,
        subroutines=subroutines,
        sections=sections,
        symbols=symbols,
        xrefs=xrefs,
        patterns=patterns,
        loops=loops,
        branches=branches,
        cycle_counts=cycle_counts,
        call_graph=call_graph,
        lifecycles=lifecycles,
        dependencies=dependencies,
        dead_code=dead_code,
        optimizations=optimizations,
        lines=annotated_lines  # Use annotated lines instead of raw lines
    )

    return html

if __name__ == "__main__":
    sys.exit(main())
