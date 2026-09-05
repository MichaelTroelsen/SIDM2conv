"""First tests for pyscript/cockpit_widgets.py.

WHY THIS FILE EXISTS. Until 2026-09-04 no test under any name imported this
module (537 lines) -- `test_conversion_cockpit.py` imports `pipeline_config`
and `conversion_executor`, and `test_cockpit_real_files.py` imports only
stdlib and shells out. Its sibling `test_conversion_cockpit_gui.py` was added
the same day.

WHAT IS TESTED AND WHAT IS NOT. Every widget class here subclasses a Qt type,
so INSTANTIATING one needs a QApplication and, for anything visual, a display.
Nothing below constructs a widget. What it does cover is the part that is pure
and the part that has to agree with another module -- the two things that rot
without anyone noticing:

  * `_escape_html`, called unbound, including the REPLACEMENT ORDER;
  * the class-level tables (`COLORS`, `BADGE_STYLES`) whose keys other methods
    index into;
  * `get_config`/`_current_mode` driven by stubs, checked against what
    `PipelineConfig` will actually accept.

Whether any of it LOOKS right still needs a display and a person (DOC-1).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pyscript"))

pytest.importorskip("PyQt6", reason="cockpit_widgets imports PyQt6 widgets")

import cockpit_widgets as W          # noqa: E402
from pipeline_config import PipelineConfig          # noqa: E402


# ---------------------------------------------------------------------------
# Import surface
# ---------------------------------------------------------------------------

def test_every_public_widget_class_is_importable():
    """The cheapest possible regression: a NameError or a bad Qt import in this
    module currently surfaces only when the cockpit is launched by hand."""
    for name in ("StatsCard", "ProgressWidget", "FileListWidget",
                 "LogStreamWidget", "ConfigPanel", "StatusBadge"):
        assert hasattr(W, name), "cockpit_widgets no longer exports %s" % name


# ---------------------------------------------------------------------------
# _escape_html -- pure, and the only thing between a log line and the log pane
# ---------------------------------------------------------------------------

def test_escape_html_escapes_all_five_characters():
    esc = W.LogStreamWidget._escape_html
    assert esc(None, "<b>") == "&lt;b&gt;"
    assert esc(None, '"q"') == "&quot;q&quot;"
    assert esc(None, "it's") == "it&#39;s"
    assert esc(None, "a & b") == "a &amp; b"


def test_escape_html_replaces_AMPERSAND_FIRST():
    """THE ORDERING IS THE BUG THAT HIDES. `&` must be replaced before the
    others, or their output gets re-escaped: with `&` last, "<" becomes "&lt;"
    and then "&amp;lt;", and the pane shows the entity instead of the
    character. Reordering the chain is a plausible tidy-up that silently
    double-escapes every message.
    """
    esc = W.LogStreamWidget._escape_html
    assert esc(None, "<") == "&lt;", "not '&amp;lt;' -- ampersand must go first"
    assert esc(None, "&lt;") == "&amp;lt;", (
        "literal text that already looks like an entity must be escaped once, "
        "not left alone")

    # POSITIVE CONTROL. cockpit_widgets.py is read-only to the task that added
    # this file, so the usual proof -- reorder the real chain and watch the test
    # go red -- is not available. Instead, run the WRONG order over the same
    # input here and assert it produces the double-escaped result. If this ever
    # stops differing, the assertion above has stopped discriminating and is
    # passing for no reason.
    def wrong_order(text):
        return (text.replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("'", "&#39;")
                    .replace("&", "&amp;"))

    assert wrong_order("<") == "&amp;lt;"
    assert wrong_order("<") != esc(None, "<"), (
        "the ampersand-last ordering is no longer distinguishable from the "
        "correct one -- this test proves nothing")


def test_escape_html_is_what_append_log_actually_uses():
    """Structural: the escaping is worthless if the formatter stops calling it.
    `append_log` builds raw HTML by concatenation, so an unescaped message goes
    straight into the pane's markup."""
    import inspect
    src = inspect.getsource(W.LogStreamWidget.append_log)
    assert "_escape_html(message)" in src, (
        "append_log no longer escapes the message before embedding it in HTML")


