"""Custom visualization widgets for SF2 Viewer.

Provides interactive visualizations for:
- Waveforms (256 sample data)
- Filter cutoff frequency curves (11-bit values)
- ADSR envelopes (4-bit attack/decay/sustain/release)
"""

from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtCore import Qt, QPoint
from typing import List


class WaveformWidget(QWidget):
    """Draw waveform from wave table data.

    Displays a waveform as a connected line graph with proper scaling
    for byte values (0-255).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data: List[int] = []
        self.setMinimumHeight(200)

    def set_data(self, data: List[int]):
        """Update waveform data and repaint.

        Args:
            data: List of byte values (0-255) representing the waveform
        """
        self.data = data
        self.update()

    def paintEvent(self, event):
        """Draw waveform as connected lines."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.data:
            # Draw empty state
            painter.setPen(QPen(QColor(128, 128, 128), 1))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                           "No waveform data")
            return

        width = self.width()
        height = self.height()

        if len(self.data) < 2:
            return

        # Calculate scaling
        x_scale = width / (len(self.data) - 1) if len(self.data) > 1 else 1
        y_scale = height / 256.0  # Byte values 0-255

        # Draw center line (zero crossing reference)
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawLine(0, height // 2, width, height // 2)

        # Draw grid lines
        painter.setPen(QPen(QColor(220, 220, 220), 1, Qt.PenStyle.DotLine))
        for i in range(1, 8):
            y = int((height / 8) * i)
            painter.drawLine(0, y, width, y)

        # Draw waveform
        painter.setPen(QPen(QColor(0, 100, 255), 2))
        for i in range(len(self.data) - 1):
            x1 = int(i * x_scale)
            y1 = int(height - (self.data[i] * y_scale))
            x2 = int((i + 1) * x_scale)
            y2 = int(height - (self.data[i + 1] * y_scale))
            painter.drawLine(x1, y1, x2, y2)

        # Draw axis labels
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.drawText(5, 15, f"Max: 255")
        painter.drawText(5, height - 5, f"Min: 0")


class FilterResponseWidget(QWidget):
    """Draw filter cutoff frequency curve.

    Displays filter cutoff values (11-bit, 0-2047) as a frequency response curve.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cutoff_data: List[int] = []
        self.setMinimumHeight(200)

    def set_data(self, cutoff_data: List[int]):
        """Update filter cutoff data and repaint.

        Args:
            cutoff_data: List of cutoff frequency values (0-2047)
        """
        self.cutoff_data = cutoff_data
        self.update()

    def paintEvent(self, event):
        """Draw filter response curve."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.cutoff_data:
            # Draw empty state
            painter.setPen(QPen(QColor(128, 128, 128), 1))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                           "No filter data")
            return

        width = self.width()
        height = self.height()

        if len(self.cutoff_data) < 2:
            return

        # Calculate scaling (11-bit cutoff: 0-2047)
        x_scale = width / (len(self.cutoff_data) - 1) if len(self.cutoff_data) > 1 else 1
        y_scale = height / 2048.0

        # Draw grid
        painter.setPen(QPen(QColor(220, 220, 220), 1, Qt.PenStyle.DotLine))
        for i in range(1, 8):
            y = int((height / 8) * i)
            painter.drawLine(0, y, width, y)

        # Draw center line
        painter.setPen(QPen(QColor(200, 200, 200), 1))
        painter.drawLine(0, height // 2, width, height // 2)

        # Draw cutoff frequency curve (orange for filter)
        painter.setPen(QPen(QColor(255, 140, 0), 2))
        for i in range(len(self.cutoff_data) - 1):
            x1 = int(i * x_scale)
            y1 = int(height - (self.cutoff_data[i] * y_scale))
            x2 = int((i + 1) * x_scale)
            y2 = int(height - (self.cutoff_data[i + 1] * y_scale))
            painter.drawLine(x1, y1, x2, y2)

        # Draw axis labels
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        font = QFont("Arial", 8)
        painter.setFont(font)
        painter.drawText(5, 15, "Cutoff: 2047")
        painter.drawText(5, height - 5, "Cutoff: 0")


class EnvelopeWidget(QWidget):
    """Draw ADSR envelope visualization.

    Displays Attack/Decay/Sustain/Release envelope shape based on 4-bit
    values (0-15 for each parameter).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.attack = 0
        self.decay = 0
        self.sustain = 0
        self.release = 0
        self.setMinimumHeight(200)

    def set_envelope(self, attack: int, decay: int, sustain: int, release: int):
        """Set ADSR values.

        Args:
            attack: Attack time (4-bit: 0-15)
            decay: Decay time (4-bit: 0-15)
            sustain: Sustain level (4-bit: 0-15)
            release: Release time (4-bit: 0-15)
        """
        self.attack = max(0, min(15, attack))
        self.decay = max(0, min(15, decay))
        self.sustain = max(0, min(15, sustain))
        self.release = max(0, min(15, release))
        self.update()

    def paintEvent(self, event):
        """Draw ADSR envelope shape."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()
        margin = 40

        # Draw background grid
        painter.setPen(QPen(QColor(240, 240, 240), 1))
        painter.fillRect(self.rect(), QColor(255, 255, 255))

        # Scale times for visualization
        attack_time = max(1, self.attack * 2)
        decay_time = max(1, self.decay * 2)
        sustain_time = 80
        release_time = max(1, self.release * 2)

        total_time = attack_time + decay_time + sustain_time + release_time

        # Calculate dimensions within margins
        plot_width = width - (2 * margin)
        plot_height = height - (2 * margin)

        if plot_width <= 0 or plot_height <= 0:
            return

        x_scale = plot_width / total_time if total_time > 0 else 1
        y_scale = plot_height / 15.0  # 0-15 sustain level

        # Starting point (on baseline)
        x_offset = margin
        y_offset = height - margin

        sustain_level_px = y_offset - (self.sustain * y_scale)

        # Draw ADSR envelope
        painter.setPen(QPen(QColor(0, 200, 0), 3))
        points = []

        # Starting point (level 0)
        x_start = x_offset
        y_start = y_offset
        points.append(QPoint(int(x_start), int(y_start)))

        # Attack phase: 0 -> 15
        x_attack_end = x_start + (attack_time * x_scale)
        y_attack_end = y_offset - (15 * y_scale)
        points.append(QPoint(int(x_attack_end), int(y_attack_end)))

        # Decay phase: 15 -> sustain
        x_decay_end = x_attack_end + (decay_time * x_scale)
        y_decay_end = sustain_level_px
        points.append(QPoint(int(x_decay_end), int(y_decay_end)))

        # Sustain phase: hold at sustain level
        x_sustain_end = x_decay_end + (sustain_time * x_scale)
        y_sustain_end = sustain_level_px
        points.append(QPoint(int(x_sustain_end), int(y_sustain_end)))

        # Release phase: sustain -> 0
        x_release_end = x_sustain_end + (release_time * x_scale)
        y_release_end = y_offset
        points.append(QPoint(int(x_release_end), int(y_release_end)))

        # Draw the envelope lines
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        # Draw phase labels
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        font = QFont("Arial", 8)
        painter.setFont(font)

        label_y = y_offset + 20
        painter.drawText(int(x_start + (attack_time * x_scale) / 2 - 10), int(label_y), "A")
        painter.drawText(int(x_attack_end + (decay_time * x_scale) / 2 - 10), int(label_y), "D")
        painter.drawText(int(x_decay_end + (sustain_time * x_scale) / 2 - 10), int(label_y), "S")
        painter.drawText(int(x_sustain_end + (release_time * x_scale) / 2 - 10), int(label_y), "R")

        # Draw parameter values
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        font = QFont("Arial", 9)
        font.setBold(True)
        painter.setFont(font)

        value_text = f"A:{self.attack:2d}  D:{self.decay:2d}  S:{self.sustain:2d}  R:{self.release:2d}"
        painter.drawText(margin, 20, value_text)

        # Draw axes
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawLine(x_offset, y_offset, x_offset + plot_width, y_offset)  # X-axis
        painter.drawLine(x_offset, y_offset, x_offset, y_offset - plot_height)  # Y-axis

        # Draw axis labels
        painter.drawText(x_offset - 30, y_offset + 5, "Time")
        painter.drawText(x_offset - 35, y_offset - plot_height, "Level")
