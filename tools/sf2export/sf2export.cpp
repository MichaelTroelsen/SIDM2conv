/*
 * SF2Export - Standalone SF2 to PSID Converter
 *
 * Minimal extraction from SID Factory II source code to enable
 * SF2 → SID conversion for automated testing.
 *
 * Based on: SIDFactoryII/source/utils/psidfile.cpp
 * License: Same as SID Factory II (GPL)
 */

#include <iostream>
#include <fstream>
#include <cstring>
#include <string>
#include <vector>

// Endian conversion for big-endian PSID format
unsigned short endian_convert(unsigned short value) {
    return (value >> 8) | (value << 8);
}

// PSID file header structure
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

// Copy string into fixed-size buffer with null padding
void copy_string(const std::string& src, char* dest, size_t size) {
    size_t len = src.length();
    for (size_t i = 0; i < size; ++i) {
        dest[i] = (i < len) ? src[i] : 0;
    }
}

// Read entire file into memory
std::vector<unsigned char> read_file(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary);
    if (!file) {
        throw std::runtime_error("Cannot open file: " + filename);
    }

    file.seekg(0, std::ios::end);
    size_t size = file.tellg();
    file.seekg(0, std::ios::beg);

    std::vector<unsigned char> data(size);
    file.read(reinterpret_cast<char*>(data.data()), size);

    return data;
}

// Write binary data to file
void write_file(const std::string& filename, const unsigned char* data, size_t size) {
    std::ofstream file(filename, std::ios::binary);
    if (!file) {
        throw std::runtime_error("Cannot write file: " + filename);
    }

    file.write(reinterpret_cast<const char*>(data), size);
}

// Extract metadata strings from SF2 auxiliary data section
void extract_metadata(const std::vector<unsigned char>& data,
                     std::string& title, std::string& author, std::string& copyright) {
    // SF2 files store metadata as null-terminated strings near the end
    // Search last 512 bytes for printable strings
    size_t search_start = (data.size() > 512) ? (data.size() - 512) : 0;

    std::vector<std::string> strings;
    std::string current;

    for (size_t i = search_start; i < data.size(); ++i) {
        unsigned char c = data[i];

        if (c == 0) {
            if (current.length() > 3) {  // Reasonable string length
                strings.push_back(current);
            }
            current.clear();
        } else if (c >= 0x20 && c <= 0x7E) {  // Printable ASCII
            current += static_cast<char>(c);
        } else {
            current.clear();  // Reset on non-printable
        }
    }

    // Take last 3 strings as title/author/copyright
    if (strings.size() >= 3) {
        title = strings[strings.size() - 3];
        author = strings[strings.size() - 2];
        copyright = strings[strings.size() - 1];
    } else if (strings.size() >= 2) {
        title = strings[strings.size() - 2];
        author = strings[strings.size() - 1];
    } else if (strings.size() >= 1) {
        title = strings[strings.size() - 1];
    }
}

