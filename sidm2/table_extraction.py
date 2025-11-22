"""
Table extraction functions for Laxity SID files.
"""

from collections import Counter
from typing import Dict, List, Optional, Tuple

from .constants import (
    OPCODE_BYTES, COMMON_AD_VALUES, COMMON_SR_VALUES,
    VALID_FILTER_SETTINGS, VALID_RESTART_OPTIONS,
    SEARCH_START_OFFSET, SEARCH_END_OFFSET,
    INSTRUMENT_SCORE_THRESHOLD, MIN_VALID_INSTRUMENTS,
    VALID_WAVEFORMS, WAVE_TABLE_WAVEFORMS,
    WAVE_TABLE_ADDR_MIN, WAVE_TABLE_ADDR_MAX,
    PULSE_TABLE_ADDR_MIN, PULSE_TABLE_ADDR_MAX,
)


def find_sid_register_tables(data: bytes, load_addr: int) -> Dict[int, int]:
    """
    Find table addresses for each SID register by tracing
    STA $D4xx,Y instructions back to their LDA source.

    Args:
        data: C64 program data
        load_addr: Memory load address

    Returns:
        Dict mapping SID register offset to table address
    """
    tables: Dict[int, int] = {}

    for i in range(len(data) - 3):
        # STA $D4xx,Y (99 lo hi)
        if data[i] == 0x99:
            addr = data[i + 1] | (data[i + 2] << 8)
            if not (0xD400 <= addr <= 0xD418):
                continue

            reg = addr - 0xD400

            # Look backwards for LDA table,X
            for j in range(1, 30):
                if i - j < 0:
                    break

                # LDA $xxxx,X (BD lo hi)
                if data[i - j] == 0xBD:
                    table = data[i - j + 1] | (data[i - j + 2] << 8)
                    tables[reg] = table
                    break

    return tables


def find_table_addresses_from_player(data: bytes, load_addr: int) -> Dict[str, int]:
    """
    Find table addresses by tracing the player code.

    Args:
        data: C64 program data
        load_addr: Memory load address

    Returns:
        Dict with keys 'pulse', 'filter', 'wave' mapping to addresses
    """
    tables: Dict[str, int] = {}

    pulse_candidates = []
    filter_candidates = []
    wave_candidates = []

    for i in range(len(data) - 5):
        # LDA absolute,X (BD) or LDA absolute,Y (B9)
        if data[i] in (0xBD, 0xB9):
            addr = data[i + 1] | (data[i + 2] << 8)

            # Check if in reasonable range for tables
            if load_addr <= addr < load_addr + len(data):
                # Look ahead for STA to SID
                for j in range(3, 20):
                    if i + j + 2 < len(data):
                        if data[i + j] in (0x8D, 0x99, 0x9D):  # STA variants
                            sta_addr = data[i + j + 1] | (data[i + j + 2] << 8)

                            # Pulse registers $D402, $D403
                            if sta_addr in (0xD402, 0xD403, 0xD409, 0xD40A, 0xD410, 0xD411):
                                pulse_candidates.append(addr)
                                break
                            # Filter registers $D415, $D416, $D417
                            elif sta_addr in (0xD415, 0xD416, 0xD417):
                                filter_candidates.append(addr)
                                break
                            # Waveform register $D404
                            elif sta_addr in (0xD404, 0xD40B, 0xD412):
                                wave_candidates.append(addr)
                                break

    # Use most common candidates
    if pulse_candidates:
        tables['pulse'] = Counter(pulse_candidates).most_common(1)[0][0]

    if filter_candidates:
        tables['filter'] = Counter(filter_candidates).most_common(1)[0][0]

    if wave_candidates:
        tables['wave'] = Counter(wave_candidates).most_common(1)[0][0]

    return tables


