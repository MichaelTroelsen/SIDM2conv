#!/usr/bin/env python3
"""
Complete Python implementation of siddump v1.08

This is a drop-in replacement for siddump.exe that uses the Python CPU6502Emulator.
Provides frame-by-frame SID register capture and analysis for validation and debugging.

Based on: G5/siddump108/siddump.c (547 lines) + tools/cpu.c (1,217 lines)
Python implementation: ~600 lines (vs 1,764 lines C)

Usage:
    python siddump_complete.py <sidfile> [options]

Options:
    -a<value>  Accumulator value on init (subtune number) default = 0
    -c<value>  Frequency recalibration (note frequency in hex)
    -d<value>  Select calibration note (abs.notation 80-DF). Default middle-C (B0)
    -f<value>  First frame to display, default 0
    -l         Low-resolution mode (only display 1 row per note)
    -n<value>  Note spacing, default 0 (none)
    -o<value>  "Oldnote-sticky" factor. Default 1, increase for better vibrato display
    -p<value>  Pattern spacing, default 0 (none)
    -s         Display time in minutes:seconds:frame format
    -t<value>  Playback time in seconds, default 60
    -z         Include CPU cycles+rastertime (PAL)+rastertime, badline corrected

Author: Python port by Claude Sonnet 4.5 (2025-12-22)
Original: siddump v1.08 (C implementation)
"""

import sys
import os
import struct
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Add parent directory to path to import cpu6502_emulator
sys.path.insert(0, str(Path(__file__).parent.parent))
from sidm2.cpu6502_emulator import CPU6502Emulator


# ==============================================================================
# Constants and Data Structures
# ==============================================================================

MAX_INSTR = 0x100000  # Maximum instructions per init/play routine

# Note names (C-0 to B-7, 96 notes total)
NOTE_NAMES = [
    "C-0", "C#0", "D-0", "D#0", "E-0", "F-0", "F#0", "G-0", "G#0", "A-0", "A#0", "B-0",
    "C-1", "C#1", "D-1", "D#1", "E-1", "F-1", "F#1", "G-1", "G#1", "A-1", "A#1", "B-1",
    "C-2", "C#2", "D-2", "D#2", "E-2", "F-2", "F#2", "G-2", "G#2", "A-2", "A#2", "B-2",
    "C-3", "C#3", "D-3", "D#3", "E-3", "F-3", "F#3", "G-3", "G#3", "A-3", "A#3", "B-3",
    "C-4", "C#4", "D-4", "D#4", "E-4", "F-4", "F#4", "G-4", "G#4", "A-4", "A#4", "B-4",
    "C-5", "C#5", "D-5", "D#5", "E-5", "F-5", "F#5", "G-5", "G#5", "A-5", "A#5", "B-5",
    "C-6", "C#6", "D-6", "D#6", "E-6", "F-6", "F#6", "G-6", "G#6", "A-6", "A#6", "B-6",
    "C-7", "C#7", "D-7", "D#7", "E-7", "F-7", "F#7", "G-7", "G#7", "A-7", "A#7", "B-7"
]

# Frequency table - low bytes (96 notes, C-0 to B-7)
FREQ_TBL_LO = bytes([
    0x17, 0x27, 0x39, 0x4b, 0x5f, 0x74, 0x8a, 0xa1, 0xba, 0xd4, 0xf0, 0x0e,
    0x2d, 0x4e, 0x71, 0x96, 0xbe, 0xe8, 0x14, 0x43, 0x74, 0xa9, 0xe1, 0x1c,
    0x5a, 0x9c, 0xe2, 0x2d, 0x7c, 0xcf, 0x28, 0x85, 0xe8, 0x52, 0xc1, 0x37,
    0xb4, 0x39, 0xc5, 0x5a, 0xf7, 0x9e, 0x4f, 0x0a, 0xd1, 0xa3, 0x82, 0x6e,
    0x68, 0x71, 0x8a, 0xb3, 0xee, 0x3c, 0x9e, 0x15, 0xa2, 0x46, 0x04, 0xdc,
    0xd0, 0xe2, 0x14, 0x67, 0xdd, 0x79, 0x3c, 0x29, 0x44, 0x8d, 0x08, 0xb8,
    0xa1, 0xc5, 0x28, 0xcd, 0xba, 0xf1, 0x78, 0x53, 0x87, 0x1a, 0x10, 0x71,
    0x42, 0x89, 0x4f, 0x9b, 0x74, 0xe2, 0xf0, 0xa6, 0x0e, 0x33, 0x20, 0xff
])

