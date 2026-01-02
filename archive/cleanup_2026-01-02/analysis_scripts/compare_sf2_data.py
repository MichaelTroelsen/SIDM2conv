#!/usr/bin/env python3
"""Compare music data between two SF2 files and reference export."""

import sys
import struct
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def parse_sf2_file(sf2_path: Path):
    """Parse SF2 file and extract music data."""
    print(f"\nParsing: {sf2_path.name}")

    with open(sf2_path, 'rb') as f:
        data = f.read()

    # Basic SF2 format parsing
    # Read PRG load address (first 2 bytes, little-endian)
    load_addr = struct.unpack('<H', data[0:2])[0]
    c64_data = data[2:]  # Skip PRG header

    print(f"  Load address: ${load_addr:04X}")
    print(f"  C64 data size: {len(c64_data)} bytes")

    # Look for SF2 metadata blocks (these start at fixed offsets in the file)
    # We'll parse the key tables:
    # - Orderlist (3 voices × positions)
    # - Instruments (32 instruments × 8 bytes)
    # - Sequences (up to 256 sequences)

    result = {
        'load_addr': load_addr,
        'orderlist': [],
        'instruments': [],
        'sequences': [],
        'wave_table': [],
        'pulse_table': [],
        'filter_table': [],
    }

    # Try to find and parse tables
    # This is a simplified version - the full parser would have more robust detection
    return result


def export_sf2_data(sf2_file: Path, output_dir: Path):
    """Export all music data from an SF2 file."""
    print(f"\nExporting data from: {sf2_file.name}")

    data = parse_sf2_file(sf2_file)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export orderlist
    orderlist_file = output_dir / 'orderlist.txt'
    with open(orderlist_file, 'w') as f:
        f.write("Orderlist (Voice 1, Voice 2, Voice 3):\n")
        f.write("=" * 70 + "\n")
        for i, (v1, v2, v3) in enumerate(data['orderlist']):
            f.write(f"Position {i:3d}: ${v1:02X} ${v2:02X} ${v3:02X}\n")

    # Export instruments
    instruments_file = output_dir / 'instruments.txt'
    with open(instruments_file, 'w') as f:
        f.write("Instruments:\n")
        f.write("=" * 70 + "\n")
        for i, inst in enumerate(data['instruments']):
            f.write(f"Instrument {i:2d}: "
                   f"Wave=${inst['wave']:02X} "
                   f"Pulse=${inst['pulse']:02X} "
                   f"Filter=${inst['filter']:02X} "
                   f"Attack=${inst['attack']:X} "
                   f"Decay=${inst['decay']:X} "
                   f"Sustain=${inst['sustain']:X} "
                   f"Release=${inst['release']:X} "
                   f"Vibrato=${inst['vibrato']:02X}\n")

    # Export sequences (just the first 20 for comparison)
    for seq_idx in range(min(20, len(data['sequences']))):
        seq = data['sequences'][seq_idx]
        seq_file = output_dir / f'sequence_{seq_idx:02d}_${seq_idx:X}.txt'
        with open(seq_file, 'w') as f:
            f.write(f"Sequence {seq_idx} (${seq_idx:02X}):\n")
            f.write("=" * 70 + "\n")
            for event in seq:
                f.write(f"${event:02X}\n")

    # Export tables summary
    summary_file = output_dir / 'summary.txt'
    with open(summary_file, 'w') as f:
        f.write(f"SF2 File: {sf2_file.name}\n")
        f.write("=" * 70 + "\n")
        f.write(f"Orderlist positions: {len(data['orderlist'])}\n")
        f.write(f"Instruments: {len(data['instruments'])}\n")
        f.write(f"Sequences: {len(data['sequences'])}\n")
        f.write(f"Wave table entries: {len(data['wave_table'])}\n")
        f.write(f"Pulse table entries: {len(data['pulse_table'])}\n")
        f.write(f"Filter table entries: {len(data['filter_table'])}\n")
        f.write(f"Arp table entries: {len(data.get('arp_table', []))}\n")

    print(f"  ✓ Exported to {output_dir}")
    return data


def compare_orderlists(data1, data2, name1, name2):
    """Compare orderlist data."""
    print(f"\n{'='*70}")
    print(f"ORDERLIST COMPARISON: {name1} vs {name2}")
    print(f"{'='*70}")

    ol1 = data1['orderlist']
    ol2 = data2['orderlist']

    if len(ol1) != len(ol2):
        print(f"⚠ LENGTH MISMATCH: {len(ol1)} vs {len(ol2)}")

    matches = 0
    for i in range(min(len(ol1), len(ol2))):
        if ol1[i] == ol2[i]:
            matches += 1
        else:
            print(f"Position {i:3d}: ${ol1[i][0]:02X} ${ol1[i][1]:02X} ${ol1[i][2]:02X} vs "
                  f"${ol2[i][0]:02X} ${ol2[i][1]:02X} ${ol2[i][2]:02X}")

    accuracy = (matches / max(len(ol1), len(ol2))) * 100
    print(f"\nOrderlist accuracy: {matches}/{max(len(ol1), len(ol2))} ({accuracy:.1f}%)")
    return accuracy


