# X11 Monitor Dimmer

A lightweight multi-monitor dimmer for **Linux X11** with per-monitor overlay dimming, persistent monitor naming, host-monitor-aware controller placement, tray support, and optional EDID-based model name detection.

## Status

**Current project state:** stable for the original author's environment.

- Initial author: **viridel48**
- Current milestone snapshot: **v0.75**
- This project is being released to the community for further development.
- It is **unlikely to receive major future updates** from the initial author, because it already works correctly for the original configuration.
- **v1.0 is intentionally reserved for the point at which the project supports both X11 and Wayland.**

## Scope

This project currently targets:

- **Linux X11**
- GTK3
- Cinnamon-friendly workflow
- Per-monitor overlay dimming
- Read-only EDID-based model-name detection

This project does **not** currently target:

- Wayland
- full hardware brightness control via DDC/CI
- broad multi-desktop support guarantees
- universal packaging

## What matters most in everyday use

The following items are ranked by practical user impact, not by implementation order.

1. **Reliable per-monitor dimming on X11**
   - The project exists first and foremost to provide stable, practical monitor dimming where native brightness control is unsuitable or unavailable.

2. **Predictable controller behavior**
   - The controller opens, hides, reopens, and follows the selected host monitor reliably.
   - Geometry and placement are treated as first-class behavior, not cosmetic extras.

3. **Low-friction runtime flow**
   - Panel launcher toggles the controller.
   - The GUI **Close** button hides it.
   - Tray support provides **Show / Hide** and **Quit** without needing a terminal.

4. **Per-monitor defaults and clean monitor management**
   - Each monitor can be dimmed independently.
   - Defaults can be saved and restored.
   - Manual custom names are preserved.

5. **Model-aware labeling**
   - When available, EDID/model information is used to label displays clearly.
   - This improves usability without depending on full DDC/CI brightness control.

6. **Minimal overhead when dimming is functionally off**
   - A no-functional dim state should not leave a useless overlay running.

7. **Inline support-the-author reminder**
   - The `for_the_animals` line is intentionally low-priority and non-intrusive.
   - It is not a popup, not a blocker, and not part of normal control flow.
   - It exists only as a small support-the-author message encouraging users to consider donating to a local animal shelter or cruelty prevention service.
   - Under normal production settings, it should appear only rarely, generally a few times a year at most for ordinary usage.

## Confirmed working architecture

The codebase is split into focused modules:

- `ui_window.py` — top-level orchestration
- `ui_alignment.py` — window geometry and host-monitor positioning
- `ui_rows.py` — main monitor row widgets
- `ui_animals.py` — inline support-the-author row UI
- `for_the_animals.py` — launch-count reminder state/policy
- `ui_tray.py` — tray icon integration
- `ddcu.py` — read-only EDID/model/model-name resolution
- `overlay.py` — overlay dimming control
- `config.py` — persisted settings/config helpers

## Feature summary

- Per-monitor overlay dimming
- Per-monitor slider + Off button
- Save / Restore Default brightness
- Manual custom monitor naming
- Resolved monitor model names from EDID
- Default label format: `ModelName (Port)`
- Label precedence:
  1. Custom name override
  2. DDC/EDID model label in format `ModelName (Port)`
  3. Generic fallback `Monitor (Port)`
- Host-monitor-aware controller placement
- Shared-grid UI alignment
- Tray icon with Show / Hide and Quit
- Panel/taskbar launcher toggle workflow
- Inline `for_the_animals` support-the-author reminder
- Optional `ddcutil` installer helper

## Important behavior

### Open / close model

The intended everyday workflow is:

- panel or launcher button toggles the controller
- tray menu offers Show / Hide and Quit
- GUI **Close** hides the controller
- the app remains self-contained in the background until explicitly quit

### Overlay behavior

When dimming is functionally off, the overlay should not remain running as a no-op.  
A no-functional dim state should fully terminate or disable the overlay rather than keep dead overhead around.

## DDC / model-name support

This project does **not** currently rely on successful DDC/CI brightness control.

Instead, the implemented v0.60 path uses **read-only EDID/model detection** to resolve display names such as:

- `ARZOPA (DP-3)`
- `TOSHIBA-TV (DP-5)`

That means model-name retrieval can work even when full VCP brightness control does not.

## Dependencies

Core runtime depends on a typical GTK3/X11 Python environment plus a few external utilities.

Examples used in development:

- Python 3
- GTK 3 via PyGObject
- `wmctrl`
- `xrandr`

Optional or feature-dependent items:

- `ddcutil` for read-only model-name retrieval helpers
- Ayatana AppIndicator GI bindings for tray support

## Installation notes

This project currently assumes a local/manual install style rather than a packaged distribution.

Typical pieces include:

- Python launcher script
- local shell wrappers
- `.desktop` entries
- optional tray support
- optional `ddcutil` helper script

## Configuration notes

The app persists its state and supports:

- remembered host monitor
- remembered custom monitor names
- remembered defaults
- launch-count tracking for `for_the_animals`

## Notes on `for_the_animals`

The `for_the_animals` feature is intentionally restrained.

It is:

- an inline line in the controller window
- a support-the-author style note
- a prompt to consider donating to a local animal shelter or cruelty prevention service
- intentionally non-spammy

It is **not**:

- a popup
- a startup block
- a hard-disable mechanism
- a central feature of the dimmer

Production behavior is intentionally conservative:

- first appearance at open **100**
- **Remind me later** delays the next appearance by **10** more opens
- **No thanks** delays the next appearance by **200** more opens

For most ordinary use patterns, that means it should only appear a few times a year at most.

## Development notes

This repo is intentionally being released in a state that is:

- useful
- working
- modular enough for continuation

It is **not** claiming to be a broad final desktop product yet.

If you continue development, the most meaningful future targets are:

- broader desktop/session validation
- Wayland compatibility
- cleanup and packaging
- community-driven refinement

## Roadmap snapshot

- **v0.50** — `for_the_animals`
- **v0.60** — DDCU / read-only model retrieval
- **v0.75** — polish and runtime integration
- **v0.80** — GitHub/repo preparation
- **v1.0** — reserved for X11 + Wayland compatibility

## Tested environment

Known-good development environment included:

- Linux Mint Cinnamon
- X11
- NVIDIA proprietary driver path
- multi-monitor configuration with DP outputs

This does **not** guarantee identical behavior on all systems.

## Contributing

Community continuation is welcome.

Please keep changes focused and avoid rewriting stable modules unnecessarily, especially:

- `ui_alignment.py`
- confirmed working UI layout behavior
- stable tray/toggle runtime flow

## Author

Initial author: **viridel48**