# Frequency table - high bytes
FREQ_TBL_HI = bytes([
    0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x01, 0x02,
    0x02, 0x02, 0x02, 0x02, 0x02, 0x02, 0x03, 0x03, 0x03, 0x03, 0x03, 0x04,
    0x04, 0x04, 0x04, 0x05, 0x05, 0x05, 0x06, 0x06, 0x06, 0x07, 0x07, 0x08,
    0x08, 0x09, 0x09, 0x0a, 0x0a, 0x0b, 0x0c, 0x0d, 0x0d, 0x0e, 0x0f, 0x10,
    0x11, 0x12, 0x13, 0x14, 0x15, 0x17, 0x18, 0x1a, 0x1b, 0x1d, 0x1f, 0x20,
    0x22, 0x24, 0x27, 0x29, 0x2b, 0x2e, 0x31, 0x34, 0x37, 0x3a, 0x3e, 0x41,
    0x45, 0x49, 0x4e, 0x52, 0x57, 0x5c, 0x62, 0x68, 0x6e, 0x75, 0x7c, 0x83,
    0x8b, 0x93, 0x9c, 0xa5, 0xaf, 0xb9, 0xc4, 0xd0, 0xdd, 0xea, 0xf8, 0xff
])

# Filter type names
FILTER_NAMES = ["Off", "Low", "Bnd", "L+B", "Hi ", "L+H", "B+H", "LBH"]


@dataclass
class Channel:
    """SID channel state (one voice)."""
    freq: int = 0      # Frequency (16-bit)
    pulse: int = 0     # Pulse width (12-bit, 0x000-0xFFF)
    wave: int = 0      # Waveform + gate control byte
    adsr: int = 0      # ADSR envelope (16-bit: AD|SR)
    note: int = -1     # Detected note number (0-95, -1=invalid)


@dataclass
class Filter:
    """SID filter state."""
    cutoff: int = 0    # Filter cutoff (11-bit)
    ctrl: int = 0      # Filter control (voice routing)
    type: int = 0      # Filter type + master volume


# ==============================================================================
# SID File Parser
# ==============================================================================

@dataclass
class SIDHeader:
    """PSID/RSID file header."""
    magic: str              # 'PSID' or 'RSID'
    version: int           # Header version (1 or 2)
    data_offset: int       # Offset to C64 data
    load_address: int      # Load address (0 = read from data)
    init_address: int      # Init routine address
    play_address: int      # Play routine address
    songs: int             # Number of songs
    start_song: int        # Default song (1-based)
    speed: int             # Speed bits (0=CIA, 1=VBI)
    name: str              # Song name (32 chars)
    author: str            # Author (32 chars)
    copyright: str         # Copyright (32 chars)


def parse_sid_file(filename: str) -> Tuple[SIDHeader, bytes]:
    """Parse SID file and return header + C64 data.

    Args:
        filename: Path to .sid file

    Returns:
        Tuple of (SIDHeader, c64_data)

    Raises:
        ValueError: If file is not a valid SID file
    """
    with open(filename, 'rb') as f:
        data = f.read()

    if len(data) < 0x7C:
        raise ValueError("File too small to be a valid SID file")

    # Parse header (big-endian)
    magic = data[0:4].decode('ascii', errors='replace')
    if magic not in ('PSID', 'RSID'):
        raise ValueError(f"Invalid SID file magic: {magic}")

    version = struct.unpack('>H', data[4:6])[0]
    data_offset = struct.unpack('>H', data[6:8])[0]
    load_address = struct.unpack('>H', data[8:10])[0]
    init_address = struct.unpack('>H', data[10:12])[0]
    play_address = struct.unpack('>H', data[12:14])[0]
    songs = struct.unpack('>H', data[14:16])[0]
    start_song = struct.unpack('>H', data[16:18])[0]
    speed = struct.unpack('>I', data[18:22])[0]

    # Parse strings (null-terminated, max 32 chars)
    name = data[22:54].split(b'\x00')[0].decode('ascii', errors='replace')
    author = data[54:86].split(b'\x00')[0].decode('ascii', errors='replace')
    copyright = data[86:118].split(b'\x00')[0].decode('ascii', errors='replace')

    header = SIDHeader(
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
        copyright=copyright
    )

    # Extract C64 data
    c64_data = data[data_offset:]

    # If load_address is 0, read it from first 2 bytes of data (little-endian)
    if load_address == 0 and len(c64_data) >= 2:
        load_address = c64_data[0] | (c64_data[1] << 8)
        header.load_address = load_address
        c64_data = c64_data[2:]  # Skip load address bytes

    return header, c64_data


