from __future__ import annotations
import ctypes
from Xlib import X, display, Xatom

from .config import MIN_BRIGHTNESS, MAX_BRIGHTNESS

SHAPE_SET = 0
SHAPE_INPUT = 2
YX_BANDED = 3


class OverlayManager:
    def __init__(self):
        self.disp = display.Display()
        self.screen = self.disp.screen()
        self.root = self.screen.root
        self.windows = {}

        self.x11 = ctypes.cdll.LoadLibrary("libX11.so.6")
        self.xext = ctypes.cdll.LoadLibrary("libXext.so.6")

        self.x11.XOpenDisplay.restype = ctypes.c_void_p
        self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.raw_disp = self.x11.XOpenDisplay(None)
        if not self.raw_disp:
            raise RuntimeError("Failed to open X display")

        self.xext.XShapeCombineRectangles.argtypes = [
            ctypes.c_void_p,
            ctypes.c_ulong,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        self.xext.XShapeCombineRectangles.restype = None

    def ensure_overlay(self, mon):
        output = mon["output"]
        if output in self.windows:
            return self.windows[output]

        win = self.root.create_window(
            int(mon["x"]),
            int(mon["y"]),
            int(mon["width"]),
            int(mon["height"]),
            0,
            int(self.screen.root_depth),
            X.InputOutput,
            X.CopyFromParent,
            background_pixel=int(self.screen.black_pixel),
            override_redirect=1,
            event_mask=0,
        )

        state_atom = self.disp.intern_atom("_NET_WM_STATE")
        above_atom = self.disp.intern_atom("_NET_WM_STATE_ABOVE")
        win.change_property(state_atom, Xatom.ATOM, 32, [above_atom])

        win.map()
        self.disp.sync()

        self.xext.XShapeCombineRectangles(
            self.raw_disp,
            int(win.id),
            SHAPE_INPUT,
            0,
            0,
            None,
            0,
            SHAPE_SET,
            YX_BANDED,
        )
        self.x11.XFlush(ctypes.c_void_p(self.raw_disp))

        self.windows[output] = win
        return win

    def set_brightness(self, mon, brightness):
        brightness = max(MIN_BRIGHTNESS, min(MAX_BRIGHTNESS, int(brightness)))
        if brightness >= 100:
            self.turn_off(mon["output"])
            return

        win = self.ensure_overlay(mon)
        opacity_atom = self.disp.intern_atom("_NET_WM_WINDOW_OPACITY")
        opacity = 1.0 - (brightness / 100.0)
        opacity_value = int(0xFFFFFFFF * opacity)
        win.change_property(opacity_atom, Xatom.CARDINAL, 32, [opacity_value])
        self.disp.sync()

    def turn_off(self, output):
        win = self.windows.pop(output, None)
        if win is None:
            return
        try:
            win.destroy()
            self.disp.sync()
        except Exception:
            pass

    def shutdown(self):
        for output in list(self.windows.keys()):
            self.turn_off(output)
        try:
            self.disp.close()
        except Exception:
            pass
