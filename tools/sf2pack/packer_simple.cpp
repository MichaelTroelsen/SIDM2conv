/*
 * packer_simple.cpp - Simplified SF2 Packer Implementation
 *
 * Core 6502 code relocation logic extracted from SID Factory II
 * This is the CRITICAL component that sf2export.cpp was missing!
 */

#include "packer_simple.h"
#include "opcodes.h"
#include <stdexcept>
#include <iostream>

namespace SF2Pack {

PackerSimple::PackerSimple(const DriverConfig& config)
    : config_(config) {
}


PackerSimple::~PackerSimple() {
}


std::vector<unsigned char> PackerSimple::Pack(const C64Memory& input_memory) {
    // Make a working copy of the memory
    C64Memory memory;
    for (unsigned int i = 0; i < 0x10000; ++i) {
        memory[i] = input_memory[i];
    }

    // Step 1: Process driver code with relocation
    ProcessDriverCode(memory);

    // Step 2: Find the end of data
    unsigned short data_start = config_.driver_code_top;
    unsigned short data_end = config_.driver_code_top + config_.driver_code_size;

    // Extend to include all data tables (scan up to 0x3000 for safety)
    for (unsigned short addr = data_end; addr < 0x3000; ++addr) {
        if (memory[addr] != 0) {
            data_end = addr + 1;
        }
    }

    unsigned int data_size = data_end - data_start;

    // Step 3: Move data to destination address
    // This is critical! We've patched the CODE, now we need to MOVE the data
    if (config_.destination_address != config_.driver_code_top) {
        for (unsigned int i = 0; i < data_size; ++i) {
            memory[config_.destination_address + i] = memory[config_.driver_code_top + i];
        }
        // Clear old location
        for (unsigned short addr = config_.driver_code_top; addr < data_end; ++addr) {
            memory[addr] = 0;
        }
    }

    // Step 4: Export as PRG from destination address
    std::vector<unsigned char> packed_data = memory.ExportToPRG(
        config_.destination_address,
        config_.destination_address + data_size
    );

    return packed_data;
}


void PackerSimple::ProcessDriverCode(C64Memory& memory) {
    // This is the CRITICAL function that performs 6502 code relocation
    // Extracted from packer.cpp:429-509

    const unsigned short driver_top = config_.driver_code_top;
    const unsigned short driver_size = config_.driver_code_size;
    const unsigned short driver_bottom = driver_top + driver_size;
    const unsigned short address_delta = GetAddressDelta();

    std::cout << "Processing driver code:\n";
    std::cout << "  Driver: $" << std::hex << driver_top
              << " - $" << driver_bottom << std::dec << "\n";
    std::cout << "  Address delta: " << std::hex << address_delta << std::dec << "\n";
    std::cout << "  ZP: $" << std::hex << (int)config_.current_lowest_zp
              << " -> $" << (int)config_.target_lowest_zp << std::dec << "\n";

    unsigned int relocations_abs = 0;
    unsigned int relocations_zp = 0;

    // Scan through driver code instruction by instruction
    unsigned short address = driver_top;

    while (address < driver_bottom) {
        unsigned char opcode = memory[address];
        unsigned char opcode_size = GetOpcodeSize(opcode);
        AddressingMode mode = GetOpcodeAddressingMode(opcode);

        // Relocate absolute addresses (ABS, ABX, ABY, IND)
        if (RequiresRelocation(mode)) {
            if (opcode_size != 3) {
                throw std::runtime_error("Expected 3-byte instruction for absolute addressing");
            }

            // Read the 16-bit address (little-endian)
            unsigned short vector = memory.GetWord(address + 1);

            // Determine relocated address
            unsigned short relocated_vector;

            // Don't relocate ROM addresses ($D000-$DFFF contains SID chip, I/O, ROM)
            if (vector >= 0xD000 && vector <= 0xDFFF) {
                relocated_vector = vector;  // Keep ROM addresses unchanged
            } else {
                // Apply relocation delta
                relocated_vector = vector + address_delta;
            }

            // Patch the instruction if address changed
            if (vector != relocated_vector) {
                memory.SetWord(address + 1, relocated_vector);
                relocations_abs++;
            }
        }

        // Relocate zero page addresses (ZP, ZPX, ZPY, IZX, IZY)
        if (RequiresZeroPageAdjustment(mode)) {
            if (opcode_size != 2) {
                throw std::runtime_error("Expected 2-byte instruction for zero page addressing");
            }

            unsigned char zp = memory.GetByte(address + 1);

            // Calculate relative offset from current ZP base
            unsigned char zp_offset = zp - config_.current_lowest_zp;

            // Apply new ZP base
            unsigned char zp_relocated = config_.target_lowest_zp + zp_offset;

            // Patch the instruction
            memory.SetByte(address + 1, zp_relocated);
            relocations_zp++;
        }

        // Move to next instruction
        address += opcode_size;
    }

    std::cout << "  Relocations: " << relocations_abs << " absolute, "
              << relocations_zp << " zero page\n";
}


unsigned short PackerSimple::GetAddressDelta() const {
    // Calculate how much to adjust all addresses
    // This moves code/data from current location to target location
    return config_.destination_address - config_.driver_code_top;
}


unsigned short PackerSimple::RelocateVector(unsigned short vector) const {
    // Apply relocation delta, but protect ROM addresses
    if (vector >= 0xD000 && vector <= 0xDFFF) {
        return vector;  // ROM/IO region
    }
    return vector + GetAddressDelta();
}

} // namespace SF2Pack
