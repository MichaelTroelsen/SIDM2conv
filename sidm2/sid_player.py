"""Python SID Player for validation and debugging.

This module provides a SID file player that uses the 6502 CPU emulator
to execute SID files and capture detailed register state for analysis.

Useful for:
- Validating conversions by comparing original vs converted SID
- Understanding SID playback behavior
- Debugging conversion issues
"""

import struct
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from pathlib import Path

from .cpu6502_emulator import CPU6502Emulator, FrameState, SIDRegisterWrite
from .errors import InvalidInputError, ConversionError


# Standard C64 frequency table (PAL)
FREQ_TABLE_LO = [
    0x17, 0x27, 0x39, 0x4B, 0x5F, 0x74, 0x8A, 0xA1, 0xBA, 0xD4, 0xF0, 0x0E,
    0x2D, 0x4E, 0x71, 0x96, 0xBE, 0xE8, 0x14, 0x43, 0x74, 0xA9, 0xE1, 0x1C,
    0x5A, 0x9C, 0xE2, 0x2D, 0x7C, 0xCF, 0x28, 0x85, 0xE8, 0x52, 0xC1, 0x37,
    0xB4, 0x39, 0xC5, 0x5A, 0xF7, 0x9E, 0x4F, 0x0A, 0xD1, 0xA3, 0x82, 0x6E,
    0x68, 0x71, 0x8A, 0xB3, 0xEE, 0x3C, 0x9E, 0x15, 0xA2, 0x46, 0x04, 0xDC,
    0xD0, 0xE2, 0x14, 0x67, 0xDD, 0x79, 0x3C, 0x29, 0x44, 0x8D, 0x08, 0xB8,
    0xA1, 0xC5, 0x28, 0xCD, 0xBA, 0xF1, 0x78, 0x53, 0x87, 0x1A, 0x10, 0x71,
    0x42, 0x89, 0x4F, 0x9B, 0x74, 0xE2, 0xF0, 0xA6, 0x0E, 0x33, 0x20, 0xFF,
]

FREQ_TABLE_HI = [
    0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x02,
    0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x03, 0x03, 0x03, 0x03, 0x03, 0x04,
    0x04, 0x04, 0x04, 0x05, 0x05, 0x05, 0x06, 0x06, 0x06, 0x07, 0x07, 0x08,
    0x08, 0x09, 0x09, 0x0A, 0x0A, 0x0B, 0x0C, 0x0D, 0x0D, 0x0E, 0x0F, 0x10,
    0x11, 0x12, 0x13, 0x14, 0x15, 0x17, 0x18, 0x1A, 0x1B, 0x1D, 0x1F, 0x20,
    0x22, 0x24, 0x27, 0x29, 0x2B, 0x2E, 0x31, 0x34, 0x37, 0x3A, 0x3E, 0x41,
    0x45, 0x49, 0x4E, 0x52, 0x57, 0x5C, 0x62, 0x68, 0x6E, 0x75, 0x7C, 0x83,
    0x8B, 0x93, 0x9C, 0xA5, 0xAF, 0xB9, 0xC4, 0xD0, 0xDD, 0xEA, 0xF8, 0xFF,
]

NOTE_NAMES = [
    "C-0", "C#0", "D-0", "D#0", "E-0", "F-0", "F#0", "G-0", "G#0", "A-0", "A#0", "B-0",
    "C-1", "C#1", "D-1", "D#1", "E-1", "F-1", "F#1", "G-1", "G#1", "A-1", "A#1", "B-1",
    "C-2", "C#2", "D-2", "D#2", "E-2", "F-2", "F#2", "G-2", "G#2", "A-2", "A#2", "B-2",
    "C-3", "C#3", "D-3", "D#3", "E-3", "F-3", "F#3", "G-3", "G#3", "A-3", "A#3", "B-3",
    "C-4", "C#4", "D-4", "D#4", "E-4", "F-4", "F#4", "G-4", "G#4", "A-4", "A#4", "B-4",
    "C-5", "C#5", "D-5", "D#5", "E-5", "F-5", "F#5", "G-5", "G#5", "A-5", "A#5", "B-5",
    "C-6", "C#6", "D-6", "D#6", "E-6", "F-6", "F#6", "G-6", "G#6", "A-6", "A#6", "B-6",
    "C-7", "C#7", "D-7", "D#7", "E-7", "F-7", "F#7", "G-7", "G#7", "A-7", "A#7", "B-7",
]

