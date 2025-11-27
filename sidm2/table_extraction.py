"""
Table extraction functions for Laxity SID files.
"""

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple, Union

from .constants import (
    OPCODE_BYTES, COMMON_AD_VALUES, COMMON_SR_VALUES,
    VALID_FILTER_SETTINGS, VALID_RESTART_OPTIONS,
    SEARCH_START_OFFSET, SEARCH_END_OFFSET,
    INSTRUMENT_SCORE_THRESHOLD, MIN_VALID_INSTRUMENTS,
    VALID_WAVEFORMS, WAVE_TABLE_WAVEFORMS,
    WAVE_TABLE_ADDR_MIN, WAVE_TABLE_ADDR_MAX,
    PULSE_TABLE_ADDR_MIN, PULSE_TABLE_ADDR_MAX,
)
from .exceptions import TableExtractionError


def get_valid_wave_entry_points(wave_table: List[Tuple[int, int]]) -> set:
    """
    Get valid entry points in a wave table.

    Wave pointers from instruments should point to:
    - Index 0 (always valid)
    - Index immediately after a $7F xx (jump) command

    Args:
        wave_table: List of (col0, col1) tuples from wave table
                   For normal entries: col0=waveform, col1=note_offset
                   For jump commands: col0=$7F, col1=target_index

    Returns:
        Set of valid entry point indices
    """
    valid_points = {0}  # Index 0 is always valid

    for idx, entry in enumerate(wave_table):
        col0 = entry[0]
        # If this entry is a jump command ($7F), the next entry is a valid start point
        if col0 == 0x7F and idx + 1 < len(wave_table):
            valid_points.add(idx + 1)

    return valid_points


def validate_wave_pointer(wave_ptr: int, wave_table: List[Tuple[int, int]]) -> bool:
    """
    Validate if a wave pointer points to a valid entry point.

    Args:
        wave_ptr: Wave pointer value from instrument
        wave_table: List of wave table entries

    Returns:
        True if wave_ptr is a valid entry point
    """
    if not wave_table:
        return wave_ptr == 0

    valid_points = get_valid_wave_entry_points(wave_table)
    return wave_ptr in valid_points


def find_sid_register_tables(data: bytes, load_addr: int) -> Dict[int, int]:
    """
    Find table addresses for each SID register by tracing
    STA $D4xx,Y instructions back to their LDA source.

    Args:
        data: C64 program data
        load_addr: Memory load address

    Returns:
        Dict mapping SID register offset to table address

    Raises:
        TableExtractionError: If data is invalid or too small
    """
    if not data or len(data) < 4:
        raise TableExtractionError(f"Data too small for table extraction: {len(data) if data else 0} bytes")

    tables: Dict[int, int] = {}

    try:
        for i in range(len(data) - 3):
            # STA $D4xx,Y (99 lo hi)
            if data[i] == 0x99:
                if i + 2 >= len(data):
                    continue

                addr = data[i + 1] | (data[i + 2] << 8)
                if not (0xD400 <= addr <= 0xD418):
                    continue

                reg = addr - 0xD400

                # Look backwards for LDA table,X
                for j in range(1, 30):
                    if i - j < 0:
                        break

                    # LDA $xxxx,X (BD lo hi)
                    if i - j + 2 < len(data) and data[i - j] == 0xBD:
                        table = data[i - j + 1] | (data[i - j + 2] << 8)
                        tables[reg] = table
                        break
    except IndexError as e:
        raise TableExtractionError(f"Index error while searching for SID register tables: {e}")

    return tables


