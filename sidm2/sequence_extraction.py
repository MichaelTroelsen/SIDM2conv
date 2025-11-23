"""
Sequence and command extraction functions.
"""

from typing import Dict, List, Set, Tuple, Optional


def get_command_names() -> List[str]:
    """
    Return list of command names for SF2 command table.
    Based on JCH NewPlayer v21 super commands.
    """
    return [
        "Slide Up",      # 0
        "Slide Down",    # 1
        "Vibrato",       # 2
        "Portamento",    # 3
        "Set ADSR",      # 4
        "Set Filter",    # 5
        "Set Wave",      # 6
        "Set Pulse",     # 7
        "Set Speed",     # 8
        "Set Volume",    # 9
        "Arpeggio",      # A
        "Note Cut",      # B
        "Legato",        # C
        "Retrigger",     # D
        "Delay",         # E
        "End",           # F
    ]


def analyze_sequence_commands(raw_sequences: List[bytes]) -> Dict:
    """
    Analyze commands used in sequences and extract command statistics.

    Args:
        raw_sequences: List of raw sequence byte arrays

    Returns:
        Dict with:
        - commands_used: set of command indices used
        - command_counts: dict of command index -> count
        - command_contexts: dict of command index -> list of (seq_idx, note_before)
        - set_adsr_values: list of (AD, SR) tuples from Set ADSR commands
    """
    result = {
        'commands_used': set(),
        'command_counts': {},
        'command_contexts': {},
        'set_adsr_values': []
    }

    for seq_idx, seq in enumerate(raw_sequences):
        last_note = None
        i = 0
        while i < len(seq):
            byte = seq[i]
            if 0xC0 <= byte <= 0xCF:
                cmd = byte - 0xC0
                result['commands_used'].add(cmd)
                result['command_counts'][cmd] = result['command_counts'].get(cmd, 0) + 1
                if cmd not in result['command_contexts']:
                    result['command_contexts'][cmd] = []
                result['command_contexts'][cmd].append((seq_idx, last_note))

                # Extract parameters for Set ADSR command (cmd 4)
                if cmd == 4 and i + 1 < len(seq):
                    instr_idx = seq[i + 1]
                    if instr_idx not in [idx for idx, _ in result.get('set_adsr_indices', [])]:
                        if 'set_adsr_indices' not in result:
                            result['set_adsr_indices'] = []
                        result['set_adsr_indices'].append((instr_idx, (seq_idx, i)))
                    i += 1

            elif 0x00 <= byte <= 0x6F:
                last_note = byte
            i += 1

    return result