# ---------------------------------------------------------------------------
# Class-level tables other methods index into
# ---------------------------------------------------------------------------

def test_log_colours_contain_the_fallback_key_append_log_uses():
    """`append_log` does COLORS.get(level.upper(), COLORS["INFO"]) -- the
    fallback is a direct subscript, so losing "INFO" turns an unknown log level
    into a KeyError instead of a default colour."""
    assert "INFO" in W.LogStreamWidget.COLORS
    for level, colour in W.LogStreamWidget.COLORS.items():
        assert re.fullmatch(r"#[0-9a-fA-F]{6}", colour), (
            "%s has a colour Qt will not parse: %r" % (level, colour))


def test_status_badge_styles_are_all_the_shape_the_widget_unpacks():
    """Each value is unpacked as (icon, colour, label); a 2- or 4-tuple raises
    at construction, which only happens when that status first occurs."""
    for status, style in W.StatusBadge.BADGE_STYLES.items():
        assert isinstance(style, tuple) and len(style) == 3, (
            "BADGE_STYLES[%r] is not a 3-tuple" % status)
        icon, colour, label = style
        assert icon and label, "%r has an empty icon or label" % status
        assert re.fullmatch(r"#[0-9a-fA-F]{6}", colour), (
            "%r has a colour Qt will not parse: %r" % (status, colour))


# ---------------------------------------------------------------------------
# The cross-module agreements -- these are the ones that break silently
# ---------------------------------------------------------------------------

class _Radio:
    def __init__(self, checked=False):
        self._c = checked

    def isChecked(self):
        return self._c


class _Combo:
    def __init__(self, text):
        self._t = text

    def currentText(self):
        return self._t


class _Label:
    def __init__(self, text):
        self._t = text

    def text(self):
        return self._t


class _Panel:
    """Just enough attributes for get_config/_current_mode, no Qt."""
    _current_mode = W.ConfigPanel._current_mode
    get_config = W.ConfigPanel.get_config

    def __init__(self, mode="simple", driver="laxity"):
        self.simple_radio = _Radio(mode == "simple")
        self.advanced_radio = _Radio(mode == "advanced")
        self.custom_radio = _Radio(mode == "custom")
        self.driver_combo = _Combo(driver)
        self.output_dir_label = _Label("out")
        self.step_checkboxes = {"conversion": _Radio(True),
                                "validation": _Radio(False)}


@pytest.mark.parametrize("mode", ["simple", "advanced", "custom"])
def test_current_mode_returns_each_mode_and_defaults_to_simple(mode):
    assert _Panel(mode=mode)._current_mode() == mode
    # nothing checked at all -> "simple", which is the documented fallback
    p = _Panel(mode="none-of-them")
    assert p._current_mode() == "simple"


def test_every_mode_the_panel_can_emit_is_one_PipelineConfig_ACCEPTS():
    """CROSS-MODULE INVARIANT. `PipelineConfig.set_mode` raises
    ConfigurationError on anything outside its three-item list, and the panel
    is the thing that supplies the string. If either side is edited alone the
    cockpit raises only when a user selects that mode.
    """
    for mode in ("simple", "advanced", "custom"):
        emitted = _Panel(mode=mode).get_config()["mode"]
        cfg = PipelineConfig()
        cfg.set_mode(emitted)          # must not raise
        assert cfg.mode == emitted


def test_get_config_emits_only_keys_PipelineConfig_actually_has():
    """CROSS-MODULE INVARIANT, the other direction. The panel's dict is fed
    back through PipelineConfig, whose from_json_text now REFUSES an unknown
    key outright -- so a key here that is not a field is a live failure, not a
    tidiness point.
    """
    import dataclasses
    fields = {f.name for f in dataclasses.fields(PipelineConfig)}
    emitted = set(_Panel().get_config())
    assert emitted - fields == set(), (
        "ConfigPanel.get_config emits key(s) PipelineConfig has no field for: "
        "%s" % sorted(emitted - fields))


def test_get_config_reports_the_checkbox_states_it_was_given():
    got = _Panel(driver="driver11").get_config()
    assert got["primary_driver"] == "driver11"
    assert got["enabled_steps"] == {"conversion": True, "validation": False}
