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
    from PyQt6.QtCore import Qt, QSize, QPoint
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



class DarkColorScheme:
    """The same names as ColorScheme, dark.

    EVERY ATTRIBUTE ColorScheme DEFINES MUST EXIST HERE. A hand-written second
    palette drops a colour the moment someone adds one to the light class, and
    the failure is silent: the stylesheet f-string raises AttributeError only
    for the widget that uses it, at runtime, in dark mode only. So the pairing
    is asserted by a test rather than trusted -- exactly the shape that let
    PipelineConfig.to_dict hand-list 15 of 16 fields (fixed 2026-09-04); a
    hand-maintained mirror of a structure is a mirror that goes stale.

    The hues are kept and the LIGHTNESS inverted, rather than picking new
    colours: PRIMARY stays blue, ERROR stays red. A dark theme that also
    re-assigns meaning is two changes wearing one name.
    """

    PRIMARY = "#64B5F6"
    PRIMARY_DARK = "#42A5F5"
    PRIMARY_LIGHT = "#1E3A5F"

    SUCCESS = "#81C784"
    SUCCESS_DARK = "#66BB6A"
    SUCCESS_LIGHT = "#1B3A22"

    WARNING = "#FFB74D"
    WARNING_DARK = "#FFA726"
    WARNING_LIGHT = "#4A3418"

    ERROR = "#E57373"
    ERROR_DARK = "#EF5350"
    ERROR_LIGHT = "#4A2222"

    BACKGROUND = "#121212"
    SURFACE = "#1E1E1E"
    TEXT_PRIMARY = "#ECECEC"
    TEXT_SECONDARY = "#A0A0A0"
    TEXT_DISABLED = "#5C5C5C"
    DIVIDER = "#333333"

    INFO = "#4DD0E1"
    INFO_LIGHT = "#12363B"


# The scheme the stylesheet builders read when none is passed. Module-level
# rather than a GUI attribute so `StyleSheet.get_main_stylesheet()` keeps its
# existing zero-argument call sites working unchanged.
_ACTIVE_DARK = False


def active_scheme():
    """ColorScheme or DarkColorScheme, per `set_dark_mode`."""
    return DarkColorScheme if _ACTIVE_DARK else ColorScheme


def set_dark_mode(enabled: bool) -> None:
    """Switch the palette every stylesheet builder reads.

    Returns nothing and touches no widget -- a caller that wants the change on
    screen re-applies `StyleSheet.get_main_stylesheet()`. Keeping the toggle
    free of Qt is what lets it be tested without a QApplication.
    """
    global _ACTIVE_DARK
    _ACTIVE_DARK = bool(enabled)


def dark_mode_enabled() -> bool:
    return _ACTIVE_DARK


# ---------------------------------------------------------------------------
# TOOLTIPS -- declared as DATA, so a control without help text is findable.
#
# Scoped DELIBERATELY to the configuration surface rather than "all controls":
# those are the ones whose meaning is not obvious from their label, and a
# tooltip on a button that says "Start" adds nothing. See docs/IMPROVEMENTS_TODO.md
# CC-6b for what was implemented and what was struck.
# ---------------------------------------------------------------------------

