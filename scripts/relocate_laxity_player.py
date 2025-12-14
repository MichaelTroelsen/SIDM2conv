#!/usr/bin/env python3
"""
Relocation engine for Laxity player code.
Relocates player from $1000 to $0E00 (offset: -$0200)
"""

import struct
from pathlib import Path

class LaxityRelocator:
    """Relocate Laxity player code."""
    
    # Original and new addresses
    ORIGINAL_START = 0x1000
    ORIGINAL_END = 0x19FF
    NEW_START = 0x0E00
    RELOCATION_OFFSET = NEW_START - ORIGINAL_START  # -0x0200
    
    # 6502 addressing modes that reference absolute addresses
    ABSOLUTE_OPCODES = {
        # LDA - Load Accumulator
        0xAD: 'LDA abs',    # LDA $xxxx
        0xBD: 'LDA abs,X',  # LDA $xxxx,X
        0xB9: 'LDA abs,Y',  # LDA $xxxx,Y
        0xA1: 'LDA ind,X',  # LDA ($xx,X)
        0xB1: 'LDA ind,Y',  # LDA ($xx),Y
        
        # STA - Store Accumulator
        0x8D: 'STA abs',    # STA $xxxx
        0x9D: 'STA abs,X',  # STA $xxxx,X
        0x99: 'STA abs,Y',  # STA $xxxx,Y
        0x81: 'STA ind,X',  # STA ($xx,X)
        0x91: 'STA ind,Y',  # STA ($xx),Y
        
        # LDX, LDY, STX, STY
        0xAE: 'LDX abs',
        0xBE: 'LDX abs,Y',
        0xAC: 'LDY abs',
        0xBC: 'LDY abs,X',
        0x8E: 'STX abs',
        0x8C: 'STY abs',
        
        # Increment/Decrement
        0xEE: 'INC abs',
        0xFE: 'INC abs,X',
        0xCE: 'DEC abs',
        0xDE: 'DEC abs,X',
        
        # Logical operations
        0x2D: 'AND abs',
        0x3D: 'AND abs,X',
        0x39: 'AND abs,Y',
        0x0D: 'ORA abs',
        0x1D: 'ORA abs,X',
        0x19: 'ORA abs,Y',
        0x4D: 'EOR abs',
        0x5D: 'EOR abs,X',
        0x59: 'EOR abs,Y',
        
        # Bit operations
        0x2C: 'BIT abs',
        
        # Comparisons
        0xCD: 'CMP abs',
        0xDD: 'CMP abs,X',
        0xD9: 'CMP abs,Y',
        0xEC: 'CPX abs',
        0xCC: 'CPY abs',
        
        # Shift/Rotate
        0x0E: 'ASL abs',
        0x1E: 'ASL abs,X',
        0x4E: 'LSR abs',
        0x5E: 'LSR abs,X',
        0x2E: 'ROL abs',
        0x3E: 'ROL abs,X',
        0x6E: 'ROR abs',
        0x7E: 'ROR abs,X',
        
        # Add/Subtract
        0x6D: 'ADC abs',
        0x7D: 'ADC abs,X',
        0x79: 'ADC abs,Y',
        0xED: 'SBC abs',
        0xFD: 'SBC abs,X',
        0xF9: 'SBC abs,Y',
        
        # JMP/JSR
        0x4C: 'JMP abs',
        0x20: 'JSR abs',
    }
    
    def relocate(self, input_file: str, output_file: str) -> dict:
        """Relocate player code."""
        # Read original code
        with open(input_file, 'rb') as f:
            original_code = bytearray(f.read())
        
        # Copy for relocation
        relocated_code = bytearray(original_code)
        
        stats = {
            'total_bytes': len(original_code),
            'patches_applied': 0,
            'warnings': []
        }
        
        # Scan for addresses that need patching
        i = 0
        while i < len(relocated_code) - 2:
            opcode = relocated_code[i]
            
            if opcode in self.ABSOLUTE_OPCODES:
                # Get 16-bit address (little-endian)
                lo = relocated_code[i + 1]
                hi = relocated_code[i + 2]
                addr = (hi << 8) | lo
                
                # Check if address is in Laxity range
                if self.ORIGINAL_START <= addr <= self.ORIGINAL_END:
                    # Apply relocation
                    new_addr = addr + self.RELOCATION_OFFSET
                    new_lo = new_addr & 0xFF
                    new_hi = (new_addr >> 8) & 0xFF
                    
                    relocated_code[i + 1] = new_lo
                    relocated_code[i + 2] = new_hi
                    
                    stats['patches_applied'] += 1
                    
                    if i % 20 == 0:  # Sample logging
                        print(f"  Patch: ${addr:04X} -> ${new_addr:04X} at offset ${i:04X}")
            
            i += 1
        
        # Write relocated code
        with open(output_file, 'wb') as f:
            f.write(relocated_code)
        
        return stats

def main():
    """Main entry point."""
    print("Building Laxity Code Relocation Engine")
    print("=" * 60)
    print()
    
    relocator = LaxityRelocator()
    
    input_file = Path('./drivers/laxity/laxity_player_reference.bin')
    output_file = Path('./drivers/laxity/laxity_player_relocated.bin')
    
    if not input_file.exists():
        print(f"Error: {input_file} not found")
        return
    
    print(f"Input:  {input_file}")
    print(f"Output: {output_file}")
    print()
    print(f"Relocation offset: {relocator.RELOCATION_OFFSET:+#06x} "
          f"(${relocator.ORIGINAL_START:04X} -> ${relocator.NEW_START:04X})")
    print()
    print("Relocating...")
    
    stats = relocator.relocate(str(input_file), str(output_file))
    
    print()
    print(f"Relocation Complete:")
    print(f"  Original size: {stats['total_bytes']:,} bytes")
    print(f"  Patches applied: {stats['patches_applied']}")
    print(f"  Output: {output_file}")
    print()
    print("Phase 3: Code Relocation Engine Complete")


if __name__ == '__main__':
    main()