# ==============================================================================
# Note Detection
# ==============================================================================

def detect_note(freq: int, prev_note: int, oldnotefactor: int,
                freq_tbl_lo: bytes, freq_tbl_hi: bytes) -> int:
    """Detect note number from frequency value.

    Uses frequency table matching with distance calculation.
    Favors previous note if frequencies are close (vibrato detection).

    Args:
        freq: Current frequency value (16-bit)
        prev_note: Previous note number (for sticky note detection)
        oldnotefactor: Factor to favor old note (1=no favor, higher=more sticky)
        freq_tbl_lo: Frequency table low bytes
        freq_tbl_hi: Frequency table high bytes

    Returns:
        Note number (0-95) or -1 if no match
    """
    if freq == 0:
        return -1

    best_note = 0
    min_dist = 0x7FFFFFFF

    for note in range(96):
        table_freq = freq_tbl_lo[note] | (freq_tbl_hi[note] << 8)
        dist = abs(freq - table_freq)

        # Favor the old note to handle vibrato better
        if note == prev_note and oldnotefactor > 1:
            dist //= oldnotefactor

        if dist < min_dist:
            min_dist = dist
            best_note = note

    return best_note


# ==============================================================================
# Output Formatting
# ==============================================================================

def format_voice_column(chn: Channel, prevchn: Channel, prevchn2: Channel,
                       is_first_frame: bool, newnote: bool, lowres: bool,
                       freq_delta: int) -> str:
    """Format a single voice column for output.

    Handles three output modes:
    1. New note event: "3426  G-5 C3  21 0F01 450"
    2. Frequency change: "2BD6 (E-5 C0) .. .... 4A0"
    3. No change: "....  ... ..  .. .... ..."

    Args:
        chn: Current channel state
        prevchn: Previous frame channel state
        prevchn2: Two frames ago channel state (for gate detection)
        is_first_frame: True if this is the first displayed frame
        newnote: True if this is a new note in lowres mode
        lowres: True if low-resolution mode enabled
        freq_delta: Frequency change from prevchn2

    Returns:
        Formatted string for this voice column (27 chars)
    """
    output = []

    # Frequency display
    if is_first_frame or prevchn.note == -1 or chn.freq != prevchn.freq:
        output.append(f"{chn.freq:04X} ")

        # Note display (only if wave >= 0x10, meaning voice is active)
        if chn.wave >= 0x10:
            # New note vs same note with frequency change
            if chn.note != prevchn.note:
                if prevchn.note == -1:
                    # Brand new note
                    output.append(f" {NOTE_NAMES[chn.note]} {chn.note | 0x80:02X}  ")
                else:
                    # Note changed
                    output.append(f"({NOTE_NAMES[chn.note]} {chn.note | 0x80:02X}) ")
            else:
                # Same note, frequency changed (vibrato/slide)
                if freq_delta > 0:
                    output.append(f"(+ {freq_delta:04X}) ")
                elif freq_delta < 0:
                    output.append(f"(- {-freq_delta:04X}) ")
                else:
                    output.append(" ... ..  ")
        else:
            output.append(" ... ..  ")
    else:
        output.append("....  ... ..  ")

    # Waveform
    if is_first_frame or newnote or chn.wave != prevchn.wave:
        output.append(f"{chn.wave:02X} ")
    else:
        output.append(".. ")

    # ADSR
    if is_first_frame or newnote or chn.adsr != prevchn.adsr:
        output.append(f"{chn.adsr:04X} ")
    else:
        output.append(".... ")

    # Pulse width
    if is_first_frame or newnote or chn.pulse != prevchn.pulse:
        output.append(f"{chn.pulse:03X} ")
    else:
        output.append("... ")

    return ''.join(output)


