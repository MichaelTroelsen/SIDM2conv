#!/usr/bin/env python3
"""
Annotating 6502 Disassembler for SID Files

Creates detailed annotated disassembly with:
- Routine identification (init, play, subroutines)
- Inline comments explaining each instruction
- Labeled branch targets and subroutines
- Pattern recognition for common operations
- Memory map and variable tables

Author: SIDM2 Project
Date: 2025-12-03
"""

import struct
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

# Reference: SF2-Packed SID Memory Layout
# Based on analysis of STINSENS_PLAYER_DISASSEMBLY.md and SF2PACKED_STINSENS_ANNOTATED_DISASSEMBLY.md
#
# MEMORY MAP (Typical SF2-Packed SID):
# ┌─────────────────┬──────────────────────────────────┐
# │ Address Range   │ Description                      │
# ├─────────────────┼──────────────────────────────────┤
# │ $1000-$1048     │ Jump table and header            │
# │ $1000-$1006     │ Init routine                     │
# │ $1006-$1900     │ Play routine and player code     │
# │ $1914-$1954     │ Wave table                       │
# │ $1A1E-$1A4E     │ Filter table                     │
# │ $1A3B-$1A7B     │ Pulse table                      │
# │ $1A6B-$1AAB     │ Instrument table                 │
# │ $1A8B-$1ACB     │ Arpeggio table                   │
# │ $1ADB-$1B9B     │ Command table                    │
# │ $1C00-$27BA     │ Music data                       │
# └─────────────────┴──────────────────────────────────┘
#
# KEY PLAYER VARIABLES (Zero Page & RAM):
# ┌─────────┬──────┬─────────────────────────────────────────┐
# │ Address │ Size │ Description                             │
# ├─────────┼──────┼─────────────────────────────────────────┤
# │ $FC-$FD │ 2    │ Temporary pointer for table/sequence    │
# │ $FE-$FF │ 2    │ Secondary pointer for data structures   │
# │ $1780   │ 1    │ Tempo counter (frames per row)          │
# │ $1781   │ 1    │ Player state flags                      │
# │ $1782   │ 1    │ Current subtune number                  │
# │ $1783   │ 1    │ Frame counter / timing                  │
# │ $178F+X │ 3    │ Per-voice: Note duration counter        │
# │ $1792+X │ 3    │ Per-voice: Sequence position            │
# │ $1795+X │ 3    │ Per-voice: Active flag                  │
# │ $1798+X │ 3    │ Per-voice: Wave table position          │
# │ $179B+X │ 3    │ Per-voice: Current instrument           │
# │ $17B0+X │ 3    │ Per-voice: Transpose value              │
# │ $17F8+X │ 3    │ Per-voice: Speed/timing flags           │
# └─────────┴──────┴─────────────────────────────────────────┘
#
# Note: X = voice number (0, 1, 2) for per-voice arrays

