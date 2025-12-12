"""6502 CPU Disassembler for driver code relocation.

This module provides 6502 instruction decoding to identify relocatable
addresses in driver code during SF2 packing.
"""

from typing import Tuple, Optional
from enum import Enum


class AddressingMode(Enum):
    """6502 addressing modes."""
    IMP = 'Implied'           # BRK, RTS
    IMM = 'Immediate'         # LDA #$00
    ZP = 'Zero Page'          # LDA $00
    ZPX = 'Zero Page,X'       # LDA $00,X
    ZPY = 'Zero Page,Y'       # LDX $00,Y
    ABS = 'Absolute'          # LDA $1000
    ABX = 'Absolute,X'        # LDA $1000,X
    ABY = 'Absolute,Y'        # LDA $1000,Y
    IND = 'Indirect'          # JMP ($1000)
    IZX = 'Indexed Indirect'  # LDA ($00,X)
    IZY = 'Indirect Indexed'  # LDA ($00),Y
    REL = 'Relative'          # BNE $1000


class Instruction:
    """Represents a single 6502 instruction."""

    def __init__(self, address: int, opcode: int, mnemonic: str,
                 mode: AddressingMode, operand: Optional[int] = None):
        self.address = address
        self.opcode = opcode
        self.mnemonic = mnemonic
        self.mode = mode
        self.operand = operand
        self.size = self._compute_size()

    def _compute_size(self) -> int:
        """Compute instruction size in bytes."""
        if self.mode in (AddressingMode.IMP,):
            return 1
        elif self.mode in (AddressingMode.IMM, AddressingMode.ZP,
                           AddressingMode.ZPX, AddressingMode.ZPY,
                           AddressingMode.IZX, AddressingMode.IZY,
                           AddressingMode.REL):
            return 2
        elif self.mode in (AddressingMode.ABS, AddressingMode.ABX,
                           AddressingMode.ABY, AddressingMode.IND):
            return 3
        return 1

    def is_relocatable(self) -> bool:
        """Check if this instruction contains a relocatable address.

        Absolute addressing modes (ABS, ABX, ABY, IND) contain 16-bit
        addresses that need relocation when driver code moves.
        """
        return self.mode in (AddressingMode.ABS, AddressingMode.ABX,
                             AddressingMode.ABY, AddressingMode.IND)

    def __repr__(self) -> str:
        if self.operand is None:
            return f"${self.address:04X}: {self.mnemonic}"
        elif self.mode == AddressingMode.IMM:
            return f"${self.address:04X}: {self.mnemonic} #${self.operand:02X}"
        elif self.mode in (AddressingMode.ZP, AddressingMode.REL):
            return f"${self.address:04X}: {self.mnemonic} ${self.operand:02X}"
        else:
            return f"${self.address:04X}: {self.mnemonic} ${self.operand:04X}"


