# X11 Monitor Dimmer

A lightweight multi-display dimmer for **Linux X11**, originally authored by **Viridel48 through v0.85**.

## Status

**v0.85 is the final original-author X11 release.** Future Wayland or broader display-server support is intentionally left to community developers. **v1.0 is reserved for that future compatibility milestone.**

## Highlights

- independent overlay dimming for each connected display
- 100% means truly off: the corresponding overlay window is destroyed
- two independently stored defaults per display
- optional custom names for both defaults
- quick-dim presets from 90% through 20%
- global restore controls and **Dimmer Off All**
- EDID-based display names with safe `Display #N` fallback
- manual custom display names always take precedence
- host-display-aware controller placement
- panel/menu toggle workflow
- tray Show / Hide / Quit support
- compact About, Credits, History, and Future Roadmap panels
- restrained **For the Animals** support-the-author reminder

## Display naming

The display-name hierarchy is:

1. Custom name
2. EDID/system display name
3. `Display #N`

The controller presents the name and X11 port on two lines, for example:

```text
ARZOPA
DP-3
```

If the system cannot provide a model name, dimming functionality is completely unaffected. The easiest resolution is simply to enter a Custom name.

## Installation

v0.85 is distributed as a standard Debian/Ubuntu/Linux Mint `.deb` package.

1. Download `X11-Monitor-Dimmer-v0.85-Final.deb`.
2. Double-click the file.
3. Choose **Install Package** in the system package installer.
4. After installation, open the application menu, search for **X11 Monitor Dimmer**, and launch it.
5. On Cinnamon, right-click the running panel/taskbar icon and pin it if you want permanent one-click access.

The package manager handles the required runtime dependencies automatically. No terminal extraction step is required.

## Runtime model

- launcher: Show / Hide
- controller Close: Hide
- tray: Show / Hide / Quit
- **Dimmer Off All** and global default restores start an automatic close countdown
- mouse movement and activity outside the application do not cancel that countdown
- an intentional click inside the application cancels it
- if the **For the Animals** reminder is visible, that reminder must be resolved before a pending global-action countdown begins

## Requirements

Core runtime requirements include:

- Linux X11 session
- Python 3
- GTK 3 / PyGObject
- python-xlib
- `xrandr`
- `wmctrl`
- Ayatana AppIndicator GTK3 bindings for tray integration

The final application does not require hardware brightness control.

## Configuration

User configuration is stored under:

```text
~/.config/x11-monitor-dimmer/
```

Application files, documentation, and icon resources are installed system-wide by the package manager. Removing or upgrading the package does not require deleting your personal configuration.

## For the Animals

If this tool has been useful to you, please consider showing appreciation by donating to a local animal shelter or cruelty-prevention organization.

The in-application reminder is deliberately low-frequency: first appearance at open 100, **Remind me later** adds 10 opens, and **No thanks** adds 200 opens.

## Future roadmap

The original author's active development ends with v0.85. Community continuation is welcome for Wayland support, future display-server structures, compatibility work, and other enhancements.

If broader compatibility is implemented, the `X11` portion of the application name may be replaced with a more universally representative name.

The original author's preference is that the application remain freely available rather than becoming a paid product, subscription, paid-feature service, or other monetized software. This is an author preference, not an additional GPL licensing condition.

The **For the Animals** messaging should retain its intent; genuine enhancements such as location-aware shelter information, websites, or contact details are encouraged.

Consistent with the attribution principles recognized in GPLv3 Section 7(b), future developers are respectfully asked to retain the original project accreditation through future updates and enhancements: **Originally authored by Viridel48 through v0.85.** This is a request from the original author and is not intended as an additional licensing condition.

## License

GPL-3.0. See `LICENSE`.