def find_instrument_table(data: bytes, load_addr: int, verbose: bool = False) -> Optional[int]:
    """
    Find the instrument table in Laxity format.
    Instruments are 8 bytes each, typically in $1900-$1B00 range.

    Args:
        data: C64 program data
        load_addr: Memory load address
        verbose: Enable verbose output

    Returns:
        Address of instrument table, or None if not found
    """
    best_addr = 0
    best_score = 0
    candidates = []

    search_start = SEARCH_START_OFFSET
    search_end = min(len(data) - 128, SEARCH_END_OFFSET)

    for offset in range(search_start, search_end):
        score = 0
        valid_instruments = 0

        # Check up to 8 consecutive potential instruments
        for i in range(8):
            off = offset + (i * 8)
            if off + 8 > len(data):
                break

            ad = data[off]
            sr = data[off + 1]
            restart = data[off + 2]
            filter_set = data[off + 3]
            filter_ptr = data[off + 4]
            pulse_ptr = data[off + 5]
            pulse_prop = data[off + 6]
            wave_ptr = data[off + 7]

            # Score based on typical instrument characteristics
            instr_score = 0

            # Avoid values that look like 6502 opcodes
            if ad not in OPCODE_BYTES and sr not in OPCODE_BYTES:
                instr_score += 2

            # Realistic ADSR values
            attack = (ad >> 4) & 0x0F
            decay = ad & 0x0F

            if attack <= 0x0F and decay <= 0x0F:
                instr_score += 1

            # Strong penalty for AD=00 SR=00
            if ad == 0x00 and sr == 0x00:
                instr_score -= 8
            elif i == 0 and ad == 0x00:
                instr_score -= 3

            # Bonus for common AD values
            if ad in COMMON_AD_VALUES:
                instr_score += 3
            elif ad == 0x00:
                instr_score += 1
            elif ad < 0x20:
                instr_score += 1
            else:
                instr_score -= 2

            # SR scoring
            sustain = (sr >> 4) & 0x0F
            if sustain >= 0x08:
                instr_score += 2
            if sr in COMMON_SR_VALUES:
                instr_score += 2

            # Wave pointer should be small
            if wave_ptr < 32:
                instr_score += 3
            elif wave_ptr < 64:
                instr_score += 1

            # Filter setting validation
            if filter_set in VALID_FILTER_SETTINGS:
                instr_score += 2

            # Pointer validation
            if pulse_ptr < 64 and filter_ptr < 64:
                instr_score += 2

            # Restart options validation
            if restart in VALID_RESTART_OPTIONS:
                instr_score += 2
            elif restart < 32 or (restart & 0xF0) in (0x40, 0x80, 0x90):
                instr_score += 1

            # Pulse property validation
            if pulse_prop < 8:
                instr_score += 1

            if instr_score >= INSTRUMENT_SCORE_THRESHOLD:
                valid_instruments += 1
                score += instr_score

        # Require minimum valid instruments
        if valid_instruments >= MIN_VALID_INSTRUMENTS:
            addr = load_addr + offset
            if verbose:
                candidates.append((addr, score, valid_instruments))
            if score > best_score:
                best_score = score
                best_addr = addr

    if verbose:
        candidates.sort(key=lambda x: x[1], reverse=True)
        debug_info = {
            'best_addr': best_addr,
            'best_score': best_score,
            'candidates': candidates[:5]
        }
        return best_addr if best_addr else None, debug_info

    return best_addr if best_addr else None


