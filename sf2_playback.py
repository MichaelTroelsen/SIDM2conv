"""SF2 playback engine using external tools and PyQt6-Multimedia.

This module provides audio playback for SF2 files by leveraging:
1. sf2_to_sid.py - Exports SF2 to SID format
2. SID2WAV.EXE - Converts SID to WAV audio
3. PyQt6-Multimedia - Plays the generated WAV files
"""

import subprocess
import tempfile
import os
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtCore import QUrl, QTimer, pyqtSignal, QObject
    from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
    PYQT6_MM_AVAILABLE = True
except ImportError:
    PYQT6_MM_AVAILABLE = False


class SF2PlaybackEngine(QObject):
    """Handle SF2 playback via external tools.

    Conversion pipeline:
    1. SF2 → SID (using sf2_to_sid.py script)
    2. SID → WAV (using SID2WAV.EXE external tool)
    3. WAV → Audio (using PyQt6-Multimedia QMediaPlayer)
    """

    playback_started = pyqtSignal()
    playback_stopped = pyqtSignal()
    playback_error = pyqtSignal(str)
    position_changed = pyqtSignal(int)  # milliseconds

    def __init__(self):
        super().__init__()

        if not PYQT6_MM_AVAILABLE:
            raise RuntimeError("PyQt6-Multimedia is required. Install with: pip install PyQt6-Multimedia")

        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)

        self.temp_files = []
        self.current_sf2 = None

        # Connect signals
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.player.positionChanged.connect(self.position_changed.emit)
        self.player.errorOccurred.connect(self._on_player_error)

    def play_sf2(self, sf2_path: str, duration: int = 30) -> bool:
        """Export SF2 to SID, convert to WAV, and play.

        Args:
            sf2_path: Path to SF2 file to play
            duration: Duration in seconds to render (default 30)

        Returns:
            True if playback started successfully, False otherwise
        """
        try:
            self.current_sf2 = sf2_path

            # Create temp directory
            temp_dir = tempfile.mkdtemp()
            sid_path = Path(temp_dir) / "temp.sid"
            wav_path = Path(temp_dir) / "temp.wav"

            self.temp_files.extend([str(sid_path), str(wav_path)])

            # Step 1: Export SF2 to SID
            self._log(f"Exporting SF2 to SID...")
            result = subprocess.run([
                "python", "scripts/sf2_to_sid.py",
                sf2_path,
                str(sid_path)
            ], capture_output=True, timeout=30, text=True)

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                self.playback_error.emit(f"Failed to export SID: {error_msg}")
                return False

            # Step 2: Convert SID to WAV
            self._log(f"Converting SID to WAV ({duration}s)...")
            result = subprocess.run([
                "tools\\SID2WAV.EXE",
                f"-t{duration}",  # Duration in seconds
                "-16",             # 16-bit audio
                str(sid_path),
                str(wav_path)
            ], capture_output=True, timeout=120, text=True)

            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                self.playback_error.emit(f"Failed to convert WAV: {error_msg}")
                return False

            # Verify WAV file was created
            if not Path(wav_path).exists():
                self.playback_error.emit("WAV file not created")
                return False

            # Step 3: Load and play WAV
            self._log(f"Loading and playing audio...")
            self.player.setSource(QUrl.fromLocalFile(str(wav_path)))
            self.player.play()

            return True

        except subprocess.TimeoutExpired:
            self.playback_error.emit("Conversion timeout (took too long)")
            return False
        except FileNotFoundError as e:
            self.playback_error.emit(f"File not found: {e}")
            return False
        except Exception as e:
            self.playback_error.emit(f"Playback error: {e}")
            return False

    def pause(self):
        """Pause playback."""
        self.player.pause()

    def stop(self):
        """Stop playback."""
        self.player.stop()
        self._cleanup_temp_files()

    def set_volume(self, volume: int):
        """Set volume level.

        Args:
            volume: Volume level 0-100
        """
        if 0 <= volume <= 100:
            self.audio_output.setVolume(volume / 100.0)

    def resume(self):
        """Resume paused playback."""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.player.play()

    def is_playing(self) -> bool:
        """Check if currently playing."""
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def get_duration(self) -> int:
        """Get total duration in milliseconds."""
        return self.player.duration()

    def get_position(self) -> int:
        """Get current position in milliseconds."""
        return self.player.position()

    def _on_state_changed(self, state):
        """Handle playback state changes."""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.playback_started.emit()
        elif state == QMediaPlayer.PlaybackState.StoppedState:
            self.playback_stopped.emit()
            self._cleanup_temp_files()

    def _on_player_error(self, error):
        """Handle media player errors."""
        error_string = self.player.errorString()
        self.playback_error.emit(f"Playback error: {error_string}")

    def _cleanup_temp_files(self):
        """Remove temporary files."""
        for path in self.temp_files:
            try:
                if Path(path).exists():
                    Path(path).unlink()
            except Exception:
                pass
        self.temp_files.clear()

    def _log(self, message: str):
        """Internal logging (can be overridden for debugging)."""
        # print(f"[SF2Playback] {message}")
        pass

    def __del__(self):
        """Cleanup on deletion."""
        self._cleanup_temp_files()
