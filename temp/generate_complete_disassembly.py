#!/usr/bin/env python3
"""
Generate Complete SID Disassembly Documentation

Creates a comprehensive disassembly document similar to STINSENS_PLAYER_DISASSEMBLY.md
with memory maps, hex dumps, and annotated assembly code.

Author: SIDM2 Project
Date: 2025-12-03
"""

import subprocess
from pathlib import Path
import struct

def read_sid_header(sid_path):
    """Read SID file header information"""
    with open(sid_path, 'rb') as f:
        data = f.read()

    magic = data[0:4].decode('ascii', errors='ignore')
    version = struct.unpack('>H', data[4:6])[0]
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_addr = struct.unpack('>H', data[8:10])[0]
    init_addr = struct.unpack('>H', data[10:12])[0]
    play_addr = struct.unpack('>H', data[12:14])[0]
    songs = struct.unpack('>H', data[14:16])[0]
    start_song = struct.unpack('>H', data[16:18])[0]

    name = data[0x16:0x36].decode('ascii', errors='ignore').rstrip('\x00')
    author = data[0x36:0x56].decode('ascii', errors='ignore').rstrip('\x00')
    copyright_str = data[0x56:0x76].decode('ascii', errors='ignore').rstrip('\x00')

    # Handle load address
    sid_data = data[data_offset:]
    actual_load = load_addr
    if load_addr == 0:
        actual_load = struct.unpack('<H', sid_data[0:2])[0]
        sid_data = sid_data[2:]

    data_size = len(sid_data)
    end_addr = actual_load + data_size - 1

    return {
        'magic': magic,
        'version': version,
        'load_addr': actual_load,
        'init_addr': init_addr,
        'play_addr': play_addr,
        'songs': songs,
        'start_song': start_song,
        'name': name,
        'author': author,
        'copyright': copyright_str,
        'data_size': data_size,
        'end_addr': end_addr,
        'sid_data': sid_data
    }


def generate_hex_dump(data, start_addr, max_lines=64):
    """Generate hex dump of binary data"""
    lines = []
    offset = 0

    while offset < len(data) and len(lines) < max_lines:
        addr = start_addr + offset
        hex_bytes = []
        ascii_chars = []

        for i in range(16):
            if offset + i < len(data):
                byte = data[offset + i]
                hex_bytes.append(f"{byte:02X}")
                if 32 <= byte <= 126:
                    ascii_chars.append(chr(byte))
                else:
                    ascii_chars.append('.')
            else:
                hex_bytes.append("  ")
                ascii_chars.append(' ')

        hex_str = ' '.join(hex_bytes[:8]) + '  ' + ' '.join(hex_bytes[8:])
        ascii_str = ''.join(ascii_chars)
        lines.append(f"${addr:04X}: {hex_str}  {ascii_str}")
        offset += 16

    if offset < len(data):
        remaining = len(data) - offset
        lines.append(f"\n; ... {remaining} more bytes (${start_addr + offset:04X}-${start_addr + len(data) - 1:04X}) ...")

    return lines


