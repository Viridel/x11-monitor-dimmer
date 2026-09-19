#!/usr/bin/env python3
import os
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

shortcut_created = os.environ.get("X11MD_SHORTCUT_CREATED", "no") == "yes"

dialog = Gtk.MessageDialog(
    transient_for=None,
    flags=0,
    message_type=Gtk.MessageType.INFO,
    buttons=Gtk.ButtonsType.OK,
    text="X11 Monitor Dimmer installed successfully",
)
dialog.set_title("X11 Monitor Dimmer")
dialog.set_keep_above(True)

if shortcut_created:
    secondary = (
        "Desktop shortcut created.\n\n"
        "Launch X11 Monitor Dimmer from the desktop shortcut, "
        "or search for “X11 Monitor Dimmer” in the application menu.\n\n"
        "After it opens, you can pin the running icon to your preferred "
        "panel/taskbar for one-click access."
    )
else:
    secondary = (
        "To launch X11 Monitor Dimmer, search for “X11 Monitor Dimmer” "
        "in the application menu.\n\n"
        "After it opens, you can pin the running icon to your preferred "
        "panel/taskbar for one-click access."
    )

dialog.format_secondary_text(secondary)
dialog.run()
dialog.destroy()
