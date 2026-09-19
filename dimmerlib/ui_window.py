from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, Pango

from .config import (
    APP_NAME,
    MIN_BRIGHTNESS,
    MAX_BRIGHTNESS,
    MIN_DEFAULT,
    MAX_CUSTOM_NAME,
    QUICK_BRIGHTNESS_LEVELS,
    load_config,
    parse_xrandr,
    save_config,
)
from .overlay import OverlayManager
from .ui_rows import MonitorRow, center_button_label
from .ui_alignment import WindowAligner
from .ui_dialogs import (
    ABOUT_CREDITS_RESPONSE,
    ABOUT_HISTORY_RESPONSE,
    ABOUT_ROADMAP_RESPONSE,
    AboutDialog,
    CreditsDialog,
    FutureRoadmapDialog,
    HistoryLogDialog,
    NameDefaultsDialog,
    NameDisplaysDialog,
)
from .for_the_animals import ForTheAnimals
from .ui_animals import AnimalsRow
from .display_id import resolve_display_names, fallback_display_name


class DimmerApp(Gtk.Window):
    def __init__(self):
        super().__init__(title=APP_NAME)
        # Stable X11 window identity for Cinnamon launcher/taskbar grouping.
        self.set_wmclass("x11-monitor-dimmer", "X11MonitorDimmer")

        self.min_brightness = MIN_BRIGHTNESS
        self.max_brightness = MAX_BRIGHTNESS
        self.config = load_config()
        self.monitors = parse_xrandr()
        self.monitor_map = {m["output"]: m for m in self.monitors}
        self.display_id_report = resolve_display_names()
        self.output_model_map = self.display_id_report.get("output_name_map", {})
        self.display_number_map = {
            mon["output"]: index
            for index, mon in enumerate(self.monitors, start=1)
        }
        self.rows = {}
        self.overlay = OverlayManager()
        self.current_brightness = {m["output"]: 100 for m in self.monitors}
        self._transition_running = False
        self._close_countdown_source = None
        self._close_countdown_remaining = 0
        self._close_countdown_base = ""
        self._pending_close_after_animals = None
        self._modal_shade_window = None
        self.animals = ForTheAnimals(self.config)

        self._migrate_legacy_display_names()

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
        # The controller is a real application window.  NORMAL + an explicit
        # taskbar hint lets Cinnamon associate the running window with the
        # installed launcher so it can be pinned normally.
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.set_skip_taskbar_hint(False)
        self.stick()
        self.connect("delete-event", self.on_delete)

        # Main content is hosted in a Gtk.Overlay so modal dialogs can dim the
        # controller *inside the existing window*. This avoids creating any
        # second top-level shade window, so there is no WM shadow box and no
        # stacking race that can hide the popup.
        self.client_overlay = Gtk.Overlay()
        self.client_overlay.set_hexpand(True)
        self.client_overlay.set_vexpand(True)
        self.add(self.client_overlay)

        self.root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=self.outer_spacing)
        self.root.set_hexpand(True)
        self.client_overlay.add(self.root)

        # Modal background shade. Draw it directly inside the controller's
        # existing client window so there is no second X11 top-level window,
        # no window-manager shadow, and no wallpaper showing through.
        self.modal_dim = Gtk.DrawingArea()
        self.modal_dim.set_hexpand(True)
        self.modal_dim.set_vexpand(True)
        self.modal_dim.set_halign(Gtk.Align.FILL)
        self.modal_dim.set_valign(Gtk.Align.FILL)
        self.modal_dim.set_no_show_all(True)
        self.modal_dim.connect("draw", self._draw_modal_dim)
        self.client_overlay.add_overlay(self.modal_dim)
        self.modal_dim.hide()

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
            row.attach_to(self.top_grid, idx)

        bottom_row = len(self.monitors)

        self.names_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=self.bottom_inner_spacing)
        self.names_box.set_halign(Gtk.Align.FILL)
        self.names_box.set_valign(Gtk.Align.FILL)

        self.name_displays_btn = Gtk.Button(label="Name Displays")
        self.name_displays_btn.connect("clicked", self.on_name_displays)
        center_button_label(self.name_displays_btn, self.small_font_pt + 1)
        self.names_box.pack_start(self.name_displays_btn, True, True, 0)

        self.name_defaults_btn = Gtk.Button(label="Name Defaults")
        self.name_defaults_btn.connect("clicked", self.on_name_defaults)
        center_button_label(self.name_defaults_btn, self.small_font_pt + 1)
        self.names_box.pack_start(self.name_defaults_btn, True, True, 0)

        self.top_grid.attach(self.names_box, 1, bottom_row, 1, 2)

        self.all_off_btn = Gtk.Button(label="Dimmer\nOff All")
        self.all_off_btn.set_halign(Gtk.Align.FILL)
        self.all_off_btn.set_valign(Gtk.Align.FILL)
        self.all_off_btn.connect("clicked", self.on_all_off)
        center_button_label(self.all_off_btn, self.small_font_pt + 1)
        self.top_grid.attach(self.all_off_btn, 2, bottom_row, 1, 2)

        self.quick_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=self.quick_spacing)
        self.quick_box.set_hexpand(True)
        self.quick_box.set_halign(Gtk.Align.FILL)
        self.quick_buttons = []
        for level in QUICK_BRIGHTNESS_LEVELS:
            btn = Gtk.Button(label=f"{level}%")
            btn.set_hexpand(True)
            btn.connect("clicked", self.on_quick_level, level)
            center_button_label(btn, self.small_font_pt)
            self.quick_box.pack_start(btn, True, True, 0)
            self.quick_buttons.append(btn)
        self.top_grid.attach(self.quick_box, 3, bottom_row, 1, 1)

        # Use a literal circled-information glyph rather than a themed icon. Some
        # desktop icon themes map the standard information icon to a lightbulb.
        self.version_btn = Gtk.Button(label="ⓘ")
        self.version_btn.set_halign(Gtk.Align.FILL)
        self.version_btn.set_valign(Gtk.Align.FILL)
        self.version_btn.set_tooltip_text("About X11 Monitor Dimmer")
        self.version_btn.connect("clicked", self.on_version)
        self.top_grid.attach(self.version_btn, 4, bottom_row, 1, 1)

        self.status_frame = Gtk.Frame()
        self.status_frame.set_shadow_type(Gtk.ShadowType.IN)
        self.status_frame.set_halign(Gtk.Align.FILL)
        self.status_frame.set_valign(Gtk.Align.FILL)
        self.status_label = Gtk.Label(label="")
        self.status_label.set_xalign(0.5)
        self.status_label.set_halign(Gtk.Align.FILL)
        self.status_label.set_valign(Gtk.Align.CENTER)
        self.status_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.status_frame.add(self.status_label)
        self.top_grid.attach(self.status_frame, 3, bottom_row + 1, 2, 1)

        self.all_default_buttons = {}
        for col, slot in ((5, 1), (6, 2)):
            btn = Gtk.Button()
            btn.set_halign(Gtk.Align.FILL)
            btn.set_valign(Gtk.Align.FILL)
            btn.connect("clicked", self.on_all_to_default, slot)
            self.all_default_buttons[slot] = btn
            self.top_grid.attach(btn, col, bottom_row, 1, 2)

        self.refresh_default_names()

        animals_row = bottom_row + 2
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

        self._connect_internal_click_cancel_recursive(self)

        self.show_all()
        self.animals_ui.refresh()
        GLib.idle_add(self._initial_setup)

    def _migrate_legacy_display_names(self):
        changed = False
        for mon in self.monitors:
            output = mon["output"]
            cfg_mon = self.config.setdefault("monitors", {}).setdefault(output, {})
            custom = str(cfg_mon.get("custom_name") or "").strip()
            if not custom:
                continue

            old_system = str(self.output_model_map.get(output) or "").strip()
            legacy_generated_names = {
                f"Monitor {output}",
                f"Display {output}",
            }
            if old_system:
                legacy_generated_names.add(f"{old_system} ({output})")

            if custom in legacy_generated_names:
                cfg_mon.pop("custom_name", None)
                changed = True

        if changed:
            save_config(self.config)

    def edid_display_name(self, mon):
        resolved = str(self.output_model_map.get(mon["output"]) or "").strip()
        return resolved

    def automatic_display_name(self, mon):
        resolved = self.edid_display_name(mon)
        if resolved:
            return resolved
        number = self.display_number_map.get(mon["output"], 1)
        return fallback_display_name(number)

    def effective_display_name(self, mon):
        cfg_mon = self.config.setdefault("monitors", {}).setdefault(mon["output"], {})
        custom = str(cfg_mon.get("custom_name") or "").strip()
        if custom:
            return custom
        return self.automatic_display_name(mon)

    def display_name_for_message(self, mon):
        return self.effective_display_name(mon)

    def get_default_name(self, slot):
        stored = self.config.setdefault("default_names", {})
        custom = str(stored.get(str(slot)) or "").strip()[:MAX_CUSTOM_NAME]
        return custom or f"Default {slot}"

    def default_value_error(self, brightness):
        brightness = int(brightness)
        if brightness >= 100:
            return "100% cannot be saved as a default. Use Dimmer Off to stop dimming."
        if brightness < MIN_DEFAULT:
            return "Brightness below 40% cannot be saved as a default."
        return None

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
            return 1120
        if mon_width >= 3840:
            return 1320
        return int(mon_width * 0.48)

    def _set_profile_numbers(self, mon_width):
        if mon_width <= 1920:
            self.window_w = 1120
            self.window_h_base = 268
            self.window_h_animals = 310

            display_actual = 126
            slider_actual = 280
            off_actual = 88
            default_panel_actual = 172
            monitor_row_h_actual = 78
            bottom_h_actual = 86
            btn_h_actual = 34
            quick_spacing_actual = 3
            bottom_inner_actual = 4
            default_inner_actual = 4
            default_row_actual = 2

            self.value_chars = 4
            self.small_font_pt = 8
            self.display_font_pt = 9
            self.value_font_pt = 10

            border_actual = 4
            outer_actual = 4
            h_spacing_actual = 6
            row_v_spacing_actual = 5
        else:
            self.window_w = 1320
            self.window_h_base = 280
            self.window_h_animals = 324

            display_actual = 150
            slider_actual = 370
            off_actual = 100
            default_panel_actual = 188
            monitor_row_h_actual = 82
            bottom_h_actual = 90
            btn_h_actual = 36
            quick_spacing_actual = 4
            bottom_inner_actual = 5
            default_inner_actual = 5
            default_row_actual = 3

            self.value_chars = 4
            self.small_font_pt = 8
            self.display_font_pt = 9
            self.value_font_pt = 11

            border_actual = 4
            outer_actual = 4
            h_spacing_actual = 7
            row_v_spacing_actual = 6

        self.display_w = self._lu(display_actual)
        self.slider_min_w = self._lu(slider_actual)
        self.off_btn_w = self._lu(off_actual)
        self.default_panel_w = self._lu(default_panel_actual)
        self.monitor_row_h = self._lu(monitor_row_h_actual)
        self.bottom_h = self._lu(bottom_h_actual)
        self.btn_h = self._lu(btn_h_actual)
        self.quick_spacing = self._lu(quick_spacing_actual)
        self.bottom_inner_spacing = self._lu(bottom_inner_actual)
        self.default_inner_spacing = self._lu(default_inner_actual)
        self.default_row_spacing = self._lu(default_row_actual)

        self.border_px = self._lu(border_actual)
        self.outer_spacing = self._lu(outer_actual)
        self.h_spacing = self._lu(h_spacing_actual)
        self.row_v_spacing = self._lu(row_v_spacing_actual)

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
            row.apply_size_profile()

        self.names_box.set_spacing(self.bottom_inner_spacing)
        self.names_box.set_size_request(self.display_w, self.bottom_h)
        self.name_displays_btn.set_size_request(self.display_w, -1)
        self.name_defaults_btn.set_size_request(self.display_w, -1)
        center_button_label(self.name_displays_btn, self.small_font_pt + 1)
        center_button_label(self.name_defaults_btn, self.small_font_pt + 1)

        self.all_off_btn.set_size_request(self.off_btn_w, self.bottom_h)
        center_button_label(self.all_off_btn, self.small_font_pt + 1)

        self.quick_box.set_spacing(self.quick_spacing)
        for btn in self.quick_buttons:
            btn.set_size_request(-1, self.btn_h)
            center_button_label(btn, self.small_font_pt)

        self.version_btn.set_size_request(-1, self.btn_h)
        center_button_label(self.version_btn, self.small_font_pt + 5)

        self.status_frame.set_size_request(-1, self.btn_h)
        self.status_label.modify_font(Pango.FontDescription(f"Sans {self.small_font_pt + 1}"))

        for btn in self.all_default_buttons.values():
            btn.set_size_request(self.default_panel_w, self.bottom_h)
            center_button_label(btn, self.small_font_pt + 2)

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
        for row in self.rows.values():
            row.refresh_value_label()
            row.update_restore_controls()
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
        self.cancel_close_countdown(show_message=False)
        self.set_opacity(0.0)
        self.show_all()
        self.animals_ui.refresh()

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
        self.cancel_close_countdown(show_message=False)
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

    def apply_brightness(self, output, brightness):
        brightness = int(brightness)
        self.current_brightness[output] = brightness

        mon = self.monitor_map.get(output)
        if mon is None:
            return

        # Critical runtime rule: 100% is not a transparent overlay. It fully
        # destroys/removes that monitor's overlay window.
        if brightness >= 100:
            self.overlay.turn_off(output)
        else:
            self.overlay.set_brightness(mon, brightness)

    def toggle_visibility(self):
        if self.is_visible():
            self.fade_hide()
        else:
            for output, row in self.rows.items():
                row.scale.set_value(self.current_brightness.get(output, 100))
                row.refresh_value_label()
                row.update_restore_controls()

            self.fade_show()
            self._register_controller_open()
            GLib.idle_add(self.move_to_host_output, self.config.get("ui_host_output"))

    def show_status(self, text):
        self.status_label.set_text(str(text))

    def refresh_display_names(self):
        for row in self.rows.values():
            row.refresh_display_name()

    def refresh_default_names(self):
        if hasattr(self, "rows"):
            for row in self.rows.values():
                row.refresh_default_names()
        if hasattr(self, "all_default_buttons"):
            for slot, btn in self.all_default_buttons.items():
                btn.set_label(f"All to\n{self.get_default_name(slot)}")
                center_button_label(btn, self.small_font_pt + 2)

    def _main_popup_anchor_geometry(self):
        """Return the single approved primary-popup geometry.

        Left/right are the slider/value footprint shifted left by exactly 4 px
        as previously approved. Width is preserved, so the right edge remains
        exactly 4 px before the Set-column boundary. Top is the controller
        client area's top edge, immediately below the native title bar.
        """
        if not self.rows:
            return None

        first_row = next(iter(self.rows.values()))
        try:
            quick_pos = self.quick_box.translate_coordinates(self, 0, 0)
            set_pos = first_row.set_panel.widget().translate_coordinates(self, 0, 0)
        except Exception:
            return None

        if quick_pos is None or set_pos is None:
            return None

        offset = self._lu(4)
        left = int(quick_pos[0]) - offset
        right = int(set_pos[0]) - offset
        top = 0
        width = right - left

        if width <= 0:
            return None
        return left, top, width

    def _root_coords_for_main_client_point(self, x, y):
        gdk_window = self.get_window()
        if gdk_window is None:
            return None
        try:
            coords = gdk_window.get_root_coords(int(x), int(y))
            if coords is not None and len(coords) >= 2:
                return int(coords[-2]), int(coords[-1])
        except Exception:
            pass
        try:
            origin = gdk_window.get_origin()
            if len(origin) == 3:
                _ok, ox, oy = origin
            else:
                ox, oy = origin
            return int(ox) + int(x), int(oy) + int(y)
        except Exception:
            return None

    def _prepare_main_popup(self, dialog):
        geometry = self._main_popup_anchor_geometry()
        if geometry is None:
            return False

        anchor_x, anchor_y, target_width = geometry
        root_pos = self._root_coords_for_main_client_point(anchor_x, anchor_y)
        if root_pos is None:
            return False
        root_x, root_y = root_pos

        if hasattr(dialog, 'lock_width'):
            dialog.lock_width(target_width)
        else:
            dialog.set_size_request(target_width, -1)

        # Realize while still hidden, settle the content-driven height, and move
        # before dialog.run() maps the first visible frame. No after-map move.
        dialog.set_position(Gtk.WindowPosition.NONE)
        dialog.realize()
        dialog.resize(int(target_width), 1)
        dialog.move(int(root_x), int(root_y))
        return True

    def _draw_modal_dim(self, widget, cr):
        """Paint a black 60% veil over the controller client area."""
        allocation = widget.get_allocation()
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.60)
        cr.rectangle(0, 0, allocation.width, allocation.height)
        cr.fill()
        return True

    def _show_modal_brightness_shade(self):
        """Darken the controller client area without changing window opacity.

        This is an in-window translucent black layer, not a second X11 window.
        Therefore the wallpaper never shows through the controller, there is no
        separate WM shadow/box, and the modal popup cannot be hidden beneath it.
        """
        if hasattr(self, 'modal_dim'):
            self.modal_dim.show()
            self.modal_dim.queue_draw()

    def _hide_modal_brightness_shade(self):
        if hasattr(self, 'modal_dim'):
            self.modal_dim.hide()

    def _begin_main_popup(self, dialog):
        positioned = self._prepare_main_popup(dialog)
        self._show_modal_brightness_shade()

        # Gtk.Dialog.run() does not show a hidden dialog. Map it only after
        # its final size/position have been prepared, so there is no visible
        # first-position jump.
        dialog.show_all()
        if positioned:
            geometry = self._main_popup_anchor_geometry()
            if geometry is not None:
                anchor_x, anchor_y, _target_width = geometry
                root_pos = self._root_coords_for_main_client_point(anchor_x, anchor_y)
                if root_pos is not None:
                    dialog.move(int(root_pos[0]), int(root_pos[1]))

        return None

    def _end_main_popup(self, _unused_previous_state=None):
        self._hide_modal_brightness_shade()

    def on_name_displays(self, *_args):
        self.cancel_close_countdown(show_message=False)
        dialog = NameDisplaysDialog(self)
        previous_opacity = self._begin_main_popup(dialog)
        try:
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                dialog.commit()
                self.show_status("Display names saved.")
        finally:
            dialog.destroy()
            self._end_main_popup(previous_opacity)

    def on_name_defaults(self, *_args):
        self.cancel_close_countdown(show_message=False)
        dialog = NameDefaultsDialog(self)
        previous_opacity = self._begin_main_popup(dialog)
        try:
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                dialog.commit()
                self.show_status("Default names saved.")
        finally:
            dialog.destroy()
            self._end_main_popup(previous_opacity)

    def on_quick_level(self, _button, level):
        self.cancel_close_countdown(show_message=False)
        for row in self.rows.values():
            row.scale.set_value(int(level))
        self.show_status(f"All displays set to {int(level)}%.")

    def on_all_off(self, *_args):
        self.cancel_close_countdown(show_message=False)
        for row in self.rows.values():
            row.scale.set_value(100)
        self.request_close_countdown("Dimming overlay terminated on all displays.")

    def on_all_to_default(self, _button, slot):
        self.cancel_close_countdown(show_message=False)
        restored = 0
        for row in self.rows.values():
            value = row.default_values.get(slot)
            if value is None:
                continue
            row.scale.set_value(int(value))
            row.update_restore_controls()
            restored += 1

        name = self.get_default_name(slot)
        if restored == 0:
            self.show_status(f"{name} has not been saved for any monitor.")
            return

        if restored == len(self.rows):
            base = f"{name} restored to all monitors."
        else:
            base = f"{name} restored to {restored} of {len(self.rows)} monitors."
        self.request_close_countdown(base)

    def request_close_countdown(self, base_message):
        """Start auto-close unless the For the Animals prompt needs a response first."""
        self.cancel_close_countdown(show_message=False)
        if self.animals.should_show():
            self._pending_close_after_animals = str(base_message)
            self.show_status(
                f"{base_message} Choose Remind me later or No thanks before auto-close."
            )
            return

        self.start_close_countdown(base_message)

    def start_close_countdown(self, base_message):
        self.cancel_close_countdown(show_message=False, clear_pending=False)
        self._pending_close_after_animals = None
        self._close_countdown_base = base_message
        self._close_countdown_remaining = 3
        self.show_status(f"{base_message} Closing in 3...")

        def tick():
            self._close_countdown_remaining -= 1
            if self._close_countdown_remaining <= 0:
                self._close_countdown_source = None
                self.fade_hide()
                return False
            self.show_status(
                f"{self._close_countdown_base} Closing in {self._close_countdown_remaining}..."
            )
            return True

        self._close_countdown_source = GLib.timeout_add_seconds(1, tick)

    def cancel_close_countdown(self, show_message=True, clear_pending=True):
        had_active_countdown = self._close_countdown_source is not None
        had_pending_countdown = self._pending_close_after_animals is not None

        if self._close_countdown_source is not None:
            try:
                GLib.source_remove(self._close_countdown_source)
            except Exception:
                pass
            self._close_countdown_source = None
            self._close_countdown_remaining = 0

        if clear_pending:
            self._pending_close_after_animals = None

        if show_message and (had_active_countdown or (clear_pending and had_pending_countdown)):
            self.show_status("Auto-close cancelled.")
        return False

    def _connect_internal_click_cancel_recursive(self, widget):
        # Intentional mouse clicks inside the application cancel an active
        # countdown. Pointer movement, scrolling, and clicks outside the app do not.
        try:
            widget.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            widget.connect("button-press-event", self._on_internal_click)
        except Exception:
            pass

        if isinstance(widget, Gtk.Container):
            try:
                for child in widget.get_children():
                    self._connect_internal_click_cancel_recursive(child)
            except Exception:
                pass

    def _on_internal_click(self, *_args):
        if self._close_countdown_source is not None:
            self.cancel_close_countdown(show_message=True)
        return False

    def on_version(self, *_args):
        self.cancel_close_countdown(show_message=False)

        dialog = AboutDialog(self)
        previous_opacity = self._begin_main_popup(dialog)
        try:
            while True:
                response = dialog.run()

                if response == ABOUT_CREDITS_RESPONSE:
                    credits = CreditsDialog(dialog)
                    credits.run()
                    credits.destroy()
                    continue

                if response == ABOUT_HISTORY_RESPONSE:
                    history = HistoryLogDialog(dialog)
                    history.run()
                    history.destroy()
                    continue

                if response == ABOUT_ROADMAP_RESPONSE:
                    roadmap = FutureRoadmapDialog(dialog)
                    roadmap.run()
                    roadmap.destroy()
                    continue

                break
        finally:
            dialog.destroy()
            self._end_main_popup(previous_opacity)

    def _resume_pending_close_after_animals(self):
        pending = self._pending_close_after_animals
        self._pending_close_after_animals = None
        if pending:
            self.start_close_countdown(pending)

    def on_animals_remind(self, *_args):
        self.animals.remind_me_later()
        save_config(self.config)
        self._refresh_for_the_animals()
        self._realign_to_current_host()
        self._resume_pending_close_after_animals()

    def on_animals_no_thanks(self, *_args):
        self.animals.no_thanks()
        save_config(self.config)
        self._refresh_for_the_animals()
        self._realign_to_current_host()
        self._resume_pending_close_after_animals()

    def on_delete(self, *_args):
        self.fade_hide()
        return True

    def shutdown(self):
        self.cancel_close_countdown(show_message=False)
        self.overlay.shutdown()
