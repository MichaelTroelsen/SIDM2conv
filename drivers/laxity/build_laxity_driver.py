#!/usr/bin/env python3
"""
Build Laxity SF2 driver by combining wrapper, player code, and headers.

Memory Layout:
$0D7E-$0DFF   Wrapper (130 bytes)
$0E00-$16FF   Relocated Player (2.3 KB)
$1700-$18FF   Header Blocks (512 bytes)
"""

import struct
from pathlib import Path

class LaxityDriverBuilder:
    """Build complete Laxity SF2 driver."""
    
    WRAPPER_START = 0x0D7E
    WRAPPER_SIZE = 0x0182   # $0D7E-$0E00 = 130 bytes
    
    PLAYER_START = 0x0E00
    PLAYER_SIZE = 0x08FF    # $0E00-$16FF = 2.3 KB
    
    HEADER_START = 0x1700
    HEADER_SIZE = 0x0200    # $1700-$18FF = 512 bytes
    
    MUSIC_START = 0x1900
    
    def build(self, wrapper_file, player_file, output_file):
        """Build complete driver."""
        print("Building Laxity SF2 Driver")
        print("=" * 60)
        
        # Create driver binary (full 64KB for now, will be trimmed)
        driver = bytearray(0x10000)
        
        # Write wrapper code at $0D7E
        print(f"\n1. Loading wrapper from {wrapper_file}...")
        with open(wrapper_file, 'rb') as f:
            wrapper_code = f.read()
        
        if len(wrapper_code) > self.WRAPPER_SIZE:
            print(f"Warning: Wrapper is {len(wrapper_code)} bytes, max {self.WRAPPER_SIZE}")
            wrapper_code = wrapper_code[:self.WRAPPER_SIZE]
        
        print(f"   Wrapper size: {len(wrapper_code)} bytes at ${self.WRAPPER_START:04X}")
        driver[self.WRAPPER_START:self.WRAPPER_START + len(wrapper_code)] = wrapper_code
        
        # Write relocated player code at $0E00
        print(f"\n2. Loading player from {player_file}...")
        with open(player_file, 'rb') as f:
            player_code = f.read()
        
        if len(player_code) > self.PLAYER_SIZE:
            print(f"Warning: Player is {len(player_code)} bytes, max {self.PLAYER_SIZE}")
            player_code = player_code[:self.PLAYER_SIZE]
        
        print(f"   Player size: {len(player_code)} bytes at ${self.PLAYER_START:04X}")
        driver[self.PLAYER_START:self.PLAYER_START + len(player_code)] = player_code
        
        # Create minimal header blocks at $1700-$18FF
        print(f"\n3. Creating SF2 header blocks...")
        headers = self.create_headers()
        print(f"   Header size: {len(headers)} bytes at ${self.HEADER_START:04X}")
        driver[self.HEADER_START:self.HEADER_START + len(headers)] = headers
        
        # Calculate total used size
        total_used = self.HEADER_START + len(headers)
        print(f"\n4. Driver image created:")
        print(f"   Wrapper:  ${self.WRAPPER_START:04X}-${self.WRAPPER_START + len(wrapper_code):04X}")
        print(f"   Player:   ${self.PLAYER_START:04X}-${self.PLAYER_START + len(player_code):04X}")
        print(f"   Headers:  ${self.HEADER_START:04X}-${self.HEADER_START + len(headers):04X}")
        print(f"   Total:    {total_used:,} bytes (${total_used:04X})")
        
        # Write driver file (trim to used size)
        driver = driver[:total_used]
        with open(output_file, 'wb') as f:
            f.write(driver)
        
        print(f"\n5. Driver saved to: {output_file}")
        print(f"   Size: {len(driver):,} bytes (${len(driver):04X})")
        
        return len(driver)
    
    def create_headers(self):
        """Create SF2 header blocks."""
        headers = bytearray(512)
        
        # File ID at $1700
        headers[0x00:0x02] = struct.pack('>H', 0x1337)  # SF2 magic
        headers[0x02] = 0x01  # Version
        headers[0x03] = 0x09  # Laxity driver type
        
        # Entry points at $1704-$1709
        headers[0x04:0x06] = struct.pack('>H', 0x0D7E)  # Init
        headers[0x06:0x08] = struct.pack('>H', 0x0D81)  # Play
        headers[0x08:0x0A] = struct.pack('>H', 0x0D84)  # Stop
        
        # Common block at $1740
        headers[0x40:0x42] = struct.pack('>H', 0x1900)  # Sequence table
        headers[0x42:0x44] = struct.pack('>H', 0x1A6B)  # Instrument table
        headers[0x44:0x46] = struct.pack('>H', 0x1ACB)  # Wave table
        headers[0x46:0x48] = struct.pack('>H', 0x1A3B)  # Pulse table
        headers[0x48:0x4A] = struct.pack('>H', 0x1A1E)  # Filter table
        
        headers[0x4A] = 0x03  # 3 voices
        headers[0x4B] = 0x03  # 3 sequences
        headers[0x4C] = 0xFF  # All features supported
        
        return headers


def main():
    """Main entry point."""
    builder = LaxityDriverBuilder()
    
    wrapper_file = Path('./laxity_driver.asm')
    player_file = Path('./laxity_player_relocated.bin')
    output_file = Path('./sf2driver_laxity_00.prg')
    
    # For now, create a minimal test driver
    # In production, wrapper_file would be assembled
    
    if not player_file.exists():
        print(f"Error: {player_file} not found")
        return
    
    print(f"Laxity SF2 Driver Builder")
    print()
    
    # Create minimal wrapper (for testing)
    print("Note: Using placeholder wrapper code")
    print("Next step: Assemble laxity_driver.asm with 64tass")
    print()
    
    # Create test driver with just player code
    test_driver = bytearray(0x2000)  # 8KB
    
    with open(player_file, 'rb') as f:
        player = f.read()
    
    # Place player at $0E00
    test_driver[0x0E00:0x0E00 + len(player)] = player
    
    # Add minimal header at $1700
    test_driver[0x1700:0x1702] = struct.pack('>H', 0x1337)
    test_driver[0x1704:0x1706] = struct.pack('>H', 0x0D7E)
    test_driver[0x1706:0x1708] = struct.pack('>H', 0x0D81)
    test_driver[0x1708:0x170A] = struct.pack('>H', 0x0D84)
    
    with open(output_file, 'wb') as f:
        f.write(test_driver)
    
    print(f"Test driver created: {output_file}")
    print(f"Size: {len(test_driver)} bytes")
    print()
    print("NEXT: Assemble wrapper with 64tass, then rebuild with assembled code")


if __name__ == '__main__':
    main()