WAVEFORM_NAMES = {
    0x00: "---",
    0x01: "TRI",
    0x10: "TRI",
    0x11: "PUL",
    0x21: "SAW",
    0x41: "NOI",
    0x80: "NOI",
    0x81: "NOI",
}


@dataclass
class PSIDHeader:
    """PSID/RSID file header."""
    magic: str
    version: int
    data_offset: int
    load_address: int
    init_address: int
    play_address: int
    songs: int
    start_song: int
    speed: int
    name: str
    author: str
    copyright: str
    flags: int = 0
    start_page: int = 0
    page_length: int = 0
    second_sid: int = 0
    third_sid: int = 0


@dataclass
class NoteEvent:
    """A detected note event."""
    frame: int
    voice: int
    note: int
    note_name: str
    frequency: int
    waveform: int
    adsr: int
    pulse: int
    gate_on: bool


@dataclass
class PlaybackResult:
    """Complete playback analysis result."""
    header: PSIDHeader
    frames: List[FrameState]
    writes: List[SIDRegisterWrite]
    notes: List[NoteEvent]
    duration_seconds: float
    total_cycles: int


class SIDPlayer:
    """Play SID files and capture detailed state."""

    def __init__(self, capture_writes: bool = True):
        """Initialize SID player.

        Args:
            capture_writes: If True, capture all SID register writes
        """
        self.cpu = CPU6502Emulator(capture_writes=capture_writes)
        self.header: Optional[PSIDHeader] = None

    def load_sid(self, filepath: str) -> PSIDHeader:
        """Load a SID file.

        Args:
            filepath: Path to SID file

        Returns:
            Parsed PSID header
        """
        with open(filepath, 'rb') as f:
            data = f.read()

        # Parse header
        magic = data[0:4].decode('ascii', errors='replace')
        if magic not in ('PSID', 'RSID'):
            raise InvalidInputError(
                input_type='SID file',
                value=str(sid_path),
                expected='PSID or RSID magic bytes at file start',
                got=f'Magic bytes: {repr(magic)}',
                suggestions=[
                    'Verify file is a valid SID file (not corrupted)',
                    'Check file extension is .sid',
                    'Try opening file in a SID player (e.g., VICE) to verify',
                    f'Inspect file header: hexdump -C {sid_path} | head -5',
                    'Re-download file if obtained from internet'
                ],
                docs_link='guides/TROUBLESHOOTING.md#invalid-sid-files'
            )

        version = struct.unpack('>H', data[4:6])[0]
        data_offset = struct.unpack('>H', data[6:8])[0]
        load_address = struct.unpack('>H', data[8:10])[0]
        init_address = struct.unpack('>H', data[10:12])[0]
        play_address = struct.unpack('>H', data[12:14])[0]
        songs = struct.unpack('>H', data[14:16])[0]
        start_song = struct.unpack('>H', data[16:18])[0]
        speed = struct.unpack('>I', data[18:22])[0]

        # String fields (32 bytes each)
        name = data[22:54].decode('latin-1').rstrip('\x00')
        author = data[54:86].decode('latin-1').rstrip('\x00')
        copyright = data[86:118].decode('latin-1').rstrip('\x00')

        # Optional v2 fields
        flags = 0
        start_page = 0
        page_length = 0
        second_sid = 0
        third_sid = 0
        if version >= 2 and len(data) >= 0x7C:
            flags = struct.unpack('>H', data[0x76:0x78])[0]
            start_page = data[0x78]
            page_length = data[0x79]
            second_sid = struct.unpack('>H', data[0x7A:0x7C])[0] if len(data) >= 0x7E else 0
            third_sid = struct.unpack('>H', data[0x7C:0x7E])[0] if len(data) >= 0x80 else 0

        self.header = PSIDHeader(
            magic=magic,
            version=version,
            data_offset=data_offset,
            load_address=load_address,
            init_address=init_address,
            play_address=play_address,
            songs=songs,
            start_song=start_song,
            speed=speed,
            name=name,
            author=author,
            copyright=copyright,
            flags=flags,
            start_page=start_page,
            page_length=page_length,
            second_sid=second_sid,
            third_sid=third_sid,
        )

        # Load data into memory
        sid_data = data[data_offset:]

        # Handle load address in data
        actual_load = load_address
        if load_address == 0:
            actual_load = sid_data[0] | (sid_data[1] << 8)
            sid_data = sid_data[2:]
            self.header.load_address = actual_load

        # Clear memory and load
        self.cpu.mem = bytearray(65536)
        self.cpu.mem[0x01] = 0x37  # Bank configuration
        self.cpu.load_memory(sid_data, actual_load)

        return self.header

    def freq_to_note(self, freq: int) -> Tuple[int, str]:
        """Convert frequency to note number and name.

        Args:
            freq: SID frequency value

        Returns:
            (note_number, note_name) tuple
        """
        best_note = 0
        best_dist = 0x7FFFFFFF

        for i in range(96):
            cmp_freq = FREQ_TABLE_LO[i] | (FREQ_TABLE_HI[i] << 8)
            dist = abs(freq - cmp_freq)
            if dist < best_dist:
                best_dist = dist
                best_note = i

        return best_note, NOTE_NAMES[best_note]

    def play(self, seconds: float = 60, subtune: int = 0) -> PlaybackResult:
        """Play SID file and capture all state.

        Args:
            seconds: Duration to play in seconds
            subtune: Subtune number (0-based)

        Returns:
            PlaybackResult with all captured data
        """
        if not self.header:
            raise ConversionError(
                stage='Playback',
                reason='No SID file has been loaded yet',
                suggestions=[
                    'Load a SID file first: player.load_sid_file("path/to/file.sid")',
                    'Check that load_sid_file() completed successfully',
                    'Verify the file path is correct'
                ]
            )

        frames: List[FrameState] = []
        notes: List[NoteEvent] = []
        total_cycles = 0
        num_frames = int(seconds * 50)  # PAL: 50 fps

        # Clear SID writes from any previous run
        self.cpu.sid_writes.clear()
        self.cpu.current_frame = 0

        # Run init routine
        init_addr = self.header.init_address
        play_addr = self.header.play_address

        self.cpu.reset(pc=init_addr, a=subtune)
        self.cpu.run_until_return()

        # Handle play address = 0 (use interrupt vector)
        if play_addr == 0:
            if (self.cpu.mem[0x01] & 0x07) == 0x05:
                play_addr = self.cpu.mem[0xFFFE] | (self.cpu.mem[0xFFFF] << 8)
            else:
                play_addr = self.cpu.mem[0x0314] | (self.cpu.mem[0x0315] << 8)

        # Track previous state for note detection
        prev_state: Optional[FrameState] = None
        prev_notes = [-1, -1, -1]
        prev_gate = [False, False, False]

        # Run play routine for each frame
        for frame in range(num_frames):
            self.cpu.current_frame = frame
            self.cpu.reset(pc=play_addr, a=self.cpu.a, x=self.cpu.x, y=self.cpu.y)
            self.cpu.cycles = 0
            self.cpu.run_until_return()

            total_cycles += self.cpu.cycles

            # Capture frame state
            state = self.cpu.get_frame_state()
            frames.append(state)

            # Detect note events
            for voice in range(3):
                freq, pw, ctrl, ad, sr = state.get_voice(voice)
                adsr = (ad << 8) | sr
                gate_on = bool(ctrl & 0x01)
                waveform = ctrl & 0xFE

                # Only analyze if waveform is active (not just gate)
                if ctrl >= 0x10:
                    note, note_name = self.freq_to_note(freq)

                    # Detect new note (gate transition or frequency change with gate)
                    is_new_note = False
                    if gate_on and not prev_gate[voice]:
                        is_new_note = True
                    elif gate_on and note != prev_notes[voice]:
                        is_new_note = True

                    if is_new_note:
                        notes.append(NoteEvent(
                            frame=frame,
                            voice=voice,
                            note=note,
                            note_name=note_name,
                            frequency=freq,
                            waveform=waveform,
                            adsr=adsr,
                            pulse=pw,
                            gate_on=gate_on,
                        ))

                    prev_notes[voice] = note
                    prev_gate[voice] = gate_on
                else:
                    prev_gate[voice] = False

            prev_state = state

        return PlaybackResult(
            header=self.header,
            frames=frames,
            writes=self.cpu.sid_writes,
            notes=notes,
            duration_seconds=seconds,
            total_cycles=total_cycles,
        )

    def dump_frames(self, result: PlaybackResult, start: int = 0, count: int = 100) -> str:
        """Generate formatted frame dump similar to siddump.

        Args:
            result: PlaybackResult from play()
            start: Starting frame
            count: Number of frames to dump

        Returns:
            Formatted string
        """
        lines = []
        lines.append(f"SID: {result.header.name} by {result.header.author}")
        lines.append(f"Load: ${result.header.load_address:04X}  Init: ${result.header.init_address:04X}  Play: ${result.header.play_address:04X}")
        lines.append("")
        lines.append("| Frame | Freq1 Note WF ADSR Pul | Freq2 Note WF ADSR Pul | Freq3 Note WF ADSR Pul | FCut Res Vol |")
        lines.append("+-------+-----------------------+-----------------------+-----------------------+--------------+")

        prev_state: Optional[FrameState] = None

        for i, state in enumerate(result.frames[start:start + count]):
            frame = start + i
            parts = [f"| {frame:5d} |"]

            for voice in range(3):
                freq, pw, ctrl, ad, sr = state.get_voice(voice)
                adsr = (ad << 8) | sr

                # Frequency and note
                if ctrl >= 0x10:
                    note, note_name = self.freq_to_note(freq)
                    freq_str = f"{freq:04X}"
                    note_str = note_name
                else:
                    freq_str = f"{freq:04X}"
                    note_str = "..."

                # Show changes vs previous frame
                if prev_state:
                    prev_freq, prev_pw, prev_ctrl, prev_ad, prev_sr = prev_state.get_voice(voice)
                    if freq == prev_freq:
                        freq_str = "...."
                    if ctrl == prev_ctrl:
                        wf_str = ".."
                    else:
                        wf_str = f"{ctrl:02X}"
                    if (ad << 8 | sr) == (prev_ad << 8 | prev_sr):
                        adsr_str = "...."
                    else:
                        adsr_str = f"{adsr:04X}"
                    if pw == prev_pw:
                        pw_str = "..."
                    else:
                        pw_str = f"{pw:03X}"
                else:
                    wf_str = f"{ctrl:02X}"
                    adsr_str = f"{adsr:04X}"
                    pw_str = f"{pw:03X}"

                parts.append(f" {freq_str} {note_str} {wf_str} {adsr_str} {pw_str} |")

            # Filter
            fc = state.fc
            res_filt = state.res_filt
            mode_vol = state.mode_vol

            if prev_state:
                if fc == prev_state.fc:
                    fc_str = "...."
                else:
                    fc_str = f"{fc:04X}"
                if res_filt == prev_state.res_filt:
                    res_str = ".."
                else:
                    res_str = f"{res_filt:02X}"
                if (mode_vol & 0x0F) == (prev_state.mode_vol & 0x0F):
                    vol_str = "."
                else:
                    vol_str = f"{mode_vol & 0x0F:X}"
            else:
                fc_str = f"{fc:04X}"
                res_str = f"{res_filt:02X}"
                vol_str = f"{mode_vol & 0x0F:X}"

            parts.append(f" {fc_str} {res_str}  {vol_str}  |")
            lines.append("".join(parts))

            prev_state = state

        return "\n".join(lines)


