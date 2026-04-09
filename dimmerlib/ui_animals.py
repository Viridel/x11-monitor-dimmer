from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from .ui_rows import center_button_label


class AnimalsRow:
    def __init__(self, app, animals_state, remind_cb, no_thanks_cb):
        self.app = app
        self.animals_state = animals_state

        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=app.h_spacing)
        self.box.set_hexpand(True)
        self.box.set_halign(Gtk.Align.FILL)
        self.box.set_margin_top(app.row_v_spacing)
        self.box.set_no_show_all(True)

        self.label = Gtk.Label()
        self.label.set_hexpand(True)
        self.label.set_halign(Gtk.Align.START)
        self.label.set_xalign(0.0)
        self.label.set_line_wrap(True)
        self.label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)

        self.remind_btn = Gtk.Button(label="Remind me later")
        self.remind_btn.set_size_request(app._lu(132), app.btn_h)
        self.remind_btn.connect("clicked", remind_cb)
        center_button_label(self.remind_btn, app.small_font_pt)

        self.no_btn = Gtk.Button(label="No thanks")
        self.no_btn.set_size_request(app._lu(96), app.btn_h)
        self.no_btn.connect("clicked", no_thanks_cb)
        center_button_label(self.no_btn, app.small_font_pt)

        self.box.pack_start(self.label, True, True, 0)
        self.box.pack_start(self.remind_btn, False, False, 0)
        self.box.pack_start(self.no_btn, False, False, 0)

        self.apply_size_profile()
        self.hide()

    def attach_to(self, grid, row, col=1, width=6):
        grid.attach(self.box, col, row, width, 1)

    def apply_size_profile(self):
        self.box.set_spacing(self.app.h_spacing)
        self.box.set_margin_top(self.app.row_v_spacing)

        self.label.modify_font(
            Pango.FontDescription(f"Sans Bold Italic {self.app.small_font_pt + 2}")
        )

        self.remind_btn.set_size_request(self.app._lu(132), self.app.btn_h)
        self.no_btn.set_size_request(self.app._lu(96), self.app.btn_h)

        center_button_label(self.remind_btn, self.app.small_font_pt)
        center_button_label(self.no_btn, self.app.small_font_pt)

    def refresh_text(self):
        escaped = GLib.markup_escape_text(self.animals_state.get_message())
        self.label.set_markup(f"<b><i>{escaped}</i></b>")

    def refresh_visibility(self):
        if self.animals_state.should_show():
            self.show()
        else:
            self.hide()

    def refresh(self):
        self.refresh_text()
        self.refresh_visibility()

    def show(self):
        self.box.show()
        self.label.show()
        self.remind_btn.show()
        self.no_btn.show()

    def hide(self):
        self.box.hide()
