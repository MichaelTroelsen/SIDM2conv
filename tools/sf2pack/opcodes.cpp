/*
 * opcodes.cpp - 6502 Opcode Tables Implementation
 *
 * Extracted from SID Factory II cpumos6510.cpp
 * Full 256-opcode lookup table for size and addressing mode
 */

#include "opcodes.h"

namespace SF2Pack {

// 6502 instruction matrix (256 opcodes)
// Format: {size, addressing_mode}
static const OpcodeInfo opcode_table[256] = {
    {1, am_IMP}, {2, am_IZX}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {2, am_ZP }, {2, am_ZP }, {1, am_IMP},  // 0x00-0x07
    {1, am_IMP}, {2, am_IMM}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {3, am_ABS}, {3, am_ABS}, {1, am_IMP},  // 0x08-0x0F
    {2, am_REL}, {2, am_IZY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {2, am_ZPX}, {2, am_ZPX}, {1, am_IMP},  // 0x10-0x17
    {1, am_IMP}, {3, am_ABY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {3, am_ABX}, {3, am_ABX}, {1, am_IMP},  // 0x18-0x1F

    {3, am_ABS}, {2, am_IZX}, {1, am_IMP}, {1, am_IMP}, {2, am_ZP }, {2, am_ZP }, {2, am_ZP }, {1, am_IMP},  // 0x20-0x27
    {1, am_IMP}, {2, am_IMM}, {1, am_IMP}, {1, am_IMP}, {3, am_ABS}, {3, am_ABS}, {3, am_ABS}, {1, am_IMP},  // 0x28-0x2F
    {2, am_REL}, {2, am_IZY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {2, am_ZPX}, {2, am_ZPX}, {1, am_IMP},  // 0x30-0x37
    {1, am_IMP}, {3, am_ABY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {3, am_ABX}, {3, am_ABX}, {1, am_IMP},  // 0x38-0x3F

    {1, am_IMP}, {2, am_IZX}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {2, am_ZP }, {2, am_ZP }, {1, am_IMP},  // 0x40-0x47
    {1, am_IMP}, {2, am_IMM}, {1, am_IMP}, {1, am_IMP}, {3, am_ABS}, {3, am_ABS}, {3, am_ABS}, {1, am_IMP},  // 0x48-0x4F
    {2, am_REL}, {2, am_IZY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {2, am_ZPX}, {2, am_ZPX}, {1, am_IMP},  // 0x50-0x57
    {1, am_IMP}, {3, am_ABY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {3, am_ABX}, {3, am_ABX}, {1, am_IMP},  // 0x58-0x5F

    {1, am_IMP}, {2, am_IZX}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {2, am_ZP }, {2, am_ZP }, {1, am_IMP},  // 0x60-0x67
    {1, am_IMP}, {2, am_IMM}, {1, am_IMP}, {1, am_IMP}, {3, am_IND}, {3, am_ABS}, {3, am_ABS}, {1, am_IMP},  // 0x68-0x6F
    {2, am_REL}, {2, am_IZY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {2, am_ZPX}, {2, am_ZPX}, {1, am_IMP},  // 0x70-0x77
    {1, am_IMP}, {3, am_ABY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {3, am_ABX}, {3, am_ABX}, {1, am_IMP},  // 0x78-0x7F

    {1, am_IMP}, {2, am_IZX}, {1, am_IMP}, {1, am_IMP}, {2, am_ZP }, {2, am_ZP }, {2, am_ZP }, {1, am_IMP},  // 0x80-0x87
    {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {3, am_ABS}, {3, am_ABS}, {3, am_ABS}, {1, am_IMP},  // 0x88-0x8F
    {2, am_REL}, {2, am_IZY}, {1, am_IMP}, {1, am_IMP}, {2, am_ZPX}, {2, am_ZPX}, {2, am_ZPY}, {1, am_IMP},  // 0x90-0x97
    {1, am_IMP}, {3, am_ABY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {3, am_ABX}, {1, am_IMP}, {1, am_IMP},  // 0x98-0x9F

    {2, am_IMM}, {2, am_IZX}, {2, am_IMM}, {1, am_IMP}, {2, am_ZP }, {2, am_ZP }, {2, am_ZP }, {1, am_IMP},  // 0xA0-0xA7
    {1, am_IMP}, {2, am_IMM}, {1, am_IMP}, {1, am_IMP}, {3, am_ABS}, {3, am_ABS}, {3, am_ABS}, {1, am_IMP},  // 0xA8-0xAF
    {2, am_REL}, {2, am_IZY}, {1, am_IMP}, {1, am_IMP}, {2, am_ZPX}, {2, am_ZPX}, {2, am_ZPY}, {1, am_IMP},  // 0xB0-0xB7
    {1, am_IMP}, {3, am_ABY}, {1, am_IMP}, {1, am_IMP}, {3, am_ABX}, {3, am_ABX}, {3, am_ABY}, {1, am_IMP},  // 0xB8-0xBF

    {2, am_IMM}, {2, am_IZX}, {1, am_IMP}, {1, am_IMP}, {2, am_ZP }, {2, am_ZP }, {2, am_ZP }, {1, am_IMP},  // 0xC0-0xC7
    {1, am_IMP}, {2, am_IMM}, {1, am_IMP}, {1, am_IMP}, {3, am_ABS}, {3, am_ABS}, {3, am_ABS}, {1, am_IMP},  // 0xC8-0xCF
    {2, am_REL}, {2, am_IZY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {2, am_ZPX}, {2, am_ZPX}, {1, am_IMP},  // 0xD0-0xD7
    {1, am_IMP}, {3, am_ABY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {3, am_ABX}, {3, am_ABX}, {1, am_IMP},  // 0xD8-0xDF

    {2, am_IMM}, {2, am_IZX}, {1, am_IMP}, {1, am_IMP}, {2, am_ZP }, {2, am_ZP }, {2, am_ZP }, {1, am_IMP},  // 0xE0-0xE7
    {1, am_IMP}, {2, am_IMM}, {1, am_IMP}, {1, am_IMP}, {3, am_ABS}, {3, am_ABS}, {3, am_ABS}, {1, am_IMP},  // 0xE8-0xEF
    {2, am_REL}, {2, am_IZY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {2, am_ZPX}, {2, am_ZPX}, {1, am_IMP},  // 0xF0-0xF7
    {1, am_IMP}, {3, am_ABY}, {1, am_IMP}, {1, am_IMP}, {1, am_IMP}, {3, am_ABX}, {3, am_ABX}, {1, am_IMP}   // 0xF8-0xFF
};


unsigned char GetOpcodeSize(unsigned char opcode) {
    return opcode_table[opcode].size;
}


AddressingMode GetOpcodeAddressingMode(unsigned char opcode) {
    return opcode_table[opcode].mode;
}


bool RequiresRelocation(AddressingMode mode) {
    // Absolute addressing modes that need address patching
    return (mode == am_ABS || mode == am_ABX || mode == am_ABY || mode == am_IND);
}


bool RequiresZeroPageAdjustment(AddressingMode mode) {
    // Zero page addressing modes that need ZP base adjustment
    return (mode == am_ZP || mode == am_ZPX || mode == am_ZPY ||
            mode == am_IZX || mode == am_IZY);
}

} // namespace SF2Pack