def compare_instruments(data1, data2, name1, name2):
    """Compare instrument data."""
    print(f"\n{'='*70}")
    print(f"INSTRUMENTS COMPARISON: {name1} vs {name2}")
    print(f"{'='*70}")

    inst1 = data1['instruments']
    inst2 = data2['instruments']

    if len(inst1) != len(inst2):
        print(f"⚠ LENGTH MISMATCH: {len(inst1)} vs {len(inst2)}")

    matches = 0
    for i in range(min(len(inst1), len(inst2))):
        if inst1[i] == inst2[i]:
            matches += 1
        else:
            print(f"Instrument {i:2d}:")
            print(f"  {name1}: Wave=${inst1[i]['wave']:02X} Pulse=${inst1[i]['pulse']:02X} "
                  f"Filter=${inst1[i]['filter']:02X} ADSR=${inst1[i]['attack']:X}{inst1[i]['decay']:X}"
                  f"{inst1[i]['sustain']:X}{inst1[i]['release']:X} Vib=${inst1[i]['vibrato']:02X}")
            print(f"  {name2}: Wave=${inst2[i]['wave']:02X} Pulse=${inst2[i]['pulse']:02X} "
                  f"Filter=${inst2[i]['filter']:02X} ADSR=${inst2[i]['attack']:X}{inst2[i]['decay']:X}"
                  f"{inst2[i]['sustain']:X}{inst2[i]['release']:X} Vib=${inst2[i]['vibrato']:02X}")

    accuracy = (matches / max(len(inst1), len(inst2))) * 100
    print(f"\nInstruments accuracy: {matches}/{max(len(inst1), len(inst2))} ({accuracy:.1f}%)")
    return accuracy


def compare_sequences(data1, data2, name1, name2, max_sequences=20):
    """Compare sequence data."""
    print(f"\n{'='*70}")
    print(f"SEQUENCES COMPARISON (first {max_sequences}): {name1} vs {name2}")
    print(f"{'='*70}")

    seq1 = data1['sequences']
    seq2 = data2['sequences']

    if len(seq1) != len(seq2):
        print(f"⚠ TOTAL SEQUENCES MISMATCH: {len(seq1)} vs {len(seq2)}")

    matches = 0
    total = 0

    for i in range(min(max_sequences, len(seq1), len(seq2))):
        if seq1[i] == seq2[i]:
            matches += 1
        else:
            print(f"\nSequence {i} (${i:02X}):")
            print(f"  {name1}: {len(seq1[i])} events")
            print(f"  {name2}: {len(seq2[i])} events")

            # Show first few differences
            diffs = 0
            for j in range(min(len(seq1[i]), len(seq2[i]))):
                if seq1[i][j] != seq2[i][j] and diffs < 5:
                    print(f"    Event {j}: ${seq1[i][j]:02X} vs ${seq2[i][j]:02X}")
                    diffs += 1
        total += 1

    accuracy = (matches / total) * 100 if total > 0 else 0
    print(f"\nSequences accuracy (first {max_sequences}): {matches}/{total} ({accuracy:.1f}%)")
    return accuracy


def main():
    """Main comparison."""
    # File paths
    original_sf2 = Path(r"C:\Users\mit\claude\c64server\SIDM2\learnings\Laxity - Stinsen - Last Night Of 89.sf2")
    converted_sf2 = Path(r"C:\Users\mit\claude\c64server\SIDM2\output\Stinsens_FINAL.sf2")

    # Output directories
    original_export = Path(r"C:\Users\mit\claude\c64server\SIDM2\output\comparison\original")
    converted_export = Path(r"C:\Users\mit\claude\c64server\SIDM2\output\comparison\converted")

    print("="*70)
    print("SF2 DATA COMPARISON")
    print("="*70)

    # Export data from both files
    original_data = export_sf2_data(original_sf2, original_export)
    converted_data = export_sf2_data(converted_sf2, converted_export)

    if original_data is None or converted_data is None:
        print("\nERROR: Failed to parse one or both SF2 files")
        return 1

    # Compare data
    ol_accuracy = compare_orderlists(original_data, converted_data, "ORIGINAL", "CONVERTED")
    inst_accuracy = compare_instruments(original_data, converted_data, "ORIGINAL", "CONVERTED")
    seq_accuracy = compare_sequences(original_data, converted_data, "ORIGINAL", "CONVERTED")

    # Final summary
    print(f"\n{'='*70}")
    print("FINAL COMPARISON SUMMARY")
    print(f"{'='*70}")
    print(f"Orderlist accuracy:   {ol_accuracy:.1f}%")
    print(f"Instruments accuracy: {inst_accuracy:.1f}%")
    print(f"Sequences accuracy:   {seq_accuracy:.1f}%")

    overall = (ol_accuracy + inst_accuracy + seq_accuracy) / 3
    print(f"\nOverall accuracy:     {overall:.1f}%")

    if overall >= 99.9:
        print("\n✅ EXCELLENT: Files are virtually identical!")
    elif overall >= 95.0:
        print("\n✓ GOOD: Files are very similar with minor differences")
    elif overall >= 80.0:
        print("\n⚠ FAIR: Files have some differences")
    else:
        print("\n❌ POOR: Files have significant differences")

    return 0


if __name__ == '__main__':
    sys.exit(main())
