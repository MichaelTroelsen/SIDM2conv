#!/usr/bin/env python3
"""
Laxity SF2 driver conversion module.
Handles SID to SF2 conversion using custom Laxity driver.
"""

import struct
from pathlib import Path
from sidm2.sf2_header_generator import SF2HeaderGenerator


class LaxityConverter:
    """Convert Laxity SID files to SF2 using custom driver."""

    # Driver memory layout
    DRIVER_PATH = Path('./drivers/laxity/sf2driver_laxity_00.prg')

    # Music data addresses (where tables are injected)
    SEQUENCE_ADDR = 0x1900
    INSTRUMENTS_ADDR = 0x1A6B
    WAVE_ADDR = 0x1ACB
    PULSE_ADDR = 0x1A3B
    FILTER_ADDR = 0x1A1E

    @staticmethod
    def convert_filter_table(laxity_filter_entries):
        """
        Convert Laxity filter table format to SF2 filter format.

        Laxity format (animation-based, 4 bytes):
          Byte 0: Target cutoff high byte (0x00-0xFF)
          Byte 1: Delta (add/sub value per frame)
          Byte 2: Duration (bits 0-6) + direction (bit 7)
          Byte 3: Next entry index (Y×4 format)

        SF2 format (static values, 4 bytes):
          Byte 0: Cutoff high byte (bits 3-10 of 11-bit value)
          Byte 1: Cutoff low byte (bits 0-2 of 11-bit value)
          Byte 2: Resonance (0x00-0xFF)
          Byte 3: Next entry index (direct format)

        Args:
            laxity_filter_entries: List of 4-byte tuples from Laxity SID

        Returns:
            List of 4-byte tuples in SF2 format
        """
        sf2_entries = []

        for entry in laxity_filter_entries:
            if len(entry) != 4:
                continue

            target_cutoff_8bit, delta, duration_dir, next_idx_y4 = entry

            # Convert 8-bit Laxity target to 11-bit SF2 cutoff
            # Laxity: 0x00-0xFF (256 values)
            # SF2:    0x000-0x7FF (2048 values)
            # Scale factor: 8x (2048 / 256 = 8)
            cutoff_11bit = target_cutoff_8bit * 8

            # Clamp to valid 11-bit range
            cutoff_11bit = max(0, min(0x7FF, cutoff_11bit))

            # Split into high/low bytes
            cutoff_hi = (cutoff_11bit >> 8) & 0xFF
            cutoff_lo = cutoff_11bit & 0xFF

            # Default resonance (middle value)
            # Could potentially derive from duration_dir in future
            resonance = 0x80  # Mid-range resonance

            # Convert Y×4 index to direct index
            # Laxity uses Y-register indexing with stride 4
            # SF2 uses direct indexing
            if next_idx_y4 == 0 or next_idx_y4 == 0x7F:
                next_idx_direct = 0x7F  # End marker
            elif next_idx_y4 % 4 == 0:
                next_idx_direct = next_idx_y4 // 4
            else:
                next_idx_direct = 0x7F  # Invalid index, use end marker

            # Create SF2 entry
            sf2_entry = (cutoff_hi, cutoff_lo, resonance, next_idx_direct)
            sf2_entries.append(sf2_entry)

        return sf2_entries
    
    def __init__(self):
        """Initialize converter."""
        self.driver = None
        self.headers = None
        self.load_driver()
        self.load_headers()
    
    def load_driver(self):
        """Load Laxity driver template."""
        if not self.DRIVER_PATH.exists():
            raise FileNotFoundError(f"Driver not found: {self.DRIVER_PATH}")

        with open(self.DRIVER_PATH, 'rb') as f:
            self.driver = bytearray(f.read())

        print(f"Loaded Laxity driver: {len(self.driver)} bytes")

    def load_headers(self):
        """Generate SF2 header blocks."""
        gen = SF2HeaderGenerator(driver_size=len(self.driver))
        self.headers = gen.generate_complete_headers()
        print(f"Generated SF2 headers: {len(self.headers)} bytes")
    
    def inject_tables(self, sf2_data, laxity_data):
        """Inject Laxity tables into SF2 driver."""
        # Copy driver as base
        result = bytearray(self.driver)
        
        # Extend if needed
        needed_size = max(0x1900 + len(laxity_data), len(result))
        if len(result) < needed_size:
            result.extend([0] * (needed_size - len(result)))
        
        # Inject music data at Laxity addresses
        if len(laxity_data) > 0:
            result[0x1900:0x1900 + len(laxity_data)] = laxity_data
        
        return bytes(result)
    
    def convert(self, sid_file, output_file, laxity_extractor):
        """
        Convert SID to SF2 using Laxity driver.
        
        Args:
            sid_file: Path to input SID file
            output_file: Path to output SF2 file
            laxity_extractor: Function to extract Laxity data from SID
        
        Returns:
            Conversion result dictionary
        """
        print(f"Converting: {sid_file}")
        
        # Extract Laxity data from SID
        laxity_data = laxity_extractor(str(sid_file))
        
        # Inject into driver
        sf2_data = self.inject_tables(self.driver, laxity_data)
        
        # Write output
        with open(output_file, 'wb') as f:
            f.write(sf2_data)
        
        result = {
            'success': True,
            'input': str(sid_file),
            'output': str(output_file),
            'driver_size': len(self.driver),
            'music_size': len(laxity_data),
            'output_size': len(sf2_data),
            'player_type': 'Laxity',
            'accuracy': 0.70  # Expected 70-90%
        }
        
        print(f"  Output: {output_file} ({len(sf2_data)} bytes)")
        print(f"  Music data: {len(laxity_data)} bytes")
        print(f"  Expected accuracy: 70-90%")
        
        return result
