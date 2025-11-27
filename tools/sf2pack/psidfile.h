/*
 * psidfile.h - PSID File Export
 *
 * Creates PSID v2 format files from packed SF2 data
 * Based on SID Factory II PSIDFile class
 */

#pragma once

#include <string>
#include <vector>

namespace SF2Pack {

// PSID file header structure (124 bytes)
#pragma pack(push, 1)
struct PSIDHeader {
    char magic[4];               // 0x00: 'PSID'
    unsigned short version;      // 0x04: 0x0002 (big-endian)
    unsigned short data_offset;  // 0x06: 0x007C (124 bytes)
    unsigned short load_address; // 0x08: 0x0000 (use PRG address)
    unsigned short init_address; // 0x0A: driver_address + init_offset
    unsigned short play_address; // 0x0C: driver_address + play_offset
    unsigned short song_count;   // 0x0E: Number of songs
    unsigned short default_song; // 0x10: Default song (1-based)
    unsigned int speed_flags;    // 0x12: Speed bits (0=60Hz, 1=50Hz)
    char title[32];              // 0x16: Title (null-padded)
    char author[32];             // 0x36: Author (null-padded)
    char copyright[32];          // 0x56: Copyright (null-padded)
    unsigned short flags;        // 0x76: SID model and video standard
    unsigned char start_page;    // 0x78: Relocation start page
    unsigned char page_length;   // 0x79: Relocation page count
    unsigned char second_sid;    // 0x7A: Second SID address
    unsigned char third_sid;     // 0x7B: Third SID address
};
#pragma pack(pop)


class PSIDFile {
public:
    PSIDFile();
    ~PSIDFile();

    // Create PSID from PRG data
    bool CreateFromPRG(const unsigned char* prg_data, unsigned int prg_size,
                       unsigned short init_offset, unsigned short play_offset);

    // Set metadata
    void SetTitle(const std::string& title);
    void SetAuthor(const std::string& author);
    void SetCopyright(const std::string& copyright);

    // Export to file
    bool WriteToFile(const std::string& filename) const;

    // Get PSID data
    std::vector<unsigned char> GetPSIDData() const;

private:
    void InitializeHeader();
    void CopyString(const std::string& src, char* dest, size_t size);
    unsigned short EndianConvert(unsigned short value) const;

    PSIDHeader header_;
    std::vector<unsigned char> prg_data_;
};

} // namespace SF2Pack
