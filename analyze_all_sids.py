#!/usr/bin/env python3
"""
Analyze all SID files to understand instrument and table formats.
"""

import struct
import os
from laxity_parser import LaxityParser

def load_sid(path):
    with open(path, 'rb') as f:
        data = f.read()

    # Parse PSID header
    magic = data[0:4].decode('ascii')
    version = struct.unpack('>H', data[4:6])[0]
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_address = struct.unpack('>H', data[8:10])[0]
    init_address = struct.unpack('>H', data[10:12])[0]
    play_address = struct.unpack('>H', data[12:14])[0]
    name = data[22:54].decode('latin-1').rstrip('\x00')
    author = data[54:86].decode('latin-1').rstrip('\x00')

    c64_data = data[data_offset:]
    if load_address == 0:
        load_address = struct.unpack('<H', c64_data[0:2])[0]
        c64_data = c64_data[2:]

    return {
        'name': name,
        'author': author,
        'load_address': load_address,
        'init_address': init_address,
        'play_address': play_address,
        'c64_data': c64_data,
        'data_size': len(c64_data)
    }

def analyze_sid(filepath):
    """Analyze a single SID file"""
    sid = load_sid(filepath)

    print(f"\n{'='*60}")
    print(f"FILE: {os.path.basename(filepath)}")
    print(f"{'='*60}")
    print(f"Name: {sid['name']}")
    print(f"Author: {sid['author']}")
    print(f"Load: ${sid['load_address']:04X}, Init: ${sid['init_address']:04X}, Play: ${sid['play_address']:04X}")
    print(f"Data size: {sid['data_size']} bytes")

    # Parse with Laxity parser
    parser = LaxityParser(sid['c64_data'], sid['load_address'])

    print("\nFinding orderlists...")
    orderlists = parser.find_orderlists()

    print("\nFinding sequences...")
    sequences, seq_addrs = parser.find_sequences()

    print("\nFinding instruments...")
    instruments = parser.find_instruments()

    # Summary
    print(f"\n--- SUMMARY ---")
    print(f"Orderlists: {len(orderlists)}")
    for i, ol in enumerate(orderlists):
        print(f"  Voice {i+1}: {len(ol)} entries, max seq={max(ol) if ol else 0}")

    print(f"Sequences: {len(sequences)}")
    if sequences:
        total_bytes = sum(len(s) for s in sequences)
        print(f"  Total bytes: {total_bytes}")

    print(f"Instruments: {len(instruments)}")
    for i, instr in enumerate(instruments):
        hex_str = ' '.join(f'{b:02X}' for b in instr)
        print(f"  Instr {i}: {hex_str}")

    return {
        'orderlists': orderlists,
        'sequences': sequences,
        'instruments': instruments
    }

def main():
    sid_dir = 'SID'

    results = {}

    for filename in sorted(os.listdir(sid_dir)):
        if filename.endswith('.sid'):
            filepath = os.path.join(sid_dir, filename)
            try:
                results[filename] = analyze_sid(filepath)
            except Exception as e:
                print(f"\nERROR analyzing {filename}: {e}")

    # Cross-file analysis
    print("\n" + "="*60)
    print("CROSS-FILE ANALYSIS")
    print("="*60)

    # Check instrument patterns
    print("\nInstrument byte patterns across all files:")
    all_instruments = []
    for filename, data in results.items():
        for instr in data['instruments']:
            all_instruments.append((filename, instr))

    if all_instruments:
        print(f"Total instruments found: {len(all_instruments)}")

        # Analyze byte positions
        for pos in range(8):
            values = [instr[pos] if len(instr) > pos else 0 for _, instr in all_instruments]
            unique = set(values)
            print(f"  Byte {pos}: {len(unique)} unique values, range {min(values):02X}-{max(values):02X}")

if __name__ == '__main__':
    main()
