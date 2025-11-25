/*
 * opcodes.h - 6502 Opcode Tables
 *
 * Extracted from SID Factory II cpumos6510.cpp
 * Provides opcode metadata for address relocation
 */

#pragma once

namespace SF2Pack {

// 6502 Addressing modes
enum AddressingMode {
    am_IMP,     // Implicit
    am_IMM,     // Immediate
    am_ZP,      // Zero page
    am_ZPX,     // Zero page,X
    am_ZPY,     // Zero page,Y
    am_IZX,     // Indirect (zero page,X)
    am_IZY,     // Indirect (zero page),Y
    am_ABS,     // Absolute
    am_ABX,     // Absolute,X
    am_ABY,     // Absolute,Y
    am_IND,     // Indirect
    am_REL      // Relative
};

// Opcode information
struct OpcodeInfo {
    unsigned char size;           // Instruction size in bytes (1, 2, or 3)
    AddressingMode mode;          // Addressing mode
};

// Opcode lookup functions
unsigned char GetOpcodeSize(unsigned char opcode);
AddressingMode GetOpcodeAddressingMode(unsigned char opcode);

// Check if addressing mode requires relocation
bool RequiresRelocation(AddressingMode mode);
bool RequiresZeroPageAdjustment(AddressingMode mode);

} // namespace SF2Pack
