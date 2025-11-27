/*
 * c64memory.cpp - Simplified C64 Memory Management Implementation
 *
 * Minimal 64KB memory container for SF2 packing
 */

#include "c64memory.h"
#include <stdexcept>

namespace SF2Pack {

C64Memory::C64Memory() {
    Clear();
}


C64Memory::~C64Memory() {
}


bool C64Memory::LoadFromPRG(const unsigned char* prg_data, unsigned int prg_size) {
    if (!prg_data || prg_size < 3) {
        return false;
    }

    // PRG format: first 2 bytes are load address (little-endian)
    unsigned short load_address = prg_data[0] | (prg_data[1] << 8);
    unsigned int data_size = prg_size - 2;

    // Check if data fits in memory
    if (load_address + data_size > 0x10000) {
        return false;
    }

    // Copy data to memory
    std::memcpy(&data_[load_address], &prg_data[2], data_size);

    return true;
}


bool C64Memory::LoadFromData(unsigned short load_address, const unsigned char* data, unsigned int data_size) {
    if (!data || data_size == 0) {
        return false;
    }

    // Check if data fits in memory
    if (load_address + data_size > 0x10000) {
        return false;
    }

    // Copy data to memory
    std::memcpy(&data_[load_address], data, data_size);

    return true;
}


std::vector<unsigned char> C64Memory::ExportToPRG(unsigned short top_address, unsigned short bottom_address) const {
    if (top_address >= bottom_address) {
        throw std::runtime_error("Invalid address range for PRG export");
    }

    unsigned int data_size = bottom_address - top_address;
    std::vector<unsigned char> prg_data(data_size + 2);

    // Write load address (little-endian)
    prg_data[0] = top_address & 0xFF;
    prg_data[1] = (top_address >> 8) & 0xFF;

    // Write data
    std::memcpy(&prg_data[2], &data_[top_address], data_size);

    return prg_data;
}


unsigned char& C64Memory::operator[](unsigned short address) {
    return data_[address];
}


unsigned char C64Memory::operator[](unsigned short address) const {
    return data_[address];
}


unsigned char C64Memory::GetByte(unsigned short address) const {
    return data_[address];
}


unsigned short C64Memory::GetWord(unsigned short address) const {
    // Little-endian word read
    return data_[address] | (data_[address + 1] << 8);
}


void C64Memory::SetByte(unsigned short address, unsigned char value) {
    data_[address] = value;
}


void C64Memory::SetWord(unsigned short address, unsigned short value) {
    // Little-endian word write
    data_[address] = value & 0xFF;
    data_[address + 1] = (value >> 8) & 0xFF;
}


unsigned char* C64Memory::GetRawData() {
    return data_;
}


const unsigned char* C64Memory::GetRawData() const {
    return data_;
}


void C64Memory::Clear() {
    std::memset(data_, 0, 0x10000);
}

} // namespace SF2Pack