def extract_command_parameters(data: bytes, load_addr: int, raw_sequences: List[bytes]) -> List[Tuple[int, int, int]]:
    """
    Extract command parameters based on usage in sequences.

    Parses Laxity NewPlayer v21 command format and converts to SF2 Driver 11 format.

    Laxity format:
    - $0x yy = Slide up speed $xyy
    - $2x yy = Slide down speed $xyy
    - $60 xy = Vibrato x=freq, y=amp
    - $8x xx = Portamento speed $xxx
    - $9x yy = Set D=x and SR=yy (persistent)
    - $ax yy = Set D=x and SR=yy (until next note)
    - $c0 xx = Set wave pointer
    - $dx yy = Filter/pulse control (x=0: filter ptr, x=1: filter val, x=2: pulse ptr)
    - $e0 xx = Set speed
    - $f0 xx = Set volume

    Args:
        data: C64 program data
        load_addr: Memory load address
        raw_sequences: List of raw sequence byte arrays

    Returns:
        List of (sf2_command_type, param1, param2) tuples for SF2 command table
        SF2 command types: 0=slide, 1=vibrato, 2=portamento, 3=arpeggio, etc.
    """
    command_params = []

    for seq in raw_sequences:
        i = 0
        while i < len(seq):
            byte = seq[i]

            # Skip non-command bytes
            if byte < 0x80:
                i += 1
                continue

            # Instrument reference ($A0-$BF)
            if 0xA0 <= byte <= 0xBF:
                i += 1
                continue

            # Command parsing based on Laxity format
            high_nibble = (byte >> 4) & 0x0F
            low_nibble = byte & 0x0F

            if i + 1 >= len(seq):
                i += 1
                continue

            param_byte = seq[i + 1]

            # Parse Laxity commands and convert to SF2 format
            if high_nibble == 0x0:  # $0x yy = Slide up
                # SF2 T0: slide with direction in sign
                speed_hi = low_nibble
                speed_lo = param_byte
                speed = (speed_hi << 8) | speed_lo
                entry = (0, speed_hi, speed_lo)  # T0 = slide
                if entry not in command_params:
                    command_params.append(entry)
                i += 2

            elif high_nibble == 0x2:  # $2x yy = Slide down
                # SF2 T0: slide down (negative direction)
                speed_hi = low_nibble | 0x80  # Set sign bit for down
                speed_lo = param_byte
                entry = (0, speed_hi, speed_lo)  # T0 = slide
                if entry not in command_params:
                    command_params.append(entry)
                i += 2

            elif byte == 0x60:  # $60 xy = Vibrato
                # SF2 T1: vibrato XX=freq, YY=amp
                freq = (param_byte >> 4) & 0x0F
                amp = param_byte & 0x0F
                entry = (1, freq, amp)  # T1 = vibrato
                if entry not in command_params:
                    command_params.append(entry)
                i += 2

            elif high_nibble == 0x8:  # $8x xx = Portamento
                # SF2 T2: portamento XXYY = 16-bit speed
                speed_hi = low_nibble
                speed_lo = param_byte
                entry = (2, speed_hi, speed_lo)  # T2 = portamento
                if entry not in command_params:
                    command_params.append(entry)
                i += 2

            elif high_nibble == 0x9:  # $9x yy = Set ADSR (persistent)
                # SF2 T9: set instrument ADSR
                ad = low_nibble << 4  # D value in high nibble
                sr = param_byte
                entry = (9, ad, sr)  # T9 = ADSR persist
                if entry not in command_params:
                    command_params.append(entry)
                i += 2

            elif high_nibble == 0xA:  # $ax yy = Set ADSR (local)
                # SF2 T8: set local ADSR
                ad = low_nibble << 4  # D value in high nibble
                sr = param_byte
                entry = (8, ad, sr)  # T8 = ADSR local
                if entry not in command_params:
                    command_params.append(entry)
                i += 2

            elif byte == 0xC0:  # $c0 xx = Set wave pointer
                # SF2 Tb: wave program
                wave_idx = param_byte
                entry = (0x0B, 0, wave_idx)  # Tb = wave index
                if entry not in command_params:
                    command_params.append(entry)
                i += 2

            elif high_nibble == 0xD:  # $dx yy = Filter/pulse control
                # x=0: filter ptr, x=1: filter value, x=2: pulse ptr
                if low_nibble == 0:
                    entry = (0x0A, 0, param_byte)  # Ta = filter program
                elif low_nibble == 2:
                    entry = (0x0C, 0, param_byte)  # Tc = pulse program
                else:
                    i += 2
                    continue
                if entry not in command_params:
                    command_params.append(entry)
                i += 2

            elif byte == 0xE0:  # $e0 xx = Set speed
                # SF2 Td: tempo program
                speed = param_byte
                entry = (0x0D, 0, speed)  # Td = tempo
                if entry not in command_params:
                    command_params.append(entry)
                i += 2

            elif byte == 0xF0:  # $f0 xx = Set volume
                # SF2 Te: main volume
                volume = param_byte & 0x0F
                entry = (0x0E, 0, volume)  # Te = volume
                if entry not in command_params:
                    command_params.append(entry)
                i += 2

            else:
                # Unknown or continuation byte
                i += 1

    return command_params