def find_wave_table_from_player_code(data: bytes, load_addr: int) -> Optional[int]:
    """
    Find wave table addresses by analyzing player code.
    Returns (note_addr, wave_addr) or (None, None) if not found.
    """
    # Search for LDA absolute,Y (opcode B9) instructions
    lda_refs = []
    for i in range(min(len(data) - 2, 0x900)):
        if data[i] == 0xB9:  # LDA absolute,Y
            lo = data[i + 1]
            hi = data[i + 2]
            addr = hi * 256 + lo
            if WAVE_TABLE_ADDR_MIN <= addr <= WAVE_TABLE_ADDR_MAX:
                lda_refs.append((load_addr + i, addr))

    # Group references by address
    addr_counts = {}
    for code_addr, table_addr in lda_refs:
        addr_counts[table_addr] = addr_counts.get(table_addr, 0) + 1

    sorted_addrs = sorted(addr_counts.items(), key=lambda x: x[1], reverse=True)

    if len(sorted_addrs) >= 2:
        all_addrs = [addr for addr, count in sorted_addrs]

        best_pair = None
        best_wave_count = 0

        for i, addr1 in enumerate(all_addrs):
            for addr2 in all_addrs[i+1:]:
                diff = addr2 - addr1
                if 0x20 <= diff <= 0x80:
                    off1 = addr1 - load_addr
                    off2 = addr2 - load_addr

                    if off1 < 0 or off2 < 0 or off2 >= len(data):
                        continue

                    # Check if first array has valid note offsets
                    note_score = 0
                    for j in range(min(16, len(data) - off1)):
                        note_val = data[off1 + j]
                        if note_val in (0x7E, 0x7F):
                            note_score += 3
                        elif 0x80 <= note_val <= 0xDF:
                            note_score += 2
                        elif note_val <= 0x20:
                            note_score += 1

                    # Check if second array has valid waveforms
                    valid_waves = {0x01, 0x10, 0x11, 0x20, 0x21, 0x40, 0x41, 0x80, 0x81, 0xF0}
                    wave_count = 0
                    for j in range(min(16, len(data) - off2)):
                        if data[off2 + j] in valid_waves:
                            wave_count += 1

                    total_score = wave_count + note_score
                    if wave_count >= 4 and note_score >= 4 and total_score > best_wave_count:
                        best_wave_count = total_score
                        best_pair = (addr1, addr2)

        if best_pair:
            return best_pair

    return (None, None)


def find_and_extract_wave_table(data: bytes, load_addr: int, verbose: bool = False, siddump_waveforms: Optional[List[int]] = None) -> Tuple[Optional[int], List[Tuple[int, int]]]:
    """
    Find and extract wave table from Laxity SID.
    Returns (address, entries) where entries is list of (waveform, note_offset).

    SF2 Factory II wave table format:
    - Column 0: Waveform ($11=tri, $21=saw, $41=pulse, $81=noise) or $7F for jump
    - Column 1: Note offset or jump target

    Special commands:
    - $7F xx = Jump to entry xx
    - $7E = Hold/stop
    """
    # First try to find wave table by analyzing player code
    note_addr, wave_addr = find_wave_table_from_player_code(data, load_addr)

    if note_addr and wave_addr:
        note_off = note_addr - load_addr
        wave_off = wave_addr - load_addr

        entries = []
        for i in range(64):
            if note_off + i >= len(data) or wave_off + i >= len(data):
                break
            note_val = data[note_off + i]
            wave_val = data[wave_off + i]

            if note_val == 0x7F and wave_val == 0:
                entries.append((note_val, wave_val))
                break

            # SF2 format: (first_col, second_col)
            # For $7F commands: first_col=$7F, second_col=target
            # For normal entries: first_col=waveform, second_col=note
            if note_val == 0x7F:
                entries.append((note_val, wave_val))  # Jump command
            else:
                entries.append((wave_val, note_val))  # Swap: waveform first, note second

            if i > 8 and wave_val not in WAVE_TABLE_WAVEFORMS:
                break

        if entries and len(entries) >= 4:
            if verbose:
                return (note_addr, entries, {'note_addr': note_addr, 'wave_addr': wave_addr})
            return (note_addr, entries)

    # Fall back to pattern matching
    valid_waveforms = VALID_WAVEFORMS.copy()
    if siddump_waveforms:
        valid_waveforms.update(siddump_waveforms)

    best_addr = 0
    best_entries = []
    best_score = 0
    candidates = []

    for start in range(0x600, min(len(data) - 64, 0x1600)):
        entries = []
        pos = start
        score = 0

        while pos < min(start + 256, len(data) - 1):
            note_offset = data[pos]
            waveform = data[pos + 1] if pos + 1 < len(data) else 0

            if note_offset == 0x7F:
                entries.append((note_offset, waveform))
                score += 5
                break
            elif note_offset == 0x7E:
                entries.append((note_offset, waveform))
                score += 5
                break
            elif waveform in valid_waveforms:
                entries.append((note_offset, waveform))
                score += 3
                pos += 2
            else:
                break

        has_terminator = len(entries) >= 2 and entries[-1][0] in (0x7E, 0x7F)

        if len(entries) < 2:
            continue

        waveform_set = {wf for _, wf in entries}

        if has_terminator:
            score += len(entries) * 2

        if len(waveform_set) == 1 and len(entries) > 8:
            penalty = min(len(entries) * 2, 150)
            score -= penalty

        variety_bonus = len(waveform_set) * 5
        score += variety_bonus

        if siddump_waveforms:
            matched = waveform_set & siddump_waveforms
            score += len(matched) * 10
            match_ratio = len(matched) / len(siddump_waveforms) if siddump_waveforms else 0
            if match_ratio >= 0.5:
                score += 20
            if match_ratio >= 0.75:
                score += 30

        if verbose:
            waveform_types = sorted(waveform_set)
            addr = load_addr + start
            candidates.append((addr, score, len(entries), waveform_types))

        if score > best_score or (score == best_score and score > 0):
            if score == best_score and best_entries:
                current_variety = len({wf for _, wf in entries})
                best_variety = len({wf for _, wf in best_entries})
                if current_variety <= best_variety:
                    continue

            best_score = score
            best_addr = load_addr + start
            best_entries = entries

    if verbose:
        candidates.sort(key=lambda x: x[1], reverse=True)
        debug_info = {
            'best_addr': best_addr,
            'best_score': best_score,
            'candidates': candidates[:5]
        }
        return best_addr, best_entries, debug_info

    return best_addr, best_entries


