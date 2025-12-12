#!/usr/bin/env python3
"""Comprehensive test for Wave and Pulse table extraction"""
import struct

# Read the newly extracted file
with open("test_wave_pulse_fixed.sf2", 'rb') as f:
    sf2_data = f.read()

# Get load address
load_addr = struct.unpack('<H', sf2_data[0:2])[0]
print(f"SF2 Load Address: ${load_addr:04X}")
print()

# Test Wave table
print("=" * 60)
print("WAVE TABLE TEST")
print("=" * 60)

wave_addr = 0x1924
wave_offset = wave_addr - load_addr + 2

print(f"Wave table at memory ${wave_addr:04X}, file offset ${wave_offset:04X}")
print()

# Expected wave data (from working FIXED.sf2 file)
expected_wave_col0 = bytes([0x21, 0x21, 0x41, 0x7F, 0x81, 0x41, 0x41, 0x41, 0x7F, 0x81])
expected_wave_col1 = bytes([0x80, 0x80, 0x00, 0x02, 0xC0, 0xA1, 0x9A, 0x00, 0x07, 0xC4])

# Read actual wave data
actual_wave_col0 = sf2_data[wave_offset:wave_offset + 10]
actual_wave_col1 = sf2_data[wave_offset + 256:wave_offset + 256 + 10]

print("Column 0 (Waveform) - first 10 bytes:")
print(f"  Expected: {' '.join(f'{b:02X}' for b in expected_wave_col0)}")
print(f"  Actual:   {' '.join(f'{b:02X}' for b in actual_wave_col0)}")

if actual_wave_col0 == expected_wave_col0:
    print("  [CORRECT]")
else:
    print("  [WRONG]")

print()
print("Column 1 (Note Offset) - first 10 bytes:")
print(f"  Expected: {' '.join(f'{b:02X}' for b in expected_wave_col1)}")
print(f"  Actual:   {' '.join(f'{b:02X}' for b in actual_wave_col1)}")

if actual_wave_col1 == expected_wave_col1:
    print("  ✓ CORRECT")
else:
    print("  ✗ WRONG")

print()
print("=" * 60)
print("PULSE TABLE TEST")
print("=" * 60)

pulse_addr = 0x1B24
pulse_offset = pulse_addr - load_addr + 2

print(f"Pulse table at memory ${pulse_addr:04X}, file offset ${pulse_offset:04X}")
print()

# Expected pulse data
expected_pulse_col0 = bytes([0x88, 0x00, 0x81, 0x00, 0x00, 0x0F, 0x7F, 0x88, 0x7F, 0x88])
expected_pulse_col1 = bytes([0x00, 0x00, 0x70, 0x40, 0x10, 0xF0, 0x00, 0x00, 0x00, 0x00])
expected_pulse_col2 = bytes([0x00, 0x01, 0x00, 0x04, 0x20, 0x20, 0x04, 0x00, 0x07, 0x00])

# Read actual pulse data
actual_pulse_col0 = sf2_data[pulse_offset:pulse_offset + 10]
actual_pulse_col1 = sf2_data[pulse_offset + 256:pulse_offset + 256 + 10]
actual_pulse_col2 = sf2_data[pulse_offset + 512:pulse_offset + 512 + 10]

print("Column 0 (Value) - first 10 bytes:")
print(f"  Expected: {' '.join(f'{b:02X}' for b in expected_pulse_col0)}")
print(f"  Actual:   {' '.join(f'{b:02X}' for b in actual_pulse_col0)}")

if actual_pulse_col0 == expected_pulse_col0:
    print("  ✓ CORRECT")
else:
    print("  ✗ WRONG")

print()
print("Column 1 (Delta) - first 10 bytes:")
print(f"  Expected: {' '.join(f'{b:02X}' for b in expected_pulse_col1)}")
print(f"  Actual:   {' '.join(f'{b:02X}' for b in actual_pulse_col1)}")

if actual_pulse_col1 == expected_pulse_col1:
    print("  ✓ CORRECT")
else:
    print("  ✗ WRONG")

print()
print("Column 2 (Duration) - first 10 bytes:")
print(f"  Expected: {' '.join(f'{b:02X}' for b in expected_pulse_col2)}")
print(f"  Actual:   {' '.join(f'{b:02X}' for b in actual_pulse_col2)}")

if actual_pulse_col2 == expected_pulse_col2:
    print("  ✓ CORRECT")
else:
    print("  ✗ WRONG")

print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)

wave_correct = (actual_wave_col0 == expected_wave_col0 and
                actual_wave_col1 == expected_wave_col1)
pulse_correct = (actual_pulse_col0 == expected_pulse_col0 and
                 actual_pulse_col1 == expected_pulse_col1 and
                 actual_pulse_col2 == expected_pulse_col2)

if wave_correct and pulse_correct:
    print("✓ ALL TESTS PASSED - Wave and Pulse extraction is correct!")
else:
    if not wave_correct:
        print("✗ Wave table extraction FAILED")
    if not pulse_correct:
        print("✗ Pulse table extraction FAILED")