TOOLTIPS = {
    "simple_radio": "Run only the essential pipeline steps -- parse, convert, write SF2.",
    "advanced_radio": "Run every pipeline step, including validation and audio export.",
    "custom_radio": "Choose individual steps yourself; nothing is implied.",
    "driver_combo": ("Target SF2 driver. Auto-selection reads the player id, so override "
                     "this only when you know the file's player better than player-id does "
                     "-- a native Laxity NP21 file converted with Driver 11 scores 1-8%."),
}

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
        painter.drawPolygon([QPoint(x, y) for x, y in points])

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
    def get_main_stylesheet(scheme=None) -> str:
        """Get main application stylesheet for `scheme` (default: active).

        The palette is a PARAMETER now rather than a hard reference to
        ColorScheme, which is what makes a second palette possible at all --
        every colour in this 160-line f-string used to name the light class
        directly, so "dark mode" could not have been more than a re-skin of
        one widget.
        """
        C = scheme or active_scheme()
        return f"""
        QMainWindow, QWidget {{
            background-color: {C.BACKGROUND};
            color: {C.TEXT_PRIMARY};
        }}

        QTabWidget::pane {{
            border: 1px solid {C.DIVIDER};
        }}

        QTabBar::tab {{
            background-color: {C.SURFACE};
            color: {C.TEXT_SECONDARY};
            padding: 8px 20px;
            border: 1px solid {C.DIVIDER};
            margin-right: 2px;
            border-radius: 4px 4px 0px 0px;
        }}

        QTabBar::tab:selected {{
            background-color: {C.SURFACE};
            color: {C.PRIMARY};
            border-bottom: 3px solid {C.PRIMARY};
        }}

        QPushButton {{
            background-color: {C.PRIMARY};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
        }}

        QPushButton:hover {{
            background-color: {C.PRIMARY_DARK};
        }}

        QPushButton:pressed {{
            background-color: {C.PRIMARY_DARK};
            padding: 9px 15px 7px 17px;
        }}

        QPushButton:disabled {{
            background-color: {C.TEXT_DISABLED};
            color: {C.TEXT_SECONDARY};
        }}

        QPushButton#startBtn {{
            background-color: {C.SUCCESS};
        }}

        QPushButton#startBtn:hover {{
            background-color: {C.SUCCESS_DARK};
        }}

        QPushButton#pauseBtn {{
            background-color: {C.WARNING};
        }}

        QPushButton#pauseBtn:hover {{
            background-color: {C.WARNING_DARK};
        }}

        QPushButton#stopBtn {{
            background-color: {C.ERROR};
        }}

        QPushButton#stopBtn:hover {{
            background-color: {C.ERROR_DARK};
        }}

        QGroupBox {{
            border: 1px solid {C.DIVIDER};
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            font-weight: bold;
            color: {C.TEXT_PRIMARY};
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0px 3px 0px 3px;
        }}

        QProgressBar {{
            border: 1px solid {C.DIVIDER};
            border-radius: 4px;
            background-color: {C.SURFACE};
            padding: 2px;
            text-align: center;
            height: 20px;
        }}

        QProgressBar::chunk {{
            background-color: {C.PRIMARY};
            border-radius: 3px;
        }}

        QLineEdit, QComboBox {{
            border: 1px solid {C.DIVIDER};
            border-radius: 4px;
            padding: 6px;
            background-color: {C.SURFACE};
            color: {C.TEXT_PRIMARY};
        }}

        QLineEdit:focus, QComboBox:focus {{
            border: 2px solid {C.PRIMARY};
        }}

        QTableWidget, QListWidget {{
            border: 1px solid {C.DIVIDER};
            background-color: {C.SURFACE};
            color: {C.TEXT_PRIMARY};
            gridline-color: {C.DIVIDER};
        }}

        QTableWidget::item:selected, QListWidget::item:selected {{
            background-color: {C.PRIMARY_LIGHT};
            color: {C.TEXT_PRIMARY};
        }}

        QHeaderView::section {{
            background-color: {C.PRIMARY_LIGHT};
            color: {C.TEXT_PRIMARY};
            padding: 6px;
            border: none;
            font-weight: bold;
        }}

        QScrollBar:vertical {{
            background-color: {C.BACKGROUND};
            width: 12px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {C.TEXT_DISABLED};
            border-radius: 6px;
            min-height: 20px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {C.TEXT_SECONDARY};
        }}

        QLabel {{
            color: {C.TEXT_PRIMARY};
        }}

        QStatusBar {{
            border-top: 1px solid {C.DIVIDER};
            color: {C.TEXT_SECONDARY};
        }}
        """

    @staticmethod
    def get_dashboard_stylesheet(scheme=None) -> str:
        """Get dashboard-specific stylesheet"""
        C = scheme or active_scheme()
        return f"""
        QLabel {{
            color: {C.TEXT_SECONDARY};
        }}

        QLabel[title="true"] {{
            color: {C.TEXT_PRIMARY};
            font-size: 14px;
            font-weight: bold;
        }}

        QFrame#dashboardSection {{
            background-color: {C.SURFACE};
            border: 1px solid {C.DIVIDER};
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
    def apply_tooltips(widgets: dict) -> int:
        """Set help text on any widget whose key appears in TOOLTIPS.

        Takes a name->widget mapping so the caller decides what it owns, and
        returns how many were applied -- a silent zero is how a tooltip pass
        gets quietly lost in a refactor that renames a control.
        """
        n = 0
        for name, widget in (widgets or {}).items():
            text = TOOLTIPS.get(name)
            if text and widget is not None and hasattr(widget, "setToolTip"):
                widget.setToolTip(text)
                n += 1
        return n

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
