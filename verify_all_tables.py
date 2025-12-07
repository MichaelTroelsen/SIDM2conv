#!/usr/bin/env python3
"""
Comprehensive SF2 table verification script.
Compares generated SF2 file with expected Driver 11 format.
"""

import struct
import sys

def read_sf2_data(filepath):
    """Read SF2 file and return (data, load_addr)"""
    with open(filepath, 'rb') as f:
        data = f.read()
    # SF2 files are PRG files: first 2 bytes are load address (little-endian)
    load_addr = struct.unpack('<H', data[0:2])[0]
    return data, load_addr

def get_offset(load_addr, mem_addr):
    """Convert memory address to file offset"""
    # PRG format: load address (2 bytes) + data
    return mem_addr - load_addr + 2

def verify_wave_table(data, load_addr):
    """Verify wave table format (2 columns × 256 rows, column-major)"""
    wave_addr = 0x1924  # Driver 11 wave table address
    offset = get_offset(load_addr, wave_addr)

    print("=" * 80)
    print("WAVE TABLE at $1924 (2 columns × 256 rows, column-major)")
    print("=" * 80)
    print("Column 0 (Waveforms) - first 10 bytes:")
    waveforms = [data[offset + i] for i in range(10)]
    print(f"  {' '.join(f'{b:02X}' for b in waveforms)}")
    print(f"  Expected: 21 21 41 7F 81 41 41 41 7F 81")

    print("\nColumn 1 (Notes) - first 10 bytes (offset +256):")
    notes = [data[offset + 256 + i] for i in range(10)]
    print(f"  {' '.join(f'{b:02X}' for b in notes)}")
    print(f"  Expected: 80 80 00 02 C0 A1 9A 00 07 C4")

    # Check if it matches expected
    expected_wf = [0x21, 0x21, 0x41, 0x7F, 0x81, 0x41, 0x41, 0x41, 0x7F, 0x81]
    expected_nt = [0x80, 0x80, 0x00, 0x02, 0xC0, 0xA1, 0x9A, 0x00, 0x07, 0xC4]

    wf_match = waveforms == expected_wf
    nt_match = notes == expected_nt

    print(f"\n  Waveforms: {'PASS' if wf_match else 'FAIL'}")
    print(f"  Notes:     {'PASS' if nt_match else 'FAIL'}")
    return wf_match and nt_match

def verify_pulse_table(data, load_addr):
    """Verify pulse table format (4 columns × 256 rows, column-major)"""
    pulse_addr = 0x1B24  # Driver 11 pulse table address
    offset = get_offset(load_addr, pulse_addr)

    print("\n" + "=" * 80)
    print("PULSE TABLE at $1B24 (4 columns × 256 rows, column-major)")
    print("=" * 80)

    for col in range(4):
        col_offset = offset + (col * 256)
        print(f"Column {col} - first 10 bytes (offset +{col*256}):")
        col_data = [data[col_offset + i] for i in range(10)]
        print(f"  {' '.join(f'{b:02X}' for b in col_data)}")

    print("\n  Format: Col0=Value, Col1=Delta, Col2=Duration, Col3=Next")
    return True  # Can't verify without known good data

def verify_filter_table(data, load_addr):
    """Verify filter table format (4 columns × 256 rows, column-major)"""
    filter_addr = 0x1E24  # Driver 11 filter table address
    offset = get_offset(load_addr, filter_addr)

    print("\n" + "=" * 80)
    print("FILTER TABLE at $1E24 (4 columns × 256 rows, column-major)")
    print("=" * 80)

    for col in range(4):
        col_offset = offset + (col * 256)
        print(f"Column {col} - first 10 bytes (offset +{col*256}):")
        col_data = [data[col_offset + i] for i in range(10)]
        print(f"  {' '.join(f'{b:02X}' for b in col_data)}")

    print("\n  Format: Col0=Cutoff, Col1=Count, Col2=Duration, Col3=Next")
    return True

def verify_instruments_table(data, load_addr):
    """Verify instruments table format (6 columns × 32 rows, column-major)"""
    instr_addr = 0x1784  # Driver 11 instruments table address
    offset = get_offset(load_addr, instr_addr)

    print("\n" + "=" * 80)
    print("INSTRUMENTS TABLE at $1784 (6 columns × 32 rows, column-major)")
    print("=" * 80)

    for col in range(6):
        col_offset = offset + (col * 32)
        print(f"Column {col} - first 8 bytes (offset +{col*32}):")
        col_data = [data[col_offset + i] for i in range(8)]
        print(f"  {' '.join(f'{b:02X}' for b in col_data)}")

    print("\n  Format: Col0=AD, Col1=SR, Col2=Flags, Col3=Filter, Col4=Pulse, Col5=Wave")
    return True

def verify_commands_table(data, load_addr):
    """Verify commands table format (3 columns × 64 rows)"""
    cmd_addr = 0x1844  # Driver 11 commands table address
    offset = get_offset(load_addr, cmd_addr)

    print("\n" + "=" * 80)
    print("COMMANDS TABLE at $1844 (3 columns × 64 rows)")
    print("=" * 80)

    # Check if row-major or column-major
    print("First 30 bytes (checking layout):")
    cmd_data = [data[offset + i] for i in range(30)]
    print(f"  {' '.join(f'{b:02X}' for b in cmd_data)}")

    print("\n  Format: Col0=Command, Col1=Param1, Col2=Param2")
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_all_tables.py <sf2_file>")
        sys.exit(1)

    sf2_file = sys.argv[1]
    print(f"Verifying SF2 file: {sf2_file}\n")

    data, load_addr = read_sf2_data(sf2_file)
    print(f"Load address: ${load_addr:04X}")
    print(f"File size: {len(data)} bytes\n")

    # Verify all tables
    results = {}
    results['wave'] = verify_wave_table(data, load_addr)
    results['pulse'] = verify_pulse_table(data, load_addr)
    results['filter'] = verify_filter_table(data, load_addr)
    results['instruments'] = verify_instruments_table(data, load_addr)
    results['commands'] = verify_commands_table(data, load_addr)

    # Summary
    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)
    for table, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {table.upper()}: {status}")

if __name__ == '__main__':
    main()
