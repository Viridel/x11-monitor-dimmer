from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from .config import MIN_BRIGHTNESS, MAX_BRIGHTNESS, MIN_DEFAULT, default_label, save_config


def center_button_label(btn, font_pt=None):
    child = btn.get_child()
    if child is None:
        return
    if isinstance(child, Gtk.Label):
        child.set_justify(Gtk.Justification.CENTER)
        child.set_xalign(0.5)
        child.set_yalign(0.5)
        child.set_line_wrap(True)
        child.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        if font_pt is not None:
            child.modify_font(Pango.FontDescription(f"Sans {font_pt}"))


class MonitorRow:
    def __init__(self, app, mon, cfg_mon, selected_host, radio_group_widget=None):
        self.app = app
        self.mon = mon
        self.cfg_mon = cfg_mon
        self.default_value = cfg_mon.get("default_brightness")

        if radio_group_widget is None:
            self.radio = Gtk.RadioButton.new(None)
        else:
            self.radio = Gtk.RadioButton.new_from_widget(radio_group_widget)
        self.radio.set_active(selected_host)
        self.radio.set_halign(Gtk.Align.CENTER)
        self.radio.connect("toggled", self.on_radio_toggled)

        self.name_entry = Gtk.Entry()
        self.name_entry.set_width_chars(app.entry_chars)
        self.name_entry.set_max_width_chars(app.entry_chars + 2)
        self.name_entry.set_hexpand(False)
        self.name_entry.set_halign(Gtk.Align.FILL)
        self.name_entry.set_alignment(0.0)

        default_name = (
            app.default_monitor_label(mon)
            if hasattr(app, "default_monitor_label")
            else default_label(mon)
        )
        self.name_entry.set_text(cfg_mon.get("custom_name") or default_name)

        self.name_entry.connect("activate", self.save_name)
        self.name_entry.connect("focus-out-event", self.on_focus_out)

        self.scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL,
            MIN_BRIGHTNESS,
            MAX_BRIGHTNESS,
            1,
        )
        self.scale.set_digits(0)
        self.scale.set_draw_value(False)
        self.scale.set_inverted(True)
        self.scale.set_hexpand(True)
        self.scale.set_halign(Gtk.Align.FILL)
        self.scale.set_size_request(app.slider_min_w, -1)
        self.scale.set_value(self.app.current_brightness[self.mon["output"]])
        self.scale.connect("value-changed", self.on_scale_changed)

        self.value_label = Gtk.Label()
        self.value_label.set_width_chars(app.value_chars)
        self.value_label.set_max_width_chars(app.value_chars)
        self.value_label.set_xalign(0.5)
        self.value_label.set_halign(Gtk.Align.CENTER)

        self.off_btn = Gtk.Button(label="Off")
        self.off_btn.set_size_request(app.off_btn_w, app.btn_h)
        self.off_btn.connect("clicked", self.on_off)
        center_button_label(self.off_btn, app.small_font_pt)

        self.restore_btn = Gtk.Button(label="Restore\nDefault")
        self.restore_btn.set_size_request(app.restore_btn_w, app.btn_h)
        self.restore_btn.connect("clicked", self.on_restore)
        center_button_label(self.restore_btn, app.small_font_pt)

        self.save_btn = Gtk.Button(label="Save as\nDefault")
        self.save_btn.set_size_request(app.save_btn_w, app.btn_h)
        self.save_btn.connect("clicked", self.on_save_default)
        center_button_label(self.save_btn, app.small_font_pt)

        self.error_label = Gtk.Label()
        self.error_label.set_xalign(0.0)
        self.error_label.set_halign(Gtk.Align.START)
        self.error_label.set_hexpand(True)
        self.error_label.set_line_wrap(True)
        self.error_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.error_label.set_max_width_chars(72)
        self.error_label.set_no_show_all(True)
        self.error_label.modify_font(Pango.FontDescription(f"Sans Italic {app.error_font_pt}"))

        self.refresh_value_label()
        self.update_restore_enabled()

    def attach_to(self, grid, row_index):
        grid.attach(self.radio,       0, row_index,     1, 1)
        grid.attach(self.name_entry,  1, row_index,     1, 1)
        grid.attach(self.scale,       2, row_index,     1, 1)
        grid.attach(self.value_label, 3, row_index,     1, 1)
        grid.attach(self.off_btn,     4, row_index,     1, 1)
        grid.attach(self.restore_btn, 5, row_index,     1, 1)
        grid.attach(self.save_btn,    6, row_index,     1, 1)
        grid.attach(self.error_label, 1, row_index + 1, 6, 1)

    def refresh_value_label(self):
        brightness = int(round(self.scale.get_value()))
        self.value_label.set_text(str(brightness))

    def clear_error(self):
        self.error_label.hide()
        self.error_label.set_text("")

    def clear_error_if_visible(self):
        if self.error_label.get_visible():
            self.clear_error()

    def show_error(self, text):
        self.error_label.set_text(text)
        self.error_label.show()

    def update_restore_enabled(self):
        self.restore_btn.set_sensitive(self.default_value is not None)

    def on_radio_toggled(self, button):
        self.clear_error_if_visible()
        if not button.get_active():
            return
        self.app.config["ui_host_output"] = self.mon["output"]
        save_config(self.app.config)
        GLib.idle_add(self.app.transition_to_host_output, self.mon["output"])

    def save_name(self, *_args):
        self.clear_error_if_visible()
        self.app.config.setdefault("monitors", {}).setdefault(self.mon["output"], {})["custom_name"] = self.name_entry.get_text().strip()
        save_config(self.app.config)

    def on_focus_out(self, *_args):
        self.save_name()
        self.name_entry.set_position(0)
        return False

    def on_scale_changed(self, scale):
        self.clear_error_if_visible()
        self.refresh_value_label()
        brightness = int(round(scale.get_value()))
        self.app.apply_brightness(self.mon["output"], brightness, source_output=self.mon["output"])

    def on_off(self, *_args):
        self.clear_error_if_visible()
        self.scale.set_value(100)

    def on_restore(self, *_args):
        self.clear_error_if_visible()
        if self.default_value is None:
            return
        self.scale.set_value(int(self.default_value))

    def on_save_default(self, *_args):
        self.clear_error_if_visible()
        brightness = int(round(self.scale.get_value()))
        if brightness >= 100:
            self.show_error("100 cannot be saved as Default. Use Off to stop dimming.")
            return
        if brightness < MIN_DEFAULT:
            self.show_error("To maintain baseline monitor visibility in all conditions, brightness lower than 40% cannot be saved as Default.")
            return

        self.default_value = brightness
        self.cfg_mon["default_brightness"] = brightness
        self.app.config.setdefault("monitors", {})[self.mon["output"]] = self.cfg_mon
        save_config(self.app.config)
        self.update_restore_enabled()