def find_table_addresses_from_player(data: bytes, load_addr: int) -> Dict[str, int]:
    """
    Find table addresses by tracing the player code.

    Args:
        data: C64 program data
        load_addr: Memory load address

    Returns:
        Dict with keys 'pulse', 'filter', 'wave' mapping to addresses

    Raises:
        TableExtractionError: If data is invalid or too small
    """
    if not data or len(data) < 6:
        raise TableExtractionError(f"Data too small for player code analysis: {len(data) if data else 0} bytes")

    tables: Dict[str, int] = {}

    pulse_candidates = []
    filter_candidates = []
    wave_candidates = []

    try:
        for i in range(len(data) - 5):
            # LDA absolute,X (BD) or LDA absolute,Y (B9)
            if data[i] in (0xBD, 0xB9):
                if i + 2 >= len(data):
                    continue

                addr = data[i + 1] | (data[i + 2] << 8)

                # Check if in reasonable range for tables
                if load_addr <= addr < load_addr + len(data):
                    # Look ahead for STA to SID
                    for j in range(3, 20):
                        if i + j + 2 >= len(data):
                            break

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
    except IndexError as e:
        raise TableExtractionError(f"Index error while analyzing player code: {e}")

    # Use most common candidates
    try:
        if pulse_candidates:
            tables['pulse'] = Counter(pulse_candidates).most_common(1)[0][0]

        if filter_candidates:
            tables['filter'] = Counter(filter_candidates).most_common(1)[0][0]

        if wave_candidates:
            tables['wave'] = Counter(wave_candidates).most_common(1)[0][0]
    except (IndexError, ValueError) as e:
        raise TableExtractionError(f"Error selecting table candidates: {e}")

    return tables


def find_instrument_table(data: bytes, load_addr: int, verbose: bool = False, wave_table: Optional[List[Tuple[int, int]]] = None) -> Union[Optional[int], Tuple[Optional[int], Dict[str, Any]]]:
    """
    Find the instrument table in Laxity format.
    Instruments are 8 bytes each, typically in $1900-$1B00 range.

    Args:
        data: C64 program data
        load_addr: Memory load address
        verbose: Enable verbose output
        wave_table: Optional wave table for validating wave pointers

    Returns:
        Address of instrument table, or None if not found

    Raises:
        TableExtractionError: If data is invalid or too small
    """
    if not data or len(data) < 128:
        raise TableExtractionError(f"Data too small for instrument table search: {len(data) if data else 0} bytes")

    best_addr = 0
    best_score = 0
    candidates = []

    # Get valid wave entry points if wave table is provided
    valid_wave_points = None
    if wave_table:
        try:
            valid_wave_points = get_valid_wave_entry_points(wave_table)
        except (IndexError, ValueError) as e:
            # Continue without wave pointer validation if wave table is malformed
            valid_wave_points = None

    search_start = SEARCH_START_OFFSET
    search_end = min(len(data) - 128, SEARCH_END_OFFSET)

    try:
        for offset in range(search_start, search_end):
            score = 0
            valid_instruments = 0

            # Check up to 8 consecutive potential instruments
            for i in range(8):
                off = offset + (i * 8)
                if off + 8 > len(data):
                    break

                # Laxity instrument format (8 bytes):
                # 0: AD, 1: SR, 2-4: flags/unknown, 5: Pulse param, 6: Pulse Ptr, 7: Wave Ptr
                ad = data[off]
                sr = data[off + 1]
                pulse_param = data[off + 5]
                pulse_ptr = data[off + 6]
                wave_ptr = data[off + 7]
                filter_ptr = 0  # Filter pointer not directly in instrument table

                # Flags/control bytes (bytes 2-4)
                flags1 = data[off + 2]
                flags2 = data[off + 3]
                flags3 = data[off + 4]

            # Compatibility
            restart = flags1
            filter_set = flags3
            pulse_prop = 0

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
                # Extra penalty for first instrument being silent (very uncommon)
                if i == 0:
                    instr_score -= 10
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

            # Wave pointer validation
            if valid_wave_points:
                # Use validated entry points for scoring
                if wave_ptr in valid_wave_points:
                    instr_score += 5  # Strong bonus for valid entry point
                elif wave_ptr < len(wave_table):
                    instr_score += 1  # Small bonus for being within range
                else:
                    instr_score -= 2  # Penalty for out of range
            else:
                # Fallback: Wave pointer should be small
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

    except IndexError as e:
        raise TableExtractionError(f"Index error while searching for instrument table: {e}")

    if verbose:
        candidates.sort(key=lambda x: x[1], reverse=True)
        debug_info = {
            'best_addr': best_addr,
            'best_score': best_score,
            'candidates': candidates[:5]
        }
        return best_addr if best_addr else None, debug_info

    return best_addr if best_addr else None


