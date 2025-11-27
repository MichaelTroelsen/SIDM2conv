/*
 * sf2pack.cpp - SF2 to SID Packer (Main Entry Point)
 *
 * Command-line tool to pack SF2 files into playable SID format
 * with full 6502 code relocation support.
 *
 * Usage: sf2pack input.sf2 output.sid [options]
 */

#include "c64memory.h"
#include "packer_simple.h"
#include "psidfile.h"
#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <cstring>

using namespace SF2Pack;

// Default Driver 11 configuration
struct DefaultDriverConfig {
    static const unsigned short DRIVER_CODE_TOP = 0x0D7E;   // From Angular.sf2 analysis
    static const unsigned short DRIVER_CODE_SIZE = 0x0800;  // ~2KB driver code
    static const unsigned char CURRENT_LOWEST_ZP = 0x02;    // Driver 11 default
    static const unsigned short INIT_OFFSET = 0x0000;       // Init at driver start
    static const unsigned short PLAY_OFFSET = 0x0003;       // Play at driver+3
};


// Read entire file into memory
std::vector<unsigned char> ReadFile(const std::string& filename) {
    std::ifstream file(filename, std::ios::binary | std::ios::ate);
    if (!file) {
        throw std::runtime_error("Cannot open file: " + filename);
    }

    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);

    std::vector<unsigned char> data(size);
    if (!file.read(reinterpret_cast<char*>(data.data()), size)) {
        throw std::runtime_error("Cannot read file: " + filename);
    }

    return data;
}


// Parse command line arguments
struct Options {
    std::string input_file;
    std::string output_file;
    unsigned short address = 0x1000;  // Default load address
    unsigned char zp = 0x02;          // Default zero page base
    std::string title;
    std::string author;
    std::string copyright;
    bool verbose = false;
};


bool ParseArguments(int argc, char* argv[], Options& options) {
    if (argc < 3) {
        return false;
    }

    options.input_file = argv[1];
    options.output_file = argv[2];

    for (int i = 3; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "--address" && i + 1 < argc) {
            options.address = static_cast<unsigned short>(std::stoul(argv[++i], nullptr, 0));
        } else if (arg == "--zp" && i + 1 < argc) {
            options.zp = static_cast<unsigned char>(std::stoul(argv[++i], nullptr, 0));
        } else if (arg == "--title" && i + 1 < argc) {
            options.title = argv[++i];
        } else if (arg == "--author" && i + 1 < argc) {
            options.author = argv[++i];
        } else if (arg == "--copyright" && i + 1 < argc) {
            options.copyright = argv[++i];
        } else if (arg == "-v" || arg == "--verbose") {
            options.verbose = true;
        } else if (arg == "--help" || arg == "-h") {
            return false;
        } else {
            std::cerr << "Unknown option: " << arg << "\n";
            return false;
        }
    }

    return true;
}


void PrintUsage(const char* program_name) {
    std::cout << "SF2Pack - SF2 to SID Packer with Full Code Relocation\n";
    std::cout << "======================================================\n\n";
    std::cout << "Usage: " << program_name << " <input.sf2> <output.sid> [options]\n\n";
    std::cout << "Options:\n";
    std::cout << "  --address ADDR    Target load address (hex or decimal, default: 0x1000)\n";
    std::cout << "  --zp ZP           Target zero page base (hex or decimal, default: 0x02)\n";
    std::cout << "  --title TITLE     Set song title\n";
    std::cout << "  --author AUTHOR   Set author name\n";
    std::cout << "  --copyright TEXT  Set copyright text\n";
    std::cout << "  -v, --verbose     Verbose output\n";
    std::cout << "  -h, --help        Show this help\n\n";
    std::cout << "Examples:\n";
    std::cout << "  " << program_name << " Angular.sf2 Angular.sid\n";
    std::cout << "  " << program_name << " file.sf2 file.sid --address 0x1000 --zp 0x02\n";
    std::cout << "  " << program_name << " file.sf2 file.sid --title \"My Song\" --author \"Me\"\n";
}


int main(int argc, char* argv[]) {
    try {
        // Parse command line
        Options options;
        if (!ParseArguments(argc, argv, options)) {
            PrintUsage(argv[0]);
            return 1;
        }

        if (options.verbose) {
            std::cout << "SF2Pack v1.0 - SF2 to SID Packer\n";
            std::cout << "=================================\n";
            std::cout << "Input:  " << options.input_file << "\n";
            std::cout << "Output: " << options.output_file << "\n";
            std::cout << "Target address: $" << std::hex << options.address << std::dec << "\n";
            std::cout << "Target ZP base: $" << std::hex << (int)options.zp << std::dec << "\n\n";
        }

        // Step 1: Load SF2 file
        if (options.verbose) {
            std::cout << "Loading SF2 file...\n";
        }

        std::vector<unsigned char> sf2_data = ReadFile(options.input_file);

        if (sf2_data.size() < 3) {
            throw std::runtime_error("SF2 file too small");
        }

        // Step 2: Load into C64 memory
        C64Memory memory;
        if (!memory.LoadFromPRG(sf2_data.data(), sf2_data.size())) {
            throw std::runtime_error("Failed to load SF2 data into memory");
        }

        // Extract load address for info
        unsigned short sf2_load_address = sf2_data[0] | (sf2_data[1] << 8);

        if (options.verbose) {
            std::cout << "  SF2 load address: $" << std::hex << sf2_load_address << std::dec << "\n";
            std::cout << "  Data size: " << (sf2_data.size() - 2) << " bytes\n\n";
        }

        // Step 3: Configure packer
        DriverConfig config;
        config.driver_code_top = DefaultDriverConfig::DRIVER_CODE_TOP;
        config.driver_code_size = DefaultDriverConfig::DRIVER_CODE_SIZE;
        config.current_lowest_zp = DefaultDriverConfig::CURRENT_LOWEST_ZP;
        config.target_lowest_zp = options.zp;
        config.destination_address = options.address;

        // Step 4: Pack with relocation
        if (options.verbose) {
            std::cout << "Packing with relocation...\n";
        }

        PackerSimple packer(config);
        std::vector<unsigned char> packed_data = packer.Pack(memory);

        if (options.verbose) {
            std::cout << "  Packed size: " << (packed_data.size() - 2) << " bytes\n\n";
        }

        // Step 5: Create PSID file
        if (options.verbose) {
            std::cout << "Creating PSID file...\n";
        }

        PSIDFile psid;
        if (!psid.CreateFromPRG(packed_data.data(), packed_data.size(),
                                DefaultDriverConfig::INIT_OFFSET,
                                DefaultDriverConfig::PLAY_OFFSET)) {
            throw std::runtime_error("Failed to create PSID file");
        }

        // Set metadata
        if (!options.title.empty()) {
            psid.SetTitle(options.title);
        }
        if (!options.author.empty()) {
            psid.SetAuthor(options.author);
        }
        if (!options.copyright.empty()) {
            psid.SetCopyright(options.copyright);
        }

        // Step 6: Write output
        if (!psid.WriteToFile(options.output_file)) {
            throw std::runtime_error("Failed to write output file");
        }

        if (options.verbose) {
            std::cout << "\nConversion complete!\n";
            std::cout << "Output: " << options.output_file << "\n";
        } else {
            std::cout << "Successfully created " << options.output_file << "\n";
        }

        return 0;

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
}