def build_sf2_command_table(command_params: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
    """
    Build SF2 command table from extracted parameters.

    SF2 Driver 11 command table format: 3 bytes per entry
    - Byte 0: Command type (T0-TF)
    - Byte 1: Parameter 1 (XX)
    - Byte 2: Parameter 2 (YY)

    Args:
        command_params: List of (type, param1, param2) tuples

    Returns:
        List of 64 command entries (padded with zeros if needed)
    """
    # Start with default entries
    commands = []

    # Add extracted commands
    for cmd_type, param1, param2 in command_params:
        commands.append((cmd_type, param1, param2))

    # Pad to 64 entries
    while len(commands) < 64:
        commands.append((0, 0, 0))

    return commands[:64]


def extract_arpeggio_indices(raw_sequences: List[bytes]) -> Set[int]:
    """
    Extract arpeggio table indices used in sequences.

    Scans for Laxity arpeggio commands (high nibble 0x3) and extracts
    the following parameter byte as the arpeggio table index.

    Args:
        raw_sequences: List of raw sequence byte arrays

    Returns:
        Set of arpeggio table indices used
    """
    arp_indices = set()

    for seq in raw_sequences:
        i = 0
        while i < len(seq) - 1:
            byte = seq[i]

            # Laxity arpeggio command: $3x yy where yy is arpeggio index
            # In some variants it's $C3 yy (0xC3 = command 3)
            if byte == 0xC3:  # Command 3 = Arpeggio
                arp_idx = seq[i + 1]
                if arp_idx < 32:  # Valid arpeggio index range
                    arp_indices.add(arp_idx)
                i += 2
            elif (byte & 0xF0) == 0x30:  # $3x yy format
                arp_idx = seq[i + 1]
                if arp_idx < 32:
                    arp_indices.add(arp_idx)
                i += 2
            else:
                i += 1

    return arp_indices


def find_arpeggio_table_in_memory(
    data: bytes,
    load_addr: int,
    arp_indices: Set[int],
    verbose: bool = False
) -> Tuple[Optional[int], List[Tuple[int, ...]]]:
    """
    Find and extract arpeggio table from C64 memory.

    Uses pattern matching to find sequences of semitone values that
    match common arpeggio patterns (major, minor, octave, etc.).

    Args:
        data: C64 program data
        load_addr: Memory load address
        arp_indices: Set of arpeggio indices used in sequences
        verbose: Enable debug output

    Returns:
        Tuple of (table_address, list of arpeggio entries)
        Each entry is a tuple of semitone values ending with 0x7F
    """
    # Common arpeggio patterns to search for
    known_patterns = [
        (0x00, 0x04, 0x07, 0x7F),  # Major chord
        (0x00, 0x03, 0x07, 0x7F),  # Minor chord
        (0x00, 0x0C, 0x7F),        # Octave
        (0x00, 0x07, 0x7F),        # Fifth
        (0x00, 0x05, 0x07, 0x7F),  # Sus4 chord
        (0x00, 0x04, 0x08, 0x7F),  # Augmented
        (0x00, 0x03, 0x06, 0x7F),  # Diminished
    ]

    best_addr = None
    best_score = 0
    best_entries = []

    # Search in typical data range
    search_start = 0x600
    search_end = min(len(data), 0x1A00)

    for offset in range(search_start, search_end - 16):
        score = 0
        entries = []

        # Try to parse as arpeggio table starting here
        pos = offset
        entry_count = 0

        while pos < len(data) - 4 and entry_count < 32:
            # Check for valid arpeggio entry pattern
            entry = []
            entry_pos = pos

            # Read semitone values until terminator
            while entry_pos < len(data) and len(entry) < 8:
                byte = data[entry_pos]

                # Valid semitone values: 0x00-0x7D
                if byte <= 0x7D:
                    entry.append(byte)
                    entry_pos += 1
                # Terminator/loop marker
                elif byte == 0x7F:
                    entry.append(byte)
                    entry_pos += 1
                    break
                # Jump command (0x7E or 0x7F followed by target)
                elif byte == 0x7E:
                    entry.append(byte)
                    if entry_pos + 1 < len(data):
                        entry.append(data[entry_pos + 1])
                        entry_pos += 2
                    break
                else:
                    # Invalid byte for arpeggio
                    break

            if len(entry) >= 2 and entry[-1] in (0x7F, 0x7E):
                # Valid entry found
                entries.append(tuple(entry))

                # Score this entry
                entry_tuple = tuple(entry)

                # Check against known patterns
                for pattern in known_patterns:
                    if entry_tuple == pattern:
                        score += 20
                        break
                    # Partial match
                    if entry_tuple[:3] == pattern[:3]:
                        score += 10
                        break

                # Valid semitone range bonus
                for val in entry[:-1]:  # Exclude terminator
                    if 0 <= val <= 24:  # Reasonable semitone offset
                        score += 1

                # Proper terminator
                if entry[-1] == 0x7F:
                    score += 3

                pos = entry_pos
                entry_count += 1
            else:
                # Invalid entry, stop parsing
                break

        # Bonus for having multiple valid entries
        if len(entries) >= 3:
            score += len(entries) * 2

        # Bonus if we have entries for indices used in sequences
        if arp_indices and len(entries) >= max(arp_indices, default=0) + 1:
            score += 10

        if score > best_score and len(entries) >= 1:
            best_score = score
            best_addr = load_addr + offset
            best_entries = entries

    if verbose and best_addr:
        print(f"    Found arpeggio table at ${best_addr:04X} with {len(best_entries)} entries (score: {best_score})")

    return best_addr, best_entries


def build_sf2_arp_table(
    extracted_entries: List[Tuple[int, ...]],
    max_entries: int = 32
) -> List[Tuple[int, int, int, int]]:
    """
    Build SF2 arpeggio table from extracted entries.

    SF2 arpeggio format: 4 columns per entry
    - Each column contains a semitone offset (0x00-0x7D) or jump/end marker

    Args:
        extracted_entries: List of extracted arpeggio tuples
        max_entries: Maximum number of entries (default 32)

    Returns:
        List of 4-tuple arpeggio entries padded to max_entries
    """
    # Default patterns for padding
    defaults = [
        (0x00, 0x04, 0x07, 0x7F),  # Major chord
        (0x00, 0x03, 0x07, 0x7F),  # Minor chord
        (0x00, 0x0C, 0x7F, 0x00),  # Octave
    ]

    result = []

    # Convert extracted entries to 4-column format
    for entry in extracted_entries[:max_entries]:
        if len(entry) >= 4:
            result.append((entry[0], entry[1], entry[2], entry[3]))
        elif len(entry) == 3:
            result.append((entry[0], entry[1], entry[2], 0x00))
        elif len(entry) == 2:
            result.append((entry[0], entry[1], 0x7F, 0x00))
        else:
            result.append((0x00, 0x7F, 0x00, 0x00))

    # Pad with defaults if needed
    default_idx = 0
    while len(result) < max_entries:
        result.append(defaults[default_idx % len(defaults)])
        default_idx += 1

    return result[:max_entries]
