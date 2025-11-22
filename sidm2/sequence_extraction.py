"""
Sequence and command extraction functions.
"""

from typing import Dict, List, Set, Tuple


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


def extract_command_parameters(data: bytes, load_addr: int, raw_sequences: List[bytes]) -> List[Tuple[int, int]]:
    """
    Extract command parameters based on usage in sequences.

    Args:
        data: C64 program data
        load_addr: Memory load address
        raw_sequences: List of raw sequence byte arrays

    Returns:
        List of (command_idx, parameter_value) tuples
    """
    command_params = []

    for seq in raw_sequences:
        i = 0
        while i < len(seq):
            byte = seq[i]

            if 0xC0 <= byte <= 0xCF:
                cmd = byte - 0xC0
                param = 0

                if i + 1 < len(seq):
                    next_byte = seq[i + 1]
                    # Commands that take inline parameters
                    if cmd in [8, 9]:  # Speed and Volume
                        if next_byte < 0x80:
                            param = next_byte
                            i += 1

                if (cmd, param) not in command_params:
                    command_params.append((cmd, param))

            i += 1

    return command_params