# 6502 opcode definitions (name, operand format, length)
OPCODES = {
    # ADC
    0x69: ("ADC", "#${:02X}", 2), 0x65: ("ADC", "${:02X}", 2), 0x75: ("ADC", "${:02X},X", 2),
    0x6D: ("ADC", "${:04X}", 3), 0x7D: ("ADC", "${:04X},X", 3), 0x79: ("ADC", "${:04X},Y", 3),
    0x61: ("ADC", "(${:02X},X)", 2), 0x71: ("ADC", "(${:02X}),Y", 2),
    # AND
    0x29: ("AND", "#${:02X}", 2), 0x25: ("AND", "${:02X}", 2), 0x35: ("AND", "${:02X},X", 2),
    0x2D: ("AND", "${:04X}", 3), 0x3D: ("AND", "${:04X},X", 3), 0x39: ("AND", "${:04X},Y", 3),
    0x21: ("AND", "(${:02X},X)", 2), 0x31: ("AND", "(${:02X}),Y", 2),
    # ASL
    0x0A: ("ASL", "A", 1), 0x06: ("ASL", "${:02X}", 2), 0x16: ("ASL", "${:02X},X", 2),
    0x0E: ("ASL", "${:04X}", 3), 0x1E: ("ASL", "${:04X},X", 3),
    # Branch instructions
    0x90: ("BCC", "${:04X}", 2), 0xB0: ("BCS", "${:04X}", 2), 0xF0: ("BEQ", "${:04X}", 2),
    0x30: ("BMI", "${:04X}", 2), 0xD0: ("BNE", "${:04X}", 2), 0x10: ("BPL", "${:04X}", 2),
    0x50: ("BVC", "${:04X}", 2), 0x70: ("BVS", "${:04X}", 2),
    # BIT
    0x24: ("BIT", "${:02X}", 2), 0x2C: ("BIT", "${:04X}", 3),
    # BRK, NOP
    0x00: ("BRK", "", 1), 0xEA: ("NOP", "", 1),
    # CLC, CLD, CLI, CLV, SEC, SED, SEI
    0x18: ("CLC", "", 1), 0xD8: ("CLD", "", 1), 0x58: ("CLI", "", 1), 0xB8: ("CLV", "", 1),
    0x38: ("SEC", "", 1), 0xF8: ("SED", "", 1), 0x78: ("SEI", "", 1),
    # CMP, CPX, CPY
    0xC9: ("CMP", "#${:02X}", 2), 0xC5: ("CMP", "${:02X}", 2), 0xD5: ("CMP", "${:02X},X", 2),
    0xCD: ("CMP", "${:04X}", 3), 0xDD: ("CMP", "${:04X},X", 3), 0xD9: ("CMP", "${:04X},Y", 3),
    0xC1: ("CMP", "(${:02X},X)", 2), 0xD1: ("CMP", "(${:02X}),Y", 2),
    0xE0: ("CPX", "#${:02X}", 2), 0xE4: ("CPX", "${:02X}", 2), 0xEC: ("CPX", "${:04X}", 3),
    0xC0: ("CPY", "#${:02X}", 2), 0xC4: ("CPY", "${:02X}", 2), 0xCC: ("CPY", "${:04X}", 3),
    # DEC, INC
    0xC6: ("DEC", "${:02X}", 2), 0xD6: ("DEC", "${:02X},X", 2),
    0xCE: ("DEC", "${:04X}", 3), 0xDE: ("DEC", "${:04X},X", 3),
    0xE6: ("INC", "${:02X}", 2), 0xF6: ("INC", "${:02X},X", 2),
    0xEE: ("INC", "${:04X}", 3), 0xFE: ("INC", "${:04X},X", 3),
    # DEX, DEY, INX, INY
    0xCA: ("DEX", "", 1), 0x88: ("DEY", "", 1), 0xE8: ("INX", "", 1), 0xC8: ("INY", "", 1),
    # EOR
    0x49: ("EOR", "#${:02X}", 2), 0x45: ("EOR", "${:02X}", 2), 0x55: ("EOR", "${:02X},X", 2),
    0x4D: ("EOR", "${:04X}", 3), 0x5D: ("EOR", "${:04X},X", 3), 0x59: ("EOR", "${:04X},Y", 3),
    0x41: ("EOR", "(${:02X},X)", 2), 0x51: ("EOR", "(${:02X}),Y", 2),
    # JMP, JSR
    0x4C: ("JMP", "${:04X}", 3), 0x6C: ("JMP", "(${:04X})", 3), 0x20: ("JSR", "${:04X}", 3),
    # LDA, LDX, LDY
    0xA9: ("LDA", "#${:02X}", 2), 0xA5: ("LDA", "${:02X}", 2), 0xB5: ("LDA", "${:02X},X", 2),
    0xAD: ("LDA", "${:04X}", 3), 0xBD: ("LDA", "${:04X},X", 3), 0xB9: ("LDA", "${:04X},Y", 3),
    0xA1: ("LDA", "(${:02X},X)", 2), 0xB1: ("LDA", "(${:02X}),Y", 2),
    0xA2: ("LDX", "#${:02X}", 2), 0xA6: ("LDX", "${:02X}", 2), 0xB6: ("LDX", "${:02X},Y", 2),
    0xAE: ("LDX", "${:04X}", 3), 0xBE: ("LDX", "${:04X},Y", 3),
    0xA0: ("LDY", "#${:02X}", 2), 0xA4: ("LDY", "${:02X}", 2), 0xB4: ("LDY", "${:02X},X", 2),
    0xAC: ("LDY", "${:04X}", 3), 0xBC: ("LDY", "${:04X},X", 3),
    # LSR, ASL, ROL, ROR
    0x4A: ("LSR", "A", 1), 0x46: ("LSR", "${:02X}", 2), 0x56: ("LSR", "${:02X},X", 2),
    0x4E: ("LSR", "${:04X}", 3), 0x5E: ("LSR", "${:04X},X", 3),
    0x2A: ("ROL", "A", 1), 0x26: ("ROL", "${:02X}", 2), 0x36: ("ROL", "${:02X},X", 2),
    0x2E: ("ROL", "${:04X}", 3), 0x3E: ("ROL", "${:04X},X", 3),
    0x6A: ("ROR", "A", 1), 0x66: ("ROR", "${:02X}", 2), 0x76: ("ROR", "${:02X},X", 2),
    0x6E: ("ROR", "${:04X}", 3), 0x7E: ("ROR", "${:04X},X", 3),
    # ORA
    0x09: ("ORA", "#${:02X}", 2), 0x05: ("ORA", "${:02X}", 2), 0x15: ("ORA", "${:02X},X", 2),
    0x0D: ("ORA", "${:04X}", 3), 0x1D: ("ORA", "${:04X},X", 3), 0x19: ("ORA", "${:04X},Y", 3),
    0x01: ("ORA", "(${:02X},X)", 2), 0x11: ("ORA", "(${:02X}),Y", 2),
    # PHA, PHP, PLA, PLP
    0x48: ("PHA", "", 1), 0x08: ("PHP", "", 1), 0x68: ("PLA", "", 1), 0x28: ("PLP", "", 1),
    # RTI, RTS
    0x40: ("RTI", "", 1), 0x60: ("RTS", "", 1),
    # SBC
    0xE9: ("SBC", "#${:02X}", 2), 0xE5: ("SBC", "${:02X}", 2), 0xF5: ("SBC", "${:02X},X", 2),
    0xED: ("SBC", "${:04X}", 3), 0xFD: ("SBC", "${:04X},X", 3), 0xF9: ("SBC", "${:04X},Y", 3),
    0xE1: ("SBC", "(${:02X},X)", 2), 0xF1: ("SBC", "(${:02X}),Y", 2),
    # STA, STX, STY
    0x85: ("STA", "${:02X}", 2), 0x95: ("STA", "${:02X},X", 2),
    0x8D: ("STA", "${:04X}", 3), 0x9D: ("STA", "${:04X},X", 3), 0x99: ("STA", "${:04X},Y", 3),
    0x81: ("STA", "(${:02X},X)", 2), 0x91: ("STA", "(${:02X}),Y", 2),
    0x86: ("STX", "${:02X}", 2), 0x96: ("STX", "${:02X},Y", 2), 0x8E: ("STX", "${:04X}", 3),
    0x84: ("STY", "${:02X}", 2), 0x94: ("STY", "${:02X},X", 2), 0x8C: ("STY", "${:04X}", 3),
    # TAX, TAY, TSX, TXA, TXS, TYA
    0xAA: ("TAX", "", 1), 0xA8: ("TAY", "", 1), 0xBA: ("TSX", "", 1),
    0x8A: ("TXA", "", 1), 0x9A: ("TXS", "", 1), 0x98: ("TYA", "", 1),
}

