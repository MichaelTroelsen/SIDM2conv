#!/usr/bin/env python3
"""
Laxity Player Format Analyzer

This tool analyzes SID files that use Laxity's player routine and attempts
to extract the music data structure for conversion to SID Factory II format.

Based on analysis of Unboxed_Ending_8580.sid:
- Load: $1000
- Init: $1000 (JMP $1040)
- Play: $1003 (JMP $10C6)
- Data ends at $219F
"""

import struct
import sys
import os


def read_sid_file(filepath):
    """Read and parse SID file, return C64 data and addresses"""
    with open(filepath, 'rb') as f:
        data = f.read()

    # Parse PSID header
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_address = struct.unpack('>H', data[8:10])[0]
    init_address = struct.unpack('>H', data[10:12])[0]
    play_address = struct.unpack('>H', data[12:14])[0]

    # Get C64 data
    c64_data = data[data_offset:]

    # Handle embedded load address
    if load_address == 0:
        load_address = struct.unpack('<H', c64_data[0:2])[0]
        c64_data = c64_data[2:]

    return c64_data, load_address, init_address, play_address


class LaxityAnalyzer:
    """Analyze Laxity player format to understand data structure"""

    def __init__(self, c64_data, load_address):
        self.data = c64_data
        self.load_addr = load_address
        self.end_addr = load_address + len(c64_data)

        # Create virtual C64 memory
        self.memory = bytearray(65536)
        end = min(load_address + len(c64_data), 65536)
        self.memory[load_address:end] = c64_data[:end - load_address]

    def get_byte(self, addr):
        return self.memory[addr & 0xFFFF]

    def get_word(self, addr):
        return self.get_byte(addr) | (self.get_byte(addr + 1) << 8)

    def analyze_init_routine(self, init_addr):
        """Analyze the init routine to find data pointers"""
        print(f"\n=== INIT ROUTINE ANALYSIS (${init_addr:04X}) ===\n")

        # First instruction should be JMP to actual init
        if self.get_byte(init_addr) == 0x4C:  # JMP
            real_init = self.get_word(init_addr + 1)
            print(f"Init jumps to: ${real_init:04X}")
            return self.analyze_routine(real_init)

        return self.analyze_routine(init_addr)

    def analyze_routine(self, addr):
        """Analyze a routine and find absolute address references"""
        addresses = []
        i = 0
        max_bytes = 256

        # Simple disassembly to find absolute addresses
        while i < max_bytes:
            opcode = self.get_byte(addr + i)

            # Look for instructions with absolute addressing
            # LDA abs, STA abs, JSR abs, JMP abs, etc.
            abs_opcodes = {
                0x20: 3,  # JSR
                0x4C: 3,  # JMP
                0x8D: 3,  # STA abs
                0x8E: 3,  # STX abs
                0x8C: 3,  # STY abs
                0xAD: 3,  # LDA abs
                0xAE: 3,  # LDX abs
                0xAC: 3,  # LDY abs
                0xBD: 3,  # LDA abs,X
                0xB9: 3,  # LDA abs,Y
                0x9D: 3,  # STA abs,X
                0x99: 3,  # STA abs,Y
                0xCD: 3,  # CMP abs
                0xEC: 3,  # CPX abs
                0xCC: 3,  # CPY abs
                0x2D: 3,  # AND abs
                0x0D: 3,  # ORA abs
                0x4D: 3,  # EOR abs
                0x6D: 3,  # ADC abs
                0xED: 3,  # SBC abs
                0xCE: 3,  # DEC abs
                0xEE: 3,  # INC abs
            }

            if opcode in abs_opcodes:
                target = self.get_word(addr + i + 1)
                if self.load_addr <= target < self.end_addr:
                    addresses.append(target)
                i += abs_opcodes[opcode]
            elif opcode == 0x60:  # RTS
                break
            else:
                # Skip based on addressing mode
                i += self._get_instruction_size(opcode)

        return sorted(set(addresses))

    def _get_instruction_size(self, opcode):
        """Get instruction size based on opcode"""
        # Simplified - returns typical sizes
        implied = [0x00, 0x08, 0x18, 0x28, 0x38, 0x48, 0x58, 0x60, 0x68,
                   0x78, 0x88, 0x8A, 0x98, 0x9A, 0xA8, 0xAA, 0xB8, 0xBA,
                   0xC8, 0xCA, 0xD8, 0xE8, 0xEA, 0xF8, 0x40]
        if opcode in implied:
            return 1

        # Branch and immediate/zero page typically 2 bytes
        if (opcode & 0x1F) in [0x00, 0x01, 0x04, 0x05, 0x09, 0x10, 0x11,
                               0x14, 0x15]:
            return 2

        # Absolute typically 3 bytes
        return 3

    def find_pointer_tables(self):
        """Find low/high byte pointer table pairs"""
        print("\n=== SEARCHING FOR POINTER TABLES ===\n")

        candidates = []

        for addr in range(self.load_addr, self.end_addr - 16):
            # Get potential low-byte table
            lo_bytes = [self.get_byte(addr + i) for i in range(8)]

            # Try to find matching high-byte table
            for offset in range(1, 128):
                hi_addr = addr + offset
                if hi_addr >= self.end_addr - 8:
                    break

                hi_bytes = [self.get_byte(hi_addr + i) for i in range(8)]

                # Check if these form valid pointers within our data
                valid = 0
                for i in range(8):
                    ptr = lo_bytes[i] | (hi_bytes[i] << 8)
                    if self.load_addr <= ptr < self.end_addr:
                        valid += 1

                if valid >= 6:
                    candidates.append((addr, hi_addr, offset, valid))

        # Sort by validity score
        candidates.sort(key=lambda x: x[3], reverse=True)

        # Print top candidates
        for lo, hi, offset, score in candidates[:10]:
            print(f"Lo table: ${lo:04X}, Hi table: ${hi:04X}, "
                  f"offset: {offset}, valid: {score}/8")

            # Show the pointers
            ptrs = []
            for i in range(8):
                ptr = self.get_byte(lo + i) | (self.get_byte(hi + i) << 8)
                ptrs.append(f"${ptr:04X}")
            print(f"  Pointers: {', '.join(ptrs)}")

        return candidates

    def analyze_sequence_data(self):
        """Analyze potential sequence data patterns"""
        print("\n=== ANALYZING SEQUENCE DATA PATTERNS ===\n")

        # Based on the hex dump, the data around $2000-$219F looks like sequence data
        # Common patterns observed:
        # - 0x7E, 0x7F = rest/tie
        # - 0x80-0x9F = instrument selection (0x80 = --, 0x90 = tie)
        # - 0xC0-0xCF = command prefixes
        # - 0x00-0x60 = note values

        # Scan for sequence-like regions
        regions = []

        for addr in range(self.load_addr + 0x800, self.end_addr - 32):
            score = 0
            events = 0

            for i in range(0, 32, 3):  # Check triplets (instrument, command, note)
                b1 = self.get_byte(addr + i)
                b2 = self.get_byte(addr + i + 1)
                b3 = self.get_byte(addr + i + 2)

                # Check if this looks like SF2 event format
                # Instrument: 0x80-0x9F
                if 0x80 <= b1 <= 0x9F:
                    score += 2
                # Command: 0x80 (--) or 0xC0-0xCF
                if b2 == 0x80 or 0xC0 <= b2 <= 0xCF:
                    score += 2
                # Note: 0x00-0x60, 0x7E (rest), 0x7F (end)
                if b3 <= 0x60 or b3 in (0x7E, 0x7F):
                    score += 2

                events += 1

            if score >= 20:
                regions.append((addr, score))

        # Group adjacent regions
        if regions:
            regions.sort(key=lambda x: x[1], reverse=True)

            print("High-scoring sequence regions:")
            for addr, score in regions[:15]:
                print(f"  ${addr:04X}: score={score}")

                # Show first few bytes
                bytes_str = ' '.join(f'{self.get_byte(addr + i):02X}'
                                     for i in range(12))
                print(f"    {bytes_str}")

        return regions

    def analyze_data_tables(self):
        """Look for instrument, wave, and other tables"""
        print("\n=== ANALYZING DATA TABLES ===\n")

        # Look for structured data patterns that might be tables
        # Instrument tables typically have 6-8 bytes per entry

        table_candidates = []

        for addr in range(self.load_addr + 0x200, self.end_addr - 64):
            # Check for repeating structure
            structure_score = 0

            # Check 8 potential entries of 6 bytes each
            for entry in range(8):
                entry_addr = addr + entry * 6

                # Instruments often have ADSR values in first 2 bytes
                ad = self.get_byte(entry_addr)
                sr = self.get_byte(entry_addr + 1)

                # AD/SR values are typically in reasonable ranges
                if ad <= 0xFF and sr <= 0xFF:
                    # Wave byte often has specific patterns
                    wave = self.get_byte(entry_addr + 2)
                    if wave in (0x11, 0x21, 0x41, 0x81, 0x10, 0x20, 0x40, 0x80):
                        structure_score += 2

            if structure_score >= 8:
                table_candidates.append((addr, structure_score))

        if table_candidates:
            table_candidates.sort(key=lambda x: x[1], reverse=True)

            print("Potential instrument tables:")
            for addr, score in table_candidates[:5]:
                print(f"  ${addr:04X}: score={score}")

                # Show potential instrument entries
                for i in range(4):
                    entry = addr + i * 6
                    data = [self.get_byte(entry + j) for j in range(6)]
                    data_str = ' '.join(f'{b:02X}' for b in data)
                    print(f"    Entry {i}: {data_str}")

        return table_candidates

    def full_analysis(self, init_addr, play_addr):
        """Perform complete analysis"""
        print("=" * 70)
        print("LAXITY PLAYER FORMAT ANALYSIS")
        print("=" * 70)
        print(f"Load address: ${self.load_addr:04X}")
        print(f"End address:  ${self.end_addr:04X}")
        print(f"Data size:    {len(self.data)} bytes")

        # Analyze init routine
        init_refs = self.analyze_init_routine(init_addr)
        if init_refs:
            print(f"\nAddresses referenced from init routine:")
            for addr in init_refs:
                print(f"  ${addr:04X}")

        # Find pointer tables
        ptr_tables = self.find_pointer_tables()

        # Analyze sequence data
        seq_regions = self.analyze_sequence_data()

        # Analyze data tables
        data_tables = self.analyze_data_tables()

        # Summary
        print("\n" + "=" * 70)
        print("ANALYSIS SUMMARY")
        print("=" * 70)
        print(f"Potential pointer tables found: {len(ptr_tables)}")
        print(f"Sequence-like regions found: {len(seq_regions)}")
        print(f"Potential data tables found: {len(data_tables)}")

        print("\n=== SUGGESTED APPROACH ===\n")
        print("Based on this analysis, the converter should:")
        print("1. Extract sequence data from identified regions")
        print("2. Parse instrument tables from structured data areas")
        print("3. Reconstruct order lists from pointer tables")
        print("4. Map the data to SID Factory II format")

        return {
            'init_refs': init_refs,
            'ptr_tables': ptr_tables,
            'seq_regions': seq_regions,
            'data_tables': data_tables
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python laxity_analyzer.py <file.sid>")
        sys.exit(1)

    filepath = sys.argv[1]
    c64_data, load_addr, init_addr, play_addr = read_sid_file(filepath)

    analyzer = LaxityAnalyzer(c64_data, load_addr)
    results = analyzer.full_analysis(init_addr, play_addr)


if __name__ == '__main__':
    main()