def find_wave_table_from_player_code(data: bytes, load_addr: int) -> Tuple[Optional[int], Optional[int]]:
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

    Raises:
        TableExtractionError: If data is invalid or too small
    """
    if not data or len(data) < 64:
        raise TableExtractionError(f"Data too small for wave table extraction: {len(data) if data else 0} bytes")

    try:
        # First try to find wave table by analyzing player code
        note_addr, wave_addr = find_wave_table_from_player_code(data, load_addr)
    except (IndexError, ValueError) as e:
        # Fall back to pattern matching if player code analysis fails
        note_addr, wave_addr = None, None

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
    try:
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

                # SF2 format requires (waveform, note_offset) order - swap from Laxity format
                if note_offset == 0x7F:
                    entries.append((waveform, note_offset))
                    score += 5
                    break
                elif note_offset == 0x7E:
                    entries.append((waveform, note_offset))
                    score += 5
                    break
                elif waveform in valid_waveforms:
                    entries.append((waveform, note_offset))
                    score += 3
                    pos += 2
                else:
                    break

            # After byte swap, note_offset is at index [1]
            has_terminator = len(entries) >= 2 and entries[-1][1] in (0x7E, 0x7F)

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

    except IndexError as e:
        raise TableExtractionError(f"Index error while extracting wave table: {e}")

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

    Raises:
        TableExtractionError: If data is invalid or too small
    """
    if not data or len(data) < 64:
        raise TableExtractionError(f"Data too small for pulse table extraction: {len(data) if data else 0} bytes")

    # First try pattern-based detection which is more reliable
    # Key insight: look for the characteristic pattern where first entry
    # has a non-zero pulse value and next=0, followed by entries with chains

    best_addr = 0
    best_entries = []
    best_score = 0

    # Search in the typical range for Laxity pulse tables (offset 0x600-0x1200 from load address)
    for start in range(0x600, min(len(data) - 64, 0x1200)):
        addr = load_addr + start
        if avoid_addr and abs(addr - avoid_addr) < 128:
            continue

        entries = []
        pos = start
        score = 0
        seen_next_indices = set()
        valid_structure = True

        for entry_idx in range(16):
            if pos + 4 > len(data):
                break

            pulse_val = data[pos]
            count = data[pos + 1]
            duration = data[pos + 2]
            next_idx = data[pos + 3]

            # Validate next index structure (Y*4 format)
            # Next should be 0, or divisible by 4 and point to valid entry
            if next_idx != 0:
                if next_idx % 4 != 0:
                    valid_structure = False
                    break
                if next_idx > 64:
                    valid_structure = False
                    break

            # Score based on pulse table characteristics
            entry_score = 0

            # Pulse value scoring
            if pulse_val == 0xFF:
                entry_score += 3  # Common "keep current" value
            elif pulse_val <= 0x0F:
                entry_score += 2  # Small initial values very common
            elif pulse_val <= 0x20:
                entry_score += 1

            # Count (add/sub value) typically $00-$80
            if count <= 0x80:
                entry_score += 1

            # Duration scoring - bit 7 is direction flag
            dur_clean = duration & 0x7F
            if 0 < dur_clean <= 0x60:
                entry_score += 2
            elif dur_clean == 0:
                entry_score += 1  # Immediate

            # Next index structure bonus
            if next_idx % 4 == 0:
                entry_score += 2
                if next_idx == 0:
                    entry_score += 1  # First entry or loop to start

            # First entry should have next=0 or small valid index
            if entry_idx == 0:
                if next_idx == 0 and pulse_val != 0:
                    entry_score += 3  # Strong bonus for correct first entry
                elif pulse_val == 0 and count == 0 and duration == 0 and next_idx == 0:
                    entry_score -= 5  # Strong penalty for all-zero first entry

            # Convert Laxity Y*4 index format to SF2 direct index format
            direct_idx = next_idx // 4 if next_idx % 4 == 0 and next_idx != 0 else next_idx
            entries.append((pulse_val, count, duration, direct_idx))
            score += entry_score

            # Track next indices for scoring (but don't break on loops)
            if next_idx != 0:
                if next_idx in seen_next_indices:
                    score += 3  # Bonus for having loop targets
                seen_next_indices.add(next_idx)

            # Stop at end marker (all zeros)
            if pulse_val == 0 and count == 0 and duration == 0 and next_idx == 0 and entry_idx > 0:
                break

            pos += 4

        if not valid_structure:
            continue

        # Additional scoring for table quality
        if len(entries) >= 3:
            score += len(entries) * 2

        # Bonus for having typical first entry (non-zero pulse value, next=0)
        if entries and entries[0][0] != 0 and entries[0][3] == 0:
            score += 5

        # Strong bonus for tables with inter-entry references (chain pattern)
        # Real pulse tables have entries that reference each other
        non_zero_nexts = sum(1 for e in entries if e[3] != 0)
        if non_zero_nexts >= 3:
            score += 20  # Strong bonus for chains
        elif non_zero_nexts >= 1:
            score += 8

        # Bonus for having $FF pulse values (keep current) or small values <= 0x0F
        valid_pulse_vals = sum(1 for e in entries if e[0] == 0xFF or e[0] <= 0x0F)
        if valid_pulse_vals >= len(entries) * 0.5:
            score += 10

        # Strong bonus for typical pulse modulation patterns
        # Duration values with bit 7 set (subtract) are common
        has_subtract = sum(1 for e in entries if e[2] & 0x80)
        if has_subtract >= 2:
            score += 10

        # Bonus if next values form proper chains (increasing pattern)
        next_vals = [e[3] for e in entries if e[3] != 0]
        if len(next_vals) >= 3 and len(set(next_vals)) >= 3:
            score += 10  # Multiple different next values = real chain

        if score > best_score and len(entries) >= 2:
            best_score = score
            best_addr = addr
            best_entries = entries

    if best_entries:
        return best_addr, best_entries

    # Fallback: try to find pulse table by analyzing player code references
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

            entries.append((val, cnt, dur, nxt))

            # Stop at end marker
            if val == 0 and cnt == 0 and dur == 0 and nxt == 0 and i > 0:
                break

        if entries:
            return (base_addr, entries)

    # Return empty if nothing found
    return 0, []