def find_and_extract_pulse_table(data: bytes, load_addr: int, pulse_ptrs: Optional[set] = None, avoid_addr: int = 0) -> Tuple[Optional[int], List[bytes]]:
    """
    Find and extract pulse table from Laxity SID.

    Pulse table format (4 bytes per entry, Y-indexed with stride 4):
    - Byte 0: Initial pulse value (hi nibble -> pulse lo, lo nibble -> pulse hi), $FF = keep
    - Byte 1: Add/subtract value per frame
    - Byte 2: Duration (bits 0-6) + direction (bit 7: 0=add, 1=subtract)
    - Byte 3: Next entry index (pre-multiplied by 4)

    Returns (address, entries) where entries is list of 4-byte tuples.
    """
    # First try to find pulse table by analyzing player code references
    # Look for LDA $xxxx,Y patterns in the typical pulse table address range
    pulse_refs = []
    for i in range(min(len(data) - 2, 0x900)):
        if data[i] == 0xB9:  # LDA absolute,Y
            lo = data[i + 1]
            hi = data[i + 2]
            addr = hi * 256 + lo
            if PULSE_TABLE_ADDR_MIN <= addr <= PULSE_TABLE_ADDR_MAX:
                pulse_refs.append(addr)

    if pulse_refs:
        # Use minimum address as base (pulse table columns are at +0, +1, +2, +3)
        base_addr = min(pulse_refs)
        base_off = base_addr - load_addr

        entries = []
        for i in range(16):
            off = base_off + i * 4
            if off + 3 >= len(data):
                break

            val = data[off]
            cnt = data[off + 1]
            dur = data[off + 2]
            nxt = data[off + 3]

            # Validate entry - next index should be divisible by 4 and reasonable
            # or loop back to a previous entry
            if nxt != 0 and (nxt % 4 != 0 or nxt > 64):
                # Allow if it's looping back
                if nxt not in [j * 4 for j in range(i + 1)]:
                    break

            entries.append((val, cnt, dur, nxt))

            # Stop if we've found a reasonable number of entries
            if i >= 2 and nxt == i * 4:  # Self-loop
                break

        if entries:
            return (base_addr, entries)

    # Fallback to pattern matching with improved scoring
    best_addr = 0
    best_entries = []
    best_score = 0

    for start in range(0x600, min(len(data) - 64, 0x1800)):
        addr = load_addr + start
        if avoid_addr and abs(addr - avoid_addr) < 128:
            continue

        entries = []
        pos = start
        score = 0
        seen_indices = set()

        for entry_idx in range(32):
            if pos + 4 > len(data):
                break

            pulse_val = data[pos]
            count = data[pos + 1]
            duration = data[pos + 2]
            next_idx = data[pos + 3]

            # Score based on pulse table characteristics
            # Pulse value can be anything (including $FF for keep current)
            if pulse_val == 0xFF:
                score += 2  # Common "keep current" value
            elif pulse_val <= 0x0F:
                score += 1  # Small initial values common

            # Count (add/sub value) typically $00-$80
            if count <= 0x80:
                score += 1

            # Duration (bits 0-6) should be reasonable, bit 7 is direction
            dur_clean = duration & 0x7F
            if 0 < dur_clean <= 0x40:
                score += 2
            elif dur_clean == 0:
                score += 1  # Immediate

            # Next index should be divisible by 4 (Y*4 indexing)
            if next_idx % 4 == 0 and next_idx < 128:
                score += 3
            elif next_idx == 0:
                score += 2  # Loop to start

            entries.append((pulse_val, count, duration, next_idx))

            # Check for loop back (common pattern)
            entry_y = entry_idx * 4
            if next_idx in seen_indices or next_idx == entry_y:
                score += 5  # Bonus for valid loop
                break
            seen_indices.add(entry_y)

            pos += 4

        if score > best_score and len(entries) >= 2:
            best_score = score
            best_addr = addr
            best_entries = entries

    return best_addr, best_entries


