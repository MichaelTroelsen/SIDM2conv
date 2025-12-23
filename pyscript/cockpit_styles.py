#!/usr/bin/env python3
"""
Conversion Cockpit Styling - Professional UI styling and theming

Provides centralized stylesheet, icon generation, and color scheme management
for a polished, professional Conversion Cockpit interface.

Version: 1.0.0
Date: 2025-12-23
"""

from pathlib import Path
from typing import Tuple, Optional

try:
    from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
    from PyQt6.QtCore import Qt, QSize
except ImportError:
    raise ImportError("PyQt6 is required for Cockpit Styles")


class ColorScheme:
    """Professional color scheme for Conversion Cockpit"""

    # Primary colors
    PRIMARY = "#2196F3"          # Blue
    PRIMARY_DARK = "#1976D2"
    PRIMARY_LIGHT = "#BBDEFB"

    # Success/Completion
    SUCCESS = "#4CAF50"          # Green
    SUCCESS_DARK = "#388E3C"
    SUCCESS_LIGHT = "#C8E6C9"

    # Warning/Caution
    WARNING = "#FF9800"          # Orange
    WARNING_DARK = "#E65100"
    WARNING_LIGHT = "#FFE0B2"

    # Error/Failure
    ERROR = "#F44336"            # Red
    ERROR_DARK = "#C62828"
    ERROR_LIGHT = "#FFCDD2"

    # Neutral/UI
    BACKGROUND = "#FAFAFA"       # Light gray
    SURFACE = "#FFFFFF"          # White
    TEXT_PRIMARY = "#212121"     # Dark text
    TEXT_SECONDARY = "#757575"   # Gray text
    TEXT_DISABLED = "#BDBDBD"    # Disabled text
    DIVIDER = "#E0E0E0"          # Border color

    # Accent colors
    INFO = "#00BCD4"             # Cyan
    INFO_LIGHT = "#B2EBF2"