def generate_complete_documentation(sid_path, output_path):
    """Generate complete disassembly documentation"""

    # Read SID header
    header = read_sid_header(sid_path)

    # Get basic disassembly
    result = subprocess.run(
        ['python', 'disassemble_sid.py', str(sid_path)],
        capture_output=True,
        text=True
    )
    disassembly = result.stdout

    # Write comprehensive markdown document
    with open(output_path, 'w', encoding='utf-8') as f:
        # Title
        f.write(f"# Complete Disassembly: {header['name']}\n\n")
        f.write(f"**Author:** {header['author']}\n\n")
        if header['copyright']:
            f.write(f"**Copyright:** {header['copyright']}\n\n")
        f.write(f"**Disassembled:** 2025-12-03\n\n")
        f.write("---\n\n")

        # Table of Contents
        f.write("## Table of Contents\n\n")
        f.write("1. [File Information](#file-information)\n")
        f.write("2. [Memory Map](#memory-map)\n")
        f.write("3. [Complete Disassembly](#complete-disassembly)\n")
        f.write("4. [Data Tables](#data-tables)\n")
        f.write("5. [Music Data](#music-data)\n\n")
        f.write("---\n\n")

        # File Information
        f.write("## File Information\n\n")
        f.write(f"- **Format:** {header['magic']} v{header['version']}\n")
        f.write(f"- **Load Address:** ${header['load_addr']:04X}\n")
        f.write(f"- **Init Address:** ${header['init_addr']:04X}\n")
        f.write(f"- **Play Address:** ${header['play_addr']:04X}\n")
        f.write(f"- **Songs:** {header['songs']}\n")
        f.write(f"- **Start Song:** {header['start_song']}\n")
        f.write(f"- **Data Size:** {header['data_size']:,} bytes\n")
        f.write(f"- **End Address:** ${header['end_addr']:04X}\n")
        f.write(f"- **Memory Range:** ${header['load_addr']:04X}-${header['end_addr']:04X}\n\n")

        # Memory Map
        f.write("## Memory Map\n\n")
        f.write("| Address Range | Size | Description |\n")
        f.write("|--------------|------|-------------|\n")

        load = header['load_addr']

        # Known sections based on SF2 player structure
        sections = [
            (load, load + 0x048, 49, "Jump table and player header"),
            (load + 0x049, load + 0x900, 2232, "Player code (init + play routines)"),
            (load + 0x914, load + 0x954, 64, "Wave table (note offsets + waveforms)"),
            (load + 0xA1E, load + 0xA4E, 48, "Filter table (16 entries × 3 bytes)"),
            (load + 0xA3B, load + 0xA7B, 64, "Pulse table (16 entries × 4 bytes)"),
            (load + 0xA6B, load + 0xAAB, 64, "Instrument table (8 instruments × 8 bytes)"),
            (load + 0xA8B, load + 0xACB, 64, "Arpeggio table (16 entries × 4 bytes)"),
            (load + 0xADB, load + 0xB9B, 192, "Command table (64 commands × 3 bytes)"),
        ]

        # Add sections that exist
        for start, end, size, desc in sections:
            if end <= header['end_addr']:
                f.write(f"| ${start:04X}-${end:04X} | {size:4} | {desc} |\n")

        # Music data section
        if header['end_addr'] > load + 0xB9B:
            music_start = load + 0xC00
            music_size = header['end_addr'] - music_start + 1
            f.write(f"| ${music_start:04X}-${header['end_addr']:04X} | {music_size:4} | Music data (patterns, sequences, orders) |\n")

        f.write("\n")

        # Complete Disassembly
        f.write("## Complete Disassembly\n\n")
        f.write("Full 6502/6510 assembly disassembly of the player code and music data.\n\n")
        f.write("```asm\n")
        f.write(disassembly)
        f.write("```\n\n")

        # Data Tables
        f.write("## Data Tables\n\n")
        f.write("Hex dumps of the music data tables embedded in the SID file.\n\n")

        # Table sections
        table_defs = [
            (0x914, 0x954, "Wave Table", "Note offsets and waveform selections"),
            (0xA1E, 0xA4E, "Filter Table", "Filter cutoff and resonance programs"),
            (0xA3B, 0xA7B, "Pulse Table", "Pulse width modulation programs"),
            (0xA6B, 0xAAB, "Instrument Table", "Instrument definitions (ADSR, table pointers, flags)"),
            (0xA8B, 0xACB, "Arpeggio Table", "Arpeggio note offset patterns"),
            (0xADB, 0xB9B, "Command Table", "Effect commands (slide, vibrato, etc.)"),
        ]

        for offset, end_offset, name, description in table_defs:
            start_addr = load + offset
            end_addr = load + end_offset

            if end_addr <= header['end_addr']:
                size = end_addr - start_addr + 1
                f.write(f"### {name}\n\n")
                f.write(f"**Location:** ${start_addr:04X}-${end_addr:04X} ({size} bytes)\n\n")
                f.write(f"{description}\n\n")
                f.write("```\n")

                # Extract table data
                table_start = offset
                table_end = end_offset + 1
                table_data = header['sid_data'][table_start:table_end]

                hex_lines = generate_hex_dump(table_data, start_addr, max_lines=32)
                for line in hex_lines:
                    f.write(line + "\n")

                f.write("```\n\n")

        # Music Data
        music_start = load + 0xC00
        if music_start < header['end_addr']:
            f.write("## Music Data\n\n")
            f.write(f"**Location:** ${music_start:04X}-${header['end_addr']:04X}\n\n")
            f.write("Pattern and sequence data for the music composition.\n\n")
            f.write("```\n")

            # Show first 512 bytes of music data
            music_offset = 0xC00
            music_data = header['sid_data'][music_offset:]

            hex_lines = generate_hex_dump(music_data, music_start, max_lines=32)
            for line in hex_lines:
                f.write(line + "\n")

            f.write("```\n\n")

        # Footer
        f.write("---\n\n")
        f.write("*Generated by SIDM2 Complete Disassembly Tool*\n")
        f.write(f"*Source: {sid_path.name}*\n")


def main():
    """Main entry point"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python generate_complete_disassembly.py <sid_file> [output.md]")
        sys.exit(1)

    sid_path = Path(sys.argv[1])
    if not sid_path.exists():
        print(f"Error: File not found: {sid_path}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = Path(f"docs/{sid_path.stem}_COMPLETE_DISASSEMBLY.md")

    print(f"Generating complete disassembly for {sid_path.name}...")
    generate_complete_documentation(sid_path, output_path)
    print(f"✓ Complete documentation written to {output_path}")
    print(f"  File size: {output_path.stat().st_size:,} bytes")


if __name__ == '__main__':
    main()
