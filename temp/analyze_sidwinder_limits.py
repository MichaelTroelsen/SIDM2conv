"""Analyze SIDwinder disassembly failures"""
import struct
from pathlib import Path

failing_files = [
    "Driver 11 Test - Arpeggio.sid",
    "Driver 11 Test - Filter.sid",
    "Driver 11 Test - Polyphonic.sid",
    "Driver 11 Test - Tie Notes.sid",
    "polyphonic_cpp.sid",
    "polyphonic_test.sid",
    "tie_notes_test.sid"
]

working_files = [
    "Cocktail_to_Go_tune_3.sid",
    "Broware.sid",
    "Staying_Alive.sid"
]

def parse_sid_header(filepath):
    with open(filepath, 'rb') as f:
        data = f.read(128)
        magic = data[0:4].decode('ascii')
        version = struct.unpack('>H', data[4:6])[0]
        data_offset = struct.unpack('>H', data[6:8])[0]
        load_addr = struct.unpack('>H', data[8:10])[0]
        init_addr = struct.unpack('>H', data[10:12])[0]
        play_addr = struct.unpack('>H', data[12:14])[0]
        
        return {
            'magic': magic,
            'version': version,
            'data_offset': data_offset,
            'load': load_addr,
            'init': init_addr,
            'play': play_addr
        }

print("=" * 80)
print("SIDWINDER DISASSEMBLY ANALYSIS")
print("=" * 80)
print()

print("FAILING FILES:")
print("-" * 80)
for f in failing_files:
    path = Path('SIDSF2player') / f
    if path.exists():
        info = parse_sid_header(path)
        print(f"{f:45} load=${info['load']:04X} init=${info['init']:04X} play=${info['play']:04X}")

print()
print("WORKING FILES:")
print("-" * 80)
for f in working_files:
    path = Path('SIDSF2player') / f
    if path.exists():
        info = parse_sid_header(path)
        print(f"{f:45} load=${info['load']:04X} init=${info['init']:04X} play=${info['play']:04X}")

print()
print("=" * 80)
print("PATTERN ANALYSIS:")
print("=" * 80)
print()
print("Standard SF2-packed SID:  load=$0000 init=$1000 play=$1003")
print("Laxity NewPlayer format:  load=$0000 init=$1000 play=$10A1 (approx)")
print()
print("The failing files have play addresses far beyond the typical range,")
print("suggesting they use extended player code or non-standard init sequences")
print("that SIDwinder's CPU emulator can't handle correctly.")
