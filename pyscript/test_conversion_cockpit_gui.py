"""CC-6b: keyboard shortcuts, tooltips and dark mode.

WHY THIS FILE EXISTS AT ALL. Before it, NO test under any name imported
`conversion_cockpit_gui` (2,033 lines) or `cockpit_widgets` (537) --
`test_conversion_cockpit.py` imports `pipeline_config` and
`conversion_executor` instead. That gap is why /whattask's test-pairing rule
found nothing to declare and CC-6b shipped blocked twice.

WHAT IS AND IS NOT TESTED HERE. Everything below runs WITHOUT a QApplication:
the shortcut table is checked against the class, the palettes against each
other, the tooltips through a stub widget. None of it proves the window looks
right -- that needs a display and a person, and is filed as
doc-1-cockpit-screenshots. What it does prove is that the DATA behind the three
features is complete and wired, which is the half that rots silently.

`conversion_cockpit_gui` calls `sys.exit(1)` at import when PyQt6 is missing --
it does not raise, it exits -- so the importorskip below is load-bearing: on a
machine without PyQt6 it must run BEFORE the import, or collection kills the
whole pytest process. Same class as the closed
scripts-test-midi-comparison-sys-exits-at-import.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pyscript"))

pytest.importorskip("PyQt6", reason="the cockpit GUI modules require PyQt6")

import cockpit_styles as S          # noqa: E402


# ---------------------------------------------------------------------------
# Dark mode
# ---------------------------------------------------------------------------

def test_dark_palette_defines_EVERY_colour_the_light_one_does():
    """THE LOAD-BEARING TEST. A hand-written second palette goes stale the
    moment a colour is added to the first, and the failure is invisible: the
    stylesheet f-string raises AttributeError only for the widget using it,
    at runtime, in dark mode only.

    Deliberately not written as "dark defines BACKGROUND" -- that would pass
    again the day someone adds a colour. Same shape as the PipelineConfig
    to_dict defect fixed 2026-09-04, where a hand-listed 15 of 16 fields
    dropped one silently.
    """
    light = {k for k in vars(S.ColorScheme) if k.isupper()}
    dark = {k for k in vars(S.DarkColorScheme) if k.isupper()}
    assert light, "sanity: ColorScheme should define colours"
    assert light - dark == set(), (
        "DarkColorScheme is missing colour(s) the light scheme defines: %s"
        % sorted(light - dark))
    assert dark - light == set(), (
        "DarkColorScheme defines colour(s) no light scheme has: %s"
        % sorted(dark - light))


def test_dark_mode_actually_changes_the_generated_stylesheet():
    """Not just that a toggle exists -- that the sheet the widgets get differs."""
    try:
        S.set_dark_mode(False)
        light_sheet = S.StyleSheet.get_main_stylesheet()
        S.set_dark_mode(True)
        dark_sheet = S.StyleSheet.get_main_stylesheet()
    finally:
        S.set_dark_mode(False)

    assert light_sheet != dark_sheet
    assert S.ColorScheme.BACKGROUND in light_sheet
    assert S.DarkColorScheme.BACKGROUND in dark_sheet
    assert S.ColorScheme.BACKGROUND not in dark_sheet, (
        "a light colour survived into the dark sheet -- something still names "
        "ColorScheme directly instead of the active scheme")


def test_dark_background_is_actually_darker():
    """Cheap, and it catches a palette pasted in from the wrong half."""
    def lum(hexstr):
        h = hexstr.lstrip("#")
        return sum(int(h[i:i + 2], 16) for i in (0, 2, 4)) / 3

    assert lum(S.DarkColorScheme.BACKGROUND) < lum(S.ColorScheme.BACKGROUND)
    assert lum(S.DarkColorScheme.TEXT_PRIMARY) > lum(S.ColorScheme.TEXT_PRIMARY)


def test_set_dark_mode_is_pure_data_and_needs_no_widgets():
    """The toggle must not require Qt -- that is what makes it testable."""
    try:
        S.set_dark_mode(True)
        assert S.dark_mode_enabled() is True
        assert S.active_scheme() is S.DarkColorScheme
        S.set_dark_mode(False)
        assert S.active_scheme() is S.ColorScheme
    finally:
        S.set_dark_mode(False)


# ---------------------------------------------------------------------------
# Keyboard shortcuts
# ---------------------------------------------------------------------------

def test_every_shortcut_binds_a_method_that_exists():
    """A key bound to a missing handler still constructs, still swallows the
    keypress, and does nothing -- the user presses Ctrl+S and gets silence.
    Checked against the CLASS so no QApplication is needed."""
    import conversion_cockpit_gui as G

    assert G.SHORTCUTS, "the shortcut table should not be empty"
    for key, handler in G.SHORTCUTS.items():
        fn = getattr(G.CockpitMainWindow, handler, None)
        assert callable(fn), (
            "SHORTCUTS binds %s to %r, which is not a method on "
            "CockpitMainWindow" % (key, handler))


def test_the_four_shortcuts_CC_6b_asked_for_are_present():
    """The bullet named these four explicitly."""
    import conversion_cockpit_gui as G

    for key in ("Ctrl+O", "Ctrl+S", "F5", "Esc"):
        assert key in G.SHORTCUTS, "CC-6b names %s" % key


def test_install_shortcuts_REFUSES_a_handler_that_does_not_exist():
    """The guard, exercised with stubs so it needs no Qt."""
    import conversion_cockpit_gui as G

    class FakeSeq:
        def __init__(self, key):
            self.key = key

    class FakeSc:
        def __init__(self, seq, parent):
            self.activated = self
        def connect(self, fn):
            pass

    class Win:
        _install_shortcuts = G.CockpitMainWindow._install_shortcuts
        def add_files_manually(self): pass
        def save_configuration(self): pass
        def refresh_dashboard(self): pass
        def stop_conversion(self): pass
        def toggle_dark_mode(self): pass

    ok = Win()._install_shortcuts(_seq=FakeSeq, _sc=FakeSc)
    assert len(ok) == len(G.SHORTCUTS)

    class Broken(Win):
        save_configuration = None

    with pytest.raises(AttributeError, match="save_configuration"):
        Broken()._install_shortcuts(_seq=FakeSeq, _sc=FakeSc)


# ---------------------------------------------------------------------------
# Tooltips
# ---------------------------------------------------------------------------

def test_every_declared_tooltip_has_real_text():
    assert S.TOOLTIPS, "the tooltip table should not be empty"
    for name, text in S.TOOLTIPS.items():
        assert isinstance(text, str) and len(text.strip()) > 10, (
            "tooltip for %r is empty or too short to help" % name)


def test_apply_tooltips_sets_only_what_it_declares_and_reports_the_count():
    """Returns a count because a silent zero is how a tooltip pass gets lost
    when a control is renamed."""
    class Stub:
        def __init__(self):
            self.tip = None
        def setToolTip(self, text):
            self.tip = text

    widgets = {name: Stub() for name in S.TOOLTIPS}
    widgets["not_declared"] = Stub()
    widgets["missing_widget"] = None

    n = S.UIHelpers.apply_tooltips(widgets)
    assert n == len(S.TOOLTIPS)
    assert widgets["not_declared"].tip is None
    for name in S.TOOLTIPS:
        assert widgets[name].tip == S.TOOLTIPS[name]


def test_config_panel_exposes_the_controls_the_tooltip_table_names():
    """The table and the panel must agree; a renamed control would otherwise
    silently lose its help text."""
    import cockpit_widgets as W

    src = Path(W.__file__).read_text(encoding="utf-8")
    assert "def apply_tooltips" in src
    for name in S.TOOLTIPS:
        assert ("self.%s" % name) in src, (
            "cockpit_styles.TOOLTIPS names %r but ConfigPanel has no such "
            "control" % name)