def find_and_extract_filter_table(data: bytes, load_addr: int, filter_ptrs: Optional[set] = None, avoid_addr: int = 0) -> Tuple[Optional[int], List[bytes]]:
    """
    Find and extract filter table from Laxity SID.
    Returns (address, entries) where entries is list of 4-byte tuples.
    """
    best_addr = 0
    best_entries = []
    best_score = 0

    for start in range(0x600, min(len(data) - 64, 0x1800)):
        addr = load_addr + start
        if avoid_addr and abs(addr - avoid_addr) < 128:
            continue

        entries = []
        pos = start
        score = 0
        seen_indices = set()

        for entry_idx in range(32):
            if pos + 4 > len(data):
                break

            filter_val = data[pos]
            count = data[pos + 1]
            duration = data[pos + 2]
            next_idx = data[pos + 3]

            if 0x10 <= filter_val <= 0xF0:
                score += 2

            if count > 0 and count < 128:
                score += 1
            if duration > 0 and duration < 128:
                score += 1
            if next_idx < 32:
                score += 1

            entries.append((filter_val, count, duration, next_idx))

            if next_idx in seen_indices or next_idx == entry_idx:
                score += 3
                break
            seen_indices.add(entry_idx)

            pos += 4

        if score > best_score and len(entries) >= 2:
            best_score = score
            best_addr = addr
            best_entries = entries

    return best_addr, best_entries


