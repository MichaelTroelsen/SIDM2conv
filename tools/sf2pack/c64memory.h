/*
 * c64memory.h - Simplified C64 Memory Management
 *
 * Minimal 64KB memory container for SF2 packing
 * Simplified from SID Factory II C64File class
 */

#pragma once

#include <cstring>
#include <vector>

namespace SF2Pack {

class C64Memory {
public:
    C64Memory();
    ~C64Memory();

    // Load from PRG format (2-byte load address + data)
    bool LoadFromPRG(const unsigned char* prg_data, unsigned int prg_size);

    // Load from raw data at specific address
    bool LoadFromData(unsigned short load_address, const unsigned char* data, unsigned int data_size);

    // Export to PRG format
    std::vector<unsigned char> ExportToPRG(unsigned short top_address, unsigned short bottom_address) const;

    // Memory access
    unsigned char& operator[](unsigned short address);
    unsigned char operator[](unsigned short address) const;

    unsigned char GetByte(unsigned short address) const;
    unsigned short GetWord(unsigned short address) const;  // Little-endian

    void SetByte(unsigned short address, unsigned char value);
    void SetWord(unsigned short address, unsigned short value);  // Little-endian

    // Get raw data pointer (use with caution)
    unsigned char* GetRawData();
    const unsigned char* GetRawData() const;

    // Clear memory
    void Clear();

private:
    unsigned char data_[0x10000];  // 64KB C64 memory space
};

} // namespace SF2Pack
