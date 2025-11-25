/*
 * psidfile.cpp - PSID File Export Implementation
 *
 * Creates PSID v2 format files from packed SF2 data
 */

#include "psidfile.h"
#include <fstream>
#include <cstring>
#include <stdexcept>

namespace SF2Pack {

PSIDFile::PSIDFile() {
    InitializeHeader();
}


PSIDFile::~PSIDFile() {
}


bool PSIDFile::CreateFromPRG(const unsigned char* prg_data, unsigned int prg_size,
                              unsigned short init_offset, unsigned short play_offset) {
    if (!prg_data || prg_size < 3) {
        return false;
    }

    // Extract load address from PRG (first 2 bytes, little-endian)
    unsigned short load_address = prg_data[0] | (prg_data[1] << 8);

    // Store PRG data
    prg_data_.clear();
    prg_data_.insert(prg_data_.end(), prg_data, prg_data + prg_size);

    // Set header addresses
    header_.load_address = 0x0000;  // Use PRG load address
    header_.init_address = EndianConvert(load_address + init_offset);
    header_.play_address = EndianConvert(load_address + play_offset);

    return true;
}


void PSIDFile::SetTitle(const std::string& title) {
    CopyString(title, header_.title, 32);
}


void PSIDFile::SetAuthor(const std::string& author) {
    CopyString(author, header_.author, 32);
}


void PSIDFile::SetCopyright(const std::string& copyright) {
    CopyString(copyright, header_.copyright, 32);
}


bool PSIDFile::WriteToFile(const std::string& filename) const {
    std::ofstream file(filename, std::ios::binary);
    if (!file) {
        return false;
    }

    // Write header
    file.write(reinterpret_cast<const char*>(&header_), sizeof(header_));

    // Write PRG data
    if (!prg_data_.empty()) {
        file.write(reinterpret_cast<const char*>(prg_data_.data()), prg_data_.size());
    }

    return file.good();
}


std::vector<unsigned char> PSIDFile::GetPSIDData() const {
    std::vector<unsigned char> psid_data;

    // Add header
    const unsigned char* header_bytes = reinterpret_cast<const unsigned char*>(&header_);
    psid_data.insert(psid_data.end(), header_bytes, header_bytes + sizeof(header_));

    // Add PRG data
    psid_data.insert(psid_data.end(), prg_data_.begin(), prg_data_.end());

    return psid_data;
}


void PSIDFile::InitializeHeader() {
    std::memset(&header_, 0, sizeof(header_));

    // Magic identifier
    header_.magic[0] = 'P';
    header_.magic[1] = 'S';
    header_.magic[2] = 'I';
    header_.magic[3] = 'D';

    // PSID v2
    header_.version = EndianConvert(0x0002);

    // Data offset (124 bytes header)
    header_.data_offset = EndianConvert(0x007C);

    // Default values
    header_.song_count = EndianConvert(1);
    header_.default_song = EndianConvert(1);
    header_.speed_flags = 0;  // 50Hz PAL

    // Flags: 6581 SID (0x10) + PAL (0x04)
    header_.flags = EndianConvert(0x0014);

    // Relocation info (not used)
    header_.start_page = 0;
    header_.page_length = 0;
    header_.second_sid = 0;
    header_.third_sid = 0;
}


void PSIDFile::CopyString(const std::string& src, char* dest, size_t size) {
    size_t len = src.length();
    for (size_t i = 0; i < size; ++i) {
        dest[i] = (i < len) ? src[i] : 0;
    }
}


unsigned short PSIDFile::EndianConvert(unsigned short value) const {
    // Convert to big-endian (PSID format)
    return (value >> 8) | (value << 8);
}

} // namespace SF2Pack