def find_and_extract_filter_table(data: bytes, load_addr: int, filter_ptrs: Optional[set] = None, avoid_addr: int = 0) -> Tuple[Optional[int], List[bytes]]:
    """
    Find and extract filter table from Laxity SID.

    Filter table format (4 bytes per entry, Y-indexed with stride 4):
    - Byte 0: Filter cutoff high byte (any value valid)
    - Byte 1: Add/subtract value per frame
    - Byte 2: Duration (bits 0-6) + direction (bit 7: 0=add, 1=subtract)
    - Byte 3: Next entry index (pre-multiplied by 4)

    Returns (address, entries) where entries is list of 4-byte tuples.

    Raises:
        TableExtractionError: If data is invalid or too small
    """
    if not data or len(data) < 64:
        raise TableExtractionError(f"Data too small for filter table extraction: {len(data) if data else 0} bytes")

    # Try known Laxity NewPlayer v21 address first: $1A1E
    LAXITY_FILTER_ADDR = 0x1A1E
    if load_addr <= LAXITY_FILTER_ADDR and LAXITY_FILTER_ADDR < load_addr + len(data):
        laxity_offset = LAXITY_FILTER_ADDR - load_addr
        if laxity_offset + 16 < len(data):
            # Try extracting from known address
            entries = []
            pos = laxity_offset
            for entry_idx in range(16):
                if pos + 4 > len(data):
                    break

                filter_val = data[pos]
                # Check for end marker (0x7F)
                if filter_val == 0x7F:
                    break

                count = data[pos + 1]
                duration = data[pos + 2]
                next_idx = data[pos + 3]

                # Validate Y*4 format for next index
                if next_idx != 0 and (next_idx % 4 != 0 or next_idx > 64):
                    break

                entries.append((filter_val, count, duration, next_idx))

                # Stop at end marker (all zeros)
                if filter_val == 0 and count == 0 and duration == 0 and next_idx == 0 and entry_idx > 0:
                    break

                pos += 4

            # If we extracted a reasonable table from known address, use it
            if len(entries) >= 2:
                return LAXITY_FILTER_ADDR, entries

    best_addr = 0
    best_entries = []
    best_score = 0

    # Fallback: Search in the typical range for Laxity filter tables
    # Extended range to cover larger SID files (some go up to $2F63)
    for start in range(0x600, min(len(data) - 64, 0x2000)):
        addr = load_addr + start
        # Skip if this address would start within the avoided table
        if avoid_addr and addr >= avoid_addr and addr < avoid_addr + 64:
            continue

        entries = []
        pos = start
        score = 0
        seen_next_indices = set()
        valid_structure = True

        for entry_idx in range(16):
            if pos + 4 > len(data):
                break

            # Stop if we would read into the avoided table
            entry_addr = load_addr + pos
            if avoid_addr and entry_addr >= avoid_addr:
                break

            filter_val = data[pos]
            count = data[pos + 1]
            duration = data[pos + 2]
            next_idx = data[pos + 3]

            # Validate next index structure (Y*4 format)
            if next_idx != 0:
                if next_idx % 4 != 0:
                    valid_structure = False
                    break
                if next_idx > 64:
                    valid_structure = False
                    break

            # Score based on filter table characteristics
            entry_score = 0

            # Filter cutoff can be any value, but typical ranges are common
            if filter_val == 0xFF:
                entry_score += 2  # Keep current
            elif filter_val >= 0x40:
                entry_score += 1  # Higher cutoff values common

            # Count (add/sub value) typically in valid ranges
            if count > 0:
                entry_score += 1

            # Duration scoring
            dur_clean = duration & 0x7F
            if 0 < dur_clean <= 0x60:
                entry_score += 2
            elif dur_clean == 0:
                entry_score += 1

            # Next index structure bonus
            if next_idx % 4 == 0:
                entry_score += 2
                if next_idx == 0:
                    entry_score += 1

            # First entry should have reasonable values
            if entry_idx == 0:
                if filter_val >= 0x40 and next_idx != 0 and next_idx % 4 == 0:
                    entry_score += 5  # Strong bonus for good first entry
                elif filter_val == 0 and count == 0 and duration == 0 and next_idx == 0:
                    entry_score -= 5  # Penalty for all-zero first entry

            entries.append((filter_val, count, duration, next_idx))
            score += entry_score

            # Track next indices for scoring
            if next_idx != 0:
                if next_idx in seen_next_indices:
                    score += 3
                seen_next_indices.add(next_idx)

            # Stop at end marker (all zeros)
            if filter_val == 0 and count == 0 and duration == 0 and next_idx == 0 and entry_idx > 0:
                break

            pos += 4

        if not valid_structure:
            continue

        # Additional scoring for table quality
        if len(entries) >= 2:
            score += len(entries) * 2

        # Strong bonus for tables with inter-entry references (chain pattern)
        non_zero_nexts = sum(1 for e in entries if e[3] != 0)
        if non_zero_nexts >= 3:
            score += 20
        elif non_zero_nexts >= 1:
            score += 8

        # Bonus for typical filter patterns (high cutoff values)
        high_cutoffs = sum(1 for e in entries if e[0] >= 0x40 or e[0] == 0xFF)
        if high_cutoffs >= len(entries) * 0.5:
            score += 10

        # Bonus for having subtract patterns (filter sweeps)
        has_subtract = sum(1 for e in entries if e[2] & 0x80)
        if has_subtract >= 1:
            score += 5

        if score > best_score and len(entries) >= 2:
            best_score = score
            best_addr = addr
            best_entries = entries

    return best_addr, best_entries


