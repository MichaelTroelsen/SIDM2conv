"""
Complete 6502 Disassembler

Implements full 6502 instruction set with all addressing modes and illegal opcodes.
Based on SIDdecompiler's disassembler architecture but implemented in pure Python.

Features:
- All 256 opcodes (legal + illegal)
- All addressing modes (13 modes)
- Label generation and management
- Memory access type tracking
- Address table support
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)


# Addressing Modes
class AddrMode(Enum):
    """6502 Addressing Modes"""
    IMP = "Implied"          # implied
    ACC = "Accumulator"      # A
    IMM = "Immediate"        # #$nn
    ZP = "Zero Page"         # $nn
    ZPX = "Zero Page,X"      # $nn,X
    ZPY = "Zero Page,Y"      # $nn,Y
    REL = "Relative"         # $nnnn (branch)
    ABS = "Absolute"         # $nnnn
    ABSX = "Absolute,X"      # $nnnn,X
    ABSY = "Absolute,Y"      # $nnnn,Y
    IND = "Indirect"         # ($nnnn)
    XIND = "Indexed Indirect"# ($nn,X)
    INDY = "Indirect Indexed"# ($nn),Y


# Opcode Mnemonics
class Mnemonic:
    """6502 Instruction Mnemonics"""
    # Legal Opcodes
    ADC = "ADC"  # Add with Carry
    AND = "AND"  # Logical AND
    ASL = "ASL"  # Arithmetic Shift Left
    BCC = "BCC"  # Branch if Carry Clear
    BCS = "BCS"  # Branch if Carry Set
    BEQ = "BEQ"  # Branch if Equal
    BIT = "BIT"  # Bit Test
    BMI = "BMI"  # Branch if Minus
    BNE = "BNE"  # Branch if Not Equal
    BPL = "BPL"  # Branch if Plus
    BRK = "BRK"  # Break
    BVC = "BVC"  # Branch if Overflow Clear
    BVS = "BVS"  # Branch if Overflow Set
    CLC = "CLC"  # Clear Carry
    CLD = "CLD"  # Clear Decimal
    CLI = "CLI"  # Clear Interrupt
    CLV = "CLV"  # Clear Overflow
    CMP = "CMP"  # Compare Accumulator
    CPX = "CPX"  # Compare X
    CPY = "CPY"  # Compare Y
    DEC = "DEC"  # Decrement Memory
    DEX = "DEX"  # Decrement X
    DEY = "DEY"  # Decrement Y
    EOR = "EOR"  # Exclusive OR
    INC = "INC"  # Increment Memory
    INX = "INX"  # Increment X
    INY = "INY"  # Increment Y
    JMP = "JMP"  # Jump
    JSR = "JSR"  # Jump to Subroutine
    LDA = "LDA"  # Load Accumulator
    LDX = "LDX"  # Load X
    LDY = "LDY"  # Load Y
    LSR = "LSR"  # Logical Shift Right
    NOP = "NOP"  # No Operation
    ORA = "ORA"  # Logical OR
    PHA = "PHA"  # Push Accumulator
    PHP = "PHP"  # Push Processor Status
    PLA = "PLA"  # Pull Accumulator
    PLP = "PLP"  # Pull Processor Status
    ROL = "ROL"  # Rotate Left
    ROR = "ROR"  # Rotate Right
    RTI = "RTI"  # Return from Interrupt
    RTS = "RTS"  # Return from Subroutine
    SBC = "SBC"  # Subtract with Carry
    SEC = "SEC"  # Set Carry
    SED = "SED"  # Set Decimal
    SEI = "SEI"  # Set Interrupt
    STA = "STA"  # Store Accumulator
    STX = "STX"  # Store X
    STY = "STY"  # Store Y
    TAX = "TAX"  # Transfer A to X
    TAY = "TAY"  # Transfer A to Y
    TSX = "TSX"  # Transfer SP to X
    TXA = "TXA"  # Transfer X to A
    TXS = "TXS"  # Transfer X to SP
    TYA = "TYA"  # Transfer Y to A

    # Illegal Opcodes (used by some SID players)
    SLO = "SLO"  # ASL + ORA
    RLA = "RLA"  # ROL + AND
    SRE = "SRE"  # LSR + EOR
    RRA = "RRA"  # ROR + ADC
    SAX = "SAX"  # STA + STX
    LAX = "LAX"  # LDA + LDX
    DCP = "DCP"  # DEC + CMP
    ISC = "ISC"  # INC + SBC
    ANC = "ANC"  # AND + set C to bit 7
    ALR = "ALR"  # AND + LSR
    ARR = "ARR"  # AND + ROR
    XAA = "XAA"  # TXA + AND
    AHX = "AHX"  # Store A & X & H
    TAS = "TAS"  # Transfer A & X to SP
    SHY = "SHY"  # Store Y & H
    SHX = "SHX"  # Store X & H
    LAS = "LAS"  # Load A, X, SP
    AXS = "AXS"  # A & X minus immediate


@dataclass
class OpcodeDef:
    """Definition of a single 6502 opcode"""
    opcode: int           # Opcode byte value (0x00-0xFF)
    mnemonic: str         # Instruction mnemonic
    addr_mode: AddrMode   # Addressing mode
    bytes: int            # Total instruction size in bytes
    cycles: int           # Base cycle count
    illegal: bool = False # True for illegal/undocumented opcodes


# Complete 6502 Opcode Table (all 256 opcodes)
OPCODE_TABLE: List[OpcodeDef] = [
    # 0x00-0x0F
    OpcodeDef(0x00, Mnemonic.BRK, AddrMode.IMP, 1, 7),
    OpcodeDef(0x01, Mnemonic.ORA, AddrMode.XIND, 2, 6),
    OpcodeDef(0x02, "JAM", AddrMode.IMP, 1, 0, illegal=True),  # Halts CPU
    OpcodeDef(0x03, Mnemonic.SLO, AddrMode.XIND, 2, 8, illegal=True),
    OpcodeDef(0x04, Mnemonic.NOP, AddrMode.ZP, 2, 3, illegal=True),
    OpcodeDef(0x05, Mnemonic.ORA, AddrMode.ZP, 2, 3),
    OpcodeDef(0x06, Mnemonic.ASL, AddrMode.ZP, 2, 5),
    OpcodeDef(0x07, Mnemonic.SLO, AddrMode.ZP, 2, 5, illegal=True),
    OpcodeDef(0x08, Mnemonic.PHP, AddrMode.IMP, 1, 3),
    OpcodeDef(0x09, Mnemonic.ORA, AddrMode.IMM, 2, 2),
    OpcodeDef(0x0A, Mnemonic.ASL, AddrMode.ACC, 1, 2),
    OpcodeDef(0x0B, Mnemonic.ANC, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0x0C, Mnemonic.NOP, AddrMode.ABS, 3, 4, illegal=True),
    OpcodeDef(0x0D, Mnemonic.ORA, AddrMode.ABS, 3, 4),
    OpcodeDef(0x0E, Mnemonic.ASL, AddrMode.ABS, 3, 6),
    OpcodeDef(0x0F, Mnemonic.SLO, AddrMode.ABS, 3, 6, illegal=True),

    # 0x10-0x1F
    OpcodeDef(0x10, Mnemonic.BPL, AddrMode.REL, 2, 2),
    OpcodeDef(0x11, Mnemonic.ORA, AddrMode.INDY, 2, 5),
    OpcodeDef(0x12, "JAM", AddrMode.IMP, 1, 0, illegal=True),
    OpcodeDef(0x13, Mnemonic.SLO, AddrMode.INDY, 2, 8, illegal=True),
    OpcodeDef(0x14, Mnemonic.NOP, AddrMode.ZPX, 2, 4, illegal=True),
    OpcodeDef(0x15, Mnemonic.ORA, AddrMode.ZPX, 2, 4),
    OpcodeDef(0x16, Mnemonic.ASL, AddrMode.ZPX, 2, 6),
    OpcodeDef(0x17, Mnemonic.SLO, AddrMode.ZPX, 2, 6, illegal=True),
    OpcodeDef(0x18, Mnemonic.CLC, AddrMode.IMP, 1, 2),
    OpcodeDef(0x19, Mnemonic.ORA, AddrMode.ABSY, 3, 4),
    OpcodeDef(0x1A, Mnemonic.NOP, AddrMode.IMP, 1, 2, illegal=True),
    OpcodeDef(0x1B, Mnemonic.SLO, AddrMode.ABSY, 3, 7, illegal=True),
    OpcodeDef(0x1C, Mnemonic.NOP, AddrMode.ABSX, 3, 4, illegal=True),
    OpcodeDef(0x1D, Mnemonic.ORA, AddrMode.ABSX, 3, 4),
    OpcodeDef(0x1E, Mnemonic.ASL, AddrMode.ABSX, 3, 7),
    OpcodeDef(0x1F, Mnemonic.SLO, AddrMode.ABSX, 3, 7, illegal=True),

    # 0x20-0x2F
    OpcodeDef(0x20, Mnemonic.JSR, AddrMode.ABS, 3, 6),
    OpcodeDef(0x21, Mnemonic.AND, AddrMode.XIND, 2, 6),
    OpcodeDef(0x22, "JAM", AddrMode.IMP, 1, 0, illegal=True),
    OpcodeDef(0x23, Mnemonic.RLA, AddrMode.XIND, 2, 8, illegal=True),
    OpcodeDef(0x24, Mnemonic.BIT, AddrMode.ZP, 2, 3),
    OpcodeDef(0x25, Mnemonic.AND, AddrMode.ZP, 2, 3),
    OpcodeDef(0x26, Mnemonic.ROL, AddrMode.ZP, 2, 5),
    OpcodeDef(0x27, Mnemonic.RLA, AddrMode.ZP, 2, 5, illegal=True),
    OpcodeDef(0x28, Mnemonic.PLP, AddrMode.IMP, 1, 4),
    OpcodeDef(0x29, Mnemonic.AND, AddrMode.IMM, 2, 2),
    OpcodeDef(0x2A, Mnemonic.ROL, AddrMode.ACC, 1, 2),
    OpcodeDef(0x2B, Mnemonic.ANC, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0x2C, Mnemonic.BIT, AddrMode.ABS, 3, 4),
    OpcodeDef(0x2D, Mnemonic.AND, AddrMode.ABS, 3, 4),
    OpcodeDef(0x2E, Mnemonic.ROL, AddrMode.ABS, 3, 6),
    OpcodeDef(0x2F, Mnemonic.RLA, AddrMode.ABS, 3, 6, illegal=True),

    # 0x30-0x3F
    OpcodeDef(0x30, Mnemonic.BMI, AddrMode.REL, 2, 2),
    OpcodeDef(0x31, Mnemonic.AND, AddrMode.INDY, 2, 5),
    OpcodeDef(0x32, "JAM", AddrMode.IMP, 1, 0, illegal=True),
    OpcodeDef(0x33, Mnemonic.RLA, AddrMode.INDY, 2, 8, illegal=True),
    OpcodeDef(0x34, Mnemonic.NOP, AddrMode.ZPX, 2, 4, illegal=True),
    OpcodeDef(0x35, Mnemonic.AND, AddrMode.ZPX, 2, 4),
    OpcodeDef(0x36, Mnemonic.ROL, AddrMode.ZPX, 2, 6),
    OpcodeDef(0x37, Mnemonic.RLA, AddrMode.ZPX, 2, 6, illegal=True),
    OpcodeDef(0x38, Mnemonic.SEC, AddrMode.IMP, 1, 2),
    OpcodeDef(0x39, Mnemonic.AND, AddrMode.ABSY, 3, 4),
    OpcodeDef(0x3A, Mnemonic.NOP, AddrMode.IMP, 1, 2, illegal=True),
    OpcodeDef(0x3B, Mnemonic.RLA, AddrMode.ABSY, 3, 7, illegal=True),
    OpcodeDef(0x3C, Mnemonic.NOP, AddrMode.ABSX, 3, 4, illegal=True),
    OpcodeDef(0x3D, Mnemonic.AND, AddrMode.ABSX, 3, 4),
    OpcodeDef(0x3E, Mnemonic.ROL, AddrMode.ABSX, 3, 7),
    OpcodeDef(0x3F, Mnemonic.RLA, AddrMode.ABSX, 3, 7, illegal=True),

    # 0x40-0x4F
    OpcodeDef(0x40, Mnemonic.RTI, AddrMode.IMP, 1, 6),
    OpcodeDef(0x41, Mnemonic.EOR, AddrMode.XIND, 2, 6),
    OpcodeDef(0x42, "JAM", AddrMode.IMP, 1, 0, illegal=True),
    OpcodeDef(0x43, Mnemonic.SRE, AddrMode.XIND, 2, 8, illegal=True),
    OpcodeDef(0x44, Mnemonic.NOP, AddrMode.ZP, 2, 3, illegal=True),
    OpcodeDef(0x45, Mnemonic.EOR, AddrMode.ZP, 2, 3),
    OpcodeDef(0x46, Mnemonic.LSR, AddrMode.ZP, 2, 5),
    OpcodeDef(0x47, Mnemonic.SRE, AddrMode.ZP, 2, 5, illegal=True),
    OpcodeDef(0x48, Mnemonic.PHA, AddrMode.IMP, 1, 3),
    OpcodeDef(0x49, Mnemonic.EOR, AddrMode.IMM, 2, 2),
    OpcodeDef(0x4A, Mnemonic.LSR, AddrMode.ACC, 1, 2),
    OpcodeDef(0x4B, Mnemonic.ALR, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0x4C, Mnemonic.JMP, AddrMode.ABS, 3, 3),
    OpcodeDef(0x4D, Mnemonic.EOR, AddrMode.ABS, 3, 4),
    OpcodeDef(0x4E, Mnemonic.LSR, AddrMode.ABS, 3, 6),
    OpcodeDef(0x4F, Mnemonic.SRE, AddrMode.ABS, 3, 6, illegal=True),

    # 0x50-0x5F
    OpcodeDef(0x50, Mnemonic.BVC, AddrMode.REL, 2, 2),
    OpcodeDef(0x51, Mnemonic.EOR, AddrMode.INDY, 2, 5),
    OpcodeDef(0x52, "JAM", AddrMode.IMP, 1, 0, illegal=True),
    OpcodeDef(0x53, Mnemonic.SRE, AddrMode.INDY, 2, 8, illegal=True),
    OpcodeDef(0x54, Mnemonic.NOP, AddrMode.ZPX, 2, 4, illegal=True),
    OpcodeDef(0x55, Mnemonic.EOR, AddrMode.ZPX, 2, 4),
    OpcodeDef(0x56, Mnemonic.LSR, AddrMode.ZPX, 2, 6),
    OpcodeDef(0x57, Mnemonic.SRE, AddrMode.ZPX, 2, 6, illegal=True),
    OpcodeDef(0x58, Mnemonic.CLI, AddrMode.IMP, 1, 2),
    OpcodeDef(0x59, Mnemonic.EOR, AddrMode.ABSY, 3, 4),
    OpcodeDef(0x5A, Mnemonic.NOP, AddrMode.IMP, 1, 2, illegal=True),
    OpcodeDef(0x5B, Mnemonic.SRE, AddrMode.ABSY, 3, 7, illegal=True),
    OpcodeDef(0x5C, Mnemonic.NOP, AddrMode.ABSX, 3, 4, illegal=True),
    OpcodeDef(0x5D, Mnemonic.EOR, AddrMode.ABSX, 3, 4),
    OpcodeDef(0x5E, Mnemonic.LSR, AddrMode.ABSX, 3, 7),
    OpcodeDef(0x5F, Mnemonic.SRE, AddrMode.ABSX, 3, 7, illegal=True),

    # 0x60-0x6F
    OpcodeDef(0x60, Mnemonic.RTS, AddrMode.IMP, 1, 6),
    OpcodeDef(0x61, Mnemonic.ADC, AddrMode.XIND, 2, 6),
    OpcodeDef(0x62, "JAM", AddrMode.IMP, 1, 0, illegal=True),
    OpcodeDef(0x63, Mnemonic.RRA, AddrMode.XIND, 2, 8, illegal=True),
    OpcodeDef(0x64, Mnemonic.NOP, AddrMode.ZP, 2, 3, illegal=True),
    OpcodeDef(0x65, Mnemonic.ADC, AddrMode.ZP, 2, 3),
    OpcodeDef(0x66, Mnemonic.ROR, AddrMode.ZP, 2, 5),
    OpcodeDef(0x67, Mnemonic.RRA, AddrMode.ZP, 2, 5, illegal=True),
    OpcodeDef(0x68, Mnemonic.PLA, AddrMode.IMP, 1, 4),
    OpcodeDef(0x69, Mnemonic.ADC, AddrMode.IMM, 2, 2),
    OpcodeDef(0x6A, Mnemonic.ROR, AddrMode.ACC, 1, 2),
    OpcodeDef(0x6B, Mnemonic.ARR, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0x6C, Mnemonic.JMP, AddrMode.IND, 3, 5),
    OpcodeDef(0x6D, Mnemonic.ADC, AddrMode.ABS, 3, 4),
    OpcodeDef(0x6E, Mnemonic.ROR, AddrMode.ABS, 3, 6),
    OpcodeDef(0x6F, Mnemonic.RRA, AddrMode.ABS, 3, 6, illegal=True),

    # 0x70-0x7F
    OpcodeDef(0x70, Mnemonic.BVS, AddrMode.REL, 2, 2),
    OpcodeDef(0x71, Mnemonic.ADC, AddrMode.INDY, 2, 5),
    OpcodeDef(0x72, "JAM", AddrMode.IMP, 1, 0, illegal=True),
    OpcodeDef(0x73, Mnemonic.RRA, AddrMode.INDY, 2, 8, illegal=True),
    OpcodeDef(0x74, Mnemonic.NOP, AddrMode.ZPX, 2, 4, illegal=True),
    OpcodeDef(0x75, Mnemonic.ADC, AddrMode.ZPX, 2, 4),
    OpcodeDef(0x76, Mnemonic.ROR, AddrMode.ZPX, 2, 6),
    OpcodeDef(0x77, Mnemonic.RRA, AddrMode.ZPX, 2, 6, illegal=True),
    OpcodeDef(0x78, Mnemonic.SEI, AddrMode.IMP, 1, 2),
    OpcodeDef(0x79, Mnemonic.ADC, AddrMode.ABSY, 3, 4),
    OpcodeDef(0x7A, Mnemonic.NOP, AddrMode.IMP, 1, 2, illegal=True),
    OpcodeDef(0x7B, Mnemonic.RRA, AddrMode.ABSY, 3, 7, illegal=True),
    OpcodeDef(0x7C, Mnemonic.NOP, AddrMode.ABSX, 3, 4, illegal=True),
    OpcodeDef(0x7D, Mnemonic.ADC, AddrMode.ABSX, 3, 4),
    OpcodeDef(0x7E, Mnemonic.ROR, AddrMode.ABSX, 3, 7),
    OpcodeDef(0x7F, Mnemonic.RRA, AddrMode.ABSX, 3, 7, illegal=True),

    # 0x80-0x8F
    OpcodeDef(0x80, Mnemonic.NOP, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0x81, Mnemonic.STA, AddrMode.XIND, 2, 6),
    OpcodeDef(0x82, Mnemonic.NOP, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0x83, Mnemonic.SAX, AddrMode.XIND, 2, 6, illegal=True),
    OpcodeDef(0x84, Mnemonic.STY, AddrMode.ZP, 2, 3),
    OpcodeDef(0x85, Mnemonic.STA, AddrMode.ZP, 2, 3),
    OpcodeDef(0x86, Mnemonic.STX, AddrMode.ZP, 2, 3),
    OpcodeDef(0x87, Mnemonic.SAX, AddrMode.ZP, 2, 3, illegal=True),
    OpcodeDef(0x88, Mnemonic.DEY, AddrMode.IMP, 1, 2),
    OpcodeDef(0x89, Mnemonic.NOP, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0x8A, Mnemonic.TXA, AddrMode.IMP, 1, 2),
    OpcodeDef(0x8B, Mnemonic.XAA, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0x8C, Mnemonic.STY, AddrMode.ABS, 3, 4),
    OpcodeDef(0x8D, Mnemonic.STA, AddrMode.ABS, 3, 4),
    OpcodeDef(0x8E, Mnemonic.STX, AddrMode.ABS, 3, 4),
    OpcodeDef(0x8F, Mnemonic.SAX, AddrMode.ABS, 3, 4, illegal=True),

    # 0x90-0x9F
    OpcodeDef(0x90, Mnemonic.BCC, AddrMode.REL, 2, 2),
    OpcodeDef(0x91, Mnemonic.STA, AddrMode.INDY, 2, 6),
    OpcodeDef(0x92, "JAM", AddrMode.IMP, 1, 0, illegal=True),
    OpcodeDef(0x93, Mnemonic.AHX, AddrMode.INDY, 2, 6, illegal=True),
    OpcodeDef(0x94, Mnemonic.STY, AddrMode.ZPX, 2, 4),
    OpcodeDef(0x95, Mnemonic.STA, AddrMode.ZPX, 2, 4),
    OpcodeDef(0x96, Mnemonic.STX, AddrMode.ZPY, 2, 4),
    OpcodeDef(0x97, Mnemonic.SAX, AddrMode.ZPY, 2, 4, illegal=True),
    OpcodeDef(0x98, Mnemonic.TYA, AddrMode.IMP, 1, 2),
    OpcodeDef(0x99, Mnemonic.STA, AddrMode.ABSY, 3, 5),
    OpcodeDef(0x9A, Mnemonic.TXS, AddrMode.IMP, 1, 2),
    OpcodeDef(0x9B, Mnemonic.TAS, AddrMode.ABSY, 3, 5, illegal=True),
    OpcodeDef(0x9C, Mnemonic.SHY, AddrMode.ABSX, 3, 5, illegal=True),
    OpcodeDef(0x9D, Mnemonic.STA, AddrMode.ABSX, 3, 5),
    OpcodeDef(0x9E, Mnemonic.SHX, AddrMode.ABSY, 3, 5, illegal=True),
    OpcodeDef(0x9F, Mnemonic.AHX, AddrMode.ABSY, 3, 5, illegal=True),

    # 0xA0-0xAF
    OpcodeDef(0xA0, Mnemonic.LDY, AddrMode.IMM, 2, 2),
    OpcodeDef(0xA1, Mnemonic.LDA, AddrMode.XIND, 2, 6),
    OpcodeDef(0xA2, Mnemonic.LDX, AddrMode.IMM, 2, 2),
    OpcodeDef(0xA3, Mnemonic.LAX, AddrMode.XIND, 2, 6, illegal=True),
    OpcodeDef(0xA4, Mnemonic.LDY, AddrMode.ZP, 2, 3),
    OpcodeDef(0xA5, Mnemonic.LDA, AddrMode.ZP, 2, 3),
    OpcodeDef(0xA6, Mnemonic.LDX, AddrMode.ZP, 2, 3),
    OpcodeDef(0xA7, Mnemonic.LAX, AddrMode.ZP, 2, 3, illegal=True),
    OpcodeDef(0xA8, Mnemonic.TAY, AddrMode.IMP, 1, 2),
    OpcodeDef(0xA9, Mnemonic.LDA, AddrMode.IMM, 2, 2),
    OpcodeDef(0xAA, Mnemonic.TAX, AddrMode.IMP, 1, 2),
    OpcodeDef(0xAB, Mnemonic.LAX, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0xAC, Mnemonic.LDY, AddrMode.ABS, 3, 4),
    OpcodeDef(0xAD, Mnemonic.LDA, AddrMode.ABS, 3, 4),
    OpcodeDef(0xAE, Mnemonic.LDX, AddrMode.ABS, 3, 4),
    OpcodeDef(0xAF, Mnemonic.LAX, AddrMode.ABS, 3, 4, illegal=True),

    # 0xB0-0xBF
    OpcodeDef(0xB0, Mnemonic.BCS, AddrMode.REL, 2, 2),
    OpcodeDef(0xB1, Mnemonic.LDA, AddrMode.INDY, 2, 5),
    OpcodeDef(0xB2, "JAM", AddrMode.IMP, 1, 0, illegal=True),
    OpcodeDef(0xB3, Mnemonic.LAX, AddrMode.INDY, 2, 5, illegal=True),
    OpcodeDef(0xB4, Mnemonic.LDY, AddrMode.ZPX, 2, 4),
    OpcodeDef(0xB5, Mnemonic.LDA, AddrMode.ZPX, 2, 4),
    OpcodeDef(0xB6, Mnemonic.LDX, AddrMode.ZPY, 2, 4),
    OpcodeDef(0xB7, Mnemonic.LAX, AddrMode.ZPY, 2, 4, illegal=True),
    OpcodeDef(0xB8, Mnemonic.CLV, AddrMode.IMP, 1, 2),
    OpcodeDef(0xB9, Mnemonic.LDA, AddrMode.ABSY, 3, 4),
    OpcodeDef(0xBA, Mnemonic.TSX, AddrMode.IMP, 1, 2),
    OpcodeDef(0xBB, Mnemonic.LAS, AddrMode.ABSY, 3, 4, illegal=True),
    OpcodeDef(0xBC, Mnemonic.LDY, AddrMode.ABSX, 3, 4),
    OpcodeDef(0xBD, Mnemonic.LDA, AddrMode.ABSX, 3, 4),
    OpcodeDef(0xBE, Mnemonic.LDX, AddrMode.ABSY, 3, 4),
    OpcodeDef(0xBF, Mnemonic.LAX, AddrMode.ABSY, 3, 4, illegal=True),

    # 0xC0-0xCF
    OpcodeDef(0xC0, Mnemonic.CPY, AddrMode.IMM, 2, 2),
    OpcodeDef(0xC1, Mnemonic.CMP, AddrMode.XIND, 2, 6),
    OpcodeDef(0xC2, Mnemonic.NOP, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0xC3, Mnemonic.DCP, AddrMode.XIND, 2, 8, illegal=True),
    OpcodeDef(0xC4, Mnemonic.CPY, AddrMode.ZP, 2, 3),
    OpcodeDef(0xC5, Mnemonic.CMP, AddrMode.ZP, 2, 3),
    OpcodeDef(0xC6, Mnemonic.DEC, AddrMode.ZP, 2, 5),
    OpcodeDef(0xC7, Mnemonic.DCP, AddrMode.ZP, 2, 5, illegal=True),
    OpcodeDef(0xC8, Mnemonic.INY, AddrMode.IMP, 1, 2),
    OpcodeDef(0xC9, Mnemonic.CMP, AddrMode.IMM, 2, 2),
    OpcodeDef(0xCA, Mnemonic.DEX, AddrMode.IMP, 1, 2),
    OpcodeDef(0xCB, Mnemonic.AXS, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0xCC, Mnemonic.CPY, AddrMode.ABS, 3, 4),
    OpcodeDef(0xCD, Mnemonic.CMP, AddrMode.ABS, 3, 4),
    OpcodeDef(0xCE, Mnemonic.DEC, AddrMode.ABS, 3, 6),
    OpcodeDef(0xCF, Mnemonic.DCP, AddrMode.ABS, 3, 6, illegal=True),

    # 0xD0-0xDF
    OpcodeDef(0xD0, Mnemonic.BNE, AddrMode.REL, 2, 2),
    OpcodeDef(0xD1, Mnemonic.CMP, AddrMode.INDY, 2, 5),
    OpcodeDef(0xD2, "JAM", AddrMode.IMP, 1, 0, illegal=True),
    OpcodeDef(0xD3, Mnemonic.DCP, AddrMode.INDY, 2, 8, illegal=True),
    OpcodeDef(0xD4, Mnemonic.NOP, AddrMode.ZPX, 2, 4, illegal=True),
    OpcodeDef(0xD5, Mnemonic.CMP, AddrMode.ZPX, 2, 4),
    OpcodeDef(0xD6, Mnemonic.DEC, AddrMode.ZPX, 2, 6),
    OpcodeDef(0xD7, Mnemonic.DCP, AddrMode.ZPX, 2, 6, illegal=True),
    OpcodeDef(0xD8, Mnemonic.CLD, AddrMode.IMP, 1, 2),
    OpcodeDef(0xD9, Mnemonic.CMP, AddrMode.ABSY, 3, 4),
    OpcodeDef(0xDA, Mnemonic.NOP, AddrMode.IMP, 1, 2, illegal=True),
    OpcodeDef(0xDB, Mnemonic.DCP, AddrMode.ABSY, 3, 7, illegal=True),
    OpcodeDef(0xDC, Mnemonic.NOP, AddrMode.ABSX, 3, 4, illegal=True),
    OpcodeDef(0xDD, Mnemonic.CMP, AddrMode.ABSX, 3, 4),
    OpcodeDef(0xDE, Mnemonic.DEC, AddrMode.ABSX, 3, 7),
    OpcodeDef(0xDF, Mnemonic.DCP, AddrMode.ABSX, 3, 7, illegal=True),

    # 0xE0-0xEF
    OpcodeDef(0xE0, Mnemonic.CPX, AddrMode.IMM, 2, 2),
    OpcodeDef(0xE1, Mnemonic.SBC, AddrMode.XIND, 2, 6),
    OpcodeDef(0xE2, Mnemonic.NOP, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0xE3, Mnemonic.ISC, AddrMode.XIND, 2, 8, illegal=True),
    OpcodeDef(0xE4, Mnemonic.CPX, AddrMode.ZP, 2, 3),
    OpcodeDef(0xE5, Mnemonic.SBC, AddrMode.ZP, 2, 3),
    OpcodeDef(0xE6, Mnemonic.INC, AddrMode.ZP, 2, 5),
    OpcodeDef(0xE7, Mnemonic.ISC, AddrMode.ZP, 2, 5, illegal=True),
    OpcodeDef(0xE8, Mnemonic.INX, AddrMode.IMP, 1, 2),
    OpcodeDef(0xE9, Mnemonic.SBC, AddrMode.IMM, 2, 2),
    OpcodeDef(0xEA, Mnemonic.NOP, AddrMode.IMP, 1, 2),
    OpcodeDef(0xEB, Mnemonic.SBC, AddrMode.IMM, 2, 2, illegal=True),
    OpcodeDef(0xEC, Mnemonic.CPX, AddrMode.ABS, 3, 4),
    OpcodeDef(0xED, Mnemonic.SBC, AddrMode.ABS, 3, 4),
    OpcodeDef(0xEE, Mnemonic.INC, AddrMode.ABS, 3, 6),
    OpcodeDef(0xEF, Mnemonic.ISC, AddrMode.ABS, 3, 6, illegal=True),

    # 0xF0-0xFF
    OpcodeDef(0xF0, Mnemonic.BEQ, AddrMode.REL, 2, 2),
    OpcodeDef(0xF1, Mnemonic.SBC, AddrMode.INDY, 2, 5),
    OpcodeDef(0xF2, "JAM", AddrMode.IMP, 1, 0, illegal=True),
    OpcodeDef(0xF3, Mnemonic.ISC, AddrMode.INDY, 2, 8, illegal=True),
    OpcodeDef(0xF4, Mnemonic.NOP, AddrMode.ZPX, 2, 4, illegal=True),
    OpcodeDef(0xF5, Mnemonic.SBC, AddrMode.ZPX, 2, 4),
    OpcodeDef(0xF6, Mnemonic.INC, AddrMode.ZPX, 2, 6),
    OpcodeDef(0xF7, Mnemonic.ISC, AddrMode.ZPX, 2, 6, illegal=True),
    OpcodeDef(0xF8, Mnemonic.SED, AddrMode.IMP, 1, 2),
    OpcodeDef(0xF9, Mnemonic.SBC, AddrMode.ABSY, 3, 4),
    OpcodeDef(0xFA, Mnemonic.NOP, AddrMode.IMP, 1, 2, illegal=True),
    OpcodeDef(0xFB, Mnemonic.ISC, AddrMode.ABSY, 3, 7, illegal=True),
    OpcodeDef(0xFC, Mnemonic.NOP, AddrMode.ABSX, 3, 4, illegal=True),
    OpcodeDef(0xFD, Mnemonic.SBC, AddrMode.ABSX, 3, 4),
    OpcodeDef(0xFE, Mnemonic.INC, AddrMode.ABSX, 3, 7),
    OpcodeDef(0xFF, Mnemonic.ISC, AddrMode.ABSX, 3, 7, illegal=True),
]

# Create fast lookup dictionary
OPCODES: Dict[int, OpcodeDef] = {op.opcode: op for op in OPCODE_TABLE}


@dataclass
class Label:
    """Assembly label"""
    address: int
    name: str
    is_code: bool = True  # True for code labels, False for data
    is_generated: bool = True  # True for auto-generated labels
    references: Set[int] = None  # Addresses that reference this label

    def __post_init__(self):
        if self.references is None:
            self.references = set()


class Region(Enum):
    """Memory region type"""
    CODE = "code"
    DATA = "data"
    UNKNOWN = "unknown"


@dataclass
class DisassembledLine:
    """A single disassembled instruction or data line"""
    address: int
    opcode: Optional[int]
    instruction: str  # Mnemonic or ".byte"
    operand: str      # Operand string
    bytes: bytes      # Raw bytes
    is_referenced: bool = False
    comment: Optional[str] = None


class Disassembler6502:
    """
    Complete 6502 disassembler with label management and code flow analysis.

    Compatible with SIDdecompiler output format.
    """

    def __init__(self, memory: bytes, start_addr: int, size: int):
        """
        Initialize disassembler.

        Args:
            memory: Memory buffer (entire C64 64KB space or slice)
            start_addr: Starting address of code/data to disassemble
            size: Number of bytes to disassemble
        """
        self.memory = memory
        self.start_addr = start_addr
        self.size = size
        self.end_addr = start_addr + size

        # Label management
        self.labels: Dict[int, Label] = {}

        # Disassembly output
        self.lines: Dict[int, DisassembledLine] = {}

        # Memory access tracking
        self.code_addresses: Set[int] = set()  # Executed as code
        self.data_addresses: Set[int] = set()  # Read as data
        self.write_addresses: Set[int] = set()  # Written to

        # Configuration
        self.allow_illegal_opcodes = True
        self.comment_unused = True

    def add_label(self, address: int, name: Optional[str] = None, is_code: bool = True) -> Label:
        """
        Add or get a label at the specified address.

        Args:
            address: Memory address
            name: Label name (auto-generated if None)
            is_code: True if this is a code label

        Returns:
            Label object
        """
        if address in self.labels:
            return self.labels[address]

        if name is None:
            name = self._generate_label(address)

        label = Label(
            address=address,
            name=name,
            is_code=is_code,
            is_generated=(name is None)
        )
        self.labels[address] = label
        return label

    def _generate_label(self, address: int) -> str:
        """Generate automatic label name based on address."""
        if address < 0x100:
            return f"z{address:02x}"  # Zero page
        else:
            return f"l{address:04x}"  # Absolute

    def mark_code_address(self, address: int):
        """Mark address as containing executable code."""
        self.code_addresses.add(address)

    def mark_data_address(self, address: int):
        """Mark address as containing data."""
        self.data_addresses.add(address)

    def is_branch_instruction(self, opcode: OpcodeDef) -> bool:
        """Check if opcode is a branch instruction."""
        return opcode.addr_mode == AddrMode.REL

    def is_jump_instruction(self, mnemonic: str) -> bool:
        """Check if instruction is a jump (JMP, JSR)."""
        return mnemonic in (Mnemonic.JMP, Mnemonic.JSR)

    def get_branch_target(self, address: int, offset: int) -> int:
        """
        Calculate branch target address from relative offset.

        Args:
            address: Address of branch instruction
            offset: Signed 8-bit offset

        Returns:
            Target address
        """
        # Convert unsigned byte to signed
        if offset >= 128:
            offset -= 256
        # Branch offset is relative to the NEXT instruction (PC + 2)
        return address + 2 + offset

    def disassemble_instruction(self, address: int) -> Optional[DisassembledLine]:
        """
        Disassemble single instruction at address.

        Args:
            address: Address to disassemble

        Returns:
            DisassembledLine or None if address out of range
        """
        if address < self.start_addr or address >= self.end_addr:
            return None

        # Convert logical address to physical memory offset
        mem_offset = address - self.start_addr
        if mem_offset >= len(self.memory):
            return None

        opcode_byte = self.memory[mem_offset]
        opcode_def = OPCODES[opcode_byte]

        # Check illegal opcodes
        if opcode_def.illegal and not self.allow_illegal_opcodes:
            # Treat as data
            return DisassembledLine(
                address=address,
                opcode=None,
                instruction=".byte",
                operand=f"${opcode_byte:02x}",
                bytes=bytes([opcode_byte]),
                comment="Illegal opcode"
            )

        # Extract operand bytes
        operand_bytes = []
        for i in range(1, opcode_def.bytes):
            if mem_offset + i < len(self.memory):
                operand_bytes.append(self.memory[mem_offset + i])
            else:
                # Truncated instruction at end of memory
                return DisassembledLine(
                    address=address,
                    opcode=opcode_byte,
                    instruction=opcode_def.mnemonic,
                    operand="???",
                    bytes=bytes([opcode_byte]),
                    comment="Truncated"
                )

        # Format operand based on addressing mode
        operand_str = self._format_operand(address, opcode_def, operand_bytes)

        # Get all instruction bytes
        instr_bytes = bytes([opcode_byte] + operand_bytes)

        # Create labels for jump/branch targets
        if self.is_branch_instruction(opcode_def):
            # Relative branch
            target = self.get_branch_target(address, operand_bytes[0])
            self.add_label(target, is_code=True)
        elif self.is_jump_instruction(opcode_def.mnemonic):
            # Absolute jump/call
            if opcode_def.addr_mode == AddrMode.ABS:
                target = operand_bytes[0] | (operand_bytes[1] << 8)
                self.add_label(target, is_code=True)

        return DisassembledLine(
            address=address,
            opcode=opcode_byte,
            instruction=opcode_def.mnemonic,
            operand=operand_str,
            bytes=instr_bytes
        )

    def _format_operand(self, address: int, opcode: OpcodeDef, operand_bytes: List[int]) -> str:
        """
        Format operand string based on addressing mode.

        Args:
            address: Instruction address
            opcode: Opcode definition
            operand_bytes: Operand bytes (0-2 bytes)

        Returns:
            Formatted operand string
        """
        mode = opcode.addr_mode

        if mode == AddrMode.IMP or mode == AddrMode.ACC:
            return ""

        if mode == AddrMode.IMM:
            return f"#${operand_bytes[0]:02x}"

        if mode == AddrMode.ZP:
            addr = operand_bytes[0]
            if addr in self.labels:
                return self.labels[addr].name
            return f"${addr:02x}"

        if mode == AddrMode.ZPX:
            addr = operand_bytes[0]
            if addr in self.labels:
                return f"{self.labels[addr].name},x"
            return f"${addr:02x},x"

        if mode == AddrMode.ZPY:
            addr = operand_bytes[0]
            if addr in self.labels:
                return f"{self.labels[addr].name},y"
            return f"${addr:02x},y"

        if mode == AddrMode.REL:
            # Branch - show label
            target = self.get_branch_target(address, operand_bytes[0])
            if target in self.labels:
                return self.labels[target].name
            return self._generate_label(target)

        if mode == AddrMode.ABS:
            addr = operand_bytes[0] | (operand_bytes[1] << 8)
            if addr in self.labels:
                return self.labels[addr].name
            return f"${addr:04x}"

        if mode == AddrMode.ABSX:
            addr = operand_bytes[0] | (operand_bytes[1] << 8)
            if addr in self.labels:
                return f"{self.labels[addr].name},x"
            return f"${addr:04x},x"

        if mode == AddrMode.ABSY:
            addr = operand_bytes[0] | (operand_bytes[1] << 8)
            if addr in self.labels:
                return f"{self.labels[addr].name},y"
            return f"${addr:04x},y"

        if mode == AddrMode.IND:
            addr = operand_bytes[0] | (operand_bytes[1] << 8)
            if addr in self.labels:
                return f"({self.labels[addr].name})"
            return f"(${addr:04x})"

        if mode == AddrMode.XIND:
            addr = operand_bytes[0]
            if addr in self.labels:
                return f"({self.labels[addr].name},x)"
            return f"(${addr:02x},x)"

        if mode == AddrMode.INDY:
            addr = operand_bytes[0]
            if addr in self.labels:
                return f"({self.labels[addr].name}),y"
            return f"(${addr:02x}),y"

        return "???"

    def disassemble_range(self, start: int, end: int):
        """
        Disassemble a range of addresses.

        Args:
            start: Start address
            end: End address (exclusive)
        """
        addr = start
        while addr < end:
            line = self.disassemble_instruction(addr)
            if line:
                self.lines[addr] = line
                self.mark_code_address(addr)
                addr += len(line.bytes)
            else:
                # Treat as data byte
                mem_offset = addr - self.start_addr
                if mem_offset < len(self.memory):
                    byte_val = self.memory[mem_offset]
                    self.lines[addr] = DisassembledLine(
                        address=addr,
                        opcode=None,
                        instruction=".byte",
                        operand=f"${byte_val:02x}",
                        bytes=bytes([byte_val])
                    )
                    self.mark_data_address(addr)
                addr += 1

    def disassemble(self):
        """Disassemble entire specified range."""
        self.disassemble_range(self.start_addr, self.end_addr)

    def format_output(self, relocate_addr: Optional[int] = None) -> str:
        """
        Format disassembly as text output compatible with SIDdecompiler.

        Args:
            relocate_addr: If specified, show relocated addresses

        Returns:
            Formatted assembly listing
        """
        output = []

        # Sort addresses
        addresses = sorted(self.lines.keys())

        for addr in addresses:
            line = self.lines[addr]

            # Calculate displayed address (relocated if specified)
            display_addr = addr
            if relocate_addr is not None:
                display_addr = addr - self.start_addr + relocate_addr

            # Label line if present
            if addr in self.labels:
                label = self.labels[addr]
                output.append(f"{label.name}:")

            # Format instruction line
            bytes_str = " ".join(f"{b:02x}" for b in line.bytes)

            # Instruction/operand
            if line.operand:
                instr = f"{line.instruction:4s} {line.operand}"
            else:
                instr = line.instruction

            # Full line with address, bytes, instruction
            full_line = f"${display_addr:04x}: {bytes_str:12s} {instr:20s}"

            if line.comment:
                full_line += f"  ; {line.comment}"

            output.append(full_line)

        return "\n".join(output)


def main():
    """Test disassembler"""
    # Test with simple code
    code = bytes([
        0xA9, 0x00,        # LDA #$00
        0x8D, 0x00, 0xD4,  # STA $D400
        0x60               # RTS
    ])

    disasm = Disassembler6502(code, 0x1000, len(code))
    disasm.disassemble()
    print(disasm.format_output())


if __name__ == "__main__":
    main()
