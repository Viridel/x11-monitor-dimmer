from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from .config import MIN_DEFAULT, MAX_CUSTOM_NAME, save_config


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


class _DefaultPanel:
    def __init__(self, app, title, control_factory):
        self.app = app
        self.frame = Gtk.Frame()
        self.frame.set_shadow_type(Gtk.ShadowType.IN)
        self.frame.set_hexpand(False)
        self.frame.set_halign(Gtk.Align.FILL)
        self.frame.set_valign(Gtk.Align.FILL)

        grid = Gtk.Grid()
        grid.set_column_spacing(app.default_inner_spacing)
        grid.set_row_spacing(app.default_row_spacing)
        grid.set_margin_start(app._lu(5))
        grid.set_margin_end(app._lu(7))
        grid.set_margin_top(app._lu(4))
        grid.set_margin_bottom(app._lu(4))
        self.frame.add(grid)
        self.grid = grid

        self.title = Gtk.Label(label=title)
        self.title.set_angle(90)
        self.title.set_halign(Gtk.Align.CENTER)
        self.title.set_valign(Gtk.Align.CENTER)
        self.title.set_justify(Gtk.Justification.CENTER)
        grid.attach(self.title, 0, 0, 1, 2)

        self.controls = {}
        self.labels = {}
        for row_index, slot in enumerate((1, 2)):
            control = control_factory(slot)
            control.set_halign(Gtk.Align.CENTER)
            control.set_valign(Gtk.Align.CENTER)
            self.controls[slot] = control
            grid.attach(control, 1, row_index, 1, 1)

            label = Gtk.Label()
            label.set_xalign(0.0)
            label.set_halign(Gtk.Align.START)
            label.set_valign(Gtk.Align.CENTER)
            label.set_ellipsize(Pango.EllipsizeMode.END)
            label.set_max_width_chars(MAX_CUSTOM_NAME)
            self.labels[slot] = label
            grid.attach(label, 2, row_index, 1, 1)

        self.apply_size_profile()

    def widget(self):
        return self.frame

    def set_name(self, slot, text):
        self.labels[slot].set_text(text)

    def apply_size_profile(self):
        self.frame.set_size_request(self.app.default_panel_w, self.app.monitor_row_h)
        self.grid.set_column_spacing(self.app.default_inner_spacing)
        self.grid.set_row_spacing(self.app.default_row_spacing)
        self.title.modify_font(Pango.FontDescription(f"Sans {self.app.small_font_pt}"))
        for label in self.labels.values():
            label.modify_font(Pango.FontDescription(f"Sans {self.app.small_font_pt + 1}"))