def extract_hr_table(data: bytes, load_addr: int, init_addr: int) -> List[Tuple[int, int]]:
    """
    Extract HR (Hard Restart) table from Laxity player.

    HR table controls the hard restart behavior for notes.
    In Laxity, this is typically a simple value controlling gate timing.

    Args:
        data: C64 program data
        load_addr: Memory load address
        init_addr: Init routine address

    Returns:
        List of (frames, waveform) tuples for HR entries
    """
    # Default HR table entry
    default_hr = [(0x0F, 0x00)]

    init_offset = init_addr - load_addr
    if init_offset < 0 or init_offset >= len(data):
        return default_hr

    # Search for HR-related patterns in Laxity player
    # Common patterns:
    # 1. LDA #$xx; STA hr_value - hard restart frames
    # 2. Table of 2-byte entries: (frames, wave)

    # Look for patterns that suggest HR timing values
    # Typical HR frames: $09-$0F (for gate timing)
    for i in range(init_offset, min(init_offset + 500, len(data) - 3)):
        # Look for LDA immediate followed by STA
        if data[i] == 0xA9:  # LDA immediate
            value = data[i + 1]
            # HR frames are typically 0x09-0x0F
            if 0x09 <= value <= 0x0F:
                if data[i + 2] in (0x85, 0x8D):  # STA zp or STA abs
                    return [(value, 0x00)]

    # Try to find HR table by searching for typical patterns
    # HR tables often have frames in range 0x08-0x10
    for addr in range(load_addr + 0x100, load_addr + len(data) - 4, 2):
        offset = addr - load_addr
        if offset + 2 <= len(data):
            frames = data[offset]
            wave = data[offset + 1]
            # Valid HR entry: frames in reasonable range, wave is valid
            if 0x08 <= frames <= 0x10 and wave in (0x00, 0x08, 0x09):
                return [(frames, wave)]

    return default_hr


