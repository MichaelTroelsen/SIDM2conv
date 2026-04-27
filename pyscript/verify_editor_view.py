"""Faithful Python port of SIDFactoryII DataSourceSequence::Unpack
(datasource_sequence.cpp:197-267) plus Block 5 / orderlist parsing,
to verify what the editor will see when it loads our SF2 files —
without launching the GUI.

Usage: python verify_editor_view.py <path.sf2>
"""
import struct
import sys


def parse_sf2_block5(data, load_addr):
    """Walk the SF2 header chain, return Block 5 (MusicData) parameters."""
    if data[2:4] != b'\x37\x13':
        raise SystemExit("not a valid SF2 file (missing 0x1337 magic)")
    off = 4
    while off + 2 < len(data):
        block_id = data[off]
        if block_id == 0xFF:
            break
        block_size = data[off + 1]
        body = data[off + 2:off + 2 + block_size]
        if block_id == 5:
            # Layout per sf2_header_generator.create_music_data_block (18 bytes):
            #   track_count(1) ol_ptr_lo(2) ol_ptr_hi(2)
            #   seq_count(1)   seq_ptr_lo(2) seq_ptr_hi(2)
            #   ol_size(2)     ol_track1_addr(2)
            #   seq_size(2)    seq00_addr(2)
            r = lambda o, n: int.from_bytes(body[o:o+n], 'little')
            return {
                'track_count':    r(0, 1),
                'ol_ptr_lo_addr': r(1, 2),
                'ol_ptr_hi_addr': r(3, 2),
                'seq_count':      r(5, 1),
                'seq_ptr_lo_addr': r(6, 2),
                'seq_ptr_hi_addr': r(8, 2),
                'ol_size':        r(10, 2),
                'ol_track1_addr': r(12, 2),
                'seq_size':       r(14, 2),
                'seq00_addr':     r(16, 2),
            }
        off += 2 + block_size
    raise SystemExit("Block 5 (MusicData) not found")


def addr_to_offset(addr, load_addr):
    return 2 + (addr - load_addr)


def unpack_sequence(seq_bytes):
    """Direct port of DataSourceSequence::Unpack (datasource_sequence.cpp:197-267).

    Returns list of events: each is a dict with command/instrument/note (and note
    is one of: 0x00=gate-off, 0x7E=tie/sustain, 0x01-0x6F=pitch, where 0x01=C-0).
    """
    events = []
    duration = 0
    tie_note = False
    i = 0
    while i < 0x100:
        value = seq_bytes[i]; i += 1
        if value == 0x7F:
            return events, i  # i is packed size

        ev = {'command': 0x80, 'instrument': 0x80, 'note': None}
        if value >= 0xC0:
            ev['command'] = value
            value = seq_bytes[i]; i += 1
        if value >= 0xA0:
            ev['instrument'] = value
            value = seq_bytes[i]; i += 1
        if value >= 0x80:
            duration = value & 0x0F
            tie_note = (value & 0x10) != 0
            if tie_note:
                ev['instrument'] = 0x90
            value = seq_bytes[i]; i += 1
        assert value < 0x80, f"editor would assert here on note byte {value:#x}"
        ev['note'] = value
        events.append(ev)
        # Duration ticks become tie or gate-off events
        for _ in range(duration):
            tail = {'command': 0x80, 'instrument': 0x80,
                    'note': 0x7E if value != 0x00 else 0x00}
            events.append(tail)
    return events, i


NOTE_NAMES = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']
def note_str(n):
    if n is None: return '???'
    if n == 0x00: return '--- '   # gate off
    if n == 0x7E: return '... '   # tie
    pitch = n - 1                 # SF2: 0x01 = C-0
    return f"{NOTE_NAMES[pitch % 12]}{pitch // 12}"


def main(path):
    data = open(path, 'rb').read()
    load_addr = struct.unpack('<H', data[0:2])[0]
    print(f"=== {path} ===")
    print(f"Load: ${load_addr:04X}, file size: {len(data)} bytes")

    b5 = parse_sf2_block5(data, load_addr)
    print(f"Block 5 (MusicData): track_count={b5['track_count']}, seq_count={b5['seq_count']}")
    print(f"  ol_track1=${b5['ol_track1_addr']:04X} (size ${b5['ol_size']:02X})")
    print(f"  seq00    =${b5['seq00_addr']:04X} (size ${b5['seq_size']:02X})")

    # Read each voice's orderlist, find the (single) referenced pattern,
    # unpack it, dump events.
    for v in range(b5['track_count']):
        ol_addr = b5['ol_track1_addr'] + v * b5['ol_size']
        ol_off = addr_to_offset(ol_addr, load_addr)
        ol_bytes = data[ol_off:ol_off + b5['ol_size']]
        # Find first sequence index (orderlist is [idx, 0xFE, 0xFF...])
        seq_idx = ol_bytes[0]
        print(f"\nVoice {v} orderlist @ ${ol_addr:04X}: "
              f"first 4 bytes = {ol_bytes[:4].hex()} -> plays seq #{seq_idx}")

        seq_addr = b5['seq00_addr'] + seq_idx * b5['seq_size']
        seq_off = addr_to_offset(seq_addr, load_addr)
        seq_bytes = data[seq_off:seq_off + b5['seq_size']]

        events, packed_size = unpack_sequence(seq_bytes)
        print(f"  Sequence #{seq_idx} @ ${seq_addr:04X}, packed={packed_size}B, "
              f"unpacked={len(events)} ticks")
        # Print only the keyframes (where instrument or command changes)
        last_inst, last_cmd = None, None
        keyframes = []
        for tick, e in enumerate(events):
            if (e['instrument'] != 0x80 and e['instrument'] != last_inst) or \
               (e['command'] != 0x80 and e['command'] != last_cmd) or \
               (e['note'] not in (0x00, 0x7E)):
                keyframes.append((tick, e))
                if e['instrument'] != 0x80: last_inst = e['instrument']
                if e['command']    != 0x80: last_cmd  = e['command']
        for tick, e in keyframes[:30]:
            cmd_s   = f"cmd={e['command']:02X}"   if e['command']    != 0x80 else "      "
            inst_s  = f"inst={e['instrument']:02X}" if e['instrument'] != 0x80 else "        "
            print(f"    t={tick:3d}  {note_str(e['note']):4s}  {inst_s} {cmd_s}")
        if len(keyframes) > 30:
            print(f"    ... ({len(keyframes) - 30} more keyframes)")


if __name__ == '__main__':
    for p in sys.argv[1:]:
        main(p)
