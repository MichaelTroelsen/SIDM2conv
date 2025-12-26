#!/usr/bin/env python3
"""
SF2 Playback Engine - Handle SF2 file playback via external tools and QtMultimedia
"""

import subprocess
import tempfile
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, QObject
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# Add parent directory to path for logging
sys.path.insert(0, str(Path(__file__).parent.parent))
from sidm2.sf2_debug_logger import get_sf2_logger


class SF2PlaybackEngine(QObject):
    """Handle SF2 playback via external tools"""

    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_error = pyqtSignal(str)
    position_changed = pyqtSignal(int)  # milliseconds
    status_message = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        self.temp_files = []
        self.current_sf2: Optional[str] = None
        self.logger = get_sf2_logger()

        # Connect signals
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.player.positionChanged.connect(self.position_changed.emit)

        self.logger.log_action("SF2 Playback Engine initialized")

    def play_sf2(self, sf2_path: str, duration: int = 30) -> bool:
        """Export SF2 to SID, convert to WAV, and play

        Args:
            sf2_path: Path to SF2 file
            duration: Duration in seconds (default 30)

        Returns:
            True if playback started successfully, False otherwise
        """
        try:
            self.logger.log_playback('start', details={
                'sf2_path': sf2_path,
                'duration_s': duration,
                'message': f'Starting playback: {Path(sf2_path).name}'
            })

            self.current_sf2 = sf2_path

            # Create temp files
            temp_dir = tempfile.mkdtemp()
            sid_path = Path(temp_dir) / "temp.sid"
            wav_path = Path(temp_dir) / "temp.wav"

            self.temp_files.extend([sid_path, wav_path])

            # Step 1: Export SF2 to SID
            self.status_message.emit("Converting SF2 to SID...")
            self.logger.log_action("Converting SF2 to SID", {
                'sf2_path': sf2_path,
                'sid_path': str(sid_path)
            })

            result = subprocess.run([
                "python", "scripts/sf2_to_sid.py",
                sf2_path,
                str(sid_path)
            ], capture_output=True, timeout=30, text=True)

            if result.returncode != 0:
                error = result.stderr or result.stdout or "Unknown error"
                self.logger.log_playback('error', details={
                    'stage': 'SF2 to SID conversion',
                    'error': error,
                    'returncode': result.returncode
                })
                self.playback_error.emit(f"Failed to export SID: {error}")
                return False

            self.logger.log_action("SF2 to SID conversion successful", {
                'output_path': str(sid_path),
                'file_exists': sid_path.exists()
            })

            # Step 2: Convert SID to WAV
            self.status_message.emit("Converting SID to WAV...")
            self.logger.log_action("Converting SID to WAV", {
                'sid_path': str(sid_path),
                'wav_path': str(wav_path),
                'duration_s': duration
            })

            result = subprocess.run([
                "tools/SID2WAV.EXE",
                f"-t{duration}",  # Duration in seconds
                "-16",   # 16-bit
                str(sid_path),
                str(wav_path)
            ], capture_output=True, timeout=60, text=True)

            if result.returncode != 0:
                error = result.stderr or result.stdout or "Unknown error"
                self.logger.log_playback('error', details={
                    'stage': 'SID to WAV conversion',
                    'error': error,
                    'returncode': result.returncode
                })
                self.playback_error.emit(f"Failed to convert WAV: {error}")
                return False

            if not wav_path.exists():
                self.logger.log_playback('error', details={
                    'stage': 'WAV file creation',
                    'error': f'WAV file not created: {wav_path}'
                })
                self.playback_error.emit(f"WAV file was not created: {wav_path}")
                return False

            self.logger.log_action("SID to WAV conversion successful", {
                'output_path': str(wav_path),
                'file_exists': wav_path.exists(),
                'file_size_bytes': wav_path.stat().st_size if wav_path.exists() else 0
            })

            # Step 3: Load and play WAV
            self.status_message.emit("Loading and playing audio...")
            self.logger.log_action("Loading WAV file into QMediaPlayer", {
                'wav_path': str(wav_path)
            })

            self.player.setSource(QUrl.fromLocalFile(str(wav_path)))
            self.player.play()

            self.logger.log_music_state(True, {
                'sf2_file': Path(sf2_path).name,
                'duration_s': duration
            })

            return True

        except subprocess.TimeoutExpired:
            self.logger.log_playback('error', details={
                'error': 'Conversion timeout',
                'message': 'Conversion process took too long'
            })
            self.playback_error.emit("Conversion timeout - process took too long")
            return False
        except FileNotFoundError as e:
            self.logger.log_playback('error', details={
                'error': 'File not found',
                'exception': str(e)
            })
            self.playback_error.emit(f"File not found: {e}")
            return False
        except Exception as e:
            self.logger.log_playback('error', details={
                'error': 'Unexpected error',
                'exception': str(e),
                'exception_type': type(e).__name__
            })
            self.playback_error.emit(f"Playback error: {e}")
            return False

    def is_playing(self) -> bool:
        """Check if currently playing"""
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def pause(self):
        """Pause playback"""
        self.logger.log_playback('pause', details={
            'position_ms': self.get_position(),
            'duration_ms': self.get_duration()
        })
        self.player.pause()

    def resume(self):
        """Resume playback after pause"""
        self.logger.log_playback('resume', details={
            'position_ms': self.get_position(),
            'duration_ms': self.get_duration()
        })
        self.player.play()

    def stop(self):
        """Stop playback"""
        self.logger.log_playback('stop', details={
            'position_ms': self.get_position(),
            'duration_ms': self.get_duration(),
            'sf2_file': Path(self.current_sf2).name if self.current_sf2 else None
        })
        self.logger.log_music_state(False, {
            'reason': 'User stopped playback'
        })
        self.player.stop()
        self._cleanup_temp_files()

    def set_volume(self, volume: int):
        """Set volume (0-100)"""
        self.audio_output.setVolume(min(100, max(0, volume)) / 100.0)

    def get_position(self) -> int:
        """Get current playback position in milliseconds"""
        return self.player.position()

    def get_duration(self) -> int:
        """Get total duration in milliseconds"""
        return self.player.duration()

    def _on_state_changed(self, state):
        """Handle playback state changes"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.logger.log_action("Playback state changed to PLAYING", {
                'state': 'PLAYING',
                'position_ms': self.get_position(),
                'duration_ms': self.get_duration()
            })
            self.playback_started.emit()
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self.logger.log_action("Playback state changed to STOPPED", {
                'state': 'STOPPED',
                'reason': 'Natural end or user stop'
            })
            self.playback_stopped.emit()
            self._cleanup_temp_files()
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.logger.log_action("Playback state changed to PAUSED", {
                'state': 'PAUSED',
                'position_ms': self.get_position()
            })

    def _cleanup_temp_files(self):
        """Remove temporary files"""
        for path in self.temp_files:
            try:
                if path.exists():
                    path.unlink()
            except Exception:
                pass
        self.temp_files.clear()