def extract_init_table(data: bytes, load_addr: int, init_addr: int,
                       tempo: int, volume: int) -> List[int]:
    """
    Extract Init table from Laxity player.

    Init table contains initialization values:
    [tempo_index, volume, voice0_instr, voice1_instr, voice2_instr]

    Args:
        data: C64 program data
        load_addr: Memory load address
        init_addr: Init routine address
        tempo: Extracted tempo value
        volume: Extracted volume value

    Returns:
        List of 5 init values
    """
    # Default init table
    default_init = [0x00, volume, 0x00, 0x01, 0x02]

    init_offset = init_addr - load_addr
    if init_offset < 0 or init_offset >= len(data):
        return default_init

    # Try to extract default instruments from init routine
    # Laxity often initializes channels with:
    # LDA #$xx; STA instr_ch1, etc.

    default_instruments = [0x00, 0x01, 0x02]
    found_instruments = []

    # Search for instrument initialization patterns
    for i in range(init_offset, min(init_offset + 300, len(data) - 3)):
        if data[i] == 0xA9:  # LDA immediate
            value = data[i + 1]
            # Instrument indices are typically 0-15
            if value <= 15:
                if i + 2 < len(data) and data[i + 2] in (0x85, 0x8D):
                    # Check if this might be an instrument assignment
                    # by looking at consecutive assignments
                    if len(found_instruments) < 3:
                        found_instruments.append(value)
                        if len(found_instruments) == 3:
                            default_instruments = found_instruments
                            break

    return [0x00, volume] + default_instruments