# 6502 Opcode table: opcode -> (mnemonic, addressing_mode)
OPCODE_TABLE = {
    # ADC
    0x69: ('ADC', AddressingMode.IMM),
    0x65: ('ADC', AddressingMode.ZP),
    0x75: ('ADC', AddressingMode.ZPX),
    0x6D: ('ADC', AddressingMode.ABS),
    0x7D: ('ADC', AddressingMode.ABX),
    0x79: ('ADC', AddressingMode.ABY),
    0x61: ('ADC', AddressingMode.IZX),
    0x71: ('ADC', AddressingMode.IZY),

    # AND
    0x29: ('AND', AddressingMode.IMM),
    0x25: ('AND', AddressingMode.ZP),
    0x35: ('AND', AddressingMode.ZPX),
    0x2D: ('AND', AddressingMode.ABS),
    0x3D: ('AND', AddressingMode.ABX),
    0x39: ('AND', AddressingMode.ABY),
    0x21: ('AND', AddressingMode.IZX),
    0x31: ('AND', AddressingMode.IZY),

    # ASL
    0x0A: ('ASL', AddressingMode.IMP),
    0x06: ('ASL', AddressingMode.ZP),
    0x16: ('ASL', AddressingMode.ZPX),
    0x0E: ('ASL', AddressingMode.ABS),
    0x1E: ('ASL', AddressingMode.ABX),

    # Branch instructions
    0x90: ('BCC', AddressingMode.REL),
    0xB0: ('BCS', AddressingMode.REL),
    0xF0: ('BEQ', AddressingMode.REL),
    0x30: ('BMI', AddressingMode.REL),
    0xD0: ('BNE', AddressingMode.REL),
    0x10: ('BPL', AddressingMode.REL),
    0x50: ('BVC', AddressingMode.REL),
    0x70: ('BVS', AddressingMode.REL),

    # BIT
    0x24: ('BIT', AddressingMode.ZP),
    0x2C: ('BIT', AddressingMode.ABS),

    # BRK
    0x00: ('BRK', AddressingMode.IMP),

    # Clear/Set flags
    0x18: ('CLC', AddressingMode.IMP),
    0xD8: ('CLD', AddressingMode.IMP),
    0x58: ('CLI', AddressingMode.IMP),
    0xB8: ('CLV', AddressingMode.IMP),
    0x38: ('SEC', AddressingMode.IMP),
    0xF8: ('SED', AddressingMode.IMP),
    0x78: ('SEI', AddressingMode.IMP),

    # CMP
    0xC9: ('CMP', AddressingMode.IMM),
    0xC5: ('CMP', AddressingMode.ZP),
    0xD5: ('CMP', AddressingMode.ZPX),
    0xCD: ('CMP', AddressingMode.ABS),
    0xDD: ('CMP', AddressingMode.ABX),
    0xD9: ('CMP', AddressingMode.ABY),
    0xC1: ('CMP', AddressingMode.IZX),
    0xD1: ('CMP', AddressingMode.IZY),

    # CPX
    0xE0: ('CPX', AddressingMode.IMM),
    0xE4: ('CPX', AddressingMode.ZP),
    0xEC: ('CPX', AddressingMode.ABS),

    # CPY
    0xC0: ('CPY', AddressingMode.IMM),
    0xC4: ('CPY', AddressingMode.ZP),
    0xCC: ('CPY', AddressingMode.ABS),

    # DEC
    0xC6: ('DEC', AddressingMode.ZP),
    0xD6: ('DEC', AddressingMode.ZPX),
    0xCE: ('DEC', AddressingMode.ABS),
    0xDE: ('DEC', AddressingMode.ABX),

    # DEX, DEY
    0xCA: ('DEX', AddressingMode.IMP),
    0x88: ('DEY', AddressingMode.IMP),

    # EOR
    0x49: ('EOR', AddressingMode.IMM),
    0x45: ('EOR', AddressingMode.ZP),
    0x55: ('EOR', AddressingMode.ZPX),
    0x4D: ('EOR', AddressingMode.ABS),
    0x5D: ('EOR', AddressingMode.ABX),
    0x59: ('EOR', AddressingMode.ABY),
    0x41: ('EOR', AddressingMode.IZX),
    0x51: ('EOR', AddressingMode.IZY),

    # INC
    0xE6: ('INC', AddressingMode.ZP),
    0xF6: ('INC', AddressingMode.ZPX),
    0xEE: ('INC', AddressingMode.ABS),
    0xFE: ('INC', AddressingMode.ABX),

    # INX, INY
    0xE8: ('INX', AddressingMode.IMP),
    0xC8: ('INY', AddressingMode.IMP),

    # JMP
    0x4C: ('JMP', AddressingMode.ABS),
    0x6C: ('JMP', AddressingMode.IND),

    # JSR
    0x20: ('JSR', AddressingMode.ABS),

    # LDA
    0xA9: ('LDA', AddressingMode.IMM),
    0xA5: ('LDA', AddressingMode.ZP),
    0xB5: ('LDA', AddressingMode.ZPX),
    0xAD: ('LDA', AddressingMode.ABS),
    0xBD: ('LDA', AddressingMode.ABX),
    0xB9: ('LDA', AddressingMode.ABY),
    0xA1: ('LDA', AddressingMode.IZX),
    0xB1: ('LDA', AddressingMode.IZY),

    # LDX
    0xA2: ('LDX', AddressingMode.IMM),
    0xA6: ('LDX', AddressingMode.ZP),
    0xB6: ('LDX', AddressingMode.ZPY),
    0xAE: ('LDX', AddressingMode.ABS),
    0xBE: ('LDX', AddressingMode.ABY),

    # LDY
    0xA0: ('LDY', AddressingMode.IMM),
    0xA4: ('LDY', AddressingMode.ZP),
    0xB4: ('LDY', AddressingMode.ZPX),
    0xAC: ('LDY', AddressingMode.ABS),
    0xBC: ('LDY', AddressingMode.ABX),

    # LSR
    0x4A: ('LSR', AddressingMode.IMP),
    0x46: ('LSR', AddressingMode.ZP),
    0x56: ('LSR', AddressingMode.ZPX),
    0x4E: ('LSR', AddressingMode.ABS),
    0x5E: ('LSR', AddressingMode.ABX),

    # NOP
    0xEA: ('NOP', AddressingMode.IMP),

    # ORA
    0x09: ('ORA', AddressingMode.IMM),
    0x05: ('ORA', AddressingMode.ZP),
    0x15: ('ORA', AddressingMode.ZPX),
    0x0D: ('ORA', AddressingMode.ABS),
    0x1D: ('ORA', AddressingMode.ABX),
    0x19: ('ORA', AddressingMode.ABY),
    0x01: ('ORA', AddressingMode.IZX),
    0x11: ('ORA', AddressingMode.IZY),

    # Stack operations
    0x48: ('PHA', AddressingMode.IMP),
    0x08: ('PHP', AddressingMode.IMP),
    0x68: ('PLA', AddressingMode.IMP),
    0x28: ('PLP', AddressingMode.IMP),

    # ROL
    0x2A: ('ROL', AddressingMode.IMP),
    0x26: ('ROL', AddressingMode.ZP),
    0x36: ('ROL', AddressingMode.ZPX),
    0x2E: ('ROL', AddressingMode.ABS),
    0x3E: ('ROL', AddressingMode.ABX),

    # ROR
    0x6A: ('ROR', AddressingMode.IMP),
    0x66: ('ROR', AddressingMode.ZP),
    0x76: ('ROR', AddressingMode.ZPX),
    0x6E: ('ROR', AddressingMode.ABS),
    0x7E: ('ROR', AddressingMode.ABX),

    # RTI, RTS
    0x40: ('RTI', AddressingMode.IMP),
    0x60: ('RTS', AddressingMode.IMP),

    # SBC
    0xE9: ('SBC', AddressingMode.IMM),
    0xE5: ('SBC', AddressingMode.ZP),
    0xF5: ('SBC', AddressingMode.ZPX),
    0xED: ('SBC', AddressingMode.ABS),
    0xFD: ('SBC', AddressingMode.ABX),
    0xF9: ('SBC', AddressingMode.ABY),
    0xE1: ('SBC', AddressingMode.IZX),
    0xF1: ('SBC', AddressingMode.IZY),

    # STA
    0x85: ('STA', AddressingMode.ZP),
    0x95: ('STA', AddressingMode.ZPX),
    0x8D: ('STA', AddressingMode.ABS),
    0x9D: ('STA', AddressingMode.ABX),
    0x99: ('STA', AddressingMode.ABY),
    0x81: ('STA', AddressingMode.IZX),
    0x91: ('STA', AddressingMode.IZY),

    # STX
    0x86: ('STX', AddressingMode.ZP),
    0x96: ('STX', AddressingMode.ZPY),
    0x8E: ('STX', AddressingMode.ABS),

    # STY
    0x84: ('STY', AddressingMode.ZP),
    0x94: ('STY', AddressingMode.ZPX),
    0x8C: ('STY', AddressingMode.ABS),

    # Register transfers
    0xAA: ('TAX', AddressingMode.IMP),
    0xA8: ('TAY', AddressingMode.IMP),
    0xBA: ('TSX', AddressingMode.IMP),
    0x8A: ('TXA', AddressingMode.IMP),
    0x9A: ('TXS', AddressingMode.IMP),
    0x98: ('TYA', AddressingMode.IMP),
}

