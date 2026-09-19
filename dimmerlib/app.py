from __future__ import annotations
import os
import signal
import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from .config import RUNTIME_DIR, PIDFILE, already_running
from .ui_window import DimmerApp
from .ui_tray import TrayController

APP = None
TRAY = None
IS_QUITTING = False

_ICON_DIR_CANDIDATES = (
    Path.home() / ".local" / "share" / "x11-monitor-dimmer" / "icons",
    Path("/usr/share/x11-monitor-dimmer/icons"),
)
ICON_DIR = next(
    (path for path in _ICON_DIR_CANDIDATES if (path / "x11-monitor-dimmer.png").exists()),
    _ICON_DIR_CANDIDATES[-1],
)
ICON_FILE = ICON_DIR / "x11-monitor-dimmer.png"


def on_usr1(_signum, _frame):
    if APP is not None:
        GLib.idle_add(APP.toggle_visibility)


def quit_app():
    global IS_QUITTING
    if IS_QUITTING:
        return False

    IS_QUITTING = True

    if APP is not None:
        try:
            APP.shutdown()
        except Exception:
            pass

    Gtk.main_quit()
    return False


def toggle_app():
    if APP is not None:
        GLib.idle_add(APP.toggle_visibility)
    return False


def main():
    global APP, TRAY

    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

    existing = already_running()
    if existing:
        print(existing)
        return 0

    PIDFILE.write_text(str(os.getpid()), encoding="utf-8")
    signal.signal(signal.SIGUSR1, on_usr1)

    if ICON_FILE.exists():
        try:
            Gtk.Window.set_default_icon_from_file(str(ICON_FILE))
        except Exception:
            pass

    APP = DimmerApp()
    TRAY = TrayController(
        toggle_cb=toggle_app,
        quit_cb=quit_app,
        icon_name="x11-monitor-dimmer",
        icon_theme_path=str(ICON_DIR),
    )

    Gtk.main()

    if APP is not None and not IS_QUITTING:
        APP.shutdown()

    return 0


if __name__ == "__main__":
    sys.exit(main())