def extract_arp_table(data: bytes, load_addr: int) -> List[Tuple[int, int, int, int]]:
    """
    Extract arpeggio table from Laxity player.

    Arpeggio table format (4 bytes per entry):
    - Byte 0: Note offset 1 (or command)
    - Byte 1: Note offset 2
    - Byte 2: Note offset 3
    - Byte 3: Speed/control (bits 0-5 = speed, bit 6 = loop, bit 7 = end)

    SF2 arp table format (column-major):
    - Column 0: First note offset
    - Column 1: Second note offset
    - Column 2: Third note offset
    - Column 3: Speed/control

    Args:
        data: C64 program data
        load_addr: Memory load address

    Returns:
        List of (note1, note2, note3, speed) tuples
    """
    # Default arpeggio table entries
    default_arp = [
        (0x00, 0x00, 0x00, 0x00),  # Entry 0: No arpeggio
        (0x00, 0x04, 0x07, 0x01),  # Entry 1: Major chord (C-E-G)
        (0x00, 0x03, 0x07, 0x01),  # Entry 2: Minor chord (C-Eb-G)
        (0x00, 0x07, 0x0C, 0x01),  # Entry 3: Fifth + octave
    ]

    best_addr = 0
    best_entries = []
    best_score = 0

    # Search for arpeggio table patterns
    # Typical range: after instrument table, before sequence data
    for start in range(0x600, min(len(data) - 64, 0x1400)):
        entries = []
        pos = start
        score = 0
        valid_structure = True

        for entry_idx in range(16):
            if pos + 4 > len(data):
                break

            note1 = data[pos]
            note2 = data[pos + 1]
            note3 = data[pos + 2]
            speed = data[pos + 3]

            # Validate arpeggio entry
            entry_score = 0

            # Note offsets should be reasonable (0-24 semitones typical)
            # Special values: 0x7E = hold, 0x7F = end/jump
            valid_notes = True
            for note in [note1, note2, note3]:
                if note <= 0x18:  # Up to 24 semitones
                    entry_score += 1
                elif note in (0x7E, 0x7F):  # Control bytes
                    entry_score += 2
                elif note <= 0x30:  # Extended range
                    entry_score += 0
                else:
                    valid_notes = False

            if not valid_notes:
                valid_structure = False
                break

            # Speed should be reasonable (0-63 typical, bit 6-7 for flags)
            speed_val = speed & 0x3F
            if speed_val <= 0x10:
                entry_score += 2
            elif speed_val <= 0x20:
                entry_score += 1

            # First entry often has all zeros (no arp)
            if entry_idx == 0 and note1 == 0 and note2 == 0 and note3 == 0:
                entry_score += 3

            # Common chord patterns get bonus
            # Major chord: 0, 4, 7
            if note1 == 0 and note2 == 4 and note3 == 7:
                entry_score += 5
            # Minor chord: 0, 3, 7
            elif note1 == 0 and note2 == 3 and note3 == 7:
                entry_score += 5
            # Octave: 0, 12
            elif note1 == 0 and (note2 == 12 or note3 == 12):
                entry_score += 3

            entries.append((note1, note2, note3, speed))
            score += entry_score

            # Stop at end marker
            if note1 == 0x7F or (note1 == 0 and note2 == 0 and note3 == 0 and speed == 0 and entry_idx > 0):
                break

            pos += 4

        if not valid_structure:
            continue

        # Additional scoring
        if len(entries) >= 2:
            score += len(entries) * 2

        # Bonus for having typical first entry (zeros)
        if entries and entries[0] == (0, 0, 0, 0):
            score += 5

        # Bonus for having recognizable chord patterns
        chord_patterns = sum(1 for e in entries if (
            (e[0] == 0 and e[1] == 4 and e[2] == 7) or  # Major
            (e[0] == 0 and e[1] == 3 and e[2] == 7) or  # Minor
            (e[0] == 0 and e[1] == 7 and e[2] == 12)    # Fifth+octave
        ))
        if chord_patterns >= 1:
            score += 10

        if score > best_score and len(entries) >= 2:
            best_score = score
            best_addr = load_addr + start
            best_entries = entries

    if best_entries and best_score >= 15:
        return best_entries

    return default_arp