def compare_playback(result1: PlaybackResult, result2: PlaybackResult,
                     tolerance_freq: int = 0, tolerance_frames: int = 0) -> Dict:
    """Compare two playback results for differences.

    Args:
        result1: First playback result (reference)
        result2: Second playback result (test)
        tolerance_freq: Frequency difference tolerance
        tolerance_frames: Frame count difference tolerance

    Returns:
        Dictionary with comparison statistics and differences
    """
    min_frames = min(len(result1.frames), len(result2.frames))

    # Track differences per frame
    frame_diffs = 0
    voice_diffs = [0, 0, 0]
    freq_diffs = 0
    wave_diffs = 0
    adsr_diffs = 0
    filter_diffs = 0

    differences = []

    for i in range(min_frames):
        s1, s2 = result1.frames[i], result2.frames[i]
        frame_has_diff = False

        for v in range(3):
            f1, p1, c1, a1, r1 = s1.get_voice(v)
            f2, p2, c2, a2, r2 = s2.get_voice(v)

            if abs(f1 - f2) > tolerance_freq:
                freq_diffs += 1
                voice_diffs[v] += 1
                frame_has_diff = True
                differences.append({
                    'frame': i,
                    'voice': v,
                    'type': 'freq',
                    'expected': f1,
                    'actual': f2,
                })

            if c1 != c2:
                wave_diffs += 1
                voice_diffs[v] += 1
                frame_has_diff = True
                differences.append({
                    'frame': i,
                    'voice': v,
                    'type': 'ctrl',
                    'expected': c1,
                    'actual': c2,
                })

            if (a1 << 8 | r1) != (a2 << 8 | r2):
                adsr_diffs += 1
                voice_diffs[v] += 1
                frame_has_diff = True

        # Filter comparison
        if s1.fc != s2.fc or s1.res_filt != s2.res_filt or (s1.mode_vol & 0x0F) != (s2.mode_vol & 0x0F):
            filter_diffs += 1
            frame_has_diff = True

        if frame_has_diff:
            frame_diffs += 1

    # Calculate accuracy
    total_comparisons = min_frames * 3 * 4  # 3 voices, 4 params per voice
    total_diffs = freq_diffs + wave_diffs + adsr_diffs
    accuracy = (total_comparisons - total_diffs) / total_comparisons * 100 if total_comparisons > 0 else 0

    return {
        'frames_compared': min_frames,
        'frames_with_diffs': frame_diffs,
        'accuracy_percent': accuracy,
        'freq_diffs': freq_diffs,
        'wave_diffs': wave_diffs,
        'adsr_diffs': adsr_diffs,
        'filter_diffs': filter_diffs,
        'voice_diffs': voice_diffs,
        'first_differences': differences[:50],  # First 50 differences
    }


