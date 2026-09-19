# X11 Monitor Dimmer v0.85

## Final original-author X11 release

v0.85 is the final X11 release planned from the original author, **Viridel48**.

The major improvements since v0.75 are:

- two independent saved defaults for every display
- optional custom names for both defaults
- compact per-display Set / Restore controls
- global **All to [Default]** controls
- quick-dim buttons from 90% through 20%
- **Dimmer Off All** with automatic controller close
- compact **Name Displays** and **Name Defaults** management
- Custom → EDID/system → `Display #N` identification fallback
- clear missing-EDID guidance that does not treat identification failure as a dimming failure
- a dedicated **ⓘ Information** panel with Credits, Full History Log, and Future Roadmap
- improved auto-close behavior that ignores mouse movement and outside clicks
- a unique project icon for the launcher, desktop shortcut, application window, and tray indicator
- a standard Debian/Ubuntu/Linux Mint installation package

At 100%, the dimming overlay is fully terminated rather than left running as a transparent overlay.

## Installation

Download `X11-Monitor-Dimmer-v0.85-Final.deb`, double-click it, and choose **Install Package**.

After installation, open the application menu and launch **X11 Monitor Dimmer**. On Cinnamon, the running taskbar/panel icon can then be pinned for permanent one-click access.

Required runtime packages are handled by the package manager.

## Future development

The original author's active development ends with v0.85. **v1.0 is reserved for Wayland support and/or broader display-server compatibility implemented by future community developers.**