class MonitorRow:
    def __init__(self, app, mon, cfg_mon, selected_host, radio_group_widget=None):
        self.app = app
        self.mon = mon
        self.cfg_mon = cfg_mon
        self._setting_controls = False
        self._set_flash_sources = {1: None, 2: None}

        self._migrate_legacy_default()
        self.default_values = {
            1: self._read_default_value(1),
            2: self._read_default_value(2),
        }

        # selected_default_slot belonged to the earlier radio-button design.
        # Defaults are now independent saved slots, so the old UI-state key is discarded.
        if "selected_default_slot" in self.cfg_mon:
            self.cfg_mon.pop("selected_default_slot", None)
            save_config(self.app.config)

        if radio_group_widget is None:
            self.radio = Gtk.RadioButton.new(None)
        else:
            self.radio = Gtk.RadioButton.new_from_widget(radio_group_widget)
        self.radio.set_active(selected_host)
        self.radio.set_halign(Gtk.Align.CENTER)
        self.radio.set_valign(Gtk.Align.CENTER)
        self.radio.connect("toggled", self.on_radio_toggled)

        self.display_frame = Gtk.Frame()
        self.display_frame.set_shadow_type(Gtk.ShadowType.IN)
        self.display_frame.set_halign(Gtk.Align.FILL)
        self.display_frame.set_valign(Gtk.Align.FILL)
        self.display_label = Gtk.Label()
        self.display_label.set_xalign(0.0)
        self.display_label.set_yalign(0.5)
        self.display_label.set_halign(Gtk.Align.FILL)
        self.display_label.set_valign(Gtk.Align.CENTER)
        self.display_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.display_frame.add(self.display_label)
        self.refresh_display_name()

        self.off_btn = Gtk.Button(label="Dimmer\nOff")
        self.off_btn.set_halign(Gtk.Align.FILL)
        self.off_btn.set_valign(Gtk.Align.FILL)
        self.off_btn.connect("clicked", self.on_off)
        center_button_label(self.off_btn, app.small_font_pt)

        self.scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL,
            app.min_brightness,
            app.max_brightness,
            1,
        )
        self.scale.set_digits(0)
        self.scale.set_draw_value(False)
        # 100% = no dimming, and belongs at the LEFT of the control.
        # Lower percentages progress to the right as dimming increases.
        self.scale.set_inverted(True)
        self.scale.set_hexpand(True)
        self.scale.set_halign(Gtk.Align.FILL)
        self.scale.set_valign(Gtk.Align.CENTER)
        self.scale.set_size_request(app.slider_min_w, -1)
        self.scale.set_value(self.app.current_brightness[self.mon["output"]])
        self.scale.connect("value-changed", self.on_scale_changed)

        self.value_label = Gtk.Label()
        self.value_label.set_width_chars(app.value_chars)
        self.value_label.set_max_width_chars(app.value_chars)
        self.value_label.set_xalign(0.5)
        self.value_label.set_halign(Gtk.Align.CENTER)
        self.value_label.set_valign(Gtk.Align.CENTER)

        def set_factory(_slot):
            return Gtk.CheckButton()

        self.set_panel = _DefaultPanel(app, "Set", set_factory)
        for slot, button in self.set_panel.controls.items():
            button.set_active(False)
            button.connect("clicked", self.on_set_default_clicked, slot)

        def restore_factory(_slot):
            return Gtk.CheckButton()

        self.restore_panel = _DefaultPanel(app, "Restore", restore_factory)
        for slot, button in self.restore_panel.controls.items():
            button.connect("clicked", self.on_restore_clicked, slot)

        self.refresh_default_names()
        self.refresh_value_label()
        self.update_restore_controls()
        self.apply_size_profile()

    def _migrate_legacy_default(self):
        if "default_1_brightness" not in self.cfg_mon and self.cfg_mon.get("default_brightness") is not None:
            try:
                self.cfg_mon["default_1_brightness"] = int(self.cfg_mon["default_brightness"])
                save_config(self.app.config)
            except Exception:
                pass

    def _read_default_value(self, slot):
        value = self.cfg_mon.get(f"default_{slot}_brightness")
        if value is None:
            return None
        try:
            value = int(value)
        except Exception:
            return None
        if value < MIN_DEFAULT or value >= 100:
            return None
        return value

    def attach_to(self, grid, row_index):
        grid.attach(self.radio,                  0, row_index, 1, 1)
        grid.attach(self.display_frame,          1, row_index, 1, 1)
        grid.attach(self.off_btn,                2, row_index, 1, 1)
        grid.attach(self.scale,                  3, row_index, 1, 1)
        grid.attach(self.value_label,            4, row_index, 1, 1)
        grid.attach(self.set_panel.widget(),     5, row_index, 1, 1)
        grid.attach(self.restore_panel.widget(), 6, row_index, 1, 1)

    def apply_size_profile(self):
        self.display_frame.set_size_request(self.app.display_w, self.app.monitor_row_h)
        self.display_label.set_margin_start(self.app._lu(10))
        self.display_label.set_margin_end(self.app._lu(8))
        self.display_label.modify_font(Pango.FontDescription(f"Sans {self.app.display_font_pt}"))

        self.off_btn.set_size_request(self.app.off_btn_w, self.app.monitor_row_h)
        center_button_label(self.off_btn, self.app.small_font_pt + 1)

        self.scale.set_size_request(self.app.slider_min_w, -1)
        self.value_label.set_width_chars(self.app.value_chars)
        self.value_label.set_max_width_chars(self.app.value_chars)
        self.value_label.modify_font(Pango.FontDescription(f"Sans {self.app.value_font_pt}"))

        self.set_panel.apply_size_profile()
        self.restore_panel.apply_size_profile()

    def refresh_display_name(self):
        primary = self.app.effective_display_name(self.mon)
        output = self.mon["output"]
        escaped_primary = GLib.markup_escape_text(primary)
        escaped_output = GLib.markup_escape_text(output)
        self.display_label.set_markup(f"<b>{escaped_primary}</b>\n{escaped_output}")

    def refresh_default_names(self):
        for slot in (1, 2):
            name = self.app.get_default_name(slot)
            self.set_panel.set_name(slot, name)
            self.restore_panel.set_name(slot, name)

    def refresh_value_label(self):
        brightness = int(round(self.scale.get_value()))
        self.value_label.set_text(f"{brightness}%")

    def update_restore_controls(self):
        current = int(round(self.scale.get_value()))
        self._setting_controls = True
        try:
            for slot, button in self.restore_panel.controls.items():
                value = self.default_values.get(slot)
                button.set_sensitive(value is not None)
                button.set_active(value is not None and current == int(value))
        finally:
            self._setting_controls = False

    def _flash_set_control(self, slot):
        button = self.set_panel.controls[slot]

        existing = self._set_flash_sources.get(slot)
        if existing is not None:
            try:
                GLib.source_remove(existing)
            except Exception:
                pass

        self._setting_controls = True
        try:
            button.set_active(True)
            button.set_sensitive(False)
        finally:
            self._setting_controls = False

        def clear_flash():
            self._set_flash_sources[slot] = None
            self._setting_controls = True
            try:
                button.set_active(False)
                button.set_sensitive(True)
            finally:
                self._setting_controls = False
            return False

        self._set_flash_sources[slot] = GLib.timeout_add(1000, clear_flash)

    def on_radio_toggled(self, button):
        if not button.get_active():
            return
        self.app.config["ui_host_output"] = self.mon["output"]
        save_config(self.app.config)
        GLib.idle_add(self.app.transition_to_host_output, self.mon["output"])

    def on_scale_changed(self, scale):
        self.refresh_value_label()
        self.update_restore_controls()
        brightness = int(round(scale.get_value()))
        self.app.apply_brightness(self.mon["output"], brightness)

    def on_off(self, *_args):
        self.scale.set_value(100)
        self.app.show_status(f"Dimming overlay terminated on {self.app.display_name_for_message(self.mon)}.")

    def on_set_default_clicked(self, button, slot):
        if self._setting_controls:
            return

        brightness = int(round(self.scale.get_value()))
        error = self.app.default_value_error(brightness)
        if error:
            self._setting_controls = True
            try:
                button.set_active(False)
            finally:
                self._setting_controls = False
            self.app.show_status(error)
            return

        # Each slot is an independent stored value. Saving one slot never writes
        # to, clears, or otherwise changes the other slot.
        self.default_values[slot] = brightness
        self.cfg_mon[f"default_{slot}_brightness"] = brightness
        self.app.config.setdefault("monitors", {})[self.mon["output"]] = self.cfg_mon
        save_config(self.app.config)

        self.update_restore_controls()
        self._flash_set_control(slot)
        self.app.show_status(
            f"{self.app.get_default_name(slot)} saved for "
            f"{self.app.display_name_for_message(self.mon)} at {brightness}%."
        )

    def on_restore_clicked(self, _button, slot):
        if self._setting_controls:
            return
        value = self.default_values.get(slot)
        if value is None:
            return

        self.scale.set_value(int(value))
        self.update_restore_controls()
        self.app.show_status(
            f"{self.app.get_default_name(slot)} restored for "
            f"{self.app.display_name_for_message(self.mon)}."
        )
