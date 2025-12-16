#!/usr/bin/env python3
"""
SF2 Visualization Widgets - Custom PyQt6 widgets for displaying waveforms, filters, and envelopes
"""

from typing import List, Optional
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtCore import Qt, QPoint


class WaveformWidget(QWidget):
    """Display waveform data as a connected line graph"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.data: List[int] = []
        self.setMinimumHeight(200)

    def set_data(self, data: List[int]):
        """Update waveform data and repaint"""
        self.data = data
        self.update()

    def paintEvent(self, event):
        """Draw waveform as connected lines"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.data or len(self.data) < 2:
            painter.drawText(10, 30, "No waveform data available")
            return

        width = self.width()
        height = self.height()

        # Safety check: ensure we have some space
        if width < 10 or height < 10:
            return

        x_scale = width / (len(self.data) - 1) if len(self.data) > 1 else 1
        y_scale = height / 256  # 0-255 byte values

        # Draw center line (zero reference)
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.PenStyle.DashLine))
        center_y = height // 2
        painter.drawLine(0, center_y, width, center_y)

        # Draw grid lines
        painter.setPen(QPen(QColor(230, 230, 230), 1))
        for i in range(0, height, 40):
            painter.drawLine(0, i, width, i)

        # Draw waveform
        painter.setPen(QPen(QColor(0, 100, 255), 2))
        for i in range(len(self.data) - 1):
            x1 = int(i * x_scale)
            y1 = int(height - (self.data[i] * y_scale))
            x2 = int((i + 1) * x_scale)
            y2 = int(height - (self.data[i + 1] * y_scale))
            painter.drawLine(x1, y1, x2, y2)

        # Draw value labels
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setFont(QFont("Courier", 8))
        painter.drawText(10, 15, f"Samples: {len(self.data)}")
        painter.drawText(10, 30, f"Min: 0x00, Max: 0xFF")


class FilterResponseWidget(QWidget):
    """Display filter cutoff frequency curve"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cutoff_data: List[int] = []
        self.setMinimumHeight(200)

    def set_data(self, cutoff_data: List[int]):
        """Update filter cutoff data and repaint"""
        self.cutoff_data = cutoff_data
        self.update()

    def paintEvent(self, event):
        """Draw filter cutoff frequency response curve"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.cutoff_data or len(self.cutoff_data) < 2:
            painter.drawText(10, 30, "No filter data available")
            return

        width = self.width()
        height = self.height()

        # Safety check
        if width < 10 or height < 10:
            return

        x_scale = width / (len(self.cutoff_data) - 1) if len(self.cutoff_data) > 1 else 1
        y_scale = height / 2048  # 11-bit cutoff (0-2047)

        # Draw center line
        painter.setPen(QPen(QColor(200, 200, 200), 1, Qt.PenStyle.DashLine))
        painter.drawLine(0, height // 2, width, height // 2)

        # Draw grid lines
        painter.setPen(QPen(QColor(230, 230, 230), 1))
        for i in range(0, height, 40):
            painter.drawLine(0, i, width, i)

        # Draw frequency curve
        painter.setPen(QPen(QColor(255, 100, 0), 2))
        for i in range(len(self.cutoff_data) - 1):
            x1 = int(i * x_scale)
            y1 = int(height - (self.cutoff_data[i] * y_scale))
            x2 = int((i + 1) * x_scale)
            y2 = int(height - (self.cutoff_data[i + 1] * y_scale))
            painter.drawLine(x1, y1, x2, y2)

        # Draw value labels
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setFont(QFont("Courier", 8))
        painter.drawText(10, 15, f"Samples: {len(self.cutoff_data)}")
        painter.drawText(10, 30, f"Range: 0-2047 (11-bit)")


class EnvelopeWidget(QWidget):
    """Display ADSR envelope visualization"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.attack = 0
        self.decay = 0
        self.sustain = 0
        self.release = 0
        self.setMinimumHeight(200)

    def set_envelope(self, attack: int, decay: int, sustain: int, release: int):
        """Set ADSR values (4-bit each: 0-15)"""
        self.attack = attack & 0x0F
        self.decay = decay & 0x0F
        self.sustain = sustain & 0x0F
        self.release = release & 0x0F
        self.update()

    def paintEvent(self, event):
        """Draw ADSR envelope shape"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Safety check
        if width < 50 or height < 50:
            return

        # ADSR envelope shape:
        # Attack: 0 -> max (0.15 * time_scale)
        # Decay: max -> sustain (0.15 * time_scale)
        # Sustain: hold at sustain level (0.40 * time_scale)
        # Release: sustain -> 0 (0.30 * time_scale)

        time_scale = 100  # pixels per time unit

        attack_x = self.attack * time_scale if self.attack > 0 else 5
        decay_x = self.decay * time_scale if self.decay > 0 else 5
        sustain_x = 150  # Fixed sustain phase
        release_x = self.release * time_scale if self.release > 0 else 5

        total_time = attack_x + decay_x + sustain_x + release_x
        x_scale = (width - 40) / total_time if total_time > 0 else 1

        sustain_level = height - 50 - (self.sustain / 15.0 * (height - 100))
        max_level = 30

        # Build envelope points
        points = []
        x_pos = 20

        # Attack phase (0 -> max)
        points.append(QPoint(x_pos, height - 30))
        x_pos += int(attack_x * x_scale)
        points.append(QPoint(x_pos, max_level))

        # Decay phase (max -> sustain)
        x_pos += int(decay_x * x_scale)
        points.append(QPoint(x_pos, int(sustain_level)))

        # Sustain phase (hold)
        x_pos += int(sustain_x * x_scale)
        points.append(QPoint(x_pos, int(sustain_level)))

        # Release phase (sustain -> 0)
        x_pos += int(release_x * x_scale)
        points.append(QPoint(x_pos, height - 30))

        # Draw envelope curve
        painter.setPen(QPen(QColor(0, 200, 0), 2))
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        # Draw phase labels
        painter.setPen(QPen(QColor(100, 100, 100), 1))
        painter.setFont(QFont("Courier", 8))

        # Attack label
        if len(points) > 0:
            label_x = (points[0].x() + points[1].x()) // 2
            painter.drawText(label_x - 15, height - 5, "A")

        # Decay label
        if len(points) > 1:
            label_x = (points[1].x() + points[2].x()) // 2
            painter.drawText(label_x - 15, height - 5, "D")

        # Sustain label
        if len(points) > 2:
            label_x = (points[2].x() + points[3].x()) // 2
            painter.drawText(label_x - 15, height - 5, "S")

        # Release label
        if len(points) > 3:
            label_x = (points[3].x() + points[4].x()) // 2
            painter.drawText(label_x - 15, height - 5, "R")

        # Draw ADSR values
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.setFont(QFont("Courier", 9))
        painter.drawText(width - 120, 15, f"A: {self.attack:2d}  D: {self.decay:2d}")
        painter.drawText(width - 120, 30, f"S: {self.sustain:2d}  R: {self.release:2d}")