def format_frame_row(frame_num: int, channels: List[Channel],
                    prev_channels: List[Channel], prev_channels2: List[Channel],
                    filt: Filter, prevfilt: Filter, is_first_frame: bool,
                    timeseconds: bool, lowres: bool, spacing: int,
                    oldnotefactor: int, cycles: int, profiling: bool) -> Tuple[str, bool]:
    """Format complete frame row for output.

    Args:
        frame_num: Frame number (0-based from start)
        channels: Current frame channel states [3]
        prev_channels: Previous frame states [3]
        prev_channels2: Two frames ago states [3] (for gate detection)
        filt: Current filter state
        prevfilt: Previous filter state
        is_first_frame: True if this is the first displayed frame
        timeseconds: True to display time as mm:ss.ff instead of frame number
        lowres: True for low-resolution mode
        spacing: Note spacing (for lowres mode)
        oldnotefactor: Sticky note factor
        cycles: CPU cycles for profiling
        profiling: True to include profiling info

    Returns:
        Tuple of (formatted_string, should_print) - should_print only for lowres mode
    """
    output = []
    should_print = True

    # Frame/time column
    if timeseconds:
        mins = frame_num // 3000
        secs = (frame_num // 50) % 60
        frames = frame_num % 50
        output.append(f"|{mins:01d}:{secs:02d}.{frames:02d}| ")
    else:
        output.append(f"| {frame_num:5d} | ")

    # Process each voice
    for voice in range(3):
        chn = channels[voice]
        prevchn = prev_channels[voice]
        prevchn2 = prev_channels2[voice]

        newnote = False
        freq_delta = chn.freq - prevchn2.freq

        # Keyoff-keyon sequence detection
        if chn.wave >= 0x10:
            if (chn.wave & 1) and ((not (prevchn2.wave & 1)) or (prevchn2.wave < 0x10)):
                prevchn.note = -1

        # Format this voice column
        voice_str = format_voice_column(chn, prevchn, prevchn2, is_first_frame,
                                       newnote, lowres, freq_delta)
        output.append(voice_str)
        output.append("| ")

    # Filter cutoff
    if is_first_frame or filt.cutoff != prevfilt.cutoff:
        output.append(f"{filt.cutoff:04X} ")
    else:
        output.append(".... ")

    # Filter control
    if is_first_frame or filt.ctrl != prevfilt.ctrl:
        output.append(f"{filt.ctrl:02X} ")
    else:
        output.append(".. ")

    # Filter type/passband
    filt_type_idx = (filt.type >> 4) & 0x7
    prevfilt_type_idx = (prevfilt.type >> 4) & 0x7
    if is_first_frame or filt_type_idx != prevfilt_type_idx:
        output.append(f"{FILTER_NAMES[filt_type_idx]} ")
    else:
        output.append("... ")

    # Master volume
    if is_first_frame or (filt.type & 0xF) != (prevfilt.type & 0xF):
        output.append(f"{filt.type & 0xF:01X} ")
    else:
        output.append(". ")

    # Profiling info (cycles, raster lines)
    if profiling:
        rasterlines = (cycles + 62) // 63
        badlines = (cycles + 503) // 504
        rasterlines_bad = (badlines * 40 + cycles + 62) // 63
        output.append(f"| {cycles:4d} {rasterlines:02X} {rasterlines_bad:02X} ")

    output.append("|")

    return ''.join(output), should_print


# ==============================================================================
# Main Siddump Logic
# ==============================================================================

def run_siddump(filename: str, args):
    """Run siddump analysis on SID file.

    Args:
        filename: Path to .sid file
        args: Parsed command-line arguments
    """
    # Parse SID file
    try:
        header, c64_data = parse_sid_file(filename)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Create frequency tables (modifiable for calibration)
    freq_tbl_lo = bytearray(FREQ_TBL_LO)
    freq_tbl_hi = bytearray(FREQ_TBL_HI)

    # Frequency recalibration if requested
    if args.basefreq:
        basenote = args.basenote & 0x7F
        if basenote < 0 or basenote > 95:
            print("Warning: Calibration note out of range. Aborting recalibration.")
        else:
            import math
            for note in range(96):
                note_offset = note - basenote
                freq = args.basefreq * (2.0 ** (note_offset / 12.0))
                freq_int = int(freq)
                if freq_int > 0xFFFF:
                    freq_int = 0xFFFF
                freq_tbl_lo[note] = freq_int & 0xFF
                freq_tbl_hi[note] = (freq_int >> 8) & 0xFF

    # Create CPU emulator
    cpu = CPU6502Emulator(capture_writes=False)  # We'll read registers manually

    # Load C64 data into memory
    load_address = header.load_address
    if load_address + len(c64_data) >= 0x10000:
        print("Error: SID data continues past end of C64 memory.")
        return 1

    cpu.load_memory(c64_data, load_address)

    # Print header info
    print(f"Load address: ${load_address:04X} Init address: ${header.init_address:04X} Play address: ${header.play_address:04X}")
    print(f"Calling initroutine with subtune {args.subtune}")

    # Run init routine
    cpu.mem[0x01] = 0x37  # I/O visible, BASIC ROM disabled
    cpu.reset(header.init_address, args.subtune, 0, 0)

    instr_count = 0
    while instr_count < MAX_INSTR:
        # VIC simulation for SID detection loops
        cpu.mem[0xD012] = (cpu.mem[0xD012] + 1) & 0xFF
        if cpu.mem[0xD012] == 0 or ((cpu.mem[0xD011] & 0x80) and cpu.mem[0xD012] >= 0x38):
            cpu.mem[0xD011] ^= 0x80
            cpu.mem[0xD012] = 0x00

        if not cpu.run_instruction():
            break

        # Check for Kernal exit
        if (cpu.mem[0x01] & 0x07) != 0x05 and (cpu.pc == 0xEA31 or cpu.pc == 0xEA81):
            break

        instr_count += 1

    if instr_count >= MAX_INSTR:
        print(f"Warning: CPU executed a high number of instructions in init, breaking")

    # Determine play address
    play_address = header.play_address
    if play_address == 0:
        print("Warning: SID has play address 0, reading from interrupt vector instead")
        if (cpu.mem[0x01] & 0x07) == 0x05:
            play_address = cpu.mem[0xFFFE] | (cpu.mem[0xFFFF] << 8)
        else:
            play_address = cpu.mem[0x314] | (cpu.mem[0x315] << 8)
        print(f"New play address is ${play_address:04X}")

    # Initialize channel structures
    channels = [Channel() for _ in range(3)]
    prev_channels = [Channel() for _ in range(3)]
    prev_channels2 = [Channel() for _ in range(3)]
    filt = Filter()
    prevfilt = Filter()

    # Print frame loop header
    total_frames = args.seconds * 50
    print(f"Calling playroutine for {total_frames} frames, starting from frame {args.firstframe}")
    middle_c_freq = freq_tbl_lo[48] | (freq_tbl_hi[48] << 8)
    print(f"Middle C frequency is ${middle_c_freq:04X}\n")

    # Print table header
    print("| Frame | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | Freq Note/Abs WF ADSR Pul | FCut RC Typ V |", end='')
    if args.profiling:
        print(" Cycl RL RB |", end='')
    print()

    print("+-------+---------------------------+---------------------------+---------------------------+---------------+", end='')
    if args.profiling:
        print("------------+", end='')
    print()

    # Frame loop
    frame = 0
    counter = 0
    rows = 0

    while frame < args.firstframe + total_frames:
        # Run play routine
        cpu.reset(play_address, 0, 0, 0)

        instr_count = 0
        while instr_count < MAX_INSTR:
            if not cpu.run_instruction():
                break

            # Check for Kernal exit
            if (cpu.mem[0x01] & 0x07) != 0x05 and (cpu.pc == 0xEA31 or cpu.pc == 0xEA81):
                break

            instr_count += 1

        if instr_count >= MAX_INSTR:
            print("Error: CPU executed abnormally high amount of instructions in playroutine, exiting")
            return 1

        # Read SID registers
        for voice in range(3):
            base = 0xD400 + voice * 7
            channels[voice].freq = cpu.mem[base] | (cpu.mem[base + 1] << 8)
            channels[voice].pulse = (cpu.mem[base + 2] | (cpu.mem[base + 3] << 8)) & 0xFFF
            channels[voice].wave = cpu.mem[base + 4]
            channels[voice].adsr = cpu.mem[base + 6] | (cpu.mem[base + 5] << 8)

            # Detect note
            if channels[voice].wave >= 0x10:
                channels[voice].note = detect_note(
                    channels[voice].freq,
                    prev_channels[voice].note,
                    args.oldnotefactor,
                    freq_tbl_lo,
                    freq_tbl_hi
                )
            else:
                channels[voice].note = -1

        filt.cutoff = (cpu.mem[0xD415] << 5) | (cpu.mem[0xD416] << 8)
        filt.ctrl = cpu.mem[0xD417]
        filt.type = cpu.mem[0xD418]

        # Display frame (if in range)
        if frame >= args.firstframe:
            display_frame = frame - args.firstframe
            is_first = (frame == args.firstframe)

            row_str, should_print = format_frame_row(
                display_frame,
                channels,
                prev_channels,
                prev_channels2,
                filt,
                prevfilt,
                is_first,
                args.timeseconds,
                args.lowres,
                args.spacing,
                args.oldnotefactor,
                cpu.cycles,
                args.profiling
            )

            # Low-res mode: only print every Nth row
            if not args.lowres or (display_frame % args.spacing == 0):
                print(row_str)

                # Update previous states for displayed frames
                for voice in range(3):
                    prev_channels[voice] = Channel(
                        freq=channels[voice].freq,
                        pulse=channels[voice].pulse,
                        wave=channels[voice].wave,
                        adsr=channels[voice].adsr,
                        note=channels[voice].note
                    )
                prevfilt = Filter(
                    cutoff=filt.cutoff,
                    ctrl=filt.ctrl,
                    type=filt.type
                )

            # Pattern/note spacing
            if args.spacing:
                counter += 1
                if counter >= args.spacing:
                    counter = 0
                    if args.pattspacing:
                        rows += 1
                        if rows >= args.pattspacing:
                            rows = 0
                            print("+=======+===========================+===========================+===========================+===============+")
                        else:
                            if not args.lowres:
                                print("+-------+---------------------------+---------------------------+---------------------------+---------------+")
                    else:
                        if not args.lowres:
                            print("+-------+---------------------------+---------------------------+---------------------------+---------------+")

        # Update two-frame-ago state for gate detection
        for voice in range(3):
            prev_channels2[voice] = Channel(
                freq=channels[voice].freq,
                pulse=channels[voice].pulse,
                wave=channels[voice].wave,
                adsr=channels[voice].adsr,
                note=channels[voice].note
            )

        frame += 1

    return 0


# ==============================================================================
# Command Line Interface
# ==============================================================================

def parse_arguments():
    """Parse command-line arguments matching siddump.exe interface."""
    parser = argparse.ArgumentParser(
        description='Python siddump - Frame-by-frame SID register analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python siddump_complete.py music.sid -t30
    python siddump_complete.py music.sid -a1 -t60 -z
    python siddump_complete.py music.sid -c0117 -d80 -t120

Warning: CPU emulation may be inaccurate for some edge cases.
        """
    )

    parser.add_argument('sidfile', help='SID file to analyze')
    parser.add_argument('-a', '--subtune', type=int, default=0,
                       help='Accumulator value on init (subtune number), default=0')
    parser.add_argument('-c', '--basefreq', type=lambda x: int(x, 16), default=0,
                       help='Frequency recalibration (note frequency in hex)')
    parser.add_argument('-d', '--basenote', type=lambda x: int(x, 16), default=0xB0,
                       help='Select calibration note (abs.notation 80-DF), default=B0 (middle C)')
    parser.add_argument('-f', '--firstframe', type=int, default=0,
                       help='First frame to display, default=0')
    parser.add_argument('-l', '--lowres', action='store_true',
                       help='Low-resolution mode (only display 1 row per note)')
    parser.add_argument('-n', '--spacing', type=int, default=0,
                       help='Note spacing, default=0 (none)')
    parser.add_argument('-o', '--oldnotefactor', type=int, default=1,
                       help='"Oldnote-sticky" factor, default=1 (increase for better vibrato display)')
    parser.add_argument('-p', '--pattspacing', type=int, default=0,
                       help='Pattern spacing, default=0 (none)')
    parser.add_argument('-s', '--timeseconds', action='store_true',
                       help='Display time in minutes:seconds:frame format')
    parser.add_argument('-t', '--seconds', type=int, default=60,
                       help='Playback time in seconds, default=60')
    parser.add_argument('-z', '--profiling', action='store_true',
                       help='Include CPU cycles+rastertime (PAL)+rastertime, badline corrected')

    args = parser.parse_args()

    # Validate arguments
    if args.oldnotefactor < 1:
        args.oldnotefactor = 1

    if args.lowres and not args.spacing:
        args.lowres = False

    return args


def main():
    """Main entry point."""
    args = parse_arguments()

    if not os.path.exists(args.sidfile):
        print(f"Error: File not found: {args.sidfile}", file=sys.stderr)
        return 1

    try:
        return run_siddump(args.sidfile, args)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
