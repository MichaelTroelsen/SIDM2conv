"""
SID to MIDI Converter using CPU Emulation (Python-only, no Ruby required)

This module emulates the 6502 CPU to execute SID files and captures
SID register writes, then converts them to MIDI format. This is a
pure-Python alternative to SIDtool.

Usage:
    converter = SIDToMidiConverter('song.sid')
    converter.run(frames=5000)
    converter.export_midi('song.mid')
"""

import struct
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from .sid_player import SIDPlayer

logger = logging.getLogger(__name__)

try:
    from mido import MidiFile, MidiTrack, Message, MetaMessage
    MIDO_AVAILABLE = True
except ImportError:
    MIDO_AVAILABLE = False
    logger.warning("mido library not available. Install with: pip install mido")


@dataclass
class MIDINoteEvent:
    """A single MIDI note event."""
    voice: int          # 0-2 (SID voices 1-3)
    frame: int          # Frame number
    midi_note: int      # MIDI note number (0-127)
    velocity: int       # MIDI velocity (0-127)
    is_note_on: bool    # True = note on, False = note off


class SIDToMidiConverter:
    """Convert SID files to MIDI using CPU emulation."""

    # SID frequency to MIDI note conversion table
    # Based on PAL SID frequency table (985248Hz / 16)
    # MIDI note 60 (Middle C) = SID frequency $1168
    SID_FREQ_TO_MIDI = {}

    # Generate frequency table (will be populated in __init__)
    MIDI_NOTE_FREQUENCIES = []

    def __init__(self, sid_path: str):
        """Initialize converter

        Args:
            sid_path: Path to SID file
        """
        self.sid_path = sid_path
        self.emulator = None
        self.midi_events: List[MIDINoteEvent] = []
        self.current_notes = [None, None, None]  # Current note for each voice
        self.tempo_bpm = 150  # PAL 50Hz ≈ 150 BPM at 4/4 time

        if not MIDO_AVAILABLE:
            raise ImportError("mido library required. Install with: pip install mido")

        # Initialize frequency conversion table
        self._init_freq_table()

        logger.info(f"SID to MIDI converter initialized: {sid_path}")

    def _init_freq_table(self):
        """Initialize SID frequency to MIDI note conversion table."""
        # MIDI note frequencies (A440 tuning)
        # MIDI note 69 = A4 = 440 Hz
        # Each semitone = 2^(1/12) ratio

        for midi_note in range(128):
            freq_hz = 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
            self.MIDI_NOTE_FREQUENCIES.append(freq_hz)

        # SID frequency = (freq_hz * 16777216) / clock_rate
        # PAL clock rate = 985248 Hz
        # NTSC clock rate = 1022727 Hz
        # We'll use PAL for now

        clock_rate = 985248.0
        for midi_note in range(128):
            freq_hz = self.MIDI_NOTE_FREQUENCIES[midi_note]
            sid_freq = int((freq_hz * 16777216.0) / clock_rate)
            self.SID_FREQ_TO_MIDI[sid_freq] = midi_note

    def _sid_freq_to_midi_note(self, sid_freq: int) -> Optional[int]:
        """Convert SID frequency value to MIDI note number using SIDtool's formula.

        Args:
            sid_freq: SID frequency register value (16-bit)

        Returns:
            MIDI note number (0-127) or None if out of range
        """
        import math

        # SIDtool's approach (from synth.rb):
        # actual_frequency = sid_frequency * (CLOCK_FREQUENCY / 16777216)
        # midi_tone = (12 * (Math.log(frequency * 0.0022727272727) / Math.log(2))) + 69

        CLOCK_FREQUENCY = 985248.0  # PAL clock

        # Convert SID frequency to actual frequency in Hz
        actual_freq = sid_freq * (CLOCK_FREQUENCY / 16777216.0)

        # Convert to MIDI note (0.0022727272727 = 1/440)
        # Formula: 12 * log2(freq_hz / 440) + 69
        if actual_freq <= 0:
            return None

        midi_tone = (12 * (math.log(actual_freq / 440.0) / math.log(2))) + 69

        # Round to nearest integer (like SIDtool does)
        midi_note = round(midi_tone)

        # Validate range
        if midi_note < 0 or midi_note > 127:
            return None

        return midi_note

    def run(self, frames: int = 5000, song: int = 0):
        """Run CPU emulation and capture SID register writes.

        Args:
            frames: Number of frames to emulate (default 5000 = ~100 seconds)
            song: Song number to play (default 0)
        """
        logger.info(f"Emulating SID playback ({frames} frames)...")

        try:
            # Load and run SID player
            self.player = SIDPlayer(capture_writes=True)
            self.player.load_sid(self.sid_path)

            # Convert frames to seconds (PAL = 50 fps)
            seconds = frames / 50.0
            result = self.player.play(seconds=seconds, subtune=song)

            logger.info(f"  Emulated {frames} frames (~{seconds:.1f} seconds)")
            logger.info(f"  Captured {len(result.frames)} frame states")

            # Convert SID frame states to MIDI events (like SIDtool does)
            self._convert_to_midi_events(result.frames)

            logger.info(f"  Generated {len(self.midi_events)} MIDI events")

        except Exception as e:
            logger.error(f"Emulation failed: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _convert_to_midi_events(self, frame_states):
        """Convert frame states to MIDI note events using SIDtool's EXACT batch approach.

        SIDtool's approach (batch processing):
        1. Create synth when gate turns ON (tracks start_frame)
        2. While gate ON, collect frequency changes as controls
        3. When gate turns OFF, finalize synth
        4. Build MIDI using LAST frequency as initial tone, controls as note changes

        This matches SIDtool's Synth class behavior exactly.
        """
        if not frame_states:
            logger.warning("No frame states to convert")
            return

        logger.info("Converting SID frame states to MIDI notes...")

        # Track synths for each voice (like SIDtool's @synths array)
        @dataclass
        class Synth:
            start_frame: int
            last_frequency: int = 0
            last_midi_note: int = 0
            controls: list = None  # List of (frame, midi_note) tuples
            attack_decay: int = 0
            end_frame: int = 0  # Track when gate turns OFF
            released_at: int = 0  # Frame when gate went OFF (for ADSR calculation)

            def __post_init__(self):
                if self.controls is None:
                    self.controls = []

            def calculate_end_frame(self, frames_per_second=50):
                """Calculate end frame - simply when gate turned OFF.

                Note: In SID, ADSR envelope affects volume, not note duration.
                For MIDI export, we should end notes when gate turns OFF.
                """
                if self.released_at == 0:
                    # Synth never released (still playing at end)
                    # Return frame after last control, or start frame if no controls
                    if self.controls:
                        return self.controls[-1][0] + 1
                    return self.start_frame + 1

                # End frame is simply when gate turned OFF
                return self.released_at

            @staticmethod
            def _adsr_attack_to_seconds(attack):
                """Convert ADSR attack value to seconds (from SIDtool)."""
                table = [0.002, 0.008, 0.016, 0.024, 0.038, 0.056, 0.068, 0.08,
                        0.1, 0.25, 0.5, 0.8, 1, 3, 5, 8]
                return table[attack] if 0 <= attack < 16 else 0

            @staticmethod
            def _adsr_decay_to_seconds(decay):
                """Convert ADSR decay/release value to seconds (from SIDtool)."""
                table = [0.006, 0.024, 0.048, 0.072, 0.114, 0.168, 0.204, 0.240,
                        0.3, 0.75, 1.5, 2.4, 3, 9, 15, 24]
                return table[decay] if 0 <= decay < 16 else 0

        current_synths = [None, None, None]  # Current active synth per voice
        all_synths = [[], [], []]  # All synths per voice
        last_frame = 0  # Track last frame for end timing

        # Pass 1: Collect synths (like SIDtool's finish_frame loop)
        for frame_state in frame_states:
            last_frame = frame_state.frame

            for voice in range(3):
                # Get voice state
                if voice == 0:
                    freq, ctrl, ad = frame_state.freq1, frame_state.ctrl1, frame_state.ad1
                elif voice == 1:
                    freq, ctrl, ad = frame_state.freq2, frame_state.ctrl2, frame_state.ad2
                else:
                    freq, ctrl, ad = frame_state.freq3, frame_state.ctrl3, frame_state.ad3

                gate = (ctrl & 0x01) != 0

                if gate:
                    if freq > 0:
                        # Like SIDtool: create synth if needed
                        if current_synths[voice] is None:
                            current_synths[voice] = Synth(
                                start_frame=frame_state.frame,
                                attack_decay=ad
                            )
                            all_synths[voice].append(current_synths[voice])

                        synth = current_synths[voice]

                        # Like synth.rb frequency setter: check if MIDI note changed
                        current_midi = self._sid_freq_to_midi_note(freq)
                        if current_midi is not None:
                            # If we already have a frequency, check if MIDI note changed
                            if synth.last_frequency > 0:
                                previous_midi = synth.last_midi_note
                                if current_midi != previous_midi:
                                    # Add control event (like SIDtool's @controls << [frame, midi])
                                    synth.controls.append((frame_state.frame, current_midi))

                            # Always update last frequency (like SIDtool's @frequency = frequency)
                            synth.last_frequency = freq
                            synth.last_midi_note = current_midi
                else:
                    # Gate OFF - release synth (record release frame for ADSR)
                    if current_synths[voice] is not None:
                        current_synths[voice].released_at = frame_state.frame
                        current_synths[voice] = None

        # Pass 2: Build MIDI events (like SIDtool's build_track)
        for voice in range(3):
            for synth in all_synths[voice]:
                if synth.last_frequency == 0:
                    continue  # Skip empty synths

                # Initial note ON (using LAST frequency as tone, like SIDtool)
                attack = (synth.attack_decay >> 4) & 0x0F
                velocity = min(127, max(64, 64 + attack * 4))

                self.midi_events.append(MIDINoteEvent(
                    voice=voice,
                    frame=synth.start_frame,
                    midi_note=synth.last_midi_note,
                    velocity=velocity,
                    is_note_on=True
                ))

                current_tone = synth.last_midi_note

                # Control events (note changes while gate ON)
                for control_frame, control_midi in synth.controls:
                    # Turn off previous note
                    self.midi_events.append(MIDINoteEvent(
                        voice=voice,
                        frame=control_frame,
                        midi_note=current_tone,
                        velocity=0,
                        is_note_on=False
                    ))

                    # Turn on new note
                    self.midi_events.append(MIDINoteEvent(
                        voice=voice,
                        frame=control_frame,
                        midi_note=control_midi,
                        velocity=velocity,
                        is_note_on=True
                    ))

                    current_tone = control_midi

                # Final note OFF (calculate using ADSR envelope like SIDtool)
                end_frame = synth.calculate_end_frame()
                if end_frame > 0:
                    self.midi_events.append(MIDINoteEvent(
                        voice=voice,
                        frame=end_frame,
                        midi_note=current_tone,
                        velocity=0,
                        is_note_on=False
                    ))
                # If still playing at end (released_at == 0), don't add note OFF
                # (synth still active when capture ended)

        logger.info(f"  Converted to {len(self.midi_events)} MIDI events")

    def export_midi(self, output_path: str):
        """Export MIDI events to MIDI file.

        Args:
            output_path: Output MIDI file path
        """
        if not self.midi_events:
            logger.warning("No MIDI events to export")
            return

        logger.info(f"Exporting MIDI file: {output_path}")

        # Create MIDI file
        mid = MidiFile()

        # Match SIDtool's timing: 25 ticks per beat, 120 BPM
        # This gives 50 ticks per second (same as PAL frame rate)
        ticks_per_beat = 25  # Same as SIDtool
        ticks_per_frame = 1   # 1 tick per frame (50 ticks/sec, 50 frames/sec)

        mid.ticks_per_beat = ticks_per_beat

        # Create one track per voice
        for voice in range(3):
            track = MidiTrack()
            mid.tracks.append(track)

            # Track name
            track.append(MetaMessage('track_name', name=f'SID Voice {voice + 1}', time=0))

            # Set tempo (120 BPM)
            if voice == 0:  # Only set tempo in first track
                track.append(MetaMessage('set_tempo', tempo=500000, time=0))  # 120 BPM

            # Program change (use lead synth sound)
            track.append(Message('program_change', program=80, time=0))

            # Add note events for this voice
            voice_events = [e for e in self.midi_events if e.voice == voice]
            voice_events.sort(key=lambda e: e.frame)

            last_frame = 0
            for event in voice_events:
                # Calculate delta time in ticks
                delta_frames = event.frame - last_frame
                delta_ticks = delta_frames * ticks_per_frame

                if event.is_note_on:
                    track.append(Message('note_on',
                                       note=event.midi_note,
                                       velocity=event.velocity,
                                       time=delta_ticks))
                else:
                    track.append(Message('note_off',
                                       note=event.midi_note,
                                       velocity=0,
                                       time=delta_ticks))

                last_frame = event.frame

            # End of track
            track.append(MetaMessage('end_of_track', time=0))

        # Save MIDI file
        mid.save(output_path)
        logger.info(f"  [OK] MIDI file saved: {output_path}")

        # Print statistics
        stats = self.get_statistics()
        logger.info(f"\nMIDI Statistics:")
        logger.info(f"  Tempo: {self.tempo_bpm} BPM")
        logger.info(f"  Ticks per beat: {ticks_per_beat}")
        logger.info(f"  Total events: {len(self.midi_events)}")
        for voice_stat in stats['voices']:
            logger.info(f"  Voice {voice_stat['voice']}: "
                       f"{voice_stat['note_ons']} notes")

    def get_statistics(self) -> dict:
        """Get statistics about MIDI conversion."""
        stats = {
            'tempo_bpm': self.tempo_bpm,
            'total_events': len(self.midi_events),
            'voices': []
        }

        for voice in range(3):
            voice_events = [e for e in self.midi_events if e.voice == voice]
            note_ons = [e for e in voice_events if e.is_note_on]

            stats['voices'].append({
                'voice': voice + 1,
                'total_events': len(voice_events),
                'note_ons': len(note_ons),
                'note_offs': len(voice_events) - len(note_ons)
            })

        return stats


def convert_sid_to_midi(sid_path: str, midi_path: str, frames: int = 5000, song: int = 0):
    """Convert SID file to MIDI using CPU emulation.

    Args:
        sid_path: Input SID file
        midi_path: Output MIDI file
        frames: Number of frames to emulate (default 5000)
        song: Song number (default 0)
    """
    logger.info("="*60)
    logger.info("SID to MIDI Conversion (Python Emulator)")
    logger.info("="*60)
    logger.info(f"Input:  {sid_path}")
    logger.info(f"Output: {midi_path}")
    logger.info(f"Frames: {frames}")
    logger.info("")

    try:
        converter = SIDToMidiConverter(sid_path)
        converter.run(frames=frames, song=song)
        converter.export_midi(midi_path)

        logger.info("")
        logger.info("="*60)
        logger.info("[OK] Conversion complete!")
        logger.info("="*60)

        return True

    except Exception as e:
        logger.error(f"\n[ERROR] Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    import sys
    import os

    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    if len(sys.argv) < 3:
        print("Usage: python sid_to_midi_emulator.py <input.sid> <output.mid> [frames]")
        print("\nPure-Python SID to MIDI converter (no Ruby required)")
        print("Uses CPU emulation to capture SID register writes")
        sys.exit(1)

    sid_file = sys.argv[1]
    midi_file = sys.argv[2]
    frames = int(sys.argv[3]) if len(sys.argv) > 3 else 5000

    if not os.path.exists(sid_file):
        logger.error(f"SID file not found: {sid_file}")
        sys.exit(1)

    success = convert_sid_to_midi(sid_file, midi_file, frames=frames)
    sys.exit(0 if success else 1)
