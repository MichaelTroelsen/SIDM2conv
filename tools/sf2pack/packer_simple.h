/*
 * packer_simple.h - Simplified SF2 Packer
 *
 * Simplified version of SID Factory II Packer class
 * Performs 6502 code relocation for SF2 → SID export
 */

#pragma once

#include "c64memory.h"
#include <vector>

namespace SF2Pack {

// Driver 11 configuration (hardcoded)
struct DriverConfig {
    unsigned short driver_code_top;     // Where driver code starts (e.g., 0x1000)
    unsigned short driver_code_size;    // Size of driver code region
    unsigned char current_lowest_zp;    // Current zero page base in driver
    unsigned char target_lowest_zp;     // Target zero page base for export
    unsigned short destination_address; // Target load address for SID
};


class PackerSimple {
public:
    PackerSimple(const DriverConfig& config);
    ~PackerSimple();

    // Pack SF2 data with relocation
    // Input: SF2 file loaded into memory
    // Output: Packed PRG data ready for PSID export
    std::vector<unsigned char> Pack(const C64Memory& memory);

private:
    // Process driver code with address relocation
    void ProcessDriverCode(C64Memory& memory);

    // Calculate address delta for relocation
    unsigned short GetAddressDelta() const;

    // Relocate a single vector (address)
    unsigned short RelocateVector(unsigned short vector) const;

    DriverConfig config_;
};

} // namespace SF2Pack