# SID register mapping
SID_REGISTERS = {
    0xD400: "Voice 1 Frequency Lo",
    0xD401: "Voice 1 Frequency Hi",
    0xD402: "Voice 1 Pulse Width Lo",
    0xD403: "Voice 1 Pulse Width Hi",
    0xD404: "Voice 1 Control Register",
    0xD405: "Voice 1 Attack/Decay",
    0xD406: "Voice 1 Sustain/Release",
    0xD407: "Voice 2 Frequency Lo",
    0xD408: "Voice 2 Frequency Hi",
    0xD409: "Voice 2 Pulse Width Lo",
    0xD40A: "Voice 2 Pulse Width Hi",
    0xD40B: "Voice 2 Control Register",
    0xD40C: "Voice 2 Attack/Decay",
    0xD40D: "Voice 2 Sustain/Release",
    0xD40E: "Voice 3 Frequency Lo",
    0xD40F: "Voice 3 Frequency Hi",
    0xD410: "Voice 3 Pulse Width Lo",
    0xD411: "Voice 3 Pulse Width Hi",
    0xD412: "Voice 3 Control Register",
    0xD413: "Voice 3 Attack/Decay",
    0xD414: "Voice 3 Sustain/Release",
    0xD415: "Filter Cutoff Lo",
    0xD416: "Filter Cutoff Hi",
    0xD417: "Filter Resonance/Routing",
    0xD418: "Filter Mode/Volume",
}