# Complete 256-byte instruction size table for ALL 6502 opcodes
# Includes documented and undocumented/illegal opcodes
# 1 = 1 byte (implied/accumulator), 2 = 2 bytes (immediate/zp/relative), 3 = 3 bytes (absolute)
INSTRUCTION_SIZES = [
    1,2,0,0,2,2,2,0,1,2,1,0,3,3,3,0,  # $00-$0F
    2,2,0,0,2,2,2,0,1,3,1,0,3,3,3,0,  # $10-$1F
    3,2,0,0,2,2,2,0,1,2,1,0,3,3,3,0,  # $20-$2F
    2,2,0,0,2,2,2,0,1,3,1,0,3,3,3,0,  # $30-$3F
    1,2,0,0,2,2,2,0,1,2,1,0,3,3,3,0,  # $40-$4F
    2,2,0,0,2,2,2,0,1,3,1,0,3,3,3,0,  # $50-$5F
    1,2,0,0,2,2,2,0,1,2,1,0,3,3,3,0,  # $60-$6F
    2,2,0,0,2,2,2,0,1,3,1,0,3,3,3,0,  # $70-$7F
    2,2,0,0,2,2,2,0,1,2,1,0,3,3,3,0,  # $80-$8F
    2,2,0,0,2,2,2,0,1,3,1,0,3,3,3,0,  # $90-$9F
    2,2,2,0,2,2,2,0,1,2,1,0,3,3,3,0,  # $A0-$AF
    2,2,0,0,2,2,2,0,1,3,1,0,3,3,3,0,  # $B0-$BF
    2,2,0,0,2,2,2,0,1,2,1,0,3,3,3,0,  # $C0-$CF
    2,2,0,0,2,2,2,0,1,3,1,0,3,3,3,0,  # $D0-$DF
    2,2,0,0,2,2,2,0,1,2,1,0,3,3,3,0,  # $E0-$EF
    2,2,0,0,2,2,2,0,1,3,1,0,3,3,3,0,  # $F0-$FF
]

