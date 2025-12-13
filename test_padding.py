#!/usr/bin/env python3
"""Test table padding logic"""

import sys
sys.path.insert(0, '.')
from sidm2.table_extraction import extract_all_laxity_tables

with open('SIDSF2player/Aint_Somebody.sid', 'rb') as f:
    data = f.read()

# Skip PSID header
c64_data = data[0x7C:]
load_addr = 0x1000

laxity_tables = extract_all_laxity_tables(c64_data, load_addr)

# Simulate the padding logic from sf2_writer.py
pulse_entries = laxity_tables.get('pulse_table', [])
original_count = len(pulse_entries)

print(f"Original pulse entries: {original_count}")
print(f"Entries: {pulse_entries}")

# Padding logic
MIN_PULSE_ENTRIES = 16
neutral_entry = (0xFF, 0x00, 0x00, 0x00)
while len(pulse_entries) < MIN_PULSE_ENTRIES:
    pulse_entries.append(neutral_entry)

print(f"\nAfter padding: {len(pulse_entries)} entries")
print(f"Message would be: Written {len(pulse_entries)} Pulse table entries (padded from {len(laxity_tables.get('pulse_table', []))})")

# Check filter too
filter_entries = laxity_tables.get('filter_table', [])
original_filter_count = len(filter_entries)

print(f"\n\nOriginal filter entries: {original_filter_count}")
print(f"Entries: {filter_entries}")

MIN_FILTER_ENTRIES = 16
neutral_entry = (0x00, 0x00, 0x00, 0x00)
while len(filter_entries) < MIN_FILTER_ENTRIES:
    filter_entries.append(neutral_entry)

print(f"\nAfter padding: {len(filter_entries)} entries")