def main():
    """Test the SID player."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m sidm2.sid_player <sidfile> [seconds]")
        print("")
        print("Options:")
        print("  sidfile  Path to .sid file")
        print("  seconds  Duration to analyze (default: 10)")
        return 1

    filepath = sys.argv[1]
    seconds = float(sys.argv[2]) if len(sys.argv) > 2 else 10

    player = SIDPlayer()
    print(f"Loading {filepath}...")
    header = player.load_sid(filepath)

    print(f"\nSID Info:")
    print(f"  Name: {header.name}")
    print(f"  Author: {header.author}")
    print(f"  Copyright: {header.copyright}")
    print(f"  Load: ${header.load_address:04X}")
    print(f"  Init: ${header.init_address:04X}")
    print(f"  Play: ${header.play_address:04X}")
    print(f"  Songs: {header.songs}")

    print(f"\nPlaying for {seconds} seconds...")
    result = player.play(seconds=seconds)

    print(f"\nPlayback Stats:")
    print(f"  Frames: {len(result.frames)}")
    print(f"  Total cycles: {result.total_cycles}")
    print(f"  Register writes: {len(result.writes)}")
    print(f"  Notes detected: {len(result.notes)}")

    # Show first few notes
    if result.notes:
        print(f"\nFirst 20 notes:")
        for note in result.notes[:20]:
            print(f"  Frame {note.frame:4d}: Voice {note.voice+1} {note.note_name} "
                  f"(${note.frequency:04X}) WF=${note.waveform:02X} ADSR=${note.adsr:04X}")

    # Show frame dump
    print("\n" + player.dump_frames(result, 0, 50))

    return 0


if __name__ == '__main__':
    exit(main())
