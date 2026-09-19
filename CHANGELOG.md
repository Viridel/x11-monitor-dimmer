# Changelog

## v0.85 — Final X11 release
Since v0.80:
- Implemented a standard Debian/Ubuntu/Linux Mint installer with dependency handling, application-menu integration, desktop shortcut creation, and upgrade support.
- Added the dedicated project icon and improved launcher / panel integration.
- Finalized the shared popup-shell design, modal background dimming, and consistent Name Displays / Name Defaults / About presentation.
- Corrected final GUI formatting, sizing, alignment, and popup-behavior issues discovered during live testing.
- Final original-author X11 release.

## v0.80 — Controller redesign development milestone
- Added a second independent saved default for each display.
- Added custom names for both saved defaults.
- Added per-display Set / Restore controls for both defaults.
- Added global **All to [Default]** controls.
- Added quick-dim preset buttons from 90% through 20%.
- Added **Dimmer Off All** with automatic controller close.
- Added **Name Defaults** management.
- Improved display identification with Custom → EDID/system → `Display #N` fallback.
- Added graceful missing-EDID guidance without affecting dimming functionality.
- Added the **ⓘ Information** panel with Credits, Full History Log, and Future Roadmap.
- Refined auto-close so only intentional clicks inside the application interrupt the countdown.

## v0.75
- Runtime flow completed into a self-contained desktop-style application model.
- Panel launcher toggle flow finalized.
- Tray support added with Show / Hide and Quit.
- Quit helper added.
- `ui_animals.py` extracted from `ui_window.py`.
- Read-only display model-name integration finalized in the live UI at that milestone.
- Backup / locked-state workflow matured for milestone preservation.

## v0.60
- Display-identification work narrowed to read-only model retrieval.
- Full DDC/CI brightness control explicitly removed from project scope.
- `ddcutil` was explored during development but was not required by the final identification path.
- EDID-backed model-name retrieval was verified from the X11 display stack.

## v0.50
- `for_the_animals` feature implemented.
- Inline support-the-author message added to the controller window.
- Launch-count-based reminder logic finalized.
- Production reminder behavior established:
  - first appearance at open 100
  - **Remind me later** = +10 opens
  - **No thanks** = +200 opens

## Pre-v0.50 foundation work

### Core dimmer architecture
- Project established as an **X11 overlay dimmer** rather than a gamma/colour-shift tool.
- Real per-display overlay dimming made functional.
- Overlay lifecycle stabilized so a functionally-off state destroys the overlay instead of leaving a transparent no-op window.
- Persistent configuration support established.

### Main controller behavior
- Per-display slider workflow implemented.
- Per-display Off behavior implemented.
- Save / Restore default-brightness behavior implemented.
- Default validation rules added.
- Error messaging refined and kept inline instead of disruptive popups.

### Naming and display identity
- Manual custom display naming implemented.
- Reset naming behavior added.
- Fallback naming and persistence stabilized before later EDID/model integration.

### Windowing and placement
- Host-display selection and persistence implemented.
- Controller movement between displays implemented.
- Always-on-top, top-middle placement, and fade behavior established.

### UI refactor and alignment
- Independent row layouts were replaced by a shared-grid layout.
- Column alignment and bottom-control positioning were stabilized.
- Geometry logic was extracted into `ui_alignment.py`.
- Confirmed host alignment achieved across the development 1080p and 4K display configuration.

### Runtime and project structure
- Single-instance and signal-based show/hide behavior implemented.
- Close-button behavior finalized as hide rather than terminate.
- Toggle launcher wrapper established.
- Codebase split into focused modules for overlay, alignment, rows, window orchestration, tray support, and reminder state.
