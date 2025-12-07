#!/usr/bin/env python3
"""
Extract SF2 from SF2-Packed SID

Reconstructs an SF2 file from an SF2-packed SID file by:
1. Detecting the SF2 driver type
2. Extracting tables from known driver memory locations
3. Building a proper SF2 file with header blocks

Uses ONLY the SF2-packed SID as input (original SF2 only for verification).
"""

import struct
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class SF2Extractor:
    """Extract SF2 data from SF2-packed SID files."""

    def __init__(self, sid_path: str):
        self.sid_path = Path(sid_path)
        self.data = None
        self.load_address = 0
        self.music_data = None

        # Driver 11 table locations (ABSOLUTE C64 memory addresses)
        # These are preserved in SF2-packed files at the same addresses
        # Note: Init, HR, Arpeggio, Tempo may be at different locations in packed files
        self.driver11_tables = {
            # These tables are at the SAME absolute addresses in packed files
            'Instruments': (0x1040, 0x1100, 192),  # 32 instruments × 6 bytes (93.8% match)
            'Commands': (0x1100, 0x11E0, 224),     # Command table (95.1% match)
            'Wave': (0x11E0, 0x13E0, 512),         # Wave table (90.6% match)
            'Pulse': (0x13E0, 0x16E0, 768),        # Pulse table (94.3% match)
            'Filter': (0x16E0, 0x19E0, 768),       # Filter table (37% match - partial)

            # These tables may be at different locations in packed files
            # Using original addresses as fallback
            'Init': (0x0F20, 0x0F40, 32),          # Init table
            'HR': (0x0F40, 0x1040, 256),           # Hard restart table
            'Arpeggio': (0x19E0, 0x1AE0, 256),     # Arpeggio table
            'Tempo': (0x1AE0, 0x1BE0, 256),        # Tempo table
        }

        self._load_file()

    def _load_file(self):
        """Load SF2-packed SID file."""
        with open(self.sid_path, 'rb') as f:
            raw_data = f.read()

        # Parse PSID header
        magic = raw_data[0:4]
        if magic == b'PSID' or magic == b'RSID':
            version = struct.unpack('>H', raw_data[4:6])[0]
            load_addr = struct.unpack('>H', raw_data[8:10])[0]
            self.init_addr = struct.unpack('>H', raw_data[10:12])[0]
            self.play_addr = struct.unpack('>H', raw_data[12:14])[0]

            header_size = 0x7C if version == 2 else 0x76

            if load_addr == 0:
                self.load_address = struct.unpack('<H', raw_data[header_size:header_size+2])[0]
                self.music_data = raw_data[header_size+2:]
            else:
                self.load_address = load_addr
                self.music_data = raw_data[header_size:]

            # Also store the PSID metadata
            self.name = raw_data[0x16:0x36].decode('ascii', errors='ignore').rstrip('\x00')
            self.author = raw_data[0x36:0x56].decode('ascii', errors='ignore').rstrip('\x00')
            self.copyright = raw_data[0x56:0x76].decode('ascii', errors='ignore').rstrip('\x00')

            print(f"Loaded SF2-packed SID: {self.sid_path}")
            print(f"  Load address: ${self.load_address:04X}")
            print(f"  Init address: ${self.init_addr:04X}")
            print(f"  Play address: ${self.play_addr:04X}")
            print(f"  Music data: {len(self.music_data):,} bytes")
            print(f"  Name: {self.name}")
            print(f"  Author: {self.author}")
        else:
            raise ValueError("Not a PSID/RSID file")

    def get_byte(self, address: int) -> int:
        """Get byte at memory address."""
        offset = address - self.load_address
        if 0 <= offset < len(self.music_data):
            return self.music_data[offset]
        return 0

    def get_bytes(self, address: int, count: int) -> bytes:
        """Get bytes starting at memory address."""
        offset = address - self.load_address
        if 0 <= offset < len(self.music_data):
            end = min(offset + count, len(self.music_data))
            return self.music_data[offset:end]
        return b''

    def extract_table(self, name: str) -> bytes:
        """Extract a table from the SF2-packed SID."""
        if name not in self.driver11_tables:
            return b''

        start, end, size = self.driver11_tables[name]

        # Extract raw bytes from the SID file
        table_data = self.get_bytes(start, size)

        print(f"  Extracting {name}: ${start:04X}-${end:04X} ({len(table_data)} bytes)")

        return table_data

    def extract_all_tables(self) -> Dict[str, bytes]:
        """Extract all tables from the SF2-packed SID."""
        print("\nExtracting tables from SF2-packed SID...")

        tables = {}
        for name in self.driver11_tables:
            table_data = self.extract_table(name)
            if table_data:
                tables[name] = table_data

        return tables

    def build_sf2_file(self, output_path: str, tables: Dict[str, bytes]):
        """Build a complete SF2 file from extracted tables."""
        print(f"\nBuilding SF2 file: {output_path}")

        # Load the Driver 11 template as a base
        template_path = Path("G5/examples/Driver 11 Test - Arpeggio.sf2")
        if not template_path.exists():
            print(f"ERROR: Template not found: {template_path}")
            return False

        with open(template_path, 'rb') as f:
            sf2_data = bytearray(f.read())

        print(f"  Template size: {len(sf2_data):,} bytes")

        # Parse template to find load address
        template_load = struct.unpack('<H', sf2_data[0:2])[0]
        print(f"  Template load address: ${template_load:04X}")

        # Now inject the extracted tables into the template
        # The template already has the correct structure, we just replace the data

        for name, table_data in tables.items():
            if name not in self.driver11_tables:
                continue

            start, end, size = self.driver11_tables[name]

            # Calculate offset in SF2 file (accounting for 2-byte load address)
            offset = start - template_load + 2

            if offset < 0 or offset + len(table_data) > len(sf2_data):
                print(f"  WARNING: {name} offset ${offset:04X} out of bounds")
                continue

            # Replace template data with extracted data
            sf2_data[offset:offset+len(table_data)] = table_data
            print(f"  Injected {name}: {len(table_data)} bytes at offset ${offset:04X}")

        # Write the output file
        with open(output_path, 'wb') as f:
            f.write(sf2_data)

        print(f"\nCreated SF2 file: {output_path}")
        print(f"  Size: {len(sf2_data):,} bytes")

        return True

    def verify_with_original(self, original_path: str, extracted_path: str):
        """Verify extracted SF2 against original."""
        print(f"\n{'='*80}")
        print("VERIFICATION (comparing with original SF2)")
        print(f"{'='*80}\n")

        # Read both files
        with open(original_path, 'rb') as f:
            orig_data = f.read()
        with open(extracted_path, 'rb') as f:
            extracted_data = f.read()

        # Parse headers
        orig_load = struct.unpack('<H', orig_data[0:2])[0]
        extr_load = struct.unpack('<H', extracted_data[0:2])[0]

        orig_music = orig_data[2:]
        extr_music = extracted_data[2:]

        print(f"Original:  {len(orig_data):,} bytes (load ${orig_load:04X})")
        print(f"Extracted: {len(extracted_data):,} bytes (load ${extr_load:04X})")

        # Compare table by table
        print(f"\n{'Table':<15} {'Size':<8} {'Match %':<10} {'Status'}")
        print("-"*60)

        total_matches = 0
        total_bytes = 0

        for name, (start, end, size) in self.driver11_tables.items():
            # Extract from both
            offset_start = start - orig_load
            offset_end = offset_start + size

            orig_table = orig_music[offset_start:offset_end]
            extr_table = extr_music[offset_start:offset_end]

            # Compare
            matches = sum(1 for i in range(min(len(orig_table), len(extr_table)))
                         if orig_table[i] == extr_table[i])
            total = min(len(orig_table), len(extr_table))
            match_pct = (matches / total * 100) if total > 0 else 0

            total_matches += matches
            total_bytes += total

            status = "PERFECT" if match_pct == 100 else \
                     "GOOD" if match_pct >= 80 else \
                     "FAIR" if match_pct >= 50 else \
                     "POOR"

            print(f"{name:<15} {size:<8} {match_pct:>6.1f}%   {status}")

        print("-"*60)
        overall = (total_matches / total_bytes * 100) if total_bytes > 0 else 0
        print(f"{'OVERALL':<15} {total_bytes:<8} {overall:>6.1f}%   "
              f"{'EXCELLENT' if overall >= 90 else 'GOOD' if overall >= 70 else 'FAIR'}")

        return overall


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python extract_sf2_from_packed_sid.py <packed_sid> <output_sf2> [original_sf2_for_verification]")
        sys.exit(1)

    packed_sid = sys.argv[1]
    output_sf2 = sys.argv[2]
    original_sf2 = sys.argv[3] if len(sys.argv) > 3 else None

    # Extract tables from SF2-packed SID
    extractor = SF2Extractor(packed_sid)
    tables = extractor.extract_all_tables()

    # Build SF2 file
    success = extractor.build_sf2_file(output_sf2, tables)

    # Verify if original provided
    if success and original_sf2:
        accuracy = extractor.verify_with_original(original_sf2, output_sf2)
        print(f"\n{'='*80}")
        print(f"RESULT: {accuracy:.1f}% accuracy")
        print(f"{'='*80}")


if __name__ == '__main__':
    main()