class IconGenerator:
    """Generate icons programmatically"""

    @staticmethod
    def create_circular_icon(
        color: str,
        size: int = 64,
        label: Optional[str] = None
    ) -> QPixmap:
        """Create a circular colored icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw circle
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)

        # Draw label if provided
        if label:
            painter.setPen(Qt.GlobalColor.white)
            font = painter.font()
            font.setPointSize(size // 4)
            painter.setFont(font)
            painter.drawText(0, 0, size, size, Qt.AlignmentFlag.AlignCenter, label)

        painter.end()
        return pixmap

    @staticmethod
    def create_play_icon(color: str = ColorScheme.SUCCESS, size: int = 48) -> QPixmap:
        """Create a play button icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background circle
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)

        # Draw play triangle
        painter.setBrush(Qt.GlobalColor.white)
        margin = size // 4
        points = [
            (margin, margin),
            (margin, size - margin),
            (size - margin, size // 2)
        ]
        painter.drawPolygon([QSize(x, y) for x, y in points])

        painter.end()
        return pixmap

    @staticmethod
    def create_pause_icon(color: str = ColorScheme.WARNING, size: int = 48) -> QPixmap:
        """Create a pause button icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background circle
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)

        # Draw pause bars
        painter.setBrush(Qt.GlobalColor.white)
        bar_width = size // 6
        margin = size // 4

        # Left bar
        painter.drawRect(margin, margin, bar_width, size - 2 * margin)

        # Right bar
        painter.drawRect(size - margin - bar_width, margin, bar_width, size - 2 * margin)

        painter.end()
        return pixmap

    @staticmethod
    def create_stop_icon(color: str = ColorScheme.ERROR, size: int = 48) -> QPixmap:
        """Create a stop button icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background circle
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)

        # Draw stop square
        painter.setBrush(Qt.GlobalColor.white)
        margin = size // 4
        painter.drawRect(margin, margin, size - 2 * margin, size - 2 * margin)

        painter.end()
        return pixmap

    @staticmethod
    def create_settings_icon(color: str = ColorScheme.PRIMARY, size: int = 48) -> QPixmap:
        """Create a settings/gear icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setBrush(Qt.GlobalColor.transparent)
        painter.setPen(QColor(color))
        pen = painter.pen()
        pen.setWidth(2)
        painter.setPen(pen)

        # Draw gear shape (simplified)
        center = size // 2
        outer_radius = size // 3
        inner_radius = size // 6

        # Draw outer circle
        painter.drawEllipse(center - outer_radius, center - outer_radius, 2 * outer_radius, 2 * outer_radius)

        # Draw inner circle
        painter.drawEllipse(center - inner_radius, center - inner_radius, 2 * inner_radius, 2 * inner_radius)

        # Draw teeth
        painter.setBrush(QColor(color))
        for i in range(12):
            angle = i * 30
            x = center + (outer_radius + 5) * (1 if angle < 180 else -1)
            y = center
            painter.drawEllipse(x - 2, y - 2, 4, 4)

        painter.end()
        return pixmap

    @staticmethod
    def create_checkmark_icon(color: str = ColorScheme.SUCCESS, size: int = 48) -> QPixmap:
        """Create a checkmark icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background circle
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)

        # Draw checkmark
        painter.setPen(QColor(Qt.GlobalColor.white))
        pen = painter.pen()
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        margin = size // 4
        painter.drawLine(
            int(margin * 1.2), int(size / 2),
            int(size / 2 - 2), int(size - margin)
        )
        painter.drawLine(
            int(size / 2 - 2), int(size - margin),
            int(size - margin), int(margin)
        )

        painter.end()
        return pixmap

    @staticmethod
    def create_error_icon(color: str = ColorScheme.ERROR, size: int = 48) -> QPixmap:
        """Create an error/X icon"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background circle
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)

        # Draw X
        painter.setPen(QColor(Qt.GlobalColor.white))
        pen = painter.pen()
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        margin = size // 4
        painter.drawLine(margin, margin, size - margin, size - margin)
        painter.drawLine(size - margin, margin, margin, size - margin)

        painter.end()
        return pixmap


class StyleSheet:
    """Qt Stylesheet definitions"""

    @staticmethod
    def get_main_stylesheet() -> str:
        """Get main application stylesheet"""
        return f"""
        QMainWindow, QWidget {{
            background-color: {ColorScheme.BACKGROUND};
            color: {ColorScheme.TEXT_PRIMARY};
        }}

        QTabWidget::pane {{
            border: 1px solid {ColorScheme.DIVIDER};
        }}

        QTabBar::tab {{
            background-color: {ColorScheme.SURFACE};
            color: {ColorScheme.TEXT_SECONDARY};
            padding: 8px 20px;
            border: 1px solid {ColorScheme.DIVIDER};
            margin-right: 2px;
            border-radius: 4px 4px 0px 0px;
        }}

        QTabBar::tab:selected {{
            background-color: {ColorScheme.SURFACE};
            color: {ColorScheme.PRIMARY};
            border-bottom: 3px solid {ColorScheme.PRIMARY};
        }}

        QPushButton {{
            background-color: {ColorScheme.PRIMARY};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
        }}

        QPushButton:hover {{
            background-color: {ColorScheme.PRIMARY_DARK};
        }}

        QPushButton:pressed {{
            background-color: {ColorScheme.PRIMARY_DARK};
            padding: 9px 15px 7px 17px;
        }}

        QPushButton:disabled {{
            background-color: {ColorScheme.TEXT_DISABLED};
            color: {ColorScheme.TEXT_SECONDARY};
        }}

        QPushButton#startBtn {{
            background-color: {ColorScheme.SUCCESS};
        }}

        QPushButton#startBtn:hover {{
            background-color: {ColorScheme.SUCCESS_DARK};
        }}

        QPushButton#pauseBtn {{
            background-color: {ColorScheme.WARNING};
        }}

        QPushButton#pauseBtn:hover {{
            background-color: {ColorScheme.WARNING_DARK};
        }}

        QPushButton#stopBtn {{
            background-color: {ColorScheme.ERROR};
        }}

        QPushButton#stopBtn:hover {{
            background-color: {ColorScheme.ERROR_DARK};
        }}

        QGroupBox {{
            border: 1px solid {ColorScheme.DIVIDER};
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
            color: {ColorScheme.TEXT_PRIMARY};
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0px 3px 0px 3px;
        }}

        QProgressBar {{
            border: 1px solid {ColorScheme.DIVIDER};
            border-radius: 4px;
            background-color: {ColorScheme.SURFACE};
            padding: 2px;
            text-align: center;
            height: 20px;
        }}

        QProgressBar::chunk {{
            background-color: {ColorScheme.PRIMARY};
            border-radius: 3px;
        }}

        QLineEdit, QComboBox {{
            border: 1px solid {ColorScheme.DIVIDER};
            border-radius: 4px;
            padding: 6px;
            background-color: {ColorScheme.SURFACE};
            color: {ColorScheme.TEXT_PRIMARY};
        }}

        QLineEdit:focus, QComboBox:focus {{
            border: 2px solid {ColorScheme.PRIMARY};
        }}

        QTableWidget, QListWidget {{
            border: 1px solid {ColorScheme.DIVIDER};
            background-color: {ColorScheme.SURFACE};
            color: {ColorScheme.TEXT_PRIMARY};
            gridline-color: {ColorScheme.DIVIDER};
        }}

        QTableWidget::item:selected, QListWidget::item:selected {{
            background-color: {ColorScheme.PRIMARY_LIGHT};
            color: {ColorScheme.TEXT_PRIMARY};
        }}

        QHeaderView::section {{
            background-color: {ColorScheme.PRIMARY_LIGHT};
            color: {ColorScheme.TEXT_PRIMARY};
            padding: 6px;
            border: none;
            font-weight: bold;
        }}

        QScrollBar:vertical {{
            background-color: {ColorScheme.BACKGROUND};
            width: 12px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {ColorScheme.TEXT_DISABLED};
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {ColorScheme.TEXT_SECONDARY};
        }}

        QLabel {{
            color: {ColorScheme.TEXT_PRIMARY};
        }}

        QStatusBar {{
            border-top: 1px solid {ColorScheme.DIVIDER};
            color: {ColorScheme.TEXT_SECONDARY};
        }}
        """

    @staticmethod
    def get_dashboard_stylesheet() -> str:
        """Get dashboard-specific stylesheet"""
        return f"""
        QLabel {{
            color: {ColorScheme.TEXT_SECONDARY};
        }}

        QLabel[title="true"] {{
            color: {ColorScheme.TEXT_PRIMARY};
            font-size: 14px;
            font-weight: bold;
        }}

        QFrame#dashboardSection {{
            background-color: {ColorScheme.SURFACE};
            border: 1px solid {ColorScheme.DIVIDER};
            border-radius: 4px;
            padding: 15px;
        }}
        """


class UIHelpers:
    """Helper functions for UI customization"""

    @staticmethod
    def get_icon_with_text(text: str, size: int = 32) -> QIcon:
        """Create an icon with text label"""
        pixmap = IconGenerator.create_circular_icon(
            ColorScheme.PRIMARY,
            size,
            text[0].upper() if text else "?"
        )
        return QIcon(pixmap)

    @staticmethod
    def apply_button_style(button, button_type: str = "primary"):
        """Apply predefined button style"""
        button.setMinimumHeight(36)
        button.setMinimumWidth(80)

        if button_type == "play":
            button.setObjectName("startBtn")
            button.setToolTip("Start conversion")
        elif button_type == "pause":
            button.setObjectName("pauseBtn")
            button.setToolTip("Pause conversion")
        elif button_type == "stop":
            button.setObjectName("stopBtn")
            button.setToolTip("Stop conversion")

    @staticmethod
    def format_large_text(text: str, size: int = 14, bold: bool = True) -> str:
        """Format text for display (to be used with stylesheets)"""
        # Return the text as-is, styling done via stylesheet
        return text


def main():
    """Test the styling system"""
    print("Conversion Cockpit Styling System")
    print("=" * 70)

    # Test icon generation
    print("\nIcon Generation:")
    print("  - Play icon:", IconGenerator.create_play_icon().size().width(), "x", IconGenerator.create_play_icon().size().height())
    print("  - Pause icon:", IconGenerator.create_pause_icon().size().width(), "x", IconGenerator.create_pause_icon().size().height())
    print("  - Stop icon:", IconGenerator.create_stop_icon().size().width(), "x", IconGenerator.create_stop_icon().size().height())
    print("  - Checkmark icon:", IconGenerator.create_checkmark_icon().size().width(), "x", IconGenerator.create_checkmark_icon().size().height())
    print("  - Error icon:", IconGenerator.create_error_icon().size().width(), "x", IconGenerator.create_error_icon().size().height())

    # Test colors
    print("\nColor Scheme:")
    print(f"  Primary: {ColorScheme.PRIMARY}")
    print(f"  Success: {ColorScheme.SUCCESS}")
    print(f"  Warning: {ColorScheme.WARNING}")
    print(f"  Error: {ColorScheme.ERROR}")

    # Test stylesheet
    print("\nStylesheet:")
    stylesheet = StyleSheet.get_main_stylesheet()
    print(f"  Generated {len(stylesheet)} characters")
    print(f"  Contains {stylesheet.count('background-color')} color definitions")

    print("\n" + "=" * 70)
    print("All styling components created successfully")


if __name__ == '__main__':
    main()