# Set of opcodes that use absolute addressing modes (need relocation)
# Includes ABS ($xxxx), ABX ($xxxx,X), ABY ($xxxx,Y), IND (JMP ($xxxx))
RELOCATABLE_OPCODES = {
    # ABS mode opcodes (column 4 and 12, some in column 8)
    0x0D, 0x0E,  # ORA/ASL abs
    0x2C, 0x2D, 0x2E,  # BIT/AND/ROL abs
    0x4C, 0x4D, 0x4E,  # JMP/EOR/LSR abs
    0x6C, 0x6D, 0x6E,  # JMP ind/ADC/ROR abs
    0x8C, 0x8D, 0x8E,  # STY/STA/STX abs
    0xAC, 0xAD, 0xAE,  # LDY/LDA/LDX abs
    0xCC, 0xCD, 0xCE,  # CPY/CMP/DEC abs
    0xEC, 0xED, 0xEE,  # CPX/SBC/INC abs
    0x20,  # JSR abs
    # ABX mode opcodes (column 13)
    0x1D, 0x1E,  # ORA/ASL abs,X
    0x3D, 0x3E,  # AND/ROL abs,X
    0x5D, 0x5E,  # EOR/LSR abs,X
    0x7D, 0x7E,  # ADC/ROR abs,X
    0x9D,  # STA abs,X
    0xBC, 0xBD,  # LDY/LDA abs,X
    0xDD, 0xDE,  # CMP/DEC abs,X
    0xFD, 0xFE,  # SBC/INC abs,X
    # ABY mode opcodes (column 9)
    0x19,  # ORA abs,Y
    0x39,  # AND abs,Y
    0x59,  # EOR abs,Y
    0x79,  # ADC abs,Y
    0x99,  # STA abs,Y
    0xB9,  # LDA abs,Y
    0xBE,  # LDX abs,Y
    0xD9,  # CMP abs,Y
    0xF9,  # SBC abs,Y
}


