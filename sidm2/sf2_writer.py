"""
SF2 file writer - writes SID Factory II project files.
"""

import struct
import os
from typing import Optional

from .models import ExtractedData, SF2DriverInfo
from .table_extraction import find_and_extract_wave_table, extract_all_laxity_tables
from .instrument_extraction import extract_laxity_instruments, extract_laxity_wave_table
from .sequence_extraction import get_command_names


class SF2Writer:
    """Write SID Factory II .sf2 project files"""

    # SF2 file format constants
    SF2_FILE_ID = 0x1337
    SF2_DRIVER_VERSION = 11

    # Header block IDs
    BLOCK_DESCRIPTOR = 1
    BLOCK_DRIVER_COMMON = 2
    BLOCK_DRIVER_TABLES = 3
    BLOCK_INSTRUMENT_DESC = 4
    BLOCK_MUSIC_DATA = 5
    BLOCK_END = 0xFF

    def __init__(self, extracted_data: ExtractedData, driver_type: str = 'np20'):
        self.data = extracted_data
        self.output = bytearray()
        self.template_path = None
        self.driver_info = SF2DriverInfo()
        self.load_address = 0
        self.driver_type = driver_type

    def write(self, filepath: str):
        """Write the SF2 file"""
        template_path = self._find_template(self.driver_type)

        if template_path and os.path.exists(template_path):
            print(f"Using template: {template_path}")
            with open(template_path, 'rb') as f:
                template_data = f.read()

            self.output = bytearray(template_data)
            self._inject_music_data_into_template()
        else:
            driver_path = self._find_driver()

            if driver_path and os.path.exists(driver_path):
                print(f"Using driver: {driver_path}")
                with open(driver_path, 'rb') as f:
                    driver_data = f.read()

                self.output = bytearray(driver_data)
            else:
                print("Warning: No template or driver found, creating minimal structure")
                self._create_minimal_structure()

            self._inject_music_data()

        self._inject_auxiliary_data()

        with open(filepath, 'wb') as f:
            f.write(self.output)

        print(f"Written SF2 file: {filepath}")
        print(f"File size: {len(self.output)} bytes")

    def _find_template(self, driver_type: str = 'driver11') -> Optional[str]:
        """Find an SF2 template file to use as base"""
        driver_templates = {
            'driver11': [
                'template.sf2',
                r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\music\Driver 11 Test - Arpeggio.sf2',
            ],
            'np20': [
                'template_np20.sf2',
                r'C:\Users\mit\Downloads\sidfactory2-master\sidfactory2-master\SIDFactoryII\drivers\sf2driver_np20_00.prg',
                r'C:\Users\mit\Downloads\SIDFactoryII_Win32_20231002\drivers\sf2driver_np20_00.prg',
            ],
        }

        search_paths = driver_templates.get(driver_type, driver_templates['driver11'])
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        for path in search_paths:
            if os.path.isabs(path):
                if os.path.exists(path):
                    return path
            else:
                full_path = os.path.join(base_dir, path)
                if os.path.exists(full_path):
                    return full_path

        return None

    def _parse_sf2_header(self):
        """Parse the SF2 driver header to find data locations"""
        if len(self.output) < 4:
            return False

        self.load_address = struct.unpack('<H', self.output[0:2])[0]

        file_id = struct.unpack('<H', self.output[2:4])[0]
        if file_id != self.SF2_FILE_ID:
            print(f"Warning: File ID {file_id:04X} != expected {self.SF2_FILE_ID:04X}")
            return False

        print(f"Parsing SF2 header (load address: ${self.load_address:04X})")

        offset = 4
        while offset < len(self.output) - 2:
            block_id = self.output[offset]
            if block_id == self.BLOCK_END:
                break

            block_size = self.output[offset + 1]
            block_data = self.output[offset + 2:offset + 2 + block_size]

            if block_id == self.BLOCK_DESCRIPTOR:
                self._parse_descriptor_block(block_data)
            elif block_id == self.BLOCK_MUSIC_DATA:
                self._parse_music_data_block(block_data)
            elif block_id == self.BLOCK_DRIVER_TABLES:
                self._parse_tables_block(block_data)

            offset += 2 + block_size

        return True

    def _parse_descriptor_block(self, data: bytes):
        """Parse descriptor block"""
        if len(data) < 3:
            return

        self.driver_info.driver_type = data[0]
        self.driver_info.driver_size = struct.unpack('<H', data[1:3])[0]

        name_end = 3
        while name_end < len(data) and data[name_end] != 0:
            name_end += 1

        self.driver_info.driver_name = data[3:name_end].decode('latin-1', errors='replace')
        print(f"  Driver: {self.driver_info.driver_name}")

    def _parse_music_data_block(self, data: bytes):
        """Parse music data block to find sequence/orderlist locations"""
        if len(data) < 18:
            return

        idx = 0
        self.driver_info.track_count = data[idx]
        idx += 1

        self.driver_info.orderlist_ptrs_lo = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        self.driver_info.orderlist_ptrs_hi = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2

        self.driver_info.sequence_count = data[idx]
        idx += 1

        self.driver_info.sequence_ptrs_lo = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        self.driver_info.sequence_ptrs_hi = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2

        self.driver_info.orderlist_size = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        self.driver_info.orderlist_start = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2

        self.driver_info.sequence_size = struct.unpack('<H', data[idx:idx+2])[0]
        idx += 2
        self.driver_info.sequence_start = struct.unpack('<H', data[idx:idx+2])[0]

        print(f"  Tracks: {self.driver_info.track_count}")
        print(f"  Sequences: {self.driver_info.sequence_count}")
        print(f"  Sequence start: ${self.driver_info.sequence_start:04X}")
        print(f"  Orderlist start: ${self.driver_info.orderlist_start:04X}")

    def _parse_tables_block(self, data: bytes):
        """Parse table definitions block to find table addresses"""
        idx = 0

        while idx < len(data):
            if idx >= len(data):
                break

            table_type = data[idx]
            if table_type == 0xFF:
                break

            if idx + 3 > len(data):
                break

            table_id = data[idx + 1]
            text_field_size = data[idx + 2]

            name_start = idx + 3
            name_end = name_start
            while name_end < len(data) and data[name_end] != 0:
                name_end += 1
            name = data[name_start:name_end].decode('latin-1', errors='replace')

            pos = name_end + 1
            if pos + 12 <= len(data):
                addr = struct.unpack('<H', data[pos+5:pos+7])[0]
                columns = struct.unpack('<H', data[pos+7:pos+9])[0]
                rows = struct.unpack('<H', data[pos+9:pos+11])[0]

                table_info = {
                    'type': table_type,
                    'id': table_id,
                    'addr': addr,
                    'columns': columns,
                    'rows': rows,
                    'name': name
                }

                if table_type == 0x80:
                    self.driver_info.table_addresses['Instruments'] = table_info
                    print(f"    Instruments table at ${addr:04X} ({columns}×{rows}) [ID={table_id}]")
                elif table_type == 0x81:
                    self.driver_info.table_addresses['Commands'] = table_info
                    print(f"    Commands table at ${addr:04X} ({columns}×{rows}) [ID={table_id}]")
                else:
                    if name:
                        self.driver_info.table_addresses[name] = table_info
                        first_char = name[0] if name else ''
                        if first_char in ['W', 'P', 'F', 'A', 'T']:
                            key_map = {'W': 'Wave', 'P': 'Pulse', 'F': 'Filter', 'A': 'Arp', 'T': 'Tempo'}
                            self.driver_info.table_addresses[key_map.get(first_char, first_char)] = table_info

                idx = pos + 12
            else:
                break

    def _addr_to_offset(self, addr: int) -> int:
        """Convert C64 address to file offset"""
        return addr - self.load_address + 2

    def _inject_music_data_into_template(self):
        """Inject extracted music data into a template SF2 file"""
        print("Injecting music data into template...")
        print(f"Template size: {len(self.output)} bytes")

        if not self._parse_sf2_header():
            print("Warning: Could not parse SF2 header, using fallback")
            self._print_extraction_summary()
            return

        required_size = self._addr_to_offset(self.driver_info.sequence_start) + (self.driver_info.sequence_count * 256)
        if len(self.output) < required_size:
            print(f"  Expanding file from {len(self.output)} to {required_size} bytes")
            self.output.extend(bytearray(required_size - len(self.output)))

        if self.data.instruments or self.data.raw_sequences:
            self._inject_instruments()

        if self.data.sequences and self.driver_info.sequence_start:
            self._inject_sequences()

        if self.data.orderlists and self.driver_info.orderlist_start:
            self._inject_orderlists()

        self._inject_wave_table()
        self._inject_pulse_table()
        self._inject_filter_table()
        self._inject_hr_table()
        self._inject_init_table()
        self._inject_tempo_table()
        self._inject_arp_table()

        self._print_extraction_summary()

    def _inject_sequences(self):
        """Inject sequence data into the SF2 file using packed format"""
        print("\n  Injecting sequences...")

        seq_start = self._addr_to_offset(self.driver_info.sequence_start)
        ptr_lo_offset = self._addr_to_offset(self.driver_info.sequence_ptrs_lo)
        ptr_hi_offset = self._addr_to_offset(self.driver_info.sequence_ptrs_hi)

        if seq_start >= len(self.output) or seq_start < 0:
            print(f"    Warning: Invalid sequence start offset {seq_start}")
            return

        SEQUENCE_SLOT_SIZE = 256
        sequences_written = 0

        for i, seq in enumerate(self.data.sequences[:127]):
            if i >= self.driver_info.sequence_count:
                break

            current_addr = self.driver_info.sequence_start + (i * SEQUENCE_SLOT_SIZE)

            if ptr_lo_offset + i < len(self.output):
                self.output[ptr_lo_offset + i] = current_addr & 0xFF
            if ptr_hi_offset + i < len(self.output):
                self.output[ptr_hi_offset + i] = (current_addr >> 8) & 0xFF

            seq_offset = self._addr_to_offset(current_addr)

            if hasattr(self.data, 'raw_sequences') and i < len(self.data.raw_sequences):
                raw_seq = self.data.raw_sequences[i]
                j = 0
                while j < len(raw_seq):
                    b = raw_seq[j]

                    if 0xC0 <= b <= 0xCF:
                        cmd = b - 0xC0

                        if seq_offset < len(self.output):
                            self.output[seq_offset] = b
                            seq_offset += 1

                        if j + 1 < len(raw_seq):
                            param = raw_seq[j + 1]

                            if cmd in (0, 1):  # Slide Up/Down
                                speed_hi = 0x00
                                speed_lo = param
                                if seq_offset < len(self.output):
                                    self.output[seq_offset] = speed_hi
                                    seq_offset += 1
                                if seq_offset < len(self.output):
                                    self.output[seq_offset] = speed_lo
                                    seq_offset += 1
                                j += 2
                            elif cmd == 2:  # Vibrato
                                freq = (param >> 4) & 0x0F
                                amp = param & 0x0F
                                sf2_freq = freq
                                sf2_amp = 0x10 - amp if amp > 0 else 0x10
                                if seq_offset < len(self.output):
                                    self.output[seq_offset] = sf2_freq
                                    seq_offset += 1
                                if seq_offset < len(self.output):
                                    self.output[seq_offset] = sf2_amp
                                    seq_offset += 1
                                j += 2
                            elif cmd == 3:  # Portamento
                                speed_hi = 0x00
                                speed_lo = param
                                if seq_offset < len(self.output):
                                    self.output[seq_offset] = speed_hi
                                    seq_offset += 1
                                if seq_offset < len(self.output):
                                    self.output[seq_offset] = speed_lo
                                    seq_offset += 1
                                j += 2
                            elif cmd == 4:  # Set ADSR
                                if hasattr(self.data, 'laxity_instruments') and param < len(self.data.laxity_instruments):
                                    instr = self.data.laxity_instruments[param]
                                    ad = instr.get('ad', 0x09)
                                    sr = instr.get('sr', 0x00)
                                else:
                                    ad = 0x09
                                    sr = 0x00

                                if seq_offset < len(self.output):
                                    self.output[seq_offset] = ad
                                    seq_offset += 1
                                if seq_offset < len(self.output):
                                    self.output[seq_offset] = sr
                                    seq_offset += 1
                                j += 2
                            else:
                                if seq_offset < len(self.output):
                                    self.output[seq_offset] = param
                                    seq_offset += 1
                                j += 2
                        else:
                            j += 1
                    else:
                        if seq_offset < len(self.output):
                            self.output[seq_offset] = b
                            seq_offset += 1
                        j += 1
            else:
                for event in seq:
                    if event.instrument != 0x80 and seq_offset < len(self.output):
                        self.output[seq_offset] = event.instrument
                        seq_offset += 1

                    if event.command != 0x00 and seq_offset < len(self.output):
                        self.output[seq_offset] = event.command
                        seq_offset += 1

                    if seq_offset < len(self.output):
                        self.output[seq_offset] = event.note
                        seq_offset += 1

                    if event.note == 0x7F:
                        break

                if seq_offset > 0 and seq_offset < len(self.output):
                    if self.output[seq_offset - 1] != 0x7F:
                        self.output[seq_offset] = 0x7F
                        seq_offset += 1

            sequences_written += 1

        print(f"    Written {sequences_written} sequences")

    def _inject_orderlists(self):
        """Inject orderlist data into the SF2 file using fixed 256-byte slots"""
        print("  Injecting orderlists...")

        ol_start = self._addr_to_offset(self.driver_info.orderlist_start)
        ptr_lo_offset = self._addr_to_offset(self.driver_info.orderlist_ptrs_lo)
        ptr_hi_offset = self._addr_to_offset(self.driver_info.orderlist_ptrs_hi)

        if ol_start >= len(self.output) or ol_start < 0:
            print(f"    Warning: Invalid orderlist start offset {ol_start}")
            return

        ORDERLIST_SLOT_SIZE = 256
        tracks_written = 0

        for track, orderlist in enumerate(self.data.orderlists[:3]):
            current_addr = self.driver_info.orderlist_start + (track * ORDERLIST_SLOT_SIZE)

            if ptr_lo_offset + track < len(self.output):
                self.output[ptr_lo_offset + track] = current_addr & 0xFF
            if ptr_hi_offset + track < len(self.output):
                self.output[ptr_hi_offset + track] = (current_addr >> 8) & 0xFF

            ol_offset = self._addr_to_offset(current_addr)
            last_trans = -1

            for transposition, seq_idx in orderlist:
                sf2_trans = 0xA0 + (transposition if transposition < 32 else transposition - 256)
                sf2_trans = max(0x80, min(0xBF, sf2_trans))

                if sf2_trans != last_trans:
                    if ol_offset < len(self.output):
                        self.output[ol_offset] = sf2_trans
                        ol_offset += 1
                        last_trans = sf2_trans

                if ol_offset < len(self.output):
                    self.output[ol_offset] = seq_idx & 0x7F
                    ol_offset += 1

            if ol_offset + 1 < len(self.output):
                self.output[ol_offset] = 0xFF
                self.output[ol_offset + 1] = 0x00

            tracks_written += 1

        print(f"    Written {tracks_written} orderlists")

    def _inject_instruments(self):
        """Inject instrument data into the SF2 file using extracted Laxity data"""
        print("  Injecting instruments...")

        if 'Instruments' not in self.driver_info.table_addresses:
            print("    Warning: No instrument table found in driver")
            return

        instr_table = self.driver_info.table_addresses['Instruments']
        instr_addr = instr_table['addr']
        columns = instr_table['columns']
        rows = instr_table['rows']

        wave_addr, wave_entries = find_and_extract_wave_table(self.data.c64_data, self.data.load_address)
        laxity_instruments = extract_laxity_instruments(self.data.c64_data, self.data.load_address, wave_entries)
        self.data.laxity_instruments = laxity_instruments

        print(f"    Extracted {len(laxity_instruments)} instruments from Laxity format")

        if hasattr(self.data, 'siddump_data') and self.data.siddump_data:
            siddump_adsr = set(self.data.siddump_data['adsr_values'])
            laxity_adsr = set((i['ad'], i['sr']) for i in laxity_instruments)
            matches = len(siddump_adsr & laxity_adsr)
            match_rate = matches / len(siddump_adsr) if siddump_adsr else 0
            print(f"    Validation: {match_rate*100:.0f}% of siddump ADSR values found in extraction")

        def waveform_to_wave_index(wave_for_sf2):
            if wave_for_sf2 == 0x21:
                return 0x00
            elif wave_for_sf2 == 0x41:
                return 0x02
            elif wave_for_sf2 == 0x11:
                return 0x04
            elif wave_for_sf2 == 0x81:
                return 0x06
            else:
                return 0x00

        sf2_instruments = []
        is_np20 = columns == 8

        for lax_instr in laxity_instruments:
            wave_ptr = lax_instr.get('wave_ptr', 0)
            pulse_ptr = lax_instr.get('pulse_ptr', 0)
            filter_ptr = lax_instr.get('filter_ptr', 0)

            if wave_ptr == 0:
                wave_ptr = waveform_to_wave_index(lax_instr['wave_for_sf2'])

            if is_np20:
                sf2_instr = [
                    lax_instr['ad'],
                    lax_instr['sr'],
                    wave_ptr,
                    pulse_ptr,
                    filter_ptr,
                    0x00,
                    0x00,
                    0x00
                ]
            else:
                restart = lax_instr.get('restart', 0)
                flags = 0x00
                if restart & 0x80:
                    flags |= 0x80
                if restart & 0x10:
                    flags |= 0x10
                if lax_instr.get('filter_setting', 0):
                    flags |= 0x40

                sf2_instr = [
                    lax_instr['ad'],
                    lax_instr['sr'],
                    flags,
                    filter_ptr,
                    pulse_ptr,
                    wave_ptr
                ]
            sf2_instruments.append(sf2_instr)

        while len(sf2_instruments) < 16:
            if is_np20:
                sf2_instruments.append([0x09, 0xA0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
            else:
                sf2_instruments.append([0x09, 0xA0, 0x00, 0x00, 0x00, 0x00])

        for i, lax_instr in enumerate(laxity_instruments):
            if i < len(sf2_instruments):
                instr = sf2_instruments[i]
                wave_names = {0x00: 'saw', 0x02: 'pulse', 0x04: 'tri', 0x06: 'noise'}
                wave_idx_pos = 2 if is_np20 else 5
                wave_name = wave_names.get(instr[wave_idx_pos], '?')
                name = lax_instr.get('name', f'{i:02d} {wave_name}')
                print(f"      {i}: {name} (AD={instr[0]:02X} SR={instr[1]:02X})")

        instruments_written = 0

        for col in range(columns):
            for row in range(rows):
                offset = self._addr_to_offset(instr_addr) + col * rows + row

                if offset >= len(self.output):
                    continue

                if row < len(sf2_instruments) and col < len(sf2_instruments[row]):
                    self.output[offset] = sf2_instruments[row][col]
                else:
                    self.output[offset] = 0

            if col == 0:
                instruments_written = min(len(sf2_instruments), rows)

        print(f"    Written {instruments_written} instruments")

    def _inject_wave_table(self):
        """Inject wave table data extracted from Laxity SID"""
        print("  Injecting wave table...")

        if 'Wave' not in self.driver_info.table_addresses:
            print("    Warning: No wave table found in driver")
            return

        wave_table = self.driver_info.table_addresses['Wave']
        wave_addr = wave_table['addr']
        columns = wave_table['columns']
        rows = wave_table['rows']

        extracted_waves = extract_laxity_wave_table(self.data.c64_data, self.data.load_address)

        if extracted_waves:
            wave_data = extracted_waves
            print(f"    Extracted {len(extracted_waves)} wave entries from SID")
        else:
            wave_data = [
                (0x00, 0x41), (0x7F, 0x00),
                (0x00, 0x21), (0x7F, 0x02),
                (0x00, 0x11), (0x7F, 0x04),
                (0x00, 0x81), (0x7F, 0x06),
            ]

        if hasattr(self.data, 'siddump_data') and self.data.siddump_data:
            siddump_waveforms = set(self.data.siddump_data['waveforms'])
            existing_waveforms = set(wf for _, wf in wave_data)
            missing = siddump_waveforms - existing_waveforms
            missing = {wf for wf in missing
                      if (wf | 0x01) not in existing_waveforms
                      and wf not in (0x01, 0x09, 0xF0)}
            if missing:
                print(f"    Validation: {len(missing)} waveforms from siddump not in wave table")

        base_offset = self._addr_to_offset(wave_addr)

        for i, (note_offset, waveform) in enumerate(wave_data):
            if i < rows and base_offset + i < len(self.output):
                self.output[base_offset + i] = waveform

        col1_offset = base_offset + rows
        for i, (note_offset, waveform) in enumerate(wave_data):
            if i < rows and col1_offset + i < len(self.output):
                self.output[col1_offset + i] = note_offset

        print(f"    Written {len(wave_data)} wave table entries")

    def _inject_hr_table(self):
        """Inject HR (Hard Restart) table data"""
        print("  Injecting HR table...")

        hr_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'HR' in name:
                hr_table = info
                break

        if not hr_table:
            print("    Warning: No HR table found")
            return

        hr_addr = hr_table['addr']
        rows = hr_table['rows']

        hr_entries = [(0x0F, 0x00)]

        base_offset = self._addr_to_offset(hr_addr)

        for i, (frames, wave) in enumerate(hr_entries):
            if i < rows and base_offset + i < len(self.output):
                self.output[base_offset + i] = frames

        col1_offset = base_offset + rows
        for i, (frames, wave) in enumerate(hr_entries):
            if i < rows and col1_offset + i < len(self.output):
                self.output[col1_offset + i] = wave

        print(f"    Written {len(hr_entries)} HR table entries")

    def _inject_pulse_table(self):
        """Inject pulse table data extracted from Laxity SID"""
        print("  Injecting Pulse table...")

        pulse_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'Pulse' in name or name == 'P':
                pulse_table = info
                break

        if not pulse_table:
            print("    Warning: No Pulse table found in driver")
            return

        pulse_addr = pulse_table['addr']
        columns = pulse_table['columns']
        rows = pulse_table['rows']

        laxity_tables = extract_all_laxity_tables(self.data.c64_data, self.data.load_address)
        pulse_entries = laxity_tables.get('pulse_table', [])

        if not pulse_entries:
            pulse_entries = [(0x08, 0x01, 0x40, 0x00)]

        base_offset = self._addr_to_offset(pulse_addr)

        for col in range(min(columns, 4)):
            for i, entry in enumerate(pulse_entries):
                if i < rows:
                    offset = base_offset + (col * rows) + i
                    if offset < len(self.output) and col < len(entry):
                        self.output[offset] = entry[col]

        print(f"    Written {len(pulse_entries)} Pulse table entries")

    def _inject_filter_table(self):
        """Inject filter table data extracted from Laxity SID"""
        print("  Injecting Filter table...")

        filter_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'Filter' in name or name == 'F':
                filter_table = info
                break

        if not filter_table:
            print("    Warning: No Filter table found in driver")
            return

        filter_addr = filter_table['addr']
        columns = filter_table['columns']
        rows = filter_table['rows']

        laxity_tables = extract_all_laxity_tables(self.data.c64_data, self.data.load_address)
        filter_entries = laxity_tables.get('filter_table', [])

        if not filter_entries:
            filter_entries = [(0x40, 0x01, 0x20, 0x00)]

        base_offset = self._addr_to_offset(filter_addr)

        for col in range(min(columns, 4)):
            for i, entry in enumerate(filter_entries):
                if i < rows:
                    offset = base_offset + (col * rows) + i
                    if offset < len(self.output) and col < len(entry):
                        self.output[offset] = entry[col]

        print(f"    Written {len(filter_entries)} Filter table entries")

    def _inject_init_table(self):
        """Inject Init table data"""
        print("  Injecting Init table...")

        init_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'Init' in name:
                init_table = info
                break

        if not init_table:
            print("    Warning: No Init table found in driver")
            return

        init_addr = init_table['addr']
        columns = init_table['columns']
        rows = init_table['rows']

        init_entries = [0x00, 0x0F, 0x00, 0x01, 0x02]

        base_offset = self._addr_to_offset(init_addr)

        for i, val in enumerate(init_entries):
            if i < rows * columns and base_offset + i < len(self.output):
                self.output[base_offset + i] = val

        print(f"    Written {len(init_entries)} Init table entries")

    def _inject_tempo_table(self):
        """Inject Tempo table data"""
        print("  Injecting Tempo table...")

        tempo_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'Tempo' in name or name == 'T':
                tempo_table = info
                break

        if not tempo_table:
            print("    Warning: No Tempo table found in driver")
            return

        tempo_addr = tempo_table['addr']
        rows = tempo_table['rows']

        tempo = self.data.tempo if hasattr(self.data, 'tempo') else 6

        tempo_entries = [tempo, 0x7F]

        base_offset = self._addr_to_offset(tempo_addr)

        for i, val in enumerate(tempo_entries):
            if i < rows and base_offset + i < len(self.output):
                self.output[base_offset + i] = val

        print(f"    Written tempo: {tempo}")

    def _inject_arp_table(self):
        """Inject Arpeggio table data"""
        print("  Injecting Arp table...")

        arp_table = None
        for name, info in self.driver_info.table_addresses.items():
            if 'Arp' in name or name == 'A':
                arp_table = info
                break

        if not arp_table:
            print("    Warning: No Arp table found in driver")
            return

        arp_addr = arp_table['addr']
        columns = arp_table['columns']
        rows = arp_table['rows']

        arp_entries = [
            (0x00, 0x04, 0x07, 0x7F),
            (0x00, 0x03, 0x07, 0x7F),
            (0x00, 0x0C, 0x7F, 0x00),
        ]

        base_offset = self._addr_to_offset(arp_addr)

        for col in range(min(columns, 4)):
            for i, entry in enumerate(arp_entries):
                if i < rows:
                    offset = base_offset + (col * rows) + i
                    if offset < len(self.output) and col < len(entry):
                        self.output[offset] = entry[col]

        print(f"    Written {len(arp_entries)} Arp table entries")

    def _inject_auxiliary_data(self):
        """Inject auxiliary data with instrument and command names"""
        print("  Injecting auxiliary data (names)...")

        wave_addr, wave_entries = find_and_extract_wave_table(self.data.c64_data, self.data.load_address)
        laxity_instruments = extract_laxity_instruments(self.data.c64_data, self.data.load_address, wave_entries)
        instrument_names = [instr['name'] for instr in laxity_instruments]
        command_names = get_command_names()

        instr_table_id = 1
        cmd_table_id = 0
        if 'Instruments' in self.driver_info.table_addresses:
            instr_table_id = self.driver_info.table_addresses['Instruments']['id']
        if 'Commands' in self.driver_info.table_addresses:
            cmd_table_id = self.driver_info.table_addresses['Commands']['id']

        aux_data = bytearray()

        desc_data = self._build_description_data()
        if desc_data:
            aux_data.append(5)
            aux_data.extend(struct.pack('<H', 1))
            aux_data.extend(struct.pack('<H', len(desc_data)))
            aux_data.extend(desc_data)

        table_text_data = self._build_table_text_data(instrument_names, command_names, instr_table_id, cmd_table_id)

        aux_data.append(4)
        aux_data.extend(struct.pack('<H', 2))
        aux_data.extend(struct.pack('<H', len(table_text_data)))
        aux_data.extend(table_text_data)

        aux_data.append(0)
        aux_data.extend(struct.pack('<H', 0))
        aux_data.extend(struct.pack('<H', 0))

        aux_pointer_offset = 0x0FFB - self.load_address + 2

        if aux_pointer_offset < len(self.output):
            self.output.extend(aux_data)

            if hasattr(self.data, 'header') and self.data.header:
                print(f"    Written metadata: {self.data.header.name} by {self.data.header.author}")
            print(f"    Written {len(instrument_names)} instrument names")
            print(f"    Written {len(command_names)} command names")
        else:
            print("    Warning: Could not find auxiliary data pointer location")

    def _build_description_data(self):
        """Build description data block with song metadata from SID header"""
        if not hasattr(self.data, 'header') or not self.data.header:
            return None

        header = self.data.header
        data = bytearray()

        name = header.name if header.name else ""
        name_bytes = name.encode('latin-1', errors='replace')[:255]
        data.append(len(name_bytes))
        data.extend(name_bytes)

        author = header.author if header.author else ""
        author_bytes = author.encode('latin-1', errors='replace')[:255]
        data.append(len(author_bytes))
        data.extend(author_bytes)

        copyright_str = header.copyright if header.copyright else ""
        copyright_bytes = copyright_str.encode('latin-1', errors='replace')[:255]
        data.append(len(copyright_bytes))
        data.extend(copyright_bytes)

        return data

    def _build_table_text_data(self, instrument_names, command_names, instr_table_id=1, cmd_table_id=0):
        """Build the table text data block"""
        data = bytearray()

        num_tables = 2
        data.append(num_tables)

        data.extend(struct.pack('<i', instr_table_id))
        data.extend(struct.pack('<H', 1))
        data.extend(struct.pack('<H', len(instrument_names)))
        for name in instrument_names:
            name_bytes = name.encode('latin-1', errors='replace')[:255]
            data.append(len(name_bytes))
            data.extend(name_bytes)

        data.extend(struct.pack('<i', cmd_table_id))
        data.extend(struct.pack('<H', 1))
        data.extend(struct.pack('<H', len(command_names)))
        for name in command_names:
            name_bytes = name.encode('latin-1', errors='replace')[:255]
            data.append(len(name_bytes))
            data.extend(name_bytes)

        return data

    def _print_extraction_summary(self):
        """Print summary of extracted data"""
        if self.data.sequences:
            print(f"\n  Extracted {len(self.data.sequences)} sequences:")
            for i, seq in enumerate(self.data.sequences[:5]):
                print(f"    Sequence {i}: {len(seq)} events")
            if len(self.data.sequences) > 5:
                print(f"    ... and {len(self.data.sequences) - 5} more")

        if self.data.instruments:
            print(f"\n  Extracted {len(self.data.instruments)} instruments")

        if self.data.orderlists:
            print(f"\n  Created {len(self.data.orderlists)} orderlists")

        if hasattr(self.data, 'raw_sequences') and self.data.raw_sequences:
            from .sequence_extraction import analyze_sequence_commands
            cmd_analysis = analyze_sequence_commands(self.data.raw_sequences)
            if cmd_analysis['commands_used']:
                print(f"\n  Commands used in sequences:")
                cmd_names = get_command_names()
                for cmd in sorted(cmd_analysis['commands_used']):
                    count = cmd_analysis['command_counts'].get(cmd, 0)
                    name = cmd_names[cmd] if cmd < len(cmd_names) else f"Cmd {cmd}"
                    print(f"    {cmd:2d}: {name} ({count}x)")

    def _find_driver(self) -> Optional[str]:
        """Find SF2 driver file"""
        search_paths = [
            'sf2driver16_01.prg',
            'drivers/sf2driver16_01.prg',
            '../drivers/sf2driver16_01.prg',
        ]

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        for path in search_paths:
            full_path = os.path.join(base_dir, path)
            if os.path.exists(full_path):
                return full_path

        return None

    def _create_minimal_structure(self):
        """Create a minimal SF2-like structure"""
        self.output = bytearray(8192)

    def _inject_music_data(self):
        """Inject extracted music data into the SF2 structure"""
        print("Note: Music data injection is a placeholder")
        print("The output file structure may need manual refinement")
