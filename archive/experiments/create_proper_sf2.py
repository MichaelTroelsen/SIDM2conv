#!/usr/bin/env python3
"""
Create a proper SF2 file using the SF2Writer framework.

This uses the existing SF2Writer class which handles the correct block structure.
"""

import pickle
import struct
from sidm2.models import ExtractedData, PSIDHeader, SequenceEvent
from sidm2.sf2_writer import SF2Writer


def load_extracted_sequences():
    """Load sequences and orderlists from pickle file."""
    with open('sf2_music_data_extracted.pkl', 'rb') as f:
        data = pickle.load(f)
    return data['sequences'], data['orderlists']


def convert_sequences_to_model(sequences):
    """Convert sequence format to SequenceEvent objects."""
    converted = []

    for seq in sequences:
        events = []
        for entry in seq:
            # entry is [inst, cmd, note]
            event = SequenceEvent(
                instrument=entry[0],
                command=entry[1],
                note=entry[2]
            )
            events.append(event)
        converted.append(events)

    return converted


def convert_orderlists_to_model(orderlists):
    """Convert orderlist format to (transpose, seq_idx) tuples."""
    converted = []

    for orderlist in orderlists:
        entries = []
        # Orderlist is: [A0, 00, A0, 01, ..., A0, 7F]
        # Convert to list of (transpose, seq_idx) tuples
        i = 0
        while i < len(orderlist) - 1:
            transpose = orderlist[i]
            seq_idx = orderlist[i + 1]

            if seq_idx == 0x7F:  # End marker
                break

            entries.append((transpose, seq_idx))
            i += 2

        converted.append(entries)

    return converted


def create_minimal_psid_header():
    """Create a minimal PSID header for the ExtractedData."""
    return PSIDHeader(
        magic='PSID',
        version=2,
        data_offset=0x7C,
        load_address=0x1000,
        init_address=0x1000,
        play_address=0x1003,
        songs=1,
        start_song=1,
        speed=0,
        name='Reconstructed from Siddump',
        author='Laxity (Original)',
        copyright='2025 (Reconstructed)'
    )


def main():
    sid_file = 'SID/Stinsens_Last_Night_of_89.sid'
    output_file = 'output/Stinsens_reconstructed_proper.sf2'

    print("=" * 70)
    print("CREATING PROPER SF2 FILE WITH SF2WRITER")
    print("=" * 70)
    print()

    # Step 1: Load extracted data
    print("Step 1: Load extracted sequences and orderlists...")
    sequences_raw, orderlists_raw = load_extracted_sequences()
    print(f"  Loaded {len(sequences_raw)} sequences")
    print(f"  Loaded {len(orderlists_raw)} orderlists")
    print()

    # Step 2: Convert to model format
    print("Step 2: Convert to ExtractedData model format...")
    sequences = convert_sequences_to_model(sequences_raw)
    orderlists = convert_orderlists_to_model(orderlists_raw)
    print(f"  Converted {len(sequences)} sequences")
    print(f"  Converted {len(orderlists)} orderlists")
    print()

    # Step 3: Load SID file for c64_data
    print("Step 3: Load SID file...")
    with open(sid_file, 'rb') as f:
        sid_data = f.read()

    # Extract C64 data (after PSID header)
    load_addr = struct.unpack('<H', sid_data[0x7C:0x7E])[0]
    c64_data = sid_data[0x7E:]
    print(f"  Load address: ${load_addr:04X}")
    print(f"  C64 data size: {len(c64_data)} bytes")
    print()

    # Step 4: Create ExtractedData object
    print("Step 4: Create ExtractedData object...")
    header = create_minimal_psid_header()

    # Create default tables (since we used defaults in assembly)
    default_wave = bytes([0x11, 0x00] * 64)      # Default: pulse wave
    default_pulse = bytes([0x08, 0x00, 0x00, 0x01] * 32)
    default_filter = bytes([0x00] * 128)
    default_instruments = [bytes([0x88, 0x00, 0x00, 0x00, 0x00, 0x00])] * 32  # Default ADSR

    extracted_data = ExtractedData(
        header=header,
        c64_data=c64_data,
        load_address=load_addr,
        sequences=sequences,
        orderlists=orderlists,
        instruments=default_instruments,
        wavetable=default_wave,
        pulsetable=default_pulse,
        filtertable=default_filter,
        tempo=6,
        init_volume=0x0F
    )

    print(f"  Sequences: {len(extracted_data.sequences)}")
    print(f"  Orderlists: {len(extracted_data.orderlists)}")
    print(f"  Instruments: {len(extracted_data.instruments)}")
    print()

    # Step 5: Write SF2 file using SF2Writer
    print("Step 5: Write SF2 file using SF2Writer...")
    print("  This will use a template and create proper block structure")
    print()

    try:
        writer = SF2Writer(extracted_data, driver_type='d11')
        writer.write(output_file)

        print(f"SUCCESS! SF2 file created: {output_file}")
        print()

        # Show file size
        import os
        file_size = os.path.getsize(output_file)
        print(f"File size: {file_size} bytes")
        print()

        print("=" * 70)
        print("NEXT: Load this file in SID Factory II Editor")
        print("=" * 70)
        print()
        print("File → Open → output/Stinsens_reconstructed_proper.sf2")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