class CPU6502:
    """6502 CPU disassembler for code relocation."""

    def __init__(self, memory: bytes):
        """Initialize disassembler with memory contents.

        Args:
            memory: 64KB memory array (or subset)
        """
        self.memory = memory

    def disassemble(self, start_addr: int, end_addr: int) -> list[Instruction]:
        """Disassemble a range of memory.

        Args:
            start_addr: Starting address (relative to memory array)
            end_addr: Ending address (exclusive)

        Returns:
            List of Instruction objects
        """
        instructions = []
        pc = start_addr

        while pc < end_addr:
            try:
                instr = self.decode_instruction(pc)
                instructions.append(instr)
                pc += instr.size
            except (IndexError, KeyError):
                # Unknown opcode or out of bounds - skip byte
                pc += 1

        return instructions

    def decode_instruction(self, address: int) -> Instruction:
        """Decode a single instruction at given address.

        Args:
            address: Memory address (relative to memory array)

        Returns:
            Instruction object

        Raises:
            KeyError: If opcode is unknown
            IndexError: If address is out of bounds
        """
        opcode = self.memory[address]

        if opcode not in OPCODE_TABLE:
            raise KeyError(f"Unknown opcode ${opcode:02X} at ${address:04X}")

        mnemonic, mode = OPCODE_TABLE[opcode]
        operand = None

        # Read operand based on addressing mode
        if mode in (AddressingMode.IMM, AddressingMode.ZP,
                    AddressingMode.ZPX, AddressingMode.ZPY,
                    AddressingMode.IZX, AddressingMode.IZY,
                    AddressingMode.REL):
            operand = self.memory[address + 1]
        elif mode in (AddressingMode.ABS, AddressingMode.ABX,
                      AddressingMode.ABY, AddressingMode.IND):
            # Little-endian 16-bit operand
            lo = self.memory[address + 1]
            hi = self.memory[address + 2]
            operand = (hi << 8) | lo

        return Instruction(address, opcode, mnemonic, mode, operand)

    def relocate_instruction(self, instr: Instruction,
                            address_delta: int) -> bytes:
        """Generate relocated instruction bytes.

        Args:
            instr: Instruction to relocate
            address_delta: Amount to add to absolute addresses

        Returns:
            Relocated instruction bytes
        """
        if not instr.is_relocatable():
            # Non-relocatable - return original bytes
            return self.memory[instr.address:instr.address + instr.size]

        # Relocate absolute address
        new_operand = (instr.operand + address_delta) & 0xFFFF
        lo = new_operand & 0xFF
        hi = (new_operand >> 8) & 0xFF

        return bytes([instr.opcode, lo, hi])

    def scan_relocatable_addresses(self, start_addr: int, end_addr: int,
                                  code_start: int, code_end: int) -> list[Tuple[int, int]]:
        """Scan for relocatable addresses using instruction size table.

        This is more robust than full disassembly because it handles unknown
        opcodes correctly using the size table.

        Args:
            start_addr: Start of code section (relative to memory array)
            end_addr: End of code section (exclusive)
            code_start: Start of relocatable memory range (absolute address)
            code_end: End of relocatable memory range (absolute address)

        Returns:
            List of (offset, address) tuples where:
                offset = byte offset in memory array where address is stored
                address = the address value that needs relocation
        """
        relocatable_addrs = []
        pc = start_addr

        while pc < end_addr and pc < len(self.memory):
            opcode = self.memory[pc]
            size = INSTRUCTION_SIZES[opcode]

            # Handle unknown/illegal opcodes (size=0)
            if size == 0:
                pc += 1
                continue

            # Check if this is a 3-byte instruction with absolute addressing
            if size == 3 and opcode in RELOCATABLE_OPCODES:
                # Read the 16-bit address operand
                if pc + 2 < len(self.memory):
                    addr_lo = self.memory[pc + 1]
                    addr_hi = self.memory[pc + 2]
                    address = (addr_hi << 8) | addr_lo

                    # Only relocate if address is within relocatable range
                    # AND not a hardware register (e.g., SID at $D400-$D7FF)
                    if code_start <= address < code_end:
                        # Don't relocate SID/VIC/CIA hardware addresses
                        if not (0xD000 <= address < 0xE000):
                            relocatable_addrs.append((pc + 1, address))

            pc += size

        return relocatable_addrs
