from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk

from .config import (
    APP_NAME,
    load_config,
    parse_xrandr,
    save_config,
    default_label,
)
from .overlay import OverlayManager
from .ui_rows import MonitorRow, center_button_label
from .ui_alignment import WindowAligner
from .for_the_animals import ForTheAnimals
from .ui_animals import AnimalsRow
from .ddcu import resolve_display_models


class DimmerApp(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_NAME)

        self.config = load_config()
        self.monitors = parse_xrandr()
        self.monitor_map = {m["output"]: m for m in self.monitors}
        self.ddcu_report = resolve_display_models()
        self.output_model_map = self.ddcu_report.get("output_model_map", {})
        self.rows = {}
        self.overlay = OverlayManager()
        self.current_brightness = {m["output"]: 100 for m in self.monitors}
        self._transition_running = False
        self._sync_in_progress = False
        self.animals = ForTheAnimals(self.config)

        initial_host = self.config.get("ui_host_output")
        if initial_host not in self.monitor_map:
            primary = self.primary_monitor()
            initial_host = primary["output"] if primary else None
            self.config["ui_host_output"] = initial_host
            save_config(self.config)

        self.host_monitor = self.monitor_map.get(initial_host) or self.primary_monitor()
        host_width = self.host_monitor["width"] if self.host_monitor else 1920
        self._set_profile_numbers(host_width)
        self._sync_window_height_to_animals()

        self.set_border_width(self.border_px)
        self.set_default_size(self._lu(self.window_w), self._lu(self.window_h))
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.stick()
        self.connect("delete-event", self.on_delete)

        self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=self.outer_spacing)
        self.root.set_hexpand(True)
        self.add(self.root)

        self.top_grid = Gtk.Grid()
        self.top_grid.set_column_spacing(self.h_spacing)
        self.top_grid.set_row_spacing(self.row_v_spacing)
        self.top_grid.set_column_homogeneous(False)
        self.top_grid.set_hexpand(True)
        self.top_grid.set_halign(Gtk.Align.FILL)
        self.root.pack_start(self.top_grid, False, False, 0)

        radio_group_widget = None
        for idx, mon in enumerate(self.monitors):
            cfg_mon = self.config.setdefault("monitors", {}).setdefault(mon["output"], {})
            row = MonitorRow(
                self,
                mon,
                cfg_mon,
                selected_host=(mon["output"] == initial_host),
                radio_group_widget=radio_group_widget,
            )
            if radio_group_widget is None:
                radio_group_widget = row.radio
            self.rows[mon["output"]] = row
            row.attach_to(self.top_grid, idx * 2)

        bottom_row = len(self.monitors) * 2

        self.reset_names_btn = Gtk.Button(label="Reset Device\nNames")
        self.reset_names_btn.set_size_request(self.name_btn_w, self.btn_h)
        self.reset_names_btn.set_hexpand(False)
        self.reset_names_btn.set_halign(Gtk.Align.FILL)
        self.reset_names_btn.connect("clicked", self.on_reset_device_names)
        center_button_label(self.reset_names_btn, self.small_font_pt)
        self.top_grid.attach(self.reset_names_btn, 1, bottom_row, 1, 1)

        self.sync_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=self.sync_spacing)
        self.sync_box.set_hexpand(False)
        self.sync_box.set_halign(Gtk.Align.CENTER)

        self.sync_check = Gtk.CheckButton()
        self.sync_check.set_active(bool(self.config.get("sync_sliders", False)))
        self.sync_check.connect("toggled", self.on_sync_toggled)

        self.sync_label = Gtk.Label(label="Synchronize Sliders")
        self.sync_label.set_xalign(0.0)

        self.sync_box.pack_start(self.sync_check, False, False, 0)
        self.sync_box.pack_start(self.sync_label, False, False, 0)
        self.top_grid.attach(self.sync_box, 2, bottom_row, 1, 1)

        self.all_off_btn = Gtk.Button(label="All Off")
        self.all_off_btn.set_size_request(self.action_btn_w, self.btn_h)
        self.all_off_btn.set_hexpand(False)
        self.all_off_btn.set_halign(Gtk.Align.FILL)
        self.all_off_btn.connect("clicked", self.on_all_off)
        center_button_label(self.all_off_btn, self.small_font_pt)
        self.top_grid.attach(self.all_off_btn, 4, bottom_row, 1, 1)

        self.all_default_btn = Gtk.Button(label="All to\nDefault")
        self.all_default_btn.set_size_request(self.action_btn_w, self.btn_h)
        self.all_default_btn.set_hexpand(False)
        self.all_default_btn.set_halign(Gtk.Align.FILL)
        self.all_default_btn.connect("clicked", self.on_all_to_default)
        center_button_label(self.all_default_btn, self.small_font_pt)
        self.top_grid.attach(self.all_default_btn, 5, bottom_row, 1, 1)

        self.close_btn = Gtk.Button(label="Close")
        self.close_btn.set_size_request(self.action_btn_w, self.btn_h)
        self.close_btn.set_hexpand(False)
        self.close_btn.set_halign(Gtk.Align.FILL)
        self.close_btn.connect("clicked", self.on_close_clicked)
        center_button_label(self.close_btn, self.small_font_pt)
        self.top_grid.attach(self.close_btn, 6, bottom_row, 1, 1)

        animals_row = bottom_row + 1
        self.animals_ui = AnimalsRow(
            app=self,
            animals_state=self.animals,
            remind_cb=self.on_animals_remind,
            no_thanks_cb=self.on_animals_no_thanks,
        )
        self.animals_ui.attach_to(self.top_grid, animals_row, col=1, width=6)

        self.aligner = WindowAligner(
            window=self,
            target_width_fn=self._target_window_width,
            size_profile_callback=self._apply_size_profile,
            top_margin=8,
            second_pass_ms=90,
        )

        self.show_all()
        GLib.idle_add(self._initial_setup)

    def default_monitor_label(self, mon):
        resolved = self.output_model_map.get(mon["output"])
        if resolved:
            return f"{resolved} ({mon['output']})"
        return default_label(mon)

    def _ui_scale(self):
        try:
            scale = self.get_scale_factor()
            if scale and scale > 0:
                return int(scale)
        except Exception:
            pass
        return 1

    def _lu(self, px):
        return max(1, round(px / self._ui_scale()))

    def _target_window_width(self, mon_width):
        if mon_width <= 1920:
            return 960
        if mon_width >= 3840:
            return 1320
        return int(mon_width * 0.38)

    def _set_profile_numbers(self, mon_width):
        if mon_width <= 1920:
            self.window_w = 960
            self.window_h_base = 148
            self.window_h_animals = 184

            slider_actual = 110
            action_actual = 84
            off_actual = 84
            restore_actual = 84
            save_actual = 84
            name_actual = 110
            btn_h_actual = 28

            self.entry_chars = 11
            self.value_chars = 3
            self.small_font_pt = 8
            self.error_font_pt = 9

            border_actual = 4
            outer_actual = 4
            h_spacing_actual = 6
            row_v_spacing_actual = 4
            sync_spacing_actual = 8
        else:
            self.window_w = 1320
            self.window_h_base = 148
            self.window_h_animals = 184

            slider_actual = 150
            action_actual = 96
            off_actual = 96
            restore_actual = 96
            save_actual = 96
            name_actual = 120
            btn_h_actual = 28

            self.entry_chars = 12
            self.value_chars = 3
            self.small_font_pt = 8
            self.error_font_pt = 9

            border_actual = 4
            outer_actual = 4
            h_spacing_actual = 8
            row_v_spacing_actual = 4
            sync_spacing_actual = 10

        self.slider_min_w = self._lu(slider_actual)
        self.action_btn_w = self._lu(action_actual)
        self.off_btn_w = self._lu(off_actual)
        self.restore_btn_w = self._lu(restore_actual)
        self.save_btn_w = self._lu(save_actual)
        self.name_btn_w = self._lu(name_actual)
        self.btn_h = self._lu(btn_h_actual)

        self.border_px = self._lu(border_actual)
        self.outer_spacing = self._lu(outer_actual)
        self.h_spacing = self._lu(h_spacing_actual)
        self.row_v_spacing = self._lu(row_v_spacing_actual)
        self.sync_spacing = self._lu(sync_spacing_actual)

    def _sync_window_height_to_animals(self):
        self.window_h = self.window_h_animals if self.animals.should_show() else self.window_h_base

    def _apply_size_profile(self, mon):
        self.host_monitor = mon
        self._set_profile_numbers(mon["width"])
        self._sync_window_height_to_animals()

        self.set_border_width(self.border_px)
        self.root.set_spacing(self.outer_spacing)
        self.top_grid.set_column_spacing(self.h_spacing)
        self.top_grid.set_row_spacing(self.row_v_spacing)

        for row in self.rows.values():
            row.name_entry.set_width_chars(self.entry_chars)
            row.name_entry.set_max_width_chars(self.entry_chars + 2)

            row.scale.set_size_request(self.slider_min_w, -1)

            row.value_label.set_width_chars(self.value_chars)
            row.value_label.set_max_width_chars(self.value_chars)

            row.off_btn.set_size_request(self.off_btn_w, self.btn_h)
            row.restore_btn.set_size_request(self.restore_btn_w, self.btn_h)
            row.save_btn.set_size_request(self.save_btn_w, self.btn_h)

            center_button_label(row.off_btn, self.small_font_pt)
            center_button_label(row.restore_btn, self.small_font_pt)
            center_button_label(row.save_btn, self.small_font_pt)

        self.reset_names_btn.set_size_request(self.name_btn_w, self.btn_h)
        center_button_label(self.reset_names_btn, self.small_font_pt)

        self.sync_box.set_spacing(self.sync_spacing)

        self.all_off_btn.set_size_request(self.action_btn_w, self.btn_h)
        center_button_label(self.all_off_btn, self.small_font_pt)

        self.all_default_btn.set_size_request(self.action_btn_w, self.btn_h)
        center_button_label(self.all_default_btn, self.small_font_pt)

        self.close_btn.set_size_request(self.action_btn_w, self.btn_h)
        center_button_label(self.close_btn, self.small_font_pt)

        self.animals_ui.apply_size_profile()
        self.animals_ui.refresh()

        self.top_grid.queue_resize()
        self.queue_resize()

    def _refresh_for_the_animals(self):
        self.animals_ui.refresh()
        self._sync_window_height_to_animals()
        self.top_grid.queue_resize()
        self.queue_resize()

    def _realign_to_current_host(self):
        GLib.idle_add(self.move_to_host_output, self.config.get("ui_host_output"))

    def _register_controller_open(self):
        self.animals.controller_opened()
        save_config(self.config)
        self._refresh_for_the_animals()

    def _initial_setup(self):
        self.close_btn.grab_focus()
        for row in self.rows.values():
            row.name_entry.select_region(0, 0)
            row.name_entry.set_position(0)
            row.refresh_value_label()

        self._register_controller_open()
        self.move_to_host_output(self.config.get("ui_host_output"))
        return False

    def primary_monitor(self):
        for mon in self.monitors:
            if mon["primary"]:
                return mon
        return self.monitors[0] if self.monitors else None

    def move_to_host_output(self, output):
        mon = self.monitor_map.get(output)
        if mon is None:
            mon = self.primary_monitor()
        if mon is None:
            return False
        return self.aligner.align_to_monitor(mon)

    def transition_to_host_output(self, output):
        if self._transition_running:
            return False

        self._transition_running = True
        steps = 10
        interval_ms = 40
        state = {"phase": "out", "step": 0, "output": output}

        def tick():
            if state["phase"] == "out":
                opacity = max(0.0, 1.0 - ((state["step"] + 1) / steps))
                self.set_opacity(opacity)
                state["step"] += 1
                if state["step"] >= steps:
                    self.move_to_host_output(state["output"])
                    state["phase"] = "in"
                    state["step"] = 0
                return True

            opacity = min(1.0, (state["step"] + 1) / steps)
            self.set_opacity(opacity)
            state["step"] += 1
            if state["step"] >= steps:
                self.set_opacity(1.0)
                self._transition_running = False
                return False
            return True

        GLib.timeout_add(interval_ms, tick)
        return False

    def fade_show(self):
        self.set_opacity(0.0)
        self.show_all()
        self.close_btn.grab_focus()

        steps = 8
        interval = 30
        state = {"step": 0}

        def tick():
            opacity = min(1.0, (state["step"] + 1) / steps)
            self.set_opacity(opacity)
            state["step"] += 1
            return state["step"] < steps

        GLib.timeout_add(interval, tick)

    def fade_hide(self):
        steps = 8
        interval = 30
        state = {"step": 0}

        def tick():
            opacity = max(0.0, 1.0 - ((state["step"] + 1) / steps))
            self.set_opacity(opacity)
            state["step"] += 1
            if state["step"] >= steps:
                self.hide()
                self.set_opacity(1.0)
                return False
            return True

        GLib.timeout_add(interval, tick)

    def apply_brightness(self, output, brightness, source_output=None):
        brightness = int(brightness)
        self.current_brightness[output] = brightness

        mon = self.monitor_map.get(output)
        if mon is not None:
            if brightness >= 100:
                self.overlay.turn_off(output)
            else:
                self.overlay.set_brightness(mon, brightness)

        if self._sync_in_progress:
            return

        if self.sync_check.get_active() and source_output is not None:
            self._sync_in_progress = True
            try:
                for other_output, row in self.rows.items():
                    if other_output == source_output:
                        continue
                    if int(round(row.scale.get_value())) != brightness:
                        row.scale.set_value(brightness)
            finally:
                self._sync_in_progress = False

    def toggle_visibility(self):
        if self.is_visible():
            self.fade_hide()
        else:
            for output, row in self.rows.items():
                row.scale.set_value(self.current_brightness.get(output, 100))
                row.name_entry.set_position(0)
                row.refresh_value_label()

            self.fade_show()
            self._register_controller_open()
            self.close_btn.grab_focus()
            GLib.idle_add(self.move_to_host_output, self.config.get("ui_host_output"))

    def on_reset_device_names(self, *_args):
        for output, row in self.rows.items():
            cfg_mon = self.config.setdefault("monitors", {}).setdefault(output, {})
            cfg_mon.pop("custom_name", None)
            row.name_entry.set_text(self.default_monitor_label(self.monitor_map[output]))
            row.name_entry.set_position(0)
        save_config(self.config)

    def on_sync_toggled(self, button):
        self.config["sync_sliders"] = bool(button.get_active())
        save_config(self.config)

    def on_all_off(self, *_args):
        for row in self.rows.values():
            row.clear_error_if_visible()
            row.scale.set_value(100)

    def on_all_to_default(self, *_args):
        for row in self.rows.values():
            row.clear_error_if_visible()
            if row.default_value is not None:
                row.scale.set_value(int(row.default_value))

    def on_animals_remind(self, *_args):
        self.animals.remind_me_later()
        save_config(self.config)
        self._refresh_for_the_animals()
        self._realign_to_current_host()

    def on_animals_no_thanks(self, *_args):
        self.animals.no_thanks()
        save_config(self.config)
        self._refresh_for_the_animals()
        self._realign_to_current_host()

    def on_close_clicked(self, *_args):
        self.fade_hide()

    def on_delete(self, *_args):
        self.fade_hide()
        return True

    def shutdown(self):
        self.overlay.shutdown()