def extract_command_table(data: bytes, load_addr: int, sequences: list = None) -> List[bytes]:
    """
    Extract command table from Laxity player.

    Commands in Laxity format use bytes $C0-$DF in sequences.
    Each command can have 0-2 parameter bytes following it.

    Command table format (for SF2):
    - Each entry is variable length based on command type
    - Common commands: vibrato, slide, portamento, etc.

    Args:
        data: C64 program data
        load_addr: Memory load address
        sequences: Optional list of extracted sequences to analyze

    Returns:
        List of command bytes/entries
    """
    # Default command table with common Laxity commands
    default_commands = [
        bytes([0x00]),  # Cmd 0: No command
        bytes([0x00]),  # Cmd 1: Set AD
        bytes([0x00]),  # Cmd 2: Set SR
        bytes([0x00]),  # Cmd 3: Set waveform
        bytes([0x00]),  # Cmd 4: Set pulse
        bytes([0x00]),  # Cmd 5: Vibrato
        bytes([0x00]),  # Cmd 6: Slide up
        bytes([0x00]),  # Cmd 7: Slide down
    ]

    if not sequences:
        return default_commands

    # Analyze sequences to find command usage
    command_usage = {}
    for seq in sequences:
        if hasattr(seq, '__iter__'):
            for i, byte in enumerate(seq):
                if isinstance(byte, int):
                    # Commands are in range $C0-$DF
                    if 0xC0 <= byte <= 0xDF:
                        cmd_idx = byte - 0xC0
                        if cmd_idx not in command_usage:
                            command_usage[cmd_idx] = 0
                        command_usage[cmd_idx] += 1

    # Build command table based on usage
    commands = []
    for i in range(32):  # Up to 32 commands
        if i in command_usage:
            # Command is used - add placeholder entry
            commands.append(bytes([0x00]))
        else:
            commands.append(bytes([0x00]))

    if commands:
        return commands

    return default_commands


def extract_all_laxity_tables(data: bytes, load_addr: int) -> Dict[str, Any]:
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

    # Extract filter table - use improved pattern-based detection first
    pulse_addr = result.get('pulse_addr', 0)
    found_addr, found_entries = find_and_extract_filter_table(data, load_addr, avoid_addr=pulse_addr)
    if found_addr and found_entries:
        result['filter_addr'] = found_addr
        result['filter_table'] = found_entries
    else:
        # Fallback to heuristic searches
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

        if filter_addr:
            result['filter_addr'] = filter_addr
            filter_offset = filter_addr - load_addr

            filter_entries = []
            for i in range(16):
                off = filter_offset + (i * 4)
                if off + 4 <= len(data):
                    entry = (data[off], data[off+1], data[off+2], data[off+3])
                    filter_entries.append(entry)
                    # Stop on all-zero entry (terminator)
                    if entry[0] == 0 and entry[1] == 0 and entry[2] == 0 and entry[3] == 0 and i > 0:
                        break
            result['filter_table'] = filter_entries

    if 'filter_table' not in result or not result['filter_table']:
        result['filter_table'] = [(0x40, 0x01, 0x20, 0x00)]

    return result
