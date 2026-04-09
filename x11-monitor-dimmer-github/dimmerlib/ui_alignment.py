from __future__ import annotations

import subprocess

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib


class WindowAligner:
    def __init__(
        self,
        window,
        target_width_fn,
        size_profile_callback=None,
        top_margin=8,
        second_pass_ms=90,
    ):
        self.window = window
        self.target_width_fn = target_width_fn
        self.size_profile_callback = size_profile_callback
        self.top_margin = int(top_margin)
        self.second_pass_ms = int(second_pass_ms)

    def _ui_scale(self):
        try:
            scale = self.window.get_scale_factor()
            if scale and scale > 0:
                return int(scale)
        except Exception:
            pass
        return 1

    def _xid(self):
        try:
            gdk_win = self.window.get_window()
            if gdk_win is None:
                return None
            return int(gdk_win.get_xid())
        except Exception:
            return None

    def _read_wmctrl_geometry(self, xid):
        if xid is None:
            return None

        try:
            result = subprocess.run(
                ["wmctrl", "-lG"],
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            return None

        if result.returncode != 0:
            return None

        for raw_line in result.stdout.splitlines():
            parts = raw_line.split(None, 7)
            if len(parts) < 7:
                continue

            try:
                line_xid = int(parts[0], 16)
            except Exception:
                continue

            if line_xid != xid:
                continue

            try:
                return {
                    "x": int(parts[2]),
                    "y": int(parts[3]),
                    "w": int(parts[4]),
                    "h": int(parts[5]),
                }
            except Exception:
                return None

        return None

    def _request_size(self, mon):
        target_actual_w = int(self.target_width_fn(mon["width"]))
        target_actual_h = int(getattr(self.window, "window_h", 148))
        scale = self._ui_scale()

        logical_w = max(1, round(target_actual_w / scale))
        logical_h = max(1, round(target_actual_h / scale))

        self.window.resize(logical_w, logical_h)

    def _move_to(self, xid, x, y):
        if xid is not None:
            try:
                subprocess.run(
                    ["wmctrl", "-i", "-r", hex(xid), "-e", f"0,{x},{y},-1,-1"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                return
            except Exception:
                pass

        try:
            self.window.move(x, y)
        except Exception:
            pass

    def _align_once(self, mon):
        if self.size_profile_callback is not None:
            self.size_profile_callback(mon)

        self.window.show_all()
        self._request_size(mon)

        while Gtk.events_pending():
            Gtk.main_iteration_do(False)

        xid = self._xid()
        geom = self._read_wmctrl_geometry(xid)

        if geom is not None:
            actual_w = int(geom["w"])
        else:
            try:
                logical_w, _logical_h = self.window.get_size()
                actual_w = int(logical_w * self._ui_scale())
            except Exception:
                actual_w = int(self.target_width_fn(mon["width"]))

        x = int(mon["x"] + max(0, (mon["width"] - actual_w) // 2))
        y = int(mon["y"] + self.top_margin)

        self._move_to(xid, x, y)
        return False

    def align_to_monitor(self, mon):
        self._align_once(mon)
        GLib.timeout_add(self.second_pass_ms, self._align_once, mon)
        return False