// Convert SF2 file to PSID format
void convert_sf2_to_psid(const std::string& sf2_path, const std::string& sid_path,
                        unsigned short init_offset, unsigned short play_offset,
                        bool verbose) {
    if (verbose) {
        std::cout << "SF2Export v1.0 - SF2 to PSID Converter\n";
        std::cout << "======================================\n";
        std::cout << "Input:  " << sf2_path << "\n";
        std::cout << "Output: " << sid_path << "\n";
    }

    // Read SF2 file (PRG format: first 2 bytes are load address)
    std::vector<unsigned char> sf2_data = read_file(sf2_path);

    if (sf2_data.size() < 2) {
        throw std::runtime_error("SF2 file too small");
    }

    // Extract load address (little-endian)
    unsigned short driver_address = static_cast<unsigned short>(sf2_data[0]) |
                                   (static_cast<unsigned short>(sf2_data[1]) << 8);

    // Extract metadata
    std::string title, author, copyright;
    extract_metadata(sf2_data, title, author, copyright);

    if (verbose) {
        std::cout << "\nSF2 Analysis:\n";
        std::cout << "  Load address: $" << std::hex << driver_address << std::dec << "\n";
        std::cout << "  Data size:    " << (sf2_data.size() - 2) << " bytes\n";
        if (!title.empty())
            std::cout << "  Title:        " << title << "\n";
        if (!author.empty())
            std::cout << "  Author:       " << author << "\n";
        if (!copyright.empty())
            std::cout << "  Copyright:    " << copyright << "\n";
    }

    // Create PSID header
    PSIDHeader header;
    memset(&header, 0, sizeof(header));

    header.magic[0] = 'P';
    header.magic[1] = 'S';
    header.magic[2] = 'I';
    header.magic[3] = 'D';

    header.version = endian_convert(0x0002);
    header.data_offset = endian_convert(0x007C);  // 124 bytes
    header.load_address = 0x0000;  // Use PRG address
    header.init_address = endian_convert(driver_address + init_offset);
    header.play_address = endian_convert(driver_address + play_offset);
    header.song_count = endian_convert(1);
    header.default_song = endian_convert(1);
    header.speed_flags = 0;  // 50Hz PAL

    copy_string(title, header.title, 32);
    copy_string(author, header.author, 32);
    copy_string(copyright, header.copyright, 32);

    // Flags: 6581 SID (0x10) + PAL (0x04)
    header.flags = endian_convert(0x14);

    header.start_page = 0;
    header.page_length = 0;
    header.second_sid = 0;
    header.third_sid = 0;

    // Build PSID file: [header][PRG data]
    size_t psid_size = sizeof(header) + sf2_data.size();
    std::vector<unsigned char> psid_data(psid_size);

    memcpy(psid_data.data(), &header, sizeof(header));
    memcpy(psid_data.data() + sizeof(header), sf2_data.data(), sf2_data.size());

    // Write PSID file
    write_file(sid_path, psid_data.data(), psid_size);

    if (verbose) {
        std::cout << "\nPSID Export:\n";
        std::cout << "  Init address: $" << std::hex << (driver_address + init_offset) << std::dec << "\n";
        std::cout << "  Play address: $" << std::hex << (driver_address + play_offset) << std::dec << "\n";
        std::cout << "  Total size:   " << psid_size << " bytes\n";
        std::cout << "\nConversion complete!\n";
    }
}

int main(int argc, char* argv[]) {
    try {
        // Parse command line
        if (argc < 3) {
            std::cerr << "Usage: sf2export <input.sf2> <output.sid> [options]\n";
            std::cerr << "\nOptions:\n";
            std::cerr << "  --driver11       Driver 11 offsets (init=0, play=3) [default]\n";
            std::cerr << "  --np20           NewPlayer 20 offsets (init=0, play=161)\n";
            std::cerr << "  --init <offset>  Custom init offset (hex or decimal)\n";
            std::cerr << "  --play <offset>  Custom play offset (hex or decimal)\n";
            std::cerr << "  -v, --verbose    Verbose output\n";
            std::cerr << "\nExample:\n";
            std::cerr << "  sf2export Angular.sf2 Angular_converted.sid\n";
            std::cerr << "  sf2export file.sf2 file.sid --np20 -v\n";
            return 1;
        }

        std::string sf2_path = argv[1];
        std::string sid_path = argv[2];

        // Default: Driver 11 offsets
        unsigned short init_offset = 0;
        unsigned short play_offset = 3;
        bool verbose = false;

        // Parse options
        for (int i = 3; i < argc; ++i) {
            std::string arg = argv[i];

            if (arg == "--driver11") {
                init_offset = 0;
                play_offset = 3;
            } else if (arg == "--np20") {
                init_offset = 0;
                play_offset = 0xA1;  // 161 decimal
            } else if (arg == "--init" && i + 1 < argc) {
                init_offset = static_cast<unsigned short>(std::stoul(argv[++i], nullptr, 0));
            } else if (arg == "--play" && i + 1 < argc) {
                play_offset = static_cast<unsigned short>(std::stoul(argv[++i], nullptr, 0));
            } else if (arg == "-v" || arg == "--verbose") {
                verbose = true;
            } else {
                std::cerr << "Unknown option: " << arg << "\n";
                return 1;
            }
        }

        // Perform conversion
        convert_sf2_to_psid(sf2_path, sid_path, init_offset, play_offset, verbose);

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
}
