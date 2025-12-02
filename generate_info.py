#!/usr/bin/env python3
"""Generate comprehensive info.txt file for conversion pipeline output."""

import struct
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


def parse_psid_header(data):
    """Parse PSID header to extract metadata."""
    magic = data[0:4].decode('ascii', errors='ignore')
    version = struct.unpack('>H', data[4:6])[0]
    load_addr = struct.unpack('>H', data[8:10])[0]
    init_addr = struct.unpack('>H', data[10:12])[0]
    play_addr = struct.unpack('>H', data[12:14])[0]
    songs = struct.unpack('>H', data[14:16])[0]
    start_song = struct.unpack('>H', data[16:18])[0]

    name = data[0x16:0x36].decode('ascii', errors='ignore').rstrip('\x00')
    author = data[0x36:0x56].decode('ascii', errors='ignore').rstrip('\x00')
    copyright = data[0x56:0x76].decode('ascii', errors='ignore').rstrip('\x00')

    header_size = 0x7C if version == 2 else 0x76
    if load_addr == 0:
        load_addr = struct.unpack('<H', data[header_size:header_size+2])[0]

    data_size = len(data) - header_size
    end_addr = load_addr + data_size - (2 if load_addr == 0 else 0)

    return {
        'magic': magic,
        'version': version,
        'load_addr': load_addr,
        'init_addr': init_addr,
        'play_addr': play_addr,
        'songs': songs,
        'start_song': start_song,
        'header_size': header_size,
        'name': name,
        'author': author,
        'copyright': copyright,
        'data_size': data_size,
        'end_addr': end_addr
    }