class AnnotatingDisassembler:
    """Sophisticated 6502 disassembler with pattern recognition and annotation"""

    def __init__(self, sid_path: Path):
        self.sid_path = sid_path

        # Analysis data structures (initialize BEFORE loading file)
        self.jsr_targets: Set[int] = set()  # Subroutine entry points
        self.branch_targets: Set[int] = set()  # Branch destinations
        self.labels: Dict[int, str] = {}  # Address -> label name
        self.comments: Dict[int, str] = {}  # Address -> comment
        self.sid_writes: Dict[int, List[int]] = defaultdict(list)  # Address -> SID registers written
        self.memory_regions = []  # Will be populated during loading

        # Load and analyze file
        self.load_sid_file()

    def load_sid_file(self):
        """Load and parse SID file"""
        with open(self.sid_path, 'rb') as f:
            data = f.read()

        # Parse PSID header
        self.magic = data[0:4].decode('ascii', errors='ignore')
        self.version = struct.unpack('>H', data[4:6])[0]
        data_offset = struct.unpack('>H', data[6:8])[0]
        load_addr = struct.unpack('>H', data[8:10])[0]
        self.init_addr = struct.unpack('>H', data[10:12])[0]
        self.play_addr = struct.unpack('>H', data[12:14])[0]
        self.songs = struct.unpack('>H', data[14:16])[0]

        self.name = data[0x16:0x36].decode('ascii', errors='ignore').rstrip('\x00')
        self.author = data[0x36:0x56].decode('ascii', errors='ignore').rstrip('\x00')
        self.copyright = data[0x56:0x76].decode('ascii', errors='ignore').rstrip('\x00')

        # Extract music data
        sid_data = data[data_offset:]
        self.load_addr = load_addr
        if load_addr == 0:
            self.load_addr = struct.unpack('<H', sid_data[0:2])[0]
            sid_data = sid_data[2:]

        self.sid_data = sid_data
        self.end_addr = self.load_addr + len(sid_data) - 1

        # Create 64KB memory model
        self.memory = bytearray(65536)
        for i, byte in enumerate(sid_data):
            self.memory[self.load_addr + i] = byte

        # Build memory map regions for annotation
        self.build_memory_map()

    def build_memory_map(self):
        """Build memory map with address ranges and descriptions."""
        # Define memory regions based on typical SF2-packed layout
        # Format: (start_addr, end_addr, description)
        self.memory_regions = [
            (self.load_addr, self.load_addr + 0x48, "Jump table and header"),
            (self.init_addr, self.play_addr - 1, "Init routine"),
            (self.play_addr, self.load_addr + 0x900, "Play routine and player code"),
            (self.load_addr + 0x914, self.load_addr + 0x954, "Wave table"),
            (self.load_addr + 0xA1E, self.load_addr + 0xA4E, "Filter table"),
            (self.load_addr + 0xA3B, self.load_addr + 0xA7B, "Pulse table"),
            (self.load_addr + 0xA6B, self.load_addr + 0xAAB, "Instrument table"),
            (self.load_addr + 0xA8B, self.load_addr + 0xACB, "Arpeggio table"),
            (self.load_addr + 0xADB, self.load_addr + 0xB9B, "Command table"),
            (self.load_addr + 0xC00, self.end_addr, "Music data"),
        ]
        # Sort by start address to ensure proper lookup
        self.memory_regions.sort(key=lambda x: x[0])

        # Build Key Player Variables mapping
        # Format: {address: (size, description, is_indexed)}
        self.player_variables = {
            # Zero page pointers
            0xFC: (2, "Temporary pointer for table/sequence access", False),
            0xFE: (2, "Secondary pointer for data structures", False),
            # Player state variables
            self.load_addr + 0x780: (1, "Tempo counter (frames per row)", False),
            self.load_addr + 0x781: (1, "Player state flags", False),
            self.load_addr + 0x782: (1, "Current subtune number", False),
            self.load_addr + 0x783: (1, "Frame counter / timing", False),
            # Per-voice arrays (indexed with X)
            self.load_addr + 0x78F: (3, "Per-voice: Note duration counter", True),
            self.load_addr + 0x792: (3, "Per-voice: Sequence position", True),
            self.load_addr + 0x795: (3, "Per-voice: Active flag", True),
            self.load_addr + 0x798: (3, "Per-voice: Wave table position", True),
            self.load_addr + 0x79B: (3, "Per-voice: Current instrument", True),
            self.load_addr + 0x7B0: (3, "Per-voice: Transpose value", True),
            self.load_addr + 0x7F8: (3, "Per-voice: Speed/timing flags", True),
        }

    def get_player_variable(self, addr: int, is_indexed: bool = False) -> str:
        """Get player variable description for given address."""
        # Check all variables to find matches
        for base_addr, (size, desc, indexed) in self.player_variables.items():
            # Check if address falls within this variable's range
            if base_addr <= addr < base_addr + size:
                # For indexed variables, require indexed addressing
                # For non-indexed variables, require non-indexed addressing
                if is_indexed == indexed:
                    return desc

        return ""  # No variable found

    def get_memory_region(self, addr: int) -> str:
        """Get memory region description for given address.
        Returns the most specific (smallest) region that contains the address.
        """
        matches = []
        for start, end, desc in self.memory_regions:
            if start <= addr <= end:
                size = end - start + 1
                matches.append((size, desc))

        if not matches:
            return ""  # No region found

        # Return the smallest (most specific) region
        matches.sort(key=lambda x: x[0])
        return matches[0][1]

    def analyze_code(self):
        """First pass: analyze code to identify targets and patterns"""
        pc = 0

        while pc < len(self.sid_data):
            addr = self.load_addr + pc
            opcode = self.sid_data[pc]

            if opcode not in OPCODES:
                pc += 1
                continue

            mnem, operand_fmt, size = OPCODES[opcode]

            # Identify JSR targets (subroutines)
            if mnem == "JSR" and size == 3:
                target = struct.unpack('<H', self.sid_data[pc+1:pc+3])[0]
                self.jsr_targets.add(target)

            # Identify branch targets
            elif mnem in ["BCC", "BCS", "BEQ", "BMI", "BNE", "BPL", "BVC", "BVS"]:
                offset = self.sid_data[pc + 1]
                if offset >= 128:
                    offset -= 256
                target = addr + 2 + offset
                self.branch_targets.add(target)

            # Identify SID writes
            elif mnem == "STA" and size == 3:
                target = struct.unpack('<H', self.sid_data[pc+1:pc+3])[0]
                if 0xD400 <= target <= 0xD418:
                    self.sid_writes[addr].append(target)

            pc += size

    def generate_comment(self, addr: int, opcode: int, operand_val: int, mnem: str, operand_str: str = "") -> str:
        """Generate intelligent comment for instruction"""
        comments = []

        # Check if this is an indexed addressing mode
        is_indexed = ",X" in operand_str or ",Y" in operand_str

        # Player variables (PRIORITY 1)
        if mnem in ["LDA", "STA", "LDX", "STX", "LDY", "STY", "INC", "DEC", "BIT", "CMP", "CPX", "CPY"]:
            var_desc = self.get_player_variable(operand_val, is_indexed)
            if var_desc:
                comments.append(f"; {var_desc}")
                return " ".join(comments)  # Return early with variable description

        # SID register writes (PRIORITY 2)
        if mnem in ["STA", "STX", "STY"] and 0xD400 <= operand_val <= 0xD418:
            reg_name = SID_REGISTERS.get(operand_val, "SID Register")
            comments.append(f"; {reg_name}")

        # Common immediate values (PRIORITY 3)
        elif mnem in ["LDA", "LDX", "LDY"] and "#$" in OPCODES[opcode][1]:
            if operand_val == 0x00:
                comments.append("; Clear/initialize")
            elif operand_val == 0x7F:
                comments.append("; End marker")
            elif operand_val == 0xFF:
                comments.append("; Loop marker / all bits set")

        # Comparisons (PRIORITY 4)
        elif mnem == "CMP":
            if operand_val == 0x01:
                comments.append("; Check if == 1")
            elif operand_val == 0x7F:
                comments.append("; Check for end marker")
            elif operand_val == 0xFF:
                comments.append("; Check for loop marker")

        return " ".join(comments) if comments else ""

    def assign_labels(self):
        """Assign meaningful labels to important addresses"""
        # Label init and play routines
        self.labels[self.init_addr] = "Init"
        self.labels[self.play_addr] = "Play"

        # Label subroutines
        for i, addr in enumerate(sorted(self.jsr_targets)):
            if addr not in self.labels:
                self.labels[addr] = f"Sub_{addr:04X}"

        # Label branch targets (loops)
        for addr in self.branch_targets:
            if addr not in self.labels:
                self.labels[addr] = f"L_{addr:04X}"

    def disassemble_instruction(self, pc: int) -> Tuple[str, int, str]:
        """Disassemble single instruction with annotation. Returns (asm_line, size, comment)"""
        addr = self.load_addr + pc
        opcode = self.sid_data[pc]

        if opcode not in OPCODES:
            return f"${addr:04X}  {opcode:02X}            .byte  ${opcode:02X}", 1, "; Unknown opcode"

        mnem, operand_fmt, size = OPCODES[opcode]

        # Get bytes
        instr_bytes = [self.sid_data[pc + i] if pc + i < len(self.sid_data) else 0 for i in range(size)]
        bytes_str = " ".join(f"{b:02X}" for b in instr_bytes).ljust(12)

        # Format operand
        comment = ""
        if size == 1:
            operand = operand_fmt
        elif size == 2:
            operand_val = instr_bytes[1]
            # Branch instructions
            if mnem in ["BCC", "BCS", "BEQ", "BMI", "BNE", "BPL", "BVC", "BVS"]:
                offset = operand_val if operand_val < 128 else operand_val - 256
                target = addr + 2 + offset
                operand = f"${target:04X}"
                if target in self.labels:
                    operand = self.labels[target]
                if offset < 0:
                    comment = f"; Jump back {-offset} bytes"
                else:
                    comment = f"; Jump forward {offset} bytes"
            else:
                operand = operand_fmt.format(operand_val)
                comment = self.generate_comment(addr, opcode, operand_val, mnem, operand)
        else:  # size == 3
            operand_val = struct.unpack('<H', self.sid_data[pc+1:pc+3])[0]
            operand = operand_fmt.format(operand_val)
            comment = self.generate_comment(addr, opcode, operand_val, mnem, operand)

            # JSR - add target label if available
            if mnem == "JSR" and operand_val in self.labels:
                operand = self.labels[operand_val]

        # Add memory region as fallback if no specific comment
        if not comment:
            # For memory operations, check the operand address for table regions
            # For other instructions, check the instruction address
            region_addr = addr
            if size >= 2 and mnem in ["LDA", "STA", "LDX", "STX", "LDY", "STY",
                                       "INC", "DEC", "BIT", "CMP", "CPX", "CPY",
                                       "AND", "ORA", "EOR", "ADC", "SBC"]:
                # Use operand address for memory access instructions
                if size == 2:
                    region_addr = operand_val
                elif size == 3:
                    region_addr = operand_val

            region = self.get_memory_region(region_addr)
            if region:
                comment = f"; [{region}]"

        # Format instruction line
        asm = f"{mnem:7} {operand}".ljust(20)
        line = f"${addr:04X}  {bytes_str}  {asm}"

        return line, size, comment

    def format_hex_dump(self, data: bytes, start_addr: int) -> str:
        """Format binary data as hex dump."""
        lines = []
        for i in range(0, len(data), 16):
            addr_offset = i
            hex_bytes = ' '.join(f'{b:02x}' for b in data[i:i+16])
            lines.append(f'{addr_offset:02x}: {hex_bytes}')
        return '\n'.join(lines)

    def decode_instruments(self) -> List[Dict]:
        """Decode instrument table into structured data."""
        instruments = []
        instr_offset = 0xA6B

        if instr_offset + 64 > len(self.sid_data):
            return instruments

        instr_data = self.sid_data[instr_offset:instr_offset+64]

        for i in range(8):
            base = i * 8
            if base + 8 <= len(instr_data):
                instruments.append({
                    'num': i,
                    'ad': instr_data[base + 0],
                    'sr': instr_data[base + 1],
                    'wave': instr_data[base + 2],
                    'pulse': instr_data[base + 3],
                    'filter': instr_data[base + 4],
                    'arp': instr_data[base + 5],
                    'flags': instr_data[base + 6],
                    'vib': instr_data[base + 7]
                })

        return instruments

    def write_table_section(self, f, title: str, start_offset: int, size: int,
                           format_desc: str, entries_desc: str = None):
        """Write a table format section with hexdump."""
        start_addr = self.load_addr + start_offset
        end_addr = start_addr + size - 1

        # Check if table exists in the file
        if start_offset + size > len(self.sid_data):
            return

        f.write(f"### {title}\n\n")
        f.write(f"Location: **${start_addr:04X}-${end_addr:04X}** ({size} bytes")
        if entries_desc:
            f.write(f", {entries_desc}")
        f.write(")\n\n")

        # Format description
        f.write("```asm\n")
        f.write(";===============================================================================\n")
        f.write(f"; {title}\n")
        f.write(";===============================================================================\n")
        f.write(format_desc)
        f.write("```\n\n")

        # Hex dump
        f.write(f"#### Hex Dump (from {self.name})\n\n")
        f.write("```\n")
        f.write(f"Address: ${start_addr:04X}-${end_addr:04X}  Size: {size} bytes")
        if entries_desc:
            f.write(f"  Count: {entries_desc}")
        f.write("\n")
        f.write("="*80 + "\n")

        table_data = self.sid_data[start_offset:start_offset+size]
        f.write(self.format_hex_dump(table_data, start_addr))
        f.write("\n```\n\n")

    def write_key_player_variables(self, f):
        """Write Key Player Variables section."""
        f.write("## Key Player Variables (Zero Page & RAM)\n\n")
        f.write("| Address | Size | Description |\n")
        f.write("|---------|------|-------------|\n")
        f.write("| $FC-$FD | 2    | Temporary pointer for table/sequence access |\n")
        f.write("| $FE-$FF | 2    | Secondary pointer for data structures |\n")
        f.write(f"| ${self.load_addr+0x780:04X}   | 1    | Tempo counter (frames per row) |\n")
        f.write(f"| ${self.load_addr+0x781:04X}   | 1    | Player state flags |\n")
        f.write(f"| ${self.load_addr+0x782:04X}   | 1    | Current subtune number |\n")
        f.write(f"| ${self.load_addr+0x783:04X}   | 1    | Frame counter / timing |\n")
        f.write(f"| ${self.load_addr+0x78F:04X}+X | 3    | Per-voice: Note duration counter |\n")
        f.write(f"| ${self.load_addr+0x792:04X}+X | 3    | Per-voice: Sequence position |\n")
        f.write(f"| ${self.load_addr+0x795:04X}+X | 3    | Per-voice: Active flag |\n")
        f.write(f"| ${self.load_addr+0x798:04X}+X | 3    | Per-voice: Wave table position |\n")
        f.write(f"| ${self.load_addr+0x79B:04X}+X | 3    | Per-voice: Current instrument |\n")
        f.write(f"| ${self.load_addr+0x7B0:04X}+X | 3    | Per-voice: Transpose value |\n")
        f.write(f"| ${self.load_addr+0x7F8:04X}+X | 3    | Per-voice: Speed/timing flags |\n\n")

    def write_player_execution_flow(self, f):
        """Write Player Execution Flow section."""
        f.write("## Player Execution Flow\n\n")
        f.write("### Initialization Sequence\n\n")
        f.write("1. **Entry**: Init routine called with subtune number in A register\n")
        f.write("2. **State Clear**: Zero out player state variables ($1782-$17F7)\n")
        f.write("3. **Configuration**: Load tempo, filter, and resonance settings\n")
        f.write("4. **Voice Setup**: Initialize speed and position for all 3 voices\n")
        f.write("5. **Flag Set**: Mark player as initialized ($1781 = $80)\n\n")

        f.write("### Play Loop (50Hz PAL)\n\n")
        f.write("1. **Tempo Check**: Decrement tempo counter, reload if zero\n")
        f.write("2. **Voice Processing** (for each of 3 voices):\n")
        f.write("   - Check if voice needs new note\n")
        f.write("   - Read sequence data (note, instrument, command)\n")
        f.write("   - Process transpose values\n")
        f.write("   - Load instrument parameters\n")
        f.write("   - Execute wave table programs\n")
        f.write("3. **SID Updates**:\n")
        f.write("   - Set frequency (from note + transpose)\n")
        f.write("   - Set waveform and gate control\n")
        f.write("   - Apply ADSR envelope\n")
        f.write("   - Update pulse width (if used)\n")
        f.write("   - Update filter (if enabled)\n")
        f.write("4. **Return**: Exit until next frame\n\n")

    def write_key_data_structures(self, f):
        """Write Key Data Structures section."""
        f.write("## Key Data Structures\n\n")

        f.write(f"### Sequence Pointers (${self.load_addr+0x99F:04X}-${self.load_addr+0x9A5:04X})\n\n")
        f.write("```\n")
        f.write(f"${self.load_addr+0x99F:04X}-${self.load_addr+0x9A0:04X}: Voice 1 sequence pointer (16-bit)\n")
        f.write(f"${self.load_addr+0x9A1:04X}-${self.load_addr+0x9A2:04X}: Voice 2 sequence pointer (16-bit)\n")
        f.write(f"${self.load_addr+0x9A3:04X}-${self.load_addr+0x9A4:04X}: Voice 3 sequence pointer (16-bit)\n")
        f.write("```\n\n")

        f.write("### Tempo Table\n\n")
        f.write("Speed values in frames per row, terminated by $7F wrap marker.\n\n")
        f.write("```\n")
        f.write("Format: [speed1] [speed2] ... [speedN] $7F [wrap_position]\n")
        f.write("Example: 02 02 02 02 7F 00 = constant speed of 2 frames/row\n")
        f.write("```\n\n")

        f.write("### Per-Voice State\n\n")
        f.write("Each voice (0-2) maintains separate state in parallel arrays:\n\n")
        f.write("```\n")
        f.write(f"${self.load_addr+0x78F:04X}+X: Note duration counter (counts down to 0)\n")
        f.write(f"${self.load_addr+0x792:04X}+X: Current position in sequence data\n")
        f.write(f"${self.load_addr+0x795:04X}+X: Sequence active flag (0=inactive, 1=active)\n")
        f.write(f"${self.load_addr+0x798:04X}+X: Current position in wave table program\n")
        f.write(f"${self.load_addr+0x79B:04X}+X: Current instrument number (0-7)\n")
        f.write(f"${self.load_addr+0x7B0:04X}+X: Transpose value (semitones ± 12)\n")
        f.write(f"${self.load_addr+0x7F8:04X}+X: Voice speed flag (timing divisor)\n")
        f.write("```\n\n")

    def write_notes_on_implementation(self, f):
        """Write Notes on Implementation section."""
        f.write("## Notes on This Implementation\n\n")
        f.write("This SF2-packed player uses several optimization techniques:\n\n")
        f.write("1. **Table-Driven Design**: All sound parameters stored in compact tables\n")
        f.write("2. **Programmatic Control**: Wave, pulse, and filter tables contain mini-programs\n")
        f.write("3. **Per-Voice State**: Each voice independently tracks position and timing\n")
        f.write("4. **Tempo Flexibility**: Variable speed system with loop markers\n")
        f.write("5. **Transpose System**: In-sequence transpose adjustments (values $A0+)\n")
        f.write("6. **Gate Control**: Explicit gate on/off for envelope precision\n")
        f.write("7. **Command System**: Effects like slides, vibrato, arpeggios via command table\n")
        f.write("8. **Hard Restart**: Prevents ADSR bugs with 2-frame gate-off before notes\n\n")

    def write_memory_usage(self, f):
        """Write Memory Usage section."""
        f.write("## Memory Usage\n\n")

        code_size = 0x6A1
        tables_size = (0xB9B - 0x914) + 1
        music_size = self.end_addr - (self.load_addr + 0xC00) + 1
        total_size = self.end_addr - self.load_addr + 1

        f.write(f"- **Player code**: ~{code_size:,} bytes (${self.load_addr:04X}-${self.load_addr+code_size-1:04X})\n")
        f.write(f"- **Data tables**: ~{tables_size:,} bytes (${self.load_addr+0x914:04X}-${self.load_addr+0xB9B:04X})\n")
        f.write(f"- **Music data**: ~{music_size:,} bytes (${self.load_addr+0xC00:04X}-${self.end_addr:04X})\n")
        f.write(f"- **Total**: ~{total_size:,} bytes\n\n")

    def write_data_tables(self, f):
        """Write data tables section with format descriptions and hex dumps."""
        # Tables are subsections within Annotated Disassembly, not a separate section

        # Instrument Table
        self.write_table_section(f,
            "Instrument Table Format",
            0xA6B, 64,
            """; Offset 0: Attack/Decay (ADSR)
; Offset 1: Sustain/Release (ADSR)
; Offset 2: Wave table pointer
; Offset 3: Pulse table pointer
; Offset 4: Filter table pointer
; Offset 5: Arpeggio table pointer
; Offset 6: Flags/Options
; Offset 7: Vibrato/Other settings
""",
            "8 instruments × 8 bytes"
        )

        # Add decoded instruments table
        instruments = self.decode_instruments()
        if instruments:
            f.write("#### Decoded Instruments\n\n")
            f.write("| Inst | AD   | SR   | Wave | Pulse | Filter | Arp  | Flags | Vib  |\n")
            f.write("|------|------|------|------|-------|--------|------|-------|------|\n")
            for instr in instruments:
                f.write(f"| {instr['num']}    | ${instr['ad']:02X}  | ${instr['sr']:02X}  | ${instr['wave']:02X}  | ${instr['pulse']:02X}   | ${instr['filter']:02X}    | ${instr['arp']:02X}  | ${instr['flags']:02X}   | ${instr['vib']:02X}  |\n")
            f.write("\n")

        # Wave Table
        self.write_table_section(f,
            "Wave Table Format",
            0x914, 64,
            """; $0914-$0933: Note offsets (32 entries)
;   Each byte is a note offset (0-95) or special marker:
;   $7F = Loop marker
;   $7E = Gate on (sustain)
;   $80 = Note offset special (recalculate frequency)
;
; $0934-$0953: Waveforms (32 entries)
;   Bits 0-3: Waveform type
;     $01 = Triangle
;     $02 = Sawtooth
;     $04 = Pulse
;     $08 = Noise
;   Bit 4: Gate bit
;   Bits 5-7: Additional control flags
""",
            "32 notes + 32 waveforms"
        )

        # Pulse Table
        self.write_table_section(f,
            "Pulse Table Format",
            0xA3B, 64,
            """; Byte 0: Initial pulse width value (bits 0-7 of 12-bit value)
; Byte 1: Delta (change per frame)
; Byte 2: Duration (frames to run)
; Byte 3: Next entry index (or $7F for loop)
;
; Each entry creates a pulse width sweep program.
; Multiple entries can be chained together for complex modulation.
""",
            "16 entries × 4 bytes"
        )

        # Filter Table
        self.write_table_section(f,
            "Filter Table Format",
            0xA1E, 48,
            """; Byte 0: Initial cutoff frequency (0-255)
; Byte 1: Delta (change per frame)
; Byte 2: Duration (frames to run)
;
; Each entry creates a filter sweep program.
; Filter type and resonance are set separately in init routine.
""",
            "16 entries × 3 bytes"
        )

        # Arpeggio Table
        self.write_table_section(f,
            "Arpeggio Table Format",
            0xA8B, 64,
            """; Byte 0-3: Note offsets (semitones)
;   Each byte is added to the base note to create chord notes.
;   Cycles through all 4 bytes to create arpeggio effect.
;   Common patterns:
;     00 04 07 00 = Major chord (root, major 3rd, 5th)
;     00 03 07 00 = Minor chord (root, minor 3rd, 5th)
;     00 0C 00 0C = Octave jump
""",
            "16 entries × 4 bytes"
        )

        # Command Table
        self.write_table_section(f,
            "Command Table Format",
            0xADB, 192,
            """; Byte 0: Command type
;   $00 = Slide
;   $01 = Vibrato
;   $02 = Portamento
;   $03 = Arpeggio
;   $04 = Fret
;   $08 = ADSR (note-based)
;   $09 = ADSR (persistent)
;   $0A = Index Filter
;   $0B = Index Wave
;   $0C = Index Pulse
;   $0D = Tempo
;   $0E = Volume
;   $0F = Demo flag
;
; Byte 1: Parameter 1 (command-specific)
; Byte 2: Parameter 2 (command-specific)
""",
            "64 commands × 3 bytes"
        )

    def generate_markdown(self, output_path: Path):
        """Generate complete annotated disassembly markdown document"""

        # Analyze code first
        print("Analyzing code structure...")
        self.analyze_code()
        self.assign_labels()

        with open(output_path, 'w', encoding='utf-8') as f:
            # Header
            f.write(f"# Complete Annotated Disassembly: {self.name}\n\n")
            f.write(f"**Author:** {self.author}\n\n")
            if self.copyright:
                f.write(f"**Copyright:** {self.copyright}\n\n")
            f.write("**Player Type:** SID Factory II SF2-Packed Format\n\n")
            f.write("---\n\n")

            # File info
            f.write("## File Information\n\n")
            f.write(f"- **Format:** {self.magic} v{self.version}\n")
            f.write(f"- **Load Address:** ${self.load_addr:04X}\n")
            f.write(f"- **Init Address:** ${self.init_addr:04X}\n")
            f.write(f"- **Play Address:** ${self.play_addr:04X}\n")
            f.write(f"- **Data Size:** {len(self.sid_data):,} bytes\n")
            f.write(f"- **End Address:** ${self.end_addr:04X}\n\n")

            # Memory map
            f.write("## Memory Map\n\n")
            f.write("| Address Range | Description |\n")
            f.write("|---------------|-------------|\n")
            f.write(f"| ${self.load_addr:04X}-${self.load_addr+0x48:04X} | Jump table and header |\n")
            f.write(f"| ${self.init_addr:04X}-{self.play_addr:04X} | Init routine |\n")
            f.write(f"| ${self.play_addr:04X}-${self.load_addr+0x900:04X} | Play routine and player code |\n")
            f.write(f"| ${self.load_addr+0x914:04X}-${self.load_addr+0x954:04X} | Wave table |\n")
            f.write(f"| ${self.load_addr+0xA1E:04X}-${self.load_addr+0xA4E:04X} | Filter table |\n")
            f.write(f"| ${self.load_addr+0xA3B:04X}-${self.load_addr+0xA7B:04X} | Pulse table |\n")
            f.write(f"| ${self.load_addr+0xA6B:04X}-${self.load_addr+0xAAB:04X} | Instrument table |\n")
            f.write(f"| ${self.load_addr+0xA8B:04X}-${self.load_addr+0xACB:04X} | Arpeggio table |\n")
            f.write(f"| ${self.load_addr+0xADB:04X}-${self.load_addr+0xB9B:04X} | Command table |\n")
            f.write(f"| ${self.load_addr+0xC00:04X}-${self.end_addr:04X} | Music data |\n\n")

            # Key Player Variables
            self.write_key_player_variables(f)

            # Annotated disassembly
            f.write("## Annotated Disassembly\n\n")

            # Disassemble code in logical sections
            code_end = min(0x6A1, len(self.sid_data))

            # Determine section boundaries
            init_start = 0
            play_start = self.play_addr - self.load_addr if self.play_addr > self.load_addr else 3
            play_end = code_end

            # Init Routine Section
            f.write(f"### Init Routine (${self.init_addr:04X}-${self.load_addr + play_start - 1:04X})\n\n")
            f.write("```asm\n")
            f.write(";===============================================================================\n")
            f.write("; Init Routine - Called once to initialize the player\n")
            f.write(f"; Entry: A = subtune number (0-based)\n")
            f.write(";===============================================================================\n")

            pc = init_start
            while pc < play_start:
                addr = self.load_addr + pc

                if addr in self.labels:
                    f.write(f"\n{self.labels[addr]}:\n")

                if addr == self.init_addr and pc > 0:
                    f.write("\n;---------------------------------------------------------------\n")
                    f.write("; Actual Init Code Starts Here\n")
                    f.write(";---------------------------------------------------------------\n")

                line, size, comment = self.disassemble_instruction(pc)

                if comment:
                    f.write(f"{line}  {comment}\n")
                else:
                    f.write(f"{line}\n")

                pc += size

            f.write("```\n\n")

            # Play Routine Section
            f.write(f"### Play Routine (${self.play_addr:04X} and beyond)\n\n")
            f.write("The play routine is called 50 times per second (PAL) to update the music.\n\n")
            f.write("```asm\n")
            f.write(";===============================================================================\n")
            f.write("; Main Play Loop - Processes each voice and updates SID registers\n")
            f.write(";===============================================================================\n")

            pc = play_start
            while pc < play_end:
                addr = self.load_addr + pc

                if addr in self.labels:
                    f.write(f"\n{self.labels[addr]}:\n")

                if addr == self.play_addr:
                    f.write("\n;---------------------------------------------------------------\n")
                    f.write("; Play Routine Entry Point\n")
                    f.write(";---------------------------------------------------------------\n")

                line, size, comment = self.disassemble_instruction(pc)

                if comment:
                    f.write(f"{line}  {comment}\n")
                else:
                    f.write(f"{line}\n")

                pc += size

            f.write("```\n\n")

            # Data Tables Section
            self.write_data_tables(f)

            # Player Execution Flow
            self.write_player_execution_flow(f)

            # Key Data Structures
            self.write_key_data_structures(f)

            # Notes on Implementation
            self.write_notes_on_implementation(f)

            # Memory Usage
            self.write_memory_usage(f)

            # Footer
            f.write("---\n\n")
            f.write(f"*This disassembly documents the SF2-packed format as used in \"{self.name}\"*\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python annotating_disassembler.py <sid_file> [output.md]")
        sys.exit(1)

    sid_path = Path(sys.argv[1])
    if not sid_path.exists():
        print(f"Error: File not found: {sid_path}")
        sys.exit(1)

    output_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else Path(f"docs/{sid_path.stem}_ANNOTATED_DISASSEMBLY.md")

    print(f"Creating annotated disassembly for {sid_path.name}...")
    disasm = AnnotatingDisassembler(sid_path)
    disasm.generate_markdown(output_path)
    print(f"Complete! Documentation written to {output_path}")
    print(f"  File size: {output_path.stat().st_size:,} bytes")


if __name__ == '__main__':
    main()
