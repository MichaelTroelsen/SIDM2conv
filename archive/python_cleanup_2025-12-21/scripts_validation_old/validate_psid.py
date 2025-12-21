#!/usr/bin/env python3
"""
PSID/RSID Format Validator

Validates SID files against the PSID v2 specification.
Based on docs/format-specification.md and tools/prg2sid reference.

Usage:
    python validate_psid.py <sid_file>
    python validate_psid.py <original.sid> <exported.sid>  # Compare mode
"""

import sys
import struct
from pathlib import Path
from typing import Dict, List, Tuple, Optional


class PSIDValidator:
    """Validates PSID/RSID file format compliance."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.errors = []
        self.warnings = []
        self.header = {}

        with open(filepath, 'rb') as f:
            self.data = f.read()

    def validate(self) -> bool:
        """Run all validation checks. Returns True if valid."""
        self.errors = []
        self.warnings = []

        # Minimum file size check
        if len(self.data) < 124:
            self.errors.append(f"File too small: {len(self.data)} bytes (minimum 124)")
            return False

        # Parse and validate header
        self._parse_header()
        self._validate_magic()
        self._validate_version()
        self._validate_addresses()
        self._validate_song_count()
        self._validate_metadata()
        self._validate_flags()
        self._validate_data_section()

        return len(self.errors) == 0

    def _parse_header(self):
        """Parse PSID header fields."""
        d = self.data

        # All multi-byte values are big-endian except load address in data
        self.header = {
            'magic': d[0:4].decode('ascii', errors='ignore'),
            'version': struct.unpack('>H', d[4:6])[0],
            'data_offset': struct.unpack('>H', d[6:8])[0],
            'load_addr': struct.unpack('>H', d[8:10])[0],
            'init_addr': struct.unpack('>H', d[10:12])[0],
            'play_addr': struct.unpack('>H', d[12:14])[0],
            'num_songs': struct.unpack('>H', d[14:16])[0],
            'start_song': struct.unpack('>H', d[16:18])[0],
            'speed': struct.unpack('>I', d[18:22])[0],
            'name': d[22:54].rstrip(b'\x00').decode('ascii', errors='replace'),
            'author': d[54:86].rstrip(b'\x00').decode('ascii', errors='replace'),
            'copyright': d[86:118].rstrip(b'\x00').decode('ascii', errors='replace'),
        }

        # v2+ fields
        if len(d) >= 124:
            self.header['flags'] = struct.unpack('>H', d[118:120])[0]
            self.header['start_page'] = d[120]
            self.header['page_length'] = d[121]
            self.header['reserved'] = struct.unpack('>H', d[122:124])[0]

    def _validate_magic(self):
        """Validate magic ID."""
        magic = self.header['magic']
        if magic not in ['PSID', 'RSID']:
            self.errors.append(f"Invalid magic ID: '{magic}' (expected 'PSID' or 'RSID')")

    def _validate_version(self):
        """Validate version number."""
        version = self.header['version']
        if version < 1 or version > 4:
            self.errors.append(f"Invalid version: {version} (expected 1-4)")
        elif version == 1:
            self.warnings.append("Version 1 format (no flags field)")

    def _validate_addresses(self):
        """Validate memory addresses."""
        load_addr = self.header['load_addr']
        init_addr = self.header['init_addr']
        play_addr = self.header['play_addr']

        # Load address can be 0 (read from data)
        if load_addr == 0:
            # Check if data section has valid load address
            data_offset = self.header['data_offset']
            if len(self.data) >= data_offset + 2:
                actual_load = struct.unpack('<H', self.data[data_offset:data_offset+2])[0]
                if actual_load < 0x0400 or actual_load >= 0xD000:
                    self.warnings.append(f"Unusual load address from data: ${actual_load:04X}")
        elif load_addr < 0x0400 or load_addr >= 0xD000:
            self.warnings.append(f"Unusual load address in header: ${load_addr:04X}")

        # Init and play addresses
        if init_addr == 0:
            self.warnings.append("Init address is 0 (uses load address)")
        elif init_addr < 0x0400 or init_addr >= 0xD000:
            self.errors.append(f"Invalid init address: ${init_addr:04X}")

        if play_addr == 0:
            self.warnings.append("Play address is 0 (interrupt routine)")
        elif play_addr < 0x0400 or play_addr >= 0xD000:
            self.errors.append(f"Invalid play address: ${play_addr:04X}")

    def _validate_song_count(self):
        """Validate song count and start song."""
        num_songs = self.header['num_songs']
        start_song = self.header['start_song']

        if num_songs == 0:
            self.errors.append("Number of songs is 0")
        elif num_songs > 256:
            self.warnings.append(f"Unusually high song count: {num_songs}")

        if start_song == 0:
            self.errors.append("Start song is 0 (should be 1-based)")
        elif start_song > num_songs:
            self.errors.append(f"Start song ({start_song}) > number of songs ({num_songs})")

    def _validate_metadata(self):
        """Validate song metadata strings."""
        name = self.header['name']
        author = self.header['author']
        copyright = self.header['copyright']

        # Empty metadata is technically valid but suspicious for exported files
        if not name and not author and not copyright:
            self.warnings.append("All metadata fields are empty (no title, author, copyright)")

        # Check for non-printable characters
        for field, value in [('name', name), ('author', author), ('copyright', copyright)]:
            if any(ord(c) < 32 for c in value if c):
                self.warnings.append(f"Non-printable characters in {field}")

    def _validate_flags(self):
        """Validate flags field (v2+)."""
        if 'flags' not in self.header:
            return

        flags = self.header['flags']

        # Extract flag components
        is_mus = (flags & 0x0001) != 0
        is_psid_specific = (flags & 0x0002) != 0
        clock = (flags >> 2) & 0x03
        sid_model = (flags >> 4) & 0x03

        if is_mus:
            self.warnings.append("MUS data flag set (Compute!'s Sidplayer format)")

        if clock == 0:
            self.warnings.append("Clock speed unknown (should be PAL=1, NTSC=2, or Both=3)")

        if sid_model == 0:
            self.warnings.append("SID model unknown (should be 6581=1, 8580=2, or Both=3)")

    def _validate_data_section(self):
        """Validate data section exists and has content."""
        data_offset = self.header['data_offset']

        if data_offset < 118:
            self.errors.append(f"Data offset too small: {data_offset} (minimum 118 for v1, 124 for v2)")
        elif data_offset != 124 and data_offset != 118:
            self.warnings.append(f"Unusual data offset: {data_offset} (expected 118 or 124)")

        if len(self.data) <= data_offset:
            self.errors.append(f"No data section (file ends at header)")
        else:
            data_size = len(self.data) - data_offset
            if data_size < 2:
                self.errors.append(f"Data section too small: {data_size} bytes")
            elif data_size < 100:
                self.warnings.append(f"Very small data section: {data_size} bytes")

    def get_summary(self) -> str:
        """Get validation summary."""
        lines = []
        lines.append("=" * 60)
        lines.append(f"PSID Validator: {self.filepath.name}")
        lines.append("=" * 60)
        lines.append("")

        # Header info
        h = self.header
        lines.append("Header Information:")
        lines.append(f"  Magic ID:      {h['magic']}")
        lines.append(f"  Version:       {h['version']}")
        lines.append(f"  Data offset:   ${h['data_offset']:04X} ({h['data_offset']})")
        lines.append(f"  Load address:  ${h['load_addr']:04X}")
        lines.append(f"  Init address:  ${h['init_addr']:04X}")
        lines.append(f"  Play address:  ${h['play_addr']:04X}")
        lines.append(f"  Songs:         {h['num_songs']} (start: {h['start_song']})")
        lines.append(f"  Speed flags:   ${h['speed']:08X}")
        lines.append(f"  Name:          '{h['name']}'")
        lines.append(f"  Author:        '{h['author']}'")
        lines.append(f"  Copyright:     '{h['copyright']}'")

        if 'flags' in h:
            flags = h['flags']
            clock = (flags >> 2) & 0x03
            sid_model = (flags >> 4) & 0x03
            clock_str = ['Unknown', 'PAL', 'NTSC', 'Both'][clock]
            model_str = ['Unknown', '6581', '8580', 'Both'][sid_model]
            lines.append(f"  Flags:         ${flags:04X} (Clock: {clock_str}, SID: {model_str})")

        lines.append(f"  File size:     {len(self.data):,} bytes")
        lines.append(f"  Data size:     {len(self.data) - h['data_offset']:,} bytes")
        lines.append("")

        # Validation results
        if self.errors:
            lines.append(f"ERRORS ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"  X {err}")
            lines.append("")

        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for warn in self.warnings:
                lines.append(f"  ! {warn}")
            lines.append("")

        if not self.errors and not self.warnings:
            lines.append("* All validation checks passed")
            lines.append("")

        # Final status
        lines.append("=" * 60)
        if self.errors:
            lines.append("RESULT: INVALID - File does not conform to PSID specification")
        elif self.warnings:
            lines.append("RESULT: VALID (with warnings)")
        else:
            lines.append("RESULT: VALID - File conforms to PSID specification")
        lines.append("=" * 60)

        return "\n".join(lines)


def compare_psid_files(original: Path, exported: Path) -> str:
    """Compare two PSID files and report differences."""
    val_orig = PSIDValidator(original)
    val_exp = PSIDValidator(exported)

    val_orig.validate()
    val_exp.validate()

    lines = []
    lines.append("=" * 60)
    lines.append("PSID Comparison Report")
    lines.append("=" * 60)
    lines.append(f"Original:  {original}")
    lines.append(f"Exported:  {exported}")
    lines.append("")

    # Compare headers
    h_orig = val_orig.header
    h_exp = val_exp.header

    differences = []

    for key in h_orig.keys():
        if key not in h_exp:
            continue
        if h_orig[key] != h_exp[key]:
            differences.append((key, h_orig[key], h_exp[key]))

    if differences:
        lines.append(f"Header Differences ({len(differences)}):")
        lines.append("-" * 60)
        for key, orig_val, exp_val in differences:
            if isinstance(orig_val, int):
                lines.append(f"  {key:14s}: ${orig_val:04X} -> ${exp_val:04X}")
            else:
                lines.append(f"  {key:14s}: '{orig_val}' -> '{exp_val}'")
        lines.append("")
    else:
        lines.append("* All header fields match")
        lines.append("")

    # Validation comparison
    lines.append("Original Validation:")
    if val_orig.errors:
        for err in val_orig.errors:
            lines.append(f"  X {err}")
    else:
        lines.append("  * Valid")
    lines.append("")

    lines.append("Exported Validation:")
    if val_exp.errors:
        for err in val_exp.errors:
            lines.append(f"  X {err}")
    else:
        lines.append("  * Valid")
    lines.append("")

    # Data size comparison
    orig_data_size = len(val_orig.data) - h_orig['data_offset']
    exp_data_size = len(val_exp.data) - h_exp['data_offset']

    lines.append("Data Section:")
    lines.append(f"  Original size: {orig_data_size:,} bytes")
    lines.append(f"  Exported size: {exp_data_size:,} bytes")
    lines.append(f"  Difference:    {exp_data_size - orig_data_size:+,} bytes")
    lines.append("")

    lines.append("=" * 60)

    return "\n".join(lines)


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_psid.py <sid_file>")
        print("       python validate_psid.py <original.sid> <exported.sid>")
        sys.exit(1)

    file1 = Path(sys.argv[1])

    if not file1.exists():
        print(f"Error: File not found: {file1}")
        sys.exit(1)

    # Comparison mode
    if len(sys.argv) >= 3:
        file2 = Path(sys.argv[2])
        if not file2.exists():
            print(f"Error: File not found: {file2}")
            sys.exit(1)

        print(compare_psid_files(file1, file2))
        sys.exit(0)

    # Single file validation
    validator = PSIDValidator(file1)
    validator.validate()
    print(validator.get_summary())

    sys.exit(0 if len(validator.errors) == 0 else 1)


if __name__ == '__main__':
    main()