def extract_all_laxity_tables(data: bytes, load_addr: int) -> Dict[str, any]:
    """
    Extract ALL tables from Laxity SID file.
    Returns dict with instruments, wave_table, pulse_table, filter_table.
    """
    result = {
        'instruments': [],
        'wave_table': [],
        'pulse_table': [],
        'filter_table': [],
        'commands': [],
        'instr_addr': 0,
        'wave_addr': 0,
        'pulse_addr': 0,
        'filter_addr': 0,
    }

    # Find instrument table
    instr_addr = find_instrument_table(data, load_addr)

    if instr_addr:
        result['instr_addr'] = instr_addr
        instr_offset = instr_addr - load_addr

        for i in range(32):
            off = instr_offset + (i * 8)
            if off + 8 <= len(data):
                instr = data[off:off + 8]
                ad = instr[0]
                sr = instr[1]
                if ad == 0 and sr == 0 and instr[7] == 0 and i > 0:
                    break
                result['instruments'].append(bytes(instr))
            else:
                break

    # Find table addresses by tracing player code
    table_addrs = find_table_addresses_from_player(data, load_addr)

    # Extract wave table
    if 'wave' in table_addrs:
        wave_addr = table_addrs['wave']
        result['wave_addr'] = wave_addr
        wave_offset = wave_addr - load_addr

        wave_entries = []
        for i in range(64):
            off = wave_offset + (i * 2)
            if off + 2 <= len(data):
                note_offset = data[off]
                waveform = data[off + 1]
                wave_entries.append((note_offset, waveform))
                if note_offset == 0x7E or (note_offset == 0x7F and waveform <= i):
                    break
        result['wave_table'] = wave_entries
    else:
        wave_addr, wave_entries = find_and_extract_wave_table(data, load_addr)
        if wave_addr:
            result['wave_addr'] = wave_addr
            result['wave_table'] = wave_entries

    # Extract pulse table
    pulse_addr, pulse_entries = find_and_extract_pulse_table(data, load_addr)
    if pulse_addr and pulse_entries:
        result['pulse_addr'] = pulse_addr
        result['pulse_table'] = pulse_entries
    elif 'pulse' in table_addrs:
        pulse_addr = table_addrs['pulse']
        result['pulse_addr'] = pulse_addr
        pulse_offset = pulse_addr - load_addr

        pulse_entries = []
        for i in range(16):
            off = pulse_offset + (i * 4)
            if off + 4 <= len(data):
                entry = (data[off], data[off+1], data[off+2], data[off+3])
                pulse_entries.append(entry)
                if entry[3] == i:
                    break
        result['pulse_table'] = pulse_entries
    else:
        result['pulse_table'] = [(0x08, 0x01, 0x40, 0x00)]

    # Extract filter table
    filter_addr = None

    if result['instruments']:
        filter_ptrs = set()
        for instr in result['instruments']:
            if len(instr) >= 5:
                fptr = instr[4]
                if fptr > 0 and fptr < 32:
                    filter_ptrs.add(fptr)

        if filter_ptrs and result['instr_addr']:
            for offset_dist in [0x100, 0x180, 0x200, 0x80]:
                test_addr = result['instr_addr'] - offset_dist
                test_offset = test_addr - load_addr
                if test_offset >= 0 and test_offset + 64 <= len(data):
                    first_val = data[test_offset]
                    if 0x10 <= first_val <= 0xF0 or first_val == 0x00:
                        filter_addr = test_addr
                        break

    if not filter_addr and 'filter' in table_addrs:
        filter_addr = table_addrs['filter']

    if not filter_addr:
        pulse_addr = result.get('pulse_addr', 0)
        found_addr, found_entries = find_and_extract_filter_table(data, load_addr, avoid_addr=pulse_addr)
        if found_addr:
            filter_addr = found_addr
            result['filter_addr'] = filter_addr
            result['filter_table'] = found_entries

    if filter_addr and 'filter_table' not in result:
        result['filter_addr'] = filter_addr
        filter_offset = filter_addr - load_addr

        filter_entries = []
        for i in range(16):
            off = filter_offset + (i * 4)
            if off + 4 <= len(data):
                entry = (data[off], data[off+1], data[off+2], data[off+3])
                filter_entries.append(entry)
                if entry[3] == i:
                    break
        result['filter_table'] = filter_entries

    if 'filter_table' not in result or not result['filter_table']:
        result['filter_table'] = [(0x40, 0x01, 0x20, 0x00)]

    return result