def identify_player(sid_path):
    """Run player-id.exe to identify the player type."""
    try:
        # Get absolute paths
        player_id_path = Path(__file__).parent / 'tools' / 'player-id.exe'
        sid_path_abs = Path(sid_path).resolve()

        result = subprocess.run(
            [str(player_id_path), str(sid_path_abs)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent  # Set working directory to script location
        )

        # Parse output to find player type
        # Format: "filename.sid                        PlayerType"
        lines = result.stdout.split('\n')
        for line in lines:
            if '.sid' in line.lower() and not line.strip().startswith('Detected'):
                # Extract player type from the line
                parts = line.split()
                if len(parts) >= 2:
                    # Player type is the last part(s) of the line
                    player_type = ' '.join(parts[1:])
                    return player_type.strip()

        return "Unknown"
    except Exception as e:
        return f"Unknown (error: {e})"


def format_hex_table(data, name="Table", start_addr=None, end_addr=None):
    """Format binary data as hex table with 16 bytes per row."""
    lines = []
    lines.append(f"\n{name}")
    if start_addr is not None and end_addr is not None:
        size = len(data)
        lines.append(f"Start: ${start_addr:04X}  End: ${end_addr:04X}  Size: {size} bytes")
    lines.append("=" * 80)

    if not data or len(data) == 0:
        lines.append("(empty)")
        return "\n".join(lines)

    bytes_per_row = 16
    for row in range((len(data) + bytes_per_row - 1) // bytes_per_row):
        row_offset = row * bytes_per_row
        row_label = f"{row_offset:02x}:"
        hex_parts = []

        for col in range(bytes_per_row):
            byte_offset = row_offset + col
            if byte_offset < len(data):
                hex_parts.append(f"{data[byte_offset]:02x}")
            else:
                hex_parts.append("  ")

        hex_line = " ".join(hex_parts)
        lines.append(f"{row_label} {hex_line}")

    return "\n".join(lines)


def extract_table(sid_data, load_addr, start_addr, end_addr):
    """Extract a data table from SID file."""
    offset_start = start_addr - load_addr
    offset_end = end_addr - load_addr

    if offset_start < 0 or offset_end > len(sid_data):
        return b''

    return sid_data[offset_start:offset_end]


def generate_info_file(original_sid_path, converted_sf2_path, output_dir, title_override=None):
    """Generate comprehensive info.txt file.

    Args:
        original_sid_path: Path to original SID file
        converted_sf2_path: Path to converted SF2 file
        output_dir: Output directory for info.txt
        title_override: Optional title to use instead of SID header title (for consistent naming)
    """

    # Read SID files
    with open(original_sid_path, 'rb') as f:
        original_data = f.read()

    with open(converted_sf2_path, 'rb') as f:
        converted_data = f.read()

    # Parse headers
    orig_header = parse_psid_header(original_data)
    conv_header = parse_psid_header(converted_data)

    # Extract music data
    orig_music_data = original_data[orig_header['header_size']:]
    conv_music_data = converted_data[conv_header['header_size']:]

    # Get song name for filenames (sanitized)
    # Use override if provided, otherwise use header
    song_name = title_override if title_override else (orig_header['name'] if orig_header['name'] else "Unknown")
    song_name_clean = song_name.replace("'", "").replace(" ", "_").replace("/", "_")

    # Identify player type using player-id.exe
    player_type = identify_player(original_sid_path)

    output = []

    # Header
    output.append("=" * 80)
    output.append("SID to SF2 Conversion Report")
    output.append("=" * 80)
    output.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output.append(f"Converter: SIDM2 SID to SF2 Converter v0.6.2")
    output.append("")

    # Source file information
    output.append("=" * 80)
    output.append("Source File Information")
    output.append("=" * 80)
    output.append(f"File: {original_sid_path}")
    output.append(f"Format: PSID v{orig_header['version']}")
    output.append(f"Player Type: {player_type}")
    output.append("")
    output.append(f"Title: {orig_header['name']}")
    output.append(f"Author: {orig_header['author']}")
    output.append(f"Copyright: {orig_header['copyright']}")
    output.append("")
    output.append(f"Songs: {orig_header['songs']}")
    output.append(f"Start song: {orig_header['start_song']}")
    output.append(f"Load address: ${orig_header['load_addr']:04X}")
    output.append(f"Init address: ${orig_header['init_addr']:04X}")
    output.append(f"Play address: ${orig_header['play_addr']:04X}")
    output.append(f"Data size: {orig_header['data_size']:,} bytes")
    output.append(f"End address: ${orig_header['end_addr']:04X}")
    output.append("")

    # Conversion results
    output.append("=" * 80)
    output.append("Conversion Results")
    output.append("=" * 80)
    output.append(f"Output File: {song_name_clean}_d11.sf2")
    output.append(f"Driver: Driver 11 (Luxury driver with full features)")
    output.append(f"File Size: {len(converted_data):,} bytes")
    output.append("")

    # Original SID file preservation
    output.append("=" * 80)
    output.append("Original SID File (Preserved)")
    output.append("=" * 80)
    output.append(f"Source: {original_sid_path}")
    source_size = Path(original_sid_path).stat().st_size
    output.append(f"Size: {source_size:,} bytes")
    output.append(f"Copied to: {song_name_clean}.sid")
    output.append(f"Location: Same directory as this info.txt")
    output.append("")

    # Tool information section
    output.append("=" * 80)
    output.append("Pipeline Tools Used")
    output.append("=" * 80)
    output.append("")
    output.append("Conversion:")
    output.append(f"  - sid_to_sf2.py: SID → SF2 conversion")
    output.append(f"    Input:  {original_sid_path}")
    output.append(f"    Output: {song_name_clean}_d11.sf2")
    output.append("")
    output.append("Analysis:")
    output.append(f"  - player-id.exe: Player identification")
    output.append(f"    Detected: {player_type}")
    output.append(f"    Using:    tools/sidid.cfg")
    output.append("")
    output.append(f"  - siddump.exe: SID register dump (6502 emulation)")
    output.append(f"    Output: {song_name_clean}_original.dump")
    output.append(f"    Time:   15 seconds @ 50Hz")
    output.append("")
    output.append(f"  - SID2WAV.EXE: Audio rendering")
    output.append(f"    Output: {song_name_clean}_original.wav")
    output.append(f"    Format: 16-bit PCM, 44.1kHz")
    output.append(f"    Time:   15 seconds")
    output.append("")
    output.append("Documentation:")
    output.append(f"  - xxd: Hexadecimal dump")
    output.append(f"    Output: {song_name_clean}_original.hex")
    output.append(f"            {song_name_clean}_converted.hex")
    output.append("")
    output.append(f"  - extract_addresses.py: Memory address extraction")
    output.append(f"    Output: addresses.txt")
    output.append("")
    output.append(f"  - generate_info.py: This report")
    output.append(f"    Output: info.txt")
    output.append("")

    # Table addresses in SF2
    output.append("=" * 80)
    output.append("Table Addresses in SF2")
    output.append("=" * 80)
    output.append("  - Commands: $1844 (3×64)")
    output.append("  - Instruments: $1784 (6×32)")
    output.append("  - Wave: $1924 (2×256)")
    output.append("  - Pulse: $1B24 (3×256)")
    output.append("  - Filter: $1E24 (3×256)")
    output.append("  - Arpeggio: $2124 (1×256)")
    output.append("  - Tempo: $2224 (1×256)")
    output.append("  - HR: $1684 (32 bytes)")
    output.append("  - Init: $1664 (2 bytes)")
    output.append("")

    # Original SID data structure addresses (for Laxity format)
    if orig_header['load_addr'] >= 0x1000:
        output.append("=" * 80)
        output.append("Original SID Data Structure Addresses")
        output.append("=" * 80)
        output.append("")
        output.append("Player Code:")
        output.append(f"  Start: ${orig_header['load_addr']:04X}")
        output.append("  End:   $1900")
        output.append("  Size:  2304 bytes")
        output.append(f"  Note:  Init: ${orig_header['init_addr']:04X}, Play: ${orig_header['play_addr']:04X}")
        output.append("")

        # These are typical Laxity NewPlayer v21 addresses
        output.append("Instruments:")
        output.append("  Start: $1A6B")
        output.append("  End:   $1AAB")
        output.append("  Size:  64 bytes")
        output.append("  Count: 8 instruments")
        output.append("")

        output.append("Wave Table (split format):")
        output.append("  Notes:     $1914 - $1934 (32 bytes)")
        output.append("  Waveforms: $1934 - $1954 (32 bytes)")
        output.append("")

        output.append("Pulse Table:")
        output.append("  Start: $1A3B")
        output.append("  End:   $1A7B")
        output.append("  Size:  64 bytes")
        output.append("")

        output.append("Filter Table:")
        output.append("  Start: $1A1E")
        output.append("  End:   $1A4E")
        output.append("  Size:  48 bytes")
        output.append("")

        output.append("Command Table:")
        output.append("  Start: $1ADB")
        output.append("  End:   $1B9B")
        output.append("  Size:  192 bytes")
        output.append("")

    # Hex tables - Original SID
    output.append("=" * 80)
    output.append("ORIGINAL SID DATA TABLES (HEX VIEW)")
    output.append("=" * 80)

    if orig_header['load_addr'] >= 0x1000:
        # Laxity format tables
        tables = [
            ("Commands", 0x1ADB, 0x1B9B),
            ("Instruments", 0x1A6B, 0x1AAB),
            ("Wave", 0x1914, 0x1954),
            ("Pulse", 0x1A3B, 0x1A7B),
            ("Filter", 0x1A1E, 0x1A4E),
            ("Arp", 0x1A8B, 0x1ACB),
        ]
    else:
        # SF2 Driver 11 format tables
        tables = [
            ("Commands", 0x1859, 0x1919),
            ("Instruments", 0x17E9, 0x1829),
            ("Wave", 0x1692, 0x16D2),
            ("Pulse", 0x17B9, 0x17F9),
            ("Filter", 0x179C, 0x17CC),
            ("Arp", 0x1809, 0x1849),
        ]

    for table_name, start_addr, end_addr in tables:
        table_data = extract_table(orig_music_data, orig_header['load_addr'], start_addr, end_addr)
        output.append(format_hex_table(table_data, table_name, start_addr, end_addr))

    # Hex tables - Converted SF2
    output.append("")
    output.append("=" * 80)
    output.append("CONVERTED SF2 DATA TABLES (HEX VIEW)")
    output.append("=" * 80)

    sf2_tables = [
        ("Commands", 0x1844, 0x1904),
        ("Instruments", 0x1784, 0x1844),
        ("Wave", 0x1924, 0x1B24),
        ("Pulse", 0x1B24, 0x1E24),
        ("Filter", 0x1E24, 0x2124),
        ("Arpeggio", 0x2124, 0x2224),
        ("Tempo", 0x2224, 0x2324),
    ]

    for table_name, start_addr, end_addr in sf2_tables:
        table_data = extract_table(conv_music_data, conv_header['load_addr'], start_addr, end_addr)
        output.append(format_hex_table(table_data, table_name, start_addr, end_addr))

    # Write output
    output_path = Path(output_dir) / "info.txt"
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output))

    # Copy original SID file to output directory
    source_sid = Path(original_sid_path)
    dest_sid = Path(output_dir) / f"{song_name_clean}.sid"
    shutil.copy2(source_sid, dest_sid)

    print(f"Generated: {output_path}")
    print(f"Copied SID: {dest_sid}")
    print(f"Song name: {song_name}")
    print(f"Output files should use base name: {song_name_clean}")

    return song_name_clean


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python generate_info.py <original_sid> <converted_sf2> <output_dir> [title_override]")
        sys.exit(1)

    original_sid = sys.argv[1]
    converted_sf2 = sys.argv[2]
    output_dir = sys.argv[3]
    title_override = sys.argv[4] if len(sys.argv) > 4 else None

    generate_info_file(original_sid, converted_sf2, output_dir, title_override)
