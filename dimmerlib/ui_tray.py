from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

_INDICATOR_BACKEND = None
_BACKEND_ERROR = None

try:
    gi.require_version("AyatanaAppIndicator3", "0.1")
    from gi.repository import AyatanaAppIndicator3 as _IndicatorLib
    _INDICATOR_BACKEND = "ayatana"
except Exception as exc:
    _IndicatorLib = None
    _BACKEND_ERROR = exc


class TrayController:
    def __init__(self, toggle_cb, quit_cb, icon_name="video-display"):
        self.toggle_cb = toggle_cb
        self.quit_cb = quit_cb
        self.icon_name = icon_name
        self.available = _IndicatorLib is not None
        self.backend = _INDICATOR_BACKEND
        self.error = _BACKEND_ERROR
        self.indicator = None
        self.menu = None

        if not self.available:
            return

        self.indicator = _IndicatorLib.Indicator.new(
            "x11-monitor-dimmer",
            self.icon_name,
            _IndicatorLib.IndicatorCategory.APPLICATION_STATUS,
        )
        self.indicator.set_status(_IndicatorLib.IndicatorStatus.ACTIVE)
        self.indicator.set_title("X11 Monitor Dimmer")

        self.menu = Gtk.Menu()

        self.toggle_item = Gtk.MenuItem.new_with_label("Show / Hide")
        self.toggle_item.connect("activate", self._on_toggle)
        self.menu.append(self.toggle_item)

        self.quit_item = Gtk.MenuItem.new_with_label("Quit")
        self.quit_item.connect("activate", self._on_quit)
        self.menu.append(self.quit_item)

        self.menu.show_all()
        self.indicator.set_menu(self.menu)

    def _on_toggle(self, *_args):
        self.toggle_cb()

    def _on_quit(self, *_args):
        self.quit_cb()

